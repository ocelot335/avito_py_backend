import json
import logging
from datetime import datetime, timezone
from aiokafka import AIOKafkaProducer

from config.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class KafkaProducerClient:
    def __init__(self):
        self.producer = AIOKafkaProducer(
            bootstrap_servers=settings.kafka_bootstrap_servers,
            value_serializer=lambda v: json.dumps(v).encode("utf-8"),
        )

    async def start(self):
        await self.producer.start()
        logger.info("kafka producer запущен")

    async def stop(self):
        await self.producer.stop()
        logger.info("kafka producer остановлен")

    async def send_moderation_request(self, item_id: int, task_id: int):
        topic = settings.kafka_moderation_topic
        # делаем так, чтобы воркер знал куда именно писать,
        # если несколько задач с одним item_id(например через какое-то время был ещё запрос)
        message = {
            "task_id": task_id,
            "item_id": item_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        try:
            await self.producer.send_and_wait(topic, value=message)
            logger.info(
                f"сообщение отправлено в kafka | topic: {topic} | task_id: {task_id} | item_id: {item_id}"
            )
        except Exception as e:
            logger.error(
                f"ошибка при отправке в kafka (item_id={item_id}): {e}"
            )
            raise
