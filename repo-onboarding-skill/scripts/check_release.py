#!/usr/bin/env python3
"""发布自检（05 手册 §五 的机器执行版）。

检查项：
1. skill/scripts/scan.py 的 SCAN_VERSION == CHANGELOG 最新版本段
2. CHANGELOG [Unreleased] 段非空（含占位标记也算）
3. SKILL.md frontmatter name 正确
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def scan_version() -> str:
    text = (ROOT / "skill" / "scripts" / "scan.py").read_text(encoding="utf-8")
    m = re.search(r'SCAN_VERSION\s*=\s*"([^"]+)"', text)
    return m.group(1) if m else ""


def latest_changelog_version() -> str | None:
    text = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    versions = re.findall(r"^## \[([^\]]+)\]", text, re.MULTILINE)
    for v in versions:
        if v != "Unreleased":
            return v
    return None


def main() -> int:
    errors: list[str] = []

    sv = scan_version()
    cv = latest_changelog_version()
    if sv != cv:
        errors.append(f"版本不一致: scan.py SCAN_VERSION={sv!r} vs CHANGELOG 最新={cv!r}")

    changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    unreleased = re.search(r"## \[Unreleased\]\n(.*?)(?=\n## \[|\Z)", changelog, re.DOTALL)
    body = (unreleased.group(1) if unreleased else "").strip()
    if not body:
        errors.append("CHANGELOG [Unreleased] 为空段（禁止空段，无内容时写 '- （暂无）'）")

    skill = (ROOT / "skill" / "SKILL.md").read_text(encoding="utf-8")
    if not re.search(r"^name: repo-onboarding$", skill, re.MULTILINE):
        errors.append("SKILL.md frontmatter name 不正确")

    if errors:
        print("发布自检未通过:")
        for e in errors:
            print(" -", e)
        return 1
    print(f"release check OK (v{sv})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
