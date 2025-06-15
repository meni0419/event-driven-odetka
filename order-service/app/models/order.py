from sqlalchemy import Column, String, DateTime, Enum, Numeric, Text, Integer
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from enum import Enum as PyEnum
from ..database import Base


class OrderStatus(PyEnum):
    PENDING = "pending"  # Ожидает обработки
    CONFIRMED = "confirmed"  # Подтвержден
    PROCESSING = "processing"  # В обработке
    SHIPPED = "shipped"  # Отправлен
    DELIVERED = "delivered"  # Доставлен
    CANCELLED = "cancelled"  # Отменен
    REFUNDED = "refunded"  # Возвращен


class Order(Base):
    __tablename__ = "orders"

    id = Column(String, primary_key=True, index=True)  # UUID
    cart_id = Column(String, nullable=False, index=True)  # ID корзины
    user_id = Column(String, nullable=True, index=True)  # ID пользователя (если есть)

    # Статус заказа
    status = Column(Enum(OrderStatus), default=OrderStatus.PENDING, nullable=False)

    # Суммы
    total_amount = Column(Numeric(10, 2), nullable=False)
    discount_amount = Column(Numeric(10, 2), default=0.00)
    shipping_amount = Column(Numeric(10, 2), default=0.00)
    tax_amount = Column(Numeric(10, 2), default=0.00)
    final_amount = Column(Numeric(10, 2), nullable=False)

    # Количество товаров
    total_items = Column(Integer, nullable=False)

    # Информация о доставке
    shipping_address = Column(Text, nullable=True)
    shipping_method = Column(String(100), nullable=True)

    # Дополнительная информация
    notes = Column(Text, nullable=True)

    # Временные метки
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    confirmed_at = Column(DateTime, nullable=True)
    shipped_at = Column(DateTime, nullable=True)
    delivered_at = Column(DateTime, nullable=True)

    # Связи
    items = relationship("OrderItem", back_populates="order", cascade="all, delete-orphan")
    payments = relationship("Payment", back_populates="order", cascade="all, delete-orphan")