"""
Tenant Context Manager for Multi-Tenant SaaS

This module provides standardized utilities for working with tenant data
in a multi-tenant environment. All services and jobs should use these
utilities to ensure proper schema isolation.

Key Principles:
1. NEVER query tenant-specific tables without a tenant context
2. ALWAYS use the context managers provided here
3. Operational tables exist in TENANT schemas, not PUBLIC
4. PUBLIC schema contains: tenants, modules, plans, subscriptions

Usage Examples:

    # In a background job:
    async with tenant_db_context(tenant_id) as session:
        result = await session.execute(text("SELECT * FROM inventory"))

    # In a service:
    class InventoryService:
        def __init__(self, db: AsyncSession):
            # db should already be configured for tenant schema
            self.db = db

    # Getting tenant from request:
    tenant = get_tenant_from_request(request)
"""

import logging
import uuid
from typing import Optional, AsyncGenerator, Dict, Any
from contextlib import asynccontextmanager

from sqlalchemy import text, select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import Request, HTTPException, status

logger = logging.getLogger(__name__)

# Cache for tenant lookups (reduces DB queries)
_tenant_cache: Dict[str, dict] = {}
_CACHE_TTL_SECONDS = 300  # 5 minutes


class TenantNotFoundError(Exception):
    """Raised when tenant cannot be found."""
    pass


class TenantInactiveError(Exception):
    """Raised when tenant is not active."""
    pass


class NoTenantContextError(Exception):
    """Raised when code requires tenant context but none is provided."""
    pass


async def get_tenant_by_id(tenant_id: uuid.UUID) -> dict:
    """
    Fetch tenant details by ID.

    Args:
        tenant_id: UUID of the tenant

    Returns:
        Tenant dictionary with id, subdomain, database_schema, status

    Raises:
        TenantNotFoundError: If tenant doesn't exist
    """
    from app.database import async_session_factory

    cache_key = str(tenant_id)
    if cache_key in _tenant_cache:
        return _tenant_cache[cache_key]

    async with async_session_factory() as session:
        result = await session.execute(
            text("""
                SELECT
                    id,
                    name,
                    subdomain,
                    database_schema,
                    status,
                    settings,
                    plan_id
                FROM public.tenants
                WHERE id = :tenant_id
            """),
            {"tenant_id": str(tenant_id)}
        )
        row = result.fetchone()

        if not row:
            raise TenantNotFoundError(f"Tenant {tenant_id} not found")

        tenant = {
            "id": str(row.id),
            "name": row.name,
            "subdomain": row.subdomain,
            "database_schema": row.database_schema,
            "status": row.status,
            "settings": row.settings or {},
            "plan_id": str(row.plan_id) if row.plan_id else None
        }

        # Cache it
        _tenant_cache[cache_key] = tenant

        return tenant


async def get_tenant_by_subdomain(subdomain: str) -> dict:
    """
    Fetch tenant details by subdomain.

    Args:
        subdomain: Tenant's subdomain

    Returns:
        Tenant dictionary

    Raises:
        TenantNotFoundError: If tenant doesn't exist
    """
    from app.database import async_session_factory

    cache_key = f"subdomain:{subdomain}"
    if cache_key in _tenant_cache:
        return _tenant_cache[cache_key]

    async with async_session_factory() as session:
        result = await session.execute(
            text("""
                SELECT
                    id,
                    name,
                    subdomain,
                    database_schema,
                    status,
                    settings,
                    plan_id
                FROM public.tenants
                WHERE subdomain = :subdomain
            """),
            {"subdomain": subdomain}
        )
        row = result.fetchone()

        if not row:
            raise TenantNotFoundError(f"Tenant with subdomain '{subdomain}' not found")

        tenant = {
            "id": str(row.id),
            "name": row.name,
            "subdomain": row.subdomain,
            "database_schema": row.database_schema,
            "status": row.status,
            "settings": row.settings or {},
            "plan_id": str(row.plan_id) if row.plan_id else None
        }

        # Cache both by ID and subdomain
        _tenant_cache[cache_key] = tenant
        _tenant_cache[str(row.id)] = tenant

        return tenant


def clear_tenant_cache(tenant_id: Optional[str] = None):
    """
    Clear tenant cache.

    Args:
        tenant_id: Specific tenant to clear, or None to clear all
    """
    global _tenant_cache
    if tenant_id:
        _tenant_cache.pop(tenant_id, None)
        # Also clear subdomain cache entries for this tenant
        to_remove = [k for k, v in _tenant_cache.items() if v.get("id") == tenant_id]
        for k in to_remove:
            _tenant_cache.pop(k, None)
    else:
        _tenant_cache = {}


@asynccontextmanager
async def tenant_db_context(
    tenant_id: uuid.UUID,
    verify_active: bool = True
) -> AsyncGenerator[AsyncSession, None]:
    """
    Context manager for executing queries in a tenant's schema.

    This is the RECOMMENDED way to run queries against tenant data
    in background jobs, services, and utilities.

    Args:
        tenant_id: UUID of the tenant
        verify_active: If True, raises error if tenant is not active

    Yields:
        AsyncSession configured for the tenant's schema

    Raises:
        TenantNotFoundError: If tenant doesn't exist
        TenantInactiveError: If tenant is not active and verify_active=True

    Example:
        async with tenant_db_context(tenant_id) as session:
            result = await session.execute(
                text("SELECT * FROM inventory WHERE is_active = true")
            )
            items = result.fetchall()
    """
    from app.database import engine

    # Get tenant info
    tenant = await get_tenant_by_id(tenant_id)

    if verify_active and tenant["status"] != "active":
        raise TenantInactiveError(
            f"Tenant {tenant['subdomain']} is not active (status: {tenant['status']})"
        )

    schema = tenant["database_schema"]

    # Create connection with tenant schema
    async with engine.connect() as conn:
        # Set search path to tenant schema
        await conn.execute(text(f'SET search_path TO "{schema}"'))

        # Create session from connection
        session = AsyncSession(bind=conn, expire_on_commit=False)

        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


def get_tenant_from_request(request: Request) -> dict:
    """
    Extract tenant information from a FastAPI request.

    The tenant middleware should have already set these on request.state.

    Args:
        request: FastAPI Request object

    Returns:
        Tenant dictionary

    Raises:
        NoTenantContextError: If no tenant context in request
    """
    if not hasattr(request.state, "tenant_id"):
        raise NoTenantContextError(
            "No tenant context found in request. "
            "Ensure tenant middleware is configured."
        )

    return {
        "id": getattr(request.state, "tenant_id", None),
        "subdomain": getattr(request.state, "subdomain", None),
        "schema": getattr(request.state, "schema", None),
    }


def require_tenant_context(request: Request) -> dict:
    """
    FastAPI dependency to require tenant context.

    Usage:
        @router.get("/inventory")
        async def get_inventory(tenant: dict = Depends(require_tenant_context)):
            ...

    Raises:
        HTTPException: If no tenant context
    """
    try:
        return get_tenant_from_request(request)
    except NoTenantContextError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tenant context required. Include X-Tenant-ID header."
        )


# ============================================================
# TABLE EXISTENCE CHECKS
# ============================================================

async def table_exists_in_schema(
    session: AsyncSession,
    table_name: str,
    schema_name: Optional[str] = None
) -> bool:
    """
    Check if a table exists in a schema.

    Args:
        session: Database session
        table_name: Name of the table
        schema_name: Schema name (uses current search_path if None)

    Returns:
        True if table exists
    """
    if schema_name:
        query = text("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables
                WHERE table_schema = :schema
                AND table_name = :table
            )
        """)
        result = await session.execute(
            query,
            {"schema": schema_name, "table": table_name}
        )
    else:
        query = text("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables
                WHERE table_name = :table
                AND table_schema = current_schema()
            )
        """)
        result = await session.execute(query, {"table": table_name})

    return result.scalar() or False


async def ensure_table_exists(
    session: AsyncSession,
    table_name: str,
    error_message: Optional[str] = None
):
    """
    Ensure a table exists, raising an error if not.

    Useful for defensive programming in services.

    Args:
        session: Database session
        table_name: Name of the table
        error_message: Custom error message

    Raises:
        RuntimeError: If table doesn't exist
    """
    exists = await table_exists_in_schema(session, table_name)
    if not exists:
        raise RuntimeError(
            error_message or
            f"Table '{table_name}' does not exist in current schema. "
            f"Ensure tenant schema is properly initialized."
        )


# ============================================================
# MULTI-TENANT BEST PRACTICES
# ============================================================

"""
MULTI-TENANT DEVELOPMENT GUIDELINES
====================================

1. SCHEMA ISOLATION
   - Operational data (orders, inventory, users) lives in TENANT schemas
   - Platform data (tenants, modules, plans) lives in PUBLIC schema
   - Never mix queries across schemas without explicit intent

2. SESSION HANDLING
   - API endpoints: Use TenantDB dependency (already configured by middleware)
   - Background jobs: Use tenant_db_context() context manager
   - Services: Accept session as constructor argument

3. RAW SQL
   - Avoid raw SQL when possible (use SQLAlchemy models)
   - If raw SQL needed, never hardcode schema names
   - The session's search_path determines which schema is used

4. ERROR HANDLING
   - Catch ProgrammingError for "relation does not exist" errors
   - These indicate the table hasn't been created in the tenant schema
   - Handle gracefully (skip, log, or create table on-demand)

5. CACHING
   - Cache keys MUST include tenant_id
   - Example: f"inventory:{tenant_id}:{product_id}"
   - Never share cached data across tenants

6. TESTING
   - Test with multiple tenants
   - Test with missing tables (new tenant, incomplete setup)
   - Test tenant isolation (data from tenant A not visible to B)

COMMON MISTAKES TO AVOID
========================

❌ Querying tenant tables in PUBLIC schema
❌ Using hardcoded schema names in SQL
❌ Caching data without tenant_id in key
❌ Running background jobs without tenant context
❌ Assuming all tables exist in every tenant schema

✅ Always use tenant_db_context() for tenant data access
✅ Use TenantDB dependency in API endpoints
✅ Include tenant_id in all cache keys
✅ Handle missing tables gracefully
✅ Test multi-tenant scenarios
"""
