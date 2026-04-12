from __future__ import annotations

import pathlib
import runpy


def main() -> None:
    root = pathlib.Path(__file__).resolve().parents[1]
    target = root / "code-review-env" / "scripts" / "verify_all.py"
    runpy.run_path(str(target), run_name="__main__")


if __name__ == "__main__":
    main()
