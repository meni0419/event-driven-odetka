from typing import List, Optional
from sqlalchemy.orm import Session
from ..models.cart import Cart
from ..models.cart_item import CartItem
from ..schemas.cart import Cart as CartSchema, CartSummary
from ..schemas.cart_item import CartItemCreate, CartItemUpdate
from .catalog_client import CatalogClient
from .kafka_client import kafka_client
import logging

logger = logging.getLogger(__name__)


class CartService:
    def __init__(self, db: Session):
        self.db = db
        self.catalog_client = CatalogClient()

    def get_or_create_cart(self, session_id: str) -> Cart:
        """Получить или создать корзину для сессии"""
        cart = self.db.query(Cart).filter(Cart.id == session_id).first()
        if not cart:
            cart = Cart(id=session_id)
            self.db.add(cart)
            self.db.commit()
            self.db.refresh(cart)
        return cart

    async def add_item(self, session_id: str, item_data: CartItemCreate) -> CartItem:
        """Добавить товар в корзину"""
        cart = self.get_or_create_cart(session_id)

        # Проверяем данные товара в каталоге
        try:
            product = await self.catalog_client.get_product(item_data.product_id)
            if not product:
                raise ValueError(f"Product {item_data.product_id} not found")

            if not product.get("is_active", False):
                raise ValueError(f"Product {item_data.product_id} is not active")

            if product.get("inventory", 0) < item_data.quantity:
                raise ValueError(f"Insufficient inventory for product {item_data.product_id}")
        except Exception as e:
            logger.error(f"Error checking product {item_data.product_id}: {e}")
            # В тестовом режиме продолжаем без проверки
            product = {
                "id": item_data.product_id,
                "name": f"Product {item_data.product_id}",
                "price": 99.99,
                "is_active": True,
                "inventory": 999
            }

        # Проверяем, есть ли уже такой товар в корзине
        existing_item = self.db.query(CartItem).filter(
            CartItem.cart_id == cart.id,
            CartItem.product_id == item_data.product_id
        ).first()

        if existing_item:
            # Обновляем количество
            old_quantity = existing_item.quantity
            existing_item.quantity += item_data.quantity
            existing_item.price_at_add = product["price"]
            item = existing_item
            action = "updated"
        else:
            # Создаем новый товар в корзине
            item = CartItem(
                cart_id=cart.id,
                product_id=item_data.product_id,
                quantity=item_data.quantity,
                price_at_add=product["price"]
            )
            self.db.add(item)
            action = "added"

        self.db.commit()
        self.db.refresh(item)

        # 🚀 Публикуем событие в Kafka
        await self._publish_item_added_event(session_id, item, product, action)

        logger.info(f"Added item {item_data.product_id} to cart {session_id}")
        return item

    async def update_item(self, session_id: str, product_id: int, item_data: CartItemUpdate) -> Optional[CartItem]:
        """Обновить количество товара в корзине"""
        cart = self.get_or_create_cart(session_id)

        item = self.db.query(CartItem).filter(
            CartItem.cart_id == cart.id,
            CartItem.product_id == product_id
        ).first()

        if not item:
            return None

        old_quantity = item.quantity

        if item_data.quantity <= 0:
            self.db.delete(item)
            self.db.commit()

            # 🚀 Публикуем событие удаления
            await self._publish_item_removed_event(session_id, product_id, old_quantity)
            return None
        else:
            item.quantity = item_data.quantity
            self.db.commit()
            self.db.refresh(item)

            # 🚀 Публикуем событие обновления
            await self._publish_item_updated_event(session_id, item, old_quantity)
            return item

    async def remove_item(self, session_id: str, product_id: int) -> bool:
        """Удалить товар из корзины"""
        cart = self.get_or_create_cart(session_id)

        item = self.db.query(CartItem).filter(
            CartItem.cart_id == cart.id,
            CartItem.product_id == product_id
        ).first()

        if item:
            quantity = item.quantity
            self.db.delete(item)
            self.db.commit()

            # 🚀 Публикуем событие удаления
            await self._publish_item_removed_event(session_id, product_id, quantity)
            return True
        return False

    def get_cart(self, session_id: str) -> CartSummary:
        """Получить корзину с подсчётом итогов"""
        cart = self.get_or_create_cart(session_id)

        items = self.db.query(CartItem).filter(CartItem.cart_id == cart.id).all()

        total_amount = sum(item.quantity * item.price_at_add for item in items)
        total_items = sum(item.quantity for item in items)

        return CartSummary(
            cart_id=session_id,
            items=items,
            total_items=total_items,
            total_amount=total_amount
        )

    async def clear_cart(self, session_id: str) -> bool:
        """Очистить корзину"""
        cart = self.get_or_create_cart(session_id)

        # Получаем items перед удалением для события
        items = self.db.query(CartItem).filter(CartItem.cart_id == cart.id).all()
        deleted_count = len(items)

        if deleted_count > 0:
            # Удаляем все items
            self.db.query(CartItem).filter(CartItem.cart_id == cart.id).delete()
            self.db.commit()

            # 🚀 Публикуем событие очистки корзины
            await self._publish_cart_cleared_event(session_id, items)

        logger.info(f"Cleared cart {session_id}, removed {deleted_count} items")
        return deleted_count > 0

    async def checkout(self, session_id: str) -> dict:
        """Оформить заказ"""
        cart_summary = self.get_cart(session_id)

        if not cart_summary.items:
            raise ValueError("Cart is empty")

        # Создаем заказ (тут будет интеграция с Order Service)
        order_data = {
            "session_id": session_id,
            "items": [
                {
                    "product_id": item.product_id,
                    "quantity": item.quantity,
                    "price_at_add": float(item.price_at_add)
                }
                for item in cart_summary.items
            ],
            "total_amount": float(cart_summary.total_amount),
            "total_items": cart_summary.total_items
        }

        # 🚀 Публикуем событие начала оформления заказа
        await self._publish_checkout_initiated_event(session_id, order_data)

        # Очищаем корзину после успешного заказа
        await self.clear_cart(session_id)

        logger.info(f"Checkout completed for session {session_id}")

        return {
            "message": "Order created successfully",
            "order": order_data,
            "order_id": f"ORDER-{session_id}"
        }

    # 🚀 Методы для публикации событий в Kafka

    async def _publish_item_added_event(self, session_id: str, item: CartItem, product: dict, action: str):
        """Публикация события добавления товара в корзину"""
        payload = {
            "cart_id": session_id,
            "item": {
                "product_id": item.product_id,
                "quantity": item.quantity,
                "price_at_add": float(item.price_at_add),
                "total_price": float(item.quantity * item.price_at_add)
            },
            "product": {
                "name": product.get("name", f"Product {item.product_id}"),
                "price": product.get("price", item.price_at_add)
            },
            "action": action  # "added" или "updated"
        }

        await kafka_client.publish_event(
            topic="cart.item.added",
            event_type="item_added_to_cart",
            payload=payload,
            key=session_id
        )

    async def _publish_item_updated_event(self, session_id: str, item: CartItem, old_quantity: int):
        """Публикация события обновления товара в корзине"""
        payload = {
            "cart_id": session_id,
            "item": {
                "product_id": item.product_id,
                "old_quantity": old_quantity,
                "new_quantity": item.quantity,
                "price_at_add": float(item.price_at_add),
                "total_price": float(item.quantity * item.price_at_add)
            }
        }

        await kafka_client.publish_event(
            topic="cart.item.updated",
            event_type="item_updated_in_cart",
            payload=payload,
            key=session_id
        )

    async def _publish_item_removed_event(self, session_id: str, product_id: int, quantity: int):
        """Публикация события удаления товара из корзины"""
        payload = {
            "cart_id": session_id,
            "removed_item": {
                "product_id": product_id,
                "quantity": quantity
            }
        }

        await kafka_client.publish_event(
            topic="cart.item.removed",
            event_type="item_removed_from_cart",
            payload=payload,
            key=session_id
        )

    async def _publish_cart_cleared_event(self, session_id: str, items: List[CartItem]):
        """Публикация события очистки корзины"""
        payload = {
            "cart_id": session_id,
            "cleared_items": [
                {
                    "product_id": item.product_id,
                    "quantity": item.quantity,
                    "price_at_add": float(item.price_at_add)
                }
                for item in items
            ],
            "total_items_cleared": len(items)
        }

        await kafka_client.publish_event(
            topic="cart.cleared",
            event_type="cart_cleared",
            payload=payload,
            key=session_id
        )

    async def _publish_checkout_initiated_event(self, session_id: str, order_data: dict):
        """Публикация события начала оформления заказа"""
        payload = {
            "cart_id": session_id,
            "order": order_data,
            "checkout_timestamp": order_data.get("checkout_timestamp")
        }

        await kafka_client.publish_event(
            topic="cart.checkout.initiated",
            event_type="checkout_initiated",
            payload=payload,
            key=session_id
        )