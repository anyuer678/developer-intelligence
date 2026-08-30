"""采集器测试：mock GitHub API 验证 upsert 与增量逻辑。"""

from __future__ import annotations

import json
import sqlite3
from unittest.mock import patch

from pgi import ids, sync
from pgi.db import connect, init_db


def _conn() -> tuple[sqlite3.Connection, str]:
    import tempfile

    fd, path = tempfile.mkstemp(suffix=".db")
    import os

    os.close(fd)
    c = connect(path)
    init_db(c)
    return c, path


def _fake_repo(name: str) -> dict:
    return {
        "full_name": f"anyuer678/{name}", "description": f"{name} desc",
        "language": "Python", "stargazers_count": 10, "forks_count": 2,
        "fork": False, "archived": False, "visibility": "public",
        "created_at": "2026-01-01T00:00:00Z", "pushed_at": "2026-08-30T00:00:00Z",
        "topics": ["ai"], "id": 1,
    }


def _fake_commit(sha: str) -> dict:
    return {
        "sha": sha,
        "commit": {
            "author": {"date": "2026-08-01T00:00:00Z", "email": "a@b.c"},
            "message": f"msg {sha}",
        },
        "stats": {"additions": 1, "deletions": 0, "total": 1},
    }


def _fake_issue(num: int, state: str = "open") -> dict:
    return {
        "number": num, "title": f"issue {num}", "state": state,
        "labels": [{"name": "bug"}], "created_at": "2026-08-01T00:00:00Z",
        "closed_at": None, "id": num,
    }


def _fake_release(tag: str) -> dict:
    return {
        "tag_name": tag, "name": tag, "published_at": "2026-08-10T00:00:00Z",
        "body": "release notes", "id": 1,
    }


def test_upsert_repo_commit_issue_release():
    conn, path = _conn()
    try:
        sync.upsert_repo(conn, _fake_repo("lumen"))
        sync.upsert_commit(conn, "anyuer678/lumen", _fake_commit("abc123"))
        sync.upsert_issue(conn, "anyuer678/lumen", _fake_issue(1))
        sync.upsert_release(conn, "anyuer678/lumen", _fake_release("v1.0"))
        conn.commit()

        assert conn.execute("SELECT COUNT(*) FROM repos").fetchone()[0] == 1
        assert conn.execute("SELECT COUNT(*) FROM commits").fetchone()[0] == 1
        assert conn.execute("SELECT COUNT(*) FROM issues").fetchone()[0] == 1
        assert conn.execute("SELECT COUNT(*) FROM releases").fetchone()[0] == 1

        # ID 契约
        rid = conn.execute("SELECT id FROM repos").fetchone()[0]
        assert rid == ids.build("github", "repo", "anyuer678/lumen")
    finally:
        conn.close()
        import os

        os.unlink(path)


@patch.object(sync, "_get")
@patch.object(sync, "_paginate")
def test_sync_full_flow(mock_paginate, mock_get):
    conn, path = _conn()
    try:
        # /user 用 _get；repos/stars 用 _paginate
        mock_get.return_value = {"login": "anyuer678"}
        mock_paginate.side_effect = [
            [_fake_repo("lumen"), _fake_repo("keyvault")],  # repos
            [],  # commits for lumen（空）
            [],  # issues for lumen
            [],  # commits for keyvault
            [],  # issues for keyvault
            [{"full_name": "some/starred"}],  # starred
        ]
        stats = sync.sync(conn, username=None, include_commits=True, max_repos=2)
        assert stats["repos"] == 2
        assert stats["stars"] == 1
        assert conn.execute("SELECT COUNT(*) FROM repos").fetchone()[0] == 2
        assert conn.execute("SELECT COUNT(*) FROM my_stars").fetchone()[0] == 1
        # sync_state 游标已写
        assert conn.execute("SELECT COUNT(*) FROM sync_state").fetchone()[0] >= 1
    finally:
        conn.close()
        import os

        os.unlink(path)


@patch.object(sync, "_get")
def test_sync_rate_limit_raises(mock_get):
    mock_get.side_effect = sync.SyncError("GitHub API 限流（403）")
    conn, path = _conn()
    try:
        import pytest

        with pytest.raises(sync.SyncError):
            sync.sync(conn, username="anyuer678")
    finally:
        conn.close()
        import os

        os.unlink(path)


def test_paginate_breaks_on_empty():
    conn, path = _conn()
    try:
        # 直接验证 _paginate 对非 list 的容忍由 sync 主流程消化——这里验空列表
        from unittest.mock import Mock

        with patch.object(sync, "_get", return_value=[]):
            items = sync._paginate("https://api.github.com/x", "")
        assert items == []
    finally:
        conn.close()
        import os

        os.unlink(path)


def test_id_contract_in_sync():
    """采集器写入的 ID 符合 {connector}:{type}:{native_id} 契约。"""
    conn, path = _conn()
    try:
        sync.upsert_repo(conn, _fake_repo("a"))
        sync.upsert_commit(conn, "anyuer678/a", _fake_commit("deadbeef"))
        sync.upsert_issue(conn, "anyuer678/a", _fake_issue(7))
        conn.commit()
        for table, col in [("repos", "id"), ("commits", "id"), ("issues", "id")]:
            eid = conn.execute(f"SELECT {col} FROM {table}").fetchone()[0]
            connector, etype, native = ids.parse(eid)
            assert connector == "github"
    finally:
        conn.close()
        import os

        os.unlink(path)