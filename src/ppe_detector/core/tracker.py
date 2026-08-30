"""Multi-Object Tracker for Personnel and Workers across Video Streams."""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from ppe_detector.core.detector import DetectionBox


@dataclass
class TrackedPerson:
    """Represents a single tracked worker across video frames."""
    track_id: int
    box: DetectionBox
    age: int = 0
    disappeared_frames: int = 0
    consecutive_violations: int = 0
    is_compliant: bool = True
    missing_ppe: List[str] = field(default_factory=list)
    confidence: float = 1.0


class CentroidIoUTracker:
    """High-speed Multi-Object Tracker leveraging centroid distances and IoU overlap."""

    def __init__(self, max_disappeared: int = 30, max_distance_px: float = 120.0):
        self.next_id = 1
        self.tracks: Dict[int, TrackedPerson] = {}
        self.max_disappeared = max_disappeared
        self.max_distance_px = max_distance_px

    def _register(self, box: DetectionBox) -> TrackedPerson:
        """Register a new tracked entity."""
        person = TrackedPerson(
            track_id=self.next_id,
            box=box,
            age=1,
            disappeared_frames=0,
            confidence=box.confidence,
        )
        self.tracks[self.next_id] = person
        self.next_id += 1
        return person

    def _deregister(self, track_id: int):
        """Remove a track that has disappeared."""
        if track_id in self.tracks:
            del self.tracks[track_id]

    def update(self, person_boxes: List[DetectionBox]) -> List[TrackedPerson]:
        """Update tracker with freshly detected person boxes in the current frame."""
        if not person_boxes:
            # Mark all existing tracks as disappeared
            for tid in list(self.tracks.keys()):
                self.tracks[tid].disappeared_frames += 1
                if self.tracks[tid].disappeared_frames > self.max_disappeared:
                    self._deregister(tid)
            return list(self.tracks.values())

        if not self.tracks:
            # Register all current boxes
            for b in person_boxes:
                self._register(b)
            return list(self.tracks.values())

        track_ids = list(self.tracks.keys())
        track_boxes = [self.tracks[tid].box for tid in track_ids]

        # Calculate cost matrix based on Euclidean distance + (1 - IoU)
        matched_tracks = set()
        matched_detections = set()

        for d_idx, det in enumerate(person_boxes):
            best_match_id = None
            best_cost = float("inf")

            dc_x, dc_y = det.center

            for t_idx, tid in enumerate(track_ids):
                if tid in matched_tracks:
                    continue

                tc_x, tc_y = track_boxes[t_idx].center
                dist = math.hypot(dc_x - tc_x, dc_y - tc_y)

                if dist > self.max_distance_px:
                    continue

                iou = det.iou(track_boxes[t_idx])
                cost = dist * (1.0 - (iou * 0.5))

                if cost < best_cost:
                    best_cost = cost
                    best_match_id = tid

            if best_match_id is not None:
                matched_tracks.add(best_match_id)
                matched_detections.add(d_idx)

                # Update matched track
                self.tracks[best_match_id].box = det
                self.tracks[best_match_id].disappeared_frames = 0
                self.tracks[best_match_id].age += 1
                self.tracks[best_match_id].confidence = det.confidence

        # Handle unmatched existing tracks
        for tid in track_ids:
            if tid not in matched_tracks:
                self.tracks[tid].disappeared_frames += 1
                if self.tracks[tid].disappeared_frames > self.max_disappeared:
                    self._deregister(tid)

        # Handle new unmatched detections
        for d_idx, det in enumerate(person_boxes):
            if d_idx not in matched_detections:
                self._register(det)

        return list(self.tracks.values())
