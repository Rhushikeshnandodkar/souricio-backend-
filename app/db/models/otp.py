"""
OTP (One-Time Password) database model
"""
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Index
from datetime import datetime
from app.db.models.base import Base


class OTP(Base):
    __tablename__ = "otps"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    email = Column(String(255), index=True, nullable=False)
    code = Column(String(6), nullable=False)  # 6-digit code
    expires_at = Column(DateTime, nullable=False, index=True)
    is_used = Column(Boolean, default=False, nullable=False, index=True)
    
    # Timestamp
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Indexes for faster lookups
    __table_args__ = (
        Index('ix_otps_email_code', 'email', 'code'),
        Index('ix_otps_email_created', 'email', 'created_at'),
    )
