"""
JWT token service for creating and verifying authentication tokens
"""
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from jose import JWTError, jwt
from app.core.config import settings


def get_secret_key() -> str:
    """
    Get JWT secret key from settings, or generate a default one for development.
    
    Returns:
        Secret key string
    """
    secret_key = settings.JWT_SECRET_KEY or settings.SECRET_KEY
    
    if not secret_key:
        # For development only - should be set via environment variable in production
        secret_key = settings.SECRET_KEY
    
    return secret_key


def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """
    Create a JWT access token.
    
    Args:
        data: Dictionary containing token payload data
        expires_delta: Optional timedelta for token expiration. If not provided,
                      uses default expiration from settings.
    
    Returns:
        Encoded JWT token string
    """
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    
    encoded_jwt = jwt.encode(
        to_encode,
        get_secret_key(),
        algorithm=settings.ALGORITHM
    )
    
    return encoded_jwt


def verify_token(token: str) -> Optional[Dict[str, Any]]:
    """
    Verify and decode a JWT token.
    
    Args:
        token: JWT token string
        
    Returns:
        Decoded token payload if valid, None otherwise
    """
    try:
        payload = jwt.decode(
            token,
            get_secret_key(),
            algorithms=[settings.ALGORITHM]
        )
        return payload
    except JWTError:
        return None


def get_user_email_from_token(token: str) -> Optional[str]:
    """
    Extract user email from JWT token.
    
    Args:
        token: JWT token string
        
    Returns:
        User email if token is valid, None otherwise
    """
    payload = verify_token(token)
    if payload:
        # JWT standard uses "sub" (subject) for user identifier
        return payload.get("sub")
    return None


def get_user_id_from_token(token: str) -> Optional[int]:
    """
    Extract user ID from JWT token.
    
    Args:
        token: JWT token string
        
    Returns:
        User ID if token is valid, None otherwise
    """
    payload = verify_token(token)
    if payload:
        return payload.get("user_id")
    return None


def create_refresh_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """
    Create a JWT refresh token with longer expiration.
    
    Args:
        data: Dictionary containing token payload data
        expires_delta: Optional timedelta for token expiration. If not provided,
                      uses default expiration from settings (7 days).
    
    Returns:
        Encoded JWT refresh token string
    """
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        # Default to 7 days for refresh tokens
        expire = datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    
    to_encode.update({"exp": expire, "type": "refresh"})
    
    encoded_jwt = jwt.encode(
        to_encode,
        get_secret_key(),
        algorithm=settings.ALGORITHM
    )
    
    return encoded_jwt


def verify_refresh_token(token: str) -> Optional[Dict[str, Any]]:
    """
    Verify and decode a JWT refresh token.
    
    Args:
        token: JWT refresh token string
        
    Returns:
        Decoded token payload if valid and is a refresh token, None otherwise
    """
    payload = verify_token(token)
    if payload and payload.get("type") == "refresh":
        return payload
    return None
