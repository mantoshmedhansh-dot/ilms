"""Lead Management API endpoints."""
from datetime import datetime, date, timedelta, timezone
from typing import Optional, List
from uuid import UUID
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, func, and_, or_, Integer
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.lead import (
    Lead, LeadActivity, LeadScoreRule, LeadAssignmentRule,
    LeadSource, LeadStatus, LeadPriority, LeadType, ActivityType
)
from app.models.user import User
from app.models.customer import Customer
from app.schemas.lead import (
    LeadCreate, LeadUpdate, LeadResponse, LeadDetailResponse, LeadListResponse,
    LeadAssignRequest, LeadStatusUpdateRequest, LeadQualifyRequest,
    LeadConvertRequest, LeadLostRequest,
    LeadActivityCreate, LeadActivityResponse,
    LeadScoreRuleCreate, LeadScoreRuleResponse,
    LeadAssignmentRuleCreate, LeadAssignmentRuleResponse,
    LeadDashboardResponse, LeadPipelineResponse, LeadSourceReportResponse,
    AutoAssignRequest, BulkAutoAssignRequest,
)
from app.api.deps import get_current_user
from app.services.lead_assignment_service import (

    LeadAssignmentService, LeadAssignmentError, AssignmentStrategy
)
from app.core.module_decorators import require_module

router = APIRouter()


# ==================== Helper Functions ====================

async def generate_lead_number(db: AsyncSession) -> str:
    """Generate unique lead number."""
    today = datetime.now(timezone.utc).strftime("%Y%m%d")
    prefix = f"LEAD-{today}-"

    result = await db.execute(
        select(func.count(Lead.id)).where(Lead.lead_number.like(f"{prefix}%"))
    )
    count = result.scalar() or 0
    return f"{prefix}{count + 1:04d}"


async def calculate_lead_score(lead: Lead, db: AsyncSession) -> tuple[int, dict]:
    """Calculate lead score based on rules."""
    result = await db.execute(
        select(LeadScoreRule).where(LeadScoreRule.is_active == True).order_by(LeadScoreRule.priority.desc())
    )
    rules = result.scalars().all()

    total_score = 0
    breakdown = {}

    for rule in rules:
        field_value = getattr(lead, rule.field, None)
        if field_value is None:
            continue

        # Convert enums to string for comparison
        if hasattr(field_value, 'value'):
            field_value = field_value.value

        matched = False
        if rule.operator == 'eq':
            matched = str(field_value) == rule.value
        elif rule.operator == 'ne':
            matched = str(field_value) != rule.value
        elif rule.operator == 'gt':
            matched = float(field_value) > float(rule.value)
        elif rule.operator == 'gte':
            matched = float(field_value) >= float(rule.value)
        elif rule.operator == 'lt':
            matched = float(field_value) < float(rule.value)
        elif rule.operator == 'lte':
            matched = float(field_value) <= float(rule.value)
        elif rule.operator == 'in':
            matched = str(field_value) in rule.value.split(',')
        elif rule.operator == 'contains':
            matched = rule.value.lower() in str(field_value).lower()

        if matched:
            total_score += rule.score_points
            breakdown[rule.name] = rule.score_points

    return total_score, breakdown


async def auto_assign_lead(lead: Lead, db: AsyncSession) -> Optional[UUID]:
    """Auto-assign lead based on rules."""
    result = await db.execute(
        select(LeadAssignmentRule).where(
            LeadAssignmentRule.is_active == True
        ).order_by(LeadAssignmentRule.priority.desc())
    )
    rules = result.scalars().all()

    for rule in rules:
        # Check source match
        if rule.source and lead.source != rule.source:
            continue
        # Check lead type match
        if rule.lead_type and lead.lead_type != rule.lead_type:
            continue
        # Check region match
        if rule.region_id and lead.region_id != rule.region_id:
            continue
        # Check pincode pattern
        if rule.pincode_pattern and lead.pincode:
            if not lead.pincode.startswith(rule.pincode_pattern):
                continue
        # Check score range
        if rule.min_score and lead.score < rule.min_score:
            continue
        if rule.max_score and lead.score > rule.max_score:
            continue

        # Found matching rule
        if rule.assign_to_user_id:
            return rule.assign_to_user_id
        # TODO: Implement round robin

    return None


# ==================== Lead CRUD ====================

@router.post("", response_model=LeadResponse, status_code=status.HTTP_201_CREATED)
@require_module("crm_service")
async def create_lead(
    lead_in: LeadCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new lead."""
    # Check for duplicate phone
    result = await db.execute(
        select(Lead).where(
            and_(
                Lead.phone == lead_in.phone,
                Lead.status.notin_([LeadStatus.WON, LeadStatus.LOST, LeadStatus.DISQUALIFIED])
            )
        )
    )
    existing = result.scalar_one_or_none()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Lead with phone {lead_in.phone} already exists (Lead #{existing.lead_number})"
        )

    # Generate lead number
    lead_number = await generate_lead_number(db)

    # Create lead
    lead = Lead(
        lead_number=lead_number,
        **lead_in.model_dump(exclude={'interested_products', 'tags'}),
        interested_products={"ids": [str(p) for p in lead_in.interested_products]} if lead_in.interested_products else None,
        tags={"values": lead_in.tags} if lead_in.tags else None,
        created_by_id=current_user.id
    )

    db.add(lead)
    await db.flush()

    # Calculate score
    score, breakdown = await calculate_lead_score(lead, db)
    lead.score = score
    lead.score_breakdown = breakdown

    # Auto-assign if not assigned
    if not lead.assigned_to_id:
        assigned_id = await auto_assign_lead(lead, db)
        if assigned_id:
            lead.assigned_to_id = assigned_id
            lead.assigned_at = datetime.now(timezone.utc)
            lead.assigned_by_id = current_user.id

    # Create initial activity
    activity = LeadActivity(
        lead_id=lead.id,
        activity_type=ActivityType.NOTE,
        subject="Lead Created",
        description=f"Lead created from {lead.source}",
        created_by_id=current_user.id
    )
    db.add(activity)

    await db.commit()
    await db.refresh(lead)

    # Build response
    response = LeadResponse.model_validate(lead)
    if lead.assigned_to:
        response.assigned_to_name = f"{lead.assigned_to.first_name} {lead.assigned_to.last_name or ''}".strip()

    return response


@router.get("", response_model=LeadListResponse)
@require_module("crm_service")
async def list_leads(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    status: Optional[LeadStatus] = None,
    source: Optional[LeadSource] = None,
    priority: Optional[LeadPriority] = None,
    assigned_to_id: Optional[UUID] = None,
    is_qualified: Optional[bool] = None,
    city: Optional[str] = None,
    search: Optional[str] = None,
    follow_up_due: Optional[bool] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List leads with filters."""
    query = select(Lead)

    # Apply filters
    if status:
        query = query.where(Lead.status == status)
    if source:
        query = query.where(Lead.source == source)
    if priority:
        query = query.where(Lead.priority == priority)
    if assigned_to_id:
        query = query.where(Lead.assigned_to_id == assigned_to_id)
    if is_qualified is not None:
        query = query.where(Lead.is_qualified == is_qualified)
    if city:
        query = query.where(Lead.city.ilike(f"%{city}%"))
    if search:
        query = query.where(
            or_(
                Lead.first_name.ilike(f"%{search}%"),
                Lead.last_name.ilike(f"%{search}%"),
                Lead.phone.ilike(f"%{search}%"),
                Lead.email.ilike(f"%{search}%"),
                Lead.company_name.ilike(f"%{search}%"),
                Lead.lead_number.ilike(f"%{search}%")
            )
        )
    if follow_up_due:
        query = query.where(
            and_(
                Lead.next_follow_up_date.isnot(None),
                Lead.next_follow_up_date <= datetime.now(timezone.utc)
            )
        )

    # Get total
    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar() or 0

    # Get items
    query = query.order_by(Lead.created_at.desc()).offset(skip).limit(limit)
    result = await db.execute(query)
    leads = result.scalars().all()

    # Build response
    items = []
    for lead in leads:
        item = LeadResponse.model_validate(lead)
        if lead.assigned_to:
            item.assigned_to_name = f"{lead.assigned_to.first_name} {lead.assigned_to.last_name or ''}".strip()
        items.append(item)

    return LeadListResponse(items=items, total=total, skip=skip, limit=limit)


@router.get("/{lead_id}", response_model=LeadDetailResponse)
@require_module("crm_service")
async def get_lead(
    lead_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get lead details."""
    result = await db.execute(
        select(Lead).where(Lead.id == lead_id)
    )
    lead = result.scalar_one_or_none()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    # Get activities
    act_result = await db.execute(
        select(LeadActivity).where(LeadActivity.lead_id == lead_id).order_by(LeadActivity.created_at.desc())
    )
    activities = act_result.scalars().all()

    # Build response
    response = LeadDetailResponse.model_validate(lead)
    if lead.assigned_to:
        response.assigned_to_name = f"{lead.assigned_to.first_name} {lead.assigned_to.last_name or ''}".strip()

    # Add activities
    response.activities = []
    for act in activities:
        act_resp = LeadActivityResponse.model_validate(act)
        if act.created_by:
            act_resp.created_by_name = f"{act.created_by.first_name} {act.created_by.last_name or ''}".strip()
        response.activities.append(act_resp)

    return response


@router.put("/{lead_id}", response_model=LeadResponse)
@require_module("crm_service")
async def update_lead(
    lead_id: UUID,
    lead_in: LeadUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update a lead."""
    result = await db.execute(
        select(Lead).where(Lead.id == lead_id)
    )
    lead = result.scalar_one_or_none()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    # Update fields
    update_data = lead_in.model_dump(exclude_unset=True, exclude={'interested_products', 'tags'})
    for field, value in update_data.items():
        setattr(lead, field, value)

    if lead_in.interested_products is not None:
        lead.interested_products = {"ids": [str(p) for p in lead_in.interested_products]}
    if lead_in.tags is not None:
        lead.tags = {"values": lead_in.tags}

    # Recalculate score
    score, breakdown = await calculate_lead_score(lead, db)
    lead.score = score
    lead.score_breakdown = breakdown

    await db.commit()
    await db.refresh(lead)

    response = LeadResponse.model_validate(lead)
    if lead.assigned_to:
        response.assigned_to_name = f"{lead.assigned_to.first_name} {lead.assigned_to.last_name or ''}".strip()

    return response


@router.post("/{lead_id}/assign", response_model=LeadResponse)
@require_module("crm_service")
async def assign_lead(
    lead_id: UUID,
    assign_in: LeadAssignRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Assign lead to a user."""
    result = await db.execute(
        select(Lead).where(Lead.id == lead_id)
    )
    lead = result.scalar_one_or_none()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    old_assignee_id = lead.assigned_to_id

    # Update assignment
    lead.assigned_to_id = assign_in.assigned_to_id
    lead.assigned_at = datetime.now(timezone.utc)
    lead.assigned_by_id = current_user.id

    # Log activity
    activity = LeadActivity(
        lead_id=lead.id,
        activity_type=ActivityType.ASSIGNMENT,
        subject="Lead Assigned",
        description=assign_in.notes or "Lead reassigned",
        old_assignee_id=old_assignee_id,
        new_assignee_id=assign_in.assigned_to_id,
        created_by_id=current_user.id
    )
    db.add(activity)

    await db.commit()
    await db.refresh(lead)

    response = LeadResponse.model_validate(lead)
    if lead.assigned_to:
        response.assigned_to_name = f"{lead.assigned_to.first_name} {lead.assigned_to.last_name or ''}".strip()

    return response


# ==================== Auto Assignment Endpoints ====================

@router.post("/{lead_id}/auto-assign")
@require_module("crm_service")
async def auto_assign_lead(
    lead_id: UUID,
    request: AutoAssignRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Auto-assign a lead using the specified strategy.

    Strategies:
    - ROUND_ROBIN: Even distribution among agents
    - LOAD_BALANCED: Assign to agent with lowest current load
    - GEOGRAPHIC: Match lead location to agent territory
    """
    try:
        strategy = AssignmentStrategy(request.strategy.upper())
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid strategy. Valid options: {[s.value for s in AssignmentStrategy]}"
        )

    company_id = current_user.company_id
    if not company_id:
        raise HTTPException(status_code=400, detail="Company ID required")

    try:
        service = LeadAssignmentService(db, company_id)
        lead = await service.assign_lead(
            lead_id=lead_id,
            strategy=strategy,
            team_id=request.team_id,
            user_id=current_user.id
        )

        return {
            "success": True,
            "lead_id": str(lead_id),
            "assigned_to": str(lead.assigned_to) if lead.assigned_to else None,
            "strategy": strategy.value,
            "message": "Lead assigned successfully"
        }

    except LeadAssignmentError as e:
        raise HTTPException(status_code=400, detail=e.message)


@router.post("/auto-assign/bulk")
@require_module("crm_service")
async def bulk_auto_assign_leads(
    request: BulkAutoAssignRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Auto-assign multiple leads in bulk.

    Either provide specific lead_ids or set assign_all_unassigned=True.
    """
    try:
        strategy = AssignmentStrategy(request.strategy.upper())
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid strategy. Valid options: {[s.value for s in AssignmentStrategy]}"
        )

    company_id = current_user.company_id
    if not company_id:
        raise HTTPException(status_code=400, detail="Company ID required")

    service = LeadAssignmentService(db, company_id)

    if request.assign_all_unassigned:
        result = await service.auto_assign_all_pending(
            strategy=strategy,
            team_id=request.team_id,
            user_id=current_user.id
        )
    elif request.lead_ids:
        result = await service.bulk_assign_leads(
            lead_ids=request.lead_ids,
            strategy=strategy,
            team_id=request.team_id,
            user_id=current_user.id
        )
    else:
        raise HTTPException(
            status_code=400,
            detail="Either provide lead_ids or set assign_all_unassigned=True"
        )

    return result


@router.get("/unassigned")
@require_module("crm_service")
async def get_unassigned_leads(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    source: Optional[str] = None,
    limit: int = Query(100, ge=1, le=500)
):
    """Get all unassigned leads for assignment."""
    company_id = current_user.company_id
    if not company_id:
        raise HTTPException(status_code=400, detail="Company ID required")

    service = LeadAssignmentService(db, company_id)
    leads = await service.get_unassigned_leads(limit=limit, source=source)

    return {
        "count": len(leads),
        "leads": [
            {
                "id": str(lead.id),
                "lead_number": lead.lead_number,
                "name": lead.name,
                "source": lead.source if lead.source else None,
                "created_at": lead.created_at.isoformat() if lead.created_at else None,
            }
            for lead in leads
        ]
    }


@router.get("/assignment-stats")
@require_module("crm_service")
async def get_lead_assignment_stats(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    days: int = Query(30, ge=1, le=365)
):
    """Get lead assignment statistics and distribution."""
    company_id = current_user.company_id
    if not company_id:
        raise HTTPException(status_code=400, detail="Company ID required")

    service = LeadAssignmentService(db, company_id)
    start_date = datetime.now(timezone.utc) - timedelta(days=days)

    stats = await service.get_assignment_stats(start_date=start_date)

    return stats


@router.get("/agents/workload")
@require_module("crm_service")
async def get_agents_workload(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    team_id: Optional[UUID] = None
):
    """Get current workload for all sales agents."""
    company_id = current_user.company_id
    if not company_id:
        raise HTTPException(status_code=400, detail="Company ID required")

    service = LeadAssignmentService(db, company_id)
    agents = await service.get_available_agents(team_id=team_id)

    workloads = []
    for agent in agents:
        load = await service.get_agent_current_load(agent.id)
        workloads.append({
            "agent_id": str(agent.id),
            "agent_name": f"{agent.first_name} {agent.last_name or ''}".strip() if hasattr(agent, 'first_name') else str(agent.id),
            "email": agent.email if hasattr(agent, 'email') else None,
            **load
        })

    return {
        "agents": workloads,
        "total_agents": len(workloads)
    }


@router.post("/{lead_id}/status", response_model=LeadResponse)
@require_module("crm_service")
async def update_lead_status(
    lead_id: UUID,
    status_in: LeadStatusUpdateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update lead status."""
    result = await db.execute(
        select(Lead).where(Lead.id == lead_id)
    )
    lead = result.scalar_one_or_none()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    old_status = lead.status

    # Update status
    lead.status = status_in.status

    # Update follow-up
    if status_in.follow_up_date:
        lead.next_follow_up_date = status_in.follow_up_date
        lead.next_follow_up_notes = status_in.follow_up_notes

    # Log activity
    activity = LeadActivity(
        lead_id=lead.id,
        activity_type=ActivityType.STATUS_CHANGE,
        subject=f"Status changed to {status_in.status.value}",
        description=status_in.notes,
        old_status=old_status,
        new_status=status_in.status,
        follow_up_date=status_in.follow_up_date,
        follow_up_notes=status_in.follow_up_notes,
        created_by_id=current_user.id
    )
    db.add(activity)

    await db.commit()
    await db.refresh(lead)

    response = LeadResponse.model_validate(lead)
    if lead.assigned_to:
        response.assigned_to_name = f"{lead.assigned_to.first_name} {lead.assigned_to.last_name or ''}".strip()

    return response


@router.post("/{lead_id}/qualify", response_model=LeadResponse)
@require_module("crm_service")
async def qualify_lead(
    lead_id: UUID,
    qualify_in: LeadQualifyRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Qualify or disqualify a lead."""
    result = await db.execute(
        select(Lead).where(Lead.id == lead_id)
    )
    lead = result.scalar_one_or_none()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    lead.is_qualified = qualify_in.is_qualified
    lead.qualification_date = datetime.now(timezone.utc) if qualify_in.is_qualified else None
    lead.qualified_by_id = current_user.id if qualify_in.is_qualified else None

    if qualify_in.score is not None:
        lead.score = qualify_in.score

    if qualify_in.is_qualified:
        lead.status = LeadStatus.QUALIFIED.value
    else:
        lead.status = LeadStatus.DISQUALIFIED.value

    # Log activity
    activity = LeadActivity(
        lead_id=lead.id,
        activity_type=ActivityType.STATUS_CHANGE,
        subject="Lead Qualified" if qualify_in.is_qualified else "Lead Disqualified",
        description=qualify_in.notes,
        old_status=lead.status,
        new_status=LeadStatus.QUALIFIED if qualify_in.is_qualified else LeadStatus.DISQUALIFIED,
        created_by_id=current_user.id
    )
    db.add(activity)

    await db.commit()
    await db.refresh(lead)

    response = LeadResponse.model_validate(lead)
    if lead.assigned_to:
        response.assigned_to_name = f"{lead.assigned_to.first_name} {lead.assigned_to.last_name or ''}".strip()

    return response


@router.post("/{lead_id}/convert", response_model=LeadResponse)
@require_module("crm_service")
async def convert_lead(
    lead_id: UUID,
    convert_in: LeadConvertRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Convert lead to customer/order."""
    result = await db.execute(
        select(Lead).where(Lead.id == lead_id)
    )
    lead = result.scalar_one_or_none()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    if lead.status == LeadStatus.WON:
        raise HTTPException(status_code=400, detail="Lead already converted")

    # Create customer if requested
    if convert_in.create_customer:
        # Check if customer with same phone exists
        cust_result = await db.execute(
            select(Customer).where(Customer.phone == lead.phone)
        )
        existing_customer = cust_result.scalar_one_or_none()

        if existing_customer:
            lead.converted_customer_id = existing_customer.id
        else:
            # Generate customer code
            today = datetime.now(timezone.utc).strftime("%Y%m%d")
            cust_count_result = await db.execute(
                select(func.count(Customer.id)).where(Customer.customer_code.like(f"CUST-{today}%"))
            )
            cust_count = cust_count_result.scalar() or 0
            customer_code = f"CUST-{today}-{cust_count + 1:04d}"

            customer = Customer(
                customer_code=customer_code,
                first_name=lead.first_name,
                last_name=lead.last_name,
                email=lead.email,
                phone=lead.phone,
                alternate_phone=lead.alternate_phone,
                customer_type="INDIVIDUAL" if lead.lead_type == LeadType.INDIVIDUAL else "BUSINESS",
                source=lead.source
            )
            db.add(customer)
            await db.flush()
            lead.converted_customer_id = customer.id

    # Update lead status
    lead.status = LeadStatus.WON.value
    lead.converted_at = datetime.now(timezone.utc)
    lead.converted_by_id = current_user.id
    lead.actual_value = lead.estimated_value

    # Log activity
    activity = LeadActivity(
        lead_id=lead.id,
        activity_type=ActivityType.CONVERSION,
        subject="Lead Converted to Customer",
        description=convert_in.notes or "Lead successfully converted",
        old_status=lead.status,
        new_status=LeadStatus.WON,
        created_by_id=current_user.id
    )
    db.add(activity)

    await db.commit()
    await db.refresh(lead)

    response = LeadResponse.model_validate(lead)
    if lead.assigned_to:
        response.assigned_to_name = f"{lead.assigned_to.first_name} {lead.assigned_to.last_name or ''}".strip()

    return response


@router.post("/{lead_id}/lost", response_model=LeadResponse)
@require_module("crm_service")
async def mark_lead_lost(
    lead_id: UUID,
    lost_in: LeadLostRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Mark lead as lost."""
    result = await db.execute(
        select(Lead).where(Lead.id == lead_id)
    )
    lead = result.scalar_one_or_none()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    old_status = lead.status

    lead.status = LeadStatus.LOST.value
    lead.lost_reason = lost_in.lost_reason
    lead.lost_reason_details = lost_in.lost_reason_details
    lead.lost_to_competitor = lost_in.lost_to_competitor
    lead.lost_at = datetime.now(timezone.utc)

    # Log activity
    activity = LeadActivity(
        lead_id=lead.id,
        activity_type=ActivityType.STATUS_CHANGE,
        subject=f"Lead Lost - {lost_in.lost_reason.value}",
        description=lost_in.lost_reason_details,
        old_status=old_status,
        new_status=LeadStatus.LOST,
        created_by_id=current_user.id
    )
    db.add(activity)

    await db.commit()
    await db.refresh(lead)

    response = LeadResponse.model_validate(lead)
    return response


# ==================== Lead Activities ====================

@router.post("/{lead_id}/activities", response_model=LeadActivityResponse, status_code=status.HTTP_201_CREATED)
@require_module("crm_service")
async def add_lead_activity(
    lead_id: UUID,
    activity_in: LeadActivityCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Add activity to a lead."""
    result = await db.execute(
        select(Lead).where(Lead.id == lead_id)
    )
    lead = result.scalar_one_or_none()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    # Create activity
    activity = LeadActivity(
        lead_id=lead_id,
        **activity_in.model_dump(),
        created_by_id=current_user.id
    )
    db.add(activity)

    # Update lead contact tracking
    lead.last_contacted_at = datetime.now(timezone.utc)
    lead.contact_attempts += 1

    # Update follow-up
    if activity_in.follow_up_date:
        lead.next_follow_up_date = activity_in.follow_up_date
        lead.next_follow_up_notes = activity_in.follow_up_notes

    await db.commit()
    await db.refresh(activity)

    response = LeadActivityResponse.model_validate(activity)
    response.created_by_name = f"{current_user.first_name} {current_user.last_name or ''}".strip()

    return response


@router.get("/{lead_id}/activities", response_model=List[LeadActivityResponse])
@require_module("crm_service")
async def get_lead_activities(
    lead_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all activities for a lead."""
    result = await db.execute(
        select(LeadActivity).where(LeadActivity.lead_id == lead_id).order_by(LeadActivity.created_at.desc())
    )
    activities = result.scalars().all()

    items = []
    for act in activities:
        item = LeadActivityResponse.model_validate(act)
        if act.created_by:
            item.created_by_name = f"{act.created_by.first_name} {act.created_by.last_name or ''}".strip()
        items.append(item)

    return items


# ==================== Dashboard & Reports ====================

@router.get("/dashboard/overview", response_model=LeadDashboardResponse)
@require_module("crm_service")
async def get_lead_dashboard(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get lead management dashboard."""
    today = date.today()
    today_start = datetime.combine(today, datetime.min.time())

    # Total leads
    total_result = await db.execute(select(func.count(Lead.id)))
    total_leads = total_result.scalar() or 0

    # New today
    new_result = await db.execute(
        select(func.count(Lead.id)).where(Lead.created_at >= today_start)
    )
    new_leads_today = new_result.scalar() or 0

    # In pipeline (not won/lost/disqualified)
    pipeline_result = await db.execute(
        select(func.count(Lead.id)).where(
            Lead.status.notin_([LeadStatus.WON, LeadStatus.LOST, LeadStatus.DISQUALIFIED])
        )
    )
    leads_in_pipeline = pipeline_result.scalar() or 0

    # By status
    status_result = await db.execute(
        select(Lead.status, func.count(Lead.id)).group_by(Lead.status)
    )
    leads_by_status = {str(row[0].value): row[1] for row in status_result.all()}

    # Converted today
    converted_result = await db.execute(
        select(func.count(Lead.id)).where(
            and_(Lead.status == LeadStatus.WON, Lead.converted_at >= today_start)
        )
    )
    converted_today = converted_result.scalar() or 0

    # Conversion rate
    total_closed = leads_by_status.get("WON", 0) + leads_by_status.get("LOST", 0)
    conversion_rate = Decimal("0")
    if total_closed > 0:
        conversion_rate = Decimal(str(round(leads_by_status.get("WON", 0) / total_closed * 100, 2)))

    # Total value won
    value_result = await db.execute(
        select(func.sum(Lead.actual_value)).where(Lead.status == LeadStatus.WON)
    )
    total_value_won = value_result.scalar() or Decimal("0")

    # Pending follow-ups
    pending_result = await db.execute(
        select(func.count(Lead.id)).where(
            and_(
                Lead.next_follow_up_date.isnot(None),
                Lead.next_follow_up_date > datetime.now(timezone.utc),
                Lead.status.notin_([LeadStatus.WON, LeadStatus.LOST, LeadStatus.DISQUALIFIED])
            )
        )
    )
    pending_follow_ups = pending_result.scalar() or 0

    # Overdue follow-ups
    overdue_result = await db.execute(
        select(func.count(Lead.id)).where(
            and_(
                Lead.next_follow_up_date.isnot(None),
                Lead.next_follow_up_date <= datetime.now(timezone.utc),
                Lead.status.notin_([LeadStatus.WON, LeadStatus.LOST, LeadStatus.DISQUALIFIED])
            )
        )
    )
    overdue_follow_ups = overdue_result.scalar() or 0

    # By source
    source_result = await db.execute(
        select(Lead.source, func.count(Lead.id)).group_by(Lead.source)
    )
    leads_by_source = {str(row[0].value): row[1] for row in source_result.all()}

    # Qualified leads
    qualified_result = await db.execute(
        select(func.count(Lead.id)).where(Lead.is_qualified == True)
    )
    qualified_leads = qualified_result.scalar() or 0

    return LeadDashboardResponse(
        date=today,
        total_leads=total_leads,
        new_leads_today=new_leads_today,
        leads_in_pipeline=leads_in_pipeline,
        leads_by_status=leads_by_status,
        converted_today=converted_today,
        conversion_rate=conversion_rate,
        total_value_won=total_value_won,
        pending_follow_ups=pending_follow_ups,
        overdue_follow_ups=overdue_follow_ups,
        leads_by_source=leads_by_source,
        qualified_leads=qualified_leads
    )


@router.get("/reports/pipeline", response_model=LeadPipelineResponse)
@require_module("crm_service")
async def get_pipeline_report(
    start_date: date = Query(...),
    end_date: date = Query(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get lead pipeline/funnel report."""
    start_dt = datetime.combine(start_date, datetime.min.time())
    end_dt = datetime.combine(end_date, datetime.max.time())

    # Pipeline by status with value
    result = await db.execute(
        select(
            Lead.status,
            func.count(Lead.id),
            func.sum(Lead.estimated_value)
        ).where(
            and_(Lead.created_at >= start_dt, Lead.created_at <= end_dt)
        ).group_by(Lead.status)
    )
    rows = result.all()

    pipeline = []
    for row in rows:
        pipeline.append({
            "status": row[0].value,
            "count": row[1],
            "value": float(row[2] or 0)
        })

    # Funnel stages
    total = sum(p["count"] for p in pipeline)
    funnel = []
    if total > 0:
        for p in pipeline:
            funnel.append({
                "stage": p["status"],
                "count": p["count"],
                "percentage": round(p["count"] / total * 100, 2)
            })

    return LeadPipelineResponse(
        start_date=start_date,
        end_date=end_date,
        pipeline=pipeline,
        conversion_funnel=funnel
    )


@router.get("/reports/source", response_model=LeadSourceReportResponse)
@require_module("crm_service")
async def get_source_report(
    start_date: date = Query(...),
    end_date: date = Query(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get lead source performance report."""
    start_dt = datetime.combine(start_date, datetime.min.time())
    end_dt = datetime.combine(end_date, datetime.max.time())

    # By source with conversion
    result = await db.execute(
        select(
            Lead.source,
            func.count(Lead.id),
            func.sum(func.cast(Lead.status == LeadStatus.WON, Integer)),
            func.sum(Lead.actual_value)
        ).where(
            and_(Lead.created_at >= start_dt, Lead.created_at <= end_dt)
        ).group_by(Lead.source)
    )
    rows = result.all()

    by_source = []
    best_rate = 0
    best_source = None
    total_leads = 0
    total_converted = 0

    for row in rows:
        total = row[1]
        converted = row[2] or 0
        rate = round(converted / total * 100, 2) if total > 0 else 0
        value = float(row[3] or 0)

        total_leads += total
        total_converted += converted

        by_source.append({
            "source": row[0].value,
            "total": total,
            "converted": converted,
            "conversion_rate": rate,
            "value": value
        })

        if rate > best_rate:
            best_rate = rate
            best_source = row[0].value

    return LeadSourceReportResponse(
        start_date=start_date,
        end_date=end_date,
        by_source=by_source,
        best_performing_source=best_source,
        total_leads=total_leads,
        total_converted=total_converted
    )


# ==================== Score Rules ====================

@router.post("/score-rules", response_model=LeadScoreRuleResponse, status_code=status.HTTP_201_CREATED)
@require_module("crm_service")
async def create_score_rule(
    rule_in: LeadScoreRuleCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a lead score rule."""
    rule = LeadScoreRule(**rule_in.model_dump())
    db.add(rule)
    await db.commit()
    await db.refresh(rule)
    return LeadScoreRuleResponse.model_validate(rule)


@router.get("/score-rules", response_model=List[LeadScoreRuleResponse])
@require_module("crm_service")
async def list_score_rules(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List all score rules."""
    result = await db.execute(
        select(LeadScoreRule).order_by(LeadScoreRule.priority.desc())
    )
    rules = result.scalars().all()
    return [LeadScoreRuleResponse.model_validate(r) for r in rules]


# ==================== Assignment Rules ====================

@router.post("/assignment-rules", response_model=LeadAssignmentRuleResponse, status_code=status.HTTP_201_CREATED)
@require_module("crm_service")
async def create_assignment_rule(
    rule_in: LeadAssignmentRuleCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a lead assignment rule."""
    rule = LeadAssignmentRule(
        **rule_in.model_dump(exclude={'round_robin_users'}),
        round_robin_users={"ids": [str(u) for u in rule_in.round_robin_users]} if rule_in.round_robin_users else None
    )
    db.add(rule)
    await db.commit()
    await db.refresh(rule)
    return LeadAssignmentRuleResponse.model_validate(rule)


@router.get("/assignment-rules", response_model=List[LeadAssignmentRuleResponse])
@require_module("crm_service")
async def list_assignment_rules(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List all assignment rules."""
    result = await db.execute(
        select(LeadAssignmentRule).order_by(LeadAssignmentRule.priority.desc())
    )
    rules = result.scalars().all()
    return [LeadAssignmentRuleResponse.model_validate(r) for r in rules]
