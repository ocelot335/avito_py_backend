import asyncpg
from fastapi import Depends
from db.database import get_db_pool
from models.db import AdDto, AdFeaturesDto


class AdRepository:
    def __init__(self, pool: asyncpg.Pool):
        self._pool = pool

    async def get_ad_by_id(self, item_id: int) -> AdDto | None:
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT id, seller_id, title, description, category_id, images_qty, is_closed, created_at
                FROM ads WHERE id = $1
                """,
                item_id,
            )
            return AdDto(**dict(row)) if row else None

    async def get_ad_features(self, item_id: int) -> AdFeaturesDto | None:
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT a.id AS item_id, a.seller_id AS seller_id,
                       s.is_verified AS is_verified_seller, a.title AS title,
                       a.description AS description, a.category_id AS category_id,
                       a.images_qty AS images_qty
                FROM ads a
                JOIN sellers s ON a.seller_id = s.id
                WHERE a.id = $1 AND a.is_closed = FALSE
                """,
                item_id,
            )
            return AdFeaturesDto(**dict(row)) if row else None

    async def create_ad(
        self,
        item_id: int,
        seller_id: int,
        title: str,
        description: str,
        category_id: int,
        images_qty: int,
    ) -> AdDto:
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO ads (id, seller_id, title, description, category_id, images_qty)
                VALUES ($1, $2, $3, $4, $5, $6)
                ON CONFLICT (id) DO UPDATE SET
                    title = EXCLUDED.title, description = EXCLUDED.description,
                    category_id = EXCLUDED.category_id, images_qty = EXCLUDED.images_qty
                RETURNING id, seller_id, title, description, category_id, images_qty, is_closed, created_at
                """,
                item_id,
                seller_id,
                title,
                description,
                category_id,
                images_qty,
            )
            return AdDto(**dict(row))

    async def close_ad(self, item_id: int) -> None:
        async with self._pool.acquire() as conn:
            await conn.execute(
                "UPDATE ads SET is_closed = TRUE WHERE id = $1", item_id
            )


def get_ad_repository(
    pool: asyncpg.Pool = Depends(get_db_pool),
) -> AdRepository:
    return AdRepository(pool)
