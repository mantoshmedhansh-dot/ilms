"""Manifest API endpoints for transporter handover operations."""
from typing import Optional
import uuid
from math import ceil
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, status, Query, Depends
from sqlalchemy import select, func, and_, or_
from sqlalchemy.orm import selectinload

from app.api.deps import DB, CurrentUser, require_permissions
from app.models.manifest import Manifest, ManifestItem, ManifestStatus, BusinessType
from app.models.shipment import Shipment, ShipmentStatus, ShipmentTracking
from app.models.warehouse import Warehouse
from app.models.transporter import Transporter
from app.models.order import Order, OrderStatus
from app.schemas.manifest import (
    ManifestCreate,
    ManifestUpdate,
    ManifestResponse,
    ManifestDetailResponse,
    ManifestListResponse,
    ManifestItemResponse,
    ManifestBrief,
    ManifestAddShipmentRequest,
    ManifestRemoveShipmentRequest,
    ManifestScanRequest,
    ManifestScanResponse,
    ManifestConfirmRequest,
    ManifestConfirmResponse,
    ManifestHandoverRequest,
    ManifestHandoverResponse,
    ManifestCancelRequest,
    ManifestPrintResponse,
)
from app.schemas.transporter import TransporterBrief


router = APIRouter()


def generate_manifest_number() -> str:
    """Generate unique manifest number."""
    from datetime import datetime, timezone
    import random
    date_str = datetime.now().strftime("%Y%m%d")
    random_suffix = random.randint(1000, 9999)
    return f"MF-{date_str}-{random_suffix}"


# ==================== MANIFEST CRUD ====================

@router.get(
    "",
    response_model=ManifestListResponse,
    dependencies=[Depends(require_permissions("logistics:view"))]
)
async def list_manifests(
    db: DB,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    warehouse_id: Optional[uuid.UUID] = Query(None),
    transporter_id: Optional[uuid.UUID] = Query(None),
    status: Optional[ManifestStatus] = Query(None),
    business_type: Optional[BusinessType] = Query(None),
    search: Optional[str] = Query(None),
    from_date: Optional[datetime] = Query(None),
    to_date: Optional[datetime] = Query(None),
):
    """Get paginated list of manifests."""
    query = select(Manifest)
    count_query = select(func.count(Manifest.id))

    if warehouse_id:
        query = query.where(Manifest.warehouse_id == warehouse_id)
        count_query = count_query.where(Manifest.warehouse_id == warehouse_id)

    if transporter_id:
        query = query.where(Manifest.transporter_id == transporter_id)
        count_query = count_query.where(Manifest.transporter_id == transporter_id)

    if status:
        query = query.where(Manifest.status == status)
        count_query = count_query.where(Manifest.status == status)

    if business_type:
        query = query.where(Manifest.business_type == business_type)
        count_query = count_query.where(Manifest.business_type == business_type)

    if search:
        query = query.where(Manifest.manifest_number.ilike(f"%{search}%"))
        count_query = count_query.where(Manifest.manifest_number.ilike(f"%{search}%"))

    if from_date:
        query = query.where(Manifest.manifest_date >= from_date)
        count_query = count_query.where(Manifest.manifest_date >= from_date)

    if to_date:
        query = query.where(Manifest.manifest_date <= to_date)
        count_query = count_query.where(Manifest.manifest_date <= to_date)

    # Get total count
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # Get paginated results
    offset = (page - 1) * size
    query = query.options(selectinload(Manifest.transporter))
    query = query.order_by(Manifest.manifest_date.desc())
    query = query.offset(offset).limit(size)

    result = await db.execute(query)
    manifests = result.scalars().all()

    return ManifestListResponse(
        items=[ManifestResponse.model_validate(m) for m in manifests],
        total=total,
        page=page,
        size=size,
        pages=ceil(total / size) if total > 0 else 1,
    )


@router.get(
    "/{manifest_id}",
    response_model=ManifestDetailResponse,
    dependencies=[Depends(require_permissions("logistics:view"))]
)
async def get_manifest(
    manifest_id: uuid.UUID,
    db: DB,
):
    """Get manifest with items."""
    query = (
        select(Manifest)
        .where(Manifest.id == manifest_id)
        .options(
            selectinload(Manifest.transporter),
            selectinload(Manifest.items),
        )
    )
    result = await db.execute(query)
    manifest = result.scalar_one_or_none()

    if not manifest:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Manifest not found"
        )

    response_data = ManifestResponse.model_validate(manifest).model_dump()
    response_data["items"] = [ManifestItemResponse.model_validate(i) for i in manifest.items]

    return ManifestDetailResponse(**response_data)


@router.post(
    "",
    response_model=ManifestResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permissions("logistics:create"))]
)
async def create_manifest(
    data: ManifestCreate,
    db: DB,
    current_user: CurrentUser,
):
    """Create a new manifest."""
    # Verify warehouse exists
    wh_query = select(Warehouse).where(Warehouse.id == data.warehouse_id)
    wh_result = await db.execute(wh_query)
    if not wh_result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Warehouse not found"
        )

    # Verify transporter exists
    transporter_query = select(Transporter).where(Transporter.id == data.transporter_id)
    transporter_result = await db.execute(transporter_query)
    if not transporter_result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Transporter not found"
        )

    manifest = Manifest(
        manifest_number=generate_manifest_number(),
        warehouse_id=data.warehouse_id,
        transporter_id=data.transporter_id,
        status=ManifestStatus.DRAFT,
        business_type=data.business_type,
        manifest_date=data.manifest_date or datetime.now(timezone.utc),
        vehicle_number=data.vehicle_number,
        driver_name=data.driver_name,
        driver_phone=data.driver_phone,
        remarks=data.remarks,
        created_by=current_user.id,
    )

    db.add(manifest)
    await db.commit()

    # Reload with transporter relationship
    query = (
        select(Manifest)
        .where(Manifest.id == manifest.id)
        .options(selectinload(Manifest.transporter))
    )
    result = await db.execute(query)
    manifest = result.scalar_one()

    return ManifestResponse.model_validate(manifest)


@router.put(
    "/{manifest_id}",
    response_model=ManifestResponse,
    dependencies=[Depends(require_permissions("logistics:update"))]
)
async def update_manifest(
    manifest_id: uuid.UUID,
    data: ManifestUpdate,
    db: DB,
    current_user: CurrentUser,
):
    """Update manifest details."""
    query = select(Manifest).where(Manifest.id == manifest_id)
    result = await db.execute(query)
    manifest = result.scalar_one_or_none()

    if not manifest:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Manifest not found"
        )

    if manifest.status not in [ManifestStatus.DRAFT, ManifestStatus.PENDING]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Manifest cannot be updated in current status"
        )

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(manifest, field, value)

    await db.commit()
    await db.refresh(manifest)

    return ManifestResponse.model_validate(manifest)


# ==================== MANIFEST OPERATIONS ====================

@router.post(
    "/{manifest_id}/add-shipments",
    response_model=ManifestDetailResponse,
    dependencies=[Depends(require_permissions("logistics:update"))]
)
async def add_shipments_to_manifest(
    manifest_id: uuid.UUID,
    data: ManifestAddShipmentRequest,
    db: DB,
    current_user: CurrentUser,
):
    """Add shipments to manifest."""
    query = select(Manifest).where(Manifest.id == manifest_id)
    result = await db.execute(query)
    manifest = result.scalar_one_or_none()

    if not manifest:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Manifest not found"
        )

    if manifest.status not in [ManifestStatus.DRAFT, ManifestStatus.PENDING]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot add shipments to manifest in current status"
        )

    # Get shipments
    shipments_query = select(Shipment).where(
        and_(
            Shipment.id.in_(data.shipment_ids),
            Shipment.transporter_id == manifest.transporter_id,
            Shipment.status.in_([
                ShipmentStatus.PACKED,
                ShipmentStatus.READY_FOR_PICKUP,
            ]),
            Shipment.manifest_id.is_(None),
        )
    ).options(selectinload(Shipment.order))

    shipments_result = await db.execute(shipments_query)
    shipments = shipments_result.scalars().all()

    if not shipments:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No valid shipments found to add"
        )

    total_weight = manifest.total_weight_kg
    total_boxes = manifest.total_boxes

    for shipment in shipments:
        # Create manifest item
        item = ManifestItem(
            manifest_id=manifest.id,
            shipment_id=shipment.id,
            awb_number=shipment.awb_number or shipment.shipment_number,
            tracking_number=shipment.tracking_number,
            order_number=shipment.order.order_number if shipment.order else shipment.shipment_number,
            weight_kg=shipment.weight_kg,
            no_of_boxes=shipment.no_of_boxes,
            destination_pincode=shipment.ship_to_pincode,
            destination_city=shipment.ship_to_city,
        )
        db.add(item)

        # Update shipment
        shipment.manifest_id = manifest.id
        shipment.status = ShipmentStatus.MANIFESTED.value

        total_weight += shipment.weight_kg
        total_boxes += shipment.no_of_boxes

    # Update manifest totals
    manifest.total_shipments += len(shipments)
    manifest.total_weight_kg = total_weight
    manifest.total_boxes = total_boxes
    manifest.status = ManifestStatus.PENDING.value

    await db.commit()

    # Refresh and return
    query = (
        select(Manifest)
        .where(Manifest.id == manifest_id)
        .options(
            selectinload(Manifest.transporter),
            selectinload(Manifest.items),
        )
    )
    result = await db.execute(query)
    manifest = result.scalar_one()

    response_data = ManifestResponse.model_validate(manifest).model_dump()
    response_data["items"] = [ManifestItemResponse.model_validate(i) for i in manifest.items]

    return ManifestDetailResponse(**response_data)


@router.post(
    "/{manifest_id}/remove-shipments",
    response_model=ManifestDetailResponse,
    dependencies=[Depends(require_permissions("logistics:update"))]
)
async def remove_shipments_from_manifest(
    manifest_id: uuid.UUID,
    data: ManifestRemoveShipmentRequest,
    db: DB,
    current_user: CurrentUser,
):
    """Remove shipments from manifest."""
    query = select(Manifest).where(Manifest.id == manifest_id)
    result = await db.execute(query)
    manifest = result.scalar_one_or_none()

    if not manifest:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Manifest not found"
        )

    if manifest.status not in [ManifestStatus.DRAFT, ManifestStatus.PENDING]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot remove shipments from manifest in current status"
        )

    # Get items to remove
    items_query = select(ManifestItem).where(
        and_(
            ManifestItem.manifest_id == manifest_id,
            ManifestItem.shipment_id.in_(data.shipment_ids),
            ManifestItem.is_handed_over == False,
        )
    )
    items_result = await db.execute(items_query)
    items = items_result.scalars().all()

    for item in items:
        # Update shipment
        shipment_query = select(Shipment).where(Shipment.id == item.shipment_id)
        shipment_result = await db.execute(shipment_query)
        shipment = shipment_result.scalar_one_or_none()
        if shipment:
            shipment.manifest_id = None
            shipment.status = ShipmentStatus.READY_FOR_PICKUP.value

        # Update manifest totals
        manifest.total_shipments -= 1
        manifest.total_weight_kg -= item.weight_kg
        manifest.total_boxes -= item.no_of_boxes

        await db.delete(item)

    if manifest.total_shipments == 0:
        manifest.status = ManifestStatus.DRAFT.value

    await db.commit()

    # Refresh and return
    query = (
        select(Manifest)
        .where(Manifest.id == manifest_id)
        .options(
            selectinload(Manifest.transporter),
            selectinload(Manifest.items),
        )
    )
    result = await db.execute(query)
    manifest = result.scalar_one()

    response_data = ManifestResponse.model_validate(manifest).model_dump()
    response_data["items"] = [ManifestItemResponse.model_validate(i) for i in manifest.items]

    return ManifestDetailResponse(**response_data)


@router.post(
    "/{manifest_id}/scan",
    response_model=ManifestScanResponse,
    dependencies=[Depends(require_permissions("logistics:update"))]
)
async def scan_shipment_for_handover(
    manifest_id: uuid.UUID,
    data: ManifestScanRequest,
    db: DB,
    current_user: CurrentUser,
):
    """Scan shipment for handover verification."""
    query = select(Manifest).where(Manifest.id == manifest_id)
    result = await db.execute(query)
    manifest = result.scalar_one_or_none()

    if not manifest:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Manifest not found"
        )

    if manifest.status not in [ManifestStatus.PENDING, ManifestStatus.CONFIRMED]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Manifest is not ready for scanning"
        )

    # Find item
    item_query = select(ManifestItem).where(ManifestItem.manifest_id == manifest_id)

    if data.awb_number:
        item_query = item_query.where(ManifestItem.awb_number == data.awb_number)
    elif data.shipment_id:
        item_query = item_query.where(ManifestItem.shipment_id == data.shipment_id)
    elif data.barcode:
        item_query = item_query.where(
            or_(
                ManifestItem.awb_number == data.barcode,
                ManifestItem.tracking_number == data.barcode,
            )
        )
    else:
        return ManifestScanResponse(
            success=False,
            message="Provide awb_number, shipment_id, or barcode",
            item=None,
            total_scanned=manifest.scanned_shipments,
            total_pending=manifest.total_shipments - manifest.scanned_shipments,
        )

    item_result = await db.execute(item_query)
    item = item_result.scalar_one_or_none()

    if not item:
        return ManifestScanResponse(
            success=False,
            message="Shipment not found in manifest",
            item=None,
            total_scanned=manifest.scanned_shipments,
            total_pending=manifest.total_shipments - manifest.scanned_shipments,
        )

    if item.is_scanned:
        return ManifestScanResponse(
            success=True,
            message="Already scanned",
            item={
                "id": item.id,
                "awb_number": item.awb_number,
                "order_number": item.order_number,
                "is_scanned": item.is_scanned,
                "is_handed_over": item.is_handed_over,
            },
            total_scanned=manifest.scanned_shipments,
            total_pending=manifest.total_shipments - manifest.scanned_shipments,
        )

    # Mark as scanned
    item.is_scanned = True
    item.scanned_at = datetime.now(timezone.utc)
    item.scanned_by = current_user.id

    manifest.scanned_shipments += 1

    await db.commit()
    await db.refresh(item)
    await db.refresh(manifest)

    return ManifestScanResponse(
        success=True,
        message=f"Scanned: {item.awb_number}",
        item={
            "id": item.id,
            "awb_number": item.awb_number,
            "order_number": item.order_number,
            "is_scanned": item.is_scanned,
            "is_handed_over": item.is_handed_over,
        },
        total_scanned=manifest.scanned_shipments,
        total_pending=manifest.total_shipments - manifest.scanned_shipments,
    )


@router.post(
    "/{manifest_id}/confirm",
    response_model=ManifestConfirmResponse,
    dependencies=[Depends(require_permissions("logistics:update"))]
)
async def confirm_manifest(
    manifest_id: uuid.UUID,
    data: ManifestConfirmRequest,
    db: DB,
    current_user: CurrentUser,
):
    """Confirm manifest for handover."""
    query = select(Manifest).where(Manifest.id == manifest_id)
    result = await db.execute(query)
    manifest = result.scalar_one_or_none()

    if not manifest:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Manifest not found"
        )

    if manifest.status != ManifestStatus.PENDING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Manifest is not in pending status"
        )

    if manifest.total_shipments == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Manifest has no shipments"
        )

    # Update manifest
    manifest.status = ManifestStatus.CONFIRMED.value
    manifest.confirmed_at = datetime.now(timezone.utc)
    manifest.confirmed_by = current_user.id

    if data.vehicle_number:
        manifest.vehicle_number = data.vehicle_number
    if data.driver_name:
        manifest.driver_name = data.driver_name
    if data.driver_phone:
        manifest.driver_phone = data.driver_phone
    if data.remarks:
        manifest.remarks = data.remarks

    await db.commit()
    await db.refresh(manifest)

    return ManifestConfirmResponse(
        success=True,
        manifest_id=manifest.id,
        manifest_number=manifest.manifest_number,
        status=manifest.status,
        total_shipments=manifest.total_shipments,
        message="Manifest confirmed successfully",
    )


@router.post(
    "/{manifest_id}/handover",
    response_model=ManifestHandoverResponse,
    dependencies=[Depends(require_permissions("logistics:update"))]
)
async def complete_handover(
    manifest_id: uuid.UUID,
    data: ManifestHandoverRequest,
    db: DB,
    current_user: CurrentUser,
):
    """Complete handover to transporter - marks all shipments as shipped."""
    query = (
        select(Manifest)
        .where(Manifest.id == manifest_id)
        .options(
            selectinload(Manifest.items),
            selectinload(Manifest.transporter),
        )
    )
    result = await db.execute(query)
    manifest = result.scalar_one_or_none()

    if not manifest:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Manifest not found"
        )

    if manifest.status != ManifestStatus.CONFIRMED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Manifest must be confirmed before handover"
        )

    now = datetime.now(timezone.utc)
    shipped_count = 0

    # Update all items and shipments
    for item in manifest.items:
        item.is_handed_over = True
        item.handed_over_at = now

        # Update shipment status to SHIPPED
        shipment_query = select(Shipment).where(Shipment.id == item.shipment_id)
        shipment_result = await db.execute(shipment_query)
        shipment = shipment_result.scalar_one_or_none()

        if shipment:
            shipment.status = ShipmentStatus.PICKED_UP.value
            shipment.shipped_at = now

            # Add tracking
            tracking = ShipmentTracking(
                shipment_id=shipment.id,
                status=ShipmentStatus.PICKED_UP,
                remarks=f"Handed over to {manifest.transporter.name if manifest.transporter else 'transporter'}",
                event_time=now,
                source="MANIFEST",
                updated_by=current_user.id,
            )
            db.add(tracking)

            # Update order
            order_query = select(Order).where(Order.id == shipment.order_id)
            order_result = await db.execute(order_query)
            order = order_result.scalar_one_or_none()
            if order:
                order.status = OrderStatus.SHIPPED.value

                # GAP H: Deduct inventory on dispatch
                try:
                    from app.models.order import OrderItem
                    from app.services.inventory_service import InventoryService
                    inv_svc = InventoryService(db)
                    oi_result = await db.execute(
                        select(OrderItem).where(OrderItem.order_id == order.id)
                    )
                    for oi in oi_result.scalars().all():
                        await inv_svc._update_inventory_summary(
                            warehouse_id=shipment.warehouse_id,
                            product_id=oi.product_id,
                            variant_id=oi.variant_id,
                            quantity_change=-oi.quantity,
                            allocated_change=-oi.quantity,
                            in_transit_change=oi.quantity,
                        )
                except Exception as e:
                    import logging
                    logging.getLogger(__name__).warning(
                        f"Inventory deduction failed for shipment {shipment.shipment_number}: {e}"
                    )

            shipped_count += 1

    # Update manifest
    manifest.status = ManifestStatus.HANDED_OVER.value
    manifest.handover_at = now
    manifest.handover_by = current_user.id
    if data.handover_remarks:
        manifest.remarks = data.handover_remarks

    await db.commit()
    await db.refresh(manifest)

    return ManifestHandoverResponse(
        success=True,
        manifest_id=manifest.id,
        manifest_number=manifest.manifest_number,
        status=manifest.status,
        shipped_orders=shipped_count,
        message=f"Handover complete. {shipped_count} shipments marked as shipped.",
    )


@router.post(
    "/{manifest_id}/cancel",
    response_model=ManifestResponse,
    dependencies=[Depends(require_permissions("logistics:delete"))]
)
async def cancel_manifest(
    manifest_id: uuid.UUID,
    data: ManifestCancelRequest,
    db: DB,
    current_user: CurrentUser,
):
    """Cancel a manifest."""
    query = (
        select(Manifest)
        .where(Manifest.id == manifest_id)
        .options(selectinload(Manifest.items))
    )
    result = await db.execute(query)
    manifest = result.scalar_one_or_none()

    if not manifest:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Manifest not found"
        )

    if manifest.status == ManifestStatus.HANDED_OVER:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot cancel handed-over manifest"
        )

    # Remove shipments from manifest
    for item in manifest.items:
        shipment_query = select(Shipment).where(Shipment.id == item.shipment_id)
        shipment_result = await db.execute(shipment_query)
        shipment = shipment_result.scalar_one_or_none()
        if shipment:
            shipment.manifest_id = None
            shipment.status = ShipmentStatus.READY_FOR_PICKUP.value

        await db.delete(item)

    manifest.status = ManifestStatus.CANCELLED.value
    manifest.cancelled_at = datetime.now(timezone.utc)
    manifest.cancellation_reason = data.reason
    manifest.total_shipments = 0
    manifest.scanned_shipments = 0
    manifest.total_weight_kg = 0
    manifest.total_boxes = 0

    await db.commit()
    await db.refresh(manifest)

    return ManifestResponse.model_validate(manifest)


@router.get(
    "/{manifest_id}/print",
    response_model=ManifestPrintResponse,
    dependencies=[Depends(require_permissions("logistics:view"))]
)
async def get_manifest_print_data(
    manifest_id: uuid.UUID,
    db: DB,
):
    """Get manifest data for printing."""
    query = (
        select(Manifest)
        .where(Manifest.id == manifest_id)
        .options(
            selectinload(Manifest.transporter),
            selectinload(Manifest.items),
        )
    )
    result = await db.execute(query)
    manifest = result.scalar_one_or_none()

    if not manifest:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Manifest not found"
        )

    response_data = ManifestResponse.model_validate(manifest).model_dump()
    response_data["items"] = [ManifestItemResponse.model_validate(i) for i in manifest.items]
    manifest_detail = ManifestDetailResponse(**response_data)

    return ManifestPrintResponse(
        manifest=manifest_detail,
        company_name="ILMS.AI",
        company_address="Plot 36-A KH No 181, Najafgarh, Delhi - 110043",
        company_phone="+91-9311939076",
        company_gstin="07ABDCA6170C1Z5",
        print_date=datetime.now(timezone.utc),
        print_url=None,
    )
