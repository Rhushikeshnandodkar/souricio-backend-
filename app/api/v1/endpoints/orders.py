"""
Order API endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, status as http_status, Query
from fastapi.responses import Response
from sqlalchemy.orm import Session
from typing import Optional
from decimal import Decimal
from datetime import datetime
import json

from app.dependencies import get_db, get_current_user, get_current_admin, get_current_owner
from app.db.models.user import User, UserRole
from app.schemas.order import OrderCreate, OrderResponse, OrderSummaryResponse, OwnerOrderSummaryResponse, OrderDetailResponse, AdminOrderUpdate
from app.schemas.response import APIResponse, ErrorResponse, ErrorDetail
from app.services.order_service import (
    place_order_from_quote,
    get_user_orders,
    get_all_orders,
    get_all_orders_advanced,
    get_order_by_id,
    get_order_detail_by_id,
    update_order_status
)
from app.services.pdf_service import generate_invoice_pdf

router = APIRouter()


@router.post("", response_model=APIResponse, status_code=http_status.HTTP_201_CREATED, tags=["Orders"])
def place_order(
    order_data: OrderCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Place an order from an approved quote.
    
    This endpoint allows authenticated users to place orders from their approved quotes.
    The quote must be:
    - Approved status
    - Not expired
    - Have a valid total amount
    - Not already converted to an order
    
    Args:
        order_data: Order creation data (quote_id)
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        Standard API response with created order
        
    Raises:
        HTTPException: If validation fails or order creation fails
    """
    try:
        order = place_order_from_quote(
            db=db,
            quote_id=order_data.quote_id,
            user_id=current_user.id
        )
        return APIResponse(
            status="success",
            message="Order placed successfully",
            data=order.model_dump()
        )
    except ValueError as e:
        error_message = str(e)
        
        # Determine appropriate HTTP status code based on error message
        if "not found" in error_message.lower():
            status_code = http_status.HTTP_404_NOT_FOUND
            error_code = "QUOTE_NOT_FOUND"
        elif "does not belong" in error_message.lower():
            status_code = http_status.HTTP_403_FORBIDDEN
            error_code = "QUOTE_ACCESS_DENIED"
        elif "already exists" in error_message.lower():
            status_code = http_status.HTTP_409_CONFLICT
            error_code = "ORDER_ALREADY_EXISTS"
        elif "expired" in error_message.lower():
            status_code = http_status.HTTP_400_BAD_REQUEST
            error_code = "QUOTE_EXPIRED"
        elif "must be approved" in error_message.lower() or "status" in error_message.lower():
            status_code = http_status.HTTP_400_BAD_REQUEST
            error_code = "INVALID_QUOTE_STATUS"
        elif "valid total" in error_message.lower():
            status_code = http_status.HTTP_400_BAD_REQUEST
            error_code = "INVALID_QUOTE_TOTAL"
        else:
            status_code = http_status.HTTP_400_BAD_REQUEST
            error_code = "ORDER_PLACEMENT_ERROR"
        
        error_response = ErrorResponse(
            status="error",
            message="Failed to place order",
            error=ErrorDetail(
                code=error_code,
                message=error_message
            )
        )
        raise HTTPException(
            status_code=status_code,
            detail=json.loads(error_response.model_dump_json())
        )
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        print(f"Error placing order: {error_trace}")
        print(f"Exception type: {type(e).__name__}")
        print(f"Exception message: {str(e)}")
        
        # Try to extract more specific error information
        error_message = str(e)
        if not error_message or error_message == "":
            error_message = f"An unexpected error occurred: {type(e).__name__}"
        
        error_response = ErrorResponse(
            status="error",
            message="Internal server error",
            error=ErrorDetail(
                code="INTERNAL_ERROR",
                message=f"An unexpected error occurred while placing the order: {error_message}. Please check server logs for details."
            )
        )
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=json.loads(error_response.model_dump_json())
        )


@router.get("", response_model=APIResponse, tags=["Orders"])
def list_orders(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000,
                       description="Maximum number of records to return"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get orders with pagination.
    Owners see all orders, regular users see only their own orders.

    Args:
        skip: Number of records to skip
        limit: Maximum number of records to return
        current_user: Current authenticated user
        db: Database session

    Returns:
        Standard API response with paginated orders list
    """
    try:
        # If user is an owner, return all orders; otherwise return only their orders
        if current_user.role == UserRole.OWNER:
            orders, total = get_all_orders(
                db=db,
                skip=skip,
                limit=limit
            )
        else:
            orders, total = get_user_orders(
                db=db,
                user_id=current_user.id,
                skip=skip,
                limit=limit
            )
        return APIResponse(
            status="success",
            message="Orders retrieved successfully",
            data={
                "orders": [order.model_dump() for order in orders],
                "total": total,
                "skip": skip,
                "limit": limit
            }
        )
    except Exception as e:
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                status="error",
                message="Failed to retrieve orders",
                error=ErrorDetail(
                    code="ORDERS_FETCH_ERROR",
                    message=str(e)
                )
            ).model_dump()
        )


@router.get("/{order_id}", response_model=APIResponse, tags=["Orders"])
def get_order(
    order_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get order details by ID.
    Owners can view any order, regular users can only view their own orders.

    Args:
        order_id: Order ID
        current_user: Current authenticated user
        db: Database session

    Returns:
        Standard API response with order details
    """
    try:
        # If user is an owner, allow viewing any order; otherwise restrict to their own orders
        if current_user.role == UserRole.OWNER:
            order = get_order_by_id(db, order_id, user_id=None)
        else:
            order = get_order_by_id(db, order_id, current_user.id)

        if not order:
            raise HTTPException(
                status_code=http_status.HTTP_404_NOT_FOUND,
                detail=ErrorResponse(
                    status="error",
                    message="Order not found",
                    error=ErrorDetail(
                        code="ORDER_NOT_FOUND",
                        message="Order does not exist or does not belong to you"
                    )
                ).model_dump()
            )

        return APIResponse(
            status="success",
            message="Order retrieved successfully",
            data=order.model_dump()
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                status="error",
                message="Failed to retrieve order",
                error=ErrorDetail(
                    code="ORDER_FETCH_ERROR",
                    message=str(e)
                )
            ).model_dump()
        )


@router.get("/{order_id}/invoice", tags=["Orders"])
def get_order_invoice(
    order_id: int,
    download: bool = Query(False, description="Force download instead of inline display"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Generate and return PDF invoice for an order (user can only access their own orders).

    Args:
        order_id: Order ID
        download: If True, forces download; if False, displays inline
        current_user: Current authenticated user
        db: Database session

    Returns:
        PDF file response
    """
    try:
        # Users can only access their own orders (unless they're owners)
        if current_user.role == UserRole.OWNER:
            order = get_order_detail_by_id(db, order_id)
        else:
            order_detail = get_order_detail_by_id(db, order_id)
            if not order_detail or order_detail.user_id != current_user.id:
                raise HTTPException(
                    status_code=http_status.HTTP_403_FORBIDDEN,
                    detail=ErrorResponse(
                        status="error",
                        message="Access denied",
                        error=ErrorDetail(
                            code="ACCESS_DENIED",
                            message="You do not have permission to access this order"
                        )
                    ).model_dump()
                )
            order = order_detail

        if not order:
            raise HTTPException(
                status_code=http_status.HTTP_404_NOT_FOUND,
                detail=ErrorResponse(
                    status="error",
                    message="Order not found",
                    error=ErrorDetail(
                        code="ORDER_NOT_FOUND",
                        message="Order does not exist or does not belong to you"
                    )
                ).model_dump()
            )

        # Generate PDF invoice
        pdf_buffer = generate_invoice_pdf(order)
        pdf_bytes = pdf_buffer.read()

        # Determine content disposition
        disposition = "attachment" if download else "inline"
        filename = f"invoice-{order.order_number}.pdf"

        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f'{disposition}; filename="{filename}"',
                "Content-Length": str(len(pdf_bytes)),
            }
        )
    except HTTPException:
        raise
    except RuntimeError as e:
        # Handle WeasyPrint not available error
        raise HTTPException(
            status_code=http_status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=ErrorResponse(
                status="error",
                message="PDF generation service unavailable",
                error=ErrorDetail(
                    code="PDF_SERVICE_UNAVAILABLE",
                    message=str(e)
                )
            ).model_dump()
        )
    except Exception as e:
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                status="error",
                message="Failed to generate invoice",
                error=ErrorDetail(
                    code="INVOICE_GENERATION_ERROR",
                    message=str(e)
                )
            ).model_dump()
        )


# Admin endpoints - these will be registered under /admin/orders prefix
admin_router = APIRouter()


@admin_router.get("/orders", response_model=APIResponse, tags=["Admin", "Orders"])
def admin_list_orders(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000,
                       description="Maximum number of records to return"),
    status: Optional[str] = Query(None, description="Filter by status"),
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    Get all orders (admin only) with pagination and optional status filter.

    Args:
        skip: Number of records to skip
        limit: Maximum number of records to return
        status: Optional status filter
        current_user: Current authenticated admin user
        db: Database session

    Returns:
        Standard API response with paginated orders list
    """
    try:
        orders, total = get_all_orders(
            db=db,
            skip=skip,
            limit=limit,
            status=status
        )
        return APIResponse(
            status="success",
            message="Orders retrieved successfully",
            data={
                "orders": [order.model_dump() for order in orders],
                "total": total,
                "skip": skip,
                "limit": limit
            }
        )
    except Exception as e:
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                status="error",
                message="Failed to retrieve orders",
                error=ErrorDetail(
                    code="ORDERS_FETCH_ERROR",
                    message=str(e)
                )
            ).model_dump()
        )


@admin_router.get("/orders/all", response_model=APIResponse, tags=["Admin", "Orders"])
def owner_list_all_orders(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000,
                       description="Maximum number of records to return"),
    min_price: Optional[Decimal] = Query(
        None, description="Minimum price filter"),
    max_price: Optional[Decimal] = Query(
        None, description="Maximum price filter"),
    status: Optional[str] = Query(
        None, description="Filter by status (pending, processing, shipped, delivered, cancelled)"),
    created_from: Optional[str] = Query(
        None, description="Filter orders created on or after this date (ISO format: YYYY-MM-DDTHH:MM:SS)"),
    created_to: Optional[str] = Query(
        None, description="Filter orders created on or before this date (ISO format: YYYY-MM-DDTHH:MM:SS)"),
    order_number: Optional[str] = Query(
        None, description="Search by order number (partial match)"),
    user_email: Optional[str] = Query(
        None, description="Search by user email (partial match)"),
    sort_by: Optional[str] = Query(
        None, description="Sort by field (created_at, updated_at, total, order_number, status)"),
    sort_order: Optional[str] = Query(
        "desc", description="Sort order (asc, desc)"),
    current_user: User = Depends(get_current_owner),
    db: Session = Depends(get_db)
):
    """
    Get all orders with advanced filtering, searching, and sorting (owner only).

    This endpoint provides comprehensive filtering capabilities including:
    - Price range filtering (min_price, max_price)
    - Status filtering
    - Date range filtering (created dates)
    - Search by order number or user email
    - Sorting by various fields

    Args:
        skip: Number of records to skip
        limit: Maximum number of records to return
        min_price: Optional minimum price filter
        max_price: Optional maximum price filter
        status: Optional status filter
        created_from: Optional filter for orders created on or after this date (ISO format string)
        created_to: Optional filter for orders created on or before this date (ISO format string)
        order_number: Optional search by order number (partial match)
        user_email: Optional search by user email (partial match)
        sort_by: Optional field to sort by
        sort_order: Optional sort order (asc, desc)
        current_user: Current authenticated owner user
        db: Database session

    Returns:
        Standard API response with paginated orders list including user emails
    """
    try:
        # Parse datetime strings to datetime objects
        parsed_created_from = None
        parsed_created_to = None

        if created_from:
            try:
                parsed_created_from = datetime.fromisoformat(
                    created_from.replace('Z', '+00:00'))
            except (ValueError, AttributeError):
                raise ValueError(
                    f"Invalid date format for created_from: {created_from}. Use ISO format (YYYY-MM-DDTHH:MM:SS)")

        if created_to:
            try:
                parsed_created_to = datetime.fromisoformat(
                    created_to.replace('Z', '+00:00'))
            except (ValueError, AttributeError):
                raise ValueError(
                    f"Invalid date format for created_to: {created_to}. Use ISO format (YYYY-MM-DDTHH:MM:SS)")

        orders, total = get_all_orders_advanced(
            db=db,
            skip=skip,
            limit=limit,
            min_price=min_price,
            max_price=max_price,
            status=status,
            created_from=parsed_created_from,
            created_to=parsed_created_to,
            order_number=order_number,
            user_email=user_email,
            sort_by=sort_by,
            sort_order=sort_order
        )
        return APIResponse(
            status="success",
            message="Orders retrieved successfully",
            data={
                "orders": [order.model_dump() for order in orders],
                "total": total,
                "skip": skip,
                "limit": limit
            }
        )
    except ValueError as e:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail=ErrorResponse(
                status="error",
                message="Invalid filter parameters",
                error=ErrorDetail(
                    code="INVALID_FILTER",
                    message=str(e)
                )
            ).model_dump()
        )
    except Exception as e:
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                status="error",
                message="Failed to retrieve orders",
                error=ErrorDetail(
                    code="ORDERS_FETCH_ERROR",
                    message=str(e)
                )
            ).model_dump()
        )


@admin_router.get("/orders/{order_id}", response_model=APIResponse, tags=["Admin", "Orders"])
def admin_get_order(
    order_id: int,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    Get order details by ID with customer information (admin only).
    Admins can view any order with full customer details.

    Args:
        order_id: Order ID
        current_user: Current authenticated admin user
        db: Database session

    Returns:
        Standard API response with order details including customer information
    """
    try:
        order = get_order_detail_by_id(db, order_id)

        if not order:
            raise HTTPException(
                status_code=http_status.HTTP_404_NOT_FOUND,
                detail=ErrorResponse(
                    status="error",
                    message="Order not found",
                    error=ErrorDetail(
                        code="ORDER_NOT_FOUND",
                        message="Order does not exist"
                    )
                ).model_dump()
            )

        return APIResponse(
            status="success",
            message="Order retrieved successfully",
            data=order.model_dump()
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                status="error",
                message="Failed to retrieve order",
                error=ErrorDetail(
                    code="ORDER_FETCH_ERROR",
                    message=str(e)
                )
            ).model_dump()
        )


@admin_router.put("/orders/{order_id}", response_model=APIResponse, tags=["Admin", "Orders"])
def admin_update_order(
    order_id: int,
    update_data: AdminOrderUpdate,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    Update order status and notes (admin only).
    Admins can update order status and add notes.

    Args:
        order_id: Order ID
        update_data: Order update data (status, notes)
        current_user: Current authenticated admin user
        db: Database session

    Returns:
        Standard API response with updated order details
    """
    try:
        order = update_order_status(
            db=db,
            order_id=order_id,
            status=update_data.status,
            notes=update_data.notes
        )

        return APIResponse(
            status="success",
            message="Order updated successfully",
            data=order.model_dump()
        )
    except ValueError as e:
        error_message = str(e)
        if "not found" in error_message.lower():
            status_code = http_status.HTTP_404_NOT_FOUND
            error_code = "ORDER_NOT_FOUND"
        elif "invalid status" in error_message.lower():
            status_code = http_status.HTTP_400_BAD_REQUEST
            error_code = "INVALID_STATUS"
        else:
            status_code = http_status.HTTP_400_BAD_REQUEST
            error_code = "ORDER_UPDATE_ERROR"

        raise HTTPException(
            status_code=status_code,
            detail=ErrorResponse(
                status="error",
                message="Failed to update order",
                error=ErrorDetail(
                    code=error_code,
                    message=error_message
                )
            ).model_dump()
        )
    except Exception as e:
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                status="error",
                message="Failed to update order",
                error=ErrorDetail(
                    code="ORDER_UPDATE_ERROR",
                    message=str(e)
                )
            ).model_dump()
        )


@admin_router.get("/orders/{order_id}/invoice", tags=["Admin", "Orders"])
def admin_get_order_invoice(
    order_id: int,
    download: bool = Query(False, description="Force download instead of inline display"),
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    Generate and return PDF invoice for an order (admin only).
    Admins can generate invoices for any order.

    Args:
        order_id: Order ID
        download: If True, forces download; if False, displays inline
        current_user: Current authenticated admin user
        db: Database session

    Returns:
        PDF file response
    """
    try:
        order = get_order_detail_by_id(db, order_id)

        if not order:
            raise HTTPException(
                status_code=http_status.HTTP_404_NOT_FOUND,
                detail=ErrorResponse(
                    status="error",
                    message="Order not found",
                    error=ErrorDetail(
                        code="ORDER_NOT_FOUND",
                        message="Order does not exist"
                    )
                ).model_dump()
            )

        # Generate PDF invoice
        pdf_buffer = generate_invoice_pdf(order)
        pdf_bytes = pdf_buffer.read()

        # Determine content disposition
        disposition = "attachment" if download else "inline"
        filename = f"invoice-{order.order_number}.pdf"

        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f'{disposition}; filename="{filename}"',
                "Content-Length": str(len(pdf_bytes)),
            }
        )
    except HTTPException:
        raise
    except RuntimeError as e:
        # Handle WeasyPrint not available error
        raise HTTPException(
            status_code=http_status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=ErrorResponse(
                status="error",
                message="PDF generation service unavailable",
                error=ErrorDetail(
                    code="PDF_SERVICE_UNAVAILABLE",
                    message=str(e)
                )
            ).model_dump()
        )
    except Exception as e:
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                status="error",
                message="Failed to generate invoice",
                error=ErrorDetail(
                    code="INVOICE_GENERATION_ERROR",
                    message=str(e)
                )
            ).model_dump()
        )

