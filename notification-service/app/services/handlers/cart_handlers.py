import logging
from typing import Dict, Any
import httpx
from datetime import datetime

from ...config import settings

logger = logging.getLogger(__name__)


class CartEventHandlers:
    """Обработчики событий корзины"""

    @staticmethod
    async def handle_item_added(event_data: Dict[str, Any]):
        """Обработка добавления товара в корзину"""
        payload = event_data.get('payload', {})
        cart_id = payload.get('cart_id')
        item = payload.get('item', {})

        logger.info(
            f"🛍️ Item added to cart {cart_id}: "
            f"Product {item.get('product_id')} x{item.get('quantity')}"
        )

        # Отправляем уведомление
        await CartEventHandlers._send_notification(
            cart_id=cart_id,
            event_type="item_added",
            message=f"Товар добавлен в корзину: {item.get('quantity')} шт."
        )

        # Обновляем аналитику
        await CartEventHandlers._update_analytics("item_added", payload)

    @staticmethod
    async def handle_item_updated(event_data: Dict[str, Any]):
        """Обработка обновления товара в корзине"""
        payload = event_data.get('payload', {})
        cart_id = payload.get('cart_id')
        item = payload.get('item', {})

        logger.info(
            f"🔄 Item updated in cart {cart_id}: "
            f"Product {item.get('product_id')} -> {item.get('quantity')} шт."
        )

        await CartEventHandlers._send_notification(
            cart_id=cart_id,
            event_type="item_updated",
            message=f"Количество товара изменено: {item.get('quantity')} шт."
        )

        await CartEventHandlers._update_analytics("item_updated", payload)

    @staticmethod
    async def handle_item_removed(event_data: Dict[str, Any]):
        """Обработка удаления товара из корзины"""
        payload = event_data.get('payload', {})
        cart_id = payload.get('cart_id')
        product_id = payload.get('product_id')

        logger.info(f"🗑️ Item removed from cart {cart_id}: Product {product_id}")

        await CartEventHandlers._send_notification(
            cart_id=cart_id,
            event_type="item_removed",
            message=f"Товар удален из корзины"
        )

        await CartEventHandlers._update_analytics("item_removed", payload)

    @staticmethod
    async def handle_cart_cleared(event_data: Dict[str, Any]):
        """Обработка очистки корзины"""
        payload = event_data.get('payload', {})
        cart_id = payload.get('cart_id')
        items_count = payload.get('items_removed', 0)

        logger.info(f"🧹 Cart cleared {cart_id}: {items_count} items removed")

        await CartEventHandlers._send_notification(
            cart_id=cart_id,
            event_type="cart_cleared",
            message=f"Корзина очищена ({items_count} товаров)"
        )

        await CartEventHandlers._update_analytics("cart_cleared", payload)

    @staticmethod
    async def handle_checkout_initiated(event_data: Dict[str, Any]):
        """Обработка начала оформления заказа"""
        payload = event_data.get('payload', {})
        cart_id = payload.get('cart_id')
        order_id = payload.get('order_id')
        total_amount = payload.get('total_amount', 0)

        logger.info(
            f"🛒 Checkout initiated for cart {cart_id}: "
            f"Order {order_id}, Amount: ${total_amount}"
        )

        await CartEventHandlers._send_notification(
            cart_id=cart_id,
            event_type="checkout_initiated",
            message=f"Заказ оформлен! Сумма: ${total_amount}"
        )

        await CartEventHandlers._update_analytics("checkout_initiated", payload)

        # Дополнительная логика для checkout
        await CartEventHandlers._process_checkout(payload)

    @staticmethod
    async def _send_notification(cart_id: str, event_type: str, message: str):
        """Отправка уведомления пользователю"""
        try:
            notification_data = {
                "cart_id": cart_id,
                "event_type": event_type,
                "message": message,
                "timestamp": datetime.utcnow().isoformat()
            }

            # В реальном проекте здесь был бы HTTP-запрос к сервису уведомлений
            logger.info(f"📧 Notification sent: {notification_data}")

            # Пример HTTP-запроса:
            # async with httpx.AsyncClient() as client:
            #     await client.post(
            #         f"{settings.email_service_url}/notifications",
            #         json=notification_data
            #     )

        except Exception as e:
            logger.error(f"❌ Failed to send notification: {e}")

    @staticmethod
    async def _update_analytics(event_type: str, payload: Dict[str, Any]):
        """Обновление аналитических данных"""
        try:
            analytics_data = {
                "event_type": event_type,
                "timestamp": datetime.utcnow().isoformat(),
                "data": payload
            }

            logger.info(f"📊 Analytics updated: {event_type}")

            # В реальном проекте здесь был бы HTTP-запрос к сервису аналитики
            # async with httpx.AsyncClient() as client:
            #     await client.post(
            #         f"{settings.analytics_service_url}/events",
            #         json=analytics_data
            #     )

        except Exception as e:
            logger.error(f"❌ Failed to update analytics: {e}")

    @staticmethod
    async def _process_checkout(payload: Dict[str, Any]):
        """Дополнительная обработка checkout"""
        try:
            # Здесь можно добавить логику:
            # - Резервирование товаров
            # - Создание записи в системе платежей
            # - Отправка данных в систему доставки

            logger.info("💳 Processing checkout logic...")

            # Имитация обработки
            await asyncio.sleep(0.1)

            logger.info("✅ Checkout processing completed")

        except Exception as e:
            logger.error(f"❌ Failed to process checkout: {e}")