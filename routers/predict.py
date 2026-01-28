from functools import lru_cache
from fastapi import APIRouter, Depends, status
from services.predict import PredictionService
from models.prediction import PredictionRequestDto, PredictionResponseDto


predict_router = APIRouter()


@lru_cache
def get_prediction_service() -> PredictionService:
    return PredictionService()


@predict_router.post(
    "/", response_model=PredictionResponseDto, status_code=status.HTTP_200_OK
)
def predict(
    to_predict: PredictionRequestDto,
    prediction_service: PredictionService = Depends(get_prediction_service),
):
    is_approved = prediction_service.predict_ad_approve(to_predict)

    return PredictionResponseDto(result=is_approved)
