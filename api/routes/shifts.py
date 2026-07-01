"""
Shift management routes
"""
from __future__ import annotations

import os
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from asyncpg import Pool

from api.db import get_pool
from api.models import ShiftStart, ShiftResponse

router = APIRouter(prefix="/api/shifts", tags=["shifts"])


def _label_for_now() -> str:
    now = datetime.now(timezone.utc)
    hour = now.hour
    if 6 <= hour < 14:
        slot = "Day"
    elif 14 <= hour < 22:
        slot = "Afternoon"
    else:
        slot = "Night"
    return f"{slot} Shift — {now.strftime('%B %-d, %Y')}"


@router.get("", response_model=list[ShiftResponse])
async def list_shifts(pool: Pool = Depends(get_pool)):
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT * FROM shifts ORDER BY start_ts DESC LIMIT 100"
        )
    return [ShiftResponse(**dict(r)) for r in rows]


@router.post("/start", response_model=ShiftResponse)
async def start_shift(body: ShiftStart, pool: Pool = Depends(get_pool)):
    async with pool.acquire() as conn:
        # Close any open shift first
        await conn.execute(
            "UPDATE shifts SET end_ts = NOW() WHERE end_ts IS NULL"
        )
        label = body.label or _label_for_now()
        row = await conn.fetchrow(
            """INSERT INTO shifts (label, start_ts)
               VALUES ($1, NOW())
               RETURNING *""",
            label,
        )
    return ShiftResponse(**dict(row))


@router.post("/end", response_model=ShiftResponse)
async def end_shift(pool: Pool = Depends(get_pool)):
    async with pool.acquire() as conn:
        shift = await conn.fetchrow(
            "SELECT * FROM shifts WHERE end_ts IS NULL ORDER BY start_ts DESC LIMIT 1"
        )
        if not shift:
            raise HTTPException(status_code=404, detail="No active shift found")

        shift_id = shift["id"]
        start_ts = shift["start_ts"]

        # Compute totals
        total_pieces = await conn.fetchval(
            "SELECT COUNT(*) FROM piece_events WHERE shift_id = $1", shift_id
        ) or 0

        total_downtime = await conn.fetchval(
            """SELECT COALESCE(SUM(duration_seconds), 0)
               FROM downtime_events WHERE shift_id = $1 AND end_ts IS NOT NULL""",
            shift_id,
        ) or 0

        avg_speed = await conn.fetchval(
            """SELECT COALESCE(AVG(avg_speed_fpm), 0.0)
               FROM production_metrics WHERE shift_id = $1""",
            shift_id,
        ) or 0.0

        # Peak hour
        peak_row = await conn.fetchrow(
            """SELECT date_part('hour', timestamp)::int AS hr, COUNT(*) AS cnt
               FROM piece_events WHERE shift_id = $1
               GROUP BY hr ORDER BY cnt DESC LIMIT 1""",
            shift_id,
        )
        peak_hour = int(peak_row["hr"]) if peak_row else None
        peak_pieces = int(peak_row["cnt"]) if peak_row else 0

        # OEE availability
        now = datetime.now(timezone.utc)
        planned_seconds = (now - start_ts).total_seconds()
        oee = round((planned_seconds - total_downtime) / planned_seconds, 4) if planned_seconds > 0 else 0.0

        row = await conn.fetchrow(
            """UPDATE shifts SET
                end_ts = NOW(),
                total_pieces = $2,
                total_downtime_seconds = $3,
                avg_speed_fpm = $4,
                peak_hour = $5,
                peak_hour_pieces = $6,
                oee_availability = $7
               WHERE id = $1
               RETURNING *""",
            shift_id, total_pieces, total_downtime, float(avg_speed),
            peak_hour, peak_pieces, oee,
        )
    return ShiftResponse(**dict(row))


@router.get("/{shift_id}", response_model=ShiftResponse)
async def get_shift(shift_id: int, pool: Pool = Depends(get_pool)):
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT * FROM shifts WHERE id = $1", shift_id)
    if not row:
        raise HTTPException(status_code=404, detail="Shift not found")
    return ShiftResponse(**dict(row))
