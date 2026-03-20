import json
from typing import Any, Mapping
import redis.asyncio as redis
from fastapi import Depends

from clients.redis import get_redis
from config.config import get_settings

settings = get_settings()


class AccountRedisStorage:
    PREFIX = "account:"

    # TTL: 5 минут в .env
    # Данные аккаунта меняются крайне редко, так что границу задаёт статус.
    # 5 минут - это  компромисс, чтобы бд не страдало,
    # когда мы каждый раз будем проверять статус и
    # чтобы кеш протух не слишко поздно

    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client

    async def set(self, account_id: int, row: Mapping[str, Any]) -> None:
        await self.redis.set(
            name=f"{self.PREFIX}{account_id}",
            value=json.dumps(row),
            ex=settings.redis_account_ttl_sec,
        )

    async def get(self, account_id: int) -> Mapping[str, Any] | None:
        row = await self.redis.get(f"{self.PREFIX}{account_id}")
        return json.loads(row) if row else None

    async def delete(self, account_id: int) -> None:
        await self.redis.delete(f"{self.PREFIX}{account_id}")


def get_account_redis_storage(
    redis_client: redis.Redis = Depends(get_redis),
) -> AccountRedisStorage:
    return AccountRedisStorage(redis_client)
