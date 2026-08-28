import pytest
from app.db import db_repo
from app.services.stream_manager import video_service

@pytest.mark.integration
def test_get_alerts_endpoint(client):
    # Clear any previous alerts
    db_repo.clear_inconsistency_alerts()
    video_service.anomaly_detector.clear_alerts()

    # Query empty alerts
    res = client.get("/api/alerts")
    assert res.status_code == 200
    data = res.json()
    assert data["total"] == 0
    assert data["alerts"] == []

    # Inject an anomaly record
    alert_record = db_repo.record_inconsistency(
        in_count=2,
        out_count=3,
        message="Test Inconsistency: 3 tanks went OUT, but only 2 came IN.",
        severity="ERROR"
    )

    res2 = client.get("/api/alerts")
    assert res2.status_code == 200
    data2 = res2.json()
    assert data2["total"] >= 1
    assert data2["alerts"][0]["in_count"] == 2
    assert data2["alerts"][0]["out_count"] == 3
    assert data2["alerts"][0]["discrepancy"] == 1

@pytest.mark.integration
def test_clear_alerts_endpoint(client):
    # Ensure at least 1 alert exists
    db_repo.record_inconsistency(
        in_count=2,
        out_count=1,
        message="Test Inconsistency: Missing 1 tank.",
        severity="WARNING"
    )

    # Clear alerts
    res = client.post("/api/alerts/clear")
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert data["cleared_count"] >= 1

    # Verify empty afterwards
    res_after = client.get("/api/alerts")
    assert res_after.json()["total"] == 0

@pytest.mark.integration
def test_status_endpoint_has_alert_keys(client):
    res = client.get("/api/status")
    assert res.status_code == 200
    data = res.json()
    assert "active_alerts_count" in data
    assert "latest_alert" in data
