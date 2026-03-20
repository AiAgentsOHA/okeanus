"""Redis connection pool -- singleton async client."""

from __future__ import annotations

import logging

import redis.asyncio as redis

from okeanus.config import settings

logger = logging.getLogger(__name__)

_redis_client: redis.Redis | None = None


async def get_redis() -> redis.Redis:
    """Return the singleton Redis client, creating it on first call."""
    global _redis_client
    if _redis_client is None:
        _redis_client = redis.from_url(
            settings.redis_url,
            decode_responses=True,
            max_connections=20,
        )
        # Verify connection
        await _redis_client.ping()
        logger.info("Redis connected: %s", settings.redis_url)
    return _redis_client


async def close_redis() -> None:
    """Close the Redis connection pool."""
    global _redis_client
    if _redis_client is not None:
        await _redis_client.aclose()
        _redis_client = None
        logger.info("Redis connection closed")
