"""
Tag business logic service
"""
from sqlalchemy.orm import Session
from typing import Optional

from app.db.models.tag import Tag
from app.schemas.models import TagCreate, TagUpdate, Tag as TagSchema
from app.services.utils import generate_slug, get_unique_slug
from app.services.cache_service import (
    delete_from_cache,
    invalidate_pattern,
    tag_key,
    tags_list_key
)
import logging

logger = logging.getLogger(__name__)


def get_tag_by_id(db: Session, tag_id: int) -> Optional[Tag]:
    """Get a tag by ID."""
    return db.query(Tag).filter(
        Tag.id == tag_id,
        Tag.deleted_at.is_(None)
    ).first()


def create_tag(db: Session, tag_data: TagCreate) -> Tag:
    """Create a new tag."""
    # Check if tag with same name already exists
    existing_tag = db.query(Tag).filter(
        Tag.name == tag_data.name
    ).first()

    if existing_tag:
        raise ValueError(f"Tag with name '{tag_data.name}' already exists")

    # Generate unique slug from name
    base_slug = generate_slug(tag_data.name)
    unique_slug = get_unique_slug(db, base_slug, Tag)

    new_tag = Tag(
        name=tag_data.name,
        slug=unique_slug,
        description=tag_data.description,
        color=tag_data.color,
        icon=tag_data.icon,
        is_active=tag_data.is_active if tag_data.is_active is not None else True,
        sort_order=tag_data.sort_order or 0
    )
    db.add(new_tag)
    db.commit()
    db.refresh(new_tag)
    
    # Invalidate cache (fire and forget)
    try:
        import asyncio
        from app.services.cache_service import invalidate_cache_async
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.create_task(invalidate_cache_async(
                    key=tag_key(new_tag.id),
                    pattern="tags:list:*"
                ))
            else:
                loop.run_until_complete(invalidate_cache_async(
                    key=tag_key(new_tag.id),
                    pattern="tags:list:*"
                ))
        except RuntimeError:
            asyncio.run(invalidate_cache_async(
                key=tag_key(new_tag.id),
                pattern="tags:list:*"
            ))
    except Exception as e:
        logger.warning(f"Failed to invalidate cache after tag creation: {str(e)}")
    
    return new_tag


def update_tag(db: Session, tag_id: int, tag_data: TagUpdate) -> Tag:
    """Update an existing tag by ID."""
    db_tag = db.query(Tag).filter(
        Tag.id == tag_id
    ).first()

    if not db_tag:
        raise ValueError(f"Tag with ID {tag_id} not found")

    # Check if name is being updated and if it conflicts with existing tag
    if tag_data.name and tag_data.name != db_tag.name:
        existing_tag = db.query(Tag).filter(
            Tag.name == tag_data.name
        ).first()

        if existing_tag:
            raise ValueError(f"Tag with name '{tag_data.name}' already exists")

    # Update fields
    if tag_data.name is not None:
        db_tag.name = tag_data.name
        # Regenerate slug when name changes
        base_slug = generate_slug(tag_data.name)
        db_tag.slug = get_unique_slug(
            db, base_slug, Tag, exclude_id=tag_id)
    if tag_data.description is not None:
        db_tag.description = tag_data.description
    if tag_data.color is not None:
        db_tag.color = tag_data.color
    if tag_data.icon is not None:
        db_tag.icon = tag_data.icon
    if tag_data.is_active is not None:
        db_tag.is_active = tag_data.is_active
    if tag_data.sort_order is not None:
        db_tag.sort_order = tag_data.sort_order

    db.commit()
    db.refresh(db_tag)
    
    # Invalidate cache (fire and forget)
    try:
        import asyncio
        from app.services.cache_service import invalidate_cache_async
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.create_task(invalidate_cache_async(
                    key=tag_key(tag_id),
                    pattern="tags:list:*"
                ))
            else:
                loop.run_until_complete(invalidate_cache_async(
                    key=tag_key(tag_id),
                    pattern="tags:list:*"
                ))
        except RuntimeError:
            asyncio.run(invalidate_cache_async(
                key=tag_key(tag_id),
                pattern="tags:list:*"
            ))
    except Exception as e:
        logger.warning(f"Failed to invalidate cache after tag update: {str(e)}")
    
    return db_tag


def delete_tag(db: Session, tag_id: int) -> None:
    """Soft delete a tag by ID."""
    from datetime import datetime

    db_tag = db.query(Tag).filter(
        Tag.id == tag_id,
        Tag.deleted_at.is_(None)
    ).first()

    if not db_tag:
        raise ValueError(f"Tag with ID {tag_id} not found")

    # Soft delete: set deleted_at timestamp
    db_tag.deleted_at = datetime.utcnow()
    db.commit()
    
    # Invalidate cache (fire and forget)
    try:
        import asyncio
        from app.services.cache_service import invalidate_cache_async
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.create_task(invalidate_cache_async(
                    key=tag_key(tag_id),
                    pattern="tags:list:*"
                ))
            else:
                loop.run_until_complete(invalidate_cache_async(
                    key=tag_key(tag_id),
                    pattern="tags:list:*"
                ))
        except RuntimeError:
            asyncio.run(invalidate_cache_async(
                key=tag_key(tag_id),
                pattern="tags:list:*"
            ))
    except Exception as e:
        logger.warning(f"Failed to invalidate cache after tag deletion: {str(e)}")
