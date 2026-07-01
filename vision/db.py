"""
Direct database writes from vision service.
Uses a separate asyncpg pool from the API service.
"""
from __future__ import annotations

import asyncio
import logging
import os
from datetime import datetime, timezone
from typing import Optional

import asyncpg

logger = logging.getLogger("harvest_oak.vision_db")

_pool: Optional[asyncpg.Pool] = None


async def init_pool():
    global _pool
    db_url = os.environ["DB_URL"]
    _pool = await asyncpg.create_pool(
        dsn=db_url,
        min_size=1,
        max_size=5,
        command_timeout=10,
        server_settings={"application_name": "harvest_oak_vision"},
    )
    logger.info("Vision DB pool initialized")


async def close_pool():
    global _pool
    if _pool:
        await _pool.close()
        _pool = None


async def insert_piece_event(
    direction: str,
    confidence: float,
    line_speed_fpm: float,
    shift_id: Optional[int],
    camera_id: str = "cam_01",
):
    if not _pool:
        return
    try:
        async with _pool.acquire() as conn:
            await conn.execute(
                """INSERT INTO piece_events (timestamp, camera_id, direction, confidence, line_speed_fpm, shift_id)
                   VALUES (NOW(), $1, $2, $3, $4, $5)""",
                camera_id, direction, confidence, line_speed_fpm, shift_id,
            )
    except Exception as e:
        logger.error(f"piece_event insert failed: {e}")


async def insert_downtime_event(
    start_ts: datetime,
    end_ts: datetime,
    duration_seconds: int,
    state: str,
    snapshot_path: Optional[str],
    shift_id: Optional[int],
):
    if not _pool:
        return
    try:
        async with _pool.acquire() as conn:
            await conn.execute(
                """INSERT INTO downtime_events
                   (start_ts, end_ts, duration_seconds, state, snapshot_path, shift_id)
                   VALUES ($1, $2, $3, $4, $5, $6)""",
                start_ts, end_ts, duration_seconds, state, snapshot_path, shift_id,
            )
    except Exception as e:
        logger.error(f"downtime_event insert failed: {e}")


async def upsert_production_metric(
    pieces_count: int,
    avg_speed_fpm: float,
    downtime_seconds: int,
    state: str,
    shift_id: Optional[int],
):
    """Insert a 1-minute rollup metric."""
    if not _pool:
        return
    try:
        async with _pool.acquire() as conn:
            await conn.execute(
                """INSERT INTO production_metrics
                   (timestamp, pieces_count, avg_speed_fpm, downtime_seconds, state, shift_id)
                   VALUES (date_trunc('minute', NOW()), $1, $2, $3, $4, $5)
                   ON CONFLICT DO NOTHING""",
                pieces_count, avg_speed_fpm, downtime_seconds, state, shift_id,
            )
    except Exception as e:
        logger.error(f"production_metric insert failed: {e}")


async def get_active_shift_id() -> Optional[int]:
    if not _pool:
        return None
    try:
        async with _pool.acquire() as conn:
            return await conn.fetchval(
                "SELECT id FROM shifts WHERE end_ts IS NULL ORDER BY start_ts DESC LIMIT 1"
            )
    except Exception as e:
        logger.error(f"get_active_shift_id failed: {e}")
        return None


async def get_today_piece_count() -> int:
    if not _pool:
        return 0
    try:
        from datetime import date
        today = date.today()
        day_start = datetime(today.year, today.month, today.day, tzinfo=timezone.utc)
        async with _pool.acquire() as conn:
            count = await conn.fetchval(
                "SELECT COUNT(*) FROM piece_events WHERE timestamp >= $1", day_start
            )
            return count or 0
    except Exception as e:
        logger.error(f"get_today_piece_count failed: {e}")
        return 0


async def get_today_downtime_seconds() -> int:
    if not _pool:
        return 0
    try:
        from datetime import date
        today = date.today()
        day_start = datetime(today.year, today.month, today.day, tzinfo=timezone.utc)
        async with _pool.acquire() as conn:
            secs = await conn.fetchval(
                """SELECT COALESCE(SUM(duration_seconds), 0)
                   FROM downtime_events
                   WHERE start_ts >= $1 AND end_ts IS NOT NULL""",
                day_start,
            )
            return secs or 0
    except Exception as e:
        logger.error(f"get_today_downtime failed: {e}")
        return 0
