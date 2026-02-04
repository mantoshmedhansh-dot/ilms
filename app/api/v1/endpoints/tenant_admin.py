"""API endpoints for tenant administration (super admin)."""

import logging
from fastapi import APIRouter, Depends, HTTPException, Query

logger = logging.getLogger(__name__)
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


@router.post("/tenants/{tenant_id}/fix-schema")
async def fix_tenant_schema(
    tenant_id: UUID,
    db: AsyncSession = DB
):
    """
    Fix tenant schema by adding missing tables (regions, etc.).

    This endpoint repairs tenant schemas that were created before
    all required tables were added to the schema creation process.

    TODO: Requires SUPER_ADMIN role in production.
    """
    from sqlalchemy import text, select
    from app.models.tenant import Tenant

    try:
        # Get tenant
        tenant_stmt = select(Tenant).where(Tenant.id == tenant_id)
        tenant_result = await db.execute(tenant_stmt)
        tenant = tenant_result.scalar_one_or_none()

        if not tenant:
            raise HTTPException(status_code=404, detail=f"Tenant {tenant_id} not found")

        schema_name = tenant.database_schema
        tables_created = []
        tables_skipped = []

        # Check and create regions table
        check_regions = await db.execute(text(f"""
            SELECT EXISTS (
                SELECT FROM information_schema.tables
                WHERE table_schema = '{schema_name}'
                AND table_name = 'regions'
            )
        """))
        regions_exists = check_regions.scalar()

        if not regions_exists:
            await db.execute(text(f"""
                CREATE TABLE IF NOT EXISTS "{schema_name}".regions (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    name VARCHAR(100) NOT NULL,
                    code VARCHAR(50) UNIQUE NOT NULL,
                    type VARCHAR(20) NOT NULL DEFAULT 'CITY',
                    parent_id UUID REFERENCES "{schema_name}".regions(id) ON DELETE SET NULL,
                    description TEXT,
                    is_active BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMPTZ DEFAULT NOW(),
                    updated_at TIMESTAMPTZ DEFAULT NOW()
                )
            """))
            await db.execute(text(f"""
                CREATE INDEX IF NOT EXISTS idx_regions_code ON "{schema_name}".regions(code);
                CREATE INDEX IF NOT EXISTS idx_regions_parent ON "{schema_name}".regions(parent_id);
            """))
            tables_created.append("regions")
        else:
            tables_skipped.append("regions")

        # Check and create audit_logs table
        check_audit = await db.execute(text(f"""
            SELECT EXISTS (
                SELECT FROM information_schema.tables
                WHERE table_schema = '{schema_name}'
                AND table_name = 'audit_logs'
            )
        """))
        audit_exists = check_audit.scalar()

        if not audit_exists:
            await db.execute(text(f"""
                CREATE TABLE IF NOT EXISTS "{schema_name}".audit_logs (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    user_id UUID REFERENCES "{schema_name}".users(id) ON DELETE SET NULL,
                    action VARCHAR(50) NOT NULL,
                    entity_type VARCHAR(50) NOT NULL,
                    entity_id UUID,
                    old_values JSONB,
                    new_values JSONB,
                    description TEXT,
                    ip_address VARCHAR(50),
                    user_agent VARCHAR(500),
                    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL
                )
            """))
            await db.execute(text(f"""
                CREATE INDEX IF NOT EXISTS idx_audit_action ON "{schema_name}".audit_logs(action);
                CREATE INDEX IF NOT EXISTS idx_audit_entity ON "{schema_name}".audit_logs(entity_type);
                CREATE INDEX IF NOT EXISTS idx_audit_created ON "{schema_name}".audit_logs(created_at);
            """))
            tables_created.append("audit_logs")
        else:
            tables_skipped.append("audit_logs")

        # Check and add missing department column to roles table
        try:
            dept_check = await db.execute(text(f"""
                SELECT 1 FROM information_schema.columns
                WHERE table_schema = '{schema_name}'
                AND table_name = 'roles'
                AND column_name = 'department'
            """))
            dept_exists = dept_check.scalar() is not None

            if not dept_exists:
                await db.execute(text(f"""
                    ALTER TABLE "{schema_name}".roles
                    ADD COLUMN department VARCHAR(50)
                """))
                tables_created.append("roles.department column")
        except Exception as dept_err:
            logger.warning(f"Department column check/add skipped: {dept_err}")

        # Add foreign key to users.region_id if not exists
        # PostgreSQL doesn't support ADD CONSTRAINT IF NOT EXISTS, so check first
        try:
            fk_check = await db.execute(text(f"""
                SELECT 1 FROM information_schema.table_constraints
                WHERE constraint_schema = '{schema_name}'
                AND table_name = 'users'
                AND constraint_name = 'fk_users_region'
            """))
            fk_exists = fk_check.scalar() is not None

            if not fk_exists:
                await db.execute(text(f"""
                    ALTER TABLE "{schema_name}".users
                    ADD CONSTRAINT fk_users_region
                    FOREIGN KEY (region_id) REFERENCES "{schema_name}".regions(id) ON DELETE SET NULL
                """))
        except Exception as fk_err:
            logger.warning(f"FK creation skipped: {fk_err}")

        # Create index on users.region_id if not exists
        try:
            await db.execute(text(f"""
                CREATE INDEX IF NOT EXISTS idx_users_region ON "{schema_name}".users(region_id);
            """))
        except Exception as idx_err:
            logger.warning(f"Index creation skipped: {idx_err}")

        await db.commit()

        return {
            "success": True,
            "tenant_id": str(tenant_id),
            "schema": schema_name,
            "tables_created": tables_created,
            "tables_skipped": tables_skipped,
            "message": f"Schema fix completed. Created: {tables_created}, Skipped (already exist): {tables_skipped}"
        }

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to fix schema: {str(e)}")


@router.post("/tenants/{tenant_id}/reset-admin-password")
async def reset_admin_password(
    tenant_id: UUID,
    new_password: str = Query(..., description="New password for admin"),
    db: AsyncSession = DB
):
    """
    Reset admin user password for a tenant.

    TODO: Requires SUPER_ADMIN role in production.
    """
    from sqlalchemy import text, select
    from app.models.tenant import Tenant
    from app.core.security import get_password_hash

    try:
        # Get tenant
        tenant_stmt = select(Tenant).where(Tenant.id == tenant_id)
        tenant_result = await db.execute(tenant_stmt)
        tenant = tenant_result.scalar_one_or_none()

        if not tenant:
            raise HTTPException(status_code=404, detail=f"Tenant {tenant_id} not found")

        schema_name = tenant.database_schema
        password_hash = get_password_hash(new_password)

        # Update first user's password (admin)
        await db.execute(text(f"""
            UPDATE "{schema_name}".users
            SET password_hash = :password_hash, updated_at = NOW()
            WHERE id = (SELECT id FROM "{schema_name}".users ORDER BY created_at LIMIT 1)
        """), {"password_hash": password_hash})

        await db.commit()

        return {
            "success": True,
            "message": "Admin password reset successfully"
        }

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to reset password: {str(e)}")


@router.get("/tenants/{tenant_id}/users")
async def list_tenant_users(
    tenant_id: UUID,
    db: AsyncSession = DB
):
    """
    List users in a tenant schema (for debugging).

    TODO: Requires SUPER_ADMIN role in production.
    """
    from sqlalchemy import text, select
    from app.models.tenant import Tenant

    try:
        # Get tenant
        tenant_stmt = select(Tenant).where(Tenant.id == tenant_id)
        tenant_result = await db.execute(tenant_stmt)
        tenant = tenant_result.scalar_one_or_none()

        if not tenant:
            raise HTTPException(status_code=404, detail=f"Tenant {tenant_id} not found")

        schema_name = tenant.database_schema

        # Get users from tenant schema
        users_query = await db.execute(text(f"""
            SELECT id, email, first_name, last_name, is_active, is_verified, created_at
            FROM "{schema_name}".users
            ORDER BY created_at DESC
            LIMIT 50
        """))
        users = users_query.fetchall()

        return {
            "tenant_id": str(tenant_id),
            "schema": schema_name,
            "user_count": len(users),
            "users": [
                {
                    "id": str(u[0]),
                    "email": u[1],
                    "first_name": u[2],
                    "last_name": u[3],
                    "is_active": u[4],
                    "is_verified": u[5],
                    "created_at": str(u[6])
                }
                for u in users
            ]
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list users: {str(e)}")
