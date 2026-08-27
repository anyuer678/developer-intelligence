"""入口点检测（TASK-M1-02）。输入为扫描期已读入的代码文本缓存。"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from repo_intel.detect.quality import is_test_file
from repo_intel.rules.loader import load
from repo_intel.schema.profiles import EntryCandidate


@dataclass
class EntryPointRule:
    id: str
    type: str
    confidence: float
    languages: set[str] = field(default_factory=set)
    content_all: list[str] = field(default_factory=list)
    file_name: str | None = None
    manifest_field: str | None = None


def _load_rules() -> list[EntryPointRule]:
    out: list[EntryPointRule] = []
    for item in load("entrypoints").get("rules", []):
        out.append(
            EntryPointRule(
                id=item["id"],
                type=item.get("type", "cli"),
                confidence=float(item.get("confidence", 0.5)),
                languages=set(item.get("languages", [])),
                content_all=list(item.get("content_all", [])),
                file_name=item.get("file_name"),
                manifest_field=item.get("manifest_field"),
            ),
        )
    return out


def _bin_targets(bin_value: Any) -> list[str]:
    """package.json bin 字段：string 或 {name: path} 两种形态。"""
    if isinstance(bin_value, str):
        return [bin_value]
    if isinstance(bin_value, dict):
        return [str(v) for v in bin_value.values()]
    return []


def detect_entrypoints(
    code_texts: dict[str, tuple[str, str]],
    root_path: Path,
) -> list[EntryCandidate]:
    """code_texts: rel_posix -> (language, text)。返回按置信度降序的候选列表。"""
    rules = _load_rules()

    root_pkg: dict[str, Any] | None = None
    pkg_path = root_path / "package.json"
    if pkg_path.is_file():
        try:
            loaded = json.loads(pkg_path.read_text(encoding="utf-8"))
            if isinstance(loaded, dict):
                root_pkg = loaded
        except (OSError, ValueError):
            root_pkg = None

    hits: list[EntryCandidate] = []

    for rule in rules:
        # --- manifest 驱动（bin 字段）---
        if rule.manifest_field == "bin":
            if not root_pkg:
                continue
            for target in _bin_targets(root_pkg.get("bin")):
                rel = Path(target.replace("\\", "/")).as_posix().lstrip("./")
                if (root_path / rel).is_file():
                    hits.append(
                        EntryCandidate(
                            file=rel,
                            type=rule.type,
                            confidence=rule.confidence,
                            evidence=[f"package.json bin -> {target}"],
                        ),
                    )
            continue

        # --- 内容/文件名驱动（跳过测试文件：ADR-014 自举发现噪音）---
        for rel, (lang, text) in code_texts.items():
            if is_test_file(rel):
                continue
            if rule.file_name is not None:
                if Path(rel).name == rule.file_name:
                    hits.append(
                        EntryCandidate(
                            file=rel,
                            type=rule.type,
                            confidence=rule.confidence,
                            evidence=[f"文件名匹配 {rule.file_name}"],
                        ),
                    )
                continue
            if lang not in rule.languages:
                continue
            if all(pat in text for pat in rule.content_all):
                hits.append(
                    EntryCandidate(
                        file=rel,
                        type=rule.type,
                        confidence=rule.confidence,
                        evidence=[f"content: {' & '.join(rule.content_all)}"],
                    ),
                )

    hits.sort(key=lambda c: (-(c.confidence or 0.0), c.file))
    return hits
