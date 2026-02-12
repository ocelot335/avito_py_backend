import pytest
import os
from unittest.mock import MagicMock
import numpy as np
from fastapi.testclient import TestClient
from config.config import Settings, get_settings
from main import app
from routers.predict import get_prediction_service
from services.predict import PredictionService

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
def override_dependency(mock_model):
    service = PredictionService(model=mock_model)
    app.dependency_overrides[get_prediction_service] = lambda: service
    yield service
    app.dependency_overrides = {}


def test_predict_violation_true(
    override_dependency, mock_model, valid_payload
):
    mock_model.predict_proba.return_value = np.array([[0.15, 0.85]])

    response = client.post("/predict/", json=valid_payload)

    assert response.status_code == 200
    data = response.json()
    assert data["is_violation"] is True
    assert data["probability"] == 0.85


def test_predict_violation_false(
    override_dependency, mock_model, valid_payload
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


def test_validation_error_wrong_type(override_dependency, valid_payload):
    payload = valid_payload
    payload["seller_id"] = "asdf"

    response = client.post("/predict/", json=payload)

    assert response.status_code == 422
    data = response.json()
    assert data["detail"][0]["loc"] == ["body", "seller_id"]
    assert data["detail"][0]["type"] == "int_parsing"


def test_validation_max_length_description(override_dependency, valid_payload):
    payload = valid_payload
    payload["description"] = "a" * 1001

    response = client.post("/predict/", json=payload)

    assert response.status_code == 422
    data = response.json()
    assert data["detail"][0]["loc"] == ["body", "description"]
    assert "string_too_long" in data["detail"][0]["type"]


def test_internal_error_during_prediction(
    override_dependency, mock_model, valid_payload
):
    mock_model.predict_proba.side_effect = Exception("Sklearn crashed!")

    with TestClient(app, raise_server_exceptions=False) as tc:
        response = tc.post("/predict/", json=valid_payload)

        assert response.status_code == 500
