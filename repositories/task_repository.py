import asyncpg
from fastapi import Depends
from db.database import get_db_pool
from models.db import ModerationTaskDto


class ModerationTaskRepository:
    def __init__(self, pool: asyncpg.Pool):
        self._pool = pool

    async def create_moderation_task(self, item_id: int) -> int:
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                "INSERT INTO moderation_results (item_id, status) VALUES ($1, 'pending') RETURNING id",
                item_id,
            )
            return row["id"]

    async def update_moderation_task_status(
        self, task_id: int, status: str, error_message: str = None
    ) -> None:
        async with self._pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE moderation_results
                SET status = $2, error_message = $3, processed_at = CURRENT_TIMESTAMP
                WHERE id = $1
                """,
                task_id,
                status,
                error_message,
            )

    async def update_moderation_task_success(
        self, task_id: int, is_violation: bool, probability: float
    ) -> None:
        async with self._pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE moderation_results
                SET status = 'completed', is_violation = $2, probability = $3, processed_at = CURRENT_TIMESTAMP
                WHERE id = $1
                """,
                task_id,
                is_violation,
                probability,
            )

    async def get_moderation_task(
        self, task_id: int
    ) -> ModerationTaskDto | None:
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT id AS task_id, status, is_violation, probability
                FROM moderation_results
                WHERE id = $1
                """,
                task_id,
            )
            return ModerationTaskDto(**dict(row)) if row else None

    async def get_task_ids_by_item_id(self, item_id: int) -> list[int]:
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT id FROM moderation_results WHERE item_id = $1", item_id
            )
            return [row["id"] for row in rows]

    async def delete_tasks_by_item_id(self, item_id: int) -> None:
        async with self._pool.acquire() as conn:
            await conn.execute(
                "DELETE FROM moderation_results WHERE item_id = $1", item_id
            )


def get_task_repository(
    pool: asyncpg.Pool = Depends(get_db_pool),
) -> ModerationTaskRepository:
    return ModerationTaskRepository(pool)
