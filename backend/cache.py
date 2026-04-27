"""Cache management for Language Coach using Redis."""

from __future__ import annotations

import functools
import json
import logging
from typing import Any, Optional

import redis

from config import settings

logger = logging.getLogger(__name__)


class CacheManager:
    """Redis cache manager."""

    def __init__(self) -> None:
        try:
            self.redis = redis.from_url(settings.redis_url, decode_responses=True)
            self.enabled = True
        except Exception as err:
            logger.warning("redis_cache_disabled", extra={"error": str(err)})
            self.enabled = False

    def get(self, key: str) -> Optional[Any]:
        if not self.enabled:
            return None
        try:
            value = self.redis.get(key)
            return json.loads(value) if value else None
        except Exception:
            return None

    def set(self, key: str, value: Any, expire: Optional[int] = None) -> bool:
        if not self.enabled:
            return False
        try:
            ttl = expire or settings.cache_expire
            return bool(self.redis.set(key, json.dumps(value, ensure_ascii=False), ex=ttl))
        except Exception:
            return False

    def delete(self, key: str) -> bool:
        if not self.enabled:
            return False
        try:
            return self.redis.delete(key) > 0
        except Exception:
            return False


cache = CacheManager()


def cached(prefix: str, expire: Optional[int] = None):
    """Decorator for caching function results."""

    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            key = f"{prefix}:{func.__name__}:{str(args)}:{str(kwargs)}"
            result = cache.get(key)
            if result is not None:
                return result

            result = func(*args, **kwargs)
            if result is not None:
                cache.set(key, result, expire)
            return result

        return wrapper

    return decorator
