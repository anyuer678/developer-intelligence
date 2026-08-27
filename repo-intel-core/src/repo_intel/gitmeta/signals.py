"""月度切片信号包（TASK-M3-03）：03 号 Evolution Timeline 的输入。"""

from __future__ import annotations

import json
import os
import re
import subprocess
from collections import Counter
from pathlib import Path

from repo_intel.gitmeta.reader import _TIMEOUT, _git

_CREATE_NO_WINDOW = {"creationflags": subprocess.CREATE_NO_WINDOW} if os.name == "nt" else {}

SCHEMA_VERSION = "1.0"
_EMPTY_TREE = "4b825dc642cb6eb9a060e54bf8d69288fbee4904"
_MANIFESTS = ("go.mod", "package.json", "pyproject.toml", "requirements.txt")
_MAX_COMMITS_SCANNED = 3000

_STOPWORDS = {
    "the",
    "a",
    "an",
    "and",
    "or",
    "to",
    "of",
    "in",
    "for",
    "on",
    "with",
    "fix",
    "add",
    "update",
    "chore",
    "docs",
    "init",
    "merge",
    "pull",
    "request",
    "branch",
    "test",
    "tests",
    "new",
    "use",
    "into",
    "from",
    "this",
    "that",
    "not",
}
_TERM_RE = re.compile(r"[a-z][a-z0-9_-]{2,}|[\u4e00-\u9fff]{2,}")


def _files_of(root: Path, rev: str) -> list[str]:
    out = _git(root, "show", "--name-only", "--pretty=format:", rev)
    if out is None:
        return []
    return [line for line in out.splitlines() if line.strip()]


_DEP_REQ_LINE = re.compile(r"^([A-Za-z0-9][A-Za-z0-9._-]*)")


def _blob(root: Path, rev: str, path: str) -> str:
    out = _git(root, "show", f"{rev}:{path}")
    return out or ""


def _dep_names(filename: str, text: str) -> set[str]:
    """从 manifest 文本提取声明依赖名集合（宽松口径，仅供月度差集）。"""
    names: set[str] = set()
    if filename == "package.json":
        try:
            pkg = json.loads(text)
            for section in ("dependencies", "devDependencies"):
                if isinstance(pkg.get(section), dict):
                    names |= {str(k) for k in pkg[section]}
        except ValueError:
            pass
    elif filename == "go.mod":
        for m in re.finditer(r"(?m)^\s*(?:-\s+)?([\w./~-]+)\s+v\d", text):
            names.add(m.group(1))
    else:  # pyproject.toml / requirements.txt 行式条目
        for line in text.splitlines():
            m = _DEP_REQ_LINE.match(line.split("#")[0].split(";")[0].strip())
            if m:
                names.add(m.group(1))
    return {n.lower() for n in names}


def _diff_added_deps(root: Path, old: str, new: str) -> list[str]:
    """旧→新 月末边界间新增的声明依赖（新集合 − 旧集合，按字母序）。"""
    try:
        proc = subprocess.run(
            ["git", "-C", str(root), "diff", "--name-only", old, new, "--", *_MANIFESTS],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=_TIMEOUT,
            **_CREATE_NO_WINDOW,
        )
    except (OSError, subprocess.TimeoutExpired):
        return []
    if proc.returncode != 0:
        return []

    added: set[str] = set()
    for fname in [line.strip() for line in proc.stdout.splitlines() if line.strip()]:
        old_names = _dep_names(fname, _blob(root, old, fname))
        new_names = _dep_names(fname, _blob(root, new, fname))
        added |= new_names - old_names
    return sorted(added)


def _top_terms(subjects: list[str], n: int = 5) -> list[str]:
    counter: Counter[str] = Counter()
    for subject in subjects:
        for term in _TERM_RE.findall(subject.lower()):
            if term not in _STOPWORDS:
                counter[term] += 1
    return [term for term, _ in counter.most_common(n)]


def monthly_signals(
    root: str | Path,
    max_months: int | None = None,
) -> dict | None:
    """输出月度切片信号包；非 git 仓库返回 None。"""
    root_path = Path(root).resolve()

    # 单次 git 调用同时取 date/email/subject/sha，避免两次调用的行对齐风险
    log = _git(root_path, "log", "--reverse", "--date=short", "--pretty=%ad%x1f%ae%x1f%s%x1f%H")
    if log is None:
        return None
    rows: list[tuple[str, str, str, str]] = []
    for line in log.splitlines():
        parts = line.split("\x1f")
        if len(parts) == 4:
            rows.append((parts[0], parts[1], parts[2], parts[3]))
    if not rows:
        return None

    truncated = len(rows) > _MAX_COMMITS_SCANNED
    limit = min(len(rows), _MAX_COMMITS_SCANNED)
    rows = rows[:limit]

    by_month: dict[str, dict] = {}
    seen_dirs: set[str] = set()
    prev_month_last_sha: str | None = None

    for idx, (d, email, subject, sha) in enumerate(rows):
        month = d[:7]
        slot = by_month.setdefault(
            month,
            {"month": month, "commits": 0, "contributors": set(), "new_dirs": [], "subjects": []},
        )
        slot["commits"] += 1
        slot["contributors"].add(email)
        slot["subjects"].append(subject)

        for fpath in _files_of(root_path, sha):
            top_dir = fpath.split("/", 1)[0] if "/" in fpath else None
            if top_dir and top_dir not in seen_dirs and not top_dir.startswith("."):
                seen_dirs.add(top_dir)
                slot["new_dirs"].append(top_dir)

        # 月末边界：下一条提交属于新月份，或已是最后一条 → 计算依赖增量
        next_month = rows[idx + 1][0][:7] if idx + 1 < len(rows) else None
        if next_month != month:
            old_rev = prev_month_last_sha if prev_month_last_sha else _EMPTY_TREE
            slot["deps_added"] = _diff_added_deps(root_path, old_rev, sha)
            prev_month_last_sha = sha

    months = list(by_month.values())
    if max_months is not None:
        months = months[-max_months:]

    for slot in months:
        slot["top_terms"] = _top_terms(slot.pop("subjects"))
        slot["contributors"] = len(slot["contributors"])

    return {
        "schemaVersion": SCHEMA_VERSION,
        "repo": root_path.name,
        "truncated": truncated,
        "months": months,
    }
