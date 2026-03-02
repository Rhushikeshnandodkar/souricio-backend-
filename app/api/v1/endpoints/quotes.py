"""
Quote API endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi import status as http_status
from fastapi.responses import Response
from sqlalchemy.orm import Session
from typing import Optional
from decimal import Decimal
from datetime import datetime

from app.dependencies import get_db, get_current_user, get_current_admin, get_current_owner
from app.db.models.user import User, UserRole
from app.schemas.quote import (
    QuoteCreate,
    QuoteUpdate,
    AdminQuoteUpdate,
    QuoteResponse,
    QuoteSummaryResponse,
    OwnerQuoteSummaryResponse,
)
from app.schemas.response import APIResponse, ErrorResponse, ErrorDetail
from app.services.quote_service import (
    create_quote_from_cart,
    get_user_quotes,
    get_all_quotes,
    get_all_quotes_advanced,
    get_quote_by_id,
    get_quote_detail_by_id,
    update_quote,
    update_quote_status,
    update_quote_item_price,
    update_quote_item_gst,
    delete_quote,
)
from app.services.price_history_service import get_price_history
from app.schemas.quote import QuoteItemPriceUpdate, QuoteItemGstUpdate, PriceHistoryResponse
from app.services.pdf_service import generate_quote_pdf

router = APIRouter()


@router.post("", response_model=APIResponse, status_code=http_status.HTTP_201_CREATED, tags=["Quotes"])
def create_quote(
    quote_data: QuoteCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Create a quote from user's cart.
    Cart will be cleared after quote creation.

    Args:
        quote_data: Quote creation data (notes, expires_at)
        current_user: Current authenticated user
        db: Database session

    Returns:
        Standard API response with created quote
    """
    try:
        quote = create_quote_from_cart(
            db=db,
            user_id=current_user.id,
            notes=quote_data.notes,
            expires_at=quote_data.expires_at
        )
        return APIResponse(
            status="success",
            message="Quote created successfully",
            data=quote.model_dump()
        )
    except ValueError as e:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail=ErrorResponse(
                status="error",
                message="Failed to create quote",
                error=ErrorDetail(
                    code="QUOTE_CREATE_ERROR",
                    message=str(e)
                )
            ).model_dump()
        )
    except Exception as e:
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                status="error",
                message="Failed to create quote",
                error=ErrorDetail(
                    code="INTERNAL_ERROR",
                    message=str(e)
                )
            ).model_dump()
        )


@router.get("", response_model=APIResponse, tags=["Quotes"])
def list_quotes(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000,
                       description="Maximum number of records to return"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get quotes with pagination.
    Owners see all quotes, regular users see only their own quotes.

    Args:
        skip: Number of records to skip
        limit: Maximum number of records to return
        current_user: Current authenticated user
        db: Database session

    Returns:
        Standard API response with paginated quotes list
    """
    try:
        # If user is an owner, return all quotes; otherwise return only their quotes
        if current_user.role == UserRole.OWNER:
            quotes, total = get_all_quotes(
                db=db,
                skip=skip,
                limit=limit
            )
        else:
            quotes, total = get_user_quotes(
                db=db,
                user_id=current_user.id,
                skip=skip,
                limit=limit
            )
        return APIResponse(
            status="success",
            message="Quotes retrieved successfully",
            data={
                "quotes": [quote.model_dump() for quote in quotes],
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
                message="Failed to retrieve quotes",
                error=ErrorDetail(
                    code="QUOTES_FETCH_ERROR",
                    message=str(e)
                )
            ).model_dump()
        )


@router.get("/{quote_id}", response_model=APIResponse, tags=["Quotes"])
def get_quote(
    quote_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get quote details by ID.
    Owners can view any quote, regular users can only view their own quotes.

    Args:
        quote_id: Quote ID
        current_user: Current authenticated user
        db: Database session

    Returns:
        Standard API response with quote details
    """
    try:
        # If user is an owner, allow viewing any quote; otherwise restrict to their own quotes
        if current_user.role == UserRole.OWNER:
            quote = get_quote_by_id(db, quote_id, user_id=None)
        else:
            quote = get_quote_by_id(db, quote_id, current_user.id)

        if not quote:
            raise HTTPException(
                status_code=http_status.HTTP_404_NOT_FOUND,
                detail=ErrorResponse(
                    status="error",
                    message="Quote not found",
                    error=ErrorDetail(
                        code="QUOTE_NOT_FOUND",
                        message="Quote does not exist or does not belong to you"
                    )
                ).model_dump()
            )

        return APIResponse(
            status="success",
            message="Quote retrieved successfully",
            data=quote.model_dump()
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                status="error",
                message="Failed to retrieve quote",
                error=ErrorDetail(
                    code="QUOTE_FETCH_ERROR",
                    message=str(e)
                )
            ).model_dump()
        )


@router.put("/{quote_id}", response_model=APIResponse, tags=["Quotes"])
def update_quote_endpoint(
    quote_id: int,
    update_data: QuoteUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Update quote (status, notes, expiration date).
    Users can only update their own quotes.

    Args:
        quote_id: Quote ID
        update_data: Update data
        current_user: Current authenticated user
        db: Database session

    Returns:
        Standard API response with updated quote
    """
    try:
        quote = update_quote(
            db=db,
            quote_id=quote_id,
            user_id=current_user.id,
            status=update_data.status,
            notes=update_data.notes,
            expires_at=update_data.expires_at
        )
        return APIResponse(
            status="success",
            message="Quote updated successfully",
            data=quote.model_dump()
        )
    except ValueError as e:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail=ErrorResponse(
                status="error",
                message="Failed to update quote",
                error=ErrorDetail(
                    code="QUOTE_UPDATE_ERROR",
                    message=str(e)
                )
            ).model_dump()
        )
    except Exception as e:
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                status="error",
                message="Failed to update quote",
                error=ErrorDetail(
                    code="INTERNAL_ERROR",
                    message=str(e)
                )
            ).model_dump()
        )


@router.delete("/{quote_id}", response_model=APIResponse, tags=["Quotes"])
def delete_quote_endpoint(
    quote_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Delete a quote.
    Users can only delete their own quotes.

    Args:
        quote_id: Quote ID
        current_user: Current authenticated user
        db: Database session

    Returns:
        Standard API response
    """
    try:
        deleted = delete_quote(db, quote_id, current_user.id)

        if not deleted:
            raise HTTPException(
                status_code=http_status.HTTP_404_NOT_FOUND,
                detail=ErrorResponse(
                    status="error",
                    message="Quote not found",
                    error=ErrorDetail(
                        code="QUOTE_NOT_FOUND",
                        message="Quote does not exist or does not belong to you"
                    )
                ).model_dump()
            )

        return APIResponse(
            status="success",
            message="Quote deleted successfully",
            data=None
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                status="error",
                message="Failed to delete quote",
                error=ErrorDetail(
                    code="QUOTE_DELETE_ERROR",
                    message=str(e)
                )
            ).model_dump()
        )


@router.get("/{quote_id}/pdf", tags=["Quotes"])
def get_quote_pdf(
    quote_id: int,
    download: bool = Query(
        False, description="Force download instead of inline display"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Generate and return PDF for a quote.
    Owners can view any quote, regular users can only view their own quotes.

    Args:
        quote_id: Quote ID
        download: If True, forces download; if False, displays inline
        current_user: Current authenticated user
        db: Database session

    Returns:
        PDF file response
    """
    try:
        # If user is an owner, allow viewing any quote; otherwise restrict to their own quotes
        if current_user.role == UserRole.OWNER:
            quote = get_quote_detail_by_id(db, quote_id)
        else:
            quote = get_quote_by_id(db, quote_id, current_user.id)

        if not quote:
            raise HTTPException(
                status_code=http_status.HTTP_404_NOT_FOUND,
                detail=ErrorResponse(
                    status="error",
                    message="Quote not found",
                    error=ErrorDetail(
                        code="QUOTE_NOT_FOUND",
                        message="Quote does not exist or does not belong to you"
                    )
                ).model_dump()
            )

        # Generate PDF
        pdf_buffer = generate_quote_pdf(quote)
        pdf_bytes = pdf_buffer.read()

        # Determine content disposition
        disposition = "attachment" if download else "inline"
        filename = f"quote-{quote.quote_number}.pdf"

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
    except Exception as e:
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                status="error",
                message="Failed to generate PDF",
                error=ErrorDetail(
                    code="PDF_GENERATION_ERROR",
                    message=str(e)
                )
            ).model_dump()
        )


# Admin endpoints - these will be registered under /admin/quotes prefix
admin_router = APIRouter()


@admin_router.get("/quotes", response_model=APIResponse, tags=["Admin", "Quotes"])
def admin_list_quotes(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000,
                       description="Maximum number of records to return"),
    status: Optional[str] = Query(None, description="Filter by status"),
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    Get all quotes (admin only) with pagination and optional status filter.

    Args:
        skip: Number of records to skip
        limit: Maximum number of records to return
        status: Optional status filter
        current_user: Current authenticated admin user
        db: Database session

    Returns:
        Standard API response with paginated quotes list
    """
    try:
        quotes, total = get_all_quotes(
            db=db,
            skip=skip,
            limit=limit,
            status=status
        )
        return APIResponse(
            status="success",
            message="Quotes retrieved successfully",
            data={
                "quotes": [quote.model_dump() for quote in quotes],
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
                message="Failed to retrieve quotes",
                error=ErrorDetail(
                    code="QUOTES_FETCH_ERROR",
                    message=str(e)
                )
            ).model_dump()
        )


@admin_router.get("/quotes/all", response_model=APIResponse, tags=["Admin", "Quotes"])
def owner_list_all_quotes(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000,
                       description="Maximum number of records to return"),
    min_price: Optional[Decimal] = Query(
        None, description="Minimum price filter"),
    max_price: Optional[Decimal] = Query(
        None, description="Maximum price filter"),
    status: Optional[str] = Query(
        None, description="Filter by status (draft, pending, approved, rejected, expired)"),
    created_from: Optional[str] = Query(
        None, description="Filter quotes created on or after this date (ISO format: YYYY-MM-DDTHH:MM:SS)"),
    created_to: Optional[str] = Query(
        None, description="Filter quotes created on or before this date (ISO format: YYYY-MM-DDTHH:MM:SS)"),
    expires_from: Optional[str] = Query(
        None, description="Filter quotes expiring on or after this date (ISO format: YYYY-MM-DDTHH:MM:SS)"),
    expires_to: Optional[str] = Query(
        None, description="Filter quotes expiring on or before this date (ISO format: YYYY-MM-DDTHH:MM:SS)"),
    quote_number: Optional[str] = Query(
        None, description="Search by quote number (partial match)"),
    user_email: Optional[str] = Query(
        None, description="Search by user email (partial match)"),
    sort_by: Optional[str] = Query(
        None, description="Sort by field (created_at, updated_at, total, quote_number, status)"),
    sort_order: Optional[str] = Query(
        "desc", description="Sort order (asc, desc)"),
    current_user: User = Depends(get_current_owner),
    db: Session = Depends(get_db)
):
    """
    Get all quotes with advanced filtering, searching, and sorting (owner only).

    This endpoint provides comprehensive filtering capabilities including:
    - Price range filtering (min_price, max_price)
    - Status filtering
    - Date range filtering (created dates, expiration dates)
    - Search by quote number or user email
    - Sorting by various fields

    Args:
        skip: Number of records to skip
        limit: Maximum number of records to return
        min_price: Optional minimum price filter
        max_price: Optional maximum price filter
        status: Optional status filter
        created_from: Optional filter for quotes created on or after this date (ISO format string)
        created_to: Optional filter for quotes created on or before this date (ISO format string)
        expires_from: Optional filter for quotes expiring on or after this date (ISO format string)
        expires_to: Optional filter for quotes expiring on or before this date (ISO format string)
        quote_number: Optional search by quote number (partial match)
        user_email: Optional search by user email (partial match)
        sort_by: Optional field to sort by
        sort_order: Optional sort order (asc, desc)
        current_user: Current authenticated owner user
        db: Database session

    Returns:
        Standard API response with paginated quotes list including user emails
    """
    try:
        # Parse datetime strings to datetime objects
        parsed_created_from = None
        parsed_created_to = None
        parsed_expires_from = None
        parsed_expires_to = None

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

        if expires_from:
            try:
                parsed_expires_from = datetime.fromisoformat(
                    expires_from.replace('Z', '+00:00'))
            except (ValueError, AttributeError):
                raise ValueError(
                    f"Invalid date format for expires_from: {expires_from}. Use ISO format (YYYY-MM-DDTHH:MM:SS)")

        if expires_to:
            try:
                parsed_expires_to = datetime.fromisoformat(
                    expires_to.replace('Z', '+00:00'))
            except (ValueError, AttributeError):
                raise ValueError(
                    f"Invalid date format for expires_to: {expires_to}. Use ISO format (YYYY-MM-DDTHH:MM:SS)")

        quotes, total = get_all_quotes_advanced(
            db=db,
            skip=skip,
            limit=limit,
            min_price=min_price,
            max_price=max_price,
            status=status,
            created_from=parsed_created_from,
            created_to=parsed_created_to,
            expires_from=parsed_expires_from,
            expires_to=parsed_expires_to,
            quote_number=quote_number,
            user_email=user_email,
            sort_by=sort_by,
            sort_order=sort_order
        )
        return APIResponse(
            status="success",
            message="Quotes retrieved successfully",
            data={
                "quotes": [quote.model_dump() for quote in quotes],
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
                message="Failed to retrieve quotes",
                error=ErrorDetail(
                    code="QUOTES_FETCH_ERROR",
                    message=str(e)
                )
            ).model_dump()
        )


@admin_router.get("/quotes/{quote_id}", response_model=APIResponse, tags=["Admin", "Quotes"])
def admin_get_quote(
    quote_id: int,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    Get quote details by ID with customer information (admin only).
    Admins can view any quote with full customer details.

    Args:
        quote_id: Quote ID
        current_user: Current authenticated admin user
        db: Database session

    Returns:
        Standard API response with quote details including customer information
    """
    try:
        quote = get_quote_detail_by_id(db, quote_id)

        if not quote:
            raise HTTPException(
                status_code=http_status.HTTP_404_NOT_FOUND,
                detail=ErrorResponse(
                    status="error",
                    message="Quote not found",
                    error=ErrorDetail(
                        code="QUOTE_NOT_FOUND",
                        message="Quote does not exist"
                    )
                ).model_dump()
            )

        return APIResponse(
            status="success",
            message="Quote retrieved successfully",
            data=quote.model_dump()
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                status="error",
                message="Failed to retrieve quote",
                error=ErrorDetail(
                    code="QUOTE_FETCH_ERROR",
                    message=str(e)
                )
            ).model_dump()
        )


@admin_router.put("/quotes/{quote_id}", response_model=APIResponse, tags=["Admin", "Quotes"])
def admin_update_quote(
    quote_id: int,
    update_data: AdminQuoteUpdate,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    Update quote status and admin notes (admin only).

    Args:
        quote_id: Quote ID
        update_data: Update data (status, admin_notes)
        current_user: Current authenticated admin user
        db: Database session

    Returns:
        Standard API response with updated quote
    """
    try:
        quote = update_quote_status(
            db=db,
            quote_id=quote_id,
            status=update_data.status,
            admin_notes=update_data.admin_notes
        )
        return APIResponse(
            status="success",
            message="Quote updated successfully",
            data=quote.model_dump()
        )
    except ValueError as e:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail=ErrorResponse(
                status="error",
                message="Failed to update quote",
                error=ErrorDetail(
                    code="QUOTE_UPDATE_ERROR",
                    message=str(e)
                )
            ).model_dump()
        )
    except Exception as e:
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                status="error",
                message="Failed to update quote",
                error=ErrorDetail(
                    code="INTERNAL_ERROR",
                    message=str(e)
                )
            ).model_dump()
        )


@admin_router.put("/quotes/{quote_id}/items/{item_id}/price", response_model=APIResponse, tags=["Admin", "Quotes"])
def admin_update_quote_item_price(
    quote_id: int,
    item_id: int,
    price_data: QuoteItemPriceUpdate,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    Update quote item price (admin only).
    Stores the price in price history and recalculates quote totals including tax.

    Args:
        quote_id: Quote ID
        item_id: Quote item ID
        price_data: New price data
        current_user: Current authenticated admin user
        db: Database session

    Returns:
        Standard API response with updated quote
    """
    try:
        quote = update_quote_item_price(
            db=db,
            quote_id=quote_id,
            item_id=item_id,
            new_price=price_data.price,
            updated_by=current_user.id
        )
        return APIResponse(
            status="success",
            message="Quote item price updated successfully",
            data=quote.model_dump()
        )
    except ValueError as e:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail=ErrorResponse(
                status="error",
                message="Failed to update quote item price",
                error=ErrorDetail(
                    code="QUOTE_ITEM_PRICE_UPDATE_ERROR",
                    message=str(e)
                )
            ).model_dump()
        )
    except Exception as e:
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                status="error",
                message="Failed to update quote item price",
                error=ErrorDetail(
                    code="INTERNAL_ERROR",
                    message=str(e)
                )
            ).model_dump()
        )


@admin_router.put("/quotes/{quote_id}/items/{item_id}/gst", response_model=APIResponse, tags=["Admin", "Quotes"])
def admin_update_quote_item_gst(
    quote_id: int,
    item_id: int,
    gst_data: QuoteItemGstUpdate,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    Update quote item GST rate (admin only).
    Recalculates tax and quote totals.

    Args:
        quote_id: Quote ID
        item_id: Quote item ID
        gst_data: GST rate data (5.00, 12.00, 18.00, 28.00, or null to remove)
        current_user: Current authenticated admin user
        db: Database session

    Returns:
        Standard API response with updated quote
    """
    try:
        quote = update_quote_item_gst(
            db=db,
            quote_id=quote_id,
            item_id=item_id,
            gst_rate=gst_data.gst_rate,
            updated_by=current_user.id
        )
        return APIResponse(
            status="success",
            message="Quote item GST rate updated successfully",
            data=quote.model_dump()
        )
    except ValueError as e:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail=ErrorResponse(
                status="error",
                message="Failed to update quote item GST rate",
                error=ErrorDetail(
                    code="QUOTE_ITEM_GST_UPDATE_ERROR",
                    message=str(e)
                )
            ).model_dump()
        )
    except Exception as e:
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                status="error",
                message="Failed to update quote item GST rate",
                error=ErrorDetail(
                    code="INTERNAL_ERROR",
                    message=str(e)
                )
            ).model_dump()
        )


@admin_router.get("/products/{product_id}/price-history", response_model=APIResponse, tags=["Admin", "Products"])
def admin_get_product_price_history(
    product_id: int,
    variant_id: Optional[int] = Query(
        None, description="Optional variant ID to filter price history"),
    limit: int = Query(
        10, ge=1, le=100, description="Maximum number of records to return"),
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    Get price history for a product/variant (admin only).
    Returns previously given prices, most recent first.

    Args:
        product_id: Product ID
        variant_id: Optional variant ID
        limit: Maximum number of records to return
        current_user: Current authenticated admin user
        db: Database session

    Returns:
        Standard API response with price history
    """
    try:
        prices = get_price_history(
            db=db,
            product_id=product_id,
            variant_id=variant_id,
            limit=limit
        )
        return APIResponse(
            status="success",
            message="Price history retrieved successfully",
            data=PriceHistoryResponse(
                prices=prices,
                product_id=product_id,
                variant_id=variant_id
            ).model_dump()
        )
    except Exception as e:
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                status="error",
                message="Failed to retrieve price history",
                error=ErrorDetail(
                    code="PRICE_HISTORY_FETCH_ERROR",
                    message=str(e)
                )
            ).model_dump()
        )


@admin_router.get("/quotes/{quote_id}/pdf", tags=["Admin", "Quotes"])
def admin_get_quote_pdf(
    quote_id: int,
    download: bool = Query(
        False, description="Force download instead of inline display"),
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    Generate and return PDF for a quote (admin only).
    Admins can view any quote with full customer details.

    Args:
        quote_id: Quote ID
        download: If True, forces download; if False, displays inline
        current_user: Current authenticated admin user
        db: Database session

    Returns:
        PDF file response
    """
    try:
        quote = get_quote_detail_by_id(db, quote_id)

        if not quote:
            raise HTTPException(
                status_code=http_status.HTTP_404_NOT_FOUND,
                detail=ErrorResponse(
                    status="error",
                    message="Quote not found",
                    error=ErrorDetail(
                        code="QUOTE_NOT_FOUND",
                        message="Quote does not exist"
                    )
                ).model_dump()
            )

        # Generate PDF
        pdf_buffer = generate_quote_pdf(quote)
        pdf_bytes = pdf_buffer.read()

        # Determine content disposition
        disposition = "attachment" if download else "inline"
        filename = f"quote-{quote.quote_number}.pdf"

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
    except Exception as e:
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                status="error",
                message="Failed to generate PDF",
                error=ErrorDetail(
                    code="PDF_GENERATION_ERROR",
                    message=str(e)
                )
            ).model_dump()
        )
