"""One-Click Demo Runner for Industrial PPE Compliance AI Dashboard."""

from __future__ import annotations

import os
import sys
import webbrowser
import time

# Fix Windows console UTF-8 output
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# Ensure project root is in sys.path
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src"))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

import uvicorn
from ppe_detector.api.app import create_app


def main():
    port = int(os.getenv("PORT", "8090"))
    print("=" * 70)
    print("Starting Industrial PPE Compliance AI Operations Hub...")
    print("=" * 70)
    print("Real-Time YOLO Video Pipeline Initialized")
    print(f"Web Dashboard: http://localhost:{port}")
    print(f"MJPEG Video Feed: http://localhost:{port}/video_feed")
    print(f"API Documentation: http://localhost:{port}/docs")
    print("=" * 70)

    # Automatically open browser after 1.5 seconds
    def open_browser():
        time.sleep(1.5)
        webbrowser.open(f"http://localhost:{port}")

    import threading
    threading.Thread(target=open_browser, daemon=True).start()

    app = create_app()
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")


if __name__ == "__main__":
    main()
