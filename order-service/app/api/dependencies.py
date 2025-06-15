from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from typing import AsyncGenerator

from ..database import get_db
from ..services.order_service import OrderService
from ..services.payment_service import PaymentService
from ..services.catalog_client import CatalogClient


async def get_order_service(
    db: AsyncSession = Depends(get_db)
) -> OrderService:
    """Dependency для получения OrderService"""
    return OrderService(db)


async def get_payment_service(
    db: AsyncSession = Depends(get_db)
) -> PaymentService:
    """Dependency для получения PaymentService"""
    return PaymentService(db)


def get_catalog_client() -> CatalogClient:
    """Dependency для получения CatalogClient"""
    return CatalogClient()