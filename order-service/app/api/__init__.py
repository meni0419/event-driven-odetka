from fastapi import APIRouter
from .routes import orders_router, payments_router

# Создаем основной API router
api_router = APIRouter(prefix="/api/v1")

# Подключаем роуты
api_router.include_router(orders_router)
api_router.include_router(payments_router)

__all__ = ["api_router"]