"""导入语句提取（TASK-M1-03/04/05）：纯提取不做解析，路径解析归 modules.py。"""

from __future__ import annotations

import re

# ---- Python ----
_PY_FROM = re.compile(r"^[ \t]*from\s+(\.*[\w.]*)\s+import\b", re.MULTILINE)
_PY_IMPORT = re.compile(r"^[ \t]*import\s+([\w.]+(?:\s*,\s*[\w.]+)*)", re.MULTILINE)


def extract_py(text: str) -> list[tuple[str, int]]:
    """返回 (模块点分名, 相对层级)。`from .x import y` → ("x", 1)；绝对导入层级 0。"""
    out: list[tuple[str, int]] = []
    for m in _PY_FROM.finditer(text):
        raw = m.group(1)
        dots = len(raw) - len(raw.lstrip("."))
        out.append((raw[dots:], dots))
    for m in _PY_IMPORT.finditer(text):
        for name in m.group(1).split(","):
            name = name.strip()
            if name:
                out.append((name, 0))
    return out


# ---- JS / TS / Vue ----
_JS_FROM = re.compile(r"""\b(?:import|export)[^;'"]*?\bfrom\s*['"]([^'"]+)['"]""")
_JS_REQUIRE = re.compile(r"""\brequire\s*\(\s*['"]([^'"]+)['"]\s*\)""")
_JS_DYNAMIC = re.compile(r"""\bimport\s*\(\s*['"]([^'"]+)['"]\s*\)""")
_JS_COMBINED = re.compile("|".join(p.pattern for p in (_JS_FROM, _JS_REQUIRE, _JS_DYNAMIC)))


def extract_js(text: str) -> list[str]:
    """返回 import/export-from、require()、动态 import() 的原始说明符。"""
    return [m.group(m.lastindex) for m in _JS_COMBINED.finditer(text)]


# ---- Go ----
_GO_BLOCK = re.compile(r"^import\s*\((.*?)^\)", re.MULTILINE | re.DOTALL)
_GO_SINGLE = re.compile(r'^import\s+(?:\w+\s+)?"([^"]+)"', re.MULTILINE)
_GO_BLOCK_LINE = re.compile(r'"([^"]+)"')


def extract_go(text: str) -> list[str]:
    """块式与单行 import 的导入路径（不含别名）。"""
    out: list[str] = []
    for m in _GO_BLOCK.finditer(text):
        for line in m.group(1).splitlines():
            lm = _GO_BLOCK_LINE.search(line)
            if lm:
                out.append(lm.group(1))
    for m in _GO_SINGLE.finditer(text):
        out.append(m.group(1))
    return out
