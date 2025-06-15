from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from decimal import Decimal
from ..models.payment import PaymentStatus, PaymentMethod


class PaymentCreate(BaseModel):
    order_id: str
    amount: Decimal = Field(..., ge=0)
    currency: str = Field(default="USD", max_length=3)
    method: PaymentMethod


class PaymentUpdate(BaseModel):
    status: Optional[PaymentStatus] = None
    external_transaction_id: Optional[str] = None
    failure_reason: Optional[str] = None


class PaymentResponse(BaseModel):
    id: str
    order_id: str
    amount: Decimal
    currency: str
    method: PaymentMethod
    status: PaymentStatus
    external_transaction_id: Optional[str] = None
    failure_reason: Optional[str] = None
    created_at: datetime
    processed_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class PaymentMockRequest(BaseModel):
    """Схема для мок-обработки платежа"""
    success: bool = True
    transaction_id: Optional[str] = None