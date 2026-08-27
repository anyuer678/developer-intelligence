"""框架识别（TASK-M2-02）。规则表驱动；证据链必填。"""

from __future__ import annotations

from dataclasses import dataclass, field
from fnmatch import fnmatch

from repo_intel.detect.quality import is_test_file
from repo_intel.rules.loader import load
from repo_intel.schema.profiles import FrameworkHit


@dataclass
class FrameworkRule:
    id: str
    name: str
    category: str
    confidence_base: float
    deps: list[str] = field(default_factory=list)
    globs: list[tuple[str, int]] = field(default_factory=list)
    content_any: list[str] = field(default_factory=list)
    languages: set[str] = field(default_factory=set)


def _parse_globs(raw) -> list[tuple[str, int]]:
    """兼容两种写法：[pattern, min] 或 [[p1,m1],[p2,m2]]。"""
    if not raw:
        return []
    first = raw[0]
    if isinstance(first, str):
        return [(str(raw[0]), int(raw[1]))]
    return [(str(p), int(n)) for p, n in raw]


def load_framework_rules() -> list[FrameworkRule]:
    out: list[FrameworkRule] = []
    for item in load("frameworks").get("rules", []):
        out.append(
            FrameworkRule(
                id=item["id"],
                name=item["name"],
                category=item.get("category", ""),
                confidence_base=float(item.get("confidence_base", 0.5)),
                deps=[str(d) for d in item.get("dep", [])],
                globs=_parse_globs(item.get("glob")),
                content_any=[str(c) for c in item.get("content_any", [])],
                languages=set(item.get("languages", [])),
            ),
        )
    return out


def _glob_count(code_files: dict[str, str], pattern: str) -> int:
    return sum(1 for rel in code_files if fnmatch(rel, pattern))


def detect_frameworks(
    code_files: dict[str, str],
    texts: dict[str, str],
    declared_deps: dict[str, tuple[str | None, str]],
) -> list[FrameworkHit]:
    """declared_deps: 小写包名 -> (版本原文, 来源标签如 'package.json')。

    命中优先级：声明依赖 > 文件 glob > 内容子串；证据只记录实际命中的那一路。
    """
    rules = load_framework_rules()
    hits: list[FrameworkHit] = []

    for rule in rules:
        evidence: list[str] = []
        version: str | None = None

        for dep in rule.deps:
            if dep.lower() in declared_deps:
                ver, source = declared_deps[dep.lower()]
                version = ver
                ver_part = f"@{ver}" if ver else ""
                evidence.append(f"declared: {source}:{dep}{ver_part}")
                break

        if not evidence:
            for pattern, min_count in rule.globs:
                count = _glob_count(code_files, pattern)
                if count >= min_count:
                    evidence.append(f"glob {pattern} x{count}")
                    break

        if not evidence and rule.content_any:
            for pat in rule.content_any:
                found = (
                    any(
                        lang in rule.languages and pat in text and not is_test_file(rel)
                        for rel, (lang, text) in texts.items()
                    )
                    if rule.languages
                    else any(pat in t and not is_test_file(rel) for rel, (_l, t) in texts.items())
                )
                if found:
                    evidence.append(f"content: {pat}")
                    break

        if evidence:
            hits.append(
                FrameworkHit(
                    name=rule.name,
                    version=version,
                    category=rule.category,
                    confidence=rule.confidence_base,
                    evidence=evidence,
                ),
            )

    hits.sort(key=lambda h: (h.category or "zzz", -(h.confidence or 0.0), h.name))
    return hits
