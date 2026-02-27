import asyncpg
from fastapi import Depends

from db.database import get_db_connection


class ModerationTaskRepository:
    def __init__(self, connection: asyncpg.Connection):
        self._conn = connection

    async def create_moderation_task(self, item_id: int) -> int:
        row = await self._conn.fetchrow(
            """
            INSERT INTO moderation_results (item_id, status)
            VALUES ($1, 'pending')
            RETURNING id
            """,
            item_id,
        )
        return row["id"]

    async def update_moderation_task_status(
        self, task_id: int, status: str, error_message: str = None
    ) -> None:
        await self._conn.execute(
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
        await self._conn.execute(
            """
            UPDATE moderation_results
            SET status = 'completed',
                is_violation = $2,
                probability = $3,
                processed_at = CURRENT_TIMESTAMP
            WHERE id = $1
            """,
            task_id,
            is_violation,
            probability,
        )

    async def get_moderation_task(self, task_id: int) -> dict | None:
        row = await self._conn.fetchrow(
            """
            SELECT id AS task_id, status, is_violation, probability
            FROM moderation_results
            WHERE id = $1
            """,
            task_id,
        )
        if row is None:
            return None
        return dict(row)


async def get_task_repository(
    connection: asyncpg.Connection = Depends(get_db_connection),
) -> ModerationTaskRepository:
    return ModerationTaskRepository(connection)
