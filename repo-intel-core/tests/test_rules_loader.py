"""TASK-M0-03 验收：规则表 loader。"""

from __future__ import annotations

import pytest

from repo_intel.rules.loader import excludes_rules, languages_rules, load


def test_languages_table_has_core_mappings():
    rules = languages_rules()
    assert rules["extensions"][".py"] == "python"
    assert rules["extensions"][".go"] == "go"
    assert rules["extensions"][".ts"] == "typescript"
    assert ".json" in rules["data_extensions"]
    assert rules["manifests"]["go.mod"] == "go"
    assert "pnpm-workspace.yaml" in rules["monorepo_markers"]


def test_excludes_table_defaults():
    rules = excludes_rules()
    assert "node_modules" in rules["dirs"]
    assert "*.min.js" in rules["file_globs"]
    assert rules["max_file_bytes"] > 0
    assert rules["soft_file_limit"] > 0


def test_missing_rule_raises(tmp_path):
    with pytest.raises(RuntimeError):
        load("definitely-not-exist")
