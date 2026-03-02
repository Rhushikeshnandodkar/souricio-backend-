"""
Cart API schemas
"""
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from decimal import Decimal


class CartItemCreate(BaseModel):
    """Schema for adding an item to cart"""
    product_id: int = Field(..., description="Product ID")
    variant_id: Optional[int] = Field(None, description="Product variant ID (optional)")
    quantity: int = Field(1, ge=1, description="Quantity to add")


class CartItemUpdate(BaseModel):
    """Schema for updating cart item quantity"""
    quantity: int = Field(..., ge=1, description="New quantity")


class CartItemResponse(BaseModel):
    """Schema for cart item response"""
    id: int
    product_id: int
    variant_id: Optional[int] = None
    product_name: str
    variant_name: Optional[str] = None
    price: Decimal
    image: Optional[str] = None
    quantity: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class CartResponse(BaseModel):
    """Schema for cart response"""
    items: List[CartItemResponse]
    total_items: int
    total_price: Decimal


class CartBulkItem(BaseModel):
    """Schema for bulk cart update item"""
    product_id: int
    variant_id: Optional[int] = None
    quantity: int = Field(..., ge=1)


class CartBulkUpdate(BaseModel):
    """Schema for bulk cart update"""
    items: List[CartBulkItem] = Field(..., description="List of cart items to update")
