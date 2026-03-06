import asyncpg
from fastapi import Depends
from db.database import get_db_pool
from models.db import SellerDto


class SellerRepository:
    def __init__(self, pool: asyncpg.Pool):
        self._pool = pool

    async def get_seller_by_id(self, seller_id: int) -> SellerDto | None:
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT id, is_verified, created_at FROM sellers WHERE id = $1",
                seller_id,
            )
            return SellerDto(**dict(row)) if row else None

    async def create_seller(
        self, seller_id: int, is_verified: bool = False
    ) -> SellerDto:
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO sellers (id, is_verified)
                VALUES ($1, $2)
                ON CONFLICT (id) DO UPDATE SET is_verified = EXCLUDED.is_verified
                RETURNING id, is_verified, created_at
                """,
                seller_id,
                is_verified,
            )
            return SellerDto(**dict(row))


def get_seller_repository(
    pool: asyncpg.Pool = Depends(get_db_pool),
) -> SellerRepository:
    return SellerRepository(pool)
