from sqlalchemy import Column, Integer, String, DateTime, func
from sqlalchemy.orm import relationship
from ..database import Base


class Cart(Base):
    __tablename__ = "carts"

    id = Column(String, primary_key=True, index=True)  # session_id или user_id
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    # Связь с позициями корзины
    items = relationship("CartItem", back_populates="cart", cascade="all, delete-orphan")