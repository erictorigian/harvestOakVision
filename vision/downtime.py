"""
Downtime state machine — belt-speed driven.

The belt runs continuously all day. Downtime = belt stopped, not gaps
between parts at the counting line.

States:
  RUNNING  — belt moving above speed threshold
  IDLE     — belt stopped for longer than DOWNTIME_THRESHOLD_SECONDS
  UNKNOWN  — camera issue / stream drop
"""
from __future__ import annotations

import logging
import os
import time
from dataclasses import dataclass
from typing import Optional

import cv2
import numpy as np

logger = logging.getLogger("harvest_oak.downtime")

STATES = ("RUNNING", "IDLE", "UNKNOWN")

_MIN_BELT_FPM = 3.0  # must match SPEED_DEAD_BAND_FPM


@dataclass
class DowntimeRecord:
    start_time: float
    state: str
    snapshot_path: Optional[str] = None
    end_time: Optional[float] = None
    shift_id: Optional[int] = None

    @property
    def duration_seconds(self) -> int:
        end = self.end_time or time.time()
        return int(end - self.start_time)


class DowntimeTracker:
    def __init__(self, snapshot_dir: str = "/data/snapshots"):
        self.threshold_sec = float(os.environ.get("DOWNTIME_THRESHOLD_SECONDS", "45"))
        self.snapshot_dir = snapshot_dir

        os.makedirs(snapshot_dir, exist_ok=True)

        self.state: str = "UNKNOWN"
        self._last_running_time: float = time.time()
        self._state_start_time: float = time.time()

        self._current_downtime: Optional[DowntimeRecord] = None
        self._completed_events: list[DowntimeRecord] = []

        self.downtime_seconds_today: int = 0
        self._day_start: float = self._today_start()

    @staticmethod
    def _today_start() -> float:
        import datetime
        now = datetime.datetime.now()
        return now.replace(hour=0, minute=0, second=0, microsecond=0).timestamp()

    def update(
        self,
        new_pieces: int,
        motion_level: float,
        frame: Optional[np.ndarray],
        camera_ok: bool,
        belt_speed_fpm: float = 0.0,
    ) -> str:
        """
        Called every frame. Returns current state string.
        Downtime is driven entirely by belt speed — not piece gaps.
        """
        now = time.time()

        if now - self._day_start >= 86400:
            self.downtime_seconds_today = 0
            self._day_start = self._today_start()

        if not camera_ok:
            new_state = "UNKNOWN"
        elif belt_speed_fpm >= _MIN_BELT_FPM:
            self._last_running_time = now
            new_state = "RUNNING"
        else:
            since_running = now - self._last_running_time
            new_state = "IDLE" if since_running >= self.threshold_sec else "RUNNING"

        if new_state != self.state:
            self._on_state_change(self.state, new_state, frame, now)
            self.state = new_state
            self._state_start_time = now

        if self._current_downtime and new_state in ("IDLE", "UNKNOWN"):
            self.downtime_seconds_today = int(
                sum(e.duration_seconds for e in self._completed_events
                    if e.start_time >= self._day_start)
                + (now - self._current_downtime.start_time)
            )

        return self.state

    def _on_state_change(
        self, old_state: str, new_state: str, frame: Optional[np.ndarray], now: float
    ):
        is_downtime = new_state in ("IDLE", "UNKNOWN")
        was_downtime = old_state in ("IDLE", "UNKNOWN")

        if is_downtime and not was_downtime:
            snap_path = self._save_snapshot(frame, new_state, now) if frame is not None else None
            self._current_downtime = DowntimeRecord(
                start_time=now,
                state=new_state,
                snapshot_path=snap_path,
            )
            logger.warning(f"Downtime started: {new_state} (was {old_state})")

        elif was_downtime and self._current_downtime:
            self._current_downtime.end_time = now
            self._completed_events.append(self._current_downtime)
            logger.info(
                f"Downtime ended: {self._current_downtime.state} "
                f"duration={self._current_downtime.duration_seconds}s"
            )
            self._current_downtime = None

        elif is_downtime and was_downtime and self._current_downtime:
            self._current_downtime.end_time = now
            self._completed_events.append(self._current_downtime)
            snap_path = self._save_snapshot(frame, new_state, now) if frame is not None else None
            self._current_downtime = DowntimeRecord(
                start_time=now,
                state=new_state,
                snapshot_path=snap_path,
            )

    def _save_snapshot(self, frame: np.ndarray, state: str, ts: float) -> Optional[str]:
        try:
            import datetime
            dt = datetime.datetime.fromtimestamp(ts)
            filename = f"{dt.strftime('%Y%m%d_%H%M%S')}_{state}.jpg"
            path = os.path.join(self.snapshot_dir, filename)
            cv2.imwrite(path, frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
            logger.info(f"Snapshot saved: {path}")
            return path
        except Exception as e:
            logger.error(f"Snapshot save failed: {e}")
            return None

    def pop_completed_events(self) -> list[DowntimeRecord]:
        events = self._completed_events.copy()
        self._completed_events.clear()
        return events

    @property
    def current_downtime_duration(self) -> int:
        if self._current_downtime and self.state in ("IDLE", "UNKNOWN"):
            return int(time.time() - self._current_downtime.start_time)
        return 0
