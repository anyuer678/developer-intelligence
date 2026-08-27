"""TASK-M1-05 验收：Go 导入提取。"""

from __future__ import annotations

from repo_intel.detect.imports import extract_go


def test_block_import_with_alias_and_comment():
    text = 'package main\n\nimport (\n\t"demo/internal/auth"\n\tf "fmt"\n\t_ "embed" // 注释\n)\n'
    assert sorted(extract_go(text)) == ["demo/internal/auth", "embed", "fmt"]


def test_single_line_import():
    assert extract_go('package a\n\nimport "x/y"\n') == ["x/y"]
    assert extract_go('package a\n\nimport z "x/z"\n') == ["x/z"]


def test_no_imports():
    assert extract_go("package main\n") == []
