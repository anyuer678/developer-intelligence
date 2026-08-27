#!/usr/bin/env python3
"""repo-onboarding 扫描入口：lite（零依赖内置）/ full（已安装 repo-intel-core）双模式。

用法:
    python scan.py <仓库路径> [-o profile.json] [--mode auto|lite|full] [--pretty]
输出: RepoProfile Schema v1.0 兼容 JSON（lite 为其子集，字段名逐字一致）。
"""

from __future__ import annotations

import argparse
import fnmatch
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

SCHEMA_VERSION = "1.0"
SCAN_VERSION = "0.1.0"
_MAX_FILE_BYTES = 1 * 1024 * 1024  # lite 阈值更保守
_TEXT_LIMIT = 4_000_000

_EXT_LANG = {
    ".py": "python", ".js": "javascript", ".mjs": "javascript", ".cjs": "javascript",
    ".jsx": "javascript", ".ts": "typescript", ".tsx": "typescript", ".vue": "vue",
    ".go": "go", ".rs": "rust", ".java": "java", ".kt": "kotlin", ".rb": "ruby",
    ".php": "php", ".c": "c", ".h": "c", ".cpp": "cpp", ".hpp": "cpp", ".cs": "csharp",
    ".swift": "swift", ".scala": "scala", ".sh": "shell", ".bash": "shell", ".ps1": "powershell",
    ".html": "html", ".css": "css", ".scss": "scss", ".sql": "sql", ".dart": "dart", ".lua": "lua",
}
_DATA_EXT = {".json", ".yaml", ".yml", ".toml", ".ini", ".xml", ".md", ".rst", ".txt",
             ".csv", ".env", ".proto", ".graphql"}
_MANIFESTS = {"go.mod": "go", "package.json": "node-ecosystem", "pyproject.toml": "python-ecosystem",
              "requirements.txt": "python-ecosystem", "Cargo.toml": "rust-ecosystem",
              "pom.xml": "java-ecosystem"}
_ROOT_MARKERS = {"README.md", "LICENSE", "CHANGELOG.md", ".gitignore", "Makefile", "Dockerfile"}
_EXCLUDE_DIRS = {"node_modules", "vendor", "dist", "build", "out", "target", ".git", ".venv",
                 "venv", "__pycache__", ".pytest_cache", ".ruff_cache", "coverage", ".next",
                 ".nuxt", ".idea", ".vscode"}
_EXCLUDE_GLOBS = ["*.min.js", "*.min.css", "*.map", "*.lock", "package-lock.json",
                  "pnpm-lock.yaml", "yarn.lock", "poetry.lock"]
_SHEBANG_LANGS = (("python", "python"), ("bash", "shell"), ("sh", "shell"),
                  ("node", "javascript"))


def _count_lines(data: bytes) -> int:
    if not data:
        return 0
    n = data.count(b"\n")
    return n + (0 if data.endswith(b"\n") else 1)


def _stem_ext(name: str) -> str:
    lower = name.lower()
    dot = lower.rfind(".")
    return lower[dot:] if dot > 0 else ""


def _shebang_lang(first: bytes) -> str | None:
    if not first.startswith(b"#!"):
        return None
    words = [w.rsplit("/", 1)[-1] for w in first.decode("ascii", "ignore").split()]
    for token, lang in _SHEBANG_LANGS:
        if any(w == token or w.startswith(token) for w in words):
            return lang
    return None


def _load_ignore(root: Path) -> list[str]:
    path = root / ".repointelignore"
    if not path.is_file():
        return []
    try:
        return [l.strip() for l in path.read_text(encoding="utf-8", errors="replace").splitlines()
                if l.strip() and not l.strip().startswith("#")]
    except OSError:
        return []


def _ignored(pattern: str, rel: str, name: str) -> bool:
    pat = pattern.rstrip("/")
    if pattern.endswith("/"):
        return rel == pat or rel.startswith(pat + "/") or name == pat
    return (
        fnmatch.fnmatch(rel, pat)
        or fnmatch.fnmatch(name, pat)
        or rel.startswith(pat + "/")
    )


def _walk(root: Path):
    """返回 (code_files{rel:lang}, texts{rel:str}, locs{rel:int}, total_files, data_files,
    config_files, root_ecosystems, big_skipped, read_errors)。"""
    user_patterns = _load_ignore(root)
    code_files: dict[str, str] = {}
    texts: dict[str, str] = {}
    locs: dict[str, int] = {}
    config_files: set[str] = set()
    ecosystems: set[str] = set()
    total_files = data_files = big_skipped = read_errors = 0
    budget = _TEXT_LIMIT

    for dirpath, dirnames, filenames in os.walk(root):
        rel_dir = os.path.relpath(dirpath, root)
        rel_posix_dir = "" if rel_dir == "." else Path(rel_dir).as_posix()
        dirnames[:] = [
            d for d in sorted(dirnames)
            if d not in _EXCLUDE_DIRS
            and not any(_ignored(p, f"{rel_posix_dir}/{d}".strip("/"), d) for p in user_patterns)
        ]
        is_root = not rel_posix_dir
        for fname in sorted(filenames):
            rel = f"{rel_posix_dir}/{fname}" if rel_posix_dir else fname
            full = Path(dirpath) / fname
            if is_root and fname in _MANIFESTS:
                config_files.add(fname)
                ecosystems.add(_MANIFESTS[fname])
            elif is_root and fname in _ROOT_MARKERS:
                config_files.add(fname)
            if any(fnmatch.fnmatch(fname, g) for g in _EXCLUDE_GLOBS):
                continue
            if any(_ignored(p, rel, fname) for p in user_patterns):
                continue
            try:
                size = full.stat().st_size
            except OSError:
                read_errors += 1
                continue
            total_files += 1

            ext = _stem_ext(fname)
            lang = _EXT_LANG.get(ext)
            if lang is None and ext in _DATA_EXT:
                data_files += 1
                continue
            bucket = lang
            if ext == "" and size <= 65536:
                try:
                    with full.open("rb") as fh:
                        hit = _shebang_lang(fh.readline(4096))
                    if hit:
                        bucket = hit
                except OSError:
                    read_errors += 1
            if bucket is None:
                continue

            code_files[rel] = bucket
            if size <= _MAX_FILE_BYTES:
                try:
                    raw = full.read_bytes()
                    locs[rel] = _count_lines(raw)
                    if budget > 0:
                        texts[rel] = raw.decode("utf-8", errors="replace")
                        budget -= len(raw)
                except OSError:
                    read_errors += 1
            else:
                big_skipped += 1

    return (code_files, texts, locs, total_files, data_files,
            sorted(config_files), ecosystems, big_skipped, read_errors)


# ---------------------------------------------------------------- lite 各块


def _lite_entrypoints(code_files, texts, root: Path) -> list[dict]:
    hits: list[dict] = []

    def add(rel: str, etype: str, evidence: str, conf: float) -> None:
        hits.append({"file": rel, "type": etype, "confidence": conf, "evidence": [evidence]})

    pkg_path = root / "package.json"
    if pkg_path.is_file():
        try:
            pkg = json.loads(pkg_path.read_text(encoding="utf-8"))
            bin_field = pkg.get("bin")
            targets = [bin_field] if isinstance(bin_field, str) else \
                list((bin_field or {}).values()) if isinstance(bin_field, dict) else []
            for target in targets:
                rel = str(target).replace("\\", "/").lstrip("./")
                if (root / rel).is_file():
                    add(rel, "cli", f"package.json bin -> {target}", 0.85)
        except (OSError, ValueError):
            pass
    for rel, text in sorted(texts.items()):
        lang = code_files.get(rel, "")
        if lang == "python" and "__main__" in text:
            add(rel, "cli", "content: __main__", 0.8)
        elif lang == "python" and "FastAPI(" in text:
            add(rel, "server", "content: FastAPI(", 0.85)
        elif lang == "go" and "package main" in text and "func main(" in text:
            add(rel, "cli", "content: package main + func main(", 0.9)
        elif lang in ("typescript", "javascript", "vue") and "createApp(" in text:
            add(rel, "gui", "content: createApp(", 0.85)
    hits.sort(key=lambda h: (-h["confidence"], h["file"]))
    return hits


def _lite_build_run(root: Path, scripts: dict[str, str]) -> dict:
    install, dev, test = [], [], []

    def pm_base() -> str:
        if (root / "pnpm-lock.yaml").is_file():
            return "pnpm"
        if (root / "yarn.lock").is_file():
            return "yarn"
        return "npm"

    if scripts:
        base = f"{pm_base()} run"
        if "dev" in scripts:
            dev.append(f"{base} dev")
        if "test" in scripts:
            test.append(f"{base} test")
        install.append(f"{pm_base()} install")
    makefile = root / "Makefile"
    if makefile.is_file():
        try:
            for line in makefile.read_text(encoding="utf-8", errors="replace").splitlines():
                m = {"install": install, "dev": dev, "test": test}
                key = line.split(":", 1)[0].strip()
                if key in m:
                    m[key].append(key)  # 目标名占位，命令由调用方 LLM 结合上下文说明
        except OSError:
            pass
    if (root / "requirements.txt").is_file() or (root / "pyproject.toml").is_file():
        install.append("pip install -r requirements.txt" if (root / "requirements.txt").is_file()
                       else "pip install -e .")
        test.append("pytest")
    if (root / "go.mod").is_file():
        install.append("go mod download")
        test.append("go test ./...")

    def dedupe(items: list[str]) -> list[str]:
        out: list[str] = []
        for item in items:
            if item and item not in out:
                out.append(item)
        return out

    return {
        "buildSystem": sorted({s for s in
                               (["node"] if scripts else []) +
                               (["python"] if (root / "requirements.txt").is_file() or
                                (root / "pyproject.toml").is_file() else []) +
                               (["go-modules"] if (root / "go.mod").is_file() else [])}),
        "installCmd": dedupe(install),
        "devCmd": dedupe(dev),
        "testCmd": dedupe(test),
        "confidence": 0.6,
        "evidence": ["lite 模式推断，置信度固定 0.6"],
    }


def lite_scan(root_str: str) -> dict:
    root = Path(root_str).resolve()
    if not root.is_dir():
        raise NotADirectoryError(f"不是有效目录: {root}")

    (code_files, texts, locs, total_files, _data_files,
     config_files, ecosystems, big_skipped, read_errors) = _walk(root)

    warnings = [{"code": "SCAN_MODE", "detail": "lite"}]
    if len(ecosystems) >= 2:
        warnings.append({"code": "MIXED_MONOREPO",
                         "detail": f"多生态 manifest 共存: {', '.join(sorted(ecosystems))}"})
    if big_skipped:
        warnings.append({"code": "BIG_FILE_SKIPPED", "detail": f"{big_skipped} 个文件未解析"})
    if read_errors:
        warnings.append({"code": "READ_ERRORS", "detail": f"{read_errors} 个文件读取失败"})
    if total_files == 0:
        warnings.append({"code": "EMPTY_REPO", "detail": "未发现任何文件"})

    total_loc = max(sum(locs.values()), 1)
    langs = [
        {"name": name, "pct": round(loc * 100.0 / total_loc, 1),
         "files": sum(1 for r, l in code_files.items() if l == name), "loc": loc}
        for name, loc in ((n, sum(v for r, v in locs.items() if code_files[r] == n))
                          for n in sorted(set(code_files.values())))
    ]
    langs = [l for l in langs if l["loc"] > 0]
    langs.sort(key=lambda s: (-s["loc"], s["name"]))

    top_counts: dict[str, int] = {}
    for rel in code_files:
        top = rel.split("/", 1)[0]
        top_counts[top] = top_counts.get(top, 0) + 1
    structure = {
        "topLevelDirs": [{"path": k, "fileCount": v, "role": None}
                         for k, v in sorted(top_counts.items(), key=lambda kv: (-kv[1], kv[0]))],
        "configFiles": config_files,
    }
    largest = sorted(
        ({"path": rel, "loc": loc} for rel, loc in locs.items()),
        key=lambda x: (-x["loc"], x["path"]),
    )[:5]

    return {
        "schemaVersion": SCHEMA_VERSION,
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "tool": {"name": "repo-onboarding-scan", "version": SCAN_VERSION},
        "repo": {"path": str(root), "name": root.name, "vcs": None},
        "languages": langs,
        "structure": structure,
        "metrics": {"totalLoc": total_loc, "totalFiles": total_files, "largestFiles": largest},
        "warnings": warnings,
        "entryPoints": _lite_entrypoints(code_files, texts, root),
        "modules": None,
        "dependencyGraph": None,
        "frameworks": None,
        "buildRun": _lite_build_run(root, _read_scripts(root)),
        "git": None,
    }


def _read_scripts(root: Path) -> dict:
    pkg_path = root / "package.json"
    if pkg_path.is_file():
        try:
            pkg = json.loads(pkg_path.read_text(encoding="utf-8"))
            return pkg.get("scripts") or {}
        except (OSError, ValueError):
            return {}
    return {}


# ---------------------------------------------------------------- 双模式调度


def choose_backend(force: str) -> str:
    if force != "auto":
        return force
    import importlib.util

    return "full" if importlib.util.find_spec("repo_intel") else "lite"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="onboarding-scan")
    sub = parser.add_subparsers(dest="command", required=True)
    scan = sub.add_parser("scan")
    scan.add_argument("path")
    scan.add_argument("-o", "--output")
    scan.add_argument("--mode", choices=["auto", "lite", "full"], default="auto")
    scan.add_argument("--pretty", action="store_true")
    scan.add_argument(
        "--debug",
        action="store_true",
        help="将完整 JSON 原文输出到 stderr（供 issue 反馈附贴）",
    )
    args = parser.parse_args(argv)

    backend = choose_backend(args.mode)
    try:
        if backend == "full":
            from repo_intel.scanner import scan_repo  # type: ignore

            profile = scan_repo(args.path)
            payload = json.loads(profile.model_dump_json(by_alias=True))
            modes = {w["detail"] for w in payload.get("warnings", []) if w["code"] == "SCAN_MODE"}
            if "full" not in modes:
                payload.setdefault("warnings", []).append(
                    {"code": "SCAN_MODE", "detail": "full"})
        else:
            payload = lite_scan(args.path)
    except NotADirectoryError as exc:
        print(f"错误: {exc}", file=sys.stderr)
        return 2

    text = json.dumps(payload, ensure_ascii=False, indent=2 if args.pretty else None)
    if args.debug:
        # issue 反馈通道：完整 JSON 走 stderr，不污染正常输出
        print(text, file=sys.stderr)
    if args.output:
        Path(args.output).write_text(text + "\n", encoding="utf-8")
        print(f"已写入 {args.output}")
    else:
        print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
