import logging
import time
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.exc import OperationalError
from sqlalchemy import text

from .config import settings
from .database import engine, Base, SessionLocal
from .api.routes.cart import router as cart_router
from .services.kafka_client import kafka_client

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def wait_for_db(max_retries: int = 30, delay: int = 2):
    """Ожидает готовности базы данных с повторными попытками"""
    retries = 0
    while retries < max_retries:
        try:
            logger.info(f"Attempting to connect to database (attempt {retries + 1}/{max_retries})...")

            # Пробуем создать соединение
            db = SessionLocal()
            db.execute(text("SELECT 1"))  # Используем text() для SQL-запроса
            db.close()

            logger.info("✅ Database connection successful!")
            return True

        except OperationalError as e:
            retries += 1
            if retries >= max_retries:
                logger.error(f"❌ Failed to connect to database after {max_retries} attempts")
                raise e

            logger.warning(f"Database not ready, waiting {delay} seconds... (attempt {retries}/{max_retries})")
            time.sleep(delay)

    return False


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Управление жизненным циклом приложения"""
    # Startup
    logger.info("Starting Cart Service...")

    try:
        # Ждём готовности базы данных
        logger.info("Waiting for database to be ready...")
        wait_for_db()

        # Создаем таблицы в БД
        logger.info("Creating database tables...")
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables created successfully")

        # Запускаем Kafka продюсер
        logger.info("Starting Kafka producer...")
        await kafka_client.start_producer()
        logger.info("Kafka producer started successfully")

        logger.info("✅ Cart Service started successfully!")

        yield  # Приложение работает

    except Exception as e:
        logger.error(f"❌ Failed to start Cart Service: {e}")
        raise

    # Shutdown
    logger.info("Shutting down Cart Service...")

    # Останавливаем Kafka продюсер
    try:
        await kafka_client.stop_producer()
    except Exception as e:
        logger.error(f"Error stopping Kafka producer: {e}")

    logger.info("✅ Cart Service shut down successfully!")


# Создаем FastAPI приложение
app = FastAPI(
    title=settings.app_name,
    description="Микросервис управления корзиной покупок",
    version="1.0.0",
    debug=settings.debug,
    lifespan=lifespan
)

# Middleware для CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # В production указать конкретные домены
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)

# Подключаем роуты
app.include_router(cart_router, prefix="/api/v1", tags=["cart"])


# Health check endpoints
@app.get("/health")
async def health_check():
    """Проверка здоровья сервиса"""
    try:
        # Проверяем подключение к БД
        db = SessionLocal()
        try:
            db.execute(text("SELECT 1"))  # Используем text() для SQL-запроса
            db_status = "connected"
        except Exception as e:
            logger.error(f"Database check failed: {e}")
            db_status = "disconnected"
        finally:
            db.close()

        # Проверяем состояние Kafka
        kafka_status = "connected" if kafka_client.producer else "disconnected"

        return {
            "status": "healthy",
            "service": settings.app_name,
            "database": db_status,
            "kafka": kafka_status,
            "version": "1.0.0"
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=503, detail="Service unhealthy")


@app.get("/")
async def root():
    """Корневой endpoint"""
    return {
        "service": settings.app_name,
        "version": "1.0.0",
        "status": "running",
        "endpoints": {
            "health": "/health",
            "docs": "/docs",
            "cart": "/api/v1/cart",
            "kafka-ui": "http://localhost:8080"
        }
    }


# Exception handlers
@app.exception_handler(404)
async def not_found_handler(request, exc):
    return JSONResponse(
        status_code=404,
        content={"error": "Resource not found", "detail": str(exc.detail) if hasattr(exc, 'detail') else "Not found"}
    )


@app.exception_handler(500)
async def internal_error_handler(request, exc):
    logger.error(f"Internal server error: {exc}")
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error", "detail": "Something went wrong"}
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug,
        log_level="info"
    )