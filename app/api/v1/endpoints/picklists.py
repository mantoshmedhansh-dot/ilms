"""Picklist API endpoints for warehouse picking operations."""
from typing import Optional
import uuid
from math import ceil
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, status, Query, Depends
from sqlalchemy import select, func, and_, or_
from sqlalchemy.orm import selectinload

from app.api.deps import DB, CurrentUser, require_permissions
from app.models.picklist import Picklist, PicklistItem, PicklistStatus, PicklistType
from app.models.order import Order, OrderItem, OrderStatus
from app.models.warehouse import Warehouse
from app.models.inventory import StockItem
from app.models.wms import WarehouseBin
from app.schemas.picklist import (
    PicklistGenerateRequest,
    PicklistCreate,
    PicklistUpdate,
    PicklistAssignRequest,
    PicklistResponse,
    PicklistDetailResponse,
    PicklistListResponse,
    PicklistItemResponse,
    PickScanRequest,
    PickScanResponse,
    PickConfirmRequest,
    PickShortRequest,
    PickCompleteRequest,
    PickCompleteResponse,
)


router = APIRouter()


def generate_picklist_number() -> str:
    """Generate unique picklist number."""
    from datetime import datetime, timezone
    import random
    date_str = datetime.now().strftime("%Y%m%d")
    random_suffix = random.randint(1000, 9999)
    return f"PL-{date_str}-{random_suffix}"


# ==================== PICKLIST CRUD ====================

@router.get(
    "",
    response_model=PicklistListResponse,
    dependencies=[Depends(require_permissions("orders:view"))]
)
async def list_picklists(
    db: DB,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    warehouse_id: Optional[uuid.UUID] = Query(None),
    status: Optional[PicklistStatus] = Query(None),
    picklist_type: Optional[PicklistType] = Query(None),
    assigned_to: Optional[uuid.UUID] = Query(None),
    search: Optional[str] = Query(None),
):
    """Get paginated list of picklists."""
    query = select(Picklist)
    count_query = select(func.count(Picklist.id))

    if warehouse_id:
        query = query.where(Picklist.warehouse_id == warehouse_id)
        count_query = count_query.where(Picklist.warehouse_id == warehouse_id)

    if status:
        query = query.where(Picklist.status == status)
        count_query = count_query.where(Picklist.status == status)

    if picklist_type:
        query = query.where(Picklist.picklist_type == picklist_type)
        count_query = count_query.where(Picklist.picklist_type == picklist_type)

    if assigned_to:
        query = query.where(Picklist.assigned_to == assigned_to)
        count_query = count_query.where(Picklist.assigned_to == assigned_to)

    if search:
        query = query.where(Picklist.picklist_number.ilike(f"%{search}%"))
        count_query = count_query.where(Picklist.picklist_number.ilike(f"%{search}%"))

    # Get total count
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # Get paginated results
    offset = (page - 1) * size
    query = query.order_by(Picklist.priority.asc(), Picklist.created_at.desc())
    query = query.offset(offset).limit(size)

    result = await db.execute(query)
    picklists = result.scalars().all()

    return PicklistListResponse(
        items=[PicklistResponse.model_validate(p) for p in picklists],
        total=total,
        page=page,
        size=size,
        pages=ceil(total / size) if total > 0 else 1,
    )


@router.get(
    "/{picklist_id}",
    response_model=PicklistDetailResponse,
    dependencies=[Depends(require_permissions("orders:view"))]
)
async def get_picklist(
    picklist_id: uuid.UUID,
    db: DB,
):
    """Get picklist with items."""
    query = (
        select(Picklist)
        .where(Picklist.id == picklist_id)
        .options(selectinload(Picklist.items))
    )
    result = await db.execute(query)
    picklist = result.scalar_one_or_none()

    if not picklist:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Picklist not found"
        )

    response_data = PicklistResponse.model_validate(picklist).model_dump()
    response_data["items"] = [PicklistItemResponse.model_validate(i) for i in picklist.items]

    return PicklistDetailResponse(**response_data)


@router.post(
    "/generate",
    response_model=PicklistDetailResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permissions("orders:create"))]
)
async def generate_picklist(
    data: PicklistGenerateRequest,
    db: DB,
    current_user: CurrentUser,
):
    """
    Generate picklist from orders.
    Collects all items from selected orders and creates picking tasks.
    """
    # Verify warehouse exists
    wh_query = select(Warehouse).where(Warehouse.id == data.warehouse_id)
    wh_result = await db.execute(wh_query)
    if not wh_result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Warehouse not found"
        )

    # Get orders
    orders_query = select(Order).where(
        and_(
            Order.id.in_(data.order_ids),
            Order.status.in_([OrderStatus.CONFIRMED, OrderStatus.ALLOCATED]),
        )
    ).options(selectinload(Order.items))

    orders_result = await db.execute(orders_query)
    orders = orders_result.scalars().all()

    if not orders:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No valid orders found for picklist generation"
        )

    # Create picklist
    picklist = Picklist(
        picklist_number=generate_picklist_number(),
        warehouse_id=data.warehouse_id,
        status=PicklistStatus.PENDING,
        picklist_type=data.picklist_type,
        priority=data.priority,
        total_orders=len(orders),
        notes=data.notes,
        created_by=current_user.id,
    )

    db.add(picklist)
    await db.flush()

    # Create picklist items from order items
    total_items = 0
    total_quantity = 0
    pick_sequence = 0

    for order in orders:
        for item in order.items:
            # Find bin location for product
            bin_query = (
                select(WarehouseBin)
                .join(StockItem, StockItem.bin_id == WarehouseBin.id)
                .where(
                    and_(
                        StockItem.product_id == item.product_id,
                        StockItem.warehouse_id == data.warehouse_id,
                        WarehouseBin.is_pickable == True,
                    )
                )
                .order_by(WarehouseBin.pick_sequence.asc())
            )
            bin_result = await db.execute(bin_query)
            bin_location = bin_result.scalar_one_or_none()

            picklist_item = PicklistItem(
                picklist_id=picklist.id,
                order_id=order.id,
                order_item_id=item.id,
                product_id=item.product_id,
                variant_id=item.variant_id,
                sku=item.product_sku,
                product_name=item.product_name,
                variant_name=item.variant_name,
                bin_id=bin_location.id if bin_location else None,
                bin_location=bin_location.bin_code if bin_location else None,
                quantity_required=item.quantity,
                pick_sequence=pick_sequence,
            )
            db.add(picklist_item)

            total_items += 1
            total_quantity += item.quantity
            pick_sequence += 1

        # Update order status
        order.status = OrderStatus.PICKLIST_CREATED.value

    picklist.total_items = total_items
    picklist.total_quantity = total_quantity

    await db.commit()
    await db.refresh(picklist)

    # Get full picklist with items
    query = (
        select(Picklist)
        .where(Picklist.id == picklist.id)
        .options(selectinload(Picklist.items))
    )
    result = await db.execute(query)
    picklist = result.scalar_one()

    response_data = PicklistResponse.model_validate(picklist).model_dump()
    response_data["items"] = [PicklistItemResponse.model_validate(i) for i in picklist.items]

    return PicklistDetailResponse(**response_data)


@router.put(
    "/{picklist_id}/assign",
    response_model=PicklistResponse,
    dependencies=[Depends(require_permissions("orders:update"))]
)
async def assign_picklist(
    picklist_id: uuid.UUID,
    data: PicklistAssignRequest,
    db: DB,
    current_user: CurrentUser,
):
    """Assign picker to picklist."""
    query = select(Picklist).where(Picklist.id == picklist_id)
    result = await db.execute(query)
    picklist = result.scalar_one_or_none()

    if not picklist:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Picklist not found"
        )

    if picklist.status not in [PicklistStatus.PENDING, PicklistStatus.ASSIGNED]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Picklist cannot be assigned in current status"
        )

    picklist.assigned_to = data.assigned_to
    picklist.assigned_at = datetime.now(timezone.utc)
    picklist.status = PicklistStatus.ASSIGNED.value

    await db.commit()
    await db.refresh(picklist)

    return PicklistResponse.model_validate(picklist)


@router.post(
    "/{picklist_id}/start",
    response_model=PicklistResponse,
    dependencies=[Depends(require_permissions("orders:update"))]
)
async def start_picking(
    picklist_id: uuid.UUID,
    db: DB,
    current_user: CurrentUser,
):
    """Start picking process."""
    query = select(Picklist).where(Picklist.id == picklist_id)
    result = await db.execute(query)
    picklist = result.scalar_one_or_none()

    if not picklist:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Picklist not found"
        )

    if picklist.status not in [PicklistStatus.PENDING, PicklistStatus.ASSIGNED]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Picklist cannot be started in current status"
        )

    picklist.status = PicklistStatus.IN_PROGRESS.value
    picklist.started_at = datetime.now(timezone.utc)
    if not picklist.assigned_to:
        picklist.assigned_to = current_user.id
        picklist.assigned_at = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(picklist)

    return PicklistResponse.model_validate(picklist)


@router.post(
    "/{picklist_id}/scan",
    response_model=PickScanResponse,
    dependencies=[Depends(require_permissions("orders:update"))]
)
async def scan_pick_item(
    picklist_id: uuid.UUID,
    data: PickScanRequest,
    db: DB,
    current_user: CurrentUser,
):
    """Scan item during picking."""
    # Get picklist
    picklist_query = select(Picklist).where(Picklist.id == picklist_id)
    picklist_result = await db.execute(picklist_query)
    picklist = picklist_result.scalar_one_or_none()

    if not picklist:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Picklist not found"
        )

    if picklist.status != PicklistStatus.IN_PROGRESS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Picklist is not in progress"
        )

    # Find matching item
    item_query = select(PicklistItem).where(
        and_(
            PicklistItem.picklist_id == picklist_id,
            PicklistItem.is_picked == False,
        )
    )

    if data.sku:
        item_query = item_query.where(PicklistItem.sku == data.sku)
    elif data.barcode:
        item_query = item_query.where(PicklistItem.sku == data.barcode)

    if data.bin_code:
        item_query = item_query.where(PicklistItem.bin_location == data.bin_code)

    item_query = item_query.order_by(PicklistItem.pick_sequence.asc())

    item_result = await db.execute(item_query)
    item = item_result.scalar_one_or_none()

    if not item:
        return PickScanResponse(
            success=False,
            message="Item not found in picklist or already picked",
            item=None,
            remaining_quantity=0,
        )

    # Update picked quantity
    item.quantity_picked += data.quantity
    item.picked_by = current_user.id
    item.picked_at = datetime.now(timezone.utc)

    if item.quantity_picked >= item.quantity_required:
        item.is_picked = True

    # Update picklist totals
    picklist.picked_quantity += data.quantity

    await db.commit()
    await db.refresh(item)

    return PickScanResponse(
        success=True,
        message=f"Picked {data.quantity} of {item.product_name}",
        item={
            "id": item.id,
            "sku": item.sku,
            "product_name": item.product_name,
            "bin_location": item.bin_location,
            "quantity_required": item.quantity_required,
            "quantity_picked": item.quantity_picked,
            "is_picked": item.is_picked,
        },
        remaining_quantity=item.quantity_required - item.quantity_picked,
    )


@router.post(
    "/{picklist_id}/confirm",
    response_model=PickScanResponse,
    dependencies=[Depends(require_permissions("orders:update"))]
)
async def confirm_pick_item(
    picklist_id: uuid.UUID,
    data: PickConfirmRequest,
    db: DB,
    current_user: CurrentUser,
):
    """Confirm picked quantity for an item."""
    item_query = select(PicklistItem).where(
        and_(
            PicklistItem.id == data.picklist_item_id,
            PicklistItem.picklist_id == picklist_id,
        )
    )
    item_result = await db.execute(item_query)
    item = item_result.scalar_one_or_none()

    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Picklist item not found"
        )

    # Update item
    item.quantity_picked = data.quantity_picked
    item.picked_by = current_user.id
    item.picked_at = datetime.now(timezone.utc)
    item.notes = data.notes

    if data.serial_numbers:
        item.picked_serials = ",".join(data.serial_numbers)

    if item.quantity_picked >= item.quantity_required:
        item.is_picked = True

    # Update picklist totals
    picklist_query = select(Picklist).where(Picklist.id == picklist_id)
    picklist_result = await db.execute(picklist_query)
    picklist = picklist_result.scalar_one()

    # Recalculate picked quantity
    items_query = select(func.sum(PicklistItem.quantity_picked)).where(
        PicklistItem.picklist_id == picklist_id
    )
    items_result = await db.execute(items_query)
    total_picked = items_result.scalar() or 0
    picklist.picked_quantity = total_picked

    await db.commit()
    await db.refresh(item)

    return PickScanResponse(
        success=True,
        message=f"Confirmed {data.quantity_picked} of {item.product_name}",
        item={
            "id": item.id,
            "sku": item.sku,
            "product_name": item.product_name,
            "bin_location": item.bin_location,
            "quantity_required": item.quantity_required,
            "quantity_picked": item.quantity_picked,
            "is_picked": item.is_picked,
        },
        remaining_quantity=item.quantity_required - item.quantity_picked,
    )


@router.post(
    "/{picklist_id}/short",
    response_model=PickScanResponse,
    dependencies=[Depends(require_permissions("orders:update"))]
)
async def mark_item_short(
    picklist_id: uuid.UUID,
    data: PickShortRequest,
    db: DB,
    current_user: CurrentUser,
):
    """Mark item as short (not found/insufficient stock)."""
    item_query = select(PicklistItem).where(
        and_(
            PicklistItem.id == data.picklist_item_id,
            PicklistItem.picklist_id == picklist_id,
        )
    )
    item_result = await db.execute(item_query)
    item = item_result.scalar_one_or_none()

    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Picklist item not found"
        )

    item.quantity_short = data.quantity_short
    item.is_short = True
    item.short_reason = data.reason
    item.picked_by = current_user.id
    item.picked_at = datetime.now(timezone.utc)

    # Mark as complete if all quantity either picked or short
    if item.quantity_picked + item.quantity_short >= item.quantity_required:
        item.is_picked = True

    await db.commit()
    await db.refresh(item)

    return PickScanResponse(
        success=True,
        message=f"Marked {data.quantity_short} as short for {item.product_name}",
        item={
            "id": item.id,
            "sku": item.sku,
            "product_name": item.product_name,
            "bin_location": item.bin_location,
            "quantity_required": item.quantity_required,
            "quantity_picked": item.quantity_picked,
            "is_picked": item.is_picked,
        },
        remaining_quantity=item.quantity_required - item.quantity_picked - item.quantity_short,
    )


@router.post(
    "/{picklist_id}/complete",
    response_model=PickCompleteResponse,
    dependencies=[Depends(require_permissions("orders:update"))]
)
async def complete_picklist(
    picklist_id: uuid.UUID,
    db: DB,
    current_user: CurrentUser,
    notes: Optional[str] = None,
):
    """Complete picking for picklist."""
    query = (
        select(Picklist)
        .where(Picklist.id == picklist_id)
        .options(selectinload(Picklist.items))
    )
    result = await db.execute(query)
    picklist = result.scalar_one_or_none()

    if not picklist:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Picklist not found"
        )

    if picklist.status != PicklistStatus.IN_PROGRESS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Picklist is not in progress"
        )

    # Calculate totals
    total_picked = sum(i.quantity_picked for i in picklist.items)
    total_short = sum(i.quantity_short for i in picklist.items)

    # Update picklist
    picklist.status = PicklistStatus.COMPLETED.value
    picklist.completed_at = datetime.now(timezone.utc)
    picklist.picked_quantity = total_picked
    if notes:
        picklist.notes = notes

    # Update order statuses
    order_ids = set(i.order_id for i in picklist.items)
    for order_id in order_ids:
        order_query = select(Order).where(Order.id == order_id)
        order_result = await db.execute(order_query)
        order = order_result.scalar_one_or_none()
        if order:
            order.status = OrderStatus.PICKED.value

    await db.commit()
    await db.refresh(picklist)

    return PickCompleteResponse(
        success=True,
        picklist_id=picklist.id,
        picklist_number=picklist.picklist_number,
        status=picklist.status,
        total_picked=total_picked,
        total_short=total_short,
        message=f"Picklist completed. Picked: {total_picked}, Short: {total_short}",
    )


@router.post(
    "/{picklist_id}/cancel",
    response_model=PicklistResponse,
    dependencies=[Depends(require_permissions("orders:delete"))]
)
async def cancel_picklist(
    picklist_id: uuid.UUID,
    db: DB,
    current_user: CurrentUser,
    reason: str = Query(...),
):
    """Cancel a picklist."""
    query = select(Picklist).where(Picklist.id == picklist_id)
    result = await db.execute(query)
    picklist = result.scalar_one_or_none()

    if not picklist:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Picklist not found"
        )

    if picklist.status in [PicklistStatus.COMPLETED, PicklistStatus.CANCELLED]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Picklist cannot be cancelled"
        )

    picklist.status = PicklistStatus.CANCELLED.value
    picklist.cancelled_at = datetime.now(timezone.utc)
    picklist.cancellation_reason = reason

    await db.commit()
    await db.refresh(picklist)

    return PicklistResponse.model_validate(picklist)
