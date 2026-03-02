"""
ProductVariant database model
"""
from sqlalchemy import Column, Integer, String, Boolean, JSON, DateTime, ForeignKey, Numeric
from sqlalchemy.orm import relationship
from datetime import datetime
from app.db.models.base import Base

try:
    from sqlalchemy.dialects.postgresql import JSONB
    JSON_TYPE = JSONB
except ImportError:
    JSON_TYPE = JSON


class ProductVariant(Base):
    __tablename__ = "product_variants"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    name = Column(String(255), nullable=False)

    # Inventory
    sku = Column(String(100), unique=True, index=True, nullable=True)
    stock_quantity = Column(Integer, default=0, nullable=False)
    low_stock_threshold = Column(Integer, nullable=True)

    # Pricing
    price = Column(Numeric(10, 2), nullable=True)
    original_price = Column(Numeric(10, 2), nullable=True)
    cost_price = Column(Numeric(10, 2), nullable=True)
    compare_at_price = Column(Numeric(10, 2), nullable=True)

    # Physical Attributes
    weight = Column(Numeric(8, 2), nullable=True)
    dimensions = Column(JSON_TYPE, nullable=True)  # {length, width, height}
    barcode = Column(String(100), nullable=True, index=True)  # UPC/EAN/Barcode

    # Object/dict of specifications
    specifications = Column(JSON_TYPE, nullable=True)
    images = Column(JSON_TYPE, nullable=True)  # Array of image strings
    in_stock = Column(Boolean, default=True, nullable=False)

    # Audit
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow,
                        onupdate=datetime.utcnow, nullable=False)
    deleted_at = Column(DateTime, nullable=True)

    # Relationship to product
    product = relationship("Product", back_populates="variants")
