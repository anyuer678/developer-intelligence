"""buildRun 推断（TASK-M2-03）：manifest > Makefile > CI > 生态默认（ADR-008）。"""

from __future__ import annotations

import json
import re
from pathlib import Path

from repo_intel.schema.profiles import BuildRun


def _pkg_manager(root: Path) -> tuple[str, str]:
    """(安装命令, 来源证据)。锁文件优先，缺省 npm。"""
    if (root / "pnpm-lock.yaml").is_file():
        return "pnpm install", "pnpm-lock.yaml"
    if (root / "yarn.lock").is_file():
        return "yarn install", "yarn.lock"
    if (root / "package-lock.json").is_file():
        return "npm install", "package-lock.json"
    if (root / "package.json").is_file():
        return "npm install", "package.json 存在(默认)"
    return "", ""


def _makefile_targets(root: Path) -> dict[str, str]:
    """Makefile 目标名 -> 第一条命令。"""
    path = root / "Makefile"
    targets: dict[str, str] = {}
    if not path.is_file():
        return targets
    try:
        current: str | None = None
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
            m = re.match(r"^([a-zA-Z][\w-]*):\s*(?:#.*)?$", line)
            if m:
                current = m.group(1)
                targets.setdefault(current, "")
                continue
            if current and line.startswith("\t") and not targets[current]:
                cmd = line.strip().split("&&")[0].strip()
                if cmd and not cmd.startswith("#"):
                    targets[current] = cmd
    except OSError:
        pass
    return targets


def _ci_commands(root: Path) -> list[str]:
    """.github/workflows/*.yml 中 run: 行的命令集合（宽松正则，不解析 YAML 结构）。"""
    cmds: list[str] = []
    wf = root / ".github" / "workflows"
    if not wf.is_dir():
        return cmds
    for pattern in ("*.yml", "*.yaml"):
        for yml in sorted(wf.glob(pattern)):
            try:
                text = yml.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            for m in re.finditer(r"(?m)^\s*-\s*run:\s*(.+)$", text):
                cmds.append(m.group(1).strip())
    return cmds


def infer_build_run(root: Path, declared_ecosystems: set[str]) -> BuildRun:
    build_system: list[str] = []
    install: list[tuple[str, str]] = []  # (cmd, evidence)
    dev: list[tuple[str, str]] = []
    test: list[tuple[str, str]] = []

    explicit_script = False

    # ---- 源1：package.json scripts ----
    pkg_path = root / "package.json"
    scripts: dict[str, str] = {}
    if pkg_path.is_file():
        build_system.append("node")
        try:
            pkg = json.loads(pkg_path.read_text(encoding="utf-8"))
            scripts = pkg.get("scripts") or {}
        except (OSError, ValueError):
            scripts = {}
        pm_cmd, pm_src = _pkg_manager(root)
        if pm_cmd:
            install.append((pm_cmd, f"锁文件/manifest: {pm_src}"))
        for key, bucket in (("dev", dev), ("start", dev), ("test", test)):
            if key in scripts:
                explicit_script = True
                runner = scripts[key]
                base = pm_cmd.split()[0] + " run" if pm_cmd else "npm run"
                bucket.append((f"{base} {key}", f"package.json scripts.{key}: {runner}".strip()))

    # ---- 源2：Python 生态默认 + Makefile ----
    has_python = (
        bool(declared_ecosystems & {"python", "python-ecosystem"})
        or (root / "pyproject.toml").is_file()
        or (root / "requirements.txt").is_file()
    )
    if has_python:
        build_system.append("python")
        if (root / "requirements.txt").is_file():
            install.append(("pip install -r requirements.txt", "生态默认(python)"))
        if (root / "pyproject.toml").is_file():
            install.append(("pip install -e .", "生态默认(python)"))
        test.append(("pytest", "生态默认(python)"))
        explicit_script = True  # 有 manifest 即视为显式口径

    make_targets = _makefile_targets(root)
    if make_targets:
        build_system.append("make")
        for key, bucket in (("install", install), ("dev", dev), ("test", test)):
            if key in make_targets and make_targets[key]:
                bucket.append((make_targets[key], f"Makefile:{key}"))

    # ---- 源3：CI 佐证 ----
    ci_cmds = _ci_commands(root)
    for cmd in ci_cmds:
        if any(k in cmd.lower() for k in ("install",)):
            install.append((cmd, ".github/workflows run:"))
        elif any(k in cmd.lower() for k in ("test", "pytest", "vitest")):
            test.append((cmd, ".github/workflows run:"))

    # ---- Go 生态默认 ----
    if (root / "go.mod").is_file():
        build_system.append("go-modules")
        install.append(("go mod download", "生态默认(go)"))
        main_pkgs = sorted(
            str(p.parent.relative_to(root)).replace("\\", "/") for p in root.rglob("main.go")
        )
        dev.append(
            (f"go run ./{main_pkgs[0]}" if main_pkgs else "go run ./cmd/app", "生态默认(go)")
        )
        test.append(("go test ./...", "生态默认(go)"))
        explicit_script = True

    def dedupe(items: list[tuple[str, str]]) -> list[str]:
        seen: set[str] = set()
        out: list[str] = []
        for cmd, _src in items:
            if cmd and cmd not in seen:
                seen.add(cmd)
                out.append(cmd)
        return out

    confidence = 0.9 if explicit_script else 0.5
    all_sources = [src for _, src in [*install, *dev, *test]]
    evidence = sorted({s.split("(")[0].strip() for s in all_sources})[:6]

    return BuildRun(
        build_system=build_system,
        install_cmd=dedupe(install),
        dev_cmd=dedupe(dev),
        test_cmd=dedupe(test),
        confidence=confidence,
        evidence=evidence,
    )
