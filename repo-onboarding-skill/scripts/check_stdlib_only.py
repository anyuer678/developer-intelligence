#!/usr/bin/env python3
"""守卫：skill/scripts/scan.py 只允许标准库导入（硬约束#1 的机器执行版）。"""

from __future__ import annotations

import ast
import sys
from pathlib import Path

TARGET = Path(__file__).resolve().parent.parent / "skill" / "scripts" / "scan.py"

STDLIB = set(sys.stdlib_module_names)


def _module_level_imports(tree: ast.Module):
    """仅收集模块级 import（函数内的条件导入合法——如探测 core 的 full 分支）。"""
    for node in tree.body:
        if isinstance(node, ast.Import) or isinstance(node, ast.ImportFrom):
            yield node


def main() -> int:
    tree = ast.parse(TARGET.read_text(encoding="utf-8"))
    bad: list[str] = []
    for node in _module_level_imports(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                root = alias.name.split(".")[0]
                if root not in STDLIB:
                    bad.append(alias.name)
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            root = node.module.split(".")[0]
            if root not in STDLIB:
                bad.append(node.module)
    if bad:
        print("模块级违规第三方导入:", ", ".join(sorted(set(bad))))
        return 1
    print("stdlib-only OK（函数内条件导入除外）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
