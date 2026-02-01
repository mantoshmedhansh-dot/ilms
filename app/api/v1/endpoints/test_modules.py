"""
Test endpoints for Phase 1 multi-tenant module access control
"""
from fastapi import APIRouter, Request, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.module_decorators import require_module, get_tenant_enabled_modules
from app.database import get_public_session
from app.core.module_decorators import require_module

router = APIRouter()


@router.get("/test/modules/enabled")
async def get_enabled_modules(
    request: Request,
    db: AsyncSession = Depends(get_public_session)
):
    """
    Get list of enabled modules for current tenant

    This endpoint tests:
    - Tenant middleware extracting tenant from X-Tenant-ID header
    - Database query to fetch tenant subscriptions
    """
    tenant_id = request.state.tenant_id
    modules = await get_tenant_enabled_modules(db, tenant_id)
    return {
        "tenant": request.state.tenant.name,
        "tenant_id": tenant_id,
        "subdomain": request.state.tenant.subdomain,
        "enabled_modules": modules,
        "count": len(modules)
    }


@router.get("/test/modules/oms-allowed")
@require_module("oms_fulfillment")
async def test_oms_module(request: Request):
    """
    Test endpoint - requires oms_fulfillment module

    Should succeed for test tenant (Starter plan includes OMS)
    """
    return {
        "success": True,
        "message": "✅ You have access to OMS, WMS & Fulfillment module!",
        "tenant": request.state.tenant.name,
        "module": "oms_fulfillment"
    }


@router.get("/test/modules/finance-blocked")
@require_module("finance")
async def test_finance_module(request: Request):
    """
    Test endpoint - requires finance module

    Should fail with 403 for test tenant (Starter plan does NOT include Finance)
    """
    return {
        "success": True,
        "message": "✅ You have access to Finance & Accounting module!",
        "tenant": request.state.tenant.name,
        "module": "finance"
    }


@router.get("/test/modules/procurement-blocked")
@require_module("procurement")
async def test_procurement_module(request: Request):
    """
    Test endpoint - requires procurement module

    Should fail with 403 for test tenant (Starter plan does NOT include Procurement)
    """
    return {
        "success": True,
        "message": "✅ You have access to Procurement (P2P) module!",
        "tenant": request.state.tenant.name,
        "module": "procurement"
    }


@router.get("/test/modules/storefront-allowed")
@require_module("d2c_storefront")
async def test_storefront_module(request: Request):
    """
    Test endpoint - requires d2c_storefront module

    Should succeed for test tenant (Starter plan includes D2C Storefront)
    """
    return {
        "success": True,
        "message": "✅ You have access to D2C E-Commerce Storefront module!",
        "tenant": request.state.tenant.name,
        "module": "d2c_storefront"
    }


@router.get("/test/tenant/info")
async def get_tenant_info(request: Request):
    """
    Get current tenant information from request state

    Tests that middleware correctly injects tenant into request
    """
    return {
        "tenant_id": str(request.state.tenant_id),
        "tenant_name": request.state.tenant.name,
        "subdomain": request.state.tenant.subdomain,
        "database_schema": request.state.tenant.database_schema,
        "status": request.state.tenant.status,
        "plan_id": str(request.state.tenant.plan_id) if request.state.tenant.plan_id else None
    }
