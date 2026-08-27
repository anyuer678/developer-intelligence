"""GitMeta 读取（TASK-M3-02）：subprocess 本地只读 git（ADR-011）。"""

from __future__ import annotations

import os
import subprocess
from collections import Counter
from pathlib import Path

from repo_intel.schema.profiles import GitMeta, VcsInfo

_TIMEOUT = 30

# Windows 无控制台部署（服务/计划任务/pythonw）时抑制子进程黑窗口
# （下沉自 evocode analyzer gitlog.py，2026-08-26 对齐审计）
_CREATE_NO_WINDOW = {"creationflags": subprocess.CREATE_NO_WINDOW} if os.name == "nt" else {}


def _git(root: Path, *args: str) -> str | None:
    try:
        proc = subprocess.run(
            ["git", "-C", str(root), *args],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=_TIMEOUT,
            **_CREATE_NO_WINDOW,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if proc.returncode != 0:
        return None
    return proc.stdout


def _count_refs(root: Path, *args: str) -> int | None:
    out = _git(root, *args)
    if out is None:
        return None
    return sum(1 for line in out.splitlines() if line.strip())


def read_vcs_info(root: Path) -> VcsInfo:
    """读取 VCS 信息；兼容 worktree（.git 为指向真实 gitdir 的指针文件）。"""

    dot = root / ".git"
    if not dot.exists():
        return VcsInfo(type=None)

    head_branch: str | None = None
    head_path = dot / "HEAD"  # 普通仓库：root/.git/HEAD
    if dot.is_file():  # worktree：内容形如 "gitdir: <主仓>/.git/worktrees/<名>"
        try:
            first_line = dot.read_text(encoding="utf-8", errors="replace").splitlines()[0].strip()
            if first_line.lower().startswith("gitdir:"):
                head_path = Path(first_line.split(":", 1)[1].strip()) / "HEAD"
        except OSError:
            head_path = dot / "HEAD"
    try:
        head = head_path.read_text(encoding="utf-8", errors="replace").strip()
        if head.startswith("ref: refs/heads/"):
            head_branch = head[len("ref: refs/heads/") :]
    except OSError:
        pass
    return VcsInfo(type="git", head_branch=head_branch)


def read_commit_rows(root: Path) -> list[tuple[str, str, str]] | None:
    """按时间升序返回 (date, email, subject)；不可用返回 None。"""
    log = _git(root, "log", "--date=short", "--pretty=%ad%x1f%ae%x1f%s")
    if log is None:
        return None
    rows: list[tuple[str, str, str]] = []
    for line in log.splitlines():
        parts = line.split("\x1f")
        if len(parts) == 3:
            rows.append((parts[0], parts[1], parts[2]))
    rows.sort(key=lambda r: r[0])
    return rows


def read_git_meta(root: Path) -> GitMeta | None:
    """返回 None 表示不可用（无 .git / git 命令失败）——三态中的 null。"""
    rows = read_commit_rows(root)
    if rows is None:
        return None
    if not rows:
        return GitMeta(commit_count=0)

    dates = [r[0] for r in rows]
    authors = {r[1] for r in rows}
    months = Counter(d[:7] for d in dates)

    return GitMeta(
        first_commit_at=min(dates),
        last_commit_at=max(dates),
        commit_count=len(rows),
        contributor_count=len(authors),
        activity_by_month=dict(sorted(months.items())),
        branch_count=_count_refs(root, "branch", "--list"),
        tag_count=_count_refs(root, "tag", "--list"),
    )
