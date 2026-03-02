"""
Shipping address database model
"""
from datetime import datetime
from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import relationship

from app.db.models.base import Base


class ShippingAddress(Base):
    __tablename__ = "shipping_addresses"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    phone = Column(String(20), nullable=False)
    country = Column(String(100), nullable=False, default="India")
    state = Column(String(100), nullable=False)
    city = Column(String(100), nullable=False)
    address1 = Column(String(255), nullable=False)
    address2 = Column(String(255), nullable=True)
    postal_code = Column(String(20), nullable=False)
    company = Column(String(255), nullable=True)
    instructions = Column(Text, nullable=True)
    is_default = Column(Boolean, nullable=False, default=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    user = relationship("User", back_populates="shipping_addresses")

    __table_args__ = (
        Index("ix_shipping_addresses_user_default", "user_id", "is_default"),
    )

