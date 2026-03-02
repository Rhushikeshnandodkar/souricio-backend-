"""
Order API schemas
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict
from datetime import datetime
from decimal import Decimal


class OrderCreate(BaseModel):
    """Schema for creating an order from a quote"""
    quote_id: int = Field(..., description="ID of the approved quote to place as order")


class OrderItemResponse(BaseModel):
    """Schema for order item response"""
    id: int
    order_id: int
    product_id: int
    variant_id: Optional[int] = None
    product_name: str
    variant_name: Optional[str] = None
    price: Decimal
    quantity: int
    image: Optional[str] = None
    gst_rate: Optional[Decimal] = None
    item_total: Optional[Decimal] = None
    tax_amount: Optional[Decimal] = None
    item_total_with_tax: Optional[Decimal] = None
    created_at: datetime

    class Config:
        from_attributes = True


class OrderResponse(BaseModel):
    """Schema for order response"""
    id: int
    order_number: str
    quote_id: int
    user_id: int
    status: str
    subtotal: Optional[Decimal] = None
    total_tax: Optional[Decimal] = None
    total: Optional[Decimal] = None
    tax_breakdown: Optional[Dict[str, Decimal]] = None
    notes: Optional[str] = None
    items: List[OrderItemResponse]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class OrderSummaryResponse(BaseModel):
    """Schema for order summary (list view)"""
    id: int
    order_number: str
    quote_id: int
    user_id: int
    status: str
    subtotal: Optional[Decimal] = None
    total_tax: Optional[Decimal] = None
    total: Optional[Decimal] = None
    tax_breakdown: Optional[Dict[str, Decimal]] = None
    item_count: int
    item_names: Optional[List[str]] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class OwnerOrderSummaryResponse(BaseModel):
    """Schema for order summary with user email (owner/admin view)"""
    id: int
    order_number: str
    quote_id: int
    user_id: int
    user_email: str
    status: str
    subtotal: Optional[Decimal] = None
    total_tax: Optional[Decimal] = None
    total: Optional[Decimal] = None
    tax_breakdown: Optional[Dict[str, Decimal]] = None
    item_count: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class UserInfo(BaseModel):
    """Schema for user information in order detail"""
    id: int
    email: str
    role: str
    is_active: bool
    category: Optional[str] = None
    gst_number: Optional[str] = None
    shipping_address1: Optional[str] = None
    shipping_address2: Optional[str] = None
    shipping_pin: Optional[str] = None
    shipping_city: Optional[str] = None
    shipping_state: Optional[str] = None
    shipping_country: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class OrderDetailResponse(BaseModel):
    """Schema for order detail response with user information (admin/owner view)"""
    id: int
    order_number: str
    quote_id: int
    user_id: int
    user: UserInfo
    status: str
    subtotal: Optional[Decimal] = None
    total_tax: Optional[Decimal] = None
    total: Optional[Decimal] = None
    tax_breakdown: Optional[Dict[str, Decimal]] = None
    notes: Optional[str] = None
    items: List[OrderItemResponse]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class AdminOrderUpdate(BaseModel):
    """Schema for admin order update"""
    status: Optional[str] = Field(None, description="New order status (pending, processing, shipped, delivered, cancelled)")
    notes: Optional[str] = Field(None, description="Order notes")

