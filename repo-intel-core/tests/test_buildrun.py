"""TASK-M2-03 验收：buildRun 三源推断。"""

from __future__ import annotations


def test_confidence_explicit_sources(m2_profile_json):
    br = m2_profile_json["buildRun"]
    assert br["confidence"] == 0.9
    assert set(br["buildSystem"]) >= {"node", "python", "make"}


def test_install_cmd_from_makefile_and_defaults(m2_profile_json):
    install = m2_profile_json["buildRun"]["installCmd"]
    assert "pip install -r requirements.txt" in install


def test_dev_cmd_from_scripts(m2_profile_json):
    assert "npm run dev" in m2_profile_json["buildRun"]["devCmd"]


def test_test_cmd_merges_sources_deduped(m2_profile_json):
    test = m2_profile_json["buildRun"]["testCmd"]
    assert "npm run test" in test  # package.json scripts.test
    assert "pytest -q" in test  # Makefile / CI（去重后一条）


def test_evidence_records_sources(m2_profile_json):
    evidence = m2_profile_json["buildRun"]["evidence"]
    assert any("Makefile" in e for e in evidence)
    assert any(".github/workflows" in e for e in evidence)


def test_default_fallback_low_confidence(tmp_path):
    from repo_intel.detect.buildrun import infer_build_run

    (tmp_path / "main.go").write_text("package main\n\nfunc main() {}\n", encoding="utf-8")
    (tmp_path / "go.mod").write_text("module x\n\ngo 1.22\n", encoding="utf-8")
    br = infer_build_run(tmp_path, {"go"})
    assert br.confidence == 0.9  # go.mod 存在即显式口径
    assert "go mod download" in br.install_cmd
    assert "go test ./..." in br.test_cmd

    empty = infer_build_run(tmp_path / "..", set())
    assert empty.confidence == 0.5 or empty.evidence == []
