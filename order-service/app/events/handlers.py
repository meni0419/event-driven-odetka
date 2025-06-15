import logging
from typing import Dict, Any
from datetime import datetime

logger = logging.getLogger(__name__)


class OrderEventHandlers:
    """Обработчики событий для order-service"""

    @staticmethod
    async def handle_checkout_initiated(event_data: Dict[str, Any]):
        """
        Обрабатывает событие начала checkout из cart-service.
        Создает новый заказ.
        """
        try:
            # Импортируем только когда нужно, чтобы избежать circular import
            from ..database import AsyncSessionLocal
            from ..services.order_service import OrderService
            from ..services.payment_service import PaymentService
            from ..models.payment import PaymentStatus

            payload = event_data.get('payload', {})
            cart_id = payload.get('cart_id')
            items = payload.get('items', [])
            total_amount = payload.get('total_amount', 0)
            total_items = payload.get('total_items', 0)

            logger.info(f"🛒 Processing checkout for cart {cart_id}")

            if not cart_id or not items:
                logger.warning("⚠️ Invalid checkout event: missing cart_id or items")
                return

            # Создаем заказ
            async with AsyncSessionLocal() as db:
                order_service = OrderService(db)

                order = await order_service.create_order_from_cart(
                    cart_id=cart_id,
                    items=items,
                    total_amount=total_amount,
                    total_items=total_items
                )

                logger.info(f"✅ Order {order.id} created from cart {cart_id}")

                # Запрашиваем обработку платежа
                payment_service = PaymentService(db)
                await payment_service.request_payment(order)

        except Exception as e:
            logger.error(f"❌ Error handling checkout_initiated: {e}")

    @staticmethod
    async def handle_payment_processed(event_data: Dict[str, Any]):
        """
        Обрабатывает событие успешной обработки платежа.
        Подтверждает заказ.
        """
        try:
            # Импортируем только когда нужно
            from ..database import AsyncSessionLocal
            from ..services.order_service import OrderService
            from ..services.payment_service import PaymentService
            from ..models.payment import PaymentStatus

            payload = event_data.get('payload', {})
            order_id = payload.get('order_id')
            payment_id = payload.get('payment_id')
            transaction_id = payload.get('transaction_id')

            logger.info(f"💳 Processing successful payment for order {order_id}")

            if not order_id:
                logger.warning("⚠️ Invalid payment event: missing order_id")
                return

            async with AsyncSessionLocal() as db:
                order_service = OrderService(db)
                payment_service = PaymentService(db)

                # Обновляем статус платежа
                await payment_service.update_payment_status(
                    payment_id=payment_id,
                    status=PaymentStatus.COMPLETED,
                    transaction_id=transaction_id
                )

                # Подтверждаем заказ
                await order_service.confirm_order(order_id)

                logger.info(f"✅ Order {order_id} confirmed after successful payment")

        except Exception as e:
            logger.error(f"❌ Error handling payment_processed: {e}")

    @staticmethod
    async def handle_payment_failed(event_data: Dict[str, Any]):
        """
        Обрабатывает событие неудачной обработки платежа.
        Отменяет заказ.
        """
        try:
            # Импортируем только когда нужно
            from ..database import AsyncSessionLocal
            from ..services.order_service import OrderService
            from ..services.payment_service import PaymentService
            from ..models.payment import PaymentStatus

            payload = event_data.get('payload', {})
            order_id = payload.get('order_id')
            payment_id = payload.get('payment_id')
            failure_reason = payload.get('failure_reason', 'Payment failed')

            logger.info(f"❌ Processing failed payment for order {order_id}")

            if not order_id:
                logger.warning("⚠️ Invalid payment event: missing order_id")
                return

            async with AsyncSessionLocal() as db:
                order_service = OrderService(db)
                payment_service = PaymentService(db)

                # Обновляем статус платежа
                await payment_service.update_payment_status(
                    payment_id=payment_id,
                    status=PaymentStatus.FAILED,
                    failure_reason=failure_reason
                )

                # Отменяем заказ
                await order_service.cancel_order(order_id, reason=failure_reason)

                logger.info(f"❌ Order {order_id} cancelled due to payment failure")

        except Exception as e:
            logger.error(f"❌ Error handling payment_failed: {e}")