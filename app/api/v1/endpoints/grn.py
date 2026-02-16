"""Goods Receipt Note (GRN) API endpoints."""
from typing import Optional, List
from uuid import UUID
from datetime import datetime, date, timezone
from decimal import Decimal

from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy import select, func, desc, and_, or_
from sqlalchemy.orm import selectinload, joinedload
from pydantic import BaseModel

from app.api.deps import DB, get_current_user
from app.models.user import User
from app.models.purchase import (
    GoodsReceiptNote, GRNItem, PurchaseOrder, PurchaseOrderItem,
    GRNStatus, QualityCheckResult
)
from app.models.vendor import Vendor
from app.models.warehouse import Warehouse
from app.models.product import Product
from app.services.document_sequence_service import DocumentSequenceService
from app.services.costing_service import CostingService
from app.services.channel_inventory_service import ChannelInventoryService, allocate_grn_to_channels
from app.services.grn_service import GRNService
from app.models.channel import SalesChannel, ChannelInventory, ProductChannelSettings
from app.core.module_decorators import require_module

router = APIRouter()


# ==================== Schemas ====================

class GRNItemCreate(BaseModel):
    po_item_id: UUID
    product_id: UUID
    variant_id: Optional[UUID] = None
    quantity_received: int
    batch_number: Optional[str] = None
    manufacturing_date: Optional[date] = None
    expiry_date: Optional[date] = None
    serial_numbers: Optional[List[str]] = None
    remarks: Optional[str] = None


class GRNCreate(BaseModel):
    purchase_order_id: UUID
    grn_date: date
    warehouse_id: UUID
    vendor_challan_number: Optional[str] = None
    vendor_challan_date: Optional[date] = None
    transporter_name: Optional[str] = None
    vehicle_number: Optional[str] = None
    lr_number: Optional[str] = None
    e_way_bill_number: Optional[str] = None
    receiving_remarks: Optional[str] = None
    items: List[GRNItemCreate]


class GRNQCUpdate(BaseModel):
    items: List[dict]  # [{"item_id": uuid, "qc_result": "PASSED/FAILED", "quantity_accepted": int, "quantity_rejected": int, "rejection_reason": str}]
    qc_remarks: Optional[str] = None


class ChannelAllocationItem(BaseModel):
    """Single channel allocation for a GRN item."""
    channel_id: UUID
    quantity: int
    buffer_quantity: int = 0
    safety_stock: Optional[int] = None
    reorder_point: Optional[int] = None


class GRNChannelAllocation(BaseModel):
    """Channel allocation request for GRN items."""
    allocations: List[ChannelAllocationItem]


# ==================== Endpoints ====================

@router.get("/next-number")
@require_module("procurement")
async def get_next_grn_number(
    db: DB,
    current_user: User = Depends(get_current_user),
):
    """Get the next GRN number."""
    seq_service = DocumentSequenceService(db)
    next_number = await seq_service.get_next_number("GRN")
    return {"grn_number": next_number}


@router.get("")
@require_module("procurement")
async def list_grns(
    db: DB,
    current_user: User = Depends(get_current_user),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    status: Optional[str] = None,
    vendor_id: Optional[UUID] = None,
    warehouse_id: Optional[UUID] = None,
    po_id: Optional[UUID] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    search: Optional[str] = None,
):
    """List GRNs with filtering and pagination."""
    query = select(GoodsReceiptNote).options(
        selectinload(GoodsReceiptNote.vendor),
        selectinload(GoodsReceiptNote.warehouse),
        selectinload(GoodsReceiptNote.purchase_order),
        selectinload(GoodsReceiptNote.received_by_user),
    )

    conditions = []

    if status:
        conditions.append(GoodsReceiptNote.status == status.upper())

    if vendor_id:
        conditions.append(GoodsReceiptNote.vendor_id == vendor_id)

    if warehouse_id:
        conditions.append(GoodsReceiptNote.warehouse_id == warehouse_id)

    if po_id:
        conditions.append(GoodsReceiptNote.purchase_order_id == po_id)

    if start_date:
        conditions.append(GoodsReceiptNote.grn_date >= start_date)

    if end_date:
        conditions.append(GoodsReceiptNote.grn_date <= end_date)

    if search:
        conditions.append(
            or_(
                GoodsReceiptNote.grn_number.ilike(f"%{search}%"),
                GoodsReceiptNote.vendor_challan_number.ilike(f"%{search}%"),
            )
        )

    if conditions:
        query = query.where(and_(*conditions))

    # Count total
    count_query = select(func.count()).select_from(GoodsReceiptNote)
    if conditions:
        count_query = count_query.where(and_(*conditions))
    total = await db.scalar(count_query) or 0

    # Paginate
    query = query.order_by(desc(GoodsReceiptNote.created_at))
    query = query.offset((page - 1) * size).limit(size)

    result = await db.execute(query)
    grns = result.scalars().all()

    return {
        "items": [
            {
                "id": str(grn.id),
                "grn_number": grn.grn_number,
                "grn_date": grn.grn_date.isoformat() if grn.grn_date else None,
                "status": grn.status,
                "purchase_order_id": str(grn.purchase_order_id),
                "po_number": grn.purchase_order.po_number if grn.purchase_order else None,
                "vendor_id": str(grn.vendor_id),
                "vendor_name": grn.vendor.name if grn.vendor else None,
                "warehouse_id": str(grn.warehouse_id),
                "warehouse_name": grn.warehouse.name if grn.warehouse else None,
                "vendor_challan_number": grn.vendor_challan_number,
                "total_items": grn.total_items,
                "total_quantity_received": grn.total_quantity_received,
                "total_quantity_accepted": grn.total_quantity_accepted,
                "total_quantity_rejected": grn.total_quantity_rejected,
                "total_value": float(grn.total_value) if grn.total_value else 0,
                "qc_status": grn.qc_status,
                "received_by": grn.received_by_user.email if grn.received_by_user else None,
                "created_at": grn.created_at.isoformat() if grn.created_at else None,
            }
            for grn in grns
        ],
        "total": total,
        "page": page,
        "size": size,
        "pages": (total + size - 1) // size,
    }


@router.get("/stats")
@require_module("procurement")
async def get_grn_stats(
    db: DB,
    current_user: User = Depends(get_current_user),
):
    """Get GRN statistics."""
    # Count by status
    status_query = select(
        GoodsReceiptNote.status,
        func.count().label("count")
    ).group_by(GoodsReceiptNote.status)

    status_result = await db.execute(status_query)
    by_status = {row[0]: row[1] for row in status_result.all()}

    # Pending QC count
    pending_qc = by_status.get("PENDING_QC", 0)

    # Today's GRNs
    today = date.today()
    today_query = select(func.count()).select_from(GoodsReceiptNote).where(
        GoodsReceiptNote.grn_date == today
    )
    today_count = await db.scalar(today_query) or 0

    # Pending put-away
    put_away_pending = by_status.get("PUT_AWAY_PENDING", 0)

    return {
        "by_status": by_status,
        "pending_qc": pending_qc,
        "today_received": today_count,
        "put_away_pending": put_away_pending,
        "total": sum(by_status.values()),
    }


@router.get("/{grn_id}")
@require_module("procurement")
async def get_grn(
    grn_id: UUID,
    db: DB,
    current_user: User = Depends(get_current_user),
):
    """Get GRN details."""
    query = select(GoodsReceiptNote).options(
        selectinload(GoodsReceiptNote.vendor),
        selectinload(GoodsReceiptNote.warehouse),
        selectinload(GoodsReceiptNote.purchase_order),
        selectinload(GoodsReceiptNote.received_by_user),
        selectinload(GoodsReceiptNote.qc_done_by_user),
        selectinload(GoodsReceiptNote.items).selectinload(GRNItem.product),
    ).where(GoodsReceiptNote.id == grn_id)

    result = await db.execute(query)
    grn = result.scalar_one_or_none()

    if not grn:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="GRN not found"
        )

    return {
        "id": str(grn.id),
        "grn_number": grn.grn_number,
        "grn_date": grn.grn_date.isoformat() if grn.grn_date else None,
        "status": grn.status,
        "purchase_order": {
            "id": str(grn.purchase_order_id),
            "po_number": grn.purchase_order.po_number if grn.purchase_order else None,
        },
        "vendor": {
            "id": str(grn.vendor_id),
            "name": grn.vendor.name if grn.vendor else None,
        },
        "warehouse": {
            "id": str(grn.warehouse_id),
            "name": grn.warehouse.name if grn.warehouse else None,
        },
        "vendor_challan_number": grn.vendor_challan_number,
        "vendor_challan_date": grn.vendor_challan_date.isoformat() if grn.vendor_challan_date else None,
        "transporter_name": grn.transporter_name,
        "vehicle_number": grn.vehicle_number,
        "lr_number": grn.lr_number,
        "e_way_bill_number": grn.e_way_bill_number,
        "total_items": grn.total_items,
        "total_quantity_received": grn.total_quantity_received,
        "total_quantity_accepted": grn.total_quantity_accepted,
        "total_quantity_rejected": grn.total_quantity_rejected,
        "total_value": float(grn.total_value) if grn.total_value else 0,
        "qc_required": grn.qc_required,
        "qc_status": grn.qc_status,
        "qc_done_by": grn.qc_done_by_user.email if grn.qc_done_by_user else None,
        "qc_done_at": grn.qc_done_at.isoformat() if grn.qc_done_at else None,
        "qc_remarks": grn.qc_remarks,
        "receiving_remarks": grn.receiving_remarks,
        "put_away_complete": grn.put_away_complete,
        "put_away_at": grn.put_away_at.isoformat() if grn.put_away_at else None,
        "received_by": grn.received_by_user.email if grn.received_by_user else None,
        "photos_urls": grn.photos_urls,
        "items": [
            {
                "id": str(item.id),
                "po_item_id": str(item.po_item_id),
                "product_id": str(item.product_id),
                "product_name": item.product_name,
                "sku": item.sku,
                "part_code": item.part_code,
                "hsn_code": item.hsn_code,
                "quantity_expected": item.quantity_expected,
                "quantity_received": item.quantity_received,
                "quantity_accepted": item.quantity_accepted,
                "quantity_rejected": item.quantity_rejected,
                "unit_price": float(item.unit_price) if item.unit_price else 0,
                "accepted_value": float(item.accepted_value) if item.accepted_value else 0,
                "batch_number": item.batch_number,
                "manufacturing_date": item.manufacturing_date.isoformat() if item.manufacturing_date else None,
                "expiry_date": item.expiry_date.isoformat() if item.expiry_date else None,
                "serial_numbers": item.serial_numbers,
                "bin_location": item.bin_location,
                "qc_result": item.qc_result,
                "rejection_reason": item.rejection_reason,
                "remarks": item.remarks,
            }
            for item in grn.items
        ],
        "created_at": grn.created_at.isoformat() if grn.created_at else None,
        "updated_at": grn.updated_at.isoformat() if grn.updated_at else None,
    }


@router.post("", status_code=status.HTTP_201_CREATED)
@require_module("procurement")
async def create_grn(
    data: GRNCreate,
    db: DB,
    current_user: User = Depends(get_current_user),
):
    """Create a new GRN against a Purchase Order."""
    # Validate PO exists
    po = await db.get(PurchaseOrder, data.purchase_order_id)
    if not po:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Purchase Order not found"
        )

    if po.status not in ["APPROVED", "SENT_TO_VENDOR", "ACKNOWLEDGED", "PARTIALLY_RECEIVED"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot create GRN for PO with status {po.status}"
        )

    # Get next GRN number
    seq_service = DocumentSequenceService(db)
    grn_number = await seq_service.get_next_number("GRN")

    # Create GRN
    grn = GoodsReceiptNote(
        grn_number=grn_number,
        grn_date=data.grn_date,
        status="DRAFT",
        purchase_order_id=data.purchase_order_id,
        vendor_id=po.vendor_id,
        warehouse_id=data.warehouse_id,
        vendor_challan_number=data.vendor_challan_number,
        vendor_challan_date=data.vendor_challan_date,
        transporter_name=data.transporter_name,
        vehicle_number=data.vehicle_number,
        lr_number=data.lr_number,
        e_way_bill_number=data.e_way_bill_number,
        receiving_remarks=data.receiving_remarks,
        received_by=current_user.id,
        qc_required=True,
        total_items=len(data.items),
    )
    db.add(grn)
    await db.flush()

    # Create GRN items
    total_quantity = 0
    total_value = Decimal("0")

    for item_data in data.items:
        # Get PO item for product details
        po_item = await db.get(PurchaseOrderItem, item_data.po_item_id)
        if not po_item:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"PO Item {item_data.po_item_id} not found"
            )

        grn_item = GRNItem(
            grn_id=grn.id,
            po_item_id=item_data.po_item_id,
            product_id=item_data.product_id,
            variant_id=item_data.variant_id,
            product_name=po_item.product_name,
            sku=po_item.sku,
            part_code=po_item.part_code,
            hsn_code=po_item.hsn_code,
            quantity_expected=po_item.quantity_ordered - po_item.quantity_received,
            quantity_received=item_data.quantity_received,
            unit_price=po_item.unit_price,
            batch_number=item_data.batch_number,
            manufacturing_date=item_data.manufacturing_date,
            expiry_date=item_data.expiry_date,
            serial_numbers=item_data.serial_numbers,
            remarks=item_data.remarks,
            qc_result="PENDING",
        )
        db.add(grn_item)

        total_quantity += item_data.quantity_received

    grn.total_quantity_received = total_quantity
    grn.qc_status = "PENDING"

    await db.commit()
    await db.refresh(grn)

    return {
        "id": str(grn.id),
        "grn_number": grn.grn_number,
        "status": grn.status,
        "message": "GRN created successfully",
    }


@router.post("/{grn_id}/submit")
@require_module("procurement")
async def submit_grn(
    grn_id: UUID,
    db: DB,
    current_user: User = Depends(get_current_user),
):
    """Submit GRN for QC."""
    grn = await db.get(GoodsReceiptNote, grn_id)
    if not grn:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="GRN not found"
        )

    if grn.status != "DRAFT":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot submit GRN with status {grn.status}"
        )

    grn.status = "PENDING_QC"
    await db.commit()

    return {"message": "GRN submitted for QC", "status": grn.status}


@router.post("/{grn_id}/qc")
@require_module("procurement")
async def complete_qc(
    grn_id: UUID,
    data: GRNQCUpdate,
    db: DB,
    current_user: User = Depends(get_current_user),
):
    """Complete QC for GRN items."""
    grn = await db.get(GoodsReceiptNote, grn_id)
    if not grn:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="GRN not found"
        )

    if grn.status != "PENDING_QC":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot perform QC on GRN with status {grn.status}"
        )

    total_accepted = 0
    total_rejected = 0
    all_passed = True
    all_failed = True

    for item_update in data.items:
        item = await db.get(GRNItem, item_update["item_id"])
        if item and item.grn_id == grn_id:
            item.qc_result = item_update.get("qc_result", "PENDING")
            item.quantity_accepted = item_update.get("quantity_accepted", 0)
            item.quantity_rejected = item_update.get("quantity_rejected", 0)
            item.rejection_reason = item_update.get("rejection_reason")
            item.accepted_value = item.quantity_accepted * item.unit_price

            total_accepted += item.quantity_accepted
            total_rejected += item.quantity_rejected

            if item.qc_result != "PASSED":
                all_passed = False
            if item.qc_result != "FAILED":
                all_failed = False

    # Update GRN totals
    grn.total_quantity_accepted = total_accepted
    grn.total_quantity_rejected = total_rejected

    # Calculate total value
    items_query = select(GRNItem).where(GRNItem.grn_id == grn_id)
    result = await db.execute(items_query)
    items = result.scalars().all()
    grn.total_value = sum(item.accepted_value or Decimal("0") for item in items)

    # Set QC status
    if all_passed:
        grn.qc_status = "PASSED"
        grn.status = "QC_PASSED"
    elif all_failed:
        grn.qc_status = "FAILED"
        grn.status = "QC_FAILED"
    else:
        grn.qc_status = "CONDITIONAL"
        grn.status = "PARTIALLY_ACCEPTED"

    grn.qc_done_by = current_user.id
    grn.qc_done_at = datetime.now(timezone.utc)
    grn.qc_remarks = data.qc_remarks

    await db.commit()

    return {
        "message": "QC completed",
        "qc_status": grn.qc_status,
        "status": grn.status,
        "total_accepted": total_accepted,
        "total_rejected": total_rejected,
    }


@router.get("/{grn_id}/validate-serials")
@require_module("procurement")
async def validate_grn_serials(
    grn_id: UUID,
    db: DB,
    current_user: User = Depends(get_current_user),
):
    """
    Validate serial numbers in GRN against PO serials.

    Returns validation result showing:
    - matched: Serials that match PO serials
    - not_in_po: Serials scanned but not in PO
    - already_received: Serials already received in another GRN
    - requires_force: True if GRN needs to be forced due to mismatches
    """
    grn_service = GRNService(db)
    try:
        result = await grn_service.validate_grn_serials(grn_id)
        return result
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/{grn_id}/force")
@require_module("procurement")
async def force_grn(
    grn_id: UUID,
    reason: str,
    db: DB,
    current_user: User = Depends(get_current_user),
):
    """
    Force GRN acceptance when serials don't match.

    Requires 'grn:force_receive' permission (typically only Supply Chain Head).
    This bypasses serial validation and allows GRN to proceed.
    """
    grn_service = GRNService(db)

    # Check permission
    has_permission = await grn_service.check_force_permission(current_user.id)
    if not has_permission:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to force GRN. Only Supply Chain Head can do this."
        )

    try:
        result = await grn_service.force_grn_receive(
            grn_id=grn_id,
            force_reason=reason,
            user_id=current_user.id,
        )
        return result
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/{grn_id}/serial-status")
@require_module("procurement")
async def get_grn_serial_status(
    grn_id: UUID,
    db: DB,
    current_user: User = Depends(get_current_user),
):
    """
    Get GRN with detailed serial validation status for each item.
    """
    grn_service = GRNService(db)
    result = await grn_service.get_grn_with_serial_status(grn_id)

    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="GRN not found"
        )

    return result


@router.post("/{grn_id}/accept")
@require_module("procurement")
async def accept_grn(
    grn_id: UUID,
    db: DB,
    current_user: User = Depends(get_current_user),
    skip_serial_validation: bool = False,
):
    """
    Accept GRN after QC and create stock items.

    This endpoint:
    1. Validates serials against PO serials (unless is_forced or skip_serial_validation)
    2. Updates PO quantities
    3. Creates stock_items from serials
    4. Updates inventory_summary
    5. Updates product costs (COGS)
    """
    grn = await db.get(GoodsReceiptNote, grn_id)
    if not grn:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="GRN not found"
        )

    if grn.status not in ["QC_PASSED", "PARTIALLY_ACCEPTED"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot accept GRN with status {grn.status}"
        )

    grn_service = GRNService(db)

    # Validate serials (unless forced or skipped)
    if not grn.is_forced and not skip_serial_validation:
        validation = await grn_service.validate_grn_serials(grn_id)
        if not validation["is_valid"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "message": "Serial validation failed. Use /force endpoint to bypass.",
                    "validation": validation,
                }
            )
        grn.serial_validation_status = "VALIDATED"
    elif grn.is_forced:
        grn.serial_validation_status = "SKIPPED"
    else:
        grn.serial_validation_status = "SKIPPED"

    # Update PO item received quantities
    items_query = select(GRNItem).where(GRNItem.grn_id == grn_id)
    result = await db.execute(items_query)
    items = result.scalars().all()

    for item in items:
        po_item = await db.get(PurchaseOrderItem, item.po_item_id)
        if po_item:
            po_item.quantity_received += item.quantity_accepted
            po_item.quantity_accepted += item.quantity_accepted
            po_item.quantity_rejected += item.quantity_rejected

    # Update PO status
    po = await db.get(PurchaseOrder, grn.purchase_order_id)
    if po:
        po.total_received_value += grn.total_value

        # Check if fully received
        po_items_query = select(PurchaseOrderItem).where(
            PurchaseOrderItem.purchase_order_id == po.id
        )
        po_result = await db.execute(po_items_query)
        po_items = po_result.scalars().all()

        fully_received = all(
            item.quantity_received >= item.quantity_ordered
            for item in po_items
        )

        if fully_received:
            po.status = "FULLY_RECEIVED"
        else:
            po.status = "PARTIALLY_RECEIVED"

    grn.status = "ACCEPTED"
    await db.commit()

    # Update Product Costs (COGS) using Weighted Average Cost
    costing_result = None
    try:
        costing_service = CostingService(db)
        costing_result = await costing_service.update_cost_on_grn_acceptance(grn_id)
    except Exception as e:
        # Log error but don't fail the GRN acceptance
        import logging
        logging.getLogger(__name__).error(f"Failed to update product costs for GRN {grn_id}: {e}")

    # Create stock items and update inventory
    stock_result = None
    try:
        stock_result = await grn_service.create_stock_items_from_grn(
            grn_id=grn_id,
            user_id=current_user.id,
        )
    except Exception as e:
        import logging

        logging.getLogger(__name__).error(f"Failed to create stock items for GRN {grn_id}: {e}")
        # Don't fail the acceptance, but include the error
        stock_result = {"error": str(e)}

    # GAP C: Auto-create draft vendor invoice from GRN + PO data
    vendor_invoice_ref = None
    try:
        if po:
            from app.models.purchase import VendorInvoice
            import uuid as _uuid

            # Generate reference number
            vi_date = datetime.now(timezone.utc).strftime("%Y%m%d")
            vi_seq = await db.execute(
                select(func.count(VendorInvoice.id)).where(
                    VendorInvoice.our_reference.like(f"VI-{vi_date}%")
                )
            )
            vi_count = (vi_seq.scalar() or 0) + 1
            our_ref = f"VI-{vi_date}-{vi_count:04d}"

            grn_value = grn.total_value or Decimal("0")
            # Proportional tax based on GRN value vs PO total
            ratio = grn_value / po.subtotal if po.subtotal and po.subtotal > 0 else Decimal("1")
            cgst = (po.cgst_amount or Decimal("0")) * ratio
            sgst = (po.sgst_amount or Decimal("0")) * ratio
            igst = (po.igst_amount or Decimal("0")) * ratio
            cess = (po.cess_amount or Decimal("0")) * ratio
            total_tax = cgst + sgst + igst + cess
            grand_total = grn_value + total_tax

            # Compute due date from PO credit_days
            from datetime import timedelta
            due_date_val = date.today() + timedelta(days=po.credit_days or 30)

            vendor_invoice = VendorInvoice(
                id=_uuid.uuid4(),
                invoice_number=f"AUTO-{grn.grn_number}",
                invoice_date=date.today(),
                our_reference=our_ref,
                status="UNDER_VERIFICATION",
                vendor_id=grn.vendor_id,
                purchase_order_id=po.id,
                grn_id=grn.id,
                subtotal=grn_value,
                discount_amount=Decimal("0"),
                taxable_amount=grn_value,
                cgst_amount=cgst.quantize(Decimal("0.01")),
                sgst_amount=sgst.quantize(Decimal("0.01")),
                igst_amount=igst.quantize(Decimal("0.01")),
                cess_amount=cess.quantize(Decimal("0.01")),
                total_tax=total_tax.quantize(Decimal("0.01")),
                freight_charges=Decimal("0"),
                other_charges=Decimal("0"),
                round_off=Decimal("0"),
                grand_total=grand_total.quantize(Decimal("0.01")),
                due_date=due_date_val,
                amount_paid=Decimal("0"),
                balance_due=grand_total.quantize(Decimal("0.01")),
                tds_applicable=True,
                tds_rate=Decimal("0"),
                tds_amount=Decimal("0"),
                net_payable=grand_total.quantize(Decimal("0.01")),
                po_matched=True,
                grn_matched=True,
                received_by=current_user.id,
            )
            db.add(vendor_invoice)
            await db.commit()
            vendor_invoice_ref = our_ref
            import logging
            logging.getLogger(__name__).info(
                f"Auto-created vendor invoice {our_ref} for GRN {grn.grn_number}"
            )
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning(
            f"Auto vendor invoice creation failed for GRN {grn_id}: {e}"
        )

    return {
        "message": "GRN accepted, stock items created, and inventory updated",
        "status": grn.status,
        "po_status": po.status if po else None,
        "cost_update": costing_result,
        "stock_items": stock_result,
        "serial_validation_status": grn.serial_validation_status,
        "vendor_invoice": vendor_invoice_ref,
    }


@router.post("/{grn_id}/put-away")
@require_module("procurement")
async def complete_put_away(
    grn_id: UUID,
    items: List[dict],  # [{"item_id": uuid, "bin_id": uuid, "bin_location": str}]
    db: DB,
    current_user: User = Depends(get_current_user),
):
    """Complete put-away for GRN items."""
    grn = await db.get(GoodsReceiptNote, grn_id)
    if not grn:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="GRN not found"
        )

    if grn.status != "ACCEPTED":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot put away GRN with status {grn.status}"
        )

    for item_data in items:
        item = await db.get(GRNItem, item_data["item_id"])
        if item and item.grn_id == grn_id:
            item.bin_id = item_data.get("bin_id")
            item.bin_location = item_data.get("bin_location")

    grn.put_away_complete = True
    grn.put_away_at = datetime.now(timezone.utc)
    grn.status = "PUT_AWAY_COMPLETE"

    await db.commit()

    return {"message": "Put-away completed", "status": grn.status}


@router.post("/{grn_id}/cancel")
@require_module("procurement")
async def cancel_grn(
    grn_id: UUID,
    reason: str,
    db: DB,
    current_user: User = Depends(get_current_user),
):
    """Cancel a GRN."""
    grn = await db.get(GoodsReceiptNote, grn_id)
    if not grn:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="GRN not found"
        )

    if grn.status in ["ACCEPTED", "PUT_AWAY_COMPLETE"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot cancel GRN that has been accepted or put away"
        )

    grn.status = "CANCELLED"
    grn.receiving_remarks = f"Cancelled: {reason}"

    await db.commit()

    return {"message": "GRN cancelled", "status": grn.status}


# ==================== Channel Allocation Endpoints ====================

@router.post("/{grn_id}/allocate-channels")
@require_module("procurement")
async def allocate_grn_to_channels_endpoint(
    grn_id: UUID,
    allocations: List[ChannelAllocationItem],
    db: DB,
    current_user: User = Depends(get_current_user),
):
    """
    Allocate received GRN quantity to sales channels.

    This endpoint should be called after GRN is accepted to distribute
    the received inventory across channels (D2C, Amazon, Flipkart, etc.).

    The allocation can be done:
    1. Manually by specifying exact quantities per channel
    2. Using default allocation rules from ProductChannelSettings (if no allocations provided)
    """
    # Get GRN with items
    query = select(GoodsReceiptNote).options(
        selectinload(GoodsReceiptNote.items)
    ).where(GoodsReceiptNote.id == grn_id)

    result = await db.execute(query)
    grn = result.scalar_one_or_none()

    if not grn:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="GRN not found"
        )

    if grn.status not in ["ACCEPTED", "PUT_AWAY_COMPLETE"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"GRN must be in ACCEPTED or PUT_AWAY_COMPLETE status. Current: {grn.status}"
        )

    service = ChannelInventoryService(db)
    allocation_results = []

    # Process each GRN item
    for grn_item in grn.items:
        if grn_item.quantity_accepted <= 0:
            continue

        product_id = grn_item.product_id
        quantity_to_allocate = grn_item.quantity_accepted
        item_allocations = []

        # Calculate total requested for this item
        total_requested = sum(a.quantity for a in allocations)

        if total_requested > quantity_to_allocate:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Total allocation ({total_requested}) exceeds accepted quantity ({quantity_to_allocate}) for product {product_id}"
            )

        # Allocate to each channel
        for alloc in allocations:
            alloc_result = await service.allocate_to_channel(
                channel_id=alloc.channel_id,
                warehouse_id=grn.warehouse_id,
                product_id=product_id,
                quantity=alloc.quantity,
                buffer_quantity=alloc.buffer_quantity,
                safety_stock=alloc.safety_stock,
                reorder_point=alloc.reorder_point,
            )
            item_allocations.append(alloc_result)

        allocation_results.append({
            "product_id": str(product_id),
            "product_name": grn_item.product_name,
            "quantity_accepted": quantity_to_allocate,
            "allocations": item_allocations,
            "unallocated": quantity_to_allocate - total_requested,
        })

    return {
        "grn_id": str(grn_id),
        "grn_number": grn.grn_number,
        "warehouse_id": str(grn.warehouse_id),
        "items": allocation_results,
        "message": "Channel allocation completed",
    }


@router.get("/{grn_id}/channel-allocation-defaults")
@require_module("procurement")
async def get_grn_channel_allocation_defaults(
    grn_id: UUID,
    db: DB,
    current_user: User = Depends(get_current_user),
):
    """
    Get default channel allocation suggestions for a GRN based on ProductChannelSettings.

    Returns suggested allocations per product based on:
    1. ProductChannelSettings for each product
    2. Active sales channels
    3. Historical allocation patterns
    """
    # Get GRN with items
    query = select(GoodsReceiptNote).options(
        selectinload(GoodsReceiptNote.items)
    ).where(GoodsReceiptNote.id == grn_id)

    result = await db.execute(query)
    grn = result.scalar_one_or_none()

    if not grn:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="GRN not found"
        )

    # Get active channels
    channels_result = await db.execute(
        select(SalesChannel).where(SalesChannel.status == "ACTIVE")
    )
    channels = channels_result.scalars().all()

    channel_map = {str(c.id): {"id": str(c.id), "code": c.code, "name": c.name, "type": c.channel_type} for c in channels}

    # Build defaults for each product
    product_defaults = []

    for grn_item in grn.items:
        if grn_item.quantity_accepted <= 0:
            continue

        product_id = grn_item.product_id
        quantity = grn_item.quantity_accepted

        # Get ProductChannelSettings for this product
        settings_result = await db.execute(
            select(ProductChannelSettings).where(
                and_(
                    ProductChannelSettings.product_id == product_id,
                    ProductChannelSettings.warehouse_id == grn.warehouse_id,
                    ProductChannelSettings.is_active == True,
                )
            )
        )
        settings = settings_result.scalars().all()

        channel_suggestions = []

        if settings:
            # Use configured settings
            remaining = quantity
            for setting in settings:
                channel_info = channel_map.get(str(setting.channel_id), {})

                if setting.default_allocation_percentage:
                    suggested_qty = int(quantity * setting.default_allocation_percentage / 100)
                elif setting.default_allocation_qty:
                    suggested_qty = min(setting.default_allocation_qty, remaining)
                else:
                    suggested_qty = 0

                if suggested_qty > 0:
                    channel_suggestions.append({
                        "channel_id": str(setting.channel_id),
                        "channel_code": channel_info.get("code"),
                        "channel_name": channel_info.get("name"),
                        "suggested_quantity": suggested_qty,
                        "buffer_quantity": 0,
                        "safety_stock": setting.safety_stock,
                        "reorder_point": setting.reorder_point,
                    })
                    remaining -= suggested_qty

            # Add shared pool suggestion for remaining
            if remaining > 0:
                channel_suggestions.append({
                    "channel_id": None,
                    "channel_code": "SHARED",
                    "channel_name": "Shared Pool (GT/MT)",
                    "suggested_quantity": remaining,
                    "buffer_quantity": 0,
                    "safety_stock": 0,
                    "reorder_point": 0,
                })
        else:
            # No settings, suggest equal split across channels or all to shared pool
            channel_suggestions.append({
                "channel_id": None,
                "channel_code": "SHARED",
                "channel_name": "Shared Pool (GT/MT)",
                "suggested_quantity": quantity,
                "buffer_quantity": 0,
                "safety_stock": 0,
                "reorder_point": 0,
                "note": "No ProductChannelSettings found. Configure settings for automatic suggestions."
            })

        product_defaults.append({
            "product_id": str(product_id),
            "product_name": grn_item.product_name,
            "sku": grn_item.sku,
            "quantity_accepted": quantity,
            "channel_suggestions": channel_suggestions,
        })

    return {
        "grn_id": str(grn_id),
        "grn_number": grn.grn_number,
        "warehouse_id": str(grn.warehouse_id),
        "warehouse_name": grn.warehouse.name if hasattr(grn, 'warehouse') and grn.warehouse else None,
        "available_channels": list(channel_map.values()),
        "products": product_defaults,
    }
