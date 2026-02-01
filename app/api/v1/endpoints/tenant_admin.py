"""API endpoints for tenant administration (super admin)."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from typing import Optional

from app.database import get_db
from app.schemas.tenant_admin import (
    TenantListResponse,
    TenantListItem,
    TenantDetailResponse,
    TenantStatusUpdateRequest,
    TenantStatusUpdateResponse,
    PlatformStatistics,
    BillingHistoryResponse,
    BillingHistoryItem
)
from app.services.tenant_admin_service import TenantAdminService

router = APIRouter()

DB = Depends(get_db)


# TODO: Add super admin authentication check
# For now, these endpoints are unprotected for testing
# In production, add: @require_role("SUPER_ADMIN")


@router.get("/tenants", response_model=TenantListResponse)
async def list_tenants(
    status: Optional[str] = Query(None, description="Filter by status"),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: AsyncSession = DB
):
    """
    List all tenants.

    TODO: Requires SUPER_ADMIN role in production.
    """
    service = TenantAdminService(db)

    try:
        tenants, stats = await service.list_all_tenants(
            status_filter=status,
            limit=limit,
            offset=offset
        )

        # Get subscription counts for each tenant
        tenant_items = []
        for tenant in tenants:
            from app.models.tenant import TenantSubscription
            from sqlalchemy import select, func

            # Count subscriptions
            sub_count_query = select(func.count(TenantSubscription.id)).where(
                TenantSubscription.tenant_id == tenant.id,
                TenantSubscription.status == "active"
            )
            sub_count_result = await db.execute(sub_count_query)
            sub_count = int(sub_count_result.scalar() or 0)

            # Sum monthly cost
            cost_query = select(func.sum(TenantSubscription.price_paid)).where(
                TenantSubscription.tenant_id == tenant.id,
                TenantSubscription.status == "active"
            )
            cost_result = await db.execute(cost_query)
            monthly_cost = float(cost_result.scalar() or 0)

            # Get plan name
            plan_name = None
            if tenant.plan_id:
                from app.models.tenant import Plan
                plan_stmt = select(Plan).where(Plan.id == tenant.plan_id)
                plan_result = await db.execute(plan_stmt)
                plan = plan_result.scalar_one_or_none()
                if plan:
                    plan_name = plan.name

            tenant_items.append(TenantListItem(
                id=tenant.id,
                name=tenant.name,
                subdomain=tenant.subdomain,
                status=tenant.status,
                plan_name=plan_name,
                total_subscriptions=sub_count,
                monthly_cost=monthly_cost,
                onboarded_at=tenant.onboarded_at,
                last_active=None  # TODO: Track last activity
            ))

        return TenantListResponse(
            tenants=tenant_items,
            total=stats['total'],
            active=stats['active'],
            pending=stats['pending'],
            suspended=stats['suspended']
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list tenants: {str(e)}")


@router.get("/tenants/{tenant_id}", response_model=TenantDetailResponse)
async def get_tenant_details(
    tenant_id: UUID,
    db: AsyncSession = DB
):
    """
    Get detailed information about a specific tenant.

    TODO: Requires SUPER_ADMIN role in production.
    """
    service = TenantAdminService(db)

    try:
        details = await service.get_tenant_details(tenant_id)
        return TenantDetailResponse(**details)

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get tenant details: {str(e)}")


@router.patch("/tenants/{tenant_id}/status", response_model=TenantStatusUpdateResponse)
async def update_tenant_status(
    tenant_id: UUID,
    data: TenantStatusUpdateRequest,
    db: AsyncSession = DB
):
    """
    Update tenant status (activate, suspend, cancel).

    TODO: Requires SUPER_ADMIN role in production.
    """
    service = TenantAdminService(db)

    try:
        tenant = await service.update_tenant_status(
            tenant_id=tenant_id,
            new_status=data.status,
            reason=data.reason
        )

        return TenantStatusUpdateResponse(
            success=True,
            message=f"Tenant status updated to {data.status}",
            tenant_id=tenant.id,
            new_status=tenant.status
        )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update status: {str(e)}")


@router.get("/statistics", response_model=PlatformStatistics)
async def get_platform_statistics(
    db: AsyncSession = DB
):
    """
    Get platform-wide statistics.

    TODO: Requires SUPER_ADMIN role in production.
    """
    service = TenantAdminService(db)

    try:
        stats = await service.get_platform_statistics()
        return PlatformStatistics(**stats)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get statistics: {str(e)}")


@router.get("/billing", response_model=BillingHistoryResponse)
async def get_billing_history(
    tenant_id: Optional[UUID] = Query(None, description="Filter by tenant"),
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = DB
):
    """
    Get billing history across all tenants or for specific tenant.

    TODO: Requires SUPER_ADMIN role in production.
    """
    service = TenantAdminService(db)

    try:
        billing_records = await service.get_billing_history(
            tenant_id=tenant_id,
            limit=limit
        )

        # Convert to response format
        items = []
        total_revenue = 0
        pending_amount = 0

        for record in billing_records:
            # Get tenant name
            from app.models.tenant import Tenant
            from sqlalchemy import select

            tenant_stmt = select(Tenant).where(Tenant.id == record.tenant_id)
            tenant_result = await db.execute(tenant_stmt)
            tenant = tenant_result.scalar_one_or_none()

            item = BillingHistoryItem(
                id=record.id,
                tenant_id=record.tenant_id,
                tenant_name=tenant.name if tenant else "Unknown",
                invoice_number=record.invoice_number,
                billing_period_start=record.billing_period_start,
                billing_period_end=record.billing_period_end,
                amount=float(record.amount),
                tax_amount=float(record.tax_amount),
                total_amount=float(record.total_amount),
                status=record.status,
                payment_method=record.payment_method,
                paid_at=record.paid_at
            )
            items.append(item)

            if record.status == "paid":
                total_revenue += float(record.total_amount)
            elif record.status == "pending":
                pending_amount += float(record.total_amount)

        return BillingHistoryResponse(
            invoices=items,
            total=len(items),
            total_revenue=total_revenue,
            pending_amount=pending_amount
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get billing history: {str(e)}")
