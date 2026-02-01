"""
Franchisee CRM API Endpoints.

This module provides APIs for:
- Franchisee management (CRUD, approval, status)
- Contract management
- Territory assignments
- Performance tracking
- Training and certifications
- Support tickets
- Compliance audits
- Dashboard and analytics
"""
from datetime import datetime, date, timedelta, timezone
from typing import Optional, List
from uuid import UUID, uuid4
from decimal import Decimal

from fastapi import APIRouter, HTTPException, status, Query
from sqlalchemy import select, func, and_, or_
from sqlalchemy.orm import selectinload

from app.api.deps import DB, CurrentUser
from app.models.franchisee import (
    Franchisee, FranchiseeContract, FranchiseeTerritory,
    FranchiseeServiceability, ServiceCapability,
    FranchiseePerformance, FranchiseeTraining, FranchiseeSupport,
    FranchiseeSupportComment, FranchiseeAudit,
    FranchiseeStatus, FranchiseeType, FranchiseeTier,
    ContractStatus, TerritoryStatus,
    TrainingStatus, TrainingType,
    SupportTicketStatus, SupportTicketPriority, SupportTicketCategory,
    AuditStatus, AuditType, AuditResult,
)
from app.schemas.franchisee import (

    FranchiseeCreate, FranchiseeUpdate, FranchiseeResponse,
    FranchiseeDetailResponse, FranchiseeListResponse,
    FranchiseeStatusUpdate, FranchiseeApproveRequest,
    FranchiseeContractCreate, FranchiseeContractUpdate, FranchiseeContractResponse,
    ContractApproveRequest, ContractTerminateRequest,
    FranchiseeTerritoryCreate, FranchiseeTerritoryUpdate, FranchiseeTerritoryResponse,
    FranchiseePerformanceCreate, FranchiseePerformanceResponse,
    FranchiseeTrainingCreate, FranchiseeTrainingUpdate, FranchiseeTrainingResponse,
    TrainingCompleteRequest, TrainingCertificateRequest,
    FranchiseeSupportCreate, FranchiseeSupportUpdate, FranchiseeSupportResponse,
    FranchiseeSupportListResponse, SupportAssignRequest, SupportResolveRequest,
    SupportEscalateRequest, SupportFeedbackRequest,
    SupportCommentCreate, SupportCommentResponse,
    FranchiseeAuditCreate, FranchiseeAuditUpdate, FranchiseeAuditResponse,
    AuditCompleteRequest,
    FranchiseeDashboardResponse, FranchiseeLeaderboardResponse,
    ServiceabilityRequest,
)
from app.core.module_decorators import require_module


router = APIRouter()


# ==================== Helper Functions ====================

def generate_franchisee_code(franchisee_type: FranchiseeType) -> str:
    """Generate unique franchisee code."""
    prefix = {
        FranchiseeType.EXCLUSIVE: "FRE",
        FranchiseeType.NON_EXCLUSIVE: "FRN",
        FranchiseeType.MASTER: "FRM",
        FranchiseeType.SUB_FRANCHISEE: "FRS",
        FranchiseeType.DEALER: "DLR",
        FranchiseeType.DISTRIBUTOR: "DST",
    }.get(franchisee_type, "FRN")
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d")
    unique = str(uuid4())[:4].upper()
    return f"{prefix}-{timestamp}-{unique}"


def generate_contract_number() -> str:
    """Generate unique contract number."""
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d")
    unique = str(uuid4())[:6].upper()
    return f"CON-{timestamp}-{unique}"


def generate_training_code(training_type: TrainingType) -> str:
    """Generate unique training code."""
    prefix = training_type.value[:3].upper()
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d")
    unique = str(uuid4())[:4].upper()
    return f"TRN-{prefix}-{timestamp}-{unique}"


def generate_ticket_number() -> str:
    """Generate unique ticket number."""
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d")
    unique = str(uuid4())[:6].upper()
    return f"TKT-{timestamp}-{unique}"


def generate_audit_number(audit_type: AuditType) -> str:
    """Generate unique audit number."""
    prefix = audit_type.value[:3].upper()
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d")
    unique = str(uuid4())[:4].upper()
    return f"AUD-{prefix}-{timestamp}-{unique}"


# ==================== Franchisee CRUD ====================

@router.post("", response_model=FranchiseeResponse, status_code=status.HTTP_201_CREATED)
@require_module("sales_distribution")
async def create_franchisee(
    data: FranchiseeCreate,
    db: DB,
    current_user: CurrentUser,
):
    """Create a new franchisee application."""
    franchisee = Franchisee(
        id=str(uuid4()),
        franchisee_code=generate_franchisee_code(data.franchisee_type),
        status=FranchiseeStatus.PROSPECT,
        application_date=date.today(),
        created_by_id=str(current_user.id),
        **data.model_dump()
    )
    db.add(franchisee)
    await db.commit()
    await db.refresh(franchisee)
    return franchisee


@router.get("", response_model=FranchiseeListResponse)
@require_module("sales_distribution")
async def list_franchisees(
    db: DB,
    current_user: CurrentUser,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    status: Optional[FranchiseeStatus] = None,
    franchisee_type: Optional[FranchiseeType] = None,
    tier: Optional[FranchiseeTier] = None,
    city: Optional[str] = None,
    state: Optional[str] = None,
    search: Optional[str] = None,
):
    """List franchisees with filtering."""
    query = select(Franchisee)

    if status:
        query = query.where(Franchisee.status == status)
    if franchisee_type:
        query = query.where(Franchisee.franchisee_type == franchisee_type)
    if tier:
        query = query.where(Franchisee.tier == tier)
    if city:
        query = query.where(Franchisee.city.ilike(f"%{city}%"))
    if state:
        query = query.where(Franchisee.state.ilike(f"%{state}%"))
    if search:
        query = query.where(
            or_(
                Franchisee.name.ilike(f"%{search}%"),
                Franchisee.franchisee_code.ilike(f"%{search}%"),
                Franchisee.email.ilike(f"%{search}%"),
                Franchisee.phone.ilike(f"%{search}%"),
            )
        )

    # Count
    count_query = select(func.count()).select_from(query.subquery())
    total = await db.scalar(count_query) or 0

    # Fetch
    query = query.order_by(Franchisee.created_at.desc()).offset(skip).limit(limit)
    result = await db.execute(query)
    franchisees = result.scalars().all()

    return FranchiseeListResponse(items=franchisees, total=total, skip=skip, limit=limit)


@router.get("/stats/dashboard", response_model=FranchiseeDashboardResponse)
@require_module("sales_distribution")
async def get_franchisee_dashboard(
    db: DB,
    current_user: CurrentUser,
):
    """Get franchisee dashboard metrics."""
    today = date.today()
    month_start = today.replace(day=1)

    # Counts by status
    status_query = select(
        Franchisee.status, func.count(Franchisee.id)
    ).group_by(Franchisee.status)
    status_result = await db.execute(status_query)
    by_status = {str(row[0].value): row[1] for row in status_result.fetchall()}

    # Counts by type
    type_query = select(
        Franchisee.franchisee_type, func.count(Franchisee.id)
    ).group_by(Franchisee.franchisee_type)
    type_result = await db.execute(type_query)
    by_type = {str(row[0].value): row[1] for row in type_result.fetchall()}

    # Counts by tier
    tier_query = select(
        Franchisee.tier, func.count(Franchisee.id)
    ).group_by(Franchisee.tier)
    tier_result = await db.execute(tier_query)
    by_tier = {str(row[0].value): row[1] for row in tier_result.fetchall()}

    # Total counts
    total = sum(by_status.values())
    active = by_status.get("ACTIVE", 0)
    pending = by_status.get("APPLICATION_PENDING", 0) + by_status.get("UNDER_REVIEW", 0)
    suspended = by_status.get("SUSPENDED", 0)

    # Support tickets
    open_tickets_query = select(func.count(FranchiseeSupport.id)).where(
        FranchiseeSupport.status.in_([
            SupportTicketStatus.OPEN,
            SupportTicketStatus.IN_PROGRESS,
            SupportTicketStatus.WAITING_ON_FRANCHISEE,
        ])
    )
    open_tickets = await db.scalar(open_tickets_query) or 0

    sla_breached_query = select(func.count(FranchiseeSupport.id)).where(
        and_(
            FranchiseeSupport.sla_breached == True,
            FranchiseeSupport.status.not_in([
                SupportTicketStatus.RESOLVED,
                SupportTicketStatus.CLOSED,
            ])
        )
    )
    sla_breached = await db.scalar(sla_breached_query) or 0

    # Trainings
    trainings_scheduled_query = select(func.count(FranchiseeTraining.id)).where(
        FranchiseeTraining.status == TrainingStatus.SCHEDULED
    )
    trainings_scheduled = await db.scalar(trainings_scheduled_query) or 0

    # Audits
    audits_scheduled_query = select(func.count(FranchiseeAudit.id)).where(
        FranchiseeAudit.status == AuditStatus.SCHEDULED
    )
    audits_scheduled = await db.scalar(audits_scheduled_query) or 0

    audits_pending_query = select(func.count(FranchiseeAudit.id)).where(
        FranchiseeAudit.status == AuditStatus.ACTION_REQUIRED
    )
    audits_pending = await db.scalar(audits_pending_query) or 0

    # Top franchisees
    top_query = select(Franchisee).where(
        Franchisee.status == FranchiseeStatus.ACTIVE
    ).order_by(Franchisee.total_revenue.desc()).limit(5)
    top_result = await db.execute(top_query)
    top_franchisees = [
        {
            "id": str(f.id),
            "name": f.name,
            "code": f.franchisee_code,
            "tier": f.tier,
            "revenue": float(f.total_revenue),
            "orders": f.total_orders,
        }
        for f in top_result.scalars().all()
    ]

    return FranchiseeDashboardResponse(
        date=today,
        total_franchisees=total,
        active_franchisees=active,
        pending_applications=pending,
        suspended_franchisees=suspended,
        by_status=by_status,
        by_type=by_type,
        by_tier=by_tier,
        open_tickets=open_tickets,
        sla_breached_tickets=sla_breached,
        trainings_scheduled=trainings_scheduled,
        audits_scheduled=audits_scheduled,
        audits_pending_action=audits_pending,
        top_franchisees=top_franchisees,
    )


@router.get("/leaderboard", response_model=FranchiseeLeaderboardResponse)
@require_module("sales_distribution")
async def get_franchisee_leaderboard(
    db: DB,
    current_user: CurrentUser,
    period: str = Query("MONTHLY", regex="^(MONTHLY|QUARTERLY|YEARLY)$"),
):
    """Get franchisee leaderboard."""
    today = date.today()

    if period == "MONTHLY":
        period_start = today.replace(day=1)
        period_end = today
    elif period == "QUARTERLY":
        quarter_month = ((today.month - 1) // 3) * 3 + 1
        period_start = today.replace(month=quarter_month, day=1)
        period_end = today
    else:  # YEARLY
        period_start = today.replace(month=1, day=1)
        period_end = today

    # Get performance records for the period
    query = select(
        FranchiseePerformance.franchisee_id,
        func.sum(FranchiseePerformance.net_revenue).label("total_revenue"),
        func.sum(FranchiseePerformance.total_orders).label("total_orders"),
        func.avg(FranchiseePerformance.overall_score).label("avg_score"),
    ).where(
        and_(
            FranchiseePerformance.period_start >= period_start,
            FranchiseePerformance.period_end <= period_end,
        )
    ).group_by(FranchiseePerformance.franchisee_id).order_by(
        func.sum(FranchiseePerformance.net_revenue).desc()
    ).limit(20)

    result = await db.execute(query)
    rows = result.fetchall()

    # Get franchisee names
    franchisee_ids = [str(row[0]) for row in rows]
    if franchisee_ids:
        franchisees_query = select(Franchisee).where(Franchisee.id.in_(franchisee_ids))
        franchisees_result = await db.execute(franchisees_query)
        franchisees_map = {str(f.id): f for f in franchisees_result.scalars().all()}
    else:
        franchisees_map = {}

    rankings = []
    for rank, row in enumerate(rows, 1):
        franchisee = franchisees_map.get(str(row[0]))
        if franchisee:
            rankings.append({
                "rank": rank,
                "franchisee_id": str(row[0]),
                "name": franchisee.name,
                "code": franchisee.franchisee_code,
                "tier": franchisee.tier,
                "revenue": float(row[1] or 0),
                "orders": int(row[2] or 0),
                "score": float(row[3] or 0),
            })

    return FranchiseeLeaderboardResponse(
        period=period,
        period_start=period_start,
        period_end=period_end,
        rankings=rankings,
    )


@router.get("/{franchisee_id}", response_model=FranchiseeDetailResponse)
@require_module("sales_distribution")
async def get_franchisee(
    franchisee_id: UUID,
    db: DB,
    current_user: CurrentUser,
):
    """Get franchisee details."""
    query = select(Franchisee).where(Franchisee.id == str(franchisee_id))
    result = await db.execute(query)
    franchisee = result.scalar_one_or_none()

    if not franchisee:
        raise HTTPException(status_code=404, detail="Franchisee not found")

    return franchisee


@router.put("/{franchisee_id}", response_model=FranchiseeResponse)
@require_module("sales_distribution")
async def update_franchisee(
    franchisee_id: UUID,
    data: FranchiseeUpdate,
    db: DB,
    current_user: CurrentUser,
):
    """Update franchisee."""
    query = select(Franchisee).where(Franchisee.id == str(franchisee_id))
    result = await db.execute(query)
    franchisee = result.scalar_one_or_none()

    if not franchisee:
        raise HTTPException(status_code=404, detail="Franchisee not found")

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if value is not None:
            setattr(franchisee, field, value)

    await db.commit()
    await db.refresh(franchisee)
    return franchisee


@router.post("/{franchisee_id}/status", response_model=FranchiseeResponse)
@require_module("sales_distribution")
async def update_franchisee_status(
    franchisee_id: UUID,
    data: FranchiseeStatusUpdate,
    db: DB,
    current_user: CurrentUser,
):
    """Update franchisee status."""
    query = select(Franchisee).where(Franchisee.id == str(franchisee_id))
    result = await db.execute(query)
    franchisee = result.scalar_one_or_none()

    if not franchisee:
        raise HTTPException(status_code=404, detail="Franchisee not found")

    franchisee.status = data.status

    if data.status == FranchiseeStatus.ACTIVE and not franchisee.activation_date:
        franchisee.activation_date = date.today()
    elif data.status == FranchiseeStatus.TERMINATED:
        franchisee.termination_date = date.today()

    if data.reason:
        franchisee.notes = f"{franchisee.notes or ''}\n[{datetime.now(timezone.utc)}] Status changed to {data.status.value}: {data.reason}"

    await db.commit()
    await db.refresh(franchisee)
    return franchisee


@router.post("/{franchisee_id}/approve", response_model=FranchiseeResponse)
@require_module("sales_distribution")
async def approve_franchisee(
    franchisee_id: UUID,
    data: FranchiseeApproveRequest,
    db: DB,
    current_user: CurrentUser,
):
    """Approve franchisee application."""
    query = select(Franchisee).where(Franchisee.id == str(franchisee_id))
    result = await db.execute(query)
    franchisee = result.scalar_one_or_none()

    if not franchisee:
        raise HTTPException(status_code=404, detail="Franchisee not found")

    if franchisee.status not in [
        FranchiseeStatus.PROSPECT,
        FranchiseeStatus.APPLICATION_PENDING,
        FranchiseeStatus.UNDER_REVIEW,
    ]:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot approve franchisee with status {franchisee.status}"
        )

    franchisee.status = FranchiseeStatus.APPROVED.value
    franchisee.approval_date = date.today()
    franchisee.approved_by_id = str(current_user.id)

    if data.tier:
        franchisee.tier = data.tier
    if data.credit_limit:
        franchisee.credit_limit = data.credit_limit
    if data.commission_rate:
        franchisee.commission_rate = data.commission_rate
    if data.notes:
        franchisee.notes = f"{franchisee.notes or ''}\n[{datetime.now(timezone.utc)}] Approved: {data.notes}"

    await db.commit()
    await db.refresh(franchisee)
    return franchisee


# ==================== Contracts ====================

@router.post("/contracts", response_model=FranchiseeContractResponse, status_code=status.HTTP_201_CREATED)
@require_module("sales_distribution")
async def create_contract(
    data: FranchiseeContractCreate,
    db: DB,
    current_user: CurrentUser,
):
    """Create a new contract for franchisee."""
    # Verify franchisee exists
    franchisee_query = select(Franchisee).where(Franchisee.id == str(data.franchisee_id))
    franchisee_result = await db.execute(franchisee_query)
    franchisee = franchisee_result.scalar_one_or_none()

    if not franchisee:
        raise HTTPException(status_code=404, detail="Franchisee not found")

    contract_data = data.model_dump()
    contract_data["franchisee_id"] = str(data.franchisee_id)
    contract = FranchiseeContract(
        id=str(uuid4()),
        contract_number=generate_contract_number(),
        status=ContractStatus.DRAFT,
        created_by_id=str(current_user.id),
        **contract_data
    )
    db.add(contract)
    await db.commit()
    await db.refresh(contract)
    return contract


@router.get("/contracts", response_model=List[FranchiseeContractResponse])
@require_module("sales_distribution")
async def list_contracts(
    db: DB,
    current_user: CurrentUser,
    franchisee_id: Optional[UUID] = None,
    status: Optional[ContractStatus] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
):
    """List contracts."""
    query = select(FranchiseeContract)

    if franchisee_id:
        query = query.where(FranchiseeContract.franchisee_id == str(franchisee_id))
    if status:
        query = query.where(FranchiseeContract.status == status)

    query = query.order_by(FranchiseeContract.created_at.desc()).offset(skip).limit(limit)
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/contracts/{contract_id}", response_model=FranchiseeContractResponse)
@require_module("sales_distribution")
async def get_contract(
    contract_id: UUID,
    db: DB,
    current_user: CurrentUser,
):
    """Get contract details."""
    query = select(FranchiseeContract).where(FranchiseeContract.id == str(contract_id))
    result = await db.execute(query)
    contract = result.scalar_one_or_none()

    if not contract:
        raise HTTPException(status_code=404, detail="Contract not found")

    return contract


@router.post("/contracts/{contract_id}/approve", response_model=FranchiseeContractResponse)
@require_module("sales_distribution")
async def approve_contract(
    contract_id: UUID,
    data: ContractApproveRequest,
    db: DB,
    current_user: CurrentUser,
):
    """Approve contract."""
    query = select(FranchiseeContract).where(FranchiseeContract.id == str(contract_id))
    result = await db.execute(query)
    contract = result.scalar_one_or_none()

    if not contract:
        raise HTTPException(status_code=404, detail="Contract not found")

    if contract.status != ContractStatus.PENDING_APPROVAL:
        raise HTTPException(status_code=400, detail="Contract is not pending approval")

    contract.status = ContractStatus.ACTIVE.value
    contract.approved_by_id = str(current_user.id)
    contract.approved_at = datetime.now(timezone.utc)

    if data.notes:
        contract.notes = f"{contract.notes or ''}\n[{datetime.now(timezone.utc)}] Approved: {data.notes}"

    await db.commit()
    await db.refresh(contract)
    return contract


@router.post("/contracts/{contract_id}/terminate", response_model=FranchiseeContractResponse)
@require_module("sales_distribution")
async def terminate_contract(
    contract_id: UUID,
    data: ContractTerminateRequest,
    db: DB,
    current_user: CurrentUser,
):
    """Terminate contract."""
    query = select(FranchiseeContract).where(FranchiseeContract.id == str(contract_id))
    result = await db.execute(query)
    contract = result.scalar_one_or_none()

    if not contract:
        raise HTTPException(status_code=404, detail="Contract not found")

    if contract.status != ContractStatus.ACTIVE:
        raise HTTPException(status_code=400, detail="Contract is not active")

    contract.status = ContractStatus.TERMINATED.value
    contract.terminated_by_id = str(current_user.id)
    contract.terminated_at = datetime.now(timezone.utc)
    contract.termination_reason = data.reason

    await db.commit()
    await db.refresh(contract)
    return contract


# ==================== Territories ====================

@router.post("/territories", response_model=FranchiseeTerritoryResponse, status_code=status.HTTP_201_CREATED)
@require_module("sales_distribution")
async def create_territory(
    data: FranchiseeTerritoryCreate,
    db: DB,
    current_user: CurrentUser,
):
    """Assign territory to franchisee."""
    territory_data = data.model_dump()
    territory_data["franchisee_id"] = str(data.franchisee_id)
    territory = FranchiseeTerritory(
        id=str(uuid4()),
        status=TerritoryStatus.ACTIVE,
        created_by_id=str(current_user.id),
        **territory_data
    )
    db.add(territory)
    await db.commit()
    await db.refresh(territory)
    return territory


@router.get("/territories", response_model=List[FranchiseeTerritoryResponse])
@require_module("sales_distribution")
async def list_territories(
    db: DB,
    current_user: CurrentUser,
    franchisee_id: Optional[UUID] = None,
    status: Optional[TerritoryStatus] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
):
    """List territories."""
    query = select(FranchiseeTerritory)

    if franchisee_id:
        query = query.where(FranchiseeTerritory.franchisee_id == str(franchisee_id))
    if status:
        query = query.where(FranchiseeTerritory.status == status)

    query = query.order_by(FranchiseeTerritory.created_at.desc()).offset(skip).limit(limit)
    result = await db.execute(query)
    return result.scalars().all()


@router.put("/territories/{territory_id}", response_model=FranchiseeTerritoryResponse)
@require_module("sales_distribution")
async def update_territory(
    territory_id: UUID,
    data: FranchiseeTerritoryUpdate,
    db: DB,
    current_user: CurrentUser,
):
    """Update territory."""
    query = select(FranchiseeTerritory).where(FranchiseeTerritory.id == str(territory_id))
    result = await db.execute(query)
    territory = result.scalar_one_or_none()

    if not territory:
        raise HTTPException(status_code=404, detail="Territory not found")

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if value is not None:
            setattr(territory, field, value)

    await db.commit()
    await db.refresh(territory)
    return territory


# ==================== Performance ====================

@router.post("/performance", response_model=FranchiseePerformanceResponse, status_code=status.HTTP_201_CREATED)
@require_module("sales_distribution")
async def create_performance_record(
    data: FranchiseePerformanceCreate,
    db: DB,
    current_user: CurrentUser,
):
    """Create performance record."""
    # Calculate achievement
    achievement = Decimal("0")
    if data.target_revenue and data.target_revenue > 0:
        achievement = (data.net_revenue / data.target_revenue) * 100

    performance_data = data.model_dump()
    performance_data["franchisee_id"] = str(data.franchisee_id)
    performance = FranchiseePerformance(
        id=str(uuid4()),
        target_achievement_percentage=achievement,
        **performance_data
    )
    db.add(performance)
    await db.commit()
    await db.refresh(performance)
    return performance


@router.get("/performance", response_model=List[FranchiseePerformanceResponse])
@require_module("sales_distribution")
async def list_performance_records(
    db: DB,
    current_user: CurrentUser,
    franchisee_id: Optional[UUID] = None,
    period_type: Optional[str] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
):
    """List performance records."""
    query = select(FranchiseePerformance)

    if franchisee_id:
        query = query.where(FranchiseePerformance.franchisee_id == str(franchisee_id))
    if period_type:
        query = query.where(FranchiseePerformance.period_type == period_type)

    query = query.order_by(FranchiseePerformance.period_start.desc()).offset(skip).limit(limit)
    result = await db.execute(query)
    return result.scalars().all()


# ==================== Training ====================

@router.post("/trainings", response_model=FranchiseeTrainingResponse, status_code=status.HTTP_201_CREATED)
@require_module("sales_distribution")
async def create_training(
    data: FranchiseeTrainingCreate,
    db: DB,
    current_user: CurrentUser,
):
    """Schedule training for franchisee."""
    training_data = data.model_dump()
    training_data["franchisee_id"] = str(data.franchisee_id)
    if data.trainer_id:
        training_data["trainer_id"] = str(data.trainer_id)
    training = FranchiseeTraining(
        id=str(uuid4()),
        training_code=generate_training_code(data.training_type),
        status=TrainingStatus.SCHEDULED,
        **training_data
    )
    db.add(training)
    await db.commit()
    await db.refresh(training)
    return training


@router.get("/trainings", response_model=List[FranchiseeTrainingResponse])
@require_module("sales_distribution")
async def list_trainings(
    db: DB,
    current_user: CurrentUser,
    franchisee_id: Optional[UUID] = None,
    training_type: Optional[TrainingType] = None,
    status: Optional[TrainingStatus] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
):
    """List trainings."""
    query = select(FranchiseeTraining)

    if franchisee_id:
        query = query.where(FranchiseeTraining.franchisee_id == str(franchisee_id))
    if training_type:
        query = query.where(FranchiseeTraining.training_type == training_type)
    if status:
        query = query.where(FranchiseeTraining.status == status)

    query = query.order_by(FranchiseeTraining.scheduled_date.desc()).offset(skip).limit(limit)
    result = await db.execute(query)
    return result.scalars().all()


@router.post("/trainings/{training_id}/complete", response_model=FranchiseeTrainingResponse)
@require_module("sales_distribution")
async def complete_training(
    training_id: UUID,
    data: TrainingCompleteRequest,
    db: DB,
    current_user: CurrentUser,
):
    """Complete training."""
    query = select(FranchiseeTraining).where(FranchiseeTraining.id == str(training_id))
    result = await db.execute(query)
    training = result.scalar_one_or_none()

    if not training:
        raise HTTPException(status_code=404, detail="Training not found")

    training.attended = data.attended
    training.attendance_percentage = data.attendance_percentage
    training.completed_at = datetime.now(timezone.utc)

    if training.has_assessment and data.assessment_score is not None:
        training.assessment_score = data.assessment_score
        training.attempts += 1
        training.passed = data.assessment_score >= training.passing_score
        training.status = TrainingStatus.COMPLETED.value.value if training.passed else TrainingStatus.FAILED.value
    else:
        training.status = TrainingStatus.COMPLETED.value

    if data.feedback:
        training.feedback = data.feedback
    if data.feedback_rating:
        training.feedback_rating = data.feedback_rating

    await db.commit()
    await db.refresh(training)
    return training


@router.post("/trainings/{training_id}/certificate", response_model=FranchiseeTrainingResponse)
@require_module("sales_distribution")
async def issue_certificate(
    training_id: UUID,
    data: TrainingCertificateRequest,
    db: DB,
    current_user: CurrentUser,
):
    """Issue training certificate."""
    query = select(FranchiseeTraining).where(FranchiseeTraining.id == str(training_id))
    result = await db.execute(query)
    training = result.scalar_one_or_none()

    if not training:
        raise HTTPException(status_code=404, detail="Training not found")

    if training.status != TrainingStatus.COMPLETED or not training.passed:
        raise HTTPException(status_code=400, detail="Training must be completed and passed")

    training.certificate_issued = True
    training.certificate_number = f"CERT-{training.training_code}"
    training.certificate_url = f"/certificates/{training.certificate_number}.pdf"
    if data.certificate_expiry:
        training.certificate_expiry = data.certificate_expiry

    await db.commit()
    await db.refresh(training)
    return training


# ==================== Support Tickets ====================

@router.post("/support", response_model=FranchiseeSupportResponse, status_code=status.HTTP_201_CREATED)
@require_module("sales_distribution")
async def create_support_ticket(
    data: FranchiseeSupportCreate,
    db: DB,
    current_user: CurrentUser,
):
    """Create support ticket."""
    # Calculate SLA based on priority
    sla_hours = {
        SupportTicketPriority.LOW: 72,
        SupportTicketPriority.MEDIUM: 48,
        SupportTicketPriority.HIGH: 24,
        SupportTicketPriority.CRITICAL: 4,
    }.get(data.priority, 48)

    ticket_data = data.model_dump()
    ticket_data["franchisee_id"] = str(data.franchisee_id)
    ticket = FranchiseeSupport(
        id=str(uuid4()),
        ticket_number=generate_ticket_number(),
        status=SupportTicketStatus.OPEN,
        sla_due_at=datetime.now(timezone.utc) + timedelta(hours=sla_hours),
        **ticket_data
    )
    db.add(ticket)
    await db.commit()
    await db.refresh(ticket)
    return ticket


@router.get("/support", response_model=FranchiseeSupportListResponse)
@require_module("sales_distribution")
async def list_support_tickets(
    db: DB,
    current_user: CurrentUser,
    franchisee_id: Optional[UUID] = None,
    status: Optional[SupportTicketStatus] = None,
    priority: Optional[SupportTicketPriority] = None,
    category: Optional[SupportTicketCategory] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
):
    """List support tickets."""
    query = select(FranchiseeSupport)

    if franchisee_id:
        query = query.where(FranchiseeSupport.franchisee_id == str(franchisee_id))
    if status:
        query = query.where(FranchiseeSupport.status == status)
    if priority:
        query = query.where(FranchiseeSupport.priority == priority)
    if category:
        query = query.where(FranchiseeSupport.category == category)

    # Count
    count_query = select(func.count()).select_from(query.subquery())
    total = await db.scalar(count_query) or 0

    query = query.order_by(FranchiseeSupport.created_at.desc()).offset(skip).limit(limit)
    result = await db.execute(query)
    tickets = result.scalars().all()

    return FranchiseeSupportListResponse(items=tickets, total=total, skip=skip, limit=limit)


@router.get("/support/{ticket_id}", response_model=FranchiseeSupportResponse)
@require_module("sales_distribution")
async def get_support_ticket(
    ticket_id: UUID,
    db: DB,
    current_user: CurrentUser,
):
    """Get support ticket details."""
    query = select(FranchiseeSupport).where(FranchiseeSupport.id == str(ticket_id))
    result = await db.execute(query)
    ticket = result.scalar_one_or_none()

    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")

    return ticket


@router.post("/support/{ticket_id}/assign", response_model=FranchiseeSupportResponse)
@require_module("sales_distribution")
async def assign_support_ticket(
    ticket_id: UUID,
    data: SupportAssignRequest,
    db: DB,
    current_user: CurrentUser,
):
    """Assign support ticket."""
    query = select(FranchiseeSupport).where(FranchiseeSupport.id == str(ticket_id))
    result = await db.execute(query)
    ticket = result.scalar_one_or_none()

    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")

    ticket.assigned_to_id = str(data.assigned_to_id)
    ticket.assigned_at = datetime.now(timezone.utc)
    ticket.status = SupportTicketStatus.IN_PROGRESS.value

    if not ticket.first_response_at:
        ticket.first_response_at = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(ticket)
    return ticket


@router.post("/support/{ticket_id}/resolve", response_model=FranchiseeSupportResponse)
@require_module("sales_distribution")
async def resolve_support_ticket(
    ticket_id: UUID,
    data: SupportResolveRequest,
    db: DB,
    current_user: CurrentUser,
):
    """Resolve support ticket."""
    query = select(FranchiseeSupport).where(FranchiseeSupport.id == str(ticket_id))
    result = await db.execute(query)
    ticket = result.scalar_one_or_none()

    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")

    ticket.status = SupportTicketStatus.RESOLVED.value
    ticket.resolution = data.resolution
    ticket.resolved_by_id = str(current_user.id)
    ticket.resolved_at = datetime.now(timezone.utc)

    # Calculate resolution time
    resolution_time = (ticket.resolved_at - ticket.created_at).total_seconds() / 3600
    ticket.resolution_time_hours = Decimal(str(round(resolution_time, 2)))

    await db.commit()
    await db.refresh(ticket)
    return ticket


@router.post("/support/{ticket_id}/escalate", response_model=FranchiseeSupportResponse)
@require_module("sales_distribution")
async def escalate_support_ticket(
    ticket_id: UUID,
    data: SupportEscalateRequest,
    db: DB,
    current_user: CurrentUser,
):
    """Escalate support ticket."""
    query = select(FranchiseeSupport).where(FranchiseeSupport.id == str(ticket_id))
    result = await db.execute(query)
    ticket = result.scalar_one_or_none()

    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")

    ticket.status = SupportTicketStatus.ESCALATED.value
    ticket.is_escalated = True
    ticket.escalated_to_id = str(data.escalated_to_id)
    ticket.escalated_at = datetime.now(timezone.utc)
    ticket.escalation_reason = data.reason

    await db.commit()
    await db.refresh(ticket)
    return ticket


@router.post("/support/{ticket_id}/close", response_model=FranchiseeSupportResponse)
@require_module("sales_distribution")
async def close_support_ticket(
    ticket_id: UUID,
    db: DB,
    current_user: CurrentUser,
):
    """Close support ticket."""
    query = select(FranchiseeSupport).where(FranchiseeSupport.id == str(ticket_id))
    result = await db.execute(query)
    ticket = result.scalar_one_or_none()

    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")

    ticket.status = SupportTicketStatus.CLOSED.value
    ticket.closed_at = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(ticket)
    return ticket


@router.post("/support/{ticket_id}/feedback", response_model=FranchiseeSupportResponse)
@require_module("sales_distribution")
async def submit_ticket_feedback(
    ticket_id: UUID,
    data: SupportFeedbackRequest,
    db: DB,
    current_user: CurrentUser,
):
    """Submit feedback for ticket."""
    query = select(FranchiseeSupport).where(FranchiseeSupport.id == str(ticket_id))
    result = await db.execute(query)
    ticket = result.scalar_one_or_none()

    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")

    ticket.satisfaction_rating = data.satisfaction_rating
    if data.feedback:
        ticket.feedback = data.feedback

    await db.commit()
    await db.refresh(ticket)
    return ticket


@router.get("/support/{ticket_id}/comments", response_model=List[SupportCommentResponse])
@require_module("sales_distribution")
async def get_ticket_comments(
    ticket_id: UUID,
    db: DB,
    current_user: CurrentUser,
):
    """Get comments for a ticket."""
    query = select(FranchiseeSupportComment).where(
        FranchiseeSupportComment.ticket_id == str(ticket_id)
    ).order_by(FranchiseeSupportComment.created_at.asc())

    result = await db.execute(query)
    return result.scalars().all()


@router.post("/support/{ticket_id}/comments", response_model=SupportCommentResponse, status_code=status.HTTP_201_CREATED)
@require_module("sales_distribution")
async def add_ticket_comment(
    ticket_id: UUID,
    data: SupportCommentCreate,
    db: DB,
    current_user: CurrentUser,
):
    """Add comment to ticket."""
    # Verify ticket exists
    ticket_query = select(FranchiseeSupport).where(FranchiseeSupport.id == str(ticket_id))
    ticket_result = await db.execute(ticket_query)
    ticket = ticket_result.scalar_one_or_none()

    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")

    comment = FranchiseeSupportComment(
        id=str(uuid4()),
        ticket_id=str(ticket_id),
        author_id=str(current_user.id),
        author_type="STAFF",
        author_name=f"{current_user.first_name or ''} {current_user.last_name or ''}".strip() or current_user.email,
        **data.model_dump()
    )
    db.add(comment)

    # Update ticket status if waiting on franchisee
    if ticket.status == SupportTicketStatus.WAITING_ON_FRANCHISEE:
        ticket.status = SupportTicketStatus.IN_PROGRESS.value

    await db.commit()
    await db.refresh(comment)
    return comment


# ==================== Audits ====================

@router.post("/audits", response_model=FranchiseeAuditResponse, status_code=status.HTTP_201_CREATED)
@require_module("sales_distribution")
async def create_audit(
    data: FranchiseeAuditCreate,
    db: DB,
    current_user: CurrentUser,
):
    """Schedule audit for franchisee."""
    audit_data = data.model_dump()
    audit_data["franchisee_id"] = str(data.franchisee_id)
    if data.auditor_id:
        audit_data["auditor_id"] = str(data.auditor_id)
    audit = FranchiseeAudit(
        id=str(uuid4()),
        audit_number=generate_audit_number(data.audit_type),
        status=AuditStatus.SCHEDULED,
        **audit_data
    )
    db.add(audit)
    await db.commit()
    await db.refresh(audit)
    return audit


@router.get("/audits", response_model=List[FranchiseeAuditResponse])
@require_module("sales_distribution")
async def list_audits(
    db: DB,
    current_user: CurrentUser,
    franchisee_id: Optional[UUID] = None,
    audit_type: Optional[AuditType] = None,
    status: Optional[AuditStatus] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
):
    """List audits."""
    query = select(FranchiseeAudit)

    if franchisee_id:
        query = query.where(FranchiseeAudit.franchisee_id == str(franchisee_id))
    if audit_type:
        query = query.where(FranchiseeAudit.audit_type == audit_type)
    if status:
        query = query.where(FranchiseeAudit.status == status)

    query = query.order_by(FranchiseeAudit.scheduled_date.desc()).offset(skip).limit(limit)
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/audits/{audit_id}", response_model=FranchiseeAuditResponse)
@require_module("sales_distribution")
async def get_audit(
    audit_id: UUID,
    db: DB,
    current_user: CurrentUser,
):
    """Get audit details."""
    query = select(FranchiseeAudit).where(FranchiseeAudit.id == str(audit_id))
    result = await db.execute(query)
    audit = result.scalar_one_or_none()

    if not audit:
        raise HTTPException(status_code=404, detail="Audit not found")

    return audit


@router.post("/audits/{audit_id}/complete", response_model=FranchiseeAuditResponse)
@require_module("sales_distribution")
async def complete_audit(
    audit_id: UUID,
    data: AuditCompleteRequest,
    db: DB,
    current_user: CurrentUser,
):
    """Complete audit with findings."""
    query = select(FranchiseeAudit).where(FranchiseeAudit.id == str(audit_id))
    result = await db.execute(query)
    audit = result.scalar_one_or_none()

    if not audit:
        raise HTTPException(status_code=404, detail="Audit not found")

    audit.status = AuditStatus.COMPLETED.value
    audit.actual_date = data.actual_date
    audit.checklist = data.checklist
    audit.findings = data.findings
    audit.observations = data.observations
    audit.non_conformities = data.non_conformities

    audit.overall_score = data.overall_score
    audit.compliance_score = data.compliance_score
    audit.quality_score = data.quality_score
    audit.result = data.result

    audit.corrective_actions = data.corrective_actions
    audit.follow_up_required = data.follow_up_required
    audit.follow_up_date = data.follow_up_date

    audit.report_url = data.report_url
    audit.evidence_urls = data.evidence_urls

    audit.completed_at = datetime.now(timezone.utc)

    # Update franchisee compliance score
    franchisee_query = select(Franchisee).where(Franchisee.id == audit.franchisee_id)
    franchisee_result = await db.execute(franchisee_query)
    franchisee = franchisee_result.scalar_one_or_none()

    if franchisee:
        franchisee.compliance_score = data.compliance_score or data.overall_score
        franchisee.last_audit_date = data.actual_date

    # Set to ACTION_REQUIRED if there are corrective actions
    if data.corrective_actions and len(data.corrective_actions) > 0:
        audit.status = AuditStatus.ACTION_REQUIRED.value

    await db.commit()
    await db.refresh(audit)
    return audit


@router.post("/audits/{audit_id}/close", response_model=FranchiseeAuditResponse)
@require_module("sales_distribution")
async def close_audit(
    audit_id: UUID,
    db: DB,
    current_user: CurrentUser,
):
    """Close audit."""
    query = select(FranchiseeAudit).where(FranchiseeAudit.id == str(audit_id))
    result = await db.execute(query)
    audit = result.scalar_one_or_none()

    if not audit:
        raise HTTPException(status_code=404, detail="Audit not found")

    audit.status = AuditStatus.CLOSED.value
    audit.closed_at = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(audit)
    return audit


# ==================== Serviceability (Pincode-based Allocation) ====================

@router.post("/{franchisee_id}/serviceability", status_code=status.HTTP_201_CREATED)
@require_module("sales_distribution")
async def add_serviceability(
    franchisee_id: UUID,
    data: ServiceabilityRequest,
    db: DB,
    current_user: CurrentUser,
):
    """
    Add serviceability pincodes for a franchisee.

    This enables the franchisee to receive service requests for the specified pincodes.
    Use this for pincode-wise fulfillment allocation.
    """
    pincodes = data.pincodes
    service_types = data.service_types
    priority = data.priority
    max_daily_capacity = data.max_daily_capacity
    expected_response_hours = data.expected_response_hours
    expected_completion_hours = data.expected_completion_hours
    # Verify franchisee exists and is active
    franchisee_query = select(Franchisee).where(Franchisee.id == str(franchisee_id))
    franchisee_result = await db.execute(franchisee_query)
    franchisee = franchisee_result.scalar_one_or_none()

    if not franchisee:
        raise HTTPException(status_code=404, detail="Franchisee not found")

    if franchisee.status != FranchiseeStatus.ACTIVE:
        raise HTTPException(status_code=400, detail="Franchisee must be ACTIVE to add serviceability")

    # Default service types
    if not service_types:
        service_types = ["INSTALLATION", "REPAIR", "MAINTENANCE", "AMC_SERVICE"]

    created = []
    skipped = []

    for pincode in pincodes:
        # Check if already exists
        existing_query = select(FranchiseeServiceability).where(
            and_(
                FranchiseeServiceability.franchisee_id == str(franchisee_id),
                FranchiseeServiceability.pincode == pincode.strip(),
            )
        )
        existing_result = await db.execute(existing_query)
        existing = existing_result.scalar_one_or_none()

        if existing:
            # Update existing record
            existing.is_active = True
            existing.service_types = service_types
            existing.priority = priority
            existing.max_daily_capacity = max_daily_capacity
            existing.expected_response_hours = expected_response_hours
            existing.expected_completion_hours = expected_completion_hours
            existing.updated_at = datetime.now(timezone.utc)
            skipped.append({"pincode": pincode, "action": "updated"})
        else:
            # Create new record
            serviceability = FranchiseeServiceability(
                id=str(uuid4()),
                franchisee_id=str(franchisee_id),
                pincode=pincode.strip(),
                city=franchisee.city,
                state=franchisee.state,
                service_types=service_types,
                is_active=True,
                priority=priority,
                max_daily_capacity=max_daily_capacity,
                expected_response_hours=expected_response_hours,
                expected_completion_hours=expected_completion_hours,
                effective_from=date.today(),
            )
            db.add(serviceability)
            created.append({"pincode": pincode, "action": "created"})

    await db.commit()

    return {
        "message": f"Serviceability updated for {len(pincodes)} pincodes",
        "franchisee_id": str(franchisee_id),
        "created": created,
        "updated": skipped,
        "total_pincodes": len(pincodes),
    }


@router.get("/{franchisee_id}/serviceability")
@require_module("sales_distribution")
async def get_franchisee_serviceability(
    franchisee_id: UUID,
    db: DB,
    current_user: CurrentUser,
    is_active: Optional[bool] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
):
    """Get all serviceable pincodes for a franchisee."""
    query = select(FranchiseeServiceability).where(
        FranchiseeServiceability.franchisee_id == str(franchisee_id)
    )

    if is_active is not None:
        query = query.where(FranchiseeServiceability.is_active == is_active)

    # Count
    count_query = select(func.count()).select_from(query.subquery())
    total = await db.scalar(count_query) or 0

    query = query.order_by(FranchiseeServiceability.pincode).offset(skip).limit(limit)
    result = await db.execute(query)
    records = result.scalars().all()

    return {
        "franchisee_id": str(franchisee_id),
        "total": total,
        "items": [
            {
                "id": str(r.id),
                "pincode": r.pincode,
                "city": r.city,
                "state": r.state,
                "service_types": r.service_types,
                "is_active": r.is_active,
                "priority": r.priority,
                "max_daily_capacity": r.max_daily_capacity,
                "current_load": r.current_load,
                "expected_response_hours": r.expected_response_hours,
                "expected_completion_hours": r.expected_completion_hours,
                "total_jobs_completed": r.total_jobs_completed,
                "avg_rating": r.avg_rating,
                "on_time_completion_rate": r.on_time_completion_rate,
                "effective_from": str(r.effective_from) if r.effective_from else None,
                "effective_to": str(r.effective_to) if r.effective_to else None,
            }
            for r in records
        ],
    }


@router.delete("/{franchisee_id}/serviceability/{pincode}")
@require_module("sales_distribution")
async def remove_serviceability(
    franchisee_id: UUID,
    pincode: str,
    db: DB,
    current_user: CurrentUser,
    hard_delete: bool = Query(False, description="If True, permanently delete. If False, mark as inactive."),
):
    """Remove or deactivate serviceability for a pincode."""
    query = select(FranchiseeServiceability).where(
        and_(
            FranchiseeServiceability.franchisee_id == str(franchisee_id),
            FranchiseeServiceability.pincode == pincode,
        )
    )
    result = await db.execute(query)
    serviceability = result.scalar_one_or_none()

    if not serviceability:
        raise HTTPException(status_code=404, detail="Serviceability record not found")

    if hard_delete:
        await db.delete(serviceability)
        action = "deleted"
    else:
        serviceability.is_active = False
        serviceability.effective_to = date.today()
        serviceability.updated_at = datetime.now(timezone.utc)
        action = "deactivated"

    await db.commit()

    return {
        "message": f"Serviceability {action} for pincode {pincode}",
        "franchisee_id": str(franchisee_id),
        "pincode": pincode,
        "action": action,
    }


@router.put("/{franchisee_id}/serviceability/{pincode}")
@require_module("sales_distribution")
async def update_serviceability(
    franchisee_id: UUID,
    pincode: str,
    db: DB,
    current_user: CurrentUser,
    service_types: Optional[List[str]] = None,
    priority: Optional[int] = Query(None, ge=1, le=10),
    max_daily_capacity: Optional[int] = Query(None, ge=1),
    expected_response_hours: Optional[int] = Query(None, ge=1),
    expected_completion_hours: Optional[int] = Query(None, ge=1),
    is_active: Optional[bool] = None,
):
    """Update serviceability settings for a pincode."""
    query = select(FranchiseeServiceability).where(
        and_(
            FranchiseeServiceability.franchisee_id == str(franchisee_id),
            FranchiseeServiceability.pincode == pincode,
        )
    )
    result = await db.execute(query)
    serviceability = result.scalar_one_or_none()

    if not serviceability:
        raise HTTPException(status_code=404, detail="Serviceability record not found")

    if service_types is not None:
        serviceability.service_types = service_types
    if priority is not None:
        serviceability.priority = priority
    if max_daily_capacity is not None:
        serviceability.max_daily_capacity = max_daily_capacity
    if expected_response_hours is not None:
        serviceability.expected_response_hours = expected_response_hours
    if expected_completion_hours is not None:
        serviceability.expected_completion_hours = expected_completion_hours
    if is_active is not None:
        serviceability.is_active = is_active

    serviceability.updated_at = datetime.now(timezone.utc)

    await db.commit()

    return {
        "message": f"Serviceability updated for pincode {pincode}",
        "id": str(serviceability.id),
        "franchisee_id": str(franchisee_id),
        "pincode": pincode,
        "service_types": serviceability.service_types,
        "priority": serviceability.priority,
        "max_daily_capacity": serviceability.max_daily_capacity,
        "is_active": serviceability.is_active,
    }


@router.get("/serviceability/check")
@require_module("sales_distribution")
async def check_serviceability(
    pincode: str,
    db: DB,
    current_user: CurrentUser,
    service_type: Optional[str] = Query(None, description="Filter by service type"),
):
    """
    Check which franchisees can service a pincode.

    Returns franchisees sorted by priority and availability.
    """
    query = select(FranchiseeServiceability).where(
        and_(
            FranchiseeServiceability.pincode == pincode,
            FranchiseeServiceability.is_active == True,
            FranchiseeServiceability.effective_from <= date.today(),
        )
    ).order_by(
        FranchiseeServiceability.priority.asc(),
        FranchiseeServiceability.current_load.asc(),
    )

    result = await db.execute(query)
    records = result.scalars().all()

    # Filter by service type if specified
    if service_type:
        records = [
            r for r in records
            if (r.service_types and (service_type in r.service_types or "FULL_SERVICE" in r.service_types))
            or not r.service_types
        ]

    # Get franchisee details
    franchisee_ids = list(set([str(r.franchisee_id) for r in records]))
    if franchisee_ids:
        franchisees_query = select(Franchisee).where(
            and_(
                Franchisee.id.in_(franchisee_ids),
                Franchisee.status == FranchiseeStatus.ACTIVE,
            )
        )
        franchisees_result = await db.execute(franchisees_query)
        franchisees_map = {str(f.id): f for f in franchisees_result.scalars().all()}
    else:
        franchisees_map = {}

    available_franchisees = []
    for r in records:
        franchisee = franchisees_map.get(str(r.franchisee_id))
        if not franchisee:
            continue

        has_capacity = r.current_load < r.max_daily_capacity
        available_franchisees.append({
            "franchisee_id": str(franchisee.id),
            "franchisee_code": franchisee.franchisee_code,
            "franchisee_name": franchisee.name,
            "tier": franchisee.tier,
            "pincode": r.pincode,
            "service_types": r.service_types,
            "priority": r.priority,
            "has_capacity": has_capacity,
            "current_load": r.current_load,
            "max_daily_capacity": r.max_daily_capacity,
            "expected_response_hours": r.expected_response_hours,
            "expected_completion_hours": r.expected_completion_hours,
            "avg_rating": r.avg_rating,
            "on_time_completion_rate": r.on_time_completion_rate,
        })

    return {
        "pincode": pincode,
        "service_type": service_type,
        "is_serviceable": len(available_franchisees) > 0,
        "franchisees_available": len(available_franchisees),
        "franchisees": available_franchisees,
    }


@router.post("/serviceability/bulk-import")
@require_module("sales_distribution")
async def bulk_import_serviceability(
    data: List[dict],
    db: DB,
    current_user: CurrentUser,
):
    """
    Bulk import serviceability data.

    Expected format:
    [
        {
            "franchisee_code": "FRE-20240101-XXXX",
            "pincodes": ["110001", "110002", "110003"],
            "service_types": ["INSTALLATION", "REPAIR"],
            "priority": 1
        }
    ]
    """
    results = []

    for item in data:
        franchisee_code = item.get("franchisee_code")
        pincodes = item.get("pincodes", [])

        # Find franchisee
        franchisee_query = select(Franchisee).where(
            Franchisee.franchisee_code == franchisee_code
        )
        franchisee_result = await db.execute(franchisee_query)
        franchisee = franchisee_result.scalar_one_or_none()

        if not franchisee:
            results.append({
                "franchisee_code": franchisee_code,
                "status": "error",
                "message": "Franchisee not found",
            })
            continue

        created_count = 0
        updated_count = 0

        for pincode in pincodes:
            existing_query = select(FranchiseeServiceability).where(
                and_(
                    FranchiseeServiceability.franchisee_id == str(franchisee.id),
                    FranchiseeServiceability.pincode == pincode.strip(),
                )
            )
            existing_result = await db.execute(existing_query)
            existing = existing_result.scalar_one_or_none()

            if existing:
                existing.is_active = True
                existing.service_types = item.get("service_types", ["INSTALLATION"])
                existing.priority = item.get("priority", 1)
                existing.updated_at = datetime.now(timezone.utc)
                updated_count += 1
            else:
                serviceability = FranchiseeServiceability(
                    id=str(uuid4()),
                    franchisee_id=str(franchisee.id),
                    pincode=pincode.strip(),
                    city=franchisee.city,
                    state=franchisee.state,
                    service_types=item.get("service_types", ["INSTALLATION"]),
                    is_active=True,
                    priority=item.get("priority", 1),
                    max_daily_capacity=item.get("max_daily_capacity", 10),
                    effective_from=date.today(),
                )
                db.add(serviceability)
                created_count += 1

        results.append({
            "franchisee_code": franchisee_code,
            "franchisee_id": str(franchisee.id),
            "status": "success",
            "created": created_count,
            "updated": updated_count,
        })

    await db.commit()

    return {
        "message": "Bulk import completed",

        "total_items": len(data),
        "results": results,
    }


@router.post("/serviceability/reset-daily-load")
@require_module("sales_distribution")
async def reset_daily_load(
    db: DB,
    current_user: CurrentUser,
    franchisee_id: Optional[UUID] = None,
):
    """
    Reset daily load counters.

    This should be called daily (via cron job) to reset current_load to 0.
    """
    query = select(FranchiseeServiceability).where(
        FranchiseeServiceability.is_active == True
    )

    if franchisee_id:
        query = query.where(FranchiseeServiceability.franchisee_id == str(franchisee_id))

    result = await db.execute(query)
    records = result.scalars().all()

    reset_count = 0
    for r in records:
        if r.current_load > 0:
            r.current_load = 0
            r.updated_at = datetime.now(timezone.utc)
            reset_count += 1

    await db.commit()

    return {
        "message": f"Reset daily load for {reset_count} serviceability records",
        "reset_count": reset_count,
    }
