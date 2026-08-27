"""再生 golden 基线快照（TASK-M3-04）。

用法: python scripts/update-golden.py
变更输出属有意行为时使用；diff 必须人工 review 后与 schema/代码同一 PR 提交。
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def main() -> int:
    env = dict(os.environ)
    env["REPO_INTEL_UPDATE_GOLDEN"] = "1"
    proc = subprocess.run(
        [sys.executable, "-m", "pytest", "tests/test_golden.py", "-q"],
        cwd=ROOT,
        env=env,
    )
    if proc.returncode == 0:
        print("golden 已再生。请 git diff tests/golden/ 逐行 review 后提交。")
    return proc.returncode


if __name__ == "__main__":
    sys.exit(main())
