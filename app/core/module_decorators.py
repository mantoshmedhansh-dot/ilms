"""
Module access control decorators for Multi-Tenant SaaS

Provides decorators to check if tenant has access to specific modules.
Includes automatic cache cleanup to prevent memory bloat.
"""
from functools import wraps
from fastapi import HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from app.models.tenant import TenantSubscription, ErpModule
from datetime import datetime, timezone
import logging

logger = logging.getLogger(__name__)

# Cache for module access checks (to reduce database queries)
# Format: {cache_key: (has_access, cache_time)}
_module_access_cache = {}

# Maximum cache entries before cleanup (prevents unbounded growth)
_MAX_CACHE_ENTRIES = 10000

# Cache TTL in seconds
_CACHE_TTL_SECONDS = 300  # 5 minutes


def _cleanup_expired_cache_entries():
    """Remove expired entries from the module access cache."""
    global _module_access_cache
    now = datetime.now(timezone.utc)
    expired_keys = [
        key for key, (_, cache_time) in _module_access_cache.items()
        if (now - cache_time).total_seconds() >= _CACHE_TTL_SECONDS
    ]
    for key in expired_keys:
        del _module_access_cache[key]

    if expired_keys:
        logger.debug(f"Cleaned up {len(expired_keys)} expired cache entries")


def require_module(module_code: str):
    """
    Decorator to check if tenant has access to a specific module

    Usage:
        @router.get("/api/wms/zones")
        @require_module("oms_fulfillment")
        async def get_zones(request: Request):
            ...

    Args:
        module_code: Code of the required module (e.g., "oms_fulfillment")

    Raises:
        HTTPException 401: If tenant context not found
        HTTPException 403: If module not enabled for tenant
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Get tenant from context variable (set by tenant middleware)
            from app.middleware.tenant import current_tenant_var

            tenant = current_tenant_var.get()

            # Fallback: try to find Request in args/kwargs
            if tenant is None:
                request = None
                for arg in args:
                    if isinstance(arg, Request):
                        request = arg
                        break
                if not request:
                    for val in kwargs.values():
                        if isinstance(val, Request):
                            request = val
                            break
                if request and hasattr(request, 'state') and hasattr(request.state, 'tenant'):
                    tenant = request.state.tenant

            if tenant is None:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Tenant context not found. Please login."
                )

            tenant_id = tenant.id

            # Check cache first (to reduce database queries)
            cache_key = f"{tenant_id}:{module_code}"
            if cache_key in _module_access_cache:
                has_access, cache_time = _module_access_cache[cache_key]
                # Cache valid for configured TTL
                if (datetime.now(timezone.utc) - cache_time).total_seconds() < _CACHE_TTL_SECONDS:
                    if not has_access:
                        raise HTTPException(
                            status_code=status.HTTP_403_FORBIDDEN,
                            detail=f"Module '{module_code}' is not enabled for your account. Please upgrade your subscription."
                        )
                    # Access granted, proceed
                    return await func(*args, **kwargs)
                else:
                    # Entry expired, remove it
                    del _module_access_cache[cache_key]

            # Cleanup if cache is getting too large
            if len(_module_access_cache) > _MAX_CACHE_ENTRIES:
                _cleanup_expired_cache_entries()

            # Check if module is enabled for this tenant
            from app.database import async_session_maker

            async with async_session_maker() as db:
                has_access = await check_module_access(db, tenant_id, module_code)

                # Update cache
                _module_access_cache[cache_key] = (has_access, datetime.now(timezone.utc))

                if not has_access:
                    logger.warning(
                        f"Module access denied: Tenant {tenant.name} "
                        f"attempted to access module '{module_code}'"
                    )
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail=f"Module '{module_code}' is not enabled for your account. Please upgrade your subscription."
                    )

                # Module access granted, proceed with request
                logger.debug(f"Module access granted: {tenant.name} -> {module_code}")
                return await func(*args, **kwargs)

        return wrapper
    return decorator


async def check_module_access(db: AsyncSession, tenant_id: str, module_code: str) -> bool:
    """
    Check if tenant has active subscription to a module

    Args:
        db: Database session (public schema)
        tenant_id: Tenant UUID
        module_code: Module code (e.g., "oms_fulfillment")

    Returns:
        True if tenant has access, False otherwise
    """
    # Check if tenant has active subscription for this module
    result = await db.execute(
        select(TenantSubscription)
        .join(ErpModule, TenantSubscription.module_id == ErpModule.id)
        .where(
            and_(
                TenantSubscription.tenant_id == tenant_id,
                ErpModule.code == module_code,
                TenantSubscription.status == 'active'
            )
        )
    )
    subscription = result.scalar_one_or_none()

    if not subscription:
        return False

    # Check if subscription has expired
    if subscription.expires_at:
        if subscription.expires_at < datetime.now(timezone.utc):
            logger.warning(
                f"Subscription expired: Tenant {tenant_id} "
                f"| Module {module_code} | Expired {subscription.expires_at}"
            )
            return False

    return True


async def get_tenant_enabled_modules(db: AsyncSession, tenant_id: str) -> list[str]:
    """
    Get list of module codes enabled for a tenant

    Args:
        db: Database session (public schema)
        tenant_id: Tenant UUID

    Returns:
        List of module codes (e.g., ["oms_fulfillment", "finance"])
    """
    result = await db.execute(
        select(ErpModule.code)
        .join(TenantSubscription, TenantSubscription.module_id == ErpModule.id)
        .where(
            and_(
                TenantSubscription.tenant_id == tenant_id,
                TenantSubscription.status == 'active'
            )
        )
    )
    modules = result.scalars().all()
    return list(modules)


def clear_module_access_cache():
    """Clear the module access cache (useful for testing or after subscription changes)"""
    global _module_access_cache
    _module_access_cache.clear()
    logger.info("Module access cache cleared")


def clear_module_access_cache_for_tenant(tenant_id: str):
    """Clear cache for a specific tenant (when their subscription changes)"""
    global _module_access_cache
    keys_to_remove = [key for key in _module_access_cache if key.startswith(f"{tenant_id}:")]
    for key in keys_to_remove:
        del _module_access_cache[key]
    logger.info(f"Module access cache cleared for tenant {tenant_id}")
