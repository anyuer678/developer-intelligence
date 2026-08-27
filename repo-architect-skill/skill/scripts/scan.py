#!/usr/bin/env python3
"""repo-architect 扫描包装器（硬依赖 repo-intel-core，ADR-001）。

用法:
    python scan.py scan <仓库路径> [-o report.json] [--pretty]
缺失 core 时退出码 3 并打印安装指引。
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

try:
    from repo_intel.scanner import scan_repo  # type: ignore
except ImportError:  # pragma: no cover - 由 main 捕获路径覆盖
    scan_repo = None


def _mermaid(profile_json: dict) -> str:
    mods = [m["name"] for m in profile_json.get("modules") or []]
    ids = {name: f"m{i}" for i, name in enumerate(mods)}
    lines = ["flowchart LR"]
    for name in mods:
        safe = name.replace("\\", "\\\\").replace('"', "'").replace("|", "\\|").replace(")", "\\)")
        lines.append(f'  {ids[name]}["{safe}"]')
    for edge in (profile_json.get("dependencyGraph") or {}).get("internal") or []:
        src, dst = ids.get(edge["frm"]), ids.get(edge["to"])
        if src and dst:
            lines.append(f'  {src} -->|"{edge.get("weight") or 1}"| {dst}')
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="architect-scan")
    sub = parser.add_subparsers(dest="command", required=True)
    scan = sub.add_parser("scan")
    scan.add_argument("path")
    scan.add_argument("-o", "--output")
    scan.add_argument("--pretty", action="store_true")
    args = parser.parse_args(argv)

    if scan_repo is None:
        print(
            "错误: 未检测到引擎 repo-intel-core。\n"
            "架构报告依赖模块依赖图，请先安装：\n"
            '  pip install "repo-intel-core>=0.1"\n'
            "随后重新运行本命令。",
            file=sys.stderr,
        )
        return 3

    try:
        profile = scan_repo(args.path)
    except NotADirectoryError as exc:
        print(f"错误: {exc}", file=sys.stderr)
        return 2

    payload = json.loads(profile.model_dump_json(by_alias=True))
    payload["architectureMermaid"] = _mermaid(payload)

    text = json.dumps(payload, ensure_ascii=False, indent=2 if args.pretty else None)
    if args.output:
        Path(args.output).write_text(text + "\n", encoding="utf-8")
        print(f"已写入 {args.output}")
    else:
        print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
