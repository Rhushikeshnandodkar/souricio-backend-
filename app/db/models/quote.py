"""
Quote and QuoteItem database models
"""
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Numeric, Enum, Text, Boolean
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


class QuoteStatus(str, enum.Enum):
    """Quote status enumeration"""
    DRAFT = "draft"
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"


class Quote(Base):
    __tablename__ = "quotes"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    quote_number = Column(String(50), unique=True, index=True, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"),
                     nullable=False, index=True)
    status = Column(Enum(QuoteStatus), default=QuoteStatus.DRAFT,
                    nullable=False, index=True)
    expires_at = Column(DateTime, nullable=True, index=True)
    notes = Column(Text, nullable=True)
    admin_notes = Column(Text, nullable=True)
    subtotal = Column(Numeric(10, 2), nullable=True)
    total_tax = Column(Numeric(10, 2), nullable=True)
    total = Column(Numeric(10, 2), nullable=True)
    # {"5": 100.00, "18": 250.00}
    tax_breakdown = Column(JSON_TYPE, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow,
                        onupdate=datetime.utcnow, nullable=False)

    # Relationships
    user = relationship("User", backref="quotes")
    items = relationship("QuoteItem", back_populates="quote",
                         cascade="all, delete-orphan")


class QuoteItem(Base):
    __tablename__ = "quote_items"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    quote_id = Column(Integer, ForeignKey("quotes.id"),
                      nullable=False, index=True)
    product_id = Column(Integer, ForeignKey(
        "products.id"), nullable=False, index=True)
    variant_id = Column(Integer, ForeignKey(
        "product_variants.id"), nullable=True, index=True)
    product_name = Column(String(255), nullable=False)
    variant_name = Column(String(255), nullable=True)
    price = Column(Numeric(10, 2), nullable=False)
    requires_custom_price = Column(Boolean, default=False, nullable=False)
    quantity = Column(Integer, nullable=False)
    image = Column(String(500), nullable=True)

    # GST and Tax fields
    # 5.00, 12.00, 18.00, 28.00
    gst_rate = Column(Numeric(5, 2), nullable=True)
    item_total = Column(Numeric(10, 2), nullable=True)  # price * quantity
    # item_total * (gst_rate / 100)
    tax_amount = Column(Numeric(10, 2), nullable=True)
    item_total_with_tax = Column(
        Numeric(10, 2), nullable=True)  # item_total + tax_amount

    # Timestamp
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    quote = relationship("Quote", back_populates="items")
    product = relationship("Product", backref="quote_items")
    variant = relationship("ProductVariant", backref="quote_items")
