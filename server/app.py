from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
from types import ModuleType
from typing import Any


def _load_subproject_server() -> ModuleType:
    repo_root = Path(__file__).resolve().parents[1]
    subproject_root = repo_root / "code-review-env"
    subproject_root_str = str(subproject_root)
    if subproject_root_str not in sys.path:
        sys.path.insert(0, subproject_root_str)

    target = repo_root / "code-review-env" / "server" / "app.py"
    if not target.exists():
        raise FileNotFoundError(f"Missing subproject server module: {target}")

    spec = importlib.util.spec_from_file_location("code_review_env_server_app", target)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load module spec for {target}")

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_subserver = _load_subproject_server()
app: Any = _subserver.app


def main() -> Any:
    return app


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("server.app:app", host="0.0.0.0", port=7860)
