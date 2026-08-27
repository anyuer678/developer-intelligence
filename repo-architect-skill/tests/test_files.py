"""TASK-A03 验收：SKILL/模板/prompts 文件 lint。"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def test_skill_frontmatter():
    text = (ROOT / "skill" / "SKILL.md").read_text(encoding="utf-8")
    m = re.match(r"^---\n(.*?)\n---\n", text, re.DOTALL)
    assert m and "name: repo-architect" in m.group(1)


def test_skill_references_core_install_and_mermaid():
    text = (ROOT / "skill" / "SKILL.md").read_text(encoding="utf-8")
    for marker in ("repo-intel-core>=0.1", "architectureMermaid", "置信】", "禁止事项"):
        assert marker in text, f"缺少: {marker}"


def test_template_eight_sections():
    text = (ROOT / "templates" / "ARCHITECTURE_REPORT.template.md").read_text(encoding="utf-8")
    sections = re.findall(r"^## (\d)\.", text, re.MULTILINE)
    assert sections == ["1", "2", "3", "4", "5", "6", "7"]
    assert "附录 A" in text and "纯推测区" in text


def test_system_prompt_iron_rules():
    text = (ROOT / "prompts" / "system.md").read_text(encoding="utf-8")
    for rule in ("据扫描结果推断", "纯推测区", "architectureMermaid", "自检清单"):
        assert rule in text
