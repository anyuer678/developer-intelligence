"""语言识别（TASK-M0-05）：扩展名统计 → manifest 信号 → shebang 指纹。"""

from __future__ import annotations

from pathlib import PurePosixPath

# 生态信号 → 归入统计的展示语言（shebang/manifest 命中生态时使用）
ECOSYSTEM_LANG: dict[str, str] = {
    "node-ecosystem": "javascript",
}


class LanguageRules:
    def __init__(self, raw: dict) -> None:
        self.ext_lang: dict[str, str] = {k.lower(): v for k, v in raw.get("extensions", {}).items()}
        self.data_ext: dict[str, str] = {
            k.lower(): v for k, v in raw.get("data_extensions", {}).items()
        }
        self.manifests: dict[str, str] = dict(raw.get("manifests", {}))
        self.monorepo_markers: list[str] = list(raw.get("monorepo_markers", []))
        self.shebangs: dict[str, list[str]] = dict(raw.get("shebangs", {}))
        self.root_markers: list[str] = list(raw.get("root_markers", []))


def classify_extension(rules: LanguageRules, ext: str) -> tuple[str | None, bool]:
    """返回 (代码语言|None, 是否数据类文件)。ext 需已小写且带点。"""
    lang = rules.ext_lang.get(ext)
    if lang:
        return lang, False
    if ext in rules.data_ext:
        return None, True
    return None, False


def shebang_language(rules: LanguageRules, first_line: bytes) -> str | None:
    """无扩展名文件的 shebang 指纹：首行形如 `#! /usr/bin/env python3`。

    匹配规则：对首行每个空白分词取路径末段，token 精确相等或为该段前缀
    （`python3` 命中 `python`；`ipython` 不命中）。
    """
    if not first_line.startswith(b"#!"):
        return None
    try:
        text = first_line.decode("ascii", errors="ignore")
    except Exception:  # noqa: BLE001 - 解码失败按无指纹处理
        return None
    words = [w.rsplit("/", 1)[-1] for w in text.split()]
    for lang, tokens in rules.shebangs.items():
        for token in tokens:
            if any(w == token or w.startswith(token) for w in words):
                return ECOSYSTEM_LANG.get(lang, lang)
    return None


def file_stem_and_ext(name: str) -> tuple[str, str]:
    """小写扩展名（带点）；无扩展名返回 ''。多级扩展取最后一段。"""
    suffix = PurePosixPath(name.lower()).suffix
    return name.lower(), suffix
