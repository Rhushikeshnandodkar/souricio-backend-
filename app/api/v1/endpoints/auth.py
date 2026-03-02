"""
Authentication API endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, status, Request, Response
from sqlalchemy.orm import Session
from datetime import datetime

from app.dependencies import get_db, get_current_user
from app.db.models.user import User
from app.schemas.auth import (
    LoginRequest,
    SignUpRequest,
    VerifyRequest,
    ChangePasswordRequest,
    TokenResponse,
    UserResponse,
    UserUpdateRequest
)
from app.schemas.response import APIResponse, ErrorResponse, ErrorDetail
from app.services.auth_service import (
    update_user_last_login,
    authenticate_user,
    create_user_with_password,
    set_user_password,
    verify_user_password,
    update_user_profile
)
from app.services.otp_service import verify_otp
from app.services.jwt_service import create_access_token, create_refresh_token, verify_refresh_token
from datetime import timedelta
from app.core.config import settings

router = APIRouter()


@router.post("/signup", response_model=APIResponse, status_code=status.HTTP_201_CREATED, tags=["Authentication"])
async def signup(request: SignUpRequest, db: Session = Depends(get_db)):
    """
    Sign up a new user with email and password.
    Sends OTP code to email for verification.
    User account is inactive until email is verified.

    Args:
        request: Sign up request with email and password
        db: Database session

    Returns:
        Standard API response with success message

    Raises:
        HTTPException: If user already exists or email sending fails
    """
    try:
        user = await create_user_with_password(
            email=request.email,
            password=request.password,
            db=db,
            category=request.category,
            gst_number=request.gst_number,
            shipping_address1=request.shipping_address1,
            shipping_address2=request.shipping_address2,
            shipping_pin=request.shipping_pin,
            shipping_city=request.shipping_city,
            shipping_state=request.shipping_state,
            shipping_country=request.shipping_country
        )
        return APIResponse(
            status="success",
            message="Account created successfully. Please check your email for the verification code.",
            data={
                "email": user.email,
                "user_id": user.id,
                "is_active": user.is_active,
                "next_step": "verify_email"
            }
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ErrorResponse(
                status="error",
                message="Account creation failed",
                error=ErrorDetail(
                    code="USER_ALREADY_EXISTS",
                    message=str(e)
                )
            ).model_dump()
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                status="error",
                message="Internal server error",
                error=ErrorDetail(
                    code="INTERNAL_ERROR",
                    message="An error occurred while creating your account. Please try again."
                )
            ).model_dump()
        )


@router.post("/login", response_model=APIResponse, status_code=status.HTTP_200_OK, tags=["Authentication"])
def login(request: LoginRequest, response: Response, db: Session = Depends(get_db)):
    """
    Login with email and password. Returns JWT access token and sets refresh token in HTTP-only cookie.
    Only works for existing users - users must sign up first.

    Args:
        request: Login request with email and password
        response: FastAPI response object for setting cookies
        db: Database session

    Returns:
        Standard API response with JWT access token and user information

    Raises:
        HTTPException: If credentials are invalid or user does not exist
    """
    user = authenticate_user(request.email, request.password, db)

    if not user:
        # Check if user exists but is inactive
        temp_user = db.query(User).filter(
            User.email == request.email.lower().strip()).first()
        if temp_user and not temp_user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=ErrorResponse(
                    status="error",
                    message="Account verification required",
                    error=ErrorDetail(
                        code="ACCOUNT_NOT_ACTIVATED",
                        message="Please verify your email address before logging in."
                    )
                ).model_dump()
            )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ErrorResponse(
                status="error",
                message="Authentication failed",
                error=ErrorDetail(
                    code="INVALID_CREDENTIALS",
                    message="Invalid email or password."
                )
            ).model_dump()
        )

    # Update last login
    update_user_last_login(user, db)

    # Create access token
    access_token = create_access_token(
        data={
            "sub": user.email,
            "user_id": user.id
        }
    )

    # Create refresh token
    refresh_token = create_refresh_token(
        data={
            "sub": user.email,
            "user_id": user.id
        }
    )

    # Set refresh token in HTTP-only cookie
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS *
            24 * 60 * 60,  # Convert days to seconds
        httponly=True,
        secure=False,  # Set to True in production with HTTPS
        samesite="lax",
        path="/"
    )

    token_data = TokenResponse(
        access_token=access_token,
        token_type="bearer",
        user=UserResponse.model_validate(user)
    )

    return APIResponse(
        status="success",
        message="Login successful",
        data=token_data.model_dump()
    )


@router.post("/verify", response_model=APIResponse, status_code=status.HTTP_200_OK, tags=["Authentication"])
def verify_email(request: VerifyRequest, response: Response, db: Session = Depends(get_db)):
    """
    Verify email with OTP code and activate user account.
    Returns JWT access token and sets refresh token in HTTP-only cookie upon successful verification.

    Args:
        request: Verify request with email and OTP code
        response: FastAPI response object for setting cookies
        db: Database session

    Returns:
        Standard API response with JWT access token and user information

    Raises:
        HTTPException: If OTP is invalid, expired, or user not found
    """
    # Verify OTP code
    is_valid = verify_otp(request.email, request.code, db)

    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ErrorResponse(
                status="error",
                message="Verification failed",
                error=ErrorDetail(
                    code="INVALID_OTP",
                    message="Invalid or expired verification code. Please request a new code."
                )
            ).model_dump()
        )

    # Get user
    user = db.query(User).filter(
        User.email == request.email.lower().strip()).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ErrorResponse(
                status="error",
                message="User not found",
                error=ErrorDetail(
                    code="USER_NOT_FOUND",
                    message="No account found with this email address."
                )
            ).model_dump()
        )

    # Activate user account
    user.is_active = True
    db.commit()
    db.refresh(user)

    # Update last login
    update_user_last_login(user, db)

    # Create access token
    access_token = create_access_token(
        data={
            "sub": user.email,
            "user_id": user.id
        }
    )

    # Create refresh token
    refresh_token = create_refresh_token(
        data={
            "sub": user.email,
            "user_id": user.id
        }
    )

    # Set refresh token in HTTP-only cookie
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
        httponly=True,
        secure=False,  # Set to True in production with HTTPS
        samesite="lax",
        path="/"
    )

    token_data = TokenResponse(
        access_token=access_token,
        token_type="bearer",
        user=UserResponse.model_validate(user)
    )

    return APIResponse(
        status="success",
        message="Email verified successfully. Your account has been activated.",
        data=token_data.model_dump()
    )


@router.post("/change-password", response_model=APIResponse, status_code=status.HTTP_200_OK, tags=["Authentication"])
def change_password(
    request: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Change user password (requires authentication).

    Args:
        request: Change password request with current and new password
        current_user: Current authenticated user (from dependency)
        db: Database session

    Returns:
        Standard API response with success message

    Raises:
        HTTPException: If current password is incorrect
    """
    # Verify current password
    if not verify_user_password(current_user, request.current_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ErrorResponse(
                status="error",
                message="Password change failed",
                error=ErrorDetail(
                    code="INVALID_PASSWORD",
                    message="Current password is incorrect."
                )
            ).model_dump()
        )

    # Set new password
    set_user_password(current_user, request.new_password, db)

    return APIResponse(
        status="success",
        message="Password changed successfully",
        data={
            "user_id": current_user.id,
            "updated_at": datetime.utcnow().isoformat()
        }
    )


@router.post("/logout", response_model=APIResponse, status_code=status.HTTP_200_OK, tags=["Authentication"])
def logout(response: Response, current_user: User = Depends(get_current_user)):
    """
    Logout endpoint (token validation handled by dependency).
    Clears refresh token cookie.

    Note: JWT tokens are stateless. For true logout, implement token blacklisting
    or use refresh tokens. This endpoint validates the token is still valid.

    Args:
        response: FastAPI response object for clearing cookies
        current_user: Current authenticated user (from dependency)

    Returns:
        Standard API response with success message
    """
    # Clear refresh token cookie
    response.delete_cookie(
        key="refresh_token",
        path="/",
        samesite="lax"
    )

    return APIResponse(
        status="success",
        message="Logged out successfully",
        data={
            "user_id": current_user.id,
            "logged_out_at": datetime.utcnow().isoformat()
        }
    )


@router.post("/refresh", response_model=APIResponse, status_code=status.HTTP_200_OK, tags=["Authentication"])
def refresh_token(request: Request, response: Response, db: Session = Depends(get_db)):
    """
    Refresh access token using refresh token from HTTP-only cookie.

    Args:
        request: FastAPI request object to read cookies
        response: FastAPI response object for setting cookies
        db: Database session

    Returns:
        Standard API response with new access token

    Raises:
        HTTPException: If refresh token is invalid or expired
    """
    # Get refresh token from cookie
    refresh_token_value = request.cookies.get("refresh_token")

    if not refresh_token_value:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ErrorResponse(
                status="error",
                message="Refresh token not found",
                error=ErrorDetail(
                    code="REFRESH_TOKEN_MISSING",
                    message="Refresh token cookie is missing. Please log in again."
                )
            ).model_dump()
        )

    # Verify refresh token
    payload = verify_refresh_token(refresh_token_value)

    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ErrorResponse(
                status="error",
                message="Invalid refresh token",
                error=ErrorDetail(
                    code="INVALID_REFRESH_TOKEN",
                    message="Refresh token is invalid or expired. Please log in again."
                )
            ).model_dump()
        )

    # Get user from token
    email = payload.get("sub")
    user_id = payload.get("user_id")

    if not email or not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ErrorResponse(
                status="error",
                message="Invalid token payload",
                error=ErrorDetail(
                    code="INVALID_TOKEN_PAYLOAD",
                    message="Refresh token payload is invalid."
                )
            ).model_dump()
        )

    # Verify user exists and is active
    user = db.query(User).filter(
        User.email == email, User.id == user_id).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ErrorResponse(
                status="error",
                message="User not found",
                error=ErrorDetail(
                    code="USER_NOT_FOUND",
                    message="User associated with refresh token not found."
                )
            ).model_dump()
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=ErrorResponse(
                status="error",
                message="User account is inactive",
                error=ErrorDetail(
                    code="ACCOUNT_INACTIVE",
                    message="User account is inactive."
                )
            ).model_dump()
        )

    # Create new access token
    new_access_token = create_access_token(
        data={
            "sub": user.email,
            "user_id": user.id
        }
    )

    # Optionally rotate refresh token (create new one)
    new_refresh_token = create_refresh_token(
        data={
            "sub": user.email,
            "user_id": user.id
        }
    )

    # Set new refresh token in HTTP-only cookie
    response.set_cookie(
        key="refresh_token",
        value=new_refresh_token,
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
        httponly=True,
        secure=False,  # Set to True in production with HTTPS
        samesite="lax",
        path="/"
    )

    token_data = TokenResponse(
        access_token=new_access_token,
        token_type="bearer",
        user=UserResponse.model_validate(user)
    )

    return APIResponse(
        status="success",
        message="Token refreshed successfully",
        data=token_data.model_dump()
    )


@router.get("/me", response_model=APIResponse, tags=["Authentication"])
def get_current_user_info(current_user: User = Depends(get_current_user)):
    """
    Get current authenticated user information.

    Args:
        current_user: Current authenticated user (from dependency)

    Returns:
        Standard API response with user information
    """
    return APIResponse(
        status="success",
        message="User information retrieved successfully",
        data=UserResponse.model_validate(current_user).model_dump()
    )


@router.put("/profile", response_model=APIResponse, status_code=status.HTTP_200_OK, tags=["Authentication"])
def update_profile(
    request: UserUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Update user profile information (category, GST, shipping address).

    Args:
        request: Profile update request with fields to update
        current_user: Current authenticated user (from dependency)
        db: Database session

    Returns:
        Standard API response with updated user information

    Raises:
        HTTPException: If validation fails
    """
    try:
        updated_user = update_user_profile(
            user=current_user,
            db=db,
            category=request.category,
            gst_number=request.gst_number,
            shipping_address1=request.shipping_address1,
            shipping_address2=request.shipping_address2,
            shipping_pin=request.shipping_pin,
            shipping_city=request.shipping_city,
            shipping_state=request.shipping_state,
            shipping_country=request.shipping_country
        )
        
        return APIResponse(
            status="success",
            message="Profile updated successfully",
            data=UserResponse.model_validate(updated_user).model_dump()
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ErrorResponse(
                status="error",
                message="Profile update failed",
                error=ErrorDetail(
                    code="VALIDATION_ERROR",
                    message=str(e)
                )
            ).model_dump()
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                status="error",
                message="Internal server error",
                error=ErrorDetail(
                    code="INTERNAL_ERROR",
                    message="An error occurred while updating your profile. Please try again."
                )
            ).model_dump()
        )
