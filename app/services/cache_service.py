"""
Cache service for Redis caching operations.
"""
import json
import logging
from typing import Optional, Any
from app.lib.redis_client import get_redis_client

logger = logging.getLogger(__name__)

# Default TTL values in seconds
DEFAULT_TTL_LIST = 300  # 5 minutes for list endpoints
DEFAULT_TTL_ITEM = 600  # 10 minutes for single item endpoints
DEFAULT_TTL_DASHBOARD = 120  # 2 minutes for dashboard stats


def generate_cache_key(prefix: str, *args, **kwargs) -> str:
    """
    Generate a cache key from prefix and parameters.
    
    Args:
        prefix: Cache key prefix (e.g., 'product', 'products:list')
        *args: Positional arguments to include in key
        **kwargs: Keyword arguments to include in key
    
    Returns:
        Formatted cache key string
    """
    key_parts = [prefix]
    
    # Add positional arguments
    for arg in args:
        if arg is not None:
            key_parts.append(str(arg))
    
    # Add keyword arguments (sorted for consistency)
    if kwargs:
        sorted_kwargs = sorted(kwargs.items())
        for k, v in sorted_kwargs:
            if v is not None:
                key_parts.append(f"{k}:{v}")
    
    return ":".join(key_parts)


async def get_from_cache(key: str) -> Optional[Any]:
    """
    Get value from cache by key.
    
    Args:
        key: Cache key
    
    Returns:
        Cached value or None if not found or error
    """
    try:
        client = await get_redis_client()
        if client is None:
            return None
        
        try:
            value = await client.get(key)
            if value is None:
                return None
            
            # Try to parse as JSON, fallback to string
            try:
                return json.loads(value)
            except (json.JSONDecodeError, TypeError):
                return value
        except (ConnectionError, OSError, AttributeError) as conn_error:
            # Connection issues - log and return None
            logger.warning(f"Redis connection error getting cache (key: {key}): {str(conn_error)}")
            return None
    except Exception as e:
        logger.error(f"Error getting from cache (key: {key}): {str(e)}", exc_info=True)
        return None


async def set_to_cache(key: str, value: Any, ttl: int = DEFAULT_TTL_ITEM) -> bool:
    """
    Set value in cache with TTL.
    
    Args:
        key: Cache key
        value: Value to cache
        ttl: Time to live in seconds
    
    Returns:
        True if successful, False otherwise
    """
    try:
        client = await get_redis_client()
        if client is None:
            return False
        
        # Serialize value to JSON if it's not a string
        if isinstance(value, str):
            serialized_value = value
        else:
            try:
                # Check if it's a Pydantic model - use model_dump() for better compatibility
                if hasattr(value, 'model_dump'):
                    # For Pydantic v2 - use model_dump with mode='json' for proper serialization
                    try:
                        dumped = value.model_dump(mode='json')
                        serialized_value = json.dumps(dumped, default=str)
                    except Exception:
                        # Fallback to regular model_dump
                        serialized_value = json.dumps(value.model_dump(), default=str)
                elif hasattr(value, 'model_dump_json'):
                    # Alternative: use model_dump_json if available
                    serialized_value = value.model_dump_json()
                elif hasattr(value, 'dict'):
                    # For Pydantic v1
                    serialized_value = json.dumps(value.dict(), default=str)
                else:
                    # Fallback to standard JSON serialization
                    serialized_value = json.dumps(value, default=str)
            except (TypeError, ValueError) as e:
                logger.error(f"Error serializing value for cache (key: {key}): {str(e)}")
                return False
        
        try:
            await client.setex(key, ttl, serialized_value)
            return True
        except (ConnectionError, OSError, AttributeError) as conn_error:
            # Connection issues - log and return False
            logger.warning(f"Redis connection error setting cache (key: {key}): {str(conn_error)}")
            return False
    except Exception as e:
        logger.error(f"Error setting cache (key: {key}): {str(e)}", exc_info=True)
        return False


async def delete_from_cache(key: str) -> bool:
    """
    Delete a specific key from cache.
    
    Args:
        key: Cache key to delete
    
    Returns:
        True if successful, False otherwise
    """
    try:
        client = await get_redis_client()
        if client is None:
            return False
        
        await client.delete(key)
        return True
    except Exception as e:
        logger.error(f"Error deleting from cache (key: {key}): {str(e)}")
        return False


async def invalidate_pattern(pattern: str) -> int:
    """
    Invalidate all keys matching a pattern.
    
    Args:
        pattern: Redis key pattern (e.g., 'products:list:*')
    
    Returns:
        Number of keys deleted
    """
    try:
        client = await get_redis_client()
        if client is None:
            return 0
        
        # Use SCAN to find matching keys (more efficient than KEYS)
        deleted_count = 0
        async for key in client.scan_iter(match=pattern):
            await client.delete(key)
            deleted_count += 1
        
        logger.info(f"Invalidated {deleted_count} cache keys matching pattern: {pattern}")
        return deleted_count
    except Exception as e:
        logger.error(f"Error invalidating cache pattern (pattern: {pattern}): {str(e)}")
        return 0


async def get_or_cache(
    key: str,
    fetch_func,
    ttl: int = DEFAULT_TTL_ITEM,
    *args,
    **kwargs
) -> Any:
    """
    Get value from cache or fetch using provided function and cache the result.
    
    Args:
        key: Cache key
        fetch_func: Async function to fetch data if cache miss
        ttl: Time to live in seconds
        *args: Arguments to pass to fetch_func
        **kwargs: Keyword arguments to pass to fetch_func
    
    Returns:
        Cached or fetched value
    """
    # Try to get from cache first
    cached_value = await get_from_cache(key)
    if cached_value is not None:
        return cached_value
    
    # Cache miss - fetch from source
    try:
        if hasattr(fetch_func, '__call__'):
            # Check if it's an async function
            import inspect
            if inspect.iscoroutinefunction(fetch_func):
                value = await fetch_func(*args, **kwargs)
            else:
                value = fetch_func(*args, **kwargs)
        else:
            value = fetch_func
        
        # Cache the result (non-blocking, don't fail if caching fails)
        await set_to_cache(key, value, ttl)
        
        return value
    except Exception as e:
        logger.error(f"Error in get_or_cache for key {key}: {str(e)}")
        raise


# Cache key generators for different resources
def product_key(product_id: int) -> str:
    """Generate cache key for a single product."""
    return f"product:{product_id}"


def products_list_key(category: Optional[str] = None, search: Optional[str] = None, 
                     page: int = 1, size: int = 50) -> str:
    """Generate cache key for products list."""
    return generate_cache_key("products:list", category, search, page, size)


def category_key(category_id: int) -> str:
    """Generate cache key for a single category."""
    return f"category:{category_id}"


def categories_list_key(page: int = 1, size: int = 50) -> str:
    """Generate cache key for categories list."""
    return generate_cache_key("categories:list", page, size)


def tag_key(tag_id: int) -> str:
    """Generate cache key for a single tag."""
    return f"tag:{tag_id}"


def tags_list_key(page: int = 1, size: int = 50) -> str:
    """Generate cache key for tags list."""
    return generate_cache_key("tags:list", page, size)


def dashboard_stats_key(start_date: Optional[str] = None, 
                       end_date: Optional[str] = None,
                       group_by: str = "day") -> str:
    """Generate cache key for dashboard stats."""
    return generate_cache_key("dashboard:stats", start_date, end_date, group_by)


async def invalidate_cache_async(key: Optional[str] = None, pattern: Optional[str] = None):
    """
    Async helper to invalidate cache from synchronous code.
    Can be called with either a specific key or a pattern.
    """
    if key:
        await delete_from_cache(key)
    if pattern:
        await invalidate_pattern(pattern)

