"""Seed demo PPE incidents and metrics."""

import os
import cv2
import time
import numpy as np
from ppe_detector.database.repository import IncidentRepository
from ppe_detector.database.models import Incident

def seed_demo_data():
    repo = IncidentRepository()
    os.makedirs("snapshots", exist_ok=True)
    
    zones = ["Zone A (Welding)", "Zone B (Turbine Hall)", "Zone C (Chemical)", "Zone D (Scaffolding)"]
    violations = [
        ("Missing Hard Hat", "helmet"),
        ("Missing High-Vis Vest", "vest"),
        ("Missing Hard Hat & Vest", "helmet, vest"),
        ("Missing Safety Glasses", "glasses")
    ]
    
    for i in range(1, 13):
        # Generate synthetic frame
        img = np.zeros((480, 640, 3), dtype=np.uint8)
        img[:] = (20, 24, 30)
        
        cv2.rectangle(img, (180, 100), (460, 420), (45, 52, 65), -1)
        cv2.circle(img, (320, 160), 45, (80, 95, 115), -1)
        cv2.rectangle(img, (260, 210), (380, 380), (120, 140, 170), -1)
        
        v_title, v_ppe = violations[i % len(violations)]
        cv2.rectangle(img, (170, 90), (470, 430), (0, 0, 255), 2)
        cv2.putText(img, f"VIOLATION: {v_title}", (180, 80), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
        cv2.putText(img, f"{zones[i % len(zones)]} | Worker #{100+i} | Conf: 95%", (180, 455), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)
        
        snap_name = f"violation_20260901_{i:03d}.jpg"
        snap_path = os.path.join("snapshots", snap_name)
        cv2.imwrite(snap_path, img)
        
        inc = Incident(
            camera_id=f"CAM-0{((i-1)%4)+1}",
            zone_name=zones[i % len(zones)],
            worker_track_id=100 + i,
            violation_type=v_title,
            missing_ppe=v_ppe,
            confidence=0.95,
            snapshot_path=snap_name,
            status="RESOLVED" if i % 3 == 0 else "UNRESOLVED"
        )
        repo.save_incident(inc)

    print("Seeded 12 industrial PPE compliance incidents and synthetic snapshots.")

if __name__ == "__main__":
    seed_demo_data()
