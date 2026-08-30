"""REST API Route Handlers for Incidents, Metrics, and Reports."""

from __future__ import annotations

import csv
import io
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Response
from ppe_detector.database.repository import IncidentRepository
from ppe_detector.database.models import Incident, SafetyKPIs

router = APIRouter(prefix="/api", tags=["Safety API"])


def get_repo() -> IncidentRepository:
    return IncidentRepository()


@router.get("/kpis", response_model=None)
async def get_kpis(active_workers: int = 2, repo: IncidentRepository = Depends(get_repo)):
    """Fetch real-time Safety KPIs, compliance rates, and hourly incident trends."""
    kpis = repo.get_kpis(current_active_workers=active_workers)
    return {
        "compliance_rate_percent": kpis.compliance_rate_percent,
        "active_workers_count": kpis.active_workers_count,
        "total_violations_today": kpis.total_violations_today,
        "resolved_incidents_today": kpis.resolved_incidents_today,
        "hourly_trend": kpis.hourly_trend,
        "ppe_breakdown": kpis.ppe_breakdown,
        "high_risk_zones": kpis.high_risk_zones,
    }


@router.get("/incidents", response_model=None)
async def list_incidents(
    limit: int = Query(50, ge=1, le=200),
    repo: IncidentRepository = Depends(get_repo),
):
    """Retrieve the latest detected safety violation incidents."""
    incidents = repo.get_recent_incidents(limit=limit)
    return [inc.to_dict() for inc in incidents]


@router.post("/incidents/{incident_id}/resolve")
async def resolve_incident(incident_id: int, repo: IncidentRepository = Depends(get_repo)):
    """Mark a specific safety incident as RESOLVED."""
    success = repo.resolve_incident(incident_id)
    if not success:
        raise HTTPException(status_code=404, detail="Incident not found")
    return {"status": "success", "message": f"Incident #{incident_id} marked as resolved"}


@router.get("/export/csv")
async def export_incidents_csv(repo: IncidentRepository = Depends(get_repo)):
    """Export all recorded safety incidents as a CSV audit report."""
    incidents = repo.get_recent_incidents(limit=500)

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "Incident ID", "Timestamp", "Camera ID", "Zone Name",
        "Worker Track ID", "Violation Type", "Confidence", "Status"
    ])

    for inc in incidents:
        writer.writerow([
            inc.id, inc.timestamp, inc.camera_id, inc.zone_name,
            inc.worker_track_id, inc.violation_type, f"{int(inc.confidence*100)}%", inc.status
        ])

    return Response(
        content=output.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=safety_audit_report.csv"},
    )


@router.get("/zones")
async def get_zones():
    """List designated safety zones and required PPE gear."""
    return [
        {
            "id": "zone-a",
            "name": "Zone A: Heavy Machinery & Assembly",
            "required_ppe": ["helmet", "vest", "boots"],
            "risk_level": "High",
        },
        {
            "id": "zone-b",
            "name": "Zone B: Material Handling & Logistics",
            "required_ppe": ["helmet", "vest"],
            "risk_level": "Medium",
        },
        {
            "id": "zone-c",
            "name": "Zone C: Inspection & Control Room",
            "required_ppe": ["vest"],
            "risk_level": "Low",
        },
    ]
