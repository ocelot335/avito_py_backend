from fastapi import APIRouter, Depends, status, Request, Path, HTTPException
from services.predict import PredictionService
from models.prediction import PredictionRequestDto, PredictionResponseDto

from repositories.ad_repository import AdRepository, get_ad_repository


predict_router = APIRouter()


def get_prediction_service(request: Request) -> PredictionService:
    return request.app.state.prediction_service


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


# для тестов
@predict_router.post(
    "/seed_test_data",
    status_code=status.HTTP_201_CREATED,
    summary="сгенерировать тестовые данные в БД",
)
async def seed_test_data(repo: AdRepository = Depends(get_ad_repository)):
    seller = await repo.create_seller(seller_id=1, is_verified=True)

    ad = await repo.create_ad(
        item_id=100,
        seller_id=seller.id,
        title="iPhone 15 iPhone 15",
        description="Отличное состояние, Отличное состояние, Отличное состояние.",
        category_id=10,
        images_qty=5,
    )

    return {
        "message": "ОК!",
        "seller": seller,
        "ad": ad,
    }
