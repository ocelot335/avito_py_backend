import logging

import asyncpg
from fastapi import Depends

from db.database import get_db_connection
from models.db import SellerDto, AdDto, AdFeaturesDto

logger = logging.getLogger(__name__)


class AdRepository:

    def __init__(self, connection: asyncpg.Connection):
        self._conn = connection

    async def get_seller_by_id(self, seller_id: int) -> SellerDto | None:
        row = await self._conn.fetchrow(
            """
            SELECT id, is_verified, created_at
            FROM sellers
            WHERE id = $1
            """,
            seller_id,
        )
        if row is None:
            return None
        return SellerDto(**dict(row))

    async def get_ad_by_id(self, item_id: int) -> AdDto | None:
        row = await self._conn.fetchrow(
            """
            SELECT id, seller_id, title, description,
                   category_id, images_qty, created_at
            FROM ads
            WHERE id = $1
            """,
            item_id,
        )
        if row is None:
            return None
        return AdDto(**dict(row))

    async def get_ad_features(self, item_id: int) -> AdFeaturesDto | None:
        row = await self._conn.fetchrow(
            """
            SELECT
                a.id          AS item_id,
                a.seller_id   AS seller_id,
                s.is_verified AS is_verified_seller,
                a.title       AS title,
                a.description AS description,
                a.category_id AS category_id,
                a.images_qty  AS images_qty
            FROM ads a
            JOIN sellers s ON a.seller_id = s.id
            WHERE a.id = $1
            """,
            item_id,
        )
        if row is None:
            return None
        return AdFeaturesDto(**dict(row))

    async def create_seller(
        self, seller_id: int, is_verified: bool = False
    ) -> SellerDto:
        row = await self._conn.fetchrow(
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

    async def create_ad(
        self,
        item_id: int,
        seller_id: int,
        title: str,
        description: str,
        category_id: int,
        images_qty: int,
    ) -> AdDto:
        row = await self._conn.fetchrow(
            """
            INSERT INTO ads (id, seller_id, title, description,
                             category_id, images_qty)
            VALUES ($1, $2, $3, $4, $5, $6)
            ON CONFLICT (id) DO UPDATE SET
                title = EXCLUDED.title,
                description = EXCLUDED.description,
                category_id = EXCLUDED.category_id,
                images_qty = EXCLUDED.images_qty
            RETURNING id, seller_id, title, description,
                      category_id, images_qty, created_at
            """,
            item_id,
            seller_id,
            title,
            description,
            category_id,
            images_qty,
        )
        return AdDto(**dict(row))


async def get_ad_repository(
    connection: asyncpg.Connection = Depends(get_db_connection),
) -> AdRepository:
    return AdRepository(connection)
