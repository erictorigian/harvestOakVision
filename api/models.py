"""
Pydantic models for API request/response
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


# ── Live metrics (pushed by vision service via WebSocket) ──────────────────────

class LiveMetrics(BaseModel):
    timestamp: datetime
    state: str                          # RUNNING | SLOW | IDLE | UNKNOWN
    total_pieces_today: int
    pieces_last_minute: int
    pieces_per_hour_current: int
    line_speed_fpm: float
    line_speed_fpm_smoothed: float
    downtime_seconds_today: int
    current_downtime_duration: int      # seconds in current downtime event (0 if running)
    shift_id: Optional[int] = None
    frame_debug_jpeg_b64: Optional[str] = None  # only set when DEBUG_OVERLAY=true


# ── Shifts ─────────────────────────────────────────────────────────────────────

class ShiftStart(BaseModel):
    label: Optional[str] = None         # e.g. "Day Shift 2026-05-26"


class ShiftResponse(BaseModel):
    id: int
    label: Optional[str]
    start_ts: datetime
    end_ts: Optional[datetime]
    total_pieces: int
    total_downtime_seconds: int
    avg_speed_fpm: Optional[float]
    peak_hour: Optional[int]
    peak_hour_pieces: Optional[int]
    oee_availability: Optional[float]
    created_at: datetime


# ── Metrics ────────────────────────────────────────────────────────────────────

class TodaySummary(BaseModel):
    date: str
    shift_id: Optional[int]
    shift_label: Optional[str]
    total_pieces: int
    pieces_per_hour_avg: float
    peak_hour: Optional[int]
    peak_hour_pieces: int
    total_downtime_seconds: int
    downtime_pct: float
    avg_speed_fpm: float
    oee_availability: float


class HourlyBucket(BaseModel):
    hour: int                           # 0–23
    hour_label: str                     # "6 AM", "2 PM", etc.
    pieces: int
    avg_speed_fpm: float
    downtime_seconds: int
    target: int                         # from TARGET_PIECES_PER_HOUR env var


class DowntimeEvent(BaseModel):
    id: int
    start_ts: datetime
    end_ts: Optional[datetime]
    duration_seconds: Optional[int]
    state: str
    snapshot_path: Optional[str]
    shift_id: Optional[int]


# ── Settings ───────────────────────────────────────────────────────────────────

class SettingsUpdate(BaseModel):
    detection_line_y_percent: Optional[int]     = Field(None, ge=5, le=95)
    min_contour_area: Optional[int]             = Field(None, ge=100)
    count_cooldown_ms: Optional[int]            = Field(None, ge=100, le=5000)
    conveyor_visible_feet: Optional[float]      = Field(None, gt=0.0)
    downtime_threshold_seconds: Optional[int]   = Field(None, ge=5)
    target_pieces_per_hour: Optional[int]       = Field(None, ge=1)
    shift_day_start: Optional[str]              = None  # "HH:MM"
    shift_aft_start: Optional[str]              = None
    shift_night_start: Optional[str]            = None
    debug_overlay: Optional[bool]               = None


class CalibrationInput(BaseModel):
    conveyor_visible_feet: float = Field(..., gt=0.0, description="Visible conveyor span in feet")


# ── Health ─────────────────────────────────────────────────────────────────────

class HealthResponse(BaseModel):
    status: str
    db_connected: bool
    vision_connected: bool
    vision_state: Optional[str]
    uptime_seconds: int
