import pytest
from pydantic import ValidationError
from app.core.config import AppSettings, DetectorConfig, SourceConfig, StreamingConfig

@pytest.mark.unit
def test_app_settings_defaults():
    settings = AppSettings()
    assert settings.language == "es"
    assert settings.source.type == "video"
    assert settings.detector.confidence == 0.50
    assert settings.detector.imgsz == 640
    assert settings.streaming.output_width == 1024

@pytest.mark.unit
def test_app_settings_from_dict(sample_config_dict):
    settings = AppSettings(**sample_config_dict)
    assert settings.language == "en"
    assert settings.detector.confidence == 0.55
    assert settings.source.camera_name == "Test Camera"
    assert settings.streaming.jpeg_quality == 75

@pytest.mark.unit
def test_confidence_validation():
    with pytest.raises(ValidationError):
        DetectorConfig(confidence=1.5)  # Must be <= 1.0

    with pytest.raises(ValidationError):
        DetectorConfig(confidence=-0.1)  # Must be >= 0.0

@pytest.mark.unit
def test_streaming_quality_validation():
    with pytest.raises(ValidationError):
        StreamingConfig(jpeg_quality=5)  # Must be >= 10

    with pytest.raises(ValidationError):
        StreamingConfig(jpeg_quality=105)  # Must be <= 100

@pytest.mark.unit
def test_detector_device_config():
    default_cfg = DetectorConfig()
    assert default_cfg.device == "auto"

    custom_cfg = DetectorConfig(device="cuda:0")
    assert custom_cfg.device == "cuda:0"

@pytest.mark.unit
def test_app_settings_device_env_override(monkeypatch, tmp_path):
    monkeypatch.setenv("YOLO_DEVICE", "cuda:0")
    settings = AppSettings.load()
    assert settings.detector.device == "cuda:0"

@pytest.mark.unit
def test_app_settings_production_default_credentials_rejected():
    with pytest.raises(ValidationError) as excinfo:
        AppSettings(environment="production", admin_username="admin", admin_password="admin")
    assert "Default credentials 'admin:admin' are strictly prohibited in production mode" in str(excinfo.value)

@pytest.mark.unit
def test_app_settings_production_custom_credentials_accepted():
    prod_settings = AppSettings(
        environment="production",
        admin_username="secure_operator",
        admin_password="SuperSecretPassword123!"
    )
    assert prod_settings.environment == "production"
    assert prod_settings.admin_username == "secure_operator"

@pytest.mark.unit
def test_app_settings_ssl_configuration(monkeypatch):
    monkeypatch.setenv("SSL_KEYFILE", "certs/server.key")
    monkeypatch.setenv("SSL_CERTFILE", "certs/server.crt")
    settings = AppSettings.load()
    assert settings.ssl_keyfile == "certs/server.key"
    assert settings.ssl_certfile == "certs/server.crt"
