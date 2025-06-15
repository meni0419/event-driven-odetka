from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    app_name: str = "Notification Service"
    debug: bool = True

    # Kafka настройки
    kafka_bootstrap_servers: str = "localhost:9092"
    kafka_group_id: str = "notification-service"
    kafka_auto_offset_reset: str = "earliest"

    # Топики для подписки
    kafka_topics: List[str] = [
        "cart.item.added",
        "cart.item.updated",
        "cart.item.removed",
        "cart.cleared",
        "cart.checkout.initiated"
    ]

    # Внешние сервисы
    email_service_url: str = "http://localhost:8002"
    analytics_service_url: str = "http://localhost:8003"

    class Config:
        env_file = ".env"


settings = Settings()