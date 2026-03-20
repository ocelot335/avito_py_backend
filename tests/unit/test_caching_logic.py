from models.db import ModerationTaskDto


def test_simple_predict_cache_hit(client, override_dependencies):
    predict_redis = override_dependencies["predict_redis"]
    ad_repo = override_dependencies["ad_repo"]
    service = override_dependencies["service"]

    predict_redis.get.return_value = {
        "is_violation": True,
        "probability": 0.99,
    }
    response = client.get("/predict/simple_predict/456")

    assert response.status_code == 200
    assert response.json()["probability"] == 0.99
    ad_repo.get_ad_features.assert_not_called()
    service.model.predict_proba.assert_not_called()


def test_moderation_result_smart_ttl(
    client, override_dependencies, test_settings
):
    task_redis = override_dependencies["task_redis"]
    task_repo = override_dependencies["task_repo"]

    task_repo.get_moderation_task.return_value = ModerationTaskDto(
        task_id=1, status="pending"
    )
    response = client.get("/predict/moderation_result/1")

    assert response.status_code == 200
    task_redis.set.assert_called_once()
    assert (
        task_redis.set.call_args.kwargs["ttl_seconds"]
        == test_settings.redis_task_pending_ttl_sec
    )


def test_async_predict_idempotency(client, override_dependencies):
    active_redis = override_dependencies["active_redis"]
    task_repo = override_dependencies["task_repo"]
    kafka = override_dependencies["kafka"]

    active_redis.get.return_value = 999
    response = client.post("/predict/async_predict/456")

    assert response.status_code == 202
    assert response.json()["task_id"] == 999
    task_repo.create_moderation_task.assert_not_called()
    kafka.send_moderation_request.assert_not_called()


def test_close_ad_cache_invalidation(client, override_dependencies):
    task_repo = override_dependencies["task_repo"]
    predict_redis = override_dependencies["predict_redis"]
    task_redis = override_dependencies["task_redis"]
    active_redis = override_dependencies["active_redis"]

    task_repo.get_task_ids_by_item_id.return_value = [10, 11]

    response = client.post("/predict/close/6767")

    assert response.status_code == 200

    predict_redis.delete.assert_called_once_with(6767)

    active_redis.delete.assert_called_once_with(6767)

    assert task_redis.delete.call_count == 2
