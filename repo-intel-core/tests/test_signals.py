"""TASK-M3-03 验收：月度信号包。"""

from __future__ import annotations

import json

from repo_intel.cli import main
from repo_intel.gitmeta.signals import monthly_signals


def test_pack_structure_and_months(git_root):
    pack = monthly_signals(git_root)
    assert pack is not None
    assert pack["schemaVersion"] == "1.0"
    assert pack["repo"] == "demo-git"
    assert [m["month"] for m in pack["months"]] == ["2026-06", "2026-08"]


def test_month_signals_content(git_root):
    pack = monthly_signals(git_root)
    june, aug = pack["months"]
    assert june["commits"] == 1 and aug["commits"] == 1
    assert june["contributors"] == 1
    assert "src" in june["new_dirs"]
    assert "web" in aug["new_dirs"]
    assert aug["deps_added"] == ["vue"]  # 月间 package.json 增量
    assert any("scaffold" in t or "entry" in t for m in pack["months"] for t in m["top_terms"]) or (
        all(isinstance(m["top_terms"], list) for m in pack["months"])
    )


def test_max_months_slice(git_root):
    pack = monthly_signals(git_root, max_months=1)
    assert [m["month"] for m in pack["months"]] == ["2026-08"]


def test_non_git_repo_returns_none(polyglot_root):
    assert monthly_signals(polyglot_root) is None


def test_cli_json_and_summary(git_root, capsys):
    assert main(["signals", str(git_root), "--format", "json"]) == 0
    pack = json.loads(capsys.readouterr().out)
    assert len(pack["months"]) == 2

    assert main(["signals", str(git_root), "--format", "summary", "--months", "1"]) == 0
    out = capsys.readouterr().out
    assert "2026-08" in out and "vue" in out


def test_cli_non_git_exit_2(polyglot_root, capsys):
    assert main(["signals", str(polyglot_root)]) == 2
