import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .config import settings
from .database import test_connection, Base, engine
from .services.kafka_client import kafka_client
from .api.routes.cart import router as cart_router  # ✅ ИСПРАВЛЕНО

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
    logger.info("🚀 Starting Cart Service...")

    try:
        # Проверяем подключение к БД
        logger.info("🔌 Testing database connection...")
        if test_connection():
            logger.info("✅ Database connection successful")
        else:
            logger.error("❌ Database connection failed")
            raise Exception("Database connection failed")

        # Создаем таблицы БД
        logger.info("📊 Creating database tables...")
        Base.metadata.create_all(bind=engine)
        logger.info("✅ Database tables created")

        # Запускаем Kafka producer
        logger.info("🔌 Starting Kafka producer...")
        await kafka_client.start_producer()
        logger.info("✅ Kafka producer started")

        logger.info("🎉 Cart Service started successfully!")

        yield  # Приложение работает

    except Exception as e:
        logger.error(f"❌ Failed to start Cart Service: {e}")
        raise

    # Shutdown
    logger.info("🛑 Shutting down Cart Service...")

    try:
        await kafka_client.stop_producer()
        logger.info("✅ Kafka producer stopped")
    except Exception as e:
        logger.error(f"❌ Error stopping Kafka producer: {e}")

    logger.info("✅ Cart Service shut down successfully!")


# Создаем FastAPI приложение
app = FastAPI(
    title=settings.app_name,
    description="Микросервис управления корзиной покупок",
    version="1.0.0",
    debug=settings.debug,
    lifespan=lifespan
)

# CORS middleware - ИСПРАВЛЯЕМ параметры
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],  # ✅ ИСПРАВЛЕНО
    allow_headers=["*"],
)

# Подключаем роутеры
app.include_router(
    cart_router,
    prefix="/api/v1",
    tags=["cart"]
)


# Health check endpoint
@app.get("/health")
async def health_check():
    """Проверка здоровья сервиса"""
    # Проверяем подключение к БД
    db_status = "healthy" if test_connection() else "unhealthy"

    return {
        "status": "healthy",
        "service": settings.app_name,
        "database": db_status,
        "kafka_producer": "running" if kafka_client.producer else "stopped",
        "version": "1.0.0"
    }


@app.get("/")
async def root():
    """Корневой endpoint"""
    return {
        "service": settings.app_name,
        "version": "1.0.0",
        "status": "running",
        "description": "Shopping cart microservice",
        "endpoints": {
            "health": "/health",
            "cart": "/api/v1/cart",
            "docs": "/docs"
        }
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8001,
        reload=settings.debug,
        log_level="info"
    )
