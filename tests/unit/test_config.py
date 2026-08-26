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
