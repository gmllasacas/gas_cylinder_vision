from app.core.config import settings, AppSettings, SourceConfig, DetectorConfig, StreamingConfig
from app.core.logging import logger, setup_logger
from app.core.i18n import I18nManager
from app.core.security import get_current_admin

i18n = I18nManager(locales_dir=settings.locales_dir, default_lang=settings.language)

__all__ = [
    "settings",
    "AppSettings",
    "SourceConfig",
    "DetectorConfig",
    "StreamingConfig",
    "logger",
    "setup_logger",
    "I18nManager",
    "i18n",
    "get_current_admin",
]
