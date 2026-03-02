"""
Product Price History database model
"""
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Numeric, Index
from sqlalchemy.orm import relationship
from datetime import datetime
from app.db.models.base import Base


class ProductPriceHistory(Base):
    __tablename__ = "product_price_history"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    product_id = Column(Integer, ForeignKey(
        "products.id"), nullable=False, index=True)
    variant_id = Column(Integer, ForeignKey(
        "product_variants.id"), nullable=True, index=True)
    price = Column(Numeric(10, 2), nullable=False)
    quote_id = Column(Integer, ForeignKey(
        "quotes.id"), nullable=True, index=True)
    quote_item_id = Column(Integer, ForeignKey(
        "quote_items.id"), nullable=True, index=True)
    created_by = Column(Integer, ForeignKey(
        "users.id"), nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow,
                        nullable=False, index=True)

    # Relationships
    product = relationship("Product", backref="price_history")
    variant = relationship("ProductVariant", backref="price_history")
    quote = relationship("Quote", backref="price_history")
    quote_item = relationship("QuoteItem", backref="price_history")
    creator = relationship("User", backref="created_price_history")


# Create composite index for efficient queries
# Note: DESC ordering is handled in queries, not in index definition
Index('idx_product_variant_created', ProductPriceHistory.product_id,
      ProductPriceHistory.variant_id, ProductPriceHistory.created_at)
