"""M4-03 验收：函数级调用图（tree-sitter 可选能力）。"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

from repo_intel.scanner import scan_repo

pytestmark = pytest.mark.skipif(
    importlib.util.find_spec("tree_sitter") is None,
    reason="未安装 [arch] extra（tree-sitter）",
)


def build_arch_repo(root: Path) -> Path:
    repo = root / "cg"
    repo.mkdir(parents=True)

    # Python：跨文件调用 + 环（a↔b）+ 分层违规（controller→repository）
    (repo / "app.py").write_text(
        "from svc import Engine\n"
        "from repo import UserRepository\n\n"
        "class AppController:\n"
        "    def handle(self):\n"
        "        repo = UserRepository()\n"
        "        engine = Engine()\n"
        "        return repo.load() and engine.run()\n",
        encoding="utf-8",
    )
    (repo / "svc.py").write_text(
        "class Engine:\n"
        "    def run(self):\n"
        "        return helper()\n\n"
        "def helper():\n"
        "    from util import tick\n"
        "    return tick()\n",
        encoding="utf-8",
    )
    (repo / "repo.py").write_text(
        "class UserRepository:\n    def load(self):\n        return []\n",
        encoding="utf-8",
    )
    (repo / "util.py").write_text(
        "def tick():\n    return 1\n",
        encoding="utf-8",
    )

    # Go：方法接收者聚合
    go_dir = repo / "internal" / "auth"
    go_dir.mkdir(parents=True)
    (go_dir / "auth.go").write_text(
        "package auth\n\n"
        "func (s *Service) Check() bool {\n\treturn true\n}\n\n"
        "func New() *Service {\n\treturn &Service{}\n}\n",
        encoding="utf-8",
    )
    (go_dir / "service.go").write_text(
        "package auth\n\ntype Service struct{}\n",
        encoding="utf-8",
    )

    # Java：字段类型映射解析注入调用
    java_dir = repo / "src" / "main" / "java"
    java_dir.mkdir(parents=True)
    (java_dir / "Order.java").write_text(
        "public class Order {\n"
        "  private OrderRepo orderRepo;\n"
        "  public void save() {\n"
        "    orderRepo.persist(this);\n"
        "  }\n"
        "}\n",
        encoding="utf-8",
    )
    (java_dir / "OrderRepo.java").write_text(
        "public class OrderRepo {\n  public void persist(Object o) {}\n}\n",
        encoding="utf-8",
    )
    return repo


@pytest.fixture(scope="module")
def profile(tmp_path_factory: pytest.TempPathFactory):
    root = build_arch_repo(tmp_path_factory.mktemp("callgraph"))
    return scan_repo(root)


def test_nodes_across_languages(profile):
    cg = profile.call_graph
    assert cg is not None
    keys = {n.node_key for n in cg.nodes}
    assert {"Engine", "helper", "AppController", "UserRepository"} <= keys  # python 类/函数
    assert "Service" in keys  # go 接收者类型聚合
    assert "Order" in keys and "OrderRepo" in keys  # java 类


def test_cross_file_call_edge_resolved(profile):
    cg = profile.call_graph
    edges = {(e.source_node_key, e.target_node_key) for e in cg.edges}
    assert ("AppController", "UserRepository") in edges  # 构造调用根段匹配
    assert ("AppController", "Engine") in edges
    assert ("Engine", "helper") in edges  # 同文件直呼
    assert ("helper", "tick") in edges  # 跨文件函数调用


def test_layer_violation_controller_repository(profile):
    vio = [v for v in cg_violations(profile) if v["violationType"] == "LAYER_VIOLATION"]
    assert any(v["severity"] == "HIGH" and "Controller" in v["description"] for v in vio)


def test_cycle_detection_python_pair():
    """a↔b 互调 → Tarjan SCC 报环。"""
    from repo_intel.detect.callgraph.engine import build_call_graph

    files = {
        "a.py": ("python", "def a():\n    return b()\n"),
        "b.py": ("python", "def b():\n    return a()\n"),
    }
    out = build_call_graph(files)
    assert out is not None
    cycles = [v for v in out["violations"] if v["violationType"] == "CYCLE"]
    assert len(cycles) == 1


def test_three_state_null_without_tree_sitter(monkeypatch, tmp_path_factory):
    import builtins

    real_import = builtins.__import__

    def fake_import(name, *a, **k):
        if name == "tree_sitter" or name.startswith("tree_sitter."):
            raise ImportError("blocked")
        return real_import(name, *a, **k)

    monkeypatch.setattr(builtins, "__import__", fake_import)
    root = tmp_path_factory.mktemp("nolang")
    f = root / "x.py"
    f.write_text("def a():\n    pass\n", encoding="utf-8")
    profile = scan_repo(f.parent)
    assert profile.call_graph is None  # 三态：能力未启用


def cg_violations(profile):
    return [
        {
            "violationType": v.violation_type,
            "severity": v.severity,
            "description": v.description,
        }
        for v in profile.call_graph.violations
    ]
