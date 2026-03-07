from contextlib import asynccontextmanager
import logging
from fastapi import FastAPI
from config.config import get_settings
from routers.predict import predict_router
from ml.model import load_or_train_model
import uvicorn
import sentry_sdk

from services.predict import PredictionService
from db.database import create_pool, close_pool
from clients.kafka import KafkaProducerClient
from clients.redis import RedisClient

from middlewares.prometheus import PrometheusMiddleware
from routers.system import system_router

settings = get_settings()

if settings.sentry_dsn:
    sentry_sdk.init(
        dsn=settings.sentry_dsn,
        traces_sample_rate=1.0,
        environment="development",
    )

logging.basicConfig(level=settings.log_level)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        pool = await create_pool()
        app.state.db_pool = pool
        logger.info("пул соединений к бд готов")
    except Exception as e:
        logger.error(f"не удалось создать пул соединений к бд: {e}")
        raise

    redis_client = RedisClient()
    try:
        await redis_client.ping()
        app.state.redis_client = redis_client
    except Exception as e:
        logger.error(f"не удалось подключиться к redis: {e}")
        raise

    service = PredictionService(model=None)
    app.state.prediction_service = service
    try:
        model = load_or_train_model()
        service.model = model
    except Exception as e:
        logger.error(f"не получилось загрузить модель {e}")

    kafka_client = KafkaProducerClient()
    try:
        await kafka_client.start()
        app.state.kafka_client = kafka_client
    except Exception as e:
        logger.error(f"не удалось запустить kafka producer {e}")
        raise

    yield

    if hasattr(app.state, "kafka_client"):
        await app.state.kafka_client.stop()

    if hasattr(app.state, "redis_client"):
        await app.state.redis_client.close()

    pool = getattr(app.state, "db_pool", None)
    await close_pool(pool)
    logger.info("приложение остановлено")


app = FastAPI(lifespan=lifespan)

app.add_middleware(PrometheusMiddleware)


@app.get("/")
async def root():
    return {"message": "Hello world!"}


app.include_router(predict_router, prefix="/predict")
app.include_router(system_router)

if __name__ == "__main__":
    uvicorn.run(app, host=settings.host, port=settings.port)
