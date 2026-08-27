"""TASK-V01-03 / V01-04 验收：双模式调度与字段契约。"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest
from conftest import build_mini

_MODULE = Path(__file__).resolve().parent.parent / "skill" / "scripts" / "scan.py"
_spec = importlib.util.spec_from_file_location("onboarding_scan", _MODULE)
scan_mod = importlib.util.module_from_spec(_spec)
sys.modules.setdefault("onboarding_scan_contract", scan_mod)
_spec.loader.exec_module(scan_mod)  # type: ignore[union-attr]

KNOWN_SCHEMA_KEYS = {
    "schemaVersion", "generatedAt", "tool", "repo", "languages", "structure",
    "metrics", "warnings", "entryPoints", "modules", "dependencyGraph",
    "frameworks", "buildRun", "git",
}
LANG_KEYS = {"name", "pct", "files", "loc"}
BR_KEYS = {"buildSystem", "installCmd", "devCmd", "testCmd", "confidence", "evidence"}


def test_choose_backend_auto_full_when_core_installed(monkeypatch):
    monkeypatch.setattr(
        importlib.util, "find_spec",
        lambda name: object() if name == "repo_intel" else None,
    )
    assert scan_mod.choose_backend("auto") == "full"


def test_choose_backend_force_lite(monkeypatch):
    monkeypatch.setattr(importlib.util, "find_spec", lambda name: None)
    assert scan_mod.choose_backend("auto") == "lite"
    assert scan_mod.choose_backend("lite") == "lite"


def test_lite_keys_subset_of_schema(tmp_path_factory):
    mini_root = build_mini(tmp_path_factory.mktemp("keys"))
    payload = scan_mod.lite_scan(str(mini_root))
    assert set(payload) <= KNOWN_SCHEMA_KEYS
    for lang in payload["languages"]:
        assert set(lang) <= LANG_KEYS
    assert set(payload["buildRun"]) <= BR_KEYS
    assert all(set(ep) <= {"file", "type", "confidence", "evidence"}
               for ep in payload["entryPoints"])


@pytest.mark.skipif(
    importlib.util.find_spec("repo_intel") is None,
    reason="repo-intel-core 未安装，跳过双模式一致性检查",
)
def test_public_fields_match_between_modes(tmp_path_factory):
    root = build_mini(tmp_path_factory.mktemp("contract"))
    lite = scan_mod.lite_scan(str(root))
    from repo_intel.scanner import scan_repo

    full = json.loads(scan_repo(root).model_dump_json(by_alias=True))
    # 公共字段值一致（full 是超集）
    assert {l["name"]: l["loc"] for l in lite["languages"]} == \
           {l["name"]: l["loc"] for l in full["languages"]}
    assert lite["metrics"]["totalLoc"] == full["metrics"]["totalLoc"]
    assert set(lite["structure"]["configFiles"]) == set(full["structure"]["configFiles"])
    assert sys.version_info >= (3, 11)  # 环境哨兵
