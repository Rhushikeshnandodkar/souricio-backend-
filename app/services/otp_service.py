"""
OTP (One-Time Password) service for generation, storage, and verification
"""
import secrets
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import and_
from app.db.models.otp import OTP
from app.core.config import settings


def generate_otp() -> str:
    """
    Generate a random 6-digit OTP code.
    
    Returns:
        6-digit string code
    """
    return f"{secrets.randbelow(900000) + 100000:06d}"


def create_otp(email: str, db: Session) -> str:
    """
    Create and store a new OTP code for the given email.
    
    Args:
        email: User email address (normalized to lowercase)
        db: Database session
        
    Returns:
        6-digit OTP code
    """
    # Normalize email to lowercase
    email = email.lower().strip()
    
    # Generate OTP code
    code = generate_otp()
    
    # Calculate expiration time
    expires_at = datetime.utcnow() + timedelta(minutes=settings.OTP_EXPIRY_MINUTES)
    
    # Create OTP record
    otp_record = OTP(
        email=email,
        code=code,
        expires_at=expires_at,
        is_used=False
    )
    
    db.add(otp_record)
    db.commit()
    db.refresh(otp_record)
    
    return code


def verify_otp(email: str, code: str, db: Session) -> bool:
    """
    Verify an OTP code for the given email.
    
    Args:
        email: User email address (normalized to lowercase)
        code: 6-digit OTP code
        db: Database session
        
    Returns:
        True if OTP is valid and not expired, False otherwise
    """
    # Normalize email to lowercase
    email = email.lower().strip()
    
    # Find the most recent unused OTP for this email
    otp_record = db.query(OTP).filter(
        and_(
            OTP.email == email,
            OTP.code == code,
            OTP.is_used == False,
            OTP.expires_at > datetime.utcnow()
        )
    ).order_by(OTP.created_at.desc()).first()
    
    if not otp_record:
        return False
    
    # Mark OTP as used
    otp_record.is_used = True
    db.commit()
    
    return True


def cleanup_expired_otps(db: Session) -> int:
    """
    Clean up expired OTP records (optional cleanup job).
    
    Args:
        db: Database session
        
    Returns:
        Number of deleted records
    """
    deleted_count = db.query(OTP).filter(
        OTP.expires_at < datetime.utcnow()
    ).delete()
    
    db.commit()
    return deleted_count


def invalidate_user_otps(email: str, db: Session) -> int:
    """
    Invalidate all unused OTPs for a user (useful when generating new OTP).
    
    Args:
        email: User email address (normalized to lowercase)
        db: Database session
        
    Returns:
        Number of invalidated OTPs
    """
    email = email.lower().strip()
    
    invalidated_count = db.query(OTP).filter(
        and_(
            OTP.email == email,
            OTP.is_used == False,
            OTP.expires_at > datetime.utcnow()
        )
    ).update({OTP.is_used: True})
    
    db.commit()
    return invalidated_count
