import time
from typing import Optional, List
import numpy as np
from app.core.logging import logger
from app.cv.detector import YOLODetector
from app.cv.counter import LineCrossingCounter
from app.cv.renderer import FrameRenderer

class CVPipeline:
    """Orchestrates detection, trajectory analysis, line-crossing counting, overlay rendering, and telemetry."""

    def __init__(
        self,
        detector: YOLODetector,
        counter: LineCrossingCounter,
        renderer: FrameRenderer,
        debug_mode: bool = True
    ):
        self.detector = detector
        self.counter = counter
        self.renderer = renderer
        self.debug_mode = debug_mode

        # Telemetry & Performance Benchmarks
        self.inference_time_ms = 0.0
        self.encode_time_ms = 0.0
        self.total_process_time_ms = 0.0
        self.actual_processed_fps = 0.0
        self.max_compute_fps = 0.0
        self._fps_frame_times: List[float] = []

    def process_frame(self, frame: np.ndarray) -> Optional[bytes]:
        """
        Executes full CV pipeline on a pristine raw frame:
        1. YOLO Object Detection & Tracking
        2. Trajectory updates & Line Crossing calculation
        3. Visual annotations & Debug Overlays
        4. Resolution resizing & JPEG compression
        """
        t_start = time.time()
        pristine_frame = frame.copy()

        # 1. AI Inference & Tracking
        t_infer_start = time.time()
        boxes_list = self.detector.detect_and_track(frame)
        t_infer_end = time.time()
        self.inference_time_ms = (t_infer_end - t_infer_start) * 1000.0

        # 2. Update Counter
        self.counter.update_tracks(boxes_list)
        self.counter.sync_external_counts(self.detector.counter)

        # 3. Visual Annotations
        if self.debug_mode:
            annotated_frame = self.renderer.draw_overlays(
                frame=pristine_frame,
                boxes_list=boxes_list,
                track_history=self.counter.track_history,
                get_class_name_fn=self.detector.get_class_name
            )
        else:
            annotated_frame = pristine_frame

        # 4. Encoding
        t_enc_start = time.time()
        frame_bytes = self.renderer.encode_jpeg(annotated_frame)
        t_enc_end = time.time()
        self.encode_time_ms = (t_enc_end - t_enc_start) * 1000.0

        # 5. Performance Metrics
        self.total_process_time_ms = (t_enc_end - t_start) * 1000.0
        if self.total_process_time_ms > 0:
            self.max_compute_fps = round(1000.0 / self.total_process_time_ms, 1)

        now = time.time()
        self._fps_frame_times.append(now)
        if len(self._fps_frame_times) > 30:
            self._fps_frame_times.pop(0)
        if len(self._fps_frame_times) >= 2:
            time_span = self._fps_frame_times[-1] - self._fps_frame_times[0]
            if time_span > 0:
                self.actual_processed_fps = round((len(self._fps_frame_times) - 1) / time_span, 1)

        return frame_bytes

    def reset(self):
        """Resets detector cache, counter tracks, and timing buffers."""
        self.detector.reset()
        self.counter.reset()
        self._fps_frame_times.clear()
