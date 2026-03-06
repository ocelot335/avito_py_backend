from datetime import datetime, timezone
from models.db import AdDto


def test_create_users_and_ads_db(client, override_dependencies):
    ad_repo = override_dependencies["ad_repo"]
    seller_repo = override_dependencies["seller_repo"]
    payload = {
        "item_id": 100,
        "seller_id": 1,
        "is_verified_seller": True,
        "title": "iPhone",
        "description": "Good",
        "category_id": 10,
        "images_qty": 5,
    }
    response = client.post("/predict/seed_test_data", json=payload)
    assert response.status_code == 201
    seller_repo.create_seller.assert_called_once()
    ad_repo.create_ad.assert_called_once()


def test_async_predict_success(client, override_dependencies):
    mock_ad_repo = override_dependencies["ad_repo"]
    mock_task_repo = override_dependencies["task_repo"]
    mock_kafka = override_dependencies["kafka"]

    mock_ad_repo.get_ad_by_id.return_value = AdDto(
        id=6767,
        seller_id=1,
        title="T",
        description="D",
        category_id=1,
        images_qty=1,
        is_closed=False,
        created_at=datetime.now(timezone.utc),
    )
    response = client.post("/predict/async_predict/6767")
    assert response.status_code == 202
    assert response.json()["task_id"] == 1
    mock_task_repo.create_moderation_task.assert_called_once_with(6767)
    mock_kafka.send_moderation_request.assert_called_once_with(
        item_id=6767, task_id=1
    )


def test_async_predict_ad_not_found(client, override_dependencies):
    mock_ad_repo = override_dependencies["ad_repo"]
    mock_ad_repo.get_ad_by_id.return_value = None
    response = client.post("/predict/async_predict/999")
    assert response.status_code == 404


def test_async_predict_kafka_failure(client, override_dependencies):
    mock_ad_repo = override_dependencies["ad_repo"]
    mock_task_repo = override_dependencies["task_repo"]
    mock_kafka = override_dependencies["kafka"]

    mock_ad_repo.get_ad_by_id.return_value = AdDto(
        id=67,
        seller_id=1,
        title="T",
        description="D",
        category_id=1,
        images_qty=1,
        is_closed=False,
        created_at=datetime.now(timezone.utc),
    )
    mock_kafka.send_moderation_request.side_effect = Exception("kafka down!")
    response = client.post("/predict/async_predict/67")
    assert response.status_code == 500
    mock_task_repo.update_moderation_task_status.assert_called_once_with(
        task_id=1,
        status="failed",
        error_message="ошибка брокера сообщений: kafka down!",
    )


def test_get_moderation_result_success(client, override_dependencies):
    response = client.get("/predict/moderation_result/1")
    assert response.status_code == 200
    assert response.json()["status"] == "pending"


def test_get_moderation_result_not_found(client, override_dependencies):
    mock_task_repo = override_dependencies["task_repo"]
    mock_task_repo.get_moderation_task.return_value = None
    response = client.get("/predict/moderation_result/999")
    assert response.status_code == 404
