"""pgi CLI 门面冒烟。"""

from __future__ import annotations

import sqlite3

from pgi.cli import main


def test_init_creates_db_and_reports(tmp_path, capsys):
    db = tmp_path / "t.db"
    assert main(["init", "--db", str(db)]) == 0
    out = capsys.readouterr().out
    assert "schema v1" in out and "repos" in out
    # 幂等
    assert main(["init", "--db", str(db)]) == 0
    c = sqlite3.connect(str(db))
    assert c.execute("PRAGMA user_version").fetchone()[0] == 1
