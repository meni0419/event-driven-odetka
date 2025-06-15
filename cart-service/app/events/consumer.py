import json
import asyncio
from typing import Dict, Any, Callable
from aiokafka import AIOKafkaConsumer
from aiokafka.errors import KafkaError
import logging

from ..config import settings

logger = logging.getLogger(__name__)


class EventConsumer:
    def __init__(self):
        self.consumer = None
        self.bootstrap_servers = settings.kafka_bootstrap_servers
        self.group_id = settings.kafka_group_id
        self.handlers: Dict[str, Callable] = {}
        self.running = False

    async def start(self, topics: list[str]):
        """Инициализирует и запускает Kafka consumer"""
        try:
            self.consumer = AIOKafkaConsumer(
                *topics,
                bootstrap_servers=self.bootstrap_servers,
                group_id=self.group_id,
                value_deserializer=lambda m: json.loads(m.decode('utf-8')),
                key_deserializer=lambda k: k.decode('utf-8') if k else None,
                auto_offset_reset='earliest',  # Читаем с начала при первом запуске
                enable_auto_commit=False,  # Ручное подтверждение обработки
                max_poll_records=10,  # Обрабатываем по 10 сообщений за раз
                session_timeout_ms=30000,
                heartbeat_interval_ms=10000
            )
            await self.consumer.start()
            logger.info(f"Kafka consumer started for topics: {topics}")
        except Exception as e:
            logger.error(f"Failed to start Kafka consumer: {e}")
            raise

    async def stop(self):
        """Останавливает Kafka consumer"""
        self.running = False
        if self.consumer:
            try:
                await self.consumer.stop()
                logger.info("Kafka consumer stopped")
            except Exception as e:
                logger.error(f"Error stopping Kafka consumer: {e}")

    def register_handler(self, event_type: str, handler: Callable):
        """Регистрирует обработчик для определенного типа событий"""
        self.handlers[event_type] = handler
        logger.info(f"Registered handler for event type: {event_type}")

    async def consume_messages(self):
        """Основной цикл обработки сообщений"""
        self.running = True
        logger.info("Starting message consumption...")

        try:
            while self.running:
                try:
                    # Получаем пакет сообщений
                    msg_pack = await self.consumer.getmany(timeout_ms=1000)

                    if not msg_pack:
                        continue

                    # Обрабатываем сообщения по топикам
                    for topic_partition, messages in msg_pack.items():
                        for message in messages:
                            await self._process_message(message)

                    # Подтверждаем обработку всех сообщений в пакете
                    await self.consumer.commit()

                except KafkaError as e:
                    logger.error(f"Kafka error during message consumption: {e}")
                    await asyncio.sleep(5)  # Пауза перед повторной попыткой
                except Exception as e:
                    logger.error(f"Unexpected error during message consumption: {e}")
                    await asyncio.sleep(1)

        except Exception as e:
            logger.error(f"Fatal error in message consumption loop: {e}")
        finally:
            await self.stop()

    async def _process_message(self, message):
        """Обрабатывает одно сообщение"""
        try:
            event = message.value
            event_type = event.get("event_type")
            event_id = event.get("event_id")
            payload = event.get("payload", {})

            logger.info(f"Processing event {event_id} of type {event_type}")

            # Находим обработчик для этого типа события
            handler = self.handlers.get(event_type)
            if handler:
                # Вызываем обработчик
                await handler(payload, event)
                logger.info(f"Successfully processed event {event_id}")
            else:
                logger.warning(f"No handler registered for event type: {event_type}")

        except json.JSONDecodeError as e:
            logger.error(f"Failed to decode message: {e}")
        except Exception as e:
            logger.error(f"Error processing message: {e}")
            # В production здесь может быть логика отправки в Dead Letter Queue

    async def health_check(self) -> bool:
        """Проверка состояния consumer'а"""
        try:
            if not self.consumer:
                return False

            # Можно добавить дополнительные проверки
            return self.running and not self.consumer._closed
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return False