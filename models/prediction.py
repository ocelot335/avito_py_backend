from pydantic import BaseModel, Field


class PredictionRequestDto(BaseModel):
    seller_id: int = Field(..., ge=0)
    is_verified_seller: bool
    item_id: int = Field(..., ge=0)
    name: str
    description: str = Field(..., max_length=1000)
    category: int = Field(..., ge=0, le=100)
    images_qty: int = Field(..., ge=0, le=10)


class PredictionResponseDto(BaseModel):
    is_violation: bool
    probability: float
