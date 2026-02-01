"""API endpoints for Commission & Incentive management."""
from typing import Optional, List
from uuid import UUID
from datetime import date, datetime, timezone
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy import select, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.commission import (
    CommissionPlan, CommissionType, CalculationBasis,
    CommissionCategoryRate, CommissionProductRate,
    CommissionEarner, CommissionTransaction, CommissionStatus,
    CommissionPayout, CommissionPayoutLine, PayoutStatus,
    AffiliateReferral,
)
from app.models.user import User
from app.schemas.commission import (
    # Plan
    CommissionPlanCreate, CommissionPlanUpdate, CommissionPlanResponse, CommissionPlanListResponse,
    # Rates
    CommissionCategoryRateCreate, CommissionCategoryRateResponse,
    CommissionProductRateCreate, CommissionProductRateResponse,
    # Earner
    CommissionEarnerCreate, CommissionEarnerUpdate, CommissionEarnerResponse,
    # Transaction
    CommissionTransactionCreate, CommissionTransactionResponse, CommissionTransactionListResponse,
    # Payout
    CommissionPayoutCreate, CommissionPayoutResponse, CommissionPayoutListResponse,
    # Affiliate
    AffiliateReferralCreate, AffiliateReferralResponse,
    # Reports
    CommissionSummaryResponse, EarnerPerformanceResponse,
)
from app.api.deps import DB, CurrentUser, get_current_user, require_permissions
from app.services.audit_service import AuditService
from app.core.module_decorators import require_module

router = APIRouter()


# ==================== Commission Plans ====================

@router.post("/plans", response_model=CommissionPlanResponse, status_code=status.HTTP_201_CREATED)
@require_module("finance")
async def create_commission_plan(
    plan_in: CommissionPlanCreate,
    db: DB,
    current_user: User = Depends(get_current_user),
):
    """Create a new commission plan."""
    # Generate plan code
    count_result = await db.execute(select(func.count(CommissionPlan.id)))
    count = count_result.scalar() or 0
    plan_code = f"CMP-{str(count + 1).zfill(4)}"

    plan = CommissionPlan(
        plan_code=plan_code,
        **plan_in.model_dump(),
        created_by=current_user.id,
    )

    db.add(plan)
    await db.commit()
    await db.refresh(plan)

    return plan


@router.get("/plans", response_model=CommissionPlanListResponse)
@require_module("finance")
async def list_commission_plans(
    db: DB,
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=50),
    commission_type: Optional[CommissionType] = None,
    is_active: bool = True,
    current_user: User = Depends(get_current_user),
):
    """List commission plans."""
    query = select(CommissionPlan)
    count_query = select(func.count(CommissionPlan.id))

    filters = []
    if commission_type:
        filters.append(CommissionPlan.commission_type == commission_type)
    if is_active is not None:
        filters.append(CommissionPlan.is_active == is_active)

    if filters:
        query = query.where(and_(*filters))
        count_query = count_query.where(and_(*filters))

    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    query = query.order_by(CommissionPlan.created_at.desc()).offset(skip).limit(limit)
    result = await db.execute(query)
    plans = result.scalars().all()

    return CommissionPlanListResponse(
        items=[CommissionPlanResponse.model_validate(p) for p in plans],
        total=total,
        skip=skip,
        limit=limit
    )


@router.get("/plans/{plan_id}", response_model=CommissionPlanResponse)
@require_module("finance")
async def get_commission_plan(
    plan_id: UUID,
    db: DB,
    current_user: User = Depends(get_current_user),
):
    """Get commission plan by ID."""
    result = await db.execute(
        select(CommissionPlan).where(CommissionPlan.id == plan_id)
    )
    plan = result.scalar_one_or_none()

    if not plan:
        raise HTTPException(status_code=404, detail="Commission plan not found")

    return plan


@router.put("/plans/{plan_id}", response_model=CommissionPlanResponse)
@require_module("finance")
async def update_commission_plan(
    plan_id: UUID,
    plan_in: CommissionPlanUpdate,
    db: DB,
    current_user: User = Depends(get_current_user),
):
    """Update commission plan."""
    result = await db.execute(
        select(CommissionPlan).where(CommissionPlan.id == plan_id)
    )
    plan = result.scalar_one_or_none()

    if not plan:
        raise HTTPException(status_code=404, detail="Commission plan not found")

    update_data = plan_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(plan, field, value)

    plan.updated_by = current_user.id

    await db.commit()
    await db.refresh(plan)

    return plan


# ==================== Commission Rates ====================

@router.get("/plans/{plan_id}/category-rates", response_model=List[CommissionCategoryRateResponse])
@require_module("finance")
async def get_plan_category_rates(
    plan_id: UUID,
    db: DB,
    current_user: User = Depends(get_current_user),
):
    """Get category-wise commission rates for a plan."""
    result = await db.execute(
        select(CommissionCategoryRate)
        .where(CommissionCategoryRate.plan_id == plan_id)
        .order_by(CommissionCategoryRate.created_at)
    )
    rates = result.scalars().all()
    return [CommissionCategoryRateResponse.model_validate(r) for r in rates]


@router.post("/plans/{plan_id}/category-rates", response_model=CommissionCategoryRateResponse)
@require_module("finance")
async def create_category_rate(
    plan_id: UUID,
    rate_in: CommissionCategoryRateCreate,
    db: DB,
    current_user: User = Depends(get_current_user),
):
    """Add category-wise commission rate to a plan."""
    # Verify plan exists
    plan_result = await db.execute(
        select(CommissionPlan).where(CommissionPlan.id == plan_id)
    )
    if not plan_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Commission plan not found")

    rate = CommissionCategoryRate(
        plan_id=plan_id,
        **rate_in.model_dump(),
        created_by=current_user.id,
    )

    db.add(rate)
    await db.commit()
    await db.refresh(rate)

    return rate


@router.get("/plans/{plan_id}/product-rates", response_model=List[CommissionProductRateResponse])
@require_module("finance")
async def get_plan_product_rates(
    plan_id: UUID,
    db: DB,
    current_user: User = Depends(get_current_user),
):
    """Get product-specific commission rates for a plan."""
    result = await db.execute(
        select(CommissionProductRate)
        .where(CommissionProductRate.plan_id == plan_id)
        .order_by(CommissionProductRate.created_at)
    )
    rates = result.scalars().all()
    return [CommissionProductRateResponse.model_validate(r) for r in rates]


@router.post("/plans/{plan_id}/product-rates", response_model=CommissionProductRateResponse)
@require_module("finance")
async def create_product_rate(
    plan_id: UUID,
    rate_in: CommissionProductRateCreate,
    db: DB,
    current_user: User = Depends(get_current_user),
):
    """Add product-specific commission rate to a plan."""
    plan_result = await db.execute(
        select(CommissionPlan).where(CommissionPlan.id == plan_id)
    )
    if not plan_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Commission plan not found")

    rate = CommissionProductRate(
        plan_id=plan_id,
        **rate_in.model_dump(),
        created_by=current_user.id,
    )

    db.add(rate)
    await db.commit()
    await db.refresh(rate)

    return rate


# ==================== Commission Earners ====================

@router.post("/earners", response_model=CommissionEarnerResponse, status_code=status.HTTP_201_CREATED)
@require_module("finance")
async def create_commission_earner(
    earner_in: CommissionEarnerCreate,
    db: DB,
    current_user: User = Depends(get_current_user),
):
    """Register a commission earner (salesperson, affiliate, etc.)."""
    # Generate earner code
    count_result = await db.execute(select(func.count(CommissionEarner.id)))
    count = count_result.scalar() or 0

    prefix_map = {
        "SALES_REP": "SRP",
        "DEALER": "DLR",
        "DISTRIBUTOR": "DST",
        "AFFILIATE": "AFF",
        "INFLUENCER": "INF",
    }
    prefix = prefix_map.get(earner_in.earner_type, "ERN")
    earner_code = f"{prefix}-{str(count + 1).zfill(5)}"

    earner = CommissionEarner(
        earner_code=earner_code,
        **earner_in.model_dump(),
        created_by=current_user.id,
    )

    db.add(earner)
    await db.commit()
    await db.refresh(earner)

    return earner


@router.get("/earners", response_model=List[CommissionEarnerResponse])
@require_module("finance")
async def list_commission_earners(
    db: DB,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    earner_type: Optional[str] = None,
    plan_id: Optional[UUID] = None,
    is_active: bool = True,
    current_user: User = Depends(get_current_user),
):
    """List commission earners."""
    query = select(CommissionEarner)

    filters = []
    if earner_type:
        filters.append(CommissionEarner.earner_type == earner_type)
    if plan_id:
        filters.append(CommissionEarner.plan_id == plan_id)
    if is_active is not None:
        filters.append(CommissionEarner.is_active == is_active)

    if filters:
        query = query.where(and_(*filters))

    query = query.order_by(CommissionEarner.created_at.desc()).offset(skip).limit(limit)
    result = await db.execute(query)
    earners = result.scalars().all()

    return [CommissionEarnerResponse.model_validate(e) for e in earners]


@router.get("/earners/{earner_id}", response_model=CommissionEarnerResponse)
@require_module("finance")
async def get_commission_earner(
    earner_id: UUID,
    db: DB,
    current_user: User = Depends(get_current_user),
):
    """Get commission earner by ID."""
    result = await db.execute(
        select(CommissionEarner).where(CommissionEarner.id == earner_id)
    )
    earner = result.scalar_one_or_none()

    if not earner:
        raise HTTPException(status_code=404, detail="Commission earner not found")

    return earner


# ==================== Commission Transactions ====================

@router.post("/transactions", response_model=CommissionTransactionResponse, status_code=status.HTTP_201_CREATED)
@require_module("finance")
async def create_commission_transaction(
    transaction_in: CommissionTransactionCreate,
    db: DB,
    current_user: User = Depends(get_current_user),
):
    """Record a commission transaction."""
    # Verify earner
    earner_result = await db.execute(
        select(CommissionEarner).where(CommissionEarner.id == transaction_in.earner_id)
    )
    earner = earner_result.scalar_one_or_none()
    if not earner:
        raise HTTPException(status_code=404, detail="Commission earner not found")

    # Generate transaction number
    today = date.today()
    count_result = await db.execute(
        select(func.count(CommissionTransaction.id)).where(
            func.date(CommissionTransaction.created_at) == today
        )
    )
    count = count_result.scalar() or 0
    transaction_number = f"CMT-{today.strftime('%Y%m%d')}-{str(count + 1).zfill(4)}"

    transaction = CommissionTransaction(
        transaction_number=transaction_number,
        **transaction_in.model_dump(),
        created_by=current_user.id,
    )

    db.add(transaction)

    # Update earner totals
    earner.total_earned += transaction_in.commission_amount
    earner.pending_amount += transaction_in.commission_amount

    await db.commit()
    await db.refresh(transaction)

    return transaction


@router.get("/transactions", response_model=CommissionTransactionListResponse)
@require_module("finance")
async def list_commission_transactions(
    db: DB,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    earner_id: Optional[UUID] = None,
    status: Optional[CommissionStatus] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    current_user: User = Depends(get_current_user),
):
    """List commission transactions."""
    query = select(CommissionTransaction)
    count_query = select(func.count(CommissionTransaction.id))
    amount_query = select(func.coalesce(func.sum(CommissionTransaction.commission_amount), 0))

    filters = []
    if earner_id:
        filters.append(CommissionTransaction.earner_id == earner_id)
    if status:
        filters.append(CommissionTransaction.status == status)
    if start_date:
        filters.append(CommissionTransaction.transaction_date >= start_date)
    if end_date:
        filters.append(CommissionTransaction.transaction_date <= end_date)

    if filters:
        query = query.where(and_(*filters))
        count_query = count_query.where(and_(*filters))
        amount_query = amount_query.where(and_(*filters))

    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    total_amount_result = await db.execute(amount_query)
    total_amount = total_amount_result.scalar() or Decimal("0")

    query = query.order_by(CommissionTransaction.transaction_date.desc()).offset(skip).limit(limit)
    result = await db.execute(query)
    transactions = result.scalars().all()

    return CommissionTransactionListResponse(
        items=[CommissionTransactionResponse.model_validate(t) for t in transactions],
        total=total,
        total_amount=total_amount,
        skip=skip,
        limit=limit
    )


@router.post("/transactions/{transaction_id}/approve", response_model=CommissionTransactionResponse)
@require_module("finance")
async def approve_commission_transaction(
    transaction_id: UUID,
    db: DB,
    current_user: User = Depends(get_current_user),
):
    """Approve a pending commission transaction."""
    result = await db.execute(
        select(CommissionTransaction).where(CommissionTransaction.id == transaction_id)
    )
    transaction = result.scalar_one_or_none()

    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")

    if transaction.status != CommissionStatus.PENDING:
        raise HTTPException(status_code=400, detail="Transaction is not pending")

    transaction.status = CommissionStatus.APPROVED.value
    transaction.approved_by = current_user.id
    transaction.approved_at = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(transaction)

    return transaction


# ==================== Commission Payouts ====================

@router.post("/payouts", response_model=CommissionPayoutResponse, status_code=status.HTTP_201_CREATED)
@require_module("finance")
async def create_commission_payout(
    payout_in: CommissionPayoutCreate,
    db: DB,
    current_user: User = Depends(get_current_user),
):
    """Create a commission payout."""
    # Verify earner
    earner_result = await db.execute(
        select(CommissionEarner).where(CommissionEarner.id == payout_in.earner_id)
    )
    earner = earner_result.scalar_one_or_none()
    if not earner:
        raise HTTPException(status_code=404, detail="Commission earner not found")

    # Generate payout number
    today = date.today()
    count_result = await db.execute(
        select(func.count(CommissionPayout.id)).where(
            func.date(CommissionPayout.created_at) == today
        )
    )
    count = count_result.scalar() or 0
    payout_number = f"PAY-{today.strftime('%Y%m%d')}-{str(count + 1).zfill(4)}"

    # Get approved transactions not yet paid
    transactions_query = select(CommissionTransaction).where(
        and_(
            CommissionTransaction.earner_id == payout_in.earner_id,
            CommissionTransaction.status == CommissionStatus.APPROVED,
            CommissionTransaction.payout_id.is_(None),
        )
    )

    if payout_in.period_start:
        transactions_query = transactions_query.where(
            CommissionTransaction.transaction_date >= payout_in.period_start
        )
    if payout_in.period_end:
        transactions_query = transactions_query.where(
            CommissionTransaction.transaction_date <= payout_in.period_end
        )

    transactions_result = await db.execute(transactions_query)
    transactions = transactions_result.scalars().all()

    if not transactions:
        raise HTTPException(status_code=400, detail="No approved transactions found for payout")

    # Calculate totals
    gross_amount = sum(t.commission_amount for t in transactions)
    tds_amount = gross_amount * (payout_in.tds_rate / 100) if payout_in.tds_rate else Decimal("0")
    net_amount = gross_amount - tds_amount - (payout_in.deductions or Decimal("0"))

    payout = CommissionPayout(
        payout_number=payout_number,
        earner_id=payout_in.earner_id,
        period_start=payout_in.period_start,
        period_end=payout_in.period_end,
        gross_amount=gross_amount,
        tds_rate=payout_in.tds_rate or Decimal("0"),
        tds_amount=tds_amount,
        deductions=payout_in.deductions or Decimal("0"),
        net_amount=net_amount,
        payment_mode=payout_in.payment_mode,
        bank_account=payout_in.bank_account,
        remarks=payout_in.remarks,
        created_by=current_user.id,
    )

    db.add(payout)
    await db.flush()

    # Create payout lines and update transactions
    for transaction in transactions:
        line = CommissionPayoutLine(
            payout_id=payout.id,
            transaction_id=transaction.id,
            amount=transaction.commission_amount,
        )
        db.add(line)

        transaction.status = CommissionStatus.PAID.value
        transaction.payout_id = payout.id
        transaction.paid_at = datetime.now(timezone.utc)

    # Update earner
    earner.pending_amount -= gross_amount
    earner.paid_amount += net_amount
    earner.last_payout_date = date.today()

    await db.commit()

    # Load full payout
    result = await db.execute(
        select(CommissionPayout)
        .options(selectinload(CommissionPayout.lines))
        .where(CommissionPayout.id == payout.id)
    )
    payout = result.scalar_one()

    return payout


@router.get("/payouts", response_model=CommissionPayoutListResponse)
@require_module("finance")
async def list_commission_payouts(
    db: DB,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    earner_id: Optional[UUID] = None,
    status: Optional[PayoutStatus] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    current_user: User = Depends(get_current_user),
):
    """List commission payouts."""
    query = select(CommissionPayout)
    count_query = select(func.count(CommissionPayout.id))
    amount_query = select(func.coalesce(func.sum(CommissionPayout.net_amount), 0))

    filters = []
    if earner_id:
        filters.append(CommissionPayout.earner_id == earner_id)
    if status:
        filters.append(CommissionPayout.status == status)
    if start_date:
        filters.append(func.date(CommissionPayout.created_at) >= start_date)
    if end_date:
        filters.append(func.date(CommissionPayout.created_at) <= end_date)

    if filters:
        query = query.where(and_(*filters))
        count_query = count_query.where(and_(*filters))
        amount_query = amount_query.where(and_(*filters))

    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    total_amount_result = await db.execute(amount_query)
    total_amount = total_amount_result.scalar() or Decimal("0")

    query = query.order_by(CommissionPayout.created_at.desc()).offset(skip).limit(limit)
    result = await db.execute(query)
    payouts = result.scalars().all()

    return CommissionPayoutListResponse(
        items=[CommissionPayoutResponse.model_validate(p) for p in payouts],
        total=total,
        total_amount=total_amount,
        skip=skip,
        limit=limit
    )


@router.post("/payouts/{payout_id}/process", response_model=CommissionPayoutResponse)
@require_module("finance")
async def process_commission_payout(
    payout_id: UUID,
    payment_reference: str,
    payment_date: date,
    db: DB,
    current_user: User = Depends(get_current_user),
):
    """Mark payout as processed (payment made)."""
    result = await db.execute(
        select(CommissionPayout).where(CommissionPayout.id == payout_id)
    )
    payout = result.scalar_one_or_none()

    if not payout:
        raise HTTPException(status_code=404, detail="Payout not found")

    if payout.status != PayoutStatus.PENDING:
        raise HTTPException(status_code=400, detail="Payout is not pending")

    payout.status = PayoutStatus.PROCESSED.value
    payout.payment_reference = payment_reference
    payout.payment_date = payment_date
    payout.processed_by = current_user.id
    payout.processed_at = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(payout)

    return payout


# ==================== Affiliate Referrals ====================

@router.post("/affiliates/referrals", response_model=AffiliateReferralResponse, status_code=status.HTTP_201_CREATED)
@require_module("finance")
async def create_affiliate_referral(
    referral_in: AffiliateReferralCreate,
    db: DB,
    current_user: User = Depends(get_current_user),
):
    """Record an affiliate referral."""
    # Generate referral code
    import secrets

    referral_code = secrets.token_urlsafe(8).upper()

    referral = AffiliateReferral(
        referral_code=referral_code,
        **referral_in.model_dump(),
        created_by=current_user.id,
    )

    db.add(referral)
    await db.commit()
    await db.refresh(referral)

    return referral


@router.get("/affiliates/referrals", response_model=List[AffiliateReferralResponse])
@require_module("finance")
async def list_affiliate_referrals(
    db: DB,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    affiliate_id: Optional[UUID] = None,
    is_converted: Optional[bool] = None,
    current_user: User = Depends(get_current_user),
):
    """List affiliate referrals."""
    query = select(AffiliateReferral)

    filters = []
    if affiliate_id:
        filters.append(AffiliateReferral.affiliate_id == affiliate_id)
    if is_converted is not None:
        filters.append(AffiliateReferral.is_converted == is_converted)

    if filters:
        query = query.where(and_(*filters))

    query = query.order_by(AffiliateReferral.created_at.desc()).offset(skip).limit(limit)
    result = await db.execute(query)
    referrals = result.scalars().all()

    return [AffiliateReferralResponse.model_validate(r) for r in referrals]


@router.post("/affiliates/referrals/{referral_id}/convert", response_model=AffiliateReferralResponse)
@require_module("finance")
async def convert_affiliate_referral(
    referral_id: UUID,
    order_id: UUID,
    order_value: Decimal,
    db: DB,
    current_user: User = Depends(get_current_user),
):
    """Mark referral as converted and calculate commission."""
    result = await db.execute(
        select(AffiliateReferral).where(AffiliateReferral.id == referral_id)
    )
    referral = result.scalar_one_or_none()

    if not referral:
        raise HTTPException(status_code=404, detail="Referral not found")

    if referral.is_converted:
        raise HTTPException(status_code=400, detail="Referral already converted")

    # Get affiliate's commission plan
    earner_result = await db.execute(
        select(CommissionEarner).where(CommissionEarner.id == referral.affiliate_id)
    )
    earner = earner_result.scalar_one_or_none()

    commission_amount = Decimal("0")
    if earner and earner.plan_id:
        plan_result = await db.execute(
            select(CommissionPlan).where(CommissionPlan.id == earner.plan_id)
        )
        plan = plan_result.scalar_one_or_none()
        if plan:
            if plan.calculation_basis == CalculationBasis.PERCENTAGE:
                commission_amount = order_value * (plan.default_rate / 100)
            else:
                commission_amount = plan.default_rate

    referral.is_converted = True
    referral.converted_at = datetime.now(timezone.utc)
    referral.order_id = order_id
    referral.order_value = order_value
    referral.commission_amount = commission_amount

    # Create commission transaction
    if commission_amount > 0 and earner:
        today = date.today()
        count_result = await db.execute(
            select(func.count(CommissionTransaction.id)).where(
                func.date(CommissionTransaction.created_at) == today
            )
        )
        count = count_result.scalar() or 0

        transaction = CommissionTransaction(
            transaction_number=f"CMT-{today.strftime('%Y%m%d')}-{str(count + 1).zfill(4)}",
            earner_id=earner.id,
            plan_id=earner.plan_id,
            transaction_date=today,
            reference_type="AFFILIATE_REFERRAL",
            reference_id=referral.id,
            reference_number=referral.referral_code,
            base_amount=order_value,
            commission_rate=plan.default_rate if plan else Decimal("0"),
            commission_amount=commission_amount,
            status=CommissionStatus.PENDING,
            created_by=current_user.id,
        )
        db.add(transaction)

        earner.total_earned += commission_amount
        earner.pending_amount += commission_amount

    await db.commit()
    await db.refresh(referral)

    return referral


# ==================== Reports ====================

@router.get("/reports/summary")
@require_module("finance")
async def get_commission_summary(
    start_date: date,
    end_date: date,
    db: DB,
    earner_type: Optional[str] = None,
    current_user: User = Depends(get_current_user),
):
    """Get commission summary report."""
    base_filter = and_(
        CommissionTransaction.transaction_date >= start_date,
        CommissionTransaction.transaction_date <= end_date,
    )

    # Total earned
    total_query = select(
        func.count(CommissionTransaction.id).label("count"),
        func.coalesce(func.sum(CommissionTransaction.commission_amount), 0).label("amount"),
    ).where(base_filter)

    total_result = await db.execute(total_query)
    total = total_result.one()

    # By status
    status_query = select(
        CommissionTransaction.status,
        func.count(CommissionTransaction.id).label("count"),
        func.coalesce(func.sum(CommissionTransaction.commission_amount), 0).label("amount"),
    ).where(base_filter).group_by(CommissionTransaction.status)

    status_result = await db.execute(status_query)
    by_status = {
        row.status: {"count": row.count, "amount": float(row.amount)}
        for row in status_result.all()
    }

    # By plan
    plan_query = select(
        CommissionPlan.name,
        func.count(CommissionTransaction.id).label("count"),
        func.coalesce(func.sum(CommissionTransaction.commission_amount), 0).label("amount"),
    ).join(
        CommissionPlan, CommissionTransaction.plan_id == CommissionPlan.id
    ).where(base_filter).group_by(CommissionPlan.name)

    plan_result = await db.execute(plan_query)
    by_plan = [
        {"plan": row.name, "count": row.count, "amount": float(row.amount)}
        for row in plan_result.all()
    ]

    # Payouts in period
    payout_query = select(
        func.count(CommissionPayout.id).label("count"),
        func.coalesce(func.sum(CommissionPayout.net_amount), 0).label("amount"),
    ).where(
        and_(
            func.date(CommissionPayout.created_at) >= start_date,
            func.date(CommissionPayout.created_at) <= end_date,
        )
    )

    payout_result = await db.execute(payout_query)
    payouts = payout_result.one()

    return {
        "period_start": start_date.isoformat(),
        "period_end": end_date.isoformat(),
        "total_transactions": total.count,
        "total_commission": float(total.amount),
        "by_status": by_status,
        "by_plan": by_plan,
        "payouts": {
            "count": payouts.count,
            "amount": float(payouts.amount),
        },
        "pending_payout": float(by_status.get("approved", {}).get("amount", 0)),
    }


@router.get("/reports/earner-performance")
@require_module("finance")
async def get_earner_performance(
    start_date: date,
    end_date: date,
    db: DB,
    earner_id: Optional[UUID] = None,
    top_n: int = Query(10, ge=1, le=100),
    current_user: User = Depends(get_current_user),
):
    """Get top earner performance report."""
    query = select(
        CommissionEarner.id,
        CommissionEarner.earner_code,
        CommissionEarner.name,
        CommissionEarner.earner_type,
        func.count(CommissionTransaction.id).label("transaction_count"),
        func.coalesce(func.sum(CommissionTransaction.base_amount), 0).label("sales_value"),
        func.coalesce(func.sum(CommissionTransaction.commission_amount), 0).label("commission_earned"),
    ).join(
        CommissionTransaction, CommissionTransaction.earner_id == CommissionEarner.id
    ).where(
        and_(
            CommissionTransaction.transaction_date >= start_date,
            CommissionTransaction.transaction_date <= end_date,
        )
    ).group_by(
        CommissionEarner.id,
        CommissionEarner.earner_code,
        CommissionEarner.name,
        CommissionEarner.earner_type,
    ).order_by(
        func.sum(CommissionTransaction.commission_amount).desc()
    ).limit(top_n)

    if earner_id:
        query = query.where(CommissionEarner.id == earner_id)

    result = await db.execute(query)
    earners = result.all()

    return {
        "period_start": start_date.isoformat(),
        "period_end": end_date.isoformat(),
        "earners": [
            {
                "earner_id": str(row.id),
                "earner_code": row.earner_code,
                "name": row.name,
                "earner_type": row.earner_type,
                "transaction_count": row.transaction_count,
                "sales_value": float(row.sales_value),
                "commission_earned": float(row.commission_earned),
            }
            for row in earners
        ],
    }
