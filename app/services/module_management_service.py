"""Service for managing tenant module subscriptions."""

import uuid
from datetime import datetime, timezone
from typing import List, Tuple, Optional
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.tenant import Tenant, ErpModule, TenantSubscription


class ModuleManagementService:
    """Service for tenant module subscription management."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_tenant_subscriptions(
        self,
        tenant_id: uuid.UUID
    ) -> Tuple[Tenant, List[TenantSubscription]]:
        """
        Get tenant and all their module subscriptions.

        Args:
            tenant_id: Tenant UUID

        Returns:
            (tenant, subscriptions)
        """
        # Get tenant
        tenant_stmt = select(Tenant).where(Tenant.id == tenant_id)
        tenant_result = await self.db.execute(tenant_stmt)
        tenant = tenant_result.scalar_one_or_none()

        if not tenant:
            raise ValueError(f"Tenant {tenant_id} not found")

        # Get subscriptions with module details
        subs_stmt = (
            select(TenantSubscription)
            .where(TenantSubscription.tenant_id == tenant_id)
            .order_by(TenantSubscription.created_at)
        )
        subs_result = await self.db.execute(subs_stmt)
        subscriptions = list(subs_result.scalars().all())

        return tenant, subscriptions

    async def calculate_pricing(
        self,
        tenant_id: uuid.UUID,
        add_module_codes: Optional[List[str]] = None,
        remove_module_codes: Optional[List[str]] = None,
        billing_cycle: str = "monthly"
    ) -> dict:
        """
        Calculate pricing for module changes.

        Args:
            tenant_id: Tenant UUID
            add_module_codes: Modules to add
            remove_module_codes: Modules to remove
            billing_cycle: Billing cycle (monthly or yearly)

        Returns:
            Dictionary with pricing details
        """
        add_module_codes = add_module_codes or []
        remove_module_codes = remove_module_codes or []

        # Get current subscriptions
        _, current_subs = await self.get_tenant_subscriptions(tenant_id)
        current_module_codes = []
        for sub in current_subs:
            # Get module for subscription
            module_stmt = select(ErpModule).where(ErpModule.id == sub.module_id)
            module_result = await self.db.execute(module_stmt)
            module = module_result.scalar_one_or_none()
            if module and sub.status == "active":
                current_module_codes.append(module.code)

        # Calculate current cost (convert to float)
        current_cost = float(sum(sub.price_paid for sub in current_subs if sub.status == "active"))

        # Get modules to add
        if add_module_codes:
            add_stmt = select(ErpModule).where(
                ErpModule.code.in_(add_module_codes),
                ErpModule.is_active == True
            )
            add_result = await self.db.execute(add_stmt)
            add_modules = list(add_result.scalars().all())
            add_cost = sum(float(m.price_monthly or 0) for m in add_modules)
        else:
            add_cost = 0.0

        # Get modules to remove
        if remove_module_codes:
            remove_stmt = select(ErpModule).where(
                ErpModule.code.in_(remove_module_codes),
                ErpModule.is_active == True
            )
            remove_result = await self.db.execute(remove_stmt)
            remove_modules = list(remove_result.scalars().all())
            remove_cost = sum(float(m.price_monthly or 0) for m in remove_modules)
        else:
            remove_cost = 0.0

        new_monthly_cost = current_cost + add_cost - remove_cost
        difference = new_monthly_cost - current_cost

        result = {
            "current_monthly_cost": float(current_cost),
            "new_monthly_cost": float(new_monthly_cost),
            "difference": float(difference),
            "modules_to_add": add_module_codes,
            "modules_to_remove": remove_module_codes,
            "billing_cycle": billing_cycle
        }

        if billing_cycle == "yearly":
            result["yearly_cost"] = new_monthly_cost * 12 * 0.8  # 20% discount
            result["savings_yearly"] = new_monthly_cost * 12 * 0.2

        return result

    async def subscribe_to_modules(
        self,
        tenant_id: uuid.UUID,
        module_codes: List[str],
        billing_cycle: str = "monthly"
    ) -> List[TenantSubscription]:
        """
        Subscribe tenant to additional modules.

        Args:
            tenant_id: Tenant UUID
            module_codes: Module codes to subscribe to
            billing_cycle: Billing cycle

        Returns:
            List of created subscriptions
        """
        # Validate tenant exists
        tenant_stmt = select(Tenant).where(Tenant.id == tenant_id)
        tenant_result = await self.db.execute(tenant_stmt)
        tenant = tenant_result.scalar_one_or_none()
        if not tenant:
            raise ValueError(f"Tenant {tenant_id} not found")

        # Get current subscriptions
        current_stmt = select(TenantSubscription).where(
            TenantSubscription.tenant_id == tenant_id,
            TenantSubscription.status == "active"
        )
        current_result = await self.db.execute(current_stmt)
        current_subs = list(current_result.scalars().all())

        # Get currently subscribed module IDs
        current_module_ids = {sub.module_id for sub in current_subs}

        # Get modules to subscribe
        modules_stmt = select(ErpModule).where(
            ErpModule.code.in_(module_codes),
            ErpModule.is_active == True
        )
        modules_result = await self.db.execute(modules_stmt)
        modules = list(modules_result.scalars().all())

        if not modules:
            raise ValueError("No valid modules found")

        # Check for already subscribed modules
        already_subscribed = [m.code for m in modules if m.id in current_module_ids]
        if already_subscribed:
            raise ValueError(f"Already subscribed to: {', '.join(already_subscribed)}")

        # Create new subscriptions
        new_subscriptions = []
        starts_at = datetime.now(timezone.utc)

        for module in modules:
            subscription = TenantSubscription(
                id=uuid.uuid4(),
                tenant_id=tenant_id,
                module_id=module.id,
                status="active",
                billing_cycle=billing_cycle,
                price_paid=float(module.price_monthly or 0),
                starts_at=starts_at,
                expires_at=None,
                is_trial=False,
                auto_renew=True
            )
            new_subscriptions.append(subscription)
            self.db.add(subscription)

        await self.db.commit()

        return new_subscriptions

    async def unsubscribe_from_modules(
        self,
        tenant_id: uuid.UUID,
        module_codes: List[str],
        reason: Optional[str] = None
    ) -> int:
        """
        Unsubscribe tenant from modules.

        Args:
            tenant_id: Tenant UUID
            module_codes: Module codes to unsubscribe from
            reason: Reason for unsubscribing

        Returns:
            Number of subscriptions cancelled
        """
        # Get modules by code
        modules_stmt = select(ErpModule).where(ErpModule.code.in_(module_codes))
        modules_result = await self.db.execute(modules_stmt)
        modules = list(modules_result.scalars().all())
        module_ids = [m.id for m in modules]

        # Get active subscriptions for these modules
        subs_stmt = select(TenantSubscription).where(
            and_(
                TenantSubscription.tenant_id == tenant_id,
                TenantSubscription.module_id.in_(module_ids),
                TenantSubscription.status == "active"
            )
        )
        subs_result = await self.db.execute(subs_stmt)
        subscriptions = list(subs_result.scalars().all())

        if not subscriptions:
            raise ValueError("No active subscriptions found for these modules")

        # Check if trying to unsubscribe from base module
        base_modules = [m.code for m in modules if m.is_base_module]
        if base_modules:
            raise ValueError(f"Cannot unsubscribe from base modules: {', '.join(base_modules)}")

        # Cancel subscriptions
        count = 0
        now = datetime.now(timezone.utc)

        for sub in subscriptions:
            sub.status = "cancelled"
            sub.expires_at = now
            sub.auto_renew = False
            if reason:
                sub.settings["cancellation_reason"] = reason
                sub.settings["cancelled_at"] = now.isoformat()
            count += 1

        await self.db.commit()

        return count
