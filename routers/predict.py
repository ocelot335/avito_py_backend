from fastapi import APIRouter, Depends, status, Request
from services.predict import PredictionService
from models.prediction import PredictionRequestDto, PredictionResponseDto


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
