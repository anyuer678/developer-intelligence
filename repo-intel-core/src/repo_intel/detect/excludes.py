"""排除器：默认清单剪枝 + .repointelignore 支持（TASK-M0-04）。"""

from __future__ import annotations

from dataclasses import dataclass, field
from fnmatch import fnmatch
from pathlib import Path


@dataclass
class ExclusionRule:
    dirs: set[str] = field(default_factory=set)
    file_globs: list[str] = field(default_factory=list)
    max_file_bytes: int = 2 * 1024 * 1024
    soft_file_limit: int = 20000
    user_patterns: list[str] = field(default_factory=list)  # 来自 .repointelignore

    @classmethod
    def from_rules(cls, raw: dict) -> ExclusionRule:
        return cls(
            dirs=set(raw.get("dirs", [])),
            file_globs=list(raw.get("file_globs", [])),
            max_file_bytes=int(raw.get("max_file_bytes", 2 * 1024 * 1024)),
            soft_file_limit=int(raw.get("soft_file_limit", 20000)),
        )


def load_repointelignore(root: Path) -> list[str]:
    """解析仓库根的 .repointelignore：一行一个 glob，# 注释，空行忽略。"""
    path = root / ".repointelignore"
    if not path.is_file():
        return []
    patterns: list[str] = []
    try:
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
            line = line.strip()
            if line and not line.startswith("#"):
                patterns.append(line)
    except OSError:
        return []
    return patterns


def _match_pattern(pattern: str, rel_posix: str, name: str) -> bool:
    """单个用户模式匹配：支持文件名 glob、相对路径 glob、目录前缀（`dir/` 或裸目录名）。"""
    pat = pattern.rstrip("/")
    if not pat:
        return False
    if pattern.endswith("/"):
        # 目录模式：命中该目录本身或其下任意路径
        return rel_posix == pat or rel_posix.startswith(pat + "/") or name == pat
    return fnmatch(rel_posix, pat) or fnmatch(name, pat) or rel_posix.startswith(pat + "/")


class Excluder:
    """遍历期判定器：目录剪枝（不下钻）与文件跳过共用。"""

    def __init__(self, root: Path, rule: ExclusionRule) -> None:
        self.root = root
        self.rule = rule
        self.user_patterns = load_repointelignore(root)

    def is_ignored_dir(self, name: str, rel_dir_posix: str) -> bool:
        """rel_dir_posix 为该目录自身的相对路径；根级调用时为 name。"""
        if name in self.rule.dirs:
            return True
        rel = f"{rel_dir_posix}/{name}" if rel_dir_posix else name
        return any(_match_pattern(p, rel, name) for p in self.user_patterns)

    def is_ignored_file(self, rel_posix: str, name: str) -> bool:
        if any(fnmatch(name, g) or fnmatch(rel_posix, g) for g in self.rule.file_globs):
            return True
        return any(_match_pattern(p, rel_posix, name) for p in self.user_patterns)
