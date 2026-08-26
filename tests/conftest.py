import pytest
import numpy as np
from fastapi.testclient import TestClient
from app.main import app

@pytest.fixture(scope="session")
def client():
    """FastAPI TestClient session fixture."""
    with TestClient(app) as test_client:
        yield test_client

@pytest.fixture
def mock_frame():
    """Returns a synthetic 3-channel image frame for CV testing."""
    return np.zeros((480, 640, 3), dtype=np.uint8)

@pytest.fixture
def sample_config_dict():
    """Returns a valid dictionary configuration."""
    return {
        "source": {
            "type": "video",
            "video_file": "1min_test.mp4",
            "camera_url": "rtsp://admin:password@192.168.1.100:554/stream1",
            "camera_name": "Test Camera",
            "reconnect_interval_sec": 3
        },
        "language": "en",
        "detector": {
            "default_model": "best.pt",
            "fallback_model": "yolov8n.pt",
            "confidence": 0.55,
            "imgsz": 640,
            "frame_skip": 2,
            "line_points": [[100, 200], [500, 200]]
        },
        "streaming": {
            "output_width": 1024,
            "jpeg_quality": 75
        }
    }
