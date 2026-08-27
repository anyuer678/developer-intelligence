"""TASK-M2-05 验收：scan 摘要增强 + M2 字段在 profile 中就位。"""

from __future__ import annotations

from repo_intel.cli import main


def test_summary_prints_frameworks_and_build(m2_root, capsys):
    assert main(["scan", str(m2_root), "--pretty"]) == 0
    out = capsys.readouterr().out
    # 摘要仅展示置信度排序后的 top3；全量清单由 test_frameworks 覆盖
    assert "frameworks(" in out
    assert "Vite@^5" in out
    assert "build[0.90]" in out
    assert "npm install" in out


def test_polyglot_still_green_after_m2(profile_json):
    """M2 集成不得破坏既有口径（回归哨兵）。"""
    assert profile_json["metrics"]["totalLoc"] == 66
    assert (
        profile_json["metrics"]["todos"] is None
        or profile_json["metrics"]["todos"]["todoCount"] == 0
    )
    fw_names = {f["name"] for f in profile_json.get("frameworks") or []}
    assert "Vue" in fw_names  # package.json 声明 vue ^3.4.0
