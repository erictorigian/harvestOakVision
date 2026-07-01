"""
Database connection pool — asyncpg + TimescaleDB
"""
import asyncpg
import logging
import os

logger = logging.getLogger(__name__)

_pool: asyncpg.Pool | None = None


async def get_pool() -> asyncpg.Pool:
    global _pool
    if _pool is None:
        raise RuntimeError("DB pool not initialized. Call init_pool() first.")
    return _pool


async def init_pool() -> asyncpg.Pool:
    global _pool
    db_url = os.environ["DB_URL"]
    _pool = await asyncpg.create_pool(
        dsn=db_url,
        min_size=2,
        max_size=10,
        command_timeout=30,
        server_settings={"application_name": "harvest_oak_api"},
    )
    logger.info("DB pool initialized")
    return _pool


async def close_pool():
    global _pool
    if _pool:
        await _pool.close()
        _pool = None
        logger.info("DB pool closed")
