import pytest
import numpy as np
from pathlib import Path
from fastapi.testclient import TestClient

@pytest.fixture(scope="session", autouse=True)
def test_db_isolation(tmp_path_factory):
    """
    Ensures that ALL unit & integration test runs use a dedicated temporary SQLite database
    and NEVER modify or clear the production data/gas_stream.db file.
    """
    temp_dir = tmp_path_factory.mktemp("test_db_data")
    temp_db_path = str(temp_dir / "isolated_test_gas_stream.db")

    from app.db import db_manager, db_repo, DatabaseManager, DailyCountRepository
    from app.services.stream_manager import video_service

    # Create isolated database manager
    test_manager = DatabaseManager(db_path=temp_db_path)
    test_repo = DailyCountRepository(db_manager=test_manager)

    # Patch global singletons during test session
    db_manager.db_path = temp_db_path
    db_manager.init_db()
    db_repo.db = test_manager

    video_service.db = test_repo
    video_service.anomaly_detector.db = test_repo

    yield test_repo

@pytest.fixture(scope="session")
def client():
    """FastAPI TestClient session fixture with admin auth credentials."""
    from app.main import app
    with TestClient(app) as test_client:
        test_client.auth = ("admin", "admin")
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
            "video_file": "default.mp4",
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
        },
        "anomaly": {
            "enabled": True,
            "window_seconds": 60,
            "batch_idle_seconds": 15
        }
    }
