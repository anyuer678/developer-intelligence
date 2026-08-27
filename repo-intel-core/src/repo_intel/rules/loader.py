"""yaml 规则表 loader。

规则表随包分发（package data）；缺失或损坏属于安装损坏，直接抛错是合法行为——
"永远部分成功"原则约束的是对用户仓库的扫描，不含引擎自身资源。
"""

from __future__ import annotations

from functools import cache
from pathlib import Path
from typing import Any

import yaml

_RULES_DIR = Path(__file__).parent


@cache
def load(name: str) -> dict[str, Any]:
    """读取包内 rules/<name>.yaml。name 不含扩展名。"""
    path = _RULES_DIR / f"{name}.yaml"
    if not path.is_file():  # pragma: no cover - 随包分发，正常安装不会缺
        raise RuntimeError(f"内置规则表缺失: {path}")
    with path.open("r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh)
    if not isinstance(data, dict):
        raise RuntimeError(f"规则表格式错误(应为映射): {path}")
    return data


def languages_rules() -> dict[str, Any]:
    return load("languages")


def excludes_rules() -> dict[str, Any]:
    return load("excludes")
