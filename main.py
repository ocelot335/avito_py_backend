from contextlib import asynccontextmanager
import logging
from fastapi import FastAPI
from config.config import get_settings
from routers.predict import predict_router
from ml.model import load_or_train_model
import uvicorn

from services.predict import PredictionService

settings = get_settings()

logging.basicConfig(level=settings.log_level)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    service = PredictionService(model=None)
    app.state.prediction_service = service

    try:
        model = load_or_train_model()
        service.model = model
    except Exception as e:
        logger.error(f"не получилось загрузить модель {e}")

    yield


app = FastAPI(lifespan=lifespan)


@app.get("/")
async def root():
    return {"message": "Hello world!"}


app.include_router(predict_router, prefix="/predict")

if __name__ == "__main__":
    uvicorn.run(app, host=settings.host, port=settings.port)
