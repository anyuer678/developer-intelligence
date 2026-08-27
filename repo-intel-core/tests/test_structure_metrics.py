"""TASK-M0-06 验收：结构扫描 + 规模统计。"""

from __future__ import annotations


def test_language_stats_and_ordering(profile, profile_json):
    stats = {s.name: s for s in profile.languages}
    assert set(stats) == {"go", "typescript", "python", "shell", "vue"}
    assert [s.name for s in profile.languages] == [
        "go",
        "typescript",
        "python",
        "shell",
        "vue",
    ]
    assert stats["go"].files == 2
    assert stats["go"].loc == 33
    assert stats["python"].loc == 10
    assert stats["vue"].loc == 1

    total = sum(s.pct for s in profile.languages)
    assert abs(total - 100.0) < 0.5


def test_metrics_totals_and_largest_files(profile_json):
    m = profile_json["metrics"]
    assert m["totalLoc"] == 66
    assert m["totalFiles"] == 11

    largest = m["largestFiles"]
    assert len(largest) == 5
    locs = [f["loc"] for f in largest]
    assert locs == sorted(locs, reverse=True)
    assert largest[0]["path"].endswith("util.go")


def test_top_level_dirs_with_roles(profile_json):
    dirs = {d["path"]: d for d in profile_json["structure"]["topLevelDirs"]}
    assert dirs["cmd"]["role"] == "guessed-entry"
    assert dirs["cmd"]["fileCount"] == 1
    assert dirs["src"]["role"] is None  # 无 package.json 不判前端
    assert dirs["(root)"]["fileCount"] == 6  # 含 .repointelignore 自身


def test_config_files_collected_from_manifests_and_markers(profile_json):
    assert profile_json["structure"]["configFiles"] == ["README.md", "go.mod", "package.json"]


def test_mixed_monorepo_warning(profile_json):
    codes = [w["code"] for w in profile_json["warnings"]]
    assert "MIXED_MONOREPO" in codes
    detail = next(w["detail"] for w in profile_json["warnings"] if w["code"] == "MIXED_MONOREPO")
    assert "go" in detail and "node-ecosystem" in detail


def test_no_vcs_in_fixture(profile_json):
    vcs = profile_json["repo"]["vcs"]
    assert vcs is None or vcs.get("type") is None
