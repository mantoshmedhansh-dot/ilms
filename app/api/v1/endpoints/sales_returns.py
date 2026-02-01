"""Sales Return Note (SRN) API endpoints."""
from typing import Optional, List
from uuid import UUID
from datetime import datetime, date, timezone
from decimal import Decimal

from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy import select, func, desc, and_, or_
from sqlalchemy.orm import selectinload
from pydantic import BaseModel

from app.api.deps import DB, get_current_user
from app.models.user import User
from app.models.purchase import SalesReturnNote, SRNItem, SRNStatus, ReturnReason
from app.models.order import Order
from app.models.customer import Customer
from app.models.warehouse import Warehouse
from app.services.document_sequence_service import DocumentSequenceService
from app.core.module_decorators import require_module

router = APIRouter()


# ==================== Schemas ====================

class SRNItemCreate(BaseModel):
    order_item_id: Optional[UUID] = None
    product_id: UUID
    variant_id: Optional[UUID] = None
    product_name: str
    sku: str
    quantity_sold: int
    quantity_returned: int
    unit_price: Decimal
    serial_numbers: Optional[List[str]] = None
    remarks: Optional[str] = None


class SRNCreate(BaseModel):
    order_id: Optional[UUID] = None
    invoice_id: Optional[UUID] = None
    customer_id: UUID
    warehouse_id: UUID
    srn_date: date
    return_reason: str
    return_reason_detail: Optional[str] = None
    pickup_required: bool = False
    pickup_address: Optional[dict] = None
    pickup_contact_name: Optional[str] = None
    pickup_contact_phone: Optional[str] = None
    items: List[SRNItemCreate]


class PickupSchedule(BaseModel):
    pickup_scheduled_date: date
    pickup_scheduled_slot: Optional[str] = None
    courier_id: Optional[UUID] = None


# ==================== Endpoints ====================

@router.get("/next-number")
@require_module("oms_fulfillment")
async def get_next_srn_number(
    db: DB,
    current_user: User = Depends(get_current_user),
):
    """Get the next SRN number."""
    seq_service = DocumentSequenceService(db)
    next_number = await seq_service.get_next_number("SRN")
    return {"srn_number": next_number}


@router.get("")
@require_module("oms_fulfillment")
async def list_sales_returns(
    db: DB,
    current_user: User = Depends(get_current_user),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    status: Optional[str] = None,
    customer_id: Optional[UUID] = None,
    warehouse_id: Optional[UUID] = None,
    return_reason: Optional[str] = None,
    pickup_status: Optional[str] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    search: Optional[str] = None,
):
    """List sales return notes with filtering."""
    query = select(SalesReturnNote).options(
        selectinload(SalesReturnNote.customer),
        selectinload(SalesReturnNote.warehouse),
        selectinload(SalesReturnNote.order),
        selectinload(SalesReturnNote.creator),
    )

    conditions = []

    if status:
        conditions.append(SalesReturnNote.status == status.upper())

    if customer_id:
        conditions.append(SalesReturnNote.customer_id == customer_id)

    if warehouse_id:
        conditions.append(SalesReturnNote.warehouse_id == warehouse_id)

    if return_reason:
        conditions.append(SalesReturnNote.return_reason == return_reason.upper())

    if pickup_status:
        conditions.append(SalesReturnNote.pickup_status == pickup_status.upper())

    if start_date:
        conditions.append(SalesReturnNote.srn_date >= start_date)

    if end_date:
        conditions.append(SalesReturnNote.srn_date <= end_date)

    if search:
        conditions.append(SalesReturnNote.srn_number.ilike(f"%{search}%"))

    if conditions:
        query = query.where(and_(*conditions))

    # Count
    count_query = select(func.count()).select_from(SalesReturnNote)
    if conditions:
        count_query = count_query.where(and_(*conditions))
    total = await db.scalar(count_query) or 0

    # Paginate
    query = query.order_by(desc(SalesReturnNote.created_at))
    query = query.offset((page - 1) * size).limit(size)

    result = await db.execute(query)
    srns = result.scalars().all()

    return {
        "items": [
            {
                "id": str(srn.id),
                "srn_number": srn.srn_number,
                "srn_date": srn.srn_date.isoformat() if srn.srn_date else None,
                "status": srn.status,
                "customer_id": str(srn.customer_id),
                "customer_name": f"{srn.customer.first_name} {srn.customer.last_name}" if srn.customer else None,
                "order_number": srn.order.order_number if srn.order else None,
                "warehouse_name": srn.warehouse.name if srn.warehouse else None,
                "return_reason": srn.return_reason,
                "resolution_type": srn.resolution_type,
                "total_items": srn.total_items,
                "total_quantity_returned": srn.total_quantity_returned,
                "total_quantity_accepted": srn.total_quantity_accepted,
                "total_value": float(srn.total_value) if srn.total_value else 0,
                "pickup_required": srn.pickup_required,
                "pickup_status": srn.pickup_status,
                "qc_status": srn.qc_status,
                "created_at": srn.created_at.isoformat() if srn.created_at else None,
            }
            for srn in srns
        ],
        "total": total,
        "page": page,
        "size": size,
        "pages": (total + size - 1) // size,
    }


@router.get("/stats")
@require_module("oms_fulfillment")
async def get_srn_stats(
    db: DB,
    current_user: User = Depends(get_current_user),
):
    """Get sales return statistics."""
    # By status
    status_query = select(
        SalesReturnNote.status,
        func.count().label("count")
    ).group_by(SalesReturnNote.status)
    status_result = await db.execute(status_query)
    by_status = {row[0]: row[1] for row in status_result.all()}

    # By return reason
    reason_query = select(
        SalesReturnNote.return_reason,
        func.count().label("count")
    ).group_by(SalesReturnNote.return_reason)
    reason_result = await db.execute(reason_query)
    by_reason = {row[0]: row[1] for row in reason_result.all()}

    # Pending pickups
    pending_pickup_query = select(func.count()).select_from(SalesReturnNote).where(
        and_(
            SalesReturnNote.pickup_required == True,
            SalesReturnNote.pickup_status.in_(["SCHEDULED", "NOT_REQUIRED"])
        )
    )
    pending_pickups = await db.scalar(pending_pickup_query) or 0

    # Pending QC
    pending_qc = by_status.get("PENDING_QC", 0) + by_status.get("RECEIVED", 0)

    return {
        "by_status": by_status,
        "by_reason": by_reason,
        "pending_pickups": pending_pickups,
        "pending_qc": pending_qc,
        "total": sum(by_status.values()),
    }


@router.get("/{srn_id}")
@require_module("oms_fulfillment")
async def get_sales_return(
    srn_id: UUID,
    db: DB,
    current_user: User = Depends(get_current_user),
):
    """Get sales return details."""
    query = select(SalesReturnNote).options(
        selectinload(SalesReturnNote.customer),
        selectinload(SalesReturnNote.warehouse),
        selectinload(SalesReturnNote.order),
        selectinload(SalesReturnNote.courier),
        selectinload(SalesReturnNote.credit_note),
        selectinload(SalesReturnNote.replacement_order),
        selectinload(SalesReturnNote.creator),
        selectinload(SalesReturnNote.receiver),
        selectinload(SalesReturnNote.qc_inspector),
        selectinload(SalesReturnNote.items).selectinload(SRNItem.product),
    ).where(SalesReturnNote.id == srn_id)

    result = await db.execute(query)
    srn = result.scalar_one_or_none()

    if not srn:
        raise HTTPException(status_code=404, detail="SRN not found")

    return {
        "id": str(srn.id),
        "srn_number": srn.srn_number,
        "srn_date": srn.srn_date.isoformat() if srn.srn_date else None,
        "status": srn.status,
        "customer": {
            "id": str(srn.customer_id),
            "name": f"{srn.customer.first_name} {srn.customer.last_name}" if srn.customer else None,
            "phone": srn.customer.phone if srn.customer else None,
        },
        "order": {
            "id": str(srn.order_id) if srn.order_id else None,
            "order_number": srn.order.order_number if srn.order else None,
        } if srn.order_id else None,
        "warehouse": {
            "id": str(srn.warehouse_id),
            "name": srn.warehouse.name if srn.warehouse else None,
        },
        "return_reason": srn.return_reason,
        "return_reason_detail": srn.return_reason_detail,
        "resolution_type": srn.resolution_type,
        "pickup_required": srn.pickup_required,
        "pickup_status": srn.pickup_status,
        "pickup_scheduled_date": srn.pickup_scheduled_date.isoformat() if srn.pickup_scheduled_date else None,
        "pickup_scheduled_slot": srn.pickup_scheduled_slot,
        "pickup_address": srn.pickup_address,
        "pickup_contact_name": srn.pickup_contact_name,
        "pickup_contact_phone": srn.pickup_contact_phone,
        "courier_name": srn.courier_name,
        "courier_tracking_number": srn.courier_tracking_number,
        "pickup_completed_at": srn.pickup_completed_at.isoformat() if srn.pickup_completed_at else None,
        "qc_required": srn.qc_required,
        "qc_status": srn.qc_status,
        "qc_done_by": srn.qc_inspector.email if srn.qc_inspector else None,
        "qc_done_at": srn.qc_done_at.isoformat() if srn.qc_done_at else None,
        "qc_remarks": srn.qc_remarks,
        "total_items": srn.total_items,
        "total_quantity_returned": srn.total_quantity_returned,
        "total_quantity_accepted": srn.total_quantity_accepted,
        "total_quantity_rejected": srn.total_quantity_rejected,
        "total_value": float(srn.total_value) if srn.total_value else 0,
        "put_away_complete": srn.put_away_complete,
        "credit_note": {
            "id": str(srn.credit_note_id) if srn.credit_note_id else None,
        } if srn.credit_note_id else None,
        "replacement_order": {
            "id": str(srn.replacement_order_id) if srn.replacement_order_id else None,
        } if srn.replacement_order_id else None,
        "received_by": srn.receiver.email if srn.receiver else None,
        "received_at": srn.received_at.isoformat() if srn.received_at else None,
        "receiving_remarks": srn.receiving_remarks,
        "photos_urls": srn.photos_urls,
        "items": [
            {
                "id": str(item.id),
                "product_id": str(item.product_id),
                "product_name": item.product_name,
                "sku": item.sku,
                "hsn_code": item.hsn_code,
                "quantity_sold": item.quantity_sold,
                "quantity_returned": item.quantity_returned,
                "quantity_accepted": item.quantity_accepted,
                "quantity_rejected": item.quantity_rejected,
                "unit_price": float(item.unit_price),
                "return_value": float(item.return_value) if item.return_value else 0,
                "serial_numbers": item.serial_numbers,
                "item_condition": item.item_condition,
                "restock_decision": item.restock_decision,
                "qc_result": item.qc_result,
                "rejection_reason": item.rejection_reason,
                "bin_location": item.bin_location,
                "remarks": item.remarks,
            }
            for item in srn.items
        ],
        "created_by": srn.creator.email if srn.creator else None,
        "created_at": srn.created_at.isoformat() if srn.created_at else None,
        "updated_at": srn.updated_at.isoformat() if srn.updated_at else None,
    }


@router.post("", status_code=status.HTTP_201_CREATED)
@require_module("oms_fulfillment")
async def create_sales_return(
    data: SRNCreate,
    db: DB,
    current_user: User = Depends(get_current_user),
):
    """Create a new sales return note."""
    # Validate customer
    customer = await db.get(Customer, data.customer_id)
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")

    # Get next SRN number
    seq_service = DocumentSequenceService(db)
    srn_number = await seq_service.get_next_number("SRN")

    # Create SRN
    srn = SalesReturnNote(
        srn_number=srn_number,
        srn_date=data.srn_date,
        status="DRAFT",
        order_id=data.order_id,
        invoice_id=data.invoice_id,
        customer_id=data.customer_id,
        warehouse_id=data.warehouse_id,
        return_reason=data.return_reason.upper(),
        return_reason_detail=data.return_reason_detail,
        pickup_required=data.pickup_required,
        pickup_status="NOT_REQUIRED" if not data.pickup_required else None,
        pickup_address=data.pickup_address,
        pickup_contact_name=data.pickup_contact_name,
        pickup_contact_phone=data.pickup_contact_phone,
        qc_required=True,
        total_items=len(data.items),
        created_by=current_user.id,
    )
    db.add(srn)
    await db.flush()

    # Create items
    total_quantity = 0
    for item_data in data.items:
        item = SRNItem(
            srn_id=srn.id,
            order_item_id=item_data.order_item_id,
            product_id=item_data.product_id,
            variant_id=item_data.variant_id,
            product_name=item_data.product_name,
            sku=item_data.sku,
            quantity_sold=item_data.quantity_sold,
            quantity_returned=item_data.quantity_returned,
            unit_price=item_data.unit_price,
            serial_numbers=item_data.serial_numbers,
            remarks=item_data.remarks,
            qc_result="PENDING",
        )
        db.add(item)
        total_quantity += item_data.quantity_returned

    srn.total_quantity_returned = total_quantity

    await db.commit()
    await db.refresh(srn)

    return {
        "id": str(srn.id),
        "srn_number": srn.srn_number,
        "message": "Sales return note created successfully",
    }


@router.post("/{srn_id}/schedule-pickup")
@require_module("oms_fulfillment")
async def schedule_pickup(
    srn_id: UUID,
    data: PickupSchedule,
    db: DB,
    current_user: User = Depends(get_current_user),
):
    """Schedule pickup for return."""
    srn = await db.get(SalesReturnNote, srn_id)
    if not srn:
        raise HTTPException(status_code=404, detail="SRN not found")

    if not srn.pickup_required:
        raise HTTPException(status_code=400, detail="Pickup not required for this SRN")

    srn.pickup_scheduled_date = data.pickup_scheduled_date
    srn.pickup_scheduled_slot = data.pickup_scheduled_slot
    srn.courier_id = data.courier_id
    srn.pickup_status = "SCHEDULED"
    srn.pickup_requested_at = datetime.now(timezone.utc)
    srn.status = "PENDING_RECEIPT"

    await db.commit()

    return {"message": "Pickup scheduled", "pickup_status": srn.pickup_status}


@router.post("/{srn_id}/receive")
@require_module("oms_fulfillment")
async def receive_return(
    srn_id: UUID,
    remarks: Optional[str] = None,
    db: DB = None,
    current_user: User = Depends(get_current_user),
):
    """Mark return as received at warehouse."""
    srn = await db.get(SalesReturnNote, srn_id)
    if not srn:
        raise HTTPException(status_code=404, detail="SRN not found")

    srn.status = "RECEIVED"
    srn.received_by = current_user.id
    srn.received_at = datetime.now(timezone.utc)
    srn.receiving_remarks = remarks

    if srn.pickup_required:
        srn.pickup_status = "DELIVERED"
        srn.pickup_completed_at = datetime.now(timezone.utc)

    # Move to pending QC if required
    if srn.qc_required:
        srn.status = "PENDING_QC"

    await db.commit()

    return {"message": "Return received", "status": srn.status}


@router.post("/{srn_id}/qc")
@require_module("oms_fulfillment")
async def complete_qc(
    srn_id: UUID,
    items: List[dict],  # [{"item_id": uuid, "qc_result": str, "quantity_accepted": int, "quantity_rejected": int, "item_condition": str, "restock_decision": str, "rejection_reason": str}]
    qc_remarks: Optional[str] = None,
    db: DB = None,
    current_user: User = Depends(get_current_user),
):
    """Complete QC for returned items."""
    srn = await db.get(SalesReturnNote, srn_id)
    if not srn:
        raise HTTPException(status_code=404, detail="SRN not found")

    if srn.status != "PENDING_QC":
        raise HTTPException(status_code=400, detail=f"Cannot QC SRN with status {srn.status}")

    total_accepted = 0
    total_rejected = 0
    total_value = Decimal("0")
    all_passed = True
    all_failed = True

    for item_data in items:
        item = await db.get(SRNItem, item_data["item_id"])
        if item and item.srn_id == srn_id:
            item.qc_result = item_data.get("qc_result", "PENDING")
            item.quantity_accepted = item_data.get("quantity_accepted", 0)
            item.quantity_rejected = item_data.get("quantity_rejected", 0)
            item.item_condition = item_data.get("item_condition")
            item.restock_decision = item_data.get("restock_decision")
            item.rejection_reason = item_data.get("rejection_reason")
            item.return_value = item.quantity_accepted * item.unit_price

            total_accepted += item.quantity_accepted
            total_rejected += item.quantity_rejected
            total_value += item.return_value

            if item.qc_result != "PASSED":
                all_passed = False
            if item.qc_result != "FAILED":
                all_failed = False

    srn.total_quantity_accepted = total_accepted
    srn.total_quantity_rejected = total_rejected
    srn.total_value = total_value
    srn.qc_done_by = current_user.id
    srn.qc_done_at = datetime.now(timezone.utc)
    srn.qc_remarks = qc_remarks

    if all_passed:
        srn.qc_status = "PASSED"
        srn.status = "QC_PASSED"
    elif all_failed:
        srn.qc_status = "FAILED"
        srn.status = "QC_FAILED"
    else:
        srn.qc_status = "CONDITIONAL"
        srn.status = "PARTIALLY_ACCEPTED"

    await db.commit()

    return {
        "message": "QC completed",
        "qc_status": srn.qc_status,
        "status": srn.status,
        "total_accepted": total_accepted,
        "total_rejected": total_rejected,
        "total_value": float(total_value),
    }


@router.post("/{srn_id}/resolve")
@require_module("oms_fulfillment")
async def resolve_return(
    srn_id: UUID,
    resolution_type: str,  # CREDIT_NOTE, REPLACEMENT, REFUND
    db: DB,
    current_user: User = Depends(get_current_user),
):
    """Set resolution type for the return."""
    srn = await db.get(SalesReturnNote, srn_id)
    if not srn:
        raise HTTPException(status_code=404, detail="SRN not found")

    if srn.status not in ["QC_PASSED", "PARTIALLY_ACCEPTED", "ACCEPTED"]:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot resolve SRN with status {srn.status}"
        )

    srn.resolution_type = resolution_type.upper()
    srn.status = "ACCEPTED"

    await db.commit()

    return {
        "message": f"Resolution set to {resolution_type}",
        "resolution_type": srn.resolution_type,
        "status": srn.status,
    }


@router.post("/{srn_id}/put-away")
@require_module("oms_fulfillment")
async def complete_put_away(
    srn_id: UUID,
    items: List[dict],  # [{"item_id": uuid, "bin_id": uuid, "bin_location": str}]
    db: DB,
    current_user: User = Depends(get_current_user),
):
    """Complete put-away for returned items."""
    srn = await db.get(SalesReturnNote, srn_id)
    if not srn:
        raise HTTPException(status_code=404, detail="SRN not found")

    for item_data in items:
        item = await db.get(SRNItem, item_data["item_id"])
        if item and item.srn_id == srn_id:
            item.bin_id = item_data.get("bin_id")
            item.bin_location = item_data.get("bin_location")

    srn.put_away_complete = True
    srn.put_away_at = datetime.now(timezone.utc)
    srn.status = "PUT_AWAY_COMPLETE"

    await db.commit()

    return {"message": "Put-away completed", "status": srn.status}
