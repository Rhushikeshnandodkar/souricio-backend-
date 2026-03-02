"""
Price History business logic service
"""
from sqlalchemy.orm import Session
from typing import List, Optional
from decimal import Decimal
from datetime import datetime

from app.db.models.product_price_history import ProductPriceHistory
from app.schemas.quote import ProductPriceHistoryResponse


def store_price_history(
    db: Session,
    product_id: int,
    price: Decimal,
    created_by: int,
    variant_id: Optional[int] = None,
    quote_id: Optional[int] = None,
    quote_item_id: Optional[int] = None
) -> ProductPriceHistory:
    """
    Store a price in the price history.

    Args:
        db: Database session
        product_id: Product ID
        price: Price to store
        created_by: User ID who set the price
        variant_id: Optional variant ID
        quote_id: Optional quote ID where this price was used
        quote_item_id: Optional quote item ID where this price was used

    Returns:
        Created ProductPriceHistory instance
    """
    price_history = ProductPriceHistory(
        product_id=product_id,
        variant_id=variant_id,
        price=price,
        quote_id=quote_id,
        quote_item_id=quote_item_id,
        created_by=created_by
    )

    db.add(price_history)
    db.commit()
    db.refresh(price_history)

    return price_history


def get_price_history(
    db: Session,
    product_id: int,
    variant_id: Optional[int] = None,
    limit: int = 10
) -> List[ProductPriceHistoryResponse]:
    """
    Retrieve historical prices for a product/variant combination.
    Returns most recent prices first.

    Args:
        db: Database session
        product_id: Product ID
        variant_id: Optional variant ID
        limit: Maximum number of records to return (default: 10)

    Returns:
        List of price history entries, ordered by created_at DESC
    """
    query = (
        db.query(ProductPriceHistory)
        .filter(ProductPriceHistory.product_id == product_id)
        .order_by(ProductPriceHistory.created_at.desc())
    )

    # If variant_id is provided, filter by it; otherwise, get prices for base product (variant_id is None)
    if variant_id is not None:
        query = query.filter(ProductPriceHistory.variant_id == variant_id)
    else:
        query = query.filter(ProductPriceHistory.variant_id.is_(None))

    price_history = query.limit(limit).all()

    return [
        ProductPriceHistoryResponse(
            id=entry.id,
            product_id=entry.product_id,
            variant_id=entry.variant_id,
            price=entry.price,
            quote_id=entry.quote_id,
            quote_item_id=entry.quote_item_id,
            created_by=entry.created_by,
            created_at=entry.created_at
        )
        for entry in price_history
    ]


def get_latest_price(
    db: Session,
    product_id: int,
    variant_id: Optional[int] = None
) -> Optional[Decimal]:
    """
    Get the most recent price for a product/variant combination.

    Args:
        db: Database session
        product_id: Product ID
        variant_id: Optional variant ID

    Returns:
        Most recent price or None if no history exists
    """
    query = (
        db.query(ProductPriceHistory)
        .filter(ProductPriceHistory.product_id == product_id)
        .order_by(ProductPriceHistory.created_at.desc())
    )

    # If variant_id is provided, filter by it; otherwise, get prices for base product (variant_id is None)
    if variant_id is not None:
        query = query.filter(ProductPriceHistory.variant_id == variant_id)
    else:
        query = query.filter(ProductPriceHistory.variant_id.is_(None))

    latest_entry = query.first()

    return latest_entry.price if latest_entry else None
