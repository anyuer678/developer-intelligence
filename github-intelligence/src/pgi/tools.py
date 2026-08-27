"""lumen 接入工具层（04 计划书 §七 的五工具，GitHub 连接器作用域 v1）。

只读；全部纯本地。L2 语义检索与跨连接器关系待后续连接器解锁。
"""

from __future__ import annotations

import sqlite3
from typing import Any

from pgi.analyst import assemble_context
from pgi.ids import parse
from pgi.timeline import run_timeline


def _err(msg: str) -> dict:
    return {"ok": False, "error": msg}


# ---------------------------------------------------------------- memory_search


def memory_search(conn: sqlite3.Connection, query: str, limit: int = 8) -> dict:
    """三层搜索的 L1 关键词层（L2 embedding / L3 关系遍历待后续连接器）。"""
    ctx = assemble_context(conn, query, limit=limit)
    return {
        "ok": True,
        "mode": "kw",
        "timeRange": ctx["timeRange"],
        "terms": ctx["terms"],
        "blocks": ctx["blocks"],
        "pending": ["sem(embedding)", "rel(graph)"],
    }


# ---------------------------------------------------------------- memory_get


def _source_url(kind: str, full_name: str, native: str) -> str:
    if kind == "repo":
        return f"https://github.com/{full_name}"
    if kind == "commit":
        return f"https://github.com/{full_name}/commit/{native.split('@')[-1]}"
    if kind == "issue":
        return f"https://github.com/{full_name}/issues/{native.split('#')[-1]}"
    return ""


def memory_get(conn: sqlite3.Connection, entity_id: str) -> dict:
    try:
        connector, kind, native = parse(entity_id)
    except Exception as exc:  # noqa: BLE001
        return _err(f"实体 ID 非法: {exc}")
    if connector != "github":
        return _err(f"v1 仅支持 github 连接器，收到: {connector}")

    if kind == "repo":
        row = conn.execute(
            "SELECT full_name, description, primary_language, stars, pushed_at "
            "FROM repos WHERE id=?",
            (entity_id,),
        ).fetchone()
        if not row:
            return _err("未找到该仓库（未同步？）")
        return {
            "ok": True,
            "entityId": entity_id,
            "sourceUri": _source_url(kind, row["full_name"], native),
            "data": dict(row),
        }

    if kind == "commit":
        row = conn.execute(
            "SELECT c.sha, c.authored_at, c.message, c.additions, c.deletions, r.full_name "
            "FROM commits c JOIN repos r ON r.id=c.repo_id WHERE c.id=?",
            (entity_id,),
        ).fetchone()
        if not row:
            return _err("未找到该提交")
        return {
            "ok": True,
            "entityId": entity_id,
            "sourceUri": _source_url("commit", row["full_name"], native),
            "data": {
                k: row[k]
                for k in ("sha", "authored_at", "message", "additions", "deletions")
            },
        }

    if kind == "issue":
        row = conn.execute(
            "SELECT i.number, i.title, i.state, i.opened_at, r.full_name "
            "FROM issues i JOIN repos r ON r.id=i.repo_id WHERE i.id=?",
            (entity_id,),
        ).fetchone()
        if not row:
            return _err("未找到该 issue")
        return {
            "ok": True,
            "entityId": entity_id,
            "sourceUri": _source_url("issue", row["full_name"], native),
            "data": dict(row),
        }

    return _err(f"v1 暂不支持类型: {kind}")


# ---------------------------------------------------------------- memory_timeline


def memory_timeline(
    conn: sqlite3.Connection,
    entity_id: str,
    theta: float = 0.6,
) -> dict:
    """从已同步的 commits 表按月聚合并跑 Timeline 引擎（无需 core 信号包）。"""
    try:
        connector, kind, native = parse(entity_id)
    except Exception as exc:  # noqa: BLE001
        return _err(f"实体 ID 非法: {exc}")
    if connector != "github" or kind != "repo":
        return _err("timeline 仅支持仓库实体 (github:repo:owner/name)")

    rows = conn.execute(
        "SELECT substr(c.authored_at,1,7) AS m, c.message, c.author_email "
        "FROM commits c JOIN repos r ON r.id=c.repo_id "
        "WHERE r.full_name=? ORDER BY c.authored_at",
        (native,),
    ).fetchall()
    if not rows:
        return _err(f"仓库无已同步提交: {native}")

    by_month: dict[str, dict] = {}
    month_authors: dict[str, set[str]] = {}
    for r in rows:
        slot = by_month.setdefault(r["m"], {"month": r["m"], "commits": 0,
                                            "contributors": 0, "new_dirs": [],
                                            "deps_added": [], "top_terms": []})
        slot["commits"] += 1
        month_authors.setdefault(r["m"], set()).add(r["author_email"] or "unknown")
    for m, authors in month_authors.items():
        by_month[m]["contributors"] = len(authors)

    # 主题词：复用 analyst 分词器聚合月度词频 top5
    from collections import Counter

    from pgi.analyst import extract_terms

    for month_key in by_month:
        counter: Counter[str] = Counter()
        for r in rows:
            if r["m"] == month_key:
                counter.update(extract_terms(r["message"]))
        by_month[month_key]["top_terms"] = [t for t, _ in counter.most_common(5)]

    pack = {"schemaVersion": "1.0", "repo": native,
            "truncated": False, "months": list(by_month.values())}
    tl = run_timeline(pack, theta=theta)
    tl["note"] = "dirs/deps 信号需配合 repo-intel signals 使用；本输出基于 commits 表"
    return {"ok": True, **tl}


# ---------------------------------------------------------------- memory_related


def memory_related(conn: sqlite3.Connection, entity_id: str) -> dict:
    """v1：仓库实体的外部依赖邻接（runtime/dev 分组）。其余实体类型返回说明。"""
    try:
        connector, kind, native = parse(entity_id)
    except Exception as exc:  # noqa: BLE001
        return _err(f"实体 ID 非法: {exc}")
    if connector != "github" or kind != "repo":
        return _err("related v1 仅支持仓库实体")
    rows = conn.execute(
        "SELECT name, version, kind FROM dependencies WHERE repo_id=? ORDER BY kind, name",
        (entity_id,),
    ).fetchall()
    deps = [{"name": r["name"], "version": r["version"], "kind": r["kind"]} for r in rows]
    return {
        "ok": True,
        "entityId": entity_id,
        "dependencies": deps,
        "note": "图关系遍历待知识图谱连接器（04 §五 L3）",
    }


# ---------------------------------------------------------------- memory_observe


def memory_observe(conn: sqlite3.Connection) -> dict:
    """观察报告 v1：诚实的能力边界声明 + 基础统计（规则引擎待多连接器）。"""
    stats = {
        "repos": conn.execute("SELECT COUNT(*) c FROM repos").fetchone()["c"],
        "commits": conn.execute("SELECT COUNT(*) c FROM commits").fetchone()["c"],
        "issues": conn.execute("SELECT COUNT(*) c FROM issues").fetchone()["c"],
    }
    observations: list[dict[str, Any]] = []
    if stats["repos"] < 2:
        observations.append({
            "rule": "R0-insufficient-connectors",
            "detail": (
                "当前仅 GitHub 单连接器且样本少；"
                "R1 聚焦/R2 重复学习/R3 孤岛规则需要 >=2 个连接器"
            ),
        })
    last = conn.execute(
        "SELECT last_synced_at FROM sync_state ORDER BY last_synced_at DESC LIMIT 1"
    ).fetchone()
    if last:
        observations.append({"rule": "sync-freshness", "detail": f"最近同步: {last[0]}"})
    return {
        "ok": True,
        "stats": stats,
        "observations": observations or [{"rule": "none", "detail": "暂无可触发规则"}],
        "note": "主动智能红线：只报告，不执行动作（04 §六）",
    }
