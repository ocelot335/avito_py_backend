import pytest
import numpy as np
from unittest.mock import MagicMock, AsyncMock, patch
from datetime import datetime, timezone
from main import app

from models.db import AdDto, AdFeaturesDto, SellerDto, ModerationTaskDto
from services.predict import PredictionService
from routers.predict import (
    get_prediction_service,
    get_ad_repository,
    get_kafka_client,
)
from repositories.task_repository import get_task_repository
from repositories.seller_repository import get_seller_repository
from storages.prediction_redis_storage import get_prediction_redis_storage
from storages.task_redis_storage import get_task_redis_storage
from storages.active_task_redis_storage import get_active_task_redis_storage
from routers.auth import get_current_user
from models.db import AccountDto


@pytest.fixture
def valid_payload():
    return {
        "seller_id": 123,
        "is_verified_seller": True,
        "item_id": 456,
        "name": "iPhone 15",
        "description": "Just a phone",
        "category": 10,
        "images_qty": 5,
    }


@pytest.fixture
def mock_model():
    model = MagicMock()
    model.predict_proba.return_value = np.array([[0.5, 0.5]])
    return model


@pytest.fixture
def mock_ad_repo():
    repo = AsyncMock()
    repo.get_ad_features.return_value = AdFeaturesDto(
        item_id=456,
        seller_id=123,
        is_verified_seller=True,
        title="iPhone 15",
        description="Just a phone",
        category_id=10,
        images_qty=5,
    )
    repo.create_ad.return_value = AdDto(
        id=100,
        seller_id=1,
        title="iPhone 15 iPhone 15",
        description="Отличное состояние",
        category_id=10,
        images_qty=5,
        is_closed=False,
        created_at=datetime.now(timezone.utc),
    )
    repo.get_ad_by_id.return_value = AdDto(
        id=6767,
        seller_id=1,
        title="Test67",
        description="67Test",
        category_id=1,
        images_qty=1,
        is_closed=False,
        created_at=datetime.now(timezone.utc),
    )
    return repo


@pytest.fixture
def mock_seller_repo():
    repo = AsyncMock()
    repo.create_seller.return_value = SellerDto(
        id=1, is_verified=True, created_at=datetime.now(timezone.utc)
    )
    return repo


@pytest.fixture
def mock_task_repo():
    repo = AsyncMock()
    repo.create_moderation_task.return_value = 1
    repo.get_moderation_task.return_value = ModerationTaskDto(
        task_id=1,
        status="pending",
        is_violation=None,
        probability=None,
    )
    return repo


@pytest.fixture
def mock_kafka_client():
    return AsyncMock()


@pytest.fixture
def mock_predict_redis():
    mock = AsyncMock()
    mock.get.return_value = None
    return mock


@pytest.fixture
def mock_task_redis():
    mock = AsyncMock()
    mock.get.return_value = None
    return mock


@pytest.fixture
def mock_active_task_redis():
    mock = AsyncMock()
    mock.get.return_value = None
    return mock


@pytest.fixture
def override_dependencies(
    mock_model,
    mock_ad_repo,
    mock_seller_repo,
    mock_task_repo,
    mock_kafka_client,
    mock_predict_redis,
    mock_task_redis,
    mock_active_task_redis,
):
    service = PredictionService(model=mock_model)

    fake_user = AccountDto(
        id=1, login="tester", password="123", is_blocked=False
    )

    app.dependency_overrides[get_prediction_service] = lambda: service
    app.dependency_overrides[get_ad_repository] = lambda: mock_ad_repo
    app.dependency_overrides[get_seller_repository] = lambda: mock_seller_repo
    app.dependency_overrides[get_task_repository] = lambda: mock_task_repo
    app.dependency_overrides[get_kafka_client] = lambda: mock_kafka_client
    app.dependency_overrides[get_prediction_redis_storage] = (
        lambda: mock_predict_redis
    )
    app.dependency_overrides[get_task_redis_storage] = lambda: mock_task_redis
    app.dependency_overrides[get_active_task_redis_storage] = (
        lambda: mock_active_task_redis
    )
    app.dependency_overrides[get_current_user] = lambda: fake_user

    mocks = {
        "service": service,
        "ad_repo": mock_ad_repo,
        "seller_repo": mock_seller_repo,
        "task_repo": mock_task_repo,
        "kafka": mock_kafka_client,
        "predict_redis": mock_predict_redis,
        "task_redis": mock_task_redis,
        "active_redis": mock_active_task_redis,
    }
    yield mocks
    app.dependency_overrides = {}


@pytest.fixture
def mock_db_pool():
    return MagicMock()


@pytest.fixture(autouse=True)
def mock_lifespan_services():
    with patch("main.create_pool", new_callable=AsyncMock) as mock_pool, patch(
        "main.close_pool", new_callable=AsyncMock
    ), patch("main.RedisClient") as mock_redis, patch(
        "main.KafkaProducerClient"
    ) as mock_kafka:

        mock_pool.return_value = AsyncMock()

        mock_kafka_instance = MagicMock()
        mock_kafka_instance.start = AsyncMock()
        mock_kafka_instance.stop = AsyncMock()
        mock_kafka.return_value = mock_kafka_instance

        mock_redis_instance = MagicMock()
        mock_redis_instance.ping = AsyncMock()
        mock_redis_instance.close = AsyncMock()
        mock_redis.return_value = mock_redis_instance

        yield
