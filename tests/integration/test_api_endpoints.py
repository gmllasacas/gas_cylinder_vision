import pytest
from fastapi.testclient import TestClient

@pytest.mark.integration
def test_dashboard_index(client: TestClient):
    response = client.get("/")
    assert response.status_code == 200

@pytest.mark.integration
def test_get_api_status(client: TestClient):
    response = client.get("/api/status")
    assert response.status_code == 200
    data = response.json()
    assert "current_video" in data
    assert "in_count" in data
    assert "out_count" in data
    assert "ai_latency_ms" in data
    assert "conf" in data

@pytest.mark.integration
def test_get_api_videos(client: TestClient):
    response = client.get("/api/videos")
    assert response.status_code == 200
    data = response.json()
    assert "sources" in data
    assert "videos" in data

@pytest.mark.integration
def test_get_api_config(client: TestClient):
    response = client.get("/api/config")
    assert response.status_code == 200
    data = response.json()
    assert "source" in data
    assert "detector" in data

@pytest.mark.integration
def test_update_settings_confidence(client: TestClient):
    response = client.post("/api/settings/conf", params={"value": 0.65})
    assert response.status_code == 200
    data = response.json()
    assert data["conf"] == 0.65

@pytest.mark.integration
def test_update_settings_speed(client: TestClient):
    response = client.post("/api/settings/speed", params={"value": 1.5})
    assert response.status_code == 200
    data = response.json()
    assert data["playback_speed"] == 1.5

@pytest.mark.integration
def test_toggle_playback(client: TestClient):
    response = client.post("/api/playback/toggle")
    assert response.status_code == 200
    data = response.json()
    assert "is_paused" in data

@pytest.mark.integration
def test_reset_playback(client: TestClient):
    response = client.post("/api/playback/reset")
    assert response.status_code == 200
    data = response.json()
    assert data["in_count"] == 0
    assert data["out_count"] == 0
