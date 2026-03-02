"""
Tag database model
"""
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Table, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from app.db.models.base import Base

# Association table for many-to-many relationship between Products and Tags
product_tags = Table(
    'product_tags',
    Base.metadata,
    Column('product_id', Integer, ForeignKey('products.id'), primary_key=True),
    Column('tag_id', Integer, ForeignKey('tags.id'), primary_key=True)
)


class Tag(Base):
    __tablename__ = "tags"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(255), unique=True, index=True, nullable=False)
    slug = Column(String(255), unique=True, index=True, nullable=False)
    description = Column(String(1000), nullable=True)

    # Visual
    color = Column(String(7), nullable=True)  # Hex color code
    icon = Column(String(100), nullable=True)

    # Organization
    is_active = Column(Boolean, default=True, nullable=False)
    sort_order = Column(Integer, default=0, nullable=False)

    # Analytics
    usage_count = Column(Integer, default=0, nullable=False)

    # Audit
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow,
                        onupdate=datetime.utcnow, nullable=False)
    created_by = Column(Integer, nullable=True)
    updated_by = Column(Integer, nullable=True)
    deleted_at = Column(DateTime, nullable=True)

    # Relationship to products (many-to-many)
    products = relationship(
        "Product", secondary=product_tags, back_populates="tags")
