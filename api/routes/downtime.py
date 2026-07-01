"""
Downtime event routes
"""
from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, Query
from asyncpg import Pool

from api.db import get_pool
from api.models import DowntimeEvent

router = APIRouter(prefix="/api/downtime", tags=["downtime"])


@router.get("", response_model=list[DowntimeEvent])
async def get_downtime(
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
        rows = await conn.fetch(
            """SELECT * FROM downtime_events
               WHERE start_ts >= $1 AND start_ts <= $2
               ORDER BY start_ts DESC""",
            day_start, day_end,
        )
    return [DowntimeEvent(**dict(r)) for r in rows]
