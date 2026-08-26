import os
import json
from pathlib import Path
from typing import List, Literal, Optional, Any, Dict
from pydantic import BaseModel, Field
from app.core.logging import logger

# Base Directories
APP_DIR = Path(__file__).resolve().parent.parent
ROOT_DIR = APP_DIR.parent

class SourceConfig(BaseModel):
    type: Literal["video", "camera"] = "video"
    video_file: str = "1min_test.mp4"
    camera_url: str = "rtsp://admin:password@192.168.1.100:554/stream1"
    camera_name: str = "IP Camera"
    reconnect_interval_sec: int = Field(default=3, ge=1, le=60)

class DetectorConfig(BaseModel):
    default_model: str = "best.pt"
    fallback_model: str = "yolov8n.pt"
    confidence: float = Field(default=0.50, ge=0.0, le=1.0)
    imgsz: int = Field(default=640, ge=32, le=1920)
    frame_skip: int = Field(default=2, ge=1, le=10)
    line_points: List[List[int]] = Field(
        default_factory=lambda: [[1200, 400], [1700, 400]]
    )

class StreamingConfig(BaseModel):
    output_width: int = Field(default=1024, ge=320, le=3840)
    jpeg_quality: int = Field(default=70, ge=10, le=100)

class AppSettings(BaseModel):
    app_name: str = "Gas Tank Counter Dashboard"
    language: str = "es"
    source: SourceConfig = Field(default_factory=SourceConfig)
    detector: DetectorConfig = Field(default_factory=DetectorConfig)
    streaming: StreamingConfig = Field(default_factory=StreamingConfig)

    # Resolved Directory Paths
    root_dir: str = str(ROOT_DIR)
    app_dir: str = str(APP_DIR)
    data_dir: str = str(ROOT_DIR / "data")
    db_path: str = str(ROOT_DIR / "data" / "gas_stream.db")
    videos_dir: str = str(ROOT_DIR / "videos")
    models_dir: str = str(ROOT_DIR / "models")
    locales_dir: str = str(ROOT_DIR / "locales")
    static_dir: str = str(ROOT_DIR / "static")
    templates_dir: str = str(ROOT_DIR / "templates")
    config_path: str = str(ROOT_DIR / "config.json")

    @classmethod
    def load(cls, config_file: Optional[str] = None) -> "AppSettings":
        """Loads configuration from config.json with fallback to defaults."""
        target_path = Path(config_file) if config_file else ROOT_DIR / "config.json"
        
        if target_path.exists():
            try:
                with open(target_path, "r", encoding="utf-8") as fp:
                    data = json.load(fp)
                logger.info(f"Loaded configuration from {target_path}")
                return cls(**data)
            except Exception as e:
                logger.warning(f"Error reading {target_path}: {e}. Using default settings.")
        else:
            logger.info(f"Configuration file {target_path} not found. Creating default settings.")

        return cls()

    def save(self, config_file: Optional[str] = None) -> bool:
        """Persists the current configuration to config.json."""
        target_path = Path(config_file) if config_file else Path(self.config_path)
        try:
            # Dump only configuration fields, omitting internal path attributes
            data = {
                "source": self.source.model_dump(),
                "language": self.language,
                "detector": self.detector.model_dump(),
                "streaming": self.streaming.model_dump()
            }
            with open(target_path, "w", encoding="utf-8") as fp:
                json.dump(data, fp, indent=2)
            logger.info(f"Configuration saved successfully to {target_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to save configuration to {target_path}: {e}")
            return False

    def to_dict(self) -> Dict[str, Any]:
        """Returns clean dictionary compatible with existing API responses and legacy frontend."""
        return {
            "source": self.source.model_dump(),
            "language": self.language,
            "detector": self.detector.model_dump(),
            "streaming": self.streaming.model_dump()
        }

# Global singleton instance
settings = AppSettings.load()
