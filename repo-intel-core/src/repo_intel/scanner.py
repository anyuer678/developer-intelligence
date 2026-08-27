"""扫描编排器：单趟 os.walk，剪枝式排除，喂给各检测器（TASK-M0-05/06 汇合点）。

原则：对垃圾输入的唯一合法反应是降级并写 warnings。
"""

from __future__ import annotations

import heapq
import os
from pathlib import Path

from repo_intel import __version__
from repo_intel.detect.buildrun import infer_build_run
from repo_intel.detect.entrypoints import detect_entrypoints
from repo_intel.detect.excludes import Excluder, ExclusionRule
from repo_intel.detect.extdeps import collect_declared, parse_external_deps, read_go_module_prefix
from repo_intel.detect.frameworks import detect_frameworks
from repo_intel.detect.language import (
    LanguageRules,
    classify_extension,
    shebang_language,
)
from repo_intel.detect.modules import GraphBuilder
from repo_intel.detect.quality import build_test_evidence, scan_hotspots_and_todos
from repo_intel.detect.structure import ROOT_BUCKET, StructureAggregator, count_lines
from repo_intel.gitmeta.reader import read_git_meta, read_vcs_info
from repo_intel.rules.loader import excludes_rules, languages_rules
from repo_intel.schema.profiles import (
    CallGraph,
    DependencyGraph,
    LanguageStat,
    LargestFile,
    Metrics,
    RepoInfo,
    RepoProfile,
    StructureInfo,
    ToolInfo,
    TopLevelDir,
    VcsInfo,
    WarningItem,
)

_SHEBANG_PEEK_BYTES = 4096
_TEXT_BUDGET_BYTES = 16_000_000  # 导入解析文本缓存上限，超限静默降级
_STASH_LANGS = {"python", "go", "typescript", "javascript", "java"}  # PARSE_LANGS ∪ java（调用图）


def _detect_vcs(root: Path) -> VcsInfo:
    """M4 收尾：委托 gitmeta 统一实现（兼容 worktree 指针文件）。"""
    return read_vcs_info(root)


def _stem_ext(name: str) -> tuple[str, str]:
    """(小写文件名, 小写扩展名带点)。无扩展名或隐藏文件(.gitignore 类)返回 ''。"""
    lower = name.lower()
    dot = lower.rfind(".")
    if dot <= 0:
        return lower, ""
    return lower[:dot], lower[dot:]


def scan_repo(
    root: str | os.PathLike[str],
    *,
    fail_fast: bool = False,
    skip_git: bool = False,
) -> RepoProfile:
    """扫描仓库目录，返回 RepoProfile。任何单文件失败降级为 warning。"""
    root_path = Path(root).resolve()
    if not root_path.is_dir():
        raise NotADirectoryError(f"不是有效目录: {root_path}")

    lang_rules = LanguageRules(languages_rules())
    excl_rule = ExclusionRule.from_rules(excludes_rules())
    excluder = Excluder(root_path, excl_rule)
    structure = StructureAggregator()

    lang_stats: dict[str, list[int]] = {}  # lang -> [files, loc]
    data_files = 0
    big_file_skipped = 0
    read_errors = 0
    total_files = 0
    largest: list[tuple[int, str]] = []  # min-heap (loc, rel)，保留 top8 再取前5
    config_files: set[str] = set()
    root_ecosystems: set[str] = set()
    kept_code: dict[str, str] = {}  # rel -> 语言桶（全部代码文件）
    code_texts: dict[str, tuple[str, str]] = {}  # rel -> (语言, 源码文本) 仅供解析
    text_budget = _TEXT_BUDGET_BYTES
    loc_by_file: dict[str, int] = {}
    todo_total = 0
    fixme_total = 0

    for dirpath, dirnames, filenames in os.walk(root_path):
        rel_dir = os.path.relpath(dirpath, root_path)
        rel_dir_posix = "" if rel_dir == "." else Path(rel_dir).as_posix()

        # 目录剪枝：原地过滤，阻止下钻
        dirnames[:] = [d for d in sorted(dirnames) if not excluder.is_ignored_dir(d, rel_dir_posix)]

        is_root = not rel_dir_posix
        for fname in sorted(filenames):
            rel_posix = f"{rel_dir_posix}/{fname}" if rel_dir_posix else fname
            if excluder.is_ignored_file(rel_posix, fname):
                continue

            if is_root:
                eco = lang_rules.manifests.get(fname)
                if eco:
                    config_files.add(fname)
                    root_ecosystems.add(eco)
                elif fname in lang_rules.monorepo_markers or fname in lang_rules.root_markers:
                    config_files.add(fname)

            full = Path(dirpath) / fname
            try:
                size = full.stat().st_size
            except OSError:
                read_errors += 1
                continue
            total_files += 1

            _, ext = _stem_ext(fname)
            code_lang, is_data = classify_extension(lang_rules, ext)

            loc = 0
            bucket: str | None = None
            if code_lang:
                bucket = code_lang
            elif is_data:
                pass
            elif not ext:
                # 无扩展名：shebang 指纹（只读首行，最多 4KB）
                try:
                    with full.open("rb") as fh:
                        bucket = shebang_language(
                            lang_rules,
                            fh.readline(_SHEBANG_PEEK_BYTES),
                        )
                except OSError:
                    read_errors += 1
            # 其余：带扩展名但两边都不认识 → 静默忽略（M0 不设 unknown 桶）

            if bucket:
                kept_code[rel_posix] = bucket
                if size <= excl_rule.max_file_bytes:
                    try:
                        raw = full.read_bytes()
                        loc = count_lines(raw)
                        t, f = raw.count(b"TODO"), raw.count(b"FIXME")
                        todo_total += t
                        fixme_total += f
                        if bucket in _STASH_LANGS and text_budget > 0:
                            code_texts[rel_posix] = (bucket, raw.decode("utf-8", errors="replace"))
                            text_budget -= len(raw)
                    except OSError:
                        read_errors += 1
                        loc = 0
                else:
                    big_file_skipped += 1
                loc_by_file[rel_posix] = loc

            structure.add_file(rel_posix.split("/"), fname)

            if bucket:
                pair = lang_stats.setdefault(bucket, [0, 0])
                pair[0] += 1
                pair[1] += loc
                heapq.heappush(largest, (loc, rel_posix))
                if len(largest) > 8:
                    heapq.heappop(largest)
            elif is_data:
                data_files += 1

    # ---------------- warnings（顺序稳定）----------------
    warnings: list[WarningItem] = []
    ecosystems = {e for e in root_ecosystems if e != "docker" and e != "make"}
    if len(ecosystems) >= 2:
        warnings.append(
            WarningItem(
                code="MIXED_MONOREPO",
                detail=f"检测到多生态 manifest 共存: {', '.join(sorted(ecosystems))}",
            ),
        )
    markers = [m for m in lang_rules.monorepo_markers if (root_path / m).is_file()]
    if markers:
        warnings.append(
            WarningItem(code="MONOREPO_MARKERS", detail=f"monorepo 标志: {', '.join(markers)}"),
        )
    if big_file_skipped:
        warnings.append(
            WarningItem(
                code="BIG_FILE_SKIPPED",
                detail=f"{big_file_skipped} 个超大代码文件只计数未解析",
            ),
        )
    if read_errors:
        warnings.append(WarningItem(code="READ_ERRORS", detail=f"{read_errors} 个文件读取失败"))
    if total_files > excl_rule.soft_file_limit:
        warnings.append(
            WarningItem(code="FILE_LIMIT_EXCEEDED", detail=f"文件数 {total_files} 超过软上限"),
        )
    if total_files == 0:
        warnings.append(WarningItem(code="EMPTY_REPO", detail="未发现任何文件"))
    git_meta = None if skip_git else read_git_meta(root_path)
    if not skip_git and (root_path / ".git").exists() and git_meta is None:
        warnings.append(
            WarningItem(code="GIT_META_UNAVAILABLE", detail="git 命令不可用或仓库损坏"),
        )

    # ---------------- 语言占比 ----------------
    total_loc = sum(v[1] for v in lang_stats.values())
    languages: list[LanguageStat] = []
    if total_loc > 0:
        languages = sorted(
            (
                LanguageStat(
                    name=name, pct=round(pair[1] * 100.0 / total_loc, 1), files=pair[0], loc=pair[1]
                )
                for name, pair in lang_stats.items()
            ),
            key=lambda s: (-s.loc, s.name),
        )

    top_rows, root_count = structure.finalize()
    top_level_dirs = [
        TopLevelDir(path=name, file_count=count, role=role) for name, count, role in top_rows
    ]
    if root_count:
        top_level_dirs.append(TopLevelDir(path=ROOT_BUCKET, file_count=root_count, role=None))

    biggest = sorted(largest, key=lambda t: -t[0])[:5]

    # ---------------- M1：入口点 / 模块划分 / 依赖图（启用后恒为列表，不再置 null）----------------
    entry_hits = detect_entrypoints(code_texts, root_path)
    builder = GraphBuilder(
        code_files=kept_code,
        texts={rel: text for rel, (_lang, text) in code_texts.items()},
        go_prefix=read_go_module_prefix(root_path),
    )
    modules_list, internal_edges = builder.build()
    external_deps = parse_external_deps(root_path)

    # ---------------- M2：框架 / buildRun / 质量指标 ----------------
    declared = collect_declared(root_path)  # name_l -> (ver, source, kind, orig)
    dep_view = {name_l: (ver, source) for name_l, (ver, source, _k, _o) in declared.items()}
    frameworks_hits = detect_frameworks(kept_code, code_texts, dep_view)
    build_run = infer_build_run(root_path, root_ecosystems)
    hotspots, todos = scan_hotspots_and_todos(code_texts, loc_by_file)
    test_evidence = build_test_evidence(kept_code, dep_view)

    # ------- M4-03：函数级调用图（可选能力，缺 tree-sitter 保持 null 三态）-------
    from repo_intel.detect.callgraph import build_call_graph

    arch_texts = {
        rel: (lang, text) for rel, (lang, text) in code_texts.items() if lang in _STASH_LANGS
    }
    cg_raw = build_call_graph(arch_texts) if arch_texts else None
    call_graph_model = CallGraph(**cg_raw) if cg_raw else None

    return RepoProfile(
        tool=ToolInfo(version=__version__),
        repo=RepoInfo(path=str(root_path), name=root_path.name, vcs=_detect_vcs(root_path)),
        languages=languages,
        structure=StructureInfo(top_level_dirs=top_level_dirs, config_files=sorted(config_files)),
        metrics=Metrics(
            total_loc=total_loc,
            total_files=total_files,
            largest_files=[LargestFile(path=p, loc=loc_) for loc_, p in biggest],
            complexity_hotspots=hotspots,
            test_evidence=test_evidence,
            todos=todos if (todos.todo_count or todos.fixme_count) else None,
        ),
        warnings=warnings,
        entry_points=entry_hits,
        modules=modules_list,
        dependency_graph=DependencyGraph(internal=internal_edges, external=external_deps),
        frameworks=frameworks_hits,
        build_run=build_run,
        call_graph=call_graph_model,
        git=git_meta,
    )
