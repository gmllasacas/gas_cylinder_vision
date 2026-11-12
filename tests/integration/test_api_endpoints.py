import pytest
from fastapi.testclient import TestClient

@pytest.mark.integration
def test_dashboard_index(client: TestClient):
    response = client.get("/")
    assert response.status_code == 200
    assert "data-theme=\"dark\"" in response.text
    assert "alpine.min.js" in response.text

@pytest.mark.integration
def test_dashboard_index_v2(client: TestClient):
    response = client.get("/v2")
    assert response.status_code == 200
    assert "data-theme=\"dark\"" in response.text
    assert "alpine.min.js" in response.text

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

@pytest.mark.integration
def test_playback_restart(client: TestClient):
    response = client.post("/api/playback/restart")
    assert response.status_code == 200
    data = response.json()
    assert "current_frame" in data

@pytest.mark.integration
def test_playback_loop(client: TestClient):
    # Get current loop state
    res1 = client.get("/api/status")
    init_loop = res1.json()["loop"]
    
    # Toggle loop
    response = client.post("/api/playback/loop")
    assert response.status_code == 200
    data = response.json()
    assert data["loop"] == (not init_loop)
    
    # Set explicit loop state back
    response2 = client.post("/api/playback/loop", params={"enabled": init_loop})
    assert response2.status_code == 200
    assert response2.json()["loop"] == init_loop

@pytest.mark.integration
def test_playback_seek_offset(client: TestClient):
    response = client.post("/api/playback/seek_offset", params={"seconds": 5.0})
    assert response.status_code == 200
    data = response.json()
    assert "current_frame" in data

@pytest.mark.integration
def test_playback_step(client: TestClient):
    response = client.post("/api/playback/step", params={"delta_frames": 1})
    assert response.status_code == 200
    data = response.json()
    assert data["is_paused"] is True

@pytest.mark.integration
def test_settings_confidence_alias(client: TestClient):
    response = client.post("/api/settings/confidence", params={"value": 0.55})
    assert response.status_code == 200
    assert response.json()["conf"] == 0.55

@pytest.mark.integration
def test_settings_language_alias(client: TestClient):
    response = client.post("/api/settings/language", params={"lang": "en"})
    assert response.status_code == 200
    assert response.json()["lang"] == "en"
