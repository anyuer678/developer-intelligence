"""最小 stdio JSON-RPC 调度器（MCP 兼容面，ADR-011）。

协议面：initialize / tools/list / tools/call / ping；通知（无 id）不回包。
完整 MCP 特性（资源、订阅、sampling）待接入 lumen 时按需引入官方 SDK。
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from collections.abc import Iterator
from typing import Any

from pgi import __version__
from pgi.db import connect
from pgi.tools import (
    memory_get,
    memory_observe,
    memory_related,
    memory_search,
    memory_timeline,
)

SERVER_INFO = {"name": "pgi-memory", "version": __version__}

_TOOLS: list[dict[str, Any]] = [
    {
        "name": "memory_search",
        "description": "三层搜索 L1 关键词层：问题 → 证据块（支持中文时间表达）",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "limit": {"type": "integer", "default": 8},
            },
            "required": ["query"],
        },
    },
    {
        "name": "memory_get",
        "description": "实体详情 + 可回溯 sourceUri",
        "inputSchema": {
            "type": "object",
            "properties": {"entity_id": {"type": "string"}},
            "required": ["entity_id"],
        },
    },
    {
        "name": "memory_timeline",
        "description": "仓库演化阶段 Timeline",
        "inputSchema": {
            "type": "object",
            "properties": {
                "entity_id": {"type": "string"},
                "theta": {"type": "number", "default": 0.6},
            },
            "required": ["entity_id"],
        },
    },
    {
        "name": "memory_related",
        "description": "仓库外部依赖邻接（v1）",
        "inputSchema": {
            "type": "object",
            "properties": {"entity_id": {"type": "string"}},
            "required": ["entity_id"],
        },
    },
    {
        "name": "memory_observe",
        "description": "观察报告（只报告不执行）",
        "inputSchema": {"type": "object", "properties": {}},
    },
]

_DISPATCH = {
    "memory_search": lambda conn, a: memory_search(conn, a["query"], int(a.get("limit", 8))),
    "memory_get": lambda conn, a: memory_get(conn, a["entity_id"]),
    "memory_timeline": lambda conn, a: memory_timeline(conn, a["entity_id"],
                                                       float(a.get("theta", 0.6))),
    "memory_related": lambda conn, a: memory_related(conn, a["entity_id"]),
    "memory_observe": lambda conn, _a: memory_observe(conn),
}


def handle(conn: sqlite3.Connection, msg: dict) -> dict | None:
    """处理一条 JSON-RPC 消息；通知返回 None。"""
    method = msg.get("method", "")
    msg_id = msg.get("id")
    params = msg.get("params") or {}

    if method == "initialize":
        return _ok(msg_id, {"protocolVersion": params.get("protocolVersion", "2024-11-05"),
                            "capabilities": {"tools": {}},
                            "serverInfo": SERVER_INFO})
    if method == "ping":
        return _ok(msg_id, {})
    if method == "tools/list":
        return _ok(msg_id, {"tools": _TOOLS})
    if method == "tools/call":
        name = params.get("name", "")
        fn = _DISPATCH.get(name)
        if fn is None:
            return _err(msg_id, -32602, f"未知工具: {name}")
        result = fn(conn, params.get("arguments") or {})
        text = json.dumps(result, ensure_ascii=False)
        return _ok(msg_id, {"content": [{"type": "text", "text": text}]})
    if method.startswith("notifications/"):
        return None
    return _err(msg_id, -32601, f"未知方法: {method}")


def serve(conn: sqlite3.Connection, inp: Iterator[str], out) -> None:
    """逐行读 JSON-RPC，写回响应。Ctrl-D/Ctrl-C 结束。"""
    for line in inp:
        line = line.strip()
        if not line:
            continue
        try:
            msg = json.loads(line)
        except json.JSONDecodeError as exc:
            resp = _err(None, -32700, f"JSON 解析失败: {exc}")
        else:
            if not isinstance(msg, dict):
                resp = _err(None, -32600, "消息必须是对象")
            else:
                resp = handle(conn, msg)
        if resp is not None:
            out.write(json.dumps(resp, ensure_ascii=False) + "\n")
            out.flush()


def main(argv: list[str] | None = None) -> int:  # pragma: no cover - 常驻进程入口
    parser = argparse.ArgumentParser(prog="pgi-mcp", description="pgi memory tools (stdio)")
    parser.add_argument("--db", default="pgi.db")
    args = parser.parse_args(argv)
    conn = connect(args.db)
    try:
        serve(conn, sys.stdin, sys.stdout)
    finally:
        conn.close()
    return 0


# ---------------------------------------------------------------- 内部


def _ok(msg_id, result: dict) -> dict:
    return {"jsonrpc": "2.0", "id": msg_id, "result": result}


def _err(msg_id, code: int, message: str) -> dict:
    return {"jsonrpc": "2.0", "id": msg_id, "error": {"code": code, "message": message}}


if __name__ == "__main__":  # pragma: no cover
    main()
