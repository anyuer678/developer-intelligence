"""TASK-M3-04 验收：Golden 快照基线。

归一化规则（剥离跨运行不稳定字段）：
- generatedAt / tool.version / repo.path / vcs.headBranch
基线再生：REPO_INTEL_UPDATE_GOLDEN=1 pytest tests/test_golden.py
或 python scripts/update-golden.py
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest
from conftest import build_graph_repo, build_m2_repo, build_polyglot

GOLDEN_DIR = Path(__file__).parent / "golden"

FIXTURES = {
    "demo-polyglot": build_polyglot,
    "demo-graph": build_graph_repo,
    "demo-m2": build_m2_repo,
}


def _normalize(profile_json: dict) -> dict:
    dump = json.loads(json.dumps(profile_json, ensure_ascii=False))
    dump.pop("generatedAt", None)
    tool = dump.get("tool") or {}
    tool.pop("version", None)
    repo = dump.get("repo") or {}
    repo.pop("path", None)
    if isinstance(repo.get("vcs"), dict):
        repo["vcs"].pop("headBranch", None)
        repo["vcs"].pop("isDirty", None)
    # 可选能力（[arch] extra）输出整体剥离：CI 可能未装 tree-sitter，
    # 其正确性由 tests/test_callgraph.py 专测守护
    dump.pop("callGraph", None)
    return dump


def _load_or_update(name: str, normalized: dict) -> None:
    GOLDEN_DIR.mkdir(exist_ok=True)
    path = GOLDEN_DIR / f"{name}.json"
    if os.environ.get("REPO_INTEL_UPDATE_GOLDEN") == "1":
        path.write_text(
            json.dumps(normalized, ensure_ascii=False, indent=1, sort_keys=True) + "\n",
            encoding="utf-8",
        )


@pytest.mark.parametrize("name", sorted(FIXTURES))
def test_golden_snapshot(name: str, tmp_path_factory: pytest.TempPathFactory):
    builder = FIXTURES[name]
    root = builder(tmp_path_factory.mktemp(f"golden-{name}"))
    from repo_intel.scanner import scan_repo

    profile = scan_repo(root)
    normalized = _normalize(json.loads(profile.model_dump_json(by_alias=True)))

    golden_path = GOLDEN_DIR / f"{name}.json"
    if not golden_path.exists() or os.environ.get("REPO_INTEL_UPDATE_GOLDEN") == "1":
        _load_or_update(name, normalized)

    expected = json.loads(golden_path.read_text(encoding="utf-8"))
    assert normalized == expected, (
        f"{name} 输出与 golden 基线不一致。"
        "若为有意变更：运行 scripts/update-golden.py 并人工 review diff 后一并提交。"
    )
