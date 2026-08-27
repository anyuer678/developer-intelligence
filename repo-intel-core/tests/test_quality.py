"""TASK-M2-04 验收：质量指标。"""

from __future__ import annotations

from repo_intel.detect.quality import build_test_evidence, count_todos, is_test_file


def test_todos_counted(m2_profile_json):
    todos = m2_profile_json["metrics"]["todos"]
    assert todos["todoCount"] >= 2
    assert todos["fixmeCount"] == 0


def test_hotspots_long_file_and_deep_nesting(m2_profile_json):
    spots = m2_profile_json["metrics"]["complexityHotspots"]
    by_path = {}
    for s in spots:
        by_path.setdefault(s["path"], []).append(s["signal"])
    assert any(sig.startswith("long-file") for sig in by_path.get("app.py", []))
    assert any(sig.startswith("deep-nesting") for sig in by_path.get("app.py", []))
    # 长文件阈值：loc 记录与信号一致
    long_sig = next(s for s in by_path["app.py"] if s.startswith("long-file"))
    assert int(long_sig.split("=")[1]) >= 400


def test_test_evidence(m2_profile_json):
    ev = m2_profile_json["metrics"]["testEvidence"]
    assert ev["testFileCount"] == 1
    assert ev["ratioToSource"] == 0.25  # 1/4 个代码文件
    assert "pytest" in ev["frameworks"]


def test_is_test_file_patterns():
    assert is_test_file("tests/test_app.py")
    assert is_test_file("internal/auth/auth_test.go")
    assert is_test_file("src/app.spec.ts")
    assert not is_test_file("src/main.py")


def test_todo_bytes_case_sensitive():
    data = b"x TODO y todo z FIXME"
    t, f = count_todos(data)
    assert (t, f) == (1, 1)


def test_empty_evidence_when_no_tests():
    ev = build_test_evidence({"a.py": "python"}, {})
    assert ev.test_file_count == 0
    assert ev.ratio_to_source is None


# ---------------- M4#1 认知复杂度（移植自 evocode complexity_scan）----------------


from repo_intel.detect.quality import scan_complexity  # noqa: E402


def _nested_py(score_target: int) -> str:
    lines = ["def hot():", "    x = 0"]
    for i in range(score_target):
        lines.append(f"    if x < {i}:")
        lines.append("        x += 1")
    lines.append("    return x")
    return "\n".join(lines) + "\n"


def test_complexity_flags_nested_python():
    text = _nested_py(12)
    out = scan_complexity(text, "python")
    assert out is not None
    name, score, count = out
    assert name == "hot" and score >= 12 and count == 1


def test_complexity_ignores_simple_code():
    simple = "def ok():\n    return 1\n"
    assert scan_complexity(simple, "python") is None
    assert scan_complexity("const a = () => 1\n", "javascript") is None


def test_complexity_go_func():
    body_lines = ["func handler(w Writer) {"]
    for i in range(14):
        body_lines.append(f"\tif w.Read() == {i} {{ return }}")
    body_lines.append("}")
    out = scan_complexity("\n".join(body_lines) + "\n", "go")
    assert out is not None and out[2] == 1 and out[1] >= 12


def test_hotspot_signal_contains_cognitive(tmp_path):
    from repo_intel.scanner import scan_repo

    src = tmp_path / "hot"
    src.mkdir()
    body = ["def hot():", "    x = 0"]
    for i in range(12):
        body.append(f"    if x < {i}:")
        body.append("        x += 1")
    body.append("    return x")
    (src / "hot.py").write_text("\n".join(body) + "\n", encoding="utf-8")

    profile = scan_repo(src)
    signals = [s.signal for s in profile.metrics.complexity_hotspots if s.path == "hot.py"]
    assert any(sig.startswith("cognitive-complexity max=") for sig in signals)


def test_unsupported_lang_returns_none():
    assert scan_complexity("whatever", "vue") is None
