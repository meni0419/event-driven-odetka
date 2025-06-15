import json
import logging
import uuid
from datetime import datetime
from typing import Dict, Any, Optional
from aiokafka import AIOKafkaProducer
from aiokafka.errors import KafkaConnectionError, KafkaTimeoutError

from ..config import settings

logger = logging.getLogger(__name__)


class KafkaClient:
    """Kafka клиент для отправки событий из cart-service"""

    def __init__(self):
        self.producer: Optional[AIOKafkaProducer] = None
        self.bootstrap_servers = settings.kafka_bootstrap_servers

    async def start_producer(self):
        """Запуск Kafka продюсера"""
        try:
            self.producer = AIOKafkaProducer(
                bootstrap_servers=self.bootstrap_servers,
                value_serializer=lambda v: json.dumps(v).encode('utf-8'),
                key_serializer=lambda k: k.encode('utf-8') if k else None,
                retry_backoff_ms=1000,
                request_timeout_ms=30000,
                acks='all',
                enable_idempotence=True
            )
            await self.producer.start()
            logger.info("✅ Kafka producer started successfully")
        except Exception as e:
            logger.error(f"❌ Failed to start Kafka producer: {e}")
            raise

    async def stop_producer(self):
        """Остановка Kafka продюсера"""
        if self.producer:
            try:
                await self.producer.stop()
                logger.info("✅ Kafka producer stopped")
            except Exception as e:
                logger.error(f"❌ Error stopping Kafka producer: {e}")

    async def publish_event(
            self,
            topic: str,
            event_type: str,
            payload: Dict[str, Any],
            key: Optional[str] = None
    ) -> bool:
        """Публикация события в Kafka"""
        if not self.producer:
            logger.error("Kafka producer not started")
            return False

        try:
            event = {
                "event_id": str(uuid.uuid4()),
                "event_type": event_type,
                "event_timestamp": datetime.utcnow().isoformat(),
                "producer_service": "cart-service",
                "payload": payload
            }

            future = await self.producer.send(topic, value=event, key=key)
            record_metadata = await future

            logger.info(
                f"✅ Event published: {event_type} to {topic} "
                f"(partition: {record_metadata.partition}, offset: {record_metadata.offset})"
            )
            return True

        except Exception as e:
            logger.error(f"❌ Error publishing event {event_type} to {topic}: {e}")
            return False


# Глобальный экземпляр клиента
kafka_client = KafkaClient()


async def get_kafka_client() -> KafkaClient:
    """Dependency для получения Kafka клиента"""
    return kafka_client