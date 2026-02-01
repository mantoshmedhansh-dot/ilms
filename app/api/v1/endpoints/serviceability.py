"""
Serviceability and Allocation API Endpoints.

Covers:
1. Pincode serviceability check (public) - with caching for fast response
2. Warehouse serviceability management (admin)
3. Allocation rules management (admin)
4. Order allocation (internal)
"""
from typing import Optional, List
from uuid import UUID
import time

from fastapi import APIRouter, Depends, HTTPException, Query, status, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.services.serviceability_service import ServiceabilityService
from app.services.allocation_service import AllocationService
from app.services.cache_service import get_cache
from app.config import settings
from app.schemas.serviceability import (

    # Serviceability Check
    ServiceabilityCheckRequest,
    ServiceabilityCheckResponse,
    # Warehouse Serviceability
    WarehouseServiceabilityCreate,
    WarehouseServiceabilityBulkCreate,
    WarehouseServiceabilityUpdate,
    WarehouseServiceabilityResponse,
    WarehouseServiceabilityList,
    BulkPincodeUploadRequest,
    BulkPincodeUploadResponse,
    PincodeRangeRequest,
    # Allocation Rules
    AllocationRuleCreate,
    AllocationRuleUpdate,
    AllocationRuleResponse,
    AllocationRuleList,
    # Order Allocation
    OrderAllocationRequest,
    AllocationDecision,
    AllocationLogResponse,
    # Dashboard
    ServiceabilityDashboard,
)
from app.core.module_decorators import require_module

router = APIRouter(prefix="/serviceability", tags=["Serviceability"])


# ==================== Public Endpoints ====================

@router.post(
    "/check",
    response_model=ServiceabilityCheckResponse,
    summary="Check pincode serviceability",
    description="""
    Check if a pincode is serviceable.

    This endpoint:
    1. Checks cache first for fast response (< 50ms)
    2. If not cached, finds warehouses that serve this pincode
    3. Finds transporters that can deliver to this pincode
    4. Returns serviceability info, warehouse options, and transporter options
    5. Caches result for future requests

    Use this at checkout to verify delivery availability.
    Response includes X-Cache header indicating HIT or MISS.
    """
)
async def check_serviceability(
    request: ServiceabilityCheckRequest,
    response: Response,
    db: AsyncSession = Depends(get_db)
):
    """Check if a pincode is serviceable with caching."""
    start_time = time.time()
    cache = get_cache()
    channel = request.channel_code or "D2C"

    # Try cache first
    if settings.CACHE_ENABLED:
        cached = await cache.get_serviceability(request.pincode, channel)
        if cached:
            response.headers["X-Cache"] = "HIT"
            response.headers["X-Response-Time"] = f"{(time.time() - start_time) * 1000:.2f}ms"
            return ServiceabilityCheckResponse(**cached)

    # Cache miss - query database
    service = ServiceabilityService(db)
    result = await service.check_serviceability(request)

    # Cache the result
    if settings.CACHE_ENABLED:
        cache_data = result.model_dump()
        # Convert any non-serializable types
        if cache_data.get("warehouse_candidates"):
            for wc in cache_data["warehouse_candidates"]:
                if wc.get("shipping_cost"):
                    wc["shipping_cost"] = float(wc["shipping_cost"])
        if cache_data.get("minimum_shipping_cost"):
            cache_data["minimum_shipping_cost"] = float(cache_data["minimum_shipping_cost"])

        await cache.set_serviceability(
            request.pincode,
            cache_data,
            channel,
            ttl=settings.SERVICEABILITY_CACHE_TTL
        )

    response.headers["X-Cache"] = "MISS"
    response.headers["X-Response-Time"] = f"{(time.time() - start_time) * 1000:.2f}ms"
    return result


@router.get(
    "/check/{pincode}",
    response_model=ServiceabilityCheckResponse,
    summary="Quick pincode check",
    description="Quick check for pincode serviceability (GET version) - optimized for fast response with caching"
)
async def quick_check_serviceability(
    pincode: str,
    response: Response,
    payment_mode: Optional[str] = Query(None, description="COD or PREPAID"),
    channel_code: Optional[str] = Query("D2C", description="Sales channel"),
    db: AsyncSession = Depends(get_db)
):
    """Quick pincode serviceability check with caching."""
    start_time = time.time()
    cache = get_cache()
    channel = channel_code or "D2C"

    # Try cache first
    if settings.CACHE_ENABLED:
        cached = await cache.get_serviceability(pincode, channel)
        if cached:
            response.headers["X-Cache"] = "HIT"
            response.headers["X-Response-Time"] = f"{(time.time() - start_time) * 1000:.2f}ms"
            return ServiceabilityCheckResponse(**cached)

    # Cache miss - query database
    service = ServiceabilityService(db)
    request = ServiceabilityCheckRequest(
        pincode=pincode,
        payment_mode=payment_mode,
        channel_code=channel_code
    )
    result = await service.check_serviceability(request)

    # Cache the result
    if settings.CACHE_ENABLED:
        cache_data = result.model_dump()
        if cache_data.get("warehouse_candidates"):
            for wc in cache_data["warehouse_candidates"]:
                if wc.get("shipping_cost"):
                    wc["shipping_cost"] = float(wc["shipping_cost"])
        if cache_data.get("minimum_shipping_cost"):
            cache_data["minimum_shipping_cost"] = float(cache_data["minimum_shipping_cost"])

        await cache.set_serviceability(
            pincode,
            cache_data,
            channel,
            ttl=settings.SERVICEABILITY_CACHE_TTL
        )

    response.headers["X-Cache"] = "MISS"
    response.headers["X-Response-Time"] = f"{(time.time() - start_time) * 1000:.2f}ms"
    return result


# ==================== Warehouse Serviceability (Admin) ====================

@router.get(
    "/warehouse",
    response_model=WarehouseServiceabilityList,
    summary="List warehouse serviceability",
    description="List all warehouse-pincode mappings with filters"
)
@require_module("oms_fulfillment")
async def list_warehouse_serviceability(
    warehouse_id: Optional[UUID] = Query(None, description="Filter by warehouse"),
    pincode: Optional[str] = Query(None, description="Filter by pincode"),
    is_active: bool = Query(True, description="Filter by active status"),
    page: int = Query(1, ge=1),
    page_size: int = Query(100, ge=1, le=1000),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List warehouse serviceability mappings."""
    service = ServiceabilityService(db)
    skip = (page - 1) * page_size
    items, total = await service.get_warehouse_serviceability(
        warehouse_id=warehouse_id,
        pincode=pincode,
        is_active=is_active,
        skip=skip,
        limit=page_size
    )

    # Map to response
    response_items = []
    for item in items:
        response_items.append(WarehouseServiceabilityResponse(
            id=item.id,
            warehouse_id=item.warehouse_id,
            warehouse_name=item.warehouse.name if item.warehouse else None,
            warehouse_code=item.warehouse.code if item.warehouse else None,
            pincode=item.pincode,
            is_serviceable=item.is_serviceable,
            cod_available=item.cod_available,
            prepaid_available=item.prepaid_available,
            estimated_days=item.estimated_days,
            priority=item.priority,
            shipping_cost=item.shipping_cost,
            city=item.city,
            state=item.state,
            zone=item.zone,
            is_active=item.is_active,
            created_at=item.created_at,
            updated_at=item.updated_at
        ))

    return WarehouseServiceabilityList(
        items=response_items,
        total=total,
        page=page,
        page_size=page_size
    )


@router.post(
    "/warehouse",
    response_model=WarehouseServiceabilityResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add warehouse-pincode mapping",
    description="Add a single warehouse-pincode serviceability mapping"
)
@require_module("oms_fulfillment")
async def create_warehouse_serviceability(
    data: WarehouseServiceabilityCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create warehouse serviceability mapping."""
    service = ServiceabilityService(db)
    item = await service.create_warehouse_serviceability(data)

    # Invalidate cache for this pincode
    cache = get_cache()
    await cache.invalidate_serviceability(data.pincode)

    return WarehouseServiceabilityResponse(
        id=item.id,
        warehouse_id=item.warehouse_id,
        pincode=item.pincode,
        is_serviceable=item.is_serviceable,
        cod_available=item.cod_available,
        prepaid_available=item.prepaid_available,
        estimated_days=item.estimated_days,
        priority=item.priority,
        shipping_cost=item.shipping_cost,
        city=item.city,
        state=item.state,
        zone=item.zone,
        is_active=item.is_active,
        created_at=item.created_at,
        updated_at=item.updated_at
    )


@router.post(
    "/warehouse/bulk",
    response_model=BulkPincodeUploadResponse,
    summary="Bulk upload pincodes",
    description="Upload multiple pincodes for a warehouse at once"
)
@require_module("oms_fulfillment")
async def bulk_upload_pincodes(
    data: BulkPincodeUploadRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Bulk upload pincodes for a warehouse."""
    service = ServiceabilityService(db)
    result = await service.upload_pincodes_bulk(data)

    # Invalidate all serviceability cache after bulk upload
    cache = get_cache()
    await cache.invalidate_serviceability()

    return result


@router.post(
    "/warehouse/range",
    response_model=BulkPincodeUploadResponse,
    summary="Add pincode range",
    description="Add a range of pincodes (e.g., 400001 to 400099)"
)
async def add_pincode_range(
    data: PincodeRangeRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Add a range of pincodes for a warehouse."""
    # Validate range
    try:
        start = int(data.start_pincode)
        end = int(data.end_pincode)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid pincode format"
        )

    if start > end:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Start pincode must be less than end pincode"
        )

    if end - start > 1000:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Range too large. Maximum 1000 pincodes at once."
        )

    # Generate pincodes
    pincodes = [
        {
            "pincode": str(p).zfill(6),
            "city": data.city,
            "state": data.state,
            "zone": data.zone
        }
        for p in range(start, end + 1)
    ]

    # Upload
    service = ServiceabilityService(db)
    result = await service.upload_pincodes_bulk(
        BulkPincodeUploadRequest(
            warehouse_id=data.warehouse_id,
            pincodes=pincodes,
            default_estimated_days=data.estimated_days or 3,
            default_cod_available=data.cod_available
        )
    )

    # Invalidate all serviceability cache after range upload
    cache = get_cache()
    await cache.invalidate_serviceability()

    return result


@router.delete(
    "/warehouse/{warehouse_id}/pincode/{pincode}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove warehouse-pincode mapping",
    description="Remove a pincode from warehouse serviceability"
)
@require_module("oms_fulfillment")
async def delete_warehouse_serviceability(
    warehouse_id: UUID,
    pincode: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete warehouse serviceability mapping."""
    service = ServiceabilityService(db)
    deleted = await service.delete_warehouse_serviceability(warehouse_id, pincode)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Mapping not found"
        )

    # Invalidate cache for this pincode
    cache = get_cache()
    await cache.invalidate_serviceability(pincode)


# ==================== Allocation Rules (Admin) ====================

@router.get(
    "/rules",
    response_model=AllocationRuleList,
    summary="List allocation rules",
    description="List all order allocation rules"
)
@require_module("oms_fulfillment")
async def list_allocation_rules(
    channel_code: Optional[str] = Query(None, description="Filter by channel"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List allocation rules."""
    service = AllocationService(db)
    rules = await service.get_rules(channel_code=channel_code, is_active=is_active)

    response_items = []
    for rule in rules:
        response_items.append(AllocationRuleResponse(
            id=rule.id,
            name=rule.name,
            description=rule.description,
            channel_code=rule.channel_code if hasattr(rule.channel_code, 'value') else str(rule.channel_code),
            channel_id=rule.channel_id,
            channel_name=rule.channel.name if rule.channel else None,
            priority=rule.priority,
            allocation_type=rule.allocation_type if hasattr(rule.allocation_type, 'value') else str(rule.allocation_type),
            fixed_warehouse_id=rule.fixed_warehouse_id,
            fixed_warehouse_name=rule.fixed_warehouse.name if rule.fixed_warehouse else None,
            priority_factors=rule.priority_factors,
            min_order_value=rule.min_order_value,
            max_order_value=rule.max_order_value,
            payment_mode=rule.payment_mode,
            allow_split=rule.allow_split,
            max_splits=rule.max_splits,
            is_active=rule.is_active,
            created_at=rule.created_at,
            updated_at=rule.updated_at,
            created_by=rule.created_by
        ))

    return AllocationRuleList(items=response_items, total=len(response_items))


@router.post(
    "/rules",
    response_model=AllocationRuleResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create allocation rule",
    description="""
    Create a new order allocation rule.

    Allocation Types:
    - NEAREST: Allocate to nearest warehouse (by priority)
    - FIXED: Always use a specific warehouse
    - ROUND_ROBIN: Distribute evenly across warehouses
    - COST_OPTIMIZED: Select lowest shipping cost
    - PRIORITY: Use warehouse priority
    - FIFO: First In First Out (oldest stock)

    Priority Factors (comma-separated):
    - PROXIMITY: Distance-based
    - INVENTORY: Stock availability
    - COST: Shipping cost
    - SLA: Delivery time
    """
)
async def create_allocation_rule(
    data: AllocationRuleCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create allocation rule."""
    service = AllocationService(db)
    rule = await service.create_rule(data, created_by=current_user.id)
    return AllocationRuleResponse(
        id=rule.id,
        name=rule.name,
        description=rule.description,
        channel_code=rule.channel_code if hasattr(rule.channel_code, 'value') else str(rule.channel_code),
        channel_id=rule.channel_id,
        priority=rule.priority,
        allocation_type=rule.allocation_type if hasattr(rule.allocation_type, 'value') else str(rule.allocation_type),
        fixed_warehouse_id=rule.fixed_warehouse_id,
        priority_factors=rule.priority_factors,
        min_order_value=rule.min_order_value,
        max_order_value=rule.max_order_value,
        payment_mode=rule.payment_mode,
        allow_split=rule.allow_split,
        max_splits=rule.max_splits,
        is_active=rule.is_active,
        created_at=rule.created_at,
        updated_at=rule.updated_at,
        created_by=rule.created_by
    )


@router.get(
    "/rules/{rule_id}",
    response_model=AllocationRuleResponse,
    summary="Get allocation rule",
    description="Get allocation rule details"
)
@require_module("oms_fulfillment")
async def get_allocation_rule(
    rule_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get allocation rule by ID."""
    service = AllocationService(db)
    rule = await service.get_rule(rule_id)
    if not rule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Rule not found"
        )
    return AllocationRuleResponse(
        id=rule.id,
        name=rule.name,
        description=rule.description,
        channel_code=rule.channel_code if hasattr(rule.channel_code, 'value') else str(rule.channel_code),
        channel_id=rule.channel_id,
        priority=rule.priority,
        allocation_type=rule.allocation_type if hasattr(rule.allocation_type, 'value') else str(rule.allocation_type),
        fixed_warehouse_id=rule.fixed_warehouse_id,
        priority_factors=rule.priority_factors,
        min_order_value=rule.min_order_value,
        max_order_value=rule.max_order_value,
        payment_mode=rule.payment_mode,
        allow_split=rule.allow_split,
        max_splits=rule.max_splits,
        is_active=rule.is_active,
        created_at=rule.created_at,
        updated_at=rule.updated_at,
        created_by=rule.created_by
    )


@router.put(
    "/rules/{rule_id}",
    response_model=AllocationRuleResponse,
    summary="Update allocation rule",
    description="Update an existing allocation rule"
)
@require_module("oms_fulfillment")
async def update_allocation_rule(
    rule_id: UUID,
    data: AllocationRuleUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update allocation rule."""
    service = AllocationService(db)
    rule = await service.update_rule(rule_id, data)
    if not rule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Rule not found"
        )
    return AllocationRuleResponse(
        id=rule.id,
        name=rule.name,
        description=rule.description,
        channel_code=rule.channel_code if hasattr(rule.channel_code, 'value') else str(rule.channel_code),
        channel_id=rule.channel_id,
        priority=rule.priority,
        allocation_type=rule.allocation_type if hasattr(rule.allocation_type, 'value') else str(rule.allocation_type),
        fixed_warehouse_id=rule.fixed_warehouse_id,
        priority_factors=rule.priority_factors,
        min_order_value=rule.min_order_value,
        max_order_value=rule.max_order_value,
        payment_mode=rule.payment_mode,
        allow_split=rule.allow_split,
        max_splits=rule.max_splits,
        is_active=rule.is_active,
        created_at=rule.created_at,
        updated_at=rule.updated_at,
        created_by=rule.created_by
    )


@router.delete(
    "/rules/{rule_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete allocation rule",
    description="Delete an allocation rule"
)
@require_module("oms_fulfillment")
async def delete_allocation_rule(
    rule_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete allocation rule."""
    service = AllocationService(db)
    deleted = await service.delete_rule(rule_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Rule not found"
        )


# ==================== Order Allocation ====================

@router.post(
    "/allocate",
    response_model=AllocationDecision,
    summary="Allocate warehouse for order",
    description="""
    Allocate a warehouse for an order based on allocation rules.

    Flow:
    1. Check pincode serviceability
    2. Get applicable allocation rules for the channel
    3. Apply rules in priority order
    4. Check inventory availability
    5. Select best transporter
    6. Return allocation decision

    If allocation fails, returns alternatives if available.
    """
)
@require_module("oms_fulfillment")
async def allocate_order(
    request: OrderAllocationRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Allocate warehouse for an order."""
    service = AllocationService(db)
    return await service.allocate_order(request)


@router.get(
    "/allocation-logs",
    response_model=List[AllocationLogResponse],
    summary="Get allocation logs",
    description="Get order allocation decision logs"
)
@require_module("oms_fulfillment")
async def get_allocation_logs(
    order_id: Optional[UUID] = Query(None, description="Filter by order ID"),
    is_successful: Optional[bool] = Query(None, description="Filter by success status"),
    limit: int = Query(100, ge=1, le=1000),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get allocation logs."""
    service = AllocationService(db)
    logs = await service.get_allocation_logs(
        order_id=order_id,
        is_successful=is_successful,
        limit=limit
    )
    return [AllocationLogResponse(
        id=log.id,
        order_id=log.order_id,
        rule_id=log.rule_id,
        warehouse_id=log.warehouse_id,
        customer_pincode=log.customer_pincode,
        is_successful=log.is_successful,
        failure_reason=log.failure_reason,
        decision_factors=log.decision_factors,
        candidates_considered=log.candidates_considered,
        created_at=log.created_at
    ) for log in logs]


# ==================== Dashboard ====================

@router.get(
    "/dashboard",
    response_model=ServiceabilityDashboard,
    summary="Serviceability dashboard",
    description="Get serviceability and allocation statistics"
)
@require_module("oms_fulfillment")
async def get_dashboard(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get serviceability dashboard."""
    service = ServiceabilityService(db)
    return await service.get_dashboard()


# ==================== Cache Management ====================

@router.post(
    "/cache/clear",
    summary="Clear serviceability cache",
    description="Clear all cached serviceability data. Use this after bulk updates."
)
@require_module("oms_fulfillment")
async def clear_serviceability_cache(
    channel: Optional[str] = Query("D2C", description="Channel to clear cache for"),
    pincode: Optional[str] = Query(None, description="Specific pincode to clear (optional)"),
    current_user: User = Depends(get_current_user)
):
    """Clear serviceability cache."""
    cache = get_cache()

    if pincode:
        await cache.invalidate_serviceability(pincode, channel)
        return {"message": f"Cache cleared for pincode {pincode}", "channel": channel}
    else:
        count = await cache.invalidate_serviceability(channel=channel)
        return {"message": f"Cache cleared for {count} entries", "channel": channel}


@router.get(
    "/cache/status",
    summary="Get cache status",
    description="Check if caching is enabled and get cache configuration"
)
@require_module("oms_fulfillment")
async def get_cache_status(
    current_user: User = Depends(get_current_user)
):
    """Get cache status and configuration."""
    return {
        "enabled": settings.CACHE_ENABLED,
        "redis_configured": bool(settings.REDIS_URL),
        "serviceability_ttl_seconds": settings.SERVICEABILITY_CACHE_TTL,
        "product_ttl_seconds": settings.PRODUCT_CACHE_TTL,
    }


# ==================== Edge Sync Export ====================

@router.get(
    "/export/edge",
    summary="Export serviceability data for edge caching",
    description="""
    Export all active serviceability data in a format optimized for edge/CDN caching.
    This endpoint is designed for background sync jobs to populate edge stores
    (Vercel Edge Config, Cloudflare KV, static JSON files).

    **Usage:**
    - Call this from a cron job every 6-24 hours
    - Push the result to your edge store
    - Frontend reads from edge instead of hitting this API

    **Response format optimized for:**
    - Direct localStorage storage (single JSON object)
    - Static file generation (per-pincode or master index)
    - Edge KV stores (key-value pairs)
    """,
    include_in_schema=True,  # Show in docs for transparency
)
async def export_serviceability_for_edge(
    db: AsyncSession = Depends(get_db),
    format: str = Query("index", description="Output format: 'index' (all in one), 'flat' (array)"),
):
    """
    Export serviceability data for edge caching.

    No authentication required - data is public (serviceable pincodes).
    Rate limited in production.
    """
    from sqlalchemy import select
    from sqlalchemy.orm import selectinload
    from app.models.serviceability import WarehouseServiceability
    from datetime import datetime, timezone

    # Get all active warehouses that can fulfill orders
    from sqlalchemy import and_
    from app.models.warehouse import Warehouse

    stmt = (
        select(WarehouseServiceability)
        .join(Warehouse, WarehouseServiceability.warehouse_id == Warehouse.id)
        .where(
            and_(
                WarehouseServiceability.is_serviceable == True,
                WarehouseServiceability.is_active == True,
                Warehouse.is_active == True,
                Warehouse.can_fulfill_orders == True,
            )
        )
        .order_by(WarehouseServiceability.pincode, WarehouseServiceability.priority)
    )
    result = await db.execute(stmt)
    records = result.scalars().all()

    now = datetime.now(timezone.utc).isoformat()

    # IMPORTANT: Aggregate multiple warehouses per pincode
    # For customer-facing serviceability:
    # - serviceable: true if ANY warehouse serves it
    # - estimated_days: MIN (fastest delivery)
    # - shipping_cost: MIN (cheapest option shown, actual may vary)
    # - cod_available: true if ANY warehouse supports COD
    # - prepaid_available: true if ANY warehouse supports prepaid
    # - warehouse_count: number of warehouses (for hopping capability)

    from collections import defaultdict

    pincode_data = defaultdict(lambda: {
        "warehouses": [],
        "min_days": float('inf'),
        "min_cost": float('inf'),
        "cod": False,
        "prepaid": False,
        "zone": None,
        "city": None,
        "state": None,
    })

    for r in records:
        p = pincode_data[r.pincode]
        p["warehouses"].append(str(r.warehouse_id))

        # Track minimums (best options for customer)
        if r.estimated_days and r.estimated_days < p["min_days"]:
            p["min_days"] = r.estimated_days
        if r.shipping_cost is not None and float(r.shipping_cost) < p["min_cost"]:
            p["min_cost"] = float(r.shipping_cost)

        # COD/Prepaid: true if ANY warehouse supports it
        if r.cod_available:
            p["cod"] = True
        if r.prepaid_available:
            p["prepaid"] = True

        # Take first warehouse's zone/city/state (highest priority)
        if p["zone"] is None:
            p["zone"] = r.zone
            p["city"] = r.city
            p["state"] = r.state

    if format == "flat":
        # Array format - good for iteration
        return {
            "version": now,
            "total": len(pincode_data),
            "warehouse_records": len(records),
            "data": [
                {
                    "pincode": pincode,
                    "serviceable": True,
                    "cod": data["cod"],
                    "prepaid": data["prepaid"],
                    "days": data["min_days"] if data["min_days"] != float('inf') else None,
                    "cost": data["min_cost"] if data["min_cost"] != float('inf') else 0,
                    "zone": data["zone"],
                    "city": data["city"],
                    "state": data["state"],
                    "warehouse_count": len(data["warehouses"]),
                }
                for pincode, data in pincode_data.items()
            ]
        }
    else:
        # Index format - optimized for key lookup (pincode -> data)
        # This is the recommended format for localStorage/Edge Config
        pincodes = {}
        zones = {"LOCAL": [], "METRO": [], "REGIONAL": [], "NATIONAL": []}

        for pincode, data in pincode_data.items():
            pincodes[pincode] = {
                "s": True,  # serviceable (shortened for size)
                "c": data["cod"],  # cod available (from ANY warehouse)
                "p": data["prepaid"],  # prepaid available (from ANY warehouse)
                "d": data["min_days"] if data["min_days"] != float('inf') else 3,  # fastest delivery
                "$": data["min_cost"] if data["min_cost"] != float('inf') else 0,  # cheapest cost
                "z": data["zone"][0] if data["zone"] else "N",  # zone (first letter: L/M/R/N)
                "w": len(data["warehouses"]),  # warehouse count (for hopping indicator)
                "city": data["city"],
                "state": data["state"],
            }
            if data["zone"] and data["zone"] in zones:
                zones[data["zone"]].append(pincode)

        return {
            "v": now,  # version
            "n": len(pincodes),  # unique pincode count
            "r": len(records),  # total warehouse-pincode records
            "p": pincodes,  # pincode data (aggregated)
            "z": {k: len(v) for k, v in zones.items()},  # zone counts
        }
