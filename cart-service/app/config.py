from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    # App
    app_name: str = "Cart Service"
    debug: bool = True

    # Database - ИСПОЛЬЗУЕМ PSYCOPG2 для синхронного кода
    database_url: str = "postgresql+psycopg2://admin:admin123@shared-postgres:5432/ecommerce_db"

    # Kafka
    kafka_bootstrap_servers: str = "shared-kafka:9092"
    kafka_group_id: str = "cart-service-group"

    # CORS
    allowed_origins: List[str] = ["*"]

    # External services
    catalog_service_url: str = "http://localhost:8001"

    class Config:
        env_file = ".env"
        # УБИРАЕМ extra_forbidden для совместимости
        extra = "ignore"


settings = Settings()