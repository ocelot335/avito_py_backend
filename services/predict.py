from dataclasses import dataclass
from models.prediction import PredictionRequestDto


@dataclass(frozen=True)
class PredictionService:

    def predict_ad_approve(self, ad: PredictionRequestDto) -> bool:
        if ad.is_verified_seller:
            return True
        return ad.images_qty > 0
