import pytest
from storages.prediction_redis_storage import PredictionRedisStorage
from storages.task_redis_storage import TaskRedisStorage
from storages.active_task_redis_storage import ActiveTaskRedisStorage
from config.config import get_settings

settings = get_settings()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_prediction_storage_set_get(async_redis_client):
    storage = PredictionRedisStorage(async_redis_client)
    item_id = 100
    test_data = {"is_violation": True, "probability": 0.85}

    assert await storage.get(item_id) is None

    await storage.set(item_id, test_data)

    result = await storage.get(item_id)
    assert result == test_data

    ttl = await async_redis_client.ttl(f"{storage.PREFIX}{item_id}")
    assert ttl > 0
    assert ttl <= settings.redis_predict_ttl_sec


@pytest.mark.integration
@pytest.mark.asyncio
async def test_task_storage_dynamic_ttl(async_redis_client):
    storage = TaskRedisStorage(async_redis_client)
    task_id = 42
    test_data = {"task_id": 42, "status": "pending"}
    custom_ttl = 5

    await storage.set(task_id, test_data, ttl_seconds=custom_ttl)

    result = await storage.get(task_id)
    assert result == test_data

    ttl = await async_redis_client.ttl(f"{storage.PREFIX}{task_id}")
    assert ttl > 0
    assert ttl <= custom_ttl


@pytest.mark.integration
@pytest.mark.asyncio
async def test_active_task_storage_idempotency(async_redis_client):
    storage = ActiveTaskRedisStorage(async_redis_client)
    item_id = 777
    task_id = 888

    await storage.set(item_id, task_id)

    result = await storage.get(item_id)
    assert result == task_id

    assert isinstance(result, int)
