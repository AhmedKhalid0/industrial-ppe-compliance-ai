"""Threaded Video Stream Capture & Frame Buffer."""

from __future__ import annotations

import cv2
import time
import threading
import numpy as np
from queue import Queue, Empty
from typing import Optional, Union, Tuple


class ThreadedVideoStream:
    """Non-blocking threaded video reader supporting RTSP, Webcams, and synthetic video."""

    def __init__(
        self,
        source: Union[int, str] = 0,
        target_size: Optional[Tuple[int, int]] = (1280, 720),
        fps_limit: int = 30,
        use_synthetic_fallback: bool = True,
    ):
        self.source = source
        self.target_size = target_size
        self.fps_limit = fps_limit
        self.use_synthetic_fallback = use_synthetic_fallback

        self.cap: Optional[cv2.VideoCapture] = None
        self.is_running = False
        self.is_synthetic = False
        self.thread: Optional[threading.Thread] = None

        self._frame_lock = threading.Lock()
        self._latest_frame: Optional[np.ndarray] = None
        self._synthetic_tick = 0

        self._init_capture()

    def _init_capture(self):
        """Initialize OpenCV video capture or activate synthetic stream generator."""
        try:
            # Check if source is integer (webcam)
            if isinstance(self.source, str) and self.source.isdigit():
                src = int(self.source)
            else:
                src = self.source

            self.cap = cv2.VideoCapture(src)
            if self.cap.isOpened():
                ret, frame = self.cap.read()
                if ret and frame is not None:
                    self.is_synthetic = False
                    return
        except Exception:
            pass

        if self.use_synthetic_fallback:
            self.is_synthetic = True
            if self.cap is not None:
                self.cap.release()
                self.cap = None

    def start(self) -> ThreadedVideoStream:
        """Start the background frame capture thread."""
        if self.is_running:
            return self

        self.is_running = True
        self.thread = threading.Thread(target=self._capture_worker, daemon=True)
        self.thread.start()
        return self

    def _generate_synthetic_frame(self) -> np.ndarray:
        """Generate a synthetic CCTV surveillance frame with moving workers."""
        w, h = self.target_size if self.target_size else (1280, 720)
        frame = np.zeros((h, w, 3), dtype=np.uint8)

        # Industrial Background Grid
        frame[:] = (26, 22, 20)  # Dark industrial gray
        for y in range(0, h, 60):
            cv2.line(frame, (0, y), (w, y), (40, 36, 32), 1)
        for x in range(0, w, 60):
            cv2.line(frame, (x, 0), (x, h), (40, 36, 32), 1)

        # Draw Industrial Zone & Machinery
        cv2.rectangle(frame, (50, 80), (450, 620), (35, 45, 55), -1)
        cv2.putText(frame, "ZONE A: HEAVY MACHINERY & ASSEMBLY", (60, 110), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (120, 160, 200), 2)

        cv2.rectangle(frame, (520, 80), (1220, 620), (35, 55, 45), -1)
        cv2.putText(frame, "ZONE B: MATERIAL HANDLING & LOGISTICS", (530, 110), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (120, 200, 160), 2)

        # Animated Worker 1 (Compliant: Moving across Zone A)
        self._synthetic_tick += 1
        pos_x1 = int(120 + ((self._synthetic_tick * 3) % 260))
        pos_y1 = 280

        # Draw Worker 1 Silhouette
        cv2.rectangle(frame, (pos_x1, pos_y1), (pos_x1 + 100, pos_y1 + 220), (80, 80, 90), -1)
        # Head with Yellow Helmet
        cv2.circle(frame, (pos_x1 + 50, pos_y1 + 35), 25, (0, 215, 255), -1)
        # Torso with Orange Safety Vest
        cv2.rectangle(frame, (pos_x1 + 15, pos_y1 + 65), (pos_x1 + 85, pos_y1 + 155), (0, 140, 255), -1)

        # Animated Worker 2 (Violator: Missing Helmet in Zone B)
        pos_x2 = int(600 + ((self._synthetic_tick * 2) % 480))
        pos_y2 = 300
        # Draw Worker 2 Silhouette
        cv2.rectangle(frame, (pos_x2, pos_y2), (pos_x2 + 100, pos_y2 + 220), (80, 80, 90), -1)
        # Head with NO Helmet (Dark brown hair)
        cv2.circle(frame, (pos_x2 + 50, pos_y2 + 35), 25, (40, 30, 80), -1)
        # Torso with Safety Vest
        cv2.rectangle(frame, (pos_x2 + 15, pos_y2 + 65), (pos_x2 + 85, pos_y2 + 155), (0, 140, 255), -1)

        # Surveillance Timestamp Overlay
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        cv2.putText(frame, f"CAM-01 [RTSP LIVE] | {timestamp}", (30, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

        return frame

    def _capture_worker(self):
        """Worker loop reading frames continuously."""
        frame_interval = 1.0 / max(1, self.fps_limit)

        while self.is_running:
            loop_start = time.time()

            if self.is_synthetic or self.cap is None:
                frame = self._generate_synthetic_frame()
            else:
                ret, frame = self.cap.read()
                if not ret or frame is None:
                    # Loop video or switch to synthetic if video ended
                    self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                    time.sleep(0.05)
                    continue

                if self.target_size:
                    frame = cv2.resize(frame, self.target_size)

            with self._frame_lock:
                self._latest_frame = frame

            elapsed = time.time() - loop_start
            sleep_time = max(0.001, frame_interval - elapsed)
            time.sleep(sleep_time)

    def read(self) -> Optional[np.ndarray]:
        """Get a copy of the latest captured frame."""
        with self._frame_lock:
            if self._latest_frame is None:
                return None
            return self._latest_frame.copy()

    def get_frame_jpeg(self, quality: int = 80) -> Optional[bytes]:
        """Encode latest frame as JPEG bytes for HTTP / WebSocket streaming."""
        frame = self.read()
        if frame is None:
            return None
        ret, buffer = cv2.imencode(".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), quality])
        if not ret:
            return None
        return buffer.tobytes()

    def stop(self):
        """Stop capture thread and release hardware resources."""
        self.is_running = False
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=1.0)
        if self.cap:
            self.cap.release()
            self.cap = None
