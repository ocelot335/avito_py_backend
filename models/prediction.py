from pydantic import BaseModel, Field
from typing import Optional


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


class AsyncPredictResponseDto(BaseModel):
    task_id: int
    status: str
    message: str


class ModerationResultResponseDto(BaseModel):
    task_id: int
    status: str
    is_violation: Optional[bool] = None
    probability: Optional[float] = None


class SeedTestDataRequestDto(BaseModel):
    item_id: int = Field(default=100)
    seller_id: int = Field(default=1)
    is_verified_seller: bool = Field(default=True)
    title: str = Field(default="iPhone 15 iPhone 15")
    description: str = Field(
        default="Отличное состояние, Отличное состояние, Отличное состояние."
    )
    category_id: int = Field(default=10)
    images_qty: int = Field(default=5)
