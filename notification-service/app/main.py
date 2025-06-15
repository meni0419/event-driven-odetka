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
        logger.info(f"🎯 Listening to topics: {settings.kafka_topics}")

        yield  # Приложение работает

    except Exception as e:
        logger.error(f"❌ Failed to start Notification Service: {e}")
        raise

    # Shutdown
    logger.info("🛑 Shutting down Notification Service...")

    # Останавливаем consumer
    try:
        await kafka_consumer.stop()
        consumer_task.cancel()
        try:
            await consumer_task
        except asyncio.CancelledError:
            pass
    except Exception as e:
        logger.error(f"❌ Error stopping Kafka consumer: {e}")

    logger.info("✅ Notification Service shut down successfully!")


# Создаем FastAPI приложение
app = FastAPI(
    title=settings.app_name,
    description="Микросервис обработки событий и уведомлений",
    version="1.0.0",
    debug=settings.debug,
    lifespan=lifespan
)


# Health check endpoint
@app.get("/health")
async def health_check():
    """Проверка здоровья сервиса"""
    return {
        "status": "healthy",
        "service": settings.app_name,
        "kafka_consumer": "running" if kafka_consumer.running else "stopped",
        "subscribed_topics": settings.kafka_topics,
        "version": "1.0.0"
    }


@app.get("/")
async def root():
    """Корневой endpoint"""
    return {
        "service": settings.app_name,
        "version": "1.0.0",
        "status": "running",
        "description": "Event-driven notification service",
        "subscribed_topics": settings.kafka_topics,
        "endpoints": {
            "health": "/health",
            "docs": "/docs"
        }
    }


# Endpoint для получения статистики обработанных событий
@app.get("/stats")
async def get_stats():
    """Статистика обработанных событий"""
    return {
        "consumer_status": "running" if kafka_consumer.running else "stopped",
        "registered_handlers": list(kafka_consumer.handlers.keys()),
        "subscribed_topics": settings.kafka_topics
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8002,
        reload=settings.debug,
        log_level="info"
    )