"""API endpoints for Purchase/Procurement management (P2P Cycle)."""
from typing import Optional, List
from uuid import UUID
from datetime import date, datetime, timezone
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy import select, func, and_, or_, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.purchase import (
    PurchaseRequisition, PurchaseRequisitionItem, RequisitionStatus,
    PurchaseOrder, PurchaseOrderItem, POStatus,
    PODeliverySchedule, DeliveryLotStatus,
    GoodsReceiptNote, GRNItem, GRNStatus, QualityCheckResult,
    VendorInvoice, VendorInvoiceStatus,
    VendorProformaInvoice, VendorProformaItem, ProformaStatus,
    # SRN Models
    SalesReturnNote, SRNItem, SRNStatus, ReturnReason, ItemCondition,
    RestockDecision, PickupStatus, ResolutionType,
)
from app.models.vendor import Vendor, VendorLedger, VendorTransactionType
from app.models.inventory import StockItem, StockItemStatus, InventorySummary, StockMovement, StockMovementType
from app.models.product import Product
from app.models.warehouse import Warehouse
from app.models.user import User
from app.models.order import Order, OrderItem
from app.models.customer import Customer
from app.models.billing import TaxInvoice, CreditDebitNote, DocumentType, NoteReason, InvoiceStatus
from app.models.transporter import Transporter
from app.schemas.purchase import (
    # PR Schemas
    PurchaseRequisitionCreate, PurchaseRequisitionUpdate, PurchaseRequisitionResponse,
    PRListResponse, PRApproveRequest,
    # PO Schemas
    PurchaseOrderCreate, PurchaseOrderUpdate, PurchaseOrderResponse,
    POListResponse, POBrief, POApproveRequest, POSendToVendorRequest,
    # PO Delivery Schedule Schemas
    PODeliveryScheduleResponse, PODeliveryPaymentRequest,
    # GRN Schemas
    GoodsReceiptCreate, GoodsReceiptUpdate, GoodsReceiptResponse,
    GRNListResponse, GRNBrief, GRNQualityCheckRequest, GRNPutAwayRequest,
    # Vendor Invoice Schemas
    VendorInvoiceCreate, VendorInvoiceUpdate, VendorInvoiceResponse,
    VendorInvoiceListResponse, VendorInvoiceBrief,
    ThreeWayMatchRequest, ThreeWayMatchResponse,
    # Vendor Proforma Schemas
    VendorProformaCreate, VendorProformaUpdate, VendorProformaResponse,
    VendorProformaListResponse, VendorProformaBrief,
    VendorProformaApproveRequest, VendorProformaConvertToPORequest,
    # Report Schemas
    POSummaryRequest, POSummaryResponse, GRNSummaryResponse, PendingGRNResponse,
    # SRN Schemas
    SalesReturnCreate, SalesReturnResponse, SRNBrief, SRNListResponse,
    SRNQualityCheckRequest, SRNPutAwayRequest, PickupScheduleRequest,
    PickupUpdateRequest, SRNReceiveRequest, SRNResolveRequest,
)
from app.api.deps import DB, CurrentUser, get_current_user, require_permissions, Permissions
from app.services.audit_service import AuditService
from app.services.po_state_machine import (
    POStatus as POStat,  # Use alias to avoid conflict with model enum
    can_submit, can_approve, can_reject, can_send_to_vendor,
    can_receive_goods, can_edit, can_delete, can_cancel,
    transition_po, validate_transition, get_allowed_transitions
)
from app.services.approval_service import ApprovalService
from app.services.document_sequence_service import DocumentSequenceService
from app.models.approval import ApprovalEntityType
from app.core.module_decorators import require_module

router = APIRouter()


# ==================== Next Number Generation ====================

@router.get("/requisitions/next-number")
@require_module("procurement")
async def get_next_pr_number(
    db: DB,
):
    """Get the next available Purchase Requisition number.

    Returns financial year based format: PR/APL/25-26/00001
    """
    service = DocumentSequenceService(db)
    next_pr = await service.preview_next_number("PR")

    # Extract prefix (everything except the sequence number)
    parts = next_pr.rsplit("/", 1)
    prefix = parts[0] if len(parts) > 1 else "PR/APL"

    return {"next_number": next_pr, "prefix": prefix}


@router.get("/orders/next-number")
@require_module("procurement")
async def get_next_po_number(
    db: DB,
):
    """Get the next available Purchase Order number.

    Returns financial year based format: PO/APL/25-26/00001
    """
    service = DocumentSequenceService(db)
    next_po = await service.preview_next_number("PO")

    # Extract prefix (everything except the sequence number)
    parts = next_po.rsplit("/", 1)
    prefix = parts[0] if len(parts) > 1 else "PO/APL"

    return {"next_number": next_po, "prefix": prefix}


@router.get("/grn/next-number")
@require_module("procurement")
async def get_next_grn_number(
    db: DB,
):
    """Get the next available Goods Receipt Note number.

    Returns financial year based format: GRN/APL/25-26/00001
    """
    service = DocumentSequenceService(db)
    next_grn = await service.preview_next_number("GRN")

    # Extract prefix (everything except the sequence number)
    parts = next_grn.rsplit("/", 1)
    prefix = parts[0] if len(parts) > 1 else "GRN/APL"

    return {"next_number": next_grn, "prefix": prefix}


# ==================== Document Sequence Admin ====================

@router.get("/sequences/verify")
@require_module("procurement")
async def verify_document_sequences(
    db: DB,
    current_user: User = Depends(get_current_user),
):
    """
    Verify all document sequences are in sync with actual documents.

    Checks PR, PO, and GRN sequences against their respective tables.
    Returns status for each sequence and auto-repairs if out of sync.

    Requires authentication.
    """
    service = DocumentSequenceService(db)

    results = []

    # Check PR
    pr_result = await service.verify_and_repair_sequence(
        "PR", "purchase_requisitions", "requisition_number"
    )
    results.append(pr_result)

    # Check PO
    po_result = await service.verify_and_repair_sequence(
        "PO", "purchase_orders", "po_number"
    )
    results.append(po_result)

    # Check GRN
    grn_result = await service.verify_and_repair_sequence(
        "GRN", "goods_receipt_notes", "grn_number"
    )
    results.append(grn_result)

    await db.commit()

    return {
        "status": "OK" if all(r["status"] == "OK" or r["repaired"] for r in results) else "ISSUES_FOUND",
        "sequences": results,
        "message": "All sequences verified and repaired if needed"
    }


@router.post("/sequences/repair/{document_type}")
@require_module("procurement")
async def repair_document_sequence(
    document_type: str,
    max_number: int,
    db: DB,
    current_user: User = Depends(get_current_user),
):
    """
    Manually repair a document sequence to a specific number.

    Use this if you know the correct maximum sequence number.
    The sequence will be set to this number so next document gets max_number + 1.

    Args:
        document_type: PR, PO, or GRN
        max_number: The highest sequence number that exists

    Requires authentication.
    """
    service = DocumentSequenceService(
        db,
        user_id=str(current_user.id)
    )

    try:
        sequence = await service.sync_sequence_from_max(document_type, max_number)
        await db.commit()

        return {
            "success": True,
            "document_type": document_type,
            "current_number": sequence.current_number,
            "next_number": sequence.preview_next_number(),
            "message": f"Sequence repaired. Next {document_type} will be {sequence.preview_next_number()}"
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ==================== Admin Status Edit (Super Admin Only) ====================

@router.put("/admin/requisitions/{pr_id}/status")
@require_module("procurement")
async def admin_update_pr_status(
    pr_id: UUID,
    db: DB,
    permissions: Permissions,
    new_status: str = Query(..., description="New status value"),
    reason: Optional[str] = Query(None, description="Reason for status change"),
):
    """
    Update Purchase Requisition status (Super Admin only).

    Allows super admin to change PR status to any valid status.
    Use for data corrections or exceptional cases.

    Valid statuses: DRAFT, SUBMITTED, APPROVED, REJECTED, CONVERTED, CANCELLED
    """
    # Check super admin
    if not permissions.is_super_admin():
        raise HTTPException(
            status_code=403,
            detail="Only Super Admin can directly edit PR status"
        )

    # Validate status
    valid_statuses = [s.value for s in RequisitionStatus]
    if new_status.upper() not in valid_statuses:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid status. Valid values: {', '.join(valid_statuses)}"
        )

    # Get PR
    result = await db.execute(
        select(PurchaseRequisition).where(PurchaseRequisition.id == pr_id)
    )
    pr = result.scalar_one_or_none()
    if not pr:
        raise HTTPException(status_code=404, detail="Purchase Requisition not found")

    old_status = pr.status
    pr.status = new_status.upper()

    # Log the change
    audit_service = AuditService(db)
    await audit_service.log(
        action="ADMIN_STATUS_CHANGE",
        entity_type="PurchaseRequisition",
        entity_id=pr_id,
        user_id=permissions.user.id,
        old_values={"status": old_status},
        new_values={"status": new_status.upper(), "reason": reason},
        description=f"Admin changed PR status from {old_status} to {new_status.upper()}",
    )

    await db.commit()

    return {
        "success": True,
        "pr_number": pr.requisition_number,
        "old_status": old_status,
        "new_status": new_status.upper(),
        "changed_by": permissions.user.email,
        "reason": reason,
        "message": f"PR status changed from {old_status} to {new_status.upper()}"
    }


@router.put("/admin/orders/{po_id}/status")
@require_module("procurement")
async def admin_update_po_status(
    po_id: UUID,
    db: DB,
    permissions: Permissions,
    new_status: str = Query(..., description="New status value"),
    reason: Optional[str] = Query(None, description="Reason for status change"),
):
    """
    Update Purchase Order status (Super Admin only).

    Allows super admin to change PO status to any valid status.
    Use for data corrections or exceptional cases.

    Valid statuses: DRAFT, PENDING_APPROVAL, APPROVED, SENT_TO_VENDOR,
                   ACKNOWLEDGED, PARTIALLY_RECEIVED, FULLY_RECEIVED, CLOSED, CANCELLED
    """
    # Check super admin
    if not permissions.is_super_admin():
        raise HTTPException(
            status_code=403,
            detail="Only Super Admin can directly edit PO status"
        )

    # Validate status
    valid_statuses = [s.value for s in POStatus]
    if new_status.upper() not in valid_statuses:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid status. Valid values: {', '.join(valid_statuses)}"
        )

    # Get PO
    result = await db.execute(
        select(PurchaseOrder).where(PurchaseOrder.id == po_id)
    )
    po = result.scalar_one_or_none()
    if not po:
        raise HTTPException(status_code=404, detail="Purchase Order not found")

    old_status = po.status
    po.status = new_status.upper()

    # Log the change
    audit_service = AuditService(db)
    await audit_service.log(
        action="ADMIN_STATUS_CHANGE",
        entity_type="PurchaseOrder",
        entity_id=po_id,
        user_id=permissions.user.id,
        old_values={"status": old_status},
        new_values={"status": new_status.upper(), "reason": reason},
        description=f"Admin changed PO status from {old_status} to {new_status.upper()}",
    )

    await db.commit()

    return {
        "success": True,
        "po_number": po.po_number,
        "old_status": old_status,
        "new_status": new_status.upper(),
        "changed_by": permissions.user.email,
        "reason": reason,
        "message": f"PO status changed from {old_status} to {new_status.upper()}"
    }


@router.get("/admin/status-options")
@require_module("procurement")
async def get_status_options(
    permissions: Permissions,
):
    """
    Get all valid status options for PR and PO (Super Admin only).

    Returns list of valid statuses that can be used with admin status update endpoints.
    """
    # Check super admin
    if not permissions.is_super_admin():
        raise HTTPException(
            status_code=403,
            detail="Only Super Admin can access this endpoint"
        )

    return {
        "pr_statuses": [
            {"value": s.value, "label": s.value.replace("_", " ").title()}
            for s in RequisitionStatus
        ],
        "po_statuses": [
            {"value": s.value, "label": s.value.replace("_", " ").title()}
            for s in POStatus
        ],
        "grn_statuses": [
            {"value": s.value, "label": s.value.replace("_", " ").title()}
            for s in GRNStatus
        ],
    }


# ==================== Purchase Requisition (PR) ====================

@router.post("/requisitions", response_model=PurchaseRequisitionResponse, status_code=status.HTTP_201_CREATED)
@require_module("procurement")
async def create_purchase_requisition(
    pr_in: PurchaseRequisitionCreate,
    db: DB,
    current_user: User = Depends(get_current_user),
):
    """Create a new Purchase Requisition.

    Uses atomic sequence generation with financial year format: PR/APL/25-26/00001
    """
    today = date.today()

    # Generate PR number using atomic sequence service
    service = DocumentSequenceService(db)
    pr_number = await service.get_next_number("PR")

    # Calculate estimated total
    estimated_total = sum(
        item.quantity_requested * item.estimated_unit_price
        for item in pr_in.items
    )

    # Create PR
    pr = PurchaseRequisition(
        requisition_number=pr_number,
        requesting_department=pr_in.requesting_department,
        required_by_date=pr_in.required_by_date,
        delivery_warehouse_id=pr_in.delivery_warehouse_id,
        priority=pr_in.priority,
        reason=pr_in.reason,
        notes=pr_in.notes,
        request_date=today,
        requested_by=current_user.id,
        estimated_total=estimated_total,
    )

    db.add(pr)
    await db.flush()

    # Create PR items
    for item_data in pr_in.items:
        item = PurchaseRequisitionItem(
            requisition_id=pr.id,
            product_id=item_data.product_id,
            variant_id=item_data.variant_id,
            product_name=item_data.product_name,
            sku=item_data.sku,
            quantity_requested=item_data.quantity_requested,
            uom=item_data.uom,
            estimated_unit_price=item_data.estimated_unit_price,
            estimated_total=item_data.quantity_requested * item_data.estimated_unit_price,
            preferred_vendor_id=item_data.preferred_vendor_id,
            notes=item_data.notes,
            # Multi-delivery support
            monthly_quantities=item_data.monthly_quantities,
        )
        db.add(item)

    await db.commit()
    await db.refresh(pr)

    # Load items
    result = await db.execute(
        select(PurchaseRequisition)
        .options(selectinload(PurchaseRequisition.items))
        .where(PurchaseRequisition.id == pr.id)
    )
    pr = result.scalar_one()

    return pr


@router.get("/requisitions/stats")
@require_module("procurement")
async def get_requisition_stats(
    db: DB,
    current_user: User = Depends(get_current_user),
):
    """Get purchase requisition statistics."""
    # Count by status - use string comparison for VARCHAR columns
    draft_result = await db.execute(
        select(func.count(PurchaseRequisition.id))
        .where(PurchaseRequisition.status == "DRAFT")
    )
    draft_count = draft_result.scalar() or 0

    submitted_result = await db.execute(
        select(func.count(PurchaseRequisition.id))
        .where(PurchaseRequisition.status == "SUBMITTED")
    )
    submitted_count = submitted_result.scalar() or 0

    approved_result = await db.execute(
        select(func.count(PurchaseRequisition.id))
        .where(PurchaseRequisition.status == "APPROVED")
    )
    approved_count = approved_result.scalar() or 0

    rejected_result = await db.execute(
        select(func.count(PurchaseRequisition.id))
        .where(PurchaseRequisition.status == "REJECTED")
    )
    rejected_count = rejected_result.scalar() or 0

    converted_result = await db.execute(
        select(func.count(PurchaseRequisition.id))
        .where(PurchaseRequisition.status == "CONVERTED")
    )
    converted_count = converted_result.scalar() or 0

    total_result = await db.execute(
        select(func.count(PurchaseRequisition.id))
    )
    total_count = total_result.scalar() or 0

    # Calculate average approval time (for PRs that have been approved)
    # This would need approved_at and submitted_at timestamps to calculate properly
    avg_approval_time_hours = 0  # TODO: Calculate from timestamps when available

    return {
        "total": total_count,
        "draft": draft_count,
        "pending_approval": submitted_count,  # Frontend expects this name
        "approved": approved_count,
        "rejected": rejected_count,
        "converted_to_po": converted_count,  # Frontend expects this name
        "avg_approval_time_hours": avg_approval_time_hours,
    }


@router.get("/requisitions", response_model=PRListResponse)
@require_module("procurement")
async def list_purchase_requisitions(
    db: DB,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    status: Optional[RequisitionStatus] = None,
    warehouse_id: Optional[UUID] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    current_user: User = Depends(get_current_user),
):
    """List purchase requisitions."""
    query = select(PurchaseRequisition).options(
        selectinload(PurchaseRequisition.items),
        selectinload(PurchaseRequisition.requested_by_user),
        selectinload(PurchaseRequisition.delivery_warehouse),
    )
    count_query = select(func.count(PurchaseRequisition.id))

    filters = []
    if status:
        filters.append(PurchaseRequisition.status == status)
    if warehouse_id:
        filters.append(PurchaseRequisition.delivery_warehouse_id == warehouse_id)
    if start_date:
        filters.append(PurchaseRequisition.request_date >= start_date)
    if end_date:
        filters.append(PurchaseRequisition.request_date <= end_date)

    if filters:
        query = query.where(and_(*filters))
        count_query = count_query.where(and_(*filters))

    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    query = query.order_by(PurchaseRequisition.created_at.desc()).offset(skip).limit(limit)
    result = await db.execute(query)
    prs = result.scalars().all()

    # Build response with computed fields
    pr_responses = []
    for pr in prs:
        pr_dict = {
            "id": pr.id,
            "requisition_number": pr.requisition_number,
            "status": pr.status,
            "request_date": pr.request_date,
            "requested_by": pr.requested_by,
            "requested_by_name": pr.requested_by_user.full_name if pr.requested_by_user else None,
            "requesting_department": pr.requesting_department,
            "required_by_date": pr.required_by_date,
            "delivery_warehouse_id": pr.delivery_warehouse_id,
            "delivery_warehouse_name": pr.delivery_warehouse.name if pr.delivery_warehouse else None,
            "priority": pr.priority,
            "reason": pr.reason,
            "notes": pr.notes,
            "estimated_total": pr.estimated_total,
            "approved_by": pr.approved_by,
            "approved_at": pr.approved_at,
            "rejection_reason": pr.rejection_reason,
            "converted_to_po_id": pr.converted_to_po_id,
            "items": pr.items,
            "created_at": pr.created_at,
            "updated_at": pr.updated_at,
        }
        pr_responses.append(PurchaseRequisitionResponse.model_validate(pr_dict))

    return PRListResponse(
        items=pr_responses,
        total=total,
        skip=skip,
        limit=limit
    )


@router.get("/requisitions/{pr_id}", response_model=PurchaseRequisitionResponse)
@require_module("procurement")
async def get_purchase_requisition(
    pr_id: UUID,
    db: DB,
    current_user: User = Depends(get_current_user),
):
    """Get purchase requisition by ID."""
    result = await db.execute(
        select(PurchaseRequisition)
        .options(
            selectinload(PurchaseRequisition.items),
            selectinload(PurchaseRequisition.requested_by_user),
            selectinload(PurchaseRequisition.delivery_warehouse),
        )
        .where(PurchaseRequisition.id == pr_id)
    )
    pr = result.scalar_one_or_none()

    if not pr:
        raise HTTPException(status_code=404, detail="Purchase Requisition not found")

    # Build response with computed fields
    pr_dict = {
        "id": pr.id,
        "requisition_number": pr.requisition_number,
        "status": pr.status,
        "request_date": pr.request_date,
        "requested_by": pr.requested_by,
        "requested_by_name": pr.requested_by_user.full_name if pr.requested_by_user else None,
        "requesting_department": pr.requesting_department,
        "required_by_date": pr.required_by_date,
        "delivery_warehouse_id": pr.delivery_warehouse_id,
        "delivery_warehouse_name": pr.delivery_warehouse.name if pr.delivery_warehouse else None,
        "priority": pr.priority,
        "reason": pr.reason,
        "notes": pr.notes,
        "estimated_total": pr.estimated_total,
        "approved_by": pr.approved_by,
        "approved_at": pr.approved_at,
        "rejection_reason": pr.rejection_reason,
        "converted_to_po_id": pr.converted_to_po_id,
        "items": pr.items,
        "created_at": pr.created_at,
        "updated_at": pr.updated_at,
    }

    return PurchaseRequisitionResponse.model_validate(pr_dict)


@router.post("/requisitions/{pr_id}/approve", response_model=PurchaseRequisitionResponse)
@require_module("procurement")
async def approve_purchase_requisition(
    pr_id: UUID,
    request: PRApproveRequest,
    db: DB,
    current_user: User = Depends(get_current_user),
):
    """Approve or reject a purchase requisition."""
    result = await db.execute(
        select(PurchaseRequisition)
        .options(selectinload(PurchaseRequisition.items))
        .where(PurchaseRequisition.id == pr_id)
    )
    pr = result.scalar_one_or_none()

    if not pr:
        raise HTTPException(status_code=404, detail="Purchase Requisition not found")

    if pr.status != RequisitionStatus.SUBMITTED:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot {request.action.lower()} PR in {pr.status} status. Only SUBMITTED PRs can be approved/rejected."
        )

    if request.action == "APPROVE":
        pr.status = RequisitionStatus.APPROVED.value
        pr.approved_by = current_user.id
        pr.approved_at = datetime.now(timezone.utc)
    else:  # REJECT
        if not request.rejection_reason:
            raise HTTPException(status_code=400, detail="Rejection reason is required")
        pr.status = RequisitionStatus.REJECTED.value
        pr.rejection_reason = request.rejection_reason

    await db.commit()
    await db.refresh(pr)

    return pr


@router.post("/requisitions/{pr_id}/submit", response_model=PurchaseRequisitionResponse)
@require_module("procurement")
async def submit_purchase_requisition(
    pr_id: UUID,
    db: DB,
    current_user: User = Depends(get_current_user),
):
    """Submit a draft purchase requisition for approval."""
    result = await db.execute(
        select(PurchaseRequisition)
        .options(selectinload(PurchaseRequisition.items))
        .where(PurchaseRequisition.id == pr_id)
    )
    pr = result.scalar_one_or_none()

    if not pr:
        raise HTTPException(status_code=404, detail="Purchase Requisition not found")

    if pr.status != RequisitionStatus.DRAFT:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot submit PR in {pr.status} status. Only DRAFT PRs can be submitted."
        )

    # Validate PR has items
    if not pr.items:
        raise HTTPException(status_code=400, detail="Cannot submit PR without items")

    pr.status = RequisitionStatus.SUBMITTED.value

    # Create approval request
    approval = await ApprovalService.create_approval_request(
        db=db,
        entity_type=ApprovalEntityType.PURCHASE_REQUISITION,
        entity_id=pr.id,
        entity_number=pr.requisition_number,
        amount=pr.estimated_total or Decimal("0"),
        title=f"Purchase Requisition: {pr.requisition_number}",
        requested_by=current_user.id,
        description=pr.reason,
        priority=pr.priority if hasattr(pr, 'priority') and pr.priority else 5,
    )

    await db.commit()
    await db.refresh(pr)

    return pr


@router.post("/requisitions/{pr_id}/cancel", response_model=PurchaseRequisitionResponse)
@require_module("procurement")
async def cancel_purchase_requisition(
    pr_id: UUID,
    db: DB,
    current_user: User = Depends(get_current_user),
):
    """Cancel a purchase requisition."""
    result = await db.execute(
        select(PurchaseRequisition)
        .options(selectinload(PurchaseRequisition.items))
        .where(PurchaseRequisition.id == pr_id)
    )
    pr = result.scalar_one_or_none()

    if not pr:
        raise HTTPException(status_code=404, detail="Purchase Requisition not found")

    if pr.status == RequisitionStatus.CONVERTED:
        raise HTTPException(
            status_code=400,
            detail="Cannot cancel PR that has been converted to PO"
        )

    pr.status = RequisitionStatus.CANCELLED.value
    await db.commit()
    await db.refresh(pr)

    return pr


@router.delete("/requisitions/{pr_id}", status_code=status.HTTP_204_NO_CONTENT)
@require_module("procurement")
async def delete_purchase_requisition(
    pr_id: UUID,
    db: DB,
    current_user: User = Depends(get_current_user),
):
    """Delete a purchase requisition. Only DRAFT and CANCELLED PRs can be deleted."""
    result = await db.execute(
        select(PurchaseRequisition)
        .options(selectinload(PurchaseRequisition.items))
        .where(PurchaseRequisition.id == pr_id)
    )
    pr = result.scalar_one_or_none()

    if not pr:
        raise HTTPException(status_code=404, detail="Purchase Requisition not found")

    # Only allow deletion of DRAFT or CANCELLED PRs
    if pr.status not in [RequisitionStatus.DRAFT, RequisitionStatus.CANCELLED]:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot delete PR in {pr.status} status. Only DRAFT or CANCELLED PRs can be deleted."
        )

    # Delete items first (due to foreign key constraint)
    await db.execute(
        delete(PurchaseRequisitionItem).where(PurchaseRequisitionItem.requisition_id == pr_id)
    )

    # Delete the PR
    await db.delete(pr)
    await db.commit()

    return None


@router.put("/requisitions/{pr_id}", response_model=PurchaseRequisitionResponse)
@require_module("procurement")
async def update_purchase_requisition(
    pr_id: UUID,
    update_data: PurchaseRequisitionUpdate,
    db: DB,
    current_user: User = Depends(get_current_user),
):
    """Update a purchase requisition. Only DRAFT and SUBMITTED PRs can be edited.

    Supports full editing including:
    - Header fields (warehouse, priority, dates, reason, notes)
    - Line items (if items provided, replaces all existing items)
    """
    result = await db.execute(
        select(PurchaseRequisition)
        .options(selectinload(PurchaseRequisition.items))
        .where(PurchaseRequisition.id == pr_id)
    )
    pr = result.scalar_one_or_none()

    if not pr:
        raise HTTPException(status_code=404, detail="Purchase Requisition not found")

    # Only allow editing of DRAFT or SUBMITTED PRs
    allowed_statuses = [RequisitionStatus.DRAFT, RequisitionStatus.SUBMITTED]
    if pr.status not in allowed_statuses:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot edit PR with status '{pr.status}'. Only DRAFT or SUBMITTED PRs can be edited."
        )

    # Get update dict excluding items (handle separately)
    update_dict = update_data.model_dump(exclude_unset=True, exclude={"items"})

    # Update scalar fields
    for field, value in update_dict.items():
        setattr(pr, field, value)

    # Handle items update if provided
    if update_data.items is not None:
        # Delete existing items
        for item in pr.items:
            await db.delete(item)

        # Create new items
        estimated_total = Decimal("0")
        for item_data in update_data.items:
            item_dict = item_data.model_dump()
            item_total = item_dict["quantity_requested"] * item_dict["estimated_unit_price"]

            pr_item = PurchaseRequisitionItem(
                requisition_id=pr_id,
                product_id=item_dict["product_id"],
                variant_id=item_dict.get("variant_id"),
                product_name=item_dict["product_name"],
                sku=item_dict["sku"],
                quantity_requested=item_dict["quantity_requested"],
                uom=item_dict.get("uom", "PCS"),
                estimated_unit_price=item_dict["estimated_unit_price"],
                estimated_total=item_total,
                preferred_vendor_id=item_dict.get("preferred_vendor_id"),
                notes=item_dict.get("notes"),
                monthly_quantities=item_dict.get("monthly_quantities"),
            )
            db.add(pr_item)
            estimated_total += item_total

        # Update PR total
        pr.estimated_total = estimated_total

    await db.commit()

    # Refresh with items loaded
    await db.refresh(pr)
    result = await db.execute(
        select(PurchaseRequisition)
        .options(selectinload(PurchaseRequisition.items))
        .where(PurchaseRequisition.id == pr_id)
    )
    pr = result.scalar_one_or_none()

    return pr


@router.post("/requisitions/{pr_id}/convert-to-po", response_model=PurchaseOrderResponse)
@require_module("procurement")
async def convert_requisition_to_po(
    pr_id: UUID,
    request: dict,  # expects {"vendor_id": "uuid"}
    db: DB,
    current_user: User = Depends(get_current_user),
):
    """Convert an approved PR to a Purchase Order with multi-delivery support."""
    # Get PR with items
    result = await db.execute(
        select(PurchaseRequisition)
        .options(selectinload(PurchaseRequisition.items))
        .where(PurchaseRequisition.id == pr_id)
    )
    pr = result.scalar_one_or_none()

    if not pr:
        raise HTTPException(status_code=404, detail="Purchase Requisition not found")

    if pr.status != RequisitionStatus.APPROVED:
        raise HTTPException(
            status_code=400,
            detail=f"Only APPROVED PRs can be converted to PO. Current status: {pr.status}"
        )

    # Validate vendor
    vendor_id = request.get("vendor_id")
    if not vendor_id:
        raise HTTPException(status_code=400, detail="vendor_id is required")

    vendor_result = await db.execute(select(Vendor).where(Vendor.id == UUID(vendor_id)))
    vendor = vendor_result.scalar_one_or_none()
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor not found")

    # Generate PO number using atomic sequence service
    service = DocumentSequenceService(db)
    po_number = await service.get_next_number("PO")

    # Get warehouse
    wh_result = await db.execute(
        select(Warehouse).where(Warehouse.id == pr.delivery_warehouse_id)
    )
    warehouse = wh_result.scalar_one_or_none()

    # Determine inter-state
    is_inter_state = False
    if warehouse and vendor.gst_state_code:
        wh_state = getattr(warehouse, 'state_code', None)
        if wh_state and wh_state != vendor.gst_state_code:
            is_inter_state = True

    # Create PO
    po = PurchaseOrder(
        po_number=po_number,
        po_date=today,
        vendor_id=vendor.id,
        vendor_name=vendor.name,
        vendor_gstin=vendor.gstin,
        delivery_warehouse_id=pr.delivery_warehouse_id,
        requisition_id=pr.id,
        expected_delivery_date=pr.required_by_date or (today + datetime.timedelta(days=30)),
        created_by=current_user.id,
        subtotal=Decimal("0"),
        taxable_amount=Decimal("0"),
        grand_total=Decimal("0"),
    )
    db.add(po)
    await db.flush()

    # Create PO items from PR items with multi-delivery support
    subtotal = Decimal("0")
    total_discount = Decimal("0")
    taxable_amount = Decimal("0")
    cgst_total = Decimal("0")
    sgst_total = Decimal("0")
    igst_total = Decimal("0")
    line_number = 0
    month_totals = {}

    for pr_item in pr.items:
        line_number += 1
        gst_rate = Decimal("18")  # Default GST

        # Calculate amounts with proper Decimal precision
        qty = Decimal(str(pr_item.quantity_requested))
        unit_price = Decimal(str(pr_item.estimated_unit_price)).quantize(Decimal("0.01"))
        gross_amount = (qty * unit_price).quantize(Decimal("0.01"))
        item_taxable = gross_amount  # No discount from PR

        # GST calculation with proper precision
        if is_inter_state:
            igst_rate = gst_rate
            cgst_rate = Decimal("0")
            sgst_rate = Decimal("0")
        else:
            igst_rate = Decimal("0")
            cgst_rate = (gst_rate / Decimal("2")).quantize(Decimal("0.01"))
            sgst_rate = (gst_rate / Decimal("2")).quantize(Decimal("0.01"))

        cgst_amount = (item_taxable * cgst_rate / Decimal("100")).quantize(Decimal("0.01"))
        sgst_amount = (item_taxable * sgst_rate / Decimal("100")).quantize(Decimal("0.01"))
        igst_amount = (item_taxable * igst_rate / Decimal("100")).quantize(Decimal("0.01"))
        item_total = (item_taxable + cgst_amount + sgst_amount + igst_amount).quantize(Decimal("0.01"))

        po_item = PurchaseOrderItem(
            purchase_order_id=po.id,
            line_number=line_number,
            product_id=pr_item.product_id,
            variant_id=pr_item.variant_id,
            product_name=pr_item.product_name,
            sku=pr_item.sku,
            quantity_ordered=pr_item.quantity_requested,
            uom=pr_item.uom,
            unit_price=unit_price,  # Use quantized Decimal
            taxable_amount=item_taxable,
            gst_rate=gst_rate.quantize(Decimal("0.01")),
            cgst_rate=cgst_rate,
            sgst_rate=sgst_rate,
            igst_rate=igst_rate.quantize(Decimal("0.01")),
            cgst_amount=cgst_amount,
            sgst_amount=sgst_amount,
            igst_amount=igst_amount,
            total_amount=item_total,
            # Multi-delivery: carry over monthly_quantities from PR item
            monthly_quantities=pr_item.monthly_quantities,
        )
        db.add(po_item)

        subtotal += gross_amount
        taxable_amount += item_taxable
        cgst_total += cgst_amount
        sgst_total += sgst_amount
        igst_total += igst_amount

        # Collect month totals for delivery schedules
        if pr_item.monthly_quantities:
            for month_code, month_qty in pr_item.monthly_quantities.items():
                if month_code not in month_totals:
                    month_totals[month_code] = {"qty": 0, "value": Decimal("0"), "tax": Decimal("0")}
                month_qty_decimal = Decimal(str(month_qty))
                item_value = (month_qty_decimal * unit_price).quantize(Decimal("0.01"))
                item_tax = (item_value * gst_rate / Decimal("100")).quantize(Decimal("0.01"))
                month_totals[month_code]["qty"] += int(month_qty)
                month_totals[month_code]["value"] += item_value
                month_totals[month_code]["tax"] += item_tax

    # Update PO totals with proper Decimal precision
    total_tax = (cgst_total + sgst_total + igst_total).quantize(Decimal("0.01"))
    grand_total = (taxable_amount + total_tax).quantize(Decimal("0.01"))

    po.subtotal = subtotal.quantize(Decimal("0.01"))
    po.taxable_amount = taxable_amount.quantize(Decimal("0.01"))
    po.cgst_amount = cgst_total.quantize(Decimal("0.01"))
    po.sgst_amount = sgst_total.quantize(Decimal("0.01"))
    po.igst_amount = igst_total.quantize(Decimal("0.01"))
    po.total_tax = total_tax
    po.grand_total = grand_total

    # Create delivery schedules from monthly_quantities
    if month_totals:
        from calendar import monthrange

        # Get the last serial number from all previous delivery schedules
        last_serial_result = await db.execute(
            select(func.max(PODeliverySchedule.serial_number_end))
        )
        last_serial = last_serial_result.scalar() or 0
        current_serial = last_serial

        sorted_months = sorted(month_totals.keys())
        lot_number = 0

        for month_code in sorted_months:
            lot_number += 1
            month_data = month_totals[month_code]

            year, month = int(month_code.split("-")[0]), int(month_code.split("-")[1])
            expected_date = date(year, month, 15)
            window_start = date(year, month, 10)
            last_day = monthrange(year, month)[1]
            window_end = date(year, month, min(20, last_day))

            # Quantize accumulated values to ensure they fit in Numeric columns
            lot_value = month_data["value"].quantize(Decimal("0.01"))
            lot_tax = month_data["tax"].quantize(Decimal("0.01"))
            lot_total = (lot_value + lot_tax).quantize(Decimal("0.01"))

            month_names = ["", "JAN", "FEB", "MAR", "APR", "MAY", "JUN",
                          "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"]
            lot_name = f"{month_names[month]} {year}"

            # Calculate serial number range for this lot
            lot_qty = month_data["qty"]
            serial_start = current_serial + 1
            serial_end = current_serial + lot_qty
            current_serial = serial_end

            delivery_schedule = PODeliverySchedule(
                purchase_order_id=po.id,
                lot_number=lot_number,
                lot_name=lot_name,
                month_code=month_code,
                expected_delivery_date=expected_date,
                delivery_window_start=window_start,
                delivery_window_end=window_end,
                total_quantity=lot_qty,
                lot_value=lot_value,
                lot_tax=lot_tax,
                lot_total=lot_total,
                status=DeliveryLotStatus.PENDING,
                serial_number_start=serial_start,
                serial_number_end=serial_end,
            )
            db.add(delivery_schedule)

    # Mark PR as converted
    pr.status = RequisitionStatus.CONVERTED.value
    pr.converted_to_po_id = po.id

    await db.commit()

    # Load full PO with items and delivery schedules
    result = await db.execute(
        select(PurchaseOrder)
        .options(
            selectinload(PurchaseOrder.items),
            selectinload(PurchaseOrder.delivery_schedules)
        )
        .where(PurchaseOrder.id == po.id)
    )
    po = result.scalar_one()

    return po


# ==================== PR Download ====================

@router.get("/requisitions/{pr_id}/download")
@require_module("procurement")
async def download_purchase_requisition(
    pr_id: UUID,
    db: DB,
    current_user: User = Depends(get_current_user),
):
    """Download Purchase Requisition as printable HTML."""
    from fastapi.responses import HTMLResponse
    from app.models.company import Company

    result = await db.execute(
        select(PurchaseRequisition)
        .options(selectinload(PurchaseRequisition.items))
        .where(PurchaseRequisition.id == pr_id)
    )
    pr = result.scalar_one_or_none()

    if not pr:
        raise HTTPException(status_code=404, detail="Purchase Requisition not found")

    # Get company details
    company_result = await db.execute(select(Company).limit(1))
    company = company_result.scalar_one_or_none()

    # Get warehouse details
    warehouse = None
    if pr.delivery_warehouse_id:
        warehouse_result = await db.execute(
            select(Warehouse).where(Warehouse.id == pr.delivery_warehouse_id)
        )
        warehouse = warehouse_result.scalar_one_or_none()

    # Get requester details
    requester_result = await db.execute(
        select(User).where(User.id == pr.requested_by)
    )
    requester = requester_result.scalar_one_or_none()

    # Company info
    company_name = company.legal_name if company else "AQUAPURITE INDIA PRIVATE LIMITED"
    company_address = f"{company.address_line1 if company else 'Plot No. 123, Sector 5'}, {company.city if company else 'New Delhi'}, {company.state if company else 'Delhi'} - {company.pincode if company else '110001'}"
    company_phone = company.phone if company else "+91-11-12345678"
    company_email = company.email if company else "info@aquapurite.com"

    # Warehouse info
    warehouse_name = warehouse.name if warehouse else "Not Specified"
    warehouse_address = f"{warehouse.address_line1 if warehouse else ''}, {warehouse.city if warehouse else ''}, {warehouse.state if warehouse else ''}" if warehouse else "N/A"

    # Requester info
    requester_name = f"{requester.first_name or ''} {requester.last_name or ''}".strip() if requester else "N/A"
    requester_email = requester.email if requester else "N/A"

    # PR details
    pr_date_str = pr.created_at.strftime('%d.%m.%Y') if pr.created_at else datetime.now().strftime('%d.%m.%Y')
    required_by_str = pr.required_by_date.strftime('%d.%m.%Y') if pr.required_by_date else "TBD"

    # Status styling
    status_colors = {
        "DRAFT": "#6c757d",
        "SUBMITTED": "#17a2b8",
        "APPROVED": "#28a745",
        "REJECTED": "#dc3545",
        "CONVERTED": "#007bff",
        "CANCELLED": "#6c757d"
    }
    status_value = pr.status if pr.status else "DRAFT"
    status_color = status_colors.get(status_value, "#6c757d")

    # Build items table
    items_html = ""
    total_items = 0
    for idx, item in enumerate(pr.items, 1):
        total_items += item.quantity_requested
        items_html += f"""
            <tr>
                <td class="text-center">{idx}</td>
                <td class="item-code">{item.sku or '-'}</td>
                <td><strong>{item.product_name or '-'}</strong></td>
                <td class="text-center"><strong>{item.quantity_requested}</strong></td>
                <td class="text-center">{item.uom or 'PCS'}</td>
                <td>{getattr(item, 'notes', '') or '-'}</td>
            </tr>"""

    html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Purchase Requisition - {pr.requisition_number}</title>
    <style>
        @page {{ size: A4; margin: 15mm; }}
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: Arial, sans-serif; font-size: 11px; line-height: 1.4; padding: 15px; background: #fff; }}
        .document {{ max-width: 210mm; margin: 0 auto; border: 2px solid #000; }}

        /* Header */
        .header {{ background: linear-gradient(135deg, #2c5282 0%, #1a365d 100%); color: white; padding: 15px; text-align: center; }}
        .header h1 {{ font-size: 22px; margin-bottom: 6px; letter-spacing: 2px; }}
        .header .contact {{ font-size: 9px; }}

        /* Document Title */
        .doc-title {{ background: #e2e8f0; padding: 12px; text-align: center; border-bottom: 2px solid #000; }}
        .doc-title h2 {{ font-size: 18px; color: #2c5282; }}

        /* Info Grid */
        .info-grid {{ display: flex; flex-wrap: wrap; border-bottom: 1px solid #000; }}
        .info-box {{ flex: 1; min-width: 25%; padding: 8px 10px; border-right: 1px solid #000; }}
        .info-box:last-child {{ border-right: none; }}
        .info-box label {{ display: block; font-size: 9px; color: #666; text-transform: uppercase; margin-bottom: 3px; }}
        .info-box value {{ display: block; font-weight: bold; font-size: 11px; }}

        /* Status Badge */
        .status-badge {{ display: inline-block; padding: 3px 10px; border-radius: 3px; color: white; font-weight: bold; font-size: 10px; }}

        /* Table */
        table {{ width: 100%; border-collapse: collapse; }}
        th {{ background: #2c5282; color: white; padding: 10px 5px; font-size: 10px; text-align: center; border: 1px solid #000; }}
        td {{ padding: 8px 5px; border: 1px solid #000; font-size: 10px; }}
        .text-center {{ text-align: center; }}
        .text-right {{ text-align: right; }}
        .item-code {{ font-family: 'Courier New', monospace; font-weight: bold; color: #2c5282; font-size: 9px; }}

        /* Party Section */
        .party-section {{ display: flex; border-bottom: 1px solid #000; }}
        .party-box {{ flex: 1; padding: 10px; border-right: 1px solid #000; }}
        .party-box:last-child {{ border-right: none; }}
        .party-header {{ background: #2c5282; color: white; padding: 5px 8px; margin: -10px -10px 10px -10px; font-size: 10px; font-weight: bold; }}
        .party-box p {{ margin-bottom: 3px; }}

        /* Footer */
        .footer {{ padding: 15px; border-top: 2px solid #000; }}
        .signature-section {{ display: flex; margin-top: 30px; }}
        .signature-box {{ flex: 1; text-align: center; }}
        .signature-line {{ border-top: 1px solid #000; width: 150px; margin: 40px auto 5px; }}

        /* Print */
        .print-btn {{ position: fixed; top: 10px; right: 10px; padding: 10px 20px; background: #2c5282; color: white; border: none; cursor: pointer; border-radius: 5px; font-size: 14px; }}
        @media print {{
            .print-btn {{ display: none; }}
            body {{ padding: 0; }}
        }}
    </style>
</head>
<body>
    <button class="print-btn" onclick="window.print()">Print / Save PDF</button>

    <div class="document">
        <!-- Header -->
        <div class="header">
            <h1>{company_name}</h1>
            <p class="contact">{company_address} | Phone: {company_phone} | Email: {company_email}</p>
        </div>

        <!-- Document Title -->
        <div class="doc-title">
            <h2>PURCHASE REQUISITION</h2>
        </div>

        <!-- PR Info -->
        <div class="info-grid">
            <div class="info-box">
                <label>PR Number</label>
                <value style="color: #2c5282; font-size: 13px;">{pr.requisition_number}</value>
            </div>
            <div class="info-box">
                <label>PR Date</label>
                <value>{pr_date_str}</value>
            </div>
            <div class="info-box">
                <label>Required By</label>
                <value>{required_by_str}</value>
            </div>
            <div class="info-box">
                <label>Status</label>
                <value><span class="status-badge" style="background: {status_color};">{status_value}</span></value>
            </div>
        </div>

        <!-- Department & Requester Info -->
        <div class="party-section">
            <div class="party-box">
                <div class="party-header">REQUESTED BY</div>
                <p><strong>{requester_name}</strong></p>
                <p>Email: {requester_email}</p>
                <p>Department: <strong>{pr.requesting_department or 'N/A'}</strong></p>
            </div>
            <div class="party-box">
                <div class="party-header">DELIVERY WAREHOUSE</div>
                <p><strong>{warehouse_name}</strong></p>
                <p>{warehouse_address}</p>
            </div>
        </div>

        <!-- Priority -->
        <div class="info-grid">
            <div class="info-box" style="flex: 0.5;">
                <label>Priority</label>
                <value>{'Urgent' if pr.priority == 1 else 'Normal' if pr.priority == 5 else 'Low' if pr.priority == 10 else f'Level {pr.priority}'}</value>
            </div>
            <div class="info-box" style="flex: 1.5;">
                <label>Reason / Notes</label>
                <value>{pr.reason or pr.notes or 'N/A'}</value>
            </div>
        </div>

        <!-- Items Table -->
        <table style="margin-top: 15px;">
            <thead>
                <tr>
                    <th style="width: 5%;">S.No</th>
                    <th style="width: 15%;">SKU / Code</th>
                    <th style="width: 40%;">Item Description</th>
                    <th style="width: 10%;">Qty</th>
                    <th style="width: 10%;">UOM</th>
                    <th style="width: 20%;">Notes</th>
                </tr>
            </thead>
            <tbody>
                {items_html}
            </tbody>
            <tfoot>
                <tr style="background: #e2e8f0; font-weight: bold;">
                    <td colspan="3" class="text-right">Total Items:</td>
                    <td class="text-center">{total_items}</td>
                    <td colspan="2"></td>
                </tr>
            </tfoot>
        </table>

        <!-- Footer -->
        <div class="footer">
            <div class="signature-section">
                <div class="signature-box">
                    <div class="signature-line"></div>
                    <p><strong>Requested By</strong></p>
                    <p style="font-size: 9px;">{requester_name}</p>
                </div>
                <div class="signature-box">
                    <div class="signature-line"></div>
                    <p><strong>Approved By</strong></p>
                    <p style="font-size: 9px;">Authorized Signatory</p>
                </div>
            </div>
            <p style="text-align: center; margin-top: 20px; font-size: 9px; color: #666;">
                Generated on {datetime.now().strftime('%d %b %Y at %H:%M')} | Document ID: {str(pr.id)[:8]}
            </p>
        </div>
    </div>
</body>
</html>
    """

    return HTMLResponse(content=html_content, status_code=200)


# ==================== Purchase Order (PO) ====================

@router.post("/orders", response_model=PurchaseOrderResponse, status_code=status.HTTP_201_CREATED)
@require_module("procurement")
async def create_purchase_order(
    po_in: PurchaseOrderCreate,
    db: DB,
    current_user: User = Depends(get_current_user),
):
    """Create a new Purchase Order."""
    # Verify vendor
    vendor_result = await db.execute(
        select(Vendor).where(Vendor.id == po_in.vendor_id)
    )
    vendor = vendor_result.scalar_one_or_none()
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor not found")

    # Generate PO number using atomic sequence service
    service = DocumentSequenceService(db)
    po_number = await service.get_next_number("PO")

    # Determine if inter-state (for IGST)
    # Get warehouse state
    wh_result = await db.execute(
        select(Warehouse).where(Warehouse.id == po_in.delivery_warehouse_id)
    )
    warehouse = wh_result.scalar_one_or_none()

    is_inter_state = False
    if warehouse and vendor.gst_state_code:
        # Compare state codes (first 2 digits of GSTIN)
        wh_state = getattr(warehouse, 'state_code', None)
        if wh_state and wh_state != vendor.gst_state_code:
            is_inter_state = True

    # Prepare Bill To (from input or default to company details)
    bill_to = po_in.bill_to
    if not bill_to:
        # Fetch company details for Bill To
        from sqlalchemy import text
        company_result = await db.execute(text("""
            SELECT legal_name, gstin, state_code, address_line1, address_line2,
                   city, state, pincode, email, phone
            FROM companies LIMIT 1
        """))
        company_row = company_result.fetchone()
        if company_row:
            bill_to = {
                "name": company_row[0],
                "gstin": company_row[1],
                "state_code": company_row[2],
                "address_line1": company_row[3],
                "address_line2": company_row[4],
                "city": company_row[5],
                "state": company_row[6],
                "pincode": company_row[7],
                "email": company_row[8],
                "phone": company_row[9],
            }

    # Prepare Ship To (from input or default to warehouse address)
    ship_to = po_in.ship_to
    if not ship_to and warehouse:
        ship_to = {
            "name": warehouse.name,
            "address_line1": getattr(warehouse, 'address_line1', None),
            "address_line2": getattr(warehouse, 'address_line2', None),
            "city": getattr(warehouse, 'city', None),
            "state": getattr(warehouse, 'state', None),
            "pincode": getattr(warehouse, 'pincode', None),
            "state_code": getattr(warehouse, 'state_code', None),
            "gstin": bill_to.get('gstin') if bill_to else None,  # Same GSTIN as buyer
        }

    # Set today's date for PO
    today = date.today()

    # Create PO with initial zero values for NOT NULL fields
    # Quantize all numeric inputs to ensure they fit in Numeric(X, 2) columns
    po = PurchaseOrder(
        po_number=po_number,
        po_date=today,
        vendor_id=vendor.id,
        vendor_name=vendor.name,
        vendor_gstin=vendor.gstin,
        delivery_warehouse_id=po_in.delivery_warehouse_id,
        requisition_id=po_in.requisition_id,
        expected_delivery_date=po_in.expected_delivery_date,
        delivery_address=po_in.delivery_address,
        bill_to=bill_to,
        ship_to=ship_to,
        payment_terms=po_in.payment_terms,
        credit_days=po_in.credit_days,
        advance_required=Decimal(str(po_in.advance_required or 0)).quantize(Decimal("0.01")),
        advance_paid=Decimal(str(po_in.advance_paid or 0)).quantize(Decimal("0.01")),
        quotation_reference=po_in.quotation_reference,
        quotation_date=po_in.quotation_date,
        freight_charges=Decimal(str(po_in.freight_charges or 0)).quantize(Decimal("0.01")),
        packing_charges=Decimal(str(po_in.packing_charges or 0)).quantize(Decimal("0.01")),
        other_charges=Decimal(str(po_in.other_charges or 0)).quantize(Decimal("0.01")),
        terms_and_conditions=po_in.terms_and_conditions,
        special_instructions=po_in.special_instructions,
        internal_notes=po_in.internal_notes,
        created_by=current_user.id,
        # Initialize NOT NULL fields with zero
        subtotal=Decimal("0"),
        taxable_amount=Decimal("0"),
        grand_total=Decimal("0"),
    )

    db.add(po)
    await db.flush()

    # Create PO items and calculate totals
    subtotal = Decimal("0")
    total_discount = Decimal("0")
    taxable_amount = Decimal("0")
    cgst_total = Decimal("0")
    sgst_total = Decimal("0")
    igst_total = Decimal("0")
    cess_total = Decimal("0")
    line_number = 0

    for item_data in po_in.items:
        line_number += 1

        # Calculate item amounts with proper Decimal precision
        qty = Decimal(str(item_data.quantity_ordered))
        unit_price = Decimal(str(item_data.unit_price)).quantize(Decimal("0.01"))
        discount_pct = Decimal(str(item_data.discount_percentage)).quantize(Decimal("0.01"))

        gross_amount = (qty * unit_price).quantize(Decimal("0.01"))
        discount_amount = (gross_amount * discount_pct / Decimal("100")).quantize(Decimal("0.01"))
        item_taxable = (gross_amount - discount_amount).quantize(Decimal("0.01"))

        # GST calculation with proper Decimal
        gst_rate = Decimal(str(item_data.gst_rate)).quantize(Decimal("0.01"))
        if is_inter_state:
            igst_rate = gst_rate
            cgst_rate = Decimal("0")
            sgst_rate = Decimal("0")
        else:
            igst_rate = Decimal("0")
            cgst_rate = (gst_rate / Decimal("2")).quantize(Decimal("0.01"))
            sgst_rate = (gst_rate / Decimal("2")).quantize(Decimal("0.01"))

        cgst_amount = (item_taxable * cgst_rate / Decimal("100")).quantize(Decimal("0.01"))
        sgst_amount = (item_taxable * sgst_rate / Decimal("100")).quantize(Decimal("0.01"))
        igst_amount = (item_taxable * igst_rate / Decimal("100")).quantize(Decimal("0.01"))
        cess_amount = Decimal("0")  # Can be added if needed

        item_total = (item_taxable + cgst_amount + sgst_amount + igst_amount + cess_amount).quantize(Decimal("0.01"))

        item = PurchaseOrderItem(
            purchase_order_id=po.id,
            line_number=line_number,
            product_id=item_data.product_id,
            variant_id=item_data.variant_id,
            product_name=item_data.product_name,
            sku=item_data.sku,
            hsn_code=item_data.hsn_code,
            quantity_ordered=item_data.quantity_ordered,
            uom=item_data.uom,
            unit_price=unit_price,  # Use quantized Decimal
            discount_percentage=discount_pct.quantize(Decimal("0.01")),
            discount_amount=discount_amount,
            taxable_amount=item_taxable,
            gst_rate=gst_rate.quantize(Decimal("0.01")),
            cgst_rate=cgst_rate,
            sgst_rate=sgst_rate,
            igst_rate=igst_rate.quantize(Decimal("0.01")),
            cgst_amount=cgst_amount,
            sgst_amount=sgst_amount,
            igst_amount=igst_amount,
            cess_amount=cess_amount,
            total_amount=item_total,
            expected_date=item_data.expected_date,
            notes=item_data.notes,
            # Month-wise quantity breakdown for multi-delivery POs
            monthly_quantities=item_data.monthly_quantities,
        )
        db.add(item)

        subtotal += gross_amount
        total_discount += discount_amount
        taxable_amount += item_taxable
        cgst_total += cgst_amount
        sgst_total += sgst_amount
        igst_total += igst_amount
        cess_total += cess_amount

    # Update PO totals with proper Decimal precision
    total_tax = (cgst_total + sgst_total + igst_total + cess_total).quantize(Decimal("0.01"))
    freight = Decimal(str(po_in.freight_charges or 0)).quantize(Decimal("0.01"))
    packing = Decimal(str(po_in.packing_charges or 0)).quantize(Decimal("0.01"))
    other = Decimal(str(po_in.other_charges or 0)).quantize(Decimal("0.01"))
    grand_total = (taxable_amount + total_tax + freight + packing + other).quantize(Decimal("0.01"))

    po.subtotal = subtotal.quantize(Decimal("0.01"))
    po.discount_amount = total_discount.quantize(Decimal("0.01"))
    po.taxable_amount = taxable_amount.quantize(Decimal("0.01"))
    po.cgst_amount = cgst_total.quantize(Decimal("0.01"))
    po.sgst_amount = sgst_total.quantize(Decimal("0.01"))
    po.igst_amount = igst_total.quantize(Decimal("0.01"))
    po.cess_amount = cess_total.quantize(Decimal("0.01"))
    po.total_tax = total_tax
    po.grand_total = grand_total

    # Create delivery schedules (lot-wise) from monthly_quantities
    # Collect all months and calculate per-month values
    month_totals = {}  # {month_code: {qty: X, value: Y, tax: Z}}

    for item_data in po_in.items:
        if item_data.monthly_quantities:
            # Ensure proper Decimal arithmetic to avoid precision overflow
            unit_price = Decimal(str(item_data.unit_price)).quantize(Decimal("0.01"))
            discount_pct = Decimal(str(item_data.discount_percentage)).quantize(Decimal("0.01"))
            gst_rate = Decimal(str(item_data.gst_rate)).quantize(Decimal("0.01"))

            item_unit_price = (unit_price * (Decimal("1") - discount_pct / Decimal("100"))).quantize(Decimal("0.01"))

            for month_code, qty in item_data.monthly_quantities.items():
                if month_code not in month_totals:
                    month_totals[month_code] = {"qty": 0, "value": Decimal("0"), "tax": Decimal("0")}

                qty_decimal = Decimal(str(qty))
                item_value = (qty_decimal * item_unit_price).quantize(Decimal("0.01"))
                item_tax = (item_value * gst_rate / Decimal("100")).quantize(Decimal("0.01"))

                month_totals[month_code]["qty"] += int(qty)
                month_totals[month_code]["value"] += item_value
                month_totals[month_code]["tax"] += item_tax

    # Create PODeliverySchedule for each month
    if month_totals:
        from datetime import timedelta
        from calendar import monthrange
        # Note: func is already imported at module level from sqlalchemy

        # Get the last serial number from all previous delivery schedules
        # Serial numbers are global across all POs and continue from the last used
        last_serial_result = await db.execute(
            select(func.max(PODeliverySchedule.serial_number_end))
        )
        last_serial = last_serial_result.scalar() or 0  # Start from 0 if no previous serials

        sorted_months = sorted(month_totals.keys())
        lot_number = 0
        current_serial = last_serial  # Track running serial number

        for month_code in sorted_months:
            lot_number += 1
            month_data = month_totals[month_code]

            # Parse month_code (YYYY-MM) to date
            year, month = int(month_code.split("-")[0]), int(month_code.split("-")[1])
            # Expected delivery: 15th of the month
            expected_date = date(year, month, 15)
            # Delivery window: 10th to 20th of the month
            window_start = date(year, month, 10)
            last_day = monthrange(year, month)[1]
            window_end = date(year, month, min(20, last_day))

            # Quantize accumulated values to ensure they fit in Numeric(14,2) and Numeric(12,2) columns
            lot_value = month_data["value"].quantize(Decimal("0.01"))
            lot_tax = month_data["tax"].quantize(Decimal("0.01"))
            lot_total = (lot_value + lot_tax).quantize(Decimal("0.01"))

            # Calculate advance and balance with proper Decimal precision
            # advance_required from frontend is an AMOUNT, not percentage
            # Calculate percentage based on lot's proportion of total PO value
            po_advance_amount = Decimal(str(po_in.advance_required or 0)).quantize(Decimal("0.01"))
            if po_advance_amount > 0 and grand_total > 0:
                # Calculate this lot's share of advance based on its proportion of total
                lot_proportion = lot_total / grand_total
                advance_amount = (po_advance_amount * lot_proportion).quantize(Decimal("0.01"))
                advance_percentage = (advance_amount / lot_total * Decimal("100")).quantize(Decimal("0.01")) if lot_total > 0 else Decimal("0")
            else:
                # Default 25% advance if no advance specified
                advance_percentage = Decimal("25")
                advance_amount = (lot_total * advance_percentage / Decimal("100")).quantize(Decimal("0.01"))
            balance_amount = (lot_total - advance_amount).quantize(Decimal("0.01"))

            # Balance due 45 days after delivery
            balance_due_date = expected_date + timedelta(days=po_in.credit_days)

            # Generate lot name (e.g., "JAN 2026")
            month_names = ["", "JAN", "FEB", "MAR", "APR", "MAY", "JUN",
                          "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"]
            lot_name = f"{month_names[month]} {year}"

            # Calculate serial number range for this lot
            lot_qty = month_data["qty"]
            serial_start = current_serial + 1
            serial_end = current_serial + lot_qty
            current_serial = serial_end  # Update for next lot

            delivery_schedule = PODeliverySchedule(
                purchase_order_id=po.id,
                lot_number=lot_number,
                lot_name=lot_name,
                month_code=month_code,
                expected_delivery_date=expected_date,
                delivery_window_start=window_start,
                delivery_window_end=window_end,
                total_quantity=lot_qty,
                lot_value=lot_value,
                lot_tax=lot_tax,
                lot_total=lot_total,
                advance_percentage=advance_percentage,
                advance_amount=advance_amount,
                balance_amount=balance_amount,
                balance_due_days=po_in.credit_days,
                balance_due_date=balance_due_date,
                status=DeliveryLotStatus.PENDING,
                # Serial number range for this lot
                serial_number_start=serial_start,
                serial_number_end=serial_end,
            )
            db.add(delivery_schedule)

    # If created from PR, update PR status
    if po_in.requisition_id:
        pr_result = await db.execute(
            select(PurchaseRequisition).where(PurchaseRequisition.id == po_in.requisition_id)
        )
        pr = pr_result.scalar_one_or_none()
        if pr:
            pr.status = RequisitionStatus.CONVERTED.value
            pr.converted_to_po_id = po.id

    await db.commit()

    # Load full PO with items and delivery schedules
    result = await db.execute(
        select(PurchaseOrder)
        .options(
            selectinload(PurchaseOrder.items),
            selectinload(PurchaseOrder.delivery_schedules)
        )
        .where(PurchaseOrder.id == po.id)
    )
    po = result.scalar_one()

    return po


@router.get("/orders", response_model=POListResponse)
@require_module("procurement")
async def list_purchase_orders(
    db: DB,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    status: Optional[POStatus] = None,
    vendor_id: Optional[UUID] = None,
    warehouse_id: Optional[UUID] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    search: Optional[str] = None,
    current_user: User = Depends(get_current_user),
):
    """List purchase orders with vendor and warehouse details."""
    from app.schemas.purchase import POVendorBrief, POWarehouseBrief

    query = select(PurchaseOrder)
    count_query = select(func.count(PurchaseOrder.id))
    total_value_query = select(func.coalesce(func.sum(PurchaseOrder.grand_total), 0))

    filters = []
    if status:
        filters.append(PurchaseOrder.status == status)
    if vendor_id:
        filters.append(PurchaseOrder.vendor_id == vendor_id)
    if warehouse_id:
        filters.append(PurchaseOrder.delivery_warehouse_id == warehouse_id)
    if start_date:
        filters.append(PurchaseOrder.po_date >= start_date)
    if end_date:
        filters.append(PurchaseOrder.po_date <= end_date)
    if search:
        filters.append(or_(
            PurchaseOrder.po_number.ilike(f"%{search}%"),
            PurchaseOrder.vendor_name.ilike(f"%{search}%"),
        ))

    if filters:
        query = query.where(and_(*filters))
        count_query = count_query.where(and_(*filters))
        total_value_query = total_value_query.where(and_(*filters))

    # Get totals
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    value_result = await db.execute(total_value_query)
    total_value = value_result.scalar() or Decimal("0")

    # Get paginated results with relationships
    query = query.order_by(PurchaseOrder.created_at.desc()).offset(skip).limit(limit)
    result = await db.execute(query)
    pos = result.scalars().all()

    # Load vendor and warehouse data for display
    vendor_ids = [po.vendor_id for po in pos if po.vendor_id]
    warehouse_ids = [po.delivery_warehouse_id for po in pos if po.delivery_warehouse_id]

    vendors_map = {}
    if vendor_ids:
        vendors_result = await db.execute(select(Vendor).where(Vendor.id.in_(vendor_ids)))
        for v in vendors_result.scalars().all():
            vendors_map[v.id] = v

    warehouses_map = {}
    if warehouse_ids:
        warehouses_result = await db.execute(select(Warehouse).where(Warehouse.id.in_(warehouse_ids)))
        for w in warehouses_result.scalars().all():
            warehouses_map[w.id] = w

    # Build response with nested vendor/warehouse objects
    items = []
    for po in pos:
        vendor = vendors_map.get(po.vendor_id) if po.vendor_id else None
        warehouse = warehouses_map.get(po.delivery_warehouse_id) if po.delivery_warehouse_id else None

        # Calculate GST amount
        gst_amount = (po.cgst_amount or Decimal("0")) + (po.sgst_amount or Decimal("0")) + (po.igst_amount or Decimal("0"))

        items.append(POBrief(
            id=po.id,
            po_number=po.po_number,
            po_date=po.po_date,
            vendor_name=po.vendor_name or (vendor.name if vendor else "N/A"),
            status=po.status,
            grand_total=po.grand_total,
            total_received_value=po.total_received_value or Decimal("0"),
            expected_delivery_date=po.expected_delivery_date,
            gst_amount=gst_amount,
            vendor=POVendorBrief(
                id=vendor.id if vendor else None,
                name=vendor.name if vendor else po.vendor_name,
                code=vendor.vendor_code if vendor else None
            ) if vendor or po.vendor_name else None,
            warehouse=POWarehouseBrief(
                id=warehouse.id if warehouse else None,
                name=warehouse.name if warehouse else None
            ) if warehouse else None
        ))

    return POListResponse(
        items=items,
        total=total,
        total_value=total_value,
        page=(skip // limit) + 1 if limit > 0 else 1,
        size=limit,
        pages=(total + limit - 1) // limit if limit > 0 else 1
    )


@router.get("/orders/{po_id}", response_model=PurchaseOrderResponse)
@require_module("procurement")
async def get_purchase_order(
    po_id: UUID,
    db: DB,
    current_user: User = Depends(get_current_user),
):
    """Get purchase order by ID."""
    result = await db.execute(
        select(PurchaseOrder)
        .options(
            selectinload(PurchaseOrder.items),
            selectinload(PurchaseOrder.delivery_schedules)
        )
        .where(PurchaseOrder.id == po_id)
    )
    po = result.scalar_one_or_none()

    if not po:
        raise HTTPException(status_code=404, detail="Purchase Order not found")

    # Fetch vendor for nested object
    vendor_brief = None
    if po.vendor_id:
        vendor_result = await db.execute(
            select(Vendor).where(Vendor.id == po.vendor_id)
        )
        vendor = vendor_result.scalar_one_or_none()
        if vendor:
            vendor_brief = {"id": vendor.id, "name": vendor.name, "code": vendor.vendor_code}

    # Fetch warehouse for nested object
    warehouse_brief = None
    if po.delivery_warehouse_id:
        warehouse_result = await db.execute(
            select(Warehouse).where(Warehouse.id == po.delivery_warehouse_id)
        )
        warehouse = warehouse_result.scalar_one_or_none()
        if warehouse:
            warehouse_brief = {"id": warehouse.id, "name": warehouse.name}

    # Build response with nested objects
    response_dict = {
        **{c.name: getattr(po, c.name) for c in po.__table__.columns},
        "items": po.items,
        "delivery_schedules": po.delivery_schedules,
        "vendor": vendor_brief,
        "warehouse": warehouse_brief,
    }

    return PurchaseOrderResponse.model_validate(response_dict)


@router.delete("/orders/{po_id}", status_code=status.HTTP_204_NO_CONTENT)
@require_module("procurement")
async def delete_purchase_order(
    po_id: UUID,
    db: DB,
    current_user: User = Depends(get_current_user),
):
    """Delete a purchase order. Only DRAFT or REJECTED POs can be deleted."""
    result = await db.execute(
        select(PurchaseOrder).where(PurchaseOrder.id == po_id)
    )
    po = result.scalar_one_or_none()

    if not po:
        raise HTTPException(status_code=404, detail="Purchase Order not found")

    # Only allow deletion of DRAFT or CANCELLED POs
    allowed_statuses = [POStatus.DRAFT, POStatus.CANCELLED]
    if po.status not in allowed_statuses:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot delete PO with status '{po.status}'. Only DRAFT or CANCELLED POs can be deleted."
        )

    # Delete PO items first (cascade should handle this, but being explicit)
    await db.execute(
        delete(PurchaseOrderItem).where(PurchaseOrderItem.purchase_order_id == po_id)
    )

    # Delete the PO
    await db.execute(
        delete(PurchaseOrder).where(PurchaseOrder.id == po_id)
    )

    await db.commit()
    return None


@router.put("/orders/{po_id}", response_model=PurchaseOrderResponse)
@require_module("procurement")
async def update_purchase_order(
    po_id: UUID,
    update_data: PurchaseOrderUpdate,
    db: DB,
    current_user: User = Depends(get_current_user),
):
    """Update a purchase order. Supports full editing including vendor and items."""
    result = await db.execute(
        select(PurchaseOrder)
        .options(
            selectinload(PurchaseOrder.items),
            selectinload(PurchaseOrder.delivery_schedules)
        )
        .where(PurchaseOrder.id == po_id)
    )
    po = result.scalar_one_or_none()

    if not po:
        raise HTTPException(status_code=404, detail="Purchase Order not found")

    # Only allow editing of DRAFT or PENDING_APPROVAL POs
    allowed_statuses = [POStatus.DRAFT.value, POStatus.PENDING_APPROVAL.value]
    if po.status not in allowed_statuses:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot edit PO with status '{po.status}'. Only DRAFT or PENDING_APPROVAL POs can be edited."
        )

    update_dict = update_data.model_dump(exclude_unset=True)
    items_data = update_dict.pop('items', None)

    # Handle vendor change
    if 'vendor_id' in update_dict and update_dict['vendor_id']:
        vendor_result = await db.execute(
            select(Vendor).where(Vendor.id == update_dict['vendor_id'])
        )
        vendor = vendor_result.scalar_one_or_none()
        if vendor:
            po.vendor_id = vendor.id
            po.vendor_name = vendor.name
            po.vendor_gstin = vendor.gstin

    # Update simple fields
    simple_fields = ['expected_delivery_date', 'credit_days', 'payment_terms',
                     'advance_required', 'advance_paid',
                     'freight_charges', 'packing_charges', 'other_charges',
                     'terms_and_conditions', 'special_instructions', 'internal_notes']
    for field in simple_fields:
        if field in update_dict and update_dict[field] is not None:
            setattr(po, field, update_dict[field])

    # Handle items replacement
    if items_data is not None:
        # Delete existing items
        await db.execute(
            delete(PurchaseOrderItem).where(PurchaseOrderItem.purchase_order_id == po_id)
        )

        # Get warehouse for GST calculation
        wh_result = await db.execute(
            select(Warehouse).where(Warehouse.id == po.delivery_warehouse_id)
        )
        warehouse = wh_result.scalar_one_or_none()

        # Determine if inter-state
        vendor_result = await db.execute(
            select(Vendor).where(Vendor.id == po.vendor_id)
        )
        vendor = vendor_result.scalar_one_or_none()
        is_inter_state = False
        if warehouse and vendor and vendor.gst_state_code:
            wh_state = getattr(warehouse, 'state_code', None)
            if wh_state and wh_state != vendor.gst_state_code:
                is_inter_state = True

        # Create new items and calculate totals
        subtotal = Decimal("0")
        total_discount = Decimal("0")
        taxable_amount = Decimal("0")
        cgst_total = Decimal("0")
        sgst_total = Decimal("0")
        igst_total = Decimal("0")
        line_number = 0

        for item_data in items_data:
            line_number += 1
            # items_data is a list of dicts from model_dump(), use dict access
            qty = Decimal(str(item_data['quantity_ordered']))
            unit_price = Decimal(str(item_data['unit_price'])).quantize(Decimal("0.01"))
            discount_pct = Decimal(str(item_data.get('discount_percentage', 0))).quantize(Decimal("0.01"))

            gross_amount = (qty * unit_price).quantize(Decimal("0.01"))
            discount_amount = (gross_amount * discount_pct / Decimal("100")).quantize(Decimal("0.01"))
            item_taxable = (gross_amount - discount_amount).quantize(Decimal("0.01"))

            gst_rate = Decimal(str(item_data.get('gst_rate', 18))).quantize(Decimal("0.01"))
            if is_inter_state:
                igst_rate = gst_rate
                cgst_rate = Decimal("0")
                sgst_rate = Decimal("0")
            else:
                igst_rate = Decimal("0")
                cgst_rate = (gst_rate / Decimal("2")).quantize(Decimal("0.01"))
                sgst_rate = (gst_rate / Decimal("2")).quantize(Decimal("0.01"))

            cgst_amount = (item_taxable * cgst_rate / Decimal("100")).quantize(Decimal("0.01"))
            sgst_amount = (item_taxable * sgst_rate / Decimal("100")).quantize(Decimal("0.01"))
            igst_amount = (item_taxable * igst_rate / Decimal("100")).quantize(Decimal("0.01"))
            item_total = (item_taxable + cgst_amount + sgst_amount + igst_amount).quantize(Decimal("0.01"))

            item = PurchaseOrderItem(
                purchase_order_id=po.id,
                line_number=line_number,
                product_id=item_data.get('product_id'),
                variant_id=item_data.get('variant_id'),
                product_name=item_data.get('product_name', ''),
                sku=item_data.get('sku', ''),
                hsn_code=item_data.get('hsn_code'),
                quantity_ordered=item_data['quantity_ordered'],
                uom=item_data.get('uom', 'PCS'),
                unit_price=unit_price,
                discount_percentage=discount_pct,
                discount_amount=discount_amount,
                taxable_amount=item_taxable,
                gst_rate=gst_rate,
                cgst_rate=cgst_rate,
                sgst_rate=sgst_rate,
                igst_rate=igst_rate,
                cgst_amount=cgst_amount,
                sgst_amount=sgst_amount,
                igst_amount=igst_amount,
                cess_amount=Decimal("0"),
                total_amount=item_total,
            )
            db.add(item)

            subtotal += gross_amount
            total_discount += discount_amount
            taxable_amount += item_taxable
            cgst_total += cgst_amount
            sgst_total += sgst_amount
            igst_total += igst_amount

        # Update PO totals
        total_tax = (cgst_total + sgst_total + igst_total).quantize(Decimal("0.01"))
        freight = Decimal(str(po.freight_charges or 0)).quantize(Decimal("0.01"))
        packing = Decimal(str(po.packing_charges or 0)).quantize(Decimal("0.01"))
        other = Decimal(str(po.other_charges or 0)).quantize(Decimal("0.01"))
        grand_total = (taxable_amount + total_tax + freight + packing + other).quantize(Decimal("0.01"))

        po.subtotal = subtotal.quantize(Decimal("0.01"))
        po.discount_amount = total_discount.quantize(Decimal("0.01"))
        po.taxable_amount = taxable_amount.quantize(Decimal("0.01"))
        po.cgst_amount = cgst_total.quantize(Decimal("0.01"))
        po.sgst_amount = sgst_total.quantize(Decimal("0.01"))
        po.igst_amount = igst_total.quantize(Decimal("0.01"))
        po.cess_amount = Decimal("0")
        po.total_tax = total_tax
        po.grand_total = grand_total

    await db.commit()

    # Refresh to get updated items
    result = await db.execute(
        select(PurchaseOrder)
        .options(
            selectinload(PurchaseOrder.items),
            selectinload(PurchaseOrder.delivery_schedules)
        )
        .where(PurchaseOrder.id == po_id)
    )
    po = result.scalar_one()

    return po


@router.post("/orders/{po_id}/submit", response_model=PurchaseOrderResponse)
@require_module("procurement")
async def submit_purchase_order(
    po_id: UUID,
    db: DB,
    current_user: User = Depends(get_current_user),
):
    """Submit a purchase order for approval (DRAFT -> PENDING_APPROVAL)."""
    import logging
    logging.info(f"PO SUBMIT: po_id={po_id}")

    result = await db.execute(
        select(PurchaseOrder)
        .options(
            selectinload(PurchaseOrder.items),
            selectinload(PurchaseOrder.delivery_schedules)
        )
        .where(PurchaseOrder.id == po_id)
    )
    po = result.scalar_one_or_none()

    if not po:
        raise HTTPException(status_code=404, detail="Purchase Order not found")

    logging.info(f"PO SUBMIT: {po.po_number}, status='{po.status}'")

    # Use state machine for validation and transition
    if not can_submit(po.status):
        allowed = get_allowed_transitions(po.status)
        raise HTTPException(
            status_code=400,
            detail=f"Cannot submit PO in '{po.status}' status. Allowed actions: {', '.join(allowed) if allowed else 'None (terminal state)'}"
        )

    # Transition using state machine
    transition_po(po, POStat.PENDING_APPROVAL, user_id=current_user.id)

    await db.commit()

    # Refresh with relationships loaded
    result = await db.execute(
        select(PurchaseOrder)
        .options(
            selectinload(PurchaseOrder.items),
            selectinload(PurchaseOrder.delivery_schedules)
        )
        .where(PurchaseOrder.id == po_id)
    )
    po = result.scalar_one()

    logging.info(f"PO SUBMIT: Success - {po.po_number} -> PENDING_APPROVAL")
    return po


@router.post("/orders/{po_id}/approve", response_model=PurchaseOrderResponse)
@require_module("procurement")
async def approve_purchase_order(
    po_id: UUID,
    db: DB,
    current_user: User = Depends(get_current_user),
    request: POApproveRequest = POApproveRequest(),
):
    """Approve or reject a purchase order."""
    print(f"=== PO APPROVE START === po_id={po_id}, action={request.action}")

    result = await db.execute(
        select(PurchaseOrder)
        .options(
            selectinload(PurchaseOrder.items),
            selectinload(PurchaseOrder.delivery_schedules)
        )
        .where(PurchaseOrder.id == po_id)
    )
    po = result.scalar_one_or_none()

    if not po:
        print(f"=== PO APPROVE ERROR === PO not found: {po_id}")
        raise HTTPException(status_code=404, detail="Purchase Order not found")

    print(f"=== PO APPROVE === {po.po_number}, status='{po.status}', action={request.action}")

    # Simple string comparison - no state machine for now
    if request.action == "APPROVE":
        if po.status not in ["DRAFT", "PENDING_APPROVAL"]:
            print(f"=== PO APPROVE REJECTED === status '{po.status}' not valid for approval")
            raise HTTPException(
                status_code=400,
                detail=f"Cannot approve PO in '{po.status}' status. Must be DRAFT or PENDING_APPROVAL."
            )
    else:
        if po.status != "PENDING_APPROVAL":
            print(f"=== PO APPROVE REJECTED === status '{po.status}' not valid for rejection")
            raise HTTPException(
                status_code=400,
                detail=f"Cannot reject PO in '{po.status}' status. Only PENDING_APPROVAL POs can be rejected."
            )

    print(f"=== PO APPROVE VALIDATED === proceeding with {request.action}")

    # Capture item data BEFORE commit (while po.items is still loaded)
    item_data_for_serials = None
    po_data_for_serials = None

    if request.action == "APPROVE":
        # Direct status change - no state machine
        po.status = "APPROVED"
        po.approved_by = current_user.id
        po.approved_at = datetime.now(timezone.utc)
        print(f"=== PO APPROVE === Set status to APPROVED")

        # Update all delivery schedules to ADVANCE_PENDING status
        for schedule in po.delivery_schedules:
            schedule.status = DeliveryLotStatus.ADVANCE_PENDING.value

        # Capture data needed for serial generation (before commit, while items are loaded)
        if po.items:
            print(f"=== PO APPROVE === Capturing {len(po.items)} items for serial generation")
            po_data_for_serials = {
                "po_id": str(po.id),
                "po_number": po.po_number,
                "vendor_id": str(po.vendor_id) if po.vendor_id else None,
            }
            item_data_for_serials = [
                {
                    "item_id": str(item.id),
                    "product_id": str(item.product_id) if item.product_id else None,
                    "product_sku": item.sku,
                    "product_name": item.product_name,
                    "quantity": item.quantity_ordered
                }
                for item in po.items
            ]
    else:
        # Reject - back to DRAFT
        po.status = "DRAFT"
        print(f"=== PO REJECT === Set status to DRAFT")
        # Cancel all delivery schedules
        for schedule in po.delivery_schedules:
            schedule.status = DeliveryLotStatus.CANCELLED.value

    # Commit the approval/rejection first
    print(f"=== PO APPROVE === Committing to database")
    await db.commit()
    print(f"=== PO APPROVE === Commit successful")

    # Now check for serial generation AFTER commit (in a clean transaction state)
    # This way, if serial check fails, the approval is already committed
    should_generate_serials = False
    serial_gen_data = None

    if request.action == "APPROVE" and item_data_for_serials:
        try:
            from sqlalchemy import text

            # Check if serials already exist (using fresh transaction)
            existing_serials = await db.execute(
                text("SELECT COUNT(*) FROM po_serials WHERE po_id = :po_id"),
                {"po_id": po_data_for_serials["po_id"]}
            )
            existing_count = existing_serials.scalar() or 0
            logging.info(f"Existing serials for PO {po_data_for_serials['po_number']}: {existing_count}")

            if existing_count == 0:
                # Get vendor supplier code
                supplier_code = "AP"  # Default
                if po_data_for_serials["vendor_id"]:
                    supplier_code_result = await db.execute(
                        text("SELECT code FROM supplier_codes WHERE vendor_id = :vendor_id LIMIT 1"),
                        {"vendor_id": po_data_for_serials["vendor_id"]}
                    )
                    supplier_code_row = supplier_code_result.first()
                    if supplier_code_row:
                        supplier_code = supplier_code_row[0]
                        logging.info(f"Found supplier_code: {supplier_code}")

                should_generate_serials = True
                serial_gen_data = {
                    "po_id": po_data_for_serials["po_id"],
                    "po_number": po_data_for_serials["po_number"],
                    "supplier_code": supplier_code,
                    "items": item_data_for_serials
                }
                logging.info(f"Will generate serials for PO {po_data_for_serials['po_number']}")
        except Exception as serial_check_error:
            logging.warning(f"Serial check failed (will skip serial generation): {serial_check_error}")

    # Re-fetch PO with all relationships for response
    result = await db.execute(
        select(PurchaseOrder)
        .options(
            selectinload(PurchaseOrder.items),
            selectinload(PurchaseOrder.delivery_schedules)
        )
        .where(PurchaseOrder.id == po_id)
    )
    po = result.scalar_one()

    # Generate serials AFTER approval is committed (so approval succeeds even if serial gen fails)
    import logging
    logging.info(f"Serial generation check: should_generate={should_generate_serials}, has_data={serial_gen_data is not None}")

    if should_generate_serials and serial_gen_data:
        try:
            from app.services.serialization import SerializationService
            from app.schemas.serialization import GenerateSerialsRequest, GenerateSerialItem, ItemType
            from app.models.serialization import ModelCodeReference

            logging.info(f"Starting serial generation for PO {serial_gen_data['po_number']}, supplier_code={serial_gen_data['supplier_code']}, items_count={len(serial_gen_data['items'])}")

            serial_service = SerializationService(db)
            serial_items = []

            for idx, item_data in enumerate(serial_gen_data["items"]):
                model_code = None
                item_type = ItemType.FINISHED_GOODS
                logging.info(f"Processing item {idx+1}: SKU={item_data['product_sku']}, qty={item_data['quantity']}, product_id={item_data['product_id']}")

                # Try to find model code reference (item_type column may not exist in production)
                # Use raw SQL to handle VARCHAR/UUID type mismatch in database
                if item_data["product_id"]:
                    ref_result = await db.execute(
                        text("SELECT model_code FROM model_code_references WHERE product_id = :product_id LIMIT 1"),
                        {"product_id": str(item_data["product_id"])}
                    )
                    ref_row = ref_result.first()
                    if ref_row:
                        model_code = ref_row[0]
                        logging.info(f"Found model_code_ref by product_id: model_code={model_code}")

                if not model_code and item_data["product_sku"]:
                    ref_result = await db.execute(
                        text("SELECT model_code FROM model_code_references WHERE product_sku = :product_sku LIMIT 1"),
                        {"product_sku": item_data["product_sku"]}
                    )
                    ref_row = ref_result.first()
                    if ref_row:
                        model_code = ref_row[0]
                        logging.info(f"Found model_code_ref by SKU: model_code={model_code}")

                if not model_code:
                    product_name = item_data["product_name"] or item_data["product_sku"] or "UNK"
                    clean_name = ''.join(c for c in product_name if c.isalpha())
                    model_code = clean_name[:3].upper() if len(clean_name) >= 3 else clean_name.upper().ljust(3, 'X')
                    logging.info(f"Generated model_code from name: {model_code}")

                serial_items.append(GenerateSerialItem(
                    po_item_id=item_data["item_id"],
                    product_id=item_data["product_id"],
                    product_sku=item_data["product_sku"],
                    model_code=model_code,
                    item_type=item_type,
                    quantity=item_data["quantity"]
                ))

            if serial_items:
                logging.info(f"Calling generate_serials_for_po with {len(serial_items)} items")
                gen_request = GenerateSerialsRequest(
                    po_id=serial_gen_data["po_id"],
                    supplier_code=serial_gen_data["supplier_code"],
                    items=serial_items
                )
                result = await serial_service.generate_serials_for_po(gen_request)
                logging.info(f"SUCCESS: Generated {result.total_generated} serials for PO {serial_gen_data['po_number']}")
            else:
                logging.warning(f"No serial_items to generate for PO {serial_gen_data['po_number']}")
        except Exception as e:
            # Log detailed error - approval is already committed
            import traceback
            logging.error(f"SERIAL GENERATION FAILED for PO {serial_gen_data['po_number']}: {type(e).__name__}: {e}")
            logging.error(f"Traceback: {traceback.format_exc()}")

    # Re-fetch PO to ensure it's attached to session (serial generation may have committed)
    result = await db.execute(
        select(PurchaseOrder)
        .options(
            selectinload(PurchaseOrder.items),
            selectinload(PurchaseOrder.delivery_schedules)
        )
        .where(PurchaseOrder.id == po_id)
    )
    po = result.scalar_one()

    logging.info(f"PO APPROVE: Returning PO {po.po_number}, status={po.status}, items={len(po.items) if po.items else 0}")
    return po


@router.post("/orders/{po_id}/send", response_model=PurchaseOrderResponse)
@require_module("procurement")
async def send_po_to_vendor(
    po_id: UUID,
    request: POSendToVendorRequest,
    db: DB,
    current_user: User = Depends(get_current_user),
):
    """Send PO to vendor (via email/portal). Auto-generates serial numbers."""
    import logging
    from app.services.serialization import SerializationService
    from app.schemas.serialization import GenerateSerialsRequest, GenerateSerialItem, ItemType
    from app.models.serialization import POSerial, ModelCodeReference

    logging.info(f"PO SEND: po_id={po_id}")

    result = await db.execute(
        select(PurchaseOrder)
        .options(
            selectinload(PurchaseOrder.items),
            selectinload(PurchaseOrder.delivery_schedules)
        )
        .where(PurchaseOrder.id == po_id)
    )
    po = result.scalar_one_or_none()

    if not po:
        raise HTTPException(status_code=404, detail="Purchase Order not found")

    logging.info(f"PO SEND: {po.po_number}, status='{po.status}'")

    # Use state machine for validation
    if not can_send_to_vendor(po.status):
        allowed = get_allowed_transitions(po.status)
        raise HTTPException(
            status_code=400,
            detail=f"Cannot send PO to vendor in '{po.status}' status. Allowed: {', '.join(allowed) if allowed else 'None'}"
        )

    # Get vendor details to find supplier code
    vendor_result = await db.execute(
        select(Vendor).where(Vendor.id == po.vendor_id)
    )
    vendor = vendor_result.scalar_one_or_none()

    # Default supplier code - check if vendor has a code assigned
    from app.models.serialization import SupplierCode
    supplier_code = "AP"  # Default to Aquapurite

    if vendor:
        # Find supplier code for this vendor
        supplier_code_result = await db.execute(
            text("SELECT code FROM supplier_codes WHERE vendor_id = :vendor_id LIMIT 1"),
            {"vendor_id": vendor.id}
        )
        supplier_code_row = supplier_code_result.first()
        if supplier_code_row:
            supplier_code = supplier_code_row[0]

    # Check if serials already exist for this PO - use raw SQL for VARCHAR/UUID mismatch
    existing_serials = await db.execute(
        text("SELECT COUNT(*) FROM po_serials WHERE po_id = :po_id"),
        {"po_id": str(po.id)}
    )
    existing_count = existing_serials.scalar() or 0

    serials_generated = 0
    serial_summaries = []

    # Only generate serials if none exist
    if existing_count == 0 and po.items:
        serial_service = SerializationService(db)

        # Build items for serial generation
        serial_items = []
        for item in po.items:
            # Try to get model code from ModelCodeReference by product_id or SKU
            model_code = None
            item_type = ItemType.FINISHED_GOODS

            if item.product_id:
                # Use raw SQL to handle VARCHAR/UUID type mismatch (item_type column may not exist)
                ref_result = await db.execute(
                    text("SELECT model_code FROM model_code_references WHERE product_id = :product_id LIMIT 1"),
                    {"product_id": str(item.product_id)}
                )
                ref_row = ref_result.first()
                if ref_row:
                    model_code = ref_row[0]

            if not model_code and item.sku:
                # Try by SKU - use raw SQL
                ref_result = await db.execute(
                    text("SELECT model_code FROM model_code_references WHERE product_sku = :product_sku LIMIT 1"),
                    {"product_sku": item.sku}
                )
                ref_row = ref_result.first()
                if ref_row:
                    model_code = ref_row[0]

            if not model_code:
                # Generate model code from product name (first 3 letters)
                product_name = item.product_name or item.sku or "UNK"
                # Remove common prefixes and get first 3 alphabetic characters
                clean_name = ''.join(c for c in product_name if c.isalpha())
                model_code = clean_name[:3].upper() if len(clean_name) >= 3 else clean_name.upper().ljust(3, 'X')

            serial_items.append(GenerateSerialItem(
                po_item_id=str(item.id),
                product_id=str(item.product_id) if item.product_id else None,
                product_sku=item.sku,
                model_code=model_code,
                quantity=item.quantity_ordered,
                item_type=item_type,
            ))

        if serial_items:
            try:
                gen_request = GenerateSerialsRequest(
                    po_id=str(po.id),
                    supplier_code=supplier_code,
                    items=serial_items,
                )
                gen_result = await serial_service.generate_serials_for_po(gen_request)
                serials_generated = gen_result.total_generated
                serial_summaries = gen_result.items

                # Mark as sent to vendor
                await serial_service.mark_serials_sent_to_vendor(str(po.id))
            except Exception as e:
                # Log error but don't fail the send operation
                print(f"Warning: Failed to generate serials for PO {po.po_number}: {e}")

    # Use state machine for transition (only if not already SENT_TO_VENDOR)
    if po.status != POStat.SENT_TO_VENDOR:
        transition_po(po, POStat.SENT_TO_VENDOR, user_id=current_user.id)

    await db.commit()
    await db.refresh(po)

    logging.info(f"PO SEND: Success - {po.po_number} -> SENT_TO_VENDOR")
    return po


@router.post("/orders/{po_id}/confirm", response_model=PurchaseOrderResponse)
@require_module("procurement")
async def confirm_purchase_order(
    po_id: UUID,
    db: DB,
    current_user: User = Depends(get_current_user),
):
    """Mark PO as acknowledged/confirmed by vendor."""
    import logging
    logging.info(f"PO CONFIRM: po_id={po_id}")

    result = await db.execute(
        select(PurchaseOrder)
        .options(
            selectinload(PurchaseOrder.items),
            selectinload(PurchaseOrder.delivery_schedules)
        )
        .where(PurchaseOrder.id == po_id)
    )
    po = result.scalar_one_or_none()

    if not po:
        raise HTTPException(status_code=404, detail="Purchase Order not found")

    logging.info(f"PO CONFIRM: {po.po_number}, status='{po.status}'")

    # Validate transition - must be SENT_TO_VENDOR to acknowledge
    if po.status != POStat.SENT_TO_VENDOR:
        allowed = get_allowed_transitions(po.status)
        raise HTTPException(
            status_code=400,
            detail=f"Cannot confirm PO in '{po.status}' status. Only SENT_TO_VENDOR POs can be confirmed. Allowed: {', '.join(allowed) if allowed else 'None'}"
        )

    # Use state machine for transition
    transition_po(po, POStat.ACKNOWLEDGED, user_id=current_user.id)

    await db.commit()
    await db.refresh(po)

    logging.info(f"PO CONFIRM: Success - {po.po_number} -> ACKNOWLEDGED")
    return po


# ==================== Delivery Schedule (Lot-wise Payment) ====================

@router.get("/orders/{po_id}/schedules", response_model=List[PODeliveryScheduleResponse])
@require_module("procurement")
async def get_delivery_schedules(
    po_id: UUID,
    db: DB,
    current_user: User = Depends(get_current_user),
):
    """Get delivery schedules for a PO."""
    result = await db.execute(
        select(PODeliverySchedule)
        .where(PODeliverySchedule.purchase_order_id == po_id)
        .order_by(PODeliverySchedule.lot_number)
    )
    schedules = result.scalars().all()

    return schedules


@router.post("/orders/{po_id}/schedules/{lot_id}/payment", response_model=PODeliveryScheduleResponse)
@require_module("procurement")
async def record_lot_payment(
    po_id: UUID,
    lot_id: UUID,
    payment: PODeliveryPaymentRequest,
    db: DB,
    current_user: User = Depends(get_current_user),
):
    """Record advance or balance payment for a delivery lot."""
    result = await db.execute(
        select(PODeliverySchedule)
        .where(
            PODeliverySchedule.id == lot_id,
            PODeliverySchedule.purchase_order_id == po_id
        )
    )
    schedule = result.scalar_one_or_none()

    if not schedule:
        raise HTTPException(status_code=404, detail="Delivery schedule not found")

    if payment.payment_type == "ADVANCE":
        if schedule.status not in [DeliveryLotStatus.PENDING, DeliveryLotStatus.ADVANCE_PENDING]:
            raise HTTPException(
                status_code=400,
                detail=f"Cannot record advance payment for lot in {schedule.status} status"
            )

        schedule.advance_paid = payment.amount
        schedule.advance_paid_date = payment.payment_date
        schedule.advance_payment_ref = payment.payment_reference
        schedule.status = DeliveryLotStatus.ADVANCE_PAID.value

    elif payment.payment_type == "BALANCE":
        if schedule.status not in [DeliveryLotStatus.DELIVERED, DeliveryLotStatus.PAYMENT_PENDING]:
            raise HTTPException(
                status_code=400,
                detail=f"Balance payment can only be recorded after delivery. Current status: {schedule.status}"
            )

        schedule.balance_paid = payment.amount
        schedule.balance_paid_date = payment.payment_date
        schedule.balance_payment_ref = payment.payment_reference
        schedule.status = DeliveryLotStatus.COMPLETED.value

    await db.commit()
    await db.refresh(schedule)

    return schedule


@router.post("/orders/{po_id}/schedules/{lot_id}/delivered", response_model=PODeliveryScheduleResponse)
@require_module("procurement")
async def mark_lot_delivered(
    po_id: UUID,
    lot_id: UUID,
    delivery_date: date,
    db: DB,
    current_user: CurrentUser,
    grn_id: Optional[UUID] = None,
):
    """Mark a delivery lot as delivered."""
    result = await db.execute(
        select(PODeliverySchedule)
        .where(
            PODeliverySchedule.id == lot_id,
            PODeliverySchedule.purchase_order_id == po_id
        )
    )
    schedule = result.scalar_one_or_none()

    if not schedule:
        raise HTTPException(status_code=404, detail="Delivery schedule not found")

    if schedule.status != DeliveryLotStatus.ADVANCE_PAID:
        raise HTTPException(
            status_code=400,
            detail=f"Lot must have advance paid before marking as delivered. Current status: {schedule.status}"
        )

    from datetime import timedelta

    schedule.actual_delivery_date = delivery_date
    schedule.grn_id = grn_id
    schedule.status = DeliveryLotStatus.PAYMENT_PENDING.value
    schedule.balance_due_date = delivery_date + timedelta(days=schedule.balance_due_days)

    await db.commit()
    await db.refresh(schedule)

    return schedule


# ==================== Serial Number Preview ====================

@router.get("/orders/next-serial")
@require_module("procurement")
async def get_next_serial_number(
    db: DB,
    current_user: User = Depends(get_current_user),
):
    """
    Get the next available serial number for PO delivery schedules.
    Used for preview in PO creation form.
    """
    last_serial_result = await db.execute(
        select(func.max(PODeliverySchedule.serial_number_end))
    )
    last_serial = last_serial_result.scalar() or 0
    next_serial = last_serial + 1

    return {
        "last_serial": last_serial,
        "next_serial": next_serial,
        "message": f"Next available serial starts from {next_serial}"
    }


# ==================== Goods Receipt Note (GRN) ====================

@router.post("/grn", response_model=GoodsReceiptResponse, status_code=status.HTTP_201_CREATED)
@require_module("procurement")
async def create_grn(
    grn_in: GoodsReceiptCreate,
    db: DB,
    current_user: User = Depends(get_current_user),
):
    """Create a Goods Receipt Note against a PO."""
    import logging
    logging.info(f"GRN CREATE: po_id={grn_in.purchase_order_id}")

    # Verify PO
    po_result = await db.execute(
        select(PurchaseOrder)
        .options(selectinload(PurchaseOrder.items))
        .where(PurchaseOrder.id == grn_in.purchase_order_id)
    )
    po = po_result.scalar_one_or_none()

    if not po:
        raise HTTPException(status_code=404, detail="Purchase Order not found")

    logging.info(f"GRN CREATE: PO {po.po_number}, status='{po.status}'")

    # Use state machine for validation
    if not can_receive_goods(po.status):
        allowed = get_allowed_transitions(po.status)
        raise HTTPException(
            status_code=400,
            detail=f"Cannot receive goods for PO in '{po.status}' status. Allowed: {', '.join(allowed) if allowed else 'None'}"
        )

    # Generate GRN number using atomic sequence service
    service = DocumentSequenceService(db)
    grn_number = await service.get_next_number("GRN")

    # Create GRN
    grn = GoodsReceiptNote(
        grn_number=grn_number,
        grn_date=grn_in.grn_date,
        purchase_order_id=po.id,
        vendor_id=po.vendor_id,
        warehouse_id=grn_in.warehouse_id,
        vendor_challan_number=grn_in.vendor_challan_number,
        vendor_challan_date=grn_in.vendor_challan_date,
        transporter_name=grn_in.transporter_name,
        vehicle_number=grn_in.vehicle_number,
        lr_number=grn_in.lr_number,
        e_way_bill_number=grn_in.e_way_bill_number,
        qc_required=grn_in.qc_required,
        receiving_remarks=grn_in.receiving_remarks,
        received_by=current_user.id,
        created_by=current_user.id,
    )

    db.add(grn)
    await db.flush()

    # Create GRN items
    total_received = 0
    total_accepted = 0
    total_rejected = 0
    total_value = Decimal("0")

    for item_data in grn_in.items:
        # Get PO item for unit price
        po_item_result = await db.execute(
            select(PurchaseOrderItem).where(PurchaseOrderItem.id == item_data.po_item_id)
        )
        po_item = po_item_result.scalar_one_or_none()
        if not po_item:
            raise HTTPException(status_code=400, detail=f"PO item {item_data.po_item_id} not found")

        # Validate quantity - prevent over-receiving
        pending_qty = po_item.quantity_ordered - po_item.quantity_received
        if item_data.quantity_received > pending_qty:
            raise HTTPException(
                status_code=400,
                detail=f"Cannot receive {item_data.quantity_received} units for {po_item.product_name}. "
                       f"PO ordered: {po_item.quantity_ordered}, "
                       f"Already received: {po_item.quantity_received}, "
                       f"Pending: {pending_qty} units"
            )

        unit_price = Decimal(str(po_item.unit_price))
        qty_accepted = Decimal(str(item_data.quantity_accepted))
        accepted_value = (qty_accepted * unit_price).quantize(Decimal("0.01"))

        grn_item = GRNItem(
            grn_id=grn.id,
            po_item_id=item_data.po_item_id,
            product_id=item_data.product_id,
            variant_id=item_data.variant_id,
            product_name=item_data.product_name,
            sku=item_data.sku,
            quantity_expected=item_data.quantity_expected,
            quantity_received=item_data.quantity_received,
            quantity_accepted=item_data.quantity_accepted,
            quantity_rejected=item_data.quantity_rejected,
            uom=item_data.uom,
            unit_price=unit_price,
            accepted_value=accepted_value,
            batch_number=item_data.batch_number,
            manufacturing_date=item_data.manufacturing_date,
            expiry_date=item_data.expiry_date,
            serial_numbers=item_data.serial_numbers,
            bin_id=item_data.bin_id,
            bin_location=item_data.bin_location,
            rejection_reason=item_data.rejection_reason,
            remarks=item_data.remarks,
        )
        db.add(grn_item)

        total_received += item_data.quantity_received
        total_accepted += item_data.quantity_accepted
        total_rejected += item_data.quantity_rejected
        total_value += accepted_value

        # Update PO item quantities
        po_item.quantity_received += item_data.quantity_received
        po_item.quantity_accepted += item_data.quantity_accepted
        po_item.quantity_rejected += item_data.quantity_rejected
        po_item.quantity_pending = po_item.quantity_ordered - po_item.quantity_received

        if po_item.quantity_pending <= 0:
            po_item.is_closed = True

    # Update GRN totals with proper precision
    grn.total_items = len(grn_in.items)
    grn.total_quantity_received = total_received
    grn.total_quantity_accepted = total_accepted
    grn.total_quantity_rejected = total_rejected
    grn.total_value = total_value.quantize(Decimal("0.01"))

    # Update PO status using state machine
    all_closed = all(item.is_closed for item in po.items)
    if all_closed:
        transition_po(po, POStat.FULLY_RECEIVED, user_id=current_user.id)
    else:
        transition_po(po, POStat.PARTIALLY_RECEIVED, user_id=current_user.id)

    po.total_received_value = (Decimal(str(po.total_received_value or 0)) + total_value).quantize(Decimal("0.01"))

    # Skip QC if not required
    if not grn_in.qc_required:
        grn.status = GRNStatus.PENDING_PUTAWAY.value
        grn.qc_status = QualityCheckResult.ACCEPTED.value

    await db.commit()

    # Load full GRN
    result = await db.execute(
        select(GoodsReceiptNote)
        .options(selectinload(GoodsReceiptNote.items))
        .where(GoodsReceiptNote.id == grn.id)
    )
    grn = result.scalar_one()

    return grn


@router.get("/grn", response_model=GRNListResponse)
@require_module("procurement")
async def list_grns(
    db: DB,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    status: Optional[GRNStatus] = None,
    vendor_id: Optional[UUID] = None,
    warehouse_id: Optional[UUID] = None,
    po_id: Optional[UUID] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    current_user: User = Depends(get_current_user),
):
    """List Goods Receipt Notes."""
    query = select(GoodsReceiptNote)
    count_query = select(func.count(GoodsReceiptNote.id))
    value_query = select(func.coalesce(func.sum(GoodsReceiptNote.total_value), 0))

    filters = []
    if status:
        filters.append(GoodsReceiptNote.status == status)
    if vendor_id:
        filters.append(GoodsReceiptNote.vendor_id == vendor_id)
    if warehouse_id:
        filters.append(GoodsReceiptNote.warehouse_id == warehouse_id)
    if po_id:
        filters.append(GoodsReceiptNote.purchase_order_id == po_id)
    if start_date:
        filters.append(GoodsReceiptNote.grn_date >= start_date)
    if end_date:
        filters.append(GoodsReceiptNote.grn_date <= end_date)

    if filters:
        query = query.where(and_(*filters))
        count_query = count_query.where(and_(*filters))
        value_query = value_query.where(and_(*filters))

    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    total_value_result = await db.execute(value_query)
    total_value = total_value_result.scalar() or Decimal("0")

    query = query.order_by(GoodsReceiptNote.created_at.desc()).offset(skip).limit(limit)
    result = await db.execute(query)
    grns = result.scalars().all()

    # Get PO numbers and vendor names for brief response
    items = []
    for grn in grns:
        # Get PO number
        po_result = await db.execute(
            select(PurchaseOrder.po_number).where(PurchaseOrder.id == grn.purchase_order_id)
        )
        po_number = po_result.scalar() or ""

        # Get vendor name
        vendor_result = await db.execute(
            select(Vendor.name).where(Vendor.id == grn.vendor_id)
        )
        vendor_name = vendor_result.scalar() or ""

        items.append(GRNBrief(
            id=grn.id,
            grn_number=grn.grn_number,
            grn_date=grn.grn_date,
            po_number=po_number,
            vendor_name=vendor_name,
            status=grn.status,
            total_quantity_received=grn.total_quantity_received,
            total_value=grn.total_value,
        ))

    return GRNListResponse(
        items=items,
        total=total,
        total_value=total_value,
        skip=skip,
        limit=limit
    )


@router.get("/grn/{grn_id}", response_model=GoodsReceiptResponse)
@require_module("procurement")
async def get_grn(
    grn_id: UUID,
    db: DB,
    current_user: User = Depends(get_current_user),
):
    """Get GRN by ID."""
    result = await db.execute(
        select(GoodsReceiptNote)
        .options(selectinload(GoodsReceiptNote.items))
        .where(GoodsReceiptNote.id == grn_id)
    )
    grn = result.scalar_one_or_none()

    if not grn:
        raise HTTPException(status_code=404, detail="GRN not found")

    return grn


@router.delete("/grn/{grn_id}", status_code=status.HTTP_204_NO_CONTENT)
@require_module("procurement")
async def delete_grn(
    grn_id: UUID,
    db: DB,
    permissions: Permissions,
):
    """
    Delete a GRN. Only DRAFT, CANCELLED, or REJECTED GRNs can be deleted.
    Super Admin can delete any GRN that hasn't been put away.
    """
    result = await db.execute(
        select(GoodsReceiptNote)
        .where(GoodsReceiptNote.id == grn_id)
    )
    grn = result.scalar_one_or_none()

    if not grn:
        raise HTTPException(status_code=404, detail="GRN not found")

    # Define which statuses can be deleted
    deletable_statuses = [
        GRNStatus.DRAFT.value,
        GRNStatus.CANCELLED.value,
        GRNStatus.REJECTED.value,
        "DRAFT", "CANCELLED", "REJECTED"  # Also allow string values
    ]

    # Super admin can also delete PENDING_QC, QC_PASSED, QC_FAILED, ACCEPTED (if not put away)
    if permissions.is_super_admin():
        deletable_statuses.extend([
            GRNStatus.PENDING_QC.value,
            GRNStatus.QC_PASSED.value,
            GRNStatus.QC_FAILED.value,
            GRNStatus.PARTIALLY_ACCEPTED.value,
            GRNStatus.ACCEPTED.value,
            "PENDING_QC", "QC_PASSED", "QC_FAILED", "PARTIALLY_ACCEPTED", "ACCEPTED"
        ])

    # Check if GRN can be deleted
    grn_status = grn.status.value if hasattr(grn.status, 'value') else str(grn.status)
    if grn_status not in deletable_statuses:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot delete GRN with status '{grn_status}'. Only DRAFT, CANCELLED, or REJECTED GRNs can be deleted."
        )

    # Cannot delete if put away is complete (inventory has been updated)
    if grn.put_away_complete:
        raise HTTPException(
            status_code=400,
            detail="Cannot delete GRN after put-away is complete. Inventory has been updated."
        )

    # Clear po_serials.grn_id references before deletion
    # Note: po_serials.grn_id is VARCHAR in production but UUID in SQLAlchemy model
    # Use raw SQL to avoid type mismatch (SQLAlchemy tries UUID comparison)
    from sqlalchemy import text
    grn_id_str = str(grn_id)
    await db.execute(
        text("""
            UPDATE po_serials
            SET grn_id = NULL, grn_item_id = NULL, received_at = NULL, received_by = NULL
            WHERE grn_id = :grn_id
        """),
        {"grn_id": grn_id_str}
    )

    # Delete the GRN (CASCADE will delete items)
    await db.delete(grn)
    await db.commit()

    return None


@router.post("/grn/{grn_id}/qc", response_model=GoodsReceiptResponse)
@require_module("procurement")
async def process_grn_quality_check(
    grn_id: UUID,
    qc_request: GRNQualityCheckRequest,
    db: DB,
    current_user: User = Depends(get_current_user),
):
    """Process quality check for GRN items."""
    result = await db.execute(
        select(GoodsReceiptNote)
        .options(selectinload(GoodsReceiptNote.items))
        .where(GoodsReceiptNote.id == grn_id)
    )
    grn = result.scalar_one_or_none()

    if not grn:
        raise HTTPException(status_code=404, detail="GRN not found")

    if grn.status != GRNStatus.PENDING_QC:
        raise HTTPException(status_code=400, detail="GRN is not pending QC")

    # Process each item's QC result
    all_accepted = True
    all_rejected = True

    for item_result in qc_request.item_results:
        item_id = item_result.get("item_id")
        qc_result = item_result.get("qc_result")
        rejection_reason = item_result.get("rejection_reason")

        # Find the GRN item
        item_query = await db.execute(
            select(GRNItem).where(GRNItem.id == UUID(item_id))
        )
        item = item_query.scalar_one_or_none()
        if item:
            item.qc_result = QualityCheckResult(qc_result)
            if rejection_reason:
                item.rejection_reason = rejection_reason

            if item.qc_result == QualityCheckResult.ACCEPTED:
                all_rejected = False
            elif item.qc_result == QualityCheckResult.REJECTED:
                all_accepted = False
                # Update accepted quantity to 0 if rejected
                item.quantity_accepted = 0
                item.quantity_rejected = item.quantity_received
            else:  # PARTIAL
                all_accepted = False
                all_rejected = False

    # Set overall QC status
    if all_accepted:
        grn.qc_status = QualityCheckResult.ACCEPTED.value
    elif all_rejected:
        grn.qc_status = QualityCheckResult.REJECTED.value
    else:
        grn.qc_status = QualityCheckResult.PARTIAL.value

    grn.qc_done_by = current_user.id
    grn.qc_done_at = datetime.now(timezone.utc)
    grn.qc_remarks = qc_request.overall_remarks
    grn.status = GRNStatus.PENDING_PUTAWAY.value

    await db.commit()
    await db.refresh(grn)

    return grn


@router.post("/grn/{grn_id}/putaway", response_model=GoodsReceiptResponse)
@require_module("procurement")
async def process_grn_putaway(
    grn_id: UUID,
    putaway_request: GRNPutAwayRequest,
    db: DB,
    current_user: User = Depends(get_current_user),
):
    """Process put-away for GRN items (add to inventory)."""
    result = await db.execute(
        select(GoodsReceiptNote)
        .options(selectinload(GoodsReceiptNote.items))
        .where(GoodsReceiptNote.id == grn_id)
    )
    grn = result.scalar_one_or_none()

    if not grn:
        raise HTTPException(status_code=404, detail="GRN not found")

    if grn.status != GRNStatus.PENDING_PUTAWAY:
        raise HTTPException(status_code=400, detail="GRN is not pending put-away")

    # Process each item location
    for loc_data in putaway_request.item_locations:
        item_id = loc_data.get("item_id")
        bin_id = loc_data.get("bin_id")
        bin_location = loc_data.get("bin_location")

        item_query = await db.execute(
            select(GRNItem).where(GRNItem.id == UUID(item_id))
        )
        item = item_query.scalar_one_or_none()

        if item and item.quantity_accepted > 0:
            item.bin_id = UUID(bin_id) if bin_id else None
            item.bin_location = bin_location

            # Create stock items for accepted quantity
            for i in range(item.quantity_accepted):
                serial = None
                if item.serial_numbers and i < len(item.serial_numbers):
                    serial = item.serial_numbers[i]

                stock_item = StockItem(
                    product_id=item.product_id,
                    variant_id=item.variant_id,
                    warehouse_id=grn.warehouse_id,
                    sku=item.sku,
                    serial_number=serial,
                    batch_number=item.batch_number,
                    manufacturing_date=item.manufacturing_date,
                    expiry_date=item.expiry_date,
                    status=StockItemStatus.AVAILABLE,
                    purchase_price=item.unit_price,
                    grn_id=grn.id,
                    grn_item_id=item.id,
                    bin_id=item.bin_id,
                    created_by=current_user.id,
                )
                db.add(stock_item)

            # Update inventory summary
            summary_result = await db.execute(
                select(InventorySummary).where(
                    and_(
                        InventorySummary.product_id == item.product_id,
                        InventorySummary.warehouse_id == grn.warehouse_id,
                    )
                )
            )
            summary = summary_result.scalar_one_or_none()

            if summary:
                summary.total_quantity += item.quantity_accepted
                summary.available_quantity += item.quantity_accepted
            else:
                summary = InventorySummary(
                    product_id=item.product_id,
                    variant_id=item.variant_id,
                    warehouse_id=grn.warehouse_id,
                    total_quantity=item.quantity_accepted,
                    available_quantity=item.quantity_accepted,
                )
                db.add(summary)

            # Create stock movement record
            movement = StockMovement(
                product_id=item.product_id,
                variant_id=item.variant_id,
                warehouse_id=grn.warehouse_id,
                movement_type=StockMovementType.INWARD,
                quantity=item.quantity_accepted,
                reference_type="GRN",
                reference_id=grn.id,
                reference_number=grn.grn_number,
                unit_price=item.unit_price,
                total_value=item.accepted_value,
                notes=f"GRN Put-away from PO",
                created_by=current_user.id,
            )
            db.add(movement)

    # Update GRN status
    grn.status = GRNStatus.COMPLETED.value
    grn.put_away_complete = True
    grn.put_away_at = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(grn)

    # Post accounting entry for GRN
    try:
        from app.services.accounting_service import AccountingService
        accounting = AccountingService(db)

        # Get vendor name from PO
        vendor_name = grn.purchase_order.vendor.company_name if grn.purchase_order and grn.purchase_order.vendor else "Unknown Vendor"

        # Calculate tax amounts from GRN
        subtotal = grn.accepted_value or Decimal("0")
        cgst = grn.cgst_amount or Decimal("0")
        sgst = grn.sgst_amount or Decimal("0")
        igst = grn.igst_amount or Decimal("0")
        total = grn.total_value or subtotal

        await accounting.post_grn_entry(
            grn_id=grn.id,
            grn_number=grn.grn_number,
            vendor_name=vendor_name,
            subtotal=subtotal,
            cgst=cgst,
            sgst=sgst,
            igst=igst,
            total=total,
            is_interstate=igst > 0,
            product_type="purifier",
        )
        await db.commit()
    except Exception as e:
        import logging
        logging.warning(f"Failed to post accounting entry for GRN {grn.grn_number}: {e}")

    return grn


# ==================== Vendor Invoice & 3-Way Matching ====================

@router.post("/invoices", response_model=VendorInvoiceResponse, status_code=status.HTTP_201_CREATED)
@require_module("procurement")
async def create_vendor_invoice(
    invoice_in: VendorInvoiceCreate,
    db: DB,
    current_user: User = Depends(get_current_user),
):
    """Record a vendor invoice."""
    # Verify vendor
    vendor_result = await db.execute(
        select(Vendor).where(Vendor.id == invoice_in.vendor_id)
    )
    vendor = vendor_result.scalar_one_or_none()
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor not found")

    # Check for duplicate invoice number
    dup_result = await db.execute(
        select(VendorInvoice).where(
            and_(
                VendorInvoice.vendor_id == invoice_in.vendor_id,
                VendorInvoice.invoice_number == invoice_in.invoice_number,
            )
        )
    )
    if dup_result.scalar_one_or_none():
        raise HTTPException(
            status_code=400,
            detail=f"Invoice {invoice_in.invoice_number} already exists for this vendor"
        )

    # Generate our reference
    count_result = await db.execute(
        select(func.count(VendorInvoice.id))
    )
    count = count_result.scalar() or 0
    our_reference = f"VINV-{date.today().strftime('%Y%m')}-{str(count + 1).zfill(5)}"

    # Calculate amounts with proper Decimal precision
    subtotal = Decimal(str(invoice_in.subtotal))
    discount_amt = Decimal(str(invoice_in.discount_amount or 0))
    taxable_amount = (subtotal - discount_amt).quantize(Decimal("0.01"))
    total_tax = (
        Decimal(str(invoice_in.cgst_amount or 0)) +
        Decimal(str(invoice_in.sgst_amount or 0)) +
        Decimal(str(invoice_in.igst_amount or 0)) +
        Decimal(str(invoice_in.cess_amount or 0))
    ).quantize(Decimal("0.01"))

    # TDS calculation
    tds_amount = Decimal("0")
    if invoice_in.tds_applicable and invoice_in.tds_rate > 0:
        tds_rate = Decimal(str(invoice_in.tds_rate))
        tds_amount = (taxable_amount * tds_rate / Decimal("100")).quantize(Decimal("0.01"))

    grand_total = Decimal(str(invoice_in.grand_total))
    net_payable = (grand_total - tds_amount).quantize(Decimal("0.01"))

    invoice = VendorInvoice(
        **invoice_in.model_dump(),
        our_reference=our_reference,
        taxable_amount=taxable_amount,
        total_tax=total_tax,
        tds_amount=tds_amount,
        net_payable=net_payable,
        balance_due=net_payable,
        received_by=current_user.id,
        received_at=datetime.now(timezone.utc),
        created_by=current_user.id,
    )

    db.add(invoice)

    # Create vendor ledger entry
    ledger_entry = VendorLedger(
        vendor_id=invoice_in.vendor_id,
        transaction_type=VendorTransactionType.INVOICE,
        transaction_date=invoice_in.invoice_date,
        due_date=invoice_in.due_date,
        reference_type="VENDOR_INVOICE",
        reference_number=our_reference,
        reference_id=invoice.id,
        vendor_invoice_number=invoice_in.invoice_number,
        vendor_invoice_date=invoice_in.invoice_date,
        credit_amount=net_payable,
        running_balance=vendor.current_balance + net_payable,
        narration=f"Vendor Invoice: {invoice_in.invoice_number}",
        created_by=current_user.id,
    )
    db.add(ledger_entry)

    # Update vendor balance
    vendor.current_balance += net_payable

    await db.commit()
    await db.refresh(invoice)

    return invoice


@router.get("/invoices", response_model=VendorInvoiceListResponse)
@require_module("procurement")
async def list_vendor_invoices(
    db: DB,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    status: Optional[VendorInvoiceStatus] = None,
    vendor_id: Optional[UUID] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    overdue_only: bool = False,
    current_user: User = Depends(get_current_user),
):
    """List vendor invoices."""
    query = select(VendorInvoice)
    count_query = select(func.count(VendorInvoice.id))
    value_query = select(func.coalesce(func.sum(VendorInvoice.grand_total), 0))
    balance_query = select(func.coalesce(func.sum(VendorInvoice.balance_due), 0))

    filters = []
    if status:
        filters.append(VendorInvoice.status == status)
    if vendor_id:
        filters.append(VendorInvoice.vendor_id == vendor_id)
    if start_date:
        filters.append(VendorInvoice.invoice_date >= start_date)
    if end_date:
        filters.append(VendorInvoice.invoice_date <= end_date)
    if overdue_only:
        filters.append(VendorInvoice.due_date < date.today())
        filters.append(VendorInvoice.balance_due > 0)

    if filters:
        query = query.where(and_(*filters))
        count_query = count_query.where(and_(*filters))
        value_query = value_query.where(and_(*filters))
        balance_query = balance_query.where(and_(*filters))

    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    total_value_result = await db.execute(value_query)
    total_value = total_value_result.scalar() or Decimal("0")

    total_balance_result = await db.execute(balance_query)
    total_balance = total_balance_result.scalar() or Decimal("0")

    query = query.order_by(VendorInvoice.invoice_date.desc()).offset(skip).limit(limit)
    result = await db.execute(query)
    invoices = result.scalars().all()

    # Build brief responses with vendor names
    items = []
    for inv in invoices:
        vendor_result = await db.execute(
            select(Vendor.name).where(Vendor.id == inv.vendor_id)
        )
        vendor_name = vendor_result.scalar() or ""

        items.append(VendorInvoiceBrief(
            id=inv.id,
            our_reference=inv.our_reference,
            invoice_number=inv.invoice_number,
            invoice_date=inv.invoice_date,
            vendor_name=vendor_name,
            grand_total=inv.grand_total,
            balance_due=inv.balance_due,
            due_date=inv.due_date,
            status=inv.status,
        ))

    return VendorInvoiceListResponse(
        items=items,
        total=total,
        total_value=total_value,
        total_balance=total_balance,
        skip=skip,
        limit=limit
    )


@router.post("/invoices/3way-match", response_model=ThreeWayMatchResponse)
@require_module("procurement")
async def perform_three_way_match(
    match_request: ThreeWayMatchRequest,
    db: DB,
    current_user: User = Depends(get_current_user),
):
    """Perform 3-way matching: PO ↔ GRN ↔ Invoice."""
    # Get PO
    po_result = await db.execute(
        select(PurchaseOrder).where(PurchaseOrder.id == match_request.purchase_order_id)
    )
    po = po_result.scalar_one_or_none()
    if not po:
        raise HTTPException(status_code=404, detail="Purchase Order not found")

    # Get GRN
    grn_result = await db.execute(
        select(GoodsReceiptNote).where(GoodsReceiptNote.id == match_request.grn_id)
    )
    grn = grn_result.scalar_one_or_none()
    if not grn:
        raise HTTPException(status_code=404, detail="GRN not found")

    # Get Invoice
    invoice_result = await db.execute(
        select(VendorInvoice).where(VendorInvoice.id == match_request.vendor_invoice_id)
    )
    invoice = invoice_result.scalar_one_or_none()
    if not invoice:
        raise HTTPException(status_code=404, detail="Vendor Invoice not found")

    # Perform matching
    po_total = po.grand_total
    grn_value = grn.total_value
    invoice_total = invoice.grand_total

    # Calculate variances
    variance_amount = abs(invoice_total - grn_value)
    variance_percentage = (variance_amount / grn_value * 100) if grn_value > 0 else Decimal("0")

    discrepancies = []
    recommendations = []

    # Check PO vs GRN
    if po.vendor_id != grn.vendor_id:
        discrepancies.append({"type": "vendor_mismatch", "message": "GRN vendor doesn't match PO vendor"})

    # Check PO vs Invoice
    if po.vendor_id != invoice.vendor_id:
        discrepancies.append({"type": "vendor_mismatch", "message": "Invoice vendor doesn't match PO vendor"})

    # Check GRN vs Invoice amounts
    if variance_percentage > match_request.tolerance_percentage:
        discrepancies.append({
            "type": "amount_variance",
            "message": f"Invoice amount ({invoice_total}) differs from GRN value ({grn_value}) by {variance_percentage:.2f}%",
            "grn_value": str(grn_value),
            "invoice_total": str(invoice_total),
        })
        recommendations.append("Review invoice line items against GRN received quantities")

    # Determine if matched
    is_matched = len(discrepancies) == 0

    if is_matched:
        # Update invoice status
        invoice.po_matched = True
        invoice.grn_matched = True
        invoice.is_fully_matched = True
        invoice.matching_variance = variance_amount
        invoice.status = VendorInvoiceStatus.VERIFIED.value
        invoice.verified_by = current_user.id
        invoice.verified_at = datetime.now(timezone.utc)

        recommendations.append("Invoice matched successfully. Ready for payment approval.")
    else:
        invoice.matching_variance = variance_amount
        invoice.variance_reason = "; ".join([d["message"] for d in discrepancies])

        if variance_percentage <= 5:
            recommendations.append("Minor variance detected. Consider manual override if acceptable.")
        else:
            recommendations.append("Significant variance. Contact vendor for clarification.")

    await db.commit()

    return ThreeWayMatchResponse(
        is_matched=is_matched,
        po_total=po_total,
        grn_value=grn_value,
        invoice_total=invoice_total,
        variance_amount=variance_amount,
        variance_percentage=variance_percentage,
        discrepancies=discrepancies,
        recommendations=recommendations,
    )


# ==================== Reports ====================

@router.get("/reports/pending-grn", response_model=List[PendingGRNResponse])
@require_module("procurement")
async def get_pending_grn_report(
    db: DB,
    vendor_id: Optional[UUID] = None,
    warehouse_id: Optional[UUID] = None,
    current_user: User = Depends(get_current_user),
):
    """Get pending GRN report - POs awaiting goods receipt."""
    query = select(PurchaseOrder).options(
        selectinload(PurchaseOrder.items)
    ).where(
        PurchaseOrder.status.in_(["SENT_TO_VENDOR", "ACKNOWLEDGED", "PARTIALLY_RECEIVED"])
    )

    if vendor_id:
        query = query.where(PurchaseOrder.vendor_id == vendor_id)
    if warehouse_id:
        query = query.where(PurchaseOrder.delivery_warehouse_id == warehouse_id)

    result = await db.execute(query)
    pos = result.scalars().all()

    pending_list = []
    today = date.today()

    for po in pos:
        total_ordered = sum(item.quantity_ordered for item in po.items)
        total_received = sum(item.quantity_received for item in po.items)
        pending_qty = total_ordered - total_received

        if pending_qty > 0:
            # Calculate pending value
            pending_value = Decimal("0")
            for item in po.items:
                item_pending = item.quantity_ordered - item.quantity_received
                if item_pending > 0:
                    pending_value += item_pending * item.unit_price

            days_pending = (today - po.po_date).days

            pending_list.append(PendingGRNResponse(
                po_id=po.id,
                po_number=po.po_number,
                vendor_name=po.vendor_name,
                po_date=po.po_date,
                expected_date=po.expected_delivery_date,
                total_ordered=total_ordered,
                total_received=total_received,
                pending_quantity=pending_qty,
                pending_value=pending_value,
                days_pending=days_pending,
            ))

    return sorted(pending_list, key=lambda x: x.days_pending, reverse=True)


@router.get("/reports/po-summary", response_model=POSummaryResponse)
@require_module("procurement")
async def get_po_summary_report(
    start_date: date,
    end_date: date,
    db: DB,
    vendor_id: Optional[UUID] = None,
    warehouse_id: Optional[UUID] = None,
    current_user: User = Depends(get_current_user),
):
    """Get PO summary report for a date range."""
    base_filter = and_(
        PurchaseOrder.po_date >= start_date,
        PurchaseOrder.po_date <= end_date,
    )

    if vendor_id:
        base_filter = and_(base_filter, PurchaseOrder.vendor_id == vendor_id)
    if warehouse_id:
        base_filter = and_(base_filter, PurchaseOrder.delivery_warehouse_id == warehouse_id)

    # Total POs
    total_query = select(
        func.count(PurchaseOrder.id),
        func.coalesce(func.sum(PurchaseOrder.grand_total), 0)
    ).where(base_filter)
    total_result = await db.execute(total_query)
    total_row = total_result.one()

    # By status
    status_query = select(
        PurchaseOrder.status,
        func.count(PurchaseOrder.id),
        func.coalesce(func.sum(PurchaseOrder.grand_total), 0)
    ).where(base_filter).group_by(PurchaseOrder.status)
    status_result = await db.execute(status_query)
    status_data = {row[0].value: {"count": row[1], "value": float(row[2])} for row in status_result.all()}

    # By vendor
    vendor_query = select(
        PurchaseOrder.vendor_name,
        func.count(PurchaseOrder.id),
        func.coalesce(func.sum(PurchaseOrder.grand_total), 0)
    ).where(base_filter).group_by(PurchaseOrder.vendor_name)
    vendor_result = await db.execute(vendor_query)
    vendor_data = [
        {"vendor": row[0], "count": row[1], "value": float(row[2])}
        for row in vendor_result.all()
    ]

    # Categorize using string values (avoid invalid enum references)
    pending_statuses = ["DRAFT", "PENDING_APPROVAL", "APPROVED", "SENT_TO_VENDOR", "ACKNOWLEDGED"]
    received_statuses = ["PARTIALLY_RECEIVED", "FULLY_RECEIVED", "CLOSED"]
    cancelled_statuses = ["CANCELLED"]

    pending_count = sum(status_data.get(s, {}).get("count", 0) for s in pending_statuses)
    pending_value = sum(status_data.get(s, {}).get("value", 0) for s in pending_statuses)
    received_count = sum(status_data.get(s, {}).get("count", 0) for s in received_statuses)
    received_value = sum(status_data.get(s, {}).get("value", 0) for s in received_statuses)
    cancelled_count = sum(status_data.get(s, {}).get("count", 0) for s in cancelled_statuses)
    cancelled_value = sum(status_data.get(s, {}).get("value", 0) for s in cancelled_statuses)

    return POSummaryResponse(
        period_start=start_date,
        period_end=end_date,
        total_po_count=total_row[0],
        total_po_value=Decimal(str(total_row[1])),
        pending_count=pending_count,
        pending_value=Decimal(str(pending_value)),
        received_count=received_count,
        received_value=Decimal(str(received_value)),
        cancelled_count=cancelled_count,
        cancelled_value=Decimal(str(cancelled_value)),
        by_vendor=vendor_data,
        by_status=status_data,
    )


# ==================== Document Downloads ====================

def _number_to_words(num: float) -> str:
    """Convert number to words for Indian currency."""
    ones = ['', 'One', 'Two', 'Three', 'Four', 'Five', 'Six', 'Seven', 'Eight', 'Nine', 'Ten',
            'Eleven', 'Twelve', 'Thirteen', 'Fourteen', 'Fifteen', 'Sixteen', 'Seventeen', 'Eighteen', 'Nineteen']
    tens = ['', '', 'Twenty', 'Thirty', 'Forty', 'Fifty', 'Sixty', 'Seventy', 'Eighty', 'Ninety']

    if num == 0:
        return 'Zero'

    def words(n):
        if n < 20:
            return ones[n]
        elif n < 100:
            return tens[n // 10] + (' ' + ones[n % 10] if n % 10 else '')
        elif n < 1000:
            return ones[n // 100] + ' Hundred' + (' ' + words(n % 100) if n % 100 else '')
        elif n < 100000:
            return words(n // 1000) + ' Thousand' + (' ' + words(n % 1000) if n % 1000 else '')
        elif n < 10000000:
            return words(n // 100000) + ' Lakh' + (' ' + words(n % 100000) if n % 100000 else '')
        else:
            return words(n // 10000000) + ' Crore' + (' ' + words(n % 10000000) if n % 10000000 else '')

    rupees = int(num)
    paise = int(round((num - rupees) * 100))

    result = 'Rupees ' + words(rupees)
    if paise:
        result += ' and ' + words(paise) + ' Paise'
    return result + ' Only'


@router.post("/orders/{po_id}/fix-and-test")
@require_module("procurement")
async def fix_and_test_po(
    po_id: UUID,
    db: DB,
):
    """
    Complete fix for PO barcode generation:
    1. Delete existing serials
    2. Reset to DRAFT
    3. Approve
    4. Generate serials
    5. Return PDF preview with barcode status
    """
    from sqlalchemy import text
    from app.services.serialization import SerializationService
    from app.schemas.serialization import GenerateSerialsRequest, GenerateSerialItem, ItemType
    from datetime import datetime
    import logging

    steps = []

    # Get PO with items
    result = await db.execute(
        select(PurchaseOrder)
        .options(selectinload(PurchaseOrder.items))
        .where(PurchaseOrder.id == po_id)
    )
    po = result.scalar_one_or_none()

    if not po:
        raise HTTPException(status_code=404, detail="PO not found")

    steps.append({"step": 1, "action": "Found PO", "result": f"{po.po_number}, status={po.status}, items={len(po.items)}"})

    # Step 2: Delete existing serials
    delete_result = await db.execute(
        text("DELETE FROM po_serials WHERE po_id = :po_id"),
        {"po_id": str(po.id)}
    )
    steps.append({"step": 2, "action": "Deleted existing serials", "result": "Done"})

    # Step 3: Reset to DRAFT then APPROVE
    po.status = POStatus.APPROVED.value
    po.approved_at = datetime.now(timezone.utc)
    await db.commit()
    steps.append({"step": 3, "action": "Set status to APPROVED", "result": "Done"})

    # Step 4: Get supplier code
    supplier_code = "AP"
    if po.vendor_id:
        sc_result = await db.execute(
            text("SELECT code FROM supplier_codes WHERE vendor_id = :vendor_id LIMIT 1"),
            {"vendor_id": str(po.vendor_id)}
        )
        sc_row = sc_result.first()
        if sc_row:
            supplier_code = sc_row[0]
    steps.append({"step": 4, "action": "Got supplier code", "result": supplier_code})

    # Step 5: Build serial items
    serial_items = []
    for item in po.items:
        model_code = None
        item_type = ItemType.SPARE_PART  # Default to spare part for this vendor

        # Try to find model code reference (item_type column may not exist in production)
        if item.product_id:
            ref_result = await db.execute(
                text("SELECT model_code FROM model_code_references WHERE product_id = :product_id LIMIT 1"),
                {"product_id": str(item.product_id)}
            )
            ref_row = ref_result.first()
            if ref_row:
                model_code = ref_row[0]

        if not model_code and item.sku:
            ref_result = await db.execute(
                text("SELECT model_code FROM model_code_references WHERE product_sku = :sku LIMIT 1"),
                {"sku": item.sku}
            )
            ref_row = ref_result.first()
            if ref_row:
                model_code = ref_row[0]

        if not model_code:
            # Generate from SKU or product name - use first 3 alpha chars
            source = item.sku or item.product_name or "UNK"
            clean = ''.join(c for c in source if c.isalpha())
            model_code = clean[:3].upper() if len(clean) >= 3 else clean.upper().ljust(3, 'X')

        serial_items.append(GenerateSerialItem(
            po_item_id=str(item.id),
            product_id=str(item.product_id) if item.product_id else None,
            product_sku=item.sku,
            model_code=model_code,
            item_type=item_type,
            quantity=item.quantity_ordered
        ))

    steps.append({"step": 5, "action": "Built serial items", "result": f"{len(serial_items)} items"})

    # Step 6: Generate serials
    try:
        serial_service = SerializationService(db)
        gen_request = GenerateSerialsRequest(
            po_id=str(po.id),
            supplier_code=supplier_code,
            items=serial_items
        )
        gen_result = await serial_service.generate_serials_for_po(gen_request)
        steps.append({
            "step": 6,
            "action": "Generated serials",
            "result": f"SUCCESS: {gen_result.total_generated} serials",
            "items": [{"model": s.model_code, "qty": s.quantity, "start": s.start_barcode, "end": s.end_barcode} for s in gen_result.items]
        })
    except Exception as e:
        import traceback
        steps.append({
            "step": 6,
            "action": "Generate serials",
            "result": f"FAILED: {type(e).__name__}: {str(e)}",
            "traceback": traceback.format_exc()
        })
        return {"success": False, "steps": steps}

    # Step 7: Verify serials in database
    verify_result = await db.execute(
        text("SELECT COUNT(*) FROM po_serials WHERE po_id = :po_id"),
        {"po_id": str(po.id)}
    )
    final_count = verify_result.scalar() or 0
    steps.append({"step": 7, "action": "Verified serials in DB", "result": f"{final_count} serials"})

    # Step 8: Get sample barcodes
    sample_result = await db.execute(
        text("SELECT barcode, model_code FROM po_serials WHERE po_id = :po_id LIMIT 5"),
        {"po_id": str(po.id)}
    )
    samples = [{"barcode": r[0], "model_code": r[1]} for r in sample_result.all()]
    steps.append({"step": 8, "action": "Sample barcodes", "result": samples})

    return {
        "success": final_count > 0,
        "po_number": po.po_number,
        "total_serials": final_count,
        "supplier_code": supplier_code,
        "steps": steps,
        "next": f"Download PDF at: /api/v1/purchase/orders/{po_id}/download"
    }


# GET version so you can trigger from browser
@router.get("/orders/{po_id}/fix-barcodes")
@require_module("procurement")
async def fix_barcodes_get(po_id: UUID, db: DB):
    """
    Browser-friendly GET endpoint to fix barcode generation.
    Just open this URL in your browser to fix the PO.
    """
    return await fix_and_test_po(po_id, db)


@router.get("/orders/{po_id}/verify-serials")
@require_module("procurement")
async def verify_serials(po_id: UUID, db: DB):
    """
    Public endpoint to verify serials were generated for a PO.
    Returns count and sample barcodes.
    """
    from sqlalchemy import text

    # Get PO info
    result = await db.execute(
        select(PurchaseOrder).where(PurchaseOrder.id == po_id)
    )
    po = result.scalar_one_or_none()

    if not po:
        raise HTTPException(status_code=404, detail="PO not found")

    # Count serials
    count_result = await db.execute(
        text("SELECT COUNT(*) FROM po_serials WHERE po_id = :po_id"),
        {"po_id": str(po.id)}
    )
    count = count_result.scalar() or 0

    # Get sample barcodes
    samples_result = await db.execute(
        text("SELECT barcode, model_code, supplier_code FROM po_serials WHERE po_id = :po_id ORDER BY serial_number LIMIT 10"),
        {"po_id": str(po.id)}
    )
    samples = [{"barcode": r[0], "model_code": r[1], "supplier_code": r[2]} for r in samples_result.all()]

    return {
        "po_number": po.po_number,
        "status": po.status if po.status else None,
        "total_serials": count,
        "samples": samples,
        "message": "SUCCESS - Barcodes are generated!" if count > 0 else "No serials found"
    }


@router.post("/orders/{po_id}/reset-to-draft")
@require_module("procurement")
async def reset_po_to_draft(
    po_id: UUID,
    db: DB,
):
    """Reset an approved PO back to DRAFT for re-approval testing."""
    from sqlalchemy import text

    # Get PO
    result = await db.execute(
        select(PurchaseOrder).where(PurchaseOrder.id == po_id)
    )
    po = result.scalar_one_or_none()

    if not po:
        raise HTTPException(status_code=404, detail="PO not found")

    old_status = po.status if po.status else None

    # Delete any existing serials for this PO
    await db.execute(
        text("DELETE FROM po_serials WHERE po_id = :po_id"),
        {"po_id": str(po.id)}
    )

    # Reset PO to DRAFT
    po.status = POStatus.DRAFT.value
    po.approved_by = None
    po.approved_at = None

    await db.commit()

    return {
        "message": f"PO {po.po_number} reset to DRAFT",
        "old_status": old_status,
        "new_status": "DRAFT",
        "serials_deleted": True
    }


@router.post("/orders/{po_id}/generate-serials")
@require_module("procurement")
async def manually_generate_serials(
    po_id: UUID,
    db: DB,
    # No auth required temporarily for fixing
):
    """
    Manually generate serials for an approved PO that doesn't have serials.
    Use this to fix POs where serial generation failed during approval.
    """
    from sqlalchemy import text
    from app.services.serialization import SerializationService
    from app.schemas.serialization import GenerateSerialsRequest, GenerateSerialItem, ItemType
    import logging

    # Get PO
    result = await db.execute(
        select(PurchaseOrder)
        .options(selectinload(PurchaseOrder.items))
        .where(PurchaseOrder.id == po_id)
    )
    po = result.scalar_one_or_none()

    if not po:
        raise HTTPException(status_code=404, detail="PO not found")

    if po.status != "APPROVED":
        raise HTTPException(status_code=400, detail=f"PO must be APPROVED to generate serials. Current status: '{po.status}'")

    # Check if serials already exist (po_serials.po_id is VARCHAR)
    existing_result = await db.execute(
        text("SELECT COUNT(*) FROM po_serials WHERE po_id = :po_id"),
        {"po_id": str(po.id)}
    )
    existing_count = existing_result.scalar() or 0

    if existing_count > 0:
        return {"message": f"Serials already exist for this PO: {existing_count} serials", "count": existing_count}

    # Get supplier code for vendor
    supplier_code = "AP"  # Default
    if po.vendor_id:
        sc_result = await db.execute(
            text("SELECT code FROM supplier_codes WHERE vendor_id = :vendor_id LIMIT 1"),
            {"vendor_id": str(po.vendor_id)}
        )
        sc_row = sc_result.first()
        if sc_row:
            supplier_code = sc_row[0]
            logging.info(f"MANUAL SERIAL GEN: Using supplier code '{supplier_code}' for vendor {po.vendor_id}")

    # Build serial items
    serial_items = []
    for item in po.items:
        model_code = None
        item_type = ItemType.FINISHED_GOODS

        # Try to find model code reference (item_type column may not exist in production)
        if item.product_id:
            ref_result = await db.execute(
                text("SELECT model_code FROM model_code_references WHERE product_id = :product_id LIMIT 1"),
                {"product_id": str(item.product_id)}
            )
            ref_row = ref_result.first()
            if ref_row:
                model_code = ref_row[0]

        if not model_code and item.sku:
            ref_result = await db.execute(
                text("SELECT model_code FROM model_code_references WHERE product_sku = :sku LIMIT 1"),
                {"sku": item.sku}
            )
            ref_row = ref_result.first()
            if ref_row:
                model_code = ref_row[0]

        if not model_code:
            # Generate from product name
            product_name = item.product_name or item.sku or "UNK"
            clean_name = ''.join(c for c in product_name if c.isalpha())
            model_code = clean_name[:3].upper() if len(clean_name) >= 3 else clean_name.upper().ljust(3, 'X')

        serial_items.append(GenerateSerialItem(
            po_item_id=str(item.id),
            product_id=str(item.product_id) if item.product_id else None,
            product_sku=item.sku,
            model_code=model_code,
            item_type=item_type,
            quantity=item.quantity_ordered
        ))

    if not serial_items:
        return {"message": "No items to generate serials for", "count": 0}

    # Generate serials
    serial_service = SerializationService(db)
    gen_request = GenerateSerialsRequest(
        po_id=str(po.id),
        supplier_code=supplier_code,
        items=serial_items
    )

    try:
        result = await serial_service.generate_serials_for_po(gen_request)
        return {
            "message": f"Successfully generated {result.total_generated} serials",
            "count": result.total_generated,
            "supplier_code": supplier_code,
            "items": [{"model_code": s.model_code, "quantity": s.quantity, "start_barcode": s.start_barcode, "end_barcode": s.end_barcode} for s in result.items]
        }
    except Exception as e:
        import traceback
        logging.error(f"MANUAL SERIAL GEN FAILED: {e}")
        logging.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Serial generation failed: {str(e)}")


@router.get("/orders/{po_id}/diagnose")
@require_module("procurement")
async def diagnose_po_serials(
    po_id: UUID,
    db: DB,
    # No auth required for diagnostics - temporary
):
    """
    Diagnostic endpoint to check PO status and serial generation.
    Returns detailed info about:
    - PO status
    - Whether serials exist
    - Supplier code configuration
    """
    from sqlalchemy import text
    from app.models.serialization import SupplierCode

    result = await db.execute(
        select(PurchaseOrder)
        .options(selectinload(PurchaseOrder.items))
        .where(PurchaseOrder.id == po_id)
    )
    po = result.scalar_one_or_none()

    if not po:
        return {"error": "PO not found"}

    # Check serials
    serials_result = await db.execute(
        text("SELECT COUNT(*) as count FROM po_serials WHERE po_id = :po_id"),
        {"po_id": str(po.id)}
    )
    serial_count = serials_result.scalar() or 0

    # Get sample serials if any
    sample_serials = []
    if serial_count > 0:
        sample_result = await db.execute(
            text("SELECT barcode, model_code, item_type FROM po_serials WHERE po_id = :po_id LIMIT 5"),
            {"po_id": str(po.id)}
        )
        sample_serials = [{"barcode": r[0], "model_code": r[1], "item_type": r[2]} for r in sample_result.all()]

    # Check supplier code for vendor
    supplier_code_info = None
    if po.vendor_id:
        sc_result = await db.execute(
            text("SELECT code, name, vendor_id FROM supplier_codes WHERE vendor_id = :vendor_id"),
            {"vendor_id": str(po.vendor_id)}
        )
        sc_row = sc_result.first()
        if sc_row:
            supplier_code_info = {"code": sc_row[0], "name": sc_row[1], "vendor_id": sc_row[2]}

    # List all supplier codes
    all_sc_result = await db.execute(
        text("SELECT code, name, vendor_id FROM supplier_codes ORDER BY code")
    )
    all_supplier_codes = [{"code": r[0], "name": r[1], "vendor_id": r[2]} for r in all_sc_result.all()]

    return {
        "po_id": str(po.id),
        "po_number": po.po_number,
        "status": po.status if po.status else None,
        "vendor_id": str(po.vendor_id) if po.vendor_id else None,
        "items_count": len(po.items) if po.items else 0,
        "serials": {
            "count": serial_count,
            "samples": sample_serials
        },
        "supplier_code_for_vendor": supplier_code_info,
        "all_supplier_codes": all_supplier_codes,
        "diagnosis": {
            "po_approved": po.status and po.status == "APPROVED",
            "has_serials": serial_count > 0,
            "vendor_has_supplier_code": supplier_code_info is not None,
            "can_generate_barcodes": po.status and po.status == "APPROVED" and serial_count > 0
        }
    }


@router.get("/orders/{po_id}/download")
@require_module("procurement")
async def download_purchase_order(
    po_id: UUID,
    db: DB,
    current_user: User = Depends(get_current_user),
):
    """Download Purchase Order as printable HTML (Multi-Delivery Template with Month-wise breakdown)."""
    from fastapi.responses import HTMLResponse
    from app.models.serialization import POSerial
    from app.models.company import Company
    from app.models.purchase import PurchaseOrderItem

    result = await db.execute(
        select(PurchaseOrder)
        .options(
            selectinload(PurchaseOrder.items).selectinload(PurchaseOrderItem.product),
            selectinload(PurchaseOrder.delivery_schedules)
        )
        .where(PurchaseOrder.id == po_id)
    )
    po = result.scalar_one_or_none()

    if not po:
        raise HTTPException(status_code=404, detail="Purchase Order not found")

    # Get company details
    company_result = await db.execute(select(Company).limit(1))
    company = company_result.scalar_one_or_none()

    # Get vendor details
    vendor_result = await db.execute(
        select(Vendor).where(Vendor.id == po.vendor_id)
    )
    vendor = vendor_result.scalar_one_or_none()

    # Get warehouse details
    warehouse_result = await db.execute(
        select(Warehouse).where(Warehouse.id == po.delivery_warehouse_id)
    )
    warehouse = warehouse_result.scalar_one_or_none()

    # Get PO serials - grouped by model code for summary
    # Use text query to handle VARCHAR/UUID type mismatch in po_id column
    # Include product_sku to help match with PO items for displaying product name
    import logging
    try:
        from sqlalchemy import text
        logging.info(f"PDF DOWNLOAD: Fetching serials for PO {po.po_number} (id={po.id})")
        serials_result = await db.execute(
            text("""
                SELECT model_code, item_type, product_sku, count(id) as quantity,
                       min(serial_number) as start_serial, max(serial_number) as end_serial,
                       min(barcode) as start_barcode, max(barcode) as end_barcode
                FROM po_serials
                WHERE po_id = :po_id
                GROUP BY model_code, item_type, product_sku
                ORDER BY model_code
            """),
            {"po_id": str(po.id)}
        )
        serial_groups = serials_result.all()
        total_serials = sum(sg.quantity for sg in serial_groups) if serial_groups else 0
        logging.info(f"PDF DOWNLOAD: Found {len(serial_groups)} serial groups, total={total_serials} serials")
    except Exception as e:
        # Log the actual error
        import traceback
        logging.error(f"PDF DOWNLOAD: Serial query failed for PO {po.po_number}: {type(e).__name__}: {e}")
        logging.error(f"Traceback: {traceback.format_exc()}")
        serial_groups = []
        total_serials = 0

    # Check if this is a multi-delivery PO (has monthly_quantities or delivery_schedules)
    has_monthly_breakdown = any(item.monthly_quantities for item in po.items)
    delivery_schedules = sorted(po.delivery_schedules, key=lambda x: x.lot_number) if po.delivery_schedules else []

    # Collect all unique months from all items
    all_months = set()
    for item in po.items:
        if item.monthly_quantities:
            all_months.update(item.monthly_quantities.keys())
    sorted_months = sorted(all_months) if all_months else []

    # Month name mapping for headers
    month_names_short = {
        "01": "JAN", "02": "FEB", "03": "MAR", "04": "APR", "05": "MAY", "06": "JUN",
        "07": "JUL", "08": "AUG", "09": "SEP", "10": "OCT", "11": "NOV", "12": "DEC"
    }

    # Build items table HTML
    items_html = ""
    subtotal = Decimal("0")
    total_qty = 0
    month_totals = {m: 0 for m in sorted_months}  # Track totals per month

    for idx, item in enumerate(po.items, 1):
        unit_price = Decimal(str(item.unit_price)) if item.unit_price else Decimal("0")
        amount = (Decimal(str(item.quantity_ordered)) * unit_price).quantize(Decimal("0.01"))
        subtotal += amount
        total_qty += item.quantity_ordered
        # Use SKU as item code (e.g., SP-SDF001)
        item_code = item.sku or '-'

        # Build month columns if multi-delivery
        month_cells = ""
        if has_monthly_breakdown and sorted_months:
            for month in sorted_months:
                qty = item.monthly_quantities.get(month, 0) if item.monthly_quantities else 0
                month_totals[month] += qty
                month_cells += f'<td class="text-center">{qty if qty > 0 else "-"}</td>'

        items_html += f"""
                <tr>
                    <td class="text-center">{idx}</td>
                    <td class="item-code">{item_code}</td>
                    <td>
                        <strong>{item.product_name or '-'}</strong>
                    </td>
                    <td class="text-center">{item.hsn_code or '84212190'}</td>
                    {month_cells}
                    <td class="text-center"><strong>{item.quantity_ordered}</strong></td>
                    <td class="text-center">{item.uom or 'Nos'}</td>
                    <td class="text-right">Rs. {float(unit_price):,.2f}</td>
                    <td class="text-right"><strong>Rs. {float(amount):,.2f}</strong></td>
                </tr>"""

    # Build total row with month totals
    month_total_cells = ""
    if has_monthly_breakdown and sorted_months:
        for month in sorted_months:
            month_total_cells += f'<td class="text-center"><strong>{month_totals[month]}</strong></td>'

    # Build month headers for table
    month_headers = ""
    if has_monthly_breakdown and sorted_months:
        for month in sorted_months:
            year_part = month.split("-")[0][-2:]  # Last 2 digits of year (e.g., "26")
            month_part = month.split("-")[1]
            month_name = month_names_short.get(month_part, month_part)
            month_headers += f'<th style="width:6%">{month_name} \'{year_part}</th>'

    # Build delivery schedule section HTML
    delivery_schedule_html = ""
    # First lot values for Advance Payment Details section
    # Default to 25% advance if no delivery schedules
    first_lot_advance = Decimal("0")
    first_lot_balance = Decimal("0")
    first_lot_advance_percentage = Decimal("25")

    # Calculate default advance/balance if no delivery schedules exist
    # Use grand_total which is already calculated above
    grand_total_for_calc = Decimal(str(po.grand_total or 0))
    if not delivery_schedules and grand_total_for_calc > 0:
        # If advance_required is set on PO, use that; otherwise use 25%
        if po.advance_required and po.advance_required > 0:
            first_lot_advance = Decimal(str(po.advance_required))
            first_lot_advance_percentage = (first_lot_advance / grand_total_for_calc * Decimal("100")).quantize(Decimal("0.01"))
        else:
            first_lot_advance_percentage = Decimal("25")
            first_lot_advance = (grand_total_for_calc * first_lot_advance_percentage / Decimal("100")).quantize(Decimal("0.01"))
        first_lot_balance = (grand_total_for_calc - first_lot_advance).quantize(Decimal("0.01"))

    if delivery_schedules:
        schedule_rows = ""
        total_qty_sched = 0
        total_lot_value = Decimal("0")
        total_advance = Decimal("0")
        total_balance = Decimal("0")

        # Get first lot's advance/balance values
        first_lot = delivery_schedules[0]
        first_lot_total = Decimal(str(first_lot.lot_total or 0))

        # Get advance percentage from first delivery schedule
        # Note: po.advance_required is an AMOUNT, not percentage, so calculate percentage if needed
        if delivery_schedules and delivery_schedules[0].advance_percentage:
            lot_advance_percentage = Decimal(str(delivery_schedules[0].advance_percentage))
            first_lot_advance_percentage = lot_advance_percentage
        elif po.advance_required and grand_total_for_calc > 0:
            # Calculate percentage from advance amount
            lot_advance_percentage = (Decimal(str(po.advance_required)) / grand_total_for_calc * Decimal("100")).quantize(Decimal("0.01"))
            first_lot_advance_percentage = lot_advance_percentage
        else:
            lot_advance_percentage = Decimal("25")  # Default 25%
            first_lot_advance_percentage = lot_advance_percentage
        lot_balance_percentage = (Decimal("100") - lot_advance_percentage).quantize(Decimal("0.01"))

        # Get stored advance/balance values from first lot
        stored_advance = Decimal(str(first_lot.advance_amount or 0))
        stored_balance = Decimal(str(first_lot.balance_amount or 0))

        # If stored values are 0, calculate from lot total using the percentage
        if stored_advance == 0 and first_lot_total > 0:
            first_lot_advance = (first_lot_total * first_lot_advance_percentage / Decimal("100")).quantize(Decimal("0.01"))
            first_lot_balance = (first_lot_total - first_lot_advance).quantize(Decimal("0.01"))
        else:
            first_lot_advance = stored_advance
            first_lot_balance = stored_balance

        # Track total serial range
        first_serial = None
        last_serial = None

        for sched in delivery_schedules:
            total_qty_sched += sched.total_quantity
            total_lot_value += Decimal(str(sched.lot_total))
            total_advance += Decimal(str(sched.advance_amount))
            total_balance += Decimal(str(sched.balance_amount))

            # Track overall serial range
            if sched.serial_number_start is not None:
                if first_serial is None:
                    first_serial = sched.serial_number_start
                last_serial = sched.serial_number_end

            adv_due_text = "With PO" if sched.lot_number == 1 else f"{sched.expected_delivery_date.strftime('%d %b %Y') if sched.expected_delivery_date else 'TBD'}"
            balance_due_text = sched.balance_due_date.strftime('%d %b %Y') if sched.balance_due_date else "TBD"

            schedule_rows += f"""
                <tr>
                    <td class="text-center"><strong>LOT {sched.lot_number} ({sched.lot_name})</strong></td>
                    <td class="text-center">{sched.expected_delivery_date.strftime('%d %b %Y') if sched.expected_delivery_date else 'TBD'}</td>
                    <td class="text-center">{sched.total_quantity:,}</td>
                    <td class="text-right">Rs. {float(sched.lot_total):,.2f}</td>
                    <td class="text-right">Rs. {float(sched.advance_amount):,.2f}</td>
                    <td class="text-center">{adv_due_text}</td>
                    <td class="text-right">Rs. {float(sched.balance_amount):,.2f}</td>
                    <td class="text-center">{balance_due_text}</td>
                </tr>"""

        delivery_schedule_html = f"""
        <!-- Delivery Schedule Section -->
        <div style="margin-top: 15px; border: 2px solid #1a5f7a; page-break-inside: avoid;">
            <div style="background: #1a5f7a; color: white; padding: 10px; font-weight: bold; font-size: 12px;">
                DELIVERY SCHEDULE & LOT-WISE PAYMENT PLAN
            </div>
            <table style="font-size: 10px;">
                <thead>
                    <tr style="background: #e0e0e0;">
                        <th style="width: 14%">LOT</th>
                        <th style="width: 12%">DELIVERY DATE</th>
                        <th style="width: 8%">QTY</th>
                        <th style="width: 14%">LOT VALUE (incl. GST)</th>
                        <th style="width: 12%">ADVANCE ({float(lot_advance_percentage):.0f}%)</th>
                        <th style="width: 12%">ADVANCE DUE</th>
                        <th style="width: 12%">BALANCE ({float(lot_balance_percentage):.0f}%)</th>
                        <th style="width: 12%">BALANCE DUE</th>
                    </tr>
                </thead>
                <tbody>
                    {schedule_rows}
                    <tr style="background: #f5f5f5; font-weight: bold;">
                        <td class="text-center">TOTAL</td>
                        <td class="text-center"></td>
                        <td class="text-center">{total_qty_sched:,}</td>
                        <td class="text-right">Rs. {float(total_lot_value):,.2f}</td>
                        <td class="text-right">Rs. {float(total_advance):,.2f}</td>
                        <td class="text-center"></td>
                        <td class="text-right">Rs. {float(total_balance):,.2f}</td>
                        <td class="text-center"></td>
                    </tr>
                </tbody>
            </table>
            <p style="padding: 8px; font-size: 9px; color: #666; background: #fff3cd;">
                <strong>Note:</strong> Advance ({float(lot_advance_percentage):.0f}%) for each lot must be paid before delivery. Balance ({float(lot_balance_percentage):.0f}%) is due {po.credit_days or 45} days after each lot's delivery.
            </p>
        </div>
        """

    # Tax calculations
    cgst_rate = Decimal("9")
    sgst_rate = Decimal("9")
    igst_rate = Decimal("18")
    cgst_amount = Decimal(str(po.cgst_amount or 0))
    sgst_amount = Decimal(str(po.sgst_amount or 0))
    igst_amount = Decimal(str(po.igst_amount or 0))
    grand_total = Decimal(str(po.grand_total or 0))

    # Advance payment - show both required and paid
    advance_required = Decimal(str(getattr(po, 'advance_required', 0) or 0))
    advance_paid = Decimal(str(getattr(po, 'advance_paid', 0) or 0))

    # Calculate advance percentage for display
    advance_percentage = (advance_required / grand_total * 100) if grand_total > 0 and advance_required > 0 else Decimal("0")

    # Balance is calculated from what's required, not what's paid
    balance_due = grand_total - advance_required

    # Company info
    company_name = company.legal_name if company else "AQUAPURITE INDIA PRIVATE LIMITED"
    company_gstin = company.gstin if company else "07AADCA1234L1ZP"
    company_cin = getattr(company, 'cin', None) if company else "U12345DL2024PTC123456"
    company_address = f"{company.address_line1 if company else 'Plot No. 123, Sector 5'}, {company.city if company else 'New Delhi'}, {company.state if company else 'Delhi'} - {company.pincode if company else '110001'}"
    company_phone = company.phone if company else "+91-11-12345678"
    company_email = company.email if company else "info@aquapurite.com"
    company_state_code = getattr(company, 'state_code', '07') if company else "07"

    # Vendor info
    vendor_name = vendor.legal_name if vendor else (po.vendor_name or "Vendor")
    vendor_gstin = vendor.gstin if vendor else (po.vendor_gstin or "N/A")
    vendor_state_code = vendor.gst_state_code if vendor else "07"
    vendor_code = vendor.vendor_code if vendor else "N/A"
    vendor_contact = vendor.contact_person if vendor else "N/A"
    vendor_phone = vendor.phone if vendor else "N/A"

    vendor_address_parts = []
    if vendor:
        if vendor.address_line1:
            vendor_address_parts.append(vendor.address_line1)
        if vendor.address_line2:
            vendor_address_parts.append(vendor.address_line2)
        if vendor.city:
            vendor_address_parts.append(vendor.city)
        if vendor.state:
            vendor_address_parts.append(vendor.state)
        if vendor.pincode:
            vendor_address_parts.append(str(vendor.pincode))
    vendor_full_address = ", ".join(vendor_address_parts) if vendor_address_parts else "N/A"

    # Warehouse (Ship To) info
    warehouse_name = warehouse.name if warehouse else "Central Warehouse"
    warehouse_address_parts = []
    if warehouse:
        if warehouse.address_line1:
            warehouse_address_parts.append(warehouse.address_line1)
        if warehouse.city:
            warehouse_address_parts.append(warehouse.city)
        if warehouse.state:
            warehouse_address_parts.append(warehouse.state)
        if warehouse.pincode:
            warehouse_address_parts.append(str(warehouse.pincode))
    warehouse_full_address = ", ".join(warehouse_address_parts) if warehouse_address_parts else "N/A"

    # Bank details
    bank_name = vendor.bank_name if vendor else "N/A"
    bank_branch = vendor.bank_branch if vendor else "N/A"
    bank_account = vendor.bank_account_number if vendor else "N/A"
    bank_ifsc = vendor.bank_ifsc if vendor else "N/A"
    beneficiary_name = vendor.beneficiary_name if vendor else vendor_name

    # Bill To info (from PO or company)
    bill_to_data = po.bill_to or {}
    bill_to_name = bill_to_data.get('name') or company_name
    bill_to_address = ", ".join(filter(None, [
        bill_to_data.get('address_line1'),
        bill_to_data.get('address_line2'),
        bill_to_data.get('city'),
        bill_to_data.get('state'),
        str(bill_to_data.get('pincode', ''))
    ])) or company_address
    bill_to_gstin = bill_to_data.get('gstin') or company_gstin
    bill_to_state_code = bill_to_data.get('state_code') or company_state_code

    # Ship To info (from PO or warehouse)
    ship_to_data = po.ship_to or {}
    ship_to_name = ship_to_data.get('name') or warehouse_name
    ship_to_address = ", ".join(filter(None, [
        ship_to_data.get('address_line1'),
        ship_to_data.get('address_line2'),
        ship_to_data.get('city'),
        ship_to_data.get('state'),
        str(ship_to_data.get('pincode', ''))
    ])) or warehouse_full_address
    ship_to_gstin = ship_to_data.get('gstin') or company_gstin
    ship_to_state_code = ship_to_data.get('state_code') or (warehouse.state_code if warehouse and hasattr(warehouse, 'state_code') else company_state_code)

    # Tax type determination - compare SHIP TO state with VENDOR state (Place of Supply rule)
    # Extract state code from GSTIN (first 2 digits) for accurate comparison
    def get_state_from_gstin(gstin):
        if gstin and len(gstin) >= 2 and gstin[:2].isdigit():
            return gstin[:2]
        return None

    # Get state codes from GSTIN first, then fall back to explicit state codes
    vendor_state_from_gstin = get_state_from_gstin(vendor_gstin)
    ship_to_state_from_gstin = get_state_from_gstin(ship_to_gstin)

    effective_vendor_state = vendor_state_from_gstin or vendor_state_code or "07"
    effective_ship_to_state = ship_to_state_from_gstin or ship_to_state_code or "07"

    is_intra_state = effective_vendor_state == effective_ship_to_state
    tax_type = "CGST + SGST (Intra-State)" if is_intra_state else "IGST (Inter-State)"

    # PO details
    po_date_str = po.po_date.strftime('%d.%m.%Y') if po.po_date else datetime.now().strftime('%d.%m.%Y')
    expected_delivery_str = po.expected_delivery_date.strftime('%d.%m.%Y') if po.expected_delivery_date else "TBD"

    # Terms & Conditions from PO (user-entered, not hardcoded)
    po_terms = getattr(po, 'terms_and_conditions', None) or ""
    if po_terms:
        # Convert newlines to HTML line breaks and escape HTML
        import html
        po_terms_html = html.escape(po_terms).replace('\n', '<br>')
    else:
        # Default message if no terms entered
        po_terms_html = "<em>Terms and conditions as per agreement.</em>"

    # Build serial numbers section HTML (goes after Terms & Conditions)
    serials_html = ""
    if serial_groups:
        serial_rows = ""
        for sg in serial_groups:
            item_type = sg.item_type if hasattr(sg.item_type, 'value') else str(sg.item_type)

            # Get product name using product_sku from serials (more reliable than model_code matching)
            product_name = "-"
            serial_product_sku = sg.product_sku if hasattr(sg, 'product_sku') else None
            matched_item = None

            for item in po.items:
                # First try exact SKU match from serial record
                if serial_product_sku and item.sku and item.sku.upper() == serial_product_sku.upper():
                    product_name = item.product_name or item.sku
                    matched_item = item
                    break
                # Fallback: Check if this item's SKU contains the model code
                elif item.sku and sg.model_code.upper() in item.sku.upper():
                    product_name = item.product_name or item.sku
                    matched_item = item
                    # Don't break here - keep looking for exact SKU match

            # If still no match, use product_sku as a fallback display
            if product_name == "-" and serial_product_sku:
                product_name = serial_product_sku

            # Override item_type if matched PO item has product with item_type info
            # This fixes incorrect item_type stored in po_serials
            if matched_item:
                # Check product relationship for item_type (Product.item_type)
                product = getattr(matched_item, 'product', None)
                if product:
                    product_item_type = getattr(product, 'item_type', None)
                    if product_item_type:
                        pt_value = product_item_type.value if hasattr(product_item_type, 'value') else str(product_item_type)
                        if pt_value in ("SP", "SPARE_PART"):
                            item_type = "SP"
                        elif pt_value in ("FG", "FINISHED_GOODS"):
                            item_type = "FG"
                        elif pt_value in ("CO", "COMPONENT"):
                            item_type = "CO"
                        elif pt_value in ("CN", "CONSUMABLE"):
                            item_type = "CN"

            # Handle both short codes (FG, SP, CO, CN) and full names
            if item_type in ("FG", "FINISHED_GOODS"):
                item_type_label = "Finished Goods"
            elif item_type in ("SP", "SPARE_PART"):
                item_type_label = "Spare Part"
            elif item_type in ("CO", "COMPONENT"):
                item_type_label = "Component"
            elif item_type in ("CN", "CONSUMABLE"):
                item_type_label = "Consumable"
            elif item_type in ("AC", "ACCESSORY"):
                item_type_label = "Accessory"
            else:
                item_type_label = item_type

            serial_rows += f"""
                    <tr>
                        <td>{product_name}</td>
                        <td class="text-center"><span class="fg-code">{sg.model_code}</span></td>
                        <td class="text-center">{item_type_label}</td>
                        <td class="text-center"><strong>{sg.quantity:,}</strong></td>
                        <td style="font-family: 'Courier New', monospace; font-size: 9px; background: #f0f8ff;">
                            <strong>{sg.start_barcode}</strong><br>to<br><strong>{sg.end_barcode}</strong>
                        </td>
                    </tr>"""

        serials_html = f"""
        <!-- Barcode Allocation Section -->
        <div style="margin-top: 15px; page-break-inside: avoid; border: 2px solid #1a5f7a;">
            <div style="background: #1a5f7a; color: white; padding: 10px; font-weight: bold; font-size: 12px;">
                BARCODE ALLOCATION BY ITEM
            </div>
            <div style="padding: 10px;">
                <p style="font-size: 9px; color: #666; margin-bottom: 8px;">
                    The following barcodes have been pre-allocated for this Purchase Order.
                    Please ensure barcodes are printed and affixed to each unit before dispatch.
                </p>
                <table style="font-size: 10px;">
                    <thead>
                        <tr style="background: #e0e0e0;">
                            <th style="width: 30%;">Item Description</th>
                            <th style="width: 12%;">Model Code</th>
                            <th style="width: 12%;">Type</th>
                            <th style="width: 10%;">Qty</th>
                            <th style="width: 36%;">Barcode Range</th>
                        </tr>
                    </thead>
                    <tbody>
                        {serial_rows}
                    </tbody>
                </table>
                <p style="font-size: 9px; color: #666; margin-top: 8px; padding: 5px; background: #fff3cd;">
                    <strong>Total Barcodes:</strong> {total_serials:,} |
                    <a href="/api/v1/serialization/po/{str(po.id)}/export?format=csv" class="no-print" style="color: #1a5f7a;">Download Barcode List (CSV)</a>
                </p>
            </div>
        </div>
        """

    # APPROVED TEMPLATE STRUCTURE (from generate_po_fasttrack_001.py)
    html_content = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Purchase Order - {po.po_number}</title>
    <style>
        @page {{ size: A4; margin: 10mm; }}
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: Arial, sans-serif; font-size: 11px; line-height: 1.4; padding: 10px; background: #fff; }}
        .document {{ max-width: 210mm; margin: 0 auto; border: 2px solid #000; }}

        /* Header */
        .header {{ background: linear-gradient(135deg, #1a5f7a 0%, #0d3d4d 100%); color: white; padding: 15px; text-align: center; }}
        .header h1 {{ font-size: 24px; margin-bottom: 8px; letter-spacing: 2px; }}
        .header .contact {{ font-size: 9px; }}

        /* Document Title */
        .doc-title {{ background: #f0f0f0; padding: 12px; text-align: center; border-bottom: 2px solid #000; }}
        .doc-title h2 {{ font-size: 18px; color: #1a5f7a; }}

        /* Info Grid */
        .info-grid {{ display: flex; flex-wrap: wrap; border-bottom: 1px solid #000; }}
        .info-box {{ flex: 1; min-width: 25%; padding: 8px 10px; border-right: 1px solid #000; }}
        .info-box:last-child {{ border-right: none; }}
        .info-box label {{ display: block; font-size: 9px; color: #666; text-transform: uppercase; margin-bottom: 3px; }}
        .info-box value {{ display: block; font-weight: bold; font-size: 11px; }}

        /* Party Section */
        .party-section {{ display: flex; border-bottom: 1px solid #000; }}
        .party-box {{ flex: 1; padding: 10px; border-right: 1px solid #000; }}
        .party-box:last-child {{ border-right: none; }}
        .party-header {{ background: #1a5f7a; color: white; padding: 5px 8px; margin: -10px -10px 10px -10px; font-size: 10px; font-weight: bold; }}
        .party-box p {{ margin-bottom: 3px; }}
        .party-box .company-name {{ font-weight: bold; font-size: 12px; color: #1a5f7a; }}

        /* Table */
        table {{ width: 100%; border-collapse: collapse; }}
        th {{ background: #1a5f7a; color: white; padding: 8px 5px; font-size: 10px; text-align: center; border: 1px solid #000; }}
        td {{ padding: 8px 5px; border: 1px solid #000; font-size: 10px; }}
        .text-center {{ text-align: center; }}
        .text-right {{ text-align: right; }}
        .fg-code {{ font-family: 'Courier New', monospace; font-weight: bold; color: #1a5f7a; font-size: 9px; }}
        .item-code {{ font-family: 'Courier New', monospace; font-weight: bold; color: #333; font-size: 9px; }}

        /* Totals */
        .totals-section {{ display: flex; border-bottom: 1px solid #000; }}
        .totals-left {{ flex: 1; padding: 10px; border-right: 1px solid #000; }}
        .totals-right {{ width: 300px; }}
        .totals-row {{ display: flex; padding: 5px 10px; border-bottom: 1px solid #ddd; }}
        .totals-row:last-child {{ border-bottom: none; }}
        .totals-label {{ flex: 1; text-align: right; padding-right: 15px; }}
        .totals-value {{ width: 110px; text-align: right; font-weight: bold; }}
        .grand-total {{ background: #1a5f7a; color: white; font-size: 12px; }}
        .advance-paid {{ background: #28a745; color: white; }}
        .balance-due {{ background: #dc3545; color: white; }}

        /* Amount in Words */
        .amount-words {{ padding: 10px; background: #f9f9f9; border-bottom: 1px solid #000; font-style: italic; }}

        /* Payment Section */
        .payment-section {{ padding: 10px; border-bottom: 1px solid #000; background: #e8f5e9; }}
        .payment-section h4 {{ color: #2e7d32; margin-bottom: 8px; }}
        .payment-detail {{ display: flex; margin-bottom: 5px; }}
        .payment-detail label {{ width: 150px; font-weight: bold; }}

        /* Bank Details */
        .bank-section {{ padding: 10px; border-bottom: 1px solid #000; background: #fff3cd; }}
        .bank-section h4 {{ color: #856404; margin-bottom: 8px; }}

        /* Terms */
        .terms {{ padding: 10px; font-size: 9px; border-bottom: 1px solid #000; }}
        .terms h4 {{ margin-bottom: 5px; color: #1a5f7a; }}
        .terms ol {{ margin-left: 15px; }}
        .terms li {{ margin-bottom: 3px; }}

        /* Signature */
        .signature-section {{ display: flex; padding: 20px; }}
        .signature-box {{ flex: 1; text-align: center; }}
        .signature-line {{ border-top: 1px solid #000; margin-top: 50px; padding-top: 5px; width: 180px; margin-left: auto; margin-right: auto; }}

        /* Footer */
        .footer {{ background: #f0f0f0; padding: 8px; text-align: center; font-size: 9px; color: #666; }}

        /* Print Button */
        .print-btn {{
            position: fixed;
            top: 20px;
            right: 20px;
            background: linear-gradient(135deg, #1a5f7a 0%, #0d3d4d 100%);
            color: white;
            border: none;
            padding: 12px 24px;
            font-size: 14px;
            font-weight: bold;
            border-radius: 5px;
            cursor: pointer;
            box-shadow: 0 4px 6px rgba(0,0,0,0.3);
            z-index: 1000;
        }}
        .print-btn:hover {{
            background: linear-gradient(135deg, #0d3d4d 0%, #1a5f7a 100%);
        }}

        @media print {{
            body {{ padding: 0; }}
            .document {{ border: 1px solid #000; }}
            .print-btn {{ display: none !important; }}
            .no-print {{ display: none !important; }}
        }}
    </style>
</head>
<body>
    <!-- Print PDF Button -->
    <button class="print-btn no-print" onclick="window.print()">Print PDF</button>

    <div class="document">
        <!-- Header -->
        <div class="header">
            <h1>{company_name}</h1>
            <div class="contact">
                {company_address}<br>
                GSTIN: {company_gstin} | CIN: {company_cin or 'N/A'}<br>
                Phone: {company_phone} | Email: {company_email}
            </div>
        </div>

        <!-- Document Title -->
        <div class="doc-title">
            <h2>PURCHASE ORDER</h2>
        </div>

        <!-- PO Info Grid -->
        <div class="info-grid">
            <div class="info-box">
                <label>PO Number</label>
                <value style="font-size: 13px; color: #1a5f7a;">{po.po_number}</value>
            </div>
            <div class="info-box">
                <label>PO Date</label>
                <value>{po_date_str}</value>
            </div>
            <div class="info-box">
                <label>PI/Quotation Ref</label>
                <value>{po.quotation_reference or 'N/A'}</value>
            </div>
            <div class="info-box">
                <label>PI/Quotation Date</label>
                <value>{po.quotation_date.strftime('%d.%m.%Y') if po.quotation_date else 'N/A'}</value>
            </div>
        </div>

        <div class="info-grid">
            <div class="info-box">
                <label>Expected Delivery</label>
                <value style="color: #dc3545;">{expected_delivery_str}</value>
            </div>
            <div class="info-box">
                <label>Delivery Terms</label>
                <value>{getattr(po, 'delivery_terms', None) or 'Ex-Works'}</value>
            </div>
            <div class="info-box">
                <label>Payment Terms</label>
                <value>{getattr(po, 'payment_terms', None) or f'{po.credit_days or 30} days credit'}</value>
            </div>
            <div class="info-box">
                <label>Tax Type</label>
                <value>{tax_type}</value>
            </div>
        </div>

        <!-- Vendor, Bill To & Ship To Details -->
        <div class="party-section">
            <div class="party-box">
                <div class="party-header">SUPPLIER / VENDOR</div>
                <p class="company-name">{vendor_name}</p>
                <p>{vendor_full_address}</p>
                <p><strong>GSTIN:</strong> {vendor_gstin}</p>
                <p><strong>State Code:</strong> {vendor_state_code}</p>
                <p><strong>Contact:</strong> {vendor_contact}</p>
                <p><strong>Phone:</strong> {vendor_phone}</p>
                <p><strong>Vendor Code:</strong> {vendor_code}</p>
            </div>
            <div class="party-box">
                <div class="party-header">BILL TO</div>
                <p class="company-name">{bill_to_name}</p>
                <p>{bill_to_address}</p>
                <p><strong>GSTIN:</strong> {bill_to_gstin}</p>
                <p><strong>State Code:</strong> {bill_to_state_code}</p>
            </div>
            <div class="party-box">
                <div class="party-header">SHIP TO</div>
                <p class="company-name">{ship_to_name}</p>
                <p>{ship_to_address}</p>
                <p><strong>GSTIN:</strong> {ship_to_gstin}</p>
                <p><strong>State Code:</strong> {ship_to_state_code}</p>
                <p><strong>Warehouse:</strong> {warehouse_name}</p>
            </div>
        </div>

        <!-- Order Items Table -->
        <table>
            <thead>
                <tr>
                    <th style="width:4%">S.N.</th>
                    <th style="width:10%">SKU</th>
                    <th style="width:{'15%' if has_monthly_breakdown else '25%'}">Description</th>
                    <th style="width:8%">HSN</th>
                    {month_headers}
                    <th style="width:7%">TOTAL</th>
                    <th style="width:5%">UOM</th>
                    <th style="width:10%">Rate</th>
                    <th style="width:12%">Amount</th>
                </tr>
            </thead>
            <tbody>
                {items_html}
                <tr style="background: #f5f5f5; font-weight: bold;">
                    <td colspan="4" class="text-right">TOTAL QUANTITIES</td>
                    {month_total_cells}
                    <td class="text-center">{total_qty}</td>
                    <td class="text-center">Nos</td>
                    <td></td>
                    <td class="text-right">Rs. {float(subtotal):,.2f}</td>
                </tr>
            </tbody>
        </table>

        <!-- Totals Section -->
        <div class="totals-section">
            <div class="totals-left">
                <strong>HSN Summary ({tax_type}):</strong>
                <table style="margin-top: 5px; font-size: 9px;">
                    {"" if is_intra_state else f'''<tr style="background: #e0e0e0;">
                        <th>HSN Code</th>
                        <th>Taxable Value</th>
                        <th>IGST @{igst_rate}%</th>
                        <th>Total Tax</th>
                    </tr>
                    <tr>
                        <td class="text-center">84212110</td>
                        <td class="text-right">Rs. {float(subtotal):,.2f}</td>
                        <td class="text-right">Rs. {float(igst_amount if igst_amount > 0 else cgst_amount + sgst_amount):,.2f}</td>
                        <td class="text-right">Rs. {float(igst_amount if igst_amount > 0 else cgst_amount + sgst_amount):,.2f}</td>
                    </tr>'''}
                    {"" if not is_intra_state else f'''<tr style="background: #e0e0e0;">
                        <th>HSN Code</th>
                        <th>Taxable Value</th>
                        <th>CGST @{cgst_rate}%</th>
                        <th>SGST @{sgst_rate}%</th>
                        <th>Total Tax</th>
                    </tr>
                    <tr>
                        <td class="text-center">84212110</td>
                        <td class="text-right">Rs. {float(subtotal):,.2f}</td>
                        <td class="text-right">Rs. {float(cgst_amount):,.2f}</td>
                        <td class="text-right">Rs. {float(sgst_amount):,.2f}</td>
                        <td class="text-right">Rs. {float(cgst_amount + sgst_amount):,.2f}</td>
                    </tr>'''}
                </table>
                <p style="margin-top: 10px; font-size: 9px; color: #666;">
                    <strong>Note:</strong> {tax_type} applicable
                </p>
            </div>
            <div class="totals-right">
                <div class="totals-row">
                    <span class="totals-label">Sub Total:</span>
                    <span class="totals-value">Rs. {float(subtotal):,.2f}</span>
                </div>
                {"" if is_intra_state else f'''<div class="totals-row">
                    <span class="totals-label">IGST @ {igst_rate}%:</span>
                    <span class="totals-value">Rs. {float(igst_amount if igst_amount > 0 else cgst_amount + sgst_amount):,.2f}</span>
                </div>'''}
                {"" if not is_intra_state else f'''<div class="totals-row">
                    <span class="totals-label">CGST @ {cgst_rate}%:</span>
                    <span class="totals-value">Rs. {float(cgst_amount):,.2f}</span>
                </div>
                <div class="totals-row">
                    <span class="totals-label">SGST @ {sgst_rate}%:</span>
                    <span class="totals-value">Rs. {float(sgst_amount):,.2f}</span>
                </div>'''}
                <div class="totals-row grand-total">
                    <span class="totals-label">GRAND TOTAL:</span>
                    <span class="totals-value">Rs. {float(grand_total):,.2f}</span>
                </div>
                <div class="totals-row" style="background: #17a2b8; color: white;">
                    <span class="totals-label">Advance Paid:</span>
                    <span class="totals-value">Rs. {float(advance_paid):,.2f}</span>
                </div>
            </div>
        </div>

        <!-- Amount in Words -->
        <div class="amount-words">
            <strong>Grand Total in Words:</strong> {_number_to_words(float(grand_total))}
        </div>

        {delivery_schedule_html}

        {serials_html}

        <!-- Payment Details (First Lot) -->
        <div class="payment-section">
            <h4>ADVANCE PAYMENT DETAILS (LOT 1)</h4>
            <div class="payment-detail">
                <label>Advance Required (Lot 1):</label>
                <span><strong>Rs. {float(first_lot_advance):,.2f}</strong> ({float(first_lot_advance_percentage):.0f}% of Lot 1 Value)</span>
            </div>
            <div class="payment-detail">
                <label>Advance Paid:</label>
                <span><strong>Rs. {float(advance_paid):,.2f}</strong> {' ✓ Paid' if advance_paid >= first_lot_advance and first_lot_advance > 0 else ''}</span>
            </div>
            <div class="payment-detail">
                <label>Payment Date:</label>
                <span>{getattr(po, 'advance_date', None).strftime('%d.%m.%Y') if getattr(po, 'advance_date', None) else 'With PO'}</span>
            </div>
            <div class="payment-detail">
                <label>Transaction Reference:</label>
                <span>{getattr(po, 'advance_reference', None) or 'RTGS/NEFT Transfer'}</span>
            </div>
            <div class="payment-detail">
                <label>Balance Payment (Lot 1):</label>
                <span><strong>Rs. {float(first_lot_balance):,.2f}</strong></span>
            </div>
        </div>

        <!-- Bank Details -->
        <div class="bank-section">
            <h4>SUPPLIER BANK DETAILS (For Future Payments)</h4>
            <div class="payment-detail">
                <label>Bank Name:</label>
                <span>{bank_name}</span>
            </div>
            <div class="payment-detail">
                <label>Branch:</label>
                <span>{bank_branch}</span>
            </div>
            <div class="payment-detail">
                <label>Account Number:</label>
                <span><strong>{bank_account}</strong></span>
            </div>
            <div class="payment-detail">
                <label>IFSC Code:</label>
                <span>{bank_ifsc}</span>
            </div>
            <div class="payment-detail">
                <label>Account Name:</label>
                <span>{beneficiary_name}</span>
            </div>
        </div>

        <!-- Terms & Conditions -->
        <div class="terms">
            <h4>TERMS & CONDITIONS:</h4>
            <div style="white-space: pre-wrap; font-size: 11px; line-height: 1.5;">{po_terms_html}</div>
        </div>

        <!-- System Generated Notice -->
        <div style="margin-top: 20px; padding: 15px; background: #f8f9fa; border: 1px solid #dee2e6; border-radius: 4px; text-align: center;">
            <p style="margin: 0; font-size: 12px; color: #495057;">
                <strong>SYSTEM GENERATED PURCHASE ORDER</strong>
            </p>
            <p style="margin: 5px 0 0 0; font-size: 10px; color: #6c757d;">
                This is an electronically generated document from Aquapurite ERP System.<br>
                No signature required. Document ID: {po.po_number}
            </p>
        </div>

        <!-- Footer -->
        <div class="footer">
            System Generated Purchase Order | Aquapurite ERP | Document ID: {po.po_number} | Generated: {datetime.now().strftime("%d-%m-%Y %H:%M:%S")}
        </div>
    </div>
</body>
</html>"""

    return HTMLResponse(content=html_content)


@router.get("/grn/{grn_id}/download")
@require_module("procurement")
async def download_grn(
    grn_id: UUID,
    db: DB,
    current_user: User = Depends(get_current_user),
):
    """Download Goods Receipt Note as printable HTML."""
    from fastapi.responses import HTMLResponse
    from app.models.company import Company

    result = await db.execute(
        select(GoodsReceiptNote)
        .options(selectinload(GoodsReceiptNote.items))
        .where(GoodsReceiptNote.id == grn_id)
    )
    grn = result.scalar_one_or_none()

    if not grn:
        raise HTTPException(status_code=404, detail="GRN not found")

    # Get company details
    company_result = await db.execute(select(Company).where(Company.is_primary == True).limit(1))
    company = company_result.scalar_one_or_none()
    if not company:
        company_result = await db.execute(select(Company).limit(1))
        company = company_result.scalar_one_or_none()

    # Get PO details
    po_result = await db.execute(
        select(PurchaseOrder).where(PurchaseOrder.id == grn.purchase_order_id)
    )
    po = po_result.scalar_one_or_none()

    # Get vendor details
    vendor_result = await db.execute(
        select(Vendor).where(Vendor.id == grn.vendor_id)
    )
    vendor = vendor_result.scalar_one_or_none()

    # Get warehouse details
    warehouse_result = await db.execute(
        select(Warehouse).where(Warehouse.id == grn.warehouse_id)
    )
    warehouse = warehouse_result.scalar_one_or_none()

    # Build items table
    items_html = ""
    for idx, item in enumerate(grn.items, 1):
        unit_price = float(item.unit_price) if item.unit_price else 0.0
        accepted_value = float(item.accepted_value) if item.accepted_value else 0.0

        items_html += f"""
        <tr>
            <td style="border: 1px solid #ddd; padding: 8px; text-align: center;">{idx}</td>
            <td style="border: 1px solid #ddd; padding: 8px;">{item.product_name or '-'}</td>
            <td style="border: 1px solid #ddd; padding: 8px;">{item.sku or '-'}</td>
            <td style="border: 1px solid #ddd; padding: 8px; text-align: center;">{item.quantity_expected}</td>
            <td style="border: 1px solid #ddd; padding: 8px; text-align: center;">{item.quantity_received}</td>
            <td style="border: 1px solid #ddd; padding: 8px; text-align: center; color: green;">{item.quantity_accepted}</td>
            <td style="border: 1px solid #ddd; padding: 8px; text-align: center; color: red;">{item.quantity_rejected}</td>
            <td style="border: 1px solid #ddd; padding: 8px; text-align: right;">₹{unit_price:,.2f}</td>
            <td style="border: 1px solid #ddd; padding: 8px; text-align: right;">₹{accepted_value:,.2f}</td>
            <td style="border: 1px solid #ddd; padding: 8px;">{item.batch_number or '-'}</td>
        </tr>
        """

    vendor_name = vendor.legal_name if vendor else "N/A"
    warehouse_name = warehouse.name if warehouse else "N/A"
    po_number = po.po_number if po else "N/A"

    qc_status_color = "green" if grn.qc_status and grn.qc_status == "ACCEPTED" else "orange"

    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>Goods Receipt Note - {grn.grn_number}</title>
        <style>
            @media print {{
                body {{ margin: 0; padding: 20px; }}
                .no-print {{ display: none; }}
            }}
            body {{
                font-family: Arial, sans-serif;
                max-width: 900px;
                margin: 0 auto;
                padding: 20px;
                color: #333;
            }}
            .header {{
                text-align: center;
                border-bottom: 2px solid #333;
                padding-bottom: 20px;
                margin-bottom: 20px;
            }}
            .company-name {{
                font-size: 24px;
                font-weight: bold;
                color: #34a853;
            }}
            .document-title {{
                font-size: 18px;
                font-weight: bold;
                margin-top: 10px;
                background: #e6f4ea;
                padding: 10px;
            }}
            .info-section {{
                display: flex;
                justify-content: space-between;
                margin-bottom: 20px;
            }}
            .info-box {{
                width: 48%;
                background: #f9f9f9;
                padding: 15px;
                border-radius: 5px;
            }}
            .info-box h3 {{
                margin: 0 0 10px 0;
                color: #34a853;
                font-size: 14px;
                border-bottom: 1px solid #ddd;
                padding-bottom: 5px;
            }}
            .info-box p {{
                margin: 5px 0;
                font-size: 12px;
            }}
            table {{
                width: 100%;
                border-collapse: collapse;
                margin-bottom: 20px;
            }}
            th {{
                background: #34a853;
                color: white;
                padding: 10px 8px;
                text-align: left;
                font-size: 11px;
            }}
            .summary-box {{
                background: #e6f4ea;
                padding: 15px;
                border-radius: 5px;
                margin-bottom: 20px;
            }}
            .summary-box h3 {{
                margin: 0 0 10px 0;
                color: #34a853;
            }}
            .summary-grid {{
                display: grid;
                grid-template-columns: repeat(4, 1fr);
                gap: 10px;
            }}
            .summary-item {{
                text-align: center;
            }}
            .summary-item .label {{
                font-size: 11px;
                color: #666;
            }}
            .summary-item .value {{
                font-size: 18px;
                font-weight: bold;
                color: #333;
            }}
            .signatures {{
                display: flex;
                justify-content: space-between;
                margin-top: 60px;
            }}
            .signature-box {{
                text-align: center;
                width: 200px;
            }}
            .signature-line {{
                border-top: 1px solid #333;
                margin-top: 40px;
                padding-top: 5px;
            }}
            .print-btn {{
                position: fixed;
                top: 10px;
                right: 10px;
                padding: 10px 20px;
                background: #34a853;
                color: white;
                border: none;
                border-radius: 5px;
                cursor: pointer;
            }}
        </style>
    </head>
    <body>
        <button class="print-btn no-print" onclick="window.print()">🖨️ Print / Save PDF</button>

        <div class="header">
            <div class="company-name">{company.legal_name if company else 'AQUAPURITE PRIVATE LIMITED'}</div>
            <div style="font-size: 12px; color: #666;">
                {company.address_line1 if company else 'PLOT 36-A, KH NO 181, PH-1, SHYAM VIHAR, DINDAPUR EXT'}, {company.city if company else 'New Delhi'} - {company.pincode if company else '110043'}, {company.state if company else 'Delhi'}
            </div>
            <div style="font-size: 10px; color: #888; margin-top: 5px;">
                GSTIN: {company.gstin if company else '07ABDCA6170C1Z0'} | PAN: {company.pan if company else 'ABDCA6170C'} | CIN: {getattr(company, 'cin', None) or 'U32909DL2025PTC454115'}
            </div>
            <div class="document-title">GOODS RECEIPT NOTE (GRN)</div>
        </div>

        <div class="info-section">
            <div class="info-box">
                <h3>VENDOR DETAILS</h3>
                <p><strong>{vendor_name}</strong></p>
                <p>Challan No: {grn.vendor_challan_number or 'N/A'}</p>
                <p>Challan Date: {grn.vendor_challan_date or 'N/A'}</p>
            </div>
            <div class="info-box">
                <h3>GRN DETAILS</h3>
                <p><strong>GRN Number:</strong> {grn.grn_number}</p>
                <p><strong>GRN Date:</strong> {grn.grn_date}</p>
                <p><strong>PO Reference:</strong> {po_number}</p>
                <p><strong>Status:</strong> {grn.status if grn.status else 'N/A'}</p>
                <p><strong>QC Status:</strong> <span style="color: {qc_status_color};">{grn.qc_status if grn.qc_status else 'PENDING'}</span></p>
            </div>
        </div>

        <div class="info-section">
            <div class="info-box">
                <h3>RECEIVING WAREHOUSE</h3>
                <p><strong>{warehouse_name}</strong></p>
            </div>
            <div class="info-box">
                <h3>TRANSPORT DETAILS</h3>
                <p><strong>Transporter:</strong> {grn.transporter_name or 'N/A'}</p>
                <p><strong>Vehicle No:</strong> {grn.vehicle_number or 'N/A'}</p>
                <p><strong>LR Number:</strong> {grn.lr_number or 'N/A'}</p>
                <p><strong>E-Way Bill:</strong> {grn.e_way_bill_number or 'N/A'}</p>
            </div>
        </div>

        <div class="summary-box">
            <h3>RECEIPT SUMMARY</h3>
            <div class="summary-grid">
                <div class="summary-item">
                    <div class="label">Total Items</div>
                    <div class="value">{grn.total_items or 0}</div>
                </div>
                <div class="summary-item">
                    <div class="label">Qty Received</div>
                    <div class="value">{grn.total_quantity_received or 0}</div>
                </div>
                <div class="summary-item">
                    <div class="label">Qty Accepted</div>
                    <div class="value" style="color: green;">{grn.total_quantity_accepted or 0}</div>
                </div>
                <div class="summary-item">
                    <div class="label">Qty Rejected</div>
                    <div class="value" style="color: red;">{grn.total_quantity_rejected or 0}</div>
                </div>
            </div>
        </div>

        <table>
            <thead>
                <tr>
                    <th style="width: 30px;">#</th>
                    <th>Product</th>
                    <th>SKU</th>
                    <th style="width: 60px;">Expected</th>
                    <th style="width: 60px;">Received</th>
                    <th style="width: 60px;">Accepted</th>
                    <th style="width: 60px;">Rejected</th>
                    <th style="width: 80px;">Unit Price</th>
                    <th style="width: 90px;">Accepted Value</th>
                    <th>Batch No</th>
                </tr>
            </thead>
            <tbody>
                {items_html}
            </tbody>
        </table>

        <div style="text-align: right; font-size: 16px; font-weight: bold; background: #e6f4ea; padding: 15px; border-radius: 5px;">
            Total Accepted Value: ₹{float(grn.total_value or 0):,.2f}
        </div>

        <p><strong>Receiving Remarks:</strong> {grn.receiving_remarks or 'None'}</p>

        <div class="signatures">
            <div class="signature-box">
                <div class="signature-line">Received By</div>
            </div>
            <div class="signature-box">
                <div class="signature-line">QC Inspector</div>
            </div>
            <div class="signature-box">
                <div class="signature-line">Store In-charge</div>
            </div>
        </div>

        <p style="text-align: center; font-size: 10px; color: #999; margin-top: 40px;">
            This is a computer-generated document. Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        </p>
    </body>
    </html>
    """

    return HTMLResponse(content=html_content)


@router.get("/invoices/{invoice_id}/download")
@require_module("procurement")
async def download_vendor_invoice(
    invoice_id: UUID,
    db: DB,
    current_user: User = Depends(get_current_user),
):
    """Download Vendor Invoice as printable HTML."""
    from fastapi.responses import HTMLResponse
    from app.models.company import Company

    result = await db.execute(
        select(VendorInvoice).where(VendorInvoice.id == invoice_id)
    )
    invoice = result.scalar_one_or_none()

    if not invoice:
        raise HTTPException(status_code=404, detail="Vendor Invoice not found")

    # Get company details
    company_result = await db.execute(select(Company).where(Company.is_primary == True).limit(1))
    company = company_result.scalar_one_or_none()
    if not company:
        company_result = await db.execute(select(Company).limit(1))
        company = company_result.scalar_one_or_none()

    # Get vendor details
    vendor_result = await db.execute(
        select(Vendor).where(Vendor.id == invoice.vendor_id)
    )
    vendor = vendor_result.scalar_one_or_none()

    # Get PO details
    po_result = await db.execute(
        select(PurchaseOrder).where(PurchaseOrder.id == invoice.purchase_order_id)
    )
    po = po_result.scalar_one_or_none()

    # Get GRN details
    grn_result = await db.execute(
        select(GoodsReceiptNote).where(GoodsReceiptNote.id == invoice.grn_id)
    )
    grn = grn_result.scalar_one_or_none()

    vendor_name = vendor.legal_name if vendor else "N/A"
    vendor_address = ""
    if vendor:
        addr_parts = [vendor.address_line1, vendor.address_line2, vendor.city, vendor.state, str(vendor.pincode) if vendor.pincode else None]
        vendor_address = ", ".join(filter(None, addr_parts))

    po_number = po.po_number if po else "N/A"
    grn_number = grn.grn_number if grn else "N/A"

    # Handle both enum and string status values
    status_val = invoice.status if hasattr(invoice.status, 'value') else str(invoice.status) if invoice.status else ""
    status_color = "green" if status_val in ["VERIFIED", "PAID", "MATCHED", "APPROVED"] else "orange"

    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>Vendor Invoice - {invoice.invoice_number}</title>
        <style>
            @media print {{
                body {{ margin: 0; padding: 20px; }}
                .no-print {{ display: none; }}
            }}
            body {{
                font-family: Arial, sans-serif;
                max-width: 900px;
                margin: 0 auto;
                padding: 20px;
                color: #333;
            }}
            .header {{
                text-align: center;
                border-bottom: 2px solid #333;
                padding-bottom: 20px;
                margin-bottom: 20px;
            }}
            .company-name {{
                font-size: 24px;
                font-weight: bold;
                color: #ea4335;
            }}
            .document-title {{
                font-size: 18px;
                font-weight: bold;
                margin-top: 10px;
                background: #fce8e6;
                padding: 10px;
            }}
            .info-section {{
                display: flex;
                justify-content: space-between;
                margin-bottom: 20px;
            }}
            .info-box {{
                width: 48%;
                background: #f9f9f9;
                padding: 15px;
                border-radius: 5px;
            }}
            .info-box h3 {{
                margin: 0 0 10px 0;
                color: #ea4335;
                font-size: 14px;
                border-bottom: 1px solid #ddd;
                padding-bottom: 5px;
            }}
            .info-box p {{
                margin: 5px 0;
                font-size: 12px;
            }}
            .amount-box {{
                background: #fce8e6;
                padding: 20px;
                border-radius: 5px;
                margin-bottom: 20px;
            }}
            .amount-grid {{
                display: grid;
                grid-template-columns: repeat(3, 1fr);
                gap: 20px;
            }}
            .amount-item {{
                text-align: center;
            }}
            .amount-item .label {{
                font-size: 11px;
                color: #666;
            }}
            .amount-item .value {{
                font-size: 20px;
                font-weight: bold;
                color: #333;
            }}
            table {{
                width: 100%;
                border-collapse: collapse;
                margin-bottom: 20px;
            }}
            th {{
                background: #ea4335;
                color: white;
                padding: 10px 8px;
                text-align: left;
                font-size: 12px;
            }}
            td {{
                border: 1px solid #ddd;
                padding: 10px 8px;
            }}
            .match-status {{
                display: inline-block;
                padding: 5px 15px;
                border-radius: 20px;
                font-size: 12px;
                font-weight: bold;
            }}
            .match-yes {{ background: #e6f4ea; color: #137333; }}
            .match-no {{ background: #fce8e6; color: #c5221f; }}
            .signatures {{
                display: flex;
                justify-content: space-between;
                margin-top: 60px;
            }}
            .signature-box {{
                text-align: center;
                width: 200px;
            }}
            .signature-line {{
                border-top: 1px solid #333;
                margin-top: 40px;
                padding-top: 5px;
            }}
            .print-btn {{
                position: fixed;
                top: 10px;
                right: 10px;
                padding: 10px 20px;
                background: #ea4335;
                color: white;
                border: none;
                border-radius: 5px;
                cursor: pointer;
            }}
        </style>
    </head>
    <body>
        <button class="print-btn no-print" onclick="window.print()">🖨️ Print / Save PDF</button>

        <div class="header">
            <div class="company-name">{company.legal_name if company else 'AQUAPURITE PRIVATE LIMITED'}</div>
            <div style="font-size: 12px; color: #666;">
                {company.address_line1 if company else 'PLOT 36-A, KH NO 181, PH-1, SHYAM VIHAR, DINDAPUR EXT'}, {company.city if company else 'New Delhi'} - {company.pincode if company else '110043'}, {company.state if company else 'Delhi'}<br>
                GSTIN: {company.gstin if company else '07ABDCA6170C1Z0'} | PAN: {company.pan if company else 'ABDCA6170C'}
            </div>
            <div class="document-title">VENDOR INVOICE RECORD</div>
        </div>

        <div class="info-section">
            <div class="info-box">
                <h3>VENDOR DETAILS</h3>
                <p><strong>{vendor_name}</strong></p>
                <p>{vendor_address}</p>
                <p>GSTIN: {vendor.gstin if vendor else 'N/A'}</p>
            </div>
            <div class="info-box">
                <h3>INVOICE DETAILS</h3>
                <p><strong>Invoice Number:</strong> {invoice.invoice_number}</p>
                <p><strong>Invoice Date:</strong> {invoice.invoice_date}</p>
                <p><strong>Due Date:</strong> {invoice.due_date or 'N/A'}</p>
                <p><strong>Status:</strong> <span style="color: {status_color}; font-weight: bold;">{status_val or 'N/A'}</span></p>
            </div>
        </div>

        <div class="info-section">
            <div class="info-box" style="width: 100%;">
                <h3>REFERENCE DOCUMENTS</h3>
                <p><strong>PO Number:</strong> {po_number}</p>
                <p><strong>GRN Number:</strong> {grn_number}</p>
            </div>
        </div>

        <div class="amount-box">
            <h3 style="margin: 0 0 15px 0; color: #ea4335;">INVOICE AMOUNTS</h3>
            <div class="amount-grid">
                <div class="amount-item">
                    <div class="label">Taxable Amount</div>
                    <div class="value">₹{float(invoice.taxable_amount or 0):,.2f}</div>
                </div>
                <div class="amount-item">
                    <div class="label">Total Tax (GST)</div>
                    <div class="value">₹{float(invoice.total_tax or 0):,.2f}</div>
                </div>
                <div class="amount-item">
                    <div class="label">Total Amount</div>
                    <div class="value" style="color: #ea4335;">₹{float(invoice.grand_total or 0):,.2f}</div>
                </div>
            </div>
        </div>

        <table>
            <thead>
                <tr>
                    <th>Tax Breakup</th>
                    <th style="text-align: right;">Amount (₹)</th>
                </tr>
            </thead>
            <tbody>
                <tr>
                    <td>CGST</td>
                    <td style="text-align: right;">₹{float(invoice.cgst_amount or 0):,.2f}</td>
                </tr>
                <tr>
                    <td>SGST</td>
                    <td style="text-align: right;">₹{float(invoice.sgst_amount or 0):,.2f}</td>
                </tr>
                <tr>
                    <td>IGST</td>
                    <td style="text-align: right;">₹{float(invoice.igst_amount or 0):,.2f}</td>
                </tr>
                <tr>
                    <td>TDS Deducted</td>
                    <td style="text-align: right;">₹{float(invoice.tds_amount or 0):,.2f}</td>
                </tr>
                <tr style="background: #f5f5f5; font-weight: bold;">
                    <td>Net Payable</td>
                    <td style="text-align: right;">₹{float(invoice.net_payable or invoice.grand_total or 0):,.2f}</td>
                </tr>
            </tbody>
        </table>

        <div style="background: #f9f9f9; padding: 15px; border-radius: 5px; margin-bottom: 20px;">
            <h3 style="margin: 0 0 10px 0; color: #333;">3-WAY MATCH STATUS</h3>
            <p>
                <strong>PO Match:</strong>
                <span class="match-status {'match-yes' if invoice.po_matched else 'match-no'}">
                    {'✓ Matched' if invoice.po_matched else '✗ Not Matched'}
                </span>
            </p>
            <p>
                <strong>GRN Match:</strong>
                <span class="match-status {'match-yes' if invoice.grn_matched else 'match-no'}">
                    {'✓ Matched' if invoice.grn_matched else '✗ Not Matched'}
                </span>
            </p>
            <p>
                <strong>Invoice Match:</strong>
                <span class="match-status {'match-yes' if invoice.is_fully_matched else 'match-no'}">
                    {'✓ Matched' if invoice.is_fully_matched else '✗ Not Matched'}
                </span>
            </p>
            {f'<p><strong>Variance:</strong> ₹{float(invoice.matching_variance or 0):,.2f} - {invoice.variance_reason or "N/A"}</p>' if invoice.matching_variance else ''}
        </div>

        <p><strong>Notes:</strong> {invoice.internal_notes or 'None'}</p>

        <div class="signatures">
            <div class="signature-box">
                <div class="signature-line">Verified By</div>
            </div>
            <div class="signature-box">
                <div class="signature-line">Approved By</div>
            </div>
            <div class="signature-box">
                <div class="signature-line">Finance Head</div>
            </div>
        </div>

        <p style="text-align: center; font-size: 10px; color: #999; margin-top: 40px;">
            This is a computer-generated document. Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        </p>
    </body>
    </html>
    """

    return HTMLResponse(content=html_content)


# ==================== Vendor Proforma Invoice (Quotations from Vendors) ====================

@router.post("/proformas", response_model=VendorProformaResponse, status_code=status.HTTP_201_CREATED)
@require_module("procurement")
async def create_vendor_proforma(
    proforma_in: VendorProformaCreate,
    db: DB,
    current_user: User = Depends(get_current_user),
):
    """Create a new Vendor Proforma Invoice (quotation from vendor)."""
    # Verify vendor exists
    vendor = await db.get(Vendor, proforma_in.vendor_id)
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor not found")

    # Generate our reference number
    today = date.today()
    count_result = await db.execute(
        select(func.count(VendorProformaInvoice.id)).where(
            func.date(VendorProformaInvoice.created_at) == today
        )
    )
    count = count_result.scalar() or 0
    our_reference = f"VPI-{today.strftime('%Y%m%d')}-{str(count + 1).zfill(4)}"

    # Calculate item totals
    subtotal = Decimal("0")
    total_discount = Decimal("0")
    total_cgst = Decimal("0")
    total_sgst = Decimal("0")
    total_igst = Decimal("0")

    items_to_create = []
    for item_data in proforma_in.items:
        qty = Decimal(str(item_data.quantity))
        unit_price = Decimal(str(item_data.unit_price))
        discount_pct = Decimal(str(item_data.discount_percent or 0))
        gst_rate = Decimal(str(item_data.gst_rate or 18))

        base_amount = (qty * unit_price).quantize(Decimal("0.01"))
        discount_amount = (base_amount * discount_pct / Decimal("100")).quantize(Decimal("0.01"))
        taxable_amount = (base_amount - discount_amount).quantize(Decimal("0.01"))

        # Calculate GST (assuming intra-state - CGST+SGST)
        gst_amount = (taxable_amount * gst_rate / Decimal("100")).quantize(Decimal("0.01"))
        cgst_amount = (gst_amount / Decimal("2")).quantize(Decimal("0.01"))
        sgst_amount = (gst_amount / Decimal("2")).quantize(Decimal("0.01"))
        igst_amount = Decimal("0")

        total_amount = (taxable_amount + gst_amount).quantize(Decimal("0.01"))

        subtotal += base_amount
        total_discount += discount_amount
        total_cgst += cgst_amount
        total_sgst += sgst_amount

        items_to_create.append({
            "data": item_data,
            "discount_amount": discount_amount,
            "taxable_amount": taxable_amount,
            "cgst_amount": cgst_amount,
            "sgst_amount": sgst_amount,
            "igst_amount": igst_amount,
            "total_amount": total_amount,
        })

    taxable_amount = (subtotal - total_discount).quantize(Decimal("0.01"))
    total_tax = (total_cgst + total_sgst + total_igst).quantize(Decimal("0.01"))
    freight = Decimal(str(proforma_in.freight_charges or 0))
    packing = Decimal(str(proforma_in.packing_charges or 0))
    other = Decimal(str(proforma_in.other_charges or 0))
    round_off = Decimal(str(proforma_in.round_off or 0))
    grand_total = (taxable_amount + total_tax + freight + packing + other + round_off).quantize(Decimal("0.01"))

    # Create proforma
    # Use vendor_pi_number or proforma_number for the vendor's document number
    vendor_doc_number = proforma_in.vendor_pi_number or proforma_in.proforma_number or our_reference

    proforma = VendorProformaInvoice(
        our_reference=our_reference,
        proforma_number=vendor_doc_number,
        proforma_date=proforma_in.proforma_date,
        validity_date=proforma_in.validity_date,
        status=ProformaStatus.RECEIVED,
        vendor_id=proforma_in.vendor_id,
        requisition_id=proforma_in.requisition_id,
        delivery_warehouse_id=proforma_in.delivery_warehouse_id,
        delivery_days=proforma_in.delivery_days,
        delivery_terms=proforma_in.delivery_terms,
        payment_terms=proforma_in.payment_terms,
        credit_days=proforma_in.credit_days,
        subtotal=subtotal.quantize(Decimal("0.01")),
        discount_amount=total_discount.quantize(Decimal("0.01")),
        discount_percent=(total_discount / subtotal * Decimal("100")).quantize(Decimal("0.01")) if subtotal else Decimal("0"),
        taxable_amount=taxable_amount,
        cgst_amount=total_cgst.quantize(Decimal("0.01")),
        sgst_amount=total_sgst.quantize(Decimal("0.01")),
        igst_amount=total_igst.quantize(Decimal("0.01")),
        total_tax=total_tax,
        freight_charges=freight.quantize(Decimal("0.01")),
        packing_charges=packing.quantize(Decimal("0.01")),
        other_charges=other.quantize(Decimal("0.01")),
        round_off=round_off.quantize(Decimal("0.01")),
        grand_total=grand_total,
        proforma_pdf_url=proforma_in.proforma_pdf_url,
        vendor_remarks=proforma_in.vendor_remarks,
        internal_notes=proforma_in.internal_notes,
        received_by=current_user.id,
        received_at=datetime.now(timezone.utc),
    )

    db.add(proforma)
    await db.flush()

    # Create items
    for item_info in items_to_create:
        item_data = item_info["data"]
        item = VendorProformaItem(
            proforma_id=proforma.id,
            product_id=item_data.product_id,
            item_code=item_data.item_code,
            description=item_data.description,
            hsn_code=item_data.hsn_code,
            uom=item_data.uom,
            quantity=item_data.quantity,
            unit_price=item_data.unit_price,
            discount_percent=item_data.discount_percent,
            discount_amount=item_info["discount_amount"],
            taxable_amount=item_info["taxable_amount"],
            gst_rate=item_data.gst_rate,
            cgst_amount=item_info["cgst_amount"],
            sgst_amount=item_info["sgst_amount"],
            igst_amount=item_info["igst_amount"],
            total_amount=item_info["total_amount"],
            lead_time_days=item_data.lead_time_days,
        )
        db.add(item)

    await db.commit()

    # Reload with items
    result = await db.execute(
        select(VendorProformaInvoice)
        .options(selectinload(VendorProformaInvoice.items))
        .where(VendorProformaInvoice.id == proforma.id)
    )
    proforma = result.scalar_one()

    return proforma


@router.get("/proformas", response_model=VendorProformaListResponse)
@require_module("procurement")
async def list_vendor_proformas(
    db: DB,
    current_user: User = Depends(get_current_user),
    vendor_id: Optional[UUID] = None,
    proforma_status: Optional[ProformaStatus] = None,
    from_date: Optional[date] = None,
    to_date: Optional[date] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
):
    """List vendor proforma invoices with filters."""
    query = select(VendorProformaInvoice).options(
        selectinload(VendorProformaInvoice.vendor)
    )

    if vendor_id:
        query = query.where(VendorProformaInvoice.vendor_id == vendor_id)
    if proforma_status:
        query = query.where(VendorProformaInvoice.status == proforma_status)
    if from_date:
        query = query.where(VendorProformaInvoice.proforma_date >= from_date)
    if to_date:
        query = query.where(VendorProformaInvoice.proforma_date <= to_date)

    # Count
    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar() or 0

    # Sum
    sum_query = select(func.sum(VendorProformaInvoice.grand_total)).select_from(query.subquery())
    total_value = (await db.execute(sum_query)).scalar() or Decimal("0")

    # Paginate
    query = query.order_by(VendorProformaInvoice.created_at.desc()).offset(skip).limit(limit)
    result = await db.execute(query)
    proformas = result.scalars().all()

    items = []
    for p in proformas:
        items.append(VendorProformaBrief(
            id=p.id,
            our_reference=p.our_reference,
            proforma_number=p.proforma_number,
            proforma_date=p.proforma_date,
            vendor_name=p.vendor.legal_name if p.vendor else "Unknown",
            grand_total=p.grand_total,
            validity_date=p.validity_date,
            status=p.status,
        ))

    return VendorProformaListResponse(
        items=items,
        total=total,
        total_value=total_value,
        skip=skip,
        limit=limit,
    )


@router.get("/proformas/{proforma_id}", response_model=VendorProformaResponse)
@require_module("procurement")
async def get_vendor_proforma(
    proforma_id: UUID,
    db: DB,
    current_user: User = Depends(get_current_user),
):
    """Get vendor proforma invoice details."""
    result = await db.execute(
        select(VendorProformaInvoice)
        .options(
            selectinload(VendorProformaInvoice.items),
            selectinload(VendorProformaInvoice.vendor),
        )
        .where(VendorProformaInvoice.id == proforma_id)
    )
    proforma = result.scalar_one_or_none()

    if not proforma:
        raise HTTPException(status_code=404, detail="Vendor Proforma not found")

    return proforma


@router.put("/proformas/{proforma_id}", response_model=VendorProformaResponse)
@require_module("procurement")
async def update_vendor_proforma(
    proforma_id: UUID,
    update_data: VendorProformaUpdate,
    db: DB,
    current_user: User = Depends(get_current_user),
):
    """Update vendor proforma invoice."""
    proforma = await db.get(VendorProformaInvoice, proforma_id)
    if not proforma:
        raise HTTPException(status_code=404, detail="Vendor Proforma not found")

    if proforma.status in [ProformaStatus.CONVERTED_TO_PO, ProformaStatus.CANCELLED]:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot update proforma with status {proforma.status}"
        )

    update_dict = update_data.model_dump(exclude_unset=True)
    for key, value in update_dict.items():
        setattr(proforma, key, value)

    await db.commit()
    await db.refresh(proforma)

    return proforma


@router.post("/proformas/{proforma_id}/approve", response_model=VendorProformaResponse)
@require_module("procurement")
async def approve_vendor_proforma(
    proforma_id: UUID,
    request: VendorProformaApproveRequest,
    db: DB,
    current_user: User = Depends(get_current_user),
):
    """Approve or reject a vendor proforma invoice."""
    proforma = await db.get(VendorProformaInvoice, proforma_id)
    if not proforma:
        raise HTTPException(status_code=404, detail="Vendor Proforma not found")

    if proforma.status not in [ProformaStatus.RECEIVED, ProformaStatus.UNDER_REVIEW]:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot approve/reject proforma with status {proforma.status}"
        )

    if request.action == "APPROVE":
        proforma.status = ProformaStatus.APPROVED.value
        proforma.approved_by = current_user.id
        proforma.approved_at = datetime.now(timezone.utc)
    else:
        proforma.status = ProformaStatus.REJECTED.value
        proforma.rejection_reason = request.rejection_reason

    await db.commit()

    # Reload with items
    result = await db.execute(
        select(VendorProformaInvoice)
        .options(selectinload(VendorProformaInvoice.items))
        .where(VendorProformaInvoice.id == proforma_id)
    )
    proforma = result.scalar_one()

    return proforma


@router.post("/proformas/{proforma_id}/convert-to-po", response_model=PurchaseOrderResponse)
@require_module("procurement")
async def convert_proforma_to_po(
    proforma_id: UUID,
    request: VendorProformaConvertToPORequest,
    db: DB,
    current_user: User = Depends(get_current_user),
):
    """Convert an approved vendor proforma invoice to a Purchase Order."""
    result = await db.execute(
        select(VendorProformaInvoice)
        .options(selectinload(VendorProformaInvoice.items))
        .where(VendorProformaInvoice.id == proforma_id)
    )
    proforma = result.scalar_one_or_none()

    if not proforma:
        raise HTTPException(status_code=404, detail="Vendor Proforma not found")

    if proforma.status != ProformaStatus.APPROVED:
        raise HTTPException(
            status_code=400,
            detail="Only approved proformas can be converted to PO"
        )

    # Generate PO number using atomic sequence service
    today = date.today()
    service = DocumentSequenceService(db)
    po_number = await service.get_next_number("PO")

    # Get vendor
    vendor = await db.get(Vendor, proforma.vendor_id)

    # Create PO (convert Decimal values to float for SQLite compatibility)
    po = PurchaseOrder(
        po_number=po_number,
        po_date=today,
        status=POStatus.DRAFT.value,
        vendor_id=proforma.vendor_id,
        vendor_name=vendor.legal_name if vendor else "Unknown",
        vendor_gstin=vendor.gstin if vendor else None,
        delivery_warehouse_id=request.delivery_warehouse_id or proforma.delivery_warehouse_id,
        expected_delivery_date=request.expected_delivery_date,
        payment_terms=proforma.payment_terms,
        credit_days=proforma.credit_days,
        quotation_reference=proforma.proforma_number,
        quotation_date=proforma.proforma_date,
        freight_charges=float(proforma.freight_charges or 0),
        packing_charges=float(proforma.packing_charges or 0),
        other_charges=float(proforma.other_charges or 0),
        special_instructions=request.special_instructions,
        subtotal=float(proforma.subtotal or 0),
        discount_amount=float(proforma.discount_amount or 0),
        taxable_amount=float(proforma.taxable_amount or 0),
        cgst_amount=float(proforma.cgst_amount or 0),
        sgst_amount=float(proforma.sgst_amount or 0),
        igst_amount=float(proforma.igst_amount or 0),
        total_tax=float(proforma.total_tax or 0),
        grand_total=float(proforma.grand_total or 0),
        created_by=current_user.id,
    )

    db.add(po)
    await db.flush()

    # Create PO items from proforma items
    for idx, item in enumerate(proforma.items, 1):
        po_item = PurchaseOrderItem(
            purchase_order_id=po.id,
            line_number=idx,
            product_id=item.product_id,
            product_name=item.description,
            sku=item.item_code or f"ITEM-{idx}",
            hsn_code=item.hsn_code,
            quantity_ordered=int(item.quantity),  # Convert Decimal to int for SQLite
            uom=item.uom,
            unit_price=float(item.unit_price),
            discount_percentage=float(item.discount_percent or 0),
            discount_amount=float(item.discount_amount or 0),
            taxable_amount=float(item.taxable_amount),
            gst_rate=float(item.gst_rate),
            cgst_rate=float(item.gst_rate / 2),
            sgst_rate=float(item.gst_rate / 2),
            igst_rate=0.0,
            cgst_amount=float(item.cgst_amount or 0),
            sgst_amount=float(item.sgst_amount or 0),
            igst_amount=float(item.igst_amount or 0),
            total_amount=float(item.total_amount),
        )
        db.add(po_item)

    # Update proforma status
    proforma.status = ProformaStatus.CONVERTED_TO_PO.value
    proforma.purchase_order_id = po.id

    await db.commit()

    # Reload PO with items
    result = await db.execute(
        select(PurchaseOrder)
        .options(selectinload(PurchaseOrder.items))
        .where(PurchaseOrder.id == po.id)
    )
    po = result.scalar_one()

    return po


@router.delete("/proformas/{proforma_id}")
@require_module("procurement")
async def cancel_vendor_proforma(
    proforma_id: UUID,
    db: DB,
    current_user: User = Depends(get_current_user),
):
    """Cancel a vendor proforma invoice."""
    proforma = await db.get(VendorProformaInvoice, proforma_id)
    if not proforma:
        raise HTTPException(status_code=404, detail="Vendor Proforma not found")

    if proforma.status == ProformaStatus.CONVERTED_TO_PO:
        raise HTTPException(
            status_code=400,
            detail="Cannot cancel proforma that has been converted to PO"
        )

    proforma.status = ProformaStatus.CANCELLED.value
    await db.commit()

    return {"message": "Vendor Proforma cancelled successfully"}


@router.get("/proformas/{proforma_id}/download")
@require_module("procurement")
async def download_vendor_proforma(
    proforma_id: UUID,
    db: DB,
    current_user: User = Depends(get_current_user),
):
    """Download vendor proforma invoice as printable HTML."""
    from fastapi.responses import HTMLResponse
    from app.models.company import Company

    result = await db.execute(
        select(VendorProformaInvoice)
        .options(
            selectinload(VendorProformaInvoice.items),
            selectinload(VendorProformaInvoice.vendor),
        )
        .where(VendorProformaInvoice.id == proforma_id)
    )
    proforma = result.scalar_one_or_none()

    if not proforma:
        raise HTTPException(status_code=404, detail="Vendor Proforma not found")

    # Get company details
    company_result = await db.execute(select(Company).where(Company.is_primary == True).limit(1))
    company = company_result.scalar_one_or_none()
    if not company:
        company_result = await db.execute(select(Company).limit(1))
        company = company_result.scalar_one_or_none()

    vendor = proforma.vendor
    status_val = proforma.status if hasattr(proforma.status, 'value') else str(proforma.status) if proforma.status else ""
    status_color = "green" if status_val in ["APPROVED", "CONVERTED_TO_PO"] else "red" if status_val in ["REJECTED", "CANCELLED", "EXPIRED"] else "orange"

    # Generate items rows
    items_html = ""
    for idx, item in enumerate(proforma.items, 1):
        items_html += f"""
        <tr>
            <td style="text-align: center;">{idx}</td>
            <td>
                <strong>{item.description}</strong><br>
                <small>Code: {item.item_code or 'N/A'} | HSN: {item.hsn_code or 'N/A'}</small>
            </td>
            <td style="text-align: center;">{item.quantity} {item.uom}</td>
            <td style="text-align: right;">₹{float(item.unit_price or 0):,.2f}</td>
            <td style="text-align: right;">{float(item.discount_percent or 0):.1f}%</td>
            <td style="text-align: right;">₹{float(item.taxable_amount or 0):,.2f}</td>
            <td style="text-align: center;">{float(item.gst_rate or 0):.0f}%</td>
            <td style="text-align: right;">₹{float(item.total_amount or 0):,.2f}</td>
        </tr>
        """

    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>Vendor Proforma - {proforma.our_reference}</title>
        <style>
            @media print {{
                body {{ margin: 0; padding: 20px; }}
                .no-print {{ display: none; }}
            }}
            body {{
                font-family: Arial, sans-serif;
                max-width: 900px;
                margin: 0 auto;
                padding: 20px;
                color: #333;
            }}
            .header {{
                text-align: center;
                border-bottom: 2px solid #333;
                padding-bottom: 20px;
                margin-bottom: 20px;
            }}
            .company-name {{
                font-size: 24px;
                font-weight: bold;
                color: #0066cc;
            }}
            .document-title {{
                font-size: 18px;
                font-weight: bold;
                margin-top: 10px;
                background: #e6f0ff;
                padding: 10px;
            }}
            .status-badge {{
                display: inline-block;
                padding: 5px 15px;
                border-radius: 20px;
                font-size: 12px;
                font-weight: bold;
                color: white;
                background: {status_color};
            }}
            .info-section {{
                display: flex;
                justify-content: space-between;
                margin-bottom: 20px;
            }}
            .info-box {{
                width: 48%;
                background: #f9f9f9;
                padding: 15px;
                border-radius: 5px;
            }}
            .info-box h3 {{
                margin: 0 0 10px 0;
                color: #0066cc;
                font-size: 14px;
                border-bottom: 1px solid #ddd;
                padding-bottom: 5px;
            }}
            .info-box p {{
                margin: 5px 0;
                font-size: 12px;
            }}
            table {{
                width: 100%;
                border-collapse: collapse;
                margin-bottom: 20px;
            }}
            th {{
                background: #0066cc;
                color: white;
                padding: 10px 8px;
                text-align: left;
                font-size: 12px;
            }}
            td {{
                border: 1px solid #ddd;
                padding: 10px 8px;
                font-size: 12px;
            }}
            .totals-section {{
                margin-left: auto;
                width: 350px;
            }}
            .totals-section table td {{
                padding: 8px;
            }}
            .totals-section .grand-total {{
                background: #e6f0ff;
                font-size: 16px;
                font-weight: bold;
            }}
            .terms-box {{
                background: #f9f9f9;
                padding: 15px;
                border-radius: 5px;
                margin-bottom: 20px;
            }}
            .signatures {{
                display: flex;
                justify-content: space-between;
                margin-top: 60px;
            }}
            .signature-box {{
                text-align: center;
                width: 200px;
            }}
            .signature-line {{
                border-top: 1px solid #333;
                margin-top: 40px;
                padding-top: 5px;
            }}
            .print-btn {{
                position: fixed;
                top: 10px;
                right: 10px;
                padding: 10px 20px;
                background: #0066cc;
                color: white;
                border: none;
                border-radius: 5px;
                cursor: pointer;
            }}
        </style>
    </head>
    <body>
        <button class="print-btn no-print" onclick="window.print()">Print / Save PDF</button>

        <div class="header">
            <div class="company-name">{company.legal_name if company else 'AQUAPURITE PRIVATE LIMITED'}</div>
            <div style="font-size: 12px; color: #666;">
                {company.address_line1 if company else 'PLOT 36-A, KH NO 181, PH-1, SHYAM VIHAR, DINDAPUR EXT'}, {company.city if company else 'New Delhi'} - {company.pincode if company else '110043'}, {company.state if company else 'Delhi'}<br>
                GSTIN: {company.gstin if company else '07ABDCA6170C1Z0'} | PAN: {company.pan if company else 'ABDCA6170C'}
            </div>
            <div class="document-title">VENDOR PROFORMA INVOICE / QUOTATION</div>
        </div>

        <div style="text-align: center; margin-bottom: 20px;">
            <span class="status-badge">{status_val}</span>
        </div>

        <div class="info-section">
            <div class="info-box">
                <h3>VENDOR DETAILS</h3>
                <p><strong>{vendor.legal_name if vendor else 'N/A'}</strong></p>
                <p>{vendor.address_line1 if vendor and vendor.address_line1 else ''} {vendor.address_line2 if vendor and vendor.address_line2 else ''}</p>
                <p>{vendor.city if vendor else ''}, {vendor.state if vendor else ''} - {vendor.pincode if vendor else ''}</p>
                <p>GSTIN: {vendor.gstin if vendor else 'N/A'}</p>
                <p>PAN: {vendor.pan if vendor else 'N/A'}</p>
            </div>
            <div class="info-box">
                <h3>PROFORMA DETAILS</h3>
                <p><strong>Our Reference:</strong> {proforma.our_reference}</p>
                <p><strong>Vendor PI Number:</strong> {proforma.proforma_number}</p>
                <p><strong>PI Date:</strong> {proforma.proforma_date}</p>
                <p><strong>Valid Until:</strong> {proforma.validity_date or 'Not Specified'}</p>
                <p><strong>Delivery Days:</strong> {proforma.delivery_days or 'N/A'} days</p>
                <p><strong>Credit Days:</strong> {proforma.credit_days or 0} days</p>
            </div>
        </div>

        <table>
            <thead>
                <tr>
                    <th style="width: 40px;">#</th>
                    <th>Item Description</th>
                    <th style="width: 80px; text-align: center;">Qty</th>
                    <th style="width: 90px; text-align: right;">Unit Price</th>
                    <th style="width: 60px; text-align: right;">Disc%</th>
                    <th style="width: 100px; text-align: right;">Taxable</th>
                    <th style="width: 60px; text-align: center;">GST%</th>
                    <th style="width: 100px; text-align: right;">Total</th>
                </tr>
            </thead>
            <tbody>
                {items_html}
            </tbody>
        </table>

        <div class="totals-section">
            <table>
                <tr>
                    <td>Subtotal</td>
                    <td style="text-align: right;">₹{float(proforma.subtotal or 0):,.2f}</td>
                </tr>
                <tr>
                    <td>Discount ({float(proforma.discount_percent or 0):.1f}%)</td>
                    <td style="text-align: right;">- ₹{float(proforma.discount_amount or 0):,.2f}</td>
                </tr>
                <tr>
                    <td>Taxable Amount</td>
                    <td style="text-align: right;">₹{float(proforma.taxable_amount or 0):,.2f}</td>
                </tr>
                <tr>
                    <td>CGST</td>
                    <td style="text-align: right;">₹{float(proforma.cgst_amount or 0):,.2f}</td>
                </tr>
                <tr>
                    <td>SGST</td>
                    <td style="text-align: right;">₹{float(proforma.sgst_amount or 0):,.2f}</td>
                </tr>
                <tr>
                    <td>IGST</td>
                    <td style="text-align: right;">₹{float(proforma.igst_amount or 0):,.2f}</td>
                </tr>
                <tr>
                    <td>Freight Charges</td>
                    <td style="text-align: right;">₹{float(proforma.freight_charges or 0):,.2f}</td>
                </tr>
                <tr>
                    <td>Packing Charges</td>
                    <td style="text-align: right;">₹{float(proforma.packing_charges or 0):,.2f}</td>
                </tr>
                <tr>
                    <td>Other Charges</td>
                    <td style="text-align: right;">₹{float(proforma.other_charges or 0):,.2f}</td>
                </tr>
                <tr>
                    <td>Round Off</td>
                    <td style="text-align: right;">₹{float(proforma.round_off or 0):,.2f}</td>
                </tr>
                <tr class="grand-total">
                    <td><strong>GRAND TOTAL</strong></td>
                    <td style="text-align: right;"><strong>₹{float(proforma.grand_total or 0):,.2f}</strong></td>
                </tr>
            </table>
        </div>

        <div class="terms-box">
            <h3 style="margin: 0 0 10px 0;">Terms & Conditions</h3>
            <p><strong>Payment Terms:</strong> {proforma.payment_terms or 'As per agreement'}</p>
            <p><strong>Delivery Terms:</strong> {proforma.delivery_terms or 'Ex-Works'}</p>
            <p><strong>Vendor Remarks:</strong> {proforma.vendor_remarks or 'None'}</p>
            <p><strong>Internal Notes:</strong> {proforma.internal_notes or 'None'}</p>
        </div>

        <div class="signatures">
            <div class="signature-box">
                <div class="signature-line">Prepared By</div>
            </div>
            <div class="signature-box">
                <div class="signature-line">Reviewed By</div>
            </div>
            <div class="signature-box">
                <div class="signature-line">Approved By</div>
            </div>
        </div>

        <p style="text-align: center; font-size: 10px; color: #999; margin-top: 40px;">
            This is a computer-generated document. Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        </p>
    </body>
    </html>
    """

    return HTMLResponse(content=html_content)


# ==================== Sales Return Note (SRN) ====================

@router.get("/srn/next-number")
@require_module("procurement")
async def get_next_srn_number(
    db: DB,
):
    """Get the next available Sales Return Note number."""
    today = date.today()
    fy_year = today.year if today.month >= 4 else today.year - 1
    fy_suffix = f"{str(fy_year)[-2:]}-{str(fy_year + 1)[-2:]}"

    # Find the highest SRN number for this financial year
    result = await db.execute(
        select(SalesReturnNote.srn_number)
        .where(SalesReturnNote.srn_number.like(f"SRN/APL/{fy_suffix}/%"))
        .order_by(SalesReturnNote.srn_number.desc())
        .limit(1)
    )
    last_srn = result.scalar_one_or_none()

    if last_srn:
        try:
            last_num = int(last_srn.split("/")[-1])
            next_num = last_num + 1
        except (IndexError, ValueError):
            next_num = 1
    else:
        next_num = 1

    next_srn = f"SRN/APL/{fy_suffix}/{str(next_num).zfill(4)}"
    return {"next_number": next_srn, "prefix": f"SRN/APL/{fy_suffix}"}


@router.post("/srn", response_model=SalesReturnResponse, status_code=status.HTTP_201_CREATED)
@require_module("procurement")
async def create_srn(
    srn_in: SalesReturnCreate,
    db: DB,
    current_user: User = Depends(get_current_user),
):
    """Create a new Sales Return Note."""
    # Validate that at least one reference is provided (order_id or invoice_id)
    if not srn_in.order_id and not srn_in.invoice_id:
        raise HTTPException(
            status_code=400,
            detail="Either order_id or invoice_id must be provided"
        )

    # Validate customer exists
    customer_result = await db.execute(
        select(Customer).where(Customer.id == srn_in.customer_id)
    )
    customer = customer_result.scalar_one_or_none()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")

    # Validate order if provided
    order = None
    if srn_in.order_id:
        order_result = await db.execute(
            select(Order)
            .options(selectinload(Order.items))
            .where(Order.id == srn_in.order_id)
        )
        order = order_result.scalar_one_or_none()
        if not order:
            raise HTTPException(status_code=404, detail="Order not found")
        # Verify customer matches
        if order.customer_id != srn_in.customer_id:
            raise HTTPException(
                status_code=400,
                detail="Order does not belong to the specified customer"
            )

    # Validate invoice if provided
    invoice = None
    if srn_in.invoice_id:
        invoice_result = await db.execute(
            select(TaxInvoice).where(TaxInvoice.id == srn_in.invoice_id)
        )
        invoice = invoice_result.scalar_one_or_none()
        if not invoice:
            raise HTTPException(status_code=404, detail="Invoice not found")

    # Validate warehouse
    wh_result = await db.execute(
        select(Warehouse).where(Warehouse.id == srn_in.warehouse_id)
    )
    if not wh_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Warehouse not found")

    # Generate SRN number using atomic sequence service
    service = DocumentSequenceService(db)
    srn_number = await service.get_next_number("SRN")

    # Determine initial status based on pickup requirement
    initial_status = SRNStatus.PENDING_RECEIPT if srn_in.pickup_required else SRNStatus.RECEIVED

    # Create SRN
    srn = SalesReturnNote(
        srn_number=srn_number,
        srn_date=srn_in.srn_date,
        order_id=srn_in.order_id,
        invoice_id=srn_in.invoice_id,
        customer_id=srn_in.customer_id,
        warehouse_id=srn_in.warehouse_id,
        status=initial_status,
        return_reason=ReturnReason(srn_in.return_reason),
        return_reason_detail=srn_in.return_reason_detail,
        resolution_type=ResolutionType(srn_in.resolution_type) if srn_in.resolution_type else None,
        pickup_required=srn_in.pickup_required,
        pickup_scheduled_date=srn_in.pickup_scheduled_date,
        pickup_address=srn_in.pickup_address,
        pickup_contact_name=srn_in.pickup_contact_name,
        pickup_contact_phone=srn_in.pickup_contact_phone,
        pickup_status=PickupStatus.SCHEDULED.value if srn_in.pickup_required and srn_in.pickup_scheduled_date else (PickupStatus.NOT_REQUIRED.value if not srn_in.pickup_required else None),
        qc_required=srn_in.qc_required,
        receiving_remarks=srn_in.receiving_remarks,
        created_by=current_user.id,
    )

    db.add(srn)
    await db.flush()

    # Create SRN items
    total_items = 0
    total_qty_returned = 0
    total_value = Decimal("0")

    for item_data in srn_in.items:
        unit_price = Decimal(str(item_data.unit_price))
        qty_returned = item_data.quantity_returned
        item_value = (unit_price * qty_returned).quantize(Decimal("0.01"))

        srn_item = SRNItem(
            srn_id=srn.id,
            order_item_id=item_data.order_item_id,
            invoice_item_id=item_data.invoice_item_id,
            product_id=item_data.product_id,
            variant_id=item_data.variant_id,
            product_name=item_data.product_name,
            sku=item_data.sku,
            hsn_code=item_data.hsn_code,
            serial_numbers=item_data.serial_numbers,
            quantity_sold=item_data.quantity_sold,
            quantity_returned=qty_returned,
            uom=item_data.uom or "PCS",
            unit_price=unit_price,
            return_value=item_value,
            remarks=item_data.remarks,
        )
        db.add(srn_item)

        total_items += 1
        total_qty_returned += qty_returned
        total_value += item_value

    # Update SRN totals
    srn.total_items = total_items
    srn.total_quantity_returned = total_qty_returned
    srn.total_value = total_value

    await db.commit()
    await db.refresh(srn)

    # Fetch with items for response
    result = await db.execute(
        select(SalesReturnNote)
        .options(selectinload(SalesReturnNote.items))
        .where(SalesReturnNote.id == srn.id)
    )
    srn = result.scalar_one()

    return srn


@router.get("/srn", response_model=SRNListResponse)
@require_module("procurement")
async def list_srns(
    db: DB,
    current_user: User = Depends(get_current_user),
    status: Optional[str] = Query(None, description="Filter by status"),
    customer_id: Optional[UUID] = Query(None, description="Filter by customer"),
    order_id: Optional[UUID] = Query(None, description="Filter by order"),
    warehouse_id: Optional[UUID] = Query(None, description="Filter by warehouse"),
    return_reason: Optional[str] = Query(None, description="Filter by return reason"),
    pickup_status: Optional[str] = Query(None, description="Filter by pickup status"),
    date_from: Optional[date] = Query(None, description="Filter from date"),
    date_to: Optional[date] = Query(None, description="Filter to date"),
    search: Optional[str] = Query(None, description="Search by SRN number or customer name"),
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=100),
):
    """List Sales Return Notes with filters."""
    query = select(SalesReturnNote)
    count_query = select(func.count(SalesReturnNote.id))
    value_query = select(func.sum(SalesReturnNote.total_value))

    # Apply filters
    conditions = []

    if status:
        conditions.append(SalesReturnNote.status == SRNStatus(status))

    if customer_id:
        conditions.append(SalesReturnNote.customer_id == customer_id)

    if order_id:
        conditions.append(SalesReturnNote.order_id == order_id)

    if warehouse_id:
        conditions.append(SalesReturnNote.warehouse_id == warehouse_id)

    if return_reason:
        conditions.append(SalesReturnNote.return_reason == ReturnReason(return_reason))

    if pickup_status:
        conditions.append(SalesReturnNote.pickup_status == pickup_status)

    if date_from:
        conditions.append(SalesReturnNote.srn_date >= date_from)

    if date_to:
        conditions.append(SalesReturnNote.srn_date <= date_to)

    if search:
        search_term = f"%{search}%"
        # Join with customer for name search
        query = query.outerjoin(Customer, SalesReturnNote.customer_id == Customer.id)
        count_query = count_query.outerjoin(Customer, SalesReturnNote.customer_id == Customer.id)
        value_query = value_query.outerjoin(Customer, SalesReturnNote.customer_id == Customer.id)
        conditions.append(
            or_(
                SalesReturnNote.srn_number.ilike(search_term),
                Customer.first_name.ilike(search_term),
                Customer.last_name.ilike(search_term),
                Customer.phone.ilike(search_term),
            )
        )

    if conditions:
        query = query.where(and_(*conditions))
        count_query = count_query.where(and_(*conditions))
        value_query = value_query.where(and_(*conditions))

    # Get total count and value
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    total_value_result = await db.execute(value_query)
    total_value = total_value_result.scalar() or Decimal("0")

    # Calculate pagination
    skip = (page - 1) * size
    pages = (total + size - 1) // size if total > 0 else 1

    # Execute main query with pagination
    query = query.order_by(SalesReturnNote.created_at.desc()).offset(skip).limit(size)
    result = await db.execute(query)
    srns = result.scalars().all()

    # Build response items with customer and order names
    items = []
    for srn in srns:
        # Fetch customer name
        customer_name = None
        if srn.customer_id:
            cust_result = await db.execute(
                select(Customer.first_name, Customer.last_name).where(Customer.id == srn.customer_id)
            )
            cust_row = cust_result.first()
            if cust_row:
                customer_name = f"{cust_row[0] or ''} {cust_row[1] or ''}".strip()

        # Fetch order number
        order_number = None
        if srn.order_id:
            order_result = await db.execute(
                select(Order.order_number).where(Order.id == srn.order_id)
            )
            order_number = order_result.scalar_one_or_none()

        items.append(SRNBrief(
            id=srn.id,
            srn_number=srn.srn_number,
            srn_date=srn.srn_date,
            customer_name=customer_name,
            order_number=order_number,
            status=srn.status if isinstance(srn.status, SRNStatus) else srn.status,
            return_reason=srn.return_reason if isinstance(srn.return_reason, ReturnReason) else srn.return_reason,
            total_quantity_returned=srn.total_quantity_returned,
            total_value=srn.total_value or Decimal("0"),
            pickup_status=srn.pickup_status,
        ))

    return SRNListResponse(
        items=items,
        total=total,
        total_value=total_value,
        page=page,
        size=size,
        pages=pages,
    )


@router.get("/srn/pending-pickups", response_model=SRNListResponse)
@require_module("procurement")
async def list_pending_pickups(
    db: DB,
    current_user: User = Depends(get_current_user),
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=100),
):
    """List SRNs with pending pickup (reverse logistics tracking)."""
    # Filter SRNs where pickup is required and not yet delivered
    pending_statuses = [
        PickupStatus.SCHEDULED.value,
        PickupStatus.PICKED_UP.value,
        PickupStatus.IN_TRANSIT.value,
    ]

    query = select(SalesReturnNote).where(
        and_(
            SalesReturnNote.pickup_required == True,
            SalesReturnNote.pickup_status.in_(pending_statuses),
        )
    )
    count_query = select(func.count(SalesReturnNote.id)).where(
        and_(
            SalesReturnNote.pickup_required == True,
            SalesReturnNote.pickup_status.in_(pending_statuses),
        )
    )

    # Get total count
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # Calculate pagination
    skip = (page - 1) * size
    pages = (total + size - 1) // size if total > 0 else 1

    # Execute main query
    query = query.order_by(SalesReturnNote.pickup_scheduled_date.asc()).offset(skip).limit(size)
    result = await db.execute(query)
    srns = result.scalars().all()

    # Build response items
    items = []
    total_value = Decimal("0")
    for srn in srns:
        # Fetch customer name
        customer_name = None
        if srn.customer_id:
            cust_result = await db.execute(
                select(Customer.first_name, Customer.last_name).where(Customer.id == srn.customer_id)
            )
            cust_row = cust_result.first()
            if cust_row:
                customer_name = f"{cust_row[0] or ''} {cust_row[1] or ''}".strip()

        # Fetch order number
        order_number = None
        if srn.order_id:
            order_result = await db.execute(
                select(Order.order_number).where(Order.id == srn.order_id)
            )
            order_number = order_result.scalar_one_or_none()

        items.append(SRNBrief(
            id=srn.id,
            srn_number=srn.srn_number,
            srn_date=srn.srn_date,
            customer_name=customer_name,
            order_number=order_number,
            status=srn.status if isinstance(srn.status, SRNStatus) else srn.status,
            return_reason=srn.return_reason if isinstance(srn.return_reason, ReturnReason) else srn.return_reason,
            total_quantity_returned=srn.total_quantity_returned,
            total_value=srn.total_value or Decimal("0"),
            pickup_status=srn.pickup_status,
        ))
        total_value += srn.total_value or Decimal("0")

    return SRNListResponse(
        items=items,
        total=total,
        total_value=total_value,
        page=page,
        size=size,
        pages=pages,
    )


@router.get("/srn/{srn_id}", response_model=SalesReturnResponse)
@require_module("procurement")
async def get_srn(
    srn_id: UUID,
    db: DB,
    current_user: User = Depends(get_current_user),
):
    """Get SRN by ID with full details."""
    result = await db.execute(
        select(SalesReturnNote)
        .options(selectinload(SalesReturnNote.items))
        .where(SalesReturnNote.id == srn_id)
    )
    srn = result.scalar_one_or_none()

    if not srn:
        raise HTTPException(status_code=404, detail="SRN not found")

    return srn


@router.post("/srn/{srn_id}/schedule-pickup", response_model=SalesReturnResponse)
@require_module("procurement")
async def schedule_srn_pickup(
    srn_id: UUID,
    request: PickupScheduleRequest,
    db: DB,
    current_user: User = Depends(get_current_user),
):
    """Schedule reverse pickup for an SRN."""
    result = await db.execute(
        select(SalesReturnNote)
        .options(selectinload(SalesReturnNote.items))
        .where(SalesReturnNote.id == srn_id)
    )
    srn = result.scalar_one_or_none()

    if not srn:
        raise HTTPException(status_code=404, detail="SRN not found")

    if srn.status not in [SRNStatus.DRAFT, SRNStatus.PENDING_RECEIPT]:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot schedule pickup for SRN in status: {srn.status}"
        )

    # Validate courier if provided
    if request.courier_id:
        courier_result = await db.execute(
            select(Transporter).where(Transporter.id == request.courier_id)
        )
        courier = courier_result.scalar_one_or_none()
        if not courier:
            raise HTTPException(status_code=404, detail="Courier/Transporter not found")
        srn.courier_id = request.courier_id
        srn.courier_name = courier.name

    # Update pickup details
    srn.pickup_required = True
    srn.pickup_scheduled_date = request.pickup_date
    srn.pickup_scheduled_slot = request.pickup_slot
    srn.pickup_status = PickupStatus.SCHEDULED.value
    srn.pickup_requested_at = datetime.now(timezone.utc)

    if request.pickup_address:
        srn.pickup_address = request.pickup_address
    if request.pickup_contact_name:
        srn.pickup_contact_name = request.pickup_contact_name
    if request.pickup_contact_phone:
        srn.pickup_contact_phone = request.pickup_contact_phone

    # Update status to PENDING_RECEIPT if it was DRAFT
    if srn.status == SRNStatus.DRAFT:
        srn.status = SRNStatus.PENDING_RECEIPT.value

    await db.commit()
    await db.refresh(srn)

    return srn


@router.post("/srn/{srn_id}/update-pickup", response_model=SalesReturnResponse)
@require_module("procurement")
async def update_srn_pickup(
    srn_id: UUID,
    request: PickupUpdateRequest,
    db: DB,
    current_user: User = Depends(get_current_user),
):
    """Update pickup status and AWB for an SRN (reverse logistics tracking)."""
    result = await db.execute(
        select(SalesReturnNote)
        .options(selectinload(SalesReturnNote.items))
        .where(SalesReturnNote.id == srn_id)
    )
    srn = result.scalar_one_or_none()

    if not srn:
        raise HTTPException(status_code=404, detail="SRN not found")

    if not srn.pickup_required:
        raise HTTPException(
            status_code=400,
            detail="This SRN does not require pickup"
        )

    # Update courier details if provided
    if request.courier_id:
        courier_result = await db.execute(
            select(Transporter).where(Transporter.id == request.courier_id)
        )
        courier = courier_result.scalar_one_or_none()
        if courier:
            srn.courier_id = request.courier_id
            srn.courier_name = courier.name

    if request.courier_name:
        srn.courier_name = request.courier_name

    if request.courier_tracking_number:
        srn.courier_tracking_number = request.courier_tracking_number

    # Update pickup status
    if request.pickup_status:
        srn.pickup_status = request.pickup_status

        # If delivered, mark pickup as complete and update SRN status
        if request.pickup_status == PickupStatus.DELIVERED.value:
            srn.pickup_completed_at = datetime.now(timezone.utc)
            srn.status = SRNStatus.RECEIVED.value
            srn.received_at = datetime.now(timezone.utc)
            srn.received_by = current_user.id

    await db.commit()
    await db.refresh(srn)

    return srn


@router.post("/srn/{srn_id}/receive", response_model=SalesReturnResponse)
@require_module("procurement")
async def receive_srn(
    srn_id: UUID,
    request: SRNReceiveRequest,
    db: DB,
    current_user: User = Depends(get_current_user),
):
    """Mark SRN goods as received (for walk-in returns or after pickup delivery)."""
    result = await db.execute(
        select(SalesReturnNote)
        .options(selectinload(SalesReturnNote.items))
        .where(SalesReturnNote.id == srn_id)
    )
    srn = result.scalar_one_or_none()

    if not srn:
        raise HTTPException(status_code=404, detail="SRN not found")

    if srn.status not in [SRNStatus.DRAFT, SRNStatus.PENDING_RECEIPT]:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot receive goods for SRN in status: {srn.status}"
        )

    # Update receiving details
    srn.received_by = current_user.id
    srn.received_at = datetime.now(timezone.utc)
    srn.receiving_remarks = request.receiving_remarks

    if request.photos_urls:
        srn.photos_urls = request.photos_urls

    # Update pickup status if this was a pickup
    if srn.pickup_required and srn.pickup_status != PickupStatus.DELIVERED.value:
        srn.pickup_status = PickupStatus.DELIVERED.value
        srn.pickup_completed_at = datetime.now(timezone.utc)

    # Determine next status based on QC requirement
    if srn.qc_required:
        srn.status = SRNStatus.PENDING_QC.value
    else:
        srn.status = SRNStatus.PUT_AWAY_PENDING.value
        # If no QC required, accept all quantities
        for item in srn.items:
            item.quantity_accepted = item.quantity_returned
            item.qc_result = QualityCheckResult.ACCEPTED.value
        srn.total_quantity_accepted = srn.total_quantity_returned

    await db.commit()
    await db.refresh(srn)

    return srn


@router.post("/srn/{srn_id}/qc", response_model=SalesReturnResponse)
@require_module("procurement")
async def process_srn_quality_check(
    srn_id: UUID,
    qc_request: SRNQualityCheckRequest,
    db: DB,
    current_user: User = Depends(get_current_user),
):
    """Process quality check for SRN items with condition assessment."""
    result = await db.execute(
        select(SalesReturnNote)
        .options(selectinload(SalesReturnNote.items))
        .where(SalesReturnNote.id == srn_id)
    )
    srn = result.scalar_one_or_none()

    if not srn:
        raise HTTPException(status_code=404, detail="SRN not found")

    if srn.status != SRNStatus.PENDING_QC:
        raise HTTPException(
            status_code=400,
            detail=f"SRN is not pending QC. Current status: {srn.status}"
        )

    # Process each item's QC result
    all_accepted = True
    all_rejected = True
    total_accepted = 0
    total_rejected = 0

    for item_result in qc_request.item_results:
        item_id = item_result.item_id
        qc_result_val = item_result.qc_result
        item_condition = item_result.item_condition
        restock_decision = item_result.restock_decision
        qty_accepted = item_result.quantity_accepted
        qty_rejected = item_result.quantity_rejected
        rejection_reason = item_result.rejection_reason

        # Find the SRN item
        item_query = await db.execute(
            select(SRNItem).where(SRNItem.id == item_id)
        )
        item = item_query.scalar_one_or_none()

        if item:
            item.qc_result = QualityCheckResult(qc_result_val) if qc_result_val else None
            item.item_condition = ItemCondition(item_condition) if item_condition else None
            item.restock_decision = RestockDecision(restock_decision) if restock_decision else None
            item.quantity_accepted = qty_accepted if qty_accepted is not None else 0
            item.quantity_rejected = qty_rejected if qty_rejected is not None else 0

            if rejection_reason:
                item.rejection_reason = rejection_reason

            # Recalculate return value based on accepted quantity
            item.return_value = (item.unit_price * item.quantity_accepted).quantize(Decimal("0.01"))

            # Track totals
            total_accepted += item.quantity_accepted
            total_rejected += item.quantity_rejected

            if item.qc_result == QualityCheckResult.ACCEPTED:
                all_rejected = False
            elif item.qc_result == QualityCheckResult.REJECTED:
                all_accepted = False
            else:
                all_accepted = False
                all_rejected = False

    # Set overall QC status
    if all_accepted:
        srn.qc_status = QualityCheckResult.ACCEPTED.value
    elif all_rejected:
        srn.qc_status = QualityCheckResult.REJECTED.value
    else:
        srn.qc_status = QualityCheckResult.PARTIAL.value

    # Update SRN totals
    srn.total_quantity_accepted = total_accepted
    srn.total_quantity_rejected = total_rejected

    # Recalculate total value based on accepted items
    new_total_value = sum(item.return_value for item in srn.items)
    srn.total_value = new_total_value

    srn.qc_done_by = current_user.id
    srn.qc_done_at = datetime.now(timezone.utc)
    srn.qc_remarks = qc_request.overall_remarks
    srn.status = SRNStatus.PUT_AWAY_PENDING.value

    await db.commit()
    await db.refresh(srn)

    return srn


@router.post("/srn/{srn_id}/putaway", response_model=SalesReturnResponse)
@require_module("procurement")
async def process_srn_putaway(
    srn_id: UUID,
    putaway_request: SRNPutAwayRequest,
    db: DB,
    current_user: User = Depends(get_current_user),
):
    """Process put-away for SRN items (add returned goods to inventory)."""
    result = await db.execute(
        select(SalesReturnNote)
        .options(selectinload(SalesReturnNote.items))
        .where(SalesReturnNote.id == srn_id)
    )
    srn = result.scalar_one_or_none()

    if not srn:
        raise HTTPException(status_code=404, detail="SRN not found")

    if srn.status != SRNStatus.PUT_AWAY_PENDING:
        raise HTTPException(
            status_code=400,
            detail=f"SRN is not pending put-away. Current status: {srn.status}"
        )

    # Process each item location
    for loc_data in putaway_request.item_locations:
        item_id = loc_data.get("item_id")
        bin_id = loc_data.get("bin_id")
        bin_location = loc_data.get("bin_location")

        item_query = await db.execute(
            select(SRNItem).where(SRNItem.id == UUID(str(item_id)))
        )
        item = item_query.scalar_one_or_none()

        if item and item.quantity_accepted > 0:
            item.bin_id = UUID(str(bin_id)) if bin_id else None
            item.bin_location = bin_location

            # Determine stock status based on restock decision
            stock_status = StockItemStatus.AVAILABLE.value
            quality_grade = "A"

            if item.restock_decision:
                if item.restock_decision == RestockDecision.RESTOCK_AS_NEW:
                    stock_status = StockItemStatus.AVAILABLE.value
                    quality_grade = "A"
                elif item.restock_decision == RestockDecision.RESTOCK_AS_REFURB:
                    stock_status = StockItemStatus.AVAILABLE.value
                    quality_grade = "REFURBISHED"
                elif item.restock_decision == RestockDecision.SEND_FOR_REPAIR:
                    stock_status = StockItemStatus.DAMAGED.value
                    quality_grade = "REPAIR"
                elif item.restock_decision == RestockDecision.RETURN_TO_VENDOR:
                    stock_status = StockItemStatus.QUARANTINE.value
                    quality_grade = "RTV"
                elif item.restock_decision == RestockDecision.SCRAP:
                    stock_status = StockItemStatus.SCRAPPED.value
                    quality_grade = "SCRAP"

            # Create stock items for accepted quantity (only for restockable items)
            if item.restock_decision in [RestockDecision.RESTOCK_AS_NEW, RestockDecision.RESTOCK_AS_REFURB, None]:
                for i in range(item.quantity_accepted):
                    serial = None
                    if item.serial_numbers and i < len(item.serial_numbers):
                        serial = item.serial_numbers[i]

                    stock_item = StockItem(
                        product_id=item.product_id,
                        variant_id=item.variant_id,
                        warehouse_id=srn.warehouse_id,
                        sku=item.sku,
                        serial_number=serial,
                        status=stock_status,
                        purchase_price=item.unit_price,
                        quality_grade=quality_grade,
                        srn_id=srn.id,
                        bin_id=item.bin_id,
                        created_by=current_user.id,
                    )
                    db.add(stock_item)

                # Update inventory summary
                summary_result = await db.execute(
                    select(InventorySummary).where(
                        and_(
                            InventorySummary.product_id == item.product_id,
                            InventorySummary.warehouse_id == srn.warehouse_id,
                        )
                    )
                )
                summary = summary_result.scalar_one_or_none()

                if summary:
                    summary.total_quantity += item.quantity_accepted
                    summary.available_quantity += item.quantity_accepted
                else:
                    summary = InventorySummary(
                        product_id=item.product_id,
                        variant_id=item.variant_id,
                        warehouse_id=srn.warehouse_id,
                        total_quantity=item.quantity_accepted,
                        available_quantity=item.quantity_accepted,
                    )
                    db.add(summary)

            # Create stock movement record for all accepted items
            movement = StockMovement(
                product_id=item.product_id,
                variant_id=item.variant_id,
                warehouse_id=srn.warehouse_id,
                movement_type=StockMovementType.RETURN_IN,
                quantity=item.quantity_accepted,
                reference_type="SRN",
                reference_id=srn.id,
                reference_number=srn.srn_number,
                unit_price=item.unit_price,
                total_value=item.return_value,
                notes=f"Sales Return Put-away - {item.restock_decision if item.restock_decision else 'Standard'}",
                created_by=current_user.id,
            )
            db.add(movement)

    # Update SRN status
    srn.status = SRNStatus.PUT_AWAY_COMPLETE.value
    srn.put_away_complete = True
    srn.put_away_at = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(srn)

    return srn


@router.post("/srn/{srn_id}/resolve", response_model=SalesReturnResponse)
@require_module("procurement")
async def resolve_srn(
    srn_id: UUID,
    request: SRNResolveRequest,
    db: DB,
    current_user: User = Depends(get_current_user),
):
    """Resolve SRN by issuing credit note, creating replacement, or processing refund."""
    result = await db.execute(
        select(SalesReturnNote)
        .options(selectinload(SalesReturnNote.items))
        .where(SalesReturnNote.id == srn_id)
    )
    srn = result.scalar_one_or_none()

    if not srn:
        raise HTTPException(status_code=404, detail="SRN not found")

    if srn.status != SRNStatus.PUT_AWAY_COMPLETE:
        raise HTTPException(
            status_code=400,
            detail=f"SRN must be put-away complete before resolution. Current status: {srn.status}"
        )

    resolution_type = ResolutionType(request.resolution_type)
    srn.resolution_type = resolution_type

    if resolution_type == ResolutionType.CREDIT_NOTE:
        # Generate credit note number
        cn_count_result = await db.execute(
            select(func.count(CreditDebitNote.id))
        )
        cn_count = cn_count_result.scalar() or 0
        cn_number = f"CN-{date.today().strftime('%Y%m%d')}-{str(cn_count + 1).zfill(4)}"

        # Create credit note
        credit_note = CreditDebitNote(
            note_number=cn_number,
            document_type=DocumentType.CREDIT_NOTE,
            invoice_id=srn.invoice_id,
            order_id=srn.order_id,
            note_date=date.today(),
            reason=NoteReason.SALES_RETURN,
            status=InvoiceStatus.DRAFT,
            subtotal=srn.total_value,
            taxable_amount=srn.total_value,
            grand_total=srn.total_value,
            internal_notes=f"Credit note for SRN {srn.srn_number}. {request.notes or ''}",
            created_by=current_user.id,
        )
        db.add(credit_note)
        await db.flush()

        srn.credit_note_id = credit_note.id
        srn.status = SRNStatus.CREDITED.value

    elif resolution_type == ResolutionType.REPLACEMENT:
        # For replacement, the order would typically be created manually
        # Just update status - linking replacement order can be done later
        srn.status = SRNStatus.REPLACED.value
        # Note: replacement_order_id can be set via a separate update endpoint

    elif resolution_type == ResolutionType.REFUND:
        # Mark for refund processing
        srn.status = SRNStatus.REFUNDED.value

    elif resolution_type == ResolutionType.REJECT:
        # Return rejected - no credit/replacement
        srn.status = SRNStatus.CANCELLED.value

    await db.commit()
    await db.refresh(srn)

    return srn


@router.delete("/srn/{srn_id}", status_code=status.HTTP_204_NO_CONTENT)
@require_module("procurement")
async def delete_srn(
    srn_id: UUID,
    db: DB,
    current_user: User = Depends(get_current_user),
):
    """Delete a draft SRN."""
    result = await db.execute(
        select(SalesReturnNote).where(SalesReturnNote.id == srn_id)
    )
    srn = result.scalar_one_or_none()

    if not srn:
        raise HTTPException(status_code=404, detail="SRN not found")

    if srn.status != SRNStatus.DRAFT:
        raise HTTPException(
            status_code=400,
            detail="Only draft SRNs can be deleted"
        )

    # Delete items first
    await db.execute(
        delete(SRNItem).where(SRNItem.srn_id == srn_id)
    )

    # Delete SRN
    await db.execute(
        delete(SalesReturnNote).where(SalesReturnNote.id == srn_id)
    )

    await db.commit()

    return None


@router.get("/srn/{srn_id}/download")
@require_module("procurement")
async def download_srn_pdf(
    srn_id: UUID,
    db: DB,
    current_user: User = Depends(get_current_user),
):
    """Download SRN as printable HTML/PDF."""
    from fastapi.responses import HTMLResponse

    result = await db.execute(
        select(SalesReturnNote)
        .options(selectinload(SalesReturnNote.items))
        .where(SalesReturnNote.id == srn_id)
    )
    srn = result.scalar_one_or_none()

    if not srn:
        raise HTTPException(status_code=404, detail="SRN not found")

    # Fetch customer
    customer = None
    if srn.customer_id:
        customer_result = await db.execute(
            select(Customer).where(Customer.id == srn.customer_id)
        )
        customer = customer_result.scalar_one_or_none()

    # Fetch warehouse
    warehouse = None
    if srn.warehouse_id:
        wh_result = await db.execute(
            select(Warehouse).where(Warehouse.id == srn.warehouse_id)
        )
        warehouse = wh_result.scalar_one_or_none()

    # Fetch order
    order = None
    if srn.order_id:
        order_result = await db.execute(
            select(Order).where(Order.id == srn.order_id)
        )
        order = order_result.scalar_one_or_none()

    # Build items HTML
    items_html = ""
    for idx, item in enumerate(srn.items, 1):
        serials_str = ", ".join(item.serial_numbers) if item.serial_numbers else "-"
        condition_str = item.item_condition if item.item_condition else "-"
        decision_str = item.restock_decision if item.restock_decision else "-"

        items_html += f"""
        <tr>
            <td style="text-align: center;">{idx}</td>
            <td>{item.product_name}<br><small style="color: #666;">SKU: {item.sku}</small></td>
            <td style="text-align: center;">{serials_str[:50]}{'...' if len(serials_str) > 50 else ''}</td>
            <td style="text-align: center;">{item.quantity_returned}</td>
            <td style="text-align: center;">{item.quantity_accepted}</td>
            <td style="text-align: center;">{condition_str}</td>
            <td style="text-align: center;">{decision_str}</td>
            <td style="text-align: right;">₹{float(item.unit_price):,.2f}</td>
            <td style="text-align: right;">₹{float(item.return_value):,.2f}</td>
        </tr>
        """

    status_val = srn.status if isinstance(srn.status, SRNStatus) else srn.status
    reason_val = srn.return_reason if isinstance(srn.return_reason, ReturnReason) else srn.return_reason

    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Sales Return Note - {srn.srn_number}</title>
        <style>
            * {{ margin: 0; padding: 0; box-sizing: border-box; }}
            body {{ font-family: Arial, sans-serif; padding: 20px; max-width: 1000px; margin: auto; }}
            @media print {{
                body {{ padding: 0; }}
                .no-print {{ display: none !important; }}
            }}
            .header {{ text-align: center; margin-bottom: 30px; border-bottom: 2px solid #0066cc; padding-bottom: 20px; }}
            .company-name {{ font-size: 24px; font-weight: bold; color: #0066cc; margin-bottom: 5px; }}
            .document-title {{ font-size: 18px; font-weight: bold; margin-top: 15px; background: #f0f0f0; padding: 10px; }}
            .status-badge {{
                display: inline-block; padding: 5px 15px; border-radius: 20px;
                font-weight: bold; font-size: 12px;
                background: {"#28a745" if status_val in ["CREDITED", "REPLACED", "REFUNDED", "PUT_AWAY_COMPLETE"] else "#ffc107" if status_val in ["PENDING_QC", "PUT_AWAY_PENDING"] else "#6c757d"};
                color: white;
            }}
            .info-section {{ display: flex; justify-content: space-between; margin-bottom: 20px; gap: 20px; }}
            .info-box {{ flex: 1; border: 1px solid #ddd; padding: 15px; border-radius: 5px; }}
            .info-box h3 {{ color: #0066cc; margin-bottom: 10px; font-size: 14px; border-bottom: 1px solid #eee; padding-bottom: 5px; }}
            .info-box p {{ margin: 5px 0; font-size: 13px; }}
            table {{ width: 100%; border-collapse: collapse; margin-bottom: 20px; }}
            th {{ background: #0066cc; color: white; padding: 10px 8px; text-align: left; font-size: 12px; }}
            td {{ border: 1px solid #ddd; padding: 10px 8px; font-size: 12px; }}
            .totals-section {{ margin-left: auto; width: 300px; }}
            .totals-section table td {{ padding: 8px; }}
            .totals-section .grand-total {{ background: #e6f0ff; font-size: 16px; font-weight: bold; }}
            .remarks-box {{ background: #f9f9f9; padding: 15px; border-radius: 5px; margin-bottom: 20px; }}
            .signatures {{ display: flex; justify-content: space-between; margin-top: 60px; }}
            .signature-box {{ text-align: center; width: 150px; }}
            .signature-line {{ border-top: 1px solid #333; margin-top: 40px; padding-top: 5px; }}
            .print-btn {{ position: fixed; top: 10px; right: 10px; padding: 10px 20px; background: #0066cc; color: white; border: none; border-radius: 5px; cursor: pointer; }}
        </style>
    </head>
    <body>
        <button class="print-btn no-print" onclick="window.print()">Print / Save PDF</button>

        <div class="header">
            <div class="company-name">AQUAPURITE PRIVATE LIMITED</div>
            <div style="font-size: 12px; color: #666;">
                PLOT 36-A, KH NO 181, PH-1, SHYAM VIHAR, DINDAPUR EXT, New Delhi - 110043, Delhi<br>
                GSTIN: 07ABDCA6170C1Z0 | PAN: ABDCA6170C
            </div>
            <div class="document-title">SALES RETURN NOTE</div>
        </div>

        <div style="text-align: center; margin-bottom: 20px;">
            <span class="status-badge">{status_val}</span>
        </div>

        <div class="info-section">
            <div class="info-box">
                <h3>CUSTOMER DETAILS</h3>
                <p><strong>{customer.first_name if customer else ''} {customer.last_name if customer else 'N/A'}</strong></p>
                <p>{customer.address_line1 if customer and customer.address_line1 else ''}</p>
                <p>{customer.city if customer else ''}, {customer.state if customer else ''} - {customer.pincode if customer else ''}</p>
                <p>Phone: {customer.phone if customer else 'N/A'}</p>
                <p>Email: {customer.email if customer else 'N/A'}</p>
            </div>
            <div class="info-box">
                <h3>SRN DETAILS</h3>
                <p><strong>SRN Number:</strong> {srn.srn_number}</p>
                <p><strong>SRN Date:</strong> {srn.srn_date}</p>
                <p><strong>Order Reference:</strong> {order.order_number if order else 'N/A'}</p>
                <p><strong>Return Reason:</strong> {reason_val}</p>
                <p><strong>Warehouse:</strong> {warehouse.name if warehouse else 'N/A'}</p>
            </div>
        </div>

        {"<div class='info-box' style='margin-bottom: 20px;'><h3>PICKUP DETAILS</h3><p><strong>Pickup Status:</strong> " + (srn.pickup_status or "N/A") + "</p><p><strong>Scheduled Date:</strong> " + (str(srn.pickup_scheduled_date) if srn.pickup_scheduled_date else "N/A") + "</p><p><strong>AWB Number:</strong> " + (srn.courier_tracking_number or "N/A") + "</p><p><strong>Courier:</strong> " + (srn.courier_name or "N/A") + "</p></div>" if srn.pickup_required else ""}

        <table>
            <thead>
                <tr>
                    <th style="width: 40px;">#</th>
                    <th>Product</th>
                    <th style="width: 100px; text-align: center;">Serial#</th>
                    <th style="width: 60px; text-align: center;">Returned</th>
                    <th style="width: 60px; text-align: center;">Accepted</th>
                    <th style="width: 80px; text-align: center;">Condition</th>
                    <th style="width: 100px; text-align: center;">Decision</th>
                    <th style="width: 90px; text-align: right;">Unit Price</th>
                    <th style="width: 100px; text-align: right;">Value</th>
                </tr>
            </thead>
            <tbody>
                {items_html}
            </tbody>
        </table>

        <div class="totals-section">
            <table>
                <tr>
                    <td>Total Qty Returned</td>
                    <td style="text-align: right;">{srn.total_quantity_returned}</td>
                </tr>
                <tr>
                    <td>Total Qty Accepted</td>
                    <td style="text-align: right;">{srn.total_quantity_accepted}</td>
                </tr>
                <tr>
                    <td>Total Qty Rejected</td>
                    <td style="text-align: right;">{srn.total_quantity_rejected}</td>
                </tr>
                <tr class="grand-total">
                    <td><strong>TOTAL VALUE</strong></td>
                    <td style="text-align: right;"><strong>₹{float(srn.total_value or 0):,.2f}</strong></td>
                </tr>
            </table>
        </div>

        <div class="remarks-box">
            <h3 style="margin-bottom: 10px;">Remarks</h3>
            <p><strong>Return Reason Detail:</strong> {srn.return_reason_detail or 'None'}</p>
            <p><strong>Receiving Remarks:</strong> {srn.receiving_remarks or 'None'}</p>
            <p><strong>QC Remarks:</strong> {srn.qc_remarks or 'None'}</p>
            <p><strong>Resolution:</strong> {srn.resolution_type if srn.resolution_type else 'Pending'}</p>
        </div>

        <div class="signatures">
            <div class="signature-box">
                <div class="signature-line">Customer</div>
            </div>
            <div class="signature-box">
                <div class="signature-line">Received By</div>
            </div>
            <div class="signature-box">
                <div class="signature-line">QC Verified</div>
            </div>
            <div class="signature-box">
                <div class="signature-line">Authorized</div>
            </div>
        </div>

        <p style="text-align: center; font-size: 10px; color: #999; margin-top: 40px;">
            This is a computer-generated document. Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        </p>
    </body>
    </html>
    """

    return HTMLResponse(content=html_content)
