"""质量指标（TASK-M2-04 / M4#1）：热点启发式 / 认知复杂度 / 测试证据 / TODO 字节计数。"""

from __future__ import annotations

import re
from fnmatch import fnmatch

from repo_intel.detect.modules import PARSE_LANGS
from repo_intel.schema.profiles import ComplexityHotspot, TestEvidence, TodoStats

_LONG_FILE_LOC = 400
_DEEP_SPACES = 24
_DEEP_TABS = 6
_COMPLEX_THRESHOLD = 12  # 移植自 evocode complexity_scan（ADR：含深度累积特性，按原版口径）

_BRANCH_RE = re.compile(
    r"\b(?:if|elif|else if|for|while|catch|switch)\b|\bcase\s|\b(?:&&|\|\||\?)\b",
)
_PY_DEF_RE = re.compile(r"^\s*(?:async\s+)?def\s+\w+\s*\(")
_GO_FUNC_RE = re.compile(r"^\s*func\s")
_BRACED_FUNC_RE = re.compile(
    r"^\s*(?!(?:for|if|while|switch|catch|do)\b)"
    r"(?:(?:public|private|protected|static|final|async|export)\s+)*"
    r"(?:function\s+\w+|[\w$<>,\s]+\s+\w+\s*\([^)]*\)\s*(?:throws[\s\w,]+)?\{)"
)
_COMPLEX_LANGS = {"python", "go", "typescript", "javascript"}

_TEST_PATTERNS = ("test_*.py", "*_test.py", "*_test.go", "*.test.*", "*.spec.*")
_TEST_FRAMEWORKS_BY_FILE = (
    ("*.test.*", "vitest/jest"),
    ("*.spec.*", "vitest/jest"),
    ("*_test.go", "go-test"),
)
_TEST_FW_BY_DEP = {
    "pytest": "pytest",
    "vitest": "vitest",
    "jest": "jest",
    "playwright": "playwright",
}


def is_test_file(rel_posix: str) -> bool:
    # 目录语义：tests/（含嵌套）下的文件一律视为测试
    if rel_posix.startswith("tests/") or rel_posix.startswith("test/") or "/tests/" in rel_posix:
        return True
    name = rel_posix.rsplit("/", 1)[-1]
    return any(fnmatch(name, pat) or fnmatch(rel_posix, f"**/{pat}") for pat in _TEST_PATTERNS)


def count_todos(data: bytes) -> tuple[int, int]:
    """字节级大小写敏感计数（ADR-010）。"""
    return data.count(b"TODO"), data.count(b"FIXME")


def scan_hotspots_and_todos(
    texts: dict[str, tuple[str, str]],
    loc_by_file: dict[str, int],
) -> tuple[list[ComplexityHotspot], TodoStats]:
    hotspots: list[ComplexityHotspot] = []
    todo_total = 0
    fixme_total = 0

    for rel in sorted(texts):
        lang, text = texts[rel]
        if lang not in PARSE_LANGS:
            continue
        loc = loc_by_file.get(rel, 0)
        if loc >= _LONG_FILE_LOC:
            hotspots.append(ComplexityHotspot(path=rel, signal=f"long-file loc={loc}"))
        deep = _max_indent(text)
        if deep >= _DEEP_SPACES:
            hotspots.append(
                ComplexityHotspot(path=rel, signal=f"deep-nesting indent={deep}"),
            )
        if lang in _COMPLEX_LANGS:
            worst = scan_complexity(text, lang)
            if worst:
                name, score, count = worst
                hotspots.append(
                    ComplexityHotspot(
                        path=rel,
                        signal=f"cognitive-complexity max={score} fn={name} over={count}",
                    ),
                )

    for _lang, text in texts.values():
        raw = text.encode("utf-8", errors="ignore")
        t, f = count_todos(raw)
        todo_total += t
        fixme_total += f

    hotspots.sort(key=lambda h: h.path)
    return hotspots, TodoStats(todo_count=todo_total, fixme_count=fixme_total)


def _complexity_of_block(lines: list[str], start: int, end: int) -> int:
    """块内认知复杂度：分支数 + 嵌套惩罚（移植 evocode complexity_scan，口径一致）。"""
    score = 0
    depth = 0
    for i in range(start, min(end + 1, len(lines))):
        line = lines[i]
        score += sum(1 + depth for _ in _BRANCH_RE.findall(line))
        stripped = line.lstrip()
        if stripped.startswith(("if ", "for ", "while ", "catch", "switch", "else ")):
            depth += 1
        elif stripped.startswith(("}", "elif", "else:")):
            depth = max(0, depth - 1)
    return score


def _py_block_end(lines: list[str], start: int) -> int:
    base_indent = len(lines[start]) - len(lines[start].lstrip())
    for i in range(start + 1, len(lines)):
        if not lines[i].strip():
            continue
        indent = len(lines[i]) - len(lines[i].lstrip())
        if indent <= base_indent:
            return i - 1
    return len(lines) - 1


def _braced_block_end(lines: list[str], start: int) -> int:
    depth = 0
    in_block = False
    for i in range(start, len(lines)):
        line = lines[i]
        depth += line.count("{") - line.count("}")
        if not in_block and "{" in line:
            in_block = True
        if in_block and depth <= 0 and i > start:
            return i
    return len(lines) - 1


def scan_complexity(text: str, lang: str) -> tuple[str, int, int] | None:
    """单文件认知复杂度扫描。

    返回 (最差函数名, 最高分, 超阈函数数)；无超阈函数返回 None。
    阈值 12 / MAJOR 分界 20，与 evocode 原版一致。
    """
    if lang not in _COMPLEX_LANGS:
        return None
    lines = text.splitlines()
    is_py = lang == "python"
    is_go = lang == "go"
    worst_name, worst_score, over_count = "", 0, 0
    i = 0
    while i < len(lines):
        line = lines[i]
        hit = (
            (is_py and _PY_DEF_RE.match(line))
            or (is_go and _GO_FUNC_RE.match(line))
            or (not is_py and not is_go and _BRACED_FUNC_RE.match(line))
        )
        if hit:
            end = _py_block_end(lines, i) if is_py else _braced_block_end(lines, i)
            score = _complexity_of_block(lines, i, end)
            if score >= _COMPLEX_THRESHOLD:
                over_count += 1
                if score > worst_score:
                    worst_score = score
                    worst_name = line.strip().split("(")[0].split()[-1]
            i = end + 1 if end > i else i + 1
        else:
            i += 1
    if not over_count:
        return None
    return worst_name, worst_score, over_count


def build_test_evidence(
    code_files: dict[str, str],
    declared_deps: dict[str, tuple[str | None, str]],
) -> TestEvidence:
    test_count = sum(1 for rel in code_files if is_test_file(rel))
    frameworks: set[str] = set()
    for dep_lower, (_ver, _src) in declared_deps.items():
        fw = _TEST_FW_BY_DEP.get(dep_lower)
        if fw:
            frameworks.add(fw)
    go_tests = any(is_test_file(r) and r.endswith("_test.go") for r in code_files)
    if go_tests:
        frameworks.add("go-test")
    total = max(len(code_files), 1)
    ratio = round(test_count / total, 2) if test_count else None
    return TestEvidence(
        test_file_count=test_count,
        ratio_to_source=ratio,
        frameworks=sorted(frameworks),
    )


def _max_indent(text: str) -> int:
    deepest = 0
    for line in text.splitlines():
        stripped = line.lstrip(" \t")
        if not stripped:
            continue
        indent = len(line) - len(stripped)
        tabs = line[:indent].count("\t")
        width = line[:indent].count(" ") + tabs * 4
        deepest = max(deepest, width)
        if deepest >= max(_DEEP_SPACES, _DEEP_TABS * 4):
            break
    return deepest
