"""YOLO-based Object Detection Engine for Industrial PPE and Personnel."""

from __future__ import annotations

import os
import time
from dataclasses import dataclass, field
from typing import List, Tuple, Optional, Dict, Any
import numpy as np


@dataclass
class DetectionBox:
    """Bounding box representation with spatial coordinates, class labels and confidence."""
    x1: float
    y1: float
    x2: float
    y2: float
    confidence: float
    class_name: str
    class_id: int

    @property
    def width(self) -> float:
        return max(0.0, self.x2 - self.x1)

    @property
    def height(self) -> float:
        return max(0.0, self.y2 - self.y1)

    @property
    def area(self) -> float:
        return self.width * self.height

    @property
    def center(self) -> Tuple[float, float]:
        return ((self.x1 + self.x2) / 2.0, (self.y1 + self.y2) / 2.0)

    def iou(self, other: DetectionBox) -> float:
        """Calculate Intersection over Union (IoU) with another bounding box."""
        ix1 = max(self.x1, other.x1)
        iy1 = max(self.y1, other.y1)
        ix2 = min(self.x2, other.x2)
        iy2 = min(self.y2, other.y2)

        iw = max(0.0, ix2 - ix1)
        ih = max(0.0, iy2 - iy1)
        intersection = iw * ih

        union = self.area + other.area - intersection
        if union <= 0:
            return 0.0
        return intersection / union

    def is_inside(self, parent: DetectionBox, threshold: float = 0.5) -> bool:
        """Check if this box is substantially contained within another (parent) box."""
        ix1 = max(self.x1, parent.x1)
        iy1 = max(self.y1, parent.y1)
        ix2 = min(self.x2, parent.x2)
        iy2 = min(self.y2, parent.y2)

        intersection = max(0.0, ix2 - ix1) * max(0.0, iy2 - iy1)
        if self.area <= 0:
            return False
        return (intersection / self.area) >= threshold


@dataclass
class DetectionResult:
    """Holds detection outputs for a single video frame."""
    boxes: List[DetectionBox] = field(default_factory=list)
    inference_time_ms: float = 0.0
    frame_width: int = 0
    frame_height: int = 0


class PPEDetector:
    """YOLOv8 / YOLOv11 Multi-class PPE Detection Engine."""

    # Standard PPE Class Mappings
    DEFAULT_CLASSES = {
        0: "person",
        1: "helmet",
        2: "no-helmet",
        3: "vest",
        4: "no-vest",
        5: "goggles",
        6: "boots",
        7: "gloves",
    }

    def __init__(
        self,
        model_path: Optional[str] = None,
        confidence_threshold: float = 0.45,
        iou_threshold: float = 0.45,
        device: str = "cpu",
    ):
        self.model_path = model_path
        self.confidence_threshold = confidence_threshold
        self.iou_threshold = iou_threshold
        self.device = device
        self.model = None
        self._is_mock = False

        self._load_model()

    def _load_model(self):
        """Load YOLO model weights or initialize fallback mock detector."""
        if self.model_path and os.path.exists(self.model_path):
            try:
                from ultralytics import YOLO
                self.model = YOLO(self.model_path)
                self._is_mock = False
                return
            except Exception:
                pass

        # Try default YOLOv8n if ultralytics is installed
        try:
            from ultralytics import YOLO
            self.model = YOLO("yolov8n.pt")
            self._is_mock = False
        except Exception:
            # Fallback mock mode for testing without GPU/heavy weights
            self._is_mock = True

    def detect(self, frame: np.ndarray) -> DetectionResult:
        """Run object detection on an input BGR image array.

        Args:
            frame: Numpy array representing image (H, W, C).

        Returns:
            DetectionResult containing detected bounding boxes and latency.
        """
        h, w = frame.shape[:2]
        start_t = time.perf_counter()

        if self._is_mock or self.model is None:
            # Return empty or synthetic result in mock mode
            elapsed = (time.perf_counter() - start_t) * 1000.0
            return DetectionResult(boxes=[], inference_time_ms=elapsed, frame_width=w, frame_height=h)

        try:
            results = self.model.predict(
                source=frame,
                conf=self.confidence_threshold,
                iou=self.iou_threshold,
                device=self.device,
                verbose=False,
            )

            boxes = []
            for r in results:
                for b in r.boxes:
                    coords = b.xyxy[0].cpu().numpy()
                    conf = float(b.conf[0].cpu().numpy())
                    cls_id = int(b.cls[0].cpu().numpy())
                    cls_name = self.model.names.get(cls_id, self.DEFAULT_CLASSES.get(cls_id, f"class_{cls_id}"))

                    boxes.append(
                        DetectionBox(
                            x1=float(coords[0]),
                            y1=float(coords[1]),
                            x2=float(coords[2]),
                            y2=float(coords[3]),
                            confidence=conf,
                            class_name=cls_name.lower(),
                            class_id=cls_id,
                        )
                    )

            elapsed = (time.perf_counter() - start_t) * 1000.0
            return DetectionResult(boxes=boxes, inference_time_ms=elapsed, frame_width=w, frame_height=h)

        except Exception:
            elapsed = (time.perf_counter() - start_t) * 1000.0
            return DetectionResult(boxes=[], inference_time_ms=elapsed, frame_width=w, frame_height=h)
