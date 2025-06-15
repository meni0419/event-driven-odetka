from sqlalchemy import Column, String, Integer, Numeric, ForeignKey
from sqlalchemy.orm import relationship
from ..database import Base


class OrderItem(Base):
    __tablename__ = "order_items"

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(String, ForeignKey("orders.id"), nullable=False)

    # Информация о товаре
    product_id = Column(Integer, nullable=False)
    product_name = Column(String(255), nullable=False)
    product_sku = Column(String(100), nullable=True)

    # Количество и цены
    quantity = Column(Integer, nullable=False)
    unit_price = Column(Numeric(10, 2), nullable=False)  # Цена за единицу на момент заказа
    total_price = Column(Numeric(10, 2), nullable=False)  # quantity * unit_price

    # Связи
    order = relationship("Order", back_populates="items")