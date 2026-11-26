import pytest
from fastapi.testclient import TestClient
from app.main import app

@pytest.mark.integration
def test_unauthenticated_dashboard_rejected():
    with TestClient(app) as raw_client:
        response = raw_client.get("/")
        assert response.status_code == 401
        assert "WWW-Authenticate" in response.headers
        assert response.headers["WWW-Authenticate"] == "Basic"

@pytest.mark.integration
def test_unauthenticated_api_rejected():
    with TestClient(app) as raw_client:
        response = raw_client.get("/api/status")
        assert response.status_code == 401
        assert "WWW-Authenticate" in response.headers

@pytest.mark.integration
def test_invalid_credentials_rejected():
    with TestClient(app) as raw_client:
        response = raw_client.get("/api/status", auth=("wrong_user", "wrong_pass"))
        assert response.status_code == 401

@pytest.mark.integration
def test_valid_admin_credentials_accepted():
    with TestClient(app) as raw_client:
        response = raw_client.get("/api/status", auth=("admin", "admin"))
        assert response.status_code == 200
        assert "current_video" in response.json()

@pytest.mark.integration
def test_health_endpoint_unauthenticated_accessible():
    with TestClient(app) as raw_client:
        response = raw_client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"

@pytest.mark.integration
def test_favicon_endpoint_unauthenticated_accessible():
    with TestClient(app) as raw_client:
        response = raw_client.get("/favicon.ico")
        assert response.status_code == 200
        assert "image" in response.headers.get("content-type", "")

@pytest.mark.integration
def test_auth_rate_limiting_lockout():
    from app.core.security import reset_auth_rate_limiter
    reset_auth_rate_limiter()
    with TestClient(app) as raw_client:
        # Perform 5 failed attempts
        for _ in range(5):
            res = raw_client.get("/api/status", auth=("wrong_user", "wrong_pass"))
            assert res.status_code == 401

        # 6th attempt should be blocked by rate limiter with 429 Too Many Requests
        lockout_res = raw_client.get("/api/status", auth=("wrong_user", "wrong_pass"))
        assert lockout_res.status_code == 429
        assert "Retry-After" in lockout_res.headers
        assert "Too many failed authentication attempts" in lockout_res.json()["detail"]

        # Reset limiter for subsequent tests
        reset_auth_rate_limiter()
