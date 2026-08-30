"""Unit tests for Bounding Box geometric algorithms and Detection models."""

import os
import sys
import unittest

SRC_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src"))
if SRC_PATH not in sys.path:
    sys.path.insert(0, SRC_PATH)

from ppe_detector.core.detector import DetectionBox, DetectionResult, PPEDetector


class TestDetectionBox(unittest.TestCase):
    def test_dimensions_and_center(self):
        box = DetectionBox(x1=100.0, y1=100.0, x2=200.0, y2=300.0, confidence=0.9, class_name="person", class_id=0)
        self.assertEqual(box.width, 100.0)
        self.assertEqual(box.height, 200.0)
        self.assertEqual(box.area, 20000.0)
        self.assertEqual(box.center, (150.0, 200.0))

    def test_iou_identical_boxes(self):
        b1 = DetectionBox(0, 0, 100, 100, 0.9, "helmet", 1)
        b2 = DetectionBox(0, 0, 100, 100, 0.9, "helmet", 1)
        self.assertAlmostEqual(b1.iou(b2), 1.0)

    def test_iou_non_overlapping_boxes(self):
        b1 = DetectionBox(0, 0, 50, 50, 0.9, "helmet", 1)
        b2 = DetectionBox(100, 100, 150, 150, 0.9, "helmet", 1)
        self.assertEqual(b1.iou(b2), 0.0)

    def test_is_inside_containment(self):
        parent = DetectionBox(0, 0, 200, 400, 0.95, "person", 0)
        child = DetectionBox(50, 20, 150, 90, 0.92, "helmet", 1)
        outside = DetectionBox(300, 300, 400, 400, 0.9, "helmet", 1)

        self.assertTrue(child.is_inside(parent, threshold=0.8))
        self.assertFalse(outside.is_inside(parent, threshold=0.5))


if __name__ == "__main__":
    unittest.main()
