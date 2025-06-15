from pydantic import BaseModel, Field
from decimal import Decimal
from typing import Optional


class OrderItemCreate(BaseModel):
    product_id: int
    quantity: int = Field(..., ge=1)
    unit_price: Decimal = Field(..., ge=0)


class OrderItemResponse(BaseModel):
    id: int
    product_id: int
    product_name: str
    product_sku: Optional[str] = None
    quantity: int
    unit_price: Decimal
    total_price: Decimal

    class Config:
        from_attributes = True