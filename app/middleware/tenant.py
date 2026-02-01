"""
Tenant middleware for multi-tenant request handling
"""
from fastapi import Request, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.tenant import Tenant
import logging

logger = logging.getLogger(__name__)


async def get_tenant_from_request(request: Request, db: AsyncSession) -> Tenant:
    """
    Extract tenant from request (subdomain, header, or JWT token)

    Priority:
    1. Custom header (X-Tenant-ID) - for API calls
    2. Subdomain - for browser access
    3. JWT token - if user is logged in

    Args:
        request: FastAPI request object
        db: Database session for public schema

    Returns:
        Tenant object if found

    Raises:
        HTTPException: If tenant not found or invalid
    """
    tenant = None

    # Option 1: Extract from custom header (for API calls)
    tenant_id = request.headers.get("X-Tenant-ID")
    if tenant_id:
        tenant = await get_tenant_by_id(db, tenant_id)
        if tenant:
            logger.info(f"Tenant identified by header: {tenant.name}")
            return tenant

    # Option 2: Extract from subdomain
    host = request.headers.get("host", "")
    if "." in host:
        subdomain = host.split(".")[0]
        # Check if it's a valid subdomain (not www, api, admin, etc.)
        if subdomain not in ["www", "api", "admin", "localhost"]:
            tenant = await get_tenant_by_subdomain(db, subdomain)
            if tenant:
                logger.info(f"Tenant identified by subdomain: {tenant.name}")
                return tenant

    # Option 3: Extract from JWT token (if user is logged in)
    if hasattr(request.state, "user") and request.state.user:
        tenant_id = request.state.user.get("tenant_id")
        if tenant_id:
            tenant = await get_tenant_by_id(db, tenant_id)
            if tenant:
                logger.info(f"Tenant identified by JWT: {tenant.name}")
                return tenant

    # No tenant found
    logger.warning(f"Tenant not found for host: {host}")
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Tenant not found. Please check your subdomain or login credentials."
    )


async def get_tenant_by_subdomain(db: AsyncSession, subdomain: str) -> Tenant:
    """Get tenant by subdomain"""
    result = await db.execute(
        select(Tenant).where(
            Tenant.subdomain == subdomain,
            Tenant.status == 'active'
        )
    )
    return result.scalar_one_or_none()


async def get_tenant_by_id(db: AsyncSession, tenant_id: str) -> Tenant:
    """Get tenant by ID"""
    result = await db.execute(
        select(Tenant).where(
            Tenant.id == tenant_id,
            Tenant.status == 'active'
        )
    )
    return result.scalar_one_or_none()


async def tenant_middleware(request: Request, call_next):
    """
    Middleware to inject tenant context into request

    This middleware:
    1. Identifies the tenant from the request
    2. Injects tenant information into request.state
    3. Sets the database schema for the tenant

    Public routes (health check, docs, etc.) skip tenant check.
    """
    # Skip tenant check for public routes
    public_routes = [
        "/health",
        "/docs",
        "/openapi.json",
        "/redoc",
        "/api/auth/login",
        "/api/auth/register",
        "/api/tenants",  # Tenant onboarding (old)
        "/",  # Root endpoint
    ]

    # Check if path starts with public prefixes
    public_prefixes = [
        "/static",
        "/api/v1/onboarding",  # Tenant onboarding (Phase 3)
        "/api/v1/admin",  # Platform administration (Phase 3D)
        "/api/v1/storefront",  # D2C public storefront
    ]

    if request.url.path in public_routes:
        return await call_next(request)

    for prefix in public_prefixes:
        if request.url.path.startswith(prefix):
            return await call_next(request)

    # Get database session for public schema
    from app.database import async_session_maker

    async with async_session_maker() as db:
        # Get tenant from request (HTTPException raised here will propagate naturally)
        tenant = await get_tenant_from_request(request, db)

        # Inject tenant into request state
        request.state.tenant = tenant
        request.state.tenant_id = str(tenant.id)
        request.state.schema = tenant.database_schema

        logger.info(
            f"Request for tenant: {tenant.name} ({tenant.subdomain}) "
            f"| Schema: {tenant.database_schema}"
        )

        # Continue with request
        response = await call_next(request)
        return response
