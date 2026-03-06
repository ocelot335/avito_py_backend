from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class SellerDto(BaseModel):
    id: int
    is_verified: bool
    created_at: datetime


class AdDto(BaseModel):
    id: int
    seller_id: int
    title: str
    description: str
    category_id: int
    images_qty: int
    is_closed: bool
    created_at: datetime


class AdFeaturesDto(BaseModel):
    item_id: int
    seller_id: int
    is_verified_seller: bool
    title: str
    description: str
    category_id: int
    images_qty: int


class ModerationTaskDto(BaseModel):
    task_id: int
    status: str
    is_violation: Optional[bool] = None
    probability: Optional[float] = None
