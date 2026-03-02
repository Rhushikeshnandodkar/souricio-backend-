"""
Shared dependencies for the application.
"""
from sqlalchemy.orm import Session
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.db.database import get_db
from app.db.models.user import User, UserRole
from app.services.jwt_service import verify_token

security = HTTPBearer()


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """
    Dependency to get current authenticated user from JWT token.
    
    Args:
        credentials: HTTP Bearer token credentials
        db: Database session
        
    Returns:
        User object
        
    Raises:
        HTTPException: If token is invalid or user not found
    """
    token = credentials.credentials
    payload = verify_token(token)
    
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    email = payload.get("sub")
    if not email:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive",
        )
    
    return user


def get_current_owner(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    Dependency to ensure current user is an owner.
    Use this for endpoints that should only be accessible to owners.
    
    Args:
        current_user: Current authenticated user (from get_current_user dependency)
        
    Returns:
        User object (guaranteed to be an owner)
        
    Raises:
        HTTPException: If user is not an owner
    """
    if current_user.role != UserRole.OWNER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This endpoint requires owner privileges"
        )
    
    return current_user


def get_current_admin(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    Dependency to ensure current user is an admin/owner.
    Alias for get_current_owner for consistency with quote admin endpoints.
    
    Args:
        current_user: Current authenticated user (from get_current_user dependency)
        
    Returns:
        User object (guaranteed to be an owner/admin)
        
    Raises:
        HTTPException: If user is not an owner/admin
    """
    if current_user.role != UserRole.OWNER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This endpoint requires admin privileges"
        )
    
    return current_user


# Re-export for convenience
__all__ = ["get_db", "get_current_user", "get_current_owner", "get_current_admin"]
