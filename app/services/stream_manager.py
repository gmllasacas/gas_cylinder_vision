import os
import time
import threading
from typing import Optional, List, Dict, Any
from app.core import settings, logger, i18n
from app.db import db_repo
from app.services.anomaly_detector import AnomalyDetector
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
        self.db = db_repo

        # Ensure storage directories
        os.makedirs(self.settings.videos_dir, exist_ok=True)
        os.makedirs(self.settings.models_dir, exist_ok=True)
        os.makedirs(self.settings.data_dir, exist_ok=True)

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
        self.counter = LineCrossingCounter(
            line_points=self.settings.detector.line_points,
            on_crossing=self._on_line_crossing
        )
        # Load today's persistent counts from SQLite
        try:
            today_record = self.db.get_or_create_daily()
            self.counter.set_counts(
                today_record.get("in_count", 0),
                today_record.get("out_count", 0)
            )
        except Exception as e:
            logger.warning(f"Could not load today's count from database: {e}")

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

        # 2. Anomaly & Inconsistency Detection Engine
        self.anomaly_detector = AnomalyDetector(
            enabled=self.settings.anomaly.enabled,
            window_seconds=self.settings.anomaly.window_seconds,
            batch_idle_seconds=self.settings.anomaly.batch_idle_seconds,
            db=self.db
        )

        # 3. Source Configuration
        self.current_source_id = ""
        self.current_video_name = ""
        self.is_paused = False
        self.playback_speed = 1.0
        self.last_frame_bytes: Optional[bytes] = None
        self.running = True
        self.new_frame_event = threading.Event()

        # Initialize Source from Settings
        self._init_source_from_settings()

        # 4. Dedicated Background Worker Thread
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

    def _get_current_stream_time(self) -> float:
        if not self.capture.is_live_stream and not self.capture.is_file_missing and self.capture.video_fps > 0:
            return float(self.capture.current_frame) / float(self.capture.video_fps)
        return time.time()

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
            self.pipeline.reset(reset_counts=False)
            self.anomaly_detector.reset()
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
                self.anomaly_detector.reset()
                self.last_frame_bytes = self.pipeline.process_frame(frame)
                self.new_frame_event.set()

    def seek_offset(self, seconds_offset: float):
        with self.lock:
            success, frame = self.capture.seek_offset(seconds_offset)
            if success and frame is not None:
                self.anomaly_detector.reset()
                self.last_frame_bytes = self.pipeline.process_frame(frame)
                self.new_frame_event.set()

    def step(self, delta_frames: int):
        with self.lock:
            success, frame = self.capture.step(delta_frames)
            if success and frame is not None:
                self.last_frame_bytes = self.pipeline.process_frame(frame)
                self.new_frame_event.set()

    def _on_line_crossing(self, direction: str, track_id: int):
        """Callback invoked whenever an object crosses the detection line."""
        try:
            cur_frame = self.capture.current_frame if hasattr(self, 'capture') else 0
            cur_time = self._get_current_stream_time()
            self.db.record_crossing(
                direction=direction,
                track_id=track_id,
                source_id=self.current_source_id,
                frame_number=cur_frame
            )
            # Evaluate anomaly & batch consistency with synchronized stream time
            self.anomaly_detector.record_event(
                direction=direction,
                track_id=track_id,
                timestamp=cur_time,
                source_id=self.current_source_id
            )
        except Exception as e:
            logger.error(f"Error persisting line crossing event: {e}")

    def reset(self, reset_db: bool = True):
        with self.lock:
            self.pipeline.reset(reset_counts=reset_db)
            self.anomaly_detector.reset()
            if reset_db:
                try:
                    self.db.reset_daily_count()
                except Exception as e:
                    logger.error(f"Error resetting database counts: {e}")
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

            # Authoritative daily counts from SQLite DB
            try:
                today_record = self.db.get_or_create_daily()
                db_in = today_record.get("in_count", self.counter.in_count)
                db_out = today_record.get("out_count", self.counter.out_count)
                db_net = today_record.get("net_count", db_in - db_out)
            except Exception:
                db_in = self.counter.in_count
                db_out = self.counter.out_count
                db_net = self.counter.in_count - self.counter.out_count

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
                "in_count": db_in,
                "out_count": db_out,
                "net_count": db_net,
                "active_tracks": self.counter.active_tracks_count,
                "active_alerts_count": self.anomaly_detector.unread_alerts_count,
                "latest_alert": self.anomaly_detector.latest_alert
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

            # Periodic check for idle under-exit anomalies using synchronized stream time
            cur_time = self._get_current_stream_time()
            self.anomaly_detector.check_idle_timeout(current_time=cur_time, source_id=self.current_source_id)

            elapsed = time.time() - start_t
            sleep_time = max(0.001, target_delay - elapsed) if (
                not self.is_paused and 
                not self.capture.is_file_missing and 
                (not self.capture.is_live_stream or self.capture.camera_connected)
            ) else 0.4
            time.sleep(sleep_time)

    def stop(self):
        """Stops the worker loop and releases video capture resources."""
        self.running = False
        self.new_frame_event.set()
        if hasattr(self, 'capture'):
            try:
                self.capture.release()
            except Exception:
                pass
        logger.info("VideoStreamService stopped.")

# Singleton instance
video_service = VideoStreamService()
