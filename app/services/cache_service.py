"""
Cache Service for Fast Serviceability and Product Lookups.

Supports:
1. Redis (preferred for production)
2. In-memory fallback (for development/testing)

Usage:
    cache = get_cache()
    await cache.set("key", value, ttl=3600)
    value = await cache.get("key")
"""
import json
import hashlib
from typing import Any, Optional, Dict
from datetime import datetime, timedelta, timezone
from abc import ABC, abstractmethod
import asyncio

from app.config import settings


class CacheBackend(ABC):
    """Abstract cache backend interface."""

    @abstractmethod
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        pass

    @abstractmethod
    async def set(self, key: str, value: Any, ttl: int = 3600) -> bool:
        """Set value in cache with TTL (seconds)."""
        pass

    @abstractmethod
    async def delete(self, key: str) -> bool:
        """Delete key from cache."""
        pass

    @abstractmethod
    async def clear_pattern(self, pattern: str) -> int:
        """Clear all keys matching pattern."""
        pass


class InMemoryCache(CacheBackend):
    """In-memory cache for development/fallback."""

    def __init__(self):
        self._cache: Dict[str, tuple[Any, datetime]] = {}
        self._lock = asyncio.Lock()

    async def get(self, key: str) -> Optional[Any]:
        async with self._lock:
            if key in self._cache:
                value, expires_at = self._cache[key]
                if expires_at > datetime.now(timezone.utc):
                    return value
                else:
                    del self._cache[key]
            return None

    async def set(self, key: str, value: Any, ttl: int = 3600) -> bool:
        async with self._lock:
            expires_at = datetime.now(timezone.utc) + timedelta(seconds=ttl)
            self._cache[key] = (value, expires_at)
            return True

    async def delete(self, key: str) -> bool:
        async with self._lock:
            if key in self._cache:
                del self._cache[key]
                return True
            return False

    async def clear_pattern(self, pattern: str) -> int:
        """Clear keys matching pattern (simple prefix match)."""
        async with self._lock:
            prefix = pattern.rstrip('*')
            keys_to_delete = [k for k in self._cache.keys() if k.startswith(prefix)]
            for key in keys_to_delete:
                del self._cache[key]
            return len(keys_to_delete)


class RedisCache(CacheBackend):
    """Redis cache backend for production."""

    def __init__(self, redis_url: str):
        self._redis_url = redis_url
        self._client = None

    async def _get_client(self):
        if self._client is None:
            try:
                import redis.asyncio as redis
                self._client = redis.from_url(self._redis_url, decode_responses=True)
            except ImportError:
                raise RuntimeError("redis package not installed. Run: pip install redis")
        return self._client

    async def get(self, key: str) -> Optional[Any]:
        try:
            client = await self._get_client()
            value = await client.get(key)
            if value:
                return json.loads(value)
            return None
        except Exception:
            return None

    async def set(self, key: str, value: Any, ttl: int = 3600) -> bool:
        try:
            client = await self._get_client()
            await client.set(key, json.dumps(value), ex=ttl)
            return True
        except Exception:
            return False

    async def delete(self, key: str) -> bool:
        try:
            client = await self._get_client()
            await client.delete(key)
            return True
        except Exception:
            return False

    async def clear_pattern(self, pattern: str) -> int:
        try:
            client = await self._get_client()
            cursor = 0
            deleted = 0
            while True:
                cursor, keys = await client.scan(cursor, match=pattern, count=100)
                if keys:
                    await client.delete(*keys)
                    deleted += len(keys)
                if cursor == 0:
                    break
            return deleted
        except Exception:
            return 0


class CacheService:
    """
    Unified cache service for the application.

    Features:
    - Automatic backend selection (Redis or in-memory)
    - Consistent key namespacing
    - JSON serialization
    - TTL management
    """

    def __init__(self, backend: CacheBackend, namespace: str = "aquapurite"):
        self._backend = backend
        self._namespace = namespace

    def _make_key(self, key: str) -> str:
        """Create namespaced cache key."""
        return f"{self._namespace}:{key}"

    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        return await self._backend.get(self._make_key(key))

    async def set(self, key: str, value: Any, ttl: int = 3600) -> bool:
        """Set value in cache."""
        return await self._backend.set(self._make_key(key), value, ttl)

    async def delete(self, key: str) -> bool:
        """Delete key from cache."""
        return await self._backend.delete(self._make_key(key))

    async def clear_pattern(self, pattern: str) -> int:
        """Clear all keys matching pattern."""
        return await self._backend.clear_pattern(self._make_key(pattern))

    # ==================== Serviceability Cache ====================

    def _serviceability_key(self, pincode: str, channel: str = "D2C") -> str:
        """Generate cache key for serviceability."""
        return f"serviceability:{channel}:{pincode}"

    async def get_serviceability(self, pincode: str, channel: str = "D2C") -> Optional[dict]:
        """Get cached serviceability result."""
        key = self._serviceability_key(pincode, channel)
        return await self.get(key)

    async def set_serviceability(
        self,
        pincode: str,
        data: dict,
        channel: str = "D2C",
        ttl: Optional[int] = None
    ) -> bool:
        """Cache serviceability result."""
        key = self._serviceability_key(pincode, channel)
        ttl = ttl or settings.SERVICEABILITY_CACHE_TTL
        return await self.set(key, data, ttl)

    async def invalidate_serviceability(self, pincode: Optional[str] = None, channel: str = "D2C") -> int:
        """Invalidate serviceability cache."""
        if pincode:
            key = self._serviceability_key(pincode, channel)
            await self.delete(key)
            return 1
        else:
            # Clear all serviceability cache for channel
            return await self.clear_pattern(f"serviceability:{channel}:*")

    # ==================== Product Cache ====================

    def _product_key(self, product_id: str) -> str:
        """Generate cache key for product."""
        return f"product:{product_id}"

    def _product_list_key(self, params_hash: str) -> str:
        """Generate cache key for product list."""
        return f"products:list:{params_hash}"

    @staticmethod
    def hash_params(params: dict) -> str:
        """Create hash from query parameters."""
        sorted_params = sorted(params.items())
        param_str = json.dumps(sorted_params, sort_keys=True)
        return hashlib.md5(param_str.encode()).hexdigest()[:12]

    async def get_product(self, product_id: str) -> Optional[dict]:
        """Get cached product."""
        key = self._product_key(product_id)
        return await self.get(key)

    async def set_product(self, product_id: str, data: dict, ttl: Optional[int] = None) -> bool:
        """Cache product data."""
        key = self._product_key(product_id)
        ttl = ttl or settings.PRODUCT_CACHE_TTL
        return await self.set(key, data, ttl)

    async def get_product_list(self, params: dict) -> Optional[dict]:
        """Get cached product list."""
        params_hash = self.hash_params(params)
        key = self._product_list_key(params_hash)
        return await self.get(key)

    async def set_product_list(self, params: dict, data: dict, ttl: Optional[int] = None) -> bool:
        """Cache product list."""
        params_hash = self.hash_params(params)
        key = self._product_list_key(params_hash)
        ttl = ttl or settings.PRODUCT_CACHE_TTL
        return await self.set(key, data, ttl)

    async def invalidate_products(self) -> int:
        """Invalidate all product caches."""
        count = await self.clear_pattern("product:*")
        count += await self.clear_pattern("products:*")
        return count

    # ==================== Category Cache ====================

    async def invalidate_categories(self) -> int:
        """Invalidate all category caches."""
        count = await self.clear_pattern("categories:*")
        return count

    # ==================== Brand Cache ====================

    async def invalidate_brands(self) -> int:
        """Invalidate all brand caches."""
        count = await self.clear_pattern("brands:*")
        return count

    # ==================== Company Cache ====================

    async def invalidate_company(self) -> int:
        """Invalidate company cache."""
        await self.delete("company:info")
        return 1

    # ==================== Bulk Invalidation ====================

    async def invalidate_storefront(self) -> int:
        """Invalidate all storefront-related caches."""
        count = await self.invalidate_products()
        count += await self.invalidate_categories()
        count += await self.invalidate_brands()
        count += await self.invalidate_company()
        return count


# Singleton cache instance
_cache_instance: Optional[CacheService] = None


def get_cache() -> CacheService:
    """Get the cache service singleton."""
    global _cache_instance

    if _cache_instance is None:
        if settings.REDIS_URL and settings.CACHE_ENABLED:
            try:
                backend = RedisCache(settings.REDIS_URL)
            except Exception:
                # Fallback to in-memory if Redis fails
                backend = InMemoryCache()
        else:
            backend = InMemoryCache()

        _cache_instance = CacheService(backend)

    return _cache_instance


async def init_cache() -> CacheService:
    """Initialize and return cache service."""
    return get_cache()
