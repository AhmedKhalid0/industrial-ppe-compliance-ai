"""PPE Compliance Evaluation & Spatial Association Rule Engine."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Dict, Set, Optional
from ppe_detector.core.detector import DetectionBox
from ppe_detector.core.tracker import TrackedPerson


@dataclass
class WorkerComplianceState:
    """Detailed safety equipment status for a single tracked worker."""
    track_id: int
    person_box: DetectionBox
    has_helmet: bool = False
    has_vest: bool = False
    has_goggles: bool = False
    has_boots: bool = False
    missing_items: List[str] = field(default_factory=list)
    is_compliant: bool = True
    consecutive_violations: int = 0
    is_persistent_violation: bool = False


class ComplianceEvaluator:
    """Evaluates spatial containment and rule compliance for industrial personnel."""

    def __init__(
        self,
        required_ppe: Optional[List[str]] = None,
        persistence_threshold_frames: int = 5,
    ):
        self.required_ppe = set(required_ppe or ["helmet", "vest"])
        self.persistence_threshold_frames = persistence_threshold_frames

    def _get_head_region(self, person: DetectionBox) -> DetectionBox:
        """Extract top 35% bounding region representing the worker's head."""
        h = person.height
        return DetectionBox(
            x1=person.x1,
            y1=person.y1,
            x2=person.x2,
            y2=person.y1 + (h * 0.35),
            confidence=person.confidence,
            class_name="head_region",
            class_id=-1,
        )

    def _get_torso_region(self, person: DetectionBox) -> DetectionBox:
        """Extract middle 55% bounding region representing the worker's torso/upper body."""
        h = person.height
        return DetectionBox(
            x1=person.x1,
            y1=person.y1 + (h * 0.15),
            x2=person.x2,
            y2=person.y1 + (h * 0.75),
            confidence=person.confidence,
            class_name="torso_region",
            class_id=-1,
        )

    def evaluate_person(
        self,
        tracked_person: TrackedPerson,
        equipment_boxes: List[DetectionBox],
    ) -> WorkerComplianceState:
        """Evaluate a single worker against all detected PPE equipment in the frame."""
        p_box = tracked_person.box
        head_box = self._get_head_region(p_box)
        torso_box = self._get_torso_region(p_box)

        has_helmet = False
        has_vest = False
        has_goggles = False
        has_boots = False

        for eq in equipment_boxes:
            cname = eq.class_name.lower()

            # Check Helmet
            if "helmet" in cname:
                if cname == "helmet" and (eq.iou(head_box) > 0.05 or eq.is_inside(head_box, 0.3)):
                    has_helmet = True
                elif cname == "no-helmet" and eq.is_inside(head_box, 0.3):
                    has_helmet = False

            # Check Vest / High-Vis Jacket
            elif "vest" in cname or "jacket" in cname:
                if cname == "vest" and (eq.iou(torso_box) > 0.05 or eq.is_inside(torso_box, 0.3)):
                    has_vest = True
                elif cname == "no-vest" and eq.is_inside(torso_box, 0.3):
                    has_vest = False

            # Check Goggles
            elif "goggle" in cname or "glass" in cname:
                if eq.is_inside(head_box, 0.2):
                    has_goggles = True

            # Check Boots
            elif "boot" in cname or "shoe" in cname:
                if eq.y1 >= p_box.y1 + (p_box.height * 0.70):
                    has_boots = True

        missing = []
        if "helmet" in self.required_ppe and not has_helmet:
            missing.append("Missing Helmet")
        if "vest" in self.required_ppe and not has_vest:
            missing.append("Missing Safety Vest")
        if "goggles" in self.required_ppe and not has_goggles:
            missing.append("Missing Goggles")
        if "boots" in self.required_ppe and not has_boots:
            missing.append("Missing Steel-Toe Boots")

        is_compliant = len(missing) == 0

        # Update tracker persistence
        if is_compliant:
            tracked_person.consecutive_violations = 0
            tracked_person.is_compliant = True
            tracked_person.missing_ppe = []
        else:
            tracked_person.consecutive_violations += 1
            tracked_person.is_compliant = False
            tracked_person.missing_ppe = missing

        is_persistent = tracked_person.consecutive_violations >= self.persistence_threshold_frames

        return WorkerComplianceState(
            track_id=tracked_person.track_id,
            person_box=p_box,
            has_helmet=has_helmet,
            has_vest=has_vest,
            has_goggles=has_goggles,
            has_boots=has_boots,
            missing_items=missing,
            is_compliant=is_compliant,
            consecutive_violations=tracked_person.consecutive_violations,
            is_persistent_violation=is_persistent,
        )

    def evaluate_frame(
        self,
        tracked_workers: List[TrackedPerson],
        equipment_boxes: List[DetectionBox],
    ) -> List[WorkerComplianceState]:
        """Evaluate compliance status for all workers in the current frame."""
        return [self.evaluate_person(worker, equipment_boxes) for worker in tracked_workers]
