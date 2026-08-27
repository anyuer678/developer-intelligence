"""TASK-M1-02 / M1-06 验收：入口点检测 + 模块划分与依赖图（scan 集成层）。"""

from __future__ import annotations


def test_entrypoints_detected_and_sorted(graph_profile_json):
    eps = {e["file"]: e for e in graph_profile_json["entryPoints"]}
    ids = {(e["file"], e["type"]) for e in graph_profile_json["entryPoints"]}

    assert ("cmd/server/main.go", "cli") in ids  # go-main
    assert ("app.py", "server") in ids  # fastapi
    assert ("app.py", "cli") in ids  # python __main__
    assert ("bin/cli.js", "cli") in ids  # package.json bin
    assert ("web/main.ts", "gui") in ids  # createApp

    # 置信度降序：go-main(0.9) 在 fastapi(0.85) 之前
    files_in_order = [e["file"] for e in graph_profile_json["entryPoints"]]
    assert files_in_order.index("cmd/server/main.go") < files_in_order.index("app.py")
    assert eps["app.py"]["evidence"]


def test_modules_listed_with_counts(graph_profile_json):
    mods = {m["name"]: m for m in graph_profile_json["modules"]}
    expected = {"(root)", "cmd", "internal", "tools", "bin", "src", "web", "core"}
    assert set(mods) == expected
    assert all(m["files"] == 1 for m in mods.values())
    assert all(m["responsibility"] is None for m in mods.values())  # 语义留给上层 LLM


def test_internal_edges_with_weights(graph_profile_json):
    edges = {
        (e["frm"], e["to"]): e["weight"] for e in graph_profile_json["dependencyGraph"]["internal"]
    }
    assert edges[("(root)", "tools")] == 1  # app.py from tools.helper
    assert edges[("cmd", "internal")] == 1  # go: demo/internal/auth 前缀剥离
    assert edges[("bin", "src")] == 1  # require("../src/util")


def test_external_imports_do_not_create_edges(graph_profile_json):
    edges = {(e["frm"], e["to"]) for e in graph_profile_json["dependencyGraph"]["internal"]}
    assert ("web", "(root)") not in edges  # import 'vue' 是外部包
    assert ("(root)", "(root)") not in edges


def test_cohesion_three_states(graph_profile_json):
    mods = {m["name"]: m for m in graph_profile_json["modules"]}
    assert mods["(root)"]["cohesionScore"] == 0.0  # 只有出边无内部命中
    assert mods["cmd"]["cohesionScore"] == 0.0
    assert mods["core"]["cohesionScore"] is None  # 无任何内部导入 → 三态 null
