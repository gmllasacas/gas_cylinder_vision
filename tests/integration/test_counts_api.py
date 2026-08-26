import pytest
from fastapi.testclient import TestClient
from app.db import db_repo

@pytest.mark.integration
def test_get_counts_today(client: TestClient):
    response = client.get("/api/counts/today")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "date" in data["data"]
    assert "in_count" in data["data"]
    assert "out_count" in data["data"]
    assert "net_count" in data["data"]

@pytest.mark.integration
def test_get_counts_history(client: TestClient):
    # Ensure at least one record exists
    db_repo.record_crossing(direction="IN")

    response = client.get("/api/counts/history?limit=10")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "history" in data
    assert len(data["history"]) >= 1

@pytest.mark.integration
def test_get_counts_events(client: TestClient):
    db_repo.record_crossing(direction="OUT", track_id=99)

    response = client.get("/api/counts/events?limit=5")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "events" in data
    assert len(data["events"]) >= 1
    assert data["events"][0]["direction"] in ("IN", "OUT")

@pytest.mark.integration
def test_reset_counts_api(client: TestClient):
    db_repo.record_crossing(direction="IN")
    response = client.post("/api/counts/reset")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["data"]["in_count"] == 0
    assert data["data"]["out_count"] == 0

