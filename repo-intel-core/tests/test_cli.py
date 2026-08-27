"""TASK-M0-07 验收：CLI。"""

from __future__ import annotations

import json

import pytest

from repo_intel.cli import main


def test_scan_writes_json_and_exits_zero(polyglot_root, tmp_path, capsys):
    out = tmp_path / "profile.json"
    rc = main(["scan", str(polyglot_root), "-o", str(out), "--pretty"])
    assert rc == 0

    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["schemaVersion"] == "1.0"
    assert data["repo"]["name"] == "demo-polyglot"
    assert data["metrics"]["totalLoc"] == 66
    # 摘要打印到终端
    stdout = capsys.readouterr().out
    assert "demo-polyglot" in stdout
    assert "go" in stdout


def test_scan_summary_without_output_file(profile_json, polyglot_root, capsys):
    rc = main(["scan", str(polyglot_root)])
    assert rc == 0
    assert "warnings" in capsys.readouterr().out  # fixture 必有 MIXED_MONOREPO


def test_scan_bad_path_exit_code_2(tmp_path, capsys):
    missing = tmp_path / "__no_such_dir__"
    assert main(["scan", str(missing)]) == 2
    assert "错误" in capsys.readouterr().err


def test_version_flag(capsys):
    with pytest.raises(SystemExit) as exc:
        main(["--version"])
    assert exc.value.code == 0
