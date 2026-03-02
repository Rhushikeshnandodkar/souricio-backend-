"""
Quote business logic service
"""
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, extract
from typing import List, Optional
from decimal import Decimal
from datetime import datetime, timedelta

from app.db.models.quote import Quote, QuoteItem, QuoteStatus
from app.db.models.user import User
from app.db.models.cart import Cart
from app.services.cart_service import get_user_cart, clear_user_cart
from app.services.price_history_service import store_price_history
from app.services.tax_service import calculate_item_tax, calculate_quote_totals
from app.schemas.cart import CartResponse
from app.schemas.quote import QuoteResponse, QuoteSummaryResponse, QuoteItemResponse, OwnerQuoteSummaryResponse, QuoteDetailResponse, UserInfo


def generate_quote_number(db: Session) -> str:
    """
    Generate a unique quote number in format QT-YYYY-NNNN.
    Auto-increments based on the current year.

    Args:
        db: Database session

    Returns:
        Unique quote number string (e.g., QT-2024-0001)
    """
    current_year = datetime.utcnow().year

    # Find the maximum quote number for the current year
    max_quote = (
        db.query(Quote)
        .filter(Quote.quote_number.like(f"QT-{current_year}-%"))
        .order_by(Quote.quote_number.desc())
        .first()
    )

    if max_quote:
        # Extract the number part and increment
        try:
            number_part = max_quote.quote_number.split("-")[-1]
            next_number = int(number_part) + 1
        except (ValueError, IndexError):
            next_number = 1
    else:
        next_number = 1

    # Format with leading zeros (4 digits)
    quote_number = f"QT-{current_year}-{next_number:04d}"
    return quote_number


def create_quote_from_cart(
    db: Session,
    user_id: int,
    notes: Optional[str] = None,
    expires_at: Optional[datetime] = None
) -> QuoteResponse:
    """
    Create a quote from user's cart items.
    Clears the cart after creating the quote.

    Args:
        db: Database session
        user_id: User ID
        notes: Optional user notes
        expires_at: Optional expiration date

    Returns:
        Created quote response

    Raises:
        ValueError: If cart is empty
    """
    # Get user's cart
    cart = get_user_cart(db, user_id)

    # Validate cart is not empty
    if not cart.items or len(cart.items) == 0:
        raise ValueError("Cannot create quote from empty cart")

    # Generate quote number
    quote_number = generate_quote_number(db)

    # Set default expiration (30 days from now) if not provided
    if expires_at is None:
        expires_at = datetime.utcnow() + timedelta(days=30)

    # Create quote (totals will be calculated after items are created)
    quote = Quote(
        quote_number=quote_number,
        user_id=user_id,
        status=QuoteStatus.DRAFT,
        expires_at=expires_at,
        notes=notes,
        subtotal=None,
        total=None
    )
    db.add(quote)
    db.flush()  # Flush to get quote ID

    # Create quote items from cart items and determine custom pricing
    quote_items = []
    items_with_price = []
    items_requiring_custom_price = []

    for cart_item in cart.items:
        # Check if price is missing or 0 (treat as custom pricing)
        price = cart_item.price
        requires_custom = False

        if price is None or price == 0 or price == Decimal("0.00"):
            requires_custom = True
            items_requiring_custom_price.append(cart_item)
        else:
            items_with_price.append((cart_item, price))

        # Calculate item totals (without GST initially - GST will be set by admin)
        item_total = None
        tax_amount = None
        item_total_with_tax = None

        if not requires_custom and price:
            item_total, tax_amount, item_total_with_tax = calculate_item_tax(
                price=price,
                quantity=cart_item.quantity,
                gst_rate=None  # No GST initially
            )

        quote_item = QuoteItem(
            quote_id=quote.id,
            product_id=cart_item.product_id,
            variant_id=cart_item.variant_id,
            product_name=cart_item.product_name,
            variant_name=cart_item.variant_name,
            # Store 0.00 for custom pricing items
            price=price or Decimal("0.00"),
            requires_custom_price=requires_custom,
            quantity=cart_item.quantity,
            image=cart_item.image,
            gst_rate=None,  # GST will be set by admin
            item_total=item_total,
            tax_amount=tax_amount,
            item_total_with_tax=item_total_with_tax
        )
        quote_items.append(quote_item)
        db.add(quote_item)

    # Calculate totals including tax
    # Reload items to get calculated values
    db.flush()
    quote_with_items = (
        db.query(Quote)
        .filter(Quote.id == quote.id)
        .options(joinedload(Quote.items))
        .first()
    )

    subtotal, total_tax, total, tax_breakdown = calculate_quote_totals(
        quote_with_items.items)

    # Update quote with calculated totals
    quote.subtotal = subtotal
    quote.total_tax = total_tax
    quote.total = total
    quote.tax_breakdown = tax_breakdown

    # Clear user's cart
    clear_user_cart(db, user_id)

    # Commit all changes
    db.commit()
    db.refresh(quote)

    # Load quote with items for response
    quote_with_items = (
        db.query(Quote)
        .filter(Quote.id == quote.id)
        .options(joinedload(Quote.items))
        .first()
    )

    return quote_to_response(quote_with_items)


def get_user_quotes(
    db: Session,
    user_id: int,
    skip: int = 0,
    limit: int = 100
) -> tuple[List[QuoteSummaryResponse], int]:
    """
    Get user's quotes with pagination.

    Args:
        db: Database session
        user_id: User ID
        skip: Number of records to skip
        limit: Maximum number of records to return

    Returns:
        Tuple of (list of quote summaries, total count)
    """
    # Get total count
    total = db.query(Quote).filter(Quote.user_id == user_id).count()

    # Get quotes with item count and items loaded
    quotes = (
        db.query(
            Quote,
            func.count(QuoteItem.id).label('item_count')
        )
        .outerjoin(QuoteItem)
        .filter(Quote.user_id == user_id)
        .group_by(Quote.id)
        .options(joinedload(Quote.items))
        .order_by(Quote.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )

    result = []
    for quote, item_count in quotes:
        # Check if quote has custom pricing by checking items
        has_custom_pricing = any(
            item.requires_custom_price for item in quote.items)

        result.append(QuoteSummaryResponse(
            id=quote.id,
            quote_number=quote.quote_number,
            user_id=quote.user_id,
            status=quote.status.value,
            expires_at=quote.expires_at,
            subtotal=quote.subtotal,
            total_tax=quote.total_tax,
            total=quote.total,
            tax_breakdown=quote.tax_breakdown,
            has_custom_pricing=has_custom_pricing,
            item_count=item_count or 0,
            created_at=quote.created_at,
            updated_at=quote.updated_at
        ))

    return result, total


def get_all_quotes(
    db: Session,
    skip: int = 0,
    limit: int = 100,
    status: Optional[str] = None
) -> tuple[List[QuoteSummaryResponse], int]:
    """
    Get all quotes (admin function) with pagination and optional status filter.

    Args:
        db: Database session
        skip: Number of records to skip
        limit: Maximum number of records to return
        status: Optional status filter

    Returns:
        Tuple of (list of quote summaries, total count)
    """
    query = db.query(
        Quote,
        func.count(QuoteItem.id).label('item_count')
    ).outerjoin(QuoteItem)

    # Apply status filter if provided
    if status:
        try:
            status_enum = QuoteStatus(status.lower())
            query = query.filter(Quote.status == status_enum)
        except ValueError:
            pass  # Invalid status, ignore filter

    # Get total count
    total = query.group_by(Quote.id).count()

    # Get quotes with items loaded
    quotes = (
        query
        .group_by(Quote.id)
        .options(joinedload(Quote.items))
        .order_by(Quote.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )

    result = []
    for quote, item_count in quotes:
        # Check if quote has custom pricing by checking items
        has_custom_pricing = any(
            item.requires_custom_price for item in quote.items)

        result.append(QuoteSummaryResponse(
            id=quote.id,
            quote_number=quote.quote_number,
            user_id=quote.user_id,
            status=quote.status.value,
            expires_at=quote.expires_at,
            subtotal=quote.subtotal,
            total_tax=quote.total_tax,
            total=quote.total,
            tax_breakdown=quote.tax_breakdown,
            has_custom_pricing=has_custom_pricing,
            item_count=item_count or 0,
            created_at=quote.created_at,
            updated_at=quote.updated_at
        ))

    return result, total


def get_all_quotes_advanced(
    db: Session,
    skip: int = 0,
    limit: int = 100,
    min_price: Optional[Decimal] = None,
    max_price: Optional[Decimal] = None,
    status: Optional[str] = None,
    created_from: Optional[datetime] = None,
    created_to: Optional[datetime] = None,
    expires_from: Optional[datetime] = None,
    expires_to: Optional[datetime] = None,
    quote_number: Optional[str] = None,
    user_email: Optional[str] = None,
    sort_by: Optional[str] = None,
    sort_order: Optional[str] = None
) -> tuple[List[OwnerQuoteSummaryResponse], int]:
    """
    Get all quotes with advanced filtering, searching, and sorting (owner function).

    Args:
        db: Database session
        skip: Number of records to skip
        limit: Maximum number of records to return
        min_price: Optional minimum price filter
        max_price: Optional maximum price filter
        status: Optional status filter
        created_from: Optional filter for quotes created on or after this date
        created_to: Optional filter for quotes created on or before this date
        expires_from: Optional filter for quotes expiring on or after this date
        expires_to: Optional filter for quotes expiring on or before this date
        quote_number: Optional search by quote number (partial match)
        user_email: Optional search by user email (partial match)
        sort_by: Optional field to sort by (created_at, updated_at, total, quote_number, status)
        sort_order: Optional sort order (asc, desc, default: desc)

    Returns:
        Tuple of (list of owner quote summaries with user email, total count)
    """
    # Validate price range
    if min_price is not None and max_price is not None:
        if min_price > max_price:
            raise ValueError("min_price cannot be greater than max_price")

    # Build base query with joins
    query = (
        db.query(
            Quote,
            User.email.label('user_email'),
            func.count(QuoteItem.id).label('item_count')
        )
        .join(User, Quote.user_id == User.id)
        .outerjoin(QuoteItem)
    )

    # Apply filters conditionally
    # Note: Price filters only apply to quotes with non-null totals
    if min_price is not None:
        query = query.filter(
            (Quote.total.isnot(None)) & (Quote.total >= min_price)
        )

    if max_price is not None:
        query = query.filter(
            (Quote.total.isnot(None)) & (Quote.total <= max_price)
        )

    if status:
        try:
            status_enum = QuoteStatus(status.lower())
            query = query.filter(Quote.status == status_enum)
        except ValueError:
            pass  # Invalid status, ignore filter

    if created_from:
        query = query.filter(Quote.created_at >= created_from)

    if created_to:
        query = query.filter(Quote.created_at <= created_to)

    if expires_from:
        query = query.filter(Quote.expires_at >= expires_from)

    if expires_to:
        query = query.filter(Quote.expires_at <= expires_to)

    if quote_number:
        query = query.filter(Quote.quote_number.ilike(f'%{quote_number}%'))

    if user_email:
        query = query.filter(User.email.ilike(f'%{user_email}%'))

    # Get total count before pagination
    total = query.group_by(Quote.id, User.email).count()

    # Apply sorting
    sort_field = None
    if sort_by:
        sort_by_lower = sort_by.lower()
        if sort_by_lower == "created_at":
            sort_field = Quote.created_at
        elif sort_by_lower == "updated_at":
            sort_field = Quote.updated_at
        elif sort_by_lower == "total":
            sort_field = Quote.total
        elif sort_by_lower == "quote_number":
            sort_field = Quote.quote_number
        elif sort_by_lower == "status":
            sort_field = Quote.status
        else:
            # Invalid sort_by, default to created_at
            sort_field = Quote.created_at
    else:
        # Default sort by created_at
        sort_field = Quote.created_at

    # Apply sort order
    if sort_order and sort_order.lower() == "asc":
        query = query.order_by(sort_field.asc())
    else:
        # Default to desc
        query = query.order_by(sort_field.desc())

    # Get quotes with pagination and items loaded
    quotes = (
        query
        .group_by(Quote.id, User.email)
        .options(joinedload(Quote.items))
        .offset(skip)
        .limit(limit)
        .all()
    )

    result = []
    for quote, email, item_count in quotes:
        # Check if quote has custom pricing by checking items
        has_custom_pricing = any(
            item.requires_custom_price for item in quote.items)

        result.append(OwnerQuoteSummaryResponse(
            id=quote.id,
            quote_number=quote.quote_number,
            user_id=quote.user_id,
            user_email=email,
            status=quote.status.value,
            expires_at=quote.expires_at,
            subtotal=quote.subtotal,
            total_tax=quote.total_tax,
            total=quote.total,
            tax_breakdown=quote.tax_breakdown,
            has_custom_pricing=has_custom_pricing,
            item_count=item_count or 0,
            created_at=quote.created_at,
            updated_at=quote.updated_at
        ))

    return result, total


def get_quote_by_id(
    db: Session,
    quote_id: int,
    user_id: Optional[int] = None
) -> Optional[QuoteResponse]:
    """
    Get quote by ID with all items.
    If user_id is provided, ensures quote belongs to user.

    Args:
        db: Database session
        quote_id: Quote ID
        user_id: Optional user ID for ownership check

    Returns:
        Quote response or None if not found
    """
    query = (
        db.query(Quote)
        .filter(Quote.id == quote_id)
        .options(joinedload(Quote.items))
    )

    if user_id:
        query = query.filter(Quote.user_id == user_id)

    quote = query.first()

    if not quote:
        return None

    return quote_to_response(quote)


def get_quote_detail_by_id(
    db: Session,
    quote_id: int
) -> Optional[QuoteDetailResponse]:
    """
    Get quote by ID with all items and user information (admin/owner function).

    Args:
        db: Database session
        quote_id: Quote ID

    Returns:
        Quote detail response with user information or None if not found
    """
    quote = (
        db.query(Quote)
        .filter(Quote.id == quote_id)
        .options(joinedload(Quote.items), joinedload(Quote.user))
        .first()
    )

    if not quote:
        return None

    # Verify user exists
    if not quote.user:
        # Fallback: fetch user separately if not loaded
        user = db.query(User).filter(User.id == quote.user_id).first()
        if not user:
            raise ValueError(
                f"User with ID {quote.user_id} not found for quote {quote_id}")
        quote.user = user

    # Build items list and check for custom pricing
    items = []
    has_custom_pricing = False

    for item in quote.items:
        if item.requires_custom_price:
            has_custom_pricing = True

        items.append(QuoteItemResponse(
            id=item.id,
            product_id=item.product_id,
            variant_id=item.variant_id,
            product_name=item.product_name,
            variant_name=item.variant_name,
            price=item.price,
            requires_custom_price=item.requires_custom_price,
            quantity=item.quantity,
            image=item.image,
            gst_rate=item.gst_rate,
            item_total=item.item_total,
            tax_amount=item.tax_amount,
            item_total_with_tax=item.item_total_with_tax,
            created_at=item.created_at
        ))

    # Build user info
    user_info = UserInfo(
        id=quote.user.id,
        email=quote.user.email,
        role=quote.user.role.value,
        is_active=quote.user.is_active,
        created_at=quote.user.created_at
    )

    return QuoteDetailResponse(
        id=quote.id,
        quote_number=quote.quote_number,
        user_id=quote.user_id,
        user=user_info,
        status=quote.status.value,
        expires_at=quote.expires_at,
        notes=quote.notes,
        admin_notes=quote.admin_notes,
        subtotal=quote.subtotal,
        total_tax=quote.total_tax,
        total=quote.total,
        tax_breakdown=quote.tax_breakdown,
        has_custom_pricing=has_custom_pricing,
        items=items,
        created_at=quote.created_at,
        updated_at=quote.updated_at
    )


def update_quote(
    db: Session,
    quote_id: int,
    user_id: int,
    status: Optional[str] = None,
    notes: Optional[str] = None,
    expires_at: Optional[datetime] = None
) -> QuoteResponse:
    """
    Update quote fields (user update).

    Args:
        db: Database session
        quote_id: Quote ID
        user_id: User ID (for ownership check)
        status: Optional new status
        notes: Optional new notes
        expires_at: Optional new expiration date

    Returns:
        Updated quote response

    Raises:
        ValueError: If quote not found or doesn't belong to user
    """
    quote = (
        db.query(Quote)
        .filter(Quote.id == quote_id, Quote.user_id == user_id)
        .first()
    )

    if not quote:
        raise ValueError(
            f"Quote with ID {quote_id} not found or does not belong to you")

    # Update fields
    if status is not None:
        try:
            quote.status = QuoteStatus(status.lower())
        except ValueError:
            raise ValueError(f"Invalid status: {status}")

    if notes is not None:
        quote.notes = notes

    if expires_at is not None:
        quote.expires_at = expires_at

    db.commit()
    db.refresh(quote)

    # Reload with items
    quote_with_items = (
        db.query(Quote)
        .filter(Quote.id == quote.id)
        .options(joinedload(Quote.items))
        .first()
    )

    return quote_to_response(quote_with_items)


def update_quote_status(
    db: Session,
    quote_id: int,
    status: Optional[str] = None,
    admin_notes: Optional[str] = None
) -> QuoteResponse:
    """
    Update quote status and admin notes (admin function).

    Args:
        db: Database session
        quote_id: Quote ID
        status: Optional new status
        admin_notes: Optional admin notes

    Returns:
        Updated quote response

    Raises:
        ValueError: If quote not found
    """
    quote = db.query(Quote).filter(Quote.id == quote_id).first()

    if not quote:
        raise ValueError(f"Quote with ID {quote_id} not found")

    # Update fields
    if status is not None:
        try:
            quote.status = QuoteStatus(status.lower())
        except ValueError:
            raise ValueError(f"Invalid status: {status}")

    if admin_notes is not None:
        quote.admin_notes = admin_notes

    db.commit()
    db.refresh(quote)

    # Reload with items
    quote_with_items = (
        db.query(Quote)
        .filter(Quote.id == quote.id)
        .options(joinedload(Quote.items))
        .first()
    )

    return quote_to_response(quote_with_items)


def delete_quote(
    db: Session,
    quote_id: int,
    user_id: int
) -> bool:
    """
    Delete a quote (hard delete).

    Args:
        db: Database session
        quote_id: Quote ID
        user_id: User ID (for ownership check)

    Returns:
        True if deleted, False if not found

    Raises:
        ValueError: If quote doesn't belong to user
    """
    quote = (
        db.query(Quote)
        .filter(Quote.id == quote_id, Quote.user_id == user_id)
        .first()
    )

    if not quote:
        return False

    db.delete(quote)
    db.commit()
    return True


def update_quote_item_price(
    db: Session,
    quote_id: int,
    item_id: int,
    new_price: Decimal,
    updated_by: int
) -> QuoteResponse:
    """
    Update a quote item's price and store it in price history.
    Recalculates quote totals after price update.

    Args:
        db: Database session
        quote_id: Quote ID
        item_id: Quote item ID
        new_price: New price (must be > 0)
        updated_by: User ID who is updating the price

    Returns:
        Updated quote response

    Raises:
        ValueError: If quote/item not found or price is invalid
    """
    # Validate price
    if new_price <= 0:
        raise ValueError("Price must be greater than 0")

    # Get quote item
    quote_item = (
        db.query(QuoteItem)
        .filter(QuoteItem.id == item_id, QuoteItem.quote_id == quote_id)
        .first()
    )

    if not quote_item:
        raise ValueError(
            f"Quote item with ID {item_id} not found in quote {quote_id}")

    # Get quote
    quote = db.query(Quote).filter(Quote.id == quote_id).first()
    if not quote:
        raise ValueError(f"Quote with ID {quote_id} not found")

    # Update quote item price
    quote_item.price = new_price
    # Price is now set, no longer requires custom pricing
    quote_item.requires_custom_price = False

    # Recalculate item totals and tax with current GST rate
    item_total, tax_amount, item_total_with_tax = calculate_item_tax(
        price=new_price,
        quantity=quote_item.quantity,
        gst_rate=quote_item.gst_rate
    )
    quote_item.item_total = item_total
    quote_item.tax_amount = tax_amount
    quote_item.item_total_with_tax = item_total_with_tax

    # Store new price in history
    store_price_history(
        db=db,
        product_id=quote_item.product_id,
        price=new_price,
        created_by=updated_by,
        variant_id=quote_item.variant_id,
        quote_id=quote_id,
        quote_item_id=item_id
    )

    # Recalculate quote totals including tax
    quote_items = db.query(QuoteItem).filter(
        QuoteItem.quote_id == quote_id).all()

    subtotal, total_tax, total, tax_breakdown = calculate_quote_totals(
        quote_items)

    # Update quote totals
    quote.subtotal = subtotal
    quote.total_tax = total_tax
    quote.total = total
    quote.tax_breakdown = tax_breakdown

    db.commit()
    db.refresh(quote)

    # Reload quote with items
    quote_with_items = (
        db.query(Quote)
        .filter(Quote.id == quote.id)
        .options(joinedload(Quote.items))
        .first()
    )

    return quote_to_response(quote_with_items)


def update_quote_item_gst(
    db: Session,
    quote_id: int,
    item_id: int,
    gst_rate: Optional[Decimal],
    updated_by: int
) -> QuoteResponse:
    """
    Update a quote item's GST rate and recalculate tax.
    Recalculates quote totals after GST update.

    Args:
        db: Database session
        quote_id: Quote ID
        item_id: Quote item ID
        gst_rate: New GST rate (5.00, 12.00, 18.00, 28.00) or None to remove GST
        updated_by: User ID who is updating the GST rate

    Returns:
        Updated quote response

    Raises:
        ValueError: If quote/item not found or GST rate is invalid
    """
    # Validate GST rate if provided
    if gst_rate is not None:
        from app.lib.gst_constants import is_valid_gst_rate
        if not is_valid_gst_rate(float(gst_rate)):
            raise ValueError("GST rate must be 5.00, 12.00, 18.00, or 28.00")

    # Get quote item
    quote_item = (
        db.query(QuoteItem)
        .filter(QuoteItem.id == item_id, QuoteItem.quote_id == quote_id)
        .first()
    )

    if not quote_item:
        raise ValueError(
            f"Quote item with ID {item_id} not found in quote {quote_id}")

    # Get quote
    quote = db.query(Quote).filter(Quote.id == quote_id).first()
    if not quote:
        raise ValueError(f"Quote with ID {quote_id} not found")

    # Check if item has a valid price
    if quote_item.requires_custom_price or quote_item.price is None or quote_item.price == 0:
        raise ValueError("Cannot set GST rate for item without a valid price")

    # Update GST rate
    quote_item.gst_rate = gst_rate

    # Recalculate item totals and tax
    item_total, tax_amount, item_total_with_tax = calculate_item_tax(
        price=quote_item.price,
        quantity=quote_item.quantity,
        gst_rate=gst_rate
    )
    quote_item.item_total = item_total
    quote_item.tax_amount = tax_amount
    quote_item.item_total_with_tax = item_total_with_tax

    # Recalculate quote totals including tax
    quote_items = db.query(QuoteItem).filter(
        QuoteItem.quote_id == quote_id).all()

    subtotal, total_tax, total, tax_breakdown = calculate_quote_totals(
        quote_items)

    # Update quote totals
    quote.subtotal = subtotal
    quote.total_tax = total_tax
    quote.total = total
    quote.tax_breakdown = tax_breakdown

    db.commit()
    db.refresh(quote)

    # Reload quote with items
    quote_with_items = (
        db.query(Quote)
        .filter(Quote.id == quote.id)
        .options(joinedload(Quote.items))
        .first()
    )

    return quote_to_response(quote_with_items)


def quote_to_response(quote: Quote) -> QuoteResponse:
    """
    Convert Quote model to QuoteResponse schema.

    Args:
        quote: Quote model instance

    Returns:
        QuoteResponse schema instance
    """
    items = []
    has_custom_pricing = False

    for item in quote.items:
        if item.requires_custom_price:
            has_custom_pricing = True

        items.append(QuoteItemResponse(
            id=item.id,
            product_id=item.product_id,
            variant_id=item.variant_id,
            product_name=item.product_name,
            variant_name=item.variant_name,
            price=item.price,
            requires_custom_price=item.requires_custom_price,
            quantity=item.quantity,
            image=item.image,
            gst_rate=item.gst_rate,
            item_total=item.item_total,
            tax_amount=item.tax_amount,
            item_total_with_tax=item.item_total_with_tax,
            created_at=item.created_at
        ))

    return QuoteResponse(
        id=quote.id,
        quote_number=quote.quote_number,
        user_id=quote.user_id,
        status=quote.status.value,
        expires_at=quote.expires_at,
        notes=quote.notes,
        admin_notes=quote.admin_notes,
        subtotal=quote.subtotal,
        total_tax=quote.total_tax,
        total=quote.total,
        tax_breakdown=quote.tax_breakdown,
        has_custom_pricing=has_custom_pricing,
        items=items,
        created_at=quote.created_at,
        updated_at=quote.updated_at
    )
