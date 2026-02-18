"""API endpoints for Dealer/Distributor management."""
from typing import Optional, List
from uuid import UUID
from datetime import date, datetime, timezone
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy import select, func, and_, or_, extract, case, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.dealer import (
    Dealer, DealerType, DealerStatus, DealerTier, CreditStatus,
    DealerPricing, DealerTierPricing, DealerCreditLedger, TransactionType,
    DealerTarget, DealerScheme, SchemeType, DealerSchemeApplication,
)
from app.models.user import User
from app.schemas.dealer import (
    # Dealer
    DealerCreate, DealerUpdate, DealerResponse, DealerBrief, DealerListResponse,
    # Pricing
    DealerPricingCreate, DealerPricingResponse,
    DealerTierPricingCreate, DealerTierPricingResponse,
    # Credit Ledger
    DealerCreditLedgerCreate, DealerCreditLedgerResponse, DealerCreditLedgerListResponse,
    # Target
    DealerTargetCreate, DealerTargetUpdate, DealerTargetResponse,
    # Scheme
    DealerSchemeCreate, DealerSchemeResponse, DealerSchemeListResponse,
    DealerSchemeApplicationCreate, DealerSchemeApplicationResponse,
    # Reports
    DealerPerformanceResponse, DealerAgingResponse,
    # DMS
    DMSDashboardResponse, DMSDashboardSummary, DMSRegionData, DMSTierData,
    DMSMonthlyTrend, DMSTopPerformer, DMSCreditAlert, DMSRecentOrder,
    DMSOrderCreate, DMSOrderResponse, DMSOrderItemResponse, DMSOrderListResponse,
)
from app.api.deps import DB, CurrentUser, get_current_user, require_permissions
from app.services.audit_service import AuditService
from app.core.module_decorators import require_module

router = APIRouter()


# ==================== Dealer CRUD ====================

@router.post("", response_model=DealerResponse, status_code=status.HTTP_201_CREATED)
@require_module("sales_distribution")
async def create_dealer(
    dealer_in: DealerCreate,
    db: DB,
    current_user: User = Depends(get_current_user),
):
    """Create a new dealer/distributor."""
    # Check for duplicate GSTIN
    if dealer_in.gstin:
        existing = await db.execute(
            select(Dealer).where(Dealer.gstin == dealer_in.gstin)
        )
        if existing.scalar_one_or_none():
            raise HTTPException(
                status_code=400,
                detail=f"Dealer with GSTIN {dealer_in.gstin} already exists"
            )

    # Generate dealer code
    count_result = await db.execute(select(func.count(Dealer.id)))
    count = count_result.scalar() or 0

    prefix_map = {
        DealerType.DISTRIBUTOR: "DST",
        DealerType.DEALER: "DLR",
        DealerType.RETAILER: "RTL",
        DealerType.FRANCHISE: "FRN",
        DealerType.INSTITUTIONAL: "INS",
    }
    prefix = prefix_map.get(dealer_in.dealer_type, "DLR")
    dealer_code = f"{prefix}-{str(count + 1).zfill(5)}"

    dealer = Dealer(
        **dealer_in.model_dump(exclude={"opening_balance"}),
        dealer_code=dealer_code,
        outstanding_amount=dealer_in.opening_balance,
    )

    db.add(dealer)
    await db.commit()
    await db.refresh(dealer)

    # Create opening balance ledger entry
    if dealer_in.opening_balance != 0:
        ledger = DealerCreditLedger(
            dealer_id=dealer.id,
            transaction_type=TransactionType.OPENING_BALANCE,
            transaction_date=date.today(),
            reference_type="OPENING",
            reference_number=dealer_code,
            debit_amount=dealer_in.opening_balance if dealer_in.opening_balance > 0 else Decimal("0"),
            credit_amount=abs(dealer_in.opening_balance) if dealer_in.opening_balance < 0 else Decimal("0"),
            balance=dealer_in.opening_balance,
            remarks="Opening balance",
        )
        db.add(ledger)
        await db.commit()

    return dealer


@router.get("", response_model=DealerListResponse)
@require_module("sales_distribution")
async def list_dealers(
    db: DB,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    search: Optional[str] = None,
    dealer_type: Optional[DealerType] = None,
    status: Optional[DealerStatus] = None,
    tier: Optional[DealerTier] = None,
    region_id: Optional[UUID] = None,
    city: Optional[str] = None,
    credit_status: Optional[CreditStatus] = None,
    current_user: User = Depends(get_current_user),
):
    """List dealers with filters."""
    query = select(Dealer)
    count_query = select(func.count(Dealer.id))

    filters = []
    if search:
        filters.append(or_(
            Dealer.name.ilike(f"%{search}%"),
            Dealer.dealer_code.ilike(f"%{search}%"),
            Dealer.gstin.ilike(f"%{search}%"),
        ))
    if dealer_type:
        filters.append(Dealer.dealer_type == dealer_type)
    if status:
        filters.append(Dealer.status == status)
    if tier:
        filters.append(Dealer.tier == tier)
    if region_id:
        filters.append(Dealer.region_id == region_id)
    if city:
        filters.append(Dealer.city.ilike(f"%{city}%"))
    if credit_status:
        filters.append(Dealer.credit_status == credit_status)

    if filters:
        query = query.where(and_(*filters))
        count_query = count_query.where(and_(*filters))

    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    query = query.order_by(Dealer.created_at.desc()).offset(skip).limit(limit)
    result = await db.execute(query)
    dealers = result.scalars().all()

    return DealerListResponse(
        items=[DealerBrief.model_validate(d) for d in dealers],
        total=total,
        skip=skip,
        limit=limit
    )


@router.get("/dropdown", response_model=List[DealerBrief])
@require_module("sales_distribution")
async def get_dealers_dropdown(
    db: DB,
    dealer_type: Optional[DealerType] = None,
    active_only: bool = True,
    current_user: User = Depends(get_current_user),
):
    """Get dealers for dropdown selection."""
    query = select(Dealer)

    if active_only:
        query = query.where(Dealer.status == DealerStatus.ACTIVE)
    if dealer_type:
        query = query.where(Dealer.dealer_type == dealer_type)

    query = query.order_by(Dealer.name)
    result = await db.execute(query)
    dealers = result.scalars().all()

    return [DealerBrief.model_validate(d) for d in dealers]


@router.get("/{dealer_id}", response_model=DealerResponse)
@require_module("sales_distribution")
async def get_dealer(
    dealer_id: UUID,
    db: DB,
    current_user: User = Depends(get_current_user),
):
    """Get dealer by ID."""
    result = await db.execute(
        select(Dealer).where(Dealer.id == dealer_id)
    )
    dealer = result.scalar_one_or_none()

    if not dealer:
        raise HTTPException(status_code=404, detail="Dealer not found")

    return dealer


@router.put("/{dealer_id}", response_model=DealerResponse)
@require_module("sales_distribution")
async def update_dealer(
    dealer_id: UUID,
    dealer_in: DealerUpdate,
    db: DB,
    current_user: User = Depends(get_current_user),
):
    """Update dealer details."""
    result = await db.execute(
        select(Dealer).where(Dealer.id == dealer_id)
    )
    dealer = result.scalar_one_or_none()

    if not dealer:
        raise HTTPException(status_code=404, detail="Dealer not found")

    update_data = dealer_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(dealer, field, value)

    dealer.updated_by = current_user.id

    await db.commit()
    await db.refresh(dealer)

    return dealer


@router.post("/{dealer_id}/approve", response_model=DealerResponse)
@require_module("sales_distribution")
async def approve_dealer(
    dealer_id: UUID,
    db: DB,
    current_user: User = Depends(get_current_user),
):
    """Approve a pending dealer."""
    result = await db.execute(
        select(Dealer).where(Dealer.id == dealer_id)
    )
    dealer = result.scalar_one_or_none()

    if not dealer:
        raise HTTPException(status_code=404, detail="Dealer not found")

    if dealer.status != DealerStatus.PENDING_APPROVAL:
        raise HTTPException(status_code=400, detail="Dealer is not pending approval")

    dealer.status = DealerStatus.ACTIVE.value
    dealer.approved_by = current_user.id
    dealer.approved_at = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(dealer)

    return dealer


# ==================== Dealer Pricing ====================

@router.get("/{dealer_id}/pricing", response_model=List[DealerPricingResponse])
@require_module("sales_distribution")
async def get_dealer_pricing(
    dealer_id: UUID,
    db: DB,
    current_user: User = Depends(get_current_user),
):
    """Get special pricing for a dealer."""
    result = await db.execute(
        select(DealerPricing)
        .where(DealerPricing.dealer_id == dealer_id)
        .order_by(DealerPricing.created_at.desc())
    )
    pricing = result.scalars().all()
    return [DealerPricingResponse.model_validate(p) for p in pricing]


@router.post("/{dealer_id}/pricing", response_model=DealerPricingResponse, status_code=status.HTTP_201_CREATED)
@require_module("sales_distribution")
async def create_dealer_pricing(
    dealer_id: UUID,
    pricing_in: DealerPricingCreate,
    db: DB,
    current_user: User = Depends(get_current_user),
):
    """Create special pricing for a dealer."""
    # Verify dealer
    dealer_result = await db.execute(
        select(Dealer).where(Dealer.id == dealer_id)
    )
    if not dealer_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Dealer not found")

    # Check for existing pricing
    existing = await db.execute(
        select(DealerPricing).where(
            and_(
                DealerPricing.dealer_id == dealer_id,
                DealerPricing.product_id == pricing_in.product_id,
                DealerPricing.is_active == True,
            )
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=400,
            detail="Active pricing already exists for this product"
        )

    pricing = DealerPricing(
        dealer_id=dealer_id,
        **pricing_in.model_dump(),
        created_by=current_user.id,
    )

    db.add(pricing)
    await db.commit()
    await db.refresh(pricing)

    return pricing


# ==================== Tier Pricing ====================

@router.get("/tiers/pricing", response_model=List[DealerTierPricingResponse])
@require_module("sales_distribution")
async def get_tier_pricing(
    db: DB,
    tier: Optional[str] = None,
    product_id: Optional[UUID] = None,
    current_user: User = Depends(get_current_user),
):
    """Get tier-based pricing."""
    query = select(DealerTierPricing)

    if tier:
        query = query.where(DealerTierPricing.tier == tier)  # VARCHAR comparison
    if product_id:
        query = query.where(DealerTierPricing.product_id == product_id)

    query = query.order_by(DealerTierPricing.tier, DealerTierPricing.product_id)
    result = await db.execute(query)
    pricing = result.scalars().all()

    return [DealerTierPricingResponse.model_validate(p) for p in pricing]


@router.post("/tiers/pricing", response_model=DealerTierPricingResponse, status_code=status.HTTP_201_CREATED)
@require_module("sales_distribution")
async def create_tier_pricing(
    pricing_in: DealerTierPricingCreate,
    db: DB,
    current_user: User = Depends(get_current_user),
):
    """Create tier-based pricing."""
    # Check for existing
    existing = await db.execute(
        select(DealerTierPricing).where(
            and_(
                DealerTierPricing.tier == pricing_in.tier,
                DealerTierPricing.product_id == pricing_in.product_id,
                DealerTierPricing.is_active == True,
            )
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=400,
            detail="Active tier pricing already exists for this product"
        )

    pricing = DealerTierPricing(
        **pricing_in.model_dump(),
    )

    db.add(pricing)
    await db.commit()
    await db.refresh(pricing)

    return pricing


# ==================== Credit Ledger ====================

@router.get("/{dealer_id}/ledger", response_model=DealerCreditLedgerListResponse)
@require_module("sales_distribution")
async def get_dealer_ledger(
    dealer_id: UUID,
    db: DB,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    current_user: User = Depends(get_current_user),
):
    """Get dealer credit ledger."""
    # Verify dealer
    dealer_result = await db.execute(
        select(Dealer).where(Dealer.id == dealer_id)
    )
    dealer = dealer_result.scalar_one_or_none()
    if not dealer:
        raise HTTPException(status_code=404, detail="Dealer not found")

    query = select(DealerCreditLedger).where(DealerCreditLedger.dealer_id == dealer_id)
    count_query = select(func.count(DealerCreditLedger.id)).where(
        DealerCreditLedger.dealer_id == dealer_id
    )

    if start_date:
        query = query.where(DealerCreditLedger.transaction_date >= start_date)
        count_query = count_query.where(DealerCreditLedger.transaction_date >= start_date)
    if end_date:
        query = query.where(DealerCreditLedger.transaction_date <= end_date)
        count_query = count_query.where(DealerCreditLedger.transaction_date <= end_date)

    # Get totals
    totals_query = select(
        func.coalesce(func.sum(DealerCreditLedger.debit_amount), 0).label("total_debit"),
        func.coalesce(func.sum(DealerCreditLedger.credit_amount), 0).label("total_credit"),
    ).where(DealerCreditLedger.dealer_id == dealer_id)

    totals_result = await db.execute(totals_query)
    totals = totals_result.one()

    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    query = query.order_by(
        DealerCreditLedger.transaction_date.desc(),
        DealerCreditLedger.created_at.desc()
    ).offset(skip).limit(limit)

    result = await db.execute(query)
    entries = result.scalars().all()

    return DealerCreditLedgerListResponse(
        items=[DealerCreditLedgerResponse.model_validate(e) for e in entries],
        total=total,
        total_debit=totals.total_debit,
        total_credit=totals.total_credit,
        closing_balance=dealer.outstanding_amount,
        skip=skip,
        limit=limit
    )


@router.post("/{dealer_id}/payment", response_model=DealerCreditLedgerResponse)
@require_module("sales_distribution")
async def record_dealer_payment(
    dealer_id: UUID,
    payment_in: DealerCreditLedgerCreate,
    db: DB,
    current_user: User = Depends(get_current_user),
):
    """Record payment from dealer."""
    # Verify dealer
    dealer_result = await db.execute(
        select(Dealer).where(Dealer.id == dealer_id)
    )
    dealer = dealer_result.scalar_one_or_none()
    if not dealer:
        raise HTTPException(status_code=404, detail="Dealer not found")

    new_balance = dealer.outstanding_amount - payment_in.credit_amount + payment_in.debit_amount

    ledger = DealerCreditLedger(
        dealer_id=dealer_id,
        transaction_type=payment_in.transaction_type,
        transaction_date=payment_in.transaction_date,
        reference_type=payment_in.reference_type,
        reference_number=payment_in.reference_number,
        reference_id=payment_in.reference_id,
        debit_amount=payment_in.debit_amount,
        credit_amount=payment_in.credit_amount,
        running_balance=new_balance,
        payment_mode=payment_in.payment_mode,
        payment_reference=payment_in.payment_reference,
        narration=payment_in.narration,
        created_by=current_user.id,
    )

    db.add(ledger)

    # Update dealer balance
    dealer.outstanding_amount = new_balance
    dealer.last_payment_date = payment_in.transaction_date

    # Update credit status based on utilization
    if dealer.credit_limit > 0 and new_balance > dealer.credit_limit * Decimal("0.9"):
        dealer.credit_status = CreditStatus.ON_HOLD.value
    elif dealer.credit_limit > 0 and new_balance > dealer.credit_limit * Decimal("0.75"):
        dealer.credit_status = CreditStatus.ACTIVE.value
    else:
        dealer.credit_status = CreditStatus.ACTIVE.value

    await db.commit()
    await db.refresh(ledger)

    return ledger


# ==================== Targets ====================

@router.get("/{dealer_id}/targets", response_model=List[DealerTargetResponse])
@require_module("sales_distribution")
async def get_dealer_targets(
    dealer_id: UUID,
    db: DB,
    year: Optional[int] = None,
    current_user: User = Depends(get_current_user),
):
    """Get dealer targets."""
    query = select(DealerTarget).where(DealerTarget.dealer_id == dealer_id)

    if year:
        query = query.where(DealerTarget.year == year)

    query = query.order_by(DealerTarget.year.desc(), DealerTarget.month.desc())
    result = await db.execute(query)
    targets = result.scalars().all()

    return [DealerTargetResponse.model_validate(t) for t in targets]


@router.post("/{dealer_id}/targets", response_model=DealerTargetResponse, status_code=status.HTTP_201_CREATED)
@require_module("sales_distribution")
async def create_dealer_target(
    dealer_id: UUID,
    target_in: DealerTargetCreate,
    db: DB,
    current_user: User = Depends(get_current_user),
):
    """Create/update dealer target for a month."""
    # Verify dealer
    dealer_result = await db.execute(
        select(Dealer).where(Dealer.id == dealer_id)
    )
    if not dealer_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Dealer not found")

    # Check for existing target
    existing = await db.execute(
        select(DealerTarget).where(
            and_(
                DealerTarget.dealer_id == dealer_id,
                DealerTarget.year == target_in.year,
                DealerTarget.month == target_in.month,
            )
        )
    )
    existing_target = existing.scalar_one_or_none()

    if existing_target:
        # Update existing
        existing_target.target_quantity = target_in.target_quantity
        existing_target.target_value = target_in.target_value
        existing_target.updated_by = current_user.id
        target = existing_target
    else:
        # Create new
        target = DealerTarget(
            dealer_id=dealer_id,
            **target_in.model_dump(),
            created_by=current_user.id,
        )
        db.add(target)

    await db.commit()
    await db.refresh(target)

    return target


# ==================== Schemes ====================

@router.get("/schemes", response_model=DealerSchemeListResponse)
@require_module("sales_distribution")
async def list_dealer_schemes(
    db: DB,
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=50),
    scheme_type: Optional[SchemeType] = None,
    is_active: bool = True,
    current_user: User = Depends(get_current_user),
):
    """List dealer schemes."""
    query = select(DealerScheme)
    count_query = select(func.count(DealerScheme.id))

    filters = []
    if scheme_type:
        filters.append(DealerScheme.scheme_type == scheme_type)
    if is_active:
        today = date.today()
        filters.append(DealerScheme.is_active == True)
        filters.append(DealerScheme.start_date <= today)
        filters.append(DealerScheme.end_date >= today)

    if filters:
        query = query.where(and_(*filters))
        count_query = count_query.where(and_(*filters))

    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    query = query.order_by(DealerScheme.start_date.desc()).offset(skip).limit(limit)
    result = await db.execute(query)
    schemes = result.scalars().all()

    return DealerSchemeListResponse(
        items=[DealerSchemeResponse.model_validate(s) for s in schemes],
        total=total,
        skip=skip,
        limit=limit
    )


@router.post("/schemes", response_model=DealerSchemeResponse, status_code=status.HTTP_201_CREATED)
@require_module("sales_distribution")
async def create_dealer_scheme(
    scheme_in: DealerSchemeCreate,
    db: DB,
    current_user: User = Depends(get_current_user),
):
    """Create a new dealer scheme."""
    # Generate scheme code
    count_result = await db.execute(select(func.count(DealerScheme.id)))
    count = count_result.scalar() or 0
    scheme_code = f"SCH-{date.today().strftime('%Y')}-{str(count + 1).zfill(4)}"

    scheme = DealerScheme(
        scheme_code=scheme_code,
        **scheme_in.model_dump(),
        created_by=current_user.id,
    )

    db.add(scheme)
    await db.commit()
    await db.refresh(scheme)

    return scheme


@router.post("/schemes/{scheme_id}/apply", response_model=DealerSchemeApplicationResponse)
@require_module("sales_distribution")
async def apply_scheme_to_dealer(
    scheme_id: UUID,
    application_in: DealerSchemeApplicationCreate,
    db: DB,
    current_user: User = Depends(get_current_user),
):
    """Apply scheme benefits to a dealer."""
    # Verify scheme
    scheme_result = await db.execute(
        select(DealerScheme).where(DealerScheme.id == scheme_id)
    )
    scheme = scheme_result.scalar_one_or_none()
    if not scheme:
        raise HTTPException(status_code=404, detail="Scheme not found")

    # Verify dealer
    dealer_result = await db.execute(
        select(Dealer).where(Dealer.id == application_in.dealer_id)
    )
    dealer = dealer_result.scalar_one_or_none()
    if not dealer:
        raise HTTPException(status_code=404, detail="Dealer not found")

    application = DealerSchemeApplication(
        scheme_id=scheme_id,
        dealer_id=application_in.dealer_id,
        achieved_value=application_in.achieved_value,
        achieved_quantity=application_in.achieved_quantity,
        benefit_earned=application_in.benefit_earned,
        benefit_type=application_in.benefit_type,
        status="APPROVED",
        approved_by=current_user.id,
        approved_at=datetime.now(timezone.utc),
        created_by=current_user.id,
    )

    db.add(application)
    await db.commit()
    await db.refresh(application)

    return application


# ==================== Reports ====================

@router.get("/reports/performance")
@require_module("sales_distribution")
async def get_dealer_performance_report(
    start_date: date,
    end_date: date,
    db: DB,
    dealer_id: Optional[UUID] = None,
    region_id: Optional[UUID] = None,
    tier: Optional[DealerTier] = None,
    current_user: User = Depends(get_current_user),
):
    """Get dealer performance report."""
    from app.models.order import Order, OrderStatus

    query = select(Dealer)

    filters = []
    if dealer_id:
        filters.append(Dealer.id == dealer_id)
    if region_id:
        filters.append(Dealer.region_id == region_id)
    if tier:
        filters.append(Dealer.tier == tier)

    if filters:
        query = query.where(and_(*filters))

    result = await db.execute(query)
    dealers = result.scalars().all()

    performance_data = []

    for dealer in dealers:
        # Get orders in period
        orders_query = select(
            func.count(Order.id).label("order_count"),
            func.coalesce(func.sum(Order.total_amount), 0).label("order_value"),
        ).where(
            and_(
                Order.dealer_id == dealer.id,
                Order.created_at >= start_date,
                Order.created_at <= end_date,
                Order.status.in_([OrderStatus.DELIVERED, OrderStatus.SHIPPED]),
            )
        )
        orders_result = await db.execute(orders_query)
        orders = orders_result.one()

        # Get targets for period
        targets_query = select(
            func.coalesce(func.sum(DealerTarget.target_value), 0).label("target_value"),
            func.coalesce(func.sum(DealerTarget.target_quantity), 0).label("target_qty"),
        ).where(
            and_(
                DealerTarget.dealer_id == dealer.id,
                DealerTarget.year >= start_date.year,
                DealerTarget.year <= end_date.year,
            )
        )
        targets_result = await db.execute(targets_query)
        targets = targets_result.one()

        achievement_pct = (
            (float(orders.order_value) / float(targets.target_value) * 100)
            if targets.target_value > 0 else 0
        )

        performance_data.append({
            "dealer_id": str(dealer.id),
            "dealer_code": dealer.dealer_code,
            "dealer_name": dealer.name,
            "tier": dealer.tier if dealer.tier else None,
            "order_count": orders.order_count,
            "order_value": float(orders.order_value),
            "target_value": float(targets.target_value),
            "achievement_percentage": round(achievement_pct, 2),
            "credit_limit": float(dealer.credit_limit),
            "current_balance": float(dealer.outstanding_amount),
            "available_credit": float(dealer.credit_limit - dealer.outstanding_amount),
        })

    return {
        "period_start": start_date.isoformat(),
        "period_end": end_date.isoformat(),
        "dealers": performance_data,
        "summary": {
            "total_dealers": len(performance_data),
            "total_order_value": sum(d["order_value"] for d in performance_data),
            "total_target_value": sum(d["target_value"] for d in performance_data),
            "avg_achievement": (
                sum(d["achievement_percentage"] for d in performance_data) / len(performance_data)
                if performance_data else 0
            ),
        }
    }


@router.get("/reports/aging")
@require_module("sales_distribution")
async def get_dealer_aging_report(
    db: DB,
    as_of_date: date = Query(default_factory=date.today),
    region_id: Optional[UUID] = None,
    current_user: User = Depends(get_current_user),
):
    """Get dealer aging report (Accounts Receivable)."""
    query = select(Dealer).where(Dealer.outstanding_amount > 0)

    if region_id:
        query = query.where(Dealer.region_id == region_id)

    result = await db.execute(query)
    dealers = result.scalars().all()

    aging_data = []
    summary_buckets = {"0-30": 0, "31-60": 0, "61-90": 0, "90+": 0}

    for dealer in dealers:
        # Get unsettled ledger entries
        ledger_query = select(DealerCreditLedger).where(
            and_(
                DealerCreditLedger.dealer_id == dealer.id,
                DealerCreditLedger.is_settled == False,
                DealerCreditLedger.debit_amount > 0,
            )
        )
        ledger_result = await db.execute(ledger_query)
        entries = ledger_result.scalars().all()

        buckets = {"0-30": Decimal("0"), "31-60": Decimal("0"), "61-90": Decimal("0"), "90+": Decimal("0")}

        for entry in entries:
            days = (as_of_date - entry.transaction_date).days
            amount = entry.debit_amount

            if days <= 30:
                buckets["0-30"] += amount
            elif days <= 60:
                buckets["31-60"] += amount
            elif days <= 90:
                buckets["61-90"] += amount
            else:
                buckets["90+"] += amount

        total = sum(buckets.values())
        if total > 0:
            aging_data.append({
                "dealer_id": str(dealer.id),
                "dealer_code": dealer.dealer_code,
                "dealer_name": dealer.name,
                "total_outstanding": float(total),
                "buckets": {k: float(v) for k, v in buckets.items()},
            })

            for k, v in buckets.items():
                summary_buckets[k] += float(v)

    return {
        "as_of_date": as_of_date.isoformat(),
        "dealers": aging_data,
        "summary": summary_buckets,
        "total_outstanding": sum(summary_buckets.values()),
    }


# ==================== DMS Dashboard ====================

@router.get("/dms/dashboard", response_model=DMSDashboardResponse)
@require_module("dms")
async def get_dms_dashboard(
    db: DB,
    current_user: User = Depends(get_current_user),
):
    """Get DMS Dashboard with KPIs, charts, and tables."""
    from app.models.order import Order, OrderStatus

    today = date.today()
    month_start = today.replace(day=1)

    # --- Summary KPIs ---
    total_result = await db.execute(select(func.count(Dealer.id)))
    total_distributors = total_result.scalar() or 0

    active_result = await db.execute(
        select(func.count(Dealer.id)).where(Dealer.status == DealerStatus.ACTIVE.value)
    )
    active_distributors = active_result.scalar() or 0

    pending_result = await db.execute(
        select(func.count(Dealer.id)).where(Dealer.status == DealerStatus.PENDING_APPROVAL.value)
    )
    pending_approval = pending_result.scalar() or 0

    # Orders MTD (B2B only = orders with dealer_id)
    orders_mtd_result = await db.execute(
        select(
            func.count(Order.id).label("count"),
            func.coalesce(func.sum(Order.total_amount), 0).label("revenue"),
            func.coalesce(func.avg(Order.total_amount), 0).label("avg_value"),
        ).where(
            and_(
                Order.dealer_id.isnot(None),
                Order.created_at >= month_start,
            )
        )
    )
    orders_mtd = orders_mtd_result.one()

    # Collection MTD (credit payments)
    collection_result = await db.execute(
        select(
            func.coalesce(func.sum(DealerCreditLedger.credit_amount), 0)
        ).where(
            and_(
                DealerCreditLedger.transaction_date >= month_start,
                DealerCreditLedger.credit_amount > 0,
            )
        )
    )
    collection_mtd = collection_result.scalar() or Decimal("0")

    # Outstanding and overdue
    outstanding_result = await db.execute(
        select(
            func.coalesce(func.sum(Dealer.outstanding_amount), 0).label("outstanding"),
            func.coalesce(func.sum(Dealer.overdue_amount), 0).label("overdue"),
        )
    )
    outstanding_row = outstanding_result.one()

    # Average credit utilization
    credit_util_result = await db.execute(
        select(
            func.avg(
                case(
                    (Dealer.credit_limit > 0, (Dealer.outstanding_amount / Dealer.credit_limit) * 100),
                    else_=Decimal("0"),
                )
            )
        ).where(Dealer.status == DealerStatus.ACTIVE.value)
    )
    credit_util_avg = credit_util_result.scalar() or Decimal("0")

    summary = DMSDashboardSummary(
        total_distributors=total_distributors,
        active_distributors=active_distributors,
        pending_approval=pending_approval,
        total_orders_mtd=orders_mtd.count,
        revenue_mtd=orders_mtd.revenue,
        collection_mtd=collection_mtd,
        total_outstanding=outstanding_row.outstanding,
        total_overdue=outstanding_row.overdue,
        avg_order_value=orders_mtd.avg_value,
        credit_utilization_avg=round(credit_util_avg, 2),
    )

    # --- By Region ---
    region_result = await db.execute(
        select(
            Dealer.region,
            func.count(Dealer.id).label("count"),
            func.coalesce(func.sum(Dealer.outstanding_amount), 0).label("outstanding"),
        ).where(Dealer.region.isnot(None))
        .group_by(Dealer.region)
        .order_by(desc(func.count(Dealer.id)))
    )
    by_region = []
    for row in region_result.all():
        by_region.append(DMSRegionData(
            region=row.region or "Unknown",
            count=row.count,
            outstanding=row.outstanding,
        ))

    # --- By Tier ---
    tier_result = await db.execute(
        select(
            Dealer.tier,
            func.count(Dealer.id).label("count"),
        ).where(Dealer.tier.isnot(None))
        .group_by(Dealer.tier)
        .order_by(desc(func.count(Dealer.id)))
    )
    by_tier = [
        DMSTierData(tier=row.tier or "STANDARD", count=row.count)
        for row in tier_result.all()
    ]

    # --- Monthly Trend (last 12 months) ---
    twelve_months_ago = today.replace(day=1)
    try:
        twelve_months_ago = twelve_months_ago.replace(year=today.year - 1)
    except ValueError:
        twelve_months_ago = twelve_months_ago.replace(year=today.year - 1, day=28)

    trend_result = await db.execute(
        select(
            extract("year", Order.created_at).label("yr"),
            extract("month", Order.created_at).label("mo"),
            func.count(Order.id).label("orders"),
            func.coalesce(func.sum(Order.total_amount), 0).label("revenue"),
        ).where(
            and_(
                Order.dealer_id.isnot(None),
                Order.created_at >= twelve_months_ago,
            )
        )
        .group_by("yr", "mo")
        .order_by("yr", "mo")
    )
    monthly_trend = []
    for row in trend_result.all():
        month_str = f"{int(row.yr)}-{int(row.mo):02d}"
        monthly_trend.append(DMSMonthlyTrend(
            month=month_str,
            orders=row.orders,
            revenue=row.revenue,
        ))

    # --- Top 10 Performers (by revenue in current FY) ---
    fy_start = date(today.year if today.month >= 4 else today.year - 1, 4, 1)

    top_result = await db.execute(
        select(
            Dealer.id,
            Dealer.dealer_code,
            Dealer.name,
            func.count(Order.id).label("order_count"),
            func.coalesce(func.sum(Order.total_amount), 0).label("revenue"),
        )
        .join(Order, Order.dealer_id == Dealer.id)
        .where(Order.created_at >= fy_start)
        .group_by(Dealer.id, Dealer.dealer_code, Dealer.name)
        .order_by(desc(func.sum(Order.total_amount)))
        .limit(10)
    )
    top_performers = []
    for row in top_result.all():
        # Get target for achievement %
        target_result = await db.execute(
            select(func.coalesce(func.sum(DealerTarget.revenue_target), 0))
            .where(DealerTarget.dealer_id == row.id)
        )
        target_val = target_result.scalar() or Decimal("0")
        achievement = (float(row.revenue) / float(target_val) * 100) if target_val > 0 else 0

        top_performers.append(DMSTopPerformer(
            dealer_id=str(row.id),
            dealer_code=row.dealer_code,
            name=row.name,
            revenue=row.revenue,
            orders=row.order_count,
            achievement_pct=round(Decimal(str(achievement)), 1),
        ))

    # --- Credit Alerts (dealers > 80% utilization) ---
    alerts_result = await db.execute(
        select(Dealer).where(
            and_(
                Dealer.credit_limit > 0,
                Dealer.outstanding_amount > Dealer.credit_limit * Decimal("0.8"),
                Dealer.status == DealerStatus.ACTIVE.value,
            )
        ).order_by(desc(Dealer.outstanding_amount))
        .limit(20)
    )
    credit_alerts = []
    for dealer in alerts_result.scalars().all():
        utilization = (float(dealer.outstanding_amount) / float(dealer.credit_limit) * 100) if dealer.credit_limit > 0 else 0
        credit_alerts.append(DMSCreditAlert(
            dealer_id=str(dealer.id),
            dealer_code=dealer.dealer_code,
            name=dealer.name,
            outstanding=dealer.outstanding_amount,
            overdue=dealer.overdue_amount,
            credit_limit=dealer.credit_limit,
            utilization_pct=round(Decimal(str(utilization)), 1),
        ))

    # --- Recent B2B Orders ---
    recent_result = await db.execute(
        select(Order)
        .where(Order.dealer_id.isnot(None))
        .options(selectinload(Order.dealer))
        .order_by(Order.created_at.desc())
        .limit(10)
    )
    recent_orders = []
    for order in recent_result.scalars().all():
        recent_orders.append(DMSRecentOrder(
            order_id=str(order.id),
            order_number=order.order_number or "",
            dealer_name=order.dealer.name if order.dealer else "Unknown",
            amount=order.total_amount or Decimal("0"),
            status=order.status or "",
            date=order.created_at.strftime("%Y-%m-%d") if order.created_at else "",
        ))

    return DMSDashboardResponse(
        summary=summary,
        by_region=by_region,
        by_tier=by_tier,
        monthly_trend=monthly_trend,
        top_performers=top_performers,
        credit_alerts=credit_alerts,
        recent_orders=recent_orders,
    )


# ==================== DMS Orders ====================

@router.get("/dms/orders", response_model=DMSOrderListResponse)
@require_module("dms")
async def list_dms_orders(
    db: DB,
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=100),
    dealer_id: Optional[UUID] = None,
    status_filter: Optional[str] = Query(None, alias="status"),
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    current_user: User = Depends(get_current_user),
):
    """List B2B orders (orders with dealer_id)."""
    from app.models.order import Order

    query = select(Order).where(Order.dealer_id.isnot(None))
    count_query = select(func.count(Order.id)).where(Order.dealer_id.isnot(None))

    filters = []
    if dealer_id:
        filters.append(Order.dealer_id == dealer_id)
    if status_filter:
        filters.append(Order.status == status_filter)
    if date_from:
        filters.append(Order.created_at >= datetime.combine(date_from, datetime.min.time()))
    if date_to:
        filters.append(Order.created_at <= datetime.combine(date_to, datetime.max.time()))

    if filters:
        query = query.where(and_(*filters))
        count_query = count_query.where(and_(*filters))

    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    skip = (page - 1) * size
    query = (
        query.options(selectinload(Order.dealer))
        .order_by(Order.created_at.desc())
        .offset(skip)
        .limit(size)
    )
    result = await db.execute(query)
    orders = result.scalars().all()

    items = []
    for order in orders:
        items.append(DMSOrderResponse(
            id=str(order.id),
            order_number=order.order_number or "",
            dealer_id=str(order.dealer_id),
            dealer_name=order.dealer.name if order.dealer else "Unknown",
            dealer_code=order.dealer.dealer_code if order.dealer else "",
            subtotal=order.subtotal or Decimal("0"),
            tax_amount=order.tax_amount or Decimal("0"),
            discount_amount=order.discount_amount or Decimal("0"),
            total_amount=order.total_amount or Decimal("0"),
            status=order.status or "",
            payment_status=order.payment_status or "",
            created_at=order.created_at.isoformat() if order.created_at else "",
        ))

    return DMSOrderListResponse(items=items, total=total, page=page, size=size)


@router.post("/{dealer_id}/orders", response_model=DMSOrderResponse, status_code=status.HTTP_201_CREATED)
@require_module("dms")
async def create_dms_order(
    dealer_id: UUID,
    order_in: DMSOrderCreate,
    db: DB,
    current_user: User = Depends(get_current_user),
):
    """Create a B2B order for a dealer with auto-pricing and credit check."""
    from app.models.order import Order, OrderItem
    from app.models.product import Product, ProductVariant

    # Verify dealer
    dealer_result = await db.execute(
        select(Dealer).where(Dealer.id == dealer_id)
    )
    dealer = dealer_result.scalar_one_or_none()
    if not dealer:
        raise HTTPException(status_code=404, detail="Dealer not found")

    if dealer.status != DealerStatus.ACTIVE.value:
        raise HTTPException(status_code=400, detail="Dealer is not active")

    if not dealer.can_place_orders:
        raise HTTPException(status_code=400, detail="Dealer is not allowed to place orders")

    # Build order items with pricing
    order_items = []
    subtotal = Decimal("0")

    for item in order_in.items:
        # Get product
        prod_result = await db.execute(
            select(Product).where(Product.id == item.product_id)
        )
        product = prod_result.scalar_one_or_none()
        if not product:
            raise HTTPException(status_code=404, detail=f"Product {item.product_id} not found")

        # Determine unit price: dealer-specific > tier pricing > product selling price
        unit_price = product.selling_price or Decimal("0")
        unit_mrp = product.mrp or unit_price

        # Check dealer-specific pricing
        dp_result = await db.execute(
            select(DealerPricing).where(
                and_(
                    DealerPricing.dealer_id == dealer_id,
                    DealerPricing.product_id == item.product_id,
                    DealerPricing.is_active == True,
                )
            )
        )
        dealer_pricing = dp_result.scalar_one_or_none()
        if dealer_pricing:
            unit_price = dealer_pricing.special_price or dealer_pricing.dealer_price
        else:
            # Check tier pricing
            if dealer.tier:
                tp_result = await db.execute(
                    select(DealerTierPricing).where(
                        and_(
                            DealerTierPricing.tier == dealer.tier,
                            DealerTierPricing.product_id == item.product_id,
                            DealerTierPricing.is_active == True,
                        )
                    )
                )
                tier_pricing = tp_result.scalar_one_or_none()
                if tier_pricing:
                    if tier_pricing.fixed_price:
                        unit_price = tier_pricing.fixed_price
                    elif tier_pricing.discount_percentage:
                        unit_price = unit_price * (1 - tier_pricing.discount_percentage / 100)

        line_total = unit_price * item.quantity
        subtotal += line_total

        order_items.append({
            "product_id": item.product_id,
            "product_name": product.name,
            "sku": product.sku or "",
            "unit_mrp": unit_mrp,
            "quantity": item.quantity,
            "unit_price": unit_price,
            "total": line_total,
        })

    # Estimate tax (18% GST default)
    tax_amount = subtotal * Decimal("0.18")
    total_amount = subtotal + tax_amount

    # Credit check
    available_credit = dealer.credit_limit - dealer.outstanding_amount
    if total_amount > available_credit and dealer.credit_limit > 0:
        raise HTTPException(
            status_code=400,
            detail=f"Order amount ₹{total_amount:.2f} exceeds available credit ₹{available_credit:.2f}"
        )

    # Generate order number
    count_result = await db.execute(
        select(func.count(Order.id)).where(Order.dealer_id.isnot(None))
    )
    count = count_result.scalar() or 0
    order_number = f"DMS-{date.today().strftime('%Y%m%d')}-{str(count + 1).zfill(5)}"

    # Create order
    order = Order(
        order_number=order_number,
        dealer_id=dealer_id,
        customer_id=dealer.user_id,
        status="CONFIRMED",
        payment_status="PENDING",
        subtotal=subtotal,
        tax_amount=tax_amount,
        discount_amount=Decimal("0"),
        total_amount=total_amount,
        internal_notes=order_in.notes,
        source="DEALER",
    )
    db.add(order)
    await db.flush()

    # Create order items
    for oi in order_items:
        item_tax = oi["total"] * Decimal("0.18")
        order_item = OrderItem(
            order_id=order.id,
            product_id=oi["product_id"],
            product_name=oi["product_name"],
            product_sku=oi["sku"],
            quantity=oi["quantity"],
            unit_price=oi["unit_price"],
            unit_mrp=oi["unit_mrp"],
            tax_amount=item_tax,
            total_amount=oi["total"] + item_tax,
        )
        db.add(order_item)

    # Create credit ledger entry (debit)
    ledger = DealerCreditLedger(
        dealer_id=dealer_id,
        transaction_type=TransactionType.INVOICE,
        transaction_date=date.today(),
        reference_type="ORDER",
        reference_number=order_number,
        reference_id=order.id,
        debit_amount=total_amount,
        credit_amount=Decimal("0"),
        balance=dealer.outstanding_amount + total_amount,
        remarks=f"B2B Order {order_number}",
    )
    db.add(ledger)

    # Update dealer outstanding
    dealer.outstanding_amount += total_amount

    # Update credit status
    if dealer.credit_limit > 0 and dealer.outstanding_amount > dealer.credit_limit * Decimal("0.9"):
        dealer.credit_status = CreditStatus.ON_HOLD.value

    await db.commit()
    await db.refresh(order)

    return DMSOrderResponse(
        id=str(order.id),
        order_number=order.order_number,
        dealer_id=str(dealer_id),
        dealer_name=dealer.name,
        dealer_code=dealer.dealer_code,
        items=[DMSOrderItemResponse(
            product_id=str(oi["product_id"]),
            product_name=oi["product_name"],
            sku=oi["sku"],
            quantity=oi["quantity"],
            unit_price=oi["unit_price"],
            total=oi["total"],
        ) for oi in order_items],
        subtotal=subtotal,
        tax_amount=tax_amount,
        discount_amount=Decimal("0"),
        total_amount=total_amount,
        status=order.status,
        payment_status=order.payment_status or "",
        credit_impact=total_amount,
        notes=order_in.notes,
        created_at=order.created_at.isoformat() if order.created_at else "",
    )


@router.get("/dms/orders/{order_id}", response_model=DMSOrderResponse)
@require_module("dms")
async def get_dms_order(
    order_id: UUID,
    db: DB,
    current_user: User = Depends(get_current_user),
):
    """Get a single B2B order with dealer context."""
    from app.models.order import Order, OrderItem

    result = await db.execute(
        select(Order)
        .where(and_(Order.id == order_id, Order.dealer_id.isnot(None)))
        .options(selectinload(Order.dealer), selectinload(Order.items))
    )
    order = result.scalar_one_or_none()

    if not order:
        raise HTTPException(status_code=404, detail="DMS Order not found")

    items = []
    for oi in order.items:
        items.append(DMSOrderItemResponse(
            product_id=str(oi.product_id),
            product_name=oi.product_name or "",
            sku=oi.sku or "",
            quantity=oi.quantity or 0,
            unit_price=oi.unit_price or Decimal("0"),
            total=oi.total_price or Decimal("0"),
        ))

    return DMSOrderResponse(
        id=str(order.id),
        order_number=order.order_number or "",
        dealer_id=str(order.dealer_id),
        dealer_name=order.dealer.name if order.dealer else "Unknown",
        dealer_code=order.dealer.dealer_code if order.dealer else "",
        items=items,
        subtotal=order.subtotal or Decimal("0"),
        tax_amount=order.tax_amount or Decimal("0"),
        discount_amount=order.discount_amount or Decimal("0"),
        total_amount=order.total_amount or Decimal("0"),
        status=order.status or "",
        payment_status=order.payment_status or "",
        credit_impact=order.total_amount or Decimal("0"),
        notes=order.notes,
        created_at=order.created_at.isoformat() if order.created_at else "",
    )
