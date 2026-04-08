from __future__ import annotations

import importlib
import sys
from pathlib import Path

from fastapi.testclient import TestClient

from db.seed import seed_project


def test_training_api_endpoints(tmp_path: Path, monkeypatch) -> None:
    source_root = Path("sample_project_canonical").resolve()
    db_path = tmp_path / "phase8_training.db"
    seed_project(source_root, db_path=str(db_path), force=True)

    monkeypatch.setenv("GRAPHREVIEW_SOURCE_ROOT", str(source_root))
    monkeypatch.setenv("GRAPHREVIEW_DB_PATH", str(db_path))
    monkeypatch.setenv("GRAPHREVIEW_EDGE_SUMMARY_ENABLED", "false")
    monkeypatch.setenv("GRAPHREVIEW_AGENT_INFERENCE_ENABLED", "false")

    if "server.app" in sys.modules:
        del sys.modules["server.app"]
    server_app = importlib.import_module("server.app")
    app = server_app.app

    client = TestClient(app)

    bootstrap = client.post("/training/bootstrap")
    assert bootstrap.status_code == 200
    payload = bootstrap.json()
    assert payload["weight_path"]

    run_response = client.post(
        "/training/run",
        json={
            "force_seed": False,
            "deterministic_output": str(tmp_path / "phase8_training.jsonl"),
            "regression_tolerance": 1.0,
        },
    )
    assert run_response.status_code == 200
    assert "ok" in run_response.json()

    listed = client.get("/training/runs", params={"limit": 5})
    assert listed.status_code == 200
    rows = listed.json()
    assert isinstance(rows, list)
