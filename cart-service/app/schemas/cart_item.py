from pydantic import BaseModel
from typing import Optional


class CartItemBase(BaseModel):
    product_id: int
    quantity: int


class CartItemCreate(CartItemBase):
    pass


class CartItemUpdate(BaseModel):
    quantity: int


class CartItem(CartItemBase):
    id: int
    cart_id: str
    price_at_add: float

    class Config:
        from_attributes = True