"""TASK-M0-04 验收：排除器（默认清单 + .repointelignore + 大文件降级）。"""

from __future__ import annotations

import json

from repo_intel.scanner import scan_repo


def test_default_and_user_exclusions(profile_json):
    langs = {s["name"] for s in profile_json["languages"]}
    # node_modules 里的 js 与 dist 下的 *.min.js 都不得计入统计来源
    assert profile_json["metrics"]["totalFiles"] == 11
    assert langs == {"go", "typescript", "python", "shell", "vue"}

    top_dirs = {d["path"] for d in profile_json["structure"]["topLevelDirs"]}
    assert "node_modules" not in top_dirs
    assert "dist" not in top_dirs  # 文件全被排除后目录不出现在结果里
    assert "build_docs" not in top_dirs  # .repointelignore 目录模式

    raw = json.dumps(profile_json, ensure_ascii=False)
    assert "leftpad" not in raw
    assert "secret.txt" not in raw
    assert "secret-notes" not in raw  # docs/internal/ 下文件；"internal" 已是依赖图字段名不可作探针


def test_big_file_degrades_to_warning(polyglot_root, monkeypatch):
    import repo_intel.scanner as scanner_mod

    base = scanner_mod.excludes_rules()
    monkeypatch.setattr(
        scanner_mod,
        "excludes_rules",
        lambda: {**base, "max_file_bytes": 64},
        raising=True,
    )
    profile = scan_repo(polyglot_root)
    codes = [w.code for w in profile.warnings]
    assert "BIG_FILE_SKIPPED" in codes
    # 大文件只计数不解析：util.go(~330B)>64B 被跳过，仅 cmd/server/main.go 计行
    go = next(s for s in profile.languages if s.name == "go")
    assert go.files == 2
    assert go.loc == 3
