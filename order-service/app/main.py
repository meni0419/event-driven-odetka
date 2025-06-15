from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import logging
import asyncio

from .config import settings
from .database import engine, Base
from .api import api_router
from .events.producer import order_event_producer
from .events.consumer import order_event_consumer
from .events.handlers import OrderEventHandlers
from .api.routes.orders import router as orders_router

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Глобальная переменная для задачи consumer'а
consumer_task = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Управление жизненным циклом приложения"""
    global consumer_task

    # Startup
    logger.info("🚀 Starting Order Service...")

    try:
        # Создаем таблицы
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("✅ Database tables created")

        # Запускаем Kafka producer
        await order_event_producer.start()
        logger.info("✅ Kafka producer started")

        # Запускаем Kafka consumer
        await order_event_consumer.start()

        # Регистрируем обработчики событий
        order_event_consumer.register_handler(
            "checkout_initiated",  # ✅ ИСПРАВЛЕНО!
            OrderEventHandlers.handle_checkout_initiated
        )
        order_event_consumer.register_handler(
            "payment_processed",
            OrderEventHandlers.handle_payment_processed
        )
        order_event_consumer.register_handler(
            "payment_failed",
            OrderEventHandlers.handle_payment_failed
        )

        # Запускаем consumer в отдельной задаче
        consumer_task = asyncio.create_task(order_event_consumer.consume_events())
        logger.info("✅ Kafka consumer started and handlers registered")

        logger.info("🎉 Order Service started successfully!")

        yield  # Приложение работает

    except Exception as e:
        logger.error(f"❌ Failed to start Order Service: {e}")
        raise

    # Shutdown
    logger.info("🛑 Shutting down Order Service...")

    try:
        # Останавливаем consumer
        if consumer_task and not consumer_task.done():
            consumer_task.cancel()
            try:
                await consumer_task
            except asyncio.CancelledError:
                pass

        await order_event_consumer.stop()
        logger.info("✅ Kafka consumer stopped")

        # Останавливаем producer
        await order_event_producer.stop()
        logger.info("✅ Kafka producer stopped")

        # Закрываем соединение с БД
        await engine.dispose()
        logger.info("✅ Database connection closed")

        logger.info("👋 Order Service shut down complete")

    except Exception as e:
        logger.error(f"❌ Error during shutdown: {e}")


# Создаем FastAPI приложение
app = FastAPI(
    title="Order Service",
    description="Микросервис управления заказами",
    version="1.0.0",
    lifespan=lifespan
)

# Настройка CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Подключаем API routes
app.include_router(api_router)
app.include_router(
    orders_router,
    prefix="/api/v1",
    tags=["orders"]
)


# Health check endpoints
@app.get("/health")
async def health_check():
    """Проверка состояния сервиса"""
    try:
        # Можно добавить проверки подключения к БД, Kafka и т.д.
        return {
            "status": "healthy",
            "service": "order-service",
            "version": "1.0.0"
        }
    except Exception as e:
        logger.error(f"❌ Health check failed: {e}")
        raise HTTPException(status_code=503, detail="Service unhealthy")


@app.get("/health/ready")
async def readiness_check():
    """Проверка готовности к обработке запросов"""
    try:
        # Проверяем что все компоненты запущены
        is_ready = (
                order_event_producer.producer is not None and
                order_event_consumer.consumer is not None and
                consumer_task is not None and not consumer_task.done()
        )

        if is_ready:
            return {
                "status": "ready",
                "service": "order-service"
            }
        else:
            raise HTTPException(status_code=503, detail="Service not ready")

    except Exception as e:
        logger.error(f"❌ Readiness check failed: {e}")
        raise HTTPException(status_code=503, detail="Service not ready")


@app.get("/")
async def root():
    """Корневой endpoint"""
    return {
        "message": "Order Service API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health"
    }


# Обработчик исключений
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Глобальный обработчик исключений"""
    logger.error(f"❌ Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "message": "An unexpected error occurred"
        }
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8002,
        reload=settings.debug
    )
