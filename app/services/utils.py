"""
Utility functions for services
"""
import re
from sqlalchemy.orm import Session
from typing import TypeVar, Type

T = TypeVar('T')


def generate_slug(text: str) -> str:
    """
    Generate a URL-friendly slug from text.
    Converts to lowercase, replaces spaces with hyphens, removes special characters.
    """
    slug = text.lower()
    slug = re.sub(r'[\s_]+', '-', slug)
    slug = re.sub(r'[^a-z0-9\-]', '', slug)
    slug = re.sub(r'-+', '-', slug)
    slug = slug.strip('-')
    return slug


def get_unique_slug(db: Session, base_slug: str, model_class: Type[T], exclude_id: int = None) -> str:
    """
    Generate a unique slug by appending a number if the base slug already exists.
    """
    slug = base_slug
    counter = 1

    while True:
        query = db.query(model_class).filter(model_class.slug == slug)
        if exclude_id:
            query = query.filter(model_class.id != exclude_id)

        existing = query.first()
        if not existing:
            return slug

        slug = f"{base_slug}-{counter}"
        counter += 1
