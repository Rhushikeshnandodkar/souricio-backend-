"""
Cart business logic service
"""
from sqlalchemy.orm import Session, joinedload
from typing import List, Optional
from decimal import Decimal

from app.db.models.cart import Cart
from app.db.models.product import Product
from app.db.models.product_variant import ProductVariant
from app.schemas.cart import CartItemResponse, CartResponse


def get_user_cart(db: Session, user_id: int) -> CartResponse:
    """
    Fetch all cart items for a user with product/variant details.
    
    Args:
        db: Database session
        user_id: User ID
        
    Returns:
        CartResponse with items, total_items, and total_price
    """
    cart_items = (
        db.query(Cart)
        .filter(Cart.user_id == user_id)
        .options(
            joinedload(Cart.product),
            joinedload(Cart.variant)
        )
        .all()
    )
    
    items = []
    total_items = 0
    total_price = Decimal("0.00")
    
    for cart_item in cart_items:
        product = cart_item.product
        variant = cart_item.variant
        
        # Determine price - use variant price if exists, otherwise product price
        # Convert None to 0 for custom pricing (frontend will display as "Request for Quote")
        raw_price = variant.price if variant else product.price
        price = raw_price if raw_price is not None else Decimal("0.00")
        
        # Determine product name and variant name
        product_name = product.name
        variant_name = variant.name if variant else None
        
        # Determine image - prefer variant image, fallback to product image
        image = None
        if variant:
            if variant.images and len(variant.images) > 0:
                image = variant.images[0]
            elif product.images and len(product.images) > 0:
                image = product.images[0]
        else:
            if product.images and len(product.images) > 0:
                image = product.images[0]
            elif product.image:
                image = product.image
        
        item_response = CartItemResponse(
            id=cart_item.id,
            product_id=cart_item.product_id,
            variant_id=cart_item.variant_id,
            product_name=product_name,
            variant_name=variant_name,
            price=price,
            image=image,
            quantity=cart_item.quantity,
            created_at=cart_item.created_at,
            updated_at=cart_item.updated_at,
        )
        
        items.append(item_response)
        total_items += cart_item.quantity
        # Only add to total if price is not 0 (custom pricing)
        if price != Decimal("0.00"):
            total_price += price * Decimal(cart_item.quantity)
    
    return CartResponse(
        items=items,
        total_items=total_items,
        total_price=total_price,
    )


def add_to_cart(
    db: Session,
    user_id: int,
    product_id: int,
    variant_id: Optional[int],
    quantity: int = 1
) -> Cart:
    """
    Add item to cart or update quantity if item already exists.
    Handles unique constraint by updating existing item.
    
    Args:
        db: Database session
        user_id: User ID
        product_id: Product ID
        variant_id: Variant ID (optional)
        quantity: Quantity to add
        
    Returns:
        Cart item (created or updated)
        
    Raises:
        ValueError: If product or variant doesn't exist
    """
    # Verify product exists
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise ValueError(f"Product with ID {product_id} not found")
    
    # Verify variant exists if provided
    if variant_id:
        variant = (
            db.query(ProductVariant)
            .filter(
                ProductVariant.id == variant_id,
                ProductVariant.product_id == product_id,
                ProductVariant.deleted_at.is_(None)
            )
            .first()
        )
        if not variant:
            raise ValueError(f"Variant with ID {variant_id} not found for product {product_id}")
    
    # Check if cart item already exists
    existing_item = (
        db.query(Cart)
        .filter(
            Cart.user_id == user_id,
            Cart.product_id == product_id,
            Cart.variant_id == variant_id
        )
        .first()
    )
    
    if existing_item:
        # Update quantity
        existing_item.quantity += quantity
        db.commit()
        db.refresh(existing_item)
        return existing_item
    else:
        # Create new cart item
        cart_item = Cart(
            user_id=user_id,
            product_id=product_id,
            variant_id=variant_id,
            quantity=quantity,
        )
        db.add(cart_item)
        db.commit()
        db.refresh(cart_item)
        return cart_item


def update_cart_item(db: Session, cart_id: int, quantity: int) -> Cart:
    """
    Update cart item quantity.
    
    Args:
        db: Database session
        cart_id: Cart item ID
        quantity: New quantity
        
    Returns:
        Updated cart item
        
    Raises:
        ValueError: If cart item doesn't exist
    """
    cart_item = db.query(Cart).filter(Cart.id == cart_id).first()
    if not cart_item:
        raise ValueError(f"Cart item with ID {cart_id} not found")
    
    cart_item.quantity = quantity
    db.commit()
    db.refresh(cart_item)
    return cart_item


def remove_cart_item(db: Session, cart_id: int, user_id: int) -> bool:
    """
    Remove cart item.
    
    Args:
        db: Database session
        cart_id: Cart item ID
        user_id: User ID (for security check)
        
    Returns:
        True if item was deleted, False if not found
        
    Raises:
        ValueError: If cart item doesn't belong to user
    """
    cart_item = (
        db.query(Cart)
        .filter(Cart.id == cart_id, Cart.user_id == user_id)
        .first()
    )
    
    if not cart_item:
        return False
    
    db.delete(cart_item)
    db.commit()
    return True


def clear_user_cart(db: Session, user_id: int) -> int:
    """
    Clear all cart items for a user.
    
    Args:
        db: Database session
        user_id: User ID
        
    Returns:
        Number of items deleted
    """
    deleted_count = (
        db.query(Cart)
        .filter(Cart.user_id == user_id)
        .delete()
    )
    db.commit()
    return deleted_count


def bulk_update_cart(
    db: Session,
    user_id: int,
    items: List[dict]
) -> CartResponse:
    """
    Bulk update/merge cart items.
    For each item:
    - If product+variant combination exists, update quantity
    - If doesn't exist, create new cart item
    
    Args:
        db: Database session
        user_id: User ID
        items: List of dicts with product_id, variant_id (optional), quantity
        
    Returns:
        Updated cart response
    """
    # Clear existing cart first (or merge logic can be implemented)
    # For simplicity, we'll replace the cart
    clear_user_cart(db, user_id)
    
    # Add all items
    for item in items:
        product_id = item.get("product_id")
        variant_id = item.get("variant_id")
        quantity = item.get("quantity", 1)
        
        try:
            add_to_cart(db, user_id, product_id, variant_id, quantity)
        except ValueError as e:
            # Log error but continue with other items
            print(f"Error adding item to cart: {e}")
            continue
    
    # Return updated cart
    return get_user_cart(db, user_id)
