"""
WebSocket publisher — vision service → API service.

Sends LiveMetrics JSON every second.
Handles reconnection automatically.
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import time

import websockets

logger = logging.getLogger("harvest_oak.publisher")


class MetricsPublisher:
    def __init__(self):
        self.api_ws_url = os.environ.get("API_WS_URL", "ws://api:8000/ws/vision_ingest")
        self._ws = None
        self._connected = False
        self._reconnect_backoff = 1.0
        self._pending: list[dict] = []

    async def connect(self):
        try:
            self._ws = await websockets.connect(
                self.api_ws_url,
                ping_interval=20,
                ping_timeout=10,
                close_timeout=5,
            )
            self._connected = True
            self._reconnect_backoff = 1.0
            logger.info(f"Connected to API WebSocket: {self.api_ws_url}")
        except Exception as e:
            self._connected = False
            logger.warning(f"WebSocket connect failed ({e}), retry in {self._reconnect_backoff:.1f}s")
            await asyncio.sleep(self._reconnect_backoff)
            self._reconnect_backoff = min(self._reconnect_backoff * 2, 30.0)

    async def publish(self, metrics: dict):
        """Send metrics dict as JSON. Retries once on failure."""
        payload = json.dumps(metrics, default=str)

        if not self._connected or self._ws is None:
            await self.connect()
            if not self._connected:
                return

        try:
            await self._ws.send(payload)
        except Exception as e:
            logger.warning(f"WebSocket send failed: {e} — reconnecting")
            self._connected = False
            self._ws = None
            await self.connect()
            if self._connected and self._ws:
                try:
                    await self._ws.send(payload)
                except Exception:
                    pass

    async def close(self):
        if self._ws:
            await self._ws.close()
        self._connected = False
