"""
Subscription Billing API Endpoints

Provides subscription billing history, current costs, and webhook handling for payment gateway.
"""

from typing import List
from fastapi import APIRouter, HTTPException, Request, Header
from pydantic import BaseModel
from datetime import datetime

from app.api.deps import DB
from app.services.billing_service import BillingService


router = APIRouter(tags=["Subscription Billing"])


# ==================== Schemas ====================

class BillingHistoryResponse(BaseModel):
    """Billing history item response."""
    id: str
    invoice_number: str
    billing_period_start: datetime
    billing_period_end: datetime
    amount: float
    tax_amount: float
    total_amount: float
    status: str
    payment_method: str | None
    payment_transaction_id: str | None
    paid_at: datetime | None
    due_date: datetime | None
    created_at: datetime


class CurrentBillingResponse(BaseModel):
    """Current billing amount response."""
    tenant_id: str
    monthly_cost: float
    yearly_cost: float
    active_modules_count: int
    billing_cycle: str
    next_billing_date: datetime | None


class WebhookPayload(BaseModel):
    """Razorpay webhook payload."""
    event: str
    payload: dict


# ==================== Endpoints ====================

@router.get("/subscription-billing/history", response_model=List[BillingHistoryResponse])
async def get_subscription_billing_history(
    request: Request,
    limit: int = 50,
    db: DB = None
):
    """
    Get subscription billing history for the current tenant.

    Returns list of subscription invoices with payment status.
    """
    tenant_id = request.state.tenant.id
    service = BillingService(db)

    billing_records = await service.get_billing_history(tenant_id, limit)

    return [
        BillingHistoryResponse(
            id=str(record.id),
            invoice_number=record.invoice_number,
            billing_period_start=record.billing_period_start,
            billing_period_end=record.billing_period_end,
            amount=float(record.amount),
            tax_amount=float(record.tax_amount or 0),
            total_amount=float(record.total_amount),
            status=record.status,
            payment_method=record.payment_method,
            payment_transaction_id=record.payment_transaction_id,
            paid_at=record.paid_at,
            due_date=record.due_date,
            created_at=record.created_at
        )
        for record in billing_records
    ]


@router.get("/subscription-billing/current", response_model=CurrentBillingResponse)
async def get_current_subscription_billing(
    request: Request,
    db: DB = None
):
    """
    Get current subscription billing amount for the tenant.

    Returns monthly and yearly cost based on active module subscriptions.
    """
    tenant_id = request.state.tenant.id
    service = BillingService(db)

    monthly_cost = await service.get_current_billing_amount(tenant_id)

    # Calculate yearly cost (20% discount)
    yearly_cost = monthly_cost * 12 * 0.8

    # TODO: Get active modules count
    # For now, return calculated costs
    return CurrentBillingResponse(
        tenant_id=str(tenant_id),
        monthly_cost=float(monthly_cost),
        yearly_cost=float(yearly_cost),
        active_modules_count=0,  # Would count from subscriptions
        billing_cycle="monthly",  # Would get from tenant settings
        next_billing_date=None  # Would calculate from subscription end date
    )


@router.post("/subscription-billing/webhooks/razorpay")
async def razorpay_webhook(
    payload: dict,
    x_razorpay_signature: str = Header(None),
    db: DB = None
):
    """
    Handle Razorpay webhooks for subscription payment events.

    This endpoint is PUBLIC (no authentication required) as it receives webhooks from Razorpay.

    Events handled:
    - subscription.charged: Payment successful
    - subscription.cancelled: Subscription cancelled
    - subscription.paused: Subscription paused
    - payment.failed: Payment failed

    Note: In production, verify webhook signature using Razorpay secret.
    """
    # TODO: Verify webhook signature
    # if not verify_razorpay_signature(payload, x_razorpay_signature):
    #     raise HTTPException(status_code=401, detail="Invalid webhook signature")

    service = BillingService(db)

    try:
        result = await service.handle_payment_webhook(payload)
        return result
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Webhook processing failed: {str(e)}"
        )


@router.get("/subscription-billing/invoice/{invoice_number}")
async def download_subscription_invoice(
    invoice_number: str,
    request: Request,
    db: DB = None
):
    """
    Download subscription invoice PDF.

    Returns invoice details that can be used to generate PDF on frontend.
    """
    tenant_id = request.state.tenant.id
    service = BillingService(db)

    # Get billing records
    billing_records = await service.get_billing_history(tenant_id, limit=100)

    # Find matching invoice
    invoice = next(
        (r for r in billing_records if r.invoice_number == invoice_number),
        None
    )

    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")

    # Return invoice data (frontend will generate PDF)
    return {
        "invoice_number": invoice.invoice_number,
        "invoice_date": invoice.created_at.isoformat(),
        "billing_period": {
            "start": invoice.billing_period_start.isoformat(),
            "end": invoice.billing_period_end.isoformat()
        },
        "tenant": {
            "id": str(request.state.tenant.id),
            "name": request.state.tenant.name
        },
        "line_items": invoice.invoice_data.get('modules', []),
        "subtotal": float(invoice.amount),
        "tax_amount": float(invoice.tax_amount or 0),
        "total_amount": float(invoice.total_amount),
        "status": invoice.status,
        "paid_at": invoice.paid_at.isoformat() if invoice.paid_at else None,
        "payment_method": invoice.payment_method,
        "transaction_id": invoice.payment_transaction_id
    }
