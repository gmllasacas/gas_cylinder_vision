import os
from typing import List, Tuple, Optional, Any, Dict
import numpy as np
from ultralytics import solutions
from app.core.logging import logger

class YOLODetector:
    """Manages YOLO neural network inference, object tracking, and bounding box extraction."""

    def __init__(
        self,
        models_dir: str,
        default_model: str = "best.pt",
        fallback_model: str = "yolov8n.pt",
        confidence: float = 0.50,
        imgsz: int = 640,
        frame_skip: int = 2,
        line_points: Optional[List[List[int]]] = None
    ):
        self.models_dir = models_dir
        self.default_model = default_model
        self.fallback_model = fallback_model
        self.confidence = confidence
        self.imgsz = imgsz
        self.frame_skip = frame_skip
        self.line_points = [tuple(p) for p in (line_points or [[1200, 400], [1700, 400]])]
        
        self.active_model_path = self._resolve_model_path()
        self.counter: Optional[Any] = None
        self.frame_counter = 0
        self.last_results = None
        self.last_boxes: List[Tuple[List[float], float, int, Optional[int]]] = []
        
        self.init_counter()

    def _resolve_model_path(self) -> str:
        """Finds the best available model weights file."""
        candidates = [
            os.path.join(self.models_dir, self.default_model),
            os.path.join(self.models_dir, self.fallback_model),
            self.default_model,
            self.fallback_model,
            "yolov8n.pt"
        ]
        for candidate in candidates:
            if os.path.exists(candidate):
                logger.info(f"Using YOLO model: {candidate}")
                return candidate
        return self.default_model

    def init_counter(self):
        """Initializes or resets the Ultralytics ObjectCounter."""
        try:
            self.counter = solutions.ObjectCounter(
                show=False,
                region=self.line_points,
                model=self.active_model_path
            )
            if hasattr(self.counter, "LOGGER") and self.counter.LOGGER is not None:
                self.counter.LOGGER.setLevel(40)  # logging.ERROR
            if hasattr(self.counter, "model") and hasattr(self.counter.model, "overrides"):
                self.counter.model.overrides["conf"] = self.confidence
                self.counter.model.overrides["imgsz"] = self.imgsz
            logger.info("ObjectCounter initialized successfully.")
        except Exception as e:
            logger.warning(f"Error initializing Ultralytics ObjectCounter: {e}")
            self.counter = None

    def set_confidence(self, conf: float):
        self.confidence = max(0.01, min(0.99, round(conf, 2)))
        if self.counter and hasattr(self.counter, "model") and hasattr(self.counter.model, "overrides"):
            self.counter.model.overrides["conf"] = self.confidence
        elif self.counter and hasattr(self.counter, "conf"):
            self.counter.conf = self.confidence

    def set_imgsz(self, imgsz: int):
        self.imgsz = imgsz
        if self.counter and hasattr(self.counter, "model") and hasattr(self.counter.model, "overrides"):
            self.counter.model.overrides["imgsz"] = self.imgsz

    def set_frame_skip(self, skip: int):
        self.frame_skip = max(1, min(10, skip))

    def set_line_points(self, points: List[List[int]]):
        self.line_points = [tuple(p) for p in points]
        self.init_counter()

    def get_class_name(self, cls_id: int) -> str:
        """Resolves class ID directly to the model's assigned class name."""
        if self.counter and hasattr(self.counter, "model") and hasattr(self.counter.model, "names"):
            names = self.counter.model.names
            if isinstance(names, dict) and cls_id in names:
                return str(names[cls_id])
            if isinstance(names, (list, tuple)) and 0 <= cls_id < len(names):
                return str(names[cls_id])
        return "gas_tank"

    def detect_and_track(self, frame: np.ndarray) -> List[Tuple[List[float], float, int, Optional[int]]]:
        """
        Executes YOLO inference and tracking with frame skipping.
        Returns a list of tuples: (xyxy, conf, cls_id, track_id).
        """
        self.frame_counter += 1
        should_run = (self.frame_counter % self.frame_skip == 0) or (self.last_results is None)

        if should_run and self.counter is not None:
            try:
                self.last_results = self.counter(frame)
                extracted = self._extract_boxes(self.last_results)
                if extracted:
                    self.last_boxes = extracted
            except Exception as e:
                logger.debug(f"Inference error: {e}")

        return self.last_boxes

    def _extract_boxes(self, results: Any) -> List[Tuple[List[float], float, int, Optional[int]]]:
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

        if self.counter is not None and hasattr(self.counter, "boxes") and hasattr(self.counter, "track_ids"):
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
            except Exception:
                pass

        return boxes_list

    def reset(self):
        """Resets detection cache and reinitializes counter."""
        self.frame_counter = 0
        self.last_results = None
        self.last_boxes.clear()
        self.init_counter()
