"""M4-02 验收：pom.xml 解析 + EOL 规则表。"""

from __future__ import annotations

from pathlib import Path

from repo_intel.detect.extdeps import collect_declared, parse_external_deps

_POM = """<?xml version="1.0"?>
<project>
  <parent><groupId>org.demo</groupId><artifactId>parent</artifactId><version>9.9</version></parent>
  <artifactId>app</artifactId>
  <version>1.2.3</version>
  <dependencyManagement>
    <dependencies>
      <dependency><groupId>org.managed</groupId><artifactId>bom-only</artifactId><version>1.0</version></dependency>
    </dependencies>
  </dependencyManagement>
  <dependencies>
    <dependency><groupId>org.springframework.boot</groupId><artifactId>spring-boot-starter-web</artifactId><version>2.5.14</version></dependency>
    <dependency><groupId>com.example</groupId><artifactId>inherit</artifactId></dependency>
    <dependency><groupId>com.example</groupId><artifactId>dup</artifactId><version>1.0</version></dependency>
    <dependency><groupId>com.example</groupId><artifactId>dup</artifactId><version>1.0</version></dependency>
  </dependencies>
</project>
"""


def _repo_with(pom: str | None = None) -> Path:
    import tempfile

    root = Path(tempfile.mkdtemp())
    if pom is not None:
        (root / "pom.xml").write_text(pom, encoding="utf-8")
    return root


def test_pom_direct_deps_with_management_and_parent_stripped():
    declared = collect_declared(_repo_with(_POM))
    assert "org.springframework.boot:spring-boot-starter-web" in declared
    assert "com.example:inherit" in declared
    # dependencyManagement 内的 BOM 不算直接依赖；parent 版本不串
    assert not any("bom-only" in k for k in declared)
    assert declared["com.example:inherit"][0] == "1.2.3"  # 继承 project 版本


def test_pom_dedup_and_version_fallback():
    deps = parse_external_deps(_repo_with(_POM))
    names = [d.name for d in deps if d.name.startswith("com.example")]
    assert names.count("com.example:dup") == 1


def test_eol_spring_boot_25_high(tmp_path):
    root = _repo_with(
        "<project><dependencies><dependency>"
        "<groupId>org.springframework.boot</groupId>"
        "<artifactId>spring-boot-starter-web</artifactId>"
        "<version>2.5.14</version></dependency></dependencies></project>",
    )
    deps = parse_external_deps(root)
    hit = next(d for d in deps if d.name.endswith("spring-boot-starter-web"))
    assert hit.risk == "HIGH"
    assert "EOL" in (hit.risk_reason or "")


def test_eol_no_match_no_claim(tmp_path):
    root = _repo_with(
        "<project><dependencies><dependency>"
        "<groupId>org.springframework.boot</groupId>"
        "<artifactId>spring-boot-starter-web</artifactId>"
        "<version>3.2.0</version></dependency></dependencies></project>",
    )
    deps = parse_external_deps(root)
    assert all(d.risk is None for d in deps)  # 不误报原则


def test_npm_vue2_cleaned_version_matches(tmp_path):
    root = tmp_path
    (root / "package.json").write_text(
        '{"dependencies": {"vue": "^2.6.14"}}',
        encoding="utf-8",
    )
    deps = parse_external_deps(root)
    vue = next(d for d in deps if d.name == "vue")
    assert vue.risk == "HIGH" and "Vue 2" in (vue.risk_reason or "")
