from __future__ import annotations

from fastapi.testclient import TestClient

from server.app import app


client = TestClient(app)


def test_operational_endpoints() -> None:
    health = client.get("/health")
    assert health.status_code == 200
    assert health.json()["ok"] is True

    tasks = client.get("/tasks")
    assert tasks.status_code == 200
    task_ids = {task["task_id"] for task in tasks.json()}
    assert {"style_review", "logic_review", "cascade_review"}.issubset(task_ids)
