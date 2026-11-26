import os
import json
from pathlib import Path
from typing import List, Literal, Optional, Any, Dict
from pydantic import BaseModel, Field, model_validator
from app.core.logging import logger

from dotenv import load_dotenv

# Base Directories
APP_DIR = Path(__file__).resolve().parent.parent
ROOT_DIR = APP_DIR.parent

class SourceConfig(BaseModel):
    type: Literal["video", "camera"] = "video"
    video_file: str = "default.mp4"
    camera_url: str = ""
    camera_name: str = "IP Camera"
    reconnect_interval_sec: int = Field(default=3, ge=1, le=60)

class DetectorConfig(BaseModel):
    default_model: str = "best.pt"
    fallback_model: str = "yolov8n.pt"
    confidence: float = Field(default=0.50, ge=0.0, le=1.0)
    imgsz: int = Field(default=640, ge=32, le=1920)
    frame_skip: int = Field(default=2, ge=1, le=10)
    device: str = Field(default="auto", description="Compute device: 'auto', 'cuda', 'cuda:0', '0', 'cpu', 'mps'")
    line_points: List[List[int]] = Field(
        default_factory=lambda: [[1200, 400], [1700, 400]]
    )

class StreamingConfig(BaseModel):
    output_width: int = Field(default=1024, ge=320, le=3840)
    jpeg_quality: int = Field(default=70, ge=10, le=100)

class AnomalyConfig(BaseModel):
    enabled: bool = True
    window_seconds: int = Field(default=60, ge=5, le=600)
    batch_idle_seconds: int = Field(default=15, ge=2, le=120)

class AppSettings(BaseModel):
    app_name: str = "Gas Tank Counter Dashboard"
    language: str = "es"
    timezone: str = "America/Lima"
    admin_username: str = "admin"
    admin_password: str = "admin"
    host: str = "0.0.0.0"
    port: int = 8000
    environment: str = "development"
    log_level: str = "INFO"
    ssl_keyfile: Optional[str] = None
    ssl_certfile: Optional[str] = None
    source: SourceConfig = Field(default_factory=SourceConfig)
    detector: DetectorConfig = Field(default_factory=DetectorConfig)
    streaming: StreamingConfig = Field(default_factory=StreamingConfig)
    anomaly: AnomalyConfig = Field(default_factory=AnomalyConfig)

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

    @model_validator(mode="after")
    def validate_production_credentials(self) -> "AppSettings":
        if str(self.environment).lower() == "production":
            is_default_user = str(self.admin_username).lower() == "admin"
            is_default_pass = str(self.admin_password).lower() == "admin"
            if is_default_user and is_default_pass:
                raise ValueError(
                    "Default credentials 'admin:admin' are strictly prohibited in production mode. "
                    "Configure strong ADMIN_USERNAME and ADMIN_PASSWORD environment variables."
                )
        return self

    @classmethod
    def load(cls, config_file: Optional[str] = None) -> "AppSettings":
        """Loads configuration from .env and config.json with fallback to defaults."""
        # 1. Load environment variables from .env if present
        env_path = ROOT_DIR / ".env"
        if env_path.exists():
            load_dotenv(env_path, override=False)

        # 2. Read structured settings from config.json
        target_path = Path(config_file) if config_file else ROOT_DIR / "config.json"
        data: Dict[str, Any] = {}
        
        if target_path.exists():
            try:
                with open(target_path, "r", encoding="utf-8") as fp:
                    data = json.load(fp)
                logger.info(f"Loaded configuration from {target_path}")
            except Exception as e:
                logger.warning(f"Error reading {target_path}: {e}. Using default settings.")
        else:
            logger.info(f"Configuration file {target_path} not found. Creating default settings.")

        # 3. Apply environment variable overrides if provided
        data["host"] = os.getenv("HOST", data.get("host", "0.0.0.0"))
        try:
            data["port"] = int(os.getenv("PORT", str(data.get("port", 8000))))
        except ValueError:
            data["port"] = 8000
        data["environment"] = os.getenv("ENVIRONMENT", data.get("environment", "development"))
        data["log_level"] = os.getenv("LOG_LEVEL", data.get("log_level", "INFO"))
        data["timezone"] = os.getenv("TIMEZONE", data.get("timezone", "America/Lima"))
        data["admin_username"] = os.getenv("ADMIN_USERNAME", data.get("admin_username", "admin"))
        data["admin_password"] = os.getenv("ADMIN_PASSWORD", data.get("admin_password", "admin"))
        data["ssl_keyfile"] = os.getenv("SSL_KEYFILE", data.get("ssl_keyfile"))
        data["ssl_certfile"] = os.getenv("SSL_CERTFILE", data.get("ssl_certfile"))

        if "source" not in data:
            data["source"] = {}
        if os.getenv("CAMERA_URL"):
            data["source"]["camera_url"] = os.getenv("CAMERA_URL")

        if "detector" not in data:
            data["detector"] = {}
        dev_env = os.getenv("YOLO_DEVICE") or os.getenv("DEVICE")
        if dev_env:
            data["detector"]["device"] = dev_env

        instance = cls(**data)
        if os.getenv("DB_PATH"):
            db_env = os.getenv("DB_PATH")
            if not os.path.isabs(db_env):
                instance.db_path = str((ROOT_DIR / db_env).resolve())
            else:
                instance.db_path = str(Path(db_env).resolve())
        return instance

    def save(self, config_file: Optional[str] = None) -> bool:
        """Persists the current configuration to config.json."""
        target_path = Path(config_file) if config_file else Path(self.config_path)
        try:
            # Dump only configuration fields, omitting internal path attributes
            src_dump = self.source.model_dump()
            if os.getenv("CAMERA_URL"):
                src_dump["camera_url"] = ""

            data = {
                "source": src_dump,
                "language": self.language,
                "detector": self.detector.model_dump(),
                "streaming": self.streaming.model_dump(),
                "anomaly": self.anomaly.model_dump()
            }
            with open(target_path, "w", encoding="utf-8") as fp:
                json.dump(data, fp, indent=2)
            logger.info(f"Configuration saved successfully to {target_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to save configuration to {target_path}: {e}")
            return False

    def to_dict(self, mask_secrets: bool = True) -> Dict[str, Any]:
        """Returns clean dictionary compatible with existing API responses and legacy frontend."""
        src_data = self.source.model_dump()
        if mask_secrets and src_data.get("camera_url"):
            from app.cv.capture import VideoCaptureManager
            src_data["camera_url"] = VideoCaptureManager.mask_credentials(src_data["camera_url"])
        return {
            "source": src_data,
            "language": self.language,
            "detector": self.detector.model_dump(),
            "streaming": self.streaming.model_dump(),
            "anomaly": self.anomaly.model_dump()
        }

# Global singleton instance
settings = AppSettings.load()
