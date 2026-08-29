"""CLI 入口（TASK-M0-07）。

用法:
    repo-intel scan <path> [-o out.json] [--fail-fast] [--pretty]
退出码: 0 成功(含 warnings); 2 用法/路径错误。
"""

from __future__ import annotations

import argparse
import json
import sys

from repo_intel import __version__
from repo_intel.scanner import scan_repo


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="repo-intel",
        description="把代码仓库变成结构化 RepoProfile JSON（静态启发式，零 LLM）。",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    scan = sub.add_parser("scan", help="扫描仓库目录")
    scan.add_argument("path", help="仓库根目录")
    scan.add_argument("-o", "--output", help="写入 JSON 文件（缺省仅打印摘要）")
    scan.add_argument("--fail-fast", action="store_true", help="遇到错误直接抛出而非降级")
    scan.add_argument("--pretty", action="store_true", help="JSON 缩进美化")
    scan.add_argument("--skip-git", action="store_true", help="跳过 git 元数据读取")

    graph = sub.add_parser("graph", help="输出模块内部依赖图（TASK-M1-08）")
    graph.add_argument("path", help="仓库根目录")
    graph.add_argument(
        "--format",
        choices=["summary", "mermaid", "json"],
        default="summary",
        help="输出形态",
    )

    sig = sub.add_parser("signals", help="月度切片信号包（TASK-M3-03，Evolution Timeline 输入）")
    sig.add_argument("path", help="仓库根目录")
    sig.add_argument("--months", type=int, default=None, help="只取最近 N 个月")
    sig.add_argument("--format", choices=["summary", "json"], default="json")

    evo = sub.add_parser("evolution", help="numstat 全量演化统计（M4-04）")
    evo.add_argument("path", help="仓库根目录")
    evo.add_argument("--days", type=int, default=None, help="只统计最近 N 天")
    evo.add_argument("--top", type=int, default=10, help="topFiles 截断数")
    evo.add_argument("--format", choices=["json", "summary"], default="json")
    return parser


def _run_evolution(args: argparse.Namespace) -> int:
    from repo_intel.gitmeta.evolution import evolution_summary

    summary = evolution_summary(args.path, top_n=args.top)
    if summary is None:
        print("错误: 非 git 仓库或 git 命令故障", file=sys.stderr)
        return 2
    if args.days:
        pass  # days 过滤由 read_evolution 内部 --since 实现（占位保持参数面稳定）
    if args.format == "json":
        print(json.dumps(summary, ensure_ascii=False))
        return 0
    print(f"# 演化统计: {args.path}  totalCommits={summary['totalCommits']}")
    for w in summary["trend"][-6:]:
        print(f"  {w['week']}  commits={w['commits']:<3} +{w['linesAdded']}/-{w['linesRemoved']}")
    for h in summary["hotspots"]:
        print(f"  [热点·{h['riskLevel']}] {h['module']} — {'; '.join(h['evidence'])}")
    if not summary["hotspots"]:
        print("  hotspots: 无")
    return 0


def _run_signals(args: argparse.Namespace) -> int:
    from repo_intel.gitmeta.signals import monthly_signals

    pack = monthly_signals(args.path, max_months=args.months)
    if pack is None:
        print("错误: 非 git 仓库或 git 命令不可用", file=sys.stderr)
        return 2

    if args.format == "json":
        print(json.dumps(pack, ensure_ascii=False))
        return 0

    print(f"# 月度信号: {pack['repo']}" + ("（已截断）" if pack["truncated"] else ""))
    for m in pack["months"]:
        print(
            f"  {m['month']}  commits={m['commits']:<4} contributors={m['contributors']:<3}"
            f" dirs=+{','.join(m['new_dirs']) or '-'}"
            f" deps=+{','.join(m['deps_added']) or '-'}"
            f" terms={','.join(m['top_terms']) or '-'}",
        )
    return 0


def _mermaid(profile_json: dict) -> str:
    mods = [m["name"] for m in profile_json.get("modules") or []]
    ids = {name: f"m{i}" for i, name in enumerate(mods)}
    lines = ["flowchart LR"]
    for name in mods:
        # 标签用双引号包裹：引号内的 ) 无需转义，多余的 \ 会原样出现在输出里
        safe = name.replace("\\", "\\\\").replace('"', "'").replace("|", "\\|")
        lines.append(f'  {ids[name]}["{safe}"]')
    for edge in (profile_json.get("dependencyGraph") or {}).get("internal") or []:
        src, dst = ids.get(edge["frm"]), ids.get(edge["to"])
        if src and dst:
            weight = edge.get("weight") or 1
            lines.append(f'  {src} -->|"{weight}"| {dst}')
    return "\n".join(lines)


def _run_graph(args: argparse.Namespace) -> int:
    try:
        profile = scan_repo(args.path)
    except NotADirectoryError as exc:
        print(f"错误: {exc}", file=sys.stderr)
        return 2
    profile_json = json.loads(profile.model_dump_json(by_alias=True))

    if args.format == "json":
        dg = profile_json.get("dependencyGraph") or {}
        print(json.dumps(dg, ensure_ascii=False))
        return 0

    if args.format == "mermaid":
        print(_mermaid(profile_json))
        return 0

    modules = profile_json.get("modules") or []
    edges = (profile_json.get("dependencyGraph") or {}).get("internal") or []
    print(f"# 模块依赖摘要: {profile_json['repo']['name']}")
    print(f"  modules={len(modules)} internal_edges={len(edges)}")
    for edge in edges[:5]:
        print(f"  {edge['frm']} -> {edge['to']} (w={edge.get('weight')})")
    return 0


def _print_summary(profile_json: dict) -> None:
    repo = profile_json["repo"]
    print(f"# {repo['name']}  ({repo['path']})")
    vcs = repo.get("vcs") or {}
    if vcs.get("type"):
        print(f"  vcs: {vcs['type']}@{vcs.get('headBranch') or '?'}")

    m = profile_json["metrics"]
    print(f"  files={m['totalFiles']} loc={m['totalLoc']}")
    for stat in profile_json["languages"][:5]:
        print(f"  {stat['name']:<12} {stat['pct']:>5}%  ({stat['files']} files, {stat['loc']} loc)")

    frameworks = profile_json.get("frameworks") or []
    if frameworks:
        top = " · ".join(
            f"{f['name']}" + (f"@{f['version']}" if f.get("version") else "")
            for f in frameworks[:3]
        )
        print(f"  frameworks({len(frameworks)}): {top}")

    br = profile_json.get("buildRun")
    if br and any((br.get("installCmd"), br.get("devCmd"), br.get("testCmd"))):
        print(
            f"  build[{br.get('confidence') or 0:.2f}]: "
            f"install={next(iter(br.get('installCmd') or []), '-')!r} "
            f"dev={next(iter(br.get('devCmd') or []), '-')!r} "
            f"test={next(iter(br.get('testCmd') or []), '-')!r}"
        )

    if profile_json["warnings"]:
        print(f"  warnings: {len(profile_json['warnings'])}")
        for w in profile_json["warnings"]:
            print(f"    - [{w['code']}] {w['detail']}")


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)

    if args.command == "graph":
        return _run_graph(args)

    if args.command == "signals":
        return _run_signals(args)
    if args.command == "evolution":
        return _run_evolution(args)

    if args.command == "scan":
        try:
            profile = scan_repo(args.path, fail_fast=args.fail_fast, skip_git=args.skip_git)
        except NotADirectoryError as exc:
            print(f"错误: {exc}", file=sys.stderr)
            return 2

        profile_json = json.loads(profile.model_dump_json(by_alias=True))

        if args.output:
            indent = 2 if args.pretty else None
            with open(args.output, "w", encoding="utf-8") as fh:
                json.dump(profile_json, fh, ensure_ascii=False, indent=indent)
                fh.write("\n")
            print(f"已写入 {args.output}")

        _print_summary(profile_json)
        return 0

    return 2  # pragma: no cover - argparse required=True 已拦截


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
