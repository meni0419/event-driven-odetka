from pydantic import BaseModel
from typing import List
from datetime import datetime
from .cart_item import CartItem


class CartBase(BaseModel):
    pass


class CartCreate(CartBase):
    session_id: str


class Cart(CartBase):
    id: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class CartSummary(BaseModel):
    cart_id: str
    total_items: int
    total_amount: float
    items: List[CartItem]

    class Config:
        from_attributes = True