"""TASK-M1-03 验收：Python 导入提取（纯提取层）。"""

from __future__ import annotations

from repo_intel.detect.imports import extract_py


def test_simple_and_dotted_imports():
    text = "import os\nimport a.b, c\n"
    assert ("os", 0) in extract_py(text)
    assert ("a.b", 0) in extract_py(text)
    assert ("c", 0) in extract_py(text)


def test_from_import_with_level():
    text = "from tools.helper import fn\nfrom . import x\nfrom ..pkg.y import z\n"
    out = dict(extract_py(text))
    assert out["tools.helper"] == 0
    assert out[""] == 1  # from . import x：目标就是当前包目录（空尾）
    assert out["pkg.y"] == 2


def test_indented_imports_inside_functions():
    text = "def f():\n    import json\n    return json\n"
    assert ("json", 0) in extract_py(text)


def test_no_false_positive_from_word():
    text = 'value = "import os"\n'  # 字符串内不匹配：锚定行首缩进后紧跟 import
    assert extract_py(text) == [] or all(t != "os" for t, _ in extract_py(text))
