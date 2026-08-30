"""Database entity models and schema definitions."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any


@dataclass
class Incident:
    """Represents an individual recorded safety non-compliance incident."""
    id: Optional[int] = None
    timestamp: str = field(default_factory=lambda: time.strftime("%Y-%m-%d %H:%M:%S"))
    camera_id: str = "CAM-01"
    zone_name: str = "Zone A (Assembly)"
    worker_track_id: int = 1
    violation_type: str = "Missing Helmet"
    missing_ppe: str = "helmet"
    confidence: float = 0.92
    snapshot_path: Optional[str] = None
    status: str = "UNRESOLVED"  # "UNRESOLVED", "RESOLVED", "FALSE_POSITIVE"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "timestamp": self.timestamp,
            "camera_id": self.camera_id,
            "zone_name": self.zone_name,
            "worker_track_id": self.worker_track_id,
            "violation_type": self.violation_type,
            "missing_ppe": self.missing_ppe,
            "confidence": round(self.confidence, 2),
            "snapshot_path": self.snapshot_path,
            "status": self.status,
        }


@dataclass
class Zone:
    """Industrial plant zone with specific PPE requirements."""
    id: str
    name: str
    required_ppe: List[str]
    description: str = ""


@dataclass
class SafetyKPIs:
    """Aggregated safety metrics and compliance indicators."""
    compliance_rate_percent: float = 100.0
    active_workers_count: int = 0
    total_violations_today: int = 0
    resolved_incidents_today: int = 0
    high_risk_zones: List[Dict[str, Any]] = field(default_factory=list)
    hourly_trend: Dict[str, int] = field(default_factory=dict)
    ppe_breakdown: Dict[str, int] = field(default_factory=dict)
