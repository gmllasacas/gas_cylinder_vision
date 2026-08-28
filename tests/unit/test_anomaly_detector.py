import pytest
from app.services.anomaly_detector import AnomalyDetector
from app.db.database import DatabaseManager
from app.db.repository import DailyCountRepository
from app.core.i18n import I18nManager

@pytest.fixture
def temp_anomaly_detector(tmp_path):
    db_file = str(tmp_path / "test_anomaly.db")
    db_mgr = DatabaseManager(db_path=db_file)
    repo = DailyCountRepository(db_manager=db_mgr)
    detector = AnomalyDetector(
        enabled=True,
        window_seconds=60.0,
        batch_idle_seconds=15.0,
        db=repo
    )
    return detector

@pytest.mark.unit
def test_anomaly_detector_balanced_batch(temp_anomaly_detector):
    """2 IN -> 2 OUT within time window: perfectly balanced, no anomaly."""
    detector = temp_anomaly_detector

    # 2 tanks come IN
    assert detector.record_event("IN", track_id=1, timestamp=10.0) is None
    assert detector.record_event("IN", track_id=2, timestamp=11.0) is None

    # Processing inside (at t=25s, before any exits, no timeout alert triggered)
    assert detector.check_idle_timeout(current_time=25.0) is None

    # 2 tanks go OUT
    assert detector.record_event("OUT", track_id=1, timestamp=30.0) is None
    assert detector.record_event("OUT", track_id=2, timestamp=32.0) is None

    # Check idle timeout after batch
    alert = detector.check_idle_timeout(current_time=50.0)
    assert alert is None
    assert detector.unread_alerts_count == 0

@pytest.mark.unit
def test_anomaly_detector_immediate_over_exit(temp_anomaly_detector):
    """2 IN -> 3 OUT: 3rd OUT triggers immediate inconsistency alert."""
    detector = temp_anomaly_detector

    # 2 tanks come IN
    detector.record_event("IN", track_id=1, timestamp=10.0)
    detector.record_event("IN", track_id=2, timestamp=11.0)

    # 1st and 2nd OUT (normal)
    detector.record_event("OUT", track_id=1, timestamp=30.0)
    detector.record_event("OUT", track_id=2, timestamp=32.0)
    assert detector.unread_alerts_count == 0

    # 3rd OUT (Anomaly! 3 OUT vs 2 IN)
    alert = detector.record_event("OUT", track_id=3, timestamp=35.0)
    assert alert is not None
    assert alert["in_count"] == 2
    assert alert["out_count"] == 3
    assert alert["discrepancy"] == 1
    assert detector.unread_alerts_count == 1

@pytest.mark.unit
def test_anomaly_detector_under_exit_timeout(temp_anomaly_detector):
    """2 IN -> 1 OUT: timeout after idle threshold from last exit triggers missing tank alert."""
    detector = temp_anomaly_detector

    # 2 tanks come IN
    detector.record_event("IN", track_id=1, timestamp=10.0)
    detector.record_event("IN", track_id=2, timestamp=11.0)

    # 1 tank goes OUT at t=30
    detector.record_event("OUT", track_id=1, timestamp=30.0)

    # Before idle timeout (only 5s elapsed after exit)
    assert detector.check_idle_timeout(current_time=35.0) is None

    # After idle timeout (20s elapsed after last exit > 15s threshold)
    alert = detector.check_idle_timeout(current_time=50.0)
    assert alert is not None
    assert alert["in_count"] == 2
    assert alert["out_count"] == 1
    assert alert["discrepancy"] == -1
    assert detector.unread_alerts_count == 1

@pytest.mark.unit
def test_anomaly_detector_zero_exit_window_timeout(temp_anomaly_detector):
    """2 IN -> 0 OUT: waits full 60s window before triggering missing tanks alert."""
    detector = temp_anomaly_detector

    # 2 tanks come IN at t=10
    detector.record_event("IN", track_id=1, timestamp=10.0)
    detector.record_event("IN", track_id=2, timestamp=11.0)

    # At t=35s (25s after IN), 0 exits yet -> should NOT trigger alert because window is 60s
    assert detector.check_idle_timeout(current_time=35.0) is None
    assert detector.unread_alerts_count == 0

    # At t=75s (65s after first IN > 60s window), triggers 0 out timeout alert
    alert = detector.check_idle_timeout(current_time=75.0)
    assert alert is not None
    assert alert["in_count"] == 2
    assert alert["out_count"] == 0
    assert alert["discrepancy"] == -2
    assert detector.unread_alerts_count == 1

@pytest.mark.unit
def test_anomaly_detector_spanish_localization(tmp_path):
    """Verifies that alerts are generated in Spanish when language is 'es'."""
    db_file = str(tmp_path / "test_anomaly_es.db")
    db_mgr = DatabaseManager(db_path=db_file)
    repo = DailyCountRepository(db_manager=db_mgr)
    i18n = I18nManager(locales_dir="locales", default_lang="es")
    i18n.set_language("es")

    detector = AnomalyDetector(
        enabled=True,
        window_seconds=60.0,
        batch_idle_seconds=15.0,
        db=repo,
        i18n=i18n
    )

    detector.record_event("IN", track_id=1, timestamp=10.0)
    detector.record_event("IN", track_id=2, timestamp=11.0)
    alert = detector.record_event("OUT", track_id=3, timestamp=12.0)
    alert = detector.record_event("OUT", track_id=4, timestamp=13.0)
    alert = detector.record_event("OUT", track_id=5, timestamp=14.0)

    assert alert is not None
    assert "Inconsistencia Detectada" in alert["message"]
    assert "SALIERON" in alert["message"]

@pytest.mark.unit
def test_anomaly_detector_reset_and_clear(temp_anomaly_detector):
    detector = temp_anomaly_detector

    detector.record_event("IN", track_id=1, timestamp=10.0)
    detector.record_event("OUT", track_id=1, timestamp=20.0)
    detector.record_event("OUT", track_id=2, timestamp=21.0)  # triggers alert (2 OUT vs 1 IN)

    assert detector.unread_alerts_count == 1
    detector.clear_alerts()
    assert detector.unread_alerts_count == 0
    assert detector.latest_alert is None
