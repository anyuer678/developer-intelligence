"""调用图数据结构与架构违规检测（M4-03，移植自 evocode arch/base.py）。

节点以 node_key（全局唯一符号：类名 / 顶层函数名 / Go 接收者类型名）标识。
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ArchNode:
    node_key: str  # 全局唯一：类名 / 文件名:顶层函数名
    name: str
    node_type: str  # CONTROLLER/SERVICE/REPOSITORY/ENTITY/UTIL/MODULE/OTHER
    file_path: str
    line: int = 0


@dataclass
class ArchEdge:
    source: str  # node_key
    target: str
    relation: str = "CALL"


@dataclass
class ArchViolation:
    violation_type: str  # LAYER_VIOLATION / CYCLE
    description: str
    severity: str
    suggestion: str
    source: str | None = None
    target: str | None = None


# ---- 节点类型推断（按命名约定，v0.2 基础版） ----
TYPE_RULES: dict[str, tuple[str, ...]] = {
    "CONTROLLER": ("controller", "view", "api"),
    "SERVICE": ("service",),
    "REPOSITORY": ("repository", "repos", "dao", "mapper", "store"),
    "ENTITY": ("entity", "model", "domain", "dto", "vo", "po", "schema"),
    "UTIL": ("util", "helper", "common", "support", "config"),
}


def infer_node_type(name: str, file_name: str = "") -> str:
    lowered = (name + " " + file_name).lower()
    for ntype, keywords in TYPE_RULES.items():
        for kw in keywords:
            if kw in lowered:
                return ntype
    return "OTHER"


_LAYER_VIOLATIONS: dict[tuple[str, str], tuple[str, str]] = {
    ("CONTROLLER", "REPOSITORY"): (
        "HIGH",
        "Controller 直接调用 Repository，违反分层，应经 Service",
    ),
    ("CONTROLLER", "ENTITY"): (
        "MEDIUM",
        "Controller 直接使用实体，建议经 Service 封装",
    ),
    ("SERVICE", "ENTITY"): ("MEDIUM", "Service 直接操作实体，建议经 Repository 访问"),
}


def check_layer_violations(
    nodes: dict[str, ArchNode],
    edges: list[ArchEdge],
) -> list[ArchViolation]:
    out: list[ArchViolation] = []
    for edge in edges:
        src = nodes.get(edge.source)
        dst = nodes.get(edge.target)
        if src is None or dst is None:
            continue
        rule = _LAYER_VIOLATIONS.get((src.node_type, dst.node_type))
        if rule:
            severity, desc = rule
            out.append(
                ArchViolation(
                    violation_type="LAYER_VIOLATION",
                    description=f"{desc}（{src.name} → {dst.name}）",
                    severity=severity,
                    suggestion=(
                        f"把 {src.name} 对 {dst.name} 的访问下沉到中间层封装，"
                        f"{src.name} 只依赖中间层接口，避免跨层调用。"
                    ),
                    source=src.node_key,
                    target=dst.node_key,
                ),
            )
    return out


def check_cycles(edges: list[ArchEdge]) -> list[ArchViolation]:
    """Tarjan SCC（size>1 或自环）：环形依赖是最严重的架构债务。"""
    adj: dict[str, list[str]] = {}
    for e in edges:
        adj.setdefault(e.source, []).append(e.target)
        adj.setdefault(e.target, [])

    index_counter = 0
    stack: list[str] = []
    on_stack: set[str] = set()
    index: dict[str, int] = {}
    lowlink: dict[str, int] = {}
    sccs: list[list[str]] = []

    def strongconnect(v: str) -> None:
        nonlocal index_counter
        index[v] = index_counter
        lowlink[v] = index_counter
        index_counter += 1
        stack.append(v)
        on_stack.add(v)
        for w in adj.get(v, []):
            if w not in index:
                strongconnect(w)
                lowlink[v] = min(lowlink[v], lowlink[w])
            elif w in on_stack:
                lowlink[v] = min(lowlink[v], index[w])
        if lowlink[v] == index[v]:
            comp: list[str] = []
            while True:
                w = stack.pop()
                on_stack.remove(w)
                comp.append(w)
                if w == v:
                    break
            if len(comp) > 1:
                sccs.append(comp)

    for v in adj:
        if v not in index:
            strongconnect(v)

    violations: list[ArchViolation] = []
    for e in edges:
        if e.source == e.target:
            violations.append(
                ArchViolation(
                    violation_type="CYCLE",
                    description=f"模块存在自依赖：{e.source} → {e.source}",
                    severity="MAJOR",
                    suggestion=(f"消除 {e.source} 对自身的调用/依赖：检查递归调用或重复注册。"),
                    source=e.source,
                    target=e.target,
                ),
            )
    for comp in sccs:
        comp.sort()
        names = " → ".join(comp + [comp[0]])
        violations.append(
            ArchViolation(
                violation_type="CYCLE",
                description=f"模块存在环形依赖：{names}",
                severity="MAJOR",
                suggestion=(
                    f"打破环 {names}：抽取公共依赖为独立模块，从环中最小节点开始消除反向依赖。"
                ),
                source=comp[0],
                target=comp[-1],
            ),
        )
    return violations


def node_metrics(nodes: list[ArchNode], edges: list[ArchEdge]) -> dict[str, dict]:
    """节点出入度指标：{node_key: {inDegree, outDegree}}。"""
    out_deg: dict[str, int] = {}
    in_deg: dict[str, int] = {}
    for e in edges:
        out_deg[e.source] = out_deg.get(e.source, 0) + 1
        in_deg[e.target] = in_deg.get(e.target, 0) + 1
    return {
        n.node_key: {
            "inDegree": in_deg.get(n.node_key, 0),
            "outDegree": out_deg.get(n.node_key, 0),
        }
        for n in nodes
    }
