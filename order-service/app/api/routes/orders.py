from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from ...database import get_db
from ...schemas.order import OrderResponse, OrderListResponse
from ...schemas.payment import PaymentMockRequest
from ...services.order_service import OrderService
from ...services.payment_service import PaymentService
from ...models.order import OrderStatus
from ...api.dependencies import get_order_service, get_payment_service
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/orders", tags=["orders"])


@router.get("/", response_model=OrderListResponse)
async def get_orders(
        page: int = Query(1, ge=1, description="Номер страницы"),
        per_page: int = Query(10, ge=1, le=100, description="Количество на странице"),
        status: Optional[OrderStatus] = Query(None, description="Фильтр по статусу"),
        user_id: Optional[str] = Query(None, description="Фильтр по пользователю"),
        order_service: OrderService = Depends(get_order_service)
):
    """Получить список заказов с пагинацией и фильтрами"""
    try:
        # Получаем реальные заказы из сервиса
        orders = await order_service.get_all_orders(
            skip=(page - 1) * per_page,
            limit=per_page,
            status=status,
            user_id=user_id
        )

        # Получаем общее количество
        total = await order_service.count_orders(status=status, user_id=user_id)

        return OrderListResponse(
            orders=orders,
            total=total,
            page=page,
            per_page=per_page,
            total_pages=(total + per_page - 1) // per_page
        )
    except Exception as e:
        logger.error(f"❌ Error getting orders: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/{order_id}", response_model=OrderResponse)
async def get_order(
        order_id: str,
        order_service: OrderService = Depends(get_order_service)
):
    """Получить заказ по ID"""
    try:
        order = await order_service.get_order(order_id)

        if not order:
            raise HTTPException(status_code=404, detail="Order not found")

        return order
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error getting order {order_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.patch("/{order_id}/status")
async def update_order_status(
        order_id: str,
        new_status: OrderStatus,
        order_service: OrderService = Depends(get_order_service)
):
    """Обновить статус заказа"""
    try:
        success = await order_service.update_order_status(order_id, new_status)

        if not success:
            raise HTTPException(status_code=404, detail="Order not found")

        return {"message": f"Order status updated to {new_status.value}"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error updating order {order_id} status: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/{order_id}/cancel")
async def cancel_order(
        order_id: str,
        reason: Optional[str] = None,
        order_service: OrderService = Depends(get_order_service)
):
    """Отменить заказ"""
    try:
        success = await order_service.cancel_order(order_id, reason)

        if not success:
            raise HTTPException(status_code=404, detail="Order not found")

        return {"message": "Order cancelled successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error cancelling order {order_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/{order_id}/confirm")
async def confirm_order(
        order_id: str,
        order_service: OrderService = Depends(get_order_service)
):
    """Подтвердить заказ (обычно после оплаты)"""
    try:
        success = await order_service.confirm_order(order_id)

        if not success:
            raise HTTPException(status_code=404, detail="Order not found")

        return {"message": "Order confirmed successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error confirming order {order_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/{order_id}/payments")
async def get_order_payments(
        order_id: str,
        payment_service: PaymentService = Depends(get_payment_service)
):
    """Получить все платежи для заказа"""
    try:
        payments = await payment_service.get_payments_for_order(order_id)
        return payments
    except Exception as e:
        logger.error(f"❌ Error getting payments for order {order_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


# Endpoint для тестирования - мок-обработка платежа
@router.post("/{order_id}/mock-payment")
async def process_mock_payment(
        order_id: str,
        payment_request: PaymentMockRequest,
        payment_service: PaymentService = Depends(get_payment_service)
):
    """
    Мок-обработка платежа для тестирования.
    В реальном проекте этого endpoint'а не было бы.
    """
    try:
        # Находим pending платеж для заказа
        payments = await payment_service.get_payments_for_order(order_id)
        pending_payment = next((p for p in payments if p.status.value == "pending"), None)

        if not pending_payment:
            raise HTTPException(status_code=404, detail="No pending payment found for this order")

        # Обрабатываем мок-платеж
        success = await payment_service.process_mock_payment(
            payment_id=pending_payment.id,
            success=payment_request.success,
            transaction_id=payment_request.transaction_id
        )

        if success:
            status = "completed" if payment_request.success else "failed"
            return {"message": f"Mock payment {status}"}
        else:
            raise HTTPException(status_code=400, detail="Failed to process payment")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error processing mock payment for order {order_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
