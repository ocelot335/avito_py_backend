from fastapi import Depends
import redis.asyncio as redis

from clients.redis import get_redis
from config.config import get_settings

settings = get_settings()


class ActiveTaskRedisStorage:
    PREFIX = "active_task:"
    # TTL: 60 секунд в .env
    # защита от спама дублей(для локальной идемпотентности)
    # если на одно объявление отправлено несколько запросов подряд,
    # мы не создаем новые задачи в бд и не грузим kafka,
    # а возвращаем id уже созданной и находящейся в очереди задачи

    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client

    async def set(self, item_id: int, task_id: int) -> None:
        await self.redis.set(
            name=f"{self.PREFIX}{item_id}",
            value=task_id,
            ex=settings.redis_active_task_ttl_sec,
        )

    async def get(self, item_id: int) -> int | None:
        task_id = await self.redis.get(f"{self.PREFIX}{item_id}")
        return int(task_id) if task_id else None

    async def delete(self, item_id: int) -> None:
        await self.redis.delete(f"{self.PREFIX}{item_id}")


def get_active_task_redis_storage(
    redis_client: redis.Redis = Depends(get_redis),
) -> ActiveTaskRedisStorage:
    return ActiveTaskRedisStorage(redis_client)
