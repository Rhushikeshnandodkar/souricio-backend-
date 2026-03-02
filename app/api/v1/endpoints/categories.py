"""
Category API endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from sqlalchemy import select
from fastapi_pagination import Page
from fastapi_pagination.ext.sqlalchemy import paginate

from app.dependencies import get_db
from app.db.models.category import Category
from app.schemas.models import CategoryCreate, CategoryUpdate, Category as CategorySchema
from app.services.category_service import (
    get_category_by_id,
    create_category,
    update_category,
    delete_category
)
from app.services.cache_service import (
    get_or_cache,
    categories_list_key,
    category_key,
    DEFAULT_TTL_LIST,
    DEFAULT_TTL_ITEM
)

router = APIRouter()


@router.get("", response_model=Page[CategorySchema], tags=["Categories"])
async def get_all_categories(
    request: Request,
    db: Session = Depends(get_db)
) -> Page[CategorySchema]:
    """
    Retrieve paginated categories from the database.
    Uses fastapi-pagination for automatic pagination handling.
    """
    try:
        # Get pagination params from query string
        page = int(request.query_params.get("page", 1))
        size = int(request.query_params.get("size", 50))
        
        # Generate cache key
        cache_key = categories_list_key(page=page, size=size)
        
        # Define fetch function for cache miss
        async def fetch_categories():
            return paginate(
                db,
                select(Category).filter(
                    Category.deleted_at.is_(None)
                ).order_by(
                    Category.sort_order,
                    Category.id),
                transformer=lambda items: [
                    CategorySchema.model_validate(category) for category in items]
            )
        
        # Get from cache or fetch
        result = await get_or_cache(
            cache_key,
            fetch_categories,
            ttl=DEFAULT_TTL_LIST
        )
        
        # If result is a dict (from cache), reconstruct Page object
        if isinstance(result, dict) and 'items' in result:
            from fastapi_pagination import Page as PageModel
            # Reconstruct items as CategorySchema objects
            items = []
            for item in result.get('items', []):
                if isinstance(item, dict):
                    try:
                        items.append(CategorySchema.model_validate(item))
                    except Exception:
                        items.append(CategorySchema(**item))
                elif hasattr(item, 'model_dump'):
                    items.append(item)
                else:
                    items.append(item)
            result = PageModel[CategorySchema](
                items=items,
                total=int(result.get('total', 0)),
                page=int(result.get('page', page)),
                size=int(result.get('size', size)),
                pages=int(result.get('pages', 1))
            )
        
        return result
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        print(f"Error retrieving categories: {error_trace}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving categories: {str(e)}"
        )


@router.get("/{category_id}", response_model=CategorySchema, tags=["Categories"])
async def get_category(category_id: int, db: Session = Depends(get_db)) -> CategorySchema:
    """Retrieve a specific category by ID."""
    cache_key = category_key(category_id)
    
    async def fetch_category():
        db_category = get_category_by_id(db, category_id)
        
        if not db_category:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Category with ID {category_id} not found"
            )
        
        return CategorySchema.model_validate(db_category)
    
    # Get from cache or fetch
    result = await get_or_cache(
        cache_key,
        fetch_category,
        ttl=DEFAULT_TTL_ITEM
    )
    
    return result


@router.post("", response_model=CategorySchema, status_code=status.HTTP_201_CREATED, tags=["Categories"])
def create_new_category(category: CategoryCreate, db: Session = Depends(get_db)) -> CategorySchema:
    """Create a new category."""
    try:
        new_category = create_category(db, category)
        return CategorySchema.model_validate(new_category)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST if "already exists" in str(
                e) else status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating category: {str(e)}"
        )


@router.put("/{category_id}", response_model=CategorySchema, tags=["Categories"])
def update_existing_category(
    category_id: int,
    category: CategoryUpdate,
    db: Session = Depends(get_db)
) -> CategorySchema:
    """Update an existing category by ID."""
    try:
        updated_category = update_category(db, category_id, category)
        return CategorySchema.model_validate(updated_category)
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
            detail=f"Error updating category: {str(e)}"
        )


@router.delete("/{category_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["Categories"])
def delete_existing_category(category_id: int, db: Session = Depends(get_db)) -> None:
    """Soft delete a category by ID."""
    try:
        delete_category(db, category_id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deleting category: {str(e)}"
        )
