"""FastAPI Web Application, Live MJPEG Video Streamer, and WebSocket Server."""

from __future__ import annotations

import os
import cv2
import time
import asyncio
import numpy as np
from typing import AsyncGenerator
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from ppe_detector.core.detector import PPEDetector, DetectionBox
from ppe_detector.core.tracker import CentroidIoUTracker
from ppe_detector.core.compliance_engine import ComplianceEvaluator
from ppe_detector.core.video_stream import ThreadedVideoStream
from ppe_detector.alerts.snapshot_manager import SnapshotManager
from ppe_detector.database.repository import IncidentRepository
from ppe_detector.database.models import Incident
from ppe_detector.api.routes import router as api_router
from ppe_detector import __version__

# Global Pipelines
video_stream: ThreadedVideoStream | None = None
detector: PPEDetector | None = None
tracker: CentroidIoUTracker | None = None
compliance_evaluator: ComplianceEvaluator | None = None
snapshot_mgr: SnapshotManager | None = None
repo: IncidentRepository | None = None

latest_processed_jpeg: bytes = b""
active_worker_count: int = 2


def get_base_dir() -> str:
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def create_app() -> FastAPI:
    """FastAPI Application Factory."""
    global video_stream, detector, tracker, compliance_evaluator, snapshot_mgr, repo

    app = FastAPI(
        title="Industrial PPE Compliance AI",
        description="Real-Time Computer Vision & HSE Safety Monitoring Platform",
        version=__version__,
    )

    base_dir = get_base_dir()
    static_dir = os.path.join(base_dir, "dashboard", "static")
    templates_dir = os.path.join(base_dir, "dashboard", "templates")
    snapshots_dir = os.path.abspath("snapshots")

    os.makedirs(static_dir, exist_ok=True)
    os.makedirs(templates_dir, exist_ok=True)
    os.makedirs(snapshots_dir, exist_ok=True)

    app.mount("/static", StaticFiles(directory=static_dir), name="static")
    app.mount("/snapshots", StaticFiles(directory=snapshots_dir), name="snapshots")

    templates = Jinja2Templates(directory=templates_dir)

    # Initialize Core Engines
    video_stream = ThreadedVideoStream(source=os.getenv("CAMERA_SOURCE", "0"), use_synthetic_fallback=True)
    video_stream.start()

    detector = PPEDetector(confidence_threshold=0.45)
    tracker = CentroidIoUTracker()
    compliance_evaluator = ComplianceEvaluator(required_ppe=["helmet", "vest"], persistence_threshold_frames=4)
    snapshot_mgr = SnapshotManager(snapshot_dir=snapshots_dir)
    repo = IncidentRepository()

    app.include_router(api_router)

    @app.get("/", response_class=HTMLResponse)
    async def dashboard_home(request: Request):
        return templates.TemplateResponse(request=request, name="index.html", context={"version": __version__})

    @app.get("/video_feed")
    def video_feed():
        """MJPEG Live Streaming Feed with AI Bounding Box Overlays."""
        return StreamingResponse(
            generate_stream_frames(),
            media_type="multipart/x-mixed-replace; boundary=frame",
        )

    @app.websocket("/ws/telemetry")
    async def telemetry_websocket(websocket: WebSocket):
        """WebSocket Streaming real-time KPIs and live worker state to UI."""
        await websocket.accept()
        try:
            while True:
                kpis = repo.get_kpis(current_active_workers=active_worker_count)
                recent_incidents = repo.get_recent_incidents(limit=5)
                payload = {
                    "kpis": {
                        "compliance_rate_percent": kpis.compliance_rate_percent,
                        "active_workers_count": kpis.active_workers_count,
                        "total_violations_today": kpis.total_violations_today,
                        "hourly_trend": kpis.hourly_trend,
                        "ppe_breakdown": kpis.ppe_breakdown,
                    },
                    "recent_incidents": [i.to_dict() for i in recent_incidents],
                    "timestamp": time.strftime("%H:%M:%S"),
                }
                await websocket.send_json(payload)
                await asyncio.sleep(1.0)
        except WebSocketDisconnect:
            pass

    return app


def generate_stream_frames() -> AsyncGenerator[bytes, None]:
    """Continuous generator processing video frames with AI detection and HUD overlays."""
    global latest_processed_jpeg, active_worker_count

    while True:
        if video_stream is None:
            time.sleep(0.05)
            continue

        raw_frame = video_stream.read()
        if raw_frame is None:
            time.sleep(0.03)
            continue

        # In synthetic mode or real mode, simulate detections if no model weights
        annotated_frame = raw_frame.copy()
        h, w = annotated_frame.shape[:2]

        # In synthetic stream, extract simulated bounding boxes
        if video_stream.is_synthetic:
            # Synthetic Worker 1 (Compliant)
            tick = video_stream._synthetic_tick
            x1 = int(120 + ((tick * 3) % 260))
            w1_box = DetectionBox(x1, 280, x1 + 100, 500, 0.94, "person", 0)
            h1_box = DetectionBox(x1 + 25, 280, x1 + 75, 335, 0.96, "helmet", 1)
            v1_box = DetectionBox(x1 + 15, 345, x1 + 85, 435, 0.92, "vest", 3)

            # Synthetic Worker 2 (Violator - Missing Helmet)
            x2 = int(600 + ((tick * 2) % 480))
            w2_box = DetectionBox(x2, 300, x2 + 100, 520, 0.91, "person", 0)
            v2_box = DetectionBox(x2 + 15, 365, x2 + 85, 455, 0.89, "vest", 3)

            person_boxes = [w1_box, w2_box]
            equipment_boxes = [h1_box, v1_box, v2_box]
        else:
            # Real YOLO detection
            det_result = detector.detect(raw_frame)
            person_boxes = [b for b in det_result.boxes if b.class_name == "person"]
            equipment_boxes = [b for b in det_result.boxes if b.class_name != "person"]

        # Track Workers
        tracked_workers = tracker.update(person_boxes)
        active_worker_count = len(tracked_workers)

        # Evaluate Safety Rules
        compliance_states = compliance_evaluator.evaluate_frame(tracked_workers, equipment_boxes)

        # Render Bounding Boxes & HUD
        for state in compliance_states:
            b = state.person_box
            if state.is_compliant:
                color = (0, 220, 50)  # Green
                status_text = f"Worker #{state.track_id} [COMPLIANT]"
            else:
                color = (0, 0, 255)  # Red Alert
                status_text = f"Worker #{state.track_id} [VIOLATION: {', '.join(state.missing_items)}]"

                # Capture snapshot on persistent violation
                if state.is_persistent_violation and state.consecutive_violations == compliance_evaluator.persistence_threshold_frames:
                    snap_path = snapshot_mgr.capture_violation_snapshot(raw_frame, state)
                    incident = Incident(
                        camera_id="CAM-01",
                        zone_name="Zone B (Logistics)" if b.x1 > 500 else "Zone A (Assembly)",
                        worker_track_id=state.track_id,
                        violation_type=", ".join(state.missing_items),
                        missing_ppe="helmet" if "Missing Helmet" in state.missing_items else "vest",
                        confidence=b.confidence,
                        snapshot_path=snap_path,
                    )
                    repo.save_incident(incident)

            # Draw Person Bounding Box
            cv2.rectangle(annotated_frame, (int(b.x1), int(b.y1)), (int(b.x2), int(b.y2)), color, 2)
            # Tag header background
            cv2.rectangle(annotated_frame, (int(b.x1), int(b.y1) - 26), (int(b.x2), int(b.y1)), color, -1)
            cv2.putText(annotated_frame, status_text, (int(b.x1) + 4, int(b.y1) - 8), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 255), 1)

        # Draw Equipment boxes
        for eq in equipment_boxes:
            eq_color = (0, 200, 255) if "helmet" in eq.class_name else (255, 140, 0)
            cv2.rectangle(annotated_frame, (int(eq.x1), int(eq.y1)), (int(eq.x2), int(eq.y2)), eq_color, 1)

        # Encode Frame to JPEG
        ret, jpeg = cv2.imencode(".jpg", annotated_frame, [int(cv2.IMWRITE_JPEG_QUALITY), 80])
        if ret:
            latest_processed_jpeg = jpeg.tobytes()
            yield (
                b"--frame\r\n"
                b"Content-Type: image/jpeg\r\n\r\n" + latest_processed_jpeg + b"\r\n"
            )

        time.sleep(0.033)  # ~30 FPS


def start():
    """Entrypoint to launch Uvicorn web server."""
    import uvicorn
    uvicorn.run("ppe_detector.api.app:create_app", host="0.0.0.0", port=8000, factory=True, reload=False)


if __name__ == "__main__":
    start()
