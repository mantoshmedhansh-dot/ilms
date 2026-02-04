"""Service for tenant administration (super admin operations)."""

import uuid
from datetime import datetime, timezone
from typing import List, Tuple, Optional
from sqlalchemy import select, func, and_, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.tenant import Tenant, ErpModule, TenantSubscription, BillingHistory, UsageMetric


class TenantAdminService:
    """Service for super admin tenant management operations."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_all_tenants(
        self,
        status_filter: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> Tuple[List[Tenant], dict]:
        """
        List all tenants with filtering.

        Args:
            status_filter: Filter by status (active, pending, suspended)
            limit: Max results
            offset: Pagination offset

        Returns:
            (tenants, stats)
        """
        # Build query
        query = select(Tenant)

        if status_filter:
            query = query.where(Tenant.status == status_filter)

        query = query.order_by(desc(Tenant.created_at)).limit(limit).offset(offset)

        # Execute query
        result = await self.db.execute(query)
        tenants = list(result.scalars().all())

        # Get statistics
        from sqlalchemy import case
        stats_query = select(
            func.count(Tenant.id).label('total'),
            func.sum(case((Tenant.status == 'active', 1), else_=0)).label('active'),
            func.sum(case((Tenant.status == 'pending', 1), else_=0)).label('pending'),
            func.sum(case((Tenant.status == 'suspended', 1), else_=0)).label('suspended')
        )
        stats_result = await self.db.execute(stats_query)
        stats_row = stats_result.first()

        stats = {
            'total': int(stats_row.total or 0),
            'active': int(stats_row.active or 0),
            'pending': int(stats_row.pending or 0),
            'suspended': int(stats_row.suspended or 0)
        }

        return tenants, stats

    async def get_tenant_details(self, tenant_id: uuid.UUID) -> dict:
        """
        Get detailed tenant information.

        Args:
            tenant_id: Tenant UUID

        Returns:
            Dictionary with tenant details
        """
        # Get tenant
        tenant_stmt = select(Tenant).where(Tenant.id == tenant_id)
        tenant_result = await self.db.execute(tenant_stmt)
        tenant = tenant_result.scalar_one_or_none()

        if not tenant:
            raise ValueError(f"Tenant {tenant_id} not found")

        # Get subscriptions
        subs_stmt = (
            select(TenantSubscription)
            .where(TenantSubscription.tenant_id == tenant_id)
            .order_by(TenantSubscription.created_at)
        )
        subs_result = await self.db.execute(subs_stmt)
        subscriptions = list(subs_result.scalars().all())

        # Calculate total cost
        total_monthly_cost = sum(
            float(sub.price_paid or 0)
            for sub in subscriptions
            if sub.status == "active"
        )

        # Get subscription details with module names
        subscription_details = []
        for sub in subscriptions:
            module_stmt = select(ErpModule).where(ErpModule.id == sub.module_id)
            module_result = await self.db.execute(module_stmt)
            module = module_result.scalar_one_or_none()

            if module:
                subscription_details.append({
                    "module_code": module.code,
                    "module_name": module.name,
                    "status": sub.status,
                    "price_paid": float(sub.price_paid or 0),
                    "starts_at": sub.starts_at,
                    "billing_cycle": sub.billing_cycle
                })

        # Get plan name if applicable
        plan_name = None
        if tenant.plan_id:
            from app.models.tenant import Plan
            plan_stmt = select(Plan).where(Plan.id == tenant.plan_id)
            plan_result = await self.db.execute(plan_stmt)
            plan = plan_result.scalar_one_or_none()
            if plan:
                plan_name = plan.name

        return {
            "id": tenant.id,
            "name": tenant.name,
            "subdomain": tenant.subdomain,
            "database_schema": tenant.database_schema,
            "status": tenant.status,
            "plan_id": tenant.plan_id,
            "plan_name": plan_name,
            "onboarded_at": tenant.onboarded_at,
            "trial_ends_at": tenant.trial_ends_at,
            "settings": tenant.settings,
            "tenant_metadata": tenant.tenant_metadata,
            "subscriptions": subscription_details,
            "total_monthly_cost": total_monthly_cost,
            "total_users": 0,  # TODO: Query user count from tenant schema
            "storage_used_mb": None,  # TODO: Calculate storage
            "api_calls_monthly": None  # TODO: Query from usage metrics
        }

    async def update_tenant_status(
        self,
        tenant_id: uuid.UUID,
        new_status: str,
        reason: Optional[str] = None
    ) -> Tenant:
        """
        Update tenant status.

        Args:
            tenant_id: Tenant UUID
            new_status: New status (active, suspended, cancelled)
            reason: Reason for change

        Returns:
            Updated tenant
        """
        valid_statuses = ["active", "pending", "suspended", "cancelled"]
        if new_status not in valid_statuses:
            raise ValueError(f"Invalid status. Must be one of: {valid_statuses}")

        # Get tenant
        tenant_stmt = select(Tenant).where(Tenant.id == tenant_id)
        tenant_result = await self.db.execute(tenant_stmt)
        tenant = tenant_result.scalar_one_or_none()

        if not tenant:
            raise ValueError(f"Tenant {tenant_id} not found")

        # Update status
        old_status = tenant.status
        tenant.status = new_status
        tenant.updated_at = datetime.now(timezone.utc)

        # Record status change in metadata
        if "status_history" not in tenant.tenant_metadata:
            tenant.tenant_metadata["status_history"] = []

        tenant.tenant_metadata["status_history"].append({
            "from": old_status,
            "to": new_status,
            "reason": reason,
            "changed_at": datetime.now(timezone.utc).isoformat()
        })

        await self.db.commit()
        await self.db.refresh(tenant)

        return tenant

    async def get_platform_statistics(self) -> dict:
        """
        Get platform-wide statistics.

        Returns:
            Dictionary with platform stats
        """
        # Tenant counts
        from sqlalchemy import case
        tenant_stats = select(
            func.count(Tenant.id).label('total'),
            func.sum(case((Tenant.status == 'active', 1), else_=0)).label('active'),
            func.sum(case((Tenant.status == 'pending', 1), else_=0)).label('pending'),
            func.sum(case((Tenant.status == 'suspended', 1), else_=0)).label('suspended')
        )
        tenant_result = await self.db.execute(tenant_stats)
        tenant_row = tenant_result.first()

        # Revenue calculation
        revenue_query = select(
            func.sum(TenantSubscription.price_paid)
        ).where(TenantSubscription.status == 'active')
        revenue_result = await self.db.execute(revenue_query)
        monthly_revenue = float(revenue_result.scalar() or 0)

        # Module popularity
        module_popularity = select(
            ErpModule.code,
            ErpModule.name,
            func.count(TenantSubscription.id).label('subscription_count')
        ).join(
            TenantSubscription,
            ErpModule.id == TenantSubscription.module_id
        ).where(
            TenantSubscription.status == 'active'
        ).group_by(
            ErpModule.id, ErpModule.code, ErpModule.name
        ).order_by(
            desc('subscription_count')
        ).limit(5)

        module_result = await self.db.execute(module_popularity)
        popular_modules = [
            {"code": row.code, "name": row.name, "subscriptions": row.subscription_count}
            for row in module_result
        ]

        # Average modules per tenant
        active_tenants = int(tenant_row.active or 1)  # Avoid division by zero
        total_subs = select(func.count(TenantSubscription.id)).where(
            TenantSubscription.status == 'active'
        )
        subs_result = await self.db.execute(total_subs)
        total_subscriptions = int(subs_result.scalar() or 0)
        avg_modules = total_subscriptions / active_tenants if active_tenants > 0 else 0

        return {
            "total_tenants": int(tenant_row.total or 0),
            "active_tenants": int(tenant_row.active or 0),
            "pending_tenants": int(tenant_row.pending or 0),
            "suspended_tenants": int(tenant_row.suspended or 0),
            "total_revenue_monthly": monthly_revenue,
            "total_revenue_yearly": monthly_revenue * 12 * 0.8,  # With yearly discount
            "total_users": 0,  # TODO: Aggregate from all tenant schemas
            "avg_modules_per_tenant": round(avg_modules, 2),
            "most_popular_modules": popular_modules,
            "growth_rate": None  # TODO: Calculate growth rate
        }

    async def get_billing_history(
        self,
        tenant_id: Optional[uuid.UUID] = None,
        limit: int = 100
    ) -> List[BillingHistory]:
        """
        Get billing history.

        Args:
            tenant_id: Filter by tenant (optional)
            limit: Max results

        Returns:
            List of billing records
        """
        query = select(BillingHistory).order_by(desc(BillingHistory.created_at)).limit(limit)

        if tenant_id:
            query = query.where(BillingHistory.tenant_id == tenant_id)

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def delete_tenant(
        self,
        tenant_id: uuid.UUID,
        drop_schema: bool = True,
        reason: Optional[str] = None
    ) -> dict:
        """
        Delete a tenant and optionally drop their database schema.

        WARNING: This is a destructive operation and cannot be undone.

        Args:
            tenant_id: Tenant UUID
            drop_schema: Whether to drop the tenant's database schema
            reason: Reason for deletion

        Returns:
            Dictionary with deletion status
        """
        # Get tenant
        tenant_stmt = select(Tenant).where(Tenant.id == tenant_id)
        tenant_result = await self.db.execute(tenant_stmt)
        tenant = tenant_result.scalar_one_or_none()

        if not tenant:
            raise ValueError(f"Tenant {tenant_id} not found")

        schema_name = tenant.database_schema
        subdomain = tenant.subdomain

        # Drop the schema if requested
        schema_dropped = False
        if drop_schema and schema_name:
            from app.services.tenant_schema_service import TenantSchemaService
            schema_service = TenantSchemaService(self.db)
            try:
                await schema_service.drop_tenant_schema(schema_name)
                schema_dropped = True
            except Exception as e:
                # Log but continue with tenant deletion
                import logging
                logging.getLogger(__name__).error(f"Failed to drop schema {schema_name}: {e}")

        # Delete subscriptions first (foreign key constraint)
        from sqlalchemy import delete
        await self.db.execute(
            delete(TenantSubscription).where(TenantSubscription.tenant_id == tenant_id)
        )

        # Delete billing history
        await self.db.execute(
            delete(BillingHistory).where(BillingHistory.tenant_id == tenant_id)
        )

        # Delete usage metrics
        await self.db.execute(
            delete(UsageMetric).where(UsageMetric.tenant_id == tenant_id)
        )

        # Delete feature flags
        from app.models.tenant import FeatureFlag
        await self.db.execute(
            delete(FeatureFlag).where(FeatureFlag.tenant_id == tenant_id)
        )

        # Delete the tenant
        await self.db.delete(tenant)
        await self.db.commit()

        return {
            "success": True,
            "tenant_id": str(tenant_id),
            "subdomain": subdomain,
            "schema_dropped": schema_dropped,
            "reason": reason,
            "message": f"Tenant '{subdomain}' deleted successfully"
        }
