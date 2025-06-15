import uuid
from typing import Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from datetime import datetime
from decimal import Decimal

from ..models.payment import Payment, PaymentStatus, PaymentMethod
from ..models.order import Order
from ..events.producer import order_event_producer
import logging

logger = logging.getLogger(__name__)


class PaymentService:
    """Сервис для работы с платежами"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def request_payment(
            self,
            order: Order,
            method: PaymentMethod = PaymentMethod.CARD
    ) -> Payment:
        """Создает запрос на оплату заказа"""
        try:
            payment_id = str(uuid.uuid4())

            payment = Payment(
                id=payment_id,
                order_id=order.id,
                amount=order.final_amount,
                method=method,
                status=PaymentStatus.PENDING
            )

            self.db.add(payment)
            await self.db.commit()
            await self.db.refresh(payment)

            logger.info(f"💳 Payment {payment.id} requested for order {order.id}")

            # Публикуем событие запроса на оплату
            await self._publish_payment_requested_event(payment, order)

            return payment

        except Exception as e:
            await self.db.rollback()
            logger.error(f"❌ Error requesting payment for order {order.id}: {e}")
            raise

    async def update_payment_status(
            self,
            payment_id: str,
            status: PaymentStatus,
            transaction_id: Optional[str] = None,
            failure_reason: Optional[str] = None,
            provider_response: Optional[str] = None
    ) -> bool:
        """Обновляет статус платежа"""
        try:
            update_data = {
                "status": status,
                "processed_at": datetime.utcnow()
            }

            if transaction_id:
                update_data["external_transaction_id"] = transaction_id
            if failure_reason:
                update_data["failure_reason"] = failure_reason
            if provider_response:
                update_data["provider_response"] = provider_response

            query = update(Payment).where(Payment.id == payment_id).values(**update_data)

            result = await self.db.execute(query)
            await self.db.commit()

            if result.rowcount > 0:
                logger.info(f"✅ Payment {payment_id} status updated to {status}")
                return True
            else:
                logger.warning(f"⚠️ Payment {payment_id} not found for status update")
                return False

        except Exception as e:
            await self.db.rollback()
            logger.error(f"❌ Error updating payment {payment_id} status: {e}")
            raise

    async def get_payment(self, payment_id: str) -> Optional[Payment]:
        """Получает платеж по ID"""
        try:
            query = select(Payment).where(Payment.id == payment_id)
            result = await self.db.execute(query)
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"❌ Error getting payment {payment_id}: {e}")
            raise

    async def get_payments_for_order(self, order_id: str) -> list[Payment]:
        """Получает все платежи для заказа"""
        try:
            query = select(Payment).where(Payment.order_id == order_id)
            result = await self.db.execute(query)
            return result.scalars().all()
        except Exception as e:
            logger.error(f"❌ Error getting payments for order {order_id}: {e}")
            raise

    async def process_mock_payment(
            self,
            payment_id: str,
            success: bool = True,
            transaction_id: Optional[str] = None
    ) -> bool:
        """
        Мок-обработка платежа для тестирования.
        В реальном проекте здесь был бы вызов внешнего платежного API.
        """
        try:
            if success:
                # Успешная оплата
                return await self.update_payment_status(
                    payment_id=payment_id,
                    status=PaymentStatus.COMPLETED,
                    transaction_id=transaction_id or f"mock_txn_{uuid.uuid4().hex[:8]}"
                )
            else:
                # Неудачная оплата
                return await self.update_payment_status(
                    payment_id=payment_id,
                    status=PaymentStatus.FAILED,
                    failure_reason="Mock payment failure for testing"
                )

        except Exception as e:
            logger.error(f"❌ Error processing mock payment {payment_id}: {e}")
            raise

    async def _publish_payment_requested_event(self, payment: Payment, order: Order):
        """Публикует событие запроса на оплату"""
        try:
            payload = {
                "payment_id": payment.id,
                "order_id": order.id,
                "amount": float(payment.amount),
                "currency": payment.currency,
                "method": payment.method.value,
                "status": payment.status.value,
                "cart_id": order.cart_id,
                "user_id": order.user_id,
                "created_at": payment.created_at.isoformat()
            }

            await order_event_producer.publish_payment_requested(payload)
            logger.info(f"📤 Published payment_requested event for payment {payment.id}")

        except Exception as e:
            logger.error(f"❌ Failed to publish payment_requested event: {e}")