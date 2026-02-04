"""
Multi-Tenant Cache Service for Fast Serviceability and Product Lookups.

IMPORTANT: All cache keys MUST include tenant_id to prevent cross-tenant
data leakage. This is a critical security requirement for multi-tenant SaaS.

Supports:
1. Redis (preferred for production)
2. In-memory fallback (for development/testing)

Usage:
    cache = get_cache()

    # ALWAYS include tenant_id in cache operations
    await cache.set_product(tenant_id, product_id, product_data)
    product = await cache.get_product(tenant_id, product_id)

    # Invalidate all products for a specific tenant
    await cache.invalidate_products(tenant_id)
"""
import json
import hashlib
from typing import Any, Optional, Dict
from datetime import datetime, timedelta, timezone
from abc import ABC, abstractmethod
import asyncio
import logging

from app.config import settings

logger = logging.getLogger(__name__)


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
    """
    In-memory cache for development/fallback.

    Note: In production multi-tenant environments, prefer Redis
    as in-memory cache doesn't share across multiple server instances.
    """

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

    async def cleanup_expired(self) -> int:
        """Remove expired entries. Call periodically to prevent memory bloat."""
        async with self._lock:
            now = datetime.now(timezone.utc)
            expired_keys = [
                k for k, (_, expires_at) in self._cache.items()
                if expires_at <= now
            ]
            for key in expired_keys:
                del self._cache[key]
            return len(expired_keys)


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
    Multi-Tenant Cache Service.

    CRITICAL: All cache operations MUST include tenant_id to ensure
    data isolation between tenants. Cache keys follow the format:

        {namespace}:{tenant_id}:{resource_type}:{identifier}

    Examples:
        ilms:tenant123:product:prod456
        ilms:tenant123:serviceability:D2C:110001
        ilms:tenant123:categories:all

    Features:
    - Tenant-isolated caching (REQUIRED for multi-tenant)
    - Automatic backend selection (Redis or in-memory)
    - JSON serialization
    - TTL management
    """

    def __init__(self, backend: CacheBackend, namespace: str = "ilms"):
        self._backend = backend
        self._namespace = namespace

    def _make_key(self, tenant_id: str, key: str) -> str:
        """
        Create namespaced, tenant-isolated cache key.

        IMPORTANT: tenant_id MUST be included to prevent cross-tenant leakage.
        """
        if not tenant_id:
            logger.warning(f"Cache key created without tenant_id: {key}")
        return f"{self._namespace}:{tenant_id}:{key}"

    def _make_global_key(self, key: str) -> str:
        """
        Create global cache key (NOT tenant-specific).

        Use sparingly - only for truly global data like:
        - Module definitions
        - Plan configurations
        - System settings
        """
        return f"{self._namespace}:global:{key}"

    async def get(self, tenant_id: str, key: str) -> Optional[Any]:
        """Get value from tenant-specific cache."""
        return await self._backend.get(self._make_key(tenant_id, key))

    async def set(self, tenant_id: str, key: str, value: Any, ttl: int = 3600) -> bool:
        """Set value in tenant-specific cache."""
        return await self._backend.set(self._make_key(tenant_id, key), value, ttl)

    async def delete(self, tenant_id: str, key: str) -> bool:
        """Delete key from tenant-specific cache."""
        return await self._backend.delete(self._make_key(tenant_id, key))

    async def clear_pattern(self, tenant_id: str, pattern: str) -> int:
        """Clear all keys matching pattern for a tenant."""
        return await self._backend.clear_pattern(self._make_key(tenant_id, pattern))

    async def clear_tenant_cache(self, tenant_id: str) -> int:
        """Clear ALL cached data for a tenant."""
        pattern = f"{self._namespace}:{tenant_id}:*"
        return await self._backend.clear_pattern(pattern)

    # ==================== Global Cache (Platform-wide) ====================

    async def get_global(self, key: str) -> Optional[Any]:
        """Get value from global cache (not tenant-specific)."""
        return await self._backend.get(self._make_global_key(key))

    async def set_global(self, key: str, value: Any, ttl: int = 3600) -> bool:
        """Set value in global cache."""
        return await self._backend.set(self._make_global_key(key), value, ttl)

    # ==================== Serviceability Cache ====================

    def _serviceability_key(self, pincode: str, channel: str = "D2C") -> str:
        """Generate cache key for serviceability (tenant_id added by caller)."""
        return f"serviceability:{channel}:{pincode}"

    async def get_serviceability(
        self,
        tenant_id: str,
        pincode: str,
        channel: str = "D2C"
    ) -> Optional[dict]:
        """Get cached serviceability result for a tenant."""
        key = self._serviceability_key(pincode, channel)
        return await self.get(tenant_id, key)

    async def set_serviceability(
        self,
        tenant_id: str,
        pincode: str,
        data: dict,
        channel: str = "D2C",
        ttl: Optional[int] = None
    ) -> bool:
        """Cache serviceability result for a tenant."""
        key = self._serviceability_key(pincode, channel)
        ttl = ttl or settings.SERVICEABILITY_CACHE_TTL
        return await self.set(tenant_id, key, data, ttl)

    async def invalidate_serviceability(
        self,
        tenant_id: str,
        pincode: Optional[str] = None,
        channel: str = "D2C"
    ) -> int:
        """Invalidate serviceability cache for a tenant."""
        if pincode:
            key = self._serviceability_key(pincode, channel)
            await self.delete(tenant_id, key)
            return 1
        else:
            # Clear all serviceability cache for tenant and channel
            return await self.clear_pattern(tenant_id, f"serviceability:{channel}:*")

    # ==================== Product Cache ====================

    def _product_key(self, product_id: str) -> str:
        """Generate cache key for product (tenant_id added by caller)."""
        return f"product:{product_id}"

    def _product_list_key(self, params_hash: str) -> str:
        """Generate cache key for product list (tenant_id added by caller)."""
        return f"products:list:{params_hash}"

    @staticmethod
    def hash_params(params: dict) -> str:
        """Create hash from query parameters."""
        sorted_params = sorted(params.items())
        param_str = json.dumps(sorted_params, sort_keys=True)
        return hashlib.md5(param_str.encode()).hexdigest()[:12]

    async def get_product(self, tenant_id: str, product_id: str) -> Optional[dict]:
        """Get cached product for a tenant."""
        key = self._product_key(product_id)
        return await self.get(tenant_id, key)

    async def set_product(
        self,
        tenant_id: str,
        product_id: str,
        data: dict,
        ttl: Optional[int] = None
    ) -> bool:
        """Cache product data for a tenant."""
        key = self._product_key(product_id)
        ttl = ttl or settings.PRODUCT_CACHE_TTL
        return await self.set(tenant_id, key, data, ttl)

    async def get_product_list(self, tenant_id: str, params: dict) -> Optional[dict]:
        """Get cached product list for a tenant."""
        params_hash = self.hash_params(params)
        key = self._product_list_key(params_hash)
        return await self.get(tenant_id, key)

    async def set_product_list(
        self,
        tenant_id: str,
        params: dict,
        data: dict,
        ttl: Optional[int] = None
    ) -> bool:
        """Cache product list for a tenant."""
        params_hash = self.hash_params(params)
        key = self._product_list_key(params_hash)
        ttl = ttl or settings.PRODUCT_CACHE_TTL
        return await self.set(tenant_id, key, data, ttl)

    async def invalidate_products(self, tenant_id: str) -> int:
        """Invalidate all product caches for a tenant."""
        count = await self.clear_pattern(tenant_id, "product:*")
        count += await self.clear_pattern(tenant_id, "products:*")
        return count

    # ==================== Category Cache ====================

    async def get_categories(self, tenant_id: str) -> Optional[list]:
        """Get cached categories for a tenant."""
        return await self.get(tenant_id, "categories:all")

    async def set_categories(
        self,
        tenant_id: str,
        data: list,
        ttl: int = 3600
    ) -> bool:
        """Cache categories for a tenant."""
        return await self.set(tenant_id, "categories:all", data, ttl)

    async def invalidate_categories(self, tenant_id: str) -> int:
        """Invalidate all category caches for a tenant."""
        return await self.clear_pattern(tenant_id, "categories:*")

    # ==================== Brand Cache ====================

    async def get_brands(self, tenant_id: str) -> Optional[list]:
        """Get cached brands for a tenant."""
        return await self.get(tenant_id, "brands:all")

    async def set_brands(
        self,
        tenant_id: str,
        data: list,
        ttl: int = 3600
    ) -> bool:
        """Cache brands for a tenant."""
        return await self.set(tenant_id, "brands:all", data, ttl)

    async def invalidate_brands(self, tenant_id: str) -> int:
        """Invalidate all brand caches for a tenant."""
        return await self.clear_pattern(tenant_id, "brands:*")

    # ==================== Company Cache ====================

    async def get_company(self, tenant_id: str) -> Optional[dict]:
        """Get cached company info for a tenant."""
        return await self.get(tenant_id, "company:info")

    async def set_company(
        self,
        tenant_id: str,
        data: dict,
        ttl: int = 3600
    ) -> bool:
        """Cache company info for a tenant."""
        return await self.set(tenant_id, "company:info", data, ttl)

    async def invalidate_company(self, tenant_id: str) -> int:
        """Invalidate company cache for a tenant."""
        await self.delete(tenant_id, "company:info")
        return 1

    # ==================== Inventory Cache ====================

    async def get_inventory(
        self,
        tenant_id: str,
        product_id: str,
        warehouse_id: str = "default"
    ) -> Optional[dict]:
        """Get cached inventory for a tenant."""
        key = f"inventory:{product_id}:{warehouse_id}"
        return await self.get(tenant_id, key)

    async def set_inventory(
        self,
        tenant_id: str,
        product_id: str,
        warehouse_id: str,
        data: dict,
        ttl: int = 600  # 10 minutes
    ) -> bool:
        """Cache inventory data for a tenant."""
        key = f"inventory:{product_id}:{warehouse_id}"
        return await self.set(tenant_id, key, data, ttl)

    async def invalidate_inventory(self, tenant_id: str) -> int:
        """Invalidate all inventory caches for a tenant."""
        return await self.clear_pattern(tenant_id, "inventory:*")

    # ==================== Bulk Invalidation ====================

    async def invalidate_storefront(self, tenant_id: str) -> int:
        """Invalidate all storefront-related caches for a tenant."""
        count = await self.invalidate_products(tenant_id)
        count += await self.invalidate_categories(tenant_id)
        count += await self.invalidate_brands(tenant_id)
        count += await self.invalidate_company(tenant_id)
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
                logger.info("Cache initialized with Redis backend")
            except Exception as e:
                logger.warning(f"Redis init failed, using in-memory: {e}")
                backend = InMemoryCache()
        else:
            backend = InMemoryCache()
            logger.info("Cache initialized with in-memory backend")

        _cache_instance = CacheService(backend)

    return _cache_instance


async def init_cache() -> CacheService:
    """Initialize and return cache service."""
    return get_cache()
