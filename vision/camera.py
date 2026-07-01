"""
Camera abstraction — RTSP / HTTP MJPEG / USB / test video file.

Handles reconnection with exponential backoff automatically.
"""
from __future__ import annotations

import logging
import os
import time
from typing import Optional

import cv2
import numpy as np

logger = logging.getLogger("harvest_oak.camera")


class CameraSource:
    def __init__(self, hw_config: dict):
        self.frame_width: int = hw_config["frame_width"]
        self._cap: Optional[cv2.VideoCapture] = None
        self._source: str | int = self._resolve_source()
        self._backoff = 1.0
        self._connected = False

    def _resolve_source(self) -> str | int:
        if os.environ.get("TEST_VIDEO_PATH"):
            path = os.environ["TEST_VIDEO_PATH"]
            logger.info(f"Test mode: using video file {path}")
            return path
        if os.environ.get("CAMERA_RTSP_URL"):
            url = os.environ["CAMERA_RTSP_URL"]
            logger.info(f"RTSP source: {url}")
            return url
        if os.environ.get("CAMERA_HTTP_URL"):
            url = os.environ["CAMERA_HTTP_URL"]
            logger.info(f"HTTP MJPEG source: {url}")
            return url
        index = int(os.environ.get("CAMERA_INDEX", "0"))
        logger.info(f"USB camera index: {index}")
        return index

    def connect(self) -> bool:
        if self._cap:
            self._cap.release()

        source = self._source
        logger.info(f"Connecting to camera source: {source}")

        # RTSP transport must be set before VideoCapture is opened
        if isinstance(source, str) and source.startswith("rtsp"):
            os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = "rtsp_transport;tcp"

        cap = cv2.VideoCapture(source)

        if not cap.isOpened():
            logger.warning(f"Could not open camera source: {source}")
            self._connected = False
            return False

        self._cap = cap
        self._connected = True
        self._backoff = 1.0
        actual_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        actual_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps = cap.get(cv2.CAP_PROP_FPS)
        logger.info(f"Camera connected: {actual_w}x{actual_h} @ {fps:.1f} FPS")
        return True

    def read_frame(self) -> Optional[np.ndarray]:
        if not self._cap or not self._connected:
            return None

        ret, frame = self._cap.read()
        if not ret or frame is None:
            logger.warning("Frame read failed — triggering reconnect")
            self._connected = False
            return None

        # Resize to configured width maintaining aspect ratio
        h, w = frame.shape[:2]
        if w != self.frame_width:
            scale = self.frame_width / w
            new_h = int(h * scale)
            frame = cv2.resize(frame, (self.frame_width, new_h))

        return frame

    def reconnect_if_needed(self) -> bool:
        """Call this when read_frame returns None. Implements exponential backoff."""
        if self._connected:
            return True
        logger.info(f"Attempting reconnect in {self._backoff:.1f}s...")
        time.sleep(self._backoff)
        self._backoff = min(self._backoff * 2, 30.0)

        # For test video, loop it
        if isinstance(self._source, str) and os.path.isfile(self._source):
            logger.info("Test video ended — looping")

        return self.connect()

    @property
    def is_connected(self) -> bool:
        return self._connected

    def release(self):
        if self._cap:
            self._cap.release()
            self._cap = None
        self._connected = False
