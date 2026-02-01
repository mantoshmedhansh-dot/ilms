"""API endpoints for Call Center CRM module."""
from typing import Optional, List
from uuid import UUID
from datetime import datetime, date, timedelta, timezone
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy import select, func, and_, or_, case
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.call_center import (
    Call, CallDisposition, CallbackSchedule, CallQAReview,
    CallType, CallCategory, CallStatus, CallOutcome,
    CustomerSentiment, CallPriority, CallbackStatus, QAStatus
)
from app.models.user import User
from app.models.customer import Customer
from app.models.service_request import ServiceRequest
from app.schemas.call_center import (
    # Disposition
    CallDispositionCreate, CallDispositionUpdate, CallDispositionResponse,
    CallDispositionListResponse,
    # Call
    CallCreate, CallUpdate, CallCompleteRequest, CallTransferRequest,
    CallResponse, CallDetailResponse, CallListResponse,
    # Callback
    CallbackCreate, CallbackUpdate, CallbackCompleteRequest,
    CallbackRescheduleRequest, CallbackResponse, CallbackListResponse,
    # QA Review
    CallQAReviewCreate, CallQAReviewUpdate, CallQAReviewResponse,
    AgentAcknowledgeRequest, QADisputeRequest,
    # Dashboard & Reports
    AgentDashboardResponse, CallCenterDashboardResponse,
    FCRReportRequest, FCRReportResponse,
    AHTReportResponse, CallVolumeReportResponse
)
from app.api.deps import DB, CurrentUser, get_current_user
from app.core.module_decorators import require_module

router = APIRouter()


# ==================== Helper Functions ====================

async def generate_call_id(db: AsyncSession) -> str:
    """Generate unique call ID."""
    today = datetime.now(timezone.utc)
    prefix = f"CALL-{today.strftime('%Y%m%d')}"

    # Get count for today
    result = await db.execute(
        select(func.count(Call.id)).where(
            Call.call_id.like(f"{prefix}%")
        )
    )
    count = result.scalar() or 0
    return f"{prefix}-{str(count + 1).zfill(4)}"


def _get_user_name(user: Optional[User]) -> Optional[str]:
    """Get formatted user name."""
    if not user:
        return None
    return f"{user.first_name} {user.last_name or ''}".strip()


# ==================== Call Disposition Endpoints ====================

@router.post("/dispositions", response_model=CallDispositionResponse, status_code=status.HTTP_201_CREATED)
@require_module("crm_service")
async def create_disposition(
    disposition_in: CallDispositionCreate,
    db: DB,
    current_user: User = Depends(get_current_user),
):
    """Create a new call disposition code."""
    # Check if code exists
    existing = await db.execute(
        select(CallDisposition).where(CallDisposition.code == disposition_in.code)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=400,
            detail=f"Disposition code '{disposition_in.code}' already exists"
        )

    disposition = CallDisposition(**disposition_in.model_dump())
    db.add(disposition)
    await db.commit()
    await db.refresh(disposition)

    return disposition


@router.get("/dispositions", response_model=CallDispositionListResponse)
@require_module("crm_service")
async def list_dispositions(
    db: DB,
    category: Optional[CallCategory] = None,
    is_active: Optional[bool] = True,
    current_user: User = Depends(get_current_user),
):
    """List all call dispositions."""
    query = select(CallDisposition).order_by(CallDisposition.sort_order, CallDisposition.name)

    if category:
        query = query.where(CallDisposition.category == category)
    if is_active is not None:
        query = query.where(CallDisposition.is_active == is_active)

    result = await db.execute(query)
    dispositions = result.scalars().all()

    return CallDispositionListResponse(
        items=[CallDispositionResponse.model_validate(d) for d in dispositions],
        total=len(dispositions)
    )


@router.put("/dispositions/{disposition_id}", response_model=CallDispositionResponse)
@require_module("crm_service")
async def update_disposition(
    disposition_id: UUID,
    disposition_in: CallDispositionUpdate,
    db: DB,
    current_user: User = Depends(get_current_user),
):
    """Update a call disposition."""
    result = await db.execute(
        select(CallDisposition).where(CallDisposition.id == disposition_id)
    )
    disposition = result.scalar_one_or_none()

    if not disposition:
        raise HTTPException(status_code=404, detail="Disposition not found")

    update_data = disposition_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(disposition, field, value)

    await db.commit()
    await db.refresh(disposition)

    return disposition


# ==================== Call Endpoints ====================

@router.post("/calls", response_model=CallResponse, status_code=status.HTTP_201_CREATED)
@require_module("crm_service")
async def log_call(
    call_in: CallCreate,
    db: DB,
    current_user: User = Depends(get_current_user),
):
    """Log a new call (start a call record)."""
    call_id = await generate_call_id(db)

    # Try to find existing customer by phone
    customer = None
    if call_in.customer_id:
        result = await db.execute(
            select(Customer).where(Customer.id == call_in.customer_id)
        )
        customer = result.scalar_one_or_none()
    elif call_in.customer_phone:
        result = await db.execute(
            select(Customer).where(Customer.phone == call_in.customer_phone)
        )
        customer = result.scalar_one_or_none()

    call = Call(
        call_id=call_id,
        call_type=call_in.call_type,
        category=call_in.category,
        sub_category=call_in.sub_category,
        customer_id=customer.id if customer else call_in.customer_id,
        customer_name=call_in.customer_name or (customer.name if customer else None),
        customer_phone=call_in.customer_phone,
        customer_email=call_in.customer_email or (customer.email if customer else None),
        customer_address=call_in.customer_address,
        agent_id=current_user.id,
        call_start_time=call_in.call_start_time or datetime.now(timezone.utc),
        priority=call_in.priority,
        call_reason=call_in.call_reason,
        product_id=call_in.product_id,
        serial_number=call_in.serial_number,
        linked_ticket_id=call_in.linked_ticket_id,
        linked_order_id=call_in.linked_order_id,
        campaign_id=call_in.campaign_id,
        status=CallStatus.IN_PROGRESS,
    )

    db.add(call)
    await db.commit()
    await db.refresh(call)

    return CallResponse(
        **{k: v for k, v in call.__dict__.items() if not k.startswith('_')},
        agent_name=_get_user_name(current_user)
    )


@router.get("/calls", response_model=CallListResponse)
@require_module("crm_service")
async def list_calls(
    db: DB,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    call_type: Optional[CallType] = None,
    category: Optional[CallCategory] = None,
    status: Optional[CallStatus] = None,
    outcome: Optional[CallOutcome] = None,
    agent_id: Optional[UUID] = None,
    customer_phone: Optional[str] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    search: Optional[str] = None,
    current_user: User = Depends(get_current_user),
):
    """List calls with filters."""
    query = (
        select(Call)
        .options(selectinload(Call.agent))
        .order_by(Call.call_start_time.desc())
    )

    # Filters
    conditions = []
    if call_type:
        conditions.append(Call.call_type == call_type)
    if category:
        conditions.append(Call.category == category)
    if status:
        conditions.append(Call.status == status)
    if outcome:
        conditions.append(Call.outcome == outcome)
    if agent_id:
        conditions.append(Call.agent_id == agent_id)
    if customer_phone:
        conditions.append(Call.customer_phone.contains(customer_phone))
    if start_date:
        conditions.append(Call.call_start_time >= datetime.combine(start_date, datetime.min.time()))
    if end_date:
        conditions.append(Call.call_start_time <= datetime.combine(end_date, datetime.max.time()))
    if search:
        conditions.append(or_(
            Call.call_id.ilike(f"%{search}%"),
            Call.customer_name.ilike(f"%{search}%"),
            Call.customer_phone.ilike(f"%{search}%"),
            Call.call_notes.ilike(f"%{search}%")
        ))

    if conditions:
        query = query.where(and_(*conditions))

    # Count
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # Paginate
    query = query.offset(skip).limit(limit)
    result = await db.execute(query)
    calls = result.scalars().all()

    items = []
    for call in calls:
        items.append(CallResponse(
            **{k: v for k, v in call.__dict__.items() if not k.startswith('_')},
            agent_name=_get_user_name(call.agent)
        ))

    return CallListResponse(
        items=items,
        total=total,
        skip=skip,
        limit=limit
    )


@router.get("/calls/{call_id}", response_model=CallDetailResponse)
@require_module("crm_service")
async def get_call(
    call_id: UUID,
    db: DB,
    current_user: User = Depends(get_current_user),
):
    """Get call details."""
    result = await db.execute(
        select(Call)
        .options(
            selectinload(Call.agent),
            selectinload(Call.customer),
            selectinload(Call.disposition),
            selectinload(Call.linked_ticket),
            selectinload(Call.callbacks),
            selectinload(Call.qa_reviews)
        )
        .where(Call.id == call_id)
    )
    call = result.scalar_one_or_none()

    if not call:
        raise HTTPException(status_code=404, detail="Call not found")

    return CallDetailResponse(
        **{k: v for k, v in call.__dict__.items() if not k.startswith('_')},
        agent_name=_get_user_name(call.agent),
        disposition_name=call.disposition.name if call.disposition else None,
        customer={"id": call.customer.id, "name": call.customer.name} if call.customer else None,
        agent={"id": call.agent.id, "name": _get_user_name(call.agent)} if call.agent else None,
        callbacks=[CallbackResponse.model_validate(cb) for cb in call.callbacks],
        qa_reviews=[CallQAReviewResponse.model_validate(qa) for qa in call.qa_reviews]
    )


@router.put("/calls/{call_id}", response_model=CallResponse)
@require_module("crm_service")
async def update_call(
    call_id: UUID,
    call_in: CallUpdate,
    db: DB,
    current_user: User = Depends(get_current_user),
):
    """Update call details during the call."""
    result = await db.execute(
        select(Call).options(selectinload(Call.agent)).where(Call.id == call_id)
    )
    call = result.scalar_one_or_none()

    if not call:
        raise HTTPException(status_code=404, detail="Call not found")

    if call.status == CallStatus.COMPLETED:
        raise HTTPException(status_code=400, detail="Cannot update completed call")

    update_data = call_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(call, field, value)

    await db.commit()
    await db.refresh(call)

    return CallResponse(
        **{k: v for k, v in call.__dict__.items() if not k.startswith('_')},
        agent_name=_get_user_name(call.agent)
    )


@router.post("/calls/{call_id}/complete", response_model=CallResponse)
@require_module("crm_service")
async def complete_call(
    call_id: UUID,
    request: CallCompleteRequest,
    db: DB,
    current_user: User = Depends(get_current_user),
):
    """Complete/end a call with disposition."""
    result = await db.execute(
        select(Call).options(selectinload(Call.agent)).where(Call.id == call_id)
    )
    call = result.scalar_one_or_none()

    if not call:
        raise HTTPException(status_code=404, detail="Call not found")

    if call.status == CallStatus.COMPLETED:
        raise HTTPException(status_code=400, detail="Call already completed")

    # Calculate duration
    end_time = datetime.now(timezone.utc)
    duration = int((end_time - call.call_start_time).total_seconds())

    # Update call
    call.call_end_time = end_time
    call.duration_seconds = duration
    call.talk_time_seconds = duration - call.hold_time_seconds
    call.status = CallStatus.COMPLETED.value
    call.outcome = request.outcome
    call.disposition_id = request.disposition_id
    call.call_notes = request.call_notes or call.call_notes
    call.resolution_notes = request.resolution_notes
    call.sentiment = request.sentiment
    call.is_resolved_first_call = request.is_resolved_first_call
    call.follow_up_required = request.follow_up_required
    call.consent_confirmed = request.consent_confirmed
    call.disclosure_read = request.disclosure_read

    # Auto-create ticket if requested
    if request.create_ticket and request.ticket_details:
        # This would integrate with service request creation
        pass

    # Auto-create callback if requested
    if request.create_callback and request.callback_datetime:
        callback = CallbackSchedule(
            call_id=call.id,
            customer_id=call.customer_id,
            customer_name=call.customer_name or "Unknown",
            customer_phone=call.customer_phone,
            assigned_agent_id=current_user.id,
            created_by_id=current_user.id,
            scheduled_date=request.callback_datetime.date(),
            scheduled_datetime=request.callback_datetime,
            reason=request.callback_reason or "Follow-up call",
            category=call.category,
            priority=call.priority,
        )
        db.add(callback)

    await db.commit()
    await db.refresh(call)

    return CallResponse(
        **{k: v for k, v in call.__dict__.items() if not k.startswith('_')},
        agent_name=_get_user_name(call.agent)
    )


@router.post("/calls/{call_id}/transfer", response_model=CallResponse)
@require_module("crm_service")
async def transfer_call(
    call_id: UUID,
    request: CallTransferRequest,
    db: DB,
    current_user: User = Depends(get_current_user),
):
    """Transfer a call to another agent."""
    result = await db.execute(
        select(Call).where(Call.id == call_id)
    )
    call = result.scalar_one_or_none()

    if not call:
        raise HTTPException(status_code=404, detail="Call not found")

    if call.status == CallStatus.COMPLETED:
        raise HTTPException(status_code=400, detail="Cannot transfer completed call")

    # Verify target agent exists
    agent_result = await db.execute(
        select(User).where(User.id == request.transfer_to_agent_id)
    )
    target_agent = agent_result.scalar_one_or_none()
    if not target_agent:
        raise HTTPException(status_code=404, detail="Target agent not found")

    # Update call
    call.transferred_from_id = call.agent_id
    call.transferred_to_id = request.transfer_to_agent_id
    call.agent_id = request.transfer_to_agent_id
    call.transfer_reason = request.transfer_reason
    call.status = CallStatus.TRANSFERRED.value

    if request.notes:
        call.internal_notes = (call.internal_notes or "") + f"\n[Transfer] {request.notes}"

    await db.commit()
    await db.refresh(call)

    return CallResponse(
        **{k: v for k, v in call.__dict__.items() if not k.startswith('_')},
        agent_name=_get_user_name(target_agent)
    )


# ==================== Callback Endpoints ====================

@router.post("/callbacks", response_model=CallbackResponse, status_code=status.HTTP_201_CREATED)
@require_module("crm_service")
async def create_callback(
    callback_in: CallbackCreate,
    db: DB,
    current_user: User = Depends(get_current_user),
):
    """Schedule a callback."""
    callback = CallbackSchedule(
        call_id=callback_in.call_id,
        customer_id=callback_in.customer_id,
        customer_name=callback_in.customer_name,
        customer_phone=callback_in.customer_phone,
        assigned_agent_id=callback_in.assigned_agent_id or current_user.id,
        created_by_id=current_user.id,
        scheduled_date=callback_in.scheduled_datetime.date(),
        scheduled_datetime=callback_in.scheduled_datetime,
        time_window_start=callback_in.time_window_start,
        time_window_end=callback_in.time_window_end,
        reason=callback_in.reason,
        category=callback_in.category,
        priority=callback_in.priority,
        notes=callback_in.notes,
        max_attempts=callback_in.max_attempts,
    )

    db.add(callback)
    await db.commit()
    await db.refresh(callback)

    return CallbackResponse.model_validate(callback)


@router.get("/callbacks", response_model=CallbackListResponse)
@require_module("crm_service")
async def list_callbacks(
    db: DB,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    status: Optional[CallbackStatus] = None,
    agent_id: Optional[UUID] = None,
    scheduled_date: Optional[date] = None,
    priority: Optional[CallPriority] = None,
    include_overdue: bool = False,
    current_user: User = Depends(get_current_user),
):
    """List scheduled callbacks."""
    query = (
        select(CallbackSchedule)
        .options(selectinload(CallbackSchedule.assigned_agent))
        .order_by(CallbackSchedule.scheduled_datetime)
    )

    conditions = []
    if status:
        conditions.append(CallbackSchedule.status == status)
    if agent_id:
        conditions.append(CallbackSchedule.assigned_agent_id == agent_id)
    if scheduled_date:
        conditions.append(CallbackSchedule.scheduled_date == scheduled_date)
    if priority:
        conditions.append(CallbackSchedule.priority == priority)

    if conditions:
        query = query.where(and_(*conditions))

    # Count totals
    count_result = await db.execute(select(func.count()).select_from(query.subquery()))
    total = count_result.scalar() or 0

    # Get summary counts
    now = datetime.now(timezone.utc)
    today = now.date()

    scheduled_count_result = await db.execute(
        select(func.count(CallbackSchedule.id)).where(
            CallbackSchedule.status == CallbackStatus.SCHEDULED
        )
    )
    scheduled_count = scheduled_count_result.scalar() or 0

    overdue_count_result = await db.execute(
        select(func.count(CallbackSchedule.id)).where(
            and_(
                CallbackSchedule.status == CallbackStatus.SCHEDULED,
                CallbackSchedule.scheduled_datetime < now
            )
        )
    )
    overdue_count = overdue_count_result.scalar() or 0

    completed_today_result = await db.execute(
        select(func.count(CallbackSchedule.id)).where(
            and_(
                CallbackSchedule.status == CallbackStatus.COMPLETED,
                func.date(CallbackSchedule.completed_at) == today
            )
        )
    )
    completed_today = completed_today_result.scalar() or 0

    # Paginate
    query = query.offset(skip).limit(limit)
    result = await db.execute(query)
    callbacks = result.scalars().all()

    items = []
    for cb in callbacks:
        items.append(CallbackResponse(
            **{k: v for k, v in cb.__dict__.items() if not k.startswith('_')},
            assigned_agent_name=_get_user_name(cb.assigned_agent)
        ))

    return CallbackListResponse(
        items=items,
        total=total,
        skip=skip,
        limit=limit,
        scheduled_count=scheduled_count,
        overdue_count=overdue_count,
        completed_today=completed_today
    )


@router.get("/callbacks/my", response_model=CallbackListResponse)
@require_module("crm_service")
async def get_my_callbacks(
    db: DB,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    status: Optional[CallbackStatus] = CallbackStatus.SCHEDULED,
    current_user: User = Depends(get_current_user),
):
    """Get current user's assigned callbacks."""
    query = (
        select(CallbackSchedule)
        .where(CallbackSchedule.assigned_agent_id == current_user.id)
        .order_by(CallbackSchedule.scheduled_datetime)
    )

    if status:
        query = query.where(CallbackSchedule.status == status)

    count_result = await db.execute(select(func.count()).select_from(query.subquery()))
    total = count_result.scalar() or 0

    query = query.offset(skip).limit(limit)
    result = await db.execute(query)
    callbacks = result.scalars().all()

    return CallbackListResponse(
        items=[CallbackResponse.model_validate(cb) for cb in callbacks],
        total=total,
        skip=skip,
        limit=limit
    )


@router.post("/callbacks/{callback_id}/complete", response_model=CallbackResponse)
@require_module("crm_service")
async def complete_callback(
    callback_id: UUID,
    request: CallbackCompleteRequest,
    db: DB,
    current_user: User = Depends(get_current_user),
):
    """Mark a callback as completed."""
    result = await db.execute(
        select(CallbackSchedule).where(CallbackSchedule.id == callback_id)
    )
    callback = result.scalar_one_or_none()

    if not callback:
        raise HTTPException(status_code=404, detail="Callback not found")

    if callback.status == CallbackStatus.COMPLETED:
        raise HTTPException(status_code=400, detail="Callback already completed")

    callback.status = CallbackStatus.COMPLETED.value
    callback.completed_at = datetime.now(timezone.utc)
    callback.completed_call_id = request.completed_call_id
    callback.completion_notes = request.completion_notes

    await db.commit()
    await db.refresh(callback)

    return CallbackResponse.model_validate(callback)


@router.post("/callbacks/{callback_id}/reschedule", response_model=CallbackResponse)
@require_module("crm_service")
async def reschedule_callback(
    callback_id: UUID,
    request: CallbackRescheduleRequest,
    db: DB,
    current_user: User = Depends(get_current_user),
):
    """Reschedule a callback."""
    result = await db.execute(
        select(CallbackSchedule).where(CallbackSchedule.id == callback_id)
    )
    callback = result.scalar_one_or_none()

    if not callback:
        raise HTTPException(status_code=404, detail="Callback not found")

    if callback.status == CallbackStatus.COMPLETED:
        raise HTTPException(status_code=400, detail="Cannot reschedule completed callback")

    # Update the callback
    callback.status = CallbackStatus.RESCHEDULED.value
    callback.scheduled_datetime = request.new_datetime
    callback.scheduled_date = request.new_datetime.date()
    callback.reschedule_count += 1
    callback.notes = (callback.notes or "") + f"\n[Rescheduled] {request.reason}"

    await db.commit()
    await db.refresh(callback)

    # Create new callback with link to old one
    new_callback = CallbackSchedule(
        call_id=callback.call_id,
        customer_id=callback.customer_id,
        customer_name=callback.customer_name,
        customer_phone=callback.customer_phone,
        assigned_agent_id=callback.assigned_agent_id,
        created_by_id=current_user.id,
        scheduled_date=request.new_datetime.date(),
        scheduled_datetime=request.new_datetime,
        reason=callback.reason,
        category=callback.category,
        priority=callback.priority,
        notes=request.notes,
        rescheduled_from_id=callback.id,
        reschedule_count=callback.reschedule_count,
    )

    db.add(new_callback)
    await db.commit()
    await db.refresh(new_callback)

    return CallbackResponse.model_validate(new_callback)


# ==================== QA Review Endpoints ====================

@router.post("/calls/{call_id}/qa-review", response_model=CallQAReviewResponse, status_code=status.HTTP_201_CREATED)
@require_module("crm_service")
async def create_qa_review(
    call_id: UUID,
    review_in: CallQAReviewCreate,
    db: DB,
    current_user: User = Depends(get_current_user),
):
    """Create a QA review for a call."""
    # Verify call exists
    call_result = await db.execute(select(Call).where(Call.id == call_id))
    call = call_result.scalar_one_or_none()
    if not call:
        raise HTTPException(status_code=404, detail="Call not found")

    if call.status != CallStatus.COMPLETED:
        raise HTTPException(status_code=400, detail="Can only review completed calls")

    # Calculate scores
    scores = [
        review_in.greeting_score,
        review_in.communication_score,
        review_in.product_knowledge_score,
        review_in.problem_solving_score,
        review_in.empathy_score,
        review_in.compliance_score,
        review_in.closing_score
    ]
    total_points = sum(scores)
    overall_score = Decimal(str(sum(scores) / len(scores)))

    review = CallQAReview(
        call_id=call_id,
        reviewer_id=current_user.id,
        greeting_score=review_in.greeting_score,
        communication_score=review_in.communication_score,
        product_knowledge_score=review_in.product_knowledge_score,
        problem_solving_score=review_in.problem_solving_score,
        empathy_score=review_in.empathy_score,
        compliance_score=review_in.compliance_score,
        closing_score=review_in.closing_score,
        overall_score=overall_score,
        total_points=total_points,
        strengths=review_in.strengths,
        areas_for_improvement=review_in.areas_for_improvement,
        reviewer_comments=review_in.reviewer_comments,
        status=QAStatus.REVIEWED,
    )

    db.add(review)
    await db.commit()
    await db.refresh(review)

    return CallQAReviewResponse(
        **{k: v for k, v in review.__dict__.items() if not k.startswith('_')},
        reviewer_name=_get_user_name(current_user)
    )


@router.post("/qa-reviews/{review_id}/acknowledge", response_model=CallQAReviewResponse)
@require_module("crm_service")
async def acknowledge_qa_review(
    review_id: UUID,
    request: AgentAcknowledgeRequest,
    db: DB,
    current_user: User = Depends(get_current_user),
):
    """Agent acknowledges QA review."""
    result = await db.execute(
        select(CallQAReview)
        .options(selectinload(CallQAReview.call))
        .where(CallQAReview.id == review_id)
    )
    review = result.scalar_one_or_none()

    if not review:
        raise HTTPException(status_code=404, detail="QA review not found")

    # Verify the current user is the agent of the call
    if review.call.agent_id != current_user.id:
        raise HTTPException(status_code=403, detail="Only the call agent can acknowledge")

    review.acknowledged_by_agent = True
    review.acknowledged_at = datetime.now(timezone.utc)
    review.agent_comments = request.comments

    await db.commit()
    await db.refresh(review)

    return CallQAReviewResponse.model_validate(review)


# ==================== Dashboard & Reports ====================

@router.get("/dashboard/agent", response_model=AgentDashboardResponse)
@require_module("crm_service")
async def get_agent_dashboard(
    db: DB,
    agent_id: Optional[UUID] = None,
    current_user: User = Depends(get_current_user),
):
    """Get agent dashboard metrics."""
    target_agent_id = agent_id or current_user.id
    today = datetime.now(timezone.utc).date()
    today_start = datetime.combine(today, datetime.min.time())
    today_end = datetime.combine(today, datetime.max.time())

    # Today's calls
    calls_result = await db.execute(
        select(Call).where(
            and_(
                Call.agent_id == target_agent_id,
                Call.call_start_time >= today_start,
                Call.call_start_time <= today_end
            )
        )
    )
    today_calls = calls_result.scalars().all()

    total_calls = len(today_calls)
    inbound = sum(1 for c in today_calls if c.call_type == CallType.INBOUND)
    outbound = sum(1 for c in today_calls if c.call_type == CallType.OUTBOUND)
    resolved = sum(1 for c in today_calls if c.is_resolved_first_call)

    # AHT calculation
    completed_calls = [c for c in today_calls if c.duration_seconds]
    avg_handle_time = 0
    avg_talk_time = 0
    if completed_calls:
        avg_handle_time = sum(c.duration_seconds for c in completed_calls) // len(completed_calls)
        talk_times = [c.talk_time_seconds for c in completed_calls if c.talk_time_seconds]
        avg_talk_time = sum(talk_times) // len(talk_times) if talk_times else 0

    # FCR rate
    first_contact = sum(1 for c in today_calls if c.is_first_contact)
    fcr_rate = Decimal(str(resolved / first_contact * 100)) if first_contact > 0 else Decimal("0")

    # Pending callbacks
    callbacks_result = await db.execute(
        select(func.count(CallbackSchedule.id)).where(
            and_(
                CallbackSchedule.assigned_agent_id == target_agent_id,
                CallbackSchedule.status == CallbackStatus.SCHEDULED
            )
        )
    )
    pending_callbacks = callbacks_result.scalar() or 0

    # Overdue callbacks
    now = datetime.now(timezone.utc)
    overdue_result = await db.execute(
        select(func.count(CallbackSchedule.id)).where(
            and_(
                CallbackSchedule.assigned_agent_id == target_agent_id,
                CallbackSchedule.status == CallbackStatus.SCHEDULED,
                CallbackSchedule.scheduled_datetime < now
            )
        )
    )
    overdue_callbacks = overdue_result.scalar() or 0

    # Get agent name
    agent_result = await db.execute(select(User).where(User.id == target_agent_id))
    agent = agent_result.scalar_one_or_none()

    return AgentDashboardResponse(
        agent_id=target_agent_id,
        agent_name=_get_user_name(agent) or "Unknown",
        date=today,
        total_calls_today=total_calls,
        inbound_calls=inbound,
        outbound_calls=outbound,
        resolved_calls=resolved,
        pending_callbacks=pending_callbacks,
        overdue_callbacks=overdue_callbacks,
        avg_handle_time_seconds=avg_handle_time,
        avg_talk_time_seconds=avg_talk_time,
        fcr_rate=fcr_rate,
    )


@router.get("/dashboard/center", response_model=CallCenterDashboardResponse)
@require_module("crm_service")
async def get_call_center_dashboard(
    db: DB,
    current_user: User = Depends(get_current_user),
):
    """Get overall call center dashboard."""
    today = datetime.now(timezone.utc).date()
    today_start = datetime.combine(today, datetime.min.time())
    today_end = datetime.combine(today, datetime.max.time())
    now = datetime.now(timezone.utc)

    # Today's calls
    calls_result = await db.execute(
        select(Call).where(
            and_(
                Call.call_start_time >= today_start,
                Call.call_start_time <= today_end
            )
        )
    )
    today_calls = calls_result.scalars().all()

    total_calls = len(today_calls)
    inbound = sum(1 for c in today_calls if c.call_type == CallType.INBOUND)
    outbound = sum(1 for c in today_calls if c.call_type == CallType.OUTBOUND)
    in_progress = sum(1 for c in today_calls if c.status == CallStatus.IN_PROGRESS)
    resolved = sum(1 for c in today_calls if c.is_resolved_first_call)
    tickets_created = sum(1 for c in today_calls if c.linked_ticket_id)
    leads_created = sum(1 for c in today_calls if c.linked_lead_id)
    escalated = sum(1 for c in today_calls if c.outcome == CallOutcome.ESCALATED)

    # Callbacks
    callbacks_scheduled_result = await db.execute(
        select(func.count(CallbackSchedule.id)).where(
            CallbackSchedule.status == CallbackStatus.SCHEDULED
        )
    )
    callbacks_scheduled = callbacks_scheduled_result.scalar() or 0

    callbacks_completed_result = await db.execute(
        select(func.count(CallbackSchedule.id)).where(
            and_(
                CallbackSchedule.status == CallbackStatus.COMPLETED,
                func.date(CallbackSchedule.completed_at) == today
            )
        )
    )
    callbacks_completed = callbacks_completed_result.scalar() or 0

    callbacks_overdue_result = await db.execute(
        select(func.count(CallbackSchedule.id)).where(
            and_(
                CallbackSchedule.status == CallbackStatus.SCHEDULED,
                CallbackSchedule.scheduled_datetime < now
            )
        )
    )
    callbacks_overdue = callbacks_overdue_result.scalar() or 0

    # AHT
    completed_calls = [c for c in today_calls if c.duration_seconds]
    avg_handle_time = 0
    if completed_calls:
        avg_handle_time = sum(c.duration_seconds for c in completed_calls) // len(completed_calls)

    # FCR
    first_contact = sum(1 for c in today_calls if c.is_first_contact)
    fcr_rate = Decimal(str(resolved / first_contact * 100)) if first_contact > 0 else Decimal("0")

    # By category
    calls_by_category = {}
    for c in today_calls:
        cat = c.category if c.category else "OTHER"
        calls_by_category[cat] = calls_by_category.get(cat, 0) + 1

    # By outcome
    calls_by_outcome = {}
    for c in today_calls:
        if c.outcome:
            out = c.outcome
            calls_by_outcome[out] = calls_by_outcome.get(out, 0) + 1

    return CallCenterDashboardResponse(
        date=today,
        total_calls_today=total_calls,
        inbound_calls=inbound,
        outbound_calls=outbound,
        calls_in_progress=in_progress,
        resolved_calls=resolved,
        tickets_created=tickets_created,
        leads_created=leads_created,
        escalated_calls=escalated,
        callbacks_scheduled=callbacks_scheduled,
        callbacks_completed=callbacks_completed,
        callbacks_overdue=callbacks_overdue,
        avg_handle_time_seconds=avg_handle_time,
        fcr_rate=fcr_rate,
        calls_by_category=calls_by_category,
        calls_by_outcome=calls_by_outcome,
    )


@router.get("/reports/fcr", response_model=FCRReportResponse)
@require_module("crm_service")
async def get_fcr_report(
    start_date: date,
    end_date: date,
    db: DB,
    agent_id: Optional[UUID] = None,
    category: Optional[CallCategory] = None,
    current_user: User = Depends(get_current_user),
):
    """Get First Call Resolution report."""
    start_dt = datetime.combine(start_date, datetime.min.time())
    end_dt = datetime.combine(end_date, datetime.max.time())

    conditions = [
        Call.call_start_time >= start_dt,
        Call.call_start_time <= end_dt,
        Call.status == CallStatus.COMPLETED
    ]
    if agent_id:
        conditions.append(Call.agent_id == agent_id)
    if category:
        conditions.append(Call.category == category)

    result = await db.execute(
        select(Call).where(and_(*conditions))
    )
    calls = result.scalars().all()

    total_calls = len(calls)
    first_contact_calls = sum(1 for c in calls if c.is_first_contact)
    resolved_first_call = sum(1 for c in calls if c.is_resolved_first_call)
    fcr_rate = Decimal(str(resolved_first_call / first_contact_calls * 100)) if first_contact_calls > 0 else Decimal("0")

    # By category
    fcr_by_category = {}
    for c in calls:
        cat = c.category if c.category else "OTHER"
        if cat not in fcr_by_category:
            fcr_by_category[cat] = {"total": 0, "fcr": 0}
        fcr_by_category[cat]["total"] += 1
        if c.is_resolved_first_call:
            fcr_by_category[cat]["fcr"] += 1

    return FCRReportResponse(
        start_date=start_date,
        end_date=end_date,
        total_calls=total_calls,
        first_contact_calls=first_contact_calls,
        resolved_first_call=resolved_first_call,
        fcr_rate=fcr_rate,
        fcr_by_category=fcr_by_category
    )
