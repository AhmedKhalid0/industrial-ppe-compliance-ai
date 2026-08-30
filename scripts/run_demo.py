"""One-Click Demo Runner for Industrial PPE Compliance AI Dashboard."""

from __future__ import annotations

import os
import sys
import webbrowser
import time

# Ensure project root is in sys.path
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src"))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

import uvicorn
from ppe_detector.api.app import create_app


def main():
    print("=" * 70)
    print("🛡️  Starting Industrial PPE Compliance AI Operations Hub...")
    print("=" * 70)
    print("⚡ Real-Time YOLO Video Pipeline Initialized")
    print("🌐 Web Dashboard: http://localhost:8000")
    print("📹 MJPEG Video Feed: http://localhost:8000/video_feed")
    print("📊 API Documentation: http://localhost:8000/docs")
    print("=" * 70)

    # Automatically open browser after 1.5 seconds
    def open_browser():
        time.sleep(1.5)
        webbrowser.open("http://localhost:8000")

    import threading
    threading.Thread(target=open_browser, daemon=True).start()

    app = create_app()
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")


if __name__ == "__main__":
    main()
