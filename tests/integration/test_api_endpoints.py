import json
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
    for s in data.get("sources", []):
        if s.get("type") == "camera":
            assert ":password@" not in s.get("url", "")
            assert "****@" in s.get("url", "")

@pytest.mark.integration
def test_get_api_config(client: TestClient):
    response = client.get("/api/config")
    assert response.status_code == 200
    data = response.json()
    assert "source" in data
    assert "detector" in data
    cam_url = data["source"].get("camera_url", "")
    if "@" in cam_url:
        assert ":password@" not in cam_url
        assert "****@" in cam_url

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

@pytest.mark.integration
def test_health_endpoint(client: TestClient):
    # Public healthcheck should succeed with or without auth
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "Gas Tank Counter" in data["service"]

@pytest.mark.integration
def test_settings_confidence_json_body(client: TestClient):
    response = client.post("/api/settings/confidence", json={"value": 0.62})
    assert response.status_code == 200
    assert response.json()["conf"] == 0.62

@pytest.mark.integration
def test_settings_speed_json_body(client: TestClient):
    response = client.post("/api/settings/speed", json={"value": 1.25})
    assert response.status_code == 200
    assert response.json()["playback_speed"] == 1.25

@pytest.mark.integration
def test_settings_language_json_body(client: TestClient):
    response = client.post("/api/settings/language", json={"value": "es"})
    assert response.status_code == 200
    assert response.json()["lang"] == "es"

@pytest.mark.integration
def test_settings_debug_json_body(client: TestClient):
    response = client.post("/api/settings/debug", json={"enabled": True})
    assert response.status_code == 200
    assert response.json()["debug_mode"] is True

@pytest.mark.integration
def test_playback_seek_json_body(client: TestClient):
    response = client.post("/api/playback/seek", json={"frame": 5})
    assert response.status_code == 200
    assert "current_frame" in response.json()

@pytest.mark.integration
def test_status_stream_sse_endpoint(client: TestClient):
    with client.stream("GET", "/api/status/stream") as response:
        assert response.status_code == 200
        assert "text/event-stream" in response.headers.get("content-type", "")

@pytest.mark.integration
def test_select_video_source_endpoint(client: TestClient):
    # Select available video
    res_list = client.get("/api/videos")
    assert res_list.status_code == 200
    videos = res_list.json().get("videos", [])
    if videos:
        target_video = videos[0]
        res_sel = client.post(f"/api/videos/select?filename={target_video}")
        assert res_sel.status_code == 200
        assert res_sel.json()["status"] == "success"

        # Verify active source updated
        res_status = client.get("/api/status")
        assert res_status.status_code == 200
        assert res_status.json()["current_source_id"] == target_video

@pytest.mark.integration
def test_select_video_source_invalid(client: TestClient):
    # Non-existent video file
    res = client.post("/api/videos/select?filename=non_existent_fake_video.mp4")
    assert res.status_code == 400
    assert res.json()["status"] == "error"

@pytest.mark.integration
def test_favicon_endpoint(client: TestClient):
    res = client.get("/favicon.ico")
    assert res.status_code == 200
    assert "image" in res.headers.get("content-type", "")

@pytest.mark.integration
def test_security_headers_present(client: TestClient):
    res = client.get("/")
    assert res.status_code == 200
    assert res.headers.get("x-frame-options") == "DENY"
    assert res.headers.get("x-content-type-options") == "nosniff"
    assert res.headers.get("referrer-policy") == "strict-origin-when-cross-origin"
    assert "frame-ancestors 'none'" in res.headers.get("content-security-policy", "")
    # In development/test over plain HTTP, HSTS is omitted to avoid breaking localhost
    assert "strict-transport-security" not in res.headers

@pytest.mark.integration
def test_security_headers_hsts_when_https(client: TestClient):
    res = client.get("/", headers={"x-forwarded-proto": "https"})
    assert res.status_code == 200
    assert "strict-transport-security" in res.headers
    assert "max-age=31536000" in res.headers.get("strict-transport-security", "")

@pytest.mark.integration
def test_video_feed_concurrency_limiting(client: TestClient):
    from app.api.v1.endpoints.stream import reset_stream_connections, MAX_CONCURRENT_STREAMS_PER_IP
    reset_stream_connections()

    open_streams = []
    try:
        # Open up to the maximum permitted streams for this client IP
        for _ in range(MAX_CONCURRENT_STREAMS_PER_IP):
            stream_ctx = client.stream("GET", "/video_feed")
            resp = stream_ctx.__enter__()
            assert resp.status_code == 200
            open_streams.append(stream_ctx)

        # Attempting one more concurrent stream should trigger HTTP 429 Too Many Requests
        excess_res = client.get("/video_feed")
        assert excess_res.status_code == 429
        assert "Retry-After" in excess_res.headers
        assert "Too many concurrent video streams" in excess_res.json()["detail"]
    finally:
        # Close open streams and verify slot release
        for stream_ctx in open_streams:
            stream_ctx.__exit__(None, None, None)
        reset_stream_connections()

