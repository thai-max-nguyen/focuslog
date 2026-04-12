import pytest
import os
import tempfile
from fastapi.testclient import TestClient
from tracker.db import Database
from tracker.api import create_app


@pytest.fixture
def client():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        path = f.name
    db = Database(path)
    db.init()
    # Seed a session on 2023-11-14 UTC
    from datetime import datetime, timezone
    day_start = int(datetime(2023, 11, 14, tzinfo=timezone.utc).timestamp())
    db.insert_session(
        app_name="VSCode",
        window_title="main.py",
        category="Work",
        start_time=day_start + 100,
        end_time=day_start + 1900,
        duration=1800,
        is_idle=False
    )
    app = create_app(db)
    client = TestClient(app)
    yield client
    db.close()
    os.unlink(path)


def test_get_sessions(client):
    res = client.get("/api/sessions?date=2023-11-14")
    assert res.status_code == 200
    data = res.json()
    assert len(data) == 1
    assert data[0]["app_name"] == "VSCode"


def test_get_summary(client):
    res = client.get("/api/summary?date=2023-11-14")
    assert res.status_code == 200
    data = res.json()
    assert data["total_active"] == 1800


def test_get_timeline(client):
    res = client.get("/api/timeline?date=2023-11-14")
    assert res.status_code == 200
    blocks = res.json()
    assert len(blocks) >= 1


def test_get_apps_leaderboard(client):
    res = client.get("/api/apps?date=2023-11-14")
    assert res.status_code == 200
    apps = res.json()
    assert apps[0]["app_name"] == "VSCode"


def test_export_csv(client):
    res = client.get("/api/export?date=2023-11-14&fmt=csv")
    assert res.status_code == 200
    assert "text/csv" in res.headers["content-type"]
    assert "VSCode" in res.text


def test_rules_crud(client):
    res = client.post("/api/rules", json={"app_name": "YouTube", "url_contains": None, "category": "Entertainment"})
    assert res.status_code == 200
    rule_id = res.json()["id"]
    res = client.get("/api/rules")
    assert res.status_code == 200
    assert any(r["app_name"] == "YouTube" for r in res.json())
    res = client.delete(f"/api/rules/{rule_id}")
    assert res.status_code == 200
