"""TASK-M2-02 验收：框架识别。"""

from __future__ import annotations

from repo_intel.detect.frameworks import detect_frameworks, load_framework_rules


def test_rule_table_has_at_least_30_rules():
    rules = load_framework_rules()
    assert len(rules) >= 30
    categories = {r.category for r in rules}
    assert {"frontend-framework", "web-framework", "ai-llm", "testing"} <= categories
    ids = [r.id for r in rules]
    assert len(ids) == len(set(ids)), "规则 id 不得重复"


def test_declared_dep_hit_with_version(m2_profile_json):
    fw = {f["name"]: f for f in m2_profile_json["frameworks"]}
    assert "FastAPI" in fw
    assert fw["FastAPI"]["version"] == "==0.110.0"
    assert any(e.startswith("declared: requirements.txt") for e in fw["FastAPI"]["evidence"])
    assert "Vue" in fw and fw["Vue"]["version"] == "^3.4.0"
    assert "Pydantic" in fw  # pyproject.toml 来源


def test_dev_dependency_hit(m2_profile_json):
    vitest = next(f for f in m2_profile_json["frameworks"] if f["name"] == "Vitest")
    assert vitest["category"] == "testing"


def test_content_signal_only_when_no_dep(graph_profile_json):
    """graph fixture 未声明 express 等；FastAPI 走声明路径，此处验证 content 路径可用性：
    直接调用检测器，构造仅内容命中的场景。"""
    hits = detect_frameworks(
        code_files={"a.py": "python"},
        texts={"a.py": ("python", "app = Flask(__name__)\n")},
        declared_deps={},
    )
    flask = [h for h in hits if h.name == "Flask"]
    assert len(flask) == 1
    assert flask[0].evidence == ["content: Flask("]


def test_content_signal_skips_test_files():
    """M3 消噪：tests/ 下出现框架特征字符串不再触发内容命中（ADR 之噪音条款）。"""
    hits = detect_frameworks(
        code_files={
            "app.py": "python",
            "tests/test_app.py": "python",
            "src/app.spec.ts": "typescript",
        },
        texts={
            "app.py": ("python", "x = 1\n"),
            "tests/test_app.py": ("python", "from flask import Flask\nFlask('t')\n"),
            "src/app.spec.ts": ("typescript", "import { jest } from '@jest/globals'\n"),
        },
        declared_deps={},
    )
    assert [h.name for h in hits] == []


def test_sorted_by_category_then_confidence(m2_profile_json):
    keys = [(f["category"], -f["confidence"], f["name"]) for f in m2_profile_json["frameworks"]]
    assert keys == sorted(keys)
