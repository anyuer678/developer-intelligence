"""GitHub 采集器（TASK-P0-Gate1）：REST 批量采集 + 增量同步。

采集范围：repos / commits / issues(含PR) / releases / my_stars。
Token 来源：环境变量 GITHUB_TOKEN（可选，未配置走匿名限流）。
幂等：UPSERT 语义写入，增量凭 sync_state 游标。
隐私红线：token 不写日志、不入库。
"""

from __future__ import annotations

import json
import os
import sqlite3
import time
from datetime import datetime, timezone
from typing import Any

import urllib.request
import urllib.error

from pgi import ids

API_BASE = "https://api.github.com"
RATE_SLEEP_S = 60  # 限流后等待（单位：秒）


class SyncError(RuntimeError):
    """采集失败（网络/限流/认证）。"""


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _token() -> str:
    return os.environ.get("GITHUB_TOKEN", "")


def _get(url: str, token: str) -> Any:
    """GET JSON；403 限流时抛 SyncError；网络错误带中文提示。"""
    req = urllib.request.Request(url, headers={"Accept": "application/vnd.github.v3+json"})
    if token:
        req.add_header("Authorization", f"Bearer {token}")

    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        if exc.code == 403:
            raise SyncError("GitHub API 限流（403）：请等待或配置 GITHUB_TOKEN 提高额度")
        if exc.code == 404:
            raise SyncError(f"资源不存在（404）：{url}")
        raise SyncError(f"GitHub API 错误（{exc.code}）")
    except urllib.error.URLError as exc:
        raise SyncError(f"网络错误: {exc.reason}")


def _paginate(url: str, token: str, per_page: int = 100, max_pages: int = 10) -> list[Any]:
    """按 link 头分页拉全；超 max_pages 截断（防失控）。"""
    items: list[Any] = []
    page = 1
    while page <= max_pages:
        sep = "&" if "?" in url else "?"
        batch = _get(f"{url}{sep}per_page={per_page}&page={page}", token)
        if not isinstance(batch, list) or len(batch) == 0:
            break
        items.extend(batch)
        page += 1
        if len(batch) < per_page:
            break
    return items


# ---------------------------------------------------------------- 各实体 upsert

def upsert_repo(conn: sqlite3.Connection, r: dict[str, Any]) -> None:
    rid = ids.build("github", "repo", r["full_name"])
    now = _now_iso()
    conn.execute(
        """INSERT INTO repos (id, full_name, description, primary_language, stars, forks,
                             is_fork, is_archived, visibility, created_at, pushed_at,
                             topics_json, my_role, first_synced_at, last_synced_at)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
           ON CONFLICT(id) DO UPDATE SET
             description=excluded.description, primary_language=excluded.primary_language,
             stars=excluded.stars, forks=excluded.forks, is_archived=excluded.is_archived,
             pushed_at=excluded.pushed_at, last_synced_at=excluded.last_synced_at""",
        (
            rid, r["full_name"], r.get("description"), r.get("language"),
            r.get("stargazers_count", 0), r.get("forks_count", 0),
            1 if r.get("fork") else 0, 1 if r.get("archived") else 0,
            r.get("visibility", "public"), r.get("created_at"), r.get("pushed_at"),
            json.dumps(r.get("topics", []), ensure_ascii=False),
            "owner", now, now,
        ),
    )


def upsert_commit(conn: sqlite3.Connection, repo_full: str, c: dict[str, Any]) -> None:
    sha = c.get("sha", "")
    if not sha:
        return
    rid = ids.build("github", "commit", f"{repo_full}@{sha}")
    repo_id = ids.build("github", "repo", repo_full)
    conn.execute(
        """INSERT INTO commits (id, repo_id, sha, authored_at, author_email, message,
                               additions, deletions, files_changed, is_my_commit)
           VALUES (?,?,?,?,?,?,?,?,?,1)
           ON CONFLICT(repo_id, sha) DO UPDATE SET authored_at=excluded.authored_at""",
        (
            rid, repo_id, sha,
            c.get("commit", {}).get("author", {}).get("date"),
            c.get("commit", {}).get("author", {}).get("email"),
            c.get("commit", {}).get("message", ""),
            c.get("stats", {}).get("additions"), c.get("stats", {}).get("deletions"),
            c.get("stats", {}).get("total"),
        ),
    )


def upsert_issue(conn: sqlite3.Connection, repo_full: str, i: dict[str, Any]) -> None:
    repo_id = ids.build("github", "repo", repo_full)
    rid = ids.build("github", "issue", f"{repo_full}#{i['number']}")
    labels = [l.get("name", "") for l in i.get("labels", [])]
    conn.execute(
        """INSERT INTO issues (id, repo_id, number, title, state, is_pr, labels_json, opened_at, closed_at)
           VALUES (?,?,?,?,?,?,?,?,?)
           ON CONFLICT(repo_id, number) DO UPDATE SET
             title=excluded.title, state=excluded.state, labels_json=excluded.labels_json,
             closed_at=excluded.closed_at""",
        (
            rid, repo_id, i["number"], i.get("title", ""), i.get("state", "open"),
            1 if "pull_request" in i else 0,
            json.dumps(labels, ensure_ascii=False),
            i.get("created_at"), i.get("closed_at"),
        ),
    )


def upsert_release(conn: sqlite3.Connection, repo_full: str, rel: dict[str, Any]) -> None:
    repo_id = ids.build("github", "repo", repo_full)
    rid = ids.build("github", "release", f"{repo_full}@{rel.get('tag_name', '')}")
    conn.execute(
        """INSERT INTO releases (id, repo_id, tag_name, name, published_at, notes)
           VALUES (?,?,?,?,?,?)
           ON CONFLICT(repo_id, tag_name) DO UPDATE SET
             name=excluded.name, published_at=excluded.published_at, notes=excluded.notes""",
        (
            rid, repo_id, rel.get("tag_name", ""), rel.get("name"),
            rel.get("published_at"), rel.get("body"),
        ),
    )


def upsert_star(conn: sqlite3.Connection, full_name: str) -> None:
    conn.execute(
        """INSERT INTO my_stars (full_name, starred_at, synced_at) VALUES (?,?,?)
           ON CONFLICT(full_name) DO NOTHING""",
        (full_name, _now_iso(), _now_iso()),
    )


# ---------------------------------------------------------------- 采集主流程

def _update_sync(conn: sqlite3.Connection, entity: str, cursor_value: str | None = None) -> None:
    now = _now_iso()
    conn.execute(
        """INSERT INTO sync_state (entity, last_synced_at, cursor) VALUES (?,?,?)
           ON CONFLICT(entity) DO UPDATE SET last_synced_at=excluded.last_synced_at,
             cursor=COALESCE(excluded.cursor, sync_state.cursor)""",
        (entity, now, cursor_value),
    )


def sync(conn: sqlite3.Connection, username: str | None = None,
         *, include_commits: bool = True, max_repos: int = 50) -> dict[str, int]:
    """全量 + 增量采集到 SQLite。

    username 缺省时用 token 当前用户；无 token 且无 username 会抛错。
    返回 {repos, commits, issues, releases, stars} 计数。
    """
    token = _token()
    stats = {"repos": 0, "commits": 0, "issues": 0, "releases": 0, "stars": 0}

    # 1. 用户身份
    if not username:
        me = _get(f"{API_BASE}/user", token)
        username = me.get("login", "")
        if not username:
            raise SyncError("无法解析当前用户，请传 --user 或配置 GITHUB_TOKEN")

    # 2. 仓库列表（含 star 的仓库单列）
    repos = _get(f"{API_BASE}/users/{username}/repos?per_page=100", token) \
        if not token else _paginate(f"{API_BASE}/user/repos?sort=updated", token, max_pages=max_repos // 10 + 1)
    if not isinstance(repos, list):
        repos = []
    repos = repos[:max_repos]

    for r in repos:
        upsert_repo(conn, r)
        stats["repos"] += 1
        full = r["full_name"]

        # 3. 每个仓库：commits / issues / releases
        if include_commits:
            try:
                commits = _paginate(f"{API_BASE}/repos/{full}/commits?per_page=100", token, max_pages=2)
                for c in commits:
                    upsert_commit(conn, full, c)
                    stats["commits"] += 1
            except SyncError:
                pass  # 单仓失败不阻断（如空仓/权限不足）

        try:
            issues = _paginate(f"{API_BASE}/repos/{full}/issues?state=all&per_page=100", token, max_pages=2)
            for i in issues:
                upsert_issue(conn, full, i)
                stats["issues"] += 1
        except SyncError:
            pass

        try:
            releases = _paginate(f"{API_BASE}/repos/{full}/releases?per_page=30", token, max_pages=1)
            for rel in releases:
                upsert_release(conn, full, rel)
                stats["releases"] += 1
        except SyncError:
            pass

    # 4. 我 star 的仓库
    try:
        stars = _paginate(f"{API_BASE}/user/starred?per_page=100", token, max_pages=3)
        for s in stars:
            upsert_star(conn, s.get("full_name", ""))
            stats["stars"] += 1
    except SyncError:
        pass

    # 5. 同步游标
    _update_sync(conn, f"repos:{username}")
    conn.commit()
    return stats


def collect(conn: sqlite3.Connection, username: str | None, **kwargs: Any) -> dict[str, int]:
    return sync(conn, username, **kwargs)