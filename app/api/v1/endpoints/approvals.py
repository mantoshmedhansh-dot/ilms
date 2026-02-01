"""
Multi-Level Approval Workflow API Endpoints.

Provides:
- Finance Approvals Dashboard
- Submit for Approval (PO, Stock Transfer, etc.)
- Approve/Reject with multi-level workflow
- Escalation and Reassignment
- Bulk approval actions
"""
from datetime import datetime, date, timedelta, timezone
from decimal import Decimal
from typing import Optional, List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func, and_, or_, case
from sqlalchemy.orm import selectinload

from app.api.deps import DB, get_current_user
from app.models.user import User
from app.models.approval import (
    ApprovalRequest,
    ApprovalHistory,
    ApprovalEntityType,
    ApprovalLevel,
    ApprovalStatus,
    get_approval_level,
    get_approval_level_name,
)
from app.models.purchase import PurchaseOrder, POStatus, PurchaseRequisition, RequisitionStatus
from app.models.vendor import Vendor, VendorStatus
from app.schemas.approval import (

    ApprovalRequestResponse,
    ApprovalRequestBrief,
    ApprovalListResponse,
    ApprovalHistoryResponse,
    ApprovalDashboardResponse,
    ApprovalLevelCount,
    SubmitForApprovalRequest,
    ApproveRequest,
    RejectRequest,
    EscalateRequest,
    ReassignRequest,
    POSubmitForApprovalRequest,
    POApprovalResponse,
    BulkApproveRequest,
    BulkRejectRequest,
    BulkActionResponse,
)
from app.core.module_decorators import require_module

router = APIRouter(prefix="/approvals", tags=["Approvals"])


# ============== Helper Functions ==============

def _get_user_name(user: Optional[User]) -> Optional[str]:
    """Get user display name."""
    if not user:
        return None
    if user.first_name and user.last_name:
        return f"{user.first_name} {user.last_name}"
    return user.email


async def _generate_approval_request_number(db) -> str:
    """Generate unique approval request number."""
    today = date.today()
    prefix = f"APR-{today.strftime('%Y%m%d')}"

    # Get max number for today
    result = await db.execute(
        select(func.max(ApprovalRequest.request_number))
        .where(ApprovalRequest.request_number.like(f"{prefix}%"))
    )
    max_number = result.scalar()

    if max_number:
        # Extract sequence and increment
        seq = int(max_number.split("-")[-1]) + 1
    else:
        seq = 1

    return f"{prefix}-{seq:04d}"


async def _create_approval_request(
    db,
    entity_type: ApprovalEntityType,
    entity_id: UUID,
    entity_number: str,
    amount: Decimal,
    title: str,
    requested_by: UUID,
    description: Optional[str] = None,
    extra_info: Optional[dict] = None,
    priority: int = 5,
) -> ApprovalRequest:
    """Create a new approval request."""
    request_number = await _generate_approval_request_number(db)
    approval_level = get_approval_level(amount)

    # Calculate due date based on priority (1=1 day, 5=3 days, 10=7 days)
    days_map = {1: 1, 2: 1, 3: 2, 4: 2, 5: 3, 6: 4, 7: 5, 8: 5, 9: 6, 10: 7}
    due_days = days_map.get(priority, 3)
    due_date = datetime.now(timezone.utc) + timedelta(days=due_days)

    approval = ApprovalRequest(
        request_number=request_number,
        entity_type=entity_type,
        entity_id=entity_id,
        entity_number=entity_number,
        amount=amount,
        approval_level=approval_level,
        status=ApprovalStatus.PENDING,
        priority=priority,
        title=title,
        description=description,
        requested_by=requested_by,
        requested_at=datetime.now(timezone.utc),
        due_date=due_date,
        extra_info=extra_info,
    )
    db.add(approval)
    await db.flush()  # Flush to get the ID

    # Create history entry
    history = ApprovalHistory(
        approval_request_id=approval.id,
        action="SUBMITTED",
        from_status=None,
        to_status=ApprovalStatus.PENDING.value,
        performed_by=requested_by,
        comments="Submitted for approval",
    )
    db.add(history)

    return approval


def _build_approval_response(
    approval: ApprovalRequest,
    include_history: bool = False
) -> ApprovalRequestResponse:
    """Build approval request response."""
    return ApprovalRequestResponse(
        id=approval.id,
        request_number=approval.request_number,
        entity_type=approval.entity_type,
        entity_id=approval.entity_id,
        entity_number=approval.entity_number,
        amount=approval.amount,
        approval_level=approval.approval_level,
        approval_level_name=get_approval_level_name(approval.approval_level),
        status=approval.status,
        priority=approval.priority,
        title=approval.title,
        description=approval.description,
        requested_by=approval.requested_by,
        requester_name=_get_user_name(approval.requester) if approval.requester else None,
        requested_at=approval.requested_at,
        current_approver_id=approval.current_approver_id,
        current_approver_name=_get_user_name(approval.current_approver) if approval.current_approver else None,
        approved_by=approval.approved_by,
        approver_name=_get_user_name(approval.approver) if approval.approver else None,
        approved_at=approval.approved_at,
        approval_comments=approval.approval_comments,
        rejected_by=approval.rejected_by,
        rejecter_name=_get_user_name(approval.rejecter) if approval.rejecter else None,
        rejected_at=approval.rejected_at,
        rejection_reason=approval.rejection_reason,
        due_date=approval.due_date,
        is_overdue=approval.is_overdue,
        escalated_at=approval.escalated_at,
        escalated_to=approval.escalated_to,
        escalation_reason=approval.escalation_reason,
        extra_info=approval.extra_info,
        created_at=approval.created_at,
        updated_at=approval.updated_at,
        history=[
            ApprovalHistoryResponse(
                id=h.id,
                action=h.action,
                from_status=h.from_status,
                to_status=h.to_status,
                comments=h.comments,
                performed_by=h.performed_by,
                actor_name=_get_user_name(h.actor) if h.actor else None,
                created_at=h.created_at,
            )
            for h in approval.history
        ] if include_history and approval.history else None,
    )


# ============== Dashboard Endpoints ==============

@router.get("/dashboard", response_model=ApprovalDashboardResponse)
@require_module("finance")
async def get_approval_dashboard(
    db: DB,
    current_user: User = Depends(get_current_user),
):
    """
    Get Finance Approvals Dashboard.

    Returns summary counts, pending items by level, and recent activity.
    """
    today = date.today()
    today_start = datetime.combine(today, datetime.min.time())
    today_end = datetime.combine(today, datetime.max.time())

    # Total pending
    pending_result = await db.execute(
        select(func.count(ApprovalRequest.id))
        .where(ApprovalRequest.status == ApprovalStatus.PENDING)
    )
    total_pending = pending_result.scalar() or 0

    # Approved today
    approved_today_result = await db.execute(
        select(func.count(ApprovalRequest.id))
        .where(
            ApprovalRequest.status == ApprovalStatus.APPROVED,
            ApprovalRequest.approved_at >= today_start,
            ApprovalRequest.approved_at <= today_end,
        )
    )
    total_approved_today = approved_today_result.scalar() or 0

    # Rejected today
    rejected_today_result = await db.execute(
        select(func.count(ApprovalRequest.id))
        .where(
            ApprovalRequest.status == ApprovalStatus.REJECTED,
            ApprovalRequest.rejected_at >= today_start,
            ApprovalRequest.rejected_at <= today_end,
        )
    )
    total_rejected_today = rejected_today_result.scalar() or 0

    # Overdue
    overdue_result = await db.execute(
        select(func.count(ApprovalRequest.id))
        .where(
            ApprovalRequest.status == ApprovalStatus.PENDING,
            ApprovalRequest.due_date < datetime.now(timezone.utc),
        )
    )
    total_overdue = overdue_result.scalar() or 0

    # By level
    by_level = []
    for level in ApprovalLevel:
        level_result = await db.execute(
            select(
                func.count(ApprovalRequest.id),
                func.coalesce(func.sum(ApprovalRequest.amount), 0),
            )
            .where(
                ApprovalRequest.status == ApprovalStatus.PENDING,
                ApprovalRequest.approval_level == level,
            )
        )
        count, amount = level_result.one()
        by_level.append(ApprovalLevelCount(
            level=level,
            level_name=get_approval_level_name(level),
            pending_count=count or 0,
            total_amount=amount or Decimal("0"),
        ))

    # By entity type
    entity_type_result = await db.execute(
        select(
            ApprovalRequest.entity_type,
            func.count(ApprovalRequest.id),
        )
        .where(ApprovalRequest.status == ApprovalStatus.PENDING)
        .group_by(ApprovalRequest.entity_type)
    )
    # row[0] is a string (VARCHAR) from DB, not an enum
    by_entity_type = {(row[0].value if hasattr(row[0], 'value') else row[0]): row[1] for row in entity_type_result.all()}

    # Recent approvals (last 10)
    recent_result = await db.execute(
        select(ApprovalRequest)
        .options(selectinload(ApprovalRequest.requester))
        .where(ApprovalRequest.status == ApprovalStatus.APPROVED)
        .order_by(ApprovalRequest.approved_at.desc())
        .limit(10)
    )
    recent_approvals = [
        ApprovalRequestBrief(
            id=a.id,
            request_number=a.request_number,
            entity_type=a.entity_type,
            entity_number=a.entity_number,
            amount=a.amount,
            approval_level=a.approval_level,
            status=a.status,
            title=a.title,
            requester_name=_get_user_name(a.requester) if a.requester else None,
            requested_at=a.requested_at,
            is_overdue=a.is_overdue,
        )
        for a in recent_result.scalars().all()
    ]

    # Urgent pending (high priority or overdue)
    urgent_result = await db.execute(
        select(ApprovalRequest)
        .options(selectinload(ApprovalRequest.requester))
        .where(
            ApprovalRequest.status == ApprovalStatus.PENDING,
            or_(
                ApprovalRequest.priority <= 3,
                ApprovalRequest.due_date < datetime.now(timezone.utc),
            )
        )
        .order_by(ApprovalRequest.priority, ApprovalRequest.requested_at)
        .limit(10)
    )
    urgent_pending = [
        ApprovalRequestBrief(
            id=a.id,
            request_number=a.request_number,
            entity_type=a.entity_type,
            entity_number=a.entity_number,
            amount=a.amount,
            approval_level=a.approval_level,
            status=a.status,
            title=a.title,
            requester_name=_get_user_name(a.requester) if a.requester else None,
            requested_at=a.requested_at,
            is_overdue=a.due_date < datetime.now(timezone.utc) if a.due_date else False,
        )
        for a in urgent_result.scalars().all()
    ]

    return ApprovalDashboardResponse(
        total_pending=total_pending,
        total_approved_today=total_approved_today,
        total_rejected_today=total_rejected_today,
        total_overdue=total_overdue,
        by_level=by_level,
        by_entity_type=by_entity_type,
        recent_approvals=recent_approvals,
        urgent_pending=urgent_pending,
    )


# ============== List Endpoints ==============

@router.get("", response_model=ApprovalListResponse)
@require_module("finance")
async def list_approvals(
    db: DB,
    status: Optional[ApprovalStatus] = Query(None),
    entity_type: Optional[ApprovalEntityType] = Query(None),
    approval_level: Optional[ApprovalLevel] = Query(None),
    search: Optional[str] = Query(None, description="Search by request/entity number"),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
):
    """
    List approval requests with filters.
    """
    query = (
        select(ApprovalRequest)
        .options(selectinload(ApprovalRequest.requester))
    )

    # Apply filters
    if status:
        query = query.where(ApprovalRequest.status == status)
    if entity_type:
        query = query.where(ApprovalRequest.entity_type == entity_type)
    if approval_level:
        query = query.where(ApprovalRequest.approval_level == approval_level)
    if search:
        query = query.where(
            or_(
                ApprovalRequest.request_number.ilike(f"%{search}%"),
                ApprovalRequest.entity_number.ilike(f"%{search}%"),
            )
        )

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # Paginate
    query = query.order_by(ApprovalRequest.requested_at.desc())
    query = query.offset((page - 1) * size).limit(size)

    result = await db.execute(query)
    approvals = result.scalars().all()

    items = [
        ApprovalRequestBrief(
            id=a.id,
            request_number=a.request_number,
            entity_type=a.entity_type,
            entity_number=a.entity_number,
            amount=a.amount,
            approval_level=a.approval_level,
            status=a.status,
            title=a.title,
            requester_name=_get_user_name(a.requester) if a.requester else None,
            requested_at=a.requested_at,
            is_overdue=a.due_date < datetime.now(timezone.utc) if a.due_date and a.status == ApprovalStatus.PENDING else False,
        )
        for a in approvals
    ]

    return ApprovalListResponse(
        items=items,
        total=total,
        page=page,
        size=size,
        pages=(total + size - 1) // size,
    )


@router.get("/pending")
@require_module("finance")
async def list_pending_approvals(
    db: DB,
    approval_level: Optional[ApprovalLevel] = Query(None),
    entity_type: Optional[ApprovalEntityType] = Query(None),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
):
    """
    List pending approval requests.

    Returns items in the format expected by the frontend.
    """
    query = (
        select(ApprovalRequest)
        .options(selectinload(ApprovalRequest.requester))
        .where(ApprovalRequest.status == ApprovalStatus.PENDING)
    )

    if approval_level:
        query = query.where(ApprovalRequest.approval_level == approval_level)
    if entity_type:
        query = query.where(ApprovalRequest.entity_type == entity_type)

    # Order by priority and date
    query = query.order_by(ApprovalRequest.priority, ApprovalRequest.requested_at)
    query = query.offset((page - 1) * size).limit(size)

    result = await db.execute(query)
    approvals = result.scalars().all()

    # Map entity types to frontend expected values
    entity_type_map = {
        "PURCHASE_ORDER": "PURCHASE_ORDER",
        "PURCHASE_REQUISITION": "PURCHASE_ORDER",  # Map PR to PO for display
        "VENDOR_ONBOARDING": "VENDOR",
        "STOCK_TRANSFER": "TRANSFER",
        "STOCK_ADJUSTMENT": "TRANSFER",
        "JOURNAL_ENTRY": "JOURNAL_ENTRY",
        "CREDIT_NOTE": "CREDIT_NOTE",
        "DEBIT_NOTE": "CREDIT_NOTE",
        "SALES_CHANNEL": "VENDOR",  # Map sales channel to vendor for display
    }

    # Map priority numbers to labels
    priority_map = {
        1: "URGENT", 2: "URGENT",
        3: "HIGH", 4: "HIGH",
        5: "NORMAL", 6: "NORMAL",
        7: "LOW", 8: "LOW", 9: "LOW", 10: "LOW",
    }

    items = []
    for a in approvals:
        # entity_type is VARCHAR in DB, not enum
        entity_type_str = a.entity_type.value if hasattr(a.entity_type, 'value') else a.entity_type
        mapped_type = entity_type_map.get(entity_type_str, entity_type_str)
        level_num = a.approval_level[-1] if a.approval_level else "1"
        is_overdue = a.due_date < datetime.now(timezone.utc) if a.due_date else False

        items.append({
            "id": str(a.id),
            "entity_type": mapped_type,
            "entity_id": str(a.entity_id),
            "reference": a.entity_number,
            "title": a.title,
            "description": a.description,
            "amount": float(a.amount) if a.amount else 0,
            "status": a.status,
            "level": f"L{level_num}",
            "current_approver": None,
            "requested_by": _get_user_name(a.requester) if a.requester else "Unknown",
            "requested_at": a.requested_at.isoformat() if a.requested_at else None,
            "sla_due_at": a.due_date.isoformat() if a.due_date else None,
            "is_sla_breached": is_overdue,
            "priority": priority_map.get(a.priority, "NORMAL"),
            "details": a.extra_info,
        })

    return {"items": items}


# ============== Stats Endpoint ==============

@router.get("/stats")
@require_module("finance")
async def get_approval_stats(
    db: DB,
    current_user: User = Depends(get_current_user),
):
    """
    Get approval statistics for the dashboard.

    Returns counts of pending, approved today, rejected today, and overdue approvals.
    """
    today = date.today()
    today_start = datetime.combine(today, datetime.min.time())
    today_end = datetime.combine(today, datetime.max.time())

    # Total pending
    pending_result = await db.execute(
        select(func.count(ApprovalRequest.id))
        .where(ApprovalRequest.status == ApprovalStatus.PENDING)
    )
    total_pending = pending_result.scalar() or 0

    # Approved today
    approved_today_result = await db.execute(
        select(func.count(ApprovalRequest.id))
        .where(
            ApprovalRequest.status == ApprovalStatus.APPROVED,
            ApprovalRequest.approved_at >= today_start,
            ApprovalRequest.approved_at <= today_end,
        )
    )
    total_approved_today = approved_today_result.scalar() or 0

    # Rejected today
    rejected_today_result = await db.execute(
        select(func.count(ApprovalRequest.id))
        .where(
            ApprovalRequest.status == ApprovalStatus.REJECTED,
            ApprovalRequest.rejected_at >= today_start,
            ApprovalRequest.rejected_at <= today_end,
        )
    )
    total_rejected_today = rejected_today_result.scalar() or 0

    # Overdue
    overdue_result = await db.execute(
        select(func.count(ApprovalRequest.id))
        .where(
            ApprovalRequest.status == ApprovalStatus.PENDING,
            ApprovalRequest.due_date < datetime.now(timezone.utc),
        )
    )
    total_overdue = overdue_result.scalar() or 0

    # By entity type
    entity_type_result = await db.execute(
        select(
            ApprovalRequest.entity_type,
            func.count(ApprovalRequest.id),
        )
        .where(ApprovalRequest.status == ApprovalStatus.PENDING)
        .group_by(ApprovalRequest.entity_type)
    )
    # row[0] is a string (VARCHAR) from DB, not an enum
    by_entity_type = {(row[0].value if hasattr(row[0], 'value') else row[0]): row[1] for row in entity_type_result.all()}

    return {
        "pending_count": total_pending,
        "approved_today": total_approved_today,
        "rejected_today": total_rejected_today,
        "sla_breached": total_overdue,
        "by_type": by_entity_type,
        "by_level": {},  # TODO: Add level counts if needed
    }


# ============== History Endpoint ==============

@router.get("/history")
@require_module("finance")
async def get_approval_history(
    db: DB,
    limit: int = Query(20, ge=1, le=100),
    entity_type: Optional[ApprovalEntityType] = Query(None),
    current_user: User = Depends(get_current_user),
):
    """
    Get recent approval activity history.

    Returns recently approved and rejected requests.
    """
    query = (
        select(ApprovalRequest)
        .options(selectinload(ApprovalRequest.requester))
        .where(
            or_(
                ApprovalRequest.status == ApprovalStatus.APPROVED,
                ApprovalRequest.status == ApprovalStatus.REJECTED,
            )
        )
    )

    if entity_type:
        query = query.where(ApprovalRequest.entity_type == entity_type)

    # Order by most recent action
    query = query.order_by(
        func.coalesce(
            ApprovalRequest.approved_at,
            ApprovalRequest.rejected_at
        ).desc()
    ).limit(limit)

    result = await db.execute(query)
    approvals = result.scalars().all()

    items = []
    for a in approvals:
        # Map entity types to frontend expected values
        entity_type_map = {
            "PURCHASE_ORDER": "PURCHASE_ORDER",
            "PURCHASE_REQUISITION": "PURCHASE_ORDER",
            "VENDOR_ONBOARDING": "VENDOR",
            "STOCK_TRANSFER": "TRANSFER",
            "STOCK_ADJUSTMENT": "TRANSFER",
            "JOURNAL_ENTRY": "JOURNAL_ENTRY",
            "CREDIT_NOTE": "CREDIT_NOTE",
            "DEBIT_NOTE": "CREDIT_NOTE",
            "SALES_CHANNEL": "VENDOR",
        }
        # entity_type is VARCHAR in DB, not enum
        entity_type_str = a.entity_type.value if hasattr(a.entity_type, 'value') else a.entity_type
        mapped_type = entity_type_map.get(entity_type_str, entity_type_str)

        items.append({
            "id": str(a.id),
            "entity_type": mapped_type,
            "entity_id": str(a.entity_id),
            "reference": a.entity_number,
            "title": a.title,
            "amount": float(a.amount) if a.amount else 0,
            "level": f"L{a.approval_level[-1]}" if a.approval_level else "L1",
            "status": a.status,
            "requested_by": _get_user_name(a.requester) if a.requester else "Unknown",
            "requested_at": a.requested_at.isoformat() if a.requested_at else None,
        })

    return {"items": items, "total": len(items)}


# ============== Detail Endpoint ==============

@router.get("/{approval_id}", response_model=ApprovalRequestResponse)
@require_module("finance")
async def get_approval_request(
    approval_id: UUID,
    db: DB,
    current_user: User = Depends(get_current_user),
):
    """Get approval request details with history."""
    result = await db.execute(
        select(ApprovalRequest)
        .options(
            selectinload(ApprovalRequest.requester),
            selectinload(ApprovalRequest.approver),
            selectinload(ApprovalRequest.rejecter),
            selectinload(ApprovalRequest.current_approver),
            selectinload(ApprovalRequest.history).selectinload(ApprovalHistory.actor),
        )
        .where(ApprovalRequest.id == approval_id)
    )
    approval = result.scalar_one_or_none()

    if not approval:
        raise HTTPException(status_code=404, detail="Approval request not found")

    return _build_approval_response(approval, include_history=True)


# ============== PO Approval Endpoints ==============

@router.post("/po/{po_id}/submit", response_model=POApprovalResponse)
@require_module("finance")
async def submit_po_for_approval(
    po_id: UUID,
    request: POSubmitForApprovalRequest,
    db: DB,
    current_user: User = Depends(get_current_user),
):
    """
    Submit a Purchase Order for multi-level approval.

    This creates an ApprovalRequest and moves the PO status to PENDING_APPROVAL.
    The approval level is determined by the PO grand total:
    - LEVEL_1: Up to ₹50,000
    - LEVEL_2: ₹50,001 to ₹5,00,000
    - LEVEL_3: Above ₹5,00,000
    """
    # Get PO
    result = await db.execute(
        select(PurchaseOrder)
        .options(selectinload(PurchaseOrder.items))
        .where(PurchaseOrder.id == po_id)
    )
    po = result.scalar_one_or_none()

    if not po:
        raise HTTPException(status_code=404, detail="Purchase Order not found")

    if po.status != POStatus.DRAFT:
        raise HTTPException(
            status_code=400,
            detail=f"Only DRAFT POs can be submitted for approval. Current status: {po.status}"
        )

    # Check if already has an active approval request
    existing_result = await db.execute(
        select(ApprovalRequest)
        .where(
            ApprovalRequest.entity_type == ApprovalEntityType.PURCHASE_ORDER,
            ApprovalRequest.entity_id == po_id,
            ApprovalRequest.status == ApprovalStatus.PENDING,
        )
    )
    if existing_result.scalar_one_or_none():
        raise HTTPException(
            status_code=400,
            detail="PO already has a pending approval request"
        )

    # Create approval request
    approval = await _create_approval_request(
        db=db,
        entity_type=ApprovalEntityType.PURCHASE_ORDER,
        entity_id=po.id,
        entity_number=po.po_number,
        amount=po.grand_total,
        title=f"PO Approval: {po.po_number} - {po.vendor_name}",
        requested_by=current_user.id,
        description=request.comments,
        extra_info={
            "vendor_name": po.vendor_name,
            "vendor_gstin": po.vendor_gstin,
            "items_count": len(po.items),
            "delivery_date": po.expected_delivery_date.isoformat() if po.expected_delivery_date else None,
        },
    )

    # Update PO
    po.status = POStatus.PENDING_APPROVAL.value
    po.approval_request_id = approval.id
    po.approval_level = approval.approval_level
    po.submitted_for_approval_at = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(approval)

    return POApprovalResponse(
        po_id=po.id,
        po_number=po.po_number,
        po_status=po.status,
        approval_request_id=approval.id,
        approval_status=approval.status,
        approval_level=approval.approval_level,
        message=f"PO submitted for {get_approval_level_name(approval.approval_level)}",
    )


# ============== Approve/Reject Endpoints ==============

@router.post("/{approval_id}/approve", response_model=ApprovalRequestResponse)
@require_module("finance")
async def approve_request(
    approval_id: UUID,
    request: ApproveRequest,
    db: DB,
    current_user: User = Depends(get_current_user),
):
    """
    Approve an approval request.

    For Purchase Orders, this also updates the PO status to APPROVED.
    """
    result = await db.execute(
        select(ApprovalRequest)
        .options(
            selectinload(ApprovalRequest.requester),
            selectinload(ApprovalRequest.history),
        )
        .where(ApprovalRequest.id == approval_id)
    )
    approval = result.scalar_one_or_none()

    if not approval:
        raise HTTPException(status_code=404, detail="Approval request not found")

    if approval.status != ApprovalStatus.PENDING:
        raise HTTPException(
            status_code=400,
            detail=f"Only PENDING requests can be approved. Current status: {approval.status}"
        )

    # Maker-Checker validation
    if approval.requested_by == current_user.id:
        raise HTTPException(
            status_code=403,
            detail="Maker-Checker violation: You cannot approve your own request"
        )

    # Update approval request
    old_status = approval.status
    approval.status = ApprovalStatus.APPROVED.value
    approval.approved_by = current_user.id
    approval.approved_at = datetime.now(timezone.utc)
    # Accept either 'comments' or 'notes' from frontend
    approval.approval_comments = request.comments or request.notes

    # Create history entry
    history = ApprovalHistory(
        approval_request_id=approval.id,
        action="APPROVED",
        from_status=old_status,
        to_status=ApprovalStatus.APPROVED.value,
        performed_by=current_user.id,
        comments=request.comments or request.notes,
    )
    db.add(history)

    # Update the entity based on type - handle all entity types
    if approval.entity_type == ApprovalEntityType.PURCHASE_ORDER:
        po_result = await db.execute(
            select(PurchaseOrder).where(PurchaseOrder.id == approval.entity_id)
        )
        po = po_result.scalar_one_or_none()
        if po:
            po.status = POStatus.APPROVED.value
            po.approved_by = current_user.id
            po.approved_at = datetime.now(timezone.utc)
    elif approval.entity_type == ApprovalEntityType.PURCHASE_REQUISITION:
        pr_result = await db.execute(
            select(PurchaseRequisition).where(PurchaseRequisition.id == approval.entity_id)
        )
        pr = pr_result.scalar_one_or_none()
        if pr:
            pr.status = RequisitionStatus.APPROVED.value
            pr.approved_by = current_user.id
            pr.approved_at = datetime.now(timezone.utc)
    elif approval.entity_type == ApprovalEntityType.VENDOR_ONBOARDING:
        # Update vendor status to ACTIVE when approved
        vendor_result = await db.execute(
            select(Vendor).where(Vendor.id == approval.entity_id)
        )
        vendor = vendor_result.scalar_one_or_none()
        if vendor:
            vendor.status = VendorStatus.ACTIVE.value
            vendor.is_verified = True
            vendor.verified_at = datetime.now(timezone.utc)
            vendor.verified_by = current_user.id
            vendor.approved_by = current_user.id
            vendor.approved_at = datetime.now(timezone.utc)

            # ORCHESTRATION: Auto-create supplier code and other downstream setups
            from app.services.vendor_orchestration_service import VendorOrchestrationService

            orchestration = VendorOrchestrationService(db)
            await orchestration.on_vendor_approved(vendor, current_user.id)

    await db.commit()
    await db.refresh(approval)

    return _build_approval_response(approval, include_history=True)


@router.post("/{approval_id}/reject", response_model=ApprovalRequestResponse)
@require_module("finance")
async def reject_request(
    approval_id: UUID,
    request: RejectRequest,
    db: DB,
    current_user: User = Depends(get_current_user),
):
    """
    Reject an approval request.

    For Purchase Orders, this moves the PO back to DRAFT status.
    """
    result = await db.execute(
        select(ApprovalRequest)
        .options(
            selectinload(ApprovalRequest.requester),
            selectinload(ApprovalRequest.history),
        )
        .where(ApprovalRequest.id == approval_id)
    )
    approval = result.scalar_one_or_none()

    if not approval:
        raise HTTPException(status_code=404, detail="Approval request not found")

    if approval.status != ApprovalStatus.PENDING:
        raise HTTPException(
            status_code=400,
            detail=f"Only PENDING requests can be rejected. Current status: {approval.status}"
        )

    # Maker-Checker validation
    if approval.requested_by == current_user.id:
        raise HTTPException(
            status_code=403,
            detail="Maker-Checker violation: You cannot reject your own request"
        )

    # Update approval request
    old_status = approval.status
    approval.status = ApprovalStatus.REJECTED.value
    approval.rejected_by = current_user.id
    approval.rejected_at = datetime.now(timezone.utc)
    approval.rejection_reason = request.reason

    # Create history entry
    history = ApprovalHistory(
        approval_request_id=approval.id,
        action="REJECTED",
        from_status=old_status,
        to_status=ApprovalStatus.REJECTED.value,
        performed_by=current_user.id,
        comments=request.reason,
    )
    db.add(history)

    # Update the entity based on type
    if approval.entity_type == ApprovalEntityType.PURCHASE_ORDER:
        po_result = await db.execute(
            select(PurchaseOrder).where(PurchaseOrder.id == approval.entity_id)
        )
        po = po_result.scalar_one_or_none()
        if po:
            po.status = POStatus.DRAFT.value  # Back to draft for revision
            po.rejection_reason = request.reason
    elif approval.entity_type == ApprovalEntityType.PURCHASE_REQUISITION:
        pr_result = await db.execute(
            select(PurchaseRequisition).where(PurchaseRequisition.id == approval.entity_id)
        )
        pr = pr_result.scalar_one_or_none()
        if pr:
            pr.status = RequisitionStatus.REJECTED.value
            pr.rejection_reason = request.reason
    elif approval.entity_type == ApprovalEntityType.VENDOR_ONBOARDING:
        # Set vendor status to INACTIVE when rejected
        vendor_result = await db.execute(
            select(Vendor).where(Vendor.id == approval.entity_id)
        )
        vendor = vendor_result.scalar_one_or_none()
        if vendor:
            vendor.status = VendorStatus.INACTIVE.value
            vendor.internal_notes = f"Rejected: {request.reason}"

    await db.commit()
    await db.refresh(approval)

    return _build_approval_response(approval, include_history=True)


# ============== Escalation Endpoint ==============

@router.post("/{approval_id}/escalate", response_model=ApprovalRequestResponse)
@require_module("finance")
async def escalate_request(
    approval_id: UUID,
    request: EscalateRequest,
    db: DB,
    current_user: User = Depends(get_current_user),
):
    """
    Escalate an approval request to a higher authority.
    """
    result = await db.execute(
        select(ApprovalRequest)
        .options(
            selectinload(ApprovalRequest.requester),
            selectinload(ApprovalRequest.history),
        )
        .where(ApprovalRequest.id == approval_id)
    )
    approval = result.scalar_one_or_none()

    if not approval:
        raise HTTPException(status_code=404, detail="Approval request not found")

    if approval.status != ApprovalStatus.PENDING:
        raise HTTPException(
            status_code=400,
            detail=f"Only PENDING requests can be escalated. Current status: {approval.status}"
        )

    # Update approval
    old_status = approval.status
    approval.status = ApprovalStatus.ESCALATED.value
    approval.escalated_at = datetime.now(timezone.utc)
    approval.escalated_to = request.escalate_to
    approval.escalation_reason = request.reason

    # Create history entry
    history = ApprovalHistory(
        approval_request_id=approval.id,
        action="ESCALATED",
        from_status=old_status,
        to_status=ApprovalStatus.ESCALATED.value,
        performed_by=current_user.id,
        comments=request.reason,
    )
    db.add(history)

    await db.commit()
    await db.refresh(approval)

    return _build_approval_response(approval, include_history=True)


# ============== Bulk Actions ==============

@router.post("/bulk/approve", response_model=BulkActionResponse)
@require_module("finance")
async def bulk_approve(
    request: BulkApproveRequest,
    db: DB,
    current_user: User = Depends(get_current_user),
):
    """
    Bulk approve multiple approval requests.
    """
    successful = []
    failed = []

    for req_id in request.request_ids:
        try:
            result = await db.execute(
                select(ApprovalRequest).where(ApprovalRequest.id == req_id)
            )
            approval = result.scalar_one_or_none()

            if not approval:
                failed.append({"id": str(req_id), "error": "Not found"})
                continue

            if approval.status != ApprovalStatus.PENDING:
                failed.append({"id": str(req_id), "error": f"Status is {approval.status}"})
                continue

            if approval.requested_by == current_user.id:
                failed.append({"id": str(req_id), "error": "Cannot approve own request"})
                continue

            # Approve
            approval.status = ApprovalStatus.APPROVED.value
            approval.approved_by = current_user.id
            approval.approved_at = datetime.now(timezone.utc)
            approval.approval_comments = request.comments

            # Update entity
            if approval.entity_type == ApprovalEntityType.PURCHASE_ORDER:
                po_result = await db.execute(
                    select(PurchaseOrder).where(PurchaseOrder.id == approval.entity_id)
                )
                po = po_result.scalar_one_or_none()
                if po:
                    po.status = POStatus.APPROVED.value
                    po.approved_by = current_user.id
                    po.approved_at = datetime.now(timezone.utc)
            elif approval.entity_type == ApprovalEntityType.VENDOR_ONBOARDING:
                vendor_result = await db.execute(
                    select(Vendor).where(Vendor.id == approval.entity_id)
                )
                vendor = vendor_result.scalar_one_or_none()
                if vendor:
                    vendor.status = VendorStatus.ACTIVE.value
                    vendor.is_verified = True
                    vendor.verified_at = datetime.now(timezone.utc)
                    vendor.verified_by = current_user.id
                    vendor.approved_by = current_user.id
                    vendor.approved_at = datetime.now(timezone.utc)

            # History
            history = ApprovalHistory(
                approval_request_id=approval.id,
                action="APPROVED",
                from_status="PENDING",
                to_status=ApprovalStatus.APPROVED.value,
                performed_by=current_user.id,
                comments=f"Bulk approval: {request.comments}" if request.comments else "Bulk approval",
            )
            db.add(history)

            successful.append(req_id)

        except Exception as e:
            failed.append({"id": str(req_id), "error": str(e)})

    await db.commit()

    return BulkActionResponse(
        successful=successful,
        failed=failed,
        total_processed=len(request.request_ids),
        total_successful=len(successful),
        total_failed=len(failed),
    )
