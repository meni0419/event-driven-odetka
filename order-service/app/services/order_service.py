import uuid
from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, func
from sqlalchemy.orm import selectinload
from datetime import datetime
from decimal import Decimal

from ..models.order import Order, OrderStatus
from ..models.order_item import OrderItem
from ..models.payment import Payment
from ..events.producer import order_event_producer
import logging

logger = logging.getLogger(__name__)


class OrderService:
    """Сервис для работы с заказами"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_order_from_cart(
            self,
            cart_id: str,
            items: List[Dict[str, Any]],
            total_amount: float,
            total_items: int,
            user_id: Optional[str] = None,
            shipping_address: Optional[str] = None
    ) -> Order:
        """Создает заказ из данных корзины"""
        try:
            # Создаем заказ
            order_id = str(uuid.uuid4())

            order = Order(
                id=order_id,
                cart_id=cart_id,
                user_id=user_id,
                status=OrderStatus.PENDING,
                total_amount=Decimal(str(total_amount)),
                final_amount=Decimal(str(total_amount)),  # Пока без скидок и налогов
                total_items=total_items,
                shipping_address=shipping_address
            )

            self.db.add(order)
            await self.db.flush()  # Получаем ID заказа

            # Создаем позиции заказа
            order_items = []
            for item_data in items:
                order_item = OrderItem(
                    order_id=order.id,
                    product_id=item_data['product_id'],
                    product_name=item_data.get('product_name', f"Product {item_data['product_id']}"),
                    quantity=item_data['quantity'],
                    unit_price=Decimal(str(item_data['price_at_add'])),
                    total_price=Decimal(str(item_data['price_at_add'] * item_data['quantity']))
                )
                order_items.append(order_item)
                self.db.add(order_item)

            await self.db.commit()
            await self.db.refresh(order)

            logger.info(f"✅ Order {order.id} created from cart {cart_id}")

            # Публикуем событие создания заказа
            await self._publish_order_created_event(order, order_items)

            return order

        except Exception as e:
            await self.db.rollback()
            logger.error(f"❌ Error creating order from cart {cart_id}: {e}")
            raise

    async def get_order(self, order_id: str) -> Optional[Order]:
        """Получает заказ по ID"""
        try:
            query = select(Order).options(
                selectinload(Order.items),
                selectinload(Order.payments)
            ).where(Order.id == order_id)

            result = await self.db.execute(query)
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"❌ Error getting order {order_id}: {e}")
            raise

    async def confirm_order(self, order_id: str) -> bool:
        """Подтверждает заказ после успешной оплаты"""
        try:
            # Обновляем статус заказа
            query = update(Order).where(Order.id == order_id).values(
                status=OrderStatus.CONFIRMED,
                confirmed_at=datetime.utcnow()
            )

            result = await self.db.execute(query)
            await self.db.commit()

            if result.rowcount > 0:
                logger.info(f"✅ Order {order_id} confirmed")

                # Получаем заказ для события
                order = await self.get_order(order_id)
                await self._publish_order_confirmed_event(order)

                return True
            else:
                logger.warning(f"⚠️ Order {order_id} not found for confirmation")
                return False

        except Exception as e:
            await self.db.rollback()
            logger.error(f"❌ Error confirming order {order_id}: {e}")
            raise

    async def cancel_order(self, order_id: str, reason: str = None) -> bool:
        """Отменяет заказ"""
        try:
            # Обновляем статус заказа
            query = update(Order).where(Order.id == order_id).values(
                status=OrderStatus.CANCELLED
            )

            result = await self.db.execute(query)
            await self.db.commit()

            if result.rowcount > 0:
                logger.info(f"❌ Order {order_id} cancelled: {reason}")

                # Получаем заказ для события
                order = await self.get_order(order_id)
                await self._publish_order_cancelled_event(order, reason)

                return True
            else:
                logger.warning(f"⚠️ Order {order_id} not found for cancellation")
                return False

        except Exception as e:
            await self.db.rollback()
            logger.error(f"❌ Error cancelling order {order_id}: {e}")
            raise

    async def update_order_status(self, order_id: str, status: OrderStatus) -> bool:
        """Обновляет статус заказа"""
        try:
            update_data = {"status": status}

            # Добавляем временные метки в зависимости от статуса
            if status == OrderStatus.SHIPPED:
                update_data["shipped_at"] = datetime.utcnow()
            elif status == OrderStatus.DELIVERED:
                update_data["delivered_at"] = datetime.utcnow()

            query = update(Order).where(Order.id == order_id).values(**update_data)

            result = await self.db.execute(query)
            await self.db.commit()

            if result.rowcount > 0:
                logger.info(f"✅ Order {order_id} status updated to {status}")

                # Публикуем соответствующее событие
                if status == OrderStatus.SHIPPED:
                    order = await self.get_order(order_id)
                    await self._publish_order_shipped_event(order)

                return True
            else:
                logger.warning(f"⚠️ Order {order_id} not found for status update")
                return False

        except Exception as e:
            await self.db.rollback()
            logger.error(f"❌ Error updating order {order_id} status: {e}")
            raise

    async def _publish_order_created_event(self, order: Order, items: List[OrderItem]):
        """Публикует событие создания заказа"""
        try:
            payload = {
                "order_id": order.id,
                "cart_id": order.cart_id,
                "user_id": order.user_id,
                "total_amount": float(order.final_amount),
                "total_items": order.total_items,
                "status": order.status.value,
                "items": [
                    {
                        "product_id": item.product_id,
                        "product_name": item.product_name,
                        "quantity": item.quantity,
                        "unit_price": float(item.unit_price),
                        "total_price": float(item.total_price)
                    } for item in items
                ],
                "created_at": order.created_at.isoformat()
            }

            await order_event_producer.publish_order_created(payload)
            logger.info(f"📤 Published order_created event for order {order.id}")

        except Exception as e:
            logger.error(f"❌ Failed to publish order_created event: {e}")

    async def _publish_order_confirmed_event(self, order: Order):
        """Публикует событие подтверждения заказа"""
        try:
            payload = {
                "order_id": order.id,
                "cart_id": order.cart_id,
                "user_id": order.user_id,
                "status": order.status.value,
                "confirmed_at": order.confirmed_at.isoformat() if order.confirmed_at else None
            }

            await order_event_producer.publish_order_confirmed(payload)
            logger.info(f"📤 Published order_confirmed event for order {order.id}")

        except Exception as e:
            logger.error(f"❌ Failed to publish order_confirmed event: {e}")

    async def _publish_order_cancelled_event(self, order: Order, reason: str = None):
        """Публикует событие отмены заказа"""
        try:
            payload = {
                "order_id": order.id,
                "cart_id": order.cart_id,
                "user_id": order.user_id,
                "status": order.status.value,
                "cancellation_reason": reason
            }

            await order_event_producer.publish_order_cancelled(payload)
            logger.info(f"📤 Published order_cancelled event for order {order.id}")

        except Exception as e:
            logger.error(f"❌ Failed to publish order_cancelled event: {e}")

    async def _publish_order_shipped_event(self, order: Order):
        """Публикует событие отправки заказа"""
        try:
            payload = {
                "order_id": order.id,
                "user_id": order.user_id,
                "status": order.status.value,
                "shipped_at": order.shipped_at.isoformat() if order.shipped_at else None,
                "shipping_address": order.shipping_address,
                "shipping_method": order.shipping_method
            }

            await order_event_producer.publish_order_shipped(payload)
            logger.info(f"📤 Published order_shipped event for order {order.id}")

        except Exception as e:
            logger.error(f"❌ Failed to publish order_shipped event: {e}")

    async def get_all_orders(
            self,
            skip: int = 0,
            limit: int = 100,
            status: Optional[OrderStatus] = None,
            user_id: Optional[str] = None
    ) -> List[Order]:
        """Получает список заказов с фильтрами и пагинацией"""
        try:
            query = select(Order).options(
                selectinload(Order.items),
                selectinload(Order.payments)
            )

            # Применяем фильтры
            if status:
                query = query.where(Order.status == status)
            if user_id:
                query = query.where(Order.user_id == user_id)

            # Добавляем сортировку и пагинацию
            query = query.order_by(Order.created_at.desc()).offset(skip).limit(limit)

            result = await self.db.execute(query)
            return result.scalars().all()

        except Exception as e:
            logger.error(f"❌ Error getting orders list: {e}")
            raise

    async def count_orders(
            self,
            status: Optional[OrderStatus] = None,
            user_id: Optional[str] = None
    ) -> int:
        """Подсчитывает общее количество заказов с фильтрами"""
        try:
            query = select(func.count(Order.id))

            # Применяем фильтры
            if status:
                query = query.where(Order.status == status)
            if user_id:
                query = query.where(Order.user_id == user_id)

            result = await self.db.execute(query)
            return result.scalar() or 0

        except Exception as e:
            logger.error(f"❌ Error counting orders: {e}")
            raise
