"""
Harvest Oak Vision Engine — API Service
FastAPI + asyncpg + TimescaleDB
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import time
from contextlib import asynccontextmanager
from typing import Optional

import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from api.db import init_pool, close_pool, get_pool
from api.models import LiveMetrics, HealthResponse
from api.routes import metrics, shifts, downtime, settings

# ── Logging ────────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format='{"time":"%(asctime)s","level":"%(levelname)s","logger":"%(name)s","msg":"%(message)s"}',
)
logger = logging.getLogger("harvest_oak.api")

# ── State ──────────────────────────────────────────────────────────────────────
_start_time = time.time()
_live_metrics: Optional[LiveMetrics] = None
_dashboard_clients: set[WebSocket] = set()


# ── Lifespan ───────────────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_pool()
    logger.info("API service started")
    yield
    await close_pool()
    logger.info("API service stopped")


# ── App ────────────────────────────────────────────────────────────────────────
app = FastAPI(
    title="Harvest Oak Vision Engine",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(metrics.router)
app.include_router(shifts.router)
app.include_router(downtime.router)
app.include_router(settings.router)


# ── Health ─────────────────────────────────────────────────────────────────────
@app.get("/api/health", response_model=HealthResponse, tags=["health"])
async def health():
    pool = await get_pool()
    db_ok = False
    try:
        async with pool.acquire() as conn:
            await conn.fetchval("SELECT 1")
        db_ok = True
    except Exception:
        pass

    return HealthResponse(
        status="ok" if db_ok else "degraded",
        db_connected=db_ok,
        vision_connected=_live_metrics is not None,
        vision_state=_live_metrics.state if _live_metrics else None,
        uptime_seconds=int(time.time() - _start_time),
    )


# ── Live metrics snapshot ──────────────────────────────────────────────────────
@app.get("/api/metrics/live", tags=["metrics"])
async def get_live():
    if _live_metrics is None:
        return {"state": "UNKNOWN", "message": "Vision service not connected"}
    return _live_metrics.model_dump()


# ── WebSocket: vision service → API (ingest) ───────────────────────────────────
@app.websocket("/ws/vision_ingest")
async def vision_ingest(ws: WebSocket):
    """Vision service connects here and pushes LiveMetrics JSON every second."""
    global _live_metrics
    await ws.accept()
    logger.info("Vision service connected via WebSocket")
    try:
        while True:
            raw = await ws.receive_text()
            data = json.loads(raw)
            _live_metrics = LiveMetrics(**data)

            # Fan out to all connected dashboard clients
            dead = set()
            for client in _dashboard_clients:
                try:
                    await client.send_text(raw)
                except Exception:
                    dead.add(client)
            _dashboard_clients.difference_update(dead)

    except WebSocketDisconnect:
        logger.warning("Vision service disconnected")
        _live_metrics = None
    except Exception as e:
        logger.error(f"Vision ingest error: {e}")
        _live_metrics = None


# ── WebSocket: dashboard clients ───────────────────────────────────────────────
@app.websocket("/ws/live")
async def live_feed(ws: WebSocket):
    """Dashboard browsers connect here to receive live metrics."""
    await ws.accept()
    _dashboard_clients.add(ws)
    logger.info(f"Dashboard client connected. Total: {len(_dashboard_clients)}")

    # Send current state immediately on connect
    if _live_metrics:
        await ws.send_text(_live_metrics.model_dump_json())

    try:
        # Keep connection alive; client sends pings
        while True:
            await asyncio.sleep(30)
            await ws.send_text('{"type":"ping"}')
    except WebSocketDisconnect:
        pass
    except Exception:
        pass
    finally:
        _dashboard_clients.discard(ws)
        logger.info(f"Dashboard client disconnected. Total: {len(_dashboard_clients)}")


# ── Phase 2 stubs ─────────────────────────────────────────────────────────────

# PHASE 2: n8n webhook forwarding
# @app.post("/api/webhooks/n8n")
# async def n8n_forward(payload: dict): ...

# PHASE 2: Defect event ingestion (second QC camera)
# @app.post("/api/defects")
# async def ingest_defect(event: DefectEvent): ...

# PHASE 2: Supabase cloud sync endpoint
# @app.post("/api/sync/supabase")
# async def sync_to_supabase(): ...


if __name__ == "__main__":
    uvicorn.run(
        "api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
        log_config=None,
    )
