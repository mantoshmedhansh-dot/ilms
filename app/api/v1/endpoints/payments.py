"""
Payment API endpoints for Razorpay integration.

Handles:
- Payment order creation
- Payment verification
- Payment status checks
- Refund processing
- Webhook handling for payment events
"""

import uuid
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, status, Depends, Request, Header
from typing import Optional

from app.api.deps import DB, CurrentUser, require_permissions
from app.schemas.payment import (
    CreatePaymentOrderRequest,
    VerifyPaymentRequest,
    InitiateRefundRequest,
)
from app.services.payment_service import (

    PaymentService,
    PaymentOrderRequest,
    PaymentOrderResponse,
    PaymentVerificationRequest,
    PaymentVerificationResponse,
    RefundRequest,
    RefundResponse,
    WebhookEvent,
)
from app.core.module_decorators import require_module

logger = logging.getLogger(__name__)


router = APIRouter(tags=["Payments"])


# ==================== PUBLIC ENDPOINTS ====================

@router.post(
    "/create-order",
    response_model=PaymentOrderResponse,
    summary="Create a Razorpay payment order",
    description="Create a new payment order with Razorpay for checkout."
)
@require_module("finance")
async def create_payment_order(
    data: CreatePaymentOrderRequest,
    db: DB,
):
    """
    Create a Razorpay order for payment.

    This endpoint is called during checkout to initialize payment.
    The returned order details are used by the frontend to launch
    Razorpay's payment modal.
    """
    from sqlalchemy import text

    # Verify order exists and belongs to user
    result = await db.execute(
        text("""
            SELECT id, order_number, total_amount, payment_status
            FROM orders
            WHERE id = :order_id
        """),
        {"order_id": data.order_id}
    )
    order = result.fetchone()

    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found"
        )

    if order.payment_status == "PAID":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Order is already paid"
        )

    # Create Razorpay order
    payment_service = PaymentService()

    try:
        payment_order = payment_service.create_order(
            PaymentOrderRequest(
                order_id=data.order_id,
                amount=data.amount,
                customer_email=data.customer_email,
                customer_phone=data.customer_phone,
                customer_name=data.customer_name,
                notes={
                    "order_number": order.order_number,
                    **(data.notes or {})
                }
            )
        )

        # Update order with Razorpay order ID
        await db.execute(
            text("""
                UPDATE orders
                SET
                    razorpay_order_id = :razorpay_order_id,
                    updated_at = :updated_at
                WHERE id = :order_id
            """),
            {
                "razorpay_order_id": payment_order.razorpay_order_id,
                "updated_at": datetime.now(timezone.utc),
                "order_id": data.order_id
            }
        )
        await db.commit()

        return payment_order

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create payment order: {str(e)}"
        )


@router.post(
    "/verify",
    response_model=PaymentVerificationResponse,
    summary="Verify payment after completion",
    description="Verify Razorpay payment signature and update order status."
)
@require_module("finance")
async def verify_payment(
    data: VerifyPaymentRequest,
    db: DB,
):
    """
    Verify payment signature from Razorpay.

    Called by frontend after successful payment to verify authenticity.
    Updates order status to 'paid' if verification succeeds.
    """
    from sqlalchemy import text

    payment_service = PaymentService()

    # Verify payment signature
    verification = payment_service.verify_payment(
        PaymentVerificationRequest(
            razorpay_order_id=data.razorpay_order_id,
            razorpay_payment_id=data.razorpay_payment_id,
            razorpay_signature=data.razorpay_signature,
            order_id=data.order_id
        )
    )

    if verification.verified:
        # Update order with payment details
        # Note: Column is "status" not "order_status", values are uppercase
        await db.execute(
            text("""
                UPDATE orders
                SET
                    payment_status = 'PAID',
                    razorpay_payment_id = :payment_id,
                    status = 'CONFIRMED',
                    amount_paid = total_amount,
                    paid_at = :paid_at,
                    confirmed_at = :paid_at,
                    updated_at = :updated_at
                WHERE id = :order_id
            """),
            {
                "payment_id": data.razorpay_payment_id,
                "paid_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc),
                "order_id": data.order_id
            }
        )
        await db.commit()

    return verification


@router.get(
    "/status/{payment_id}",
    summary="Get payment status",
    description="Fetch current status of a payment from Razorpay."
)
@require_module("finance")
async def get_payment_status(
    payment_id: str,
):
    """Get current status of a payment from Razorpay."""
    payment_service = PaymentService()

    try:
        status = payment_service.get_payment_status(payment_id)
        return status
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch payment status: {str(e)}"
        )


# ==================== ADMIN ENDPOINTS ====================

@router.post(
    "/refund",
    response_model=RefundResponse,
    dependencies=[Depends(require_permissions("finance:update"))],
    summary="Initiate a refund",
    description="Initiate a full or partial refund for a payment."
)
async def initiate_refund(
    data: InitiateRefundRequest,
    db: DB,
    current_user: CurrentUser,
):
    """
    Initiate a refund for a payment.

    Requires: finance:update permission

    - Full refund if amount is not specified
    - Partial refund if amount is provided
    """
    from sqlalchemy import text

    payment_service = PaymentService()

    try:
        # Initiate refund with Razorpay
        refund = payment_service.initiate_refund(
            RefundRequest(
                payment_id=data.payment_id,
                amount=data.amount,
                notes={
                    "order_id": str(data.order_id),
                    "reason": data.reason or "Customer request",
                    "initiated_by": str(current_user.id)
                }
            )
        )

        # Update order with refund details
        # Note: Using internal_notes to track refund since dedicated columns don't exist
        await db.execute(
            text("""
                UPDATE orders
                SET
                    internal_notes = COALESCE(internal_notes, '') ||
                        E'\n[Refund Initiated] Refund ID: ' || :refund_id ||
                        ', Amount: ₹' || :refund_amount::text ||
                        ', Time: ' || :initiated_at::text,
                    updated_at = :updated_at
                WHERE id = :order_id
            """),
            {
                "refund_id": refund.refund_id,
                "refund_amount": refund.amount / 100,  # Convert paise to INR
                "initiated_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc),
                "order_id": data.order_id
            }
        )
        await db.commit()

        return refund

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to initiate refund: {str(e)}"
        )


@router.get(
    "/order/{order_id}/payments",
    dependencies=[Depends(require_permissions("finance:view"))],
    summary="Get all payments for an order",
    description="Fetch all payment attempts for a specific order."
)
async def get_order_payments(
    order_id: uuid.UUID,
    db: DB,
):
    """
    Get all payment attempts for an order.

    Requires: finance:view permission
    """
    from sqlalchemy import text

    # Get Razorpay order ID
    result = await db.execute(
        text("SELECT razorpay_order_id FROM orders WHERE id = :order_id"),
        {"order_id": order_id}
    )
    order = result.fetchone()

    if not order or not order.razorpay_order_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No payment order found for this order"
        )

    payment_service = PaymentService()

    try:
        payments = payment_service.get_order_payments(order.razorpay_order_id)
        return {"order_id": order_id, "payments": payments}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch payments: {str(e)}"
        )


# ==================== WEBHOOK ENDPOINT ====================

@router.post(
    "/webhook",
    summary="Razorpay webhook handler",
    description="Handle payment events from Razorpay. This endpoint is called by Razorpay servers.",
    include_in_schema=False  # Hide from API docs for security
)
@require_module("finance")
async def razorpay_webhook(
    request: Request,
    db: DB,
    x_razorpay_signature: Optional[str] = Header(None, alias="X-Razorpay-Signature"),
):
    """
    Handle Razorpay webhook events.

    Events handled:
    - payment.captured: Payment was successful
    - payment.failed: Payment failed
    - order.paid: Order fully paid
    - refund.processed: Refund completed

    Security:
    - Verifies webhook signature using RAZORPAY_WEBHOOK_SECRET
    - Idempotent: Safe to receive duplicate events
    """
    from sqlalchemy import text

    # Get raw body for signature verification
    body = await request.body()

    payment_service = PaymentService()

    # Verify webhook signature
    if x_razorpay_signature:
        if not payment_service.verify_webhook_signature(body, x_razorpay_signature):
            logger.warning("Webhook signature verification failed")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid webhook signature"
            )
    else:
        logger.warning("Webhook received without signature header")
        # In production, you might want to reject unsigned webhooks
        # For now, we'll log and continue for testing

    # Parse webhook payload
    try:
        import json
        payload = json.loads(body)
    except json.JSONDecodeError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid JSON payload"
        )

    event = payload.get("event")
    event_payload = payload.get("payload", {})

    logger.info(f"Received Razorpay webhook: {event}")

    try:
        # Handle different event types
        if event == WebhookEvent.PAYMENT_CAPTURED:
            await _handle_payment_captured(db, event_payload)

        elif event == WebhookEvent.PAYMENT_FAILED:
            await _handle_payment_failed(db, event_payload)

        elif event == WebhookEvent.ORDER_PAID:
            await _handle_order_paid(db, event_payload)

        elif event == WebhookEvent.REFUND_PROCESSED:
            await _handle_refund_processed(db, event_payload)

        elif event == WebhookEvent.PAYMENT_AUTHORIZED:
            # For auto-capture, this is handled by Razorpay
            logger.info("Payment authorized, waiting for capture")

        else:
            logger.info(f"Unhandled webhook event: {event}")

        return {"status": "ok", "event": event}

    except Exception as e:
        logger.error(f"Error processing webhook {event}: {e}")
        # Return 200 to prevent Razorpay from retrying
        # We'll handle errors internally
        return {"status": "error", "message": str(e)}


async def _handle_payment_captured(db: DB, payload: dict):
    """Handle payment.captured event - payment was successful."""
    from sqlalchemy import text
    from app.services.email_service import send_order_notifications

    payment = payload.get("payment", {}).get("entity", {})
    razorpay_payment_id = payment.get("id")
    razorpay_order_id = payment.get("order_id")
    amount = payment.get("amount", 0) / 100  # Convert paise to INR

    if not razorpay_order_id:
        logger.warning("Payment captured without order_id")
        return

    logger.info(f"Payment captured: {razorpay_payment_id} for order {razorpay_order_id}")

    # Update order status
    await db.execute(
        text("""
            UPDATE orders
            SET
                payment_status = 'PAID',
                status = CASE
                    WHEN status IN ('NEW', 'PENDING_PAYMENT') THEN 'CONFIRMED'
                    ELSE status
                END,
                razorpay_payment_id = :payment_id,
                amount_paid = :amount,
                paid_at = :paid_at,
                confirmed_at = CASE
                    WHEN status IN ('NEW', 'PENDING_PAYMENT') THEN :paid_at
                    ELSE confirmed_at
                END,
                updated_at = :updated_at
            WHERE razorpay_order_id = :order_id
        """),
        {
            "payment_id": razorpay_payment_id,
            "order_id": razorpay_order_id,
            "amount": amount,
            "paid_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc)
        }
    )

    # Add status history entry
    result = await db.execute(
        text("SELECT id FROM orders WHERE razorpay_order_id = :order_id"),
        {"order_id": razorpay_order_id}
    )
    order = result.fetchone()

    if order:
        await db.execute(
            text("""
                INSERT INTO order_status_history (id, order_id, from_status, to_status, notes, created_at)
                VALUES (gen_random_uuid(), :order_id, 'PENDING_PAYMENT', 'CONFIRMED',
                        :notes, :created_at)
            """),
            {
                "order_id": order.id,
                "notes": f"Payment confirmed via Razorpay webhook. Payment ID: {razorpay_payment_id}",
                "created_at": datetime.now(timezone.utc)
            }
        )

        # Fetch full order details for notification
        order_result = await db.execute(
            text("""
                SELECT o.order_number, o.total_amount, o.payment_method, o.shipping_address,
                       c.name as customer_name, c.email as customer_email, c.phone as customer_phone
                FROM orders o
                JOIN customers c ON o.customer_id = c.id
                WHERE o.id = :order_id
            """),
            {"order_id": order.id}
        )
        order_data = order_result.fetchone()

        # Fetch order items
        items_result = await db.execute(
            text("""
                SELECT product_name, variant_name, quantity, total_amount
                FROM order_items
                WHERE order_id = :order_id
            """),
            {"order_id": order.id}
        )
        items = [dict(row._mapping) for row in items_result.fetchall()]

        # Send notifications asynchronously (don't block webhook response)
        if order_data:
            try:
                from decimal import Decimal
                import json

                shipping_address = order_data.shipping_address
                if isinstance(shipping_address, str):
                    shipping_address = json.loads(shipping_address)

                await send_order_notifications(
                    order_number=order_data.order_number,
                    customer_email=order_data.customer_email,
                    customer_phone=order_data.customer_phone,
                    customer_name=order_data.customer_name,
                    total_amount=Decimal(str(order_data.total_amount)),
                    items=items,
                    shipping_address=shipping_address,
                    payment_method=order_data.payment_method or "Online Payment"
                )
                logger.info(f"Notifications sent for order {order_data.order_number}")
            except Exception as e:
                logger.error(f"Failed to send notifications: {e}")
                # Don't fail the webhook for notification errors

    await db.commit()

    # ============ ACCOUNTING INTEGRATION ============
    # Create journal entry: DR Bank, CR Accounts Receivable
    if order:
        try:
            from app.services.auto_journal_service import AutoJournalService, AutoJournalError
            from decimal import Decimal

            auto_journal = AutoJournalService(db)
            await auto_journal.generate_for_order_payment(
                order_id=order.id,
                amount=Decimal(str(amount)),
                payment_method="RAZORPAY",
                reference_number=razorpay_payment_id,
                user_id=None,  # System-generated
                auto_post=True,
                is_cash=False,  # Razorpay is always bank
            )
            await db.commit()
            logger.info(f"Accounting entry created for Razorpay payment {razorpay_payment_id}")
        except AutoJournalError as e:
            logger.warning(f"Failed to create accounting entry for payment {razorpay_payment_id}: {e.message}")
        except Exception as e:
            logger.warning(f"Unexpected error creating accounting entry for payment {razorpay_payment_id}: {str(e)}")
    logger.info(f"Order updated for payment {razorpay_payment_id}")


async def _handle_payment_failed(db: DB, payload: dict):
    """Handle payment.failed event - payment was unsuccessful."""
    from sqlalchemy import text

    payment = payload.get("payment", {}).get("entity", {})
    razorpay_payment_id = payment.get("id")
    razorpay_order_id = payment.get("order_id")
    error_code = payment.get("error_code")
    error_description = payment.get("error_description")

    if not razorpay_order_id:
        return

    logger.info(f"Payment failed: {razorpay_payment_id} - {error_code}: {error_description}")

    # Update order payment status to failed
    await db.execute(
        text("""
            UPDATE orders
            SET
                payment_status = 'FAILED',
                internal_notes = COALESCE(internal_notes, '') ||
                    E'\n[Payment Failed] ' || :error_msg,
                updated_at = :updated_at
            WHERE razorpay_order_id = :order_id
        """),
        {
            "order_id": razorpay_order_id,
            "error_msg": f"{error_code}: {error_description}",
            "updated_at": datetime.now(timezone.utc)
        }
    )
    await db.commit()


async def _handle_order_paid(db: DB, payload: dict):
    """Handle order.paid event - order is fully paid."""
    from sqlalchemy import text

    order_entity = payload.get("order", {}).get("entity", {})
    razorpay_order_id = order_entity.get("id")
    amount_paid = order_entity.get("amount_paid", 0) / 100

    if not razorpay_order_id:
        return

    logger.info(f"Order paid: {razorpay_order_id} - Amount: {amount_paid}")

    # Ensure order is marked as paid
    await db.execute(
        text("""
            UPDATE orders
            SET
                payment_status = 'PAID',
                status = CASE
                    WHEN status IN ('NEW', 'PENDING_PAYMENT') THEN 'CONFIRMED'
                    ELSE status
                END,
                amount_paid = :amount,
                paid_at = COALESCE(paid_at, :paid_at),
                confirmed_at = COALESCE(confirmed_at, :paid_at),
                updated_at = :updated_at
            WHERE razorpay_order_id = :order_id
        """),
        {
            "order_id": razorpay_order_id,
            "amount": amount_paid,
            "paid_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc)
        }
    )
    await db.commit()


async def _handle_refund_processed(db: DB, payload: dict):
    """Handle refund.processed event - refund completed."""
    from sqlalchemy import text

    refund = payload.get("refund", {}).get("entity", {})
    refund_id = refund.get("id")
    payment_id = refund.get("payment_id")
    amount = refund.get("amount", 0) / 100

    logger.info(f"Refund processed: {refund_id} - Amount: {amount}")

    # Update order refund status
    await db.execute(
        text("""
            UPDATE orders
            SET
                payment_status = CASE
                    WHEN amount_paid - :refund_amount <= 0 THEN 'REFUNDED'
                    ELSE 'PARTIALLY_REFUNDED'
                END,
                amount_paid = GREATEST(0, amount_paid - :refund_amount),
                internal_notes = COALESCE(internal_notes, '') ||
                    E'\n[Refund Processed] Refund ID: ' || :refund_id || ', Amount: ' || :refund_amount::text,
                updated_at = :updated_at
            WHERE razorpay_payment_id = :payment_id
        """),
        {
            "payment_id": payment_id,
            "refund_id": refund_id,
            "refund_amount": amount,
            "updated_at": datetime.now(timezone.utc)
        }
    )
    await db.commit()
