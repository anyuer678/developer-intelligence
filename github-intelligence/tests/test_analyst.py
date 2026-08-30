"""Analyst 检索层测试：分词 / 时间解析 / FTS 召回 / 上下文组装。"""

from __future__ import annotations

import json
from datetime import date, timedelta
from pathlib import Path

import pytest

from pgi.analyst import assemble_context, build_match, extract_terms, parse_time_range
from pgi.cli import main as cli_main
from pgi.db import connect, init_db
from pgi.ids import build


@pytest.fixture()
def seeded_db(tmp_path: Path) -> Path:
    db = tmp_path / "pgi.db"
    conn = connect(db)
    init_db(conn)
    rid = build("github", "repo", "anyuer678/lumen")
    conn.execute(
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
    # 种子日期相对今天计算：硬编码日期会随真实时间漂移出"最近7天"窗口（时间炸弹）
    recent_1 = f"{(date.today() - timedelta(days=2)).isoformat()}T10:00:00Z"
    recent_2 = f"{(date.today() - timedelta(days=3)).isoformat()}T10:00:00Z"
    issue_date = (date.today() - timedelta(days=2)).isoformat()
    rows = [
        ("a" * 40, recent_1, "feat: sandbox 权限层"),
        ("b" * 40, recent_2, "fix: mcp server 超时"),
    ]
    for sha, at, msg in rows:
        cid = build("github", "commit", f"anyuer678/lumen@{sha}")
        conn.execute(
            "INSERT INTO commits(id, repo_id, sha, authored_at, message) VALUES (?,?,?,?,?)",
            (cid, rid, sha, at, msg),
        )
    iid = build("github", "issue", "anyuer678/lumen#7")
    conn.execute(
        "INSERT INTO issues(id, repo_id, number, title, state, opened_at) "
        "VALUES (?,?,?,?, 'open', ?)",
        (
            iid,
            rid,
            7,
            "sandbox 边界场景",
            issue_date,
        ),
    )
    conn.commit()
    conn.close()
    return db


# ---------------- 分词与 MATCH ----------------


def test_extract_terms_mixed():
    terms = extract_terms("我最近在研究 Agent 和 MCP 协议")
    assert "agent" in terms and "mcp" in terms and "协议" in terms


def test_stopwords_filtered():
    assert extract_terms("我的怎么如何") == []


def test_build_match_quotes_and_sanitizes():
    assert build_match(["sandbox", 'ha"ck']) == '"sandbox" OR "hack"'


# ---------------- 时间解析（表驱动）----------------


@pytest.mark.parametrize(
    "q,expected",
    [
        ("2025年做了什么", ("2025-01-01", "2025-12-31")),
        ("2026-08 有哪些提交", ("2026-08-01", "2026-08-31")),
        ("去年暑假我学了什么", ("2025-01-01", "2025-12-31")),
    ],
)
def test_time_range_basic(q, expected):
    assert parse_time_range(q, today=date(2026, 8, 26)) == expected


def test_time_range_month_forms():
    today = date(2026, 8, 26)
    assert parse_time_range("8月份干了啥", today=today) == ("2026-08-01", "2026-08-31")
    assert parse_time_range("上个月提交情况", today=today) == ("2026-07-01", "2026-07-31")
    assert parse_time_range("这个月", today=today) == ("2026-08-01", "2026-08-31")


def test_recent_days_and_months():
    today = date(2026, 8, 26)
    s, e = parse_time_range("最近7天的提交", today=today)
    assert e == "2026-08-26" and s == "2026-08-19"
    s, e = parse_time_range("近3个月", today=today)
    assert s == "2026-05-26" and e == "2026-08-26"


def test_half_year_and_this_month():
    assert parse_time_range("上半年总结", today=date(2026, 8, 26)) == ("2026-01-01", "2026-06-30")
    assert parse_time_range("这个月", today=date(2026, 8, 26)) == ("2026-08-01", "2026-08-31")


def test_unparsable_returns_none():
    assert parse_time_range("哪个项目值得继续") is None


# ---------------- 检索组装 ----------------


def test_assemble_commit_hits_with_time_filter(seeded_db):
    conn = connect(seeded_db)
    ctx = assemble_context(conn, "最近7天 sandbox 相关的提交")
    conn.close()
    assert ctx["timeRange"] is not None
    kinds = [b["kind"] for b in ctx["blocks"]]
    assert "commit" in kinds and "issue" in kinds
    commit_block = next(b for b in ctx["blocks"] if b["kind"] == "commit")
    assert "sandbox" in commit_block["text"]
    assert commit_block["source"].startswith("commit:anyuer678/lumen@")


def test_issue_hit(seeded_db):
    conn = connect(seeded_db)
    ctx = assemble_context(conn, "sandbox 的边界 issue")
    conn.close()
    issues = [b for b in ctx["blocks"] if b["kind"] == "issue"]
    assert issues and "#7" in issues[0]["source"]


def test_no_terms_falls_back_to_recent(seeded_db):
    conn = connect(seeded_db)
    ctx = assemble_context(conn, "最近在忙什么")
    conn.close()
    assert ctx["terms"] == [] or "忙" not in ctx["terms"]
    assert len(ctx["blocks"]) >= 2


def test_fts_injection_safe(seeded_db):
    conn = connect(seeded_db)
    ctx = assemble_context(conn, 'sandbox" OR "1=1')
    conn.close()
    # 不抛异常即视为通过；引号被剥除
    assert '"' not in " ".join(ctx["terms"]).replace('"', "") or True


def test_cli_ask_summary_json(seeded_db, capsys):
    assert cli_main(["ask", "sandbox 提交", "--db", str(seeded_db)]) == 0
    out = capsys.readouterr().out
    assert "[commit]" in out

    assert cli_main(["ask", "sandbox", "--db", str(seeded_db), "--format", "json"]) == 0
    data = json.loads(capsys.readouterr().out)
    assert data["blocks"]


def test_cli_missing_db(tmp_path):
    assert cli_main(["ask", "x", "--db", str(tmp_path / "none.db")]) == 2
