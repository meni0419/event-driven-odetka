from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
from decimal import Decimal
from ..models.order import OrderStatus


class OrderItemCreate(BaseModel):
    product_id: int
    quantity: int
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


class OrderCreate(BaseModel):
    cart_id: str
    user_id: Optional[str] = None
    items: List[OrderItemCreate]
    shipping_address: Optional[str] = None
    shipping_method: Optional[str] = None
    notes: Optional[str] = None


class OrderUpdate(BaseModel):
    status: Optional[OrderStatus] = None
    shipping_address: Optional[str] = None
    shipping_method: Optional[str] = None
    notes: Optional[str] = None


class OrderResponse(BaseModel):
    id: str
    cart_id: str
    user_id: Optional[str] = None
    status: OrderStatus

    total_amount: Decimal
    discount_amount: Decimal
    shipping_amount: Decimal
    tax_amount: Decimal
    final_amount: Decimal
    total_items: int

    shipping_address: Optional[str] = None
    shipping_method: Optional[str] = None
    notes: Optional[str] = None

    created_at: datetime
    updated_at: datetime
    confirmed_at: Optional[datetime] = None
    shipped_at: Optional[datetime] = None
    delivered_at: Optional[datetime] = None

    items: List[OrderItemResponse] = []

    class Config:
        from_attributes = True


class OrderListResponse(BaseModel):
    orders: List[OrderResponse]
    total: int
    page: int
    per_page: int
    total_pages: int