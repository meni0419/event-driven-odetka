import json
import logging
import uuid
from datetime import datetime
from typing import Dict, Any, Optional
from aiokafka import AIOKafkaProducer
from aiokafka.errors import KafkaConnectionError, KafkaTimeoutError

from ..config import settings

logger = logging.getLogger(__name__)


class OrderEventProducer:
    """Producer для отправки событий из order-service"""

    def __init__(self):
        self.producer: Optional[AIOKafkaProducer] = None
        self.bootstrap_servers = settings.kafka_bootstrap_servers

    async def start(self):
        """Запуск Kafka продюсера"""
        try:
            self.producer = AIOKafkaProducer(
                bootstrap_servers=self.bootstrap_servers,
                value_serializer=lambda v: json.dumps(v).encode('utf-8'),
                key_serializer=lambda k: k.encode('utf-8') if k else None,
                # УБИРАЕМ неправильный параметр max_in_flight_requests_per_connection
                retry_backoff_ms=1000,
                request_timeout_ms=30000,
                compression_type="gzip",
                acks='all',
                enable_idempotence=True
            )
            await self.producer.start()
            logger.info("✅ Order event producer started successfully")
        except Exception as e:
            logger.error(f"❌ Failed to start order event producer: {e}")
            raise

    async def stop(self):
        """Остановка Kafka продюсера"""
        if self.producer:
            try:
                await self.producer.stop()
                logger.info("✅ Order event producer stopped")
            except Exception as e:
                logger.error(f"❌ Error stopping order event producer: {e}")

    async def publish_event(
            self,
            topic: str,
            event_type: str,
            payload: Dict[str, Any],
            key: Optional[str] = None
    ) -> bool:
        """
        Публикация события в Kafka

        Args:
            topic: Название топика
            event_type: Тип события
            payload: Данные события
            key: Ключ для партиционирования (опционально)

        Returns:
            bool: True если успешно отправлено
        """
        if not self.producer:
            logger.error("Order event producer not started")
            return False

        try:
            # Создаем стандартное событие
            event = {
                "event_id": str(uuid.uuid4()),
                "event_type": event_type,
                "event_timestamp": datetime.utcnow().isoformat(),
                "producer_service": "order-service",
                "payload": payload
            }

            # Отправляем событие
            future = await self.producer.send(topic, value=event, key=key)
            record_metadata = await future

            logger.info(
                f"✅ Event published: {event_type} to {topic} "
                f"(partition: {record_metadata.partition}, offset: {record_metadata.offset})"
            )
            return True

        except KafkaTimeoutError:
            logger.error(f"❌ Timeout publishing event {event_type} to {topic}")
            return False
        except KafkaConnectionError:
            logger.error(f"❌ Connection error publishing event {event_type} to {topic}")
            return False
        except Exception as e:
            logger.error(f"❌ Error publishing event {event_type} to {topic}: {e}")
            return False

    # Методы для конкретных событий заказов
    async def order_created(self, order_data: Dict[str, Any]) -> bool:
        """Событие создания заказа"""
        return await self.publish_event(
            topic="order.created",
            event_type="order_created",
            payload=order_data,
            key=str(order_data.get("order_id"))
        )

    async def order_confirmed(self, order_data: Dict[str, Any]) -> bool:
        """Событие подтверждения заказа"""
        return await self.publish_event(
            topic="order.confirmed",
            event_type="order_confirmed",
            payload=order_data,
            key=str(order_data.get("order_id"))
        )

    async def order_cancelled(self, order_data: Dict[str, Any]) -> bool:
        """Событие отмены заказа"""
        return await self.publish_event(
            topic="order.cancelled",
            event_type="order_cancelled",
            payload=order_data,
            key=str(order_data.get("order_id"))
        )

    async def payment_requested(self, payment_data: Dict[str, Any]) -> bool:
        """Событие запроса платежа"""
        return await self.publish_event(
            topic="payment.requested",
            event_type="payment_requested",
            payload=payment_data,
            key=str(payment_data.get("order_id"))
        )

    async def publish_order_created(self, order_data: Dict[str, Any]) -> bool:
        """Событие создания заказа"""
        return await self.publish_event(
            topic="order.created",
            event_type="order_created",
            payload=order_data,
            key=str(order_data.get("order_id"))
        )

    async def publish_payment_requested(self, payment_data: Dict[str, Any]) -> bool:
        """Событие запроса платежа"""
        return await self.publish_event(
            topic="payment.requested",
            event_type="payment_requested",
            payload=payment_data,
            key=str(payment_data.get("order_id"))
        )


# Глобальный экземпляр продюсера
order_event_producer = OrderEventProducer()


async def get_order_event_producer() -> OrderEventProducer:
    """Dependency для получения event producer"""
    return order_event_producer
