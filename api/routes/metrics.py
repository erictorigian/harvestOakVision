"""
Metrics routes — live state, today summary, hourly breakdown, piece events
"""
from __future__ import annotations

import os
from datetime import date, datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, Query
from asyncpg import Pool

from api.db import get_pool
from api.models import TodaySummary, HourlyBucket

router = APIRouter(prefix="/api/metrics", tags=["metrics"])

TARGET_PPH = int(os.environ.get("TARGET_PIECES_PER_HOUR", "450"))


@router.get("/today", response_model=TodaySummary)
async def get_today(pool: Pool = Depends(get_pool)):
    today = date.today()
    day_start = datetime(today.year, today.month, today.day, tzinfo=timezone.utc)

    async with pool.acquire() as conn:
        # Total pieces today
        pieces = await conn.fetchval(
            "SELECT COUNT(*) FROM piece_events WHERE timestamp >= $1", day_start
        ) or 0

        # Downtime today
        downtime = await conn.fetchval(
            """SELECT COALESCE(SUM(duration_seconds), 0)
               FROM downtime_events
               WHERE start_ts >= $1 AND end_ts IS NOT NULL""",
            day_start,
        ) or 0

        # Avg speed today
        avg_speed = await conn.fetchval(
            """SELECT COALESCE(AVG(avg_speed_fpm), 0.0)
               FROM production_metrics WHERE timestamp >= $1""",
            day_start,
        ) or 0.0

        # Pieces per hour by hour
        hourly = await conn.fetch(
            """SELECT date_part('hour', timestamp) AS hr, COUNT(*) AS cnt
               FROM piece_events
               WHERE timestamp >= $1
               GROUP BY hr ORDER BY hr""",
            day_start,
        )

        peak_hour = None
        peak_pieces = 0
        if hourly:
            peak_row = max(hourly, key=lambda r: r["cnt"])
            peak_hour = int(peak_row["hr"])
            peak_pieces = int(peak_row["cnt"])

        hours_elapsed = max(
            (datetime.now(timezone.utc) - day_start).total_seconds() / 3600, 1
        )
        pph_avg = round(pieces / hours_elapsed, 1)

        planned_seconds = hours_elapsed * 3600
        uptime_seconds = planned_seconds - downtime
        oee = round(uptime_seconds / planned_seconds, 4) if planned_seconds > 0 else 0.0
        downtime_pct = round(downtime / planned_seconds * 100, 2) if planned_seconds > 0 else 0.0

        # Active shift
        shift = await conn.fetchrow(
            "SELECT id, label FROM shifts WHERE end_ts IS NULL ORDER BY start_ts DESC LIMIT 1"
        )

    return TodaySummary(
        date=today.isoformat(),
        shift_id=shift["id"] if shift else None,
        shift_label=shift["label"] if shift else None,
        total_pieces=pieces,
        pieces_per_hour_avg=pph_avg,
        peak_hour=peak_hour,
        peak_hour_pieces=peak_pieces,
        total_downtime_seconds=downtime,
        downtime_pct=downtime_pct,
        avg_speed_fpm=round(float(avg_speed), 2),
        oee_availability=oee,
    )


@router.get("/hourly", response_model=list[HourlyBucket])
async def get_hourly(
    date_str: Optional[str] = Query(None, alias="date", description="YYYY-MM-DD, defaults to today"),
    pool: Pool = Depends(get_pool),
):
    if date_str:
        d = date.fromisoformat(date_str)
    else:
        d = date.today()

    day_start = datetime(d.year, d.month, d.day, tzinfo=timezone.utc)
    day_end = datetime(d.year, d.month, d.day, 23, 59, 59, tzinfo=timezone.utc)

    async with pool.acquire() as conn:
        pieces_by_hour = await conn.fetch(
            """SELECT date_part('hour', timestamp)::int AS hr, COUNT(*) AS cnt
               FROM piece_events
               WHERE timestamp >= $1 AND timestamp <= $2
               GROUP BY hr""",
            day_start, day_end,
        )
        speed_by_hour = await conn.fetch(
            """SELECT date_part('hour', timestamp)::int AS hr,
                      COALESCE(AVG(avg_speed_fpm), 0.0) AS avg_spd
               FROM production_metrics
               WHERE timestamp >= $1 AND timestamp <= $2
               GROUP BY hr""",
            day_start, day_end,
        )
        downtime_by_hour = await conn.fetch(
            """SELECT date_part('hour', start_ts)::int AS hr,
                      COALESCE(SUM(duration_seconds), 0) AS dt
               FROM downtime_events
               WHERE start_ts >= $1 AND start_ts <= $2 AND end_ts IS NOT NULL
               GROUP BY hr""",
            day_start, day_end,
        )

    pieces_map = {r["hr"]: int(r["cnt"]) for r in pieces_by_hour}
    speed_map = {r["hr"]: float(r["avg_spd"]) for r in speed_by_hour}
    downtime_map = {r["hr"]: int(r["dt"]) for r in downtime_by_hour}

    _HOUR_LABELS = [
        "12 AM","1 AM","2 AM","3 AM","4 AM","5 AM","6 AM","7 AM",
        "8 AM","9 AM","10 AM","11 AM","12 PM","1 PM","2 PM","3 PM",
        "4 PM","5 PM","6 PM","7 PM","8 PM","9 PM","10 PM","11 PM",
    ]

    buckets = []
    for hr in range(24):
        if hr in pieces_map or hr in speed_map:
            buckets.append(HourlyBucket(
                hour=hr,
                hour_label=_HOUR_LABELS[hr],
                pieces=pieces_map.get(hr, 0),
                avg_speed_fpm=round(speed_map.get(hr, 0.0), 2),
                downtime_seconds=downtime_map.get(hr, 0),
                target=TARGET_PPH,
            ))

    return buckets


@router.get("/pieces")
async def get_pieces(
    start: datetime = Query(...),
    end: datetime = Query(...),
    pool: Pool = Depends(get_pool),
):
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """SELECT timestamp, camera_id, direction, confidence, line_speed_fpm
               FROM piece_events
               WHERE timestamp >= $1 AND timestamp <= $2
               ORDER BY timestamp DESC
               LIMIT 5000""",
            start, end,
        )
    return [dict(r) for r in rows]
