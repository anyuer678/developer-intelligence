"""TASK-M3-02 验收：GitMeta。"""

from __future__ import annotations

from pathlib import Path

from repo_intel.gitmeta.reader import read_git_meta
from repo_intel.scanner import scan_repo


def test_git_meta_fields(git_root):
    meta = read_git_meta(git_root)
    assert meta is not None
    assert meta.commit_count == 2
    assert meta.contributor_count == 1
    assert meta.first_commit_at == "2026-06-15"
    assert meta.last_commit_at == "2026-08-20"
    assert meta.activity_by_month == {"2026-06": 1, "2026-08": 1}
    assert meta.branch_count == 1  # main
    assert meta.tag_count == 0


def test_no_git_returns_null(polyglot_root):
    assert read_git_meta(polyglot_root) is None
    profile = scan_repo(polyglot_root)
    assert profile.git is None  # 三态：模块不可用
    codes = [w.code for w in profile.warnings]
    assert "GIT_META_UNAVAILABLE" not in codes  # 没有 .git 是正常态不是告警


def test_worktree_pointer_supported(git_root: Path, tmp_path: Path):
    """git worktree 场景：.git 是指针文件而非目录——HEAD/分支/历史仍可读。"""
    import subprocess

    wt = tmp_path / "wt-link"
    subprocess.run(
        ["git", "-C", str(git_root), "worktree", "add", str(wt), "-b", "wt-branch"],
        check=True,
        capture_output=True,
    )
    assert (wt / ".git").is_file()  # 指针文件特征

    meta = read_git_meta(wt)
    assert meta is not None and meta.commit_count == 2

    profile = scan_repo(wt)
    vcs = profile.repo.vcs
    assert vcs is not None and vcs.type == "git"
    assert vcs.head_branch == "wt-branch"  # worktree 自带分支名


def test_scan_profile_carries_git(git_root):
    profile = scan_repo(git_root)
    assert profile.git is not None and profile.git.commit_count == 2


def test_skip_git_flag(git_root):
    profile = scan_repo(git_root, skip_git=True)
    assert profile.git is None
