"""
Product business logic service
"""
from sqlalchemy.orm import Session, joinedload
from typing import Optional, List
from datetime import datetime
from decimal import Decimal
import logging

from app.db.models.product import Product
from app.db.models.product import ProductStatus as DBProductStatus
from app.db.models.product_variant import ProductVariant
from app.db.models.category import Category
from app.db.models.tag import Tag
from app.schemas.models import ProductCreate, Product as ProductSchema, ProductSummary, ProductVariant as ProductVariantSchema
from app.services.utils import generate_slug, get_unique_slug
from app.services.cloudinary_service import (
    process_images,
    process_image,
    delete_image_by_url,
    is_cloudinary_url
)
from app.services.cache_service import (
    delete_from_cache,
    invalidate_pattern,
    product_key,
    products_list_key
)

logger = logging.getLogger(__name__)


def db_product_to_summary(db_product: Product) -> ProductSummary:
    """Convert SQLAlchemy Product model to simplified ProductSummary model."""
    # Get category name from relationship if it exists
    category_name = None
    if hasattr(db_product, 'category') and db_product.category:
        category_name = getattr(db_product.category, 'name', None)
    
    # Calculate stock status based on variants or main product
    has_variants = False
    has_stock = False
    in_stock_variants_count = 0
    
    if hasattr(db_product, 'variants') and db_product.variants:
        # Filter out deleted variants
        active_variants = [v for v in db_product.variants if getattr(v, 'deleted_at', None) is None]
        
        if active_variants:
            has_variants = True
            # Check how many variants are in stock
            in_stock_variants_count = sum(1 for v in active_variants if getattr(v, 'in_stock', False))
            has_stock = in_stock_variants_count > 0
        else:
            # No active variants, use main product stock
            has_stock = getattr(db_product, 'stock_quantity', 0) > 0
    else:
        # No variants, use main product stock
        has_stock = getattr(db_product, 'stock_quantity', 0) > 0
    
    return ProductSummary(
        id=db_product.id,
        name=db_product.name,
        description=getattr(db_product, 'description', None),
        image=getattr(db_product, 'image', None),
        price=db_product.price,
        sku=getattr(db_product, 'sku', None),
        slug=getattr(db_product, 'slug', None),
        category=category_name,
        status=getattr(db_product, 'status', None),
        is_active=getattr(db_product, 'is_active', True),
        is_featured=getattr(db_product, 'is_featured', False),
        stock_quantity=getattr(db_product, 'stock_quantity', 0),
        rating_average=getattr(db_product, 'rating_average', None),
        has_variants=has_variants,
        has_stock=has_stock,
        in_stock_variants_count=in_stock_variants_count,
    )


def db_product_to_pydantic(db_product: Product) -> ProductSchema:
    """Convert SQLAlchemy Product model to full Pydantic Product model."""
    variants = []
    if hasattr(db_product, 'variants') and db_product.variants:
        for variant in db_product.variants:
            if getattr(variant, 'deleted_at', None) is None:
                variants.append(ProductVariantSchema(
                    id=getattr(variant, 'id', None),
                    name=variant.name,
                    sku=getattr(variant, 'sku', None),
                    price=variant.price,
                    originalPrice=getattr(variant, 'original_price', None),
                    costPrice=getattr(variant, 'cost_price', None),
                    compareAtPrice=getattr(variant, 'compare_at_price', None),
                    stockQuantity=getattr(variant, 'stock_quantity', 0),
                    lowStockThreshold=getattr(
                        variant, 'low_stock_threshold', None),
                    weight=getattr(variant, 'weight', None),
                    dimensions=getattr(variant, 'dimensions', None),
                    barcode=getattr(variant, 'barcode', None),
                    specifications=getattr(
                        variant, 'specifications', None) or {},
                    images=getattr(variant, 'images', None) or [],
                    inStock=getattr(variant, 'in_stock', True),
                    created_at=getattr(variant, 'created_at', None),
                    updated_at=getattr(variant, 'updated_at', None)
                ))

    category_obj = None
    if db_product.category:
        category_obj = {
            "id": db_product.category.id,
            "name": db_product.category.name,
            "slug": db_product.category.slug,
            "description": db_product.category.description
        }

    tags_list = []
    if hasattr(db_product, 'tags') and db_product.tags:
        for tag in db_product.tags:
            if getattr(tag, 'deleted_at', None) is None:
                tags_list.append({
                    "id": tag.id,
                    "name": tag.name,
                    "slug": tag.slug,
                    "description": tag.description
                })

    return ProductSchema(
        id=db_product.id,
        name=db_product.name,
        description=getattr(db_product, 'description', None),
        brand=getattr(db_product, 'brand', None),
        image=getattr(db_product, 'image', None),
        images=getattr(db_product, 'images', None) or [],
        category_id=getattr(db_product, 'category_id', None),
        category=category_obj,
        tags=tags_list,
        sku=getattr(db_product, 'sku', None),
        slug=getattr(db_product, 'slug', None),
        stock_quantity=getattr(db_product, 'stock_quantity', 0),
        low_stock_threshold=getattr(db_product, 'low_stock_threshold', None),
        track_inventory=getattr(db_product, 'track_inventory', True),
        status=getattr(db_product, 'status', DBProductStatus.DRAFT),
        is_active=getattr(db_product, 'is_active', True),
        is_featured=getattr(db_product, 'is_featured', False),
        is_bestseller=getattr(db_product, 'is_bestseller', False),
        published_at=getattr(db_product, 'published_at', None),
        price=db_product.price,
        compare_at_price=getattr(db_product, 'compare_at_price', None),
        cost_price=getattr(db_product, 'cost_price', None),
        tax_class=getattr(db_product, 'tax_class', None),
        currency=getattr(db_product, 'currency', 'USD'),
        meta_title=getattr(db_product, 'meta_title', None),
        meta_description=getattr(db_product, 'meta_description', None),
        meta_keywords=getattr(db_product, 'meta_keywords', None),
        weight=getattr(db_product, 'weight', None),
        dimensions=getattr(db_product, 'dimensions', None),
        shipping_class=getattr(db_product, 'shipping_class', None),
        view_count=getattr(db_product, 'view_count', 0),
        purchase_count=getattr(db_product, 'purchase_count', 0),
        rating_average=getattr(db_product, 'rating_average', Decimal('0.00')),
        rating_count=getattr(db_product, 'rating_count', 0),
        sort_order=getattr(db_product, 'sort_order', 0),
        variants=variants,
        specifications=getattr(db_product, 'specifications', None) or {},
        created_at=getattr(db_product, 'created_at', None),
        updated_at=getattr(db_product, 'updated_at', None),
        created_by=getattr(db_product, 'created_by', None),
        updated_by=getattr(db_product, 'updated_by', None),
        deleted_at=getattr(db_product, 'deleted_at', None),
        version=getattr(db_product, 'version', 1)
    )


def get_product_by_id(db: Session, product_id: int) -> Optional[Product]:
    """Get a product by ID with all relationships loaded."""
    return db.query(Product).options(
        joinedload(Product.variants),
        joinedload(Product.category),
        joinedload(Product.tags)
    ).filter(
        Product.id == product_id,
        Product.deleted_at.is_(None)
    ).first()


def process_product_images(images: Optional[List[str]], product_id: Optional[int] = None) -> List[str]:
    """
    Process product images: upload non-Cloudinary URLs to Cloudinary.
    
    Args:
        images: List of image URLs
        product_id: Optional product ID for folder organization
    
    Returns:
        List of Cloudinary URLs
    """
    if not images:
        return []
    
    folder = f"products/{product_id}" if product_id else "products"
    return process_images(images, folder=folder)


def process_variant_images(images: Optional[List[str]], product_id: Optional[int] = None, variant_id: Optional[int] = None) -> List[str]:
    """
    Process variant images: upload non-Cloudinary URLs to Cloudinary.
    
    Args:
        images: List of image URLs
        product_id: Product ID for folder organization
        variant_id: Optional variant ID for folder organization
    
    Returns:
        List of Cloudinary URLs
    """
    if not images:
        return []
    
    if product_id and variant_id:
        folder = f"products/{product_id}/variants/{variant_id}"
    elif product_id:
        folder = f"products/{product_id}/variants"
    else:
        folder = "products/variants"
    
    return process_images(images, folder=folder)


def cleanup_old_images(old_images: Optional[List[str]], new_images: Optional[List[str]]) -> None:
    """
    Delete old Cloudinary images that are no longer in the new images list.
    
    Args:
        old_images: List of old image URLs
        new_images: List of new image URLs
    """
    if not old_images:
        return
    
    if not new_images:
        new_images = []
    
    # Convert to sets for comparison
    old_set = set(old_images) if old_images else set()
    new_set = set(new_images) if new_images else set()
    
    # Find images to delete (in old but not in new)
    images_to_delete = old_set - new_set
    
    # Delete only Cloudinary images
    for image_url in images_to_delete:
        if is_cloudinary_url(image_url):
            try:
                delete_image_by_url(image_url)
                logger.info(f"Deleted old Cloudinary image: {image_url}")
            except Exception as e:
                logger.error(f"Failed to delete old Cloudinary image {image_url}: {str(e)}")


def cleanup_product_images(product: Product) -> None:
    """
    Clean up all Cloudinary images associated with a product.
    
    Args:
        product: Product model instance
    """
    images_to_delete = []
    
    # Collect product images
    if product.image and is_cloudinary_url(product.image):
        images_to_delete.append(product.image)
    
    if product.images:
        for img in product.images:
            if isinstance(img, str) and is_cloudinary_url(img):
                images_to_delete.append(img)
    
    # Collect variant images
    if hasattr(product, 'variants') and product.variants:
        for variant in product.variants:
            if variant.images:
                for img in variant.images:
                    if isinstance(img, str) and is_cloudinary_url(img):
                        images_to_delete.append(img)
    
    # Delete all collected images
    for image_url in images_to_delete:
        try:
            delete_image_by_url(image_url)
            logger.info(f"Deleted Cloudinary image: {image_url}")
        except Exception as e:
            logger.error(f"Failed to delete Cloudinary image {image_url}: {str(e)}")


def create_product(db: Session, product_data: ProductCreate) -> Product:
    """Create a new product with variants, category, and tags."""
    # Validate category_id if provided
    if product_data.category_id is not None:
        category = db.query(Category).filter(
            Category.id == product_data.category_id
        ).first()
        if not category:
            raise ValueError(
                f"Category with ID {product_data.category_id} not found")

    # Validate tag IDs if provided
    if product_data.tags:
        tag_ids = set(product_data.tags)
        existing_tags = db.query(Tag).filter(
            Tag.id.in_(tag_ids)
        ).all()
        existing_tag_ids = {tag.id for tag in existing_tags}
        missing_tag_ids = tag_ids - existing_tag_ids
        if missing_tag_ids:
            raise ValueError(
                f"Tags with IDs {list(missing_tag_ids)} not found")

    # Generate slug if not provided
    slug = product_data.slug
    if not slug:
        base_slug = generate_slug(product_data.name)
        slug = get_unique_slug(db, base_slug, Product)

    # Check SKU uniqueness if provided
    if product_data.sku:
        existing_sku = db.query(Product).filter(
            Product.sku == product_data.sku
        ).first()
        if existing_sku:
            raise ValueError(
                f"Product with SKU '{product_data.sku}' already exists")

    # Convert status enum to database enum
    product_status = product_data.status
    if isinstance(product_status, str):
        product_status = DBProductStatus(product_status)
    elif hasattr(product_status, 'value'):
        product_status = DBProductStatus(product_status.value)

    # Process images: upload non-Cloudinary URLs or base64 data URLs to Cloudinary
    processed_image = None
    if product_data.image:
        from app.services.cloudinary_service import is_base64_data_url
        try:
            # Process image (handles base64, URLs, Cloudinary URLs)
            processed_image = process_image(product_data.image, folder="products")
            # If processing returned None and it's not a base64 image, use original
            if not processed_image and not is_base64_data_url(product_data.image):
                processed_image = product_data.image
        except ValueError as e:
            # Re-raise ValueError (contains proper error message about Cloudinary config)
            raise
        except Exception as e:
            # For unexpected errors, log and raise
            logger.error(f"Unexpected error processing product image: {str(e)}")
            if is_base64_data_url(product_data.image):
                raise ValueError(f"Failed to process base64 image: {str(e)}")
            # For regular URLs, fallback to original on unexpected errors
            processed_image = product_data.image
    
    processed_images_list = []
    if product_data.images:
        processed_images_list = process_product_images(product_data.images)

    # Create the product
    new_product = Product(
        name=product_data.name,
        description=product_data.description,
        brand=product_data.brand,
        image=processed_image,
        images=processed_images_list,
        category_id=product_data.category_id,
        price=product_data.price,
        sku=product_data.sku,
        slug=slug,
        stock_quantity=product_data.stock_quantity or 0,
        low_stock_threshold=product_data.low_stock_threshold,
        track_inventory=product_data.track_inventory if product_data.track_inventory is not None else True,
        status=product_status,
        is_active=product_data.is_active if product_data.is_active is not None else True,
        is_featured=product_data.is_featured if product_data.is_featured is not None else False,
        is_bestseller=product_data.is_bestseller if product_data.is_bestseller is not None else False,
        published_at=product_data.published_at,
        compare_at_price=product_data.compare_at_price,
        cost_price=product_data.cost_price,
        tax_class=product_data.tax_class,
        currency=product_data.currency or 'USD',
        meta_title=product_data.meta_title,
        meta_description=product_data.meta_description,
        meta_keywords=product_data.meta_keywords,
        weight=product_data.weight,
        dimensions=product_data.dimensions,
        shipping_class=product_data.shipping_class,
        sort_order=product_data.sort_order or 0,
        specifications=product_data.specifications
    )
    db.add(new_product)
    db.flush()

    # Add tags (many-to-many relationship)
    if product_data.tags:
        tags = db.query(Tag).filter(
            Tag.id.in_(product_data.tags),
            Tag.deleted_at.is_(None)
        ).all()
        new_product.tags = tags

    # Create variants
    for variant_data in product_data.variants or []:
        # Handle both dict and Pydantic model
        if hasattr(variant_data, 'model_dump'):
            # Pydantic model - convert to dict
            variant_dict = variant_data.model_dump()
        elif hasattr(variant_data, 'dict'):
            # Pydantic v1 model
            variant_dict = variant_data.dict()
        elif isinstance(variant_data, dict):
            # Already a dict
            variant_dict = variant_data
        else:
            # Try to access as attributes
            variant_dict = {
                'name': getattr(variant_data, 'name', None),
                'sku': getattr(variant_data, 'sku', None),
                'price': getattr(variant_data, 'price', None),
                'originalPrice': getattr(variant_data, 'originalPrice', None),
                'costPrice': getattr(variant_data, 'costPrice', None),
                'compareAtPrice': getattr(variant_data, 'compareAtPrice', None),
                'stockQuantity': getattr(variant_data, 'stockQuantity', 0),
                'lowStockThreshold': getattr(variant_data, 'lowStockThreshold', None),
                'weight': getattr(variant_data, 'weight', None),
                'dimensions': getattr(variant_data, 'dimensions', None),
                'barcode': getattr(variant_data, 'barcode', None),
                'specifications': getattr(variant_data, 'specifications', {}),
                'images': getattr(variant_data, 'images', []),
                'inStock': getattr(variant_data, 'inStock', True)
            }
        
        # Process variant images
        variant_images = variant_dict.get('images', [])
        processed_variant_images = []
        if variant_images:
            processed_variant_images = process_variant_images(
                variant_images,
                product_id=new_product.id
            )
        
        variant_db = ProductVariant(
            product_id=new_product.id,
            name=variant_dict.get('name'),
            sku=variant_dict.get('sku'),
            price=variant_dict.get('price'),
            original_price=variant_dict.get('originalPrice'),
            cost_price=variant_dict.get('costPrice'),
            compare_at_price=variant_dict.get('compareAtPrice'),
            stock_quantity=variant_dict.get('stockQuantity', 0),
            low_stock_threshold=variant_dict.get('lowStockThreshold'),
            weight=variant_dict.get('weight'),
            dimensions=variant_dict.get('dimensions'),
            barcode=variant_dict.get('barcode'),
            specifications=variant_dict.get('specifications', {}),
            images=processed_variant_images,
            in_stock=variant_dict.get('inStock', True)
        )
        db.add(variant_db)

    db.commit()
    db.refresh(new_product)
    
    # Invalidate cache (fire and forget)
    try:
        import asyncio
        from app.services.cache_service import invalidate_cache_async
        # Try to get running event loop, if not available, create new one
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # If loop is running, schedule as background task
                asyncio.create_task(invalidate_cache_async(
                    key=product_key(new_product.id),
                    pattern="products:list:*"
                ))
            else:
                # If loop exists but not running, run the coroutine
                loop.run_until_complete(invalidate_cache_async(
                    key=product_key(new_product.id),
                    pattern="products:list:*"
                ))
        except RuntimeError:
            # No event loop, create new one
            asyncio.run(invalidate_cache_async(
                key=product_key(new_product.id),
                pattern="products:list:*"
            ))
    except Exception as e:
        logger.warning(f"Failed to invalidate cache after product creation: {str(e)}")
    
    return new_product


def update_product(db: Session, product_id: int, product_data: ProductCreate) -> Product:
    """Update an existing product by ID."""
    db_product = db.query(Product).options(
        joinedload(Product.variants),
        joinedload(Product.category),
        joinedload(Product.tags)
    ).filter(
        Product.id == product_id,
        Product.deleted_at.is_(None)
    ).first()

    if not db_product:
        raise ValueError(f"Product with ID {product_id} not found")

    # Validate category_id if provided
    if product_data.category_id is not None:
        category = db.query(Category).filter(
            Category.id == product_data.category_id
        ).first()
        if not category:
            raise ValueError(
                f"Category with ID {product_data.category_id} not found")

    # Validate tag IDs if provided
    if product_data.tags:
        tag_ids = set(product_data.tags)
        existing_tags = db.query(Tag).filter(
            Tag.id.in_(tag_ids),
            Tag.deleted_at.is_(None)
        ).all()
        existing_tag_ids = {tag.id for tag in existing_tags}
        missing_tag_ids = tag_ids - existing_tag_ids
        if missing_tag_ids:
            raise ValueError(
                f"Tags with IDs {list(missing_tag_ids)} not found")

    # Generate/update slug if name changed
    if product_data.name and product_data.name != db_product.name:
        base_slug = generate_slug(product_data.name)
        db_product.slug = get_unique_slug(
            db, base_slug, Product, exclude_id=product_id)
    elif product_data.slug and product_data.slug != db_product.slug:
        existing = db.query(Product).filter(
            Product.slug == product_data.slug,
            Product.id != product_id
        ).first()
        if existing:
            raise ValueError(
                f"Product with slug '{product_data.slug}' already exists")
        db_product.slug = product_data.slug

    # Check SKU uniqueness if being updated
    if product_data.sku and product_data.sku != db_product.sku:
        existing_sku = db.query(Product).filter(
            Product.sku == product_data.sku,
            Product.id != product_id
        ).first()
        if existing_sku:
            raise ValueError(
                f"Product with SKU '{product_data.sku}' already exists")

    # Convert status enum to database enum
    if product_data.status:
        product_status = product_data.status
        if isinstance(product_status, str):
            product_status = DBProductStatus(product_status)
        elif hasattr(product_status, 'value'):
            product_status = DBProductStatus(product_status.value)
    else:
        product_status = db_product.status

    # Store old images for cleanup
    old_image = db_product.image
    old_images = db_product.images or []
    old_variant_images = {}
    # Get existing variants before they're modified (variants are already loaded via joinedload)
    existing_variants_for_cleanup = db_product.variants or []
    for variant in existing_variants_for_cleanup:
        if variant.images:
            old_variant_images[variant.id] = variant.images

    # Update product fields
    if product_data.name is not None:
        db_product.name = product_data.name
    if product_data.description is not None:
        db_product.description = product_data.description
    if product_data.brand is not None:
        db_product.brand = product_data.brand
    
    # Process and update product images
    if product_data.image is not None:
        if product_data.image != old_image:
            # Clean up old image if it's a Cloudinary URL
            if old_image and is_cloudinary_url(old_image):
                try:
                    delete_image_by_url(old_image)
                except Exception as e:
                    logger.error(f"Failed to delete old product image: {str(e)}")
            
            # Process new image (handles URLs, base64 data URLs, etc.)
            from app.services.cloudinary_service import is_base64_data_url
            try:
                processed_image = process_image(product_data.image, folder=f"products/{product_id}")
                # If processing returned None and it's not a base64 image, use original
                if not processed_image and not is_base64_data_url(product_data.image):
                    processed_image = product_data.image
                db_product.image = processed_image
            except ValueError as e:
                # Re-raise ValueError (contains proper error message)
                raise
            except Exception as e:
                # For unexpected errors, log and handle
                logger.error(f"Unexpected error processing product image: {str(e)}")
                if is_base64_data_url(product_data.image):
                    raise ValueError(f"Failed to process base64 image: {str(e)}")
                # For regular URLs, fallback to original on unexpected errors
                db_product.image = product_data.image
        else:
            db_product.image = product_data.image
    
    if product_data.images is not None:
        # Clean up old images that are no longer in the new list
        cleanup_old_images(old_images, product_data.images)
        
        # Process new images
        processed_images_list = process_product_images(product_data.images, product_id=product_id)
        db_product.images = processed_images_list
    if product_data.category_id is not None:
        db_product.category_id = product_data.category_id
    # Allow price to be set to None explicitly (for products without prices)
    if hasattr(product_data, 'price'):
        db_product.price = product_data.price
    if product_data.sku is not None:
        db_product.sku = product_data.sku
    if product_data.stock_quantity is not None:
        db_product.stock_quantity = product_data.stock_quantity
    if product_data.low_stock_threshold is not None:
        db_product.low_stock_threshold = product_data.low_stock_threshold
    if product_data.track_inventory is not None:
        db_product.track_inventory = product_data.track_inventory
    if product_data.status is not None:
        db_product.status = product_status
    if product_data.is_active is not None:
        db_product.is_active = product_data.is_active
    if product_data.is_featured is not None:
        db_product.is_featured = product_data.is_featured
    if product_data.is_bestseller is not None:
        db_product.is_bestseller = product_data.is_bestseller
    if product_data.published_at is not None:
        db_product.published_at = product_data.published_at
    if product_data.compare_at_price is not None:
        db_product.compare_at_price = product_data.compare_at_price
    if product_data.cost_price is not None:
        db_product.cost_price = product_data.cost_price
    if product_data.tax_class is not None:
        db_product.tax_class = product_data.tax_class
    if product_data.currency is not None:
        db_product.currency = product_data.currency
    if product_data.meta_title is not None:
        db_product.meta_title = product_data.meta_title
    if product_data.meta_description is not None:
        db_product.meta_description = product_data.meta_description
    if product_data.meta_keywords is not None:
        db_product.meta_keywords = product_data.meta_keywords
    if product_data.weight is not None:
        db_product.weight = product_data.weight
    if product_data.dimensions is not None:
        db_product.dimensions = product_data.dimensions
    if product_data.shipping_class is not None:
        db_product.shipping_class = product_data.shipping_class
    if product_data.sort_order is not None:
        db_product.sort_order = product_data.sort_order
    if product_data.specifications is not None:
        db_product.specifications = product_data.specifications

    # Update tags (many-to-many relationship)
    if product_data.tags is not None:
        tags = db.query(Tag).filter(
            Tag.id.in_(product_data.tags),
            Tag.deleted_at.is_(None)
        ).all()
        db_product.tags = tags

    # Soft delete existing variants
    variants_data = product_data.variants or []
    existing_variants = db.query(ProductVariant).filter(
        ProductVariant.product_id == product_id,
        ProductVariant.deleted_at.is_(None)
    ).all()

    for variant in existing_variants:
        variant.deleted_at = datetime.utcnow()

    # Create new variants
    for variant_data in variants_data:
        # Handle both dict and Pydantic model
        if hasattr(variant_data, 'model_dump'):
            # Pydantic v2 model - convert to dict
            variant_dict = variant_data.model_dump()
        elif hasattr(variant_data, 'dict'):
            # Pydantic v1 model
            variant_dict = variant_data.dict()
        elif isinstance(variant_data, dict):
            # Already a dict
            variant_dict = variant_data
        else:
            # Try to access as attributes
            variant_dict = {
                'name': getattr(variant_data, 'name', None),
                'sku': getattr(variant_data, 'sku', None),
                'price': getattr(variant_data, 'price', None),
                'originalPrice': getattr(variant_data, 'originalPrice', None),
                'costPrice': getattr(variant_data, 'costPrice', None),
                'compareAtPrice': getattr(variant_data, 'compareAtPrice', None),
                'stockQuantity': getattr(variant_data, 'stockQuantity', 0),
                'lowStockThreshold': getattr(variant_data, 'lowStockThreshold', None),
                'weight': getattr(variant_data, 'weight', None),
                'dimensions': getattr(variant_data, 'dimensions', None),
                'barcode': getattr(variant_data, 'barcode', None),
                'specifications': getattr(variant_data, 'specifications', {}),
                'images': getattr(variant_data, 'images', []),
                'inStock': getattr(variant_data, 'inStock', True)
            }
        
        # Process variant images
        variant_images = variant_dict.get('images', [])
        processed_variant_images = []
        if variant_images:
            processed_variant_images = process_variant_images(
                variant_images,
                product_id=product_id
            )
        
        variant_db = ProductVariant(
            product_id=product_id,
            name=variant_dict.get('name'),
            sku=variant_dict.get('sku'),
            price=variant_dict.get('price'),
            original_price=variant_dict.get('originalPrice'),
            cost_price=variant_dict.get('costPrice'),
            compare_at_price=variant_dict.get('compareAtPrice'),
            stock_quantity=variant_dict.get('stockQuantity', 0),
            low_stock_threshold=variant_dict.get('lowStockThreshold'),
            weight=variant_dict.get('weight'),
            dimensions=variant_dict.get('dimensions'),
            barcode=variant_dict.get('barcode'),
            specifications=variant_dict.get('specifications', {}),
            images=processed_variant_images,
            in_stock=variant_dict.get('inStock', True)
        )
        db.add(variant_db)
    
    # Clean up old variant images that were soft deleted
    for variant_id, images in old_variant_images.items():
        cleanup_old_images(images, [])

    db.commit()
    db.refresh(db_product)
    
    # Invalidate cache (fire and forget)
    try:
        import asyncio
        from app.services.cache_service import invalidate_cache_async
        # Try to get running event loop, if not available, create new one
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # If loop is running, schedule as background task
                asyncio.create_task(invalidate_cache_async(
                    key=product_key(product_id),
                    pattern="products:list:*"
                ))
            else:
                # If loop exists but not running, run the coroutine
                loop.run_until_complete(invalidate_cache_async(
                    key=product_key(product_id),
                    pattern="products:list:*"
                ))
        except RuntimeError:
            # No event loop, create new one
            asyncio.run(invalidate_cache_async(
                key=product_key(product_id),
                pattern="products:list:*"
            ))
    except Exception as e:
        logger.warning(f"Failed to invalidate cache after product update: {str(e)}")
    
    return db_product


def delete_product(db: Session, product_id: int) -> None:
    """Soft delete a product by ID and clean up Cloudinary images."""
    db_product = db.query(Product).options(
        joinedload(Product.variants)
    ).filter(
        Product.id == product_id,
        Product.deleted_at.is_(None)
    ).first()

    if not db_product:
        raise ValueError(f"Product with ID {product_id} not found")

    # Clean up Cloudinary images before soft deleting
    try:
        cleanup_product_images(db_product)
    except Exception as e:
        logger.error(f"Error cleaning up images for product {product_id}: {str(e)}")
        # Continue with deletion even if image cleanup fails

    # Soft delete: set deleted_at timestamp
    db_product.deleted_at = datetime.utcnow()

    # Also soft delete all variants
    for variant in db_product.variants:
        if variant.deleted_at is None:
            variant.deleted_at = datetime.utcnow()

    db.commit()
    
    # Invalidate cache (fire and forget)
    try:
        import asyncio
        from app.services.cache_service import invalidate_cache_async
        # Try to get running event loop, if not available, create new one
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # If loop is running, schedule as background task
                asyncio.create_task(invalidate_cache_async(
                    key=product_key(product_id),
                    pattern="products:list:*"
                ))
            else:
                # If loop exists but not running, run the coroutine
                loop.run_until_complete(invalidate_cache_async(
                    key=product_key(product_id),
                    pattern="products:list:*"
                ))
        except RuntimeError:
            # No event loop, create new one
            asyncio.run(invalidate_cache_async(
                key=product_key(product_id),
                pattern="products:list:*"
            ))
    except Exception as e:
        logger.warning(f"Failed to invalidate cache after product deletion: {str(e)}")
