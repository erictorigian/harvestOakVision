"""
Board detector — dual-threshold brightness at the detection line.

Works on any board color (light or dark paint) against the tan belt:
  - Pixels brighter than BOARD_BRIGHT_THRESHOLD → light board
  - Pixels darker than BOARD_DARK_THRESHOLD → dark board
  - Pixels in between → bare belt surface

Belt ROI env vars (all as % of frame, 0–100):
  BELT_X1_PCT, BELT_X2_PCT, BELT_Y1_PCT, BELT_Y2_PCT
"""
from __future__ import annotations

import logging
import os
import time
from typing import Optional

import cv2
import numpy as np

logger = logging.getLogger("harvest_oak.detector")

# Silver tape exclusion
_SILVER_LOWER = np.array([0,   0,  180])
_SILVER_UPPER = np.array([180, 50, 255])

_STRIP_HALF = 8


class BoardDetector:
    def __init__(self):
        self.line_y_pct           = float(os.environ.get("DETECTION_LINE_Y_PERCENT", "50")) / 100.0
        self.bright_threshold     = int(os.environ.get("BOARD_BRIGHT_THRESHOLD", "170"))
        self.dark_threshold       = int(os.environ.get("BOARD_DARK_THRESHOLD", "60"))
        self.min_board_width_pct  = float(os.environ.get("MIN_BOARD_WIDTH_PERCENT", "5")) / 100.0
        self.cooldown_ms          = int(os.environ.get("COUNT_COOLDOWN_MS", "400"))

        self._roi_x1_pct = float(os.environ.get("BELT_X1_PCT", "0"))   / 100.0
        self._roi_x2_pct = float(os.environ.get("BELT_X2_PCT", "100")) / 100.0
        self._roi_y1_pct = float(os.environ.get("BELT_Y1_PCT", "0"))   / 100.0
        self._roi_y2_pct = float(os.environ.get("BELT_Y2_PCT", "100")) / 100.0

        self._frame_h: int = 0
        self._frame_w: int = 0
        self._detection_y: int = 0
        self._min_board_px: int = 0
        self._roi_x1: int = 0
        self._roi_x2: int = 0

        self._board_over_line: bool = False
        self._last_count_ms: float = 0.0
        self.total_pieces: int = 0

        self._prev_gray: Optional[np.ndarray] = None

    def _setup(self, h: int, w: int):
        if self._frame_h != h or self._frame_w != w:
            self._frame_h = h
            self._frame_w = w
            self._detection_y = int(h * self.line_y_pct)
            self._roi_x1 = int(self._roi_x1_pct * w)
            self._roi_x2 = int(self._roi_x2_pct * w)
            roi_w = max(1, self._roi_x2 - self._roi_x1)
            self._min_board_px = int(roi_w * self.min_board_width_pct)
            logger.info(
                f"Frame {w}x{h} — detection line Y={self._detection_y}, "
                f"belt ROI X=[{self._roi_x1},{self._roi_x2}], "
                f"min board width={self._min_board_px}px, "
                f"thresholds bright>{self.bright_threshold} dark<{self.dark_threshold}"
            )

    def _board_pixels_at_line(self, frame: np.ndarray) -> tuple[int, int]:
        """
        Return (board_pixel_count, peak_brightness) at the detection line.

        A pixel is "board" if it is brighter than bright_threshold (light-painted
        board) OR darker than dark_threshold (dark-painted board). The middle range
        is the bare tan belt and is not counted.
        """
        h, w = frame.shape[:2]
        y0 = max(0, self._detection_y - _STRIP_HALF)
        y1 = min(h, self._detection_y + _STRIP_HALF)
        strip = frame[y0:y1]

        gray = cv2.cvtColor(strip, cv2.COLOR_BGR2GRAY)
        hsv  = cv2.cvtColor(strip, cv2.COLOR_BGR2HSV)

        # Light boards (brighter than belt)
        _, bright = cv2.threshold(gray, self.bright_threshold, 255, cv2.THRESH_BINARY)
        # Dark boards (darker than belt)
        _, dark   = cv2.threshold(gray, self.dark_threshold,   255, cv2.THRESH_BINARY_INV)
        # Silver tape exclusion
        silver = cv2.inRange(hsv, _SILVER_LOWER, _SILVER_UPPER)

        board_mask = cv2.bitwise_or(bright, dark)
        board_mask = cv2.bitwise_and(board_mask, cv2.bitwise_not(silver))

        line_1d = np.max(board_mask, axis=0)
        if self._roi_x1 > 0:
            line_1d[:self._roi_x1] = 0
        if self._roi_x2 < w:
            line_1d[self._roi_x2:] = 0

        roi_gray = gray[:, self._roi_x1:self._roi_x2]
        peak = int(np.max(roi_gray)) if roi_gray.size > 0 else 0

        return int(np.count_nonzero(line_1d)), peak

    def process_frame(
        self, frame: np.ndarray, debug: bool = False
    ) -> tuple[int, list[dict], Optional[np.ndarray]]:
        h, w = frame.shape[:2]
        self._setup(h, w)

        now_ms = time.time() * 1000
        board_px, peak = self._board_pixels_at_line(frame)
        board_now = board_px >= self._min_board_px

        new_pieces = 0
        events: list[dict] = []

        if board_now and not self._board_over_line:
            if (now_ms - self._last_count_ms) >= self.cooldown_ms:
                self.total_pieces += 1
                new_pieces += 1
                self._last_count_ms = now_ms
                events.append({
                    "direction": "bottom_to_top",
                    "confidence": min(1.0, board_px / max(1, self._roi_x2 - self._roi_x1)),
                    "x": w // 2,
                    "y": self._detection_y,
                })
                logger.debug(f"Board #{self.total_pieces} — {board_px}px, peak={peak}")

        self._board_over_line = board_now

        debug_frame: Optional[np.ndarray] = None
        if debug:
            debug_frame = frame.copy()

            ry1 = int(self._roi_y1_pct * h)
            ry2 = int(self._roi_y2_pct * h)
            cv2.rectangle(debug_frame, (self._roi_x1, ry1), (self._roi_x2, ry2), (255, 255, 0), 1)

            line_color = (0, 255, 0) if board_now else (0, 255, 255)
            cv2.line(debug_frame,
                     (self._roi_x1, self._detection_y),
                     (self._roi_x2, self._detection_y),
                     line_color, 2)
            cv2.line(debug_frame, (0, self._detection_y), (self._roi_x1, self._detection_y), (60, 60, 60), 1)
            cv2.line(debug_frame, (self._roi_x2, self._detection_y), (w, self._detection_y), (60, 60, 60), 1)

            if board_now:
                label = f"BOARD {board_px}px/{self._min_board_px}px  peak={peak}"
            else:
                label = f"LINE  {board_px}px/{self._min_board_px}px  peak={peak}  >{self.bright_threshold}/<{self.dark_threshold}"
            cv2.putText(debug_frame, label,
                        (self._roi_x1 + 4, self._detection_y - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.45, line_color, 1)

            cv2.putText(debug_frame, f"Total: {self.total_pieces}", (10, 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 0), 2)

            if new_pieces:
                cv2.putText(debug_frame, f"COUNT! #{self.total_pieces}",
                            (w // 2 - 80, self._detection_y - 22),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 0, 255), 2)

        return new_pieces, events, debug_frame

    def motion_level(self, fg_mask: Optional[np.ndarray] = None) -> float:
        if fg_mask is None:
            return 0.0
        total = fg_mask.shape[0] * fg_mask.shape[1]
        return cv2.countNonZero(fg_mask) / total if total > 0 else 0.0

    def get_fg_mask(self, frame: np.ndarray) -> np.ndarray:
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        if self._prev_gray is not None and self._prev_gray.shape == gray.shape:
            diff = cv2.absdiff(gray, self._prev_gray)
            _, mask = cv2.threshold(diff, 20, 255, cv2.THRESH_BINARY)
        else:
            mask = np.zeros_like(gray)
        self._prev_gray = gray
        return mask
