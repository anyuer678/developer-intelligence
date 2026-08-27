"""测试公共设施：内存构造迷你仓库树。"""

from __future__ import annotations

import json
from pathlib import Path

import pytest


def build_polyglot(root: Path) -> Path:
    """Go + Python + TS + Vue 混合仓库，埋入排除陷阱。

    预期（供各测试断言）：
    - go:      2 files / 33 loc   (cmd/server/main.go=3, pkg/util/util.go=30)
    - python:  1 file  / 10 loc
    - ts:      1 file  / 20 loc
    - vue:     1 file  / 1 loc
    - shell:   1 file  / 2 loc    (无扩展名, shebang 命中)
    - total_files = 11；data_files = 2 (README.md, docs/guide.md)
    - 排除生效: node_modules / dist/*.min.js / secret.txt / docs/internal/
    - warning: MIXED_MONOREPO (go.mod + package.json)
    - role: cmd -> guessed-entry；config_files 含 README.md/go.mod/package.json
    """
    repo = root / "demo-polyglot"
    repo.mkdir(parents=True)

    (repo / ".repointelignore").write_text(
        "# 引擎忽略示例\nsecret.txt\ndocs/internal/\n",
        encoding="utf-8",
    )
    (repo / "README.md").write_text("# demo\n", encoding="utf-8")
    (repo / "go.mod").write_text("module demo\n\ngo 1.22\n", encoding="utf-8")
    (repo / "package.json").write_text(
        '{"name": "demo", "scripts": {"dev": "vite"}, "dependencies": {"vue": "^3.4.0"}}',
        encoding="utf-8",
    )

    cmd = repo / "cmd" / "server"
    cmd.mkdir(parents=True)
    (cmd / "main.go").write_text("package main\n\nfunc main() {}\n", encoding="utf-8")

    util = repo / "pkg" / "util"
    util.mkdir(parents=True)
    (util / "util.go").write_text(
        "package util\n\n" + "".join(f"// line {i}\n" for i in range(28)),
        encoding="utf-8",
    )

    src = repo / "src"
    src.mkdir()
    (src / "index.ts").write_text("export {};\n" * 20, encoding="utf-8")
    (src / "App.vue").write_text("<template><div/></template>\n", encoding="utf-8")

    (repo / "app.py").write_text(
        "".join(f"x = {i}\n" for i in range(10)),
        encoding="utf-8",
    )
    (repo / "run").write_text("#!/usr/bin/env bash\necho hi\n", encoding="utf-8")

    nm = repo / "node_modules" / "leftpad"
    nm.mkdir(parents=True)
    (nm / "index.js").write_text("module.exports = 0;\n" * 50, encoding="utf-8")

    dist = repo / "dist"
    dist.mkdir()
    (dist / "bundle.min.js").write_text("x", encoding="utf-8")

    docs = repo / "docs"
    docs.mkdir()
    (docs / "guide.md").write_text("# guide\n", encoding="utf-8")
    internal = docs / "internal"
    internal.mkdir()
    (internal / "secret-notes.md").write_text("x", encoding="utf-8")

    (repo / "secret.txt").write_text("token", encoding="utf-8")
    return repo


@pytest.fixture(scope="session")
def polyglot_root(tmp_path_factory: pytest.TempPathFactory) -> Path:
    return build_polyglot(tmp_path_factory.mktemp("scan"))


@pytest.fixture(scope="session")
def profile(polyglot_root: Path):
    from repo_intel.scanner import scan_repo

    return scan_repo(polyglot_root)


@pytest.fixture(scope="session")
def profile_json(profile) -> dict:
    return json.loads(profile.model_dump_json(by_alias=True))


def build_graph_repo(root: Path) -> Path:
    """M1 集成 fixture：三语言导入 + 入口点 + 外部依赖，一仓打尽。

    预期（供测试断言）：
    - 边: (root)->tools w1 · cmd->internal w1 · bin->src w1
    - 模块 8 个: (root) cmd internal tools bin src web core
    - cohesion: (root)/cmd/bin = 0.0；无导入模块 = None
    - entrypoints: go-main(0.9) > fastapi/node-bin/vue-gui(0.85) > python-__main__(0.8)
    - extdeps: github.com/x/y(runtime v1.2.3) · vue(runtime ^3.4.0) · vitest(dev ^1.2.0)
    """
    repo = root / "demo-graph"
    repo.mkdir(parents=True)

    (repo / "go.mod").write_text(
        "module demo\n\ngo 1.22\n\nrequire github.com/x/y v1.2.3\n",
        encoding="utf-8",
    )
    cmd = repo / "cmd" / "server"
    cmd.mkdir(parents=True)
    (cmd / "main.go").write_text(
        'package main\n\nimport (\n\t"demo/internal/auth"\n)\n\nfunc main() {\n\tauth.Check()\n}\n',
        encoding="utf-8",
    )
    auth = repo / "internal" / "auth"
    auth.mkdir(parents=True)
    (auth / "auth.go").write_text("package auth\n\nfunc Check() {}\n", encoding="utf-8")

    (repo / "app.py").write_text(
        "from fastapi import FastAPI\n"
        "from tools.helper import helper_fn\n\n"
        "app = FastAPI()\n\n"
        'if __name__ == "__main__":\n    app.run()\n',
        encoding="utf-8",
    )
    tools = repo / "tools"
    tools.mkdir()
    (tools / "helper.py").write_text("def helper_fn():\n    return 1\n", encoding="utf-8")

    (repo / "package.json").write_text(
        '{"name": "g", "bin": "./bin/cli.js", '
        '"dependencies": {"vue": "^3.4.0"}, '
        '"devDependencies": {"vitest": "^1.2.0"}}',
        encoding="utf-8",
    )
    bin_dir = repo / "bin"
    bin_dir.mkdir()
    (bin_dir / "cli.js").write_text(
        '#!/usr/bin/env node\nrequire("../src/util")\n', encoding="utf-8"
    )
    src = repo / "src"
    src.mkdir()
    (src / "util.js").write_text("export function u() {}\n", encoding="utf-8")

    web = repo / "web"
    web.mkdir()
    (web / "main.ts").write_text(
        "import { createApp } from 'vue'\ncreateApp({})\n",
        encoding="utf-8",
    )
    core = repo / "core"
    core.mkdir()
    (core / "logger.ts").write_text("export const log = () => 0\n", encoding="utf-8")
    return repo


@pytest.fixture(scope="session")
def graph_root(tmp_path_factory: pytest.TempPathFactory) -> Path:
    return build_graph_repo(tmp_path_factory.mktemp("graph"))


@pytest.fixture(scope="session")
def graph_profile(graph_root: Path):
    from repo_intel.scanner import scan_repo

    return scan_repo(graph_root)


@pytest.fixture(scope="session")
def graph_profile_json(graph_profile) -> dict:
    return json.loads(graph_profile.model_dump_json(by_alias=True))


def build_m2_repo(root: Path) -> Path:
    """M2 集成 fixture：框架声明 / Makefile+CI / TODO / 长文件 / 深缩进 / 测试文件。

    预期：
    - frameworks 命中 ≥6：FastAPI/Pydantic/Vue/Express/Vite/Vitest/Pytest
    - buildRun: confidence 0.9；install 含 'pip install -r requirements.txt'；
      dev 含 'npm run dev'；test 同时含 'npm run test' 与 'pytest -q'
    - todos: todo≥2 fixme=0
    - hotspots: app.py long-file + deep-nesting
    - testEvidence: count=1 ratio≈0.25 frameworks 含 pytest
    """
    repo = root / "demo-m2"
    repo.mkdir(parents=True)

    (repo / "requirements.txt").write_text(
        "fastapi==0.110.0\npytest>=8\n",
        encoding="utf-8",
    )
    (repo / "pyproject.toml").write_text(
        '[project]\nname = "m2"\ndependencies = ["pydantic>=2"]\n',
        encoding="utf-8",
    )
    (repo / "package.json").write_text(
        '{"scripts": {"dev": "vite", "test": "vitest"}, '
        '"dependencies": {"vue": "^3.4.0", "express": "^4.19.2", "vite": "^5"}, '
        '"devDependencies": {"vitest": "^1.2.0"}}',
        encoding="utf-8",
    )
    (repo / "Makefile").write_text(
        "install:\n\tpip install -r requirements.txt\n\n"
        "dev:\n\tnpm run dev\n\n"
        "test:\n\tpytest -q\n",
        encoding="utf-8",
    )
    wf = repo / ".github" / "workflows"
    wf.mkdir(parents=True)
    (wf / "ci.yml").write_text(
        "name: ci\non: push\njobs:\n  t:\n    steps:\n"
        "      - run: pip install -r requirements.txt\n"
        "      - run: pytest -q\n",
        encoding="utf-8",
    )

    body = "".join(f"# pad line {i}\n" for i in range(415))
    (repo / "app.py").write_text(
        "# TODO refactor soon\n"
        "from fastapi import FastAPI\n\n"
        f"app = FastAPI()\n{body}"
        "if True:\n" + " " * 28 + "pass\n",
        encoding="utf-8",
    )
    src = repo / "src"
    src.mkdir()
    (src / "index.ts").write_text(
        "import { createApp } from 'vue'\ncreateApp({})\n", encoding="utf-8"
    )
    (src / "utils.js").write_text(
        "// TODO fix later\nexport const u = () => ({})\n", encoding="utf-8"
    )
    tests_dir = repo / "tests"
    tests_dir.mkdir()
    (tests_dir / "test_app.py").write_text("def test_x():\n    assert True\n", encoding="utf-8")
    return repo


@pytest.fixture(scope="session")
def m2_root(tmp_path_factory: pytest.TempPathFactory) -> Path:
    return build_m2_repo(tmp_path_factory.mktemp("m2"))


@pytest.fixture(scope="session")
def m2_profile(m2_root: Path):
    from repo_intel.scanner import scan_repo

    return scan_repo(m2_root)


@pytest.fixture(scope="session")
def m2_profile_json(m2_profile) -> dict:
    return json.loads(m2_profile.model_dump_json(by_alias=True))


def _git_run(repo: Path, *args: str, date: str | None = None) -> None:
    import os
    import subprocess

    env = dict(os.environ)
    if date:
        stamp = f"{date}T10:00:00"
        env["GIT_AUTHOR_DATE"] = stamp
        env["GIT_COMMITTER_DATE"] = stamp
    subprocess.run(
        ["git", "-C", str(repo), *args],
        check=True,
        capture_output=True,
        env=env,
    )


def build_git_repo(root: Path) -> Path:
    """两个月份、两次提交的真实 git 仓库（M3 fixture）。

    预期：
    - commits=2 contributors=1 months={2026-06:1, 2026-08:1}
    - month2 new_dirs 含 web；deps_added 含 vue（package.json 月间增量）
    """
    repo = root / "demo-git"
    repo.mkdir(parents=True)
    _git_run(repo, "init", "-q", "-b", "main")
    _git_run(repo, "config", "user.email", "t@example.com")
    _git_run(repo, "config", "user.name", "tester")

    (repo / "README.md").write_text("# g\n", encoding="utf-8")
    (repo / "package.json").write_text(
        '{"dependencies": {"express": "^4.19.0"}}',
        encoding="utf-8",
    )
    src = repo / "src"
    src.mkdir()
    (src / "index.js").write_text("export {};\n", encoding="utf-8")
    _git_run(repo, "add", "-A", date="2026-06-15")
    _git_run(repo, "commit", "-qm", "feat: initial scaffold", date="2026-06-15")

    web = repo / "web"
    web.mkdir()
    (web / "main.ts").write_text("console.log(1)\n", encoding="utf-8")
    (repo / "package.json").write_text(
        '{"dependencies": {"express": "^4.19.0", "vue": "^3.4.0"}}',
        encoding="utf-8",
    )
    _git_run(repo, "add", "-A", date="2026-08-20")
    _git_run(repo, "commit", "-qm", "feat(web): add vue entry", date="2026-08-20")
    return repo


@pytest.fixture(scope="session")
def git_root(tmp_path_factory: pytest.TempPathFactory) -> Path:
    return build_git_repo(tmp_path_factory.mktemp("git"))
