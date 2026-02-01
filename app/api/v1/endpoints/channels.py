"""API endpoints for Multi-Channel Commerce (D2C, Marketplaces, etc.)."""
from typing import Optional, List
from uuid import UUID
from datetime import date, datetime, timezone
from decimal import Decimal
from math import ceil

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy import select, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.channel import (
    SalesChannel, ChannelType, ChannelStatus,
    ChannelPricing, ChannelInventory, ChannelOrder,
    ProductChannelSettings, PricingRule, PricingHistory,
    PricingRuleType,
)
from app.models.product import Product
from app.models.warehouse import Warehouse
from app.models.user import User
from app.schemas.channel import (
    # Channel
    SalesChannelCreate, SalesChannelUpdate, SalesChannelResponse, SalesChannelListResponse,
    # Pricing
    ChannelPricingCreate, ChannelPricingUpdate, ChannelPricingResponse, ChannelPricingListResponse,
    # Inventory
    ChannelInventoryCreate, ChannelInventoryUpdate, ChannelInventoryResponse, ChannelInventoryListResponse,
    # Channel Order
    ChannelOrderCreate, ChannelOrderUpdate, ChannelOrderResponse, ChannelOrderListResponse,
    # Sync
    InventorySyncRequest, PriceSyncRequest, OrderSyncResponse,
    # ProductChannelSettings
    ProductChannelSettingsCreate, ProductChannelSettingsUpdate,
    ProductChannelSettingsResponse, ProductChannelSettingsListResponse,
    # Auto-replenish
    AutoReplenishRequest, AutoReplenishResponse,
    # Marketplace sync
    MarketplaceSyncRequest, MarketplaceSyncResponse,
    # Channel inventory summary
    ChannelInventorySummary,
    # Channel inventory dashboard
    ChannelInventoryDashboardResponse,
    # Pricing Rules
    PricingRuleCreate, PricingRuleUpdate, PricingRuleResponse, PricingRuleListResponse,
    # Pricing History
    PricingHistoryResponse, PricingHistoryListResponse,
)
from app.api.deps import DB, CurrentUser, get_current_user, require_permissions
from app.services.audit_service import AuditService
from app.config import settings
from app.core.module_decorators import require_module

router = APIRouter()


# ==================== Sales Channels ====================

@router.post("", response_model=SalesChannelResponse, status_code=status.HTTP_201_CREATED)
@require_module("sales_distribution")
async def create_sales_channel(
    channel_in: SalesChannelCreate,
    db: DB,
    current_user: User = Depends(get_current_user),
):
    """Create a new sales channel."""
    # Generate channel code if not provided
    count_result = await db.execute(select(func.count(SalesChannel.id)))
    count = count_result.scalar() or 0

    prefix_map = {
        ChannelType.D2C: "D2C",
        ChannelType.D2C_WEBSITE: "D2C",
        ChannelType.D2C_APP: "D2C",
        ChannelType.MARKETPLACE: "MKT",
        ChannelType.AMAZON: "AMZ",
        ChannelType.FLIPKART: "FLK",
        ChannelType.MYNTRA: "MYN",
        ChannelType.MEESHO: "MSH",
        ChannelType.JIOMART: "JIO",
        ChannelType.TATACLIQ: "TTA",
        ChannelType.AJIO: "AJI",
        ChannelType.NYKAA: "NYK",
        ChannelType.B2B: "B2B",
        ChannelType.B2B_PORTAL: "B2B",
        ChannelType.DEALER: "DLR",
        ChannelType.DEALER_PORTAL: "DLR",
        ChannelType.OFFLINE: "OFL",
        ChannelType.RETAIL_STORE: "RET",
        ChannelType.OTHER: "OTH",
    }
    prefix = prefix_map.get(channel_in.channel_type, "CHN")

    # Use provided code or generate one
    channel_code = channel_in.code if channel_in.code else f"{prefix}-{str(count + 1).zfill(3)}"

    # Use name as display_name if not provided
    display_name = channel_in.display_name if channel_in.display_name else channel_in.name

    # Prepare channel data
    channel_data = channel_in.model_dump(exclude={'code', 'display_name', 'api_key', 'api_secret', 'config'})

    channel = SalesChannel(
        code=channel_code,
        display_name=display_name,
        **channel_data,
    )

    db.add(channel)
    await db.commit()
    await db.refresh(channel)

    return channel


@router.get("", response_model=SalesChannelListResponse)
@require_module("sales_distribution")
async def list_sales_channels(
    db: DB,
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=100),
    channel_type: Optional[ChannelType] = None,
    status: Optional[ChannelStatus] = None,
    search: Optional[str] = None,
    current_user: User = Depends(get_current_user),
):
    """List sales channels."""
    query = select(SalesChannel)
    count_query = select(func.count(SalesChannel.id))

    filters = []
    if channel_type:
        filters.append(SalesChannel.channel_type == channel_type)
    if status:
        filters.append(SalesChannel.status == status)
    if search:
        filters.append(or_(
            SalesChannel.name.ilike(f"%{search}%"),
            SalesChannel.code.ilike(f"%{search}%"),
        ))

    if filters:
        query = query.where(and_(*filters))
        count_query = count_query.where(and_(*filters))

    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    skip = (page - 1) * size
    query = query.order_by(SalesChannel.created_at.desc()).offset(skip).limit(size)
    result = await db.execute(query)
    channels = result.scalars().all()

    return SalesChannelListResponse(
        items=[SalesChannelResponse.model_validate(c) for c in channels],
        total=total,
        page=page,
        size=size,
        pages=ceil(total / size) if total > 0 else 1
    )


@router.get("/stats", dependencies=[Depends(require_permissions("channel:view"))])
async def get_channel_stats(
    db: DB,
    current_user: User = Depends(get_current_user),
):
    """Get channel statistics for dashboard."""
    # Total channels
    total_result = await db.execute(select(func.count(SalesChannel.id)))
    total_channels = total_result.scalar() or 0

    # Active channels
    active_result = await db.execute(
        select(func.count(SalesChannel.id)).where(
            SalesChannel.status == ChannelStatus.ACTIVE.value
        )
    )
    active_channels = active_result.scalar() or 0

    # Today's orders and revenue from channel_orders
    today = date.today()
    today_start = datetime.combine(today, datetime.min.time())
    today_end = datetime.combine(today, datetime.max.time())

    orders_today_result = await db.execute(
        select(func.count(ChannelOrder.id)).where(
            and_(
                ChannelOrder.created_at >= today_start,
                ChannelOrder.created_at <= today_end
            )
        )
    )
    total_orders_today = orders_today_result.scalar() or 0

    revenue_today_result = await db.execute(
        select(func.coalesce(func.sum(ChannelOrder.channel_selling_price), 0)).where(
            and_(
                ChannelOrder.created_at >= today_start,
                ChannelOrder.created_at <= today_end
            )
        )
    )
    total_revenue_today = float(revenue_today_result.scalar() or 0)

    return {
        "total_channels": total_channels,
        "active_channels": active_channels,
        "total_orders_today": total_orders_today,
        "total_revenue_today": total_revenue_today,
    }


@router.get("/dropdown")
@require_module("sales_distribution")
async def get_channels_dropdown(
    db: DB,
    active_only: bool = True,
    current_user: User = Depends(get_current_user),
):
    """Get channels for dropdown selection."""
    query = select(SalesChannel)

    if active_only:
        query = query.where(SalesChannel.status == "ACTIVE")  # VARCHAR comparison

    query = query.order_by(SalesChannel.name)
    result = await db.execute(query)
    channels = result.scalars().all()

    return [
        {
            "id": str(c.id),
            "code": c.code,
            "name": c.name,
            "type": c.channel_type,
        }
        for c in channels
    ]


# ==================== Reports (must be before /{channel_id}) ====================

@router.get("/reports/summary")
@require_module("sales_distribution")
async def get_channel_summary(
    start_date: date,
    end_date: date,
    db: DB,
    current_user: User = Depends(get_current_user),
):
    """Get sales summary by channel."""
    # Orders by channel - use channel_selling_price and created_at (actual model fields)
    orders_query = select(
        SalesChannel.name,
        SalesChannel.channel_type,
        func.count(ChannelOrder.id).label("order_count"),
        func.coalesce(func.sum(ChannelOrder.channel_selling_price), 0).label("order_value"),
    ).join(
        ChannelOrder, ChannelOrder.channel_id == SalesChannel.id
    ).where(
        and_(
            func.date(ChannelOrder.created_at) >= start_date,
            func.date(ChannelOrder.created_at) <= end_date,
        )
    ).group_by(SalesChannel.id, SalesChannel.name, SalesChannel.channel_type)

    orders_result = await db.execute(orders_query)
    by_channel = [
        {
            "channel_name": row.name,
            "channel_type": row.channel_type if row.channel_type else None,
            "order_count": row.order_count,
            "order_value": float(row.order_value),
        }
        for row in orders_result.all()
    ]

    # Totals
    total_query = select(
        func.count(ChannelOrder.id).label("total_orders"),
        func.coalesce(func.sum(ChannelOrder.channel_selling_price), 0).label("total_value"),
    ).where(
        and_(
            func.date(ChannelOrder.created_at) >= start_date,
            func.date(ChannelOrder.created_at) <= end_date,
        )
    )
    total_result = await db.execute(total_query)
    totals = total_result.one()

    # Channel counts
    channel_counts = await db.execute(
        select(
            SalesChannel.status,
            func.count(SalesChannel.id).label("count"),
        ).group_by(SalesChannel.status)
    )
    status_counts = {
        row.status: row.count
        for row in channel_counts.all()
    }

    return {
        "period_start": start_date.isoformat(),
        "period_end": end_date.isoformat(),
        "by_channel": by_channel,
        "totals": {
            "order_count": totals.total_orders,
            "order_value": float(totals.total_value),
        },
        "channels": {
            "total": sum(status_counts.values()),
            "by_status": status_counts,
        }
    }


@router.get("/reports/inventory-status")
@require_module("sales_distribution")
async def get_channel_inventory_status(
    db: DB,
    channel_id: Optional[UUID] = None,
    current_user: User = Depends(get_current_user),
):
    """Get inventory sync status across channels."""
    # Calculate available_quantity in SQL: allocated - buffer - reserved
    available_expr = func.greatest(
        0,
        func.coalesce(ChannelInventory.allocated_quantity, 0) -
        func.coalesce(ChannelInventory.buffer_quantity, 0) -
        func.coalesce(ChannelInventory.reserved_quantity, 0)
    )

    query = select(
        SalesChannel.id,
        SalesChannel.name,
        func.count(ChannelInventory.id).label("products_allocated"),
        func.coalesce(func.sum(ChannelInventory.allocated_quantity), 0).label("total_allocated"),
        func.coalesce(func.sum(available_expr), 0).label("total_available"),
    ).outerjoin(
        ChannelInventory, ChannelInventory.channel_id == SalesChannel.id
    ).group_by(SalesChannel.id, SalesChannel.name)

    if channel_id:
        query = query.where(SalesChannel.id == channel_id)

    result = await db.execute(query)
    channels = result.all()

    return {
        "channels": [
            {
                "channel_id": str(row.id),
                "channel_name": row.name,
                "products_allocated": row.products_allocated,
                "total_allocated": int(row.total_allocated),
                "total_available": int(row.total_available),
            }
            for row in channels
        ]
    }


# ==================== Channel Inventory Dashboard ====================

@router.get("/inventory/dashboard", response_model=ChannelInventoryDashboardResponse)
@require_module("sales_distribution")
async def get_channel_inventory_dashboard(
    db: DB,
    current_user: User = Depends(get_current_user),
):
    """
    Get comprehensive channel inventory dashboard.

    Returns:
        - Summary stats (total channels, warehouses, products allocated)
        - By channel breakdown (inventory per channel)
        - By warehouse breakdown (inventory per warehouse)
        - By channel-location breakdown (inventory per channel-warehouse combo)
    """
    from app.services.channel_inventory_service import ChannelInventoryService

    service = ChannelInventoryService(db)
    dashboard_data = await service.get_inventory_dashboard()

    return ChannelInventoryDashboardResponse(**dashboard_data)


# ==================== Global Channel Inventory (All Channels) ====================

@router.get("/inventory")
@require_module("sales_distribution")
async def list_all_channel_inventory(
    db: DB,
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=100),
    channel_id: Optional[UUID] = None,
    sync_status: Optional[str] = None,
    product_id: Optional[UUID] = None,
    current_user: User = Depends(get_current_user),
):
    """List channel inventory across all channels with optional filters."""
    # Base query with joins
    query = (
        select(ChannelInventory)
        .options(
            selectinload(ChannelInventory.channel),
            selectinload(ChannelInventory.product),
            selectinload(ChannelInventory.warehouse),
        )
    )

    # Apply filters
    conditions = []
    if channel_id:
        conditions.append(ChannelInventory.channel_id == channel_id)
    if product_id:
        conditions.append(ChannelInventory.product_id == product_id)
    if sync_status:
        # Map sync status to conditions
        if sync_status == "SYNCED":
            conditions.append(ChannelInventory.last_synced_at.isnot(None))
            conditions.append(ChannelInventory.is_active == True)
        elif sync_status == "PENDING":
            conditions.append(ChannelInventory.last_synced_at.is_(None))
        elif sync_status == "OUT_OF_SYNC":
            # Items where marketplace_quantity differs from calculated available
            # available = allocated - buffer - reserved
            available_calc = (
                func.coalesce(ChannelInventory.allocated_quantity, 0) -
                func.coalesce(ChannelInventory.buffer_quantity, 0) -
                func.coalesce(ChannelInventory.reserved_quantity, 0)
            )
            conditions.append(ChannelInventory.marketplace_quantity != available_calc)
        elif sync_status == "FAILED":
            conditions.append(ChannelInventory.is_active == False)

    if conditions:
        query = query.where(and_(*conditions))

    # Count total
    count_query = select(func.count(ChannelInventory.id))
    if conditions:
        count_query = count_query.where(and_(*conditions))
    count_result = await db.execute(count_query)
    total = count_result.scalar() or 0

    # Apply pagination
    offset = (page - 1) * size
    query = query.offset(offset).limit(size).order_by(ChannelInventory.updated_at.desc())

    result = await db.execute(query)
    items = result.scalars().all()

    # Transform to response format
    inventory_items = []
    for inv in items:
        # Determine sync status
        if not inv.is_active:
            status = "FAILED"
        elif inv.last_synced_at is None:
            status = "PENDING"
        elif inv.marketplace_quantity != (inv.allocated_quantity - inv.buffer_quantity - inv.reserved_quantity):
            status = "OUT_OF_SYNC"
        else:
            status = "SYNCED"

        inventory_items.append({
            "id": str(inv.id),
            "channel_id": str(inv.channel_id),
            "channel_name": inv.channel.name if inv.channel else "Unknown",
            "product_id": str(inv.product_id),
            "product_name": inv.product.name if inv.product else "Unknown",
            "product_sku": inv.product.sku if inv.product else "",
            "warehouse_id": str(inv.warehouse_id) if inv.warehouse_id else None,
            "warehouse_name": inv.warehouse.name if inv.warehouse else None,
            "allocated_quantity": inv.allocated_quantity or 0,
            "warehouse_quantity": inv.allocated_quantity or 0,  # Alias for frontend
            "channel_quantity": inv.marketplace_quantity or 0,
            "reserved_quantity": inv.reserved_quantity or 0,
            "available_quantity": inv.available_quantity or 0,
            "buffer_stock": inv.buffer_quantity or 0,
            "sync_status": status,
            "last_synced_at": inv.last_synced_at.isoformat() if inv.last_synced_at else None,
            "is_active": inv.is_active,
        })

    return {
        "items": inventory_items,
        "total": total,
        "page": page,
        "size": size,
        "pages": ceil(total / size) if size > 0 else 0,
    }


@router.get("/inventory/stats", dependencies=[Depends(require_permissions("channel:view"))])
async def get_channel_inventory_stats(
    db: DB,
    channel_id: Optional[UUID] = None,
    current_user: User = Depends(get_current_user),
):
    """Get channel inventory statistics."""
    # Base condition
    conditions = []
    if channel_id:
        conditions.append(ChannelInventory.channel_id == channel_id)

    # Total products mapped
    total_query = select(func.count(ChannelInventory.id))
    if conditions:
        total_query = total_query.where(and_(*conditions))
    total_result = await db.execute(total_query)
    total_products = total_result.scalar() or 0

    # Calculate available in SQL for comparisons
    available_calc = (
        func.coalesce(ChannelInventory.allocated_quantity, 0) -
        func.coalesce(ChannelInventory.buffer_quantity, 0) -
        func.coalesce(ChannelInventory.reserved_quantity, 0)
    )

    # Synced count (has last_synced_at and is_active)
    synced_query = select(func.count(ChannelInventory.id)).where(
        and_(
            ChannelInventory.last_synced_at.isnot(None),
            ChannelInventory.is_active == True,
            ChannelInventory.marketplace_quantity == available_calc,
            *conditions
        )
    )
    synced_result = await db.execute(synced_query)
    synced_count = synced_result.scalar() or 0

    # Out of sync count
    out_of_sync_query = select(func.count(ChannelInventory.id)).where(
        and_(
            ChannelInventory.last_synced_at.isnot(None),
            ChannelInventory.is_active == True,
            ChannelInventory.marketplace_quantity != available_calc,
            *conditions
        )
    )
    out_of_sync_result = await db.execute(out_of_sync_query)
    out_of_sync_count = out_of_sync_result.scalar() or 0

    # Failed count (inactive)
    failed_query = select(func.count(ChannelInventory.id)).where(
        and_(
            ChannelInventory.is_active == False,
            *conditions
        )
    )
    failed_result = await db.execute(failed_query)
    failed_count = failed_result.scalar() or 0

    return {
        "total_products": total_products,
        "synced_count": synced_count,
        "out_of_sync_count": out_of_sync_count,
        "failed_count": failed_count,
    }


@router.post("/inventory/{inventory_id}/sync")
@require_module("sales_distribution")
async def sync_single_inventory(
    inventory_id: UUID,
    db: DB,
    current_user: User = Depends(get_current_user),
):
    """Sync a single inventory item to its channel."""
    result = await db.execute(
        select(ChannelInventory)
        .options(selectinload(ChannelInventory.channel))
        .where(ChannelInventory.id == inventory_id)
    )
    inventory = result.scalar_one_or_none()

    if not inventory:
        raise HTTPException(status_code=404, detail="Channel inventory not found")

    # In a real implementation, this would call the marketplace API
    # For now, we simulate sync by updating marketplace_quantity to match available
    available = max(0, (inventory.allocated_quantity or 0) - (inventory.buffer_quantity or 0) - (inventory.reserved_quantity or 0))
    inventory.marketplace_quantity = available
    inventory.last_synced_at = datetime.now(timezone.utc)
    inventory.is_active = True

    await db.commit()
    await db.refresh(inventory)

    return {
        "success": True,
        "message": "Inventory synced successfully",
        "inventory_id": str(inventory.id),
        "synced_quantity": inventory.marketplace_quantity,
    }


@router.post("/inventory/sync-all")
@require_module("sales_distribution")
async def sync_all_inventory(
    db: DB,
    channel_id: Optional[UUID] = None,
    current_user: User = Depends(get_current_user),
):
    """Sync all inventory items to their channels."""
    # Build query
    query = select(ChannelInventory).where(ChannelInventory.is_active == True)
    if channel_id:
        query = query.where(ChannelInventory.channel_id == channel_id)

    result = await db.execute(query)
    items = result.scalars().all()

    synced_count = 0
    failed_count = 0

    for item in items:
        try:
            # In real implementation, call marketplace API here
            available = max(0, (item.allocated_quantity or 0) - (item.buffer_quantity or 0) - (item.reserved_quantity or 0))
            item.marketplace_quantity = available
            item.last_synced_at = datetime.now(timezone.utc)
            synced_count += 1
        except Exception:
            failed_count += 1

    await db.commit()

    return {
        "success": True,
        "message": f"Synced {synced_count} items, {failed_count} failed",
        "synced_count": synced_count,
        "failed_count": failed_count,
    }


@router.put("/inventory/{inventory_id}/buffer")
@require_module("sales_distribution")
async def update_inventory_buffer(
    inventory_id: UUID,
    db: DB,
    buffer_stock: int = Query(..., ge=0, description="Buffer stock quantity"),
    current_user: User = Depends(get_current_user),
):
    """Update buffer stock for a channel inventory item."""
    result = await db.execute(
        select(ChannelInventory).where(ChannelInventory.id == inventory_id)
    )
    inventory = result.scalar_one_or_none()

    if not inventory:
        raise HTTPException(status_code=404, detail="Channel inventory not found")

    inventory.buffer_quantity = buffer_stock
    # available_quantity is a computed property, it will recalculate automatically

    await db.commit()
    await db.refresh(inventory)

    return {
        "success": True,
        "message": "Buffer stock updated successfully",
        "inventory_id": str(inventory.id),
        "buffer_stock": inventory.buffer_quantity,
        "available_quantity": inventory.available_quantity,
    }


# ==================== Single Channel Operations ====================

@router.get("/{channel_id}", response_model=SalesChannelResponse)
@require_module("sales_distribution")
async def get_sales_channel(
    channel_id: UUID,
    db: DB,
    current_user: User = Depends(get_current_user),
):
    """Get sales channel by ID."""
    result = await db.execute(
        select(SalesChannel).where(SalesChannel.id == channel_id)
    )
    channel = result.scalar_one_or_none()

    if not channel:
        raise HTTPException(status_code=404, detail="Sales channel not found")

    return channel


@router.put("/{channel_id}", response_model=SalesChannelResponse)
@require_module("sales_distribution")
async def update_sales_channel(
    channel_id: UUID,
    channel_in: SalesChannelUpdate,
    db: DB,
    current_user: User = Depends(get_current_user),
):
    """Update sales channel."""
    result = await db.execute(
        select(SalesChannel).where(SalesChannel.id == channel_id)
    )
    channel = result.scalar_one_or_none()

    if not channel:
        raise HTTPException(status_code=404, detail="Sales channel not found")

    update_data = channel_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(channel, field, value)

    await db.commit()
    await db.refresh(channel)

    return channel


@router.delete("/{channel_id}", status_code=status.HTTP_204_NO_CONTENT)
@require_module("sales_distribution")
async def delete_sales_channel(
    channel_id: UUID,
    db: DB,
    current_user: User = Depends(get_current_user),
):
    """Delete a sales channel (soft delete by setting status to INACTIVE)."""
    result = await db.execute(
        select(SalesChannel).where(SalesChannel.id == channel_id)
    )
    channel = result.scalar_one_or_none()

    if not channel:
        raise HTTPException(status_code=404, detail="Sales channel not found")

    # Check if channel has active orders
    orders_result = await db.execute(
        select(func.count(ChannelOrder.id)).where(
            and_(
                ChannelOrder.channel_id == channel_id,
                ChannelOrder.channel_status.in_(["PENDING", "PROCESSING", "SHIPPED"])
            )
        )
    )
    active_orders = orders_result.scalar() or 0

    if active_orders > 0:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot delete channel with {active_orders} active orders"
        )

    channel.status = ChannelStatus.INACTIVE.value

    await db.commit()
    return None


@router.post("/{channel_id}/activate", response_model=SalesChannelResponse)
@require_module("sales_distribution")
async def activate_channel(
    channel_id: UUID,
    db: DB,
    current_user: User = Depends(get_current_user),
):
    """Activate a sales channel."""
    result = await db.execute(
        select(SalesChannel).where(SalesChannel.id == channel_id)
    )
    channel = result.scalar_one_or_none()

    if not channel:
        raise HTTPException(status_code=404, detail="Sales channel not found")

    channel.status = ChannelStatus.ACTIVE.value

    await db.commit()
    await db.refresh(channel)

    return channel


@router.post("/{channel_id}/deactivate", response_model=SalesChannelResponse)
@require_module("sales_distribution")
async def deactivate_channel(
    channel_id: UUID,
    db: DB,
    current_user: User = Depends(get_current_user),
):
    """Deactivate a sales channel."""
    result = await db.execute(
        select(SalesChannel).where(SalesChannel.id == channel_id)
    )
    channel = result.scalar_one_or_none()

    if not channel:
        raise HTTPException(status_code=404, detail="Sales channel not found")

    channel.status = ChannelStatus.INACTIVE.value

    await db.commit()
    await db.refresh(channel)

    return channel


# ==================== Channel Pricing ====================

@router.get("/{channel_id}/pricing", response_model=ChannelPricingListResponse)
@require_module("sales_distribution")
async def get_channel_pricing(
    channel_id: UUID,
    db: DB,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    product_id: Optional[UUID] = None,
    is_active: bool = True,
    current_user: User = Depends(get_current_user),
):
    """Get pricing for a sales channel with product details."""
    # Use selectinload to eagerly load product relationship
    query = (
        select(ChannelPricing)
        .options(selectinload(ChannelPricing.product))
        .where(ChannelPricing.channel_id == channel_id)
    )
    count_query = select(func.count(ChannelPricing.id)).where(
        ChannelPricing.channel_id == channel_id
    )

    if product_id:
        query = query.where(ChannelPricing.product_id == product_id)
        count_query = count_query.where(ChannelPricing.product_id == product_id)
    if is_active is not None:
        query = query.where(ChannelPricing.is_active == is_active)
        count_query = count_query.where(ChannelPricing.is_active == is_active)

    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    query = query.offset(skip).limit(limit)
    result = await db.execute(query)
    pricing_list = result.scalars().all()

    # Transform to include product_name and product_sku from loaded relationship
    items = []
    for p in pricing_list:
        item_dict = {
            "id": p.id,
            "channel_id": p.channel_id,
            "product_id": p.product_id,
            "variant_id": p.variant_id,
            "mrp": p.mrp,
            "selling_price": p.selling_price,
            "transfer_price": p.transfer_price,
            "discount_percentage": p.discount_percentage,
            "max_discount_percentage": p.max_discount_percentage,
            "is_active": p.is_active,
            "is_listed": p.is_listed,
            "effective_from": p.effective_from,
            "effective_to": p.effective_to,
            "margin_percentage": p.margin_percentage,
            "product_name": p.product.name if p.product else None,
            "product_sku": p.product.sku if p.product else None,
            "created_at": p.created_at,
            "updated_at": p.updated_at,
        }
        items.append(ChannelPricingResponse.model_validate(item_dict))

    return ChannelPricingListResponse(
        items=items,
        total=total,
        skip=skip,
        limit=limit
    )


@router.post("/{channel_id}/pricing", response_model=ChannelPricingResponse, status_code=status.HTTP_201_CREATED)
@require_module("sales_distribution")
async def create_channel_pricing(
    channel_id: UUID,
    pricing_in: ChannelPricingCreate,
    db: DB,
    current_user: User = Depends(get_current_user),
):
    """Create channel-specific pricing for a product."""
    # Verify channel
    channel_result = await db.execute(
        select(SalesChannel).where(SalesChannel.id == channel_id)
    )
    if not channel_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Sales channel not found")

    # Check for existing pricing
    existing = await db.execute(
        select(ChannelPricing).where(
            and_(
                ChannelPricing.channel_id == channel_id,
                ChannelPricing.product_id == pricing_in.product_id,
                ChannelPricing.variant_id == pricing_in.variant_id,
                ChannelPricing.is_active == True,
            )
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=400,
            detail="Active pricing already exists for this product on this channel"
        )

    pricing = ChannelPricing(
        channel_id=channel_id,
        **pricing_in.model_dump(),
    )

    db.add(pricing)
    await db.commit()
    await db.refresh(pricing)

    # Log to pricing history
    history = PricingHistory(
        entity_type="CHANNEL_PRICING",
        entity_id=pricing.id,
        field_name="created",
        old_value=None,
        new_value=f"selling_price={pricing.selling_price}, mrp={pricing.mrp}",
        changed_by=current_user.id,
    )
    db.add(history)
    await db.commit()

    return pricing


@router.put("/{channel_id}/pricing/{pricing_id}", response_model=ChannelPricingResponse)
@require_module("sales_distribution")
async def update_channel_pricing(
    channel_id: UUID,
    pricing_id: UUID,
    pricing_in: ChannelPricingUpdate,
    db: DB,
    current_user: User = Depends(get_current_user),
):
    """Update channel pricing."""
    result = await db.execute(
        select(ChannelPricing).where(
            and_(
                ChannelPricing.id == pricing_id,
                ChannelPricing.channel_id == channel_id,
            )
        )
    )
    pricing = result.scalar_one_or_none()

    if not pricing:
        raise HTTPException(status_code=404, detail="Channel pricing not found")

    update_data = pricing_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        old_value = getattr(pricing, field, None)
        if old_value != value:
            # Log to pricing history
            history = PricingHistory(
                entity_type="CHANNEL_PRICING",
                entity_id=pricing.id,
                field_name=field,
                old_value=str(old_value) if old_value is not None else None,
                new_value=str(value) if value is not None else None,
                changed_by=current_user.id,
            )
            db.add(history)
        setattr(pricing, field, value)

    await db.commit()
    await db.refresh(pricing)

    return pricing


@router.delete("/{channel_id}/pricing/{pricing_id}", status_code=status.HTTP_204_NO_CONTENT)
@require_module("sales_distribution")
async def delete_channel_pricing(
    channel_id: UUID,
    pricing_id: UUID,
    db: DB,
    current_user: User = Depends(get_current_user),
):
    """Delete channel pricing."""
    result = await db.execute(
        select(ChannelPricing).where(
            and_(
                ChannelPricing.id == pricing_id,
                ChannelPricing.channel_id == channel_id,
            )
        )
    )
    pricing = result.scalar_one_or_none()

    if not pricing:
        raise HTTPException(status_code=404, detail="Channel pricing not found")

    # Log to pricing history before delete
    history = PricingHistory(
        entity_type="CHANNEL_PRICING",
        entity_id=pricing.id,
        field_name="deleted",
        old_value=f"selling_price={pricing.selling_price}, mrp={pricing.mrp}",
        new_value=None,
        changed_by=current_user.id,
    )
    db.add(history)

    await db.delete(pricing)
    await db.commit()
    return None


@router.post("/{channel_id}/pricing/sync")
@require_module("sales_distribution")
async def sync_channel_pricing(
    channel_id: UUID,
    sync_request: PriceSyncRequest,
    db: DB,
    current_user: User = Depends(get_current_user),
):
    """Sync pricing to channel (push to marketplace API)."""
    # Verify channel
    channel_result = await db.execute(
        select(SalesChannel).where(SalesChannel.id == channel_id)
    )
    channel = channel_result.scalar_one_or_none()

    if not channel:
        raise HTTPException(status_code=404, detail="Sales channel not found")

    # Get pricing to sync
    query = select(ChannelPricing).where(
        and_(
            ChannelPricing.channel_id == channel_id,
            ChannelPricing.is_active == True,
        )
    )

    if sync_request.product_ids:
        query = query.where(ChannelPricing.product_id.in_(sync_request.product_ids))

    result = await db.execute(query)
    pricing_list = result.scalars().all()

    # TODO: Integrate with actual marketplace APIs
    # For now, count items that would be synced
    synced_count = len(pricing_list)

    await db.commit()

    return {
        "channel_id": str(channel_id),
        "channel_name": channel.name,
        "synced_count": synced_count,
        "sync_time": datetime.now(timezone.utc).isoformat(),
        "status": "SUCCESS",
    }


# ==================== Pricing Calculation & Bulk Operations ====================

@router.post("/{channel_id}/pricing/calculate")
@require_module("sales_distribution")
async def calculate_product_price(
    channel_id: UUID,
    db: DB,
    product_id: UUID = Query(..., description="Product to calculate price for"),
    quantity: int = Query(1, ge=1, description="Quantity for volume discounts"),
    variant_id: Optional[UUID] = Query(None, description="Product variant"),
    customer_segment: str = Query("STANDARD", description="Customer segment for pricing"),
    current_user: User = Depends(get_current_user),
):
    """
    Calculate the final price for a product on this channel.

    Applies:
    - Channel-specific pricing (ChannelPricing table)
    - Volume discounts (quantity-based)
    - Customer segment discounts
    - Max discount threshold validation

    Returns the breakdown of base price, discounts applied, and final price.
    """
    from app.services.pricing_service import PricingService

    pricing_service = PricingService(db)

    try:
        result = await pricing_service.calculate_price(
            product_id=product_id,
            channel_id=channel_id,
            quantity=quantity,
            variant_id=variant_id,
            customer_segment=customer_segment,
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{channel_id}/pricing/bulk")
@require_module("sales_distribution")
async def bulk_create_channel_pricing(
    channel_id: UUID,
    pricing_data: List[ChannelPricingCreate],
    db: DB,
    current_user: User = Depends(get_current_user),
):
    """
    Bulk create or update channel pricing.

    For each item:
    - If pricing exists for product+variant, updates it
    - Otherwise creates new pricing record

    Returns count of created/updated records and any errors.
    """
    from app.services.pricing_service import PricingService

    pricing_service = PricingService(db)

    # Convert Pydantic models to dicts
    data_list = [item.model_dump() for item in pricing_data]

    result = await pricing_service.bulk_create_channel_pricing(
        channel_id=channel_id,
        pricing_data=data_list,
    )

    return result


@router.post("/{channel_id}/pricing/copy-from/{source_channel_id}")
@require_module("sales_distribution")
async def copy_pricing_from_channel(
    channel_id: UUID,
    source_channel_id: UUID,
    db: DB,
    overwrite: bool = Query(False, description="Overwrite existing pricing if exists"),
    current_user: User = Depends(get_current_user),
):
    """
    Copy all pricing from source channel to destination channel.

    - source_channel_id: Channel to copy pricing FROM
    - channel_id: Channel to copy pricing TO
    - overwrite: If True, overwrites existing pricing; if False, skips existing

    Returns count of copied/skipped records.
    """
    from app.services.pricing_service import PricingService

    pricing_service = PricingService(db)

    result = await pricing_service.copy_pricing_between_channels(
        source_channel_id=source_channel_id,
        destination_channel_id=channel_id,
        overwrite=overwrite,
    )

    return result


@router.get("/{channel_id}/pricing/alerts")
@require_module("sales_distribution")
async def get_pricing_alerts(
    channel_id: UUID,
    db: DB,
    min_margin_threshold: Decimal = Query(Decimal("10"), description="Minimum margin % threshold"),
    current_user: User = Depends(get_current_user),
):
    """
    Get products with pricing below margin threshold.

    Returns list of products where margin % < min_margin_threshold.
    """
    from app.services.pricing_service import PricingService

    pricing_service = PricingService(db)
    alerts = await pricing_service.get_pricing_alerts(
        channel_id=channel_id,
        min_margin_threshold=min_margin_threshold,
    )

    return {
        "channel_id": str(channel_id),
        "threshold": float(min_margin_threshold),
        "alerts": alerts,
        "total_alerts": len(alerts),
    }


@router.get("/pricing/compare/{product_id}")
@require_module("sales_distribution")
async def compare_product_pricing(
    product_id: UUID,
    db: DB,
    current_user: User = Depends(get_current_user),
):
    """
    Compare a product's pricing across all channels.

    Returns pricing details for each channel including:
    - Selling price
    - Transfer price (for B2B)
    - Margin percentage
    - Max discount allowed
    """
    from app.services.pricing_service import PricingService

    pricing_service = PricingService(db)
    comparisons = await pricing_service.compare_prices_across_channels(product_id)

    return {
        "product_id": str(product_id),
        "channels": comparisons,
        "total_channels": len(comparisons),
    }


# ==================== Channel Inventory ====================

@router.get("/{channel_id}/inventory", response_model=ChannelInventoryListResponse)
@require_module("sales_distribution")
async def get_channel_inventory(
    channel_id: UUID,
    db: DB,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    product_id: Optional[UUID] = None,
    warehouse_id: Optional[UUID] = None,
    current_user: User = Depends(get_current_user),
):
    """Get inventory allocation for a channel."""
    query = select(ChannelInventory).where(ChannelInventory.channel_id == channel_id)
    count_query = select(func.count(ChannelInventory.id)).where(
        ChannelInventory.channel_id == channel_id
    )

    if product_id:
        query = query.where(ChannelInventory.product_id == product_id)
        count_query = count_query.where(ChannelInventory.product_id == product_id)
    if warehouse_id:
        query = query.where(ChannelInventory.warehouse_id == warehouse_id)
        count_query = count_query.where(ChannelInventory.warehouse_id == warehouse_id)

    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    query = query.offset(skip).limit(limit)
    result = await db.execute(query)
    inventory = result.scalars().all()

    return ChannelInventoryListResponse(
        items=[ChannelInventoryResponse.model_validate(i) for i in inventory],
        total=total,
        skip=skip,
        limit=limit
    )


@router.post("/{channel_id}/inventory", response_model=ChannelInventoryResponse, status_code=status.HTTP_201_CREATED)
@require_module("sales_distribution")
async def create_channel_inventory(
    channel_id: UUID,
    inventory_in: ChannelInventoryCreate,
    db: DB,
    current_user: User = Depends(get_current_user),
):
    """Allocate inventory to a channel."""
    # Verify channel
    channel_result = await db.execute(
        select(SalesChannel).where(SalesChannel.id == channel_id)
    )
    if not channel_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Sales channel not found")

    # Check for existing allocation
    existing = await db.execute(
        select(ChannelInventory).where(
            and_(
                ChannelInventory.channel_id == channel_id,
                ChannelInventory.product_id == inventory_in.product_id,
                ChannelInventory.warehouse_id == inventory_in.warehouse_id,
            )
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=400,
            detail="Inventory allocation already exists for this product/warehouse"
        )

    inventory = ChannelInventory(
        channel_id=channel_id,
        **inventory_in.model_dump(),
    )

    db.add(inventory)
    await db.commit()
    await db.refresh(inventory)

    return inventory


@router.put("/{channel_id}/inventory/{inventory_id}", response_model=ChannelInventoryResponse)
@require_module("sales_distribution")
async def update_channel_inventory(
    channel_id: UUID,
    inventory_id: UUID,
    inventory_in: ChannelInventoryUpdate,
    db: DB,
    current_user: User = Depends(get_current_user),
):
    """Update channel inventory allocation."""
    result = await db.execute(
        select(ChannelInventory).where(
            and_(
                ChannelInventory.id == inventory_id,
                ChannelInventory.channel_id == channel_id,
            )
        )
    )
    inventory = result.scalar_one_or_none()

    if not inventory:
        raise HTTPException(status_code=404, detail="Channel inventory not found")

    update_data = inventory_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(inventory, field, value)

    await db.commit()
    await db.refresh(inventory)

    return inventory


@router.delete("/{channel_id}/inventory/{inventory_id}", status_code=status.HTTP_204_NO_CONTENT)
@require_module("sales_distribution")
async def delete_channel_inventory(
    channel_id: UUID,
    inventory_id: UUID,
    db: DB,
    current_user: User = Depends(get_current_user),
):
    """Delete channel inventory allocation."""
    result = await db.execute(
        select(ChannelInventory).where(
            and_(
                ChannelInventory.id == inventory_id,
                ChannelInventory.channel_id == channel_id,
            )
        )
    )
    inventory = result.scalar_one_or_none()

    if not inventory:
        raise HTTPException(status_code=404, detail="Channel inventory not found")

    await db.delete(inventory)
    await db.commit()
    return None


@router.post("/{channel_id}/inventory/sync")
@require_module("sales_distribution")
async def sync_channel_inventory(
    channel_id: UUID,
    sync_request: InventorySyncRequest,
    db: DB,
    current_user: User = Depends(get_current_user),
):
    """Sync inventory to channel (push to marketplace API)."""
    channel_result = await db.execute(
        select(SalesChannel).where(SalesChannel.id == channel_id)
    )
    channel = channel_result.scalar_one_or_none()

    if not channel:
        raise HTTPException(status_code=404, detail="Sales channel not found")

    # Get inventory to sync
    query = select(ChannelInventory).where(
        and_(
            ChannelInventory.channel_id == channel_id,
            ChannelInventory.is_active == True,
        )
    )

    if sync_request.product_ids:
        query = query.where(ChannelInventory.product_id.in_(sync_request.product_ids))

    result = await db.execute(query)
    inventory_list = result.scalars().all()

    # TODO: Integrate with actual marketplace APIs
    synced_count = 0
    for inv in inventory_list:
        available = max(0, (inv.allocated_quantity or 0) - (inv.buffer_quantity or 0) - (inv.reserved_quantity or 0))
        inv.marketplace_quantity = available
        inv.last_synced_at = datetime.now(timezone.utc)
        synced_count += 1

    await db.commit()

    return {
        "channel_id": str(channel_id),
        "channel_name": channel.name,
        "synced_count": synced_count,
        "sync_time": datetime.now(timezone.utc).isoformat(),
        "status": "SUCCESS",
    }


# ==================== Channel Orders ====================

@router.get("/{channel_id}/orders", response_model=ChannelOrderListResponse)
@require_module("sales_distribution")
async def get_channel_orders(
    channel_id: UUID,
    db: DB,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    status: Optional[str] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    search: Optional[str] = None,
    current_user: User = Depends(get_current_user),
):
    """Get orders from a channel."""
    query = select(ChannelOrder).where(ChannelOrder.channel_id == channel_id)
    count_query = select(func.count(ChannelOrder.id)).where(
        ChannelOrder.channel_id == channel_id
    )
    # Use channel_selling_price instead of non-existent order_value
    value_query = select(func.coalesce(func.sum(ChannelOrder.channel_selling_price), 0)).where(
        ChannelOrder.channel_id == channel_id
    )

    filters = []
    if status:
        filters.append(ChannelOrder.channel_status == status)
    if start_date:
        # Use created_at instead of non-existent channel_order_date
        filters.append(func.date(ChannelOrder.created_at) >= start_date)
    if end_date:
        filters.append(func.date(ChannelOrder.created_at) <= end_date)
    if search:
        # Search only by channel_order_id (customer_name doesn't exist in model)
        filters.append(ChannelOrder.channel_order_id.ilike(f"%{search}%"))

    if filters:
        query = query.where(and_(*filters))
        count_query = count_query.where(and_(*filters))
        value_query = value_query.where(and_(*filters))

    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    total_value_result = await db.execute(value_query)
    total_value = total_value_result.scalar() or Decimal("0")

    # Order by created_at instead of non-existent channel_order_date
    query = query.order_by(ChannelOrder.created_at.desc()).offset(skip).limit(limit)
    result = await db.execute(query)
    orders = result.scalars().all()

    return ChannelOrderListResponse(
        items=[ChannelOrderResponse.model_validate(o) for o in orders],
        total=total,
        total_value=total_value,
        skip=skip,
        limit=limit
    )


@router.post("/{channel_id}/orders", response_model=ChannelOrderResponse, status_code=status.HTTP_201_CREATED)
@require_module("sales_distribution")
async def create_channel_order(
    channel_id: UUID,
    order_in: ChannelOrderCreate,
    db: DB,
    current_user: User = Depends(get_current_user),
):
    """Create/import an order from a channel."""
    # Verify channel
    channel_result = await db.execute(
        select(SalesChannel).where(SalesChannel.id == channel_id)
    )
    channel = channel_result.scalar_one_or_none()

    if not channel:
        raise HTTPException(status_code=404, detail="Sales channel not found")

    # Check for duplicate channel order
    existing = await db.execute(
        select(ChannelOrder).where(
            and_(
                ChannelOrder.channel_id == channel_id,
                ChannelOrder.channel_order_id == order_in.channel_order_id,
            )
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=400,
            detail=f"Order {order_in.channel_order_id} already exists for this channel"
        )

    order = ChannelOrder(
        channel_id=channel_id,
        **order_in.model_dump(),
    )

    db.add(order)
    await db.commit()
    await db.refresh(order)

    return order


@router.put("/{channel_id}/orders/{order_id}", response_model=ChannelOrderResponse)
@require_module("sales_distribution")
async def update_channel_order(
    channel_id: UUID,
    order_id: UUID,
    order_in: ChannelOrderUpdate,
    db: DB,
    current_user: User = Depends(get_current_user),
):
    """Update channel order status."""
    result = await db.execute(
        select(ChannelOrder).where(
            and_(
                ChannelOrder.id == order_id,
                ChannelOrder.channel_id == channel_id,
            )
        )
    )
    order = result.scalar_one_or_none()

    if not order:
        raise HTTPException(status_code=404, detail="Channel order not found")

    update_data = order_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(order, field, value)

    await db.commit()
    await db.refresh(order)

    return order


@router.delete("/{channel_id}/orders/{order_id}", status_code=status.HTTP_204_NO_CONTENT)
@require_module("sales_distribution")
async def delete_channel_order(
    channel_id: UUID,
    order_id: UUID,
    db: DB,
    current_user: User = Depends(get_current_user),
):
    """Delete channel order (only if not converted to internal order)."""
    result = await db.execute(
        select(ChannelOrder).where(
            and_(
                ChannelOrder.id == order_id,
                ChannelOrder.channel_id == channel_id,
            )
        )
    )
    order = result.scalar_one_or_none()

    if not order:
        raise HTTPException(status_code=404, detail="Channel order not found")

    if order.order_id:
        raise HTTPException(
            status_code=400,
            detail="Cannot delete order that has been linked to internal order"
        )

    await db.delete(order)
    await db.commit()
    return None


@router.post("/{channel_id}/orders/{order_id}/convert")
@require_module("sales_distribution")
async def convert_channel_order_to_internal(
    channel_id: UUID,
    order_id: UUID,
    db: DB,
    current_user: User = Depends(get_current_user),
):
    """Convert channel order to internal OMS order."""
    result = await db.execute(
        select(ChannelOrder).where(
            and_(
                ChannelOrder.id == order_id,
                ChannelOrder.channel_id == channel_id,
            )
        )
    )
    channel_order = result.scalar_one_or_none()

    if not channel_order:
        raise HTTPException(status_code=404, detail="Channel order not found")

    if channel_order.order_id:
        raise HTTPException(
            status_code=400,
            detail="Order already linked to internal order"
        )

    # TODO: Create internal Order from ChannelOrder
    # This would involve:
    # 1. Creating/finding customer
    # 2. Creating Order with items
    # 3. Linking channel_order to internal order

    # For now, return placeholder
    return {
        "channel_order_id": str(order_id),
        "channel_order_number": channel_order.channel_order_id,
        "status": "PENDING_IMPLEMENTATION",
        "message": "Order conversion to internal order needs implementation based on your Order model"
    }


@router.post("/{channel_id}/orders/sync", response_model=OrderSyncResponse)
@require_module("sales_distribution")
async def sync_channel_orders(
    channel_id: UUID,
    db: DB,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    current_user: User = Depends(get_current_user),
):
    """Sync orders from channel (pull from marketplace API)."""
    channel_result = await db.execute(
        select(SalesChannel).where(SalesChannel.id == channel_id)
    )
    channel = channel_result.scalar_one_or_none()

    if not channel:
        raise HTTPException(status_code=404, detail="Sales channel not found")

    # TODO: Integrate with actual marketplace APIs
    # Each marketplace has its own API:
    # - Amazon SP-API
    # - Flipkart Seller API
    # - Meesho Partner API
    # etc.

    # For now, return mock response
    return OrderSyncResponse(
        channel_id=channel_id,
        channel_name=channel.name,
        orders_fetched=0,
        orders_created=0,
        orders_updated=0,
        orders_failed=0,
        sync_time=datetime.now(timezone.utc),
        status="SUCCESS",
        message="Integration with channel API pending implementation",
    )


# ==================== Product Channel Settings ====================

@router.get("/settings/product-channel", response_model=ProductChannelSettingsListResponse)
@require_module("sales_distribution")
async def list_product_channel_settings(
    db: DB,
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=100),
    channel_id: Optional[UUID] = None,
    product_id: Optional[UUID] = None,
    warehouse_id: Optional[UUID] = None,
    auto_replenish_enabled: Optional[bool] = None,
    current_user: User = Depends(get_current_user),
):
    """List product channel settings with optional filters."""
    query = select(ProductChannelSettings)
    count_query = select(func.count(ProductChannelSettings.id))

    conditions = []
    if channel_id:
        conditions.append(ProductChannelSettings.channel_id == channel_id)
    if product_id:
        conditions.append(ProductChannelSettings.product_id == product_id)
    if warehouse_id:
        conditions.append(ProductChannelSettings.warehouse_id == warehouse_id)
    if auto_replenish_enabled is not None:
        conditions.append(ProductChannelSettings.auto_replenish_enabled == auto_replenish_enabled)

    if conditions:
        query = query.where(and_(*conditions))
        count_query = count_query.where(and_(*conditions))

    # Get total count
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # Apply pagination
    offset = (page - 1) * size
    query = query.offset(offset).limit(size).order_by(ProductChannelSettings.created_at.desc())

    result = await db.execute(query)
    items = result.scalars().all()

    return ProductChannelSettingsListResponse(
        items=[ProductChannelSettingsResponse.model_validate(item) for item in items],
        total=total,
        page=page,
        size=size,
        pages=ceil(total / size) if total > 0 else 1,
    )


@router.post("/settings/product-channel", response_model=ProductChannelSettingsResponse, status_code=status.HTTP_201_CREATED)
@require_module("sales_distribution")
async def create_product_channel_settings(
    settings_in: ProductChannelSettingsCreate,
    db: DB,
    current_user: User = Depends(get_current_user),
):
    """Create product channel settings for a product-channel-warehouse combination."""
    # Check for existing settings
    existing = await db.execute(
        select(ProductChannelSettings).where(
            and_(
                ProductChannelSettings.product_id == settings_in.product_id,
                ProductChannelSettings.channel_id == settings_in.channel_id,
                ProductChannelSettings.warehouse_id == settings_in.warehouse_id,
            )
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=400,
            detail="Settings already exist for this product-channel-warehouse combination"
        )

    # Verify channel exists
    channel_result = await db.execute(
        select(SalesChannel).where(SalesChannel.id == settings_in.channel_id)
    )
    if not channel_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Channel not found")

    settings_obj = ProductChannelSettings(**settings_in.model_dump())
    db.add(settings_obj)
    await db.commit()
    await db.refresh(settings_obj)

    return settings_obj


@router.get("/settings/product-channel/{settings_id}", response_model=ProductChannelSettingsResponse)
@require_module("sales_distribution")
async def get_product_channel_settings(
    settings_id: UUID,
    db: DB,
    current_user: User = Depends(get_current_user),
):
    """Get product channel settings by ID."""
    result = await db.execute(
        select(ProductChannelSettings).where(ProductChannelSettings.id == settings_id)
    )
    settings_obj = result.scalar_one_or_none()

    if not settings_obj:
        raise HTTPException(status_code=404, detail="Product channel settings not found")

    return settings_obj


@router.put("/settings/product-channel/{settings_id}", response_model=ProductChannelSettingsResponse)
@require_module("sales_distribution")
async def update_product_channel_settings(
    settings_id: UUID,
    settings_in: ProductChannelSettingsUpdate,
    db: DB,
    current_user: User = Depends(get_current_user),
):
    """Update product channel settings."""
    result = await db.execute(
        select(ProductChannelSettings).where(ProductChannelSettings.id == settings_id)
    )
    settings_obj = result.scalar_one_or_none()

    if not settings_obj:
        raise HTTPException(status_code=404, detail="Product channel settings not found")

    update_data = settings_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(settings_obj, field, value)

    await db.commit()
    await db.refresh(settings_obj)

    return settings_obj


@router.delete("/settings/product-channel/{settings_id}", status_code=status.HTTP_204_NO_CONTENT)
@require_module("sales_distribution")
async def delete_product_channel_settings(
    settings_id: UUID,
    db: DB,
    current_user: User = Depends(get_current_user),
):
    """Delete product channel settings."""
    result = await db.execute(
        select(ProductChannelSettings).where(ProductChannelSettings.id == settings_id)
    )
    settings_obj = result.scalar_one_or_none()

    if not settings_obj:
        raise HTTPException(status_code=404, detail="Product channel settings not found")

    await db.delete(settings_obj)
    await db.commit()
    return None


@router.post("/settings/product-channel/bulk", status_code=status.HTTP_201_CREATED)
@require_module("sales_distribution")
async def bulk_create_product_channel_settings(
    items: List[ProductChannelSettingsCreate],
    db: DB,
    current_user: User = Depends(get_current_user),
):
    """Bulk create product channel settings."""
    created = []
    errors = []

    for idx, item in enumerate(items):
        try:
            # Check for existing
            existing = await db.execute(
                select(ProductChannelSettings).where(
                    and_(
                        ProductChannelSettings.product_id == item.product_id,
                        ProductChannelSettings.channel_id == item.channel_id,
                        ProductChannelSettings.warehouse_id == item.warehouse_id,
                    )
                )
            )
            if existing.scalar_one_or_none():
                errors.append({
                    "index": idx,
                    "error": "Settings already exist for this combination",
                    "product_id": str(item.product_id),
                    "channel_id": str(item.channel_id),
                })
                continue

            settings_obj = ProductChannelSettings(**item.model_dump())
            db.add(settings_obj)
            created.append(str(settings_obj.id) if settings_obj.id else f"item_{idx}")

        except Exception as e:
            errors.append({"index": idx, "error": str(e)})

    await db.commit()

    return {
        "created_count": len(created),
        "error_count": len(errors),
        "errors": errors,
    }


# ==================== Auto-Replenish Endpoints ====================

@router.post("/inventory/replenish", response_model=AutoReplenishResponse)
@require_module("sales_distribution")
async def trigger_replenishment(
    request: AutoReplenishRequest,
    db: DB,
    current_user: User = Depends(get_current_user),
):
    """Manually trigger replenishment for a specific channel-product combination."""
    from app.services.channel_inventory_service import ChannelInventoryService

    service = ChannelInventoryService(db)

    # Get safety_stock and reorder_point from settings if not provided
    safety_stock = request.safety_stock
    reorder_point = request.reorder_point

    if safety_stock is None or reorder_point is None:
        # Try to get from ProductChannelSettings
        settings_result = await db.execute(
            select(ProductChannelSettings).where(
                and_(
                    ProductChannelSettings.channel_id == request.channel_id,
                    ProductChannelSettings.product_id == request.product_id,
                    ProductChannelSettings.is_active == True,
                )
            )
        )
        settings_obj = settings_result.scalar_one_or_none()

        if settings_obj:
            safety_stock = safety_stock or settings_obj.safety_stock or 50
            reorder_point = reorder_point or settings_obj.reorder_point or 10
        else:
            # Fall back to ChannelInventory settings
            inv_result = await db.execute(
                select(ChannelInventory).where(
                    and_(
                        ChannelInventory.channel_id == request.channel_id,
                        ChannelInventory.product_id == request.product_id,
                        ChannelInventory.is_active == True,
                    )
                )
            )
            inv = inv_result.scalar_one_or_none()

            if inv:
                safety_stock = safety_stock or inv.safety_stock or 50
                reorder_point = reorder_point or inv.reorder_point or 10
            else:
                safety_stock = safety_stock or 50
                reorder_point = reorder_point or 10

    result = await service.check_and_replenish(
        channel_id=request.channel_id,
        product_id=request.product_id,
        safety_stock=safety_stock,
        reorder_point=reorder_point,
    )

    return AutoReplenishResponse(
        channel_id=request.channel_id,
        product_id=request.product_id,
        replenished=result.get("replenished", False),
        quantity_replenished=result.get("quantity_replenished", 0),
        quantity_needed=result.get("quantity_needed", 0),
        new_available=result.get("new_available", 0),
        reason=result.get("reason"),
        details=result.get("details", []),
    )


@router.post("/inventory/replenish-channel/{channel_id}")
@require_module("sales_distribution")
async def trigger_channel_replenishment(
    channel_id: UUID,
    db: DB,
    current_user: User = Depends(get_current_user),
):
    """Trigger replenishment for all low-stock products in a channel."""
    from app.jobs.auto_replenish import replenish_channel

    result = await replenish_channel(db, str(channel_id))

    return {
        "channel_id": str(channel_id),
        "products_checked": result.get("products_checked", 0),
        "replenishments": result.get("replenishments", []),
        "errors": result.get("errors", []),
    }


@router.post("/inventory/run-auto-replenish-job")
@require_module("sales_distribution")
async def run_auto_replenish_job_endpoint(
    db: DB,
    current_user: User = Depends(get_current_user),
):
    """Manually trigger the auto-replenish job for all channels."""
    from app.jobs.auto_replenish import run_auto_replenish_job

    result = await run_auto_replenish_job(db)

    return result


# ==================== Marketplace Sync Endpoints ====================

@router.post("/inventory/marketplace-sync", response_model=MarketplaceSyncResponse)
@require_module("sales_distribution")
async def trigger_marketplace_sync(
    request: MarketplaceSyncRequest,
    db: DB,
    current_user: User = Depends(get_current_user),
):
    """Trigger marketplace sync for a specific channel."""
    from app.jobs.marketplace_sync import sync_channel_inventory, get_marketplace_adapter

    # Get channel
    channel_result = await db.execute(
        select(SalesChannel).where(SalesChannel.id == request.channel_id)
    )
    channel = channel_result.scalar_one_or_none()

    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")

    # Convert product_ids to list or None
    product_ids = [str(pid) for pid in request.product_ids] if request.product_ids else None

    result = await sync_channel_inventory(db, channel, product_ids)

    return MarketplaceSyncResponse(
        channel_id=request.channel_id,
        channel_name=channel.name,
        synced_count=result.get("synced_count", 0),
        failed_count=result.get("failed_count", 0),
        skipped_count=0,
        sync_time=datetime.now(timezone.utc),
        status="SUCCESS" if result.get("synced_count", 0) > 0 else "NO_ITEMS",
        errors=result.get("errors", []),
    )


@router.post("/inventory/run-marketplace-sync-job")
@require_module("sales_distribution")
async def run_marketplace_sync_job_endpoint(
    db: DB,
    current_user: User = Depends(get_current_user),
):
    """Manually trigger the marketplace sync job for all channels."""
    from app.jobs.marketplace_sync import run_marketplace_sync_job

    result = await run_marketplace_sync_job(db)

    return result


# ==================== Channel Inventory Summary ====================

@router.get("/inventory/summary-by-channel")
@require_module("sales_distribution")
async def get_inventory_summary_by_channel(
    db: DB,
    current_user: User = Depends(get_current_user),
):
    """Get inventory summary grouped by channel."""
    # Calculate available in SQL
    available_calc = func.greatest(
        0,
        func.coalesce(ChannelInventory.allocated_quantity, 0) -
        func.coalesce(ChannelInventory.buffer_quantity, 0) -
        func.coalesce(ChannelInventory.reserved_quantity, 0)
    )

    query = select(
        SalesChannel.id,
        SalesChannel.name,
        SalesChannel.code,
        SalesChannel.channel_type,
        func.count(ChannelInventory.id).label("total_products"),
        func.coalesce(func.sum(ChannelInventory.allocated_quantity), 0).label("total_allocated"),
        func.coalesce(func.sum(available_calc), 0).label("total_available"),
        func.coalesce(func.sum(ChannelInventory.reserved_quantity), 0).label("total_reserved"),
        func.coalesce(func.sum(ChannelInventory.buffer_quantity), 0).label("total_buffer"),
    ).outerjoin(
        ChannelInventory,
        and_(
            ChannelInventory.channel_id == SalesChannel.id,
            ChannelInventory.is_active == True,
        )
    ).where(
        SalesChannel.status == ChannelStatus.ACTIVE.value
    ).group_by(
        SalesChannel.id, SalesChannel.name, SalesChannel.code, SalesChannel.channel_type
    ).order_by(SalesChannel.name)

    result = await db.execute(query)
    rows = result.all()

    summaries = []
    for row in rows:
        # Count synced vs out-of-sync
        synced_query = select(func.count(ChannelInventory.id)).where(
            and_(
                ChannelInventory.channel_id == row.id,
                ChannelInventory.is_active == True,
                ChannelInventory.last_synced_at.isnot(None),
            )
        )
        synced_result = await db.execute(synced_query)
        synced_count = synced_result.scalar() or 0

        # Count low stock (below reorder point)
        low_stock_query = select(func.count(ChannelInventory.id)).where(
            and_(
                ChannelInventory.channel_id == row.id,
                ChannelInventory.is_active == True,
                ChannelInventory.reorder_point > 0,
                (
                    func.coalesce(ChannelInventory.allocated_quantity, 0) -
                    func.coalesce(ChannelInventory.buffer_quantity, 0) -
                    func.coalesce(ChannelInventory.reserved_quantity, 0)
                ) < ChannelInventory.reorder_point,
            )
        )
        low_stock_result = await db.execute(low_stock_query)
        low_stock_count = low_stock_result.scalar() or 0

        summaries.append({
            "channel_id": str(row.id),
            "channel_name": row.name,
            "channel_code": row.code,
            "channel_type": row.channel_type,
            "total_products": row.total_products,
            "total_allocated": int(row.total_allocated),
            "total_available": int(row.total_available),
            "total_reserved": int(row.total_reserved),
            "total_buffer": int(row.total_buffer),
            "synced_products": synced_count,
            "out_of_sync_products": row.total_products - synced_count,
            "low_stock_products": low_stock_count,
        })

    return {
        "channels": summaries,
        "total_channels": len(summaries),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/{channel_id}/inventory/summary")
@require_module("sales_distribution")
async def get_channel_inventory_summary(
    channel_id: UUID,
    db: DB,
    current_user: User = Depends(get_current_user),
):
    """Get detailed inventory summary for a specific channel."""
    # Verify channel exists
    channel_result = await db.execute(
        select(SalesChannel).where(SalesChannel.id == channel_id)
    )
    channel = channel_result.scalar_one_or_none()

    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")

    # Get aggregated stats
    available_calc = func.greatest(
        0,
        func.coalesce(ChannelInventory.allocated_quantity, 0) -
        func.coalesce(ChannelInventory.buffer_quantity, 0) -
        func.coalesce(ChannelInventory.reserved_quantity, 0)
    )

    stats_query = select(
        func.count(ChannelInventory.id).label("total_products"),
        func.coalesce(func.sum(ChannelInventory.allocated_quantity), 0).label("total_allocated"),
        func.coalesce(func.sum(available_calc), 0).label("total_available"),
        func.coalesce(func.sum(ChannelInventory.reserved_quantity), 0).label("total_reserved"),
        func.coalesce(func.sum(ChannelInventory.buffer_quantity), 0).label("total_buffer"),
        func.coalesce(func.sum(ChannelInventory.marketplace_quantity), 0).label("total_marketplace"),
    ).where(
        and_(
            ChannelInventory.channel_id == channel_id,
            ChannelInventory.is_active == True,
        )
    )

    stats_result = await db.execute(stats_query)
    stats = stats_result.one()

    # Count by sync status
    synced_count_result = await db.execute(
        select(func.count(ChannelInventory.id)).where(
            and_(
                ChannelInventory.channel_id == channel_id,
                ChannelInventory.is_active == True,
                ChannelInventory.last_synced_at.isnot(None),
            )
        )
    )
    synced_count = synced_count_result.scalar() or 0

    # Low stock count
    low_stock_result = await db.execute(
        select(func.count(ChannelInventory.id)).where(
            and_(
                ChannelInventory.channel_id == channel_id,
                ChannelInventory.is_active == True,
                ChannelInventory.reorder_point > 0,
                (
                    func.coalesce(ChannelInventory.allocated_quantity, 0) -
                    func.coalesce(ChannelInventory.buffer_quantity, 0) -
                    func.coalesce(ChannelInventory.reserved_quantity, 0)
                ) < ChannelInventory.reorder_point,
            )
        )
    )
    low_stock_count = low_stock_result.scalar() or 0

    # Get top low-stock products
    low_stock_products_query = (
        select(
            ChannelInventory.product_id,
            ChannelInventory.allocated_quantity,
            ChannelInventory.buffer_quantity,
            ChannelInventory.reserved_quantity,
            ChannelInventory.reorder_point,
            ChannelInventory.safety_stock,
            Product.name.label("product_name"),
            Product.sku.label("product_sku"),
        )
        .join(Product, Product.id == ChannelInventory.product_id)
        .where(
            and_(
                ChannelInventory.channel_id == channel_id,
                ChannelInventory.is_active == True,
                ChannelInventory.reorder_point > 0,
                (
                    func.coalesce(ChannelInventory.allocated_quantity, 0) -
                    func.coalesce(ChannelInventory.buffer_quantity, 0) -
                    func.coalesce(ChannelInventory.reserved_quantity, 0)
                ) < ChannelInventory.reorder_point,
            )
        )
        .order_by(
            (
                func.coalesce(ChannelInventory.allocated_quantity, 0) -
                func.coalesce(ChannelInventory.buffer_quantity, 0) -
                func.coalesce(ChannelInventory.reserved_quantity, 0)
            ).asc()
        )
        .limit(10)
    )

    low_stock_products_result = await db.execute(low_stock_products_query)
    low_stock_products = [
        {
            "product_id": str(row.product_id),
            "product_name": row.product_name,
            "product_sku": row.product_sku,
            "available": max(0, (row.allocated_quantity or 0) - (row.buffer_quantity or 0) - (row.reserved_quantity or 0)),
            "reorder_point": row.reorder_point,
            "safety_stock": row.safety_stock,
        }
        for row in low_stock_products_result.all()
    ]

    return {
        "channel_id": str(channel_id),
        "channel_name": channel.name,
        "channel_code": channel.code,
        "channel_type": channel.channel_type,
        "stats": {
            "total_products": stats.total_products,
            "total_allocated": int(stats.total_allocated),
            "total_available": int(stats.total_available),
            "total_reserved": int(stats.total_reserved),
            "total_buffer": int(stats.total_buffer),
            "total_marketplace": int(stats.total_marketplace),
        },
        "sync_status": {
            "synced_products": synced_count,
            "pending_sync": stats.total_products - synced_count,
        },
        "stock_health": {
            "low_stock_products": low_stock_count,
            "healthy_products": stats.total_products - low_stock_count,
        },
        "low_stock_items": low_stock_products,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


# ==================== Pricing Rules ====================

@router.get("/pricing-rules", response_model=PricingRuleListResponse)
@require_module("sales_distribution")
async def list_pricing_rules(
    db: DB,
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=100),
    channel_id: Optional[UUID] = None,
    rule_type: Optional[str] = None,
    is_active: Optional[bool] = None,
    current_user: User = Depends(get_current_user),
):
    """List all pricing rules with optional filters."""
    query = select(PricingRule)
    count_query = select(func.count(PricingRule.id))

    filters = []
    if channel_id:
        filters.append(or_(
            PricingRule.channel_id == channel_id,
            PricingRule.channel_id.is_(None)  # Include global rules
        ))
    if rule_type:
        filters.append(PricingRule.rule_type == rule_type)
    if is_active is not None:
        filters.append(PricingRule.is_active == is_active)

    if filters:
        query = query.where(and_(*filters))
        count_query = count_query.where(and_(*filters))

    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    skip = (page - 1) * size
    query = query.order_by(PricingRule.priority, PricingRule.created_at.desc()).offset(skip).limit(size)
    result = await db.execute(query)
    rules = result.scalars().all()

    return PricingRuleListResponse(
        items=[PricingRuleResponse.model_validate(r) for r in rules],
        total=total,
        page=page,
        size=size,
        pages=ceil(total / size) if total > 0 else 1
    )


@router.post("/pricing-rules", response_model=PricingRuleResponse, status_code=status.HTTP_201_CREATED)
@require_module("sales_distribution")
async def create_pricing_rule(
    rule_in: PricingRuleCreate,
    db: DB,
    current_user: User = Depends(get_current_user),
):
    """Create a new pricing rule."""
    # Check for duplicate code
    existing = await db.execute(
        select(PricingRule).where(PricingRule.code == rule_in.code)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=400,
            detail=f"Pricing rule with code '{rule_in.code}' already exists"
        )

    rule = PricingRule(**rule_in.model_dump())
    db.add(rule)
    await db.commit()
    await db.refresh(rule)

    return rule


@router.get("/pricing-rules/{rule_id}", response_model=PricingRuleResponse)
@require_module("sales_distribution")
async def get_pricing_rule(
    rule_id: UUID,
    db: DB,
    current_user: User = Depends(get_current_user),
):
    """Get a specific pricing rule."""
    result = await db.execute(
        select(PricingRule).where(PricingRule.id == rule_id)
    )
    rule = result.scalar_one_or_none()

    if not rule:
        raise HTTPException(status_code=404, detail="Pricing rule not found")

    return rule


@router.put("/pricing-rules/{rule_id}", response_model=PricingRuleResponse)
@require_module("sales_distribution")
async def update_pricing_rule(
    rule_id: UUID,
    rule_in: PricingRuleUpdate,
    db: DB,
    current_user: User = Depends(get_current_user),
):
    """Update a pricing rule."""
    result = await db.execute(
        select(PricingRule).where(PricingRule.id == rule_id)
    )
    rule = result.scalar_one_or_none()

    if not rule:
        raise HTTPException(status_code=404, detail="Pricing rule not found")

    # Store old values for history
    old_values = {}
    update_data = rule_in.model_dump(exclude_unset=True)

    for field, new_value in update_data.items():
        old_value = getattr(rule, field, None)
        if old_value != new_value:
            old_values[field] = str(old_value) if old_value is not None else None
            setattr(rule, field, new_value)

            # Log to pricing history
            history = PricingHistory(
                entity_type="PRICING_RULE",
                entity_id=rule.id,
                field_name=field,
                old_value=old_values[field],
                new_value=str(new_value) if new_value is not None else None,
                changed_by=current_user.id,
            )
            db.add(history)

    await db.commit()
    await db.refresh(rule)

    return rule


@router.delete("/pricing-rules/{rule_id}", status_code=status.HTTP_204_NO_CONTENT)
@require_module("sales_distribution")
async def delete_pricing_rule(
    rule_id: UUID,
    db: DB,
    current_user: User = Depends(get_current_user),
):
    """Delete a pricing rule."""
    result = await db.execute(
        select(PricingRule).where(PricingRule.id == rule_id)
    )
    rule = result.scalar_one_or_none()

    if not rule:
        raise HTTPException(status_code=404, detail="Pricing rule not found")

    await db.delete(rule)
    await db.commit()


# ==================== Pricing History ====================

@router.get("/pricing-history", response_model=PricingHistoryListResponse)
@require_module("sales_distribution")
async def list_pricing_history(
    db: DB,
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=100),
    entity_type: Optional[str] = None,
    entity_id: Optional[UUID] = None,
    channel_id: Optional[UUID] = None,
    current_user: User = Depends(get_current_user),
):
    """List pricing change history with optional filters."""
    query = select(PricingHistory)
    count_query = select(func.count(PricingHistory.id))

    filters = []
    if entity_type:
        filters.append(PricingHistory.entity_type == entity_type)
    if entity_id:
        filters.append(PricingHistory.entity_id == entity_id)

    # If channel_id provided, get history for pricing items in that channel
    if channel_id:
        # Get all pricing IDs for this channel
        pricing_ids_subquery = select(ChannelPricing.id).where(
            ChannelPricing.channel_id == channel_id
        )
        filters.append(
            or_(
                and_(
                    PricingHistory.entity_type == "CHANNEL_PRICING",
                    PricingHistory.entity_id.in_(pricing_ids_subquery)
                ),
                # Also include global pricing rules
                PricingHistory.entity_type == "PRICING_RULE"
            )
        )

    if filters:
        query = query.where(and_(*filters))
        count_query = count_query.where(and_(*filters))

    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    skip = (page - 1) * size
    query = query.order_by(PricingHistory.changed_at.desc()).offset(skip).limit(size)
    result = await db.execute(query)
    history_items = result.scalars().all()

    return PricingHistoryListResponse(
        items=[PricingHistoryResponse.model_validate(h) for h in history_items],
        total=total,
        page=page,
        size=size,
        pages=ceil(total / size) if total > 0 else 1
    )
