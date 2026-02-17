"""
Tenant Onboarding API Endpoints

Public endpoints for new tenant registration and signup.
These endpoints do NOT require authentication.
"""

from uuid import UUID
from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select
from pydantic import BaseModel

from app.api.deps import PublicDB as DB
from app.schemas.onboarding import (
    SubdomainCheckRequest,
    SubdomainCheckResponse,
    TenantRegistrationRequest,
    TenantRegistrationResponse,
    ModuleListResponse,
    AvailableModuleResponse,
)
from app.services.tenant_onboarding_service import TenantOnboardingService
from app.models.tenant import Tenant


router = APIRouter(tags=["Onboarding"])


@router.get("/ping")
async def ping():
    """Simple ping endpoint to test connectivity."""
    return {"status": "ok", "message": "Onboarding API is responsive"}


class TenantSetupStatusResponse(BaseModel):
    """Response for tenant setup status check."""
    tenant_id: str
    subdomain: str
    status: str
    is_ready: bool
    message: str
    error: str | None = None


class TenantRetryResponse(BaseModel):
    """Response for tenant setup retry."""
    success: bool
    message: str
    status: str


@router.post("/check-subdomain", response_model=SubdomainCheckResponse)
async def check_subdomain_availability(
    data: SubdomainCheckRequest,
    db: DB,
):
    """
    Check if a subdomain is available for registration.

    This is a public endpoint that does not require authentication.
    """
    service = TenantOnboardingService(db)

    is_available, message = await service.check_subdomain_available(data.subdomain)

    return SubdomainCheckResponse(
        subdomain=data.subdomain,
        available=is_available,
        message=message if not is_available else f"Subdomain '{data.subdomain}' is available!"
    )


@router.get("/modules", response_model=ModuleListResponse)
async def get_available_modules(
    db: DB,
):
    """
    Get list of all available ERP modules with pricing.

    This is a public endpoint that shows module catalog.
    """
    service = TenantOnboardingService(db)

    modules = await service.get_available_modules()

    module_responses = [
        AvailableModuleResponse(
            code=m.code,
            name=m.name,
            description=m.description or "",
            category=m.category or "general",
            base_price=float(m.price_monthly or 0),
            is_required=(m.code == "system_admin"),
            dependencies=m.dependencies or [],
            features=m.sections or []
        )
        for m in modules
    ]

    return ModuleListResponse(
        modules=module_responses,
        total=len(module_responses)
    )


@router.post("/register", response_model=TenantRegistrationResponse)
async def register_tenant(
    data: TenantRegistrationRequest,
    db: DB,
):
    """
    Register a new tenant and create their account.

    This endpoint:
    1. Validates subdomain availability
    2. Creates tenant record
    3. Creates module subscriptions
    4. Returns JWT tokens for immediate login

    Note: Database schema creation happens asynchronously (Phase 3B).
    The user can log in immediately, but full functionality requires schema setup.
    """
    service = TenantOnboardingService(db)

    try:
        # Register tenant
        tenant, admin_user_id, access_token, refresh_token, expires_in = await service.register_tenant(
            company_name=data.company_name,
            subdomain=data.subdomain,
            admin_email=data.admin_email,
            admin_password=data.admin_password,
            admin_first_name=data.admin_first_name,
            admin_last_name=data.admin_last_name,
            admin_phone=data.admin_phone,
            selected_modules=data.selected_modules,
            industry=data.industry,
            company_size=data.company_size,
            country=data.country
        )

        # Calculate monthly cost
        monthly_cost = await service.calculate_subscription_cost(
            module_codes=data.selected_modules,
            billing_cycle="monthly"
        )

        # Get plan name (if any)
        # For now, we'll just use "Custom" since modules are selected individually
        plan_name = "Custom Plan"

        return TenantRegistrationResponse(
            tenant_id=str(tenant.id),
            company_name=tenant.name,
            subdomain=tenant.subdomain,
            database_schema=tenant.database_schema,
            status=tenant.status,
            admin_user_id=str(admin_user_id),
            admin_email=data.admin_email,
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            expires_in=expires_in,
            subscribed_modules=data.selected_modules,
            plan_name=plan_name,
            monthly_cost=monthly_cost,
            message=f"Welcome to your ERP, {data.admin_first_name}! Your account is being set up."
        )

    except ValueError as e:
        # Business logic errors (subdomain taken, invalid modules, etc.)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        # Unexpected errors
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Registration failed: {str(e)}"
        )


@router.get("/status/{subdomain}", response_model=TenantSetupStatusResponse)
async def get_tenant_setup_status(
    subdomain: str,
    db: DB,
):
    """
    Check the setup status of a tenant.

    Use this to poll for completion after registration.
    """
    stmt = select(Tenant).where(Tenant.subdomain == subdomain)
    result = await db.execute(stmt)
    tenant = result.scalar_one_or_none()

    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tenant with subdomain '{subdomain}' not found"
        )

    is_ready = tenant.status == "active"
    error = tenant.settings.get("setup_error") if not is_ready else None

    status_messages = {
        "active": "Your account is ready! You can now log in.",
        "pending_setup": "Setting up your account... Please wait.",
        "setup_pending": "Setup is queued. Retry if it takes too long.",
        "pending": "Account created. Setup in progress...",
        "failed": "Setup failed. Please use the retry endpoint.",
    }

    return TenantSetupStatusResponse(
        tenant_id=str(tenant.id),
        subdomain=tenant.subdomain,
        status=tenant.status,
        is_ready=is_ready,
        message=status_messages.get(tenant.status, f"Status: {tenant.status}"),
        error=error
    )


@router.post("/retry/{tenant_id}", response_model=TenantRetryResponse)
async def retry_tenant_setup(
    tenant_id: UUID,
    db: DB,
):
    """
    Retry setup for a failed or pending tenant.

    Use this if initial registration timed out.
    """
    service = TenantOnboardingService(db)

    try:
        success, message = await service.retry_tenant_setup(tenant_id)

        # Get updated status
        stmt = select(Tenant).where(Tenant.id == tenant_id)
        result = await db.execute(stmt)
        tenant = result.scalar_one_or_none()

        return TenantRetryResponse(
            success=success,
            message=message,
            status=tenant.status if tenant else "unknown"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Retry failed: {str(e)}"
        )


class TenantLookupResponse(BaseModel):
    """Response for tenant lookup by subdomain."""
    tenant_id: str
    subdomain: str
    name: str
    status: str


@router.get("/tenant-lookup", response_model=TenantLookupResponse)
async def lookup_tenant_by_subdomain(
    subdomain: str,
    db: DB,
):
    """
    Lookup tenant by subdomain.

    This is a public endpoint used by the frontend to resolve
    tenant context from URL path (e.g., /t/mantosh/login).

    Returns tenant_id needed for X-Tenant-ID header.
    """
    try:
        stmt = select(Tenant).where(
            Tenant.subdomain == subdomain,
            Tenant.status.in_(['active', 'pending'])
        )
        result = await db.execute(stmt)
        tenant = result.scalar_one_or_none()

        if not tenant:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Tenant with subdomain '{subdomain}' not found"
            )

        return TenantLookupResponse(
            tenant_id=str(tenant.id),
            subdomain=tenant.subdomain,
            name=tenant.name,
            status=tenant.status
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Lookup failed: {str(e)}"
        )
