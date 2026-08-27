"""TASK-M1-04 验收：JS/TS/Vue 导入提取。"""

from __future__ import annotations

from repo_intel.detect.imports import extract_js


def test_static_import_from():
    text = "import { a } from './a'\nimport def, { b } from \"../lib/b\"\n"
    assert sorted(extract_js(text)) == ["../lib/b", "./a"]


def test_export_from():
    assert extract_js("export { x } from './x'\n") == ["./x"]


def test_require_call():
    assert extract_js("const p = require('../src/util')\n") == ["../src/util"]


def test_dynamic_import():
    assert extract_js("const m = await import('./lazy')\n") == ["./lazy"]


def test_bare_package_specifier_preserved():
    assert extract_js("import { createApp } from 'vue'\n") == ["vue"]


def test_vue_sfc_whole_text_matches_script_imports():
    text = "<template><div/></template>\n<script setup>\nimport x from './x'\n</script>\n"
    assert "./x" in extract_js(text)
