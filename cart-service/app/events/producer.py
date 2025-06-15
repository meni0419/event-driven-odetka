import json
import uuid
from datetime import datetime
from typing import Dict, Any
from aiokafka import AIOKafkaProducer
from aiokafka.errors import KafkaError
import logging

from ..config import settings

logger = logging.getLogger(__name__)

class EventProducer:
    def __init__(self):
        self.producer = None
        self.bootstrap_servers = settings.kafka_bootstrap_servers

    async def start(self):
        """Инициализирует и запускает Kafka producer"""
        try:
            self.producer = AIOKafkaProducer(
                bootstrap_servers=self.bootstrap_servers,
                value_serializer=lambda v: json.dumps(v).encode('utf-8'),
                key_serializer=lambda k: k.encode('utf-8') if k else None,
                retry_backoff_ms=500,
                request_timeout_ms=30000,
                max_in_flight_requests_per_connection=1,  # Гарантирует порядок сообщений
                enable_idempotence=True  # Предотвращает дублирование
            )
            await self.producer.start()
            logger.info("Kafka producer started successfully")
        except Exception as e:
            logger.error(f"Failed to start Kafka producer: {e}")
            raise

    async def stop(self):
        """Останавливает Kafka producer"""
        if self.producer:
            try:
                await self.producer.stop()
                logger.info("Kafka producer stopped")
            except Exception as e:
                logger.error(f"Error stopping Kafka producer: {e}")

    async def _publish_event(self, topic: str, event_data: Dict[Any, Any], key: str = None):
        """Базовый метод для публикации событий"""
        if not self.producer:
            logger.warning("Producer not initialized, attempting to start...")
            await self.start()

        # Добавляем обязательные поля события
        event = {
            "event_id": str(uuid.uuid4()),
            "event_type": topic,
            "event_timestamp": datetime.utcnow().isoformat(),
            "producer_service": "cart-service",
            "payload": event_data
        }

        try:
            await self.producer.send_and_wait(
                topic=topic,
                value=event,
                key=key
            )
            logger.info(f"Event published to topic '{topic}': {event['event_id']}")
        except KafkaError as e:
            logger.error(f"Failed to publish event to topic '{topic}': {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error publishing event to topic '{topic}': {e}")
            raise

    async def publish_item_added_to_cart(self, data: Dict[Any, Any]):
        """Публикует событие добавления товара в корзину"""
        await self._publish_event(
            topic="item_added_to_cart",
            event_data=data,
            key=data.get("cart_id")  # Используем cart_id как ключ для партиционирования
        )

    async def publish_cart_updated(self, data: Dict[Any, Any]):
        """Публикует событие изменения корзины"""
        await self._publish_event(
            topic="cart_updated",
            event_data=data,
            key=data.get("cart_id")
        )

    async def publish_cart_checkout_initiated(self, data: Dict[Any, Any]):
        """Публикует событие начала оформления заказа"""
        await self._publish_event(
            topic="cart_checkout_initiated",
            event_data=data,
            key=data.get("cart_id")
        )

    async def publish_cart_cleared(self, data: Dict[Any, Any]):
        """Публикует событие очистки корзины"""
        await self._publish_event(
            topic="cart_cleared",
            event_data=data,
            key=data.get("cart_id")
        )