import os
from typing import Optional
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Настройки приложения"""

    # Основные настройки приложения
    app_name: str = "Cart Service"
    debug: bool = False
    log_level: str = "INFO"

    # Настройки безопасности
    secret_key: str = "your-secret-key-change-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30

    # Настройки базы данных
    database_url: str = "postgresql://cart_user:cart_password@localhost:5432/cart_db"

    # Настройки внешних сервисов
    catalog_service_url: str = "http://localhost:8001"

    # Настройки Kafka
    kafka_bootstrap_servers: str = "localhost:9092"
    kafka_group_id: str = "cart-service"
    kafka_auto_offset_reset: str = "latest"
    kafka_enable_auto_commit: bool = True

    class Config:
        env_file = ".env"
        case_sensitive = False
        # Разрешаем дополнительные поля из переменных окружения
        extra = "ignore"


# Создаем экземпляр настроек
settings = Settings()