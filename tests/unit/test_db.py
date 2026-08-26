import os
import tempfile
import threading
import pytest
from app.db.database import DatabaseManager
from app.db.repository import DailyCountRepository

@pytest.fixture
def temp_db():
    """Creates an isolated temporary database for testing."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        temp_path = f.name

    db_manager = DatabaseManager(db_path=temp_path)
    repo = DailyCountRepository(db_manager)

    yield repo

    # Cleanup
    if os.path.exists(temp_path):
        try:
            os.remove(temp_path)
        except Exception:
            pass

@pytest.mark.unit
def test_db_initial_state(temp_db: DailyCountRepository):
    record = temp_db.get_or_create_daily("2026-08-25")
    assert record["date"] == "2026-08-25"
    assert record["in_count"] == 0
    assert record["out_count"] == 0
    assert record["net_count"] == 0

@pytest.mark.unit
def test_db_record_crossing_in(temp_db: DailyCountRepository):
    record = temp_db.record_crossing(
        direction="IN",
        track_id=1,
        source_id="test.mp4",
        frame_number=42,
        target_date="2026-08-25"
    )
    assert record["in_count"] == 1
    assert record["out_count"] == 0
    assert record["net_count"] == 1

@pytest.mark.unit
def test_db_record_crossing_out(temp_db: DailyCountRepository):
    temp_db.record_crossing(direction="IN", track_id=1, target_date="2026-08-25")
    record = temp_db.record_crossing(direction="OUT", track_id=2, target_date="2026-08-25")
    assert record["in_count"] == 1
    assert record["out_count"] == 1
    assert record["net_count"] == 0

@pytest.mark.unit
def test_db_events_logging(temp_db: DailyCountRepository):
    temp_db.record_crossing(direction="IN", track_id=10, source_id="cam1", frame_number=100, target_date="2026-08-25")
    temp_db.record_crossing(direction="OUT", track_id=11, source_id="cam1", frame_number=105, target_date="2026-08-25")
    
    events = temp_db.get_events(limit=10, target_date="2026-08-25")
    assert len(events) == 2
    assert events[0]["direction"] == "OUT"
    assert events[0]["track_id"] == 11
    assert events[1]["direction"] == "IN"
    assert events[1]["track_id"] == 10

@pytest.mark.unit
def test_db_history(temp_db: DailyCountRepository):
    temp_db.set_daily_counts(in_count=10, out_count=5, target_date="2026-08-24")
    temp_db.set_daily_counts(in_count=20, out_count=8, target_date="2026-08-25")

    history = temp_db.get_history(limit=10)
    assert len(history) == 2
    assert history[0]["date"] == "2026-08-25"
    assert history[0]["net_count"] == 12
    assert history[1]["date"] == "2026-08-24"
    assert history[1]["net_count"] == 5

@pytest.mark.unit
def test_db_reset_daily(temp_db: DailyCountRepository):
    temp_db.set_daily_counts(in_count=15, out_count=7, target_date="2026-08-25")
    record = temp_db.reset_daily_count(target_date="2026-08-25")
    assert record["in_count"] == 0
    assert record["out_count"] == 0
    assert record["net_count"] == 0

@pytest.mark.unit
def test_db_concurrent_crossings(temp_db: DailyCountRepository):
    """Test thread-safety with concurrent crossing records."""
    num_threads = 10
    crossings_per_thread = 20

    def worker():
        for _ in range(crossings_per_thread):
            temp_db.record_crossing(direction="IN", target_date="2026-08-25")

    threads = [threading.Thread(target=worker) for _ in range(num_threads)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    record = temp_db.get_daily_count("2026-08-25")
    assert record is not None
    assert record["in_count"] == num_threads * crossings_per_thread

