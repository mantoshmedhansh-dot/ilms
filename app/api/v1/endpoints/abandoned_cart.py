"""
Abandoned Cart API Endpoints

Provides cart persistence, recovery, and analytics for D2C storefront.
"""

import logging
import secrets
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from typing import Optional, List
from uuid import UUID

from fastapi import APIRouter, HTTPException, status, Depends, Query, Request
from sqlalchemy import select, func, and_, or_
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.abandoned_cart import AbandonedCart, CartRecoveryEmail
from app.models.customer import Customer
from app.schemas.abandoned_cart import (
    CartSyncRequest,
    CartSyncResponse,
    CartRecoverRequest,
    RecoveredCartResponse,
    CartItemResponse,
    AbandonedCartSummary,
    AbandonedCartDetail,
    AbandonedCartStats,
    RecoveryPerformance,
    RecoveryEmailTriggerRequest,
    RecoveryEmailResponse,
)
from app.api.v1.endpoints.d2c_auth import get_current_customer
from app.core.module_decorators import require_module

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/abandoned-cart", tags=["Abandoned Cart"])

# Constants
ABANDONMENT_THRESHOLD_MINUTES = 30  # Cart considered abandoned after 30 min of inactivity
CART_EXPIRY_DAYS = 30  # Carts expire after 30 days
RECOVERY_TOKEN_EXPIRY_DAYS = 7  # Recovery links expire after 7 days


# ==================== Helper Functions ====================

def generate_recovery_token() -> str:
    """Generate a secure recovery token."""
    return secrets.token_urlsafe(32)


async def get_or_create_cart(
    db: AsyncSession,
    session_id: str,
    customer_id: Optional[UUID] = None
) -> AbandonedCart:
    """Get existing cart or create new one."""
    # Build query conditions
    conditions = []
    if customer_id:
        conditions.append(AbandonedCart.customer_id == customer_id)
    conditions.append(AbandonedCart.session_id == session_id)

    # Try to find existing active cart
    result = await db.execute(
        select(AbandonedCart).where(
            and_(
                or_(*conditions),
                AbandonedCart.status.in_(["ACTIVE", "ABANDONED"])
            )
        ).order_by(AbandonedCart.updated_at.desc())
    )
    cart = result.scalar_one_or_none()

    if cart:
        # Update customer_id if logged in and cart was guest
        if customer_id and not cart.customer_id:
            cart.customer_id = customer_id
        return cart

    # Create new cart
    cart = AbandonedCart(
        session_id=session_id,
        customer_id=customer_id,
        items=[],
        recovery_token=generate_recovery_token(),
        recovery_token_expires_at=datetime.now(timezone.utc) + timedelta(days=RECOVERY_TOKEN_EXPIRY_DAYS)
    )
    db.add(cart)
    await db.flush()
    return cart


async def mark_carts_abandoned(db: AsyncSession) -> int:
    """Mark inactive carts as abandoned. Returns count of carts marked."""
    threshold = datetime.now(timezone.utc) - timedelta(minutes=ABANDONMENT_THRESHOLD_MINUTES)

    result = await db.execute(
        select(AbandonedCart).where(
            and_(
                AbandonedCart.status == "ACTIVE",
                AbandonedCart.last_activity_at < threshold,
                AbandonedCart.items_count > 0  # Only carts with items
            )
        )
    )
    carts = result.scalars().all()

    for cart in carts:
        cart.status = "ABANDONED"
        cart.abandoned_at = datetime.now(timezone.utc)

    await db.commit()
    return len(carts)


# ==================== Public Endpoints ====================

@router.post("/sync", response_model=CartSyncResponse)
@require_module("sales_distribution")
async def sync_cart(
    request: CartSyncRequest,
    http_request: Request,
    customer: Optional[Customer] = Depends(get_current_customer),
    db: AsyncSession = Depends(get_db),
):
    """
    Sync cart from frontend to backend for persistence.
    Called on cart changes and periodically.
    """
    try:
        # Get or create cart
        cart = await get_or_create_cart(
            db,
            request.session_id,
            customer.id if customer else None
        )

        # Update cart data
        cart.items = [item.model_dump(mode="json") for item in request.items]
        cart.items_count = len(request.items)
        cart.subtotal = request.subtotal
        cart.tax_amount = request.tax_amount
        cart.shipping_amount = request.shipping_amount
        cart.discount_amount = request.discount_amount
        cart.total_amount = request.total_amount
        cart.coupon_code = request.coupon_code

        # Update contact info
        if request.email:
            cart.email = request.email
        if request.phone:
            cart.phone = request.phone
        if request.customer_name:
            cart.customer_name = request.customer_name

        # Update checkout progress
        if request.checkout_step:
            cart.checkout_step = request.checkout_step
        if request.shipping_address:
            cart.shipping_address = request.shipping_address
        if request.selected_payment_method:
            cart.selected_payment_method = request.selected_payment_method

        # Update analytics
        if request.source:
            cart.source = request.source
        if request.utm_source:
            cart.utm_source = request.utm_source
        if request.utm_medium:
            cart.utm_medium = request.utm_medium
        if request.utm_campaign:
            cart.utm_campaign = request.utm_campaign
        if request.referrer_url:
            cart.referrer_url = request.referrer_url

        # Update device info
        if request.user_agent:
            cart.user_agent = request.user_agent
        if request.device_type:
            cart.device_type = request.device_type
        if request.device_fingerprint:
            cart.device_fingerprint = request.device_fingerprint

        # Update IP address from request
        cart.ip_address = http_request.client.host if http_request.client else None

        # Update activity timestamp
        cart.last_activity_at = datetime.now(timezone.utc)

        # If cart was abandoned, mark as recovered
        if cart.status == "ABANDONED":
            cart.status = "RECOVERED"
            cart.recovered_at = datetime.now(timezone.utc)

        # If cart is empty, keep it ACTIVE but not recoverable
        if len(request.items) == 0:
            cart.status = "ACTIVE"

        await db.commit()

        return CartSyncResponse(
            cart_id=cart.id,
            session_id=cart.session_id,
            status=cart.status,
            items_count=cart.items_count,
            total_amount=cart.total_amount,
            recovery_token=cart.recovery_token,
            message="Cart synced successfully"
        )

    except Exception as e:
        logger.error(f"Error syncing cart: {e}")
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to sync cart"
        )


@router.get("/recover/{token}", response_model=RecoveredCartResponse)
@require_module("sales_distribution")
async def recover_cart(
    token: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Recover an abandoned cart using recovery token.
    Used when customer clicks recovery email link.
    """
    # Find cart by recovery token
    result = await db.execute(
        select(AbandonedCart).where(
            and_(
                AbandonedCart.recovery_token == token,
                AbandonedCart.status.in_(["ABANDONED", "RECOVERED"])
            )
        )
    )
    cart = result.scalar_one_or_none()

    if not cart:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cart not found or expired"
        )

    # Check token expiry
    if cart.recovery_token_expires_at and cart.recovery_token_expires_at < datetime.now(timezone.utc):
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail="Recovery link has expired"
        )

    # Mark as recovered
    cart.status = "RECOVERED"
    cart.recovered_at = datetime.now(timezone.utc)
    cart.last_activity_at = datetime.now(timezone.utc)

    # Update recovery email status if clicked
    result = await db.execute(
        select(CartRecoveryEmail).where(
            and_(
                CartRecoveryEmail.cart_id == cart.id,
                CartRecoveryEmail.status.in_(["SENT", "DELIVERED", "OPENED"])
            )
        ).order_by(CartRecoveryEmail.created_at.desc())
    )
    recovery_email = result.scalar_one_or_none()
    if recovery_email:
        recovery_email.status = "CLICKED"
        recovery_email.clicked_at = datetime.now(timezone.utc)

    await db.commit()

    # Convert items to response format
    items = []
    for item in cart.items:
        items.append(CartItemResponse(
            product_id=item.get("product_id"),
            product_name=item.get("product_name"),
            sku=item.get("sku"),
            quantity=item.get("quantity", 1),
            price=Decimal(str(item.get("price", 0))),
            variant_id=item.get("variant_id"),
            variant_name=item.get("variant_name"),
            image_url=item.get("image_url"),
        ))

    return RecoveredCartResponse(
        cart_id=cart.id,
        items=items,
        subtotal=cart.subtotal,
        tax_amount=cart.tax_amount,
        shipping_amount=cart.shipping_amount,
        discount_amount=cart.discount_amount,
        total_amount=cart.total_amount,
        coupon_code=cart.coupon_code,
        shipping_address=cart.shipping_address,
        message="Cart recovered successfully"
    )


@router.post("/mark-converted/{session_id}")
@require_module("sales_distribution")
async def mark_cart_converted(
    session_id: str,
    order_id: UUID,
    customer: Optional[Customer] = Depends(get_current_customer),
    db: AsyncSession = Depends(get_db),
):
    """
    Mark cart as converted when order is placed.
    Called after successful checkout.
    """
    # Find the cart
    conditions = [AbandonedCart.session_id == session_id]
    if customer:
        conditions.append(AbandonedCart.customer_id == customer.id)

    result = await db.execute(
        select(AbandonedCart).where(
            and_(
                or_(*conditions),
                AbandonedCart.status.in_(["ACTIVE", "ABANDONED", "RECOVERED"])
            )
        ).order_by(AbandonedCart.updated_at.desc())
    )
    cart = result.scalar_one_or_none()

    if cart:
        cart.status = "CONVERTED"
        cart.converted_at = datetime.now(timezone.utc)
        cart.converted_order_id = order_id

        # Update recovery email status if applicable
        result = await db.execute(
            select(CartRecoveryEmail).where(
                and_(
                    CartRecoveryEmail.cart_id == cart.id,
                    CartRecoveryEmail.status == "CLICKED"
                )
            ).order_by(CartRecoveryEmail.created_at.desc())
        )
        recovery_email = result.scalar_one_or_none()
        if recovery_email:
            recovery_email.status = "CONVERTED"

        await db.commit()

    return {"message": "Cart marked as converted", "order_id": str(order_id)}


# ==================== Admin Endpoints ====================

@router.get("/admin/list", response_model=List[AbandonedCartSummary])
@require_module("sales_distribution")
async def list_abandoned_carts(
    status_filter: Optional[str] = Query(None, description="Filter by status"),
    checkout_step: Optional[str] = Query(None, description="Filter by checkout step"),
    source: Optional[str] = Query(None, description="Filter by source"),
    min_value: Optional[float] = Query(None, description="Minimum cart value"),
    has_contact: Optional[bool] = Query(None, description="Has email or phone"),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """
    List abandoned carts for admin dashboard.
    Requires admin authentication (to be added).
    """
    query = select(AbandonedCart)

    # Apply filters
    conditions = []

    if status_filter:
        conditions.append(AbandonedCart.status == status_filter)
    else:
        # Default: show abandoned and recovered
        conditions.append(AbandonedCart.status.in_(["ABANDONED", "RECOVERED"]))

    if checkout_step:
        conditions.append(AbandonedCart.checkout_step == checkout_step)

    if source:
        conditions.append(AbandonedCart.source == source)

    if min_value:
        conditions.append(AbandonedCart.total_amount >= Decimal(str(min_value)))

    if has_contact is True:
        conditions.append(
            or_(
                AbandonedCart.email.isnot(None),
                AbandonedCart.phone.isnot(None)
            )
        )

    # Only carts with items
    conditions.append(AbandonedCart.items_count > 0)

    if conditions:
        query = query.where(and_(*conditions))

    # Order by last activity
    query = query.order_by(AbandonedCart.last_activity_at.desc())

    # Pagination
    offset = (page - 1) * size
    query = query.offset(offset).limit(size)

    result = await db.execute(query)
    carts = result.scalars().all()

    return [
        AbandonedCartSummary(
            id=cart.id,
            customer_id=cart.customer_id,
            customer_name=cart.customer_name,
            email=cart.email,
            phone=cart.phone,
            status=cart.status,
            items_count=cart.items_count,
            total_amount=cart.total_amount,
            checkout_step=cart.checkout_step,
            created_at=cart.created_at,
            last_activity_at=cart.last_activity_at,
            abandoned_at=cart.abandoned_at,
            recovery_attempts=cart.recovery_attempts,
            source=cart.source,
            device_type=cart.device_type,
        )
        for cart in carts
    ]


@router.get("/admin/{cart_id}", response_model=AbandonedCartDetail)
@require_module("sales_distribution")
async def get_abandoned_cart_detail(
    cart_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """
    Get detailed abandoned cart info for admin.
    """
    result = await db.execute(
        select(AbandonedCart).options(
            selectinload(AbandonedCart.recovery_emails)
        ).where(AbandonedCart.id == cart_id)
    )
    cart = result.scalar_one_or_none()

    if not cart:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cart not found"
        )

    recovery_emails = [
        RecoveryEmailResponse(
            id=email.id,
            sequence_number=email.sequence_number,
            channel=email.channel,
            status=email.status,
            recipient=email.recipient,
            template_used=email.template_used,
            subject=email.subject,
            discount_code=email.discount_code,
            scheduled_at=email.scheduled_at,
            sent_at=email.sent_at,
            opened_at=email.opened_at,
            clicked_at=email.clicked_at,
        )
        for email in cart.recovery_emails
    ]

    return AbandonedCartDetail(
        id=cart.id,
        customer_id=cart.customer_id,
        customer_name=cart.customer_name,
        email=cart.email,
        phone=cart.phone,
        status=cart.status,
        items_count=cart.items_count,
        total_amount=cart.total_amount,
        checkout_step=cart.checkout_step,
        created_at=cart.created_at,
        last_activity_at=cart.last_activity_at,
        abandoned_at=cart.abandoned_at,
        recovery_attempts=cart.recovery_attempts,
        source=cart.source,
        device_type=cart.device_type,
        session_id=cart.session_id,
        items=cart.items,
        shipping_address=cart.shipping_address,
        coupon_code=cart.coupon_code,
        utm_source=cart.utm_source,
        utm_medium=cart.utm_medium,
        utm_campaign=cart.utm_campaign,
        referrer_url=cart.referrer_url,
        converted_order_id=cart.converted_order_id,
        converted_at=cart.converted_at,
        recovery_emails=recovery_emails,
    )


@router.get("/admin/stats", response_model=AbandonedCartStats)
@require_module("sales_distribution")
async def get_abandoned_cart_stats(
    days: int = Query(30, ge=1, le=365, description="Period in days"),
    db: AsyncSession = Depends(get_db),
):
    """
    Get abandoned cart statistics and analytics.
    """
    period_start = datetime.now(timezone.utc) - timedelta(days=days)
    period_end = datetime.now(timezone.utc)

    # Total counts by status
    result = await db.execute(
        select(
            AbandonedCart.status,
            func.count(AbandonedCart.id),
            func.sum(AbandonedCart.total_amount)
        ).where(
            AbandonedCart.created_at >= period_start
        ).group_by(AbandonedCart.status)
    )
    status_stats = {row[0]: {"count": row[1], "value": row[2] or 0} for row in result.all()}

    total_abandoned = status_stats.get("ABANDONED", {}).get("count", 0)
    total_recovered = status_stats.get("RECOVERED", {}).get("count", 0)
    total_converted = status_stats.get("CONVERTED", {}).get("count", 0)
    total_value_abandoned = Decimal(str(status_stats.get("ABANDONED", {}).get("value", 0)))
    total_value_recovered = Decimal(str(status_stats.get("CONVERTED", {}).get("value", 0)))

    # Calculate rates
    total_carts = total_abandoned + total_recovered + total_converted
    recovery_rate = (total_recovered / total_abandoned * 100) if total_abandoned > 0 else 0
    conversion_rate = (total_converted / total_carts * 100) if total_carts > 0 else 0

    # Average cart value and items
    result = await db.execute(
        select(
            func.avg(AbandonedCart.total_amount),
            func.avg(AbandonedCart.items_count)
        ).where(
            and_(
                AbandonedCart.created_at >= period_start,
                AbandonedCart.items_count > 0
            )
        )
    )
    avg_stats = result.one()
    avg_cart_value = Decimal(str(avg_stats[0] or 0))
    avg_items_per_cart = float(avg_stats[1] or 0)

    # Top abandoned products (from JSONB items)
    # This is a simplified version - in production, use proper JSONB queries
    top_products = []

    # Abandonment by checkout step
    result = await db.execute(
        select(
            AbandonedCart.checkout_step,
            func.count(AbandonedCart.id)
        ).where(
            and_(
                AbandonedCart.created_at >= period_start,
                AbandonedCart.status == "ABANDONED"
            )
        ).group_by(AbandonedCart.checkout_step)
    )
    abandonment_by_step = {row[0] or "CART": row[1] for row in result.all()}

    # Abandonment by device
    result = await db.execute(
        select(
            AbandonedCart.device_type,
            func.count(AbandonedCart.id)
        ).where(
            and_(
                AbandonedCart.created_at >= period_start,
                AbandonedCart.status == "ABANDONED"
            )
        ).group_by(AbandonedCart.device_type)
    )
    abandonment_by_device = {row[0] or "unknown": row[1] for row in result.all()}

    # Abandonment by source
    result = await db.execute(
        select(
            AbandonedCart.source,
            func.count(AbandonedCart.id)
        ).where(
            and_(
                AbandonedCart.created_at >= period_start,
                AbandonedCart.status == "ABANDONED"
            )
        ).group_by(AbandonedCart.source)
    )
    abandonment_by_source = {row[0] or "direct": row[1] for row in result.all()}

    return AbandonedCartStats(
        total_abandoned=total_abandoned,
        total_recovered=total_recovered,
        total_converted=total_converted,
        recovery_rate=round(recovery_rate, 2),
        conversion_rate=round(conversion_rate, 2),
        total_value_abandoned=total_value_abandoned,
        total_value_recovered=total_value_recovered,
        avg_cart_value=avg_cart_value,
        avg_items_per_cart=round(avg_items_per_cart, 2),
        top_abandoned_products=top_products,
        abandonment_by_checkout_step=abandonment_by_step,
        abandonment_by_device=abandonment_by_device,
        abandonment_by_source=abandonment_by_source,
        period_start=period_start,
        period_end=period_end,
    )


@router.post("/admin/trigger-recovery")
@require_module("sales_distribution")
async def trigger_recovery_email(
    request: RecoveryEmailTriggerRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Manually trigger a recovery email for a cart (admin).
    """
    # Get cart
    result = await db.execute(
        select(AbandonedCart).where(AbandonedCart.id == request.cart_id)
    )
    cart = result.scalar_one_or_none()

    if not cart:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cart not found"
        )

    if cart.status not in ["ABANDONED", "RECOVERED"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot send recovery email for cart with status: {cart.status}"
        )

    # Check for contact info
    recipient = None
    if request.channel == "EMAIL" and cart.email:
        recipient = cart.email
    elif request.channel in ["SMS", "WHATSAPP"] and cart.phone:
        recipient = cart.phone

    if not recipient:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"No {request.channel.lower()} address available for this cart"
        )

    # Get sequence number
    sequence = cart.recovery_attempts + 1

    # Create recovery email record
    recovery_email = CartRecoveryEmail(
        cart_id=cart.id,
        sequence_number=sequence,
        channel=request.channel,
        status="PENDING",
        recipient=recipient,
        template_used=f"cart_recovery_{sequence}",
        subject=f"Complete your purchase at ILMS.AI" if request.channel == "EMAIL" else None,
        discount_code=request.discount_code,
        discount_value=request.discount_value,
        scheduled_at=datetime.now(timezone.utc),
    )
    db.add(recovery_email)

    # Update cart
    cart.recovery_attempts = sequence
    cart.last_recovery_at = datetime.now(timezone.utc)

    await db.commit()

    # TODO: Actually send the email/SMS via notification service
    # For now, just mark as sent
    recovery_email.status = "SENT"
    recovery_email.sent_at = datetime.now(timezone.utc)
    await db.commit()

    return {
        "message": f"Recovery {request.channel.lower()} triggered",
        "recovery_email_id": str(recovery_email.id),
        "recipient": recipient,
        "sequence_number": sequence,
    }


@router.post("/admin/process-abandoned")
@require_module("sales_distribution")
async def process_abandoned_carts(
    db: AsyncSession = Depends(get_db),
):
    """
    Mark inactive carts as abandoned and schedule recovery emails.
    This endpoint should be called by a cron job (e.g., every 10 minutes).
    """
    # Mark carts as abandoned
    threshold = datetime.now(timezone.utc) - timedelta(minutes=ABANDONMENT_THRESHOLD_MINUTES)

    result = await db.execute(
        select(AbandonedCart).where(
            and_(
                AbandonedCart.status == "ACTIVE",
                AbandonedCart.last_activity_at < threshold,
                AbandonedCart.items_count > 0
            )
        )
    )
    carts_to_abandon = result.scalars().all()

    abandoned_count = 0
    recovery_scheduled_count = 0

    for cart in carts_to_abandon:
        cart.status = "ABANDONED"
        cart.abandoned_at = datetime.now(timezone.utc)
        abandoned_count += 1

        # Schedule first recovery email if contact info available
        if cart.email and cart.recovery_attempts == 0:
            recovery_email = CartRecoveryEmail(
                cart_id=cart.id,
                sequence_number=1,
                channel="EMAIL",
                status="PENDING",
                recipient=cart.email,
                template_used="cart_recovery_1",
                subject="You left something behind at ILMS.AI!",
                scheduled_at=datetime.now(timezone.utc) + timedelta(hours=1),  # Send after 1 hour
            )
            db.add(recovery_email)
            cart.recovery_attempts = 1
            cart.last_recovery_at = datetime.now(timezone.utc)
            recovery_scheduled_count += 1

    # Mark old carts as expired
    expiry_threshold = datetime.now(timezone.utc) - timedelta(days=CART_EXPIRY_DAYS)
    result = await db.execute(
        select(AbandonedCart).where(
            and_(
                AbandonedCart.status.in_(["ABANDONED", "RECOVERED"]),
                AbandonedCart.last_activity_at < expiry_threshold
            )
        )
    )
    expired_carts = result.scalars().all()
    expired_count = len(expired_carts)

    for cart in expired_carts:
        cart.status = "EXPIRED"

    await db.commit()

    return {
        "message": "Abandoned cart processing complete",
        "carts_marked_abandoned": abandoned_count,
        "recovery_emails_scheduled": recovery_scheduled_count,
        "carts_marked_expired": expired_count,
    }


@router.post("/admin/send-pending-recovery")
@require_module("sales_distribution")
async def send_pending_recovery_emails(
    db: AsyncSession = Depends(get_db),
):
    """
    Send pending recovery emails that are due.
    This endpoint should be called by a cron job (e.g., every 5 minutes).
    """
    now = datetime.now(timezone.utc)

    result = await db.execute(
        select(CartRecoveryEmail).options(
            selectinload(CartRecoveryEmail.cart)
        ).where(
            and_(
                CartRecoveryEmail.status == "PENDING",
                CartRecoveryEmail.scheduled_at <= now
            )
        ).limit(50)  # Process in batches
    )
    pending_emails = result.scalars().all()

    sent_count = 0
    failed_count = 0

    for email in pending_emails:
        try:
            # Check if cart is still valid for recovery
            if email.cart.status not in ["ABANDONED", "RECOVERED"]:
                email.status = "FAILED"
                email.error_message = f"Cart status is {email.cart.status}"
                failed_count += 1
                continue

            # TODO: Integrate with actual email service (SendGrid, SES, etc.)
            # For now, just mark as sent
            # await send_recovery_email(email)

            email.status = "SENT"
            email.sent_at = now
            sent_count += 1

            # Schedule next recovery email if applicable
            if email.sequence_number < 3:  # Send up to 3 emails
                next_delay = {1: 24, 2: 72}  # Hours until next email
                delay_hours = next_delay.get(email.sequence_number, 24)

                next_email = CartRecoveryEmail(
                    cart_id=email.cart_id,
                    sequence_number=email.sequence_number + 1,
                    channel="EMAIL",
                    status="PENDING",
                    recipient=email.recipient,
                    template_used=f"cart_recovery_{email.sequence_number + 1}",
                    subject="Still thinking about your cart?",
                    scheduled_at=now + timedelta(hours=delay_hours),
                    # Add discount for later emails
                    discount_code="COMEBACK10" if email.sequence_number == 1 else "COMEBACK15",
                    discount_value=10 if email.sequence_number == 1 else 15,
                )
                db.add(next_email)

                email.cart.recovery_attempts = email.sequence_number + 1
                email.cart.last_recovery_at = now

        except Exception as e:
            logger.error(f"Failed to send recovery email {email.id}: {e}")
            email.status = "FAILED"
            email.error_message = str(e)
            failed_count += 1

    await db.commit()

    return {
        "message": "Recovery email processing complete",
        "emails_sent": sent_count,
        "emails_failed": failed_count,
    }


@router.get("/admin/recovery-performance", response_model=RecoveryPerformance)
@require_module("sales_distribution")
async def get_recovery_performance(
    days: int = Query(30, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
):
    """
    Get recovery email performance metrics.
    """
    period_start = datetime.now(timezone.utc) - timedelta(days=days)

    # Overall metrics
    result = await db.execute(
        select(
            CartRecoveryEmail.status,
            func.count(CartRecoveryEmail.id)
        ).where(
            CartRecoveryEmail.created_at >= period_start
        ).group_by(CartRecoveryEmail.status)
    )
    status_counts = {row[0]: row[1] for row in result.all()}

    total_sent = status_counts.get("SENT", 0) + status_counts.get("DELIVERED", 0) + status_counts.get("OPENED", 0) + status_counts.get("CLICKED", 0) + status_counts.get("CONVERTED", 0)
    total_delivered = status_counts.get("DELIVERED", 0) + status_counts.get("OPENED", 0) + status_counts.get("CLICKED", 0) + status_counts.get("CONVERTED", 0)
    total_opened = status_counts.get("OPENED", 0) + status_counts.get("CLICKED", 0) + status_counts.get("CONVERTED", 0)
    total_clicked = status_counts.get("CLICKED", 0) + status_counts.get("CONVERTED", 0)
    total_converted = status_counts.get("CONVERTED", 0)

    # Calculate rates
    delivery_rate = (total_delivered / total_sent * 100) if total_sent > 0 else 0
    open_rate = (total_opened / total_delivered * 100) if total_delivered > 0 else 0
    click_rate = (total_clicked / total_opened * 100) if total_opened > 0 else 0
    conversion_rate = (total_converted / total_clicked * 100) if total_clicked > 0 else 0

    # Revenue from converted carts
    result = await db.execute(
        select(func.sum(AbandonedCart.total_amount)).where(
            and_(
                AbandonedCart.id.in_(
                    select(CartRecoveryEmail.cart_id).where(
                        and_(
                            CartRecoveryEmail.status == "CONVERTED",
                            CartRecoveryEmail.created_at >= period_start
                        )
                    )
                )
            )
        )
    )
    revenue_recovered = Decimal(str(result.scalar() or 0))

    # Performance by sequence number
    result = await db.execute(
        select(
            CartRecoveryEmail.sequence_number,
            func.count(CartRecoveryEmail.id).filter(CartRecoveryEmail.status != "PENDING"),
            func.count(CartRecoveryEmail.id).filter(CartRecoveryEmail.status.in_(["OPENED", "CLICKED", "CONVERTED"])),
            func.count(CartRecoveryEmail.id).filter(CartRecoveryEmail.status == "CONVERTED"),
        ).where(
            CartRecoveryEmail.created_at >= period_start
        ).group_by(CartRecoveryEmail.sequence_number)
    )
    by_sequence = [
        {
            "sequence": row[0],
            "sent": row[1],
            "opened": row[2],
            "converted": row[3],
        }
        for row in result.all()
    ]

    # Performance by channel
    result = await db.execute(
        select(
            CartRecoveryEmail.channel,
            func.count(CartRecoveryEmail.id),
            func.count(CartRecoveryEmail.id).filter(CartRecoveryEmail.status == "CONVERTED"),
        ).where(
            CartRecoveryEmail.created_at >= period_start
        ).group_by(CartRecoveryEmail.channel)
    )
    by_channel = {
        row[0]: {"sent": row[1], "converted": row[2]}
        for row in result.all()
    }

    return RecoveryPerformance(
        total_sent=total_sent,
        total_delivered=total_delivered,
        total_opened=total_opened,
        total_clicked=total_clicked,
        total_converted=total_converted,
        delivery_rate=round(delivery_rate, 2),
        open_rate=round(open_rate, 2),
        click_rate=round(click_rate, 2),
        conversion_rate=round(conversion_rate, 2),
        revenue_recovered=revenue_recovered,
        by_sequence=by_sequence,
        by_channel=by_channel,
    )
