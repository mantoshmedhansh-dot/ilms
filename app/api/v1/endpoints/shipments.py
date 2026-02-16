"""Shipment API endpoints for shipping operations."""
from typing import Optional
import uuid
import logging
from math import ceil
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, status, Query, Depends
from sqlalchemy import select, func, and_, or_
from sqlalchemy.orm import selectinload

from app.api.deps import DB, CurrentUser, require_permissions
from app.models.shipment import Shipment, ShipmentTracking, ShipmentStatus, PaymentMode, PackagingType
from app.models.order import Order, OrderStatus
from app.models.warehouse import Warehouse
from app.models.transporter import Transporter
from app.schemas.shipment import (
    ShipmentCreate,
    ShipmentUpdate,
    ShipmentResponse,
    ShipmentDetailResponse,
    ShipmentListResponse,
    ShipmentBrief,
    ShipmentTrackingResponse,
    ShipmentPackRequest,
    ShipmentPackResponse,
    ShipmentTrackingUpdate,
    ShipmentDeliveryMarkRequest,
    ShipmentDeliveryMarkResponse,
    ShipmentRTOInitiateRequest,
    ShipmentRTOResponse,
    ShipmentCancelRequest,
    BulkShipmentCreate,
    BulkShipmentResponse,
    TrackShipmentRequest,
    TrackShipmentResponse,
    ShipmentLabelResponse,
    ShipmentInvoiceResponse,
)
from app.schemas.transporter import TransporterBrief
from app.core.module_decorators import require_module


router = APIRouter()


def generate_shipment_number() -> str:
    """Generate unique shipment number."""
    from datetime import datetime, timezone
    import random
    date_str = datetime.now().strftime("%Y%m%d")
    random_suffix = random.randint(10000, 99999)
    return f"SHP-{date_str}-{random_suffix}"


# ==================== SHIPMENT CRUD ====================

@router.get(
    "",
    response_model=ShipmentListResponse,
    dependencies=[Depends(require_permissions("logistics:view"))]
)
async def list_shipments(
    db: DB,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    warehouse_id: Optional[uuid.UUID] = Query(None),
    transporter_id: Optional[uuid.UUID] = Query(None),
    status: Optional[ShipmentStatus] = Query(None),
    payment_mode: Optional[PaymentMode] = Query(None),
    search: Optional[str] = Query(None),
    from_date: Optional[datetime] = Query(None),
    to_date: Optional[datetime] = Query(None),
):
    """Get paginated list of shipments."""
    query = select(Shipment)
    count_query = select(func.count(Shipment.id))

    if warehouse_id:
        query = query.where(Shipment.warehouse_id == warehouse_id)
        count_query = count_query.where(Shipment.warehouse_id == warehouse_id)

    if transporter_id:
        query = query.where(Shipment.transporter_id == transporter_id)
        count_query = count_query.where(Shipment.transporter_id == transporter_id)

    if status:
        query = query.where(Shipment.status == status)
        count_query = count_query.where(Shipment.status == status)

    if payment_mode:
        query = query.where(Shipment.payment_mode == payment_mode)
        count_query = count_query.where(Shipment.payment_mode == payment_mode)

    if search:
        search_filter = or_(
            Shipment.shipment_number.ilike(f"%{search}%"),
            Shipment.awb_number.ilike(f"%{search}%"),
            Shipment.ship_to_phone.ilike(f"%{search}%"),
        )
        query = query.where(search_filter)
        count_query = count_query.where(search_filter)

    if from_date:
        query = query.where(Shipment.created_at >= from_date)
        count_query = count_query.where(Shipment.created_at >= from_date)

    if to_date:
        query = query.where(Shipment.created_at <= to_date)
        count_query = count_query.where(Shipment.created_at <= to_date)

    # Get total count
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # Get paginated results
    offset = (page - 1) * size
    query = query.options(selectinload(Shipment.transporter))
    query = query.order_by(Shipment.created_at.desc())
    query = query.offset(offset).limit(size)

    result = await db.execute(query)
    shipments = result.scalars().all()

    return ShipmentListResponse(
        items=[ShipmentResponse.model_validate(s) for s in shipments],
        total=total,
        page=page,
        size=size,
        pages=ceil(total / size) if total > 0 else 1,
    )


@router.get(
    "/{shipment_id}",
    response_model=ShipmentDetailResponse,
    dependencies=[Depends(require_permissions("logistics:view"))]
)
async def get_shipment(
    shipment_id: uuid.UUID,
    db: DB,
):
    """Get shipment with tracking history."""
    query = (
        select(Shipment)
        .where(Shipment.id == shipment_id)
        .options(
            selectinload(Shipment.transporter),
            selectinload(Shipment.tracking_history),
        )
    )
    result = await db.execute(query)
    shipment = result.scalar_one_or_none()

    if not shipment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Shipment not found"
        )

    response_data = ShipmentResponse.model_validate(shipment).model_dump()
    response_data["tracking_history"] = [
        ShipmentTrackingResponse.model_validate(t) for t in shipment.tracking_history
    ]

    return ShipmentDetailResponse(**response_data)


@router.post(
    "",
    response_model=ShipmentResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permissions("logistics:create"))]
)
async def create_shipment(
    data: ShipmentCreate,
    db: DB,
    current_user: CurrentUser,
):
    """Create a new shipment for an order."""
    # Verify order exists and is ready
    order_query = select(Order).where(Order.id == data.order_id)
    order_result = await db.execute(order_query)
    order = order_result.scalar_one_or_none()

    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found"
        )

    # Check if shipment already exists for this order
    existing_query = select(Shipment).where(
        and_(
            Shipment.order_id == data.order_id,
            Shipment.status.notin_([ShipmentStatus.CANCELLED, ShipmentStatus.RTO_DELIVERED]),
        )
    )
    existing_result = await db.execute(existing_query)
    if existing_result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Active shipment already exists for this order"
        )

    # Calculate volumetric weight
    volumetric_weight = None
    if data.length_cm and data.breadth_cm and data.height_cm:
        volumetric_weight = (data.length_cm * data.breadth_cm * data.height_cm) / 5000

    # Calculate chargeable weight
    chargeable_weight = max(data.weight_kg, volumetric_weight or 0)

    shipment = Shipment(
        shipment_number=generate_shipment_number(),
        order_id=data.order_id,
        warehouse_id=data.warehouse_id,
        transporter_id=data.transporter_id,
        status=ShipmentStatus.CREATED,
        payment_mode=data.payment_mode,
        cod_amount=data.cod_amount if data.payment_mode == PaymentMode.COD else None,
        packaging_type=data.packaging_type,
        no_of_boxes=data.no_of_boxes,
        weight_kg=data.weight_kg,
        volumetric_weight_kg=volumetric_weight,
        chargeable_weight_kg=chargeable_weight,
        length_cm=data.length_cm,
        breadth_cm=data.breadth_cm,
        height_cm=data.height_cm,
        ship_to_name=data.ship_to_name,
        ship_to_phone=data.ship_to_phone,
        ship_to_email=data.ship_to_email,
        ship_to_address=data.ship_to_address,
        ship_to_pincode=data.ship_to_pincode,
        ship_to_city=data.ship_to_city,
        ship_to_state=data.ship_to_state,
        expected_delivery_date=data.expected_delivery_date,
        created_by=current_user.id,
    )

    db.add(shipment)
    await db.flush()  # Flush to get shipment.id

    # Add tracking entry
    tracking = ShipmentTracking(
        shipment_id=shipment.id,
        status=ShipmentStatus.CREATED,
        remarks="Shipment created",
        event_time=datetime.now(timezone.utc),
        source="SYSTEM",
        updated_by=current_user.id,
    )
    db.add(tracking)

    await db.commit()

    # Reload with transporter relationship
    query = (
        select(Shipment)
        .where(Shipment.id == shipment.id)
        .options(selectinload(Shipment.transporter))
    )
    result = await db.execute(query)
    shipment = result.scalar_one()

    return ShipmentResponse.model_validate(shipment)


@router.put(
    "/{shipment_id}",
    response_model=ShipmentResponse,
    dependencies=[Depends(require_permissions("logistics:update"))]
)
async def update_shipment(
    shipment_id: uuid.UUID,
    data: ShipmentUpdate,
    db: DB,
    current_user: CurrentUser,
):
    """Update shipment details."""
    query = select(Shipment).where(Shipment.id == shipment_id)
    result = await db.execute(query)
    shipment = result.scalar_one_or_none()

    if not shipment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Shipment not found"
        )

    if shipment.status not in [ShipmentStatus.CREATED, ShipmentStatus.PACKED]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Shipment cannot be updated in current status"
        )

    update_data = data.model_dump(exclude_unset=True)

    # Recalculate weights if dimensions changed
    if any(k in update_data for k in ["weight_kg", "length_cm", "breadth_cm", "height_cm"]):
        length = update_data.get("length_cm", shipment.length_cm)
        breadth = update_data.get("breadth_cm", shipment.breadth_cm)
        height = update_data.get("height_cm", shipment.height_cm)
        weight = update_data.get("weight_kg", shipment.weight_kg)

        if length and breadth and height:
            volumetric = (length * breadth * height) / 5000
            update_data["volumetric_weight_kg"] = volumetric
            update_data["chargeable_weight_kg"] = max(weight, volumetric)

    for field, value in update_data.items():
        setattr(shipment, field, value)

    await db.commit()
    await db.refresh(shipment)

    return ShipmentResponse.model_validate(shipment)


# ==================== SHIPMENT OPERATIONS ====================

@router.post(
    "/{shipment_id}/pack",
    response_model=ShipmentPackResponse,
    dependencies=[Depends(require_permissions("logistics:update"))]
)
async def pack_shipment(
    shipment_id: uuid.UUID,
    data: ShipmentPackRequest,
    db: DB,
    current_user: CurrentUser,
):
    """Mark shipment as packed."""
    query = select(Shipment).where(Shipment.id == shipment_id)
    result = await db.execute(query)
    shipment = result.scalar_one_or_none()

    if not shipment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Shipment not found"
        )

    if shipment.status != ShipmentStatus.CREATED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Shipment is not in created status"
        )

    # Update shipment
    shipment.status = ShipmentStatus.PACKED.value
    shipment.packed_at = datetime.now(timezone.utc)
    shipment.packaging_type = data.packaging_type
    shipment.no_of_boxes = data.no_of_boxes
    shipment.weight_kg = data.weight_kg
    if data.length_cm:
        shipment.length_cm = data.length_cm
    if data.breadth_cm:
        shipment.breadth_cm = data.breadth_cm
    if data.height_cm:
        shipment.height_cm = data.height_cm

    # Recalculate volumetric
    if shipment.length_cm and shipment.breadth_cm and shipment.height_cm:
        shipment.volumetric_weight_kg = (
            shipment.length_cm * shipment.breadth_cm * shipment.height_cm
        ) / 5000
        shipment.chargeable_weight_kg = max(
            shipment.weight_kg, shipment.volumetric_weight_kg
        )

    # Add tracking
    tracking = ShipmentTracking(
        shipment_id=shipment.id,
        status=ShipmentStatus.PACKED,
        remarks=data.notes or "Shipment packed",
        event_time=datetime.now(timezone.utc),
        source="SYSTEM",
        updated_by=current_user.id,
    )
    db.add(tracking)

    await db.commit()
    await db.refresh(shipment)

    return ShipmentPackResponse(
        success=True,
        shipment_id=shipment.id,
        shipment_number=shipment.shipment_number,
        status=shipment.status,
        message="Shipment packed successfully",
    )


@router.post(
    "/{shipment_id}/generate-awb",
    response_model=ShipmentResponse,
    dependencies=[Depends(require_permissions("logistics:update"))]
)
async def generate_awb(
    shipment_id: uuid.UUID,
    db: DB,
    current_user: CurrentUser,
):
    """Generate AWB number for shipment."""
    query = select(Shipment).where(Shipment.id == shipment_id)
    result = await db.execute(query)
    shipment = result.scalar_one_or_none()

    if not shipment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Shipment not found"
        )

    if shipment.awb_number:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="AWB already generated"
        )

    if not shipment.transporter_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Transporter not assigned"
        )

    # Get transporter
    transporter_query = select(Transporter).where(Transporter.id == shipment.transporter_id)
    transporter_result = await db.execute(transporter_query)
    transporter = transporter_result.scalar_one()

    # Generate AWB
    prefix = transporter.awb_prefix or transporter.code[:3].upper()
    sequence = transporter.awb_sequence_current
    awb_number = f"{prefix}{sequence:010d}"

    transporter.awb_sequence_current = sequence + 1

    shipment.awb_number = awb_number
    shipment.tracking_number = awb_number
    shipment.status = ShipmentStatus.READY_FOR_PICKUP.value

    # Add tracking
    tracking = ShipmentTracking(
        shipment_id=shipment.id,
        status=ShipmentStatus.READY_FOR_PICKUP,
        remarks=f"AWB generated: {awb_number}",
        event_time=datetime.now(timezone.utc),
        source="SYSTEM",
        updated_by=current_user.id,
    )
    db.add(tracking)

    await db.commit()
    await db.refresh(shipment)

    return ShipmentResponse.model_validate(shipment)


@router.post(
    "/{shipment_id}/track",
    response_model=ShipmentTrackingResponse,
    dependencies=[Depends(require_permissions("logistics:update"))]
)
async def update_tracking(
    shipment_id: uuid.UUID,
    data: ShipmentTrackingUpdate,
    db: DB,
    current_user: CurrentUser,
):
    """Add tracking update to shipment."""
    query = select(Shipment).where(Shipment.id == shipment_id)
    result = await db.execute(query)
    shipment = result.scalar_one_or_none()

    if not shipment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Shipment not found"
        )

    # Update shipment status
    shipment.status = data.status

    # Mark shipped if transitioning to shipped
    if data.status == ShipmentStatus.SHIPPED and not shipment.shipped_at:
        shipment.shipped_at = datetime.now(timezone.utc)

    # Add tracking entry
    tracking = ShipmentTracking(
        shipment_id=shipment.id,
        status=data.status,
        status_code=data.status_code,
        location=data.location,
        city=data.city,
        state=data.state,
        pincode=data.pincode,
        remarks=data.remarks,
        event_time=data.event_time or datetime.now(timezone.utc),
        source=data.source,
        updated_by=current_user.id,
    )
    db.add(tracking)

    await db.commit()
    await db.refresh(tracking)

    return ShipmentTrackingResponse.model_validate(tracking)


@router.post(
    "/{shipment_id}/deliver",
    response_model=ShipmentDeliveryMarkResponse,
    dependencies=[Depends(require_permissions("logistics:update"))]
)
async def mark_delivered(
    shipment_id: uuid.UUID,
    data: ShipmentDeliveryMarkRequest,
    db: DB,
    current_user: CurrentUser,
):
    """
    Mark shipment as delivered with POD (Proof of Delivery).

    This endpoint triggers the complete post-delivery workflow:
    1. Updates shipment status to DELIVERED
    2. Updates order status to DELIVERED
    3. Posts COGS and warranty accounting entries
    4. Creates Installation record (auto)
    5. Creates ServiceRequest for installation (auto)
    6. Auto-assigns technician/franchisee based on pincode
    7. Queues customer notifications (SMS/Email)
    """
    query = select(Shipment).where(Shipment.id == shipment_id)
    result = await db.execute(query)
    shipment = result.scalar_one_or_none()

    if not shipment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Shipment not found"
        )

    if shipment.status == ShipmentStatus.DELIVERED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Shipment already delivered"
        )

    # Update shipment
    now = datetime.now(timezone.utc)
    shipment.status = ShipmentStatus.DELIVERED.value
    shipment.delivered_at = now
    shipment.actual_delivery_date = now.date()
    shipment.delivered_to = data.delivered_to
    shipment.delivery_relation = data.delivery_relation
    shipment.delivery_remarks = data.delivery_remarks
    shipment.pod_image_url = data.pod_image_url
    shipment.pod_signature_url = data.pod_signature_url

    if data.cod_collected:
        shipment.cod_collected = True

    shipment.delivery_attempts += 1

    # Add tracking
    tracking = ShipmentTracking(
        shipment_id=shipment.id,
        status=ShipmentStatus.DELIVERED,
        remarks=f"Delivered to {data.delivered_to}",
        event_time=now,
        source="SYSTEM",
        updated_by=current_user.id,
    )
    db.add(tracking)

    # Update order status (eagerly load items for COGS calculation)
    order_query = (
        select(Order)
        .where(Order.id == shipment.order_id)
        .options(selectinload(Order.items))
    )
    order_result = await db.execute(order_query)
    order = order_result.scalar_one_or_none()
    if order:
        order.status = OrderStatus.DELIVERED.value
        order.delivered_at = now

    await db.commit()
    await db.refresh(shipment)

    # Post COGS accounting entry
    if order:
        try:
            from decimal import Decimal
            from app.services.accounting_service import AccountingService
            accounting = AccountingService(db)

            # Calculate actual COGS from Weighted Average Cost
            from app.services.costing_service import CostingService
            costing_svc = CostingService(db)
            cost_amount = Decimal("0")
            for item in order.items:
                item_cost = await costing_svc.get_cost_for_product(
                    product_id=item.product_id,
                    quantity=item.quantity,
                    warehouse_id=shipment.warehouse_id,
                )
                cost_amount += item_cost
            if cost_amount <= 0:
                cost_amount = Decimal(str(order.total_amount)) * Decimal("0.6")
                logging.warning(
                    f"No WAC cost found, using 60%% fallback for order {order.order_number}"
                )

            await accounting.post_cogs_entry(
                order_id=order.id,
                order_number=order.order_number,
                cost_amount=cost_amount,
                product_type="purifier",
            )

            # Also post warranty provision (2% of selling price)
            warranty_amount = Decimal(str(order.total_amount)) * Decimal("0.02")
            if warranty_amount > 0:
                await accounting.post_warranty_provision(
                    order_id=order.id,
                    order_number=order.order_number,
                    provision_amount=warranty_amount,
                )

            await db.commit()
        except Exception as e:
            import logging
            logging.warning(f"Failed to post COGS/warranty for order {order.order_number}: {e}")

    # ========== POST-DELIVERY WORKFLOW ==========
    # Trigger automatic installation scheduling and technician assignment
    post_delivery_result = None
    try:
        from app.services.post_delivery_service import PostDeliveryService

        pod_data = {
            "signature_url": data.pod_signature_url,
            "image_url": data.pod_image_url,
            "received_by": data.delivered_to,
            "remarks": data.delivery_remarks,
            "latitude": getattr(data, 'latitude', None),
            "longitude": getattr(data, 'longitude', None),
        }

        post_delivery_service = PostDeliveryService(db)
        post_delivery_result = await post_delivery_service.process_delivery(
            shipment_id=str(shipment_id),
            pod_data=pod_data
        )

        import logging
        logging.info(
            f"Post-delivery workflow completed for shipment {shipment.shipment_number}: "
            f"Installation={post_delivery_result.get('installation_id')}, "
            f"ServiceRequest={post_delivery_result.get('service_request_id')}, "
            f"Technician={post_delivery_result.get('technician_id')}, "
            f"Franchisee={post_delivery_result.get('franchisee_id')}"
        )
    except Exception as e:
        import logging
        logging.warning(f"Post-delivery workflow failed for shipment {shipment.shipment_number}: {e}")
        # Don't fail the delivery marking - just log the error
        # Installation can be created manually if auto-creation fails

    # Build response with post-delivery info
    response_message = "Shipment marked as delivered"
    if post_delivery_result:
        response_message += f". Installation #{post_delivery_result.get('installation_id', 'pending')[:8]} created."
        if post_delivery_result.get('technician_id') or post_delivery_result.get('franchisee_id'):
            response_message += " Service assigned."

    return ShipmentDeliveryMarkResponse(
        success=True,
        shipment_id=shipment.id,
        shipment_number=shipment.shipment_number,
        order_id=shipment.order_id,
        status=shipment.status,
        delivered_at=shipment.delivered_at,
        message=response_message,
    )


@router.post(
    "/{shipment_id}/rto",
    response_model=ShipmentRTOResponse,
    dependencies=[Depends(require_permissions("logistics:update"))]
)
async def initiate_rto(
    shipment_id: uuid.UUID,
    data: ShipmentRTOInitiateRequest,
    db: DB,
    current_user: CurrentUser,
):
    """Initiate Return to Origin (RTO)."""
    query = select(Shipment).where(Shipment.id == shipment_id)
    result = await db.execute(query)
    shipment = result.scalar_one_or_none()

    if not shipment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Shipment not found"
        )

    if shipment.status in [ShipmentStatus.DELIVERED, ShipmentStatus.RTO_DELIVERED]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot initiate RTO for delivered shipment"
        )

    shipment.status = ShipmentStatus.RTO_INITIATED.value
    shipment.rto_reason = data.reason
    shipment.rto_initiated_at = datetime.now(timezone.utc)

    # Add tracking
    tracking = ShipmentTracking(
        shipment_id=shipment.id,
        status=ShipmentStatus.RTO_INITIATED,
        remarks=f"RTO initiated: {data.reason}",
        event_time=datetime.now(timezone.utc),
        source="SYSTEM",
        updated_by=current_user.id,
    )
    db.add(tracking)

    await db.commit()
    await db.refresh(shipment)

    return ShipmentRTOResponse(
        success=True,
        shipment_id=shipment.id,
        shipment_number=shipment.shipment_number,
        status=shipment.status,
        rto_reason=data.reason,
        message="RTO initiated successfully",
    )


@router.post(
    "/{shipment_id}/cancel",
    response_model=ShipmentResponse,
    dependencies=[Depends(require_permissions("logistics:delete"))]
)
async def cancel_shipment(
    shipment_id: uuid.UUID,
    data: ShipmentCancelRequest,
    db: DB,
    current_user: CurrentUser,
):
    """Cancel a shipment."""
    query = select(Shipment).where(Shipment.id == shipment_id)
    result = await db.execute(query)
    shipment = result.scalar_one_or_none()

    if not shipment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Shipment not found"
        )

    if shipment.status in [ShipmentStatus.DELIVERED, ShipmentStatus.SHIPPED]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot cancel shipped/delivered shipment"
        )

    shipment.status = ShipmentStatus.CANCELLED.value
    shipment.cancelled_at = datetime.now(timezone.utc)
    shipment.cancellation_reason = data.reason

    # Add tracking
    tracking = ShipmentTracking(
        shipment_id=shipment.id,
        status=ShipmentStatus.CANCELLED,
        remarks=f"Cancelled: {data.reason}",
        event_time=datetime.now(timezone.utc),
        source="SYSTEM",
        updated_by=current_user.id,
    )
    db.add(tracking)

    await db.commit()
    await db.refresh(shipment)

    return ShipmentResponse.model_validate(shipment)


# ==================== PUBLIC TRACKING ====================

@router.post(
    "/track",
    response_model=TrackShipmentResponse,
)
@require_module("oms_fulfillment")
async def track_shipment_public(
    data: TrackShipmentRequest,
    db: DB,
):
    """Public tracking API (no auth required)."""
    query = select(Shipment).options(selectinload(Shipment.tracking_history))

    if data.awb_number:
        query = query.where(Shipment.awb_number == data.awb_number)
    elif data.order_number:
        query = query.join(Order).where(Order.order_number == data.order_number)
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Provide awb_number or order_number"
        )

    result = await db.execute(query)
    shipment = result.scalar_one_or_none()

    if not shipment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Shipment not found"
        )

    status_descriptions = {
        ShipmentStatus.CREATED: "Order is being processed",
        ShipmentStatus.PACKED: "Order has been packed",
        ShipmentStatus.READY_FOR_PICKUP: "Ready for pickup by courier",
        ShipmentStatus.MANIFESTED: "Handed over to courier",
        ShipmentStatus.SHIPPED: "In transit",
        ShipmentStatus.IN_TRANSIT: "In transit to destination",
        ShipmentStatus.OUT_FOR_DELIVERY: "Out for delivery",
        ShipmentStatus.DELIVERED: "Delivered successfully",
        ShipmentStatus.RTO_INITIATED: "Return initiated",
        ShipmentStatus.RTO_IN_TRANSIT: "Return in progress",
        ShipmentStatus.RTO_DELIVERED: "Returned to seller",
        ShipmentStatus.CANCELLED: "Cancelled",
    }

    return TrackShipmentResponse(
        awb_number=shipment.awb_number or shipment.shipment_number,
        order_number=shipment.shipment_number,
        status=shipment.status,
        status_description=status_descriptions.get(shipment.status, "Unknown"),
        current_location=shipment.tracking_history[-1].location if shipment.tracking_history else None,
        expected_delivery=shipment.expected_delivery_date,
        delivered_at=shipment.delivered_at,
        delivered_to=shipment.delivered_to,
        tracking_history=[
            ShipmentTrackingResponse.model_validate(t) for t in shipment.tracking_history
        ],
    )


# ==================== LABEL & INVOICE ====================

@router.get(
    "/{shipment_id}/label",
    response_model=ShipmentLabelResponse,
    dependencies=[Depends(require_permissions("logistics:view"))]
)
async def get_shipping_label(
    shipment_id: uuid.UUID,
    db: DB,
    current_user: CurrentUser,
):
    """Get shipping label for a shipment."""
    query = (
        select(Shipment)
        .where(Shipment.id == shipment_id)
        .options(
            selectinload(Shipment.order),
            selectinload(Shipment.transporter),
        )
    )
    result = await db.execute(query)
    shipment = result.scalar_one_or_none()

    if not shipment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Shipment not found"
        )

    # Generate label URL (in production, this would generate actual PDF/ZPL)
    label_url = f"/api/v1/shipments/{shipment_id}/label/download"

    return ShipmentLabelResponse(
        shipment_id=shipment.id,
        shipment_number=shipment.shipment_number,
        awb_number=shipment.awb_number,
        label_url=label_url,
        format="PDF",
    )


@router.get(
    "/{shipment_id}/label/download",
    # No auth required for label download (demo mode - use signed URLs in production)
)
async def download_shipping_label(
    shipment_id: uuid.UUID,
    db: DB,
):
    """Download shipping label as HTML (for demo - production would generate PDF)."""
    query = (
        select(Shipment)
        .where(Shipment.id == shipment_id)
        .options(
            selectinload(Shipment.order).selectinload(Order.customer),
            selectinload(Shipment.transporter),
            selectinload(Shipment.warehouse),
        )
    )
    result = await db.execute(query)
    shipment = result.scalar_one_or_none()

    if not shipment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Shipment not found"
        )

    from fastapi.responses import HTMLResponse

    # Get address details
    ship_to = shipment.ship_to_address or {}

    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>Shipping Label - {shipment.shipment_number}</title>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 20px; }}
            .label {{ border: 2px solid #000; padding: 20px; max-width: 400px; }}
            .header {{ text-align: center; border-bottom: 2px solid #000; padding-bottom: 10px; margin-bottom: 10px; }}
            .awb {{ font-size: 24px; font-weight: bold; letter-spacing: 2px; }}
            .barcode {{ text-align: center; font-family: 'Libre Barcode 39', cursive; font-size: 48px; margin: 10px 0; }}
            .section {{ margin: 10px 0; padding: 10px 0; border-bottom: 1px dashed #ccc; }}
            .label-title {{ font-weight: bold; font-size: 12px; color: #666; }}
            .label-value {{ font-size: 14px; margin-top: 5px; }}
            .address {{ font-size: 16px; line-height: 1.5; }}
            .footer {{ text-align: center; margin-top: 15px; font-size: 12px; }}
            .logo {{ font-size: 20px; font-weight: bold; color: #0066cc; }}
        </style>
    </head>
    <body>
        <div class="label">
            <div class="header">
                <div class="logo">{shipment.transporter.name if shipment.transporter else 'ILMS.AI'}</div>
                <div class="awb">AWB: {shipment.awb_number or shipment.shipment_number}</div>
                <div class="barcode">*{shipment.awb_number or shipment.shipment_number}*</div>
            </div>

            <div class="section">
                <div class="label-title">SHIP TO:</div>
                <div class="address">
                    <strong>{shipment.ship_to_name or 'Customer'}</strong><br>
                    {ship_to.get('address_line1', '')}<br>
                    {ship_to.get('address_line2', '') + '<br>' if ship_to.get('address_line2') else ''}
                    {shipment.ship_to_city or ''}, {shipment.ship_to_state or ''}<br>
                    <strong>PIN: {shipment.ship_to_pincode or ''}</strong><br>
                    Ph: {shipment.ship_to_phone or ''}
                </div>
            </div>

            <div class="section">
                <div class="label-title">FROM:</div>
                <div class="label-value">
                    ILMS.AI<br>
                    {shipment.warehouse.address if shipment.warehouse and hasattr(shipment.warehouse, 'address') else 'Central Warehouse, Delhi'}<br>
                    Ph: +91-9311939076
                </div>
            </div>

            <div class="section">
                <table style="width:100%">
                    <tr>
                        <td><span class="label-title">Order:</span><br>{shipment.order.order_number if shipment.order else 'N/A'}</td>
                        <td><span class="label-title">Weight:</span><br>{shipment.weight_kg} kg</td>
                        <td><span class="label-title">Boxes:</span><br>{shipment.no_of_boxes}</td>
                    </tr>
                    <tr>
                        <td><span class="label-title">Payment:</span><br>{shipment.payment_mode if shipment.payment_mode else 'PREPAID'}</td>
                        <td colspan="2"><span class="label-title">COD Amount:</span><br>₹{shipment.cod_amount or 0}</td>
                    </tr>
                </table>
            </div>

            <div class="footer">
                Shipment Date: {shipment.created_at.strftime('%d-%b-%Y') if shipment.created_at else 'N/A'}<br>
                <small>Handle with care | Fragile</small>
            </div>
        </div>

        <script>window.print();</script>
    </body>
    </html>
    """

    return HTMLResponse(content=html_content)


@router.get(
    "/{shipment_id}/invoice",
    response_model=ShipmentInvoiceResponse,
    dependencies=[Depends(require_permissions("logistics:view"))]
)
async def get_shipment_invoice(
    shipment_id: uuid.UUID,
    db: DB,
    current_user: CurrentUser,
):
    """Get invoice for a shipment."""
    query = (
        select(Shipment)
        .where(Shipment.id == shipment_id)
        .options(selectinload(Shipment.order))
    )
    result = await db.execute(query)
    shipment = result.scalar_one_or_none()

    if not shipment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Shipment not found"
        )

    invoice_url = f"/api/v1/shipments/{shipment_id}/invoice/download"

    return ShipmentInvoiceResponse(
        shipment_id=shipment.id,
        shipment_number=shipment.shipment_number,
        invoice_url=invoice_url,
    )


@router.get(
    "/{shipment_id}/invoice/download",
    # No auth required for invoice download (demo mode - use signed URLs in production)
)
async def download_shipment_invoice(
    shipment_id: uuid.UUID,
    db: DB,
):
    """Download shipment invoice as HTML (for demo - production would generate PDF)."""
    query = (
        select(Shipment)
        .where(Shipment.id == shipment_id)
        .options(
            selectinload(Shipment.order).selectinload(Order.customer),
            selectinload(Shipment.order).selectinload(Order.items),
            selectinload(Shipment.transporter),
        )
    )
    result = await db.execute(query)
    shipment = result.scalar_one_or_none()

    if not shipment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Shipment not found"
        )

    from fastapi.responses import HTMLResponse

    order = shipment.order
    customer = order.customer if order else None
    ship_to = shipment.ship_to_address or {}

    # Build items table
    items_html = ""
    if order and order.items:
        for idx, item in enumerate(order.items, 1):
            unit_price = float(item.unit_price) if item.unit_price else 0.0
            total_amt = float(item.total_amount) if item.total_amount else 0.0
            items_html += f"""
            <tr>
                <td>{idx}</td>
                <td>{item.product_name}<br><small>SKU: {item.product_sku}</small></td>
                <td>{item.hsn_code or 'N/A'}</td>
                <td style="text-align:right">{item.quantity}</td>
                <td style="text-align:right">₹{unit_price:,.2f}</td>
                <td style="text-align:right">₹{total_amt:,.2f}</td>
            </tr>
            """

    invoice_number = f"INV-{shipment.shipment_number.replace('SHP-', '')}"
    invoice_date = shipment.created_at.strftime('%d-%b-%Y') if shipment.created_at else datetime.now().strftime('%d-%b-%Y')

    # Calculate totals (handle Decimal and None)
    subtotal = float(order.subtotal) if order and order.subtotal else 0.0
    tax_amount = float(order.tax_amount) if order and order.tax_amount else 0.0
    shipping_amount = float(order.shipping_amount) if order and order.shipping_amount else 0.0
    discount_amount = float(order.discount_amount) if order and order.discount_amount else 0.0
    total_amount = float(order.total_amount) if order and order.total_amount else 0.0

    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>Tax Invoice - {invoice_number}</title>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 20px; font-size: 12px; }}
            .invoice {{ max-width: 800px; margin: 0 auto; }}
            .header {{ display: flex; justify-content: space-between; border-bottom: 2px solid #000; padding-bottom: 10px; }}
            .company {{ }}
            .company-name {{ font-size: 24px; font-weight: bold; color: #0066cc; }}
            .invoice-title {{ font-size: 20px; font-weight: bold; text-align: right; }}
            .invoice-details {{ text-align: right; }}
            .addresses {{ display: flex; justify-content: space-between; margin: 20px 0; }}
            .address-box {{ width: 48%; padding: 10px; border: 1px solid #ddd; }}
            .address-title {{ font-weight: bold; background: #f0f0f0; padding: 5px; margin: -10px -10px 10px -10px; }}
            table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
            th, td {{ border: 1px solid #ddd; padding: 8px; }}
            th {{ background: #f0f0f0; }}
            .totals {{ width: 300px; margin-left: auto; }}
            .totals td {{ border: none; padding: 5px; }}
            .totals .total-row {{ font-weight: bold; font-size: 16px; border-top: 2px solid #000; }}
            .footer {{ margin-top: 30px; border-top: 1px solid #ddd; padding-top: 10px; }}
            .signature {{ text-align: right; margin-top: 50px; }}
            @media print {{ body {{ margin: 0; }} }}
        </style>
    </head>
    <body>
        <div class="invoice">
            <div class="header">
                <div class="company">
                    <div class="company-name">ILMS.AI</div>
                    <div>Plot 36-A KH No 181, Najafgarh</div>
                    <div>Delhi - 110043, India</div>
                    <div>GSTIN: 07ABDCA6170C1Z5</div>
                    <div>Phone: +91-9311939076</div>
                </div>
                <div>
                    <div class="invoice-title">TAX INVOICE</div>
                    <div class="invoice-details">
                        <div><strong>Invoice No:</strong> {invoice_number}</div>
                        <div><strong>Date:</strong> {invoice_date}</div>
                        <div><strong>Order No:</strong> {order.order_number if order else 'N/A'}</div>
                        <div><strong>AWB:</strong> {shipment.awb_number or shipment.shipment_number}</div>
                    </div>
                </div>
            </div>

            <div class="addresses">
                <div class="address-box">
                    <div class="address-title">BILL TO:</div>
                    <strong>{customer.full_name if customer else 'Customer'}</strong><br>
                    {order.billing_address.get('address_line1', ship_to.get('address_line1', '')) if order and order.billing_address else ship_to.get('address_line1', '')}<br>
                    {order.billing_address.get('city', ship_to.get('city', '')) if order and order.billing_address else ship_to.get('city', '')},
                    {order.billing_address.get('state', ship_to.get('state', '')) if order and order.billing_address else ship_to.get('state', '')} -
                    {order.billing_address.get('pincode', ship_to.get('pincode', '')) if order and order.billing_address else ship_to.get('pincode', '')}<br>
                    Phone: {customer.phone if customer else shipment.ship_to_phone or ''}
                </div>
                <div class="address-box">
                    <div class="address-title">SHIP TO:</div>
                    <strong>{shipment.ship_to_name or 'Customer'}</strong><br>
                    {ship_to.get('address_line1', '')}<br>
                    {shipment.ship_to_city or ''}, {shipment.ship_to_state or ''} - {shipment.ship_to_pincode or ''}<br>
                    Phone: {shipment.ship_to_phone or ''}
                </div>
            </div>

            <table>
                <thead>
                    <tr>
                        <th style="width:30px">#</th>
                        <th>Product Description</th>
                        <th style="width:80px">HSN</th>
                        <th style="width:50px">Qty</th>
                        <th style="width:100px">Unit Price</th>
                        <th style="width:100px">Amount</th>
                    </tr>
                </thead>
                <tbody>
                    {items_html}
                </tbody>
            </table>

            <table class="totals">
                <tr>
                    <td>Subtotal:</td>
                    <td style="text-align:right">₹{subtotal:,.2f}</td>
                </tr>
                <tr>
                    <td>CGST (9%):</td>
                    <td style="text-align:right">₹{tax_amount/2:,.2f}</td>
                </tr>
                <tr>
                    <td>SGST (9%):</td>
                    <td style="text-align:right">₹{tax_amount/2:,.2f}</td>
                </tr>
                <tr>
                    <td>Shipping:</td>
                    <td style="text-align:right">₹{shipping_amount:,.2f}</td>
                </tr>
                <tr>
                    <td>Discount:</td>
                    <td style="text-align:right">-₹{discount_amount:,.2f}</td>
                </tr>
                <tr class="total-row">
                    <td>GRAND TOTAL:</td>
                    <td style="text-align:right">₹{total_amount:,.2f}</td>
                </tr>
            </table>

            <div class="footer">
                <div><strong>Payment Method:</strong> {order.payment_method if order else 'N/A'}</div>
                <div><strong>Payment Status:</strong> {order.payment_status if order else 'N/A'}</div>
                <br>
                <div><strong>Terms & Conditions:</strong></div>
                <ol style="font-size:10px; color:#666;">
                    <li>Goods once sold will not be taken back.</li>
                    <li>All disputes are subject to Delhi jurisdiction.</li>
                    <li>E&OE - Errors and Omissions Excepted.</li>
                </ol>
            </div>

            <div class="signature">
                <div>For ILMS.AI</div>
                <br><br><br>
                <div>Authorized Signatory</div>
            </div>
        </div>

        <script>window.print();</script>
    </body>
    </html>
    """

    return HTMLResponse(content=html_content)


# ==================== SLA DASHBOARD ====================

@router.get(
    "/sla/dashboard",
    dependencies=[Depends(require_permissions("logistics:view"))]
)
async def get_sla_dashboard(
    db: DB,
    warehouse_id: Optional[uuid.UUID] = Query(None),
    transporter_id: Optional[uuid.UUID] = Query(None),
):
    """
    Get SLA dashboard with delivery performance metrics.
    
    Includes:
    - On-time delivery rate
    - At-risk shipments (may breach SLA)
    - Breached shipments (past SLA)
    - Average delivery time
    """
    from datetime import date, timedelta
    
    base_query = select(Shipment).where(
        Shipment.status.in_([
            ShipmentStatus.PICKED_UP,
            ShipmentStatus.IN_TRANSIT,
            ShipmentStatus.OUT_FOR_DELIVERY,
            ShipmentStatus.DELIVERED,
        ])
    )
    
    if warehouse_id:
        base_query = base_query.where(Shipment.warehouse_id == warehouse_id)
    if transporter_id:
        base_query = base_query.where(Shipment.transporter_id == transporter_id)
    
    result = await db.execute(base_query)
    shipments = result.scalars().all()
    
    today = date.today()
    
    # Categorize shipments
    total = 0
    on_time = 0
    breached = 0
    at_risk = 0
    in_transit = 0
    delivered = 0
    delivery_times = []
    
    at_risk_shipments = []
    breached_shipments = []
    
    for s in shipments:
        total += 1
        
        if s.status == ShipmentStatus.DELIVERED:
            delivered += 1
            
            # Check if delivered on time
            if s.actual_delivery_date and s.promised_delivery_date:
                if s.actual_delivery_date <= s.promised_delivery_date:
                    on_time += 1
                else:
                    breached += 1
                    breached_shipments.append({
                        "shipment_id": str(s.id),
                        "shipment_number": s.shipment_number,
                        "awb_number": s.awb_number,
                        "promised_date": s.promised_delivery_date.isoformat() if s.promised_delivery_date else None,
                        "actual_date": s.actual_delivery_date.isoformat() if s.actual_delivery_date else None,
                        "days_late": (s.actual_delivery_date - s.promised_delivery_date).days if s.promised_delivery_date else 0,
                    })
            elif s.promised_delivery_date is None:
                on_time += 1  # No SLA = on time
            
            # Calculate delivery time
            if s.shipped_at and s.delivered_at:
                days = (s.delivered_at.date() - s.shipped_at.date()).days
                delivery_times.append(days)
        
        else:
            in_transit += 1
            
            # Check if at risk (1 day before breach) or already breached
            if s.promised_delivery_date:
                if s.promised_delivery_date < today:
                    breached += 1
                    breached_shipments.append({
                        "shipment_id": str(s.id),
                        "shipment_number": s.shipment_number,
                        "awb_number": s.awb_number,
                        "promised_date": s.promised_delivery_date.isoformat(),
                        "days_late": (today - s.promised_delivery_date).days,
                        "status": s.status,
                    })
                elif s.promised_delivery_date <= today + timedelta(days=1):
                    at_risk += 1
                    at_risk_shipments.append({
                        "shipment_id": str(s.id),
                        "shipment_number": s.shipment_number,
                        "awb_number": s.awb_number,
                        "promised_date": s.promised_delivery_date.isoformat(),
                        "days_remaining": (s.promised_delivery_date - today).days,
                        "status": s.status,
                    })
    
    # Calculate metrics
    on_time_rate = (on_time / delivered * 100) if delivered > 0 else 100
    avg_delivery_days = sum(delivery_times) / len(delivery_times) if delivery_times else 0
    breach_rate = (breached / total * 100) if total > 0 else 0
    
    return {
        "summary": {
            "total_shipments": total,
            "delivered": delivered,
            "in_transit": in_transit,
            "on_time_deliveries": on_time,
            "breached": breached,
            "at_risk": at_risk,
        },
        "metrics": {
            "on_time_rate": round(on_time_rate, 2),
            "breach_rate": round(breach_rate, 2),
            "average_delivery_days": round(avg_delivery_days, 1),
        },
        "at_risk_shipments": at_risk_shipments[:10],  # Top 10
        "breached_shipments": breached_shipments[:10],  # Top 10
    }


@router.get(
    "/sla/at-risk",
    dependencies=[Depends(require_permissions("logistics:view"))]
)
async def get_at_risk_shipments(
    db: DB,
    days_threshold: int = Query(1, ge=0, le=7, description="Days until SLA breach"),
    warehouse_id: Optional[uuid.UUID] = Query(None),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
):
    """
    Get shipments at risk of SLA breach.
    
    Returns shipments where promised_delivery_date is within threshold days.
    """
    from datetime import date, timedelta
    
    today = date.today()
    threshold_date = today + timedelta(days=days_threshold)
    
    query = (
        select(Shipment)
        .where(
            and_(
                Shipment.status.in_([
                    ShipmentStatus.PICKED_UP,
                    ShipmentStatus.IN_TRANSIT,
                    ShipmentStatus.OUT_FOR_DELIVERY,
                ]),
                Shipment.promised_delivery_date != None,
                Shipment.promised_delivery_date <= threshold_date,
            )
        )
        .order_by(Shipment.promised_delivery_date)
    )
    
    if warehouse_id:
        query = query.where(Shipment.warehouse_id == warehouse_id)
    
    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0
    
    # Paginate
    skip = (page - 1) * size
    query = query.offset(skip).limit(size)
    
    result = await db.execute(query)
    shipments = result.scalars().all()
    
    items = []
    for s in shipments:
        days_remaining = (s.promised_delivery_date - today).days if s.promised_delivery_date else None
        status_label = "BREACHED" if days_remaining and days_remaining < 0 else "AT_RISK"
        
        items.append({
            "shipment_id": str(s.id),
            "shipment_number": s.shipment_number,
            "awb_number": s.awb_number,
            "status": s.status,
            "promised_date": s.promised_delivery_date.isoformat() if s.promised_delivery_date else None,
            "days_remaining": days_remaining,
            "sla_status": status_label,
            "ship_to_city": s.ship_to_city,
            "ship_to_pincode": s.ship_to_pincode,
        })
    
    return {
        "items": items,
        "total": total,
        "page": page,
        "size": size,
        "pages": ceil(total / size) if total > 0 else 1,
    }


# ==================== POD UPLOAD ====================

@router.post(
    "/{shipment_id}/pod/upload",
    dependencies=[Depends(require_permissions("logistics:update"))]
)
async def upload_pod(
    shipment_id: uuid.UUID,
    db: DB,
    current_user: CurrentUser,
    pod_image: Optional[bytes] = None,  # Will be file upload
    signature_image: Optional[bytes] = None,
):
    """
    Upload Proof of Delivery (POD) images.
    
    Use with multipart/form-data to upload POD image and/or signature.
    """
    from fastapi import UploadFile, File
    
    query = select(Shipment).where(Shipment.id == shipment_id)
    result = await db.execute(query)
    shipment = result.scalar_one_or_none()
    
    if not shipment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Shipment not found"
        )
    
    # This is a placeholder - in production, upload to S3/GCS
    pod_image_url = None
    pod_signature_url = None
    
    return {
        "success": True,
        "shipment_id": str(shipment_id),
        "pod_image_url": pod_image_url,
        "pod_signature_url": pod_signature_url,
        "message": "POD upload endpoint ready - integrate with file storage"
    }


from fastapi import UploadFile, File, Form
import os
from pathlib import Path


@router.post(
    "/{shipment_id}/pod/upload-file",
    dependencies=[Depends(require_permissions("logistics:update"))]
)
async def upload_pod_file(
    shipment_id: uuid.UUID,
    db: DB,
    current_user: CurrentUser,
    pod_image: Optional[UploadFile] = File(None, description="POD photo"),
    signature_image: Optional[UploadFile] = File(None, description="Signature image"),
    delivered_to: str = Form(..., description="Name of person who received"),
    delivery_relation: Optional[str] = Form(None, description="Relationship: Self, Family, Security"),
    delivery_remarks: Optional[str] = Form(None, description="Delivery remarks"),
    latitude: Optional[float] = Form(None, description="GPS latitude"),
    longitude: Optional[float] = Form(None, description="GPS longitude"),
    cod_collected: bool = Form(False, description="Was COD amount collected?"),
):
    """
    Upload POD with images and mark shipment as delivered.
    
    Use multipart/form-data to upload POD image and/or signature along with delivery details.
    """
    query = select(Shipment).where(Shipment.id == shipment_id)
    result = await db.execute(query)
    shipment = result.scalar_one_or_none()
    
    if not shipment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Shipment not found"
        )
    
    if shipment.status == ShipmentStatus.DELIVERED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Shipment already delivered"
        )
    
    # Create upload directory
    upload_dir = Path("/tmp/pod_uploads")
    upload_dir.mkdir(parents=True, exist_ok=True)
    
    pod_image_url = None
    pod_signature_url = None
    
    # Save POD image
    if pod_image and pod_image.filename:
        ext = os.path.splitext(pod_image.filename)[1] or ".jpg"
        pod_filename = f"{shipment.shipment_number}_pod{ext}"
        pod_path = upload_dir / pod_filename
        
        content = await pod_image.read()
        with open(pod_path, "wb") as f:
            f.write(content)
        
        # In production, this would be a cloud storage URL
        pod_image_url = f"/static/pod/{pod_filename}"
    
    # Save signature image
    if signature_image and signature_image.filename:
        ext = os.path.splitext(signature_image.filename)[1] or ".png"
        sig_filename = f"{shipment.shipment_number}_sig{ext}"
        sig_path = upload_dir / sig_filename
        
        content = await signature_image.read()
        with open(sig_path, "wb") as f:
            f.write(content)
        
        pod_signature_url = f"/static/pod/{sig_filename}"
    
    # Update shipment with delivery info
    now = datetime.now(timezone.utc)
    shipment.status = ShipmentStatus.DELIVERED.value
    shipment.delivered_at = now
    shipment.actual_delivery_date = now.date()
    shipment.delivered_to = delivered_to
    shipment.delivery_relation = delivery_relation
    shipment.delivery_remarks = delivery_remarks
    shipment.pod_image_url = pod_image_url
    shipment.pod_signature_url = pod_signature_url
    shipment.pod_latitude = latitude
    shipment.pod_longitude = longitude
    shipment.delivery_attempts += 1
    
    if cod_collected:
        shipment.cod_collected = True
        shipment.cod_collected_at = now
    
    # Add tracking entry
    tracking = ShipmentTracking(
        shipment_id=shipment.id,
        status=ShipmentStatus.DELIVERED,
        remarks=f"Delivered to {delivered_to}. POD collected.",
        event_time=now,
        source="POD_UPLOAD",
        updated_by=current_user.id,
    )
    db.add(tracking)
    
    # Update related order
    if shipment.order_id:
        order_query = select(Order).where(Order.id == shipment.order_id)
        order_result = await db.execute(order_query)
        order = order_result.scalar_one_or_none()
        if order:
            order.status = OrderStatus.DELIVERED.value
            order.delivered_at = now
    
    await db.commit()
    await db.refresh(shipment)
    
    return {
        "success": True,
        "shipment_id": str(shipment.id),
        "shipment_number": shipment.shipment_number,
        "status": shipment.status,
        "delivered_at": shipment.delivered_at.isoformat() if shipment.delivered_at else None,
        "pod_image_url": pod_image_url,
        "pod_signature_url": pod_signature_url,
        "gps_coordinates": {
            "latitude": latitude,
            "longitude": longitude,
        } if latitude and longitude else None,
        "message": f"Shipment delivered successfully to {delivered_to}"
    }


# ==================== E-WAY BILL INTEGRATION ====================

@router.post(
    "/{shipment_id}/generate-eway-bill",
    summary="Generate E-Way Bill for shipment",
    description="""
    Generate E-Way Bill from NIC portal for a shipment.

    **Requirements:**
    - Invoice value must be > ₹50,000
    - Shipment must have an associated invoice
    - Company must have E-Way Bill credentials configured

    **Returns:**
    - E-Way Bill number
    - Validity period based on distance
    """,
    dependencies=[Depends(require_permissions("logistics:manage"))]
)
async def generate_eway_bill_for_shipment(
    shipment_id: uuid.UUID,
    company_id: Optional[uuid.UUID] = None,
    db: DB = None,
    current_user: CurrentUser = None,
):
    """Generate E-Way Bill for a shipment."""
    from app.services.gst_ewaybill_service import GSTEWayBillService, GSTEWayBillError
    from app.models.billing import TaxInvoice, EWayBill, EWayBillItem

    # Get shipment
    query = select(Shipment).where(Shipment.id == shipment_id)
    result = await db.execute(query)
    shipment = result.scalar_one_or_none()

    if not shipment:
        raise HTTPException(status_code=404, detail="Shipment not found")

    if shipment.eway_bill_number:
        raise HTTPException(status_code=400, detail="E-Way Bill already generated for this shipment")

    # Get associated invoice
    invoice_query = (
        select(TaxInvoice)
        .where(TaxInvoice.shipment_id == shipment_id)
    )
    invoice_result = await db.execute(invoice_query)
    invoice = invoice_result.scalar_one_or_none()

    if not invoice:
        raise HTTPException(
            status_code=400,
            detail="No invoice found for this shipment. Generate invoice first."
        )

    if float(invoice.taxable_amount or 0) < 50000:
        raise HTTPException(
            status_code=400,
            detail="E-Way Bill not required for invoice value below ₹50,000"
        )

    # Check if E-Way Bill record exists for invoice
    ewb_query = select(EWayBill).where(EWayBill.invoice_id == invoice.id)
    ewb_result = await db.execute(ewb_query)
    ewb = ewb_result.scalar_one_or_none()

    effective_company_id = company_id or current_user.company_id

    if not effective_company_id:
        raise HTTPException(status_code=400, detail="Company ID is required")

    try:
        if not ewb:
            # Create E-Way Bill record from shipment data
            ewb = EWayBill(
                invoice_id=invoice.id,
                document_number=invoice.invoice_number,
                document_date=invoice.invoice_date,
                supply_type="O",  # Outward
                sub_supply_type="1",  # Supply
                document_type="INV",
                from_gstin=invoice.seller_gstin,
                from_name=invoice.seller_name,
                from_address1=invoice.seller_address[:255] if invoice.seller_address else "",
                from_place=invoice.billing_city,
                from_pincode=invoice.billing_pincode,
                from_state_code=invoice.seller_state_code,
                to_gstin=invoice.customer_gstin,
                to_name=shipment.ship_to_name,
                to_address1=shipment.ship_to_address.get("address_line1", "")[:255] if shipment.ship_to_address else "",
                to_place=shipment.ship_to_city or "",
                to_pincode=shipment.ship_to_pincode,
                to_state_code=invoice.place_of_supply_code,
                total_value=invoice.grand_total,
                cgst_amount=invoice.cgst_amount,
                sgst_amount=invoice.sgst_amount,
                igst_amount=invoice.igst_amount,
                cess_amount=invoice.cess_amount,
                distance_km=shipment.distance_km or 100,
                vehicle_number=shipment.vehicle_number,
                transport_doc_number=shipment.transport_doc_number or shipment.awb_number,
            )

            # Get transporter details
            if shipment.transporter_id:
                transporter_query = select(Transporter).where(Transporter.id == shipment.transporter_id)
                transporter_result = await db.execute(transporter_query)
                transporter = transporter_result.scalar_one_or_none()
                if transporter:
                    ewb.transporter_name = transporter.name
                    ewb.transporter_gstin = getattr(transporter, 'transporter_gstin', None)

            db.add(ewb)
            await db.flush()

            # Add items from invoice
            for item in invoice.items:
                ewb_item = EWayBillItem(
                    eway_bill_id=ewb.id,
                    product_name=item.item_name,
                    hsn_code=item.hsn_code,
                    quantity=item.quantity,
                    uom=item.uom,
                    taxable_value=item.taxable_value,
                    gst_rate=item.gst_rate,
                    cgst_amount=item.cgst_amount,
                    sgst_amount=item.sgst_amount,
                    igst_amount=item.igst_amount,
                )
                db.add(ewb_item)

        # Generate E-Way Bill via NIC portal
        ewaybill_service = GSTEWayBillService(db, effective_company_id)
        ewb_result = await ewaybill_service.generate_ewaybill(ewb.id)

        # Update shipment with E-Way Bill details
        shipment.eway_bill_number = ewb_result.get("ewb_number")
        shipment.eway_bill_id = ewb.id

        await db.commit()

        return {
            "success": True,
            "shipment_id": str(shipment_id),
            "eway_bill_number": ewb_result.get("ewb_number"),
            "eway_bill_date": ewb_result.get("ewb_date"),
            "valid_until": ewb_result.get("valid_until"),
            "message": "E-Way Bill generated successfully"
        }

    except GSTEWayBillError as e:
        raise HTTPException(
            status_code=400,
            detail={"message": e.message, "error_code": e.error_code, "details": e.details}
        )


@router.post(
    "/{shipment_id}/update-eway-bill-vehicle",
    summary="Update E-Way Bill vehicle details (Part-B)",
    description="""
    Update Part-B (vehicle/transporter details) of E-Way Bill.

    Use this when:
    - Vehicle breakdown requires change
    - Transshipment to another vehicle
    - First time vehicle assignment

    **Reason Codes:**
    - 1: Due to breakdown
    - 2: Due to transshipment
    - 3: Others
    - 4: First time
    """,
    dependencies=[Depends(require_permissions("logistics:manage"))]
)
async def update_eway_bill_vehicle(
    shipment_id: uuid.UUID,
    vehicle_number: str,
    reason_code: str = "4",
    reason_remarks: str = "",
    company_id: Optional[uuid.UUID] = None,
    db: DB = None,
    current_user: CurrentUser = None,
):
    """Update E-Way Bill Part-B (vehicle details)."""
    from app.services.gst_ewaybill_service import GSTEWayBillService, GSTEWayBillError
    from app.models.billing import EWayBill

    # Get shipment
    query = select(Shipment).where(Shipment.id == shipment_id)
    result = await db.execute(query)
    shipment = result.scalar_one_or_none()

    if not shipment:
        raise HTTPException(status_code=404, detail="Shipment not found")

    if not shipment.eway_bill_id:
        raise HTTPException(status_code=400, detail="No E-Way Bill found for this shipment")

    effective_company_id = company_id or current_user.company_id

    if not effective_company_id:
        raise HTTPException(status_code=400, detail="Company ID is required")

    try:
        ewaybill_service = GSTEWayBillService(db, effective_company_id)
        result = await ewaybill_service.update_part_b(
            ewb_id=shipment.eway_bill_id,
            vehicle_number=vehicle_number,
            reason_code=reason_code,
            reason_remarks=reason_remarks
        )

        # Update shipment vehicle number
        shipment.vehicle_number = vehicle_number
        await db.commit()

        return {
            "success": True,
            "shipment_id": str(shipment_id),
            "eway_bill_number": result.get("ewb_number"),
            "vehicle_number": result.get("vehicle_number"),
            "valid_until": result.get("valid_until"),
            "message": "E-Way Bill vehicle updated successfully"
        }

    except GSTEWayBillError as e:
        raise HTTPException(
            status_code=400,
            detail={"message": e.message, "error_code": e.error_code, "details": e.details}
        )


@router.get(
    "/{shipment_id}/eway-bill-status",
    summary="Get E-Way Bill status for shipment",
    description="Get current status and validity of E-Way Bill.",
    dependencies=[Depends(require_permissions("logistics:view"))]
)
async def get_eway_bill_status(
    shipment_id: uuid.UUID,
    company_id: Optional[uuid.UUID] = None,
    db: DB = None,
    current_user: CurrentUser = None,
):
    """Get E-Way Bill status for a shipment."""
    from app.services.gst_ewaybill_service import GSTEWayBillService, GSTEWayBillError
    from app.models.billing import EWayBill

    # Get shipment
    query = select(Shipment).where(Shipment.id == shipment_id)
    result = await db.execute(query)
    shipment = result.scalar_one_or_none()

    if not shipment:
        raise HTTPException(status_code=404, detail="Shipment not found")

    if not shipment.eway_bill_number:
        return {
            "shipment_id": str(shipment_id),
            "has_eway_bill": False,
            "message": "No E-Way Bill generated for this shipment"
        }

    # Get E-Way Bill record
    ewb_query = select(EWayBill).where(EWayBill.id == shipment.eway_bill_id)
    ewb_result = await db.execute(ewb_query)
    ewb = ewb_result.scalar_one_or_none()

    if not ewb:
        return {
            "shipment_id": str(shipment_id),
            "has_eway_bill": True,
            "eway_bill_number": shipment.eway_bill_number,
            "status": "UNKNOWN",
            "message": "E-Way Bill record not found in database"
        }

    # Check validity
    is_valid = ewb.is_valid if hasattr(ewb, 'is_valid') else True

    return {
        "shipment_id": str(shipment_id),
        "has_eway_bill": True,
        "eway_bill_number": ewb.eway_bill_number,
        "status": ewb.status,
        "generated_at": ewb.generated_at.isoformat() if ewb.generated_at else None,
        "valid_from": ewb.valid_from.isoformat() if ewb.valid_from else None,
        "valid_until": ewb.valid_until.isoformat() if ewb.valid_until else None,
        "is_valid": is_valid,
        "vehicle_number": ewb.vehicle_number,
        "distance_km": ewb.distance_km,
    }
