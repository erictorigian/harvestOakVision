"""
Board detector — deviation-from-belt-baseline at the detection line.

Learns the belt's appearance at the tripwire (rolling EMA), then detects
any object that deviates from that baseline. Works for any board color
(white, dark, tan, or anything else) without knowing brightness in advance.

Key env vars:
  LINE_DEVIATION_THRESHOLD  — pixel deviation from belt baseline to count as board (default 25)
  MIN_BOARD_WIDTH_PERCENT   — % of belt ROI width a board must span to count (default 2)
  COUNT_COOLDOWN_MS         — ms between counts (default 800)
  DETECTION_LINE_Y_PERCENT  — vertical position of tripwire 0-100 (default 50)
  BELT_X1_PCT / BELT_X2_PCT — horizontal ROI limits (default 0 / 100)
"""
from __future__ import annotations

import logging
import os
import time
from typing import Optional

import cv2
import numpy as np

logger = logging.getLogger("harvest_oak.detector")

# Silver tape exclusion (HSV: near-white, low saturation, high value)
_SILVER_LOWER = np.array([0,   0,  180])
_SILVER_UPPER = np.array([180, 50, 255])

_STRIP_HALF = 8          # half-height of the detection strip in pixels
_BG_ALPHA   = 0.02       # EMA speed — how fast baseline tracks belt changes


class BoardDetector:
    def __init__(self):
        self.line_y_pct          = float(os.environ.get("DETECTION_LINE_Y_PERCENT", "50")) / 100.0
        self.deviation_threshold = int(os.environ.get("LINE_DEVIATION_THRESHOLD", "25"))
        self.min_board_width_pct = float(os.environ.get("MIN_BOARD_WIDTH_PERCENT", "2")) / 100.0
        self.cooldown_ms         = int(os.environ.get("COUNT_COOLDOWN_MS", "800"))

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

        # Belt baseline — learned from frames with no board present
        self._strip_bg: Optional[np.ndarray] = None

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
            self._min_board_px = max(1, int(roi_w * self.min_board_width_pct))
            self._strip_bg = None  # reset baseline on frame size change
            logger.info(
                f"Frame {w}x{h} — line Y={self._detection_y}, "
                f"ROI X=[{self._roi_x1},{self._roi_x2}], "
                f"min board={self._min_board_px}px, "
                f"deviation threshold={self.deviation_threshold}"
            )

    def _board_pixels_at_line(self, frame: np.ndarray) -> tuple[int, int]:
        """
        Return (board_column_count, peak_deviation) at the detection strip.

        board_column_count: how many ROI columns deviate from belt baseline
        peak_deviation:     max per-column brightness deviation — use this to
                            tune LINE_DEVIATION_THRESHOLD (set it to ~half of
                            what you see here when a board is at the line)
        """
        h, w = frame.shape[:2]
        y0 = max(0, self._detection_y - _STRIP_HALF)
        y1 = min(h, self._detection_y + _STRIP_HALF)
        strip = frame[y0:y1]

        gray = cv2.cvtColor(strip, cv2.COLOR_BGR2GRAY)
        hsv  = cv2.cvtColor(strip, cv2.COLOR_BGR2HSV)

        # Per-column mean brightness within ROI
        roi_gray = gray[:, self._roi_x1:self._roi_x2]
        if roi_gray.size == 0:
            return 0, 0
        col_means = np.mean(roi_gray, axis=0).astype(np.float32)

        # Initialize baseline on first frame
        if self._strip_bg is None or self._strip_bg.shape != col_means.shape:
            self._strip_bg = col_means.copy()
            return 0, 0

        deviation = np.abs(col_means - self._strip_bg)

        # Zero out silver tape columns so tape marks don't trigger counts
        silver = cv2.inRange(hsv, _SILVER_LOWER, _SILVER_UPPER)
        silver_cols = np.max(silver, axis=0)[self._roi_x1:self._roi_x2].astype(bool)
        deviation[silver_cols] = 0

        board_cols = int(np.count_nonzero(deviation > self.deviation_threshold))
        peak_dev   = int(np.max(deviation)) if deviation.size > 0 else 0

        # Update baseline only when no board is present (avoid learning boards as belt)
        if board_cols < self._min_board_px:
            self._strip_bg = (1.0 - _BG_ALPHA) * self._strip_bg + _BG_ALPHA * col_means

        return board_cols, peak_dev

    def process_frame(
        self, frame: np.ndarray, debug: bool = False
    ) -> tuple[int, list[dict], Optional[np.ndarray]]:
        h, w = frame.shape[:2]
        self._setup(h, w)

        now_ms = time.time() * 1000
        board_px, peak_dev = self._board_pixels_at_line(frame)
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
                logger.debug(f"Board #{self.total_pieces} — {board_px}cols, dev={peak_dev}")

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
                label = f"BOARD {board_px}cols/{self._min_board_px}cols  dev={peak_dev}"
            else:
                label = f"LINE  {board_px}cols/{self._min_board_px}cols  dev={peak_dev}  thr={self.deviation_threshold}"
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
