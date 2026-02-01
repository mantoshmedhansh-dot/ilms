"""WMS (Warehouse Management System) API endpoints."""
from typing import Optional
import uuid
from math import ceil
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, status, Query, Depends
from sqlalchemy import select, func, and_, or_
from sqlalchemy.orm import selectinload

from app.api.deps import DB, CurrentUser, require_permissions
from app.models.wms import WarehouseZone, WarehouseBin, PutAwayRule, ZoneType, BinType
from app.models.warehouse import Warehouse
from app.models.inventory import StockItem
from app.models.product import Product
from app.schemas.wms import (
    ZoneCreate,
    ZoneUpdate,
    ZoneResponse,
    ZoneBrief,
    ZoneListResponse,
    BinCreate,
    BinBulkCreate,
    BinUpdate,
    BinResponse,
    BinBrief,
    BinListResponse,
    BinStatsResponse,
    BinEnquiryRequest,
    BinEnquiryResponse,
    BinContentItem,
    PutAwayRuleCreate,
    PutAwayRuleUpdate,
    PutAwayRuleResponse,
    PutAwayRuleListResponse,
    PutAwayRuleStatsResponse,
    PutAwaySuggestRequest,
    PutAwaySuggestResponse,
    SuggestedBin,
    PutAwayExecuteRequest,
    PutAwayExecuteResponse,
    InventoryMoveRequest,
    InventoryMoveResponse,
)


router = APIRouter()


# ==================== ZONE CRUD ====================

@router.get(
    "/zones",
    response_model=ZoneListResponse,
    dependencies=[Depends(require_permissions("inventory:view"))]
)
async def list_zones(
    db: DB,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    warehouse_id: Optional[uuid.UUID] = Query(None),
    zone_type: Optional[ZoneType] = Query(None),
    is_active: bool = Query(True),
    search: Optional[str] = Query(None),
):
    """Get paginated list of warehouse zones."""
    query = select(WarehouseZone).where(WarehouseZone.is_active == is_active)
    count_query = select(func.count(WarehouseZone.id)).where(WarehouseZone.is_active == is_active)

    if warehouse_id:
        query = query.where(WarehouseZone.warehouse_id == warehouse_id)
        count_query = count_query.where(WarehouseZone.warehouse_id == warehouse_id)

    if zone_type:
        query = query.where(WarehouseZone.zone_type == zone_type)
        count_query = count_query.where(WarehouseZone.zone_type == zone_type)

    if search:
        search_filter = or_(
            WarehouseZone.zone_code.ilike(f"%{search}%"),
            WarehouseZone.zone_name.ilike(f"%{search}%"),
        )
        query = query.where(search_filter)
        count_query = count_query.where(search_filter)

    # Get total count
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # Get paginated results
    offset = (page - 1) * size
    query = query.order_by(WarehouseZone.sort_order.asc(), WarehouseZone.zone_code.asc())
    query = query.offset(offset).limit(size)

    result = await db.execute(query)
    zones = result.scalars().all()

    return ZoneListResponse(
        items=[ZoneResponse.model_validate(z) for z in zones],
        total=total,
        page=page,
        size=size,
        pages=ceil(total / size) if total > 0 else 1,
    )


@router.get(
    "/zones/dropdown",
    response_model=list[ZoneBrief],
    dependencies=[Depends(require_permissions("inventory:view"))]
)
async def get_zones_dropdown(
    db: DB,
    warehouse_id: uuid.UUID,
    zone_type: Optional[ZoneType] = Query(None),
    is_active: bool = Query(True),
):
    """Get zones for dropdown selection."""
    query = select(WarehouseZone).where(
        and_(
            WarehouseZone.warehouse_id == warehouse_id,
            WarehouseZone.is_active == is_active,
        )
    )

    if zone_type:
        query = query.where(WarehouseZone.zone_type == zone_type)

    query = query.order_by(WarehouseZone.sort_order.asc())
    query = query.limit(100)

    result = await db.execute(query)
    zones = result.scalars().all()

    return [ZoneBrief.model_validate(z) for z in zones]


@router.get(
    "/zones/{zone_id}",
    response_model=ZoneResponse,
    dependencies=[Depends(require_permissions("inventory:view"))]
)
async def get_zone(
    zone_id: uuid.UUID,
    db: DB,
):
    """Get zone by ID."""
    query = select(WarehouseZone).where(WarehouseZone.id == zone_id)
    result = await db.execute(query)
    zone = result.scalar_one_or_none()

    if not zone:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Zone not found"
        )

    return ZoneResponse.model_validate(zone)


@router.post(
    "/zones",
    response_model=ZoneResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permissions("inventory:create"))]
)
async def create_zone(
    data: ZoneCreate,
    db: DB,
    current_user: CurrentUser,
):
    """Create a new warehouse zone."""
    # Verify warehouse exists
    wh_query = select(Warehouse).where(Warehouse.id == data.warehouse_id)
    wh_result = await db.execute(wh_query)
    if not wh_result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Warehouse not found"
        )

    # Check for duplicate zone code in warehouse
    existing_query = select(WarehouseZone).where(
        and_(
            WarehouseZone.warehouse_id == data.warehouse_id,
            WarehouseZone.zone_code == data.zone_code.upper(),
        )
    )
    existing_result = await db.execute(existing_query)
    if existing_result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Zone with this code already exists in the warehouse"
        )

    zone = WarehouseZone(
        **data.model_dump(),
        zone_code=data.zone_code.upper(),
    )

    db.add(zone)
    await db.commit()
    await db.refresh(zone)

    return ZoneResponse.model_validate(zone)


@router.put(
    "/zones/{zone_id}",
    response_model=ZoneResponse,
    dependencies=[Depends(require_permissions("inventory:update"))]
)
async def update_zone(
    zone_id: uuid.UUID,
    data: ZoneUpdate,
    db: DB,
    current_user: CurrentUser,
):
    """Update a warehouse zone."""
    query = select(WarehouseZone).where(WarehouseZone.id == zone_id)
    result = await db.execute(query)
    zone = result.scalar_one_or_none()

    if not zone:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Zone not found"
        )

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(zone, field, value)

    await db.commit()
    await db.refresh(zone)

    return ZoneResponse.model_validate(zone)


@router.delete(
    "/zones/{zone_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_permissions("inventory:delete"))]
)
async def deactivate_zone(
    zone_id: uuid.UUID,
    db: DB,
    current_user: CurrentUser,
):
    """Deactivate a zone (soft delete)."""
    query = select(WarehouseZone).where(WarehouseZone.id == zone_id)
    result = await db.execute(query)
    zone = result.scalar_one_or_none()

    if not zone:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Zone not found"
        )

    zone.is_active = False
    await db.commit()


# ==================== BIN CRUD ====================

@router.get(
    "/bins/stats",
    response_model=BinStatsResponse,
    dependencies=[Depends(require_permissions("inventory:view"))]
)
async def get_bin_stats(db: DB):
    """Get warehouse bin statistics."""
    # Total bins
    total_result = await db.execute(
        select(func.count(WarehouseBin.id)).where(WarehouseBin.is_active == True)
    )
    total_bins = total_result.scalar() or 0

    # Reserved bins
    reserved_result = await db.execute(
        select(func.count(WarehouseBin.id)).where(
            and_(
                WarehouseBin.is_active == True,
                WarehouseBin.is_reserved == True
            )
        )
    )
    reserved_bins = reserved_result.scalar() or 0

    # Occupied bins (bins with stock items)
    occupied_result = await db.execute(
        select(func.count(func.distinct(StockItem.bin_id))).where(
            StockItem.bin_id.isnot(None)
        )
    )
    occupied_bins = occupied_result.scalar() or 0

    # Available = Total - Reserved - Occupied (but not double counting)
    available_bins = max(0, total_bins - reserved_bins - occupied_bins + min(reserved_bins, occupied_bins))

    return BinStatsResponse(
        total_bins=total_bins,
        available_bins=available_bins,
        occupied_bins=occupied_bins,
        reserved_bins=reserved_bins,
    )


@router.get(
    "/bins",
    response_model=BinListResponse,
    dependencies=[Depends(require_permissions("inventory:view"))]
)
async def list_bins(
    db: DB,
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=200),
    warehouse_id: Optional[uuid.UUID] = Query(None),
    zone_id: Optional[uuid.UUID] = Query(None),
    bin_type: Optional[BinType] = Query(None),
    is_active: bool = Query(True),
    only_available: bool = Query(False),
    search: Optional[str] = Query(None),
):
    """Get paginated list of warehouse bins."""
    query = select(WarehouseBin).where(WarehouseBin.is_active == is_active)
    count_query = select(func.count(WarehouseBin.id)).where(WarehouseBin.is_active == is_active)

    if warehouse_id:
        query = query.where(WarehouseBin.warehouse_id == warehouse_id)
        count_query = count_query.where(WarehouseBin.warehouse_id == warehouse_id)

    if zone_id:
        query = query.where(WarehouseBin.zone_id == zone_id)
        count_query = count_query.where(WarehouseBin.zone_id == zone_id)

    if bin_type:
        query = query.where(WarehouseBin.bin_type == bin_type)
        count_query = count_query.where(WarehouseBin.bin_type == bin_type)

    if only_available:
        query = query.where(
            and_(
                WarehouseBin.is_reserved == False,
                WarehouseBin.is_receivable == True,
            )
        )
        count_query = count_query.where(
            and_(
                WarehouseBin.is_reserved == False,
                WarehouseBin.is_receivable == True,
            )
        )

    if search:
        search_filter = or_(
            WarehouseBin.bin_code.ilike(f"%{search}%"),
            WarehouseBin.barcode.ilike(f"%{search}%"),
        )
        query = query.where(search_filter)
        count_query = count_query.where(search_filter)

    # Get total count
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # Get paginated results
    offset = (page - 1) * size
    query = query.options(selectinload(WarehouseBin.zone))
    query = query.order_by(WarehouseBin.pick_sequence.asc(), WarehouseBin.bin_code.asc())
    query = query.offset(offset).limit(size)

    result = await db.execute(query)
    bins = result.scalars().all()

    return BinListResponse(
        items=[BinResponse.model_validate(b) for b in bins],
        total=total,
        page=page,
        size=size,
        pages=ceil(total / size) if total > 0 else 1,
    )


@router.get(
    "/bins/dropdown",
    response_model=list[BinBrief],
    dependencies=[Depends(require_permissions("inventory:view"))]
)
async def get_bins_dropdown(
    db: DB,
    warehouse_id: uuid.UUID,
    zone_id: Optional[uuid.UUID] = Query(None),
    only_available: bool = Query(False),
):
    """Get bins for dropdown selection."""
    query = select(WarehouseBin).where(
        and_(
            WarehouseBin.warehouse_id == warehouse_id,
            WarehouseBin.is_active == True,
        )
    )

    if zone_id:
        query = query.where(WarehouseBin.zone_id == zone_id)

    if only_available:
        query = query.where(
            and_(
                WarehouseBin.is_reserved == False,
                WarehouseBin.is_receivable == True,
            )
        )

    query = query.order_by(WarehouseBin.pick_sequence.asc())
    query = query.limit(200)

    result = await db.execute(query)
    bins = result.scalars().all()

    return [BinBrief.model_validate(b) for b in bins]


@router.get(
    "/bins/{bin_id}",
    response_model=BinResponse,
    dependencies=[Depends(require_permissions("inventory:view"))]
)
async def get_bin(
    bin_id: uuid.UUID,
    db: DB,
):
    """Get bin by ID."""
    query = select(WarehouseBin).where(WarehouseBin.id == bin_id)
    query = query.options(selectinload(WarehouseBin.zone))
    result = await db.execute(query)
    bin = result.scalar_one_or_none()

    if not bin:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bin not found"
        )

    return BinResponse.model_validate(bin)


@router.post(
    "/bins",
    response_model=BinResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permissions("inventory:create"))]
)
async def create_bin(
    data: BinCreate,
    db: DB,
    current_user: CurrentUser,
):
    """Create a new warehouse bin."""
    # Verify warehouse exists
    wh_query = select(Warehouse).where(Warehouse.id == data.warehouse_id)
    wh_result = await db.execute(wh_query)
    if not wh_result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Warehouse not found"
        )

    # Check for duplicate bin code in warehouse
    existing_query = select(WarehouseBin).where(
        and_(
            WarehouseBin.warehouse_id == data.warehouse_id,
            WarehouseBin.bin_code == data.bin_code.upper(),
        )
    )
    existing_result = await db.execute(existing_query)
    if existing_result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Bin with this code already exists in the warehouse"
        )

    bin = WarehouseBin(
        **data.model_dump(),
        bin_code=data.bin_code.upper(),
        barcode=data.barcode or data.bin_code.upper(),
    )

    db.add(bin)
    await db.commit()
    await db.refresh(bin)

    return BinResponse.model_validate(bin)


@router.post(
    "/bins/bulk",
    response_model=list[BinBrief],
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permissions("inventory:create"))]
)
async def create_bins_bulk(
    data: BinBulkCreate,
    db: DB,
    current_user: CurrentUser,
):
    """
    Bulk create warehouse bins.
    Creates bins for all combinations of aisle-rack-shelf.
    Example: A1-01-01, A1-01-02, ..., A1-05-04
    """
    # Verify warehouse exists
    wh_query = select(Warehouse).where(Warehouse.id == data.warehouse_id)
    wh_result = await db.execute(wh_query)
    if not wh_result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Warehouse not found"
        )

    created_bins = []
    pick_sequence = 0

    # Generate aisle range (A-Z or A-AA etc.)
    aisle_start = ord(data.aisle_start.upper())
    aisle_end = ord(data.aisle_end.upper())

    for aisle_ord in range(aisle_start, aisle_end + 1):
        aisle = chr(aisle_ord)
        for rack in range(data.rack_start, data.rack_end + 1):
            for shelf in range(data.shelf_start, data.shelf_end + 1):
                bin_code = f"{data.prefix}-{aisle}{rack:02d}-{shelf:02d}"

                # Check if bin exists
                existing_query = select(WarehouseBin).where(
                    and_(
                        WarehouseBin.warehouse_id == data.warehouse_id,
                        WarehouseBin.bin_code == bin_code,
                    )
                )
                existing_result = await db.execute(existing_query)
                if existing_result.scalar_one_or_none():
                    continue  # Skip existing bins

                bin = WarehouseBin(
                    warehouse_id=data.warehouse_id,
                    zone_id=data.zone_id,
                    bin_code=bin_code,
                    barcode=bin_code,
                    aisle=aisle,
                    rack=f"{rack:02d}",
                    shelf=f"{shelf:02d}",
                    bin_type=data.bin_type,
                    max_capacity=data.max_capacity,
                    pick_sequence=pick_sequence,
                )
                db.add(bin)
                created_bins.append(bin)
                pick_sequence += 1

    await db.commit()

    for bin in created_bins:
        await db.refresh(bin)

    return [BinBrief.model_validate(b) for b in created_bins]


@router.put(
    "/bins/{bin_id}",
    response_model=BinResponse,
    dependencies=[Depends(require_permissions("inventory:update"))]
)
async def update_bin(
    bin_id: uuid.UUID,
    data: BinUpdate,
    db: DB,
    current_user: CurrentUser,
):
    """Update a warehouse bin."""
    query = select(WarehouseBin).where(WarehouseBin.id == bin_id)
    result = await db.execute(query)
    bin = result.scalar_one_or_none()

    if not bin:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bin not found"
        )

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(bin, field, value)

    await db.commit()
    await db.refresh(bin)

    return BinResponse.model_validate(bin)


@router.delete(
    "/bins/{bin_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_permissions("inventory:delete"))]
)
async def deactivate_bin(
    bin_id: uuid.UUID,
    db: DB,
    current_user: CurrentUser,
):
    """Deactivate a bin (soft delete)."""
    query = select(WarehouseBin).where(WarehouseBin.id == bin_id)
    result = await db.execute(query)
    bin = result.scalar_one_or_none()

    if not bin:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bin not found"
        )

    # Check if bin has items
    if bin.current_items > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot deactivate bin with items. Move items first."
        )

    bin.is_active = False
    await db.commit()


# ==================== BIN ENQUIRY ====================

@router.post(
    "/bins/enquiry",
    response_model=BinEnquiryResponse,
    dependencies=[Depends(require_permissions("inventory:view"))]
)
async def bin_enquiry(
    data: BinEnquiryRequest,
    db: DB,
):
    """
    Bin enquiry - get bin details and contents.
    Can search by bin_code or barcode.
    """
    query = select(WarehouseBin).where(WarehouseBin.warehouse_id == data.warehouse_id)

    if data.bin_code:
        query = query.where(WarehouseBin.bin_code.ilike(f"%{data.bin_code}%"))
    elif data.barcode:
        query = query.where(WarehouseBin.barcode == data.barcode)
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Provide bin_code or barcode"
        )

    query = query.options(selectinload(WarehouseBin.zone))
    result = await db.execute(query)
    bin = result.scalar_one_or_none()

    if not bin:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bin not found"
        )

    # Get bin contents
    contents_query = (
        select(StockItem)
        .where(StockItem.bin_id == bin.id)
        .options(selectinload(StockItem.product))
    )
    contents_result = await db.execute(contents_query)
    stock_items = contents_result.scalars().all()

    contents = []
    for item in stock_items:
        contents.append(BinContentItem(
            stock_item_id=item.id,
            serial_number=item.serial_number,
            product_id=item.product_id,
            product_name=item.product.name if item.product else "Unknown",
            sku=item.sku,
            variant_name=None,
            status=item.status if item.status else "unknown",
            received_date=item.received_date,
        ))

    return BinEnquiryResponse(
        bin=BinResponse.model_validate(bin),
        contents=contents,
    )


# ==================== PUTAWAY RULES ====================

@router.get(
    "/putaway-rules/stats",
    response_model=PutAwayRuleStatsResponse,
    dependencies=[Depends(require_permissions("inventory:view"))]
)
async def get_putaway_rule_stats(db: DB):
    """Get putaway rule statistics."""
    # Total rules
    total_result = await db.execute(
        select(func.count(PutAwayRule.id))
    )
    total_rules = total_result.scalar() or 0

    # Active rules
    active_result = await db.execute(
        select(func.count(PutAwayRule.id)).where(PutAwayRule.is_active == True)
    )
    active_rules = active_result.scalar() or 0

    # For now, return placeholder values for processed items
    # These would need proper tracking tables to implement fully
    return PutAwayRuleStatsResponse(
        total_rules=total_rules,
        active_rules=active_rules,
        items_processed_today=0,
        unmatched_items=0,
    )


@router.get(
    "/putaway-rules",
    response_model=PutAwayRuleListResponse,
    dependencies=[Depends(require_permissions("inventory:view"))]
)
async def list_putaway_rules(
    db: DB,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    warehouse_id: Optional[uuid.UUID] = Query(None),
    is_active: bool = Query(True),
):
    """Get paginated list of putaway rules."""
    query = select(PutAwayRule).where(PutAwayRule.is_active == is_active)
    count_query = select(func.count(PutAwayRule.id)).where(PutAwayRule.is_active == is_active)

    if warehouse_id:
        query = query.where(PutAwayRule.warehouse_id == warehouse_id)
        count_query = count_query.where(PutAwayRule.warehouse_id == warehouse_id)

    # Get total count
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # Get paginated results
    offset = (page - 1) * size
    query = query.options(selectinload(PutAwayRule.target_zone))
    query = query.order_by(PutAwayRule.priority.asc())
    query = query.offset(offset).limit(size)

    result = await db.execute(query)
    rules = result.scalars().all()

    return PutAwayRuleListResponse(
        items=[PutAwayRuleResponse.model_validate(r) for r in rules],
        total=total,
        page=page,
        size=size,
        pages=ceil(total / size) if total > 0 else 1,
    )


@router.post(
    "/putaway-rules",
    response_model=PutAwayRuleResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permissions("inventory:create"))]
)
async def create_putaway_rule(
    data: PutAwayRuleCreate,
    db: DB,
    current_user: CurrentUser,
):
    """Create a new putaway rule."""
    rule = PutAwayRule(**data.model_dump())

    db.add(rule)
    await db.commit()
    await db.refresh(rule)

    return PutAwayRuleResponse.model_validate(rule)


@router.put(
    "/putaway-rules/{rule_id}",
    response_model=PutAwayRuleResponse,
    dependencies=[Depends(require_permissions("inventory:update"))]
)
async def update_putaway_rule(
    rule_id: uuid.UUID,
    data: PutAwayRuleUpdate,
    db: DB,
    current_user: CurrentUser,
):
    """Update a putaway rule."""
    query = select(PutAwayRule).where(PutAwayRule.id == rule_id)
    result = await db.execute(query)
    rule = result.scalar_one_or_none()

    if not rule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="PutAway rule not found"
        )

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(rule, field, value)

    await db.commit()
    await db.refresh(rule)

    return PutAwayRuleResponse.model_validate(rule)


@router.delete(
    "/putaway-rules/{rule_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_permissions("inventory:delete"))]
)
async def delete_putaway_rule(
    rule_id: uuid.UUID,
    db: DB,
    current_user: CurrentUser,
):
    """Delete a putaway rule."""
    query = select(PutAwayRule).where(PutAwayRule.id == rule_id)
    result = await db.execute(query)
    rule = result.scalar_one_or_none()

    if not rule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="PutAway rule not found"
        )

    await db.delete(rule)
    await db.commit()


# ==================== PUTAWAY OPERATIONS ====================

@router.post(
    "/putaway/suggest",
    response_model=PutAwaySuggestResponse,
    dependencies=[Depends(require_permissions("inventory:view"))]
)
async def suggest_putaway(
    data: PutAwaySuggestRequest,
    db: DB,
):
    """
    Suggest bins for putaway based on rules.
    Returns list of suggested bins in priority order.
    """
    # Get product info
    product_query = select(Product).where(Product.id == data.product_id)
    product_result = await db.execute(product_query)
    product = product_result.scalar_one_or_none()

    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found"
        )

    # Find matching putaway rule
    rule_query = (
        select(PutAwayRule)
        .where(
            and_(
                PutAwayRule.warehouse_id == data.warehouse_id,
                PutAwayRule.is_active == True,
                or_(
                    PutAwayRule.product_id == data.product_id,
                    PutAwayRule.category_id == product.category_id,
                    PutAwayRule.brand_id == product.brand_id,
                    and_(
                        PutAwayRule.product_id.is_(None),
                        PutAwayRule.category_id.is_(None),
                        PutAwayRule.brand_id.is_(None),
                    )
                )
            )
        )
        .options(selectinload(PutAwayRule.target_zone))
        .order_by(PutAwayRule.priority.asc())
    )
    rule_result = await db.execute(rule_query)
    matched_rule = rule_result.scalars().first()

    # Find available bins
    bin_query = (
        select(WarehouseBin)
        .where(
            and_(
                WarehouseBin.warehouse_id == data.warehouse_id,
                WarehouseBin.is_active == True,
                WarehouseBin.is_receivable == True,
                WarehouseBin.is_reserved == False,
            )
        )
        .options(selectinload(WarehouseBin.zone))
    )

    # Filter by rule's target zone if exists
    if matched_rule:
        bin_query = bin_query.where(WarehouseBin.zone_id == matched_rule.target_zone_id)
        if matched_rule.target_bin_pattern:
            bin_query = bin_query.where(
                WarehouseBin.bin_code.ilike(matched_rule.target_bin_pattern.replace("*", "%"))
            )

    # Order by pick sequence and available capacity
    bin_query = bin_query.order_by(WarehouseBin.pick_sequence.asc())
    bin_query = bin_query.limit(10)

    bin_result = await db.execute(bin_query)
    bins = bin_result.scalars().all()

    suggested = []
    for bin in bins:
        # Skip full bins
        if bin.is_full:
            continue
        # Check if has capacity for requested quantity
        available = bin.available_capacity
        if available is not None and available < data.quantity:
            continue

        suggested.append(SuggestedBin(
            bin=BinBrief.model_validate(bin),
            zone=ZoneBrief.model_validate(bin.zone) if bin.zone else None,
            available_capacity=available,
            pick_sequence=bin.pick_sequence,
        ))

    return PutAwaySuggestResponse(
        suggested_bins=suggested,
        matched_rule=PutAwayRuleResponse.model_validate(matched_rule) if matched_rule else None,
    )


@router.post(
    "/putaway/execute",
    response_model=PutAwayExecuteResponse,
    dependencies=[Depends(require_permissions("inventory:create"))]
)
async def execute_putaway(
    data: PutAwayExecuteRequest,
    db: DB,
    current_user: CurrentUser,
):
    """Execute putaway - assign stock item to bin."""
    # Get stock item
    item_query = select(StockItem).where(StockItem.id == data.stock_item_id)
    item_result = await db.execute(item_query)
    stock_item = item_result.scalar_one_or_none()

    if not stock_item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Stock item not found"
        )

    # Get target bin
    bin_query = select(WarehouseBin).where(WarehouseBin.id == data.bin_id)
    bin_result = await db.execute(bin_query)
    bin = bin_result.scalar_one_or_none()

    if not bin:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bin not found"
        )

    # Check bin availability
    if not bin.is_active or not bin.is_receivable:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Bin is not available for putaway"
        )

    if bin.is_full:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Bin is full"
        )

    # Decrement old bin if exists
    if stock_item.bin_id:
        old_bin_query = select(WarehouseBin).where(WarehouseBin.id == stock_item.bin_id)
        old_bin_result = await db.execute(old_bin_query)
        old_bin = old_bin_result.scalar_one_or_none()
        if old_bin:
            old_bin.current_items = max(0, old_bin.current_items - 1)

    # Update stock item bin
    stock_item.bin_id = bin.id

    # Increment bin item count
    bin.current_items += 1
    bin.last_activity_at = datetime.now(timezone.utc)

    await db.commit()

    return PutAwayExecuteResponse(
        success=True,
        stock_item_id=stock_item.id,
        bin_id=bin.id,
        bin_code=bin.bin_code,
        message=f"Item putaway to bin {bin.bin_code} successful",
    )


@router.post(
    "/inventory/move",
    response_model=InventoryMoveResponse,
    dependencies=[Depends(require_permissions("inventory:update"))]
)
async def move_inventory(
    data: InventoryMoveRequest,
    db: DB,
    current_user: CurrentUser,
):
    """Move inventory item between bins."""
    # Get stock item
    item_query = select(StockItem).where(StockItem.id == data.stock_item_id)
    item_result = await db.execute(item_query)
    stock_item = item_result.scalar_one_or_none()

    if not stock_item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Stock item not found"
        )

    # Verify current bin
    if stock_item.bin_id != data.from_bin_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Stock item is not in the specified source bin"
        )

    # Get source bin
    from_bin_query = select(WarehouseBin).where(WarehouseBin.id == data.from_bin_id)
    from_bin_result = await db.execute(from_bin_query)
    from_bin = from_bin_result.scalar_one_or_none()

    # Get destination bin
    to_bin_query = select(WarehouseBin).where(WarehouseBin.id == data.to_bin_id)
    to_bin_result = await db.execute(to_bin_query)
    to_bin = to_bin_result.scalar_one_or_none()

    if not from_bin or not to_bin:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Source or destination bin not found"
        )

    # Check destination bin availability
    if not to_bin.is_active or not to_bin.is_receivable:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Destination bin is not available"
        )

    if to_bin.is_full:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Destination bin is full"
        )

    # Update counts
    from_bin.current_items = max(0, from_bin.current_items - 1)
    from_bin.last_activity_at = datetime.now(timezone.utc)

    to_bin.current_items += 1
    to_bin.last_activity_at = datetime.now(timezone.utc)

    # Update stock item
    stock_item.bin_id = to_bin.id

    await db.commit()

    return InventoryMoveResponse(
        success=True,
        stock_item_id=stock_item.id,
        from_bin_code=from_bin.bin_code,
        to_bin_code=to_bin.bin_code,
        message=f"Item moved from {from_bin.bin_code} to {to_bin.bin_code}",
    )
