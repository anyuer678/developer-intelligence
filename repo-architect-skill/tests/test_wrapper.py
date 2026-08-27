"""TASK-A02 验收：扫描包装器。"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

MODULE = Path(__file__).resolve().parent.parent / "skill" / "scripts" / "scan.py"
_spec = __import__("importlib").util.spec_from_file_location("arch_scan", MODULE)
scan_mod = __import__("importlib").util.module_from_spec(_spec)
sys.modules["arch_scan"] = scan_mod
_spec.loader.exec_module(scan_mod)  # type: ignore[union-attr]

pytestmark = pytest.mark.skipif(
    __import__("importlib").util.find_spec("repo_intel") is None,
    reason="repo-intel-core 未安装",
)


def test_wrapper_full_payload_with_modules(tmp_path_factory, capsys):
    from conftest import build_arch_repo

    root = build_arch_repo(tmp_path_factory.mktemp("arch"))
    assert scan_mod.main(["scan", str(root), "--pretty"]) == 0
    out = capsys.readouterr().out
    assert '"modules"' in out


def test_mermaid_field_present_and_edges(tmp_path_factory, capsys):
    from conftest import build_arch_repo

    root = build_arch_repo(tmp_path_factory.mktemp("arch2"))
    tmp_out = root.parent / "p.json"
    assert scan_mod.main(["scan", str(root), "-o", str(tmp_out)]) == 0
    data = json.loads(Path(tmp_out).read_text(encoding="utf-8"))
    mermaid = data["architectureMermaid"]
    assert mermaid.startswith("flowchart LR")
    assert "-->" in mermaid
    mods = {m["name"] for m in data["modules"]}
    assert {"(root)", "pkgcore"} <= mods


def test_missing_core_exit_code_3(monkeypatch, tmp_path):
    monkeypatch.setattr(scan_mod, "scan_repo", None)
    assert scan_mod.main(["scan", str(tmp_path)]) == 3


def test_bad_path_exit_2():
    assert scan_mod.main(["scan", "Z:/__nope__"]) == 2
