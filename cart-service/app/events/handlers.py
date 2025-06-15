from sqlalchemy.orm import Session
from typing import Dict, Any
import logging

from ..database import SessionLocal
from ..services.cart_service import CartService
from ..services.catalog_client import CatalogClient

logger = logging.getLogger(__name__)


class CartEventHandlers:
    """Обработчики событий для cart-service"""

    def __init__(self):
        self.catalog_client = CatalogClient()

    def get_db_session(self) -> Session:
        """Получает сессию базы данных"""
        return SessionLocal()

    async def handle_product_updated(self, payload: Dict[Any, Any], event: Dict[Any, Any]):
        """
        Обрабатывает событие обновления товара из catalog-service.
        Обновляет цены в активных корзинах, если товар еще там.
        """
        try:
            product_id = payload.get("product_id")
            changes = payload.get("changes", {})

            if not product_id:
                logger.warning("Received product_updated event without product_id")
                return

            # Если цена изменилась, обновляем корзины
            if "price" in changes:
                new_price = changes["price"]
                await self._update_price_in_carts(product_id, new_price)

            logger.info(f"Processed product_updated event for product {product_id}")

        except Exception as e:
            logger.error(f"Error handling product_updated event: {e}")

    async def handle_product_deactivated(self, payload: Dict[Any, Any], event: Dict[Any, Any]):
        """
        Обрабатывает событие деактивации товара.
        Может уведомить пользователей о недоступности товара в их корзинах.
        """
        try:
            product_id = payload.get("product_id")

            if not product_id:
                logger.warning("Received product_deactivated event without product_id")
                return

            # Находим все корзины с этим товаром
            await self._notify_about_deactivated_product(product_id)

            logger.info(f"Processed product_deactivated event for product {product_id}")

        except Exception as e:
            logger.error(f"Error handling product_deactivated event: {e}")

    async def handle_inventory_updated(self, payload: Dict[Any, Any], event: Dict[Any, Any]):
        """
        Обрабатывает событие обновления остатков товара.
        Может уведомить пользователей, если товар в их корзине стал недоступен.
        """
        try:
            product_id = payload.get("product_id")
            new_quantity = payload.get("new_quantity", 0)

            if not product_id:
                logger.warning("Received inventory_updated event without product_id")
                return

            # Если товар закончился, уведомляем пользователей
            if new_quantity == 0:
                await self._notify_about_out_of_stock(product_id)

            logger.info(f"Processed inventory_updated event for product {product_id}, new quantity: {new_quantity}")

        except Exception as e:
            logger.error(f"Error handling inventory_updated event: {e}")

    async def handle_order_created(self, payload: Dict[Any, Any], event: Dict[Any, Any]):
        """
        Обрабатывает событие создания заказа.
        Очищает корзину после успешного создания заказа.
        """
        try:
            cart_id = payload.get("cart_id")
            order_id = payload.get("order_id")

            if not cart_id:
                logger.warning("Received order_created event without cart_id")
                return

            # Очищаем корзину
            db = self.get_db_session()
            try:
                cart_service = CartService(db)
                await cart_service.clear_cart(cart_id)
                logger.info(f"Cart {cart_id} cleared after order {order_id} creation")
            finally:
                db.close()

        except Exception as e:
            logger.error(f"Error handling order_created event: {e}")

    async def _update_price_in_carts(self, product_id: int, new_price: float):
        """Обновляет цену товара во всех корзинах"""
        db = self.get_db_session()
        try:
            from ..models.cart_item import CartItem

            cart_items = db.query(CartItem).filter(CartItem.product_id == product_id).all()

            for item in cart_items:
                old_price = item.price_at_add
                price_diff = abs(new_price - old_price) / old_price * 100  # Процент изменения

                # Обновляем цену только если изменение значительное (больше 5%)
                if price_diff > 5:
                    item.price_at_add = new_price
                    db.commit()

                    # Здесь можно отправить уведомление пользователю через notification-service
                    logger.info(
                        f"Updated price for product {product_id} in cart {item.cart_id}: {old_price} -> {new_price}")

        finally:
            db.close()

    async def _notify_about_deactivated_product(self, product_id: int):
        """Уведомляет пользователей о деактивации товара в их корзинах"""
        db = self.get_db_session()
        try:
            from ..models.cart_item import CartItem

            cart_items = db.query(CartItem).filter(CartItem.product_id == product_id).all()

            for item in cart_items:
                # Здесь можно отправить уведомление через notification-service
                logger.info(f"Product {product_id} in cart {item.cart_id} has been deactivated")

        finally:
            db.close()

    async def _notify_about_out_of_stock(self, product_id: int):
        """Уведомляет пользователей о том, что товар закончился"""
        db = self.get_db_session()
        try:
            from ..models.cart_item import CartItem

            cart_items = db.query(CartItem).filter(CartItem.product_id == product_id).all()

            for item in cart_items:
                # Здесь можно отправить уведомление через notification-service
                logger.info(f"Product {product_id} in cart {item.cart_id} is out of stock")

        finally:
            db.close()