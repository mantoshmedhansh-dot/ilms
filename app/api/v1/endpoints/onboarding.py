"""
Tenant Onboarding API Endpoints

Public endpoints for new tenant registration and signup.
These endpoints do NOT require authentication.
"""

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from app.api.deps import DB
from app.schemas.onboarding import (
    SubdomainCheckRequest,
    SubdomainCheckResponse,
    TenantRegistrationRequest,
    TenantRegistrationResponse,
    ModuleListResponse,
    AvailableModuleResponse,
)
from app.services.tenant_onboarding_service import TenantOnboardingService


router = APIRouter(tags=["Onboarding"])


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
