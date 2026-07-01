"""
Settings routes — read/write runtime configuration
"""
from __future__ import annotations

from fastapi import APIRouter, Depends
from asyncpg import Pool

from api.db import get_pool
from api.models import SettingsUpdate, CalibrationInput

router = APIRouter(prefix="/api", tags=["settings"])


@router.get("/settings")
async def get_settings(pool: Pool = Depends(get_pool)):
    async with pool.acquire() as conn:
        rows = await conn.fetch("SELECT key, value FROM settings ORDER BY key")
    return {r["key"]: r["value"] for r in rows}


@router.post("/settings")
async def update_settings(body: SettingsUpdate, pool: Pool = Depends(get_pool)):
    updates = body.model_dump(exclude_none=True)
    if not updates:
        return {"updated": 0}

    async with pool.acquire() as conn:
        for key, value in updates.items():
            await conn.execute(
                """INSERT INTO settings (key, value, updated_at)
                   VALUES ($1, $2, NOW())
                   ON CONFLICT (key) DO UPDATE SET value = $2, updated_at = NOW()""",
                key, str(value).lower() if isinstance(value, bool) else str(value),
            )
    return {"updated": len(updates)}


@router.post("/calibrate")
async def calibrate(body: CalibrationInput, pool: Pool = Depends(get_pool)):
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """INSERT INTO calibration (conveyor_visible_feet)
               VALUES ($1) RETURNING id, set_at""",
            body.conveyor_visible_feet,
        )
        # Update settings table too
        await conn.execute(
            """INSERT INTO settings (key, value, updated_at) VALUES ('conveyor_visible_feet', $1, NOW())
               ON CONFLICT (key) DO UPDATE SET value = $1, updated_at = NOW()""",
            str(body.conveyor_visible_feet),
        )
    return {"calibration_id": row["id"], "set_at": row["set_at"], "conveyor_visible_feet": body.conveyor_visible_feet}
