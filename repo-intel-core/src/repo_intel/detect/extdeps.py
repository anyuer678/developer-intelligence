"""外部依赖清单（TASK-M1-07）+ Maven 口径 + EOL 规则（M4-02，ADR-005/014）。"""

from __future__ import annotations

import json
import re
import tomllib
from pathlib import Path

from repo_intel.rules.loader import load
from repo_intel.schema.profiles import ExternalDep

_REQ_LINE = re.compile(r"^([A-Za-z0-9][A-Za-z0-9._-]*)\s*([<>=!~^][^;#]*)?\s*$")
_GO_REQUIRE = re.compile(r"(?m)^\s*(?:-\s+)?([A-Za-z0-9_./~-]+)\s+(v\d[\w.\-+]*)\s*$")
_POM_DEP_BLOCK = re.compile(r"<dependency>\s*(.*?)\s*</dependency>", re.DOTALL)
_POM_TAG = re.compile(r"<(\w+)>\s*(.*?)\s*</\1>", re.DOTALL)
_NUM_VERSION = re.compile(r"\d+(?:\.\d+)*")
_URL_PREFIXES = ("git+", "github:", "file:", "http:", "https:")


def _clean_version(v: str | None) -> str | None:
    if v is None:
        return None
    v = v.strip()
    return v or None


def _numeric_version(raw: str | None) -> str | None:
    """EOL 匹配用数值段提取：^2.5.14→2.5.14；git+/file: URL → None（移植 evocode）。"""
    if not raw:
        return None
    s = raw.strip()
    if s.startswith(_URL_PREFIXES):
        return None
    m = _NUM_VERSION.search(s)
    return m.group(0) if m else None


def collect_declared(root: Path) -> dict[str, tuple[str | None, str, str, str]]:
    """根 manifest 声明依赖的统一定义。

    返回: 小写包名 -> (版本原文, 来源标签, kind, 原始大小写包名)
    """
    out: dict[str, tuple[str | None, str, str, str]] = {}

    def put(name: str, ver: str | None, source: str, kind: str) -> None:
        key = name.lower()
        if key not in out:
            out[key] = (_clean_version(ver), source, kind, name)

    # ---- Maven: 根 pom.xml（仅直接依赖；剥离 dependencyManagement/parent，ADR-015）----
    pom = root / "pom.xml"
    if pom.is_file():
        try:
            content = pom.read_text(encoding="utf-8", errors="replace")
        except OSError:
            content = ""
        if content:
            stripped = re.sub(r"<dependencyManagement>[\s\S]*?</dependencyManagement>", "", content)
            stripped = re.sub(r"<parent>[\s\S]*?</parent>", "", stripped)
            pv = re.search(r"<version>\s*(.*?)\s*</version>", stripped)
            project_version = pv.group(1).strip() if pv else None
            seen_pom: set[str] = set()
            for block in _POM_DEP_BLOCK.findall(stripped):
                tags = {m.group(1): m.group(2).strip() for m in _POM_TAG.finditer(block)}
                group, artifact = tags.get("groupId"), tags.get("artifactId")
                if not group or not artifact:
                    continue
                name = f"{group}:{artifact}"
                if name in seen_pom:
                    continue
                seen_pom.add(name)
                put(name, tags.get("version") or project_version, "pom.xml", "runtime")

    pkg_path = root / "package.json"
    if pkg_path.is_file():
        try:
            pkg = json.loads(pkg_path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            pkg = {}
        if isinstance(pkg, dict):
            for name, ver in (pkg.get("dependencies") or {}).items():
                put(str(name), str(ver) if ver is not None else None, "package.json", "runtime")
            for name, ver in (pkg.get("devDependencies") or {}).items():
                put(str(name), str(ver) if ver is not None else None, "package.json", "dev")

    pp = root / "pyproject.toml"
    if pp.is_file():
        try:
            data = tomllib.loads(pp.read_text(encoding="utf-8"))
        except (OSError, tomllib.TOMLDecodeError):
            data = {}
        for entry in ((data.get("project") or {}).get("dependencies")) or []:
            m = _REQ_LINE.match(str(entry).split(";")[0].strip())
            if m:
                put(m.group(1), m.group(2), "pyproject.toml", "runtime")

    req = root / "requirements.txt"
    if req.is_file():
        try:
            for line in req.read_text(encoding="utf-8", errors="replace").splitlines():
                line = line.strip()
                if not line or line.startswith(("#", "-")):
                    continue
                m = _REQ_LINE.match(line.split("#")[0].strip())
                if m:
                    put(m.group(1), m.group(2), "requirements.txt", "runtime")
        except OSError:
            pass

    gomod = root / "go.mod"
    if gomod.is_file():
        try:
            text = gomod.read_text(encoding="utf-8", errors="replace")
        except OSError:
            text = ""
        block = re.search(r"^require\s*\(\n(.*?)^\)", text, re.MULTILINE | re.DOTALL)
        scope_text = block.group(1) if block else ""
        for m in _GO_REQUIRE.finditer(scope_text):
            put(m.group(1), m.group(2), "go.mod", "runtime")
        for m in re.finditer(r"(?m)^require\s+([A-Za-z0-9_./~-]+)\s+(v\d[\w.\-+]*)\s*$", text):
            put(m.group(1), m.group(2), "go.mod", "runtime")

    return out


_SOURCE_ECO = {
    "package.json": "npm",
    "pom.xml": "maven",
    "requirements.txt": "pip",
    "pyproject.toml": "pip",
    "go.mod": "go",
}


def parse_external_deps(root: Path) -> list[ExternalDep]:
    declared = collect_declared(root)
    eol_rules = load("deps_eol").get("rules", [])

    def find_eol(eco: str, name_orig: str, version: str | None) -> tuple[str, str] | None:
        if not version:
            return None
        numeric = _numeric_version(version)
        if not numeric:
            return None
        v = numeric.lower()
        for rule in eol_rules:
            if rule.get("ecosystem") != eco:
                continue
            r_name = str(rule["name"])
            if rule.get("prefix"):
                if not name_orig.startswith(r_name):
                    continue
            elif name_orig.lower() != r_name.lower():
                continue
            if v.startswith(str(rule["version_prefix"])):
                return str(rule.get("risk", "HIGH")), str(rule.get("reason", ""))
        return None

    items: list[ExternalDep] = []
    for _key, (ver, source, kind, orig) in declared.items():
        risk = find_eol(_SOURCE_ECO.get(source, ""), orig, ver)
        items.append(
            ExternalDep(
                name=orig,
                version=ver,
                kind=kind,
                usage_files=0,
                risk=risk[0] if risk else None,
                risk_reason=risk[1] if risk else None,
            ),
        )
    items.sort(key=lambda d: (d.kind or "", d.name.lower()))
    return items


def read_go_module_prefix(root: Path) -> str | None:
    """go.mod 的 module 声明，供 Go 导入剥离前缀用。"""
    gomod = root / "go.mod"
    if not gomod.is_file():
        return None
    try:
        text = gomod.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None
    m = re.search(r"(?m)^module\s+(\S+)\s*$", text)
    return m.group(1) if m else None
