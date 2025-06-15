from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    # App
    app_name: str = "Order Service"
    debug: bool = True

    # Database - AsyncPG для async кода
    database_url: str = "postgresql+asyncpg://admin:admin123@shared-postgres:5432/ecommerce_db"

    # Kafka
    kafka_bootstrap_servers: str = "shared-kafka:9092"
    kafka_group_id: str = "order-service-group"
    kafka_topics: List[str] = [
        "cart.checkout.initiated",
        "payment.processed",
        "payment.failed"
    ]
    kafka_auto_offset_reset: str = "earliest"

    # External services
    catalog_service_url: str = "http://cart-service:8001"

    # CORS
    allowed_origins: List[str] = ["*"]

    class Config:
        env_file = ".env"
        # ДОБАВЛЯЕМ для совместимости
        extra = "ignore"


settings = Settings()