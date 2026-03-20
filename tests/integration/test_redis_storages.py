import pytest
from storages.prediction_redis_storage import PredictionRedisStorage
from storages.task_redis_storage import TaskRedisStorage
from storages.active_task_redis_storage import ActiveTaskRedisStorage
from config.config import get_settings
from storages.account_redis_storage import AccountRedisStorage

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


@pytest.mark.asyncio
async def test_redis_invalidation_operation(async_redis_client):
    storage = PredictionRedisStorage(async_redis_client)
    item_id = 150
    test_data = {"is_violation": True, "probability": 0.99}

    await storage.set(item_id, test_data)

    assert await storage.get(item_id) is not None

    await storage.delete(item_id)

    assert await storage.get(item_id) is None


@pytest.mark.asyncio
async def test_redis_get_nonexistent_id_edge_case(async_redis_client):
    storage = PredictionRedisStorage(async_redis_client)

    result = await storage.get(999999)

    assert result is None


@pytest.mark.asyncio
async def test_redis_delete_nonexistent_id_edge_case(async_redis_client):
    storage = PredictionRedisStorage(async_redis_client)

    await storage.delete(888888)

    assert await storage.get(888888) is None


@pytest.mark.asyncio
async def test_account_redis_flow(async_redis_client):
    storage = AccountRedisStorage(async_redis_client)
    account_id = 777
    test_data = {
        "id": 777,
        "login": "redis_user",
        "password": "hashed_pass",
        "is_blocked": True,
    }

    assert await storage.get(account_id) is None

    await storage.set(account_id, test_data)

    result = await storage.get(account_id)
    assert result == test_data
    assert result["is_blocked"] is True

    ttl = await async_redis_client.ttl(f"{storage.PREFIX}{account_id}")
    assert ttl > 0
    assert ttl <= settings.redis_account_ttl_sec

    await storage.delete(account_id)
    assert await storage.get(account_id) is None
