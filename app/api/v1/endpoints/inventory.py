"""Inventory API endpoints for stock management."""
from typing import Optional, List
import uuid
from math import ceil
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, status, Query, Depends, Body
from sqlalchemy import select, func, and_
from sqlalchemy.orm import selectinload

from app.api.deps import DB, CurrentUser, require_permissions
from app.models.inventory import StockItemStatus, StockMovementType
from app.schemas.inventory import (
    StockItemCreate,
    StockItemUpdate,
    StockItemResponse,
    StockItemDetailResponse,
    StockItemListResponse,
    InventorySummaryResponse,
    InventorySummaryDetail,
    InventorySummaryListResponse,
    InventoryThresholdUpdate,
    StockMovementResponse,
    StockMovementDetail,
    StockMovementListResponse,
    BulkStockReceipt,
    BulkStockReceiptResponse,
    InventoryStats,
    InventoryDashboardStats,
    StockVerificationRequest,
    StockVerificationResponse,
    BulkStockVerificationRequest,
    BulkStockVerificationResponse,
)
from app.services.inventory_service import InventoryService
from app.core.module_decorators import require_module


router = APIRouter(tags=["Inventory"])


# ==================== PUBLIC STOCK VERIFICATION (Phase 2) ====================

@router.post(
    "/verify-stock",
    response_model=StockVerificationResponse,
    summary="Verify product stock availability (Phase 2)",
    description="Real-time stock verification for Add to Cart. No authentication required."
)
async def verify_stock(
    data: StockVerificationRequest,
    db: DB,
):
    """
    Phase 2: Live stock verification for Add to Cart.

    Target response time: 300-500ms

    This endpoint checks real-time stock availability for a product.
    Used by the storefront when a customer adds items to cart.

    No authentication required for public access.
    """
    service = InventoryService(db)

    # Get inventory summary for the product
    summaries, _ = await service.get_inventory_summary(
        product_id=data.product_id,
        warehouse_id=data.warehouse_id,
        skip=0,
        limit=100,
    )

    # Calculate total available across warehouses
    total_available = 0
    primary_warehouse_id = None

    for summary in summaries:
        available = summary.available_quantity - (summary.reserved_quantity or 0)
        if available > 0:
            total_available += available
            if primary_warehouse_id is None:
                primary_warehouse_id = summary.warehouse_id

    in_stock = total_available >= data.quantity

    # Build response
    response = StockVerificationResponse(
        product_id=data.product_id,
        in_stock=in_stock,
        available_quantity=total_available,
        requested_quantity=data.quantity,
        warehouse_id=primary_warehouse_id,
    )

    if in_stock:
        # Calculate delivery estimate based on pincode if provided
        if data.pincode:
            response.delivery_estimate = "2-4 business days"
            response.message = f"In stock! Delivery available to {data.pincode}"
        else:
            response.message = "In stock and ready to ship"
    else:
        if total_available > 0:
            response.message = f"Only {total_available} units available (requested {data.quantity})"
        else:
            response.message = "Currently out of stock"

    return response


@router.post(
    "/verify-stock/bulk",
    response_model=BulkStockVerificationResponse,
    summary="Bulk verify stock for multiple products",
    description="Check stock availability for multiple products at once (e.g., for cart checkout)."
)
async def verify_stock_bulk(
    data: BulkStockVerificationRequest,
    db: DB,
):
    """
    Bulk stock verification for checkout validation.

    Checks stock availability for all items in the cart before checkout.
    """
    service = InventoryService(db)
    results = []
    all_in_stock = True

    for item in data.items:
        # Get inventory summary for each product
        summaries, _ = await service.get_inventory_summary(
            product_id=item.product_id,
            warehouse_id=item.warehouse_id,
            skip=0,
            limit=100,
        )

        # Calculate total available
        total_available = 0
        primary_warehouse_id = None

        for summary in summaries:
            available = summary.available_quantity - (summary.reserved_quantity or 0)
            if available > 0:
                total_available += available
                if primary_warehouse_id is None:
                    primary_warehouse_id = summary.warehouse_id

        in_stock = total_available >= item.quantity
        if not in_stock:
            all_in_stock = False

        results.append(StockVerificationResponse(
            product_id=item.product_id,
            in_stock=in_stock,
            available_quantity=total_available,
            requested_quantity=item.quantity,
            warehouse_id=primary_warehouse_id,
            message="In stock" if in_stock else f"Only {total_available} available",
        ))

    return BulkStockVerificationResponse(
        all_in_stock=all_in_stock,
        items=results,
    )


# ==================== STOCK RESERVATION (Checkout) ====================

from app.services.stock_reservation_service import (
    StockReservationService,
    ReservationItem,
)
from pydantic import BaseModel


class StockReservationRequest(BaseModel):
    """Request to create a stock reservation for checkout."""
    items: List[StockVerificationRequest]
    customer_id: Optional[str] = None
    session_id: Optional[str] = None


class StockReservationResponse(BaseModel):
    """Response from stock reservation."""
    success: bool
    reservation_id: Optional[str] = None
    message: str
    reserved_items: List[dict] = []
    failed_items: List[dict] = []
    expires_in_seconds: int = 600


@router.post(
    "/reserve-stock",
    response_model=StockReservationResponse,
    summary="Reserve stock for checkout",
    description="Create a temporary stock reservation when customer proceeds to checkout. Reservations auto-expire after 10 minutes."
)
@require_module("oms_fulfillment")
async def reserve_stock_for_checkout(
    data: StockReservationRequest,
    db: DB,
):
    """
    Reserve stock for checkout process.

    Call this endpoint when customer clicks "Proceed to Checkout".
    The reservation prevents overselling by temporarily holding stock.

    - Reservation expires after 10 minutes if not confirmed
    - Call /confirm-reservation after successful payment
    - Call /release-reservation if payment fails

    No authentication required (uses session_id for guests).
    """
    service = StockReservationService(db)

    reservation_items = [
        ReservationItem(
            product_id=item.product_id,
            quantity=item.quantity,
            warehouse_id=item.warehouse_id,
        )
        for item in data.items
    ]

    result = await service.create_reservation(
        items=reservation_items,
        customer_id=data.customer_id,
        session_id=data.session_id,
    )

    return StockReservationResponse(
        success=result.success,
        reservation_id=result.reservation_id,
        message=result.message,
        reserved_items=result.reserved_items,
        failed_items=result.failed_items,
        expires_in_seconds=600,
    )


class ConfirmReservationRequest(BaseModel):
    """Request to confirm a reservation after payment."""
    reservation_id: str
    order_id: str


@router.post(
    "/confirm-reservation",
    summary="Confirm stock reservation after payment",
    description="Convert temporary reservation to permanent allocation after successful payment."
)
@require_module("oms_fulfillment")
async def confirm_stock_reservation(
    data: ConfirmReservationRequest,
    db: DB,
):
    """
    Confirm a stock reservation after successful payment.

    This converts the soft reservation to a hard allocation in the database.
    Call this after Razorpay payment success webhook.
    """
    service = StockReservationService(db)
    success = await service.confirm_reservation(
        reservation_id=data.reservation_id,
        order_id=data.order_id,
    )

    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Reservation not found or already processed"
        )

    return {"success": True, "message": "Reservation confirmed and stock allocated"}


class ReleaseReservationRequest(BaseModel):
    """Request to release a reservation."""
    reservation_id: str


@router.post(
    "/release-reservation",
    summary="Release stock reservation",
    description="Release a stock reservation when payment fails or is cancelled."
)
@require_module("oms_fulfillment")
async def release_stock_reservation(
    data: ReleaseReservationRequest,
    db: DB,
):
    """
    Release a stock reservation.

    Call this when:
    - Payment fails
    - Customer cancels checkout
    - Payment times out

    This frees up the reserved stock for other customers.
    """
    service = StockReservationService(db)
    success = await service.release_reservation(data.reservation_id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Reservation not found or already released"
        )

    return {"success": True, "message": "Reservation released"}


@router.get(
    "/reservation/{reservation_id}",
    summary="Get reservation details",
    description="Check the status of a stock reservation."
)
@require_module("oms_fulfillment")
async def get_reservation_status(
    reservation_id: str,
    db: DB,
):
    """Get the current status of a stock reservation."""
    service = StockReservationService(db)
    reservation = await service.get_reservation(reservation_id)

    if not reservation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Reservation not found or expired"
        )

    return reservation


# ==================== WAREHOUSE AVAILABILITY CHECK ====================

class WarehouseAvailabilityItem(BaseModel):
    """Item to check availability for."""
    product_id: str
    quantity: int = 1


class WarehouseAvailabilityRequest(BaseModel):
    """Request to check warehouse availability."""
    pincode: str
    items: List[WarehouseAvailabilityItem]
    payment_mode: Optional[str] = None  # PREPAID or COD


@router.post(
    "/check-warehouse-availability",
    summary="Check inventory availability across warehouses",
    description="Find the best warehouse that can fulfill all items for a given pincode."
)
@require_module("oms_fulfillment")
async def check_warehouse_availability(
    data: WarehouseAvailabilityRequest,
    db: DB,
):
    """
    Check which warehouse can fulfill the order items.

    This endpoint:
    1. Finds warehouses that service the given pincode
    2. Checks inventory availability for each item (including soft reservations)
    3. Returns the best warehouse that can fulfill all items

    Use this before checkout to verify delivery is possible.
    """
    from app.services.allocation_service import AllocationService

    service = AllocationService(db)

    # Convert to items format expected by the service
    items = [
        {"product_id": item.product_id, "quantity": item.quantity}
        for item in data.items
    ]

    result = await service.find_best_warehouse_for_items(
        pincode=data.pincode,
        items=items,
        payment_mode=data.payment_mode
    )

    if result["found"]:
        warehouse = result["warehouse"]
        return {
            "available": True,
            "warehouse": {
                "id": warehouse["warehouse_id"],
                "code": warehouse["warehouse_code"],
                "name": warehouse["warehouse_name"],
                "estimated_days": warehouse["estimated_days"],
                "shipping_cost": warehouse["shipping_cost"]
            },
            "items": warehouse["items"],
            "warehouses_checked": result["warehouses_checked"],
            "message": f"All items available from {warehouse['warehouse_name']}"
        }
    else:
        return {
            "available": False,
            "reason": result["reason"],
            "warehouses_checked": result["warehouses_checked"],
            "all_results": result.get("all_results", []),
            "message": result["reason"]
        }


# ==================== STOCK ITEMS ====================

@router.get(
    "/stock-items",
    dependencies=[Depends(require_permissions("inventory:view"))]
)
async def list_stock_items(
    db: DB,
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=200),
    warehouse_id: Optional[uuid.UUID] = Query(None),
    product_id: Optional[uuid.UUID] = Query(None),
    status: Optional[str] = Query(None),
    serial_number: Optional[str] = Query(None),
    batch_number: Optional[str] = Query(None),
    grn_number: Optional[str] = Query(None, description="Filter by GRN number"),
    item_type: Optional[str] = Query(None, description="Filter by item type: FG, SP, CO, CN, AC"),
    view: str = Query("aggregate", description="View mode: 'aggregate' for inventory_summary, 'serialized' for stock_items"),
):
    """
    Get paginated list of stock items.

    Two view modes:
    - aggregate (default): Returns inventory_summary data (product-level aggregates)
    - serialized: Returns individual stock_items with serial numbers

    Requires: inventory:view permission
    """
    from app.models.inventory import InventorySummary, StockItem
    from app.models.product import Product
    from app.models.warehouse import Warehouse
    from sqlalchemy.orm import selectinload

    skip = (page - 1) * size

    if view == "serialized":
        # Serialized view - query stock_items table with all filters
        query = select(StockItem).options(
            selectinload(StockItem.product),
            selectinload(StockItem.warehouse),
        )

        conditions = []
        if warehouse_id:
            conditions.append(StockItem.warehouse_id == warehouse_id)
        if product_id:
            conditions.append(StockItem.product_id == product_id)
        if status:
            conditions.append(StockItem.status == status)
        if serial_number:
            conditions.append(StockItem.serial_number.ilike(f"%{serial_number}%"))
        if batch_number:
            conditions.append(StockItem.batch_number == batch_number)
        if grn_number:
            conditions.append(StockItem.grn_number.ilike(f"%{grn_number}%"))
        if item_type:
            # Join with Product to filter by item_type
            query = query.join(Product, StockItem.product_id == Product.id)
            conditions.append(Product.item_type == item_type)

        if conditions:
            query = query.where(and_(*conditions))

        # Count query
        count_query = select(func.count(StockItem.id))
        if item_type:
            count_query = count_query.join(Product, StockItem.product_id == Product.id)
        if conditions:
            count_query = count_query.where(and_(*conditions))
        total = await db.scalar(count_query) or 0

        # Paginate
        query = query.order_by(StockItem.created_at.desc()).offset(skip).limit(size)
        result = await db.execute(query)
        items = result.scalars().all()

        return {
            "items": [
                {
                    "id": str(item.id),
                    "product_id": str(item.product_id),
                    "warehouse_id": str(item.warehouse_id),
                    "product": {
                        "id": str(item.product_id),
                        "name": item.product.name if item.product else None,
                        "sku": item.product.sku if item.product else None,
                    },
                    "warehouse": {
                        "id": str(item.warehouse_id),
                        "name": item.warehouse.name if item.warehouse else None,
                        "code": item.warehouse.code if item.warehouse else None,
                    },
                    "serial_number": item.serial_number,
                    "barcode": item.barcode,
                    "batch_number": item.batch_number,
                    "grn_number": item.grn_number,
                    "purchase_order_id": str(item.purchase_order_id) if item.purchase_order_id else None,
                    "quantity": 1,  # Each stock_item is 1 unit
                    "reserved_quantity": 1 if item.status in ["RESERVED", "ALLOCATED"] else 0,
                    "available_quantity": 1 if item.status == "AVAILABLE" else 0,
                    "reorder_level": 0,
                    "status": item.status,
                    "received_date": item.received_date.isoformat() if item.received_date else None,
                    "item_type": item.product.item_type if item.product else None,
                }
                for item in items
            ],
            "total": total,
            "page": page,
            "size": size,
            "pages": ceil(total / size) if total > 0 else 1,
        }

    else:
        # Aggregate view - query inventory_summary table
        query = select(InventorySummary).options(
            selectinload(InventorySummary.product),
            selectinload(InventorySummary.warehouse),
        )

        conditions = []
        if warehouse_id:
            conditions.append(InventorySummary.warehouse_id == warehouse_id)
        if product_id:
            conditions.append(InventorySummary.product_id == product_id)
        if status:
            # Map status to inventory condition
            if status == "LOW_STOCK":
                conditions.append(InventorySummary.available_quantity <= InventorySummary.reorder_level)
            elif status == "OUT_OF_STOCK":
                conditions.append(InventorySummary.available_quantity == 0)
            elif status == "IN_STOCK":
                conditions.append(InventorySummary.available_quantity > 0)
        if item_type:
            # Join with Product to filter by item_type
            query = query.join(Product, InventorySummary.product_id == Product.id)
            conditions.append(Product.item_type == item_type)

        if conditions:
            query = query.where(and_(*conditions))

        # Count
        count_query = select(func.count(InventorySummary.id))
        if item_type:
            count_query = count_query.join(Product, InventorySummary.product_id == Product.id)
        if conditions:
            count_query = count_query.where(and_(*conditions))
        total = await db.scalar(count_query) or 0

        # Paginate
        query = query.order_by(InventorySummary.product_id).offset(skip).limit(size)
        result = await db.execute(query)
        items = result.scalars().all()

        return {
            "items": [
                {
                    "id": str(item.id),
                    "product_id": str(item.product_id),
                    "warehouse_id": str(item.warehouse_id),
                    "product": {
                        "id": str(item.product_id),
                        "name": item.product.name if item.product else None,
                        "sku": item.product.sku if item.product else None,
                        "item_type": item.product.item_type if item.product else None,
                    },
                    "warehouse": {
                        "id": str(item.warehouse_id),
                        "name": item.warehouse.name if item.warehouse else None,
                        "code": item.warehouse.code if item.warehouse else None,
                    },
                    "serial_number": None,  # Aggregate view doesn't have serials
                    "batch_number": None,
                    "quantity": item.total_quantity,
                    "reserved_quantity": item.reserved_quantity,
                    "available_quantity": item.available_quantity,
                    "reorder_level": item.reorder_level,
                    "status": "AVAILABLE" if item.available_quantity > 0 else "OUT_OF_STOCK",
                    "item_type": item.product.item_type if item.product else None,
                }
                for item in items
            ],
            "total": total,
            "page": page,
            "size": size,
            "pages": ceil(total / size) if total > 0 else 1,
        }


@router.get(
    "/stock-items/{item_id}",
    response_model=StockItemDetailResponse,
    dependencies=[Depends(require_permissions("inventory:view"))]
)
async def get_stock_item(
    item_id: uuid.UUID,
    db: DB,
):
    """Get stock item by ID."""
    service = InventoryService(db)
    item = await service.get_stock_item_by_id(item_id)

    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Stock item not found"
        )

    response = StockItemDetailResponse.model_validate(item)
    if item.product:
        response.product_name = item.product.name
        response.product_sku = item.product.sku
    if item.warehouse:
        response.warehouse_name = item.warehouse.name
        response.warehouse_code = item.warehouse.code

    return response


@router.get(
    "/stock-items/serial/{serial_number}",
    response_model=StockItemDetailResponse,
    dependencies=[Depends(require_permissions("inventory:view"))]
)
async def get_stock_item_by_serial(
    serial_number: str,
    db: DB,
):
    """Get stock item by serial number."""
    service = InventoryService(db)
    item = await service.get_stock_item_by_serial(serial_number)

    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Stock item not found"
        )

    response = StockItemDetailResponse.model_validate(item)
    if item.product:
        response.product_name = item.product.name
        response.product_sku = item.product.sku
    if item.warehouse:
        response.warehouse_name = item.warehouse.name
        response.warehouse_code = item.warehouse.code

    return response


@router.post(
    "/stock-items",
    response_model=StockItemResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permissions("inventory:create"))]
)
async def create_stock_item(
    data: StockItemCreate,
    db: DB,
    current_user: CurrentUser,
):
    """
    Create a single stock item.
    Requires: inventory:create permission
    """
    service = InventoryService(db)

    # Check for duplicate serial number
    if data.serial_number:
        existing = await service.get_stock_item_by_serial(data.serial_number)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Serial number already exists"
            )

    item = await service.create_stock_item(data.model_dump(), created_by=current_user.id)
    return StockItemResponse.model_validate(item)


@router.post(
    "/stock-items/bulk-receive",
    response_model=BulkStockReceiptResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permissions("inventory:create"))]
)
async def bulk_receive_stock(
    data: BulkStockReceipt,
    db: DB,
    current_user: CurrentUser,
):
    """
    Bulk receive stock items (GRN).
    Requires: inventory:create permission
    """
    service = InventoryService(db)

    items = await service.bulk_receive_stock(
        warehouse_id=data.warehouse_id,
        grn_number=data.grn_number,
        items=[item.model_dump() for item in data.items],
        purchase_order_id=data.purchase_order_id,
        vendor_id=data.vendor_id,
        created_by=current_user.id,
    )

    return BulkStockReceiptResponse(
        message=f"Successfully received {len(items)} stock items",
        grn_number=data.grn_number,
        items_count=len(items),
    )


@router.put(
    "/stock-items/{item_id}",
    response_model=StockItemResponse,
    dependencies=[Depends(require_permissions("inventory:update"))]
)
async def update_stock_item(
    item_id: uuid.UUID,
    data: StockItemUpdate,
    db: DB,
    current_user: CurrentUser,
):
    """
    Update a stock item.
    Requires: inventory:update permission
    """
    service = InventoryService(db)
    item = await service.get_stock_item_by_id(item_id)

    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Stock item not found"
        )

    # Update fields
    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        if hasattr(item, key):
            setattr(item, key, value)

    await db.commit()
    await db.refresh(item)
    return StockItemResponse.model_validate(item)


@router.delete(
    "/stock-items/{item_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_permissions("inventory:delete"))]
)
async def delete_stock_item(
    item_id: uuid.UUID,
    db: DB,
    current_user: CurrentUser,
):
    """
    Delete a stock item (soft delete - marks as DISPOSED).
    Requires: inventory:delete permission
    """
    service = InventoryService(db)
    item = await service.get_stock_item_by_id(item_id)

    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Stock item not found"
        )

    # Check if item is allocated to an order
    if item.order_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete stock item that is allocated to an order"
        )

    # Soft delete - mark as DISPOSED
    item.status = StockItemStatus.DISPOSED.value
    item.notes = f"Deleted by user on {datetime.now(timezone.utc).isoformat()}"

    await db.commit()
    return None


# ==================== INVENTORY SUMMARY ====================

@router.get(
    "/summary",
    response_model=InventorySummaryListResponse,
    dependencies=[Depends(require_permissions("inventory:view"))]
)
async def get_inventory_summary(
    db: DB,
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=200),
    warehouse_id: Optional[uuid.UUID] = Query(None),
    product_id: Optional[uuid.UUID] = Query(None),
    low_stock_only: bool = Query(False),
    out_of_stock_only: bool = Query(False),
):
    """
    Get inventory summary per product per warehouse.
    Requires: inventory:view permission
    """
    service = InventoryService(db)
    skip = (page - 1) * size

    summaries, total = await service.get_inventory_summary(
        warehouse_id=warehouse_id,
        product_id=product_id,
        low_stock_only=low_stock_only,
        out_of_stock_only=out_of_stock_only,
        skip=skip,
        limit=size,
    )

    items = []
    for s in summaries:
        detail = InventorySummaryDetail.model_validate(s)
        if s.product:
            detail.product_name = s.product.name
            detail.product_sku = s.product.sku
        if s.warehouse:
            detail.warehouse_name = s.warehouse.name
            detail.warehouse_code = s.warehouse.code
        items.append(detail)

    return InventorySummaryListResponse(
        items=items,
        total=total,
        page=page,
        size=size,
        pages=ceil(total / size) if total > 0 else 1,
    )


@router.get(
    "/low-stock",
    response_model=InventorySummaryListResponse,
    dependencies=[Depends(require_permissions("inventory:view"))]
)
async def get_low_stock_items(
    db: DB,
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=200),
    warehouse_id: Optional[uuid.UUID] = Query(None),
):
    """Get items below reorder level."""
    service = InventoryService(db)
    skip = (page - 1) * size

    summaries, total = await service.get_inventory_summary(
        warehouse_id=warehouse_id,
        low_stock_only=True,
        skip=skip,
        limit=size,
    )

    items = []
    for s in summaries:
        detail = InventorySummaryDetail.model_validate(s)
        if s.product:
            detail.product_name = s.product.name
            detail.product_sku = s.product.sku
        if s.warehouse:
            detail.warehouse_name = s.warehouse.name
            detail.warehouse_code = s.warehouse.code
        items.append(detail)

    return InventorySummaryListResponse(
        items=items,
        total=total,
        page=page,
        size=size,
        pages=ceil(total / size) if total > 0 else 1,
    )


# ==================== STOCK MOVEMENTS ====================

@router.get(
    "/movements",
    response_model=StockMovementListResponse,
    dependencies=[Depends(require_permissions("inventory:view"))]
)
async def get_stock_movements(
    db: DB,
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=200),
    warehouse_id: Optional[uuid.UUID] = Query(None),
    product_id: Optional[uuid.UUID] = Query(None),
    movement_type: Optional[StockMovementType] = Query(None),
    date_from: Optional[datetime] = Query(None),
    date_to: Optional[datetime] = Query(None),
):
    """
    Get stock movement history.
    Requires: inventory:view permission
    """
    service = InventoryService(db)
    skip = (page - 1) * size

    movements, total = await service.get_stock_movements(
        warehouse_id=warehouse_id,
        product_id=product_id,
        movement_type=movement_type,
        date_from=date_from,
        date_to=date_to,
        skip=skip,
        limit=size,
    )

    items = []
    for m in movements:
        detail = StockMovementDetail.model_validate(m)
        if m.product:
            detail.product_name = m.product.name
            detail.product_sku = m.product.sku
        if m.warehouse:
            detail.warehouse_name = m.warehouse.name
        if m.stock_item:
            detail.serial_number = m.stock_item.serial_number
        items.append(detail)

    return StockMovementListResponse(
        items=items,
        total=total,
        page=page,
        size=size,
        pages=ceil(total / size) if total > 0 else 1,
    )


# ==================== STATS ====================

@router.get(
    "/stats",
    response_model=InventoryStats,
    dependencies=[Depends(require_permissions("inventory:view"))]
)
async def get_inventory_stats(
    db: DB,
    warehouse_id: Optional[uuid.UUID] = Query(None),
):
    """
    Get inventory statistics for Stock Items page.
    Returns: total_skus, in_stock, low_stock, out_of_stock
    Requires: inventory:view permission
    """
    service = InventoryService(db)
    stats = await service.get_inventory_stats(warehouse_id=warehouse_id)
    return stats


@router.get(
    "/dashboard-stats",
    response_model=InventoryDashboardStats,
    dependencies=[Depends(require_permissions("inventory:view"))]
)
async def get_inventory_dashboard_stats(
    db: DB,
    warehouse_id: Optional[uuid.UUID] = Query(None),
):
    """
    Get inventory statistics for Dashboard Summary page.
    Returns: total_items, total_warehouses, pending_transfers, low_stock_items
    Requires: inventory:view permission
    """
    service = InventoryService(db)
    stats = await service.get_dashboard_stats(warehouse_id=warehouse_id)
    return InventoryDashboardStats(**stats)


# ==================== STOCK ALERTS ====================

@router.post(
    "/alerts/send",
    dependencies=[Depends(require_permissions("inventory:update"))]
)
async def send_stock_alerts(
    db: DB,
    current_user: CurrentUser,
    warehouse_id: Optional[uuid.UUID] = Query(None, description="Filter by warehouse"),
    manager_email: str = Query("inventory@ilms.ai", description="Email for alerts"),
    manager_phone: Optional[str] = Query(None, description="Phone for SMS alerts"),
):
    """
    Check inventory levels and send notifications for low/out of stock items.

    This endpoint can be called:
    - Manually by inventory managers
    - Automatically via scheduled jobs/cron

    Requires: inventory:update permission
    """
    from app.services.notification_service import check_and_send_stock_alerts

    result = await check_and_send_stock_alerts(
        db=db,
        warehouse_id=str(warehouse_id) if warehouse_id else None,
        manager_email=manager_email,
        manager_phone=manager_phone,
    )

    return {
        "success": True,
        "message": "Stock alert check completed",
        "alerts_sent": result["alerts_sent"],
        "total_items_checked": result["total_items_checked"],
    }


@router.get(
    "/alerts/preview",
    dependencies=[Depends(require_permissions("inventory:view"))]
)
async def preview_stock_alerts(
    db: DB,
    warehouse_id: Optional[uuid.UUID] = Query(None),
):
    """
    Preview which items would trigger alerts without actually sending notifications.

    Returns list of items that are low stock or out of stock.
    Requires: inventory:view permission
    """
    from app.models.inventory import InventorySummary
    from app.models.product import Product
    from app.models.warehouse import Warehouse
    from sqlalchemy.orm import selectinload

    query = select(InventorySummary).options(
        selectinload(InventorySummary.product),
        selectinload(InventorySummary.warehouse),
    ).where(
        InventorySummary.available_quantity <= InventorySummary.reorder_level
    )

    if warehouse_id:
        query = query.where(InventorySummary.warehouse_id == warehouse_id)

    query = query.order_by(InventorySummary.available_quantity.asc())

    result = await db.execute(query)
    items = result.scalars().unique().all()

    alerts = []
    for item in items:
        alert_type = "out_of_stock" if item.available_quantity == 0 else "low_stock"
        alerts.append({
            "product_id": str(item.product_id),
            "product_name": item.product.name if item.product else "Unknown",
            "product_sku": item.product.sku if item.product else "N/A",
            "warehouse_id": str(item.warehouse_id),
            "warehouse_name": item.warehouse.name if item.warehouse else "Unknown",
            "current_quantity": item.available_quantity,
            "reorder_level": item.reorder_level or 10,
            "alert_type": alert_type,
        })

    return {
        "total_alerts": len(alerts),
        "out_of_stock_count": len([a for a in alerts if a["alert_type"] == "out_of_stock"]),
        "low_stock_count": len([a for a in alerts if a["alert_type"] == "low_stock"]),
        "items": alerts,
    }
