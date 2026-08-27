"""调用图编排（M4-03，移植自 evocode arch/archscan.py）。

输入为 scanner 已缓存的 (rel → (lang, text)) 子集；tree-sitter 缺失时整体返回 None
（三态：能力未启用），不产生 warning 噪音。
"""

from __future__ import annotations

from repo_intel.detect.callgraph.base import (
    ArchEdge,
    ArchNode,
    check_cycles,
    check_layer_violations,
    node_metrics,
)
from repo_intel.detect.callgraph.parsers import EXT_LANG, parser_for_extension


def has_tree_sitter() -> bool:
    try:
        import tree_sitter  # noqa: F401
    except ImportError:
        return False
    return True


def build_call_graph(files: dict[str, tuple[str, str]]) -> dict | None:
    """files: rel -> (语言, 源码文本)。返回 camelCase 契约 dict；无可用解析器→None。"""
    if not has_tree_sitter():
        return None

    nodes: list[ArchNode] = []
    all_calls: list[tuple[str, list[str]]] = []

    for rel in sorted(files):
        lang, text = files[rel]
        ext = "." + rel.rsplit(".", 1)[-1].lower() if "." in rel else ""
        parse_fn = parser_for_extension(ext)
        if parse_fn is None:
            continue
        try:
            file_nodes, calls = parse_fn(rel, text.encode("utf-8", errors="replace"))
        except Exception:  # noqa: BLE001 - 单文件解析失败跳过（降级原则）
            continue
        nodes.extend(file_nodes)
        all_calls.extend(calls)

    seen_nodes: dict[str, ArchNode] = {}
    for n in nodes:
        seen_nodes.setdefault(n.node_key, n)
    nodes = list(seen_nodes.values())
    if not nodes:
        return None

    node_keys = {n.node_key for n in nodes}
    norm = {k.lower().replace("_", "") for k in node_keys}
    edges: list[ArchEdge] = []
    for caller, names in all_calls:
        for name in names:
            key = name.lower().replace("_", "")
            if key in norm:
                target = next(k for k in node_keys if k.lower().replace("_", "") == key)
                if target != caller:
                    edges.append(ArchEdge(source=caller, target=target))

    seen_edges: set[tuple[str, str]] = set()
    unique_edges: list[ArchEdge] = []
    for e in edges:
        pair = (e.source, e.target)
        if pair not in seen_edges:
            seen_edges.add(pair)
            unique_edges.append(e)

    node_map = {n.node_key: n for n in nodes}
    violations = check_layer_violations(node_map, unique_edges)
    violations += check_cycles(unique_edges)
    metrics = node_metrics(nodes, unique_edges)

    return {
        "nodes": [
            {
                "nodeKey": n.node_key,
                "name": n.name,
                "nodeType": n.node_type,
                "filePath": n.file_path,
                "line": n.line,
                **metrics.get(n.node_key, {}),
            }
            for n in nodes
        ],
        "edges": [
            {
                "sourceNodeKey": e.source,
                "targetNodeKey": e.target,
                "relation": e.relation,
            }
            for e in unique_edges
        ],
        "violations": [
            {
                "violationType": v.violation_type,
                "description": v.description,
                "severity": v.severity,
                "suggestion": v.suggestion,
                "sourceNodeKey": v.source,
                "targetNodeKey": v.target,
            }
            for v in violations
        ],
    }
