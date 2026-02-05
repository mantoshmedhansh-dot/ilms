"""
Omnichannel API Endpoints - Phase 3: BOPIS/BORIS & Ship-from-Store.

Endpoints for:
- Store Location Management
- BOPIS (Buy Online, Pick up In Store)
- Ship-from-Store
- BORIS (Buy Online, Return In Store)
- Store Inventory Reservations
"""
import uuid
from typing import Optional, List
from decimal import Decimal
from datetime import datetime

from fastapi import APIRouter, Depends, Query, HTTPException, status

from app.api.deps import DB, CurrentUser, require_permissions
from app.services.omnichannel_service import OmnichannelService
from app.schemas.omnichannel import (
    # Store
    StoreLocationCreate, StoreLocationUpdate, StoreLocationResponse,
    StoreLocationListResponse, NearbyStoresRequest, StoreWithDistance,
    # BOPIS
    BOPISOrderCreate, BOPISOrderUpdate, BOPISPickupRequest,
    BOPISOrderResponse, BOPISOrderListResponse,
    # Ship-from-Store
    ShipFromStoreCreate, SFSAcceptRequest, SFSRejectRequest, SFSShipRequest,
    ShipFromStoreResponse, SFSListResponse,
    # Store Returns
    StoreReturnCreate, ReturnInspectionRequest, ReturnRefundRequest,
    StoreReturnResponse, StoreReturnListResponse,
    # Stats
    StoreOmnichannelStats, OmnichannelDashboardStats
)

router = APIRouter()


# ============================================================================
# STORE LOCATION ENDPOINTS
# ============================================================================

@router.post(
    "/stores",
    response_model=StoreLocationResponse,
    dependencies=[Depends(require_permissions("omnichannel.stores.create"))]
)
async def create_store(
    data: StoreLocationCreate,
    db: DB,
    current_user: CurrentUser
):
    """Create a new store location."""
    service = OmnichannelService(db, current_user.tenant_id)
    store = await service.create_store(data, current_user.id)
    await db.commit()
    return store


@router.get(
    "/stores",
    response_model=StoreLocationListResponse,
    dependencies=[Depends(require_permissions("omnichannel.stores.read"))]
)
async def list_stores(
    db: DB,
    current_user: CurrentUser,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    status: Optional[str] = None,
    city: Optional[str] = None,
    bopis_enabled: Optional[bool] = None,
    sfs_enabled: Optional[bool] = None
):
    """List all store locations."""
    service = OmnichannelService(db, current_user.tenant_id)
    skip = (page - 1) * size
    stores, total = await service.get_stores(
        skip=skip,
        limit=size,
        status=status,
        city=city,
        bopis_enabled=bopis_enabled,
        sfs_enabled=sfs_enabled
    )
    pages = (total + size - 1) // size

    return StoreLocationListResponse(
        items=stores,
        total=total,
        page=page,
        size=size,
        pages=pages
    )


@router.get(
    "/stores/{store_id}",
    response_model=StoreLocationResponse,
    dependencies=[Depends(require_permissions("omnichannel.stores.read"))]
)
async def get_store(
    store_id: uuid.UUID,
    db: DB,
    current_user: CurrentUser
):
    """Get store by ID."""
    service = OmnichannelService(db, current_user.tenant_id)
    return await service.get_store(store_id)


@router.patch(
    "/stores/{store_id}",
    response_model=StoreLocationResponse,
    dependencies=[Depends(require_permissions("omnichannel.stores.update"))]
)
async def update_store(
    store_id: uuid.UUID,
    data: StoreLocationUpdate,
    db: DB,
    current_user: CurrentUser
):
    """Update store location."""
    service = OmnichannelService(db, current_user.tenant_id)
    store = await service.update_store(store_id, data)
    await db.commit()
    return store


@router.post(
    "/stores/nearby",
    response_model=List[StoreWithDistance],
    dependencies=[Depends(require_permissions("omnichannel.stores.read"))]
)
async def find_nearby_stores(
    data: NearbyStoresRequest,
    db: DB,
    current_user: CurrentUser
):
    """Find stores near a location."""
    service = OmnichannelService(db, current_user.tenant_id)
    results = await service.find_nearby_stores(
        latitude=data.latitude,
        longitude=data.longitude,
        radius_km=data.radius_km,
        bopis_enabled=data.bopis_enabled,
        sfs_enabled=data.ship_from_store_enabled,
        limit=data.limit
    )

    # Format response with distance
    response = []
    for item in results:
        store_data = StoreLocationResponse.model_validate(item["store"])
        store_with_dist = StoreWithDistance(
            **store_data.model_dump(),
            distance_km=item["distance_km"]
        )
        response.append(store_with_dist)

    return response


# ============================================================================
# BOPIS ENDPOINTS
# ============================================================================

@router.post(
    "/bopis",
    response_model=BOPISOrderResponse,
    dependencies=[Depends(require_permissions("omnichannel.bopis.create"))]
)
async def create_bopis_order(
    data: BOPISOrderCreate,
    db: DB,
    current_user: CurrentUser
):
    """Create a BOPIS order."""
    service = OmnichannelService(db, current_user.tenant_id)
    bopis = await service.create_bopis_order(data, current_user.id)
    await db.commit()
    return bopis


@router.get(
    "/bopis",
    response_model=BOPISOrderListResponse,
    dependencies=[Depends(require_permissions("omnichannel.bopis.read"))]
)
async def list_bopis_orders(
    db: DB,
    current_user: CurrentUser,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    store_id: Optional[uuid.UUID] = None,
    status: Optional[str] = None,
    customer_id: Optional[uuid.UUID] = None
):
    """List BOPIS orders."""
    service = OmnichannelService(db, current_user.tenant_id)
    skip = (page - 1) * size
    orders, total = await service.get_bopis_orders(
        skip=skip,
        limit=size,
        store_id=store_id,
        status=status,
        customer_id=customer_id
    )
    pages = (total + size - 1) // size

    return BOPISOrderListResponse(
        items=orders,
        total=total,
        page=page,
        size=size,
        pages=pages
    )


@router.get(
    "/bopis/{bopis_id}",
    response_model=BOPISOrderResponse,
    dependencies=[Depends(require_permissions("omnichannel.bopis.read"))]
)
async def get_bopis_order(
    bopis_id: uuid.UUID,
    db: DB,
    current_user: CurrentUser
):
    """Get BOPIS order by ID."""
    service = OmnichannelService(db, current_user.tenant_id)
    return await service.get_bopis_order(bopis_id)


@router.get(
    "/bopis/lookup/{pickup_code}",
    response_model=BOPISOrderResponse,
    dependencies=[Depends(require_permissions("omnichannel.bopis.read"))]
)
async def get_bopis_by_code(
    pickup_code: str,
    db: DB,
    current_user: CurrentUser
):
    """Get BOPIS order by pickup code."""
    service = OmnichannelService(db, current_user.tenant_id)
    return await service.get_bopis_by_pickup_code(pickup_code)


@router.post(
    "/bopis/{bopis_id}/confirm",
    response_model=BOPISOrderResponse,
    dependencies=[Depends(require_permissions("omnichannel.bopis.update"))]
)
async def confirm_bopis_order(
    bopis_id: uuid.UUID,
    db: DB,
    current_user: CurrentUser
):
    """Store confirms BOPIS order availability."""
    service = OmnichannelService(db, current_user.tenant_id)
    bopis = await service.confirm_bopis_order(bopis_id, current_user.id)
    await db.commit()
    return bopis


@router.post(
    "/bopis/{bopis_id}/start-picking",
    response_model=BOPISOrderResponse,
    dependencies=[Depends(require_permissions("omnichannel.bopis.update"))]
)
async def start_bopis_picking(
    bopis_id: uuid.UUID,
    db: DB,
    current_user: CurrentUser
):
    """Start picking for BOPIS order."""
    service = OmnichannelService(db, current_user.tenant_id)
    bopis = await service.start_bopis_picking(bopis_id, current_user.id)
    await db.commit()
    return bopis


@router.post(
    "/bopis/{bopis_id}/ready",
    response_model=BOPISOrderResponse,
    dependencies=[Depends(require_permissions("omnichannel.bopis.update"))]
)
async def mark_bopis_ready(
    bopis_id: uuid.UUID,
    db: DB,
    current_user: CurrentUser,
    storage_location: Optional[str] = None
):
    """Mark BOPIS order as ready for pickup."""
    service = OmnichannelService(db, current_user.tenant_id)
    bopis = await service.mark_bopis_ready(bopis_id, current_user.id, storage_location)
    await db.commit()
    return bopis


@router.post(
    "/bopis/{bopis_id}/notify",
    response_model=BOPISOrderResponse,
    dependencies=[Depends(require_permissions("omnichannel.bopis.update"))]
)
async def notify_customer_ready(
    bopis_id: uuid.UUID,
    db: DB,
    current_user: CurrentUser
):
    """Send ready notification to customer."""
    service = OmnichannelService(db, current_user.tenant_id)
    bopis = await service.notify_customer_ready(bopis_id)
    await db.commit()
    return bopis


@router.post(
    "/bopis/{bopis_id}/pickup",
    response_model=BOPISOrderResponse,
    dependencies=[Depends(require_permissions("omnichannel.bopis.update"))]
)
async def complete_bopis_pickup(
    bopis_id: uuid.UUID,
    data: BOPISPickupRequest,
    db: DB,
    current_user: CurrentUser
):
    """Complete BOPIS order pickup."""
    service = OmnichannelService(db, current_user.tenant_id)
    bopis = await service.complete_bopis_pickup(bopis_id, data, current_user.id)
    await db.commit()
    return bopis


@router.post(
    "/bopis/{bopis_id}/cancel",
    response_model=BOPISOrderResponse,
    dependencies=[Depends(require_permissions("omnichannel.bopis.update"))]
)
async def cancel_bopis_order(
    bopis_id: uuid.UUID,
    reason: str,
    db: DB,
    current_user: CurrentUser
):
    """Cancel BOPIS order."""
    service = OmnichannelService(db, current_user.tenant_id)
    bopis = await service.cancel_bopis_order(bopis_id, reason, current_user.id)
    await db.commit()
    return bopis


# ============================================================================
# SHIP-FROM-STORE ENDPOINTS
# ============================================================================

@router.post(
    "/sfs",
    response_model=ShipFromStoreResponse,
    dependencies=[Depends(require_permissions("omnichannel.sfs.create"))]
)
async def create_sfs_order(
    data: ShipFromStoreCreate,
    db: DB,
    current_user: CurrentUser
):
    """Create ship-from-store order."""
    service = OmnichannelService(db, current_user.tenant_id)
    sfs = await service.create_sfs_order(data, current_user.id)
    await db.commit()
    return sfs


@router.get(
    "/sfs",
    response_model=SFSListResponse,
    dependencies=[Depends(require_permissions("omnichannel.sfs.read"))]
)
async def list_sfs_orders(
    db: DB,
    current_user: CurrentUser,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    store_id: Optional[uuid.UUID] = None,
    status: Optional[str] = None
):
    """List ship-from-store orders."""
    service = OmnichannelService(db, current_user.tenant_id)
    skip = (page - 1) * size
    orders, total = await service.get_sfs_orders(
        skip=skip,
        limit=size,
        store_id=store_id,
        status=status
    )
    pages = (total + size - 1) // size

    return SFSListResponse(
        items=orders,
        total=total,
        page=page,
        size=size,
        pages=pages
    )


@router.get(
    "/sfs/{sfs_id}",
    response_model=ShipFromStoreResponse,
    dependencies=[Depends(require_permissions("omnichannel.sfs.read"))]
)
async def get_sfs_order(
    sfs_id: uuid.UUID,
    db: DB,
    current_user: CurrentUser
):
    """Get ship-from-store order by ID."""
    service = OmnichannelService(db, current_user.tenant_id)
    return await service.get_sfs_order(sfs_id)


@router.post(
    "/sfs/{sfs_id}/accept",
    response_model=ShipFromStoreResponse,
    dependencies=[Depends(require_permissions("omnichannel.sfs.update"))]
)
async def accept_sfs_order(
    sfs_id: uuid.UUID,
    data: SFSAcceptRequest,
    db: DB,
    current_user: CurrentUser
):
    """Store accepts SFS order."""
    service = OmnichannelService(db, current_user.tenant_id)
    sfs = await service.accept_sfs_order(sfs_id, data, current_user.id)
    await db.commit()
    return sfs


@router.post(
    "/sfs/{sfs_id}/reject",
    response_model=ShipFromStoreResponse,
    dependencies=[Depends(require_permissions("omnichannel.sfs.update"))]
)
async def reject_sfs_order(
    sfs_id: uuid.UUID,
    data: SFSRejectRequest,
    db: DB,
    current_user: CurrentUser
):
    """Store rejects SFS order."""
    service = OmnichannelService(db, current_user.tenant_id)
    sfs = await service.reject_sfs_order(sfs_id, data, current_user.id)
    await db.commit()
    return sfs


@router.post(
    "/sfs/{sfs_id}/start-picking",
    response_model=ShipFromStoreResponse,
    dependencies=[Depends(require_permissions("omnichannel.sfs.update"))]
)
async def start_sfs_picking(
    sfs_id: uuid.UUID,
    db: DB,
    current_user: CurrentUser
):
    """Start picking for SFS order."""
    service = OmnichannelService(db, current_user.tenant_id)
    sfs = await service.start_sfs_picking(sfs_id, current_user.id)
    await db.commit()
    return sfs


@router.post(
    "/sfs/{sfs_id}/pack",
    response_model=ShipFromStoreResponse,
    dependencies=[Depends(require_permissions("omnichannel.sfs.update"))]
)
async def mark_sfs_packed(
    sfs_id: uuid.UUID,
    db: DB,
    current_user: CurrentUser
):
    """Mark SFS order as packed."""
    service = OmnichannelService(db, current_user.tenant_id)
    sfs = await service.mark_sfs_packed(sfs_id, current_user.id)
    await db.commit()
    return sfs


@router.post(
    "/sfs/{sfs_id}/ship",
    response_model=ShipFromStoreResponse,
    dependencies=[Depends(require_permissions("omnichannel.sfs.update"))]
)
async def ship_sfs_order(
    sfs_id: uuid.UUID,
    data: SFSShipRequest,
    db: DB,
    current_user: CurrentUser
):
    """Mark SFS order as shipped."""
    service = OmnichannelService(db, current_user.tenant_id)
    sfs = await service.ship_sfs_order(sfs_id, data, current_user.id)
    await db.commit()
    return sfs


# ============================================================================
# STORE RETURNS (BORIS) ENDPOINTS
# ============================================================================

@router.post(
    "/returns",
    response_model=StoreReturnResponse,
    dependencies=[Depends(require_permissions("omnichannel.returns.create"))]
)
async def create_store_return(
    data: StoreReturnCreate,
    db: DB,
    current_user: CurrentUser
):
    """Create in-store return (BORIS)."""
    service = OmnichannelService(db, current_user.tenant_id)
    ret = await service.create_store_return(data, current_user.id)
    await db.commit()
    return ret


@router.get(
    "/returns",
    response_model=StoreReturnListResponse,
    dependencies=[Depends(require_permissions("omnichannel.returns.read"))]
)
async def list_store_returns(
    db: DB,
    current_user: CurrentUser,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    store_id: Optional[uuid.UUID] = None,
    status: Optional[str] = None,
    customer_id: Optional[uuid.UUID] = None
):
    """List store returns."""
    service = OmnichannelService(db, current_user.tenant_id)
    skip = (page - 1) * size
    returns, total = await service.get_store_returns(
        skip=skip,
        limit=size,
        store_id=store_id,
        status=status,
        customer_id=customer_id
    )
    pages = (total + size - 1) // size

    return StoreReturnListResponse(
        items=returns,
        total=total,
        page=page,
        size=size,
        pages=pages
    )


@router.get(
    "/returns/{return_id}",
    response_model=StoreReturnResponse,
    dependencies=[Depends(require_permissions("omnichannel.returns.read"))]
)
async def get_store_return(
    return_id: uuid.UUID,
    db: DB,
    current_user: CurrentUser
):
    """Get store return by ID."""
    service = OmnichannelService(db, current_user.tenant_id)
    return await service.get_store_return(return_id)


@router.post(
    "/returns/{return_id}/receive",
    response_model=StoreReturnResponse,
    dependencies=[Depends(require_permissions("omnichannel.returns.update"))]
)
async def receive_return(
    return_id: uuid.UUID,
    db: DB,
    current_user: CurrentUser
):
    """Mark return as received at store."""
    service = OmnichannelService(db, current_user.tenant_id)
    ret = await service.receive_return(return_id, current_user.id)
    await db.commit()
    return ret


@router.post(
    "/returns/{return_id}/inspect",
    response_model=StoreReturnResponse,
    dependencies=[Depends(require_permissions("omnichannel.returns.update"))]
)
async def inspect_return(
    return_id: uuid.UUID,
    data: ReturnInspectionRequest,
    db: DB,
    current_user: CurrentUser
):
    """Complete return inspection."""
    service = OmnichannelService(db, current_user.tenant_id)
    ret = await service.inspect_return(return_id, data, current_user.id)
    await db.commit()
    return ret


@router.post(
    "/returns/{return_id}/refund",
    response_model=StoreReturnResponse,
    dependencies=[Depends(require_permissions("omnichannel.returns.update"))]
)
async def process_refund(
    return_id: uuid.UUID,
    data: ReturnRefundRequest,
    db: DB,
    current_user: CurrentUser
):
    """Process refund for approved return."""
    service = OmnichannelService(db, current_user.tenant_id)
    ret = await service.process_return_refund(return_id, data, current_user.id)
    await db.commit()
    return ret


@router.post(
    "/returns/{return_id}/complete",
    response_model=StoreReturnResponse,
    dependencies=[Depends(require_permissions("omnichannel.returns.update"))]
)
async def complete_return(
    return_id: uuid.UUID,
    restock_decision: str = Query(..., description="RESTOCK, RETURN_TO_WAREHOUSE, DISPOSE, REFURBISH"),
    db: DB = None,
    current_user: CurrentUser = None
):
    """Complete return with restock decision."""
    service = OmnichannelService(db, current_user.tenant_id)
    ret = await service.complete_return(return_id, restock_decision, current_user.id)
    await db.commit()
    return ret


# ============================================================================
# STATISTICS ENDPOINTS
# ============================================================================

@router.get(
    "/stats",
    response_model=OmnichannelDashboardStats,
    dependencies=[Depends(require_permissions("omnichannel.stats.read"))]
)
async def get_dashboard_stats(
    db: DB,
    current_user: CurrentUser
):
    """Get omnichannel dashboard statistics."""
    service = OmnichannelService(db, current_user.tenant_id)
    return await service.get_dashboard_stats()


@router.get(
    "/stats/store/{store_id}",
    response_model=StoreOmnichannelStats,
    dependencies=[Depends(require_permissions("omnichannel.stats.read"))]
)
async def get_store_stats(
    store_id: uuid.UUID,
    db: DB,
    current_user: CurrentUser
):
    """Get omnichannel stats for a specific store."""
    service = OmnichannelService(db, current_user.tenant_id)
    return await service.get_store_stats(store_id)
