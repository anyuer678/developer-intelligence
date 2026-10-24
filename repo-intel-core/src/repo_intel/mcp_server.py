"""最小 stdio JSON-RPC 调度器（MCP 兼容面）——repo-intel 四工具。

协议面与 pgi.mcp_server 同款：initialize / tools/list / tools/call / ping；
通知（无 id）不回包。宿主（lumen 等）以 stdio 拉起本进程：

    python -m repo_intel.mcp_server

会话级 profile 缓存：同一路径二次调用不重扫（进程生命周期内有效），
repo_scan 传 refresh=true 强制重扫。
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Iterator
from typing import Any

from repo_intel import __version__
from repo_intel.scanner import scan_repo

SERVER_INFO = {"name": "repo-intel", "version": __version__}

# {绝对路径: profile_json}；stdio 常驻进程内有效，重启即失效
_PROFILE_CACHE: dict[str, dict[str, Any]] = {}

_TOOLS: list[dict[str, Any]] = [
    {
        "name": "repo_scan",
        "description": "全量仓库画像：语言/文件/模块/框架/构建运行/热点/技术债信号（零 LLM 静态解析）",
        "inputSchema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "仓库根目录（绝对路径）"},
                "refresh": {"type": "boolean", "default": False,
                             "description": "忽略会话缓存强制重扫"},
            },
            "required": ["path"],
        },
    },
    {
        "name": "repo_graph",
        "description": "模块内部依赖图（JSON 边表或 mermaid 图）",
        "inputSchema": {
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "format": {"type": "string", "enum": ["json", "mermaid"],
                            "default": "json"},
            },
            "required": ["path"],
        },
    },
    {
        "name": "repo_signals",
        "description": "月度切片信号包：逐月提交/贡献者/新目录/新增依赖/热词（需 git 仓库）",
        "inputSchema": {
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "months": {"type": "integer", "description": "只取最近 N 个月"},
            },
            "required": ["path"],
        },
    },
    {
        "name": "repo_evolution",
        "description": "numstat 全量演化统计：周趋势/热点模块/风险等级（需 git 仓库）",
        "inputSchema": {
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "top": {"type": "integer", "default": 10, "description": "topFiles 截断数"},
            },
            "required": ["path"],
        },
    },
]


# ---------------------------------------------------------------- 工具实现

def _profile_json(path: str, refresh: bool = False) -> dict[str, Any]:
    """取 profile（带会话缓存）。失败抛 ValueError（由调度层转 ok:false）。"""
    key = str(path)
    if refresh or key not in _PROFILE_CACHE:
        try:
            profile = scan_repo(path)
        except NotADirectoryError as exc:
            raise ValueError(f"路径不是目录: {exc}") from exc
        _PROFILE_CACHE[key] = json.loads(profile.model_dump_json(by_alias=True))
    return _PROFILE_CACHE[key]


def tool_repo_scan(args: dict[str, Any]) -> dict[str, Any]:
    path = str(args.get("path", ""))
    refresh = bool(args.get("refresh", False))
    cached = (not refresh) and (path in _PROFILE_CACHE)
    try:
        profile = _profile_json(path, refresh=refresh)
    except ValueError as exc:
        return {"ok": False, "error": str(exc)}
    return {"ok": True, "path": path, "cached": cached, "profile": profile}


def tool_repo_graph(args: dict[str, Any]) -> dict[str, Any]:
    path = str(args.get("path", ""))
    fmt = args.get("format", "json")
    try:
        profile = _profile_json(path)
    except ValueError as exc:
        return {"ok": False, "error": str(exc)}
    dg = profile.get("dependencyGraph") or {}
    if fmt == "mermaid":
        from repo_intel.cli import _mermaid

        return {"ok": True, "format": "mermaid", "mermaid": _mermaid(profile)}
    return {"ok": True, "format": "json", "graph": dg}


def tool_repo_signals(args: dict[str, Any]) -> dict[str, Any]:
    from repo_intel.gitmeta.signals import monthly_signals

    path = str(args.get("path", ""))
    months = args.get("months")
    pack = monthly_signals(path, max_months=int(months) if months else None)
    if pack is None:
        return {"ok": False, "error": "非 git 仓库或 git 命令不可用"}
    return {"ok": True, "pack": pack}


def tool_repo_evolution(args: dict[str, Any]) -> dict[str, Any]:
    from repo_intel.gitmeta.evolution import evolution_summary

    path = str(args.get("path", ""))
    top = int(args.get("top", 10))
    summary = evolution_summary(path, top_n=top)
    if summary is None:
        return {"ok": False, "error": "非 git 仓库或 git 命令故障"}
    return {"ok": True, "summary": summary}


_DISPATCH = {
    "repo_scan": tool_repo_scan,
    "repo_graph": tool_repo_graph,
    "repo_signals": tool_repo_signals,
    "repo_evolution": tool_repo_evolution,
}


# ---------------------------------------------------------------- 协议调度

def handle(msg: dict) -> dict | None:
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
        try:
            result = fn(params.get("arguments") or {})
        except ValueError as exc:
            result = {"ok": False, "error": str(exc)}
        text = json.dumps(result, ensure_ascii=False)
        return _ok(msg_id, {"content": [{"type": "text", "text": text}]})
    if method.startswith("notifications/"):
        return None
    return _err(msg_id, -32601, f"未知方法: {method}")


def serve(inp: Iterator[str], out) -> None:
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
                resp = handle(msg)
        if resp is not None:
            out.write(json.dumps(resp, ensure_ascii=False) + "\n")
            out.flush()


def main(argv: list[str] | None = None) -> int:  # pragma: no cover - 常驻进程入口
    parser = argparse.ArgumentParser(prog="repo-intel-mcp",
                                     description="repo-intel tools (stdio)")
    parser.parse_args(argv)
    serve(sys.stdin, sys.stdout)
    return 0


# ---------------------------------------------------------------- 内部


def _ok(msg_id, result: dict) -> dict:
    return {"jsonrpc": "2.0", "id": msg_id, "result": result}


def _err(msg_id, code: int, message: str) -> dict:
    return {"jsonrpc": "2.0", "id": msg_id, "error": {"code": code, "message": message}}


if __name__ == "__main__":  # pragma: no cover
    main()
