"""API endpoints for Escalation Management module."""
from datetime import datetime, date, timedelta, timezone
from typing import Optional, List
from uuid import UUID
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, func, and_, or_, case
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models.escalation import (
    EscalationMatrix, Escalation, EscalationHistory, EscalationComment,
    EscalationNotification, SLAConfiguration,
    EscalationLevel, EscalationStatus, EscalationPriority,
    EscalationSource, EscalationReason, NotificationChannel
)
from app.models.user import User
from app.schemas.escalation import (
    # Matrix
    EscalationMatrixCreate, EscalationMatrixUpdate, EscalationMatrixResponse,
    # Escalation
    EscalationCreate, EscalationUpdate, EscalationResponse,
    EscalationDetailResponse, EscalationListResponse,
    # Requests
    EscalationAssignRequest, EscalationEscalateRequest,
    EscalationDeEscalateRequest, EscalationAcknowledgeRequest,
    EscalationResolveRequest, EscalationReopenRequest,
    EscalationFeedbackRequest,
    # Comments
    EscalationCommentCreate, EscalationCommentResponse,
    # History
    EscalationHistoryResponse,
    # SLA
    SLAConfigurationCreate, SLAConfigurationResponse,
    # Dashboard
    EscalationDashboardResponse, EscalationAgingReportResponse,
    SLAComplianceReportResponse
)
from app.api.deps import get_current_user
from app.core.module_decorators import require_module

router = APIRouter()


# ==================== Escalation Matrix Endpoints ====================

@router.post("/matrix", response_model=EscalationMatrixResponse, status_code=status.HTTP_201_CREATED)
@require_module("crm_service")
async def create_escalation_matrix(
    data: EscalationMatrixCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new escalation matrix rule."""
    matrix = EscalationMatrix(**data.model_dump())
    db.add(matrix)
    await db.commit()
    await db.refresh(matrix)
    return matrix


@router.get("/matrix", response_model=List[EscalationMatrixResponse])
@require_module("crm_service")
async def list_escalation_matrix(
    source_type: Optional[EscalationSource] = None,
    level: Optional[EscalationLevel] = None,
    is_active: Optional[bool] = True,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List escalation matrix rules."""
    query = select(EscalationMatrix)

    if source_type:
        query = query.where(EscalationMatrix.source_type == source_type)
    if level:
        query = query.where(EscalationMatrix.level == level)
    if is_active is not None:
        query = query.where(EscalationMatrix.is_active == is_active)

    query = query.order_by(EscalationMatrix.sort_order, EscalationMatrix.level)
    query = query.offset(skip).limit(limit)

    result = await db.execute(query)
    return result.scalars().all()


@router.get("/matrix/{matrix_id}", response_model=EscalationMatrixResponse)
@require_module("crm_service")
async def get_escalation_matrix(
    matrix_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get escalation matrix rule by ID."""
    result = await db.execute(
        select(EscalationMatrix).where(EscalationMatrix.id == matrix_id)
    )
    matrix = result.scalar_one_or_none()
    if not matrix:
        raise HTTPException(status_code=404, detail="Escalation matrix not found")
    return matrix


@router.put("/matrix/{matrix_id}", response_model=EscalationMatrixResponse)
@require_module("crm_service")
async def update_escalation_matrix(
    matrix_id: UUID,
    data: EscalationMatrixUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update escalation matrix rule."""
    result = await db.execute(
        select(EscalationMatrix).where(EscalationMatrix.id == matrix_id)
    )
    matrix = result.scalar_one_or_none()
    if not matrix:
        raise HTTPException(status_code=404, detail="Escalation matrix not found")

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(matrix, field, value)

    matrix.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(matrix)
    return matrix


@router.delete("/matrix/{matrix_id}", status_code=status.HTTP_204_NO_CONTENT)
@require_module("crm_service")
async def delete_escalation_matrix(
    matrix_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete (deactivate) escalation matrix rule."""
    result = await db.execute(
        select(EscalationMatrix).where(EscalationMatrix.id == matrix_id)
    )
    matrix = result.scalar_one_or_none()
    if not matrix:
        raise HTTPException(status_code=404, detail="Escalation matrix not found")

    matrix.is_active = False
    matrix.updated_at = datetime.now(timezone.utc)
    await db.commit()


# ==================== Escalation CRUD Endpoints ====================

@router.post("", response_model=EscalationResponse, status_code=status.HTTP_201_CREATED)
@require_module("crm_service")
async def create_escalation(
    data: EscalationCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new escalation."""
    # Generate escalation number
    today = datetime.now(timezone.utc).strftime("%Y%m%d")
    count_result = await db.execute(
        select(func.count(Escalation.id)).where(
            Escalation.escalation_number.like(f"ESC-{today}%")
        )
    )
    count = count_result.scalar() or 0
    escalation_number = f"ESC-{today}-{count + 1:04d}"

    # Get SLA configuration
    sla_query = select(SLAConfiguration).where(
        and_(
            SLAConfiguration.source_type == data.source_type,
            SLAConfiguration.priority == data.priority,
            SLAConfiguration.is_active == True
        )
    )
    if data.category_id:
        sla_query = sla_query.where(
            or_(
                SLAConfiguration.category_id == data.category_id,
                SLAConfiguration.category_id == None
            )
        )
    sla_result = await db.execute(sla_query.order_by(SLAConfiguration.category_id.desc()).limit(1))
    sla_config = sla_result.scalar_one_or_none()

    # Calculate SLA due dates
    now = datetime.now(timezone.utc)
    response_due_at = None
    resolution_due_at = None

    if sla_config:
        response_due_at = now + timedelta(minutes=sla_config.response_time_minutes)
        resolution_due_at = now + timedelta(minutes=sla_config.resolution_time_minutes)
    else:
        # Default SLA based on priority
        sla_minutes = {
            EscalationPriority.LOW: (480, 2880),      # 8h response, 48h resolution
            EscalationPriority.MEDIUM: (240, 1440),   # 4h response, 24h resolution
            EscalationPriority.HIGH: (120, 480),      # 2h response, 8h resolution
            EscalationPriority.CRITICAL: (60, 240),   # 1h response, 4h resolution
        }
        resp_mins, res_mins = sla_minutes.get(data.priority, (240, 1440))
        response_due_at = now + timedelta(minutes=resp_mins)
        resolution_due_at = now + timedelta(minutes=res_mins)

    escalation = Escalation(
        escalation_number=escalation_number,
        source_type=data.source_type,
        source_id=data.source_id,
        source_reference=data.source_reference,
        customer_id=data.customer_id,
        customer_name=data.customer_name,
        customer_phone=data.customer_phone,
        customer_email=data.customer_email,
        subject=data.subject,
        description=data.description,
        priority=data.priority,
        reason=data.reason,
        reason_details=data.reason_details,
        product_id=data.product_id,
        category_id=data.category_id,
        region_id=data.region_id,
        dealer_id=data.dealer_id,
        tags=data.tags,
        current_level=EscalationLevel.L1,
        status=EscalationStatus.NEW,
        response_due_at=response_due_at,
        resolution_due_at=resolution_due_at,
        assigned_to_id=data.assigned_to_id,
        internal_notes=data.internal_notes,
        created_by_id=current_user.id
    )

    if data.assigned_to_id:
        escalation.assigned_at = now

    db.add(escalation)
    await db.commit()
    await db.refresh(escalation)

    # Create initial history entry
    history = EscalationHistory(
        escalation_id=escalation.id,
        to_level=EscalationLevel.L1,
        to_status=EscalationStatus.NEW,
        action="CREATED",
        notes="Escalation created",
        changed_by_id=current_user.id
    )
    db.add(history)
    await db.commit()

    return escalation


@router.get("", response_model=EscalationListResponse)
@require_module("crm_service")
async def list_escalations(
    status: Optional[EscalationStatus] = None,
    level: Optional[EscalationLevel] = None,
    priority: Optional[EscalationPriority] = None,
    source_type: Optional[EscalationSource] = None,
    assigned_to_id: Optional[UUID] = None,
    customer_id: Optional[UUID] = None,
    sla_breached: Optional[bool] = None,
    search: Optional[str] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List escalations with filters."""
    query = select(Escalation)
    count_query = select(func.count(Escalation.id))

    # Apply filters
    filters = []

    if status:
        filters.append(Escalation.status == status)
    if level:
        filters.append(Escalation.current_level == level)
    if priority:
        filters.append(Escalation.priority == priority)
    if source_type:
        filters.append(Escalation.source_type == source_type)
    if assigned_to_id:
        filters.append(Escalation.assigned_to_id == assigned_to_id)
    if customer_id:
        filters.append(Escalation.customer_id == customer_id)
    if sla_breached:
        filters.append(
            or_(
                Escalation.is_response_sla_breached == True,
                Escalation.is_resolution_sla_breached == True
            )
        )
    if search:
        search_filter = or_(
            Escalation.escalation_number.ilike(f"%{search}%"),
            Escalation.subject.ilike(f"%{search}%"),
            Escalation.customer_name.ilike(f"%{search}%"),
            Escalation.customer_phone.ilike(f"%{search}%")
        )
        filters.append(search_filter)
    if start_date:
        filters.append(Escalation.created_at >= datetime.combine(start_date, datetime.min.time()))
    if end_date:
        filters.append(Escalation.created_at <= datetime.combine(end_date, datetime.max.time()))

    if filters:
        query = query.where(and_(*filters))
        count_query = count_query.where(and_(*filters))

    # Get total count
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # Get paginated results
    query = query.order_by(Escalation.created_at.desc())
    query = query.offset(skip).limit(limit)

    result = await db.execute(query)
    escalations = result.scalars().all()

    # Enrich with assigned_to_name
    for esc in escalations:
        if esc.assigned_to_id:
            user_result = await db.execute(
                select(User).where(User.id == esc.assigned_to_id)
            )
            user = user_result.scalar_one_or_none()
            if user:
                esc.assigned_to_name = f"{user.first_name or ''} {user.last_name or ''}".strip()

    return EscalationListResponse(
        items=escalations,
        total=total,
        skip=skip,
        limit=limit
    )


@router.get("/{escalation_id}", response_model=EscalationDetailResponse)
@require_module("crm_service")
async def get_escalation(
    escalation_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get escalation details with history and comments."""
    result = await db.execute(
        select(Escalation)
        .options(
            selectinload(Escalation.history),
            selectinload(Escalation.comments)
        )
        .where(Escalation.id == escalation_id)
    )
    escalation = result.scalar_one_or_none()
    if not escalation:
        raise HTTPException(status_code=404, detail="Escalation not found")

    # Enrich assigned_to_name
    if escalation.assigned_to_id:
        user_result = await db.execute(
            select(User).where(User.id == escalation.assigned_to_id)
        )
        user = user_result.scalar_one_or_none()
        if user:
            escalation.assigned_to_name = f"{user.first_name or ''} {user.last_name or ''}".strip()

    # Enrich history with changed_by_name
    for hist in escalation.history:
        user_result = await db.execute(
            select(User).where(User.id == hist.changed_by_id)
        )
        user = user_result.scalar_one_or_none()
        if user:
            hist.changed_by_name = f"{user.first_name or ''} {user.last_name or ''}".strip()

    # Enrich comments with created_by_name
    for comment in escalation.comments:
        user_result = await db.execute(
            select(User).where(User.id == comment.created_by_id)
        )
        user = user_result.scalar_one_or_none()
        if user:
            comment.created_by_name = f"{user.first_name or ''} {user.last_name or ''}".strip()

    return escalation


@router.put("/{escalation_id}", response_model=EscalationResponse)
@require_module("crm_service")
async def update_escalation(
    escalation_id: UUID,
    data: EscalationUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update escalation details."""
    result = await db.execute(
        select(Escalation).where(Escalation.id == escalation_id)
    )
    escalation = result.scalar_one_or_none()
    if not escalation:
        raise HTTPException(status_code=404, detail="Escalation not found")

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(escalation, field, value)

    escalation.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(escalation)
    return escalation


# ==================== Escalation Workflow Endpoints ====================

@router.post("/{escalation_id}/assign", response_model=EscalationResponse)
@require_module("crm_service")
async def assign_escalation(
    escalation_id: UUID,
    data: EscalationAssignRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Assign escalation to a user."""
    result = await db.execute(
        select(Escalation).where(Escalation.id == escalation_id)
    )
    escalation = result.scalar_one_or_none()
    if not escalation:
        raise HTTPException(status_code=404, detail="Escalation not found")

    if escalation.status in [EscalationStatus.RESOLVED, EscalationStatus.CLOSED]:
        raise HTTPException(status_code=400, detail="Cannot assign resolved/closed escalation")

    old_status = escalation.status
    escalation.assigned_to_id = data.assigned_to_id
    escalation.assigned_at = datetime.now(timezone.utc)

    if escalation.status == EscalationStatus.NEW:
        escalation.status = EscalationStatus.ASSIGNED.value

    escalation.updated_at = datetime.now(timezone.utc)

    # Create history entry
    history = EscalationHistory(
        escalation_id=escalation.id,
        from_level=escalation.current_level,
        to_level=escalation.current_level,
        from_status=old_status,
        to_status=escalation.status,
        action="ASSIGNED",
        notes=data.notes or f"Assigned to user {data.assigned_to_id}",
        changed_by_id=current_user.id
    )
    db.add(history)

    await db.commit()
    await db.refresh(escalation)
    return escalation


@router.post("/{escalation_id}/acknowledge", response_model=EscalationResponse)
@require_module("crm_service")
async def acknowledge_escalation(
    escalation_id: UUID,
    data: EscalationAcknowledgeRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Acknowledge an escalation."""
    result = await db.execute(
        select(Escalation).where(Escalation.id == escalation_id)
    )
    escalation = result.scalar_one_or_none()
    if not escalation:
        raise HTTPException(status_code=404, detail="Escalation not found")

    if escalation.acknowledged_at:
        raise HTTPException(status_code=400, detail="Escalation already acknowledged")

    old_status = escalation.status
    escalation.acknowledged_at = datetime.now(timezone.utc)
    escalation.first_response_at = escalation.first_response_at or datetime.now(timezone.utc)
    escalation.status = EscalationStatus.ACKNOWLEDGED.value
    escalation.updated_at = datetime.now(timezone.utc)

    # Check response SLA
    if escalation.response_due_at and datetime.now(timezone.utc) > escalation.response_due_at:
        escalation.is_response_sla_breached = True

    # Create history entry
    history = EscalationHistory(
        escalation_id=escalation.id,
        from_level=escalation.current_level,
        to_level=escalation.current_level,
        from_status=old_status,
        to_status=EscalationStatus.ACKNOWLEDGED,
        action="ACKNOWLEDGED",
        notes=data.notes or "Escalation acknowledged",
        changed_by_id=current_user.id
    )
    db.add(history)

    await db.commit()
    await db.refresh(escalation)
    return escalation


@router.post("/{escalation_id}/escalate", response_model=EscalationResponse)
@require_module("crm_service")
async def escalate_to_next_level(
    escalation_id: UUID,
    data: EscalationEscalateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Escalate to the next level."""
    result = await db.execute(
        select(Escalation).where(Escalation.id == escalation_id)
    )
    escalation = result.scalar_one_or_none()
    if not escalation:
        raise HTTPException(status_code=404, detail="Escalation not found")

    if escalation.status in [EscalationStatus.RESOLVED, EscalationStatus.CLOSED]:
        raise HTTPException(status_code=400, detail="Cannot escalate resolved/closed escalation")

    # Determine next level
    level_order = [
        EscalationLevel.L1, EscalationLevel.L2, EscalationLevel.L3,
        EscalationLevel.L4, EscalationLevel.L5, EscalationLevel.CRITICAL
    ]
    current_idx = level_order.index(escalation.current_level)

    if current_idx >= len(level_order) - 1:
        raise HTTPException(status_code=400, detail="Already at highest escalation level")

    old_level = escalation.current_level
    old_status = escalation.status

    escalation.current_level = level_order[current_idx + 1]
    escalation.status = EscalationStatus.ESCALATED.value

    if data.assign_to_id:
        escalation.assigned_to_id = data.assign_to_id
        escalation.assigned_at = datetime.now(timezone.utc)

    escalation.updated_at = datetime.now(timezone.utc)

    # Create history entry
    history = EscalationHistory(
        escalation_id=escalation.id,
        from_level=old_level,
        to_level=escalation.current_level,
        from_status=old_status,
        to_status=EscalationStatus.ESCALATED,
        action="ESCALATED",
        reason=data.reason,
        notes=data.notes,
        changed_by_id=current_user.id
    )
    db.add(history)

    await db.commit()
    await db.refresh(escalation)
    return escalation


@router.post("/{escalation_id}/de-escalate", response_model=EscalationResponse)
@require_module("crm_service")
async def de_escalate(
    escalation_id: UUID,
    data: EscalationDeEscalateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """De-escalate to a lower level."""
    result = await db.execute(
        select(Escalation).where(Escalation.id == escalation_id)
    )
    escalation = result.scalar_one_or_none()
    if not escalation:
        raise HTTPException(status_code=404, detail="Escalation not found")

    if escalation.current_level == EscalationLevel.L1:
        raise HTTPException(status_code=400, detail="Already at lowest level")

    level_order = [
        EscalationLevel.L1, EscalationLevel.L2, EscalationLevel.L3,
        EscalationLevel.L4, EscalationLevel.L5, EscalationLevel.CRITICAL
    ]
    current_idx = level_order.index(escalation.current_level)

    old_level = escalation.current_level
    old_status = escalation.status

    escalation.current_level = level_order[current_idx - 1]
    escalation.status = EscalationStatus.IN_PROGRESS.value
    escalation.updated_at = datetime.now(timezone.utc)

    # Create history entry
    history = EscalationHistory(
        escalation_id=escalation.id,
        from_level=old_level,
        to_level=escalation.current_level,
        from_status=old_status,
        to_status=EscalationStatus.IN_PROGRESS,
        action="DE_ESCALATED",
        reason=data.reason,
        notes=data.notes,
        changed_by_id=current_user.id
    )
    db.add(history)

    await db.commit()
    await db.refresh(escalation)
    return escalation


@router.post("/{escalation_id}/resolve", response_model=EscalationResponse)
@require_module("crm_service")
async def resolve_escalation(
    escalation_id: UUID,
    data: EscalationResolveRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Resolve an escalation."""
    result = await db.execute(
        select(Escalation).where(Escalation.id == escalation_id)
    )
    escalation = result.scalar_one_or_none()
    if not escalation:
        raise HTTPException(status_code=404, detail="Escalation not found")

    if escalation.status == EscalationStatus.RESOLVED:
        raise HTTPException(status_code=400, detail="Escalation already resolved")

    old_status = escalation.status
    now = datetime.now(timezone.utc)

    escalation.status = EscalationStatus.RESOLVED.value
    escalation.resolved_at = now
    escalation.resolution_notes = data.resolution_notes
    escalation.resolved_by_id = current_user.id
    escalation.updated_at = now

    # Check resolution SLA
    if escalation.resolution_due_at and now > escalation.resolution_due_at:
        escalation.is_resolution_sla_breached = True

    # Create history entry
    history = EscalationHistory(
        escalation_id=escalation.id,
        from_level=escalation.current_level,
        to_level=escalation.current_level,
        from_status=old_status,
        to_status=EscalationStatus.RESOLVED,
        action="RESOLVED",
        notes=data.resolution_notes,
        changed_by_id=current_user.id
    )
    db.add(history)

    await db.commit()
    await db.refresh(escalation)
    return escalation


@router.post("/{escalation_id}/reopen", response_model=EscalationResponse)
@require_module("crm_service")
async def reopen_escalation(
    escalation_id: UUID,
    data: EscalationReopenRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Reopen a resolved/closed escalation."""
    result = await db.execute(
        select(Escalation).where(Escalation.id == escalation_id)
    )
    escalation = result.scalar_one_or_none()
    if not escalation:
        raise HTTPException(status_code=404, detail="Escalation not found")

    if escalation.status not in [EscalationStatus.RESOLVED, EscalationStatus.CLOSED]:
        raise HTTPException(status_code=400, detail="Can only reopen resolved/closed escalations")

    old_status = escalation.status

    escalation.status = EscalationStatus.REOPENED.value
    escalation.reopen_count = (escalation.reopen_count or 0) + 1
    escalation.last_reopened_at = datetime.now(timezone.utc)
    escalation.resolved_at = None
    escalation.resolution_notes = None
    escalation.updated_at = datetime.now(timezone.utc)

    # Create history entry
    history = EscalationHistory(
        escalation_id=escalation.id,
        from_level=escalation.current_level,
        to_level=escalation.current_level,
        from_status=old_status,
        to_status=EscalationStatus.REOPENED,
        action="REOPENED",
        reason=data.reason,
        changed_by_id=current_user.id
    )
    db.add(history)

    await db.commit()
    await db.refresh(escalation)
    return escalation


@router.post("/{escalation_id}/close", response_model=EscalationResponse)
@require_module("crm_service")
async def close_escalation(
    escalation_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Close a resolved escalation."""
    result = await db.execute(
        select(Escalation).where(Escalation.id == escalation_id)
    )
    escalation = result.scalar_one_or_none()
    if not escalation:
        raise HTTPException(status_code=404, detail="Escalation not found")

    if escalation.status != EscalationStatus.RESOLVED:
        raise HTTPException(status_code=400, detail="Can only close resolved escalations")

    old_status = escalation.status

    escalation.status = EscalationStatus.CLOSED.value
    escalation.closed_at = datetime.now(timezone.utc)
    escalation.updated_at = datetime.now(timezone.utc)

    # Create history entry
    history = EscalationHistory(
        escalation_id=escalation.id,
        from_level=escalation.current_level,
        to_level=escalation.current_level,
        from_status=old_status,
        to_status=EscalationStatus.CLOSED,
        action="CLOSED",
        notes="Escalation closed",
        changed_by_id=current_user.id
    )
    db.add(history)

    await db.commit()
    await db.refresh(escalation)
    return escalation


@router.post("/{escalation_id}/feedback", response_model=EscalationResponse)
@require_module("crm_service")
async def submit_feedback(
    escalation_id: UUID,
    data: EscalationFeedbackRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Submit customer feedback on resolution."""
    result = await db.execute(
        select(Escalation).where(Escalation.id == escalation_id)
    )
    escalation = result.scalar_one_or_none()
    if not escalation:
        raise HTTPException(status_code=404, detail="Escalation not found")

    escalation.customer_satisfied = data.satisfied
    escalation.satisfaction_rating = data.rating
    escalation.customer_feedback = data.feedback
    escalation.updated_at = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(escalation)
    return escalation


# ==================== Comment Endpoints ====================

@router.post("/{escalation_id}/comments", response_model=EscalationCommentResponse, status_code=status.HTTP_201_CREATED)
@require_module("crm_service")
async def add_comment(
    escalation_id: UUID,
    data: EscalationCommentCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Add a comment to an escalation."""
    result = await db.execute(
        select(Escalation).where(Escalation.id == escalation_id)
    )
    escalation = result.scalar_one_or_none()
    if not escalation:
        raise HTTPException(status_code=404, detail="Escalation not found")

    comment = EscalationComment(
        escalation_id=escalation_id,
        comment=data.comment,
        is_internal=data.is_internal,
        attachments=data.attachments,
        created_by_id=current_user.id
    )
    db.add(comment)
    await db.commit()
    await db.refresh(comment)

    comment.created_by_name = f"{current_user.first_name or ''} {current_user.last_name or ''}".strip()
    return comment


@router.get("/{escalation_id}/comments", response_model=List[EscalationCommentResponse])
@require_module("crm_service")
async def list_comments(
    escalation_id: UUID,
    include_internal: bool = True,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List comments for an escalation."""
    query = select(EscalationComment).where(EscalationComment.escalation_id == escalation_id)

    if not include_internal:
        query = query.where(EscalationComment.is_internal == False)

    query = query.order_by(EscalationComment.created_at.desc())

    result = await db.execute(query)
    comments = result.scalars().all()

    # Enrich with created_by_name
    for comment in comments:
        user_result = await db.execute(
            select(User).where(User.id == comment.created_by_id)
        )
        user = user_result.scalar_one_or_none()
        if user:
            comment.created_by_name = f"{user.first_name or ''} {user.last_name or ''}".strip()

    return comments


# ==================== History Endpoint ====================

@router.get("/{escalation_id}/history", response_model=List[EscalationHistoryResponse])
@require_module("crm_service")
async def get_escalation_history(
    escalation_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get escalation history."""
    result = await db.execute(
        select(EscalationHistory)
        .where(EscalationHistory.escalation_id == escalation_id)
        .order_by(EscalationHistory.changed_at.desc())
    )
    history = result.scalars().all()

    # Enrich with changed_by_name
    for hist in history:
        user_result = await db.execute(
            select(User).where(User.id == hist.changed_by_id)
        )
        user = user_result.scalar_one_or_none()
        if user:
            hist.changed_by_name = f"{user.first_name or ''} {user.last_name or ''}".strip()

    return history


# ==================== SLA Configuration Endpoints ====================

@router.post("/sla-config", response_model=SLAConfigurationResponse, status_code=status.HTTP_201_CREATED)
@require_module("crm_service")
async def create_sla_configuration(
    data: SLAConfigurationCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create SLA configuration."""
    sla_config = SLAConfiguration(**data.model_dump())
    db.add(sla_config)
    await db.commit()
    await db.refresh(sla_config)
    return sla_config


@router.get("/sla-config", response_model=List[SLAConfigurationResponse])
@require_module("crm_service")
async def list_sla_configurations(
    source_type: Optional[EscalationSource] = None,
    priority: Optional[EscalationPriority] = None,
    is_active: Optional[bool] = True,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List SLA configurations."""
    query = select(SLAConfiguration)

    if source_type:
        query = query.where(SLAConfiguration.source_type == source_type)
    if priority:
        query = query.where(SLAConfiguration.priority == priority)
    if is_active is not None:
        query = query.where(SLAConfiguration.is_active == is_active)

    result = await db.execute(query.order_by(SLAConfiguration.created_at.desc()))
    return result.scalars().all()


# ==================== Dashboard & Reports ====================

@router.get("/stats/dashboard", response_model=EscalationDashboardResponse)
@require_module("crm_service")
async def get_escalation_dashboard(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get escalation dashboard metrics."""
    today = date.today()
    today_start = datetime.combine(today, datetime.min.time())
    today_end = datetime.combine(today, datetime.max.time())

    # Total escalations
    total_result = await db.execute(select(func.count(Escalation.id)))
    total_escalations = total_result.scalar() or 0

    # Open escalations (not resolved/closed)
    open_result = await db.execute(
        select(func.count(Escalation.id)).where(
            Escalation.status.notin_([EscalationStatus.RESOLVED, EscalationStatus.CLOSED])
        )
    )
    open_escalations = open_result.scalar() or 0

    # New today
    new_today_result = await db.execute(
        select(func.count(Escalation.id)).where(
            and_(
                Escalation.created_at >= today_start,
                Escalation.created_at <= today_end
            )
        )
    )
    new_today = new_today_result.scalar() or 0

    # Resolved today
    resolved_today_result = await db.execute(
        select(func.count(Escalation.id)).where(
            and_(
                Escalation.resolved_at >= today_start,
                Escalation.resolved_at <= today_end
            )
        )
    )
    resolved_today = resolved_today_result.scalar() or 0

    # By status
    status_result = await db.execute(
        select(Escalation.status, func.count(Escalation.id))
        .group_by(Escalation.status)
    )
    by_status = {str(row[0].value): row[1] for row in status_result.fetchall()}

    # By level
    level_result = await db.execute(
        select(Escalation.current_level, func.count(Escalation.id))
        .group_by(Escalation.current_level)
    )
    by_level = {str(row[0].value): row[1] for row in level_result.fetchall()}

    # By priority
    priority_result = await db.execute(
        select(Escalation.priority, func.count(Escalation.id))
        .group_by(Escalation.priority)
    )
    by_priority = {str(row[0].value): row[1] for row in priority_result.fetchall()}

    # SLA breaches
    response_breach_result = await db.execute(
        select(func.count(Escalation.id)).where(Escalation.is_response_sla_breached == True)
    )
    sla_breached_response = response_breach_result.scalar() or 0

    resolution_breach_result = await db.execute(
        select(func.count(Escalation.id)).where(Escalation.is_resolution_sla_breached == True)
    )
    sla_breached_resolution = resolution_breach_result.scalar() or 0

    # SLA compliance rate
    resolved_result = await db.execute(
        select(func.count(Escalation.id)).where(
            Escalation.status.in_([EscalationStatus.RESOLVED, EscalationStatus.CLOSED])
        )
    )
    total_resolved = resolved_result.scalar() or 0

    sla_compliance_rate = Decimal("0")
    if total_resolved > 0:
        compliant = total_resolved - sla_breached_resolution
        sla_compliance_rate = Decimal(str(round(compliant / total_resolved * 100, 2)))

    # Pending acknowledgment
    pending_ack_result = await db.execute(
        select(func.count(Escalation.id)).where(
            and_(
                Escalation.acknowledged_at == None,
                Escalation.status.notin_([EscalationStatus.RESOLVED, EscalationStatus.CLOSED])
            )
        )
    )
    pending_acknowledgment = pending_ack_result.scalar() or 0

    # Overdue response
    now = datetime.now(timezone.utc)
    overdue_response_result = await db.execute(
        select(func.count(Escalation.id)).where(
            and_(
                Escalation.first_response_at == None,
                Escalation.response_due_at < now,
                Escalation.status.notin_([EscalationStatus.RESOLVED, EscalationStatus.CLOSED])
            )
        )
    )
    overdue_response = overdue_response_result.scalar() or 0

    # Overdue resolution
    overdue_resolution_result = await db.execute(
        select(func.count(Escalation.id)).where(
            and_(
                Escalation.resolved_at == None,
                Escalation.resolution_due_at < now,
                Escalation.status.notin_([EscalationStatus.RESOLVED, EscalationStatus.CLOSED])
            )
        )
    )
    overdue_resolution = overdue_resolution_result.scalar() or 0

    # By source
    source_result = await db.execute(
        select(Escalation.source_type, func.count(Escalation.id))
        .group_by(Escalation.source_type)
    )
    by_source = {str(row[0].value): row[1] for row in source_result.fetchall()}

    return EscalationDashboardResponse(
        date=today,
        total_escalations=total_escalations,
        open_escalations=open_escalations,
        new_today=new_today,
        resolved_today=resolved_today,
        by_status=by_status,
        by_level=by_level,
        by_priority=by_priority,
        sla_breached_response=sla_breached_response,
        sla_breached_resolution=sla_breached_resolution,
        sla_compliance_rate=sla_compliance_rate,
        pending_acknowledgment=pending_acknowledgment,
        overdue_response=overdue_response,
        overdue_resolution=overdue_resolution,
        by_source=by_source
    )


@router.get("/stats/aging", response_model=EscalationAgingReportResponse)
@require_module("crm_service")
async def get_aging_report(
    start_date: date = Query(...),
    end_date: date = Query(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get escalation aging report."""
    start_datetime = datetime.combine(start_date, datetime.min.time())
    end_datetime = datetime.combine(end_date, datetime.max.time())
    now = datetime.now(timezone.utc)

    # Get open escalations in date range
    result = await db.execute(
        select(Escalation).where(
            and_(
                Escalation.created_at >= start_datetime,
                Escalation.created_at <= end_datetime,
                Escalation.status.notin_([EscalationStatus.RESOLVED, EscalationStatus.CLOSED])
            )
        )
    )
    escalations = result.scalars().all()

    # Calculate aging buckets
    buckets = {
        "0-24h": 0,
        "24-48h": 0,
        "48-72h": 0,
        "72h+": 0
    }

    for esc in escalations:
        age_hours = (now - esc.created_at).total_seconds() / 3600
        if age_hours <= 24:
            buckets["0-24h"] += 1
        elif age_hours <= 48:
            buckets["24-48h"] += 1
        elif age_hours <= 72:
            buckets["48-72h"] += 1
        else:
            buckets["72h+"] += 1

    total = len(escalations)
    aging_buckets = []
    for bucket, count in buckets.items():
        aging_buckets.append({
            "bucket": bucket,
            "count": count,
            "percentage": round(count / total * 100, 2) if total > 0 else 0
        })

    # By level
    level_counts = {}
    for esc in escalations:
        level = str(esc.current_level)
        level_counts[level] = level_counts.get(level, 0) + 1

    by_level = [{"level": k, "count": v} for k, v in level_counts.items()]

    # By priority
    priority_counts = {}
    for esc in escalations:
        priority = str(esc.priority)
        priority_counts[priority] = priority_counts.get(priority, 0) + 1

    by_priority = [{"priority": k, "count": v} for k, v in priority_counts.items()]

    return EscalationAgingReportResponse(
        start_date=start_date,
        end_date=end_date,
        aging_buckets=aging_buckets,
        by_level=by_level,
        by_priority=by_priority
    )


@router.get("/stats/sla-compliance", response_model=SLAComplianceReportResponse)
@require_module("crm_service")
async def get_sla_compliance_report(
    start_date: date = Query(...),
    end_date: date = Query(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get SLA compliance report."""
    start_datetime = datetime.combine(start_date, datetime.min.time())
    end_datetime = datetime.combine(end_date, datetime.max.time())

    # Get resolved escalations in date range
    result = await db.execute(
        select(Escalation).where(
            and_(
                Escalation.created_at >= start_datetime,
                Escalation.created_at <= end_datetime,
                Escalation.status.in_([EscalationStatus.RESOLVED, EscalationStatus.CLOSED])
            )
        )
    )
    escalations = result.scalars().all()

    total = len(escalations)
    response_met = sum(1 for e in escalations if not e.is_response_sla_breached)
    response_breached = total - response_met
    resolution_met = sum(1 for e in escalations if not e.is_resolution_sla_breached)
    resolution_breached = total - resolution_met

    response_compliance = Decimal(str(round(response_met / total * 100, 2))) if total > 0 else Decimal("0")
    resolution_compliance = Decimal(str(round(resolution_met / total * 100, 2))) if total > 0 else Decimal("0")
    overall_compliance = Decimal(str(round((response_met + resolution_met) / (total * 2) * 100, 2))) if total > 0 else Decimal("0")

    # By source
    source_data = {}
    for esc in escalations:
        source = str(esc.source_type)
        if source not in source_data:
            source_data[source] = {"total": 0, "response_met": 0, "resolution_met": 0}
        source_data[source]["total"] += 1
        if not esc.is_response_sla_breached:
            source_data[source]["response_met"] += 1
        if not esc.is_resolution_sla_breached:
            source_data[source]["resolution_met"] += 1

    by_source = [
        {
            "source": k,
            "total": v["total"],
            "response_compliance": round(v["response_met"] / v["total"] * 100, 2) if v["total"] > 0 else 0,
            "resolution_compliance": round(v["resolution_met"] / v["total"] * 100, 2) if v["total"] > 0 else 0
        }
        for k, v in source_data.items()
    ]

    # By priority
    priority_data = {}
    for esc in escalations:
        priority = str(esc.priority)
        if priority not in priority_data:
            priority_data[priority] = {"total": 0, "response_met": 0, "resolution_met": 0}
        priority_data[priority]["total"] += 1
        if not esc.is_response_sla_breached:
            priority_data[priority]["response_met"] += 1
        if not esc.is_resolution_sla_breached:
            priority_data[priority]["resolution_met"] += 1

    by_priority = [
        {
            "priority": k,
            "total": v["total"],
            "response_compliance": round(v["response_met"] / v["total"] * 100, 2) if v["total"] > 0 else 0,
            "resolution_compliance": round(v["resolution_met"] / v["total"] * 100, 2) if v["total"] > 0 else 0
        }
        for k, v in priority_data.items()
    ]

    return SLAComplianceReportResponse(
        start_date=start_date,
        end_date=end_date,
        total_escalations=total,
        response_sla_met=response_met,
        response_sla_breached=response_breached,
        resolution_sla_met=resolution_met,
        resolution_sla_breached=resolution_breached,
        response_compliance_rate=response_compliance,
        resolution_compliance_rate=resolution_compliance,
        overall_compliance_rate=overall_compliance,
        by_source=by_source,
        by_priority=by_priority,
        by_agent=[]  # Would need agent tracking for this
    )
