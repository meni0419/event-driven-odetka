from fastapi import APIRouter, Depends, HTTPException
from typing import List

from ...schemas.payment import PaymentResponse, PaymentUpdate
from ...services.payment_service import PaymentService
from ...api.dependencies import get_payment_service
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/payments", tags=["payments"])


@router.get("/{payment_id}", response_model=PaymentResponse)
async def get_payment(
        payment_id: str,
        payment_service: PaymentService = Depends(get_payment_service)
):
    """Получить платеж по ID"""
    try:
        payment = await payment_service.get_payment(payment_id)

        if not payment:
            raise HTTPException(status_code=404, detail="Payment not found")

        return payment
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error getting payment {payment_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.patch("/{payment_id}", response_model=PaymentResponse)
async def update_payment(
        payment_id: str,
        payment_update: PaymentUpdate,
        payment_service: PaymentService = Depends(get_payment_service)
):
    """Обновить платеж (используется внешним payment service)"""
    try:
        # Обновляем платеж
        success = await payment_service.update_payment_status(
            payment_id=payment_id,
            status=payment_update.status,
            transaction_id=payment_update.external_transaction_id,
            failure_reason=payment_update.failure_reason
        )

        if not success:
            raise HTTPException(status_code=404, detail="Payment not found")

        # Возвращаем обновленный платеж
        updated_payment = await payment_service.get_payment(payment_id)
        return updated_payment

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error updating payment {payment_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")