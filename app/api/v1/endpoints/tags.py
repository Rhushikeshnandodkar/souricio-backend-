"""
Tag API endpoints
"""
import logging
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from sqlalchemy import select
from fastapi_pagination import Page
from fastapi_pagination.ext.sqlalchemy import paginate

from app.dependencies import get_db
from app.db.models.tag import Tag
from app.schemas.models import TagCreate, TagUpdate, Tag as TagSchema
from app.services.tag_service import (
    get_tag_by_id,
    create_tag,
    update_tag,
    delete_tag
)
from app.services.cache_service import (
    get_or_cache,
    tags_list_key,
    tag_key,
    DEFAULT_TTL_LIST,
    DEFAULT_TTL_ITEM
)

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("", response_model=Page[TagSchema], tags=["Tags"])
async def get_all_tags(
    request: Request,
    db: Session = Depends(get_db)
) -> Page[TagSchema]:
    """
    Retrieve paginated tags from the database.
    Uses fastapi-pagination for automatic pagination handling.
    """
    try:
        # Get pagination params from query string
        page = int(request.query_params.get("page", 1))
        size = int(request.query_params.get("size", 50))
        
        # Generate cache key
        cache_key = tags_list_key(page=page, size=size)
        
        # Define fetch function for cache miss (synchronous paginate wrapped properly)
        def fetch_tags():
            return paginate(
                db,
                select(Tag).filter(
                    Tag.deleted_at.is_(None)
                ).order_by(
                    Tag.sort_order,
                    Tag.id),
                transformer=lambda items: [
                    TagSchema.model_validate(tag) for tag in items]
            )
        
        # Get from cache or fetch (handle Redis errors gracefully)
        try:
            result = await get_or_cache(
                cache_key,
                fetch_tags,
                ttl=DEFAULT_TTL_LIST
            )
        except Exception as cache_error:
            # If cache fails, fetch directly from database
            logger.warning(f"Cache operation failed, fetching directly from database: {str(cache_error)}")
            result = fetch_tags()
        
        # If result is a dict (from cache), reconstruct Page object
        if isinstance(result, dict) and 'items' in result:
            from fastapi_pagination import Page as PageModel
            # Reconstruct items as TagSchema objects
            items = []
            for item in result.get('items', []):
                if isinstance(item, dict):
                    try:
                        items.append(TagSchema.model_validate(item))
                    except Exception:
                        items.append(TagSchema(**item))
                elif hasattr(item, 'model_dump'):
                    items.append(item)
                else:
                    items.append(item)
            result = PageModel[TagSchema](
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
        print(f"Error retrieving tags: {error_trace}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving tags: {str(e)}"
        )


@router.get("/{tag_id}", response_model=TagSchema, tags=["Tags"])
async def get_tag(tag_id: int, db: Session = Depends(get_db)) -> TagSchema:
    """Retrieve a specific tag by ID."""
    cache_key = tag_key(tag_id)
    
    async def fetch_tag():
        db_tag = get_tag_by_id(db, tag_id)
        
        if not db_tag:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Tag with ID {tag_id} not found"
            )
        
        return TagSchema.model_validate(db_tag)
    
    # Get from cache or fetch
    result = await get_or_cache(
        cache_key,
        fetch_tag,
        ttl=DEFAULT_TTL_ITEM
    )
    
    return result


@router.post("", response_model=TagSchema, status_code=status.HTTP_201_CREATED, tags=["Tags"])
def create_new_tag(tag: TagCreate, db: Session = Depends(get_db)) -> TagSchema:
    """Create a new tag."""
    try:
        new_tag = create_tag(db, tag)
        return TagSchema.model_validate(new_tag)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating tag: {str(e)}"
        )


@router.put("/{tag_id}", response_model=TagSchema, tags=["Tags"])
def update_existing_tag(
    tag_id: int,
    tag: TagUpdate,
    db: Session = Depends(get_db)
) -> TagSchema:
    """Update an existing tag by ID."""
    try:
        updated_tag = update_tag(db, tag_id, tag)
        return TagSchema.model_validate(updated_tag)
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
            detail=f"Error updating tag: {str(e)}"
        )


@router.delete("/{tag_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["Tags"])
def delete_existing_tag(tag_id: int, db: Session = Depends(get_db)) -> None:
    """Soft delete a tag by ID."""
    try:
        delete_tag(db, tag_id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deleting tag: {str(e)}"
        )
