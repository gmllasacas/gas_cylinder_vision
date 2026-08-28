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

@pytest.mark.unit
def test_counter_square_region_inbound():
    """Square region: object appears inside (no count), then crosses boundary going outside (counts IN)."""
    square = [[100, 200], [300, 200], [300, 400], [100, 400]]
    counter = LineCrossingCounter(line_points=square)

    # Frame 1: Object appears / is recognized inside square (y=250) -> registered inside, NO count yet
    counter.update_tracks([([190, 240, 210, 260], 0.9, 0, 1)])
    assert counter.in_count == 0
    assert counter.out_count == 0
    assert 1 in counter.tracks_inside_polygon

    # Frame 2: Object moves still inside square (y=350) -> NO count
    counter.update_tracks([([190, 340, 210, 360], 0.9, 0, 1)])
    assert counter.in_count == 0
    assert counter.out_count == 0

    # Frame 3: Object crosses boundary going outside (y=450) -> counts as IN ("going outside as in")!
    counter.update_tracks([([190, 440, 210, 460], 0.9, 0, 1)])
    assert counter.in_count == 1
    assert counter.out_count == 0
    assert 1 not in counter.tracks_inside_polygon

    # Frame 4: Object continues outside -> NO duplicate count
    counter.update_tracks([([190, 490, 210, 510], 0.9, 0, 1)])
    assert counter.in_count == 1
    assert counter.out_count == 0

@pytest.mark.unit
def test_counter_square_region_outbound():
    """Square region: object comes from outside and crosses boundary going inside (counts OUT)."""
    square = [[100, 200], [300, 200], [300, 400], [100, 400]]
    counter = LineCrossingCounter(line_points=square)

    # Frame 1: Object is outside square (y=450) -> NO count
    counter.update_tracks([([190, 440, 210, 460], 0.9, 0, 2)])
    assert counter.in_count == 0
    assert counter.out_count == 0
    assert 2 not in counter.tracks_inside_polygon

    # Frame 2: Object crosses boundary going inside (y=300) -> counts as OUT ("going inside as out")!
    counter.update_tracks([([190, 290, 210, 310], 0.9, 0, 2)])
    assert counter.in_count == 0
    assert counter.out_count == 1
    assert 2 in counter.tracks_inside_polygon

    # Frame 3: Object continues inside square -> NO duplicate count
    counter.update_tracks([([190, 250, 210, 270], 0.9, 0, 2)])
    assert counter.in_count == 0
    assert counter.out_count == 1



