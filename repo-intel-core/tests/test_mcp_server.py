"""MCP 调度器 + 四工具测试（对齐 pgi test_tools_mcp.py 的写法）。"""

from __future__ import annotations

import json

from repo_intel import __version__
from repo_intel.mcp_server import handle, tool_repo_evolution, tool_repo_graph, \
    tool_repo_scan, tool_repo_signals


# ---------------------------------------------------------------- 协议层

def test_initialize():
    r = handle({"jsonrpc": "2.0", "id": 1, "method": "initialize",
                "params": {"protocolVersion": "2024-11-05"}})
    assert r["result"]["serverInfo"] == {"name": "repo-intel", "version": __version__}


def test_ping():
    assert handle({"jsonrpc": "2.0", "id": 2, "method": "ping"})["result"] == {}


def test_tools_list_contains_four_tools():
    r = handle({"jsonrpc": "2.0", "id": 3, "method": "tools/list"})
    names = [t["name"] for t in r["result"]["tools"]]
    assert names == ["repo_scan", "repo_graph", "repo_signals", "repo_evolution"]


def test_notification_no_response():
    assert handle({"jsonrpc": "2.0", "method": "notifications/initialized"}) is None


def test_unknown_method_and_tool():
    assert handle({"jsonrpc": "2.0", "id": 4, "method": "nope"})["error"]["code"] == -32601
    r = handle({"jsonrpc": "2.0", "id": 5, "method": "tools/call",
                "params": {"name": "nope", "arguments": {}}})
    assert r["error"]["code"] == -32602


# ---------------------------------------------------------------- 工具层

def test_scan_polyglot_and_cache(polyglot_root):
    _PROFILE_CACHE_clear()
    r1 = tool_repo_scan({"path": str(polyglot_root)})
    assert r1["ok"] is True and r1["cached"] is False
    assert r1["profile"]["repo"]["name"] == "demo-polyglot"
    r2 = tool_repo_scan({"path": str(polyglot_root)})
    assert r2["cached"] is True  # 会话缓存命中，不重扫
    r3 = tool_repo_scan({"path": str(polyglot_root), "refresh": True})
    assert r3["cached"] is False


def test_scan_bad_path():
    r = tool_repo_scan({"path": "Z:/definitely/not/exist"})
    assert r["ok"] is False and "不是目录" in r["error"]


def test_graph_json_and_mermaid(graph_root):
    rj = tool_repo_graph({"path": str(graph_root), "format": "json"})
    assert rj["ok"] is True
    assert len(rj["graph"]["internal"]) >= 3  # fixture 保证 ≥3 条内部边
    rm = tool_repo_graph({"path": str(graph_root), "format": "mermaid"})
    assert rm["ok"] is True and rm["mermaid"].startswith("flowchart")


def test_signals_git_and_non_git(git_root, polyglot_root):
    r = tool_repo_signals({"path": str(git_root)})
    assert r["ok"] is True
    assert len(r["pack"]["months"]) == 2  # fixture：2026-06 与 2026-08
    r2 = tool_repo_signals({"path": str(polyglot_root)})
    assert r2["ok"] is False  # 非 git 仓库


def test_evolution_git_and_non_git(git_root, polyglot_root):
    r = tool_repo_evolution({"path": str(git_root)})
    assert r["ok"] is True
    assert r["summary"]["totalCommits"] == 2
    r2 = tool_repo_evolution({"path": str(polyglot_root)})
    assert r2["ok"] is False


def test_tools_call_roundtrip(graph_root):
    """走完整 tools/call 调度：content[0].text 是合法 JSON。"""
    r = handle({"jsonrpc": "2.0", "id": 9, "method": "tools/call",
                "params": {"name": "repo_scan", "arguments": {"path": str(graph_root)}}})
    data = json.loads(r["result"]["content"][0]["text"])
    assert data["ok"] is True


def _PROFILE_CACHE_clear():
    from repo_intel import mcp_server

    mcp_server._PROFILE_CACHE.clear()
