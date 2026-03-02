"""
Redis client module for managing Redis connections.
"""
import logging
from typing import Optional
from redis import asyncio as aioredis
from app.core.config import settings

logger = logging.getLogger(__name__)

# Global Redis client instance
_redis_client: Optional[aioredis.Redis] = None


async def get_redis_client() -> Optional[aioredis.Redis]:
    """
    Get or create Redis client instance.

    Returns:
        Redis client instance or None if Redis is not configured or unavailable
    """
    global _redis_client

    # If Redis URL is not configured, return None
    if not settings.REDIS_URL:
        return None

    # If client already exists and is connected, return it
    if _redis_client is not None:
        try:
            # Check if connection is still alive
            await _redis_client.ping()
            return _redis_client
        except Exception:
            # Connection is dead, reset and recreate
            _redis_client = None

    # Create new Redis client
    try:
        _redis_client = aioredis.from_url(
            settings.REDIS_URL,
            encoding="utf-8",
            decode_responses=True,
            socket_connect_timeout=5,
            socket_timeout=5,
            retry_on_timeout=True,
            health_check_interval=30
        )

        # Test the connection
        await _redis_client.ping()
        logger.info("Redis client connected successfully")
        return _redis_client
    except Exception as e:
        logger.warning(f"Failed to connect to Redis: {str(e)}")
        _redis_client = None
        return None


async def close_redis_client() -> None:
    """
    Close Redis client connection.
    """
    global _redis_client

    if _redis_client is not None:
        try:
            await _redis_client.close()
            logger.info("Redis client closed successfully")
        except Exception as e:
            logger.warning(f"Error closing Redis client: {str(e)}")
        finally:
            _redis_client = None


async def check_redis_health() -> bool:
    """
    Check if Redis connection is healthy.

    Returns:
        True if Redis is connected and responding, False otherwise
    """
    try:
        client = await get_redis_client()
        if client is None:
            return False

        # Try to ping Redis
        await client.ping()
        return True
    except Exception as e:
        logger.debug(f"Redis health check failed: {str(e)}")
        return False
