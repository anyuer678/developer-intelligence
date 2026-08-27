"""TASK-M1-07 验收：外部依赖清单（根 manifest 声明口径）。"""

from __future__ import annotations


def test_node_deps_with_kinds(graph_profile_json):
    ext = {(d["name"], d["kind"]): d for d in graph_profile_json["dependencyGraph"]["external"]}
    assert ext[("vue", "runtime")]["version"] == "^3.4.0"
    assert ext[("vitest", "dev")]["version"] == "^1.2.0"


def test_go_requires_runtime(graph_profile_json):
    ext = {(d["name"], d["kind"]) for d in graph_profile_json["dependencyGraph"]["external"]}
    assert ("github.com/x/y", "runtime") in ext


def test_sorted_stable(graph_profile_json):
    ext = graph_profile_json["dependencyGraph"]["external"]
    keys = [(d["kind"], d["name"].lower()) for d in ext]
    assert keys == sorted(keys)


def test_no_duplicate_name_kind(graph_profile_json):
    ext = [(d["name"], d["kind"]) for d in graph_profile_json["dependencyGraph"]["external"]]
    assert len(ext) == len(set(ext))
