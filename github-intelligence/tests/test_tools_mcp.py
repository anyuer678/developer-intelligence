"""五工具 + MCP 调度器测试。"""

from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path

import pytest

from pgi.db import connect, init_db
from pgi.ids import build
from pgi.mcp_server import handle, serve
from pgi.tools import (
    memory_get,
    memory_observe,
    memory_related,
    memory_search,
    memory_timeline,
)


@pytest.fixture()
def db_conn(tmp_path: Path) -> sqlite3.Connection:
    conn = connect(tmp_path / "t.db")
    init_db(conn)
    rid = build("github", "repo", "anyuer678/lumen")
    conn.execute(
        "INSERT INTO repos(id, full_name, description, first_synced_at, last_synced_at) "
        "VALUES (?,?,?,?,?)",
        (rid, "anyuer678/lumen", "个人 Agent Runtime", "2026-08-26", "2026-08-26"),
    )
    cid = build("github", "commit", "anyuer678/lumen@" + "c" * 40)
    conn.execute(
        "INSERT INTO commits(id, repo_id, sha, authored_at, message) VALUES (?,?,?,?,?)",
        (cid, rid, "c" * 40, "2026-08-20T10:00:00Z", "feat: sandbox 权限层"),
    )
    for name, ver, kind in (("pydantic", ">=2.7", "runtime"), ("pytest", "^8", "dev")):
        conn.execute(
            "INSERT INTO dependencies(repo_id, name, version, kind) VALUES (?,?,?,?)",
            (rid, name, ver, kind),
        )
    conn.commit()
    yield conn
    conn.close()


# ---------------- 工具 ----------------


def test_memory_search_kw(db_conn):
    out = memory_search(db_conn, "sandbox 提交")
    assert out["ok"] and out["mode"] == "kw"
    assert any("sandbox" in b["text"] for b in out["blocks"])


def test_memory_get_commit(db_conn):
    eid = build("github", "commit", "anyuer678/lumen@" + "c" * 40)
    out = memory_get(db_conn, eid)
    assert out["ok"]
    assert out["sourceUri"].endswith("/commit/" + "c" * 40)
    assert out["data"]["message"].startswith("feat")


def test_memory_get_unknown(db_conn):
    bad = build("github", "commit", "x/y@" + "0" * 40)
    assert memory_get(db_conn, bad)["ok"] is False


def test_memory_timeline_from_db(db_conn):
    eid = build("github", "repo", "anyuer678/lumen")
    out = memory_timeline(db_conn, eid)
    assert out["ok"]
    assert len(out["stages"]) == 1
    assert out["stages"][0]["stats"]["commits"] == 1


def test_memory_related_groups_deps(db_conn):
    eid = build("github", "repo", "anyuer678/lumen")
    out = memory_related(db_conn, eid)
    kinds = {d["kind"] for d in out["dependencies"]}
    assert kinds == {"runtime", "dev"}


def test_memory_observe_honest_placeholder(db_conn):
    out = memory_observe(db_conn)
    assert out["ok"]
    rules = [o["rule"] for o in out["observations"]]
    assert any(r.startswith("R0") or r == "none" for r in rules)


# ---------------- MCP 调度器 ----------------


def _rpc(method: str, msg_id=None, **params) -> dict:
    msg: dict = {"jsonrpc": "2.0", "method": method}
    if msg_id is not None:
        msg["id"] = msg_id
    if params:
        msg["params"] = params
    return msg


def test_handle_initialize_and_tools_list(db_conn):
    resp = handle(db_conn, _rpc("initialize", 1, protocolVersion="2024-11-05"))
    assert resp["result"]["serverInfo"]["name"] == "pgi-memory"

    resp = handle(db_conn, _rpc("tools/list", 2))
    names = {t["name"] for t in resp["result"]["tools"]}
    assert names == {"memory_search", "memory_get", "memory_timeline",
                     "memory_related", "memory_observe"}


def test_handle_tools_call_roundtrip(db_conn):
    eid = build("github", "commit", "anyuer678/lumen@" + "c" * 40)
    resp = handle(db_conn, _rpc("tools/call", 3,
                                name="memory_get",
                                arguments={"entity_id": eid}))
    text = resp["result"]["content"][0]["text"]
    payload = json.loads(text)
    assert payload["ok"] is True


def test_handle_unknown_method_and_notification(db_conn):
    resp = handle(db_conn, _rpc("nope", 4))
    assert resp["error"]["code"] == -32601

    assert handle(db_conn, {"jsonrpc": "2.0",
                            "method": "notifications/initialized"}) is None


def test_serve_stdio_loop(db_conn, capsys):
    lines = [
        json.dumps(_rpc("initialize", 1)),
        "",
        json.dumps(_rpc("tools/call", 2, name="memory_observe", arguments={})),
    ]
    serve(db_conn, iter(lines), sys.stdout)
    outs = [
        json.loads(line)
        for line in capsys.readouterr().out.splitlines()
        if line.strip()
    ]
    assert len(outs) == 2
    assert outs[0]["id"] == 1 and outs[1]["id"] == 2


def test_serve_bad_json_error_frame(db_conn, capsys):
    serve(db_conn, iter(["not-json"]), sys.stdout)
    out = json.loads(capsys.readouterr().out.splitlines()[0])
    assert out["error"]["code"] == -32700
