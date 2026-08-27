"""结构扫描与规模统计（TASK-M0-06）。"""

from __future__ import annotations

from dataclasses import dataclass, field

ROOT_BUCKET = "(root)"


@dataclass
class TopDirAgg:
    file_count: int = 0
    has_main_file: bool = False  # basename 以 main. 开头
    has_pkg_json: bool = False
    has_ui_code: bool = False  # 存在 .vue/.ts/.tsx/.js/.jsx 源文件
    child_dirs: set[str] = field(default_factory=set)

    def role(self) -> str | None:
        if self.has_main_file:
            return "guessed-entry"
        if self.has_pkg_json and self.has_ui_code:
            return "guessed-frontend"
        return None


class StructureAggregator:
    """按顶层目录聚合文件数，并收集角色判定所需信号。"""

    def __init__(self) -> None:
        self.top_dirs: dict[str, TopDirAgg] = {}
        self.root_files = 0

    def add_file(self, rel_parts: list[str], name: str) -> None:
        if len(rel_parts) == 1:
            self.root_files += 1
            return
        top = rel_parts[0]
        agg = self.top_dirs.setdefault(top, TopDirAgg())
        agg.file_count += 1
        lower = name.lower()
        if lower.startswith("main."):
            agg.has_main_file = True
        if lower == "package.json":
            agg.has_pkg_json = True
        if lower.endswith((".vue", ".ts", ".tsx", ".js", ".jsx")):
            agg.has_ui_code = True
        # 记录中间目录名（供前端项目 src/app 判断等后续扩展）
        if len(rel_parts) >= 3:
            agg.child_dirs.add(rel_parts[1])

    def finalize(self) -> tuple[list[tuple[str, int, str | None]], int]:
        """返回 [(目录名, 文件数, 角色)]（按文件数降序）与根级文件数。"""
        rows = [
            (name, agg.file_count, agg.role())
            for name, agg in sorted(
                self.top_dirs.items(),
                key=lambda kv: (-kv[1].file_count, kv[0]),
            )
        ]
        return rows, self.root_files


def count_lines(data: bytes) -> int:
    """行数 = \n 个数 + 末尾无换行的残行；空文件为 0。"""
    if not data:
        return 0
    n = data.count(b"\n")
    if not data.endswith(b"\n"):
        n += 1
    return n
