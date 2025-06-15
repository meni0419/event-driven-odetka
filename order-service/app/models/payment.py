from sqlalchemy import Column, String, DateTime, Enum, Numeric, ForeignKey, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from enum import Enum as PyEnum
from ..database import Base


class PaymentStatus(PyEnum):
    PENDING = "pending"  # Ожидает оплаты
    PROCESSING = "processing"  # В процессе оплаты
    COMPLETED = "completed"  # Оплачено
    FAILED = "failed"  # Ошибка оплаты
    CANCELLED = "cancelled"  # Отменено
    REFUNDED = "refunded"  # Возврат


class PaymentMethod(PyEnum):
    CARD = "card"
    BANK_TRANSFER = "bank_transfer"
    CASH = "cash"
    DIGITAL_WALLET = "digital_wallet"


class Payment(Base):
    __tablename__ = "payments"

    id = Column(String, primary_key=True, index=True)  # UUID
    order_id = Column(String, ForeignKey("orders.id"), nullable=False)

    # Информация об оплате
    amount = Column(Numeric(10, 2), nullable=False)
    currency = Column(String(3), default="USD", nullable=False)
    method = Column(Enum(PaymentMethod), nullable=False)
    status = Column(Enum(PaymentStatus), default=PaymentStatus.PENDING, nullable=False)

    # Внешний ID транзакции (от платежной системы)
    external_transaction_id = Column(String(255), nullable=True)

    # Дополнительные данные
    provider_response = Column(Text, nullable=True)  # JSON ответ от провайдера
    failure_reason = Column(Text, nullable=True)

    # Временные метки
    created_at = Column(DateTime, default=func.now(), nullable=False)
    processed_at = Column(DateTime, nullable=True)

    # Связи
    order = relationship("Order", back_populates="payments")