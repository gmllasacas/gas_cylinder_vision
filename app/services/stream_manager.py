import os
import time
import threading
from typing import Optional, List, Dict, Any
from app.core import settings, logger, i18n
from app.cv import (
    VideoCaptureManager,
    YOLODetector,
    LineCrossingCounter,
    FrameRenderer,
    CVPipeline,
    SUPPORTED_EXTENSIONS,
)

class VideoStreamService:
    """High-level service managing video streaming, controls, telemetry, and background worker loop."""

    def __init__(self):
        self.lock = threading.Lock()
        self.settings = settings
        self.i18n = i18n

        # Ensure storage directories
        os.makedirs(self.settings.videos_dir, exist_ok=True)
        os.makedirs(self.settings.models_dir, exist_ok=True)

        # 1. Initialize CV Components
        self.capture = VideoCaptureManager(
            reconnect_interval_sec=self.settings.source.reconnect_interval_sec
        )
        self.detector = YOLODetector(
            models_dir=self.settings.models_dir,
            default_model=self.settings.detector.default_model,
            fallback_model=self.settings.detector.fallback_model,
            confidence=self.settings.detector.confidence,
            imgsz=self.settings.detector.imgsz,
            frame_skip=self.settings.detector.frame_skip,
            line_points=self.settings.detector.line_points
        )
        self.counter = LineCrossingCounter(line_points=self.settings.detector.line_points)
        self.renderer = FrameRenderer(
            i18n=self.i18n,
            output_width=self.settings.streaming.output_width,
            jpeg_quality=self.settings.streaming.jpeg_quality,
            line_points=self.settings.detector.line_points
        )
        self.pipeline = CVPipeline(
            detector=self.detector,
            counter=self.counter,
            renderer=self.renderer,
            debug_mode=True
        )

        # 2. Source Configuration
        self.current_source_id = ""
        self.current_video_name = ""
        self.is_paused = False
        self.playback_speed = 1.0
        self.last_frame_bytes: Optional[bytes] = None
        self.running = True
        self.new_frame_event = threading.Event()

        # Initialize Source from Settings
        self._init_source_from_settings()

        # 3. Dedicated Background Worker Thread
        self.worker_thread = threading.Thread(target=self._worker_loop, daemon=True)
        self.worker_thread.start()

    def _init_source_from_settings(self):
        src_cfg = self.settings.source
        if src_cfg.type == "camera":
            self.current_source_id = "live_camera"
            self.current_video_name = src_cfg.camera_name
            target_path = src_cfg.camera_url
        else:
            self.current_source_id = src_cfg.video_file
            self.current_video_name = src_cfg.video_file
            target_path = os.path.join(self.settings.videos_dir, src_cfg.video_file)

        self._connect_source(target_path)

    def _emit_standby_frame(self):
        standby_canvas = self.renderer.generate_standby_canvas(
            source_path=self.capture.current_source_path,
            is_file_missing=self.capture.is_file_missing,
            reconnect_interval_sec=self.capture.reconnect_interval_sec
        )
        encoded = self.renderer.encode_jpeg(standby_canvas)
        if encoded:
            self.last_frame_bytes = encoded
            self.new_frame_event.set()

    def _connect_source(self, target_path: str) -> bool:
        success, initial_frame = self.capture.open(target_path)
        if success and initial_frame is not None:
            self.pipeline.reset()
            self.last_frame_bytes = self.pipeline.process_frame(initial_frame)
            self.new_frame_event.set()
            return True
        else:
            self._emit_standby_frame()
            return False

    def get_available_videos(self) -> List[str]:
        if not os.path.exists(self.settings.videos_dir):
            return []
        files = [
            f for f in os.listdir(self.settings.videos_dir)
            if os.path.isfile(os.path.join(self.settings.videos_dir, f)) and f.lower().endswith(SUPPORTED_EXTENSIONS)
        ]
        files.sort()
        return files

    def get_available_sources(self) -> List[Dict[str, Any]]:
        sources = []
        src_cfg = self.settings.source
        if src_cfg.camera_url:
            sources.append({
                "type": "camera",
                "id": "live_camera",
                "name": f"🎥 {src_cfg.camera_name}",
                "url": src_cfg.camera_url
            })
        for v in self.get_available_videos():
            sources.append({
                "type": "file",
                "id": v,
                "name": f"📁 {v}",
                "url": v
            })
        return sources

    def change_source(self, source_id: str) -> bool:
        with self.lock:
            src_cfg = self.settings.source
            if source_id == "live_camera" and src_cfg.camera_url:
                target_path = src_cfg.camera_url
                self.current_source_id = "live_camera"
                self.current_video_name = src_cfg.camera_name
            else:
                target_path = os.path.join(self.settings.videos_dir, os.path.basename(source_id))
                self.current_source_id = os.path.basename(source_id)
                self.current_video_name = os.path.basename(source_id)

            return self._connect_source(target_path)

    def change_video(self, video_name: str) -> bool:
        return self.change_source(video_name)

    def set_conf(self, conf_val: float):
        with self.lock:
            self.detector.set_confidence(conf_val)

    def set_imgsz(self, imgsz_val: int):
        with self.lock:
            self.detector.set_imgsz(imgsz_val)

    def set_frame_skip(self, skip_val: int):
        with self.lock:
            self.detector.set_frame_skip(skip_val)

    def set_playback_speed(self, speed_multiplier: float):
        with self.lock:
            self.playback_speed = max(0.25, min(10.0, speed_multiplier))

    def set_lang(self, lang_code: str):
        with self.lock:
            self.i18n.set_language(lang_code)

    def set_debug_mode(self, enabled: bool):
        with self.lock:
            self.pipeline.debug_mode = enabled
            return self.pipeline.debug_mode

    def toggle_debug_mode(self):
        with self.lock:
            self.pipeline.debug_mode = not self.pipeline.debug_mode
            return self.pipeline.debug_mode

    def set_pause(self, paused: bool):
        with self.lock:
            self.is_paused = paused

    def toggle_pause(self):
        with self.lock:
            self.is_paused = not self.is_paused
            return self.is_paused

    def seek_frame(self, target_frame: int):
        with self.lock:
            success, frame = self.capture.seek_frame(target_frame)
            if success and frame is not None:
                self.last_frame_bytes = self.pipeline.process_frame(frame)
                self.new_frame_event.set()

    def seek_offset(self, seconds_offset: float):
        with self.lock:
            success, frame = self.capture.seek_offset(seconds_offset)
            if success and frame is not None:
                self.last_frame_bytes = self.pipeline.process_frame(frame)
                self.new_frame_event.set()

    def step(self, delta_frames: int):
        with self.lock:
            success, frame = self.capture.step(delta_frames)
            if success and frame is not None:
                self.last_frame_bytes = self.pipeline.process_frame(frame)
                self.new_frame_event.set()

    def reset(self):
        with self.lock:
            self.pipeline.reset()
            if not self.capture.is_live_stream and not self.capture.is_file_missing:
                success, frame = self.capture.reset_position()
                if success and frame is not None:
                    self.last_frame_bytes = self.pipeline.process_frame(frame)
                    self.new_frame_event.set()

    @property
    def config(self) -> Dict[str, Any]:
        """Backward-compatible dict export of current settings."""
        return self.settings.to_dict()

    @property
    def is_live_stream(self) -> bool:
        return self.capture.is_live_stream

    def get_status(self) -> Dict[str, Any]:
        with self.lock:
            cur_frame = self.capture.current_frame
            tot_frames = self.capture.total_frames
            vid_fps = self.capture.video_fps

            current_time = (cur_frame / vid_fps) if (not self.capture.is_live_stream and not self.capture.is_file_missing and vid_fps > 0) else 0.0
            duration = (tot_frames / vid_fps) if (not self.capture.is_live_stream and not self.capture.is_file_missing and vid_fps > 0) else 0.0

            return {
                "current_video": self.current_video_name,
                "current_source_id": self.current_source_id,
                "is_live": self.capture.is_live_stream,
                "is_file_missing": self.capture.is_file_missing,
                "camera_connected": self.capture.camera_connected,
                "connection_error_msg": self.capture.connection_error_msg,
                "active_model": os.path.basename(self.detector.active_model_path),
                "conf": self.detector.confidence,
                "imgsz": self.detector.imgsz,
                "frame_skip": self.detector.frame_skip,
                "playback_speed": self.playback_speed,
                "output_width": self.renderer.output_width,
                "lang": self.i18n.current_lang,
                "video_native_fps": round(vid_fps, 1),
                "actual_stream_fps": round(self.pipeline.actual_processed_fps, 1),
                "max_hardware_fps": round(self.pipeline.max_compute_fps, 1),
                "ai_latency_ms": round(self.pipeline.inference_time_ms, 1),
                "encode_latency_ms": round(self.pipeline.encode_time_ms, 1),
                "debug_mode": self.pipeline.debug_mode,
                "current_frame": cur_frame,
                "total_frames": tot_frames,
                "fps": round(self.pipeline.actual_processed_fps, 1),
                "current_time": round(current_time, 2),
                "duration": round(duration, 2),
                "is_paused": self.is_paused,
                "loop": self.capture.loop,
                "in_count": self.counter.in_count,
                "out_count": self.counter.out_count,
                "net_count": self.counter.in_count - self.counter.out_count,
                "active_tracks": self.counter.active_tracks_count
            }

    def _worker_loop(self):
        """Background thread executing capture loop, auto-reconnects, and frame processing."""
        while self.running:
            effective_fps = self.capture.video_fps * self.playback_speed
            target_delay = 1.0 / effective_fps if effective_fps > 0 else 0.04
            start_t = time.time()

            if not self.is_paused:
                with self.lock:
                    if self.capture.is_file_missing:
                        now = time.time()
                        if (now - self.capture.last_reconnect_attempt) >= 2.0:
                            self.capture.last_reconnect_attempt = now
                            if os.path.exists(self.capture.current_source_path):
                                self._connect_source(self.capture.current_source_path)
                            else:
                                self._emit_standby_frame()
                    elif self.capture.is_live_stream:
                        if not self.capture.cap.isOpened() or not self.capture.camera_connected:
                            now = time.time()
                            if (now - self.capture.last_reconnect_attempt) >= self.capture.reconnect_interval_sec:
                                self._connect_source(self.capture.current_source_path)
                            else:
                                self._emit_standby_frame()
                        else:
                            success, frame = self.capture.read_frame()
                            if success and frame is not None:
                                self.last_frame_bytes = self.pipeline.process_frame(frame)
                                self.new_frame_event.set()
                            else:
                                self._emit_standby_frame()
                    else:
                        success, frame = self.capture.read_frame()
                        if success and frame is not None:
                            self.last_frame_bytes = self.pipeline.process_frame(frame)
                            self.new_frame_event.set()
                        elif not self.capture.loop:
                            self.is_paused = True

            elapsed = time.time() - start_t
            sleep_time = max(0.001, target_delay - elapsed) if (
                not self.is_paused and 
                not self.capture.is_file_missing and 
                (not self.capture.is_live_stream or self.capture.camera_connected)
            ) else 0.4
            time.sleep(sleep_time)

    def generate_frames(self):
        """Yields multipart MJPEG frame chunks for HTTP StreamingResponse."""
        last_sent = None
        try:
            while self.running:
                frame_data = self.last_frame_bytes
                if frame_data is not None and frame_data is not last_sent:
                    last_sent = frame_data
                    yield (b'--frame\r\n'
                           b'Content-Type: image/jpeg\r\n\r\n' + frame_data + b'\r\n')
                time.sleep(0.015)
        except (GeneratorExit, Exception):
            pass

# Singleton instance
video_service = VideoStreamService()
