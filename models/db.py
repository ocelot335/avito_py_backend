from datetime import datetime
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
    created_at: datetime


class AdFeaturesDto(BaseModel):
    item_id: int
    seller_id: int
    is_verified_seller: bool
    title: str
    description: str
    category_id: int
    images_qty: int
