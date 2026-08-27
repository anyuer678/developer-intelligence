"""模块划分与内部依赖图（TASK-M1-06）。

口径（ADR-004/006）：
- 模块 = 含代码文件的顶层目录；散根文件归 "(root)"；
- 外部依赖不在此解析（M1-07 manifest 口径）；相对/仓库内导入才建边。
"""

from __future__ import annotations

import posixpath
from collections import defaultdict

from repo_intel.detect.imports import extract_go, extract_js, extract_py
from repo_intel.schema.profiles import InternalDep, ModuleInfo

ROOT_MODULE = "(root)"

# 参与导入解析的语言桶（其余代码语言计入 files 但不建边）
PARSE_LANGS = {"python", "typescript", "javascript", "vue", "go"}

_JS_EXTS = (".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs", ".vue")


def module_of(rel_posix: str) -> str:
    parts = rel_posix.split("/")
    return parts[0] if len(parts) > 1 else ROOT_MODULE


def _norm(path: str) -> str:
    return posixpath.normpath(path)


class GraphBuilder:
    def __init__(
        self,
        code_files: dict[str, str],
        texts: dict[str, str],
        go_prefix: str | None,
    ) -> None:
        """code_files: rel -> 语言桶；texts: rel -> 源码文本（仅 PARSE_LANGS 且可读者）。"""
        self.code_files = code_files
        self.texts = texts
        self.go_prefix = go_prefix.rstrip("/") if go_prefix else None
        self.dirs: set[str] = set()
        for rel in code_files:
            parts = rel.split("/")[:-1]
            for i in range(1, len(parts) + 1):
                self.dirs.add("/".join(parts[:i]))
        self.intra: dict[str, int] = defaultdict(int)
        self.out: dict[str, int] = defaultdict(int)
        self.edges: dict[tuple[str, str], int] = defaultdict(int)

    # 解析目标 → 仓库内 rel（文件或目录）；None 表示外部/未命中

    def _deepest_dotted(self, dotted: str) -> str | None:
        parts = dotted.split(".")
        for k in range(len(parts), 0, -1):
            path = "/".join(parts[:k])
            if f"{path}.py" in self.code_files or f"{path}/__init__.py" in self.code_files:
                return path
            if path in self.dirs:
                return path
        return None

    def _resolve_py(self, target: str, level: int, src_rel: str) -> str | None:
        if level > 0:
            base_parts = src_rel.split("/")[:-1]
            for _ in range(level - 1):
                if base_parts:
                    base_parts.pop()
            tail = target.strip(".")
            base = "/".join(base_parts)
            joined = f"{base}/{tail}".strip("/") if tail else base
            if not joined:
                return None
            hit = self._deepest_dotted(joined.replace("/", "."))
            return hit
        if target == "":
            return None
        return self._deepest_dotted(target)

    def _resolve_js(self, spec: str, src_rel: str) -> str | None:
        if not spec.startswith("."):
            return None  # 裸包名 = 外部依赖，走 manifest 口径
        base = _norm(posixpath.join(posixpath.dirname(src_rel), spec))
        if base in self.code_files:
            return base
        for ext in _JS_EXTS:
            if f"{base}{ext}" in self.code_files:
                return f"{base}{ext}"
        for ext in _JS_EXTS:
            if f"{base}/index{ext}" in self.code_files:
                return f"{base}/index{ext}"
        if base in self.dirs:
            return base
        return None

    def _resolve_go(self, imp: str) -> str | None:
        p = self.go_prefix
        if not p:
            return None
        if imp == p:
            return ROOT_MODULE
        if imp.startswith(p + "/"):
            rest = imp[len(p) + 1 :]
            if f"{rest}.go" in self.code_files or rest in self.dirs:
                return rest
        return None

    # ---------------- 主流程 ----------------

    def build(self) -> tuple[list[ModuleInfo], list[InternalDep]]:
        for rel in sorted(self.texts):
            lang = self.code_files.get(rel)
            if lang not in PARSE_LANGS:
                continue
            text = self.texts[rel]
            src_mod = module_of(rel)
            if lang == "python":
                targets = (self._resolve_py(t, lvl, rel) for t, lvl in extract_py(text))
            elif lang in ("typescript", "javascript", "vue"):
                targets = (self._resolve_js(s, rel) for s in extract_js(text))
            elif lang == "go":
                targets = (self._resolve_go(s) for s in extract_go(text))
            else:  # pragma: no cover - PARSE_LANGS 已穷举
                continue

            for dst in targets:
                if dst is None:
                    continue
                dst_mod = ROOT_MODULE if dst == ROOT_MODULE else module_of(dst)
                if dst_mod == src_mod:
                    self.intra[src_mod] += 1
                else:
                    self.out[src_mod] += 1
                    self.edges[(src_mod, dst_mod)] += 1

        files_per_mod: dict[str, int] = defaultdict(int)
        for rel, _lang in self.code_files.items():
            files_per_mod[module_of(rel)] += 1

        modules = [
            ModuleInfo(
                name=mod,
                root_path=mod,
                files=files_per_mod.get(mod, 0),
                responsibility=None,
                cohesion_score=self._cohesion(mod),
            )
            for mod in sorted(files_per_mod)
        ]

        internal = [
            InternalDep(frm=a, to=b, weight=w)
            for (a, b), w in sorted(self.edges.items(), key=lambda kv: (-kv[1], kv[0]))
        ]
        return modules, internal

    def _cohesion(self, mod: str) -> float | None:
        total = self.intra.get(mod, 0) + self.out.get(mod, 0)
        if total == 0:
            return None  # 三态：该模块没有内部导入关系可言
        return round(self.intra.get(mod, 0) / total, 2)
