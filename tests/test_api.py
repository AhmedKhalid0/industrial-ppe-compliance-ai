"""Unit tests for Incident Repository and Analytics calculations."""

import os
import sys
import unittest
import tempfile

SRC_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src"))
if SRC_PATH not in sys.path:
    sys.path.insert(0, SRC_PATH)

from ppe_detector.database.models import Incident
from ppe_detector.database.repository import IncidentRepository


class TestIncidentRepository(unittest.TestCase):
    def setUp(self):
        # Use an isolated SQLite database file
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.tmp_dir.name, "test_ppe.db")
        self.repo = IncidentRepository(db_path=self.db_path)

    def tearDown(self):
        try:
            self.tmp_dir.cleanup()
        except Exception:
            pass

    def test_save_and_retrieve_incident(self):
        inc = Incident(
            camera_id="CAM-01",
            zone_name="Zone A (Assembly)",
            worker_track_id=101,
            violation_type="Missing Helmet",
            missing_ppe="helmet",
            confidence=0.94,
        )
        inc_id = self.repo.save_incident(inc)
        self.assertIsNotNone(inc_id)
        self.assertGreater(inc_id, 0)

        incidents = self.repo.get_recent_incidents(limit=10)
        self.assertEqual(len(incidents), 1)
        self.assertEqual(incidents[0].worker_track_id, 101)
        self.assertEqual(incidents[0].violation_type, "Missing Helmet")
        self.assertEqual(incidents[0].status, "UNRESOLVED")

    def test_resolve_incident(self):
        inc = Incident(camera_id="CAM-02", zone_name="Zone B", worker_track_id=102, violation_type="Missing Vest", missing_ppe="vest")
        inc_id = self.repo.save_incident(inc)

        success = self.repo.resolve_incident(inc_id)
        self.assertTrue(success)

        incidents = self.repo.get_recent_incidents()
        self.assertEqual(incidents[0].status, "RESOLVED")

    def test_kpi_computation(self):
        self.repo.save_incident(Incident(violation_type="Missing Helmet", missing_ppe="helmet"))
        self.repo.save_incident(Incident(violation_type="Missing Safety Vest", missing_ppe="vest"))

        kpis = self.repo.get_kpis(current_active_workers=4)
        self.assertEqual(kpis.total_violations_today, 2)
        self.assertEqual(kpis.active_workers_count, 4)
        self.assertIn("Missing Helmet", kpis.ppe_breakdown)
        self.assertIn("Missing Safety Vest", kpis.ppe_breakdown)


if __name__ == "__main__":
    unittest.main()
