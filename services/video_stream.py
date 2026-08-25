import os
import json
import time
import threading
from typing import Optional, List, Dict, Set, Any
import numpy as np
import cv2
from ultralytics import solutions

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VIDEOS_DIR = os.path.join(BASE_DIR, "videos")
LOCALES_DIR = os.path.join(BASE_DIR, "locales")
MODELS_DIR = os.path.join(BASE_DIR, "models")
CONFIG_PATH = os.path.join(BASE_DIR, "config.json")

SUPPORTED_EXTENSIONS = ('.mp4', '.avi', '.mov', '.mkv', '.webm')

DEFAULT_CONFIG = {
    "source": {
        "type": "video",
        "video_file": "1min_test.mp4",
        "camera_url": "rtsp://admin:password@192.168.1.100:554/stream1",
        "camera_name": "IP Camera",
        "reconnect_interval_sec": 3
    },
    "language": "es",
    "detector": {
        "default_model": "best.pt",
        "fallback_model": "yolov8n.pt",
        "confidence": 0.50,
        "imgsz": 640,
        "frame_skip": 2,
        "line_points": [[1200, 400], [1700, 400]]
    },
    "streaming": {
        "output_width": 1024,
        "jpeg_quality": 70
    }
}

def load_config() -> Dict[str, Any]:
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, 'r', encoding='utf-8') as fp:
                return json.load(fp)
        except Exception as e:
            print(f"[Warning] Error reading config.json: {e}")
    return DEFAULT_CONFIG

def load_locales_dict() -> Dict[str, Any]:
    locales = {}
    if os.path.exists(LOCALES_DIR):
        for f in os.listdir(LOCALES_DIR):
            if f.lower().endswith('.json'):
                code = f[:-5].lower()
                try:
                    with open(os.path.join(LOCALES_DIR, f), 'r', encoding='utf-8') as fp:
                        locales[code] = json.load(fp)
                except Exception as e:
                    print(f"[Warning] Error loading locale {f}: {e}")
    return locales

class VideoStreamService:
    def __init__(self, videos_dir: str = VIDEOS_DIR, models_dir: str = MODELS_DIR):
        self.videos_dir = videos_dir
        self.models_dir = models_dir
        self.lock = threading.Lock()
        
        # Load external configuration & locales
        self.config = load_config()
        self.locales = load_locales_dict()
        self.lang = self.config.get("language", "es")
        
        # Ensure directories exist
        os.makedirs(self.videos_dir, exist_ok=True)
        os.makedirs(self.models_dir, exist_ok=True)
        
        # Configure media source directly from config.json
        src_cfg = self.config.get("source", {})
        source_type = src_cfg.get("type", "video").lower()
        self.reconnect_interval_sec = src_cfg.get("reconnect_interval_sec", 3)
        self.last_reconnect_attempt = 0.0
        self.camera_connected = False
        self.is_file_missing = False
        self.connection_error_msg = ""
        
        if source_type == "camera":
            self.is_live_stream = True
            self.current_video_name = src_cfg.get("camera_name", "IP Camera")
            self.current_source_id = "live_camera"
            self.current_source_path = src_cfg.get("camera_url", "")
        else:
            self.is_live_stream = False
            video_name = src_cfg.get("video_file", "1min_test.mp4")
            self.current_video_name = video_name
            self.current_source_id = video_name
            self.current_source_path = os.path.join(self.videos_dir, video_name)
            
        # Performance & Tuning Parameters from config
        det_cfg = self.config.get("detector", {})
        stream_cfg = self.config.get("streaming", {})
        self.conf = det_cfg.get("confidence", 0.50)
        self.imgsz = det_cfg.get("imgsz", 640)
        self.frame_skip = det_cfg.get("frame_skip", 2)
        self.output_width = stream_cfg.get("output_width", 1024)
        self.jpeg_quality = stream_cfg.get("jpeg_quality", 70)
        
        # Counting line: [(x1, y), (x2, y)]
        cfg_line = det_cfg.get("line_points", [[1200, 400], [1700, 400]])
        self.line_points = [tuple(p) for p in cfg_line]
        self.last_frame_bytes: Optional[bytes] = None
        
        # Video properties & timing defaults
        self.total_frames = 0
        self.video_fps = 25.0
        self.fps = 25.0
        self.current_frame = 0
        self.is_paused = False
        self.loop = True
        self.playback_speed = 1.0
        
        # Resolve active model from models/
        best_model_path = os.path.join(self.models_dir, "best.pt")
        yolo_model_path = os.path.join(self.models_dir, "yolov8n.pt")
        if os.path.exists(best_model_path):
            self.active_model = best_model_path
        elif os.path.exists(yolo_model_path):
            self.active_model = yolo_model_path
        elif os.path.exists(os.path.join(BASE_DIR, "best.pt")):
            self.active_model = os.path.join(BASE_DIR, "best.pt")
        else:
            self.active_model = "yolov8n.pt"
            
        self.frame_counter = 0
        self.last_results = None
        self.last_boxes_list = []
        self.debug_mode = True
        
        # Telemetry & Performance Benchmark Stats
        self.inference_time_ms = 0.0
        self.encode_time_ms = 0.0
        self.total_process_time_ms = 0.0
        self.actual_processed_fps = 0.0
        self.max_compute_fps = 0.0
        self._fps_frame_times = []
        
        # Counting & Trajectory Tracking
        self.in_count = 0
        self.out_count = 0
        self.active_tracks_count = 0
        self.track_history: Dict[int, List[tuple]] = {}
        self.counted_in_ids: Set[int] = set()
        self.counted_out_ids: Set[int] = set()
        
        self._init_counter()
        
        # Background Worker Synchronization
        self.running = True
        self.new_frame_event = threading.Event()
        
        # Initialize capture & connect to stream / file
        self.cap = cv2.VideoCapture()
        self._connect_stream(self.current_source_path)

        # Dedicated Background Worker Thread
        self.worker_thread = threading.Thread(target=self._worker_loop, daemon=True)
        self.worker_thread.start()

    def _is_live_url(self, source: str) -> bool:
        """Check if source is an RTSP/HTTP/RTMP camera stream or device index."""
        if not isinstance(source, str):
            return False
        return source.startswith(("rtsp://", "rtmp://", "http://", "https://")) or source.isdigit()

    def _mask_url_credentials(self, url: str) -> str:
        """Mask password in RTSP URLs for secure display (rtsp://user:****@ip...)."""
        if "@" in url and "://" in url:
            try:
                protocol, rest = url.split("://", 1)
                user_info, host_info = rest.split("@", 1)
                if ":" in user_info:
                    username, _ = user_info.split(":", 1)
                    return f"{protocol}://{username}:****@{host_info}"
                return f"{protocol}://****@{host_info}"
            except Exception:
                pass
        return url

    def _generate_standby_frame(self) -> np.ndarray:
        """Generates visual status canvas (Video File Missing / Camera Offline)."""
        width = self.output_width
        height = int(width * 9 / 16)
        
        # Dark Slate-950 background
        frame = np.full((height, width, 3), (15, 23, 42), dtype=np.uint8)
        
        # Draw Alert Card
        pad_x, pad_y = 50, 40
        cv2.rectangle(frame, (pad_x, pad_y), (width - pad_x, height - pad_y), (30, 41, 59), -1)
        cv2.rectangle(frame, (pad_x, pad_y), (width - pad_x, height - pad_y), (239, 68, 68), 2)
        
        center_y = height // 2
        
        # Resolve localized text from JSON
        locale_data = self.locales.get(self.lang, self.locales.get("en", {}))
        video_i18n = locale_data.get("video", {})
        
        if self.is_file_missing:
            title_text = video_i18n.get("file_missing_title", "VIDEO FILE NOT FOUND")
            sub_text = video_i18n.get("file_missing_subtitle", "Place the file inside videos/ or update config.json")
            target_str = f"Missing Target: videos/{os.path.basename(self.current_source_path)}"
            retry_text = "Waiting for video file..."
        else:
            title_text = video_i18n.get("offline_title", "CAMERA OFFLINE / UNREACHABLE")
            sub_text = video_i18n.get("offline_subtitle", "Check RTSP URL, Network connection or Credentials")
            target_str = f"Stream Target: {self._mask_url_credentials(self.current_source_path)}"
            retry_text = f"{video_i18n.get('offline_retry', 'Auto-reconnecting every')} {self.reconnect_interval_sec}s..."
        
        # Title
        cv2.putText(frame, "[ ! ] " + title_text, (pad_x + 30, center_y - 55), cv2.FONT_HERSHEY_SIMPLEX, 0.78, (68, 68, 239), 2, cv2.LINE_AA)
        
        # Subtitle Advice
        cv2.putText(frame, sub_text, (pad_x + 30, center_y - 12), cv2.FONT_HERSHEY_SIMPLEX, 0.52, (148, 163, 184), 1, cv2.LINE_AA)
        
        # Target path
        cv2.putText(frame, target_str, (pad_x + 30, center_y + 28), cv2.FONT_HERSHEY_SIMPLEX, 0.50, (203, 213, 225), 1, cv2.LINE_AA)
        
        # Status / Retry Notice
        cv2.putText(frame, retry_text, (pad_x + 30, center_y + 70), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (52, 211, 153), 2, cv2.LINE_AA)
        
        return frame

    def _emit_standby_frame(self):
        frame = self._generate_standby_frame()
        ret, buffer = cv2.imencode('.jpg', frame, [int(cv2.IMWRITE_JPEG_QUALITY), self.jpeg_quality])
        if ret:
            self.last_frame_bytes = buffer.tobytes()
            self.new_frame_event.set()

    def _connect_stream(self, source_path: str) -> bool:
        if self.cap.isOpened():
            self.cap.release()

        self.is_live_stream = self._is_live_url(source_path)
        self.last_reconnect_attempt = time.time()
        
        try:
            if self.is_live_stream:
                self.is_file_missing = False
                src = int(source_path) if source_path.isdigit() else source_path
                os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = "rtsp_transport;tcp|stimeout;3000000"
                self.cap = cv2.VideoCapture(src, cv2.CAP_FFMPEG)
                self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            else:
                # Video file validation
                if not os.path.exists(source_path):
                    self.is_file_missing = True
                    self.camera_connected = False
                    self.total_frames = 0
                    self.connection_error_msg = f"Video file not found: {os.path.basename(source_path)}"
                    print(f"[Error] {self.connection_error_msg}")
                    self._emit_standby_frame()
                    return False
                
                self.is_file_missing = False
                self.cap = cv2.VideoCapture(source_path)

            if self.cap.isOpened():
                ret, test_frame = self.cap.read()
                if ret and test_frame is not None:
                    self.camera_connected = True
                    self.is_file_missing = False
                    self.connection_error_msg = ""
                    if self.is_live_stream:
                        self.total_frames = 0
                        self.video_fps = 25.0
                    else:
                        self.total_frames = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
                        raw_fps = self.cap.get(cv2.CAP_PROP_FPS)
                        self.video_fps = raw_fps if raw_fps and 1.0 <= raw_fps <= 120.0 else 25.0
                    self.fps = self.video_fps
                    self._process_and_encode(test_frame)
                    return True
                else:
                    self.camera_connected = False
                    self.connection_error_msg = "Stream/file opened but failed to read initial frame."
            else:
                self.camera_connected = False
                self.connection_error_msg = "Could not open stream endpoint or video file."
        except Exception as e:
            self.camera_connected = False
            self.connection_error_msg = str(e)
            print(f"[Error] Connection failed: {e}")

        self._emit_standby_frame()
        return self.camera_connected

    def get_available_videos(self) -> List[str]:
        if not os.path.exists(self.videos_dir):
            return []
        files = [
            f for f in os.listdir(self.videos_dir)
            if os.path.isfile(os.path.join(self.videos_dir, f)) and f.lower().endswith(SUPPORTED_EXTENSIONS)
        ]
        files.sort()
        return files

    def get_available_sources(self) -> List[Dict[str, Any]]:
        sources = []
        src_cfg = self.config.get("source", {})
        if src_cfg.get("camera_url"):
            sources.append({
                "type": "camera",
                "id": "live_camera",
                "name": f"🎥 {src_cfg.get('camera_name', 'IP Camera')}",
                "url": src_cfg.get("camera_url", "")
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
            src_cfg = self.config.get("source", {})
            if source_id == "live_camera" and src_cfg.get("camera_url"):
                target_path = src_cfg["camera_url"]
                self.current_source_id = "live_camera"
                self.current_video_name = src_cfg.get("camera_name", "IP Camera")
            else:
                target_path = os.path.join(self.videos_dir, os.path.basename(source_id))
                self.current_source_id = os.path.basename(source_id)
                self.current_video_name = os.path.basename(source_id)

            self.current_source_path = target_path
            self.current_frame = 0
            self.frame_counter = 0
            self.last_results = None
            self.last_boxes_list.clear()
            self._reset_counts_internal()
            self._init_counter()
            return self._connect_stream(self.current_source_path)

    def change_video(self, video_name: str) -> bool:
        return self.change_source(video_name)

    def _reset_counts_internal(self):
        self.in_count = 0
        self.out_count = 0
        self.active_tracks_count = 0
        self.track_history.clear()
        self.counted_in_ids.clear()
        self.counted_out_ids.clear()

    def _init_counter(self):
        try:
            self.counter = solutions.ObjectCounter(
                show=False,
                region=self.line_points,
                model=self.active_model
            )
            if hasattr(self.counter, "model") and hasattr(self.counter.model, "overrides"):
                self.counter.model.overrides["conf"] = self.conf
                self.counter.model.overrides["imgsz"] = self.imgsz
        except Exception as e:
            print(f"[Warning] Error initializing ObjectCounter: {e}")
            self.counter = None

    def get_class_name(self, cls_id: int) -> str:
        """Resolve class ID directly to the exact model class label (e.g. gas_tank)."""
        if self.counter and hasattr(self.counter, "model") and hasattr(self.counter.model, "names"):
            names = self.counter.model.names
            if isinstance(names, dict) and cls_id in names:
                return str(names[cls_id])
            if isinstance(names, (list, tuple)) and 0 <= cls_id < len(names):
                return str(names[cls_id])
        return "gas_tank"

    def set_lang(self, lang_code: str):
        with self.lock:
            lang = lang_code.lower()
            if lang in self.locales or lang in ("en", "es"):
                self.lang = lang

    def set_conf(self, conf_val: float):
        with self.lock:
            self.conf = max(0.01, min(0.99, round(conf_val, 2)))
            if self.counter and hasattr(self.counter, "model") and hasattr(self.counter.model, "overrides"):
                self.counter.model.overrides["conf"] = self.conf
            elif self.counter and hasattr(self.counter, "conf"):
                self.counter.conf = self.conf

    def set_imgsz(self, imgsz_val: int):
        with self.lock:
            self.imgsz = imgsz_val
            if self.counter and hasattr(self.counter, "model") and hasattr(self.counter.model, "overrides"):
                self.counter.model.overrides["imgsz"] = self.imgsz

    def set_frame_skip(self, skip_val: int):
        with self.lock:
            self.frame_skip = max(1, min(10, skip_val))

    def set_playback_speed(self, speed_multiplier: float):
        with self.lock:
            self.playback_speed = max(0.25, min(10.0, speed_multiplier))

    def set_debug_mode(self, enabled: bool):
        with self.lock:
            self.debug_mode = enabled
            return self.debug_mode

    def toggle_debug_mode(self):
        with self.lock:
            self.debug_mode = not self.debug_mode
            return self.debug_mode

    def _sync_counts_from_counter(self):
        """Extract updated in_count and out_count from Ultralytics ObjectCounter."""
        if self.counter is None:
            return

        if hasattr(self.counter, "in_count"):
            c_in = getattr(self.counter, "in_count", None)
            if isinstance(c_in, (int, float)):
                self.in_count = int(c_in)
                
        if hasattr(self.counter, "out_count"):
            c_out = getattr(self.counter, "out_count", None)
            if isinstance(c_out, (int, float)):
                self.out_count = int(c_out)

        if hasattr(self.counter, "counts"):
            counts_obj = getattr(self.counter, "counts", None)
            if isinstance(counts_obj, dict):
                if "IN" in counts_obj:
                    self.in_count = int(counts_obj["IN"])
                if "OUT" in counts_obj:
                    self.out_count = int(counts_obj["OUT"])

    def _extract_boxes_and_tracks(self, results) -> List[tuple]:
        """Extract boxes data (xyxy, conf, cls_id, track_id) from results or counter."""
        boxes_list = []
        if results is not None and hasattr(results, "boxes") and results.boxes is not None:
            try:
                for b in results.boxes:
                    xyxy = b.xyxy[0].tolist() if hasattr(b, "xyxy") else []
                    conf = float(b.conf[0]) if hasattr(b, "conf") else 0.0
                    cls_id = int(b.cls[0]) if hasattr(b, "cls") else 0
                    track_id = int(b.id[0]) if hasattr(b, "id") and b.id is not None else None
                    if len(xyxy) == 4:
                        boxes_list.append((xyxy, conf, cls_id, track_id))
                if boxes_list:
                    return boxes_list
            except Exception:
                pass

        if self.counter is not None:
            if hasattr(self.counter, "boxes") and hasattr(self.counter, "track_ids"):
                try:
                    c_boxes = getattr(self.counter, "boxes", [])
                    c_ids = getattr(self.counter, "track_ids", [])
                    c_clss = getattr(self.counter, "clss", [])
                    c_confs = getattr(self.counter, "confs", [])
                    
                    for i, box in enumerate(c_boxes):
                        xyxy = box.tolist() if hasattr(box, "tolist") else list(box)
                        track_id = c_ids[i] if i < len(c_ids) else None
                        cls_id = int(c_clss[i]) if i < len(c_clss) else 0
                        conf = float(c_confs[i]) if i < len(c_confs) else 0.8
                        if len(xyxy) == 4:
                            boxes_list.append((xyxy, conf, cls_id, track_id))
                    if boxes_list:
                        return boxes_list
                except Exception:
                    pass

        return boxes_list

    def _check_directional_crossing(self, track_id: int, cx: int, cy: int):
        """
        Check if object crossed the horizontal line:
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

    def _draw_line_and_tracks(self, frame, boxes_list):
        """Draws clean gas tank bounding boxes, class labels, and counting line with localized text from JSON."""
        locale_data = self.locales.get(self.lang, self.locales.get("en", {}))
        video_i18n = locale_data.get("video", {})
        out_text = video_i18n.get("out_text", "^ OUT (Above)")
        in_text = video_i18n.get("in_text", "v IN (Below)")
        
        # 1. Draw Counting Line and Localized Direction Guides
        if len(self.line_points) >= 2:
            pt1 = tuple(self.line_points[0])
            pt2 = tuple(self.line_points[1])
            cv2.line(frame, pt1, pt2, (0, 255, 255), 3, cv2.LINE_AA)
            
            mid_x = (pt1[0] + pt2[0]) // 2
            mid_y = (pt1[1] + pt2[1]) // 2
            
            # Above line -> OUT / SALIDA
            cv2.putText(frame, out_text, (mid_x - 85, mid_y - 12), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 165, 255), 2, cv2.LINE_AA)
            # Below line -> IN / ENTRADA
            cv2.putText(frame, in_text, (mid_x - 85, mid_y + 26), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2, cv2.LINE_AA)

        # 2. Draw Clean Bounding Boxes with Class Names
        for xyxy, conf, cls_id, track_id in boxes_list:
            if len(xyxy) == 4:
                x1, y1, x2, y2 = map(int, xyxy)
                cx, cy = (x1 + x2) // 2, (y1 + y2) // 2

                if track_id is not None:
                    pts = self.track_history.get(track_id, [])
                    for i in range(1, len(pts)):
                        cv2.line(frame, pts[i - 1], pts[i], (255, 105, 180), 2)

                # High-visibility modern color palette (Electric Cyan for high confidence, Vibrant Amber for low)
                box_color = (255, 195, 0) if conf >= 0.4 else (0, 200, 255)
                
                # Draw bounding rectangle (3px width for clear visibility)
                cv2.rectangle(frame, (x1, y1), (x2, y2), box_color, 3)
                cv2.circle(frame, (cx, cy), 5, (0, 0, 255), -1)

                # Resolve Class Label (e.g. "gas_tank")
                class_label = self.get_class_name(cls_id)
                track_str = f"#{track_id} " if track_id is not None else ""
                label_text = f"{track_str}{class_label} {int(conf * 100)}%"

                font_scale = 0.68
                font_thickness = 2
                (label_w, label_h), baseline = cv2.getTextSize(label_text, cv2.FONT_HERSHEY_SIMPLEX, font_scale, font_thickness)
                
                badge_top = max(0, y1 - label_h - 12)
                badge_bottom = y1
                cv2.rectangle(frame, (x1, badge_top), (x1 + label_w + 14, badge_bottom), (15, 23, 42), -1)
                cv2.rectangle(frame, (x1, badge_top), (x1 + label_w + 14, badge_bottom), box_color, 2)
                cv2.putText(frame, label_text, (x1 + 7, badge_bottom - 6), cv2.FONT_HERSHEY_SIMPLEX, font_scale, (255, 255, 255), font_thickness, cv2.LINE_AA)
                
        return frame

    def _process_and_encode(self, im0):
        t_start = time.time()
        pristine_frame = im0.copy()
        
        self.frame_counter += 1
        should_run_yolo = (self.frame_counter % self.frame_skip == 0) or (self.last_results is None)

        t_infer_start = time.time()
        if should_run_yolo and self.counter is not None:
            try:
                self.last_results = self.counter(im0)
                extracted_boxes = self._extract_boxes_and_tracks(self.last_results)
                if extracted_boxes:
                    self.last_boxes_list = extracted_boxes
            except Exception:
                pass
        t_infer_end = time.time()
        self.inference_time_ms = (t_infer_end - t_infer_start) * 1000.0

        boxes_list = self.last_boxes_list
        self.active_tracks_count = len(boxes_list)

        for xyxy, conf, cls_id, track_id in boxes_list:
            if len(xyxy) == 4 and track_id is not None:
                x1, y1, x2, y2 = map(int, xyxy)
                cx, cy = (x1 + x2) // 2, (y1 + y2) // 2
                if track_id not in self.track_history:
                    self.track_history[track_id] = []
                self.track_history[track_id].append((cx, cy))
                if len(self.track_history[track_id]) > 30:
                    self.track_history[track_id].pop(0)
                self._check_directional_crossing(track_id, cx, cy)

        processed_frame = pristine_frame.copy()
        self._sync_counts_from_counter()

        if self.debug_mode:
            processed_frame = self._draw_line_and_tracks(processed_frame, boxes_list)

        t_enc_start = time.time()
        h, w = processed_frame.shape[:2]
        if w > self.output_width:
            scale = self.output_width / float(w)
            target_h = int(h * scale)
            stream_frame = cv2.resize(processed_frame, (self.output_width, target_h), interpolation=cv2.INTER_LINEAR)
        else:
            stream_frame = processed_frame

        ret, buffer = cv2.imencode('.jpg', stream_frame, [int(cv2.IMWRITE_JPEG_QUALITY), self.jpeg_quality])
        t_enc_end = time.time()
        
        self.encode_time_ms = (t_enc_end - t_enc_start) * 1000.0
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

        if ret:
            self.last_frame_bytes = buffer.tobytes()
            self.new_frame_event.set()
            return self.last_frame_bytes
        return self.last_frame_bytes

    def _worker_loop(self):
        """Dedicated background thread handling both local file playback and live camera streams with auto-reconnect."""
        while self.running:
            effective_fps = self.video_fps * self.playback_speed
            target_delay = 1.0 / effective_fps if effective_fps > 0 else 0.04
            start_t = time.time()

            if not self.is_paused:
                with self.lock:
                    if self.is_file_missing:
                        # Video file not found: maintain standby error canvas
                        now = time.time()
                        if (now - self.last_reconnect_attempt) >= 2.0:
                            self.last_reconnect_attempt = now
                            if os.path.exists(self.current_source_path):
                                self._connect_stream(self.current_source_path)
                            else:
                                self._emit_standby_frame()
                    elif self.is_live_stream:
                        if not self.cap.isOpened() or not self.camera_connected:
                            now = time.time()
                            if (now - self.last_reconnect_attempt) >= self.reconnect_interval_sec:
                                self._connect_stream(self.current_source_path)
                            else:
                                self._emit_standby_frame()
                        else:
                            success, im0 = self.cap.read()
                            if success and im0 is not None:
                                self.camera_connected = True
                                self.connection_error_msg = ""
                                self.current_frame += 1
                                self._process_and_encode(im0)
                            else:
                                self.camera_connected = False
                                self._emit_standby_frame()
                    else:
                        # File playback mode
                        if self.cap.isOpened():
                            success, im0 = self.cap.read()
                            if success and im0 is not None:
                                self.current_frame = int(self.cap.get(cv2.CAP_PROP_POS_FRAMES))
                                self._process_and_encode(im0)
                            else:
                                if self.loop and self.total_frames > 0:
                                    self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                                    self.current_frame = 0
                                    self.frame_counter = 0
                                    self.track_history.clear()
                                    self.last_boxes_list.clear()
                                    success, im0 = self.cap.read()
                                    if success and im0 is not None:
                                        self._process_and_encode(im0)
                                else:
                                    self.is_paused = True
            
            elapsed = time.time() - start_t
            sleep_time = max(0.001, target_delay - elapsed) if (not self.is_paused and not self.is_file_missing and (not self.is_live_stream or self.camera_connected)) else 0.4
            time.sleep(sleep_time)

    def seek_frame(self, target_frame: int):
        if self.is_live_stream or self.is_file_missing:
            return
        with self.lock:
            if not self.cap.isOpened() or self.total_frames <= 0:
                return
            clamped_frame = max(0, min(self.total_frames - 1, target_frame))
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, clamped_frame)
            self.current_frame = clamped_frame
            self.frame_counter = 0
            self.last_results = None
            self.last_boxes_list.clear()
            self.track_history.clear()
            success, im0 = self.cap.read()
            if success and im0 is not None:
                self._process_and_encode(im0)

    def seek_offset(self, seconds_offset: float):
        if self.is_live_stream or self.is_file_missing:
            return
        frame_offset = int(seconds_offset * self.video_fps)
        target = self.current_frame + frame_offset
        self.seek_frame(target)

    def step(self, frame_delta: int):
        if self.is_live_stream or self.is_file_missing:
            return
        target = self.current_frame + frame_delta
        self.seek_frame(target)

    def set_pause(self, paused: bool):
        with self.lock:
            self.is_paused = paused

    def toggle_pause(self):
        with self.lock:
            self.is_paused = not self.is_paused
            return self.is_paused

    def reset(self):
        with self.lock:
            self._reset_counts_internal()
            self._init_counter()
            if not self.is_live_stream and not self.is_file_missing and self.cap.isOpened():
                self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                self.current_frame = 0
                self.frame_counter = 0
                self.last_results = None
                self.last_boxes_list.clear()
                success, im0 = self.cap.read()
                if success and im0 is not None:
                    self._process_and_encode(im0)

    def get_status(self):
        with self.lock:
            self._sync_counts_from_counter()
            
            current_time = (self.current_frame / self.video_fps) if (not self.is_live_stream and not self.is_file_missing and self.video_fps > 0) else 0.0
            duration = (self.total_frames / self.video_fps) if (not self.is_live_stream and not self.is_file_missing and self.video_fps > 0) else 0.0
            return {
                "current_video": self.current_video_name,
                "current_source_id": self.current_source_id,
                "is_live": self.is_live_stream,
                "is_file_missing": self.is_file_missing,
                "camera_connected": self.camera_connected,
                "connection_error_msg": self.connection_error_msg,
                "active_model": os.path.basename(self.active_model),
                "conf": self.conf,
                "imgsz": self.imgsz,
                "frame_skip": self.frame_skip,
                "playback_speed": self.playback_speed,
                "output_width": self.output_width,
                "lang": self.lang,
                "video_native_fps": round(self.video_fps, 1),
                "actual_stream_fps": round(self.actual_processed_fps, 1),
                "max_hardware_fps": round(self.max_compute_fps, 1),
                "ai_latency_ms": round(self.inference_time_ms, 1),
                "encode_latency_ms": round(self.encode_time_ms, 1),
                "debug_mode": self.debug_mode,
                "current_frame": self.current_frame,
                "total_frames": self.total_frames,
                "fps": round(self.actual_processed_fps, 1),
                "current_time": round(current_time, 2),
                "duration": round(duration, 2),
                "is_paused": self.is_paused,
                "loop": self.loop,
                "in_count": self.in_count,
                "out_count": self.out_count,
                "net_count": self.in_count - self.out_count,
                "active_tracks": self.active_tracks_count
            }

    def generate_frames(self):
        """Streaming generator consuming frames from the background worker with graceful disconnect handling."""
        last_sent = None
        try:
            while self.running:
                frame_data = self.last_frame_bytes
                if frame_data is not None and frame_data is not last_sent:
                    last_sent = frame_data
                    yield (b'--frame\r\n'
                           b'Content-Type: image/jpeg\r\n\r\n' + frame_data + b'\r\n')
                time.sleep(0.015)
        except GeneratorExit:
            pass
        except Exception:
            pass

video_service = VideoStreamService()
