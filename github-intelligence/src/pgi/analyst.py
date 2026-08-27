"""Analyst 检索层（03 计划书 模块F 地基）：FTS 召回 + 中文时间解析 + 证据块组装。

LLM 回答层外置——本模块只产出带来源标签的上下文块（RAG 输入）。
"""

from __future__ import annotations

import re
import sqlite3
from datetime import date, timedelta

_STOP = {
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
    "什么",
    "哪些",
    "怎么",
    "如何",
    "我的",
    "我",
    "的",
    "了",
    "是",
    "在",
    "有",
    "哪个",
    "那些",
    "请",
    "帮我",
    "最近",
    "在忙",
    "正在",
    "一下",
    "情况",
}
_TERM_RE = re.compile(r"[a-z][a-z0-9_-]{1,}|[\u4e00-\u9fff]{2,}")
_SNIPPET_LEN = 200


def _clean_cjk_run(run: str) -> list[str]:
    """CJK 串清洗：剔除停用词子串，余下 ≥2 字片段保留。"""
    for s in sorted(
        (w for w in _STOP if re.fullmatch(r"[\u4e00-\u9fff]+", w)), key=len, reverse=True
    ):
        run = run.replace(s, " ")
    return [p for p in run.split() if len(p) >= 2]


def extract_terms(question: str, cap: int = 8) -> list[str]:
    """检索词：拉丁词(≥2) + 中文串去停用词后的余段(≥2)；截断。"""
    terms: list[str] = []
    for raw in _TERM_RE.findall(question.lower()):
        if re.fullmatch(r"[a-z][a-z0-9_-]*", raw):
            candidates = [raw.strip("_-")]
        else:
            candidates = _clean_cjk_run(raw)
        for t in candidates:
            if len(t) >= 2 and t not in _STOP and t not in terms:
                terms.append(t)
                if len(terms) >= cap:
                    return terms
    return terms


def build_match(terms: list[str]) -> str:
    """FTS5 MATCH 表达式：短语化 + 内部引号剥除（防语法注入）。"""
    safe = [t.replace('"', "") for t in terms]
    safe = [t for t in safe if t]
    return " OR ".join(f'"{t}"' for t in safe)


# ---------------------------------------------------------------- 中文时间解析（v1 范围见 ADR）


def parse_time_range(question: str, today: date | None = None) -> tuple[str, str] | None:
    """中文时间表达式 → (start,end) ISO 日期。无法解析返回 None。

    v1 支持：YYYY年 / YYYY-MM月 / N月份 / 今年 / 去年 / 上(个)月 / 本(这)月 /
             上半年 / 下半年 / 最近N天|日|周|个月
    """
    today = today or date.today()
    q = question.strip()

    def year(y: int) -> tuple[str, str]:
        return f"{y}-01-01", f"{y}-12-31"

    def month(y: int, m: int) -> tuple[str, str]:
        start = date(y, m, 1)
        end_y, end_m = (y, m + 1) if m < 12 else (y + 1, 1)
        return start.isoformat(), (date(end_y, end_m, 1) - timedelta(days=1)).isoformat()

    m = re.search(r"(\d{4})-(\d{1,2})(?=\s|月|$)", q)
    if m:
        return month(int(m.group(1)), int(m.group(2)))

    m = re.search(r"(\d{4})年", q)
    if m:
        return year(int(m.group(1)))

    m = re.search(r"(?<!\d)(\d{1,2})月份?", q)
    if m and "最近" not in q[: m.start()]:
        return month(today.year, int(m.group(1)))

    if "去年" in q:
        return year(today.year - 1)
    if "今年" in q:
        return year(today.year)
    if re.search(r"上(个)?月", q):
        y, mo = (today.year, today.month - 1) if today.month > 1 else (today.year - 1, 12)
        return month(y, mo)
    if re.search(r"(本|这)个月?", q):
        return month(today.year, today.month)
    if "上半年" in q:
        return f"{today.year}-01-01", f"{today.year}-06-30"
    if "下半年" in q:
        return f"{today.year}-07-01", f"{today.year}-12-31"

    m = re.search(r"(?:最近|近)(\d+)(?:天|日)", q)
    if m:
        n = int(m.group(1))
        return (today - timedelta(days=n)).isoformat(), today.isoformat()
    m = re.search(r"(?:最近|近)(\d+)周", q)
    if m:
        n = int(m.group(1)) * 7
        return (today - timedelta(days=n)).isoformat(), today.isoformat()
    m = re.search(r"(?:最近|近)(\d+)个?月", q)
    if m:
        import calendar

        n = int(m.group(1))
        y, mo = today.year, today.month - n
        while mo <= 0:
            mo += 12
            y -= 1
        day = min(today.day, calendar.monthrange(y, mo)[1])
        return date(y, mo, day).isoformat(), today.isoformat()
    return None


# ---------------------------------------------------------------- 召回与组装


def _fts(conn: sqlite3.Connection, table: str, match: str, limit: int) -> list[sqlite3.Row]:
    try:
        return conn.execute(
            f"SELECT rowid FROM {table}_fts WHERE {table}_fts MATCH ? LIMIT ?",
            (match, limit),
        ).fetchall()
    except sqlite3.OperationalError:
        return []


def _commit_block(row: sqlite3.Row) -> dict:
    return {
        "source": f"commit:{row['full_name']}@{row['authored_at'][:10]}",
        "kind": "commit",
        "text": row["message"][:_SNIPPET_LEN],
    }


def assemble_context(conn: sqlite3.Connection, question: str, limit: int = 8) -> dict:
    """问题 → 结构化上下文块。每块带 source 标签供 LLM 引用。"""
    time_range = parse_time_range(question)
    terms = extract_terms(question)
    blocks: list[dict] = []

    def in_range(col_val: str | None) -> bool:
        return not time_range or not col_val or time_range[0] <= col_val[:10] <= time_range[1]

    if terms:
        match = build_match(terms)

        for r in _fts(conn, "commits", match, limit * 3):
            row = conn.execute(
                "SELECT c.authored_at, c.message, r.full_name "
                "FROM commits c JOIN repos r ON r.id=c.repo_id WHERE c.rowid=?",
                (r["rowid"],),
            ).fetchone()
            if row and in_range(row["authored_at"]):
                blocks.append(_commit_block(row))

        for r in _fts(conn, "issues", match, limit * 3):
            row = conn.execute(
                "SELECT i.number, i.title, i.state, i.opened_at, r.full_name "
                "FROM issues i JOIN repos r ON r.id=i.repo_id WHERE i.rowid=?",
                (r["rowid"],),
            ).fetchone()
            if row and in_range(row["opened_at"]):
                blocks.append(
                    {
                        "source": f"issue:{row['full_name']}#{row['number']}",
                        "kind": "issue",
                        "text": f"[{row['state']}] {row['title']}",
                    }
                )

        for r in _fts(conn, "repos", match, limit):
            row = conn.execute(
                "SELECT full_name, description FROM repos WHERE rowid=?",
                (r["rowid"],),
            ).fetchone()
            if row:
                blocks.append(
                    {
                        "source": f"repo:{row['full_name']}",
                        "kind": "repo",
                        "text": row["description"] or "",
                    }
                )
    else:
        # 无关键词但有时间范围/纯问题：退化为近期提交列举
        rows = conn.execute(
            "SELECT c.authored_at, c.message, r.full_name "
            "FROM commits c JOIN repos r ON r.id=c.repo_id "
            "ORDER BY c.authored_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
        for row in rows:
            if in_range(row["authored_at"]):
                blocks.append(_commit_block(row))

    seen: set[str] = set()
    unique: list[dict] = []
    for b in blocks:
        key = b["source"] + b["text"][:50]
        if key not in seen:
            seen.add(key)
            unique.append(b)
    return {
        "question": question,
        "timeRange": list(time_range) if time_range else None,
        "terms": terms,
        "blocks": unique[:limit],
    }
