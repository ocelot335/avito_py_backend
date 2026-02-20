import pytest
import os
from unittest.mock import MagicMock, AsyncMock
import numpy as np
from fastapi.testclient import TestClient
from config.config import Settings, get_settings
from main import app
from routers.predict import get_prediction_service
from services.predict import PredictionService
from datetime import datetime, timezone

from repositories.ad_repository import get_ad_repository
from models.db import AdFeaturesDto, SellerDto, AdDto

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
def override_dependencies(mock_model, mock_repo):
    service = PredictionService(model=mock_model)
    app.dependency_overrides[get_prediction_service] = lambda: service
    app.dependency_overrides[get_ad_repository] = lambda: mock_repo
    yield service, mock_repo
    app.dependency_overrides = {}


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
    _, repo = override_dependencies

    response = client.post("/predict/seed_test_data")

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
