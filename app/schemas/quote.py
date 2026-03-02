"""
Quote API schemas
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict
from datetime import datetime
from decimal import Decimal


class QuoteCreate(BaseModel):
    """Schema for creating a quote from cart"""
    notes: Optional[str] = Field(
        None, description="User notes/comments for the quote")
    expires_at: Optional[datetime] = Field(
        None, description="Quote expiration date")


class QuoteUpdate(BaseModel):
    """Schema for updating a quote"""
    status: Optional[str] = Field(
        None, description="Quote status (draft, pending, approved, rejected, expired)")
    notes: Optional[str] = Field(None, description="User notes/comments")
    expires_at: Optional[datetime] = Field(
        None, description="Quote expiration date")


class AdminQuoteUpdate(BaseModel):
    """Schema for admin updating a quote"""
    status: Optional[str] = Field(
        None, description="Quote status (draft, pending, approved, rejected, expired)")
    admin_notes: Optional[str] = Field(
        None, description="Admin notes/comments")


class QuoteItemResponse(BaseModel):
    """Schema for quote item response"""
    id: int
    product_id: int
    variant_id: Optional[int] = None
    product_name: str
    variant_name: Optional[str] = None
    price: Decimal
    requires_custom_price: bool = False
    quantity: int
    image: Optional[str] = None
    gst_rate: Optional[Decimal] = None
    item_total: Optional[Decimal] = None
    tax_amount: Optional[Decimal] = None
    item_total_with_tax: Optional[Decimal] = None
    created_at: datetime

    class Config:
        from_attributes = True


class QuoteResponse(BaseModel):
    """Schema for quote response"""
    id: int
    quote_number: str
    user_id: int
    status: str
    expires_at: Optional[datetime] = None
    notes: Optional[str] = None
    admin_notes: Optional[str] = None
    subtotal: Optional[Decimal] = None
    total_tax: Optional[Decimal] = None
    total: Optional[Decimal] = None
    tax_breakdown: Optional[Dict[str, Decimal]] = None
    has_custom_pricing: Optional[bool] = False
    items: List[QuoteItemResponse]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class QuoteSummaryResponse(BaseModel):
    """Schema for quote summary (list view)"""
    id: int
    quote_number: str
    user_id: int
    status: str
    expires_at: Optional[datetime] = None
    subtotal: Optional[Decimal] = None
    total_tax: Optional[Decimal] = None
    total: Optional[Decimal] = None
    tax_breakdown: Optional[Dict[str, Decimal]] = None
    has_custom_pricing: Optional[bool] = False
    item_count: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class OwnerQuoteSummaryResponse(BaseModel):
    """Schema for quote summary with user email (owner view)"""
    id: int
    quote_number: str
    user_id: int
    user_email: str
    status: str
    expires_at: Optional[datetime] = None
    subtotal: Optional[Decimal] = None
    total_tax: Optional[Decimal] = None
    total: Optional[Decimal] = None
    tax_breakdown: Optional[Dict[str, Decimal]] = None
    has_custom_pricing: Optional[bool] = False
    item_count: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class UserInfo(BaseModel):
    """Schema for user information in quote detail"""
    id: int
    email: str
    role: str
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class QuoteDetailResponse(BaseModel):
    """Schema for quote detail response with user information (admin/owner view)"""
    id: int
    quote_number: str
    user_id: int
    user: UserInfo
    status: str
    expires_at: Optional[datetime] = None
    notes: Optional[str] = None
    admin_notes: Optional[str] = None
    subtotal: Optional[Decimal] = None
    total_tax: Optional[Decimal] = None
    total: Optional[Decimal] = None
    tax_breakdown: Optional[Dict[str, Decimal]] = None
    has_custom_pricing: Optional[bool] = False
    items: List[QuoteItemResponse]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class QuoteItemPriceUpdate(BaseModel):
    """Schema for updating quote item price"""
    price: Decimal = Field(..., gt=0,
                           description="New price for the quote item (must be greater than 0)")


class ProductPriceHistoryResponse(BaseModel):
    """Schema for product price history entry"""
    id: int
    product_id: int
    variant_id: Optional[int] = None
    price: Decimal
    quote_id: Optional[int] = None
    quote_item_id: Optional[int] = None
    created_by: int
    created_at: datetime

    class Config:
        from_attributes = True


class PriceHistoryResponse(BaseModel):
    """Schema for price history list response"""
    prices: List[ProductPriceHistoryResponse]
    product_id: int
    variant_id: Optional[int] = None


class QuoteItemGstUpdate(BaseModel):
    """Schema for updating quote item GST rate"""
    gst_rate: Optional[Decimal] = Field(
        None,
        description="GST rate percentage (5.00, 12.00, 18.00, 28.00). Set to null to remove GST."
    )
