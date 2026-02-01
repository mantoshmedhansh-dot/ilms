"""
Coupon API Endpoints for D2C Storefront

Validates and applies coupon codes at checkout.
"""

import logging
import uuid
from datetime import datetime, timezone
from typing import Optional, List
from decimal import Decimal

from fastapi import APIRouter, HTTPException, status, Depends
from pydantic import BaseModel, Field
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.coupon import Coupon, CouponUsage
from app.models.order import Order
from app.models.customer import Customer
from app.api.v1.endpoints.d2c_auth import get_current_customer
from app.core.module_decorators import require_module

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/coupons", tags=["Coupons"])


# ==================== Schemas ====================

class ValidateCouponRequest(BaseModel):
    """Request to validate a coupon."""
    code: str = Field(..., min_length=1, max_length=50)
    cart_total: float = Field(..., ge=0)
    cart_items: int = Field(1, ge=1)
    product_ids: Optional[List[str]] = None
    category_ids: Optional[List[str]] = None


class CouponResponse(BaseModel):
    """Coupon validation response."""
    valid: bool
    code: str
    discount_type: Optional[str] = None
    discount_value: Optional[float] = None
    discount_amount: Optional[float] = None
    message: str
    name: Optional[str] = None
    description: Optional[str] = None
    minimum_order_amount: Optional[float] = None


class ApplyCouponRequest(BaseModel):
    """Request to apply a coupon to an order."""
    code: str
    order_id: str


# ==================== Public Endpoints ====================

@router.post("/validate", response_model=CouponResponse)
@require_module("d2c_storefront")
async def validate_coupon(
    request: ValidateCouponRequest,
    customer: Optional[Customer] = Depends(get_current_customer),
    db: AsyncSession = Depends(get_db),
):
    """
    Validate a coupon code.
    Returns discount details if valid, error message if not.
    """
    code = request.code.upper().strip()

    # Find coupon
    result = await db.execute(
        select(Coupon).where(
            func.upper(Coupon.code) == code,
            Coupon.is_active == True,
        )
    )
    coupon = result.scalar_one_or_none()

    if not coupon:
        return CouponResponse(
            valid=False,
            code=code,
            message="Invalid coupon code",
        )

    # Check validity period
    now = datetime.now(timezone.utc)
    if now < coupon.valid_from:
        return CouponResponse(
            valid=False,
            code=code,
            message="This coupon is not yet active",
        )

    if coupon.valid_until and now > coupon.valid_until:
        return CouponResponse(
            valid=False,
            code=code,
            message="This coupon has expired",
        )

    # Check usage limit
    if coupon.usage_limit and coupon.used_count >= coupon.usage_limit:
        return CouponResponse(
            valid=False,
            code=code,
            message="This coupon has reached its usage limit",
        )

    # Check minimum order amount
    if coupon.minimum_order_amount and request.cart_total < float(coupon.minimum_order_amount):
        return CouponResponse(
            valid=False,
            code=code,
            message=f"Minimum order amount of ₹{coupon.minimum_order_amount:.0f} required",
            minimum_order_amount=float(coupon.minimum_order_amount),
        )

    # Check minimum items
    if coupon.minimum_items and request.cart_items < coupon.minimum_items:
        return CouponResponse(
            valid=False,
            code=code,
            message=f"Minimum {coupon.minimum_items} items required in cart",
        )

    # Check first order only
    if coupon.first_order_only and customer:
        order_count = await db.execute(
            select(func.count(Order.id)).where(
                Order.customer_id == customer.id,
                Order.status != "CANCELLED",
            )
        )
        if order_count.scalar() > 0:
            return CouponResponse(
                valid=False,
                code=code,
                message="This coupon is only valid for first orders",
            )

    # Check customer-specific coupon
    if coupon.specific_customers:
        if not customer:
            return CouponResponse(
                valid=False,
                code=code,
                message="Please login to use this coupon",
            )
        if str(customer.id) not in coupon.specific_customers:
            return CouponResponse(
                valid=False,
                code=code,
                message="This coupon is not available for your account",
            )

    # Check per-customer usage limit
    if customer and coupon.usage_limit_per_customer:
        usage_count = await db.execute(
            select(func.count(CouponUsage.id)).where(
                CouponUsage.coupon_id == coupon.id,
                CouponUsage.customer_id == customer.id,
            )
        )
        if usage_count.scalar() >= coupon.usage_limit_per_customer:
            return CouponResponse(
                valid=False,
                code=code,
                message="You have already used this coupon",
            )

    # Check product/category restrictions
    if coupon.applicable_products or coupon.applicable_categories:
        applicable = False

        if request.product_ids and coupon.applicable_products:
            for pid in request.product_ids:
                if pid in coupon.applicable_products:
                    applicable = True
                    break

        if request.category_ids and coupon.applicable_categories:
            for cid in request.category_ids:
                if cid in coupon.applicable_categories:
                    applicable = True
                    break

        if not applicable and (request.product_ids or request.category_ids):
            return CouponResponse(
                valid=False,
                code=code,
                message="This coupon is not applicable to items in your cart",
            )

    # Check excluded products
    if coupon.excluded_products and request.product_ids:
        for pid in request.product_ids:
            if pid in coupon.excluded_products:
                return CouponResponse(
                    valid=False,
                    code=code,
                    message="This coupon cannot be applied to some items in your cart",
                )

    # Calculate discount
    discount_amount = _calculate_discount(
        coupon=coupon,
        cart_total=request.cart_total,
    )

    return CouponResponse(
        valid=True,
        code=coupon.code,
        discount_type=coupon.discount_type,
        discount_value=float(coupon.discount_value),
        discount_amount=discount_amount,
        message=f"Coupon applied! You save ₹{discount_amount:.0f}",
        name=coupon.name,
        description=coupon.description,
        minimum_order_amount=float(coupon.minimum_order_amount) if coupon.minimum_order_amount else None,
    )


@router.get("/active")
@require_module("d2c_storefront")
async def get_active_coupons(
    customer: Optional[Customer] = Depends(get_current_customer),
    db: AsyncSession = Depends(get_db),
):
    """
    Get list of currently active public coupons.
    """
    now = datetime.now(timezone.utc)

    query = select(Coupon).where(
        Coupon.is_active == True,
        Coupon.valid_from <= now,
        Coupon.specific_customers == None,  # Only public coupons
    ).filter(
        (Coupon.valid_until == None) | (Coupon.valid_until > now)
    ).filter(
        (Coupon.usage_limit == None) | (Coupon.used_count < Coupon.usage_limit)
    ).order_by(Coupon.discount_value.desc()).limit(10)

    result = await db.execute(query)
    coupons = result.scalars().all()

    return [
        {
            "code": coupon.code,
            "name": coupon.name,
            "description": coupon.description,
            "discount_type": coupon.discount_type,
            "discount_value": float(coupon.discount_value),
            "minimum_order_amount": float(coupon.minimum_order_amount) if coupon.minimum_order_amount else None,
            "max_discount_amount": float(coupon.max_discount_amount) if coupon.max_discount_amount else None,
            "valid_until": coupon.valid_until.isoformat() if coupon.valid_until else None,
            "first_order_only": coupon.first_order_only,
        }
        for coupon in coupons
    ]


# ==================== Internal Functions ====================

def _calculate_discount(coupon: Coupon, cart_total: float) -> float:
    """Calculate the discount amount based on coupon type."""
    if coupon.discount_type == "PERCENTAGE":
        discount = cart_total * (float(coupon.discount_value) / 100)
        # Apply max discount cap if set
        if coupon.max_discount_amount:
            discount = min(discount, float(coupon.max_discount_amount))
        return round(discount, 2)

    elif coupon.discount_type == "FIXED_AMOUNT":
        # Don't exceed cart total
        return min(float(coupon.discount_value), cart_total)

    elif coupon.discount_type == "FREE_SHIPPING":
        # Return shipping amount (assuming ~100 for now, actual comes from checkout)
        return float(coupon.discount_value) if coupon.discount_value else 0

    return 0


async def record_coupon_usage(
    db: AsyncSession,
    coupon_code: str,
    customer_id: uuid.UUID,
    order_id: uuid.UUID,
    discount_amount: float,
):
    """
    Record coupon usage after order is placed.
    Called from order creation endpoint.
    """
    # Find coupon
    result = await db.execute(
        select(Coupon).where(func.upper(Coupon.code) == coupon_code.upper())
    )
    coupon = result.scalar_one_or_none()

    if not coupon:
        return

    # Record usage
    usage = CouponUsage(
        coupon_id=coupon.id,
        customer_id=customer_id,
        order_id=order_id,
        discount_amount=discount_amount,
    )
    db.add(usage)

    # Increment used count
    coupon.used_count += 1

    await db.commit()
    logger.info(f"Coupon {coupon_code} used by customer {customer_id} on order {order_id}")
