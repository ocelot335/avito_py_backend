import pytest
from unittest.mock import patch
import os
from unittest.mock import MagicMock, AsyncMock
import numpy as np
from fastapi.testclient import TestClient
from config.config import Settings, get_settings
from main import app
from routers.predict import get_prediction_service
from services.predict import PredictionService
from datetime import datetime, timezone

from models.db import AdDto, AdFeaturesDto, SellerDto
from repositories.task_repository import get_task_repository
from routers.predict import get_ad_repository, get_kafka_client

from workers.moderation_worker import process_message

client = TestClient(app)


@pytest.fixture(scope="session")
def test_settings():
    return Settings(model_path="test_model.pkl", log_level="DEBUG")


@pytest.fixture(autouse=True)
def override_settings(test_settings):
    app.dependency_overrides[get_settings] = lambda: test_settings
    yield
    app.dependency_overrides = {}

    if os.path.exists(test_settings.model_path):
        os.remove(test_settings.model_path)


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
def mock_repo():
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

    repo.create_seller.return_value = SellerDto(
        id=1, is_verified=True, created_at=datetime.now(timezone.utc)
    )
    repo.create_ad.return_value = AdDto(
        id=100,
        seller_id=1,
        title="iPhone 15 iPhone 15",
        description="Отличное состояние, Отличное состояние, Отличное состояние.",
        category_id=10,
        images_qty=5,
        created_at=datetime.now(timezone.utc),
    )
    return repo


@pytest.fixture
def mock_task_repo():
    repo = AsyncMock()
    repo.create_moderation_task.return_value = 1
    repo.get_moderation_task.return_value = {
        "task_id": 1,
        "status": "pending",
        "is_violation": None,
        "probability": None,
    }
    return repo


@pytest.fixture
def mock_kafka_client():
    client = AsyncMock()
    return client


@pytest.fixture
def override_dependencies(
    mock_model, mock_repo, mock_task_repo, mock_kafka_client
):
    service = PredictionService(model=mock_model)

    app.dependency_overrides[get_prediction_service] = lambda: service
    app.dependency_overrides[get_ad_repository] = lambda: mock_repo
    app.dependency_overrides[get_task_repository] = lambda: mock_task_repo
    app.dependency_overrides[get_kafka_client] = lambda: mock_kafka_client

    yield service, mock_repo, mock_task_repo, mock_kafka_client
    app.dependency_overrides = {}


@pytest.fixture
def mock_db_pool():
    pool = MagicMock()
    ctx_manager = AsyncMock()
    conn = AsyncMock()
    ctx_manager.__aenter__.return_value = conn
    pool.acquire.return_value = ctx_manager
    return pool


@pytest.fixture(autouse=True)
def mock_lifespan_services():
    with patch("main.create_pool", new_callable=AsyncMock) as mock_pool, patch(
        "main.close_pool", new_callable=AsyncMock
    ), patch("main.KafkaProducerClient") as mock_kafka:

        mock_pool.return_value = AsyncMock()

        mock_kafka_instance = MagicMock()
        mock_kafka_instance.start = AsyncMock()
        mock_kafka_instance.stop = AsyncMock()
        mock_kafka.return_value = mock_kafka_instance

        yield


def test_predict_violation_true(
    override_dependencies, mock_model, valid_payload
):
    mock_model.predict_proba.return_value = np.array([[0.15, 0.85]])

    response = client.post("/predict/", json=valid_payload)

    assert response.status_code == 200
    data = response.json()
    assert data["is_violation"] is True
    assert data["probability"] == 0.85


def test_predict_violation_false(
    override_dependencies, mock_model, valid_payload
):
    mock_model.predict_proba.return_value = np.array([[0.95, 0.05]])

    response = client.post("/predict/", json=valid_payload)

    assert response.status_code == 200
    data = response.json()
    assert data["is_violation"] is False
    assert data["probability"] == 0.05


def test_service_unavailable_no_model(valid_payload):
    service = PredictionService(model=None)
    app.dependency_overrides[get_prediction_service] = lambda: service

    response = client.post("/predict/", json=valid_payload)

    assert response.status_code == 503

    app.dependency_overrides = {}


def test_validation_error_wrong_type(override_dependencies, valid_payload):
    payload = valid_payload
    payload["seller_id"] = "asdf"

    response = client.post("/predict/", json=payload)

    assert response.status_code == 422
    data = response.json()
    assert data["detail"][0]["loc"] == ["body", "seller_id"]
    assert data["detail"][0]["type"] == "int_parsing"


def test_validation_max_length_description(
    override_dependencies, valid_payload
):
    payload = valid_payload
    payload["description"] = "a" * 1001

    response = client.post("/predict/", json=payload)

    assert response.status_code == 422
    data = response.json()
    assert data["detail"][0]["loc"] == ["body", "description"]
    assert "string_too_long" in data["detail"][0]["type"]


def test_internal_error_during_prediction(
    override_dependencies, mock_model, valid_payload
):
    mock_model.predict_proba.side_effect = Exception("Sklearn crashed!")

    with TestClient(app, raise_server_exceptions=False) as tc:
        response = tc.post("/predict/", json=valid_payload)

        assert response.status_code == 500


def test_simple_predict_violation_true(override_dependencies, mock_model):
    mock_model.predict_proba.return_value = np.array([[0.15, 0.85]])

    response = client.get("/predict/simple_predict/456")

    assert response.status_code == 200
    data = response.json()
    assert data["is_violation"] is True
    assert data["probability"] == 0.85


def test_simple_predict_violation_false(override_dependencies, mock_model):
    mock_model.predict_proba.return_value = np.array([[0.95, 0.05]])

    response = client.get("/predict/simple_predict/456")

    assert response.status_code == 200
    data = response.json()
    assert data["is_violation"] is False
    assert data["probability"] == 0.05


def test_simple_predict_not_found(override_dependencies, mock_repo):
    mock_repo.get_ad_features.return_value = None

    response = client.get("/predict/simple_predict/999")

    assert response.status_code == 404
    assert "не найдено" in response.json()["detail"]


def test_create_users_and_ads_db(override_dependencies, mock_repo):
    _, repo, _, _ = override_dependencies

    payload = {
        "item_id": 100,
        "seller_id": 1,
        "is_verified_seller": True,
        "title": "iPhone 15 iPhone 15",
        "description": "Отличное состояние, Отличное состояние, Отличное состояние.",
        "category_id": 10,
        "images_qty": 5,
    }

    response = client.post("/predict/seed_test_data", json=payload)

    assert response.status_code == 201

    repo.create_seller.assert_called_once_with(seller_id=1, is_verified=True)

    repo.create_ad.assert_called_once_with(
        item_id=100,
        seller_id=1,
        title="iPhone 15 iPhone 15",
        description="Отличное состояние, Отличное состояние, Отличное состояние.",
        category_id=10,
        images_qty=5,
    )


def test_async_predict_success(override_dependencies):
    _, mock_ad_repo, mock_task_repo, mock_kafka_client = override_dependencies

    mock_ad_repo.get_ad_by_id.return_value = AdDto(
        id=6767,
        seller_id=1,
        title="Test67",
        description="67Test",
        category_id=1,
        images_qty=1,
        created_at=datetime.now(timezone.utc),
    )

    response = client.post("/predict/async_predict/6767")

    assert response.status_code == 202
    data = response.json()
    assert data["task_id"] == 1
    assert data["status"] == "pending"

    mock_task_repo.create_moderation_task.assert_called_once_with(6767)
    mock_kafka_client.send_moderation_request.assert_called_once_with(
        item_id=6767, task_id=1
    )


def test_async_predict_ad_not_found(override_dependencies):
    _, mock_ad_repo, _, _ = override_dependencies
    mock_ad_repo.get_ad_by_id.return_value = None

    response = client.post("/predict/async_predict/999")

    assert response.status_code == 404


def test_async_predict_kafka_failure(override_dependencies):
    _, mock_ad_repo, mock_task_repo, mock_kafka_client = override_dependencies

    mock_ad_repo.get_ad_by_id.return_value = AdDto(
        id=67,
        seller_id=1,
        title="67Test",
        description="67Test",
        category_id=1,
        images_qty=1,
        created_at=datetime.now(timezone.utc),
    )
    mock_kafka_client.send_moderation_request.side_effect = Exception(
        "kafka down!"
    )

    response = client.post("/predict/async_predict/67")

    assert response.status_code == 500
    mock_task_repo.update_moderation_task_status.assert_called_once_with(
        task_id=1,
        status="failed",
        error_message="ошибка брокера сообщений: kafka down!",
    )


def test_get_moderation_result_success(override_dependencies):
    response = client.get("/predict/moderation_result/1")

    assert response.status_code == 200
    assert response.json()["task_id"] == 1
    assert response.json()["status"] == "pending"


def test_get_moderation_result_not_found(override_dependencies):
    _, _, mock_task_repo, _ = override_dependencies
    mock_task_repo.get_moderation_task.return_value = None

    response = client.get("/predict/moderation_result/999")

    assert response.status_code == 404


# далее тесты воркера


@pytest.mark.asyncio
async def test_worker_process_success(mock_model, mock_db_pool):
    msg_value = {"task_id": 1, "item_id": 456}
    service = PredictionService(model=mock_model)
    producer = AsyncMock()

    with patch("workers.moderation_worker.AdRepository") as MockAdRepo, patch(
        "workers.moderation_worker.ModerationTaskRepository"
    ) as MockTaskRepo:
        instance_ad_repo = MockAdRepo.return_value
        instance_ad_repo.get_ad_features = AsyncMock(
            return_value=AdFeaturesDto(
                item_id=456,
                seller_id=123,
                is_verified_seller=True,
                title="test",
                description="test",
                category_id=10,
                images_qty=5,
            )
        )

        instance_task_repo = MockTaskRepo.return_value
        instance_task_repo.update_moderation_task_success = AsyncMock()

        await process_message(msg_value, mock_db_pool, service, producer)

        instance_task_repo.update_moderation_task_success.assert_called_once()
        producer.send_and_wait.assert_not_called()


@pytest.mark.asyncio
@patch("asyncio.sleep", new_callable=AsyncMock)
async def test_worker_process_retries_and_dlq(
    mock_sleep, mock_model, mock_db_pool
):
    msg_value = {"task_id": 1, "item_id": 999}
    service = PredictionService(model=mock_model)
    producer = AsyncMock()

    with patch("workers.moderation_worker.AdRepository") as MockAdRepo, patch(
        "workers.moderation_worker.ModerationTaskRepository"
    ) as MockTaskRepo, patch(
        "workers.moderation_worker.settings"
    ) as mock_settings:

        mock_settings.max_retries = 2
        mock_settings.kafka_dlq_topic = "dlq_test"

        instance_ad_repo = MockAdRepo.return_value
        instance_ad_repo.get_ad_features = AsyncMock(return_value=None)

        instance_task_repo = MockTaskRepo.return_value
        instance_task_repo.update_moderation_task_status = AsyncMock()

        await process_message(msg_value, mock_db_pool, service, producer)

        mock_sleep.assert_called_once()

        instance_task_repo.update_moderation_task_status.assert_called_once()
        assert (
            instance_task_repo.update_moderation_task_status.call_args.kwargs[
                "status"
            ]
            == "failed"
        )

        producer.send_and_wait.assert_called_once()


@pytest.mark.asyncio
async def test_worker_process_dlq_on_missing_ids(mock_db_pool):
    msg_value = {"bad_key": "no_ids"}
    service = PredictionService(model=MagicMock())
    producer = AsyncMock()

    await process_message(msg_value, mock_db_pool, service, producer)

    producer.send_and_wait.assert_called_once()
    args, kwargs = producer.send_and_wait.call_args
    assert kwargs["value"]["error"] == "отсутствуют task_id или item_id"
