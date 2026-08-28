import os
from typing import List, Tuple, Optional, Dict, Any, Callable
import cv2
import numpy as np
from app.core.i18n import I18nManager
from app.cv.capture import VideoCaptureManager

class FrameRenderer:
    """Handles all visual annotations, overlays, standby canvas rendering, and JPEG encoding."""

    def __init__(
        self,
        i18n: I18nManager,
        output_width: int = 1024,
        jpeg_quality: int = 70,
        line_points: Optional[List[List[int]]] = None
    ):
        self.i18n = i18n
        self.output_width = output_width
        self.jpeg_quality = jpeg_quality
        self.line_points = [tuple(p) for p in (line_points or [[1200, 400], [1700, 400]])]

    def set_line_points(self, points: List[List[int]]):
        self.line_points = [tuple(p) for p in points]

    def generate_standby_canvas(
        self,
        source_path: str,
        is_file_missing: bool,
        reconnect_interval_sec: int = 3
    ) -> np.ndarray:
        """Generates a modern Dark Slate standby canvas when video is missing or camera is disconnected."""
        width = self.output_width
        height = int(width * 9 / 16)
        
        # Dark Slate-950 background
        frame = np.full((height, width, 3), (15, 23, 42), dtype=np.uint8)
        
        pad_x, pad_y = 50, 40
        cv2.rectangle(frame, (pad_x, pad_y), (width - pad_x, height - pad_y), (30, 41, 59), -1)
        cv2.rectangle(frame, (pad_x, pad_y), (width - pad_x, height - pad_y), (239, 68, 68), 2)
        
        center_y = height // 2

        if is_file_missing:
            title_text = self.i18n.t("video.file_missing_title", "VIDEO FILE NOT FOUND")
            sub_text = self.i18n.t("video.file_missing_subtitle", "Place the file inside videos/ or update config.json")
            target_str = f"Missing Target: videos/{os.path.basename(source_path)}"
            retry_text = "Waiting for video file..."
        else:
            title_text = self.i18n.t("video.offline_title", "CAMERA OFFLINE / UNREACHABLE")
            sub_text = self.i18n.t("video.offline_subtitle", "Check RTSP URL, Network connection or Credentials")
            masked_url = VideoCaptureManager.mask_credentials(source_path)
            target_str = f"Stream Target: {masked_url}"
            retry_prefix = self.i18n.t("video.offline_retry", "Auto-reconnecting every")
            retry_text = f"{retry_prefix} {reconnect_interval_sec}s..."

        # Header Title
        cv2.putText(frame, "[ ! ] " + title_text, (pad_x + 30, center_y - 55), cv2.FONT_HERSHEY_SIMPLEX, 0.78, (68, 68, 239), 2, cv2.LINE_AA)
        # Subtitle Advice
        cv2.putText(frame, sub_text, (pad_x + 30, center_y - 12), cv2.FONT_HERSHEY_SIMPLEX, 0.52, (148, 163, 184), 1, cv2.LINE_AA)
        # Target Path
        cv2.putText(frame, target_str, (pad_x + 30, center_y + 28), cv2.FONT_HERSHEY_SIMPLEX, 0.50, (203, 213, 225), 1, cv2.LINE_AA)
        # Status / Retry Notice
        cv2.putText(frame, retry_text, (pad_x + 30, center_y + 70), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (52, 211, 153), 2, cv2.LINE_AA)

        return frame

    def draw_overlays(
        self,
        frame: np.ndarray,
        boxes_list: List[Tuple[List[float], float, int, Optional[int]]],
        track_history: Dict[int, List[Tuple[int, int]]],
        get_class_name_fn: Callable[[int], str]
    ) -> np.ndarray:
        """Draws counting lines, localized direction hints, bounding boxes, labels, and trajectories."""
        annotated = frame.copy()

        out_text = self.i18n.t("video.out_text", "^ OUT (Above)")
        in_text = self.i18n.t("video.in_text", "v IN (Below)")

        # 1. Draw Counting Line or Polygon Region
        if len(self.line_points) >= 3:
            pts = np.array(self.line_points, dtype=np.int32).reshape((-1, 1, 2))
            # Semi-transparent zone overlay
            overlay = annotated.copy()
            cv2.fillPoly(overlay, [pts], (0, 255, 255))
            cv2.addWeighted(overlay, 0.12, annotated, 0.88, 0, annotated)
            # Outline
            cv2.polylines(annotated, [pts], isClosed=True, color=(0, 255, 255), thickness=2, lineType=cv2.LINE_AA)

            min_y = int(np.min(pts[:, 0, 1]))
            max_y = int(np.max(pts[:, 0, 1]))
            mid_x = int(np.mean(pts[:, 0, 0]))

            cv2.putText(annotated, out_text, (mid_x - 85, max(20, min_y - 10)), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 165, 255), 2, cv2.LINE_AA)
            cv2.putText(annotated, in_text, (mid_x - 85, max_y + 25), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2, cv2.LINE_AA)

        elif len(self.line_points) == 2:
            pt1 = tuple(self.line_points[0])
            pt2 = tuple(self.line_points[1])
            cv2.line(annotated, pt1, pt2, (0, 255, 255), 3, cv2.LINE_AA)
            
            mid_x = (pt1[0] + pt2[0]) // 2
            mid_y = (pt1[1] + pt2[1]) // 2
            
            cv2.putText(annotated, out_text, (mid_x - 85, mid_y - 12), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 165, 255), 2, cv2.LINE_AA)
            cv2.putText(annotated, in_text, (mid_x - 85, mid_y + 26), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2, cv2.LINE_AA)

        # 2. Draw Detections & Trajectories
        for xyxy, conf, cls_id, track_id in boxes_list:
            if len(xyxy) == 4:
                x1, y1, x2, y2 = map(int, xyxy)
                cx, cy = (x1 + x2) // 2, (y1 + y2) // 2

                # Trajectory Line
                if track_id is not None and track_id in track_history:
                    pts = track_history[track_id]
                    for i in range(1, len(pts)):
                        cv2.line(annotated, pts[i - 1], pts[i], (255, 105, 180), 2)

                # High-visibility palette
                box_color = (255, 195, 0) if conf >= 0.4 else (0, 200, 255)
                cv2.rectangle(annotated, (x1, y1), (x2, y2), box_color, 3)
                cv2.circle(annotated, (cx, cy), 5, (0, 0, 255), -1)

                # Class Badge
                class_label = get_class_name_fn(cls_id)
                track_str = f"#{track_id} " if track_id is not None else ""
                label_text = f"{track_str}{class_label} {int(conf * 100)}%"

                font_scale = 0.68
                font_thickness = 2
                (label_w, label_h), baseline = cv2.getTextSize(label_text, cv2.FONT_HERSHEY_SIMPLEX, font_scale, font_thickness)
                
                badge_top = max(0, y1 - label_h - 12)
                badge_bottom = y1
                cv2.rectangle(annotated, (x1, badge_top), (x1 + label_w + 14, badge_bottom), (15, 23, 42), -1)
                cv2.rectangle(annotated, (x1, badge_top), (x1 + label_w + 14, badge_bottom), box_color, 2)
                cv2.putText(annotated, label_text, (x1 + 7, badge_bottom - 6), cv2.FONT_HERSHEY_SIMPLEX, font_scale, (255, 255, 255), font_thickness, cv2.LINE_AA)

        return annotated

    def encode_jpeg(self, frame: np.ndarray) -> Optional[bytes]:
        """Resizes frame to output_width and encodes to JPEG bytes."""
        h, w = frame.shape[:2]
        if w > self.output_width:
            scale = self.output_width / float(w)
            target_h = int(h * scale)
            resized = cv2.resize(frame, (self.output_width, target_h), interpolation=cv2.INTER_LINEAR)
        else:
            resized = frame

        ret, buffer = cv2.imencode('.jpg', resized, [int(cv2.IMWRITE_JPEG_QUALITY), self.jpeg_quality])
        if ret:
            return buffer.tobytes()
        return None
