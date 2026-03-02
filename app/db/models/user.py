"""
User database model
"""
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Index, Enum
from sqlalchemy.orm import relationship
from datetime import datetime
import enum
from app.db.models.base import Base


class UserRole(str, enum.Enum):
    """User role enumeration"""
    USER = "user"
    OWNER = "owner"


class UserCategory(str, enum.Enum):
    """User category enumeration"""
    PERSONAL = "personal"
    ORGANIZATION = "organization"


class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=True)  # Nullable for OTP-only users
    role = Column(Enum(UserRole), default=UserRole.USER, nullable=False, index=True)
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    
    # User category and organization details
    category = Column(Enum(UserCategory), nullable=True, default=None)
    gst_number = Column(String(15), nullable=True)  # Required for organizations
    
    # Shipping address
    shipping_address1 = Column(String(255), nullable=True)
    shipping_address2 = Column(String(255), nullable=True)
    shipping_pin = Column(String(10), nullable=True)
    shipping_city = Column(String(100), nullable=True)
    shipping_state = Column(String(100), nullable=True)
    shipping_country = Column(String(100), nullable=True, default="India")
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    last_login = Column(DateTime, nullable=True)
    
    # Relationships
    shipping_addresses = relationship(
        "ShippingAddress",
        back_populates="user",
        cascade="all, delete-orphan"
    )
    
    # Index for faster email lookups
    __table_args__ = (
        Index('ix_users_email_lower', 'email'),
    )
