"""Snapshot Evidence Capture & Image Annotation Manager."""

from __future__ import annotations

import os
import time
import cv2
import numpy as np
from typing import Optional
from ppe_detector.core.compliance_engine import WorkerComplianceState


class SnapshotManager:
    """Captures and stores visual evidence snapshots of safety violations."""

    def __init__(self, snapshot_dir: str = "snapshots"):
        self.snapshot_dir = snapshot_dir
        os.makedirs(self.snapshot_dir, exist_ok=True)

    def capture_violation_snapshot(
        self,
        frame: np.ndarray,
        worker_state: WorkerComplianceState,
        camera_id: str = "CAM-01",
    ) -> Optional[str]:
        """Annotate and crop an evidence snapshot around the violating worker."""
        if frame is None:
            return None

        h, w = frame.shape[:2]
        box = worker_state.person_box

        # Expand crop box by 20% for environmental context
        pad_x = int(box.width * 0.20)
        pad_y = int(box.height * 0.20)

        cx1 = max(0, int(box.x1 - pad_x))
        cy1 = max(0, int(box.y1 - pad_y))
        cx2 = min(w, int(box.x2 + pad_x))
        cy2 = min(h, int(box.y2 + pad_y))

        cropped = frame[cy1:cy2, cx1:cx2].copy()
        if cropped.size == 0:
            return None

        # Draw red alert bounding box on crop
        rel_x1 = int(box.x1 - cx1)
        rel_y1 = int(box.y1 - cy1)
        rel_x2 = int(box.x2 - cx1)
        rel_y2 = int(box.y2 - cy1)

        cv2.rectangle(cropped, (rel_x1, rel_y1), (rel_x2, rel_y2), (0, 0, 255), 3)

        # Label tag
        missing_text = ", ".join(worker_state.missing_items)
        label = f"VIOLATION: {missing_text}"
        cv2.putText(cropped, label, (10, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
        cv2.putText(cropped, f"{camera_id} | Worker #{worker_state.track_id}", (10, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)

        # Generate filename
        timestamp_slug = time.strftime("%Y%m%d_%H%M%S")
        filename = f"violation_{timestamp_slug}_w{worker_state.track_id}.jpg"
        filepath = os.path.join(self.snapshot_dir, filename)

        cv2.imwrite(filepath, cropped)
        return os.path.relpath(filepath, start=".").replace("\\", "/")
