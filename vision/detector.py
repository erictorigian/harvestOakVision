"""
Board detection — virtual tripwire approach using MOG2 background subtraction.

Logic:
1. MOG2 isolates moving regions
2. Contours crossing the detection line trigger a count
3. Cooldown prevents double-counting a single board
4. Direction filtering — only count forward-moving boards
"""
from __future__ import annotations

import logging
import os
import time
from typing import Optional

import cv2
import numpy as np

logger = logging.getLogger("harvest_oak.detector")


class BoardDetector:
    def __init__(self):
        # Config from env vars
        self.line_y_pct = float(os.environ.get("DETECTION_LINE_Y_PERCENT", "50")) / 100.0
        self.min_contour_area = int(os.environ.get("MIN_CONTOUR_AREA", "2000"))
        self.cooldown_ms = int(os.environ.get("COUNT_COOLDOWN_MS", "800"))
        self.direction = os.environ.get("PRODUCTION_DIRECTION", "left_to_right")

        # Background subtractor — shadows=False reduces false positives on belt texture
        self._mog2 = cv2.createBackgroundSubtractorMOG2(
            history=500, varThreshold=50, detectShadows=False
        )

        # Morphological kernel for noise cleanup
        self._kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))

        # Per-frame state
        self._frame_h: int = 0
        self._frame_w: int = 0
        self._detection_y: int = 0

        # Cooldown tracking per horizontal zone (split frame into segments)
        # Prevents re-counting the same board as it slowly crawls through the line
        self._zone_last_count: dict[int, float] = {}
        self._zone_count = 8  # number of horizontal segments

        # Total counts
        self.total_pieces: int = 0
        self._last_crossing_events: list[dict] = []  # cleared each second

    def _line_y(self, frame_h: int) -> int:
        return int(frame_h * self.line_y_pct)

    def update_frame_size(self, h: int, w: int):
        if self._frame_h != h or self._frame_w != w:
            self._frame_h = h
            self._frame_w = w
            self._detection_y = self._line_y(h)
            logger.info(f"Frame size updated: {w}x{h}, detection line Y={self._detection_y}")

    def process_frame(self, frame: np.ndarray, debug: bool = False) -> tuple[int, list[dict], Optional[np.ndarray]]:
        """
        Process one frame.
        Returns: (new_pieces_this_frame, crossing_events, debug_frame_or_None)
        """
        h, w = frame.shape[:2]
        self.update_frame_size(h, w)

        # Apply background subtraction
        fg_mask = self._mog2.apply(frame)

        # Morphological cleanup — remove noise, fill holes
        fg_mask = cv2.morphologyEx(fg_mask, cv2.MORPH_OPEN, self._kernel)
        fg_mask = cv2.morphologyEx(fg_mask, cv2.MORPH_CLOSE, self._kernel)
        fg_mask = cv2.dilate(fg_mask, self._kernel, iterations=2)

        # Find contours
        contours, _ = cv2.findContours(fg_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        new_pieces = 0
        events = []
        now_ms = time.time() * 1000

        if debug:
            debug_frame = frame.copy()
            # Draw detection line
            cv2.line(debug_frame, (0, self._detection_y), (w, self._detection_y), (0, 255, 255), 2)
            cv2.putText(debug_frame, "DETECTION LINE", (10, self._detection_y - 8),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)
        else:
            debug_frame = None

        for contour in contours:
            area = cv2.contourArea(contour)
            if area < self.min_contour_area:
                continue

            x, y, bw, bh = cv2.boundingRect(contour)
            cx = x + bw // 2
            cy = y + bh // 2

            # Check if contour intersects detection line
            top = y
            bottom = y + bh
            crosses_line = top <= self._detection_y <= bottom

            if debug and debug_frame is not None:
                color = (0, 255, 0) if crosses_line else (100, 100, 100)
                cv2.rectangle(debug_frame, (x, y), (x + bw, y + bh), color, 2)
                cv2.circle(debug_frame, (cx, cy), 4, color, -1)

            if not crosses_line:
                continue

            # Determine horizontal zone for cooldown
            zone = int(cx / w * self._zone_count)
            last_count = self._zone_last_count.get(zone, 0)

            if (now_ms - last_count) < self.cooldown_ms:
                continue  # still in cooldown for this zone

            # Check motion direction (only count forward direction)
            if not self._check_direction(contour, w):
                continue

            # Count it
            self._zone_last_count[zone] = now_ms
            self.total_pieces += 1
            new_pieces += 1

            event = {
                "direction": self.direction,
                "confidence": min(1.0, area / (self.min_contour_area * 5)),
                "x": cx,
                "y": cy,
            }
            events.append(event)

            if debug and debug_frame is not None:
                cv2.putText(debug_frame, f"COUNT! #{self.total_pieces}", (cx, cy - 10),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)

        if debug and debug_frame is not None:
            # State overlay
            cv2.putText(debug_frame, f"Total: {self.total_pieces}", (10, 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 0), 2)

        self._last_crossing_events = events
        return new_pieces, events, debug_frame

    def _check_direction(self, contour: np.ndarray, frame_w: int) -> bool:
        """
        Minimal direction check: for now accept all crossings.
        Phase 2: implement optical flow direction per contour.
        """
        # PHASE 2: Use tracked centroid history to determine direction vector
        return True

    def motion_level(self, fg_mask: Optional[np.ndarray] = None) -> float:
        """Return fraction of frame with active motion (0.0 – 1.0)."""
        if fg_mask is None:
            return 0.0
        total_pixels = fg_mask.shape[0] * fg_mask.shape[1]
        motion_pixels = cv2.countNonZero(fg_mask)
        return motion_pixels / total_pixels if total_pixels > 0 else 0.0

    def get_fg_mask(self, frame: np.ndarray) -> np.ndarray:
        """Return the foreground mask for a frame (used by downtime detector)."""
        fg = self._mog2.apply(frame, learningRate=0)  # no learning — just classify
        fg = cv2.morphologyEx(fg, cv2.MORPH_OPEN, self._kernel)
        return fg
