"""API endpoints for Promotions, Coupons, Loyalty & Referral programs."""
from typing import Optional, List
from uuid import UUID
from datetime import date, datetime, timezone
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy import select, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.promotion import (
    Promotion, PromotionType, PromotionScope, DiscountApplication, PromotionStatus,
    PromotionUsage,
    ChannelCommissionPlan, ChannelCommissionCategoryRate, ChannelCommissionEarning,
    CommissionBeneficiary,
    LoyaltyProgram, ReferralProgram, CustomerReferral,
)
from app.models.customer import Customer
from app.models.user import User
from app.schemas.promotion import (
    # Promotion
    PromotionCreate, PromotionUpdate, PromotionResponse, PromotionBrief, PromotionListResponse,
    PromotionValidateRequest, PromotionValidateResponse,
    # Channel Commission
    ChannelCommissionPlanCreate, ChannelCommissionPlanResponse,
    ChannelCommissionCategoryRateCreate, ChannelCommissionCategoryRateResponse,
    ChannelCommissionEarningResponse,
    # Loyalty
    LoyaltyProgramCreate, LoyaltyProgramResponse,
    LoyaltyPointsAdjustRequest, LoyaltyRedeemRequest,
    # Referral
    ReferralProgramCreate, ReferralProgramResponse,
    CustomerReferralCreate, CustomerReferralResponse,
)
from app.api.deps import DB, CurrentUser, get_current_user, require_permissions
from app.services.audit_service import AuditService
from app.core.module_decorators import require_module

router = APIRouter()


# ==================== Promotions & Coupons ====================

@router.post("", response_model=PromotionResponse, status_code=status.HTTP_201_CREATED)
@require_module("marketing")
async def create_promotion(
    promo_in: PromotionCreate,
    db: DB,
    current_user: User = Depends(get_current_user),
):
    """Create a new promotion/coupon."""
    # Generate promo code if not provided
    promo_code = promo_in.code
    if not promo_code:
        import secrets
        promo_code = secrets.token_urlsafe(6).upper()

    # Check for duplicate code
    existing = await db.execute(
        select(Promotion).where(Promotion.code == promo_code)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail=f"Promotion code {promo_code} already exists")

    promotion = Promotion(
        code=promo_code,
        **promo_in.model_dump(exclude={"code"}),
        created_by=current_user.id,
    )

    db.add(promotion)
    await db.commit()
    await db.refresh(promotion)

    return promotion


@router.get("", response_model=PromotionListResponse)
@require_module("marketing")
async def list_promotions(
    db: DB,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    promotion_type: Optional[PromotionType] = None,
    scope: Optional[PromotionScope] = None,
    status: Optional[PromotionStatus] = None,
    is_active: bool = True,
    search: Optional[str] = None,
    current_user: User = Depends(get_current_user),
):
    """List promotions with filters."""
    query = select(Promotion)
    count_query = select(func.count(Promotion.id))

    filters = []
    if promotion_type:
        filters.append(Promotion.promotion_type == promotion_type)
    if scope:
        filters.append(Promotion.scope == scope)
    if status:
        filters.append(Promotion.status == status)
    if is_active:
        today = date.today()
        filters.append(Promotion.is_active == True)
        filters.append(Promotion.start_date <= today)
        filters.append(Promotion.end_date >= today)
    if search:
        filters.append(or_(
            Promotion.code.ilike(f"%{search}%"),
            Promotion.name.ilike(f"%{search}%"),
        ))

    if filters:
        query = query.where(and_(*filters))
        count_query = count_query.where(and_(*filters))

    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    query = query.order_by(Promotion.created_at.desc()).offset(skip).limit(limit)
    result = await db.execute(query)
    promotions = result.scalars().all()

    return PromotionListResponse(
        items=[PromotionBrief.model_validate(p) for p in promotions],
        total=total,
        skip=skip,
        limit=limit
    )


@router.get("/{promotion_id}", response_model=PromotionResponse)
@require_module("marketing")
async def get_promotion(
    promotion_id: UUID,
    db: DB,
    current_user: User = Depends(get_current_user),
):
    """Get promotion by ID."""
    result = await db.execute(
        select(Promotion).where(Promotion.id == promotion_id)
    )
    promotion = result.scalar_one_or_none()

    if not promotion:
        raise HTTPException(status_code=404, detail="Promotion not found")

    return promotion


@router.put("/{promotion_id}", response_model=PromotionResponse)
@require_module("marketing")
async def update_promotion(
    promotion_id: UUID,
    promo_in: PromotionUpdate,
    db: DB,
    current_user: User = Depends(get_current_user),
):
    """Update promotion."""
    result = await db.execute(
        select(Promotion).where(Promotion.id == promotion_id)
    )
    promotion = result.scalar_one_or_none()

    if not promotion:
        raise HTTPException(status_code=404, detail="Promotion not found")

    update_data = promo_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(promotion, field, value)

    promotion.updated_by = current_user.id

    await db.commit()
    await db.refresh(promotion)

    return promotion


@router.post("/validate", response_model=PromotionValidateResponse)
@require_module("marketing")
async def validate_promotion(
    request: PromotionValidateRequest,
    db: DB,
    current_user: User = Depends(get_current_user),
):
    """Validate a promotion code for an order."""
    today = date.today()

    # Find promotion
    result = await db.execute(
        select(Promotion).where(
            and_(
                Promotion.code == request.code.upper(),
                Promotion.is_active == True,
                Promotion.start_date <= today,
                Promotion.end_date >= today,
            )
        )
    )
    promotion = result.scalar_one_or_none()

    if not promotion:
        return PromotionValidateResponse(
            is_valid=False,
            message="Invalid or expired promotion code"
        )

    # Check usage limit
    if promotion.max_uses and promotion.times_used >= promotion.max_uses:
        return PromotionValidateResponse(
            is_valid=False,
            message="Promotion usage limit reached"
        )

    # Check per-customer limit
    if request.customer_id and promotion.max_uses_per_customer:
        usage_count = await db.execute(
            select(func.count(PromotionUsage.id)).where(
                and_(
                    PromotionUsage.promotion_id == promotion.id,
                    PromotionUsage.customer_id == request.customer_id,
                )
            )
        )
        customer_uses = usage_count.scalar() or 0
        if customer_uses >= promotion.max_uses_per_customer:
            return PromotionValidateResponse(
                is_valid=False,
                message="You have already used this promotion"
            )

    # Check minimum order value
    if promotion.min_order_value and request.order_value < promotion.min_order_value:
        return PromotionValidateResponse(
            is_valid=False,
            message=f"Minimum order value is ₹{promotion.min_order_value}"
        )

    # Check first order only
    if promotion.first_order_only and request.customer_id:
        from app.models.order import Order
        order_count = await db.execute(
            select(func.count(Order.id)).where(Order.customer_id == request.customer_id)
        )
        if (order_count.scalar() or 0) > 0:
            return PromotionValidateResponse(
                is_valid=False,
                message="This promotion is for first orders only"
            )

    # Calculate discount
    discount_amount = Decimal("0")
    if promotion.discount_type == "PERCENTAGE":
        discount_amount = request.order_value * (promotion.discount_value / 100)
        if promotion.max_discount_amount:
            discount_amount = min(discount_amount, promotion.max_discount_amount)
    else:  # FIXED
        discount_amount = promotion.discount_value

    return PromotionValidateResponse(
        is_valid=True,
        promotion_id=promotion.id,
        code=promotion.code,
        name=promotion.name,
        discount_type=promotion.discount_type,
        discount_value=promotion.discount_value,
        discount_amount=discount_amount,
        message="Promotion applied successfully"
    )


@router.post("/{promotion_id}/apply")
@require_module("marketing")
async def apply_promotion(
    promotion_id: UUID,
    order_id: UUID,
    db: DB,
    customer_id: Optional[UUID] = None,
    discount_applied: Decimal = Decimal("0"),
    current_user: User = Depends(get_current_user),
):
    """Record promotion usage after order placement."""
    result = await db.execute(
        select(Promotion).where(Promotion.id == promotion_id)
    )
    promotion = result.scalar_one_or_none()

    if not promotion:
        raise HTTPException(status_code=404, detail="Promotion not found")

    # Record usage
    usage = PromotionUsage(
        promotion_id=promotion_id,
        order_id=order_id,
        customer_id=customer_id,
        discount_applied=discount_applied,
        created_by=current_user.id,
    )
    db.add(usage)

    # Update promotion stats
    promotion.times_used += 1
    promotion.total_discount_given += discount_applied

    await db.commit()

    return {"message": "Promotion applied successfully", "usage_id": str(usage.id)}


# ==================== Channel Commission ====================

@router.post("/channel-commissions/plans", response_model=ChannelCommissionPlanResponse, status_code=status.HTTP_201_CREATED)
@require_module("marketing")
async def create_channel_commission_plan(
    plan_in: ChannelCommissionPlanCreate,
    db: DB,
    current_user: User = Depends(get_current_user),
):
    """Create a channel commission plan (for marketplace orders)."""
    plan = ChannelCommissionPlan(
        **plan_in.model_dump(),
        created_by=current_user.id,
    )

    db.add(plan)
    await db.commit()
    await db.refresh(plan)

    return plan


@router.get("/channel-commissions/plans", response_model=List[ChannelCommissionPlanResponse])
@require_module("marketing")
async def list_channel_commission_plans(
    db: DB,
    channel_id: Optional[UUID] = None,
    is_active: bool = True,
    current_user: User = Depends(get_current_user),
):
    """List channel commission plans."""
    query = select(ChannelCommissionPlan)

    if channel_id:
        query = query.where(ChannelCommissionPlan.channel_id == channel_id)
    if is_active is not None:
        query = query.where(ChannelCommissionPlan.is_active == is_active)

    result = await db.execute(query)
    plans = result.scalars().all()

    return [ChannelCommissionPlanResponse.model_validate(p) for p in plans]


@router.post("/channel-commissions/plans/{plan_id}/rates", response_model=ChannelCommissionCategoryRateResponse)
@require_module("marketing")
async def add_channel_commission_rate(
    plan_id: UUID,
    rate_in: ChannelCommissionCategoryRateCreate,
    db: DB,
    current_user: User = Depends(get_current_user),
):
    """Add category-wise rate to channel commission plan."""
    rate = ChannelCommissionCategoryRate(
        plan_id=plan_id,
        **rate_in.model_dump(),
        created_by=current_user.id,
    )

    db.add(rate)
    await db.commit()
    await db.refresh(rate)

    return rate


@router.get("/channel-commissions/earnings", response_model=List[ChannelCommissionEarningResponse])
@require_module("marketing")
async def list_channel_commission_earnings(
    db: DB,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    channel_id: Optional[UUID] = None,
    beneficiary: Optional[CommissionBeneficiary] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    current_user: User = Depends(get_current_user),
):
    """List channel commission earnings."""
    query = select(ChannelCommissionEarning)

    filters = []
    if channel_id:
        filters.append(ChannelCommissionEarning.channel_id == channel_id)
    if beneficiary:
        filters.append(ChannelCommissionEarning.beneficiary == beneficiary)
    if start_date:
        filters.append(ChannelCommissionEarning.earning_date >= start_date)
    if end_date:
        filters.append(ChannelCommissionEarning.earning_date <= end_date)

    if filters:
        query = query.where(and_(*filters))

    query = query.order_by(ChannelCommissionEarning.created_at.desc()).offset(skip).limit(limit)
    result = await db.execute(query)
    earnings = result.scalars().all()

    return [ChannelCommissionEarningResponse.model_validate(e) for e in earnings]


# ==================== Loyalty Program ====================

@router.post("/loyalty/programs", response_model=LoyaltyProgramResponse, status_code=status.HTTP_201_CREATED)
@require_module("marketing")
async def create_loyalty_program(
    program_in: LoyaltyProgramCreate,
    db: DB,
    current_user: User = Depends(get_current_user),
):
    """Create a loyalty program."""
    program = LoyaltyProgram(
        **program_in.model_dump(),
        created_by=current_user.id,
    )

    db.add(program)
    await db.commit()
    await db.refresh(program)

    return program


@router.get("/loyalty/programs", response_model=List[LoyaltyProgramResponse])
@require_module("marketing")
async def list_loyalty_programs(
    db: DB,
    is_active: bool = True,
    current_user: User = Depends(get_current_user),
):
    """List loyalty programs."""
    query = select(LoyaltyProgram)

    if is_active is not None:
        query = query.where(LoyaltyProgram.is_active == is_active)

    result = await db.execute(query)
    programs = result.scalars().all()

    return [LoyaltyProgramResponse.model_validate(p) for p in programs]


@router.get("/loyalty/customers/{customer_id}/balance")
@require_module("marketing")
async def get_customer_loyalty_balance(
    customer_id: UUID,
    db: DB,
    current_user: User = Depends(get_current_user),
):
    """Get customer's loyalty points balance."""
    # Get customer
    customer_result = await db.execute(
        select(Customer).where(Customer.id == customer_id)
    )
    customer = customer_result.scalar_one_or_none()

    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")

    # Get active loyalty program
    program_result = await db.execute(
        select(LoyaltyProgram).where(LoyaltyProgram.is_active == True)
    )
    program = program_result.scalar_one_or_none()

    loyalty_points = getattr(customer, 'loyalty_points', 0)
    points_value = Decimal("0")

    if program and loyalty_points > 0:
        points_value = loyalty_points * program.point_value

    return {
        "customer_id": str(customer_id),
        "loyalty_points": loyalty_points,
        "points_value": float(points_value),
        "program_name": program.name if program else None,
        "point_value": float(program.point_value) if program else 0,
    }


@router.post("/loyalty/customers/{customer_id}/adjust")
@require_module("marketing")
async def adjust_loyalty_points(
    customer_id: UUID,
    adjustment: LoyaltyPointsAdjustRequest,
    db: DB,
    current_user: User = Depends(get_current_user),
):
    """Adjust customer's loyalty points (add/deduct)."""
    customer_result = await db.execute(
        select(Customer).where(Customer.id == customer_id)
    )
    customer = customer_result.scalar_one_or_none()

    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")

    current_points = getattr(customer, 'loyalty_points', 0)

    if adjustment.adjustment_type == "DEDUCT" and current_points < adjustment.points:
        raise HTTPException(status_code=400, detail="Insufficient loyalty points")

    if adjustment.adjustment_type == "ADD":
        new_points = current_points + adjustment.points
    else:
        new_points = current_points - adjustment.points

    # Update customer points
    if hasattr(customer, 'loyalty_points'):
        customer.loyalty_points = new_points

    await db.commit()

    return {
        "customer_id": str(customer_id),
        "previous_points": current_points,
        "adjustment": adjustment.points,
        "adjustment_type": adjustment.adjustment_type,
        "new_points": new_points,
        "reason": adjustment.reason,
    }


@router.post("/loyalty/customers/{customer_id}/redeem")
@require_module("marketing")
async def redeem_loyalty_points(
    customer_id: UUID,
    redeem: LoyaltyRedeemRequest,
    db: DB,
    current_user: User = Depends(get_current_user),
):
    """Redeem loyalty points for discount."""
    customer_result = await db.execute(
        select(Customer).where(Customer.id == customer_id)
    )
    customer = customer_result.scalar_one_or_none()

    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")

    current_points = getattr(customer, 'loyalty_points', 0)

    if current_points < redeem.points_to_redeem:
        raise HTTPException(status_code=400, detail="Insufficient loyalty points")

    # Get program for point value
    program_result = await db.execute(
        select(LoyaltyProgram).where(LoyaltyProgram.is_active == True)
    )
    program = program_result.scalar_one_or_none()

    if not program:
        raise HTTPException(status_code=400, detail="No active loyalty program")

    discount_value = redeem.points_to_redeem * program.point_value

    # Check maximum redemption per order
    if program.max_redemption_per_order and discount_value > program.max_redemption_per_order:
        discount_value = program.max_redemption_per_order
        redeem.points_to_redeem = int(discount_value / program.point_value)

    # Check order value percentage limit
    if program.max_redemption_percentage and redeem.order_value:
        max_discount = redeem.order_value * (program.max_redemption_percentage / 100)
        if discount_value > max_discount:
            discount_value = max_discount
            redeem.points_to_redeem = int(discount_value / program.point_value)

    # Deduct points
    new_points = current_points - redeem.points_to_redeem
    if hasattr(customer, 'loyalty_points'):
        customer.loyalty_points = new_points

    await db.commit()

    return {
        "customer_id": str(customer_id),
        "points_redeemed": redeem.points_to_redeem,
        "discount_value": float(discount_value),
        "remaining_points": new_points,
        "order_id": str(redeem.order_id) if redeem.order_id else None,
    }


# ==================== Referral Program ====================

@router.post("/referral/programs", response_model=ReferralProgramResponse, status_code=status.HTTP_201_CREATED)
@require_module("marketing")
async def create_referral_program(
    program_in: ReferralProgramCreate,
    db: DB,
    current_user: User = Depends(get_current_user),
):
    """Create a customer referral program."""
    program = ReferralProgram(
        **program_in.model_dump(),
        created_by=current_user.id,
    )

    db.add(program)
    await db.commit()
    await db.refresh(program)

    return program


@router.get("/referral/programs", response_model=List[ReferralProgramResponse])
@require_module("marketing")
async def list_referral_programs(
    db: DB,
    is_active: bool = True,
    current_user: User = Depends(get_current_user),
):
    """List referral programs."""
    query = select(ReferralProgram)

    if is_active is not None:
        query = query.where(ReferralProgram.is_active == is_active)

    result = await db.execute(query)
    programs = result.scalars().all()

    return [ReferralProgramResponse.model_validate(p) for p in programs]


@router.post("/referral/referrals", response_model=CustomerReferralResponse, status_code=status.HTTP_201_CREATED)
@require_module("marketing")
async def create_customer_referral(
    referral_in: CustomerReferralCreate,
    db: DB,
    current_user: User = Depends(get_current_user),
):
    """Record a customer referral."""
    # Generate referral code
    import secrets
    referral_code = secrets.token_urlsafe(8).upper()

    referral = CustomerReferral(
        referral_code=referral_code,
        **referral_in.model_dump(),
        created_by=current_user.id,
    )

    db.add(referral)
    await db.commit()
    await db.refresh(referral)

    return referral


@router.get("/referral/referrals", response_model=List[CustomerReferralResponse])
@require_module("marketing")
async def list_customer_referrals(
    db: DB,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    referrer_id: Optional[UUID] = None,
    is_converted: Optional[bool] = None,
    current_user: User = Depends(get_current_user),
):
    """List customer referrals."""
    query = select(CustomerReferral)

    filters = []
    if referrer_id:
        filters.append(CustomerReferral.referrer_customer_id == referrer_id)
    if is_converted is not None:
        filters.append(CustomerReferral.is_converted == is_converted)

    if filters:
        query = query.where(and_(*filters))

    query = query.order_by(CustomerReferral.created_at.desc()).offset(skip).limit(limit)
    result = await db.execute(query)
    referrals = result.scalars().all()

    return [CustomerReferralResponse.model_validate(r) for r in referrals]


@router.get("/referral/customers/{customer_id}/code")
@require_module("marketing")
async def get_customer_referral_code(
    customer_id: UUID,
    db: DB,
    current_user: User = Depends(get_current_user),
):
    """Get or generate referral code for a customer."""
    # Get active referral program
    program_result = await db.execute(
        select(ReferralProgram).where(ReferralProgram.is_active == True)
    )
    program = program_result.scalar_one_or_none()

    if not program:
        raise HTTPException(status_code=400, detail="No active referral program")

    # Check if customer already has a referral code
    customer_result = await db.execute(
        select(Customer).where(Customer.id == customer_id)
    )
    customer = customer_result.scalar_one_or_none()

    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")

    # Generate code based on customer
    import hashlib

    referral_code = hashlib.md5(
        f"{customer_id}{program.id}".encode()
    ).hexdigest()[:8].upper()

    # Get referral stats
    stats_result = await db.execute(
        select(
            func.count(CustomerReferral.id).label("total_referrals"),
            func.count(CustomerReferral.id).filter(
                CustomerReferral.is_converted == True
            ).label("successful_referrals"),
            func.coalesce(func.sum(CustomerReferral.referrer_reward), 0).label("total_reward"),
        ).where(CustomerReferral.referrer_customer_id == customer_id)
    )
    stats = stats_result.one()

    return {
        "customer_id": str(customer_id),
        "referral_code": referral_code,
        "program_name": program.name,
        "referrer_reward": float(program.referrer_reward),
        "referee_reward": float(program.referee_reward),
        "stats": {
            "total_referrals": stats.total_referrals,
            "successful_referrals": stats.successful_referrals,
            "total_reward_earned": float(stats.total_reward),
        }
    }


@router.post("/referral/referrals/{referral_id}/convert", response_model=CustomerReferralResponse)
@require_module("marketing")
async def convert_customer_referral(
    referral_id: UUID,
    order_id: UUID,
    order_value: Decimal,
    db: DB,
    current_user: User = Depends(get_current_user),
):
    """Mark customer referral as converted and apply rewards."""
    result = await db.execute(
        select(CustomerReferral).where(CustomerReferral.id == referral_id)
    )
    referral = result.scalar_one_or_none()

    if not referral:
        raise HTTPException(status_code=404, detail="Referral not found")

    if referral.is_converted:
        raise HTTPException(status_code=400, detail="Referral already converted")

    # Get program for rewards
    program_result = await db.execute(
        select(ReferralProgram).where(ReferralProgram.id == referral.program_id)
    )
    program = program_result.scalar_one_or_none()

    if program:
        referral.referrer_reward = program.referrer_reward
        referral.referee_reward = program.referee_reward

        # Apply rewards to customers (could be points, credit, etc.)
        # This depends on reward type - simplified here

    referral.is_converted = True
    referral.converted_at = datetime.now(timezone.utc)
    referral.order_id = order_id
    referral.order_value = order_value

    await db.commit()
    await db.refresh(referral)

    return referral


# ==================== Reports ====================

@router.get("/reports/summary")
@require_module("marketing")
async def get_promotion_summary(
    start_date: date,
    end_date: date,
    db: DB,
    current_user: User = Depends(get_current_user),
):
    """Get promotion usage summary."""
    # Promotion usage
    usage_query = select(
        Promotion.code,
        Promotion.name,
        func.count(PromotionUsage.id).label("usage_count"),
        func.coalesce(func.sum(PromotionUsage.discount_applied), 0).label("total_discount"),
    ).join(
        PromotionUsage, PromotionUsage.promotion_id == Promotion.id
    ).where(
        and_(
            func.date(PromotionUsage.created_at) >= start_date,
            func.date(PromotionUsage.created_at) <= end_date,
        )
    ).group_by(Promotion.id, Promotion.code, Promotion.name)

    usage_result = await db.execute(usage_query)
    by_promotion = [
        {
            "code": row.code,
            "name": row.name,
            "usage_count": row.usage_count,
            "total_discount": float(row.total_discount),
        }
        for row in usage_result.all()
    ]

    # Totals
    total_query = select(
        func.count(PromotionUsage.id).label("total_uses"),
        func.coalesce(func.sum(PromotionUsage.discount_applied), 0).label("total_discount"),
    ).where(
        and_(
            func.date(PromotionUsage.created_at) >= start_date,
            func.date(PromotionUsage.created_at) <= end_date,
        )
    )
    total_result = await db.execute(total_query)
    totals = total_result.one()

    # Referral stats
    referral_query = select(
        func.count(CustomerReferral.id).label("total_referrals"),
        func.count(CustomerReferral.id).filter(
            CustomerReferral.is_converted == True
        ).label("conversions"),
        func.coalesce(func.sum(CustomerReferral.referrer_reward), 0).label("rewards_given"),
    ).where(
        and_(
            func.date(CustomerReferral.created_at) >= start_date,
            func.date(CustomerReferral.created_at) <= end_date,
        )
    )
    referral_result = await db.execute(referral_query)
    referrals = referral_result.one()

    return {
        "period_start": start_date.isoformat(),
        "period_end": end_date.isoformat(),
        "promotions": {
            "total_uses": totals.total_uses,
            "total_discount": float(totals.total_discount),
            "by_promotion": by_promotion,
        },
        "referrals": {
            "total_referrals": referrals.total_referrals,
            "conversions": referrals.conversions,
            "conversion_rate": (
                (referrals.conversions / referrals.total_referrals * 100)
                if referrals.total_referrals > 0 else 0
            ),
            "rewards_given": float(referrals.rewards_given),
        },
    }
