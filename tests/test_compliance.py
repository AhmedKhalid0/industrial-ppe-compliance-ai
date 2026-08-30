"""Unit tests for PPE Compliance Evaluator and Spatial Association Rules."""

import os
import sys
import unittest

SRC_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src"))
if SRC_PATH not in sys.path:
    sys.path.insert(0, SRC_PATH)

from ppe_detector.core.detector import DetectionBox
from ppe_detector.core.tracker import CentroidIoUTracker, TrackedPerson
from ppe_detector.core.compliance_engine import ComplianceEvaluator


class TestComplianceEngine(unittest.TestCase):
    def setUp(self):
        self.tracker = CentroidIoUTracker()
        self.evaluator = ComplianceEvaluator(required_ppe=["helmet", "vest"], persistence_threshold_frames=3)

    def test_compliant_worker(self):
        # Worker 1: Person box from (100, 100) to (200, 400)
        person_box = DetectionBox(100, 100, 200, 400, 0.95, "person", 0)
        tracked = self.tracker.update([person_box])
        self.assertEqual(len(tracked), 1)

        # Helmet located on head: (120, 100) to (180, 150)
        helmet_box = DetectionBox(120, 100, 180, 150, 0.92, "helmet", 1)
        # Vest located on torso: (110, 160) to (190, 280)
        vest_box = DetectionBox(110, 160, 190, 280, 0.90, "vest", 3)

        state = self.evaluator.evaluate_person(tracked[0], [helmet_box, vest_box])
        self.assertTrue(state.has_helmet)
        self.assertTrue(state.has_vest)
        self.assertTrue(state.is_compliant)
        self.assertEqual(len(state.missing_items), 0)

    def test_missing_helmet_violation(self):
        person_box = DetectionBox(100, 100, 200, 400, 0.95, "person", 0)
        tracked = self.tracker.update([person_box])

        # Only vest present
        vest_box = DetectionBox(110, 160, 190, 280, 0.90, "vest", 3)

        state = self.evaluator.evaluate_person(tracked[0], [vest_box])
        self.assertFalse(state.has_helmet)
        self.assertTrue(state.has_vest)
        self.assertFalse(state.is_compliant)
        self.assertIn("Missing Helmet", state.missing_items)

    def test_persistence_debounce_filter(self):
        person_box = DetectionBox(100, 100, 200, 400, 0.95, "person", 0)
        tracked = self.tracker.update([person_box])
        worker = tracked[0]

        # Frame 1: Violation
        state1 = self.evaluator.evaluate_person(worker, [])
        self.assertFalse(state1.is_persistent_violation)
        self.assertEqual(state1.consecutive_violations, 1)

        # Frame 2: Violation
        state2 = self.evaluator.evaluate_person(worker, [])
        self.assertFalse(state2.is_persistent_violation)
        self.assertEqual(state2.consecutive_violations, 2)

        # Frame 3: Threshold reached (3 frames) -> Persistent Violation!
        state3 = self.evaluator.evaluate_person(worker, [])
        self.assertTrue(state3.is_persistent_violation)
        self.assertEqual(state3.consecutive_violations, 3)


if __name__ == "__main__":
    unittest.main()
