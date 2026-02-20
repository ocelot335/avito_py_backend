import logging
from typing import AsyncGenerator
import asyncpg
from fastapi import Request

from config.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


async def create_pool() -> asyncpg.Pool:
    pool = await asyncpg.create_pool(
        dsn=settings.database_url,
        min_size=1,
        max_size=10,
    )
    return pool


async def close_pool(pool: asyncpg.Pool | None):
    if pool is not None:
        await pool.close()
        logger.info("пул соединений с бд закрыт")


async def get_db_connection(
    request: Request,
) -> AsyncGenerator[asyncpg.Connection, None]:
    pool: asyncpg.Pool = request.app.state.db_pool
    if pool is None:
        raise RuntimeError("пул соединений с бд не найден в app.state")

    async with pool.acquire() as connection:
        yield connection
