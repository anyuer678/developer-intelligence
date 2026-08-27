"""TASK-M0-05 验收：语言识别三级信号。"""

from __future__ import annotations

from repo_intel.detect.language import (
    ECOSYSTEM_LANG,
    LanguageRules,
    classify_extension,
    shebang_language,
)
from repo_intel.rules.loader import languages_rules


def _rules() -> LanguageRules:
    return LanguageRules(languages_rules())


def test_code_extension_classified():
    lang, is_data = classify_extension(_rules(), ".py")
    assert lang == "python"
    assert is_data is False


def test_data_extension_flagged():
    lang, is_data = classify_extension(_rules(), ".md")
    assert lang is None
    assert is_data is True


def test_unknown_extension_is_neither():
    assert classify_extension(_rules(), ".xyz42") == (None, False)


def test_shebang_python_hit():
    rules = _rules()
    hit = shebang_language(rules, b"#!/usr/bin/env python3\n")
    assert hit == "python"


def test_shebang_bash_hit():
    assert shebang_language(_rules(), b"#!/bin/bash\n") == "shell"


def test_shebang_node_maps_to_javascript():
    assert shebang_language(_rules(), b"#!/usr/bin/env node\n") == "javascript"
    assert ECOSYSTEM_LANG["node-ecosystem"] == "javascript"


def test_shebang_non_shebang_line_misses():
    assert shebang_language(_rules(), b"echo hi\n") is None
