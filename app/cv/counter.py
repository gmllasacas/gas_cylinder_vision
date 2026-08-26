from typing import List, Tuple, Dict, Set, Optional, Any

class LineCrossingCounter:
    """Tracks object trajectories and computes directional line crossings."""

    def __init__(self, line_points: Optional[List[List[int]]] = None):
        self.line_points = [tuple(p) for p in (line_points or [[1200, 400], [1700, 400]])]
        self.in_count = 0
        self.out_count = 0
        self.active_tracks_count = 0
        self.track_history: Dict[int, List[Tuple[int, int]]] = {}
        self.counted_in_ids: Set[int] = set()
        self.counted_out_ids: Set[int] = set()

    def set_line_points(self, points: List[List[int]]):
        self.line_points = [tuple(p) for p in points]

    def update_tracks(self, boxes_list: List[Tuple[List[float], float, int, Optional[int]]]):
        """Updates center point histories and evaluates line crossings for all active tracks."""
        self.active_tracks_count = len(boxes_list)
        current_active_ids = set()

        for xyxy, conf, cls_id, track_id in boxes_list:
            if len(xyxy) == 4 and track_id is not None:
                current_active_ids.add(track_id)
                x1, y1, x2, y2 = map(int, xyxy)
                cx, cy = (x1 + x2) // 2, (y1 + y2) // 2

                if track_id not in self.track_history:
                    self.track_history[track_id] = []
                self.track_history[track_id].append((cx, cy))
                
                # Keep max 30 history points per track
                if len(self.track_history[track_id]) > 30:
                    self.track_history[track_id].pop(0)

                self._check_crossing(track_id, cx, cy)

        # Cleanup stale tracks no longer in view
        stale_ids = [tid for tid in self.track_history if tid not in current_active_ids]
        if len(stale_ids) > 100:
            for tid in stale_ids[:50]:
                self.track_history.pop(tid, None)

    def _check_crossing(self, track_id: int, cx: int, cy: int):
        """
        Directional counting rule:
        - Downwards (y increasing, going below line) = IN
        - Upwards (y decreasing, going above line) = OUT
        """
        if len(self.line_points) < 2:
            return

        x1, y1 = self.line_points[0]
        x2, y2 = self.line_points[1]

        min_x = min(x1, x2)
        max_x = max(x1, x2)
        line_y = (y1 + y2) / 2.0

        # Check horizontal boundary with 50px tolerance
        if not (min_x - 50 <= cx <= max_x + 50):
            return

        history = self.track_history.get(track_id, [])
        if len(history) >= 2:
            prev_cx, prev_cy = history[-2]

            # 1. Going Below (Top -> Bottom): previous was above line, current is at/below line
            if prev_cy < line_y and cy >= line_y:
                if track_id not in self.counted_in_ids:
                    self.in_count += 1
                    self.counted_in_ids.add(track_id)
                    self.counted_out_ids.discard(track_id)

            # 2. Going Above (Bottom -> Top): previous was below line, current is at/above line
            elif prev_cy > line_y and cy <= line_y:
                if track_id not in self.counted_out_ids:
                    self.out_count += 1
                    self.counted_out_ids.add(track_id)
                    self.counted_in_ids.discard(track_id)

    def sync_external_counts(self, counter_instance: Any):
        """Optional synchronization with Ultralytics ObjectCounter counts."""
        if counter_instance is None:
            return

        if hasattr(counter_instance, "in_count"):
            c_in = getattr(counter_instance, "in_count", None)
            if isinstance(c_in, (int, float)):
                self.in_count = int(c_in)

        if hasattr(counter_instance, "out_count"):
            c_out = getattr(counter_instance, "out_count", None)
            if isinstance(c_out, (int, float)):
                self.out_count = int(c_out)

        if hasattr(counter_instance, "counts"):
            counts_obj = getattr(counter_instance, "counts", None)
            if isinstance(counts_obj, dict):
                if "IN" in counts_obj:
                    self.in_count = int(counts_obj["IN"])
                if "OUT" in counts_obj:
                    self.out_count = int(counts_obj["OUT"])

    def reset(self):
        """Resets all track histories and counter values."""
        self.in_count = 0
        self.out_count = 0
        self.active_tracks_count = 0
        self.track_history.clear()
        self.counted_in_ids.clear()
        self.counted_out_ids.clear()
