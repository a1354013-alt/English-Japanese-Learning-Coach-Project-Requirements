"""
Cache management for Language Coach using Redis
"""
import json
import functools
from typing import Any, Optional
import redis
from config import settings

class CacheManager:
    """Redis cache manager"""
    
    def __init__(self):
        try:
            self.redis = redis.from_url(settings.redis_url, decode_responses=True)
            self.enabled = True
        except Exception as e:
            print(f"Redis connection failed: {e}. Cache disabled.")
            self.enabled = False
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        if not self.enabled:
            return None
        try:
            value = self.redis.get(key)
            return json.loads(value) if value else None
        except Exception:
            return None
    
    def set(self, key: str, value: Any, expire: int = None) -> bool:
        """Set value in cache"""
        if not self.enabled:
            return False
        try:
            expire = expire or settings.cache_expire
            return self.redis.set(key, json.dumps(value, ensure_ascii=False), ex=expire)
        except Exception:
            return False
    
    def delete(self, key: str) -> bool:
        """Delete key from cache"""
        if not self.enabled:
            return False
        try:
            return self.redis.delete(key) > 0
        except Exception:
            return False

cache = CacheManager()

def cached(prefix: str, expire: int = None):
    """Decorator for caching function results"""
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Create a unique key based on function name and arguments
            key = f"{prefix}:{func.__name__}:{str(args)}:{str(kwargs)}"
            
            # Try to get from cache
            result = cache.get(key)
            if result is not None:
                return result
            
            # If not in cache, call function
            result = func(*args, **kwargs)
            
            # Save to cache
            if result is not None:
                cache.set(key, result, expire)
            
            return result
        return wrapper
    return decorator
