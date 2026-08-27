"""M4-04 验收：numstat 演化统计。"""

from __future__ import annotations

import json
from pathlib import Path

from conftest import _git_run

from repo_intel.gitmeta.evolution import evolution_summary, read_evolution


def test_read_entries_basic(git_root: Path):
    commits = read_evolution(git_root)
    assert commits is not None
    assert len(commits) == 2
    # git log 天然新→旧；日期集合断言不受顺序影响
    assert {c["committedAt"][:10] for c in commits} == {"2026-06-15", "2026-08-20"}
    assert commits[-1]["files"]


def test_empty_repo_vs_non_git(tmp_path: Path):
    empty = tmp_path / "empty"
    empty.mkdir()
    _git_run(empty, "init", "-q", "-b", "main")
    assert read_evolution(empty) == []  # 空仓库
    plain = tmp_path / "plain"
    plain.mkdir()
    assert read_evolution(plain) is None  # 非 git → None


def test_summary_trend_topfiles_authors(git_root: Path):
    s = evolution_summary(git_root)
    assert s["totalCommits"] == 2
    weeks = [w["week"] for w in s["trend"]]
    assert weeks == ["2026-06-15", "2026-08-17"]
    top = {t["filePath"]: t for t in s["topFiles"]}
    assert "package.json" in top and top["package.json"]["commitCount"] >= 1
    authors = s["authors"]
    assert authors[0]["authorName"] == "tester"


def test_hotspot_rules_medium_and_high(tmp_path: Path):
    repo = tmp_path / "hs"
    repo.mkdir()
    _git_run(repo, "init", "-q", "-b", "main")
    _git_run(repo, "config", "user.email", "t@example.com")
    _git_run(repo, "config", "user.name", "tester")

    # MEDIUM：同一文件变更 ≥3 次
    hot = repo / "hot.py"
    hot.write_text("x = 1\n", encoding="utf-8")
    for i in range(3):
        hot.write_text(f"x = {i}\n", encoding="utf-8")
        _git_run(repo, "add", "-A")
        _git_run(repo, "commit", "-qm", f"touch {i}")

    # HIGH：单次新增 ≥2000 行
    big = repo / "big.py"
    big.write_text("\n".join(f"y{i} = {i}" for i in range(2100)) + "\n", encoding="utf-8")
    _git_run(repo, "add", "-A")
    _git_run(repo, "commit", "-qm", "feat: big module")

    s = evolution_summary(repo)
    levels = {h["module"]: h["riskLevel"] for h in s["hotspots"]}
    assert levels.get("hot.py") == "MEDIUM"
    assert levels.get("big.py") == "HIGH"
    high = next(h for h in s["hotspots"] if h["module"] == "big.py")
    assert any("2100" in ev or "新增 2100 行" in ev for ev in high["evidence"]) or (
        any(ev.startswith("新增") for ev in high["evidence"])
    )


def test_cli_json_and_summary(git_root: Path, capsys):
    assert cli_evo(git_root, "--format", "json") == 0
    data = json.loads(capsys.readouterr().out)
    assert {"totalCommits", "trend", "topFiles", "authors", "hotspots"} <= set(data)

    assert cli_evo(git_root, "--format", "summary") == 0
    out = capsys.readouterr().out
    assert "演化统计" in out and "totalCommits=2" in out


def test_cli_bad_path(tmp_path: Path):
    from repo_intel.cli import main as cli_main

    assert cli_main(["evolution", str(tmp_path / "__nope__")]) == 2


def cli_evo(root: Path, *extra: str) -> int:
    from repo_intel.cli import main as cli_main

    return cli_main(["evolution", str(root), *extra])
