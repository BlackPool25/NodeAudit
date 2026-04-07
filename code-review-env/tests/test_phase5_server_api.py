from __future__ import annotations

import importlib
import sys
from pathlib import Path

from fastapi.testclient import TestClient

from db.seed import seed_project


def test_reports_generate_endpoint(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("GRAPHREVIEW_JUDGE_ENABLED", "false")

    source_root = Path("sample_project").resolve()
    db_path = tmp_path / "phase5_api.db"
    seed_project(source_root, db_path=str(db_path), force=True)

    monkeypatch.setenv("GRAPHREVIEW_SOURCE_ROOT", str(source_root))
    monkeypatch.setenv("GRAPHREVIEW_DB_PATH", str(db_path))

    if "server.app" in sys.modules:
        del sys.modules["server.app"]
    server_app = importlib.import_module("server.app")
    app = server_app.app

    client = TestClient(app)
    response = client.post(
        "/reports/generate",
        json={"module_override": ["checkout"], "hops": 1, "output_dir": str(tmp_path / "api_outputs")},
    )

    assert response.status_code == 200
    payload = response.json()["artifacts"]
    assert Path(payload["markdown_path"]).exists()
    assert Path(payload["json_path"]).exists()
    assert Path(payload["html_path"]).exists()
    assert 0.0 <= payload["confidence_score"] <= 1.0


def test_ui_routes_expose_generated_results(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("GRAPHREVIEW_JUDGE_ENABLED", "false")

    source_root = Path("sample_project").resolve()
    db_path = tmp_path / "phase5_ui.db"
    output_dir = tmp_path / "ui_outputs"
    seed_project(source_root, db_path=str(db_path), force=True)

    monkeypatch.setenv("GRAPHREVIEW_SOURCE_ROOT", str(source_root))
    monkeypatch.setenv("GRAPHREVIEW_DB_PATH", str(db_path))
    monkeypatch.setenv("GRAPHREVIEW_OUTPUT_DIR", str(output_dir))

    if "server.app" in sys.modules:
        del sys.modules["server.app"]
    server_app = importlib.import_module("server.app")
    app = server_app.app

    client = TestClient(app)
    generated = client.post(
        "/reports/generate",
        json={"module_override": ["checkout"], "hops": 1, "output_dir": str(output_dir), "report_prefix": "ui_case"},
    )
    assert generated.status_code == 200

    home = client.get("/")
    assert home.status_code == 200
    assert "GraphReview Results Console" in home.text

    listed = client.get("/ui/results")
    assert listed.status_code == 200
    results = listed.json()
    assert len(results) >= 1

    detail = client.get("/ui/result", params={"report_path": results[0]["report_path"]})
    assert detail.status_code == 200
    payload = detail.json()
    assert "connectivity" in payload
    assert payload["connectivity"]["node_count"] >= 1
