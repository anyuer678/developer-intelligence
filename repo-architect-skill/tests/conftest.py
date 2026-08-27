"""架构师 Skill 测试设施：构造带跨模块导入的迷你仓库。"""

from __future__ import annotations

from pathlib import Path


def build_arch_repo(root: Path) -> Path:
    repo = root / "arch-demo"
    repo.mkdir(parents=True)
    (repo / "app.py").write_text(
        "from pkgcore.engine import run\n\nif __name__ == '__main__':\n    run()\n",
        encoding="utf-8",
    )
    pkg = repo / "pkgcore"
    pkg.mkdir()
    (pkg / "__init__.py").write_text("", encoding="utf-8")
    (pkg / "engine.py").write_text(
        "from pkgcore import config\n\n"
        "def run():\n"
        "    return config.LIMIT\n",
        encoding="utf-8",
    )
    (pkg / "config.py").write_text("LIMIT = 3\n", encoding="utf-8")
    tests_dir = repo / "tests"
    tests_dir.mkdir()
    (tests_dir / "test_engine.py").write_text(
        "from pkgcore.engine import run\n\n"
        "def test_run():\n"
        "    assert run() == 3\n",
        encoding="utf-8",
    )
    (repo / "pyproject.toml").write_text(
        '[project]\nname = "arch-demo"\ndependencies = ["pydantic>=2"]\n',
        encoding="utf-8",
    )
    return repo
