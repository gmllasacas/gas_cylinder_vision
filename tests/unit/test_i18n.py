import pytest
from app.core.i18n import I18nManager
from app.core.config import settings

@pytest.mark.unit
def test_i18n_loading_and_translation():
    i18n = I18nManager(locales_dir=settings.locales_dir, default_lang="en")
    
    # Check English lookup
    i18n.set_language("en")
    assert "Gas Tank Counter" in i18n.t("ui.title")
    assert i18n.t("video.default_class") == "gas_tank"

    # Check Spanish lookup
    i18n.set_language("es")
    assert len(i18n.t("ui.title")) > 0

@pytest.mark.unit
def test_i18n_fallback():
    i18n = I18nManager(locales_dir=settings.locales_dir, default_lang="en")
    i18n.set_language("es")
    
    # Non-existent key returns key name or default fallback
    fallback_res = i18n.t("non.existent.key", default="Fallback Title")
    assert fallback_res == "Fallback Title"
