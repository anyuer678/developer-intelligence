"""TASK-V01-05 验收：SKILL.md / 模板 / prompts 文件 lint。"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def test_skill_frontmatter_complete():
    text = (ROOT / "skill" / "SKILL.md").read_text(encoding="utf-8")
    m = re.match(r"^---\n(.*?)\n---\n", text, re.DOTALL)
    assert m, "SKILL.md 缺少 frontmatter"
    front = m.group(1)
    assert "name: repo-onboarding" in front
    assert "description:" in front and len(front) > 60


def test_skill_workflow_steps_and_hallucination_rules():
    text = (ROOT / "skill" / "SKILL.md").read_text(encoding="utf-8")
    for marker in ("scan.py", "SCAN_MODE", "templates/PROJECT_GUIDE.template.md",
                   "prompts/system.md", "禁止编造"):
        assert marker in text, f"SKILL.md 缺少关键引用: {marker}"


def test_template_has_seven_sections_in_order():
    text = (ROOT / "templates" / "PROJECT_GUIDE.template.md").read_text(encoding="utf-8")
    sections = re.findall(r"^## (\d)\.", text, re.MULTILINE)
    assert sections == ["1", "2", "3", "4", "5", "6", "7"]
    assert "附录 A" in text and "来源" in text


def test_system_prompt_contains_iron_rules():
    text = (ROOT / "prompts" / "system.md").read_text(encoding="utf-8")
    for rule in ("未检测到", "据扫描结果推断", "不得增删一级标题", "自检清单"):
        assert rule in text


def test_user_skeleton_references_prompt_pair():
    text = (ROOT / "prompts" / "user-skeleton.md").read_text(encoding="utf-8")
    assert "prompts/system.md" in text
