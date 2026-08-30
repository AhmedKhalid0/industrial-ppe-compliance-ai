"""Command-Line Interface for Offline Batch Video Analysis and PPE Auditing."""

from __future__ import annotations

import os
import sys
import time
import click
import cv2
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn, TimeRemainingColumn
from rich.panel import Panel

from ppe_detector.core.detector import PPEDetector, DetectionBox
from ppe_detector.core.tracker import CentroidIoUTracker
from ppe_detector.core.compliance_engine import ComplianceEvaluator
from ppe_detector.alerts.snapshot_manager import SnapshotManager
from ppe_detector.database.repository import IncidentRepository
from ppe_detector.database.models import Incident
from ppe_detector import __version__

console = Console()


@click.command(context_settings=dict(help_option_names=["-h", "--help"]))
@click.option("-i", "--input", "input_source", required=True, help="Input video file path or camera index (e.g. video.mp4, 0, or rtsp://...).")
@click.option("-o", "--output", "output_path", default=None, help="Path to save annotated video output (.mp4).")
@click.option("-w", "--weights", default="weights/yolov8n-ppe.pt", help="Path to YOLO model weights.")
@click.option("--conf", default=0.45, show_default=True, type=float, help="Detection confidence threshold.")
@click.option("--report", "report_path", default="reports/ppe_audit.csv", show_default=True, help="Path to export CSV safety audit.")
@click.version_option(version=__version__, prog_name="industrial-ppe-compliance-ai")
def cli(input_source: str, output_path: str | None, weights: str, conf: float, report_path: str):
    """🛡️ Real-Time Industrial PPE Compliance & Safety AI Monitoring CLI."""
    console.print(
        Panel.fit(
            f"[bold blue]Industrial PPE Compliance AI v{__version__}[/bold blue]\n"
            f"[dim]Edge Computer Vision & Real-Time Safety Monitoring System[/dim]\n"
            f"[green]Author: Ahmed Khaled (Ahmed Algendy)[/green] | [cyan]https://ahmedalgendy.com[/cyan]",
            border_style="blue",
        )
    )

    # Initialize video capture
    is_cam = input_source.isdigit()
    src = int(input_source) if is_cam else input_source

    cap = cv2.VideoCapture(src)
    if not cap.isOpened():
        console.print(f"[bold red]❌ Failed to open video source:[/bold red] {input_source}")
        sys.exit(1)

    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) if not is_cam else 1000
    fps = int(cap.get(cv2.CAP_PROP_FPS)) or 30
    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)) or 1280
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)) or 720

    console.print(f"[green]📹 Input Source:[/green] {input_source} ({w}x{h} @ {fps} FPS)")
    if output_path:
        console.print(f"[green]💾 Output Video Target:[/green] {output_path}")

    # Initialize components
    detector = PPEDetector(model_path=weights, confidence_threshold=conf)
    tracker = CentroidIoUTracker()
    compliance_evaluator = ComplianceEvaluator(required_ppe=["helmet", "vest"])
    snapshot_mgr = SnapshotManager(snapshot_dir="snapshots")
    repo = IncidentRepository()

    writer = None
    if output_path:
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        writer = cv2.VideoWriter(output_path, fourcc, fps, (w, h))

    total_violations_recorded = 0
    start_time = time.perf_counter()

    with Progress(
        SpinnerColumn(),
        TextColumn("[bold cyan]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        TextColumn("• {task.completed}/{task.total} frames"),
        TimeRemainingColumn(),
        console=console,
    ) as progress:
        task_id = progress.add_task("Analyzing PPE Compliance...", total=max(1, total_frames))
        frame_idx = 0

        while cap.isOpened():
            ret, frame = cap.read()
            if not ret or frame is None:
                break

            frame_idx += 1
            progress.update(task_id, completed=frame_idx)

            # Inference
            det_result = detector.detect(frame)
            person_boxes = [b for b in det_result.boxes if b.class_name == "person"]
            equipment_boxes = [b for b in det_result.boxes if b.class_name != "person"]

            # Tracking & Compliance
            tracked_workers = tracker.update(person_boxes)
            states = compliance_evaluator.evaluate_frame(tracked_workers, equipment_boxes)

            # Annotations
            for s in states:
                b = s.person_box
                color = (0, 220, 50) if s.is_compliant else (0, 0, 255)
                tag = f"Worker #{s.track_id} [OK]" if s.is_compliant else f"Worker #{s.track_id} [VIOLATION]"

                cv2.rectangle(frame, (int(b.x1), int(b.y1)), (int(b.x2), int(b.y2)), color, 2)
                cv2.putText(frame, tag, (int(b.x1), int(b.y1) - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)

                if s.is_persistent_violation and s.consecutive_violations == compliance_evaluator.persistence_threshold_frames:
                    snap_path = snapshot_mgr.capture_violation_snapshot(frame, s)
                    inc = Incident(
                        camera_id="CLI-INSPECT",
                        zone_name="Inspection Zone",
                        worker_track_id=s.track_id,
                        violation_type=", ".join(s.missing_items),
                        missing_ppe="helmet" if "Missing Helmet" in s.missing_items else "vest",
                        confidence=b.confidence,
                        snapshot_path=snap_path,
                    )
                    repo.save_incident(inc)
                    total_violations_recorded += 1

            if writer:
                writer.write(frame)

    cap.release()
    if writer:
        writer.release()

    duration = time.perf_counter() - start_time
    fps_avg = frame_idx / max(0.001, duration)

    # Summary Table
    summary = Table(title="📊 Safety Inspection Summary", border_style="blue")
    summary.add_column("Metric", style="cyan")
    summary.add_column("Value", style="bold white")

    summary.add_row("Total Frames Analyzed", str(frame_idx))
    summary.add_row("Average Processing Speed", f"{fps_avg:.1f} FPS")
    summary.add_row("Execution Duration", f"{duration:.2f} seconds")
    summary.add_row("Total Violations Recorded", f"[red]{total_violations_recorded}[/red]")
    summary.add_row("Report Saved", report_path)

    console.print("\n", summary)


if __name__ == "__main__":
    cli()
