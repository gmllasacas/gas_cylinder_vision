import os
import json
from typing import Dict, Any, Optional
from app.core.logging import logger

class I18nManager:
    """Manages multi-language translations and locale catalogs."""
    
    def __init__(self, locales_dir: str, default_lang: str = "en"):
        self.locales_dir = locales_dir
        self.default_lang = default_lang
        self.current_lang = default_lang
        self._catalogs: Dict[str, Dict[str, Any]] = {}
        self.load_all()

    def load_all(self) -> None:
        """Loads all JSON translation files from the locales directory."""
        self._catalogs.clear()
        if not os.path.exists(self.locales_dir):
            logger.warning(f"Locales directory not found at: {self.locales_dir}")
            return

        for filename in os.listdir(self.locales_dir):
            if filename.lower().endswith(".json"):
                lang_code = os.path.splitext(filename)[0].lower()
                file_path = os.path.join(self.locales_dir, filename)
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        self._catalogs[lang_code] = json.load(f)
                    logger.debug(f"Loaded locale '{lang_code}' from {filename}")
                except Exception as e:
                    logger.error(f"Failed to load locale file {filename}: {e}")

    def set_language(self, lang: str) -> bool:
        """Sets the active language code."""
        lang = lang.lower()
        if lang in self._catalogs:
            self.current_lang = lang
            return True
        logger.warning(f"Language '{lang}' not found in loaded locales. Remaining as '{self.current_lang}'")
        return False

    def get_catalog(self, lang: Optional[str] = None) -> Dict[str, Any]:
        """Returns the dictionary catalog for a specific or current language."""
        target_lang = (lang or self.current_lang).lower()
        return self._catalogs.get(target_lang, self._catalogs.get(self.default_lang, {}))

    def t(self, key_path: str, default: str = "", lang: Optional[str] = None) -> str:
        """
        Retrieves a translated string using dot notation (e.g., 'ui.title', 'video.offline_title').
        Falls back to default_lang or the provided default string.
        """
        target_lang = (lang or self.current_lang).lower()
        
        # Try current/requested language
        val = self._resolve_key(self._catalogs.get(target_lang, {}), key_path)
        if val is not None:
            return str(val)

        # Fallback to default language
        if target_lang != self.default_lang:
            val = self._resolve_key(self._catalogs.get(self.default_lang, {}), key_path)
            if val is not None:
                return str(val)

        return default or key_path

    @staticmethod
    def _resolve_key(catalog: Dict[str, Any], key_path: str) -> Optional[Any]:
        keys = key_path.split(".")
        current = catalog
        for k in keys:
            if isinstance(current, dict) and k in current:
                current = current[k]
            else:
                return None
        return current
