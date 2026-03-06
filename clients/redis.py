import logging
import redis.asyncio as redis
from fastapi import Request
from config.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class RedisClient:
    def __init__(self):
        self.pool = redis.ConnectionPool.from_url(
            settings.redis_url,
            decode_responses=True,
        )
        self.client = redis.Redis(connection_pool=self.pool)

    async def ping(self):
        await self.client.ping()
        logger.info("подключение к redis успешно")

    async def close(self):
        await self.client.aclose()
        await self.pool.disconnect()
        logger.info("соединение с redis закрыто")


def get_redis(request: Request) -> redis.Redis:
    redis_instance = getattr(request.app.state, "redis_client", None)
    if redis_instance is None:
        raise RuntimeError("redis клиент не найден в app.state")
    return redis_instance.client
