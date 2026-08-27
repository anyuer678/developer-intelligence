"""TASK-V01-02 验收：lite 扫描器行为。"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

MODULE_PATH = Path(__file__).resolve().parent.parent / "skill" / "scripts" / "scan.py"
_spec = importlib.util.spec_from_file_location("onboarding_scan", MODULE_PATH)
scan_mod = importlib.util.module_from_spec(_spec)
sys.modules.setdefault("onboarding_scan", scan_mod)
_spec.loader.exec_module(scan_mod)  # type: ignore[union-attr]


@pytest.fixture(scope="module")
def mini_root(tmp_path_factory: pytest.TempPathFactory) -> Path:
    from conftest import build_mini

    return build_mini(tmp_path_factory.mktemp("lite"))


def test_scan_mode_lite_marker(mini_root):
    payload = scan_mod.lite_scan(str(mini_root))
    modes = [w for w in payload["warnings"] if w["code"] == "SCAN_MODE"]
    assert modes and modes[0]["detail"] == "lite"


def test_languages_and_exclusions(mini_root):
    payload = scan_mod.lite_scan(str(mini_root))
    names = {l["name"] for l in payload["languages"]}
    assert names == {"python", "shell", "typescript"}
    assert payload["metrics"]["totalFiles"] == 6  # 含 .repointelignore 自身（与 core 口径一致）
    raw = str(payload)
    assert "node_modules" not in raw.replace('"topLevelDirs"', "")
    assert "secret.txt" not in raw


def test_build_run_from_scripts(mini_root):
    br = scan_mod.lite_scan(str(mini_root))["buildRun"]
    assert "npm run dev" in br["devCmd"]
    assert br["confidence"] == 0.6


def test_shebang_shell_counted(mini_root):
    langs = {l["name"]: l for l in scan_mod.lite_scan(str(mini_root))["languages"]}
    assert langs["shell"]["loc"] == 2


def test_bad_path_exit():
    with pytest.raises(NotADirectoryError):
        scan_mod.lite_scan(str(Path("Z:/__nope__")))


def test_debug_flag_emits_json_to_stderr(mini_root, capsys):
    code = scan_mod.main(["scan", str(mini_root), "--debug"])
    assert code == 0
    captured = capsys.readouterr()
    assert '"schemaVersion"' in captured.err
    assert '"languages"' in captured.err
