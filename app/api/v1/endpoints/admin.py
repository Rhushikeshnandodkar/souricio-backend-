"""
Admin API endpoints
"""
from fastapi import APIRouter, HTTPException, status, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import select
from fastapi_pagination import Page, Params
from fastapi_pagination.ext.sqlalchemy import paginate
from typing import Optional
import json
from datetime import datetime, timezone
from app.db.models.base import Base
from app.db.database import engine
from app.dependencies import get_db, get_current_owner, get_current_admin
from app.db.models.user import User, UserRole
from app.db.models.quote import Quote, QuoteStatus, QuoteItem
from app.db.models.order import Order, OrderStatus
from app.db.models.product import Product
from app.schemas.auth import AssignRoleRequest, CreateOwnerRequest, CreateUserRequest, UserResponse, UserStats, UsersListResponse, UserUpdateRequest
from app.schemas.response import APIResponse, ErrorResponse, ErrorDetail
from app.schemas.dashboard import (
    DashboardStatsResponse,
    OverviewStats,
    QuoteStats,
    RevenueDataPoint,
    QuoteTrendDataPoint,
    UserGrowthDataPoint
)
from app.schemas.quote import OwnerQuoteSummaryResponse
from sqlalchemy import func, case, and_
from datetime import timedelta
from app.services.auth_service import update_user_role, create_user_with_password, create_active_user_with_password, update_user_profile
from app.services.cart_service import clear_user_cart
from sqlalchemy.exc import IntegrityError

router = APIRouter()


@router.post("/bootstrap-owner", response_model=APIResponse, status_code=status.HTTP_201_CREATED, tags=["Admin"])
async def bootstrap_owner(
    request: CreateOwnerRequest,
    db: Session = Depends(get_db)
):
    """
    Create the first owner user. This endpoint only works if no owner exists in the database.
    After the first owner is created, this endpoint will require owner authentication.

    This is a bootstrap endpoint for initial setup. Use this to create your first owner account.

    Args:
        request: Create owner request with email and password
        db: Database session

    Returns:
        Standard API response with created owner user information

    Raises:
        HTTPException: If owner already exists, user creation fails, or other errors
    """
    try:
        # Check if any owner exists
        existing_owner = db.query(User).filter(
            User.role == UserRole.OWNER).first()

        if existing_owner:
            # If owner exists, require authentication
            error_response = ErrorResponse(
                status="error",
                message="Owner already exists",
                error=ErrorDetail(
                    code="OWNER_EXISTS",
                    message="An owner already exists. Please use the assign-role endpoint with owner authentication to create additional owners."
                )
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=json.loads(error_response.model_dump_json())
            )

        # Create the first owner user
        # Note: We create as active and skip OTP verification for bootstrap
        owner_user = await create_user_with_password(
            request.email,
            request.password,
            db,
            role=UserRole.OWNER
        )

        # Activate the owner immediately (skip email verification for bootstrap)
        owner_user.is_active = True
        db.commit()
        db.refresh(owner_user)

        return APIResponse(
            status="success",
            message="First owner user created successfully",
            data={
                "user": UserResponse.model_validate(owner_user).model_dump()
            }
        )
    except ValueError as e:
        # User already exists
        error_response = ErrorResponse(
            status="error",
            message="User creation failed",
            error=ErrorDetail(
                code="USER_ALREADY_EXISTS",
                message=str(e)
            )
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=json.loads(error_response.model_dump_json())
        )
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        # Internal server error
        error_response = ErrorResponse(
            status="error",
            message="Internal server error",
            error=ErrorDetail(
                code="INTERNAL_ERROR",
                message="An error occurred while creating owner user. Please try again."
            )
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=json.loads(error_response.model_dump_json())
        )


@router.post("/reset-db", tags=["Admin"])
def reset_database():
    """
    Reset database by dropping and recreating all tables.
    WARNING: This will delete all data! Use only in development.
    """
    try:
        Base.metadata.drop_all(bind=engine)
        Base.metadata.create_all(bind=engine)
        return {"message": "Database reset successfully"}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error resetting database: {str(e)}"
        )


@router.get("/users", response_model=APIResponse, tags=["Admin"])
def get_all_users(
    params: Params = Depends(),
    search: Optional[str] = Query(
        None, description="Search users by email (case-insensitive)"),
    current_user: User = Depends(get_current_owner),
    db: Session = Depends(get_db)
):
    """
    Retrieve paginated list of all users with statistics. Only owners can access this endpoint.
    Uses fastapi-pagination for automatic pagination handling and includes user statistics.

    Args:
        params: Pagination parameters
        search: Optional search query to filter users by email (case-insensitive)
        current_user: Current authenticated user (must be owner)
        db: Database session

    Returns:
        Standard API response with paginated list of users and statistics

    Raises:
        HTTPException: If an error occurs while retrieving users
    """
    try:
        # Build base query
        query = select(User)

        # Apply search filter if provided
        if search and search.strip():
            search_term = f"%{search.strip()}%"
            query = query.filter(User.email.ilike(search_term))

        # Calculate statistics (without search filter for total counts)
        total_users = db.query(User).count()
        active_users = db.query(User).filter(User.is_active == True).count()
        inactive_users = db.query(User).filter(User.is_active == False).count()

        # Calculate users created this month
        now = datetime.now(timezone.utc)
        first_day_of_month = datetime(
            now.year, now.month, 1, tzinfo=timezone.utc)
        users_created_this_month = db.query(User).filter(
            User.created_at >= first_day_of_month).count()

        # Create stats object
        stats = UserStats(
            total_users=total_users,
            active_users=active_users,
            inactive_users=inactive_users,
            users_created_this_month=users_created_this_month
        )

        # Get paginated results with search filter applied
        def transform_user(user: User) -> UserResponse:
            # Count quotes for this user
            quote_count = db.query(Quote).filter(
                Quote.user_id == user.id).count()
            user_response = UserResponse.model_validate(user)
            user_response.total_quotes = quote_count
            return user_response

        paginated_result = paginate(
            db,
            query.order_by(User.created_at.desc(), User.id),
            params=params,
            transformer=lambda items: [transform_user(user) for user in items]
        )

        # Combine pagination data with stats
        users_list_response = UsersListResponse(
            items=paginated_result.items,
            total=paginated_result.total,
            page=paginated_result.page,
            size=paginated_result.size,
            pages=paginated_result.pages,
            stats=stats
        )

        return APIResponse(
            status="success",
            message="Users retrieved successfully",
            data=users_list_response.model_dump()
        )
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        print(f"Error retrieving users: {error_trace}")
        error_response = ErrorResponse(
            status="error",
            message="Internal server error",
            error=ErrorDetail(
                code="INTERNAL_ERROR",
                message="An error occurred while retrieving users. Please try again."
            )
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=json.loads(error_response.model_dump_json())
        )


@router.get("/users/{user_id}", response_model=APIResponse, tags=["Admin"])
def get_user_by_id(
    user_id: int,
    current_user: User = Depends(get_current_owner),
    db: Session = Depends(get_db)
):
    """
    Retrieve a single user by ID. Only owners can access this endpoint.

    Args:
        user_id: ID of the user to retrieve
        current_user: Current authenticated user (must be owner)
        db: Database session

    Returns:
        Standard API response with user information

    Raises:
        HTTPException: If user not found or other errors occur
    """
    try:
        user = db.query(User).filter(User.id == user_id).first()

        if not user:
            error_response = ErrorResponse(
                status="error",
                message="User not found",
                error=ErrorDetail(
                    code="USER_NOT_FOUND",
                    message=f"User with ID {user_id} does not exist."
                )
            )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=json.loads(error_response.model_dump_json())
            )

        # Count quotes for this user
        quote_count = db.query(Quote).filter(Quote.user_id == user.id).count()
        user_response = UserResponse.model_validate(user)
        user_response.total_quotes = quote_count

        return APIResponse(
            status="success",
            message="User retrieved successfully",
            data={
                "user": user_response.model_dump()
            }
        )
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        print(f"Error retrieving user: {error_trace}")
        error_response = ErrorResponse(
            status="error",
            message="Internal server error",
            error=ErrorDetail(
                code="INTERNAL_ERROR",
                message="An error occurred while retrieving user. Please try again."
            )
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=json.loads(error_response.model_dump_json())
        )


@router.put("/users/{user_id}", response_model=APIResponse, status_code=status.HTTP_200_OK, tags=["Admin"])
def update_user(
    user_id: int,
    request: UserUpdateRequest,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    Update user profile information (category, GST, shipping address). Only admins can update users.

    Args:
        user_id: ID of the user to update
        request: Profile update request with fields to update
        current_user: Current authenticated user (must be admin)
        db: Database session

    Returns:
        Standard API response with updated user information

    Raises:
        HTTPException: If user not found or validation fails
    """
    try:
        # Get user by ID
        user = db.query(User).filter(User.id == user_id).first()

        if not user:
            error_response = ErrorResponse(
                status="error",
                message="User not found",
                error=ErrorDetail(
                    code="USER_NOT_FOUND",
                    message=f"User with ID {user_id} does not exist."
                )
            )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=json.loads(error_response.model_dump_json())
            )

        # Update user profile
        updated_user = update_user_profile(
            user=user,
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
            message="User profile updated successfully",
            data={
                "user": UserResponse.model_validate(updated_user).model_dump()
            }
        )
    except ValueError as e:
        error_response = ErrorResponse(
            status="error",
            message="Profile update failed",
            error=ErrorDetail(
                code="VALIDATION_ERROR",
                message=str(e)
            )
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=json.loads(error_response.model_dump_json())
        )
    except HTTPException:
        raise
    except Exception as e:
        error_response = ErrorResponse(
            status="error",
            message="Internal server error",
            error=ErrorDetail(
                code="INTERNAL_ERROR",
                message="An error occurred while updating user profile. Please try again."
            )
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=json.loads(error_response.model_dump_json())
        )
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        print(f"Error retrieving user: {error_trace}")
        error_response = ErrorResponse(
            status="error",
            message="Internal server error",
            error=ErrorDetail(
                code="INTERNAL_ERROR",
                message="An error occurred while retrieving user. Please try again."
            )
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=json.loads(error_response.model_dump_json())
        )


@router.post("/users", response_model=APIResponse, status_code=status.HTTP_201_CREATED, tags=["Admin"])
def create_user(
    request: CreateUserRequest,
    current_user: User = Depends(get_current_owner),
    db: Session = Depends(get_db)
):
    """
    Create a new user with email and password. Only owners can create users.
    The user will be created as active immediately (no email verification required).

    Args:
        request: Create user request with email and password
        current_user: Current authenticated user (must be owner)
        db: Database session

    Returns:
        Standard API response with created user information

    Raises:
        HTTPException: If user already exists or other errors occur
    """
    try:
        # Create user as active (no OTP verification required)
        new_user = create_active_user_with_password(
            email=request.email,
            password=request.password,
            db=db,
            role=UserRole.USER,
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
            message="User created successfully",
            data={
                "user": UserResponse.model_validate(new_user).model_dump()
            }
        )
    except ValueError as e:
        # User already exists
        error_response = ErrorResponse(
            status="error",
            message="User creation failed",
            error=ErrorDetail(
                code="USER_ALREADY_EXISTS",
                message=str(e)
            )
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=json.loads(error_response.model_dump_json())
        )
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        # Internal server error
        error_response = ErrorResponse(
            status="error",
            message="Internal server error",
            error=ErrorDetail(
                code="INTERNAL_ERROR",
                message="An error occurred while creating user. Please try again."
            )
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=json.loads(error_response.model_dump_json())
        )


@router.post("/users/assign-role", response_model=APIResponse, status_code=status.HTTP_200_OK, tags=["Admin"])
def assign_user_role(
    request: AssignRoleRequest,
    current_user: User = Depends(get_current_owner),
    db: Session = Depends(get_db)
):
    """
    Assign a role to a user. Only owners can assign roles.

    Args:
        request: Assign role request with email and role
        current_user: Current authenticated user (must be owner)
        db: Database session

    Returns:
        Standard API response with updated user information

    Raises:
        HTTPException: If user not found, invalid role, or other errors
    """
    try:
        # Update user role using service function
        updated_user = update_user_role(request.email, request.role, db)

        return APIResponse(
            status="success",
            message="User role updated successfully",
            data={
                "user": UserResponse.model_validate(updated_user).model_dump()
            }
        )
    except ValueError as e:
        # User not found
        error_response = ErrorResponse(
            status="error",
            message="User not found",
            error=ErrorDetail(
                code="USER_NOT_FOUND",
                message=str(e)
            )
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=json.loads(error_response.model_dump_json())
        )
    except Exception as e:
        # Internal server error
        error_response = ErrorResponse(
            status="error",
            message="Internal server error",
            error=ErrorDetail(
                code="INTERNAL_ERROR",
                message="An error occurred while updating user role. Please try again."
            )
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=json.loads(error_response.model_dump_json())
        )


@router.delete("/users/{user_id}", response_model=APIResponse, status_code=status.HTTP_200_OK, tags=["Admin"])
def delete_user(
    user_id: int,
    current_user: User = Depends(get_current_owner),
    db: Session = Depends(get_db)
):
    """
    Delete a user by ID. Only owners can delete users.
    This endpoint will:
    - Delete all cart items associated with the user
    - Preserve quotes (they remain in the database)
    - Delete the user record

    Args:
        user_id: ID of the user to delete
        current_user: Current authenticated user (must be owner)
        db: Database session

    Returns:
        Standard API response with success message

    Raises:
        HTTPException: If user not found, user has quotes preventing deletion, or other errors
    """
    try:
        # Check if user exists
        user = db.query(User).filter(User.id == user_id).first()

        if not user:
            error_response = ErrorResponse(
                status="error",
                message="User not found",
                error=ErrorDetail(
                    code="USER_NOT_FOUND",
                    message=f"User with ID {user_id} does not exist."
                )
            )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=json.loads(error_response.model_dump_json())
            )

        # Prevent deleting yourself
        if user.id == current_user.id:
            error_response = ErrorResponse(
                status="error",
                message="Cannot delete own account",
                error=ErrorDetail(
                    code="CANNOT_DELETE_SELF",
                    message="You cannot delete your own account."
                )
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=json.loads(error_response.model_dump_json())
            )

        # Check if user has quotes
        quote_count = db.query(Quote).filter(Quote.user_id == user_id).count()
        if quote_count > 0:
            error_response = ErrorResponse(
                status="error",
                message="Cannot delete user with quotes",
                error=ErrorDetail(
                    code="USER_HAS_QUOTES",
                    message=f"Cannot delete user. User has {quote_count} quote(s) associated. Quotes must be preserved and cannot be deleted."
                )
            )
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=json.loads(error_response.model_dump_json())
            )

        # Delete all cart items for the user
        deleted_cart_count = clear_user_cart(db, user_id)

        # Delete the user
        db.delete(user)
        db.commit()

        return APIResponse(
            status="success",
            message=f"User deleted successfully. {deleted_cart_count} cart item(s) were also removed.",
            data={
                "deleted_user_id": user_id,
                "deleted_cart_items": deleted_cart_count
            }
        )
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except IntegrityError as e:
        # Handle foreign key constraint violations
        db.rollback()
        error_response = ErrorResponse(
            status="error",
            message="Cannot delete user",
            error=ErrorDetail(
                code="FOREIGN_KEY_CONSTRAINT",
                message="Cannot delete user due to database constraints. User may have associated quotes or other related data."
            )
        )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=json.loads(error_response.model_dump_json())
        )
    except Exception as e:
        # Rollback on error
        db.rollback()
        import traceback
        error_trace = traceback.format_exc()
        print(f"Error deleting user: {error_trace}")
        error_response = ErrorResponse(
            status="error",
            message="Internal server error",
            error=ErrorDetail(
                code="INTERNAL_ERROR",
                message="An error occurred while deleting user. Please try again."
            )
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=json.loads(error_response.model_dump_json())
        )


@router.get("/dashboard/stats", response_model=APIResponse, tags=["Admin"])
async def get_dashboard_stats(
    start_date: Optional[str] = Query(
        None, description="Start date in ISO format (YYYY-MM-DD). Defaults to 3 months ago."),
    end_date: Optional[str] = Query(
        None, description="End date in ISO format (YYYY-MM-DD). Defaults to today."),
    group_by: Optional[str] = Query(
        "day", description="Group by period: 'day', 'week', or 'month'"),
    current_user: User = Depends(get_current_owner),
    db: Session = Depends(get_db)
):
    """
    Get comprehensive dashboard statistics including overview, quotes, revenue trends,
    quote trends, user growth, and recent activity.

    Args:
        start_date: Start date for time-based analytics (ISO format: YYYY-MM-DD)
        end_date: End date for time-based analytics (ISO format: YYYY-MM-DD)
        group_by: Grouping period for time series data (day, week, month)
        current_user: Current authenticated user (must be owner)
        db: Database session

    Returns:
        Standard API response with dashboard statistics
    """
    from app.services.cache_service import (
        get_or_cache,
        dashboard_stats_key,
        DEFAULT_TTL_DASHBOARD
    )
    
    # Generate cache key
    cache_key = dashboard_stats_key(
        start_date=start_date,
        end_date=end_date,
        group_by=group_by or "day"
    )
    
    async def fetch_dashboard_stats():
        return await _fetch_dashboard_stats_internal(
            start_date, end_date, group_by, db
        )
    
    # Get from cache or fetch
    result = await get_or_cache(
        cache_key,
        fetch_dashboard_stats,
        ttl=DEFAULT_TTL_DASHBOARD
    )
    
    return result


async def _fetch_dashboard_stats_internal(
    start_date: Optional[str],
    end_date: Optional[str],
    group_by: Optional[str],
    db: Session
) -> APIResponse:
    """Internal function to fetch dashboard stats (extracted for caching)."""
    try:
        # Parse dates with defaults
        now = datetime.now(timezone.utc)
        if end_date:
            try:
                # Handle both YYYY-MM-DD and ISO format dates
                date_str = end_date.replace(
                    'Z', '+00:00') if 'Z' in end_date else end_date
                end_dt = datetime.fromisoformat(date_str)
                if end_dt.tzinfo is None:
                    end_dt = end_dt.replace(tzinfo=timezone.utc)
                # If only date provided (no time), make it end of day to be inclusive
                if 'T' not in end_date and ' ' not in end_date:
                    end_dt = end_dt.replace(hour=23, minute=59, second=59, microsecond=999999)
            except (ValueError, AttributeError) as e:
                # Log error for debugging
                print(f"Error parsing end_date '{end_date}': {e}")
                end_dt = now
        else:
            end_dt = now

        if start_date:
            try:
                # Handle both YYYY-MM-DD and ISO format dates
                date_str = start_date.replace(
                    'Z', '+00:00') if 'Z' in start_date else start_date
                start_dt = datetime.fromisoformat(date_str)
                if start_dt.tzinfo is None:
                    start_dt = start_dt.replace(tzinfo=timezone.utc)
                # If only date provided (no time), make it start of day
                if 'T' not in start_date and ' ' not in start_date:
                    start_dt = start_dt.replace(hour=0, minute=0, second=0, microsecond=0)
            except (ValueError, AttributeError) as e:
                # Log error for debugging
                print(f"Error parsing start_date '{start_date}': {e}")
                start_dt = end_dt - timedelta(days=90)
        else:
            start_dt = end_dt - timedelta(days=90)

        # Ensure start_date is before end_date
        if start_dt > end_dt:
            start_dt = end_dt - timedelta(days=90)

        # Overview Stats - these represent current state, not filtered by date range
        # Total users should show ALL users regardless of when they were created
        total_users = db.query(User).count()

        # Active users should show ALL active users regardless of when they were created
        active_users = db.query(User).filter(User.is_active == True).count()

        total_quotes = db.query(Quote).filter(
            and_(
                Quote.created_at >= start_dt,
                Quote.created_at <= end_dt
            )
        ).count()

        # Note: Total products is not filtered by date range as it represents
        # the current catalogue size, not products created within the period
        # Exclude soft-deleted products (where deleted_at is not NULL)
        total_products = db.query(Product).filter(Product.deleted_at.is_(None)).count()

        # Total revenue (sum of ALL order totals, not filtered by date range)
        # Only count orders that are not cancelled
        # This represents the total revenue from all orders, similar to how total_users shows all users
        total_revenue_result = db.query(func.sum(Order.total)).filter(
            and_(
                Order.total.isnot(None),
                Order.status != OrderStatus.CANCELLED
            )
        ).scalar()
        total_revenue = total_revenue_result if total_revenue_result else 0

        overview = OverviewStats(
            total_users=total_users,
            active_users=active_users,
            total_quotes=total_quotes,
            total_products=total_products,
            total_revenue=total_revenue
        )

        # Quote Statistics by Status - show ALL quotes (not filtered by date range)
        # This represents the current state of all quotes, similar to total_users
        quote_status_counts = (
            db.query(Quote.status, func.count(Quote.id))
            .group_by(Quote.status)
            .all()
        )

        status_dict = {status.value: 0 for status in QuoteStatus}
        for status, count in quote_status_counts:
            status_dict[status.value] = count

        # Total quote value - filtered by date range
        total_quote_value_result = db.query(func.sum(Quote.total)).filter(
            and_(
                Quote.created_at >= start_dt,
                Quote.created_at <= end_dt,
                Quote.total.isnot(None)
            )
        ).scalar()
        total_quote_value = total_quote_value_result if total_quote_value_result else 0

        quote_stats = QuoteStats(
            draft=status_dict.get("draft", 0),
            pending=status_dict.get("pending", 0),
            approved=status_dict.get("approved", 0),
            rejected=status_dict.get("rejected", 0),
            expired=status_dict.get("expired", 0),
            total_value=total_quote_value
        )

        # Revenue Trend (time series) - based on orders, not quotes
        # Determine date truncation based on group_by
        # Normalize group_by to lowercase
        group_by_normalized = (group_by or "day").lower()
        
        # Create date_trunc functions for different models
        if group_by_normalized == "week":
            order_date_trunc = func.date_trunc('week', Order.created_at)
            quote_date_trunc = func.date_trunc('week', Quote.created_at)
        elif group_by_normalized == "month":
            order_date_trunc = func.date_trunc('month', Order.created_at)
            quote_date_trunc = func.date_trunc('month', Quote.created_at)
        else:  # day (default)
            order_date_trunc = func.date_trunc('day', Order.created_at)
            quote_date_trunc = func.date_trunc('day', Quote.created_at)

        # Debug logging
        print(
            f"Dashboard stats - start_dt: {start_dt}, end_dt: {end_dt}, group_by: {group_by_normalized}")

        revenue_trend_data = (
            db.query(
                order_date_trunc.label('period'),
                func.sum(Order.total).label('revenue')
            )
            .filter(
                and_(
                    Order.created_at >= start_dt,
                    Order.created_at <= end_dt,
                    Order.total.isnot(None),
                    Order.status != OrderStatus.CANCELLED
                )
            )
            .group_by('period')
            .order_by('period')
            .all()
        )

        revenue_trend = [
            RevenueDataPoint(
                date=row.period.isoformat() if isinstance(
                    row.period, datetime) else str(row.period),
                revenue=row.revenue if row.revenue else 0
            )
            for row in revenue_trend_data
        ]

        # Quote Trend (time series with status breakdown)
        quote_trend_data = (
            db.query(
                quote_date_trunc.label('period'),
                func.count(Quote.id).label('count'),
                func.sum(case((Quote.status == QuoteStatus.DRAFT, 1), else_=0)).label(
                    'draft'),
                func.sum(case((Quote.status == QuoteStatus.PENDING, 1), else_=0)).label(
                    'pending'),
                func.sum(case((Quote.status == QuoteStatus.APPROVED, 1), else_=0)).label(
                    'approved'),
                func.sum(case((Quote.status == QuoteStatus.REJECTED, 1), else_=0)).label(
                    'rejected'),
                func.sum(case((Quote.status == QuoteStatus.EXPIRED, 1), else_=0)).label(
                    'expired'),
            )
            .filter(
                and_(
                    Quote.created_at >= start_dt,
                    Quote.created_at <= end_dt
                )
            )
            .group_by('period')
            .order_by('period')
            .all()
        )

        quote_trend = [
            QuoteTrendDataPoint(
                date=row.period.isoformat() if isinstance(
                    row.period, datetime) else str(row.period),
                count=row.count or 0,
                draft=int(row.draft or 0),
                pending=int(row.pending or 0),
                approved=int(row.approved or 0),
                rejected=int(row.rejected or 0),
                expired=int(row.expired or 0)
            )
            for row in quote_trend_data
        ]

        # User Growth Trend (cumulative)
        # Use the same date_trunc as revenue/quote trends
        user_growth_data = (
            db.query(
                func.date_trunc('day' if group_by_normalized == "day" else 'week' if group_by_normalized ==
                                "week" else 'month', User.created_at).label('period'),
                func.count(User.id).label('new_users')
            )
            .filter(
                and_(
                    User.created_at >= start_dt,
                    User.created_at <= end_dt
                )
            )
            .group_by('period')
            .order_by('period')
            .all()
        )

        # Calculate cumulative totals
        cumulative_total = db.query(func.count(User.id)).filter(
            User.created_at < start_dt
        ).scalar() or 0

        user_growth = []
        running_total = cumulative_total
        for row in user_growth_data:
            running_total += row.new_users or 0
            user_growth.append(
                UserGrowthDataPoint(
                    date=row.period.isoformat() if isinstance(
                        row.period, datetime) else str(row.period),
                    total_users=running_total,
                    new_users=row.new_users or 0
                )
            )

        # Recent Quotes (last 10)
        recent_quotes_query = (
            db.query(Quote)
            .join(User)
            .order_by(Quote.created_at.desc())
            .limit(10)
            .all()
        )

        recent_quotes = []
        for quote in recent_quotes_query:
            item_count = db.query(func.count(QuoteItem.id)).filter(
                QuoteItem.quote_id == quote.id
            ).scalar() or 0

            has_custom_pricing = any(
                item.requires_custom_price for item in quote.items
            ) if quote.items else False

            recent_quotes.append(
                OwnerQuoteSummaryResponse(
                    id=quote.id,
                    quote_number=quote.quote_number,
                    user_id=quote.user_id,
                    user_email=quote.user.email if quote.user else "",
                    status=quote.status.value,
                    expires_at=quote.expires_at,
                    subtotal=quote.subtotal,
                    total_tax=quote.total_tax,
                    total=quote.total,
                    tax_breakdown=quote.tax_breakdown,
                    has_custom_pricing=has_custom_pricing,
                    item_count=item_count,
                    created_at=quote.created_at,
                    updated_at=quote.updated_at
                )
            )

        # Recent Users (last 10)
        recent_users_query = (
            db.query(User)
            .order_by(User.created_at.desc())
            .limit(10)
            .all()
        )

        recent_users = []
        for user in recent_users_query:
            quote_count = db.query(func.count(Quote.id)).filter(
                Quote.user_id == user.id
            ).scalar() or 0
            user_response = UserResponse.model_validate(user)
            user_response.total_quotes = quote_count
            recent_users.append(user_response)

        # Build response
        dashboard_stats = DashboardStatsResponse(
            overview=overview,
            quotes=quote_stats,
            revenue_trend=revenue_trend,
            quote_trend=quote_trend,
            user_growth=user_growth,
            recent_quotes=recent_quotes,
            recent_users=recent_users
        )

        return APIResponse(
            status="success",
            message="Dashboard statistics retrieved successfully",
            data=dashboard_stats.model_dump()
        )
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        print(f"Error retrieving dashboard stats: {error_trace}")
        error_response = ErrorResponse(
            status="error",
            message="Internal server error",
            error=ErrorDetail(
                code="INTERNAL_ERROR",
                message="An error occurred while retrieving dashboard statistics. Please try again."
            )
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=json.loads(error_response.model_dump_json())
        )
