import json
from typing import Any, Mapping
import redis.asyncio as redis
from fastapi import Depends

from clients.redis import get_redis
from config.config import get_settings

settings = get_settings()


class PredictionRedisStorage:
    PREFIX = "predict:"
    # TTL: 10 минут в .env
    # ml-предсказание как-бы является дорогим и в то же время
    # результат зависит только от объявления, которое не должно часто меняться.
    # у нас может в это время поменяться объвление,
    # но пусть лучше лучше немного на фронте будет показывать неправильно,
    # чем постоянно дёргать бд и ml. Всё-таки синхронная ручка!

    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client

    async def set(self, item_id: int, row: Mapping[str, Any]) -> None:
        await self.redis.set(
            name=f"{self.PREFIX}{item_id}",
            value=json.dumps(row),
            ex=settings.redis_predict_ttl_sec,
        )

    async def get(self, item_id: int) -> Mapping[str, Any] | None:
        row = await self.redis.get(f"{self.PREFIX}{item_id}")
        return json.loads(row) if row else None

    async def delete(self, item_id: int) -> None:
        await self.redis.delete(f"{self.PREFIX}{item_id}")


def get_prediction_redis_storage(
    redis_client: redis.Redis = Depends(get_redis),
) -> PredictionRedisStorage:
    return PredictionRedisStorage(redis_client)
