"""
Subscription Lifecycle Management Service

Handles subscription expiry, renewal reminders, and automatic renewals.
Run as daily cron job.
"""

import uuid
from datetime import datetime, timezone, timedelta
from typing import List

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.tenant import Tenant
from app.models.module import TenantSubscription, Module
from app.models.billing import BillingHistory


class SubscriptionLifecycleService:
    """Service for managing subscription lifecycle events."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def check_expiring_subscriptions(self, days: int = 7) -> List[dict]:
        """
        Check for subscriptions expiring in the next N days and send reminders.

        Args:
            days: Number of days ahead to check for expiring subscriptions

        Returns:
            List of tenants with expiring subscriptions
        """
        cutoff_date = datetime.now(timezone.utc) + timedelta(days=days)
        current_date = datetime.now(timezone.utc)

        # Find subscriptions expiring within the next N days
        result = await self.db.execute(
            select(TenantSubscription, Tenant, Module)
            .join(Tenant, TenantSubscription.tenant_id == Tenant.id)
            .join(Module, TenantSubscription.module_id == Module.id)
            .where(
                and_(
                    TenantSubscription.status == 'active',
                    TenantSubscription.ends_at.isnot(None),
                    TenantSubscription.ends_at > current_date,
                    TenantSubscription.ends_at <= cutoff_date
                )
            )
        )

        expiring_subscriptions = []
        for subscription, tenant, module in result:
            expiring_subscriptions.append({
                'tenant_id': str(tenant.id),
                'tenant_name': tenant.name,
                'tenant_email': tenant.settings.get('admin_email', ''),
                'module_code': module.code,
                'module_name': module.name,
                'expires_at': subscription.ends_at.isoformat(),
                'days_remaining': (subscription.ends_at - current_date).days
            })

        # TODO: Send renewal reminder emails
        # for item in expiring_subscriptions:
        #     await send_renewal_reminder_email(item)

        return expiring_subscriptions

    async def suspend_expired_subscriptions(self) -> List[dict]:
        """
        Suspend subscriptions that have expired.

        Returns:
            List of suspended subscriptions
        """
        current_date = datetime.now(timezone.utc)

        # Find expired subscriptions
        result = await self.db.execute(
            select(TenantSubscription, Tenant, Module)
            .join(Tenant, TenantSubscription.tenant_id == Tenant.id)
            .join(Module, TenantSubscription.module_id == Module.id)
            .where(
                and_(
                    TenantSubscription.status == 'active',
                    TenantSubscription.ends_at.isnot(None),
                    TenantSubscription.ends_at <= current_date
                )
            )
        )

        suspended_subscriptions = []
        for subscription, tenant, module in result:
            # Update subscription status to expired
            subscription.status = 'expired'

            suspended_subscriptions.append({
                'tenant_id': str(tenant.id),
                'tenant_name': tenant.name,
                'module_code': module.code,
                'module_name': module.name,
                'expired_at': subscription.ends_at.isoformat()
            })

        if suspended_subscriptions:
            await self.db.commit()

            # TODO: Send expiry notification emails
            # for item in suspended_subscriptions:
            #     await send_expiry_notification_email(item)

        return suspended_subscriptions

    async def check_tenant_subscription_status(self, tenant_id: uuid.UUID) -> dict:
        """
        Check overall subscription status for a tenant.

        If all subscriptions have expired, suspend the tenant account.

        Args:
            tenant_id: UUID of the tenant

        Returns:
            Dict with tenant subscription status
        """
        # Get all subscriptions for the tenant
        result = await self.db.execute(
            select(TenantSubscription)
            .where(TenantSubscription.tenant_id == tenant_id)
        )
        subscriptions = list(result.scalars().all())

        if not subscriptions:
            return {
                'tenant_id': str(tenant_id),
                'status': 'no_subscriptions',
                'action': 'none'
            }

        # Count active vs expired
        active_count = sum(1 for s in subscriptions if s.status == 'active')
        expired_count = sum(1 for s in subscriptions if s.status in ('expired', 'cancelled'))

        # If all subscriptions are expired, suspend tenant
        if active_count == 0 and expired_count > 0:
            tenant_result = await self.db.execute(
                select(Tenant).where(Tenant.id == tenant_id)
            )
            tenant = tenant_result.scalar_one_or_none()

            if tenant and tenant.status == 'active':
                tenant.status = 'suspended'
                await self.db.commit()

                # TODO: Send tenant suspension notification
                # await send_tenant_suspension_email(tenant)

                return {
                    'tenant_id': str(tenant_id),
                    'status': 'suspended',
                    'action': 'tenant_suspended',
                    'message': 'All subscriptions expired, tenant suspended'
                }

        return {
            'tenant_id': str(tenant_id),
            'status': 'active',
            'active_subscriptions': active_count,
            'expired_subscriptions': expired_count,
            'action': 'none'
        }

    async def auto_renew_subscriptions(self) -> List[dict]:
        """
        Auto-renew subscriptions with auto_renew flag enabled.

        This would integrate with payment gateway to charge for renewal.

        Returns:
            List of renewed subscriptions
        """
        current_date = datetime.now(timezone.utc)
        renewal_window = current_date + timedelta(days=3)  # Renew 3 days before expiry

        # Find subscriptions eligible for auto-renewal
        result = await self.db.execute(
            select(TenantSubscription, Tenant, Module)
            .join(Tenant, TenantSubscription.tenant_id == Tenant.id)
            .join(Module, TenantSubscription.module_id == Module.id)
            .where(
                and_(
                    TenantSubscription.status == 'active',
                    TenantSubscription.ends_at.isnot(None),
                    TenantSubscription.ends_at <= renewal_window,
                    TenantSubscription.ends_at > current_date,
                    # Would check auto_renew flag here if it existed
                )
            )
        )

        renewed_subscriptions = []
        for subscription, tenant, module in result:
            # In production, charge payment here via Razorpay
            # payment_result = await charge_renewal_payment(tenant, module)

            # Extend subscription by 30 days (or 365 for yearly)
            subscription.ends_at = subscription.ends_at + timedelta(days=30)

            # Create billing record
            billing_record = BillingHistory(
                id=uuid.uuid4(),
                tenant_id=tenant.id,
                invoice_number=self._generate_invoice_number(),
                billing_period_start=subscription.ends_at - timedelta(days=30),
                billing_period_end=subscription.ends_at,
                amount=module.price_monthly,
                tax_amount=module.price_monthly * 0.18,
                total_amount=module.price_monthly * 1.18,
                status='pending',  # Would be 'paid' after successful payment
                invoice_data={
                    'type': 'renewal',
                    'module_code': module.code,
                    'module_name': module.name
                }
            )
            self.db.add(billing_record)

            renewed_subscriptions.append({
                'tenant_id': str(tenant.id),
                'tenant_name': tenant.name,
                'module_code': module.code,
                'module_name': module.name,
                'new_expiry_date': subscription.ends_at.isoformat(),
                'invoice_number': billing_record.invoice_number
            })

        if renewed_subscriptions:
            await self.db.commit()

            # TODO: Send renewal confirmation emails
            # for item in renewed_subscriptions:
            #     await send_renewal_confirmation_email(item)

        return renewed_subscriptions

    async def get_subscription_metrics(self) -> dict:
        """
        Get platform-wide subscription metrics.

        Returns:
            Dict with subscription statistics
        """
        current_date = datetime.now(timezone.utc)

        # Total active subscriptions
        active_result = await self.db.execute(
            select(TenantSubscription)
            .where(TenantSubscription.status == 'active')
        )
        total_active = len(list(active_result.scalars().all()))

        # Expiring in 7 days
        cutoff_7_days = current_date + timedelta(days=7)
        expiring_result = await self.db.execute(
            select(TenantSubscription)
            .where(
                and_(
                    TenantSubscription.status == 'active',
                    TenantSubscription.ends_at.isnot(None),
                    TenantSubscription.ends_at <= cutoff_7_days,
                    TenantSubscription.ends_at > current_date
                )
            )
        )
        expiring_7_days = len(list(expiring_result.scalars().all()))

        # Expired
        expired_result = await self.db.execute(
            select(TenantSubscription)
            .where(TenantSubscription.status.in_(['expired', 'cancelled']))
        )
        total_expired = len(list(expired_result.scalars().all()))

        # Active tenants
        active_tenants_result = await self.db.execute(
            select(Tenant)
            .where(Tenant.status == 'active')
        )
        active_tenants = len(list(active_tenants_result.scalars().all()))

        # Suspended tenants
        suspended_tenants_result = await self.db.execute(
            select(Tenant)
            .where(Tenant.status == 'suspended')
        )
        suspended_tenants = len(list(suspended_tenants_result.scalars().all()))

        return {
            'subscriptions': {
                'active': total_active,
                'expiring_in_7_days': expiring_7_days,
                'expired': total_expired
            },
            'tenants': {
                'active': active_tenants,
                'suspended': suspended_tenants,
                'total': active_tenants + suspended_tenants
            },
            'timestamp': current_date.isoformat()
        }

    def _generate_invoice_number(self) -> str:
        """Generate unique invoice number."""
        date_part = datetime.now(timezone.utc).strftime('%Y%m%d')
        random_part = str(uuid.uuid4())[:8].upper()
        return f"INV-{date_part}-{random_part}"


# Cron job functions to be called by scheduler

async def daily_subscription_check(db: AsyncSession):
    """
    Daily cron job to check subscriptions.

    Should be run once per day to:
    - Send renewal reminders for subscriptions expiring in 7 days
    - Suspend expired subscriptions
    - Check tenant overall status
    """
    service = SubscriptionLifecycleService(db)

    print("=" * 60)
    print(f"CRON: Daily Subscription Check - {datetime.now(timezone.utc)}")
    print("=" * 60)

    # Check expiring subscriptions
    expiring = await service.check_expiring_subscriptions(days=7)
    print(f"Found {len(expiring)} subscriptions expiring in 7 days")
    for item in expiring:
        print(f"  - {item['tenant_name']}: {item['module_name']} expires in {item['days_remaining']} days")

    # Suspend expired subscriptions
    expired = await service.suspend_expired_subscriptions()
    print(f"\nSuspended {len(expired)} expired subscriptions")
    for item in expired:
        print(f"  - {item['tenant_name']}: {item['module_name']} expired")

    # Get overall metrics
    metrics = await service.get_subscription_metrics()
    print(f"\nPlatform Metrics:")
    print(f"  Active Subscriptions: {metrics['subscriptions']['active']}")
    print(f"  Expiring in 7 Days: {metrics['subscriptions']['expiring_in_7_days']}")
    print(f"  Expired: {metrics['subscriptions']['expired']}")
    print(f"  Active Tenants: {metrics['tenants']['active']}")
    print(f"  Suspended Tenants: {metrics['tenants']['suspended']}")

    print("=" * 60)
