"""numstat 全量演化统计（M4-04，移植自 evocode evolution/gitlog.py）。

口径继承：
- 单次 `git log --numstat` 取全量，\\x1f 分隔避免消息歧义；
- 空仓库（HEAD 不存在）→ []，git 故障 → None（区分）；
- 周桶按 UTC 归一后取周一；热点规则 HIGH/MEDIUM 阈值原版一致。
"""

from __future__ import annotations

import os
import re
import subprocess
from datetime import UTC, datetime, timedelta
from pathlib import Path

_TIMEOUT = 60
_PRETTY = "COMMIT\x1f%h\x1f%an%x1f%ae%x1f%ad%x1f%s"
_COMMIT_LINE = re.compile(r"^COMMIT\x1f([0-9a-f]+)\x1f(.*?)\x1f(.*?)\x1f(.*?)\x1f(.*)$")
_NUMSTAT_LINE = re.compile(r"^(\d+|-)\t(\d+|-)\t(.+)$")
_CREATE_NO_WINDOW = {"creationflags": subprocess.CREATE_NO_WINDOW} if os.name == "nt" else {}


def _run(root: Path, args: list[str]) -> str | None:
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
    except (OSError, subprocess.SubprocessError):
        return None
    if proc.returncode != 0:
        return None
    return proc.stdout


def read_evolution(
    root: str | Path,
    range_days: int | None = None,
    top_n: int = 10,
) -> list[dict] | None:
    """返回 commit 明细列表；非 git 仓/故障 → None；空仓库 → []。"""
    root_path = Path(root)
    if not root_path.is_dir():
        return None

    args = [
        "-c",
        "core.quotepath=false",
        "log",
        "--numstat",
        f"--pretty=format:{_PRETTY}",
        "--date=iso-strict",
        "--no-renames",
    ]
    if range_days and range_days > 0:
        args.append(f"--since={range_days} days ago")
    out = _run(root_path, args)
    if out is None:
        # 与 evocode 同款区分：HEAD 不存在=空仓库[]；否则=故障 None
        if (
            _run(root_path, ["rev-parse", "--verify", "HEAD"]) is None
            and not (root_path / ".git").exists()
        ):
            return None
        return []

    commits: list[dict] = []
    cur: dict | None = None
    for line in out.splitlines():
        m = _COMMIT_LINE.match(line)
        if m:
            if cur is not None:
                commits.append(cur)
            cur = {
                "hash": m.group(1),
                "authorName": m.group(2),
                "authorEmail": m.group(3),
                "committedAt": m.group(4),
                "message": m.group(5),
                "linesAdded": 0,
                "linesRemoved": 0,
                "filesChanged": 0,
                "_files": {},
            }
            continue
        if cur is None:
            continue
        n = _NUMSTAT_LINE.match(line)
        if n:
            added = 0 if n.group(1) == "-" else int(n.group(1))
            removed = 0 if n.group(2) == "-" else int(n.group(2))
            path = n.group(3)
            cur["linesAdded"] += added
            cur["linesRemoved"] += removed
            cur["filesChanged"] += 1
            f = cur["_files"].setdefault(path, {"added": 0, "removed": 0})
            f["added"] += added
            f["removed"] += removed
    if cur is not None:
        commits.append(cur)
    for c in commits:
        c["files"] = c.pop("_files")
    return commits


# ---------------------------------------------------------------- 聚合（口径原版）


def week_start(committed_at: str) -> str:
    try:
        dt = datetime.fromisoformat(committed_at.replace("Z", "+00:00"))
        dt = dt.astimezone(UTC)
    except ValueError:
        return ""
    return (dt.date() - timedelta(days=dt.weekday())).isoformat()


def build_trend(commits: list[dict]) -> list[dict]:
    acc: dict[str, dict] = {}
    for c in commits:
        week = week_start(c["committedAt"])
        a = acc.setdefault(
            week,
            {"week": week, "commits": 0, "linesAdded": 0, "linesRemoved": 0},
        )
        a["commits"] += 1
        a["linesAdded"] += c["linesAdded"]
        a["linesRemoved"] += c["linesRemoved"]
    return [acc[k] for k in sorted(acc)]


def build_top_files(commits: list[dict], top_n: int = 10) -> list[dict]:
    acc: dict[str, dict] = {}
    for c in commits:
        for path, f in c["files"].items():
            a = acc.setdefault(
                path,
                {"filePath": path, "commitCount": 0, "linesAdded": 0, "linesRemoved": 0},
            )
            a["commitCount"] += 1
            a["linesAdded"] += f["added"]
            a["linesRemoved"] += f["removed"]
    ranked = sorted(acc.values(), key=lambda x: (-x["commitCount"], -x["linesAdded"]))
    return ranked[:top_n]


def build_authors(commits: list[dict]) -> list[dict]:
    acc: dict[str, dict] = {}
    for c in commits:
        name = c.get("authorName") or "unknown"
        a = acc.setdefault(name, {"authorName": name, "commits": 0, "linesAdded": 0})
        a["commits"] += 1
        a["linesAdded"] += c["linesAdded"]
    return sorted(acc.values(), key=lambda x: -x["commits"])


def detect_hotspots(top_files: list[dict], total_commits: int) -> list[dict]:
    """HIGH: 占比≥15% 且新增≥300，或新增≥2000；MEDIUM: 变更≥3 次。"""
    if total_commits == 0:
        return []
    out: list[dict] = []
    for tf in top_files:
        share = tf["commitCount"] / total_commits
        evidence = [
            f"变更 {tf['commitCount']} 次",
            f"新增 {tf['linesAdded']} 行",
            f"删除 {tf['linesRemoved']} 行",
            f"占全部提交的 {share * 100:.0f}%",
        ]
        if (share >= 0.15 and tf["linesAdded"] >= 300) or tf["linesAdded"] >= 2000:
            level = "HIGH"
        elif tf["commitCount"] >= 3:
            level = "MEDIUM"
        else:
            continue
        out.append({"module": tf["filePath"], "riskLevel": level, "evidence": evidence})
    return out


def evolution_summary(root: str | Path, top_n: int = 10) -> dict | None:
    """聚合出口：None=非 git/故障；含 trend/topFiles/authors/hotspots。"""
    commits = read_evolution(root)
    if commits is None:
        return None
    total = len(commits)
    top_files = build_top_files(commits, top_n=top_n)
    return {
        "totalCommits": total,
        "trend": build_trend(commits),
        "topFiles": top_files,
        "authors": build_authors(commits),
        "hotspots": detect_hotspots(top_files, total),
    }
