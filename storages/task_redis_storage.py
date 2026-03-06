import json
from typing import Any, Mapping

from fastapi import Depends
import redis.asyncio as redis
from clients.redis import get_redis


class TaskRedisStorage:
    PREFIX = "task:"
    # TTL: 3 сек (pending) или 1 час (completed/failed) в .env
    # постоянный опрос статуса клиентом сильно грузит бд, и в то же время
    # статус pending может измениться воркером в любую секунду(нужен короткий кэш).
    # финальные же статусы(completed/failed) уже никогда не изменятся.

    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client

    async def set(
        self, task_id: int, row: Mapping[str, Any], ttl_seconds: int
    ) -> None:
        await self.redis.set(
            name=f"{self.PREFIX}{task_id}",
            value=json.dumps(row),
            ex=ttl_seconds,
        )

    async def get(self, task_id: int) -> Mapping[str, Any] | None:
        row = await self.redis.get(f"{self.PREFIX}{task_id}")
        return json.loads(row) if row else None

    async def delete(self, task_id: int) -> None:
        await self.redis.delete(f"{self.PREFIX}{task_id}")


def get_task_redis_storage(
    redis_client: redis.Redis = Depends(get_redis),
) -> TaskRedisStorage:
    return TaskRedisStorage(redis_client)
