from fastapi.testclient import TestClient
from main import app
from routers.predict import get_prediction_service
from models.prediction import PredictionRequestDto

client = TestClient(app)


def test_predict_approve_verified_seller():
    payload = {
        "seller_id": 123,
        "is_verified_seller": True,
        "item_id": 456,
        "name": "iPhone",
        "description": "phone",
        "category": 10,
        "images_qty": 0,
    }

    response = client.post("/predict/", json=payload)

    assert response.status_code == 200
    assert response.json() == {"result": True}


def test_predict_approve_with_images():
    payload = {
        "seller_id": 123,
        "is_verified_seller": False,
        "item_id": 456,
        "name": "iPhone",
        "description": "phone",
        "category": 10,
        "images_qty": 5,
    }

    response = client.post("/predict/", json=payload)

    assert response.status_code == 200
    assert response.json() == {"result": True}


def test_predict_reject():
    payload = {
        "seller_id": 123,
        "is_verified_seller": False,
        "item_id": 456,
        "name": "iPhone",
        "description": "phone",
        "category": 10,
        "images_qty": 0,
    }

    response = client.post("/predict/", json=payload)

    assert response.status_code == 200
    assert response.json() == {"result": False}


def test_validation_error_missing_field():
    payload = {
        "seller_id": 123,
        "is_verified_seller": False,
        "item_id": 456,
        "name": "iPhone",
        "description": "phone",
        "category": 10,
    }

    response = client.post("/predict/", json=payload)

    assert response.status_code == 422
    data = response.json()
    assert data["detail"][0]["loc"] == ["body", "images_qty"]
    assert data["detail"][0]["type"] == "missing"


def test_validation_error_wrong_type():
    payload = {
        "seller_id": "x",
        "is_verified_seller": False,
        "item_id": 456,
        "name": "iPhone",
        "description": "phone",
        "category": 10,
        "images_qty": 5,
    }

    response = client.post("/predict/", json=payload)
    assert response.status_code == 422
    data = response.json()
    assert data["detail"][0]["loc"] == ["body", "seller_id"]
    assert data["detail"][0]["type"] == "int_parsing"


def test_validation_constraint_violation():
    payload = {
        "seller_id": 123,
        "is_verified_seller": False,
        "item_id": 456,
        "name": "iPhone",
        "description": "phone",
        "category": 10,
        "images_qty": -5,
    }
    response = client.post("/predict/", json=payload)
    assert response.status_code == 422
    assert "greater than or equal to 0" in response.json()["detail"][0]["msg"]


def test_business_logic_exception():
    class MockService:
        def predict_ad_approve(self, ad: PredictionRequestDto) -> bool:
            raise ValueError()

    app.dependency_overrides[get_prediction_service] = lambda: MockService()

    payload = {
        "seller_id": 123,
        "is_verified_seller": False,
        "item_id": 456,
        "name": "iPhone",
        "description": "phone",
        "category": 10,
        "images_qty": 5,
    }

    with TestClient(app, raise_server_exceptions=False) as test_client:
        response = test_client.post("/predict/", json=payload)

        assert response.status_code == 500

    app.dependency_overrides = {}
