from sqlalchemy.orm import Session
from ..database import SessionLocal


def get_db():
    """Dependency для получения сессии БД"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_current_user_or_session():
    """Временная заглушка для получения ID сессии/пользователя"""
    # В реальном приложении тут будет логика аутентификации
    return "test-session-123"