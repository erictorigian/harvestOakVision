"""
Outfeed belt speed — tracks colored sticker positions on a top-to-bottom belt.

Stickers are placed exactly 12 inches apart (red at ends, yellow between).
Vertical displacement between frames gives velocity; known spacing auto-calibrates
pixels-per-inch so no separate env-var calibration is needed.
"""
from __future__ import annotations

import collections
import logging
import time
from typing import Optional

import cv2
import numpy as np

logger = logging.getLogger("harvest_oak.belt_speed")

_SPACING_INCHES    = 12.0
_MIN_AREA          = 80      # px² — reject noise
_MAX_AREA          = 8000    # px² — reject large belt-texture blobs
_WINDOW_SECONDS    = 5.0
_X_MATCH_THRESHOLD = 60      # px — max horizontal drift between frames for same sticker

# Red wraps around the HSV hue wheel — two ranges needed
_RED_LOWER1 = np.array([0,   120,  70])
_RED_UPPER1 = np.array([10,  255, 255])
_RED_LOWER2 = np.array([170, 120,  70])
_RED_UPPER2 = np.array([180, 255, 255])

_YEL_LOWER  = np.array([20, 120, 100])
_YEL_UPPER  = np.array([35, 255, 255])


class BeltSpeedTracker:
    def __init__(self):
        self._pixels_per_inch: Optional[float] = None
        self._prev_centroids: list[tuple[float, float]] = []
        self._prev_time: float = 0.0
        self._window: collections.deque = collections.deque(maxlen=300)
        self.fpm_instant: float = 0.0
        self.fpm_smoothed: float = 0.0

    def _detect_stickers(self, frame: np.ndarray) -> list[tuple[float, float]]:
        """Return sticker centroids (x, y) sorted top-to-bottom."""
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

        red = (cv2.inRange(hsv, _RED_LOWER1, _RED_UPPER1) |
               cv2.inRange(hsv, _RED_LOWER2, _RED_UPPER2))
        yel = cv2.inRange(hsv, _YEL_LOWER, _YEL_UPPER)
        mask = cv2.bitwise_or(red, yel)

        k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, k)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, k)

        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        centroids = []
        for c in contours:
            area = cv2.contourArea(c)
            if _MIN_AREA <= area <= _MAX_AREA:
                M = cv2.moments(c)
                if M["m00"] > 0:
                    centroids.append((M["m10"] / M["m00"], M["m01"] / M["m00"]))

        centroids.sort(key=lambda p: p[1])
        return centroids

    def _update_calibration(self, centroids: list[tuple[float, float]]):
        """Re-derive px/inch from sticker spacing whenever ≥2 are visible."""
        if len(centroids) < 2:
            return
        spacings = [
            abs(centroids[i + 1][1] - centroids[i][1])
            for i in range(len(centroids) - 1)
            if abs(centroids[i + 1][1] - centroids[i][1]) > 5
        ]
        if spacings:
            px_per_inch = float(np.median(spacings)) / _SPACING_INCHES
            if px_per_inch > 0:
                self._pixels_per_inch = px_per_inch
                logger.debug(f"Belt calibration updated: {self._pixels_per_inch:.2f} px/inch")

    def process_frame(self, frame: np.ndarray) -> tuple[float, float]:
        """
        Detect stickers, update calibration, compute belt FPM.
        Returns (fpm_instant, fpm_smoothed).
        """
        now = time.time()
        centroids = self._detect_stickers(frame)
        self._update_calibration(centroids)

        dt = now - self._prev_time
        if centroids and self._prev_centroids and self._pixels_per_inch and 0 < dt < 1.0:
            dy_values = []
            for cx, cy in centroids:
                best_dist = float("inf")
                best_dy: Optional[float] = None
                for px, py in self._prev_centroids:
                    x_dist = abs(cx - px)
                    if x_dist < best_dist:
                        best_dist = x_dist
                        best_dy = cy - py
                if best_dy is not None and best_dist < _X_MATCH_THRESHOLD:
                    dy_values.append(best_dy)

            if dy_values:
                median_dy = float(np.median(dy_values))
                if median_dy > 0:  # positive = moving downward (top-to-bottom belt)
                    pix_per_sec = median_dy / dt
                    self.fpm_instant = (pix_per_sec / self._pixels_per_inch) * 60.0 / 12.0
                else:
                    self.fpm_instant = 0.0
                self._window.append((now, self.fpm_instant))

        cutoff = now - _WINDOW_SECONDS
        recent = [v for t, v in self._window if t >= cutoff and v > 0]
        if recent:
            self.fpm_smoothed = float(np.mean(recent))
        elif self.fpm_smoothed > 0:
            self.fpm_smoothed = max(0.0, self.fpm_smoothed * 0.95)

        self._prev_centroids = centroids
        self._prev_time = now
        return self.fpm_instant, self.fpm_smoothed
