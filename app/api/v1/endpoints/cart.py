"""
Cart API endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.dependencies import get_db, get_current_user
from app.db.models.user import User
from app.schemas.cart import (
    CartItemCreate,
    CartItemUpdate,
    CartResponse,
    CartBulkUpdate,
)
from app.schemas.response import APIResponse, ErrorResponse, ErrorDetail
from app.services.cart_service import (
    get_user_cart,
    add_to_cart,
    update_cart_item as update_cart_item_service,
    remove_cart_item,
    clear_user_cart,
    bulk_update_cart,
)

router = APIRouter()


@router.get("", response_model=APIResponse, tags=["Cart"])
def get_cart(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get user's cart.

    Args:
        current_user: Current authenticated user
        db: Database session

    Returns:
        Standard API response with cart data
    """
    try:
        cart = get_user_cart(db, current_user.id)
        return APIResponse(
            status="success",
            message="Cart retrieved successfully",
            data=cart.model_dump()
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                status="error",
                message="Failed to retrieve cart",
                error=ErrorDetail(
                    code="CART_FETCH_ERROR",
                    message=str(e)
                )
            ).model_dump()
        )


@router.post("", response_model=APIResponse, status_code=status.HTTP_201_CREATED, tags=["Cart"])
def add_item_to_cart(
    item: CartItemCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Add item to cart.

    Args:
        item: Cart item to add
        current_user: Current authenticated user
        db: Database session

    Returns:
        Standard API response with updated cart
    """
    try:
        add_to_cart(
            db=db,
            user_id=current_user.id,
            product_id=item.product_id,
            variant_id=item.variant_id,
            quantity=item.quantity
        )

        # Return updated cart
        cart = get_user_cart(db, current_user.id)
        return APIResponse(
            status="success",
            message="Item added to cart successfully",
            data=cart.model_dump()
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ErrorResponse(
                status="error",
                message="Failed to add item to cart",
                error=ErrorDetail(
                    code="INVALID_CART_ITEM",
                    message=str(e)
                )
            ).model_dump()
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                status="error",
                message="Failed to add item to cart",
                error=ErrorDetail(
                    code="CART_ADD_ERROR",
                    message=str(e)
                )
            ).model_dump()
        )


@router.put("/{item_id}", response_model=APIResponse, tags=["Cart"])
def update_cart_item(
    item_id: int,
    update: CartItemUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Update cart item quantity.

    Args:
        item_id: Cart item ID
        update: Update data with new quantity
        current_user: Current authenticated user
        db: Database session

    Returns:
        Standard API response with updated cart
    """
    try:
        # Verify cart item belongs to user
        from app.db.models.cart import Cart
        cart_item = (
            db.query(Cart)
            .filter(Cart.id == item_id, Cart.user_id == current_user.id)
            .first()
        )

        if not cart_item:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=ErrorResponse(
                    status="error",
                    message="Cart item not found",
                    error=ErrorDetail(
                        code="CART_ITEM_NOT_FOUND",
                        message="Cart item does not exist or does not belong to you"
                    )
                ).model_dump()
            )

        update_cart_item_service(db, item_id, update.quantity)

        # Return updated cart
        cart = get_user_cart(db, current_user.id)
        return APIResponse(
            status="success",
            message="Cart item updated successfully",
            data=cart.model_dump()
        )
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ErrorResponse(
                status="error",
                message="Failed to update cart item",
                error=ErrorDetail(
                    code="INVALID_QUANTITY",
                    message=str(e)
                )
            ).model_dump()
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                status="error",
                message="Failed to update cart item",
                error=ErrorDetail(
                    code="CART_UPDATE_ERROR",
                    message=str(e)
                )
            ).model_dump()
        )


@router.delete("/{item_id}", response_model=APIResponse, tags=["Cart"])
def remove_item_from_cart(
    item_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Remove item from cart.

    Args:
        item_id: Cart item ID
        current_user: Current authenticated user
        db: Database session

    Returns:
        Standard API response with updated cart
    """
    try:
        deleted = remove_cart_item(db, item_id, current_user.id)

        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=ErrorResponse(
                    status="error",
                    message="Cart item not found",
                    error=ErrorDetail(
                        code="CART_ITEM_NOT_FOUND",
                        message="Cart item does not exist or does not belong to you"
                    )
                ).model_dump()
            )

        # Return updated cart
        cart = get_user_cart(db, current_user.id)
        return APIResponse(
            status="success",
            message="Item removed from cart successfully",
            data=cart.model_dump()
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                status="error",
                message="Failed to remove item from cart",
                error=ErrorDetail(
                    code="CART_REMOVE_ERROR",
                    message=str(e)
                )
            ).model_dump()
        )


@router.delete("", response_model=APIResponse, tags=["Cart"])
def clear_cart(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Clear entire cart.

    Args:
        current_user: Current authenticated user
        db: Database session

    Returns:
        Standard API response
    """
    try:
        deleted_count = clear_user_cart(db, current_user.id)
        return APIResponse(
            status="success",
            message=f"Cart cleared successfully. {deleted_count} items removed.",
            data={"deleted_count": deleted_count}
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                status="error",
                message="Failed to clear cart",
                error=ErrorDetail(
                    code="CART_CLEAR_ERROR",
                    message=str(e)
                )
            ).model_dump()
        )


@router.post("/bulk", response_model=APIResponse, tags=["Cart"])
def bulk_update_cart_items(
    bulk_update: CartBulkUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Bulk update/merge cart items.

    Args:
        bulk_update: Bulk update data with items list
        current_user: Current authenticated user
        db: Database session

    Returns:
        Standard API response with updated cart
    """
    try:
        items = [item.model_dump() for item in bulk_update.items]
        cart = bulk_update_cart(db, current_user.id, items)
        return APIResponse(
            status="success",
            message="Cart updated successfully",
            data=cart.model_dump()
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                status="error",
                message="Failed to update cart",
                error=ErrorDetail(
                    code="CART_BULK_UPDATE_ERROR",
                    message=str(e)
                )
            ).model_dump()
        )
