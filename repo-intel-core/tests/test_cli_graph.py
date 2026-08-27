"""TASK-M1-08 验收：CLI `graph` 子命令。"""

from __future__ import annotations

import json

from repo_intel.cli import main


def test_graph_summary(graph_root, capsys):
    assert main(["graph", str(graph_root)]) == 0
    out = capsys.readouterr().out
    assert "modules=8" in out
    assert "(root) -> tools" in out


def test_graph_mermaid(graph_root, capsys):
    assert main(["graph", str(graph_root), "--format", "mermaid"]) == 0
    out = capsys.readouterr().out
    assert out.startswith("flowchart LR")
    assert '["(root)"]' in out and '["tools"]' in out and '["internal"]' in out
    edges = [line for line in out.splitlines() if "-->" in line]
    assert len(edges) == 3
    assert all('|"' in edge and '"|' in edge for edge in edges)


def test_graph_json(graph_root, capsys):
    assert main(["graph", str(graph_root), "--format", "json"]) == 0
    dg = json.loads(capsys.readouterr().out)
    assert {"internal", "external"} <= set(dg)
    assert len(dg["internal"]) == 3


def test_graph_bad_path(graph_root, capsys):
    from pathlib import Path

    missing = Path(graph_root).parent / "__missing__"
    assert main(["graph", str(missing)]) == 2
