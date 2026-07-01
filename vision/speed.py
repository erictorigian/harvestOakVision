"""
Line speed calculation using Lucas-Kanade sparse optical flow.

Converts pixel velocity → feet per minute using conveyor calibration.
Smoothed over a 5-second rolling window.
"""
from __future__ import annotations

import collections
import logging
import os
import time
from typing import Optional

import cv2
import numpy as np

logger = logging.getLogger("harvest_oak.speed")

# Lucas-Kanade parameters
_LK_PARAMS = dict(
    winSize=(21, 21),
    maxLevel=3,
    criteria=(cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 30, 0.01),
)
_FEATURE_PARAMS = dict(
    maxCorners=100,
    qualityLevel=0.01,
    minDistance=10,
    blockSize=7,
)


class SpeedCalculator:
    def __init__(self, frame_width: int):
        self.frame_width = frame_width
        self.conveyor_visible_feet = float(os.environ.get("CONVEYOR_VISIBLE_FEET", "8.0"))
        self.pixels_per_foot = frame_width / self.conveyor_visible_feet
        # Below this FPM, treat as zero — filters camera vibration and JPEG noise
        self._dead_band_fpm = float(os.environ.get("SPEED_DEAD_BAND_FPM", "3.0"))

        # Rolling window: (timestamp, fpm_value)
        self._window: collections.deque = collections.deque(maxlen=500)
        self._window_seconds = 5.0

        self._prev_gray: Optional[np.ndarray] = None
        self._prev_points: Optional[np.ndarray] = None
        self._prev_time: float = 0.0

        self.fpm_instant: float = 0.0
        self.fpm_smoothed: float = 0.0

        logger.info(
            f"SpeedCalc init: {self.conveyor_visible_feet}ft visible, "
            f"{self.pixels_per_foot:.1f} px/ft, frame_width={frame_width}"
        )

    def update_calibration(self, conveyor_visible_feet: float):
        self.conveyor_visible_feet = conveyor_visible_feet
        self.pixels_per_foot = self.frame_width / conveyor_visible_feet
        logger.info(f"Calibration updated: {conveyor_visible_feet}ft → {self.pixels_per_foot:.1f} px/ft")

    def process_frame(self, frame: np.ndarray) -> tuple[float, float]:
        """
        Process one frame and return (fpm_instant, fpm_smoothed).
        """
        now = time.time()
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        # Compute flow if we have a previous frame
        if self._prev_gray is not None and self._prev_points is not None:
            dt = now - self._prev_time
            if dt > 0:
                new_points, status, _ = cv2.calcOpticalFlowPyrLK(
                    self._prev_gray, gray, self._prev_points, None, **_LK_PARAMS
                )
                good_new = new_points[status == 1] if new_points is not None else np.array([])
                good_old = self._prev_points[status == 1]

                if len(good_new) >= 5:
                    # Compute horizontal displacement (conveyor moves horizontally)
                    dx = good_new[:, 0] - good_old[:, 0]
                    # Use median to reject outliers (dust, shadows)
                    median_dx = float(np.median(dx))
                    # Only count forward motion (positive dx for left-to-right)
                    if median_dx > 0:
                        pixels_per_sec = median_dx / dt
                        feet_per_sec = pixels_per_sec / self.pixels_per_foot
                        raw_fpm = feet_per_sec * 60.0
                        # Dead band: ignore readings below noise floor
                        self.fpm_instant = raw_fpm if raw_fpm >= self._dead_band_fpm else 0.0
                    else:
                        self.fpm_instant = 0.0

                    if self.fpm_instant > 0:
                        self._window.append((now, self.fpm_instant))
                    self._prev_points = good_new.reshape(-1, 1, 2)
                else:
                    # Lost track — refresh feature points
                    self._prev_points = None

        # Refresh feature points periodically or on first frame
        if self._prev_points is None or len(self._prev_points) < 20:
            # Look for features in the conveyor zone (center vertical band)
            h, w = gray.shape
            roi = gray[int(h * 0.3):int(h * 0.7), :]
            points = cv2.goodFeaturesToTrack(roi, mask=None, **_FEATURE_PARAMS)
            if points is not None:
                # Adjust Y coordinates back to full frame
                points[:, :, 1] += int(h * 0.3)
                self._prev_points = points
            else:
                self._prev_points = None

        # Smooth over window
        cutoff = now - self._window_seconds
        recent = [v for t, v in self._window if t >= cutoff and v > 0]
        if recent:
            self.fpm_smoothed = float(np.mean(recent))
        elif self.fpm_smoothed > 0:
            # Decay smoothed value when no signal
            self.fpm_smoothed = max(0.0, self.fpm_smoothed * 0.95)

        self._prev_gray = gray
        self._prev_time = now

        return self.fpm_instant, self.fpm_smoothed
