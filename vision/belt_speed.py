"""
Outfeed belt speed — tracks silver tape marks on a top-to-bottom belt.

Marks are placed exactly 12 inches apart. Vertical displacement between frames
gives velocity; known spacing auto-calibrates pixels-per-inch so no separate
env-var calibration is needed.

Belt ROI env vars (all as % of frame, 0–100):
  BELT_X1_PCT, BELT_X2_PCT, BELT_Y1_PCT, BELT_Y2_PCT
  Set these to confine detection to the belt area only.
"""
from __future__ import annotations

import collections
import logging
import os
import time
from typing import Optional

import cv2
import numpy as np

logger = logging.getLogger("harvest_oak.belt_speed")

_SPACING_INCHES    = 12.0
_MIN_AREA          = 4000    # px² — filters out small reflections and specular highlights
_MAX_AREA          = 80000   # px² — allow wide tape strips
_WINDOW_SECONDS    = 5.0
_X_MATCH_THRESHOLD = 80      # px — max horizontal drift between frames for same mark

# Silver/metallic tape: low saturation, high brightness
# Hue is irrelevant — metallic is near-achromatic
_SILVER_LOWER = np.array([0,   0,  180])
_SILVER_UPPER = np.array([180, 50, 255])


def _load_roi() -> tuple[float, float, float, float]:
    x1 = float(os.environ.get("BELT_X1_PCT", "0"))  / 100.0
    x2 = float(os.environ.get("BELT_X2_PCT", "100")) / 100.0
    y1 = float(os.environ.get("BELT_Y1_PCT", "0"))  / 100.0
    y2 = float(os.environ.get("BELT_Y2_PCT", "100")) / 100.0
    return x1, x2, y1, y2


class BeltSpeedTracker:
    def __init__(self):
        self._pixels_per_inch: Optional[float] = None
        self._prev_centroids: list[tuple[float, float]] = []
        self._prev_time: float = 0.0
        self._window: collections.deque = collections.deque(maxlen=300)
        self.fpm_instant: float = 0.0
        self.fpm_smoothed: float = 0.0
        self._roi = _load_roi()   # (x1_pct, x2_pct, y1_pct, y2_pct)
        self._dead_band_fpm = float(os.environ.get("SPEED_DEAD_BAND_FPM", "3.0"))

    def _roi_pixels(self, h: int, w: int) -> tuple[int, int, int, int]:
        x1p, x2p, y1p, y2p = self._roi
        return int(x1p * w), int(x2p * w), int(y1p * h), int(y2p * h)

    def _detect_stickers(self, frame: np.ndarray) -> list[tuple[float, float]]:
        """Return silver tape mark centroids (x, y) sorted top-to-bottom, within belt ROI."""
        h, w = frame.shape[:2]
        rx1, rx2, ry1, ry2 = self._roi_pixels(h, w)

        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        mask = cv2.inRange(hsv, _SILVER_LOWER, _SILVER_UPPER)

        # Zero out everything outside the belt ROI
        roi_mask = np.zeros_like(mask)
        roi_mask[ry1:ry2, rx1:rx2] = 255
        mask = cv2.bitwise_and(mask, roi_mask)

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
                    raw_fpm = (pix_per_sec / self._pixels_per_inch) * 60.0 / 12.0
                    self.fpm_instant = raw_fpm if raw_fpm >= self._dead_band_fpm else 0.0
                else:
                    self.fpm_instant = 0.0
                if self.fpm_instant > 0:
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
