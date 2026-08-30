"""Industrial PPE Compliance AI - Real-time PPE Detection & Safety Monitoring System."""

__version__ = "1.0.0"
__author__ = "Ahmed Khaled (Ahmed Algendy)"
__email__ = "contact@ahmedalgendy.com"
__website__ = "https://ahmedalgendy.com"

from ppe_detector.core.detector import PPEDetector, DetectionBox
from ppe_detector.core.compliance_engine import ComplianceEvaluator, WorkerComplianceState

__all__ = [
    "PPEDetector",
    "DetectionBox",
    "ComplianceEvaluator",
    "WorkerComplianceState",
    "__version__",
    "__author__",
]
