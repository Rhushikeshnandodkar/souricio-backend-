"""
Category business logic service
"""
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime

from app.db.models.category import Category
from app.schemas.models import CategoryCreate, CategoryUpdate, Category as CategorySchema
from app.services.utils import generate_slug, get_unique_slug
from app.services.cache_service import (
    delete_from_cache,
    invalidate_pattern,
    category_key,
    categories_list_key
)
import logging

logger = logging.getLogger(__name__)


def get_category_by_id(db: Session, category_id: int) -> Optional[Category]:
    """Get a category by ID."""
    return db.query(Category).filter(
        Category.id == category_id,
        Category.deleted_at.is_(None)
    ).first()


def create_category(db: Session, category_data: CategoryCreate) -> Category:
    """Create a new category."""
    # Check if category with same name already exists
    existing_category = db.query(Category).filter(
        Category.name == category_data.name
    ).first()

    if existing_category:
        raise ValueError(
            f"Category with name '{category_data.name}' already exists")

    # Generate unique slug from name
    base_slug = generate_slug(category_data.name)
    unique_slug = get_unique_slug(db, base_slug, Category)

    # Calculate level and path if parent_id is provided
    level = 0
    path = category_data.name
    if category_data.parent_id:
        parent = db.query(Category).filter(
            Category.id == category_data.parent_id
        ).first()
        if not parent:
            raise ValueError(
                f"Parent category with ID {category_data.parent_id} not found")
        level = getattr(parent, 'level', 0) + 1
        parent_path = getattr(parent, 'path', parent.name)
        path = f"{parent_path} > {category_data.name}"

    new_category = Category(
        name=category_data.name,
        slug=unique_slug,
        description=category_data.description,
        parent_id=category_data.parent_id,
        level=level,
        path=path,
        image=category_data.image,
        icon=category_data.icon,
        sort_order=category_data.sort_order or 0,
        is_active=category_data.is_active if category_data.is_active is not None else True,
        meta_title=category_data.meta_title,
        meta_description=category_data.meta_description
    )
    db.add(new_category)
    db.commit()
    db.refresh(new_category)
    
    # Invalidate cache (fire and forget)
    try:
        import asyncio
        from app.services.cache_service import invalidate_cache_async
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.create_task(invalidate_cache_async(
                    key=category_key(new_category.id),
                    pattern="categories:list:*"
                ))
            else:
                loop.run_until_complete(invalidate_cache_async(
                    key=category_key(new_category.id),
                    pattern="categories:list:*"
                ))
        except RuntimeError:
            asyncio.run(invalidate_cache_async(
                key=category_key(new_category.id),
                pattern="categories:list:*"
            ))
    except Exception as e:
        logger.warning(f"Failed to invalidate cache after category creation: {str(e)}")
    
    return new_category


def update_category(db: Session, category_id: int, category_data: CategoryUpdate) -> Category:
    """Update an existing category by ID."""
    db_category = db.query(Category).filter(
        Category.id == category_id
    ).first()

    if not db_category:
        raise ValueError(f"Category with ID {category_id} not found")

    # Check if name is being updated and if it conflicts with existing category
    if category_data.name and category_data.name != db_category.name:
        existing_category = db.query(Category).filter(
            Category.name == category_data.name
        ).first()

        if existing_category:
            raise ValueError(
                f"Category with name '{category_data.name}' already exists")

    # Update fields
    if category_data.name is not None:
        db_category.name = category_data.name
        # Regenerate slug when name changes
        base_slug = generate_slug(category_data.name)
        db_category.slug = get_unique_slug(
            db, base_slug, Category, exclude_id=category_id)
    if category_data.description is not None:
        db_category.description = category_data.description
    if category_data.parent_id is not None:
        if category_data.parent_id == category_id:
            raise ValueError("Category cannot be its own parent")
        parent = db.query(Category).filter(
            Category.id == category_data.parent_id
        ).first()
        if not parent:
            raise ValueError(
                f"Parent category with ID {category_data.parent_id} not found")
        db_category.parent_id = category_data.parent_id
        db_category.level = getattr(parent, 'level', 0) + 1
        parent_path = getattr(parent, 'path', parent.name)
        db_category.path = f"{parent_path} > {db_category.name}"
    if category_data.image is not None:
        db_category.image = category_data.image
    if category_data.icon is not None:
        db_category.icon = category_data.icon
    if category_data.sort_order is not None:
        db_category.sort_order = category_data.sort_order
    if category_data.is_active is not None:
        db_category.is_active = category_data.is_active
    if category_data.meta_title is not None:
        db_category.meta_title = category_data.meta_title
    if category_data.meta_description is not None:
        db_category.meta_description = category_data.meta_description

    db.commit()
    db.refresh(db_category)
    
    # Invalidate cache (fire and forget)
    try:
        import asyncio
        from app.services.cache_service import invalidate_cache_async
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.create_task(invalidate_cache_async(
                    key=category_key(category_id),
                    pattern="categories:list:*"
                ))
            else:
                loop.run_until_complete(invalidate_cache_async(
                    key=category_key(category_id),
                    pattern="categories:list:*"
                ))
        except RuntimeError:
            asyncio.run(invalidate_cache_async(
                key=category_key(category_id),
                pattern="categories:list:*"
            ))
    except Exception as e:
        logger.warning(f"Failed to invalidate cache after category update: {str(e)}")
    
    return db_category


def delete_category(db: Session, category_id: int) -> None:
    """Soft delete a category by ID."""
    db_category = db.query(Category).filter(
        Category.id == category_id,
        Category.deleted_at.is_(None)
    ).first()

    if not db_category:
        raise ValueError(f"Category with ID {category_id} not found")

    # Set category_id to NULL for products using this category
    from app.db.models.product import Product
    db.query(Product).filter(
        Product.category_id == category_id
    ).update({Product.category_id: None})

    # Soft delete: set deleted_at timestamp
    db_category.deleted_at = datetime.utcnow()
    db.commit()
    
    # Invalidate cache (fire and forget)
    try:
        import asyncio
        from app.services.cache_service import invalidate_cache_async
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.create_task(invalidate_cache_async(
                    key=category_key(category_id),
                    pattern="categories:list:*"
                ))
            else:
                loop.run_until_complete(invalidate_cache_async(
                    key=category_key(category_id),
                    pattern="categories:list:*"
                ))
        except RuntimeError:
            asyncio.run(invalidate_cache_async(
                key=category_key(category_id),
                pattern="categories:list:*"
            ))
    except Exception as e:
        logger.warning(f"Failed to invalidate cache after category deletion: {str(e)}")
