"""Stock Adjustments API endpoints."""
import logging
from typing import Optional
from uuid import UUID, uuid4
from datetime import datetime, date, timezone
from decimal import Decimal

from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy import select, func, desc, and_, or_
from sqlalchemy.orm import selectinload

from app.api.deps import DB, get_current_user

logger = logging.getLogger(__name__)
from app.models.user import User
from app.models.stock_adjustment import StockAdjustment, StockAdjustmentItem, InventoryAudit
from app.models.warehouse import Warehouse
from app.models.product import Product
from app.services.document_sequence_service import DocumentSequenceService
from app.core.module_decorators import require_module

router = APIRouter()


# ==================== Get Adjustment Types ====================
@router.get("/meta/types")
@require_module("oms_fulfillment")
async def get_adjustment_types(
    db: DB,
    current_user: User = Depends(get_current_user),
):
    """Get list of adjustment types with descriptions."""
    return {
        "types": [
            {"value": "CYCLE_COUNT", "label": "Cycle Count", "description": "Physical count variance"},
            {"value": "DAMAGE", "label": "Damage", "description": "Damaged goods write-off"},
            {"value": "THEFT", "label": "Theft/Pilferage", "description": "Theft or pilferage adjustment"},
            {"value": "EXPIRY", "label": "Expiry", "description": "Expired goods write-off"},
            {"value": "QUALITY_ISSUE", "label": "Quality Issue", "description": "Quality defects adjustment"},
            {"value": "CORRECTION", "label": "Data Correction", "description": "Data entry correction"},
            {"value": "WRITE_OFF", "label": "Write Off", "description": "Complete write-off"},
            {"value": "FOUND", "label": "Found Stock", "description": "Found stock (positive adjustment)"},
            {"value": "OPENING_STOCK", "label": "Opening Stock", "description": "Initial stock entry"},
            {"value": "OTHER", "label": "Other", "description": "Other adjustment reason"},
        ]
    }


# ==================== Get Adjustment Statistics ====================
@router.get("/stats/summary")
@require_module("oms_fulfillment")
async def get_adjustment_stats(
    db: DB,
    current_user: User = Depends(get_current_user),
    warehouse_id: Optional[UUID] = None,
    days: int = Query(30, ge=1, le=365),
):
    """Get stock adjustment statistics for the specified period."""
    from datetime import timedelta

    start_date = datetime.now(timezone.utc) - timedelta(days=days)

    conditions = [StockAdjustment.adjustment_date >= start_date]
    if warehouse_id:
        conditions.append(StockAdjustment.warehouse_id == warehouse_id)

    # Total adjustments
    total_query = select(func.count()).select_from(StockAdjustment).where(and_(*conditions))
    total = await db.scalar(total_query) or 0

    # Total value impact
    value_query = select(func.sum(StockAdjustment.total_value_impact)).where(and_(*conditions))
    total_value = await db.scalar(value_query) or Decimal("0")

    # By type
    type_query = select(
        StockAdjustment.adjustment_type,
        func.count().label("count"),
        func.sum(StockAdjustment.total_value_impact).label("value")
    ).where(and_(*conditions)).group_by(StockAdjustment.adjustment_type)

    type_result = await db.execute(type_query)
    by_type = [
        {
            "type": row[0],
            "count": row[1],
            "value": float(row[2]) if row[2] else 0
        }
        for row in type_result.all()
    ]

    # By status
    status_query = select(
        StockAdjustment.status,
        func.count().label("count")
    ).where(and_(*conditions)).group_by(StockAdjustment.status)

    status_result = await db.execute(status_query)
    by_status = [{"status": row[0], "count": row[1]} for row in status_result.all()]

    return {
        "period_days": days,
        "total_adjustments": total,
        "total_value_impact": float(total_value),
        "by_type": by_type,
        "by_status": by_status,
    }


# ==================== List Inventory Audits ====================
@router.get("/audits")
@require_module("oms_fulfillment")
async def list_inventory_audits(
    db: DB,
    current_user: User = Depends(get_current_user),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    warehouse_id: Optional[UUID] = None,
    status: Optional[str] = None,
):
    """List inventory audits/cycle counts."""
    query = select(InventoryAudit).options(
        selectinload(InventoryAudit.warehouse),
        selectinload(InventoryAudit.assignee)
    )

    conditions = []
    if warehouse_id:
        conditions.append(InventoryAudit.warehouse_id == warehouse_id)
    if status:
        conditions.append(InventoryAudit.status == status.lower())

    if conditions:
        query = query.where(and_(*conditions))

    # Count total
    count_query = select(func.count()).select_from(InventoryAudit)
    if conditions:
        count_query = count_query.where(and_(*conditions))
    total = await db.scalar(count_query) or 0

    # Paginate
    query = query.order_by(desc(InventoryAudit.scheduled_date))
    query = query.offset((page - 1) * size).limit(size)

    result = await db.execute(query)
    audits = result.scalars().all()

    return {
        "items": [
            {
                "id": str(audit.id),
                "audit_number": audit.audit_number,
                "audit_name": audit.audit_name,
                "warehouse_id": str(audit.warehouse_id),
                "warehouse_name": audit.warehouse.name if audit.warehouse else None,
                "scheduled_date": audit.scheduled_date.isoformat() if audit.scheduled_date else None,
                "start_date": audit.start_date.isoformat() if audit.start_date else None,
                "end_date": audit.end_date.isoformat() if audit.end_date else None,
                "status": audit.status,
                "assigned_to": audit.assignee.email if audit.assignee else None,
                "total_items_counted": audit.total_items_counted,
                "variance_items": audit.variance_items,
                "total_variance_value": float(audit.total_variance_value) if audit.total_variance_value else 0,
            }
            for audit in audits
        ],
        "total": total,
        "page": page,
        "size": size,
        "pages": (total + size - 1) // size,
    }


# ==================== Create Inventory Audit ====================
@router.post("/audits", status_code=status.HTTP_201_CREATED)
@require_module("oms_fulfillment")
async def create_inventory_audit(
    data: dict,
    db: DB,
    current_user: User = Depends(get_current_user),
):
    """Schedule a new inventory audit/cycle count."""
    today = date.today()
    random_suffix = str(uuid4())[:8].upper()
    audit_number = f"AUDIT-{today.strftime('%Y%m%d')}-{random_suffix}"

    audit = InventoryAudit(
        audit_number=audit_number,
        audit_name=data.get("audit_name"),
        warehouse_id=data["warehouse_id"],
        category_id=data.get("category_id"),
        scheduled_date=data.get("scheduled_date"),
        status="planned",
        assigned_to=data.get("assigned_to"),
        created_by=current_user.id,
        notes=data.get("notes"),
    )

    db.add(audit)
    await db.commit()
    await db.refresh(audit)

    return {
        "id": str(audit.id),
        "audit_number": audit.audit_number,
        "message": "Inventory audit scheduled successfully"
    }


# ==================== List Stock Adjustments ====================
@router.get("")
@require_module("oms_fulfillment")
async def list_stock_adjustments(
    db: DB,
    current_user: User = Depends(get_current_user),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    warehouse_id: Optional[UUID] = None,
    adjustment_type: Optional[str] = None,
    status: Optional[str] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    search: Optional[str] = None,
):
    """
    List stock adjustments with filtering.

    Filters:
    - warehouse_id: Filter by warehouse
    - adjustment_type: CYCLE_COUNT, DAMAGE, THEFT, EXPIRY, QUALITY_ISSUE, CORRECTION, WRITE_OFF, FOUND, OPENING_STOCK, OTHER
    - status: DRAFT, PENDING_APPROVAL, APPROVED, REJECTED, COMPLETED, CANCELLED
    - start_date/end_date: Date range filter
    - search: Search in adjustment number
    """
    query = select(StockAdjustment).options(
        selectinload(StockAdjustment.warehouse),
        selectinload(StockAdjustment.creator),
        selectinload(StockAdjustment.items)
    )

    conditions = []

    if warehouse_id:
        conditions.append(StockAdjustment.warehouse_id == warehouse_id)

    if adjustment_type:
        conditions.append(StockAdjustment.adjustment_type == adjustment_type.upper())

    if status:
        conditions.append(StockAdjustment.status == status.upper())

    if start_date:
        conditions.append(StockAdjustment.adjustment_date >= datetime.combine(start_date, datetime.min.time()))

    if end_date:
        conditions.append(StockAdjustment.adjustment_date <= datetime.combine(end_date, datetime.max.time()))

    if search:
        conditions.append(StockAdjustment.adjustment_number.ilike(f"%{search}%"))

    if conditions:
        query = query.where(and_(*conditions))

    # Count total
    count_query = select(func.count()).select_from(StockAdjustment)
    if conditions:
        count_query = count_query.where(and_(*conditions))
    total = await db.scalar(count_query) or 0

    # Get paginated results
    query = query.order_by(desc(StockAdjustment.adjustment_date))
    query = query.offset((page - 1) * size).limit(size)

    result = await db.execute(query)
    adjustments = result.scalars().unique().all()

    return {
        "items": [
            {
                "id": str(adj.id),
                "adjustment_number": adj.adjustment_number,
                "adjustment_type": adj.adjustment_type,
                "status": adj.status,
                "warehouse_id": str(adj.warehouse_id),
                "warehouse_name": adj.warehouse.name if adj.warehouse else None,
                "adjustment_date": adj.adjustment_date.isoformat() if adj.adjustment_date else None,
                "total_items": adj.total_items,
                "total_quantity_adjusted": adj.total_quantity_adjusted,
                "total_value_impact": float(adj.total_value_impact) if adj.total_value_impact else 0,
                "reason": adj.reason,
                "created_by": adj.creator.email if adj.creator else None,
                "approved_at": adj.approved_at.isoformat() if adj.approved_at else None,
                "created_at": adj.created_at.isoformat() if adj.created_at else None,
            }
            for adj in adjustments
        ],
        "total": total,
        "page": page,
        "size": size,
        "pages": (total + size - 1) // size,
    }


# ==================== Create Stock Adjustment ====================
@router.post("", status_code=status.HTTP_201_CREATED)
@require_module("oms_fulfillment")
async def create_stock_adjustment(
    data: dict,
    db: DB,
    current_user: User = Depends(get_current_user),
):
    """
    Create a new stock adjustment.

    Request body:
    - warehouse_id: UUID
    - adjustment_type: str (CYCLE_COUNT, DAMAGE, etc.)
    - reason: str
    - items: list of adjustment items
    - notes: str (optional)
    """
    # Generate adjustment number (SA = Stock Adjustment)
    seq_service = DocumentSequenceService(db)
    adjustment_number = await seq_service.get_next_number("SA")

    # Calculate totals from items
    items_data = data.get("items", [])
    total_items = len(items_data)
    total_quantity = 0
    total_value = Decimal("0")

    for item in items_data:
        qty = int(item.get("adjustment_quantity", 0))
        value = Decimal(str(item.get("value_impact", 0)))
        total_quantity += abs(qty)
        total_value += value

    # Create adjustment
    adjustment = StockAdjustment(
        adjustment_number=adjustment_number,
        adjustment_type=data["adjustment_type"].upper(),
        status="DRAFT",
        warehouse_id=data["warehouse_id"],
        adjustment_date=datetime.now(timezone.utc),
        created_by=current_user.id,
        total_items=total_items,
        total_quantity_adjusted=total_quantity,
        total_value_impact=total_value,
        reason=data["reason"],
        reference_document=data.get("reference_document"),
        notes=data.get("notes"),
        requires_approval=data.get("requires_approval", True),
    )

    db.add(adjustment)
    await db.flush()

    # Create adjustment items
    for item in items_data:
        adj_item = StockAdjustmentItem(
            adjustment_id=adjustment.id,
            product_id=item["product_id"],
            variant_id=item.get("variant_id"),
            stock_item_id=item.get("stock_item_id"),
            system_quantity=item.get("system_quantity", 0),
            physical_quantity=item.get("physical_quantity", 0),
            adjustment_quantity=item.get("adjustment_quantity", 0),
            unit_cost=Decimal(str(item.get("unit_cost", 0))),
            value_impact=Decimal(str(item.get("value_impact", 0))),
            serial_number=item.get("serial_number"),
            reason=item.get("reason"),
        )
        db.add(adj_item)

    await db.commit()
    await db.refresh(adjustment)

    return {
        "id": str(adjustment.id),
        "adjustment_number": adjustment.adjustment_number,
        "status": adjustment.status,
        "message": "Stock adjustment created successfully"
    }


# ==================== Get Adjustment Details ====================
@router.get("/{adjustment_id}")
@require_module("oms_fulfillment")
async def get_stock_adjustment(
    adjustment_id: UUID,
    db: DB,
    current_user: User = Depends(get_current_user),
):
    """Get stock adjustment details with items."""
    query = select(StockAdjustment).options(
        selectinload(StockAdjustment.warehouse),
        selectinload(StockAdjustment.creator),
        selectinload(StockAdjustment.approver),
        selectinload(StockAdjustment.items).selectinload(StockAdjustmentItem.product)
    ).where(StockAdjustment.id == adjustment_id)

    result = await db.execute(query)
    adjustment = result.scalar_one_or_none()

    if not adjustment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Stock adjustment not found"
        )

    return {
        "id": str(adjustment.id),
        "adjustment_number": adjustment.adjustment_number,
        "adjustment_type": adjustment.adjustment_type,
        "status": adjustment.status,
        "warehouse": {
            "id": str(adjustment.warehouse.id),
            "name": adjustment.warehouse.name,
        } if adjustment.warehouse else None,
        "adjustment_date": adjustment.adjustment_date.isoformat() if adjustment.adjustment_date else None,
        "approved_at": adjustment.approved_at.isoformat() if adjustment.approved_at else None,
        "completed_at": adjustment.completed_at.isoformat() if adjustment.completed_at else None,
        "total_items": adjustment.total_items,
        "total_quantity_adjusted": adjustment.total_quantity_adjusted,
        "total_value_impact": float(adjustment.total_value_impact) if adjustment.total_value_impact else 0,
        "reason": adjustment.reason,
        "reference_document": adjustment.reference_document,
        "notes": adjustment.notes,
        "requires_approval": adjustment.requires_approval,
        "rejection_reason": adjustment.rejection_reason,
        "created_by": {
            "id": str(adjustment.creator.id),
            "name": f"{adjustment.creator.first_name} {adjustment.creator.last_name}",
            "email": adjustment.creator.email,
        } if adjustment.creator else None,
        "approved_by": {
            "id": str(adjustment.approver.id),
            "name": f"{adjustment.approver.first_name} {adjustment.approver.last_name}",
        } if adjustment.approver else None,
        "items": [
            {
                "id": str(item.id),
                "product_id": str(item.product_id),
                "product_name": item.product.name if item.product else None,
                "product_sku": item.product.sku if item.product else None,
                "variant_id": str(item.variant_id) if item.variant_id else None,
                "serial_number": item.serial_number,
                "system_quantity": item.system_quantity,
                "physical_quantity": item.physical_quantity,
                "adjustment_quantity": item.adjustment_quantity,
                "unit_cost": float(item.unit_cost) if item.unit_cost else 0,
                "value_impact": float(item.value_impact) if item.value_impact else 0,
                "reason": item.reason,
            }
            for item in (adjustment.items or [])
        ],
        "created_at": adjustment.created_at.isoformat() if adjustment.created_at else None,
        "updated_at": adjustment.updated_at.isoformat() if adjustment.updated_at else None,
    }


# ==================== Submit for Approval ====================
@router.post("/{adjustment_id}/submit")
@require_module("oms_fulfillment")
async def submit_adjustment(
    adjustment_id: UUID,
    db: DB,
    current_user: User = Depends(get_current_user),
):
    """Submit stock adjustment for approval."""
    adjustment = await db.get(StockAdjustment, adjustment_id)

    if not adjustment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Adjustment not found"
        )

    if adjustment.status != "DRAFT":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot submit adjustment in {adjustment.status} status"
        )

    adjustment.status = "PENDING_APPROVAL"

    await db.commit()

    return {"message": "Adjustment submitted for approval", "status": adjustment.status}


# ==================== Approve Adjustment ====================
@router.post("/{adjustment_id}/approve")
@require_module("oms_fulfillment")
async def approve_adjustment(
    adjustment_id: UUID,
    db: DB,
    current_user: User = Depends(get_current_user),
):
    """Approve stock adjustment and apply inventory changes."""
    query = select(StockAdjustment).options(
        selectinload(StockAdjustment.items)
    ).where(StockAdjustment.id == adjustment_id)

    result = await db.execute(query)
    adjustment = result.scalar_one_or_none()

    if not adjustment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Adjustment not found"
        )

    if adjustment.status != "PENDING_APPROVAL":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot approve adjustment in {adjustment.status} status"
        )

    # Update inventory for each item
    from app.models.inventory import Inventory

    for item in adjustment.items:
        # Find inventory record
        inv_query = select(Inventory).where(
            and_(
                Inventory.product_id == item.product_id,
                Inventory.warehouse_id == adjustment.warehouse_id
            )
        )
        if item.variant_id:
            inv_query = inv_query.where(Inventory.variant_id == item.variant_id)

        inv_result = await db.execute(inv_query)
        inventory = inv_result.scalar_one_or_none()

        if inventory:
            # Apply adjustment
            inventory.quantity += item.adjustment_quantity
            if inventory.quantity < 0:
                inventory.quantity = 0

    # Update adjustment status
    adjustment.status = "APPROVED"
    adjustment.approved_by = current_user.id
    adjustment.approved_at = datetime.now(timezone.utc)
    adjustment.completed_at = datetime.now(timezone.utc)

    await db.commit()

    # ============ ACCOUNTING INTEGRATION ============
    # Create journal entry for inventory adjustment
    try:
        from app.services.auto_journal_service import AutoJournalService, AutoJournalError
        from decimal import Decimal

        auto_journal = AutoJournalService(db)

        # Calculate total adjustment value
        total_value = Decimal("0")
        for item in adjustment.items:
            item_value = abs(item.adjustment_quantity) * (item.unit_cost or Decimal("0"))
            total_value += item_value

        if total_value > 0:
            # Determine if positive or negative overall adjustment
            total_qty = sum(item.adjustment_quantity for item in adjustment.items)
            adjustment_type = "POSITIVE" if total_qty > 0 else "NEGATIVE"

            await auto_journal.generate_for_stock_adjustment(
                adjustment_id=adjustment.id,
                adjustment_number=adjustment.adjustment_number,
                adjustment_type=adjustment_type,
                total_value=total_value,
                reason=adjustment.reason or "Stock adjustment",
                user_id=current_user.id,
                auto_post=True,
            )
            await db.commit()
            logger.info(f"Accounting entry created for stock adjustment {adjustment.adjustment_number}")
    except AutoJournalError as e:
        logger.warning(f"Failed to create accounting entry for adjustment {adjustment.adjustment_number}: {e.message}")
    except Exception as e:
        logger.warning(f"Unexpected error creating accounting entry for adjustment: {str(e)}")

    return {
        "message": "Adjustment approved and inventory updated",
        "status": adjustment.status
    }


# ==================== Reject Adjustment ====================
@router.post("/{adjustment_id}/reject")
@require_module("oms_fulfillment")
async def reject_adjustment(
    adjustment_id: UUID,
    data: dict,
    db: DB,
    current_user: User = Depends(get_current_user),
):
    """Reject stock adjustment."""
    adjustment = await db.get(StockAdjustment, adjustment_id)

    if not adjustment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Adjustment not found"
        )

    if adjustment.status != "PENDING_APPROVAL":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot reject adjustment in {adjustment.status} status"
        )

    adjustment.status = "REJECTED"
    adjustment.rejection_reason = data.get("reason")
    adjustment.approved_by = current_user.id
    adjustment.approved_at = datetime.now(timezone.utc)

    await db.commit()

    return {"message": "Adjustment rejected", "status": adjustment.status}
