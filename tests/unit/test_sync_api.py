import numpy as np
from fastapi.testclient import TestClient
from main import app
from services.predict import PredictionService
from routers.predict import get_prediction_service
from datetime import datetime, timezone
from models.db import AdDto


def test_predict_violation_true(
    client, override_dependencies, mock_model, valid_payload
):
    mock_model.predict_proba.return_value = np.array([[0.15, 0.85]])
    response = client.post("/predict/", json=valid_payload)
    assert response.status_code == 200
    data = response.json()
    assert data["is_violation"] is True
    assert data["probability"] == 0.85


def test_predict_violation_false(
    client, override_dependencies, mock_model, valid_payload
):
    mock_model.predict_proba.return_value = np.array([[0.95, 0.05]])
    response = client.post("/predict/", json=valid_payload)
    assert response.status_code == 200
    assert response.json()["is_violation"] is False


def test_service_unavailable_no_model(
    client, override_dependencies, valid_payload
):
    service = PredictionService(model=None)
    app.dependency_overrides[get_prediction_service] = lambda: service
    response = client.post("/predict/", json=valid_payload)
    assert response.status_code == 503


def test_validation_error_wrong_type(
    client, override_dependencies, valid_payload
):
    payload = valid_payload
    payload["seller_id"] = "asdf"
    response = client.post("/predict/", json=payload)
    assert response.status_code == 422
    assert response.json()["detail"][0]["type"] == "int_parsing"


def test_validation_max_length_description(
    client, override_dependencies, valid_payload
):
    payload = valid_payload
    payload["description"] = "a" * 1001
    response = client.post("/predict/", json=payload)
    assert response.status_code == 422
    assert "string_too_long" in response.json()["detail"][0]["type"]


def test_internal_error_during_prediction(
    override_dependencies, mock_model, valid_payload
):
    mock_model.predict_proba.side_effect = Exception("Sklearn crashed!")
    with TestClient(app, raise_server_exceptions=False) as tc:
        response = tc.post("/predict/", json=valid_payload)
        assert response.status_code == 500


def test_simple_predict_violation_true(
    client, override_dependencies, mock_model
):
    mock_model.predict_proba.return_value = np.array([[0.15, 0.85]])
    response = client.get("/predict/simple_predict/456")
    assert response.status_code == 200
    assert response.json()["is_violation"] is True


def test_simple_predict_not_found(client, override_dependencies):
    mock_ad_repo = override_dependencies["ad_repo"]
    mock_ad_repo.get_ad_features.return_value = None
    response = client.get("/predict/simple_predict/999")
    assert response.status_code == 404


def test_simple_predict_violation_false(
    client, override_dependencies, mock_model
):
    mock_model.predict_proba.return_value = np.array([[0.95, 0.05]])
    response = client.get("/predict/simple_predict/456")

    assert response.status_code == 200
    assert response.json()["is_violation"] is False
    assert response.json()["probability"] == 0.05


def test_close_ad_success(client, override_dependencies):
    ad_repo = override_dependencies["ad_repo"]
    task_repo = override_dependencies["task_repo"]
    predict_redis = override_dependencies["predict_redis"]
    task_redis = override_dependencies["task_redis"]
    active_redis = override_dependencies["active_redis"]

    task_repo.get_task_ids_by_item_id.return_value = [10, 11]

    response = client.post("/predict/close/6767")

    assert response.status_code == 200
    assert response.json()["item_id"] == 6767

    ad_repo.close_ad.assert_called_once_with(6767)
    task_repo.delete_tasks_by_item_id.assert_called_once_with(6767)

    predict_redis.delete.assert_called_once_with(6767)
    active_redis.delete.assert_called_once_with(6767)

    assert task_redis.delete.call_count == 2


def test_close_ad_not_found(client, override_dependencies):
    ad_repo = override_dependencies["ad_repo"]

    ad_repo.get_ad_by_id.return_value = None

    response = client.post("/predict/close/999")

    assert response.status_code == 404


def test_close_ad_already_closed(client, override_dependencies):
    ad_repo = override_dependencies["ad_repo"]

    ad_repo.get_ad_by_id.return_value = AdDto(
        id=6767,
        seller_id=1,
        title="Test67",
        description="67Test",
        category_id=1,
        images_qty=1,
        is_closed=True,
        created_at=datetime.now(timezone.utc),
    )

    response = client.post("/predict/close/6767")

    assert response.status_code == 200
    ad_repo.close_ad.assert_not_called()
