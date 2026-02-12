from dataclasses import dataclass
import logging
from typing import Optional

from fastapi import HTTPException, status
import numpy as np
from sklearn.linear_model import LogisticRegression
from models.prediction import PredictionRequestDto, PredictionResponseDto
from config.config import get_settings

settings = get_settings()

logging.basicConfig(
    level=settings.log_level,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@dataclass()
class PredictionService:
    model: Optional[LogisticRegression] = None

    def predict_ad_approve(
        self, ad: PredictionRequestDto
    ) -> PredictionResponseDto:
        if self.model is None:
            logger.warning("ml-модель не загружена")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="ml-модель не загружена",
            )

        try:
            f_verified = 1.0 if ad.is_verified_seller else 0.0

            f_images = ad.images_qty / 10.0

            f_desc_len = len(ad.description) / 1000.0

            f_category = ad.category / 100.0

            features_list = [f_verified, f_images, f_desc_len, f_category]
            features_vector = np.array([features_list])

            logger.info(
                f"/predict request | "
                f"seller_id: {ad.seller_id}, item_id: {ad.item_id} | "
                f"Признаки [is_verified_seller, images_qty, description_length, category]: {features_list}"
            )

            probs = self.model.predict_proba(features_vector)[0]
            violation_prob = probs[1]

            is_violation = violation_prob > 0.5

            logger.info(
                f"/predict result  | "
                f"is_violation: {is_violation}, probability: {violation_prob:.4f}"
            )

            return PredictionResponseDto(
                is_violation=bool(is_violation),
                probability=float(violation_prob),
            )
        except Exception as e:
            logger.error(
                f"произошла ошибка item_id={ad.item_id}. Error: {e}",
                exc_info=True,
            )

            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Произошла ошибка при предсказании: {str(e)}",
            )
