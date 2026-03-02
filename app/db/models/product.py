"""
Product database model and ProductStatus enum
"""
from sqlalchemy import Column, Integer, String, Boolean, JSON, DateTime, ForeignKey, Numeric, Enum
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from datetime import datetime
import enum
from app.db.models.base import Base
from app.db.models.tag import product_tags

try:
    JSON_TYPE = JSONB
except ImportError:
    JSON_TYPE = JSON


# Enum for Product Status
class ProductStatus(enum.Enum):
    DRAFT = "draft"
    PUBLISHED = "published"
    ARCHIVED = "archived"
    OUT_OF_STOCK = "out_of_stock"


class Product(Base):
    __tablename__ = "products"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(255), index=True, nullable=False)
    description = Column(String(2000), nullable=True)
    brand = Column(String(100), nullable=True)
    image = Column(String(500), nullable=True)  # Base64 image string or URL
    images = Column(JSON_TYPE, nullable=True)  # Array of image strings

    # Inventory & Stock Management
    sku = Column(String(100), unique=True, index=True, nullable=True)
    slug = Column(String(255), unique=True, index=True, nullable=True)
    stock_quantity = Column(Integer, default=0, nullable=False)
    low_stock_threshold = Column(Integer, nullable=True)
    track_inventory = Column(Boolean, default=True, nullable=False)

    # Status & Visibility
    status = Column(Enum(ProductStatus),
                    default=ProductStatus.DRAFT, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    is_featured = Column(Boolean, default=False, nullable=False, index=True)
    is_bestseller = Column(Boolean, default=False, nullable=False)
    published_at = Column(DateTime, nullable=True)

    # Pricing & Commerce
    category_id = Column(Integer, ForeignKey("categories.id"), nullable=True)
    price = Column(Numeric(10, 2), index=True, nullable=True)
    compare_at_price = Column(Numeric(10, 2), nullable=True)
    cost_price = Column(Numeric(10, 2), nullable=True)
    tax_class = Column(String(50), nullable=True)
    currency = Column(String(3), default='USD', nullable=False)

    # SEO & Marketing
    meta_title = Column(String(255), nullable=True)
    meta_description = Column(String(500), nullable=True)
    meta_keywords = Column(String(500), nullable=True)

    # Physical Attributes
    weight = Column(Numeric(8, 2), nullable=True)  # Weight in kg or lbs
    dimensions = Column(JSON_TYPE, nullable=True)  # {length, width, height}
    shipping_class = Column(String(50), nullable=True)

    # Analytics & Performance
    view_count = Column(Integer, default=0, nullable=False)
    purchase_count = Column(Integer, default=0, nullable=False)
    rating_average = Column(Numeric(3, 2), default=0.0,
                            nullable=False)  # 0.00 to 5.00
    rating_count = Column(Integer, default=0, nullable=False)

    # Organization
    sort_order = Column(Integer, default=0, nullable=False)

    # Object/dict of specifications
    specifications = Column(JSON_TYPE, nullable=True)

    # Audit & Tracking
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow,
                        onupdate=datetime.utcnow, nullable=False)
    created_by = Column(Integer, nullable=True)
    updated_by = Column(Integer, nullable=True)
    deleted_at = Column(DateTime, nullable=True, index=True)
    version = Column(Integer, default=1, nullable=False)  # Optimistic locking

    # Relationships
    category = relationship("Category", back_populates="products")
    tags = relationship("Tag", secondary=product_tags,
                        back_populates="products")
    variants = relationship(
        "ProductVariant", back_populates="product", cascade="all, delete-orphan")
