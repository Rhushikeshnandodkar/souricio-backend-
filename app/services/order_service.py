"""
Order business logic service
"""
from sqlalchemy.orm import Session, joinedload
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from sqlalchemy import func, case, and_
from typing import Optional, List
from decimal import Decimal
from datetime import datetime

from app.db.models.order import Order, OrderItem, OrderStatus
from app.db.models.quote import Quote, QuoteStatus
from app.db.models.user import User
from app.schemas.order import OrderResponse, OrderItemResponse, OrderSummaryResponse, OwnerOrderSummaryResponse, OrderDetailResponse


def generate_order_number(db: Session) -> str:
    """
    Generate a unique order number in format ORD-YYYY-NNNN.
    Auto-increments based on the current year.

    Args:
        db: Database session

    Returns:
        Unique order number string (e.g., ORD-2024-0001)
    """
    current_year = datetime.utcnow().year

    # Find the maximum order number for the current year
    max_order = (
        db.query(Order)
        .filter(Order.order_number.like(f"ORD-{current_year}-%"))
        .order_by(Order.order_number.desc())
        .first()
    )

    if max_order:
        # Extract the number part and increment
        try:
            number_part = max_order.order_number.split("-")[-1]
            next_number = int(number_part) + 1
        except (ValueError, IndexError):
            next_number = 1
    else:
        next_number = 1

    # Format with leading zeros (4 digits)
    order_number = f"ORD-{current_year}-{next_number:04d}"
    return order_number


def place_order_from_quote(
    db: Session,
    quote_id: int,
    user_id: int
) -> OrderResponse:
    """
    Place an order from an approved quote.
    Validates quote and creates Order with OrderItems.

    Args:
        db: Database session
        quote_id: Quote ID to place as order
        user_id: User ID placing the order

    Returns:
        Created order response

    Raises:
        ValueError: If validation fails
    """
    # Load quote with items and user relationship
    quote = (
        db.query(Quote)
        .filter(Quote.id == quote_id)
        .options(joinedload(Quote.items))
        .first()
    )

    if not quote:
        raise ValueError(f"Quote with ID {quote_id} not found")

    # Validate quote belongs to user
    if quote.user_id != user_id:
        raise ValueError("Quote does not belong to you")

    # Validate quote status is APPROVED
    if quote.status != QuoteStatus.APPROVED:
        raise ValueError(f"Cannot place order from quote with status '{quote.status.value}'. Quote must be approved.")

    # Validate quote is not expired
    if quote.expires_at:
        # Handle timezone-aware and timezone-naive datetimes
        now = datetime.utcnow()
        expires_at = quote.expires_at
        # If expires_at is timezone-aware, make now timezone-aware too
        if expires_at.tzinfo is not None:
            from datetime import timezone
            now = datetime.now(timezone.utc)
        if expires_at < now:
            raise ValueError("Cannot place order from expired quote")

    # Validate quote has valid total
    if quote.total is None or quote.total <= 0:
        raise ValueError("Quote must have a valid total amount to place an order")

    # Check if order already exists for this quote (duplicate prevention)
    existing_order = db.query(Order).filter(Order.quote_id == quote_id).first()
    if existing_order:
        raise ValueError(f"Order already exists for quote {quote_id}")

    try:
        # Generate order number
        order_number = generate_order_number(db)

        # Convert tax_breakdown to dict if it's not already
        tax_breakdown = quote.tax_breakdown
        if tax_breakdown is not None and not isinstance(tax_breakdown, dict):
            # If it's a string, try to parse it
            if isinstance(tax_breakdown, str):
                import json
                try:
                    tax_breakdown = json.loads(tax_breakdown)
                except (json.JSONDecodeError, ValueError):
                    tax_breakdown = None

        # Create order (copy pricing from quote)
        order = Order(
            order_number=order_number,
            quote_id=quote_id,
            user_id=user_id,
            status=OrderStatus.PENDING,
            subtotal=quote.subtotal,
            total_tax=quote.total_tax,
            total=quote.total,
            tax_breakdown=tax_breakdown,
            notes=None
        )
        db.add(order)
        db.flush()  # Flush to get order ID

        # Validate quote has items
        if not quote.items or len(quote.items) == 0:
            db.rollback()
            raise ValueError("Cannot place order from quote with no items")

        # Create order items from quote items
        order_items = []
        for quote_item in quote.items:
            order_item = OrderItem(
                order_id=order.id,
                product_id=quote_item.product_id,
                variant_id=quote_item.variant_id,
                product_name=quote_item.product_name,
                variant_name=quote_item.variant_name,
                price=quote_item.price,
                quantity=quote_item.quantity,
                image=quote_item.image,
                gst_rate=quote_item.gst_rate,
                item_total=quote_item.item_total,
                tax_amount=quote_item.tax_amount,
                item_total_with_tax=quote_item.item_total_with_tax
            )
            order_items.append(order_item)
            db.add(order_item)

        # Commit all changes
        db.commit()
        db.refresh(order)

        # Reload order with items for response
        order_with_items = (
            db.query(Order)
            .filter(Order.id == order.id)
            .options(joinedload(Order.items))
            .first()
        )

        if not order_with_items:
            raise ValueError("Failed to retrieve created order")

        return order_to_response(order_with_items)
    except IntegrityError as e:
        # Rollback on integrity error (e.g., duplicate order, foreign key constraint)
        db.rollback()
        error_msg = str(e.orig) if hasattr(e, 'orig') else str(e)
        if "unique constraint" in error_msg.lower() or "duplicate" in error_msg.lower():
            raise ValueError(f"Order already exists for quote {quote_id}")
        raise ValueError(f"Database constraint violation: {error_msg}")
    except SQLAlchemyError as e:
        # Rollback on database error
        db.rollback()
        error_msg = str(e.orig) if hasattr(e, 'orig') else str(e)
        # Check if it's a table doesn't exist error
        if "does not exist" in error_msg.lower() or "no such table" in error_msg.lower():
            raise ValueError("Order tables have not been created. Please restart the backend server to create the tables.")
        raise ValueError(f"Database error: {error_msg}")
    except Exception as e:
        # Rollback on any error
        db.rollback()
        # Re-raise ValueError as-is, wrap other exceptions
        if isinstance(e, ValueError):
            raise
        # Convert other exceptions to ValueError with more context
        raise ValueError(f"Failed to create order: {str(e)}")


def order_to_response(order: Order) -> OrderResponse:
    """
    Convert Order model to OrderResponse schema.

    Args:
        order: Order model instance

    Returns:
        OrderResponse schema instance
    """
    items = []
    for item in order.items:
        items.append(OrderItemResponse(
            id=item.id,
            order_id=item.order_id,
            product_id=item.product_id,
            variant_id=item.variant_id,
            product_name=item.product_name,
            variant_name=item.variant_name,
            price=item.price,
            quantity=item.quantity,
            image=item.image,
            gst_rate=item.gst_rate,
            item_total=item.item_total,
            tax_amount=item.tax_amount,
            item_total_with_tax=item.item_total_with_tax,
            created_at=item.created_at
        ))

    return OrderResponse(
        id=order.id,
        order_number=order.order_number,
        quote_id=order.quote_id,
        user_id=order.user_id,
        status=order.status.value,
        subtotal=order.subtotal,
        total_tax=order.total_tax,
        total=order.total,
        tax_breakdown=order.tax_breakdown,
        notes=order.notes,
        items=items,
        created_at=order.created_at,
        updated_at=order.updated_at
    )


def get_user_orders(
    db: Session,
    user_id: int,
    skip: int = 0,
    limit: int = 100
) -> tuple[List[OrderSummaryResponse], int]:
    """
    Get user's orders with pagination.

    Args:
        db: Database session
        user_id: User ID
        skip: Number of records to skip
        limit: Maximum number of records to return

    Returns:
        Tuple of (list of order summaries, total count)
    """
    # Get total count
    total = db.query(Order).filter(Order.user_id == user_id).count()

    # Get orders with item count and items loaded
    orders = (
        db.query(
            Order,
            func.count(OrderItem.id).label('item_count')
        )
        .outerjoin(OrderItem)
        .filter(Order.user_id == user_id)
        .group_by(Order.id)
        .options(joinedload(Order.items))
        .order_by(Order.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )

    result = []
    for order, item_count in orders:
        # Extract item names from order items
        item_names = [item.product_name for item in order.items] if order.items else []
        result.append(OrderSummaryResponse(
            id=order.id,
            order_number=order.order_number,
            quote_id=order.quote_id,
            user_id=order.user_id,
            status=order.status.value,
            subtotal=order.subtotal,
            total_tax=order.total_tax,
            total=order.total,
            tax_breakdown=order.tax_breakdown,
            item_count=item_count or 0,
            item_names=item_names,
            created_at=order.created_at,
            updated_at=order.updated_at
        ))

    return result, total


def get_all_orders(
    db: Session,
    skip: int = 0,
    limit: int = 100,
    status: Optional[str] = None
) -> tuple[List[OrderSummaryResponse], int]:
    """
    Get all orders (admin function) with pagination and optional status filter.

    Args:
        db: Database session
        skip: Number of records to skip
        limit: Maximum number of records to return
        status: Optional status filter

    Returns:
        Tuple of (list of order summaries, total count)
    """
    query = db.query(
        Order,
        func.count(OrderItem.id).label('item_count')
    ).outerjoin(OrderItem)

    # Apply status filter if provided
    if status:
        try:
            status_enum = OrderStatus(status.lower())
            query = query.filter(Order.status == status_enum)
        except ValueError:
            pass  # Invalid status, ignore filter

    # Get total count
    total = query.group_by(Order.id).count()

    # Get orders with items loaded
    orders = (
        query
        .group_by(Order.id)
        .options(joinedload(Order.items))
        .order_by(Order.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )

    result = []
    for order, item_count in orders:
        # Extract item names from order items
        item_names = [item.product_name for item in order.items] if order.items else []
        result.append(OrderSummaryResponse(
            id=order.id,
            order_number=order.order_number,
            quote_id=order.quote_id,
            user_id=order.user_id,
            status=order.status.value,
            subtotal=order.subtotal,
            total_tax=order.total_tax,
            total=order.total,
            tax_breakdown=order.tax_breakdown,
            item_count=item_count or 0,
            item_names=item_names,
            created_at=order.created_at,
            updated_at=order.updated_at
        ))

    return result, total


def get_all_orders_advanced(
    db: Session,
    skip: int = 0,
    limit: int = 100,
    min_price: Optional[Decimal] = None,
    max_price: Optional[Decimal] = None,
    status: Optional[str] = None,
    created_from: Optional[datetime] = None,
    created_to: Optional[datetime] = None,
    order_number: Optional[str] = None,
    user_email: Optional[str] = None,
    sort_by: Optional[str] = None,
    sort_order: Optional[str] = None
) -> tuple[List[OwnerOrderSummaryResponse], int]:
    """
    Get all orders with advanced filtering, searching, and sorting (owner function).

    Args:
        db: Database session
        skip: Number of records to skip
        limit: Maximum number of records to return
        min_price: Optional minimum price filter
        max_price: Optional maximum price filter
        status: Optional status filter
        created_from: Optional filter for orders created on or after this date
        created_to: Optional filter for orders created on or before this date
        order_number: Optional search by order number (partial match)
        user_email: Optional search by user email (partial match)
        sort_by: Optional field to sort by (created_at, updated_at, total, order_number, status)
        sort_order: Optional sort order (asc, desc, default: desc)

    Returns:
        Tuple of (list of order summaries with user email, total count)
    """
    # Validate price range
    if min_price is not None and max_price is not None:
        if min_price > max_price:
            raise ValueError("min_price cannot be greater than max_price")

    # Build base query with joins
    query = (
        db.query(
            Order,
            User.email.label('user_email'),
            func.count(OrderItem.id).label('item_count')
        )
        .join(User, Order.user_id == User.id)
        .outerjoin(OrderItem)
    )

    # Apply filters conditionally
    if min_price is not None:
        query = query.filter(
            (Order.total.isnot(None)) & (Order.total >= min_price)
        )

    if max_price is not None:
        query = query.filter(
            (Order.total.isnot(None)) & (Order.total <= max_price)
        )

    if status:
        try:
            status_enum = OrderStatus(status.lower())
            query = query.filter(Order.status == status_enum)
        except ValueError:
            pass  # Invalid status, ignore filter

    if created_from:
        query = query.filter(Order.created_at >= created_from)

    if created_to:
        query = query.filter(Order.created_at <= created_to)

    if order_number:
        query = query.filter(Order.order_number.ilike(f'%{order_number}%'))

    if user_email:
        query = query.filter(User.email.ilike(f'%{user_email}%'))

    # Get total count before pagination
    total = query.group_by(Order.id, User.email).count()

    # Apply sorting
    sort_field = None
    if sort_by:
        sort_by_lower = sort_by.lower()
        if sort_by_lower == "created_at":
            sort_field = Order.created_at
        elif sort_by_lower == "updated_at":
            sort_field = Order.updated_at
        elif sort_by_lower == "total":
            sort_field = Order.total
        elif sort_by_lower == "order_number":
            sort_field = Order.order_number
        elif sort_by_lower == "status":
            sort_field = Order.status
        else:
            sort_field = Order.created_at
    else:
        sort_field = Order.created_at

    # Apply sort order
    if sort_order and sort_order.lower() == "asc":
        query = query.order_by(sort_field.asc())
    else:
        query = query.order_by(sort_field.desc())

    # Get orders with pagination and items loaded
    orders = (
        query
        .group_by(Order.id, User.email)
        .options(joinedload(Order.items))
        .offset(skip)
        .limit(limit)
        .all()
    )

    result = []
    for order, email, item_count in orders:
        result.append(OwnerOrderSummaryResponse(
            id=order.id,
            order_number=order.order_number,
            quote_id=order.quote_id,
            user_id=order.user_id,
            user_email=email,
            status=order.status.value,
            subtotal=order.subtotal,
            total_tax=order.total_tax,
            total=order.total,
            tax_breakdown=order.tax_breakdown,
            item_count=item_count or 0,
            created_at=order.created_at,
            updated_at=order.updated_at
        ))

    return result, total


def get_order_by_id(
    db: Session,
    order_id: int,
    user_id: Optional[int] = None
) -> Optional[OrderResponse]:
    """
    Get order by ID with all items.
    If user_id is provided, ensures order belongs to user.

    Args:
        db: Database session
        order_id: Order ID
        user_id: Optional user ID for ownership check

    Returns:
        Order response or None if not found
    """
    query = (
        db.query(Order)
        .filter(Order.id == order_id)
        .options(joinedload(Order.items))
    )

    if user_id:
        query = query.filter(Order.user_id == user_id)

    order = query.first()

    if not order:
        return None

    return order_to_response(order)


def get_order_detail_by_id(
    db: Session,
    order_id: int
) -> Optional[OrderDetailResponse]:
    """
    Get order by ID with all items and user information (admin/owner function).

    Args:
        db: Database session
        order_id: Order ID

    Returns:
        Order response with user information or None if not found
    """
    from app.schemas.order import OrderDetailResponse, UserInfo

    order = (
        db.query(Order)
        .filter(Order.id == order_id)
        .options(joinedload(Order.items), joinedload(Order.user))
        .first()
    )

    if not order:
        return None

    # Convert to OrderDetailResponse with user info
    from app.schemas.order import UserInfo
    
    items = []
    for item in order.items:
        items.append(OrderItemResponse(
            id=item.id,
            order_id=item.order_id,
            product_id=item.product_id,
            variant_id=item.variant_id,
            product_name=item.product_name,
            variant_name=item.variant_name,
            price=item.price,
            quantity=item.quantity,
            image=item.image,
            gst_rate=item.gst_rate,
            item_total=item.item_total,
            tax_amount=item.tax_amount,
            item_total_with_tax=item.item_total_with_tax,
            created_at=item.created_at
        ))

    user_info = UserInfo(
        id=order.user.id,
        email=order.user.email,
        role=order.user.role.value if hasattr(order.user.role, 'value') else str(order.user.role),
        is_active=order.user.is_active,
        category=order.user.category.value if order.user.category and hasattr(order.user.category, 'value') else (order.user.category if order.user.category else None),
        gst_number=order.user.gst_number,
        shipping_address1=order.user.shipping_address1,
        shipping_address2=order.user.shipping_address2,
        shipping_pin=order.user.shipping_pin,
        shipping_city=order.user.shipping_city,
        shipping_state=order.user.shipping_state,
        shipping_country=order.user.shipping_country,
        created_at=order.user.created_at
    )

    return OrderDetailResponse(
        id=order.id,
        order_number=order.order_number,
        quote_id=order.quote_id,
        user_id=order.user_id,
        user=user_info,
        status=order.status.value,
        subtotal=order.subtotal,
        total_tax=order.total_tax,
        total=order.total,
        tax_breakdown=order.tax_breakdown,
        notes=order.notes,
        items=items,
        created_at=order.created_at,
        updated_at=order.updated_at
    )


def update_order_status(
    db: Session,
    order_id: int,
    status: Optional[str] = None,
    notes: Optional[str] = None
) -> OrderDetailResponse:
    """
    Update order status and notes (admin function).

    Args:
        db: Database session
        order_id: Order ID
        status: Optional new status
        notes: Optional new notes

    Returns:
        Updated order detail response

    Raises:
        ValueError: If order not found or invalid status
    """
    order = (
        db.query(Order)
        .filter(Order.id == order_id)
        .options(joinedload(Order.items), joinedload(Order.user))
        .first()
    )

    if not order:
        raise ValueError(f"Order with ID {order_id} not found")

    # Update status if provided
    if status is not None:
        try:
            order.status = OrderStatus(status.lower())
        except ValueError:
            raise ValueError(f"Invalid status: {status}. Valid statuses are: pending, processing, shipped, delivered, cancelled")

    # Update notes if provided
    if notes is not None:
        order.notes = notes

    db.commit()
    db.refresh(order)

    # Reload with items and user
    order_with_items = (
        db.query(Order)
        .filter(Order.id == order.id)
        .options(joinedload(Order.items), joinedload(Order.user))
        .first()
    )

    if not order_with_items:
        raise ValueError("Failed to retrieve updated order")

    # Convert to OrderDetailResponse
    from app.schemas.order import UserInfo
    
    items = []
    for item in order_with_items.items:
        items.append(OrderItemResponse(
            id=item.id,
            order_id=item.order_id,
            product_id=item.product_id,
            variant_id=item.variant_id,
            product_name=item.product_name,
            variant_name=item.variant_name,
            price=item.price,
            quantity=item.quantity,
            image=item.image,
            gst_rate=item.gst_rate,
            item_total=item.item_total,
            tax_amount=item.tax_amount,
            item_total_with_tax=item.item_total_with_tax,
            created_at=item.created_at
        ))

    user_info = UserInfo(
        id=order_with_items.user.id,
        email=order_with_items.user.email,
        role=order_with_items.user.role.value if hasattr(order_with_items.user.role, 'value') else str(order_with_items.user.role),
        is_active=order_with_items.user.is_active,
        created_at=order_with_items.user.created_at
    )

    return OrderDetailResponse(
        id=order_with_items.id,
        order_number=order_with_items.order_number,
        quote_id=order_with_items.quote_id,
        user_id=order_with_items.user_id,
        user=user_info,
        status=order_with_items.status.value,
        subtotal=order_with_items.subtotal,
        total_tax=order_with_items.total_tax,
        total=order_with_items.total,
        tax_breakdown=order_with_items.tax_breakdown,
        notes=order_with_items.notes,
        items=items,
        created_at=order_with_items.created_at,
        updated_at=order_with_items.updated_at
    )

