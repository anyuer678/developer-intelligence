"""B 线测试公共设施：构造迷你仓库树（与 core fixture 同思路，独立实现保持零耦合）。"""

from __future__ import annotations

from pathlib import Path


def build_mini(root: Path) -> Path:
    repo = root / "mini"
    repo.mkdir(parents=True)
    (repo / ".repointelignore").write_text("secret.txt\n", encoding="utf-8")
    (repo / "README.md").write_text("# mini\n", encoding="utf-8")
    (repo / "package.json").write_text(
        '{"scripts": {"dev": "vite"}, "dependencies": {"vue": "^3.4.0"}}',
        encoding="utf-8",
    )
    (repo / "app.py").write_text("x = 1\ny = 2\n", encoding="utf-8")
    (repo / "run").write_text("#!/usr/bin/env bash\necho hi\n", encoding="utf-8")
    src = repo / "src"
    src.mkdir()
    (src / "index.ts").write_text("export {};\nexport {};\nexport {};\n", encoding="utf-8")
    nm = repo / "node_modules" / "x"
    nm.mkdir(parents=True)
    (nm / "i.js").write_text("bad()\n")
    (repo / "secret.txt").write_text("token", encoding="utf-8")
    return repo
