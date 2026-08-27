"""TASK-P0-03/04 验收：Schema v1 与 db 工具层。"""

from __future__ import annotations

import sqlite3

import pytest

from pgi.db import SCHEMA_VERSION, connect, init_db, schema_version
from pgi.ids import build


@pytest.fixture()
def conn() -> sqlite3.Connection:
    c = connect(":memory:")
    init_db(c)
    return c


def _insert_repo(c: sqlite3.Connection) -> str:
    rid = build("github", "repo", "anyuer678/lumen")
    c.execute(
        "INSERT INTO repos(id, full_name, description, first_synced_at, last_synced_at) "
        "VALUES (?,?,?,?,?)",
        (
            rid,
            "anyuer678/lumen",
            "个人 Agent Runtime",
            "2026-08-26T00:00:00Z",
            "2026-08-26T00:00:00Z",
        ),
    )
    return rid


def test_init_idempotent_and_versioned(conn):
    v = schema_version(conn)
    assert v == SCHEMA_VERSION == 1
    row = conn.execute("SELECT value FROM schema_meta WHERE key='schema_version'").fetchone()
    assert row["value"] == "1"
    init_db(conn)  # 二次执行不报错
    assert schema_version(conn) == 1


def test_commit_insert_populates_fts(conn):
    rid = _insert_repo(conn)
    cid = build("github", "commit", f"anyuer678/lumen@{'a' * 40}")
    conn.execute(
        "INSERT INTO commits(id, repo_id, sha, authored_at, message) VALUES (?,?,?,?,?)",
        (cid, rid, "a" * 40, "2026-08-20T10:00:00Z", "feat: sandbox 权限层"),
    )
    hit = conn.execute(
        "SELECT message FROM commits_fts WHERE commits_fts MATCH 'sandbox'",
    ).fetchall()
    assert len(hit) == 1 and "sandbox" in hit[0]["message"]


def test_issue_fts_and_fk_cascade(conn):
    rid = _insert_repo(conn)
    iid = build("github", "issue", "anyuer678/lumen#12")
    conn.execute(
        "INSERT INTO issues(id, repo_id, number, title, state) VALUES (?,?,?,?, 'open')",
        (
            iid,
            rid,
            12,
            "权限系统薄弱",
        ),
    )
    # 已知局限（ADR）：FTS5 unicode61 不切分中文，整串为一个 token —— 按完整短语匹配
    hit = conn.execute(
        "SELECT title FROM issues_fts WHERE issues_fts MATCH '\"权限系统薄弱\"'",
    ).fetchall()
    assert len(hit) == 1

    conn.execute("DELETE FROM repos WHERE id=?", (rid,))
    assert conn.execute("SELECT COUNT(*) c FROM issues").fetchone()["c"] == 0


def test_my_stars_verdict_check(conn):
    conn.execute(
        "INSERT INTO my_stars(full_name, verdict, synced_at) VALUES ('a/b','dead','now')",
    )
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            "INSERT INTO my_stars(full_name, verdict, synced_at) VALUES ('c/d','gone','now')",
        )


def test_wal_on_file_db(tmp_path):
    db_path = tmp_path / "pgi.db"
    c = connect(db_path)
    mode = c.execute("PRAGMA journal_mode").fetchone()[0]
    assert mode.lower() == "wal"


def test_fts_update_and_delete_propagate(conn):
    rid = _insert_repo(conn)
    cid = build("github", "commit", f"anyuer678/lumen@{'b' * 40}")
    conn.execute(
        "INSERT INTO commits(id, repo_id, sha, authored_at, message) VALUES (?,?,?,?,?)",
        (cid, rid, "b" * 40, "2026-08-21T09:00:00Z", "feat: sandbox layer"),
    )
    assert (
        conn.execute(
            "SELECT COUNT(*) c FROM commits_fts WHERE commits_fts MATCH 'sandbox'"
        ).fetchone()["c"]
        == 1
    )

    conn.execute("UPDATE commits SET message='feat: auth layer' WHERE id=?", (cid,))
    assert (
        conn.execute(
            "SELECT COUNT(*) c FROM commits_fts WHERE commits_fts MATCH 'sandbox'"
        ).fetchone()["c"]
        == 0
    )
    assert (
        conn.execute(
            "SELECT COUNT(*) c FROM commits_fts WHERE commits_fts MATCH 'auth'"
        ).fetchone()["c"]
        == 1
    )

    conn.execute("DELETE FROM commits WHERE id=?", (cid,))
    assert (
        conn.execute(
            "SELECT COUNT(*) c FROM commits_fts WHERE commits_fts MATCH 'auth'"
        ).fetchone()["c"]
        == 0
    )


def test_repos_fts_null_description_safe(conn):
    rid2 = build("github", "repo", "anyuer678/no-desc")
    conn.execute(
        "INSERT INTO repos(id, full_name, first_synced_at, last_synced_at) VALUES (?,?,?,?)",
        (rid2, "anyuer678/no-desc", "now", "now"),
    )
    conn.execute(
        "UPDATE repos SET description=NULL WHERE id=?",
        (rid2,),
    )  # NULL→NULL 路径不炸
    assert (
        conn.execute(
            "SELECT COUNT(*) c FROM repos_fts WHERE repos_fts MATCH 'Agent'",
        ).fetchone()["c"]
        == 0
    )  # 无描述仓库不入索引
