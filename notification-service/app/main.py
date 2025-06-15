import logging
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI

from .config import settings
from .services.consumers.kafka_consumer import kafka_consumer
from .services.handlers.cart_handlers import CartEventHandlers

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Управление жизненным циклом приложения"""
    # Startup
    logger.info("🚀 Starting Notification Service...")

    try:
        # Регистрируем обработчики событий
        logger.info("📋 Registering event handlers...")
        kafka_consumer.register_handler("item_added_to_cart", CartEventHandlers.handle_item_added)
        kafka_consumer.register_handler("item_updated_in_cart", CartEventHandlers.handle_item_updated)
        kafka_consumer.register_handler("item_removed_from_cart", CartEventHandlers.handle_item_removed)
        kafka_consumer.register_handler("cart_cleared", CartEventHandlers.handle_cart_cleared)
        kafka_consumer.register_handler("checkout_initiated", CartEventHandlers.handle_checkout_initiated)

        # Запускаем Kafka consumer
        logger.info("🔌 Starting Kafka consumer...")
        await kafka_consumer.start()

        # Запускаем фоновую задачу для потребления событий
        consumer_task = asyncio.create_task(kafka_consumer.consume_events())

        logger.info("✅ Notification Service started successfully!")
        logger.info(f"🎯 Listening to topics: {settings.