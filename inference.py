from __future__ import annotations

import os
import runpy
import sys
from pathlib import Path


def main() -> None:
    repo_root = Path(__file__).resolve().parent
    subproject = repo_root / "code-review-env"
    target = subproject / "inference.py"

    if not target.exists():
        raise FileNotFoundError(f"Missing required script: {target}")

    subproject_str = str(subproject)
    if subproject_str not in sys.path:
        sys.path.insert(0, subproject_str)

    os.chdir(subproject)
    runpy.run_path(str(target), run_name="__main__")


if __name__ == "__main__":
    main()
