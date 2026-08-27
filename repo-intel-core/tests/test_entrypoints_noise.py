"""M3 自举回归：入口点跳过测试文件；buildRun 不推荐不存在的安装来源。"""

from __future__ import annotations

from repo_intel.detect.buildrun import infer_build_run
from repo_intel.detect.entrypoints import detect_entrypoints


def test_entrypoints_skip_tests_dir(tmp_path):
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "conftest.py").write_text(
        "app = FastAPI()\nif __name__ == '__main__':\n    pass\n",
        encoding="utf-8",
    )
    (tmp_path / "scripts").mkdir()
    (tmp_path / "scripts" / "tool.py").write_text(
        "if __name__ == '__main__':\n    pass\n",
        encoding="utf-8",
    )
    texts = {
        "tests/conftest.py": ("python", "app = FastAPI()\nif __name__: pass\n"),
        "scripts/tool.py": ("python", "if __name__ == '__main__':\n    pass\n"),
    }
    hits = detect_entrypoints(texts, tmp_path)
    files = [h.file for h in hits]
    assert "scripts/tool.py" in files
    assert all(not f.startswith("tests/") for f in files)


def test_install_cmd_only_existing_sources(tmp_path):
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "x"\ndependencies = ["pydantic>=2"]\n',
        encoding="utf-8",
    )
    br = infer_build_run(tmp_path, {"python-ecosystem"})
    assert "pip install -e ." in br.install_cmd
    assert "pip install -r requirements.txt" not in br.install_cmd  # 文件不存在不推荐


def test_install_cmd_prefers_requirements_when_present(tmp_path):
    (tmp_path / "requirements.txt").write_text("fastapi==0.110.0\n", encoding="utf-8")
    (tmp_path / "pyproject.toml").write_text('[project]\nname = "x"\n', encoding="utf-8")
    br = infer_build_run(tmp_path, {"python-ecosystem"})
    assert "pip install -r requirements.txt" in br.install_cmd
