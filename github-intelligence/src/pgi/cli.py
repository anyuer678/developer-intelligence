"""pgi 命令行门面（本地能力：init / timeline；采集子命令待时序锁解锁）。"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from pgi import __version__
from pgi.db import connect, init_db, schema_version


def _cmd_init(args: argparse.Namespace) -> int:
    conn = connect(args.db)
    try:
        init_db(conn)
        tables = [
            r[0]
            for r in conn.execute(
                "SELECT name FROM sqlite_master WHERE type IN ('table','view') "
                "AND name NOT LIKE 'sqlite_%' ORDER BY name",
            )
        ]
        print(f"已初始化 {args.db} (schema v{schema_version(conn)})")
        print("tables:", ", ".join(tables))
        return 0
    finally:
        conn.close()


def _cmd_timeline(args: argparse.Namespace) -> int:
    from pgi.timeline import load_pack, render_gantt, render_text, run_timeline

    try:
        pack = load_pack(args.signals)
        labels = json.loads(Path(args.labels).read_text(encoding="utf-8")) if args.labels else None
        tl = run_timeline(pack, theta=args.theta, labels=labels)
    except (ValueError, OSError, json.JSONDecodeError) as exc:
        print(f"错误: {exc}", file=sys.stderr)
        return 2

    if args.format == "json":
        print(json.dumps(tl, ensure_ascii=False))
    elif args.format == "gantt":
        print(render_gantt(tl))
    else:
        print(render_text(tl))
    return 0


def _cmd_ask(args: argparse.Namespace) -> int:
    from pgi.analyst import assemble_context
    from pgi.db import connect

    if not Path(args.db).is_file():
        print(f"错误: 库不存在，先执行 pgi init --db {args.db}", file=sys.stderr)
        return 2
    conn = connect(args.db)
    try:
        ctx = assemble_context(conn, args.question, limit=args.limit)
    finally:
        conn.close()

    if args.format == "json":
        print(json.dumps(ctx, ensure_ascii=False))
        return 0
    print(f"# 检索: {ctx['question']}")
    if ctx["timeRange"]:
        print(f"  时间: {ctx['timeRange'][0]} ~ {ctx['timeRange'][1]}")
    if ctx["terms"]:
        print(f"  关键词: {', '.join(ctx['terms'])}")
    if not ctx["blocks"]:
        print("  （无命中）")
    for b in ctx["blocks"]:
        snippet = b["text"].replace("\n", " ")[:120]
        print(f"  [{b['kind']}] {b['source']} — {snippet}")
    return 0


def _cmd_sync(args: argparse.Namespace) -> int:
    from pgi.sync import sync

    if not _is_file_ok(args):
        return 2
    conn = connect(args.db)
    try:
        stats = sync(conn, args.user, include_commits=not args.no_commits, max_repos=args.max_repos)
    except Exception as exc:  # noqa: BLE001 - CLI 层兜底
        print(f"采集失败: {exc}", file=sys.stderr)
        return 2
    finally:
        conn.close()

    print(f"✅ 采集完成: repos={stats['repos']} commits={stats['commits']} "
          f"issues={stats['issues']} releases={stats['releases']} stars={stats['stars']}")
    return 0


def _is_file_ok(args: argparse.Namespace) -> bool:
    from pathlib import Path

    if not Path(args.db).is_file():
        print(f"错误: 库不存在，先执行 pgi init --db {args.db}", file=sys.stderr)
        return False
    return True


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="pgi", description="Personal GitHub Intelligence")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    init_p = sub.add_parser("init", help="初始化本地 SQLite 库（幂等）")
    init_p.add_argument("--db", default="pgi.db", help="数据库文件路径")

    tl = sub.add_parser("timeline", help="由信号包生成演化阶段 Timeline（纯本地）")
    tl.add_argument("--signals", required=True, help="repo-intel signals JSON 文件")
    tl.add_argument("--theta", type=float, default=0.6, help="边界余弦阈值")
    tl.add_argument("--labels", default=None, help='阶段命名注入：{"0": "Agent 化"}')
    tl.add_argument("--format", choices=["summary", "json", "gantt"], default="summary")

    ask = sub.add_parser("ask", help="Analyst 检索层：问题 → 证据上下文块（LLM 回答外置）")
    ask.add_argument("question", help="自然语言问题（支持中文时间表达）")
    ask.add_argument("--db", default="pgi.db")
    ask.add_argument("--limit", type=int, default=8)
    ask.add_argument("--format", choices=["summary", "json"], default="summary")

    sync_p = sub.add_parser("sync", help="从 GitHub 采集仓库/提交/议题/发布/星标（增量）")
    sync_p.add_argument("--db", default="pgi.db")
    sync_p.add_argument("--user", default=None, help="GitHub 用户名（缺省用 token 当前用户）")
    sync_p.add_argument("--no-commits", action="store_true", help="跳过 commits 采集（加快）")
    sync_p.add_argument("--max-repos", type=int, default=50, help="最多采集的仓库数")

    mcp = sub.add_parser("mcp", help="以 stdio JSON-RPC 暴露 memory.* 工具（lumen/宿主接入）")
    mcp.add_argument("--db", default="pgi.db")

    args = parser.parse_args(argv)
    if args.command == "init":
        return _cmd_init(args)
    if args.command == "timeline":
        return _cmd_timeline(args)
    if args.command == "ask":
        return _cmd_ask(args)
    if args.command == "sync":
        return _cmd_sync(args)
    if args.command == "mcp":
        from pgi.db import connect as _connect
        from pgi.mcp_server import serve

        conn = _connect(args.db)
        try:
            serve(conn, sys.stdin, sys.stdout)
        finally:
            conn.close()
        return 0
    return 2  # pragma: no cover


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
