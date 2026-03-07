from dataclasses import dataclass
import logging
from typing import Optional

from fastapi import HTTPException, status
import numpy as np
import sentry_sdk
from sklearn.linear_model import LogisticRegression
from exceptions import ErrorInPrediction, ModelIsNotAvailable
from models.prediction import PredictionRequestDto, PredictionResponseDto
from config.config import get_settings

import time
from metrics import (
    PREDICTIONS_TOTAL,
    PREDICTION_DURATION,
    PREDICTION_ERRORS_TOTAL,
    MODEL_PREDICTION_PROBABILITY,
)

settings = get_settings()

logger = logging.getLogger(__name__)


@dataclass()
class PredictionService:
    model: Optional[LogisticRegression] = None

    def predict_ad_approve(
        self, ad: PredictionRequestDto
    ) -> PredictionResponseDto:

        if "POSION_PILL_67_67" in ad.description:
            PREDICTION_ERRORS_TOTAL.labels(error_type="prediction_error").inc()
            logger.error("имитация падения ML-модели.")
            e = ErrorInPrediction(
                "модель не смогла обработать этот текст (SegFault)"
            )
            sentry_sdk.capture_exception(e)
            raise HTTPException(status_code=500, detail=str(e))

        if self.model is None:
            PREDICTION_ERRORS_TOTAL.labels(
                error_type="model_unavailable"
            ).inc()
            logger.warning("ml-модель не загружена")
            e = ModelIsNotAvailable("ML-модель не загружена")
            sentry_sdk.capture_exception(e)
            raise HTTPException(status_code=503, detail=str(e))

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

            # --- собственно предсказание
            start_time = time.time()
            probs = self.model.predict_proba(features_vector)[0]
            inference_duration = time.time() - start_time
            PREDICTION_DURATION.observe(inference_duration)
            # ---

            violation_prob = probs[1]

            is_violation = violation_prob > 0.5

            logger.info(
                f"/predict result  | "
                f"is_violation: {is_violation}, probability: {violation_prob:.4f}"
            )

            MODEL_PREDICTION_PROBABILITY.observe(float(violation_prob))

            result_label = "violation" if is_violation else "no_violation"
            PREDICTIONS_TOTAL.labels(result=result_label).inc()

            return PredictionResponseDto(
                is_violation=bool(is_violation),
                probability=float(violation_prob),
            )
        except Exception as e:
            PREDICTION_ERRORS_TOTAL.labels(error_type="prediction_error").inc()

            logger.error(
                f"произошла ошибка item_id={ad.item_id}. Error: {e}",
                exc_info=True,
            )

            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Произошла ошибка при предсказании: {str(e)}",
            )
