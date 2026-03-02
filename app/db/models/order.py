"""
Order and OrderItem database models
"""
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Numeric, Enum, Text, UniqueConstraint
from sqlalchemy.orm import relationship
from datetime import datetime
import enum
from app.db.models.base import Base

try:
    from sqlalchemy.dialects.postgresql import JSONB
    JSON_TYPE = JSONB
except ImportError:
    from sqlalchemy import JSON
    JSON_TYPE = JSON


class OrderStatus(str, enum.Enum):
    """Order status enumeration"""
    PENDING = "pending"
    PROCESSING = "processing"
    SHIPPED = "shipped"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"


class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    order_number = Column(String(50), unique=True, index=True, nullable=False)
    quote_id = Column(Integer, ForeignKey("quotes.id"), nullable=False, unique=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    status = Column(Enum(OrderStatus), default=OrderStatus.PENDING, nullable=False, index=True)
    
    # Pricing information (copied from quote)
    subtotal = Column(Numeric(10, 2), nullable=True)
    total_tax = Column(Numeric(10, 2), nullable=True)
    total = Column(Numeric(10, 2), nullable=True)
    # {"5": 100.00, "18": 250.00}
    tax_breakdown = Column(JSON_TYPE, nullable=True)
    
    # Optional fields
    notes = Column(Text, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    quote = relationship("Quote", backref="orders")
    user = relationship("User", backref="orders")
    items = relationship("OrderItem", back_populates="order", cascade="all, delete-orphan")


class OrderItem(Base):
    __tablename__ = "order_items"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False, index=True)
    variant_id = Column(Integer, ForeignKey("product_variants.id"), nullable=True, index=True)
    
    # Snapshot of product information
    product_name = Column(String(255), nullable=False)
    variant_name = Column(String(255), nullable=True)
    price = Column(Numeric(10, 2), nullable=False)
    quantity = Column(Integer, nullable=False)
    image = Column(String(500), nullable=True)
    
    # GST and Tax fields
    # 5.00, 12.00, 18.00, 28.00
    gst_rate = Column(Numeric(5, 2), nullable=True)
    item_total = Column(Numeric(10, 2), nullable=True)  # price * quantity
    # item_total * (gst_rate / 100)
    tax_amount = Column(Numeric(10, 2), nullable=True)
    item_total_with_tax = Column(Numeric(10, 2), nullable=True)  # item_total + tax_amount
    
    # Timestamp
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    order = relationship("Order", back_populates="items")
    product = relationship("Product", backref="order_items")
    variant = relationship("ProductVariant", backref="order_items")

