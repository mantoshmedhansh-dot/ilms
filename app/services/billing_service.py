"""
Billing Service for Razorpay Integration

Handles subscription creation, payment processing, and webhook management.
"""

import uuid
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.tenant import Tenant, TenantSubscription, ErpModule as Module, BillingHistory


class BillingService:
    """Service for managing billing and payments."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_subscription(
        self,
        tenant_id: uuid.UUID,
        module_codes: list[str],
        billing_cycle: str = "monthly"
    ) -> Dict[str, Any]:
        """
        Create billing record for new module subscriptions.

        In production, this would integrate with Razorpay to create actual payment subscription.
        For now, creates billing record and returns payment details.

        Args:
            tenant_id: UUID of the tenant
            module_codes: List of module codes to subscribe to
            billing_cycle: 'monthly' or 'yearly'

        Returns:
            Dict with billing details and subscription info
        """
        # Get tenant
        tenant_result = await self.db.execute(
            select(Tenant).where(Tenant.id == tenant_id)
        )
        tenant = tenant_result.scalar_one_or_none()

        if not tenant:
            raise ValueError(f"Tenant {tenant_id} not found")

        # Get modules and calculate cost
        modules_result = await self.db.execute(
            select(Module).where(Module.code.in_(module_codes))
        )
        modules = modules_result.scalars().all()

        # Calculate total cost
        total_monthly = sum(float(m.price_monthly or 0) for m in modules)
        total_yearly = sum(float(m.price_yearly or 0) for m in modules)

        # Select price based on billing cycle
        if billing_cycle == "yearly":
            total_amount = total_yearly
            billing_period_months = 12
        else:
            total_amount = total_monthly
            billing_period_months = 1

        # Create billing record
        billing_record = BillingHistory(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            invoice_number=self._generate_invoice_number(),
            billing_period_start=datetime.now(timezone.utc),
            billing_period_end=datetime.now(timezone.utc) + timedelta(days=30 * billing_period_months),
            amount=Decimal(str(total_amount)),
            tax_amount=Decimal(str(total_amount * 0.18)),  # 18% GST
            total_amount=Decimal(str(total_amount * 1.18)),
            status='pending',
            invoice_data={
                'modules': [{'code': m.code, 'name': m.name, 'price': float(m.price_monthly)} for m in modules],
                'billing_cycle': billing_cycle,
                'subtotal': total_amount,
                'tax_rate': 0.18,
                'tax_amount': total_amount * 0.18,
                'total': total_amount * 1.18
            }
        )

        self.db.add(billing_record)
        await self.db.commit()
        await self.db.refresh(billing_record)

        # In production, create Razorpay subscription here
        # razorpay_subscription = self._create_razorpay_subscription(tenant, billing_record)

        return {
            'billing_id': str(billing_record.id),
            'invoice_number': billing_record.invoice_number,
            'amount': float(billing_record.amount),
            'tax_amount': float(billing_record.tax_amount),
            'total_amount': float(billing_record.total_amount),
            'status': billing_record.status,
            'billing_cycle': billing_cycle,
            'modules_count': len(modules),
            # 'razorpay_subscription_id': razorpay_subscription['id'],  # Would be set in production
            # 'payment_link': razorpay_subscription['short_url'],  # Would be set in production
        }

    async def handle_payment_webhook(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle Razorpay webhook for payment events.

        Events handled:
        - subscription.charged: Payment successful
        - subscription.cancelled: Subscription cancelled
        - subscription.paused: Subscription paused
        - payment.failed: Payment failed

        Args:
            payload: Webhook payload from Razorpay

        Returns:
            Dict with processing result
        """
        event = payload.get('event')

        if event == 'subscription.charged':
            # Payment successful
            return await self._handle_payment_success(payload)

        elif event == 'subscription.cancelled':
            # Subscription cancelled
            return await self._handle_subscription_cancelled(payload)

        elif event == 'subscription.paused':
            # Subscription paused
            return await self._handle_subscription_paused(payload)

        elif event == 'payment.failed':
            # Payment failed
            return await self._handle_payment_failed(payload)

        else:
            return {'status': 'ignored', 'event': event}

    async def _handle_payment_success(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Mark subscription as paid when payment succeeds."""
        # Extract subscription details from payload
        subscription_data = payload.get('payload', {}).get('subscription', {}).get('entity', {})
        notes = subscription_data.get('notes', {})
        tenant_id = notes.get('tenant_id')

        if not tenant_id:
            return {'status': 'error', 'message': 'Missing tenant_id in webhook payload'}

        # Find pending billing record
        billing_result = await self.db.execute(
            select(BillingHistory)
            .where(
                BillingHistory.tenant_id == uuid.UUID(tenant_id),
                BillingHistory.status == 'pending'
            )
            .order_by(BillingHistory.created_at.desc())
        )
        billing_record = billing_result.scalar_one_or_none()

        if billing_record:
            billing_record.status = 'paid'
            billing_record.paid_at = datetime.now(timezone.utc)
            billing_record.payment_transaction_id = subscription_data.get('id')
            await self.db.commit()

            return {
                'status': 'success',
                'message': f'Payment recorded for tenant {tenant_id}',
                'invoice_number': billing_record.invoice_number
            }

        return {'status': 'error', 'message': 'No pending billing record found'}

    async def _handle_subscription_cancelled(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Suspend tenant subscriptions when Razorpay subscription is cancelled."""
        subscription_data = payload.get('payload', {}).get('subscription', {}).get('entity', {})
        notes = subscription_data.get('notes', {})
        tenant_id = notes.get('tenant_id')

        if not tenant_id:
            return {'status': 'error', 'message': 'Missing tenant_id in webhook payload'}

        # Update all active tenant subscriptions to 'suspended'
        subscriptions_result = await self.db.execute(
            select(TenantSubscription)
            .where(
                TenantSubscription.tenant_id == uuid.UUID(tenant_id),
                TenantSubscription.status == 'active'
            )
        )
        subscriptions = subscriptions_result.scalars().all()

        for subscription in subscriptions:
            subscription.status = 'suspended'
            subscription.ends_at = datetime.now(timezone.utc)

        await self.db.commit()

        return {
            'status': 'success',
            'message': f'Suspended {len(subscriptions)} subscriptions for tenant {tenant_id}'
        }

    async def _handle_subscription_paused(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Handle subscription pause event."""
        # Similar to cancellation but with 'paused' status
        subscription_data = payload.get('payload', {}).get('subscription', {}).get('entity', {})
        notes = subscription_data.get('notes', {})
        tenant_id = notes.get('tenant_id')

        if not tenant_id:
            return {'status': 'error', 'message': 'Missing tenant_id in webhook payload'}

        # Update tenant status to paused
        tenant_result = await self.db.execute(
            select(Tenant).where(Tenant.id == uuid.UUID(tenant_id))
        )
        tenant = tenant_result.scalar_one_or_none()

        if tenant:
            tenant.status = 'suspended'
            await self.db.commit()

            return {
                'status': 'success',
                'message': f'Paused tenant {tenant_id}'
            }

        return {'status': 'error', 'message': 'Tenant not found'}

    async def _handle_payment_failed(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Handle payment failure event."""
        payment_data = payload.get('payload', {}).get('payment', {}).get('entity', {})
        notes = payment_data.get('notes', {})
        tenant_id = notes.get('tenant_id')

        if not tenant_id:
            return {'status': 'error', 'message': 'Missing tenant_id in webhook payload'}

        # Find billing record and mark as failed
        billing_result = await self.db.execute(
            select(BillingHistory)
            .where(
                BillingHistory.tenant_id == uuid.UUID(tenant_id),
                BillingHistory.status == 'pending'
            )
            .order_by(BillingHistory.created_at.desc())
        )
        billing_record = billing_result.scalar_one_or_none()

        if billing_record:
            billing_record.status = 'failed'
            await self.db.commit()

            # TODO: Send payment failure notification email

            return {
                'status': 'success',
                'message': f'Marked payment as failed for tenant {tenant_id}',
                'invoice_number': billing_record.invoice_number
            }

        return {'status': 'error', 'message': 'No pending billing record found'}

    def _generate_invoice_number(self) -> str:
        """Generate unique invoice number."""
        # Format: INV-YYYYMMDD-XXXXX
        date_part = datetime.now(timezone.utc).strftime('%Y%m%d')
        random_part = str(uuid.uuid4())[:8].upper()
        return f"INV-{date_part}-{random_part}"

    async def get_billing_history(
        self,
        tenant_id: uuid.UUID,
        limit: int = 50
    ) -> list[BillingHistory]:
        """
        Get billing history for a tenant.

        Args:
            tenant_id: UUID of the tenant
            limit: Maximum number of records to return

        Returns:
            List of billing history records
        """
        result = await self.db.execute(
            select(BillingHistory)
            .where(BillingHistory.tenant_id == tenant_id)
            .order_by(BillingHistory.created_at.desc())
            .limit(limit)
        )

        return list(result.scalars().all())

    async def get_current_billing_amount(self, tenant_id: uuid.UUID) -> Decimal:
        """
        Calculate current monthly billing amount for a tenant.

        Args:
            tenant_id: UUID of the tenant

        Returns:
            Total monthly cost of all active subscriptions
        """
        # Get all active subscriptions
        subscriptions_result = await self.db.execute(
            select(TenantSubscription, Module)
            .join(Module, TenantSubscription.module_id == Module.id)
            .where(
                TenantSubscription.tenant_id == tenant_id,
                TenantSubscription.status == 'active'
            )
        )

        total = Decimal('0')
        for subscription, module in subscriptions_result:
            total += Decimal(str(module.price_monthly or 0))

        return total
