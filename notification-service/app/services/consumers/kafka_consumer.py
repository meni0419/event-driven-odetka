import json
import logging
import asyncio
from typing import Dict, Any, List, Callable
from aiokafka import AIOKafkaConsumer
from aiokafka.errors import KafkaConnectionError, KafkaTimeoutError

from ...config import settings

logger = logging.getLogger(__name__)


class KafkaEventConsumer:
    """Kafka Consumer для обработки событий"""

    def __init__(self):
        self.consumer = None
        self.handlers: Dict[str, List[Callable]] = {}
        self.running = False

    async def start(self):
        """Запуск Kafka Consumer"""
        try:
            self.consumer = AIOKafkaConsumer(
                *settings.kafka_topics,
                bootstrap_servers=settings.kafka_bootstrap_servers,
                group_id=settings.kafka_group_id,
                auto_offset_reset=settings.kafka_auto_offset_reset,
                value_deserializer=lambda m: json.loads(m.decode('utf-8'))
            )

            await self.consumer.start()
            logger.info(f"✅ Kafka consumer started for topics: {settings.kafka_topics}")

        except Exception as e:
            logger.error(f"❌ Failed to start Kafka consumer: {e}")
            raise

    async def stop(self):
        """Остановка Kafka Consumer"""
        self.running = False
        if self.consumer:
            try:
                await self.consumer.stop()
                logger.info("✅ Kafka consumer stopped")
            except Exception as e:
                logger.error(f"❌ Error stopping Kafka consumer: {e}")

    def register_handler(self, event_type: str, handler: Callable):
        """Регистрация обработчика для типа события"""
        if event_type not in self.handlers:
            self.handlers[event_type] = []
        self.handlers[event_type].append(handler)
        logger.info(f"✅ Registered handler for event type: {event_type}")

    async def consume_events(self):
        """Основной цикл потребления событий"""
        if not self.consumer:
            raise RuntimeError("Consumer not started")

        self.running = True
        logger.info("🔄 Starting event consumption...")

        try:
            async for message in self.consumer:
                if not self.running:
                    break

                try:
                    # Извлекаем данные события
                    event_data = message.value
                    topic = message.topic
                    partition = message.partition
                    offset = message.offset

                    logger.info(
                        f"📨 Received event: {event_data.get('event_type')} "
                        f"from {topic} (partition: {partition}, offset: {offset})"
                    )

                    # Обрабатываем событие
                    await self._process_event(event_data, topic)

                except Exception as e:
                    logger.error(f"❌ Error processing message: {e}")
                    # В production здесь можно добавить логику retry или DLQ

        except Exception as e:
            logger.error(f"❌ Error in consume loop: {e}")
            raise

    async def _process_event(self, event_data: Dict[str, Any], topic: str):
        """Обработка отдельного события"""
        event_type = event_data.get('event_type')

        if not event_type:
            logger.warning(f"⚠️ Event without type received from {topic}")
            return

        # Находим обработчики для этого типа события
        handlers = self.handlers.get(event_type, [])

        if not handlers:
            logger.warning(f"⚠️ No handlers registered for event type: {event_type}")
            return

        # Выполняем все обработчики параллельно
        tasks = []
        for handler in handlers:
            try:
                task = asyncio.create_task(handler(event_data))
                tasks.append(task)
            except Exception as e:
                logger.error(f"❌ Error creating task for handler {handler.__name__}: {e}")

        # Ждем выполнения всех обработчиков
        if tasks:
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # Логируем результаты
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    logger.error(f"❌ Handler {handlers[i].__name__} failed: {result}")
                else:
                    logger.debug(f"✅ Handler {handlers[i].__name__} completed successfully")


# Глобальный экземпляр consumer'а
kafka_consumer = KafkaEventConsumer()