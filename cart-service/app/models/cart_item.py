from sqlalchemy import Column, Integer, String, Float, ForeignKey
from sqlalchemy.orm import relationship
from ..database import Base


class CartItem(Base):
    __tablename__ = "cart_items"

    id = Column(Integer, primary_key=True, index=True)
    cart_id = Column(String, ForeignKey("carts.id"))
    product_id = Column(Integer, index=True)
    quantity = Column(Integer)
    price_at_add = Column(Float)  # Цена на момент добавления

    # Связь с корзиной
    cart = relationship("Cart", back_populates="items")