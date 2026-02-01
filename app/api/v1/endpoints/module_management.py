"""API endpoints for tenant module management."""

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID

from app.database import get_db
from app.schemas.module_management import (
    ModuleSubscribeRequest,
    ModuleUnsubscribeRequest,
    SubscriptionChangeResponse,
    TenantModulesResponse,
    PricingCalculationRequest,
    PricingCalculationResponse,
    ModuleSubscriptionDetail
)
from app.services.module_management_service import ModuleManagementService
from app.core.module_decorators import require_module

router = APIRouter()

DB = Depends(get_db)


@router.get("/subscriptions", response_model=TenantModulesResponse)
@require_module("system_admin")
async def get_tenant_modules(
    request: Request,
    db: AsyncSession = DB
):
    """
    Get all module subscriptions for current tenant.

    Requires: system_admin module
    """
    tenant_id = request.state.tenant.id
    service = ModuleManagementService(db)

    try:
        tenant, subscriptions = await service.get_tenant_subscriptions(tenant_id)

        # Build subscription details
        subscription_details = []
        total_monthly_cost = 0
        active_count = 0

        for sub in subscriptions:
            # Get module from sub.module relationship (eager loaded)
            from app.models.tenant import ErpModule
            from sqlalchemy import select

            module_stmt = select(ErpModule).where(ErpModule.id == sub.module_id)
            module_result = await db.execute(module_stmt)
            module = module_result.scalar_one()

            detail = ModuleSubscriptionDetail(
                id=sub.id,
                module_id=sub.module_id,
                module_code=module.code,
                module_name=module.name,
                status=sub.status,
                billing_cycle=sub.billing_cycle or "monthly",
                price_paid=float(sub.price_paid or 0),
                starts_at=sub.starts_at,
                expires_at=sub.expires_at,
                is_trial=sub.is_trial,
                trial_ends_at=sub.trial_ends_at,
                auto_renew=sub.auto_renew
            )
            subscription_details.append(detail)

            if sub.status == "active":
                total_monthly_cost += float(sub.price_paid or 0)
                active_count += 1

        return TenantModulesResponse(
            tenant_id=tenant.id,
            tenant_name=tenant.name,
            subscriptions=subscription_details,
            total_modules=len(subscriptions),
            active_modules=active_count,
            total_monthly_cost=total_monthly_cost,
            total_yearly_cost=total_monthly_cost * 12 * 0.8  # 20% yearly discount
        )

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get subscriptions: {str(e)}")


@router.post("/calculate-pricing", response_model=PricingCalculationResponse)
@require_module("system_admin")
async def calculate_pricing(
    data: PricingCalculationRequest,
    request: Request,
    db: AsyncSession = DB
):
    """
    Calculate pricing for adding/removing modules.

    Requires: system_admin module
    """
    tenant_id = request.state.tenant.id
    service = ModuleManagementService(db)

    try:
        result = await service.calculate_pricing(
            tenant_id=tenant_id,
            add_module_codes=data.add_modules,
            remove_module_codes=data.remove_modules,
            billing_cycle=data.billing_cycle
        )

        return PricingCalculationResponse(**result)

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to calculate pricing: {str(e)}")


@router.post("/subscribe", response_model=SubscriptionChangeResponse)
@require_module("system_admin")
async def subscribe_to_modules(
    data: ModuleSubscribeRequest,
    request: Request,
    db: AsyncSession = DB
):
    """
    Subscribe to additional modules.

    Requires: system_admin module
    """
    tenant_id = request.state.tenant.id
    service = ModuleManagementService(db)

    try:
        # Subscribe to modules
        new_subs = await service.subscribe_to_modules(
            tenant_id=tenant_id,
            module_codes=data.module_codes,
            billing_cycle=data.billing_cycle
        )

        # Get updated subscriptions
        tenant, all_subs = await service.get_tenant_subscriptions(tenant_id)

        # Build response
        subscription_details = []
        total_monthly_cost = 0

        for sub in all_subs:
            from app.models.tenant import ErpModule
            from sqlalchemy import select

            module_stmt = select(ErpModule).where(ErpModule.id == sub.module_id)
            module_result = await db.execute(module_stmt)
            module = module_result.scalar_one()

            detail = ModuleSubscriptionDetail(
                id=sub.id,
                module_id=sub.module_id,
                module_code=module.code,
                module_name=module.name,
                status=sub.status,
                billing_cycle=sub.billing_cycle or "monthly",
                price_paid=float(sub.price_paid or 0),
                starts_at=sub.starts_at,
                expires_at=sub.expires_at,
                is_trial=sub.is_trial,
                trial_ends_at=sub.trial_ends_at,
                auto_renew=sub.auto_renew
            )
            subscription_details.append(detail)

            if sub.status == "active":
                total_monthly_cost += float(sub.price_paid or 0)

        return SubscriptionChangeResponse(
            success=True,
            message=f"Successfully subscribed to {len(new_subs)} module(s)",
            subscriptions=subscription_details,
            total_monthly_cost=total_monthly_cost,
            total_yearly_cost=total_monthly_cost * 12 * 0.8,
            changes_applied=len(new_subs)
        )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to subscribe: {str(e)}")


@router.post("/unsubscribe", response_model=SubscriptionChangeResponse)
@require_module("system_admin")
async def unsubscribe_from_modules(
    data: ModuleUnsubscribeRequest,
    request: Request,
    db: AsyncSession = DB
):
    """
    Unsubscribe from modules.

    Requires: system_admin module
    """
    tenant_id = request.state.tenant.id
    service = ModuleManagementService(db)

    try:
        # Unsubscribe
        count = await service.unsubscribe_from_modules(
            tenant_id=tenant_id,
            module_codes=data.module_codes,
            reason=data.reason
        )

        # Get updated subscriptions
        tenant, all_subs = await service.get_tenant_subscriptions(tenant_id)

        # Build response
        subscription_details = []
        total_monthly_cost = 0

        for sub in all_subs:
            from app.models.tenant import ErpModule
            from sqlalchemy import select

            module_stmt = select(ErpModule).where(ErpModule.id == sub.module_id)
            module_result = await db.execute(module_stmt)
            module = module_result.scalar_one()

            detail = ModuleSubscriptionDetail(
                id=sub.id,
                module_id=sub.module_id,
                module_code=module.code,
                module_name=module.name,
                status=sub.status,
                billing_cycle=sub.billing_cycle or "monthly",
                price_paid=float(sub.price_paid or 0),
                starts_at=sub.starts_at,
                expires_at=sub.expires_at,
                is_trial=sub.is_trial,
                trial_ends_at=sub.trial_ends_at,
                auto_renew=sub.auto_renew
            )
            subscription_details.append(detail)

            if sub.status == "active":
                total_monthly_cost += float(sub.price_paid or 0)

        return SubscriptionChangeResponse(
            success=True,
            message=f"Successfully unsubscribed from {count} module(s)",
            subscriptions=subscription_details,
            total_monthly_cost=total_monthly_cost,
            total_yearly_cost=total_monthly_cost * 12 * 0.8,
            changes_applied=count
        )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to unsubscribe: {str(e)}")
