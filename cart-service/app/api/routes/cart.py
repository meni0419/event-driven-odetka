from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Union

from ...database import get_db
from ...schemas.cart import Cart as CartSchema, CartSummary
from ...schemas.cart_item import CartItem, CartItemCreate, CartItemUpdate
from ...services.cart_service import CartService
from ..dependencies import get_current_user_or_session

router = APIRouter()


@router.get("/cart", response_model=CartSummary)
async def get_cart(
        cart_id: str = Depends(get_current_user_or_session),
        db: Session = Depends(get_db)
):
    """Получение текущей корзины пользователя"""
    cart_service = CartService(db)
    return cart_service.get_cart(cart_id)  # Этот метод синхронный


@router.post("/cart/items", response_model=CartItem)
async def add_item_to_cart(
        item: CartItemCreate,
        cart_id: str = Depends(get_current_user_or_session),
        db: Session = Depends(get_db)
):
    """Добавление товара в корзину"""
    cart_service = CartService(db)
    return await cart_service.add_item(cart_id, item)  # ✅ Добавили await


@router.put("/cart/items/{product_id}", response_model=Union[CartItem, dict])
async def update_cart_item(
        product_id: int,
        item: CartItemUpdate,
        cart_id: str = Depends(get_current_user_or_session),
        db: Session = Depends(get_db)
):
    """Обновление количества товара в корзине"""
    cart_service = CartService(db)
    result = await cart_service.update_item(cart_id, product_id, item)  # ✅ Добавили await

    if result is None:
        return {"message": "Item removed from cart (quantity was 0 or less)"}
    return result


@router.delete("/cart/items/{product_id}")
async def remove_item_from_cart(
        product_id: int,
        cart_id: str = Depends(get_current_user_or_session),
        db: Session = Depends(get_db)
):
    """Удаление товара из корзины"""
    cart_service = CartService(db)
    success = await cart_service.remove_item(cart_id, product_id)  # ✅ Добавили await

    if success:
        return {"message": "Item removed from cart"}
    else:
        raise HTTPException(status_code=404, detail="Item not found in cart")


@router.delete("/cart")
async def clear_cart(
        cart_id: str = Depends(get_current_user_or_session),
        db: Session = Depends(get_db)
):
    """Очистка корзины"""
    cart_service = CartService(db)
    success = await cart_service.clear_cart(cart_id)  # ✅ Добавили await

    if success:
        return {"message": "Cart cleared successfully"}
    else:
        return {"message": "Cart was already empty"}


@router.post("/cart/checkout")
async def checkout_cart(
        cart_id: str = Depends(get_current_user_or_session),
        db: Session = Depends(get_db)
):
    """Оформление заказа"""
    cart_service = CartService(db)
    try:
        result = await cart_service.checkout(cart_id)  # ✅ Добавили await
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))