from fastapi import APIRouter, Depends, status, Request, Path, HTTPException
from services.predict import PredictionService
from models.prediction import (
    PredictionRequestDto,
    PredictionResponseDto,
    AsyncPredictResponseDto,
    ModerationResultResponseDto,
    SeedTestDataRequestDto,
)
import logging

from repositories.ad_repository import AdRepository, get_ad_repository
from repositories.task_repository import (
    ModerationTaskRepository,
    get_task_repository,
)
from clients.kafka import KafkaProducerClient


logger = logging.getLogger(__name__)

predict_router = APIRouter()


def get_prediction_service(request: Request) -> PredictionService:
    return request.app.state.prediction_service


def get_kafka_client(request: Request) -> KafkaProducerClient:
    client = getattr(request.app.state, "kafka_client", None)
    if client is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="асинхронный вызов сейчас недоступен",
        )
    return client


@predict_router.post(
    "/", response_model=PredictionResponseDto, status_code=status.HTTP_200_OK
)
def predict(
    to_predict: PredictionRequestDto,
    prediction_service: PredictionService = Depends(get_prediction_service),
):
    return prediction_service.predict_ad_approve(to_predict)


@predict_router.get(
    "/simple_predict/{item_id}",
    response_model=PredictionResponseDto,
    status_code=status.HTTP_200_OK,
)
async def simple_predict(
    item_id: int = Path(..., ge=0),
    prediction_service: PredictionService = Depends(get_prediction_service),
    repo: AdRepository = Depends(get_ad_repository),
):
    ad_features = await repo.get_ad_features(item_id)

    if not ad_features:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"объявление с id {item_id} не найдено",
        )

    ml_request = PredictionRequestDto(
        seller_id=ad_features.seller_id,
        is_verified_seller=ad_features.is_verified_seller,
        item_id=ad_features.item_id,
        name=ad_features.title,
        description=ad_features.description,
        category=ad_features.category_id,
        images_qty=ad_features.images_qty,
    )

    return prediction_service.predict_ad_approve(ml_request)


@predict_router.post(
    "/async_predict/{item_id}",
    response_model=AsyncPredictResponseDto,
    status_code=status.HTTP_202_ACCEPTED,
)
async def async_predict(
    item_id: int = Path(..., ge=0),
    ad_repo: AdRepository = Depends(get_ad_repository),
    task_repo: ModerationTaskRepository = Depends(get_task_repository),
    kafka_client: KafkaProducerClient = Depends(get_kafka_client),
):
    ad = await ad_repo.get_ad_by_id(item_id)
    if not ad:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Объявление с id {item_id} не найдено",
        )

    task_id = await task_repo.create_moderation_task(item_id)

    try:
        await kafka_client.send_moderation_request(
            item_id=item_id, task_id=task_id
        )
    except Exception as e:
        error_msg = f"ошибка брокера сообщений: {str(e)}"
        await task_repo.update_moderation_task_status(
            task_id=task_id, status="failed", error_message=error_msg
        )

        logger.error(
            f"произошла ошибка при отправке в kafka для задания {task_id}. Помечено в бд со следующим сообщением: {e}"
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="не удалось отправить задачу в очередь",
        )

    return AsyncPredictResponseDto(
        task_id=task_id,
        status="pending",
        message="Moderation request accepted",
    )


@predict_router.get(
    "/moderation_result/{task_id}",
    response_model=ModerationResultResponseDto,
    status_code=status.HTTP_200_OK,
)
async def get_moderation_result(
    task_id: int = Path(..., ge=1, description="id задачи"),
    task_repo: ModerationTaskRepository = Depends(get_task_repository),
):
    task_data = await task_repo.get_moderation_task(task_id)

    if not task_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"задача модерации с таким task_id({task_id}) не найдена",
        )

    return ModerationResultResponseDto(**task_data)


# для тестов
@predict_router.post(
    "/seed_test_data",
    status_code=status.HTTP_201_CREATED,
    summary="сгенерировать тестовые данные в БД",
)
async def seed_test_data(
    payload: SeedTestDataRequestDto,
    repo: AdRepository = Depends(get_ad_repository),
):
    seller = await repo.create_seller(
        seller_id=payload.seller_id, is_verified=payload.is_verified_seller
    )

    ad = await repo.create_ad(
        item_id=payload.item_id,
        seller_id=seller.id,
        title=payload.title,
        description=payload.description,
        category_id=payload.category_id,
        images_qty=payload.images_qty,
    )

    return {
        "message": "ОК!",
        "seller": seller,
        "ad": ad,
    }
