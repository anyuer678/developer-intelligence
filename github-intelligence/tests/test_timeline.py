"""Timeline 算法引擎测试（合成信号包 + 真实信号包集成）。"""

from __future__ import annotations

import importlib.util
import json
import subprocess
from pathlib import Path

import pytest

from pgi.cli import main as cli_main
from pgi.timeline import (
    merge_sparse_buckets,
    render_gantt,
    render_text,
    run_timeline,
)


def _month(m: str, commits: int, dirs=None, deps=None, terms=None) -> dict:
    return {
        "month": m,
        "commits": commits,
        "contributors": 1,
        "new_dirs": dirs or [],
        "deps_added": deps or [],
        "top_terms": terms or [],
    }


def _two_regime_pack() -> dict:
    return {
        "schemaVersion": "1.0",
        "repo": "demo",
        "truncated": False,
        "months": [
            _month("2026-01", 10, dirs=["src"], deps=["fastapi"], terms=["api", "server"]),
            _month("2026-02", 12, dirs=["src"], deps=[], terms=["api"]),
            _month("2026-03", 8, dirs=["src"], deps=["pydantic"], terms=["api", "model"]),
            _month("2026-05", 15, dirs=["web"], deps=["vue"], terms=["ui", "frontend"]),
            _month("2026-06", 11, dirs=["web"], deps=[], terms=["ui"]),
        ],
    }


def test_two_regimes_split_at_boundary():
    tl = run_timeline(_two_regime_pack())
    assert len(tl["stages"]) == 2
    assert tl["stages"][0]["start"] == "2026-01"
    assert tl["stages"][1]["end"] == "2026-06"
    # 日历缺口（04 月缺失）强制边界
    assert tl["stages"][1]["months"][0] == "2026-05"
    assert all(st["label"] is None for st in tl["stages"])


def test_labels_injection():
    tl = run_timeline(_two_regime_pack(), labels={0: "API 后端期", 1: "前端期"})
    assert tl["stages"][0]["label"] == "API 后端期"


def test_single_month_single_stage():
    tl = run_timeline({"repo": "x", "months": [_month("2026-07", 5)]})
    assert len(tl["stages"]) == 1


def test_all_similar_single_stage():
    pack = {
        "repo": "y",
        "months": [
            _month(f"2026-0{i}", 8, dirs=["src"], deps=["a"], terms=["core"]) for i in range(1, 7)
        ],
    }
    tl = run_timeline(pack)
    assert len(tl["stages"]) == 1


def test_sparse_merge_keeps_low_activity_months():
    months = [_month("2026-01", 10), _month("2026-02", 1), _month("2026-03", 1)]
    buckets = merge_sparse_buckets(months, min_bucket_commits=2)
    assert len(buckets) == 1 and buckets[0]["commits"] == 12


def test_empty_pack_raises():
    with pytest.raises(ValueError):
        run_timeline({"repo": "z", "months": []})


def test_renderers():
    tl = run_timeline(_two_regime_pack())
    text = render_text(tl)
    gantt = render_gantt(tl)
    assert "Evolution Timeline" in text and "boundary" in text
    assert gantt.startswith("gantt") and "dateFormat YYYY-MM" in gantt


def test_cli_json_and_summary(tmp_path, capsys):
    pack_file = tmp_path / "pack.json"
    pack_file.write_text(json.dumps(_two_regime_pack()), encoding="utf-8")
    assert cli_main(["timeline", "--signals", str(pack_file), "--format", "json"]) == 0
    data = json.loads(capsys.readouterr().out)
    assert len(data["stages"]) == 2

    assert cli_main(["timeline", "--signals", str(pack_file)]) == 0
    assert "Stage" in capsys.readouterr().out


def test_cli_bad_pack(tmp_path):
    bad = tmp_path / "bad.json"
    bad.write_text("{}", encoding="utf-8")
    assert cli_main(["timeline", "--signals", str(bad)]) == 2


@pytest.mark.skipif(
    importlib.util.find_spec("repo_intel") is None,
    reason="repo-intel-core 未安装",
)
def test_cross_repo_integration_with_core_signals():
    """端到端：用 core 对自身产 signals → pgi 出 timeline（真实数据冒烟）。"""
    core_root = Path(__file__).resolve().parent.parent.parent / "repo-intel-core"
    if not (core_root / ".git").exists():
        pytest.skip("core 仓库不在本地")

    import os

    env = {**os.environ, "PYTHONIOENCODING": "utf-8"}
    proc = subprocess.run(
        ["repo-intel", "signals", str(core_root), "--format", "json"],
        capture_output=True,
        text=True,
        encoding="utf-8-sig",
        env=env,
    )
    assert proc.returncode == 0
    pack = json.loads(proc.stdout)

    pack_file = core_root.parent / "__smoke_signals.json"
    pack_file.write_text(json.dumps(pack, ensure_ascii=False), encoding="utf-8")
    try:
        assert cli_main(["timeline", "--signals", str(pack_file)]) == 0
    finally:
        pack_file.unlink(missing_ok=True)
