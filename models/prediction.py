from pydantic import BaseModel, Field


class PredictionRequestDto(BaseModel):
    seller_id: int = Field(..., ge=0)
    is_verified_seller: bool
    item_id: int = Field(..., ge=0)
    name: str
    description: str
    category: int
    images_qty: int = Field(..., ge=0)


class PredictionResponseDto(BaseModel):
    result: bool
