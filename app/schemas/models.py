from pydantic import BaseModel
from typing import List, Dict, Optional, Generic, TypeVar, Any
from datetime import datetime
from decimal import Decimal
from enum import Enum

T = TypeVar('T')


# Product Status Enum
class ProductStatus(str, Enum):
    DRAFT = "draft"
    PUBLISHED = "published"
    ARCHIVED = "archived"
    OUT_OF_STOCK = "out_of_stock"


# Category Models
class CategoryBase(BaseModel):
    name: str
    description: Optional[str] = None


class CategoryCreate(CategoryBase):
    parent_id: Optional[int] = None
    image: Optional[str] = None
    icon: Optional[str] = None
    sort_order: Optional[int] = 0
    is_active: Optional[bool] = True
    meta_title: Optional[str] = None
    meta_description: Optional[str] = None


class CategoryUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    parent_id: Optional[int] = None
    image: Optional[str] = None
    icon: Optional[str] = None
    sort_order: Optional[int] = None
    is_active: Optional[bool] = None
    meta_title: Optional[str] = None
    meta_description: Optional[str] = None


class Category(CategoryBase):
    id: int
    slug: str
    parent_id: Optional[int] = None
    level: int = 0
    path: Optional[str] = None
    image: Optional[str] = None
    icon: Optional[str] = None
    sort_order: int = 0
    is_active: bool = True
    meta_title: Optional[str] = None
    meta_description: Optional[str] = None
    product_count: int = 0
    created_at: datetime
    updated_at: datetime
    created_by: Optional[int] = None
    updated_by: Optional[int] = None
    deleted_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# Tag Models
class TagBase(BaseModel):
    name: str
    description: Optional[str] = None


class TagCreate(TagBase):
    color: Optional[str] = None
    icon: Optional[str] = None
    is_active: Optional[bool] = True
    sort_order: Optional[int] = 0


class TagUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    color: Optional[str] = None
    icon: Optional[str] = None
    is_active: Optional[bool] = None
    sort_order: Optional[int] = None


class Tag(TagBase):
    id: int
    slug: str
    color: Optional[str] = None
    icon: Optional[str] = None
    is_active: bool = True
    sort_order: int = 0
    usage_count: int = 0
    created_at: datetime
    updated_at: datetime
    created_by: Optional[int] = None
    updated_by: Optional[int] = None
    deleted_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class ProductVariant(BaseModel):
    id: Optional[int] = None
    name: str
    sku: Optional[str] = None
    price: Optional[Decimal] = None
    originalPrice: Optional[Decimal] = None
    costPrice: Optional[Decimal] = None
    compareAtPrice: Optional[Decimal] = None
    stockQuantity: Optional[int] = 0
    lowStockThreshold: Optional[int] = None
    weight: Optional[Decimal] = None
    dimensions: Optional[Dict[str, Any]] = None
    barcode: Optional[str] = None
    specifications: Optional[Dict[str, str]] = {}
    images: Optional[List[str]] = []
    inStock: bool = True
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class ProductCreate(BaseModel):
    name: str
    description: Optional[str] = None
    brand: Optional[str] = None
    image: Optional[str] = None
    images: Optional[List[str]] = []
    category_id: Optional[int] = None
    tags: Optional[List[int]] = []  # List of tag IDs
    price: Optional[Decimal] = None

    # Inventory & Stock
    sku: Optional[str] = None
    slug: Optional[str] = None
    stock_quantity: Optional[int] = 0
    low_stock_threshold: Optional[int] = None
    track_inventory: Optional[bool] = True

    # Status & Visibility
    status: Optional[ProductStatus] = ProductStatus.DRAFT
    is_active: Optional[bool] = True
    is_featured: Optional[bool] = False
    is_bestseller: Optional[bool] = False
    published_at: Optional[datetime] = None

    # Pricing
    compare_at_price: Optional[Decimal] = None
    cost_price: Optional[Decimal] = None
    tax_class: Optional[str] = None
    currency: Optional[str] = "USD"

    # SEO
    meta_title: Optional[str] = None
    meta_description: Optional[str] = None
    meta_keywords: Optional[str] = None

    # Physical Attributes
    weight: Optional[Decimal] = None
    dimensions: Optional[Dict[str, Any]] = None
    shipping_class: Optional[str] = None

    # Organization
    sort_order: Optional[int] = 0

    variants: Optional[List[ProductVariant]] = []
    specifications: Optional[Dict[str, str]] = {}


class ProductSummary(BaseModel):
    """Simplified product model for list responses"""
    id: int
    name: str
    description: Optional[str] = None
    image: Optional[str] = None
    price: Optional[Decimal] = None
    sku: Optional[str] = None
    slug: Optional[str] = None
    category: Optional[str] = None  # Category name
    status: Optional[ProductStatus] = None
    is_active: Optional[bool] = True
    is_featured: Optional[bool] = False
    stock_quantity: Optional[int] = 0
    rating_average: Optional[Decimal] = None
    # Stock status fields (calculated based on variants if present)
    has_variants: Optional[bool] = False
    has_stock: Optional[bool] = False
    in_stock_variants_count: Optional[int] = 0

    class Config:
        from_attributes = True


class Product(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    brand: Optional[str] = None
    image: Optional[str] = None
    images: Optional[List[str]] = []
    category_id: Optional[int] = None
    # Category object with id, name, etc.
    category: Optional[Dict[str, Any]] = None
    # List of tag objects with id, name, etc.
    tags: Optional[List[Dict[str, Any]]] = []

    # Inventory & Stock
    sku: Optional[str] = None
    slug: Optional[str] = None
    stock_quantity: int = 0
    low_stock_threshold: Optional[int] = None
    track_inventory: bool = True

    # Status & Visibility
    status: ProductStatus = ProductStatus.DRAFT
    is_active: bool = True
    is_featured: bool = False
    is_bestseller: bool = False
    published_at: Optional[datetime] = None

    # Pricing & Commerce
    price: Optional[Decimal] = None
    compare_at_price: Optional[Decimal] = None
    cost_price: Optional[Decimal] = None
    tax_class: Optional[str] = None
    currency: str = "USD"

    # SEO & Marketing
    meta_title: Optional[str] = None
    meta_description: Optional[str] = None
    meta_keywords: Optional[str] = None

    # Physical Attributes
    weight: Optional[Decimal] = None
    dimensions: Optional[Dict[str, Any]] = None
    shipping_class: Optional[str] = None

    # Analytics & Performance
    view_count: int = 0
    purchase_count: int = 0
    rating_average: Decimal = Decimal("0.00")
    rating_count: int = 0

    # Organization
    sort_order: int = 0

    variants: Optional[List[ProductVariant]] = []
    specifications: Optional[Dict[str, str]] = {}

    # Audit
    created_at: datetime
    updated_at: datetime
    created_by: Optional[int] = None
    updated_by: Optional[int] = None
    deleted_at: Optional[datetime] = None
    version: int = 1

    class Config:
        from_attributes = True
