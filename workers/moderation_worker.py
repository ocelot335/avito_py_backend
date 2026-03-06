import asyncio
import json
import logging
from datetime import datetime, timezone
from aiokafka import AIOKafkaConsumer, AIOKafkaProducer

from config.config import get_settings
from db.database import create_pool, close_pool
from ml.model import load_or_train_model
from services.predict import PredictionService
from repositories.ad_repository import AdRepository
from repositories.task_repository import ModerationTaskRepository
from models.prediction import PredictionRequestDto

settings = get_settings()
logging.basicConfig(level=settings.log_level)
logger = logging.getLogger("moderation_worker")


async def process_message(
    msg_value: dict,
    db_pool,
    prediction_service: PredictionService,
    producer: AIOKafkaProducer,
):
    task_id = msg_value.get("task_id")
    item_id = msg_value.get("item_id")
    if not task_id or not item_id:
        logger.error(f"отсутствуют task_id или item_id: {msg_value}")
        await send_to_dlq(
            msg_value, "отсутствуют task_id или item_id", producer, 0
        )
        return

    ad_repo = AdRepository(db_pool)
    task_repo = ModerationTaskRepository(db_pool)

    for attempt in range(1, settings.max_retries + 1):
        try:
            ad_features = await ad_repo.get_ad_features(item_id)
            if not ad_features:
                raise ValueError(f"объявление с id {item_id} не найдено в бд")

            ml_request = PredictionRequestDto(
                seller_id=ad_features.seller_id,
                is_verified_seller=ad_features.is_verified_seller,
                item_id=ad_features.item_id,
                name=ad_features.title,
                description=ad_features.description,
                category=ad_features.category_id,
                images_qty=ad_features.images_qty,
            )

            result = prediction_service.predict_ad_approve(ml_request)

            await task_repo.update_moderation_task_success(
                task_id=task_id,
                is_violation=result.is_violation,
                probability=result.probability,
            )
            logger.info(
                f"task_id={task_id} завершён успешно, попытка {attempt}"
            )
            return

        except Exception as e:
            error_msg = str(e)
            if attempt < settings.max_retries:
                logger.warning(
                    f"ошибка при обработке task_id={task_id}: {e} "
                    f"таймер {settings.retry_delay_seconds} сек перед следующей попыткой"
                )
                await asyncio.sleep(settings.retry_delay_seconds)
            else:
                logger.error(
                    f"все {settings.max_retries} попытки исчерпаны для task_id({task_id}). "
                    f"последняя ошибка: {error_msg}",
                    exc_info=True,
                )

                try:
                    await task_repo.update_moderation_task_status(
                        task_id=task_id,
                        status="failed",
                        error_message=error_msg,
                    )
                except Exception as db_err:
                    logger.error(
                        f"не удалось обновить статус в бд для task_id({task_id}): {db_err}"
                    )

                await send_to_dlq(msg_value, error_msg, producer, attempt)


async def send_to_dlq(
    msg_value: dict,
    error_msg: str,
    producer: AIOKafkaProducer,
    attempts: int,
):
    dlq_message = {
        "original_message": msg_value,
        "error": error_msg,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "retry_count": attempts,
    }

    try:
        await producer.send_and_wait(
            settings.kafka_dlq_topic, value=dlq_message
        )
        logger.info(
            f"отправлено в dlq({settings.kafka_dlq_topic}): {dlq_message}"
        )
    except Exception as kafka_err:
        logger.error(f"НЕ УДАЛОСЬ ОТПРАВИТЬ В DLQ: {kafka_err}")
        raise  # бросаем исключение, чтобы не сработал commit() в основном цикле, может перемудрил здесь


async def main():
    try:
        db_pool = await create_pool()
        logger.info("пул соединений к бд готов")
    except Exception as e:
        logger.error(f"не удалось создать пул соединений к бд: {e}")
        raise

    prediction_service = PredictionService(model=None)
    try:
        model = load_or_train_model()
        prediction_service.model = model
    except Exception as e:
        logger.error(f"не получилось загрузить модель {e}")
        raise

    consumer = AIOKafkaConsumer(
        settings.kafka_moderation_topic,
        bootstrap_servers=settings.kafka_bootstrap_servers,
        group_id=settings.kafka_consumer_group,
        value_deserializer=lambda m: json.loads(m.decode("utf-8")),
        auto_offset_reset="earliest",
        enable_auto_commit=False,
    )
    await consumer.start()

    producer = AIOKafkaProducer(
        bootstrap_servers=settings.kafka_bootstrap_servers,
        value_serializer=lambda v: json.dumps(v).encode("utf-8"),
    )
    await producer.start()

    logger.info("воркер начал работать")

    try:
        async for msg in consumer:
            logger.debug(f"получено сообщение: {msg.value}")
            await process_message(
                msg.value, db_pool, prediction_service, producer
            )
            await consumer.commit()
    except asyncio.CancelledError:
        logger.info("остановка...")
    except Exception as e:
        logger.error(f"ошибка воркера: {e}", exc_info=True)
    finally:
        await producer.stop()
        await consumer.stop()
        await close_pool(db_pool)
        logger.info("воркер остановлен")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("exit")
