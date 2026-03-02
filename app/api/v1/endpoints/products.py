"""
Product API endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import select, or_
from fastapi_pagination import Page
from fastapi_pagination.ext.sqlalchemy import paginate
from typing import Optional

from app.dependencies import get_db, get_current_user
from app.db.models.product import Product
from app.db.models.category import Category
from app.db.models.user import User, UserRole
from app.schemas.models import ProductCreate, Product as ProductSchema, ProductSummary
from app.services.product_service import (
    get_product_by_id,
    create_product,
    update_product,
    delete_product,
    db_product_to_summary,
    db_product_to_pydantic
)
from app.services.cache_service import (
    get_or_cache,
    products_list_key,
    product_key,
    DEFAULT_TTL_LIST,
    DEFAULT_TTL_ITEM
)
from fastapi import Request
import json
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("", response_model=Page[ProductSummary], tags=["Products"])
async def get_all_products(
    request: Request,
    category: Optional[str] = Query(None, description="Filter products by category slug"),
    search: Optional[str] = Query(None, description="Search products by name, description, SKU, or brand"),
    db: Session = Depends(get_db)
) -> Page[ProductSummary]:
    """
    Retrieve paginated products from the database (simplified response).
    Uses fastapi-pagination for automatic pagination handling.
    
    Optionally filter by category slug using the 'category' query parameter.
    Optionally search products by name, description, SKU, or brand using the 'search' query parameter.
    Example: /api/v1/products?category=electronics&search=laptop
    """
    try:
        # Get pagination params from query string
        page = int(request.query_params.get("page", 1))
        size = int(request.query_params.get("size", 50))
        
        # Generate cache key
        cache_key = products_list_key(category=category, search=search, page=page, size=size)
        
        # Define fetch function for cache miss
        async def fetch_products():
            # Build base query with eager loading of category and variants relationships
            query = select(Product).options(
                joinedload(Product.category),
                joinedload(Product.variants)
            ).filter(
                Product.deleted_at.is_(None)
            )
            
            # If search parameter is provided, add search filters
            if search:
                search_term = f"%{search.strip()}%"
                query = query.filter(
                    or_(
                        Product.name.ilike(search_term),
                        Product.description.ilike(search_term),
                        Product.sku.ilike(search_term),
                        Product.brand.ilike(search_term),
                        Product.meta_keywords.ilike(search_term)
                    )
                )
            
            # If category parameter is provided, filter by category
            if category:
                # Look up category by slug
                db_category = db.query(Category).filter(
                    Category.slug == category,
                    Category.deleted_at.is_(None)
                ).first()
                
                if not db_category:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail=f"Category with slug '{category}' not found"
                    )
                
                # Add category filter to query
                query = query.filter(Product.category_id == db_category.id)
            
            # Apply ordering and pagination
            query = query.order_by(Product.sort_order, Product.id)
            
            return paginate(
                db,
                query,
                transformer=lambda items: [
                    db_product_to_summary(product) for product in items]
            )
        
        # Get from cache or fetch
        result = await get_or_cache(
            cache_key,
            fetch_products,
            ttl=DEFAULT_TTL_LIST
        )
        
        # Check if result needs reconstruction
        from fastapi_pagination import Page as PageModel
        
        # Check if result is already a Page object (from fresh fetch) - return as-is
        # Page objects are not dicts, so check type first
        if not isinstance(result, dict) and not isinstance(result, str):
            # Check if it has Page-like attributes
            if hasattr(result, 'items') and hasattr(result, 'total') and hasattr(result, 'page') and hasattr(result, 'size'):
                # It's already a Page object, return it
                return result
        
        # If result is a string (shouldn't happen but handle it)
        if isinstance(result, str):
            try:
                result = json.loads(result)
            except:
                # If parsing fails, fetch fresh
                logger.warning("Failed to parse cached result as JSON, fetching fresh")
                result = await fetch_products()
                return result
        
        # If result is a dict (from cache), reconstruct Page object
        if isinstance(result, dict) and 'items' in result:
            # Reconstruct items as ProductSummary objects
            items = []
            for item in result.get('items', []):
                if isinstance(item, dict):
                    # Handle nested dict items - use model_validate for better compatibility
                    try:
                        items.append(ProductSummary.model_validate(item))
                    except Exception as e:
                        # Fallback to direct construction
                        try:
                            items.append(ProductSummary(**item))
                        except Exception:
                            # Last resort: log and skip
                            logger.warning(f"Failed to reconstruct ProductSummary from cache: {e}")
                            continue
                elif hasattr(item, 'model_dump'):
                    # Already a Pydantic model
                    items.append(item)
                else:
                    items.append(item)
            
            # Reconstruct Page object
            result = PageModel[ProductSummary](
                items=items,
                total=int(result.get('total', 0)),
                page=int(result.get('page', page)),
                size=int(result.get('size', size)),
                pages=int(result.get('pages', 1))
            )
        else:
            # If result is neither Page object nor dict, something went wrong - fetch fresh
            logger.warning(f"Unexpected result type from cache: {type(result)}, fetching fresh")
            result = await fetch_products()
        
        return result
    except HTTPException:
        # Re-raise HTTP exceptions (like 404 for category not found)
        raise
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        print(f"Error retrieving products: {error_trace}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving products: {str(e)}"
        )


@router.get("/{product_id}", response_model=ProductSchema, tags=["Products"])
async def get_product(product_id: int, db: Session = Depends(get_db)) -> ProductSchema:
    """Retrieve a specific product by ID."""
    cache_key = product_key(product_id)
    
    async def fetch_product():
        db_product = get_product_by_id(db, product_id)
        
        if not db_product:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Product with ID {product_id} not found"
            )
        
        return db_product_to_pydantic(db_product)
    
    # Get from cache or fetch
    result = await get_or_cache(
        cache_key,
        fetch_product,
        ttl=DEFAULT_TTL_ITEM
    )
    
    return result


@router.post("", response_model=ProductSchema, status_code=status.HTTP_201_CREATED, tags=["Products"])
def create_new_product(
    product: ProductCreate, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> ProductSchema:
    """Create a new product with variants, category, and tags."""
    # Check if user is owner
    if current_user.role != UserRole.OWNER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="only Product owners are allowed to add the product"
        )
    
    try:
        new_product = create_product(db, product)
        # Reload with relationships
        db_product = get_product_by_id(db, new_product.id)
        return db_product_to_pydantic(db_product)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating product: {str(e)}"
        )


@router.put("/{product_id}", response_model=ProductSchema, tags=["Products"])
def update_existing_product(
    product_id: int,
    product: ProductCreate,
    db: Session = Depends(get_db)
) -> ProductSchema:
    """Update an existing product by ID."""
    try:
        updated_product = update_product(db, product_id, product)
        # Reload with relationships
        db_product = get_product_by_id(db, product_id)
        return db_product_to_pydantic(db_product)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND if "not found" in str(
                e).lower() else status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating product: {str(e)}"
        )


@router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["Products"])
def delete_existing_product(product_id: int, db: Session = Depends(get_db)) -> None:
    """Soft delete a product by ID."""
    try:
        delete_product(db, product_id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deleting product: {str(e)}"
        )
