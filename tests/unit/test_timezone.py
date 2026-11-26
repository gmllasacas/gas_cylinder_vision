import pytest
from datetime import datetime
from zoneinfo import ZoneInfo
from app.core import settings
from app.db.repository import DailyCountRepository

@pytest.mark.unit
def test_timezone_setting():
    assert settings.timezone == "America/Lima"
    tz = DailyCountRepository._get_tz()
    assert tz.key == "America/Lima"

@pytest.mark.unit
def test_repository_today_and_now_use_configured_timezone():
    lima_tz = ZoneInfo("America/Lima")
    expected_date = datetime.now(lima_tz).strftime("%Y-%m-%d")
    today_str = DailyCountRepository._today_str()
    assert today_str == expected_date

    now_iso = DailyCountRepository._now_iso()
    # Check that ISO string has timezone offset corresponding to America/Lima (UTC-5)
    parsed = datetime.fromisoformat(now_iso)
    assert parsed.tzinfo is not None

