import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from models.db import AdFeaturesDto
from services.predict import PredictionService
from workers.moderation_worker import process_message


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
        producer.send_and_wait.assert_called_once()


@pytest.mark.asyncio
async def test_worker_process_dlq_on_missing_ids(mock_db_pool):
    msg_value = {"bad_key": "no_ids"}
    service = PredictionService(model=MagicMock())
    producer = AsyncMock()

    await process_message(msg_value, mock_db_pool, service, producer)

    producer.send_and_wait.assert_called_once()
    assert (
        producer.send_and_wait.call_args.kwargs["value"]["error"]
        == "отсутствуют task_id или item_id"
    )
