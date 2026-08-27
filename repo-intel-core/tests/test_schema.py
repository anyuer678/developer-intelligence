"""TASK-M0-02 验收：Schema v1.0-draft。"""

from __future__ import annotations

import json

from repo_intel.schema.profiles import SCHEMA_VERSION, RepoInfo, RepoProfile, ToolInfo


def _minimal() -> RepoProfile:
    return RepoProfile(
        tool=ToolInfo(version="test"),
        repo=RepoInfo(path="/tmp/x", name="x"),
    )


def test_schema_version_is_v1_draft():
    assert SCHEMA_VERSION == "1.0"
    assert _minimal().schema_version == "1.0"


def test_camel_case_aliases_in_json_dump():
    dump = json.loads(_minimal().model_dump_json(by_alias=True))
    assert dump["schemaVersion"] == "1.0"
    assert dump["repo"]["path"] == "/tmp/x"
    assert "topLevelDirs" in dump["structure"]
    assert "configFiles" in dump["structure"]
    assert "totalLoc" in dump["metrics"]
    assert "largestFiles" in dump["metrics"]


def test_reserved_fields_are_null_three_state():
    """M1+ 模块未启用 → JSON 中恒为 null（字段三态）。"""
    dump = json.loads(_minimal().model_dump_json(by_alias=True))
    for key in ("entryPoints", "modules", "dependencyGraph", "frameworks", "buildRun", "git"):
        assert key in dump, f"缺少预留字段 {key}"
        assert dump[key] is None


def test_construct_via_snake_case_and_alias_roundtrip():
    p = _minimal()
    again = RepoProfile.model_validate(json.loads(p.model_dump_json(by_alias=True)))
    assert again.repo.name == "x"
