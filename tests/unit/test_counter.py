import pytest
from app.cv.counter import LineCrossingCounter

@pytest.mark.unit
def test_counter_initial_state():
    counter = LineCrossingCounter(line_points=[[100, 200], [500, 200]])
    assert counter.in_count == 0
    assert counter.out_count == 0
    assert counter.active_tracks_count == 0

@pytest.mark.unit
def test_counter_inbound_crossing():
    """Object moving downwards (y: 150 -> 250) across horizontal line y=200."""
    counter = LineCrossingCounter(line_points=[[100, 200], [500, 200]])
    
    # Frame 1: Object above line (y=150)
    counter.update_tracks([([190, 140, 210, 160], 0.9, 0, 1)])
    assert counter.in_count == 0

    # Frame 2: Object crossed below line (y=250)
    counter.update_tracks([([190, 240, 210, 260], 0.9, 0, 1)])
    assert counter.in_count == 1
    assert counter.out_count == 0

    # Frame 3: Object continues below line (should not count again)
    counter.update_tracks([([190, 280, 210, 300], 0.9, 0, 1)])
    assert counter.in_count == 1

@pytest.mark.unit
def test_counter_outbound_crossing():
    """Object moving upwards (y: 250 -> 150) across horizontal line y=200."""
    counter = LineCrossingCounter(line_points=[[100, 200], [500, 200]])
    
    # Frame 1: Object below line (y=250)
    counter.update_tracks([([190, 240, 210, 260], 0.9, 0, 2)])
    assert counter.out_count == 0

    # Frame 2: Object crossed above line (y=150)
    counter.update_tracks([([190, 140, 210, 160], 0.9, 0, 2)])
    assert counter.out_count == 1
    assert counter.in_count == 0

@pytest.mark.unit
def test_counter_reset():
    counter = LineCrossingCounter(line_points=[[100, 200], [500, 200]])
    counter.in_count = 5
    counter.out_count = 3
    counter.reset()
    assert counter.in_count == 0
    assert counter.out_count == 0
    assert len(counter.track_history) == 0

@pytest.mark.unit
def test_counter_callback():
    crossings = []
    def on_cross(direction, track_id):
        crossings.append((direction, track_id))

    counter = LineCrossingCounter(line_points=[[100, 200], [500, 200]], on_crossing=on_cross)
    counter.update_tracks([([190, 140, 210, 160], 0.9, 0, 1)])
    counter.update_tracks([([190, 240, 210, 260], 0.9, 0, 1)])

    assert len(crossings) == 1
    assert crossings[0] == ("IN", 1)

@pytest.mark.unit
def test_counter_set_counts():
    counter = LineCrossingCounter(line_points=[[100, 200], [500, 200]])
    counter.set_counts(in_count=42, out_count=18)
    assert counter.in_count == 42
    assert counter.out_count == 18

