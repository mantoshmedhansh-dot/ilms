"""
Distributed Order Management (DOM) API Endpoints.

Provides endpoints for:
- Fulfillment Node Management
- Routing Rule Configuration
- Order Orchestration
- ATP/ATF Checks
- Backorder Management
- Pre-order Management
"""
import uuid
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import DB, CurrentUser, require_permissions
from app.services.dom_service import DOMService
from app.schemas.dom import (
    # Fulfillment Node
    FulfillmentNodeCreate,
    FulfillmentNodeUpdate,
    FulfillmentNodeResponse,
    FulfillmentNodeListResponse,
    # Routing Rule
    RoutingRuleCreate,
    RoutingRuleUpdate,
    RoutingRuleResponse,
    RoutingRuleListResponse,
    # Orchestration
    OrchestrationRequest,
    OrchestrationResult,
    BulkOrchestrationRequest,
    BulkOrchestrationResponse,
    # ATP
    ATPCheckRequest,
    ATPCheckResponse,
    # Backorder
    BackorderCreate,
    BackorderUpdate,
    BackorderResponse,
    BackorderListResponse,
    BackorderAllocateRequest,
    BackorderAllocateResponse,
    # Preorder
    PreorderCreate,
    PreorderUpdate,
    PreorderResponse,
    PreorderListResponse,
    PreorderConvertRequest,
    PreorderConvertResponse,
    # Logs and Stats
    OrchestrationLogResponse,
    OrchestrationLogListResponse,
    DOMStats,
    NodePerformanceStats,
    # Enums
    FulfillmentNodeType,
    BackorderStatus,
    PreorderStatus,
)

router = APIRouter(tags=["Distributed Order Management"])


# ============================================================================
# FULFILLMENT NODES
# ============================================================================

@router.get(
    "/nodes",
    response_model=FulfillmentNodeListResponse,
    dependencies=[Depends(require_permissions("inventory:view"))]
)
async def list_fulfillment_nodes(
    db: DB,
    current_user: CurrentUser,
    node_type: Optional[str] = Query(None, description="Filter by node type"),
    is_active: Optional[bool] = Query(True, description="Filter by active status"),
    region_id: Optional[uuid.UUID] = Query(None, description="Filter by region"),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
):
    """List all fulfillment nodes with optional filters."""
    service = DOMService(db)
    nodes, total = await service.get_fulfillment_nodes(
        node_type=node_type,
        is_active=is_active,
        region_id=region_id,
        page=page,
        size=size,
    )
    return FulfillmentNodeListResponse(
        items=[FulfillmentNodeResponse.model_validate(n) for n in nodes],
        total=total,
        page=page,
        size=size,
        pages=(total + size - 1) // size,
    )


@router.get(
    "/nodes/dropdown",
    dependencies=[Depends(require_permissions("inventory:view"))]
)
async def get_nodes_dropdown(
    db: DB,
    current_user: CurrentUser,
    node_type: Optional[str] = Query(None),
):
    """Get nodes for dropdown selection."""
    service = DOMService(db)
    nodes, _ = await service.get_fulfillment_nodes(
        node_type=node_type,
        is_active=True,
        page=1,
        size=1000,
    )
    return [
        {"id": str(n.id), "code": n.code, "name": n.name, "type": n.node_type}
        for n in nodes
    ]


@router.get(
    "/nodes/{node_id}",
    response_model=FulfillmentNodeResponse,
    dependencies=[Depends(require_permissions("inventory:view"))]
)
async def get_fulfillment_node(
    node_id: uuid.UUID,
    db: DB,
    current_user: CurrentUser,
):
    """Get fulfillment node by ID."""
    service = DOMService(db)
    node = await service.get_fulfillment_node(node_id)
    if not node:
        raise HTTPException(status_code=404, detail="Fulfillment node not found")
    return FulfillmentNodeResponse.model_validate(node)


@router.post(
    "/nodes",
    response_model=FulfillmentNodeResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permissions("inventory:create"))]
)
async def create_fulfillment_node(
    data: FulfillmentNodeCreate,
    db: DB,
    current_user: CurrentUser,
):
    """Create a new fulfillment node."""
    service = DOMService(db)

    # Check for duplicate code
    existing = await service.get_fulfillment_node_by_code(data.code)
    if existing:
        raise HTTPException(status_code=400, detail="Node with this code already exists")

    node = await service.create_fulfillment_node(data, created_by=current_user.id)
    return FulfillmentNodeResponse.model_validate(node)


@router.put(
    "/nodes/{node_id}",
    response_model=FulfillmentNodeResponse,
    dependencies=[Depends(require_permissions("inventory:update"))]
)
async def update_fulfillment_node(
    node_id: uuid.UUID,
    data: FulfillmentNodeUpdate,
    db: DB,
    current_user: CurrentUser,
):
    """Update a fulfillment node."""
    service = DOMService(db)
    node = await service.update_fulfillment_node(node_id, data)
    if not node:
        raise HTTPException(status_code=404, detail="Fulfillment node not found")
    return FulfillmentNodeResponse.model_validate(node)


@router.post(
    "/nodes/sync-warehouses",
    dependencies=[Depends(require_permissions("inventory:create"))]
)
async def sync_nodes_from_warehouses(
    db: DB,
    current_user: CurrentUser,
):
    """
    Sync fulfillment nodes from existing warehouses.
    Creates nodes for warehouses that don't have corresponding nodes.
    """
    service = DOMService(db)
    created = await service.sync_nodes_from_warehouses()
    return {"message": f"Created {created} fulfillment nodes from warehouses"}


# ============================================================================
# ROUTING RULES
# ============================================================================

@router.get(
    "/routing-rules",
    response_model=RoutingRuleListResponse,
    dependencies=[Depends(require_permissions("orders:view"))]
)
async def list_routing_rules(
    db: DB,
    current_user: CurrentUser,
    is_active: Optional[bool] = Query(True),
    channel_id: Optional[uuid.UUID] = Query(None),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
):
    """List all routing rules with optional filters."""
    service = DOMService(db)
    rules, total = await service.get_routing_rules(
        is_active=is_active,
        channel_id=channel_id,
        page=page,
        size=size,
    )
    return RoutingRuleListResponse(
        items=[RoutingRuleResponse.model_validate(r) for r in rules],
        total=total,
        page=page,
        size=size,
        pages=(total + size - 1) // size,
    )


@router.get(
    "/routing-rules/{rule_id}",
    response_model=RoutingRuleResponse,
    dependencies=[Depends(require_permissions("orders:view"))]
)
async def get_routing_rule(
    rule_id: uuid.UUID,
    db: DB,
    current_user: CurrentUser,
):
    """Get routing rule by ID."""
    service = DOMService(db)
    rule = await service.get_routing_rule(rule_id)
    if not rule:
        raise HTTPException(status_code=404, detail="Routing rule not found")
    return RoutingRuleResponse.model_validate(rule)


@router.post(
    "/routing-rules",
    response_model=RoutingRuleResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permissions("orders:create"))]
)
async def create_routing_rule(
    data: RoutingRuleCreate,
    db: DB,
    current_user: CurrentUser,
):
    """Create a new routing rule."""
    service = DOMService(db)
    rule = await service.create_routing_rule(data, created_by=current_user.id)
    return RoutingRuleResponse.model_validate(rule)


@router.put(
    "/routing-rules/{rule_id}",
    response_model=RoutingRuleResponse,
    dependencies=[Depends(require_permissions("orders:update"))]
)
async def update_routing_rule(
    rule_id: uuid.UUID,
    data: RoutingRuleUpdate,
    db: DB,
    current_user: CurrentUser,
):
    """Update a routing rule."""
    service = DOMService(db)
    rule = await service.update_routing_rule(rule_id, data)
    if not rule:
        raise HTTPException(status_code=404, detail="Routing rule not found")
    return RoutingRuleResponse.model_validate(rule)


@router.delete(
    "/routing-rules/{rule_id}",
    dependencies=[Depends(require_permissions("orders:delete"))]
)
async def delete_routing_rule(
    rule_id: uuid.UUID,
    db: DB,
    current_user: CurrentUser,
):
    """Delete (deactivate) a routing rule."""
    service = DOMService(db)
    success = await service.delete_routing_rule(rule_id)
    if not success:
        raise HTTPException(status_code=404, detail="Routing rule not found")
    return {"message": "Routing rule deactivated"}


# ============================================================================
# ORDER ORCHESTRATION
# ============================================================================

@router.post(
    "/orchestrate",
    response_model=OrchestrationResult,
    dependencies=[Depends(require_permissions("orders:update"))]
)
async def orchestrate_order(
    request: OrchestrationRequest,
    db: DB,
    current_user: CurrentUser,
):
    """
    Orchestrate order fulfillment.

    This is the main DOM entry point that:
    1. Evaluates routing rules
    2. Checks inventory across nodes
    3. Selects optimal fulfillment node(s)
    4. Handles splitting if needed
    5. Creates backorders if inventory unavailable

    Use `dry_run=true` to simulate without making changes.
    """
    service = DOMService(db)
    result = await service.orchestrate_order(request)
    return result


@router.post(
    "/orchestrate/bulk",
    response_model=BulkOrchestrationResponse,
    dependencies=[Depends(require_permissions("orders:update"))]
)
async def orchestrate_orders_bulk(
    request: BulkOrchestrationRequest,
    db: DB,
    current_user: CurrentUser,
):
    """Orchestrate multiple orders in bulk."""
    service = DOMService(db)

    results = []
    successful = 0
    failed = 0

    for order_id in request.order_ids:
        single_request = OrchestrationRequest(
            order_id=order_id,
            allow_split=request.allow_split,
            allow_backorder=request.allow_backorder,
            dry_run=request.dry_run,
        )
        result = await service.orchestrate_order(single_request)
        results.append(result)

        if result.status.value in ["ROUTED", "SPLIT"]:
            successful += 1
        else:
            failed += 1

    return BulkOrchestrationResponse(
        total_orders=len(request.order_ids),
        successful=successful,
        failed=failed,
        results=results,
    )


@router.post(
    "/orchestrate/simulate",
    response_model=OrchestrationResult,
    dependencies=[Depends(require_permissions("orders:view"))]
)
async def simulate_orchestration(
    request: OrchestrationRequest,
    db: DB,
    current_user: CurrentUser,
):
    """
    Simulate order orchestration without making changes.
    Useful for testing routing rules and seeing potential decisions.
    """
    request.dry_run = True
    service = DOMService(db)
    result = await service.orchestrate_order(request)
    return result


# ============================================================================
# ATP/ATF CHECK
# ============================================================================

@router.post("/atp/check", response_model=ATPCheckResponse)
async def check_atp(
    request: ATPCheckRequest,
    db: DB,
):
    """
    Check Available to Promise (ATP) for products.

    Used during checkout to verify inventory availability before order placement.
    Returns availability across all nodes and recommends best fulfillment option.

    This endpoint is public (no auth) for storefront use.
    """
    service = DOMService(db)
    result = await service.check_atp(request)
    return result


# ============================================================================
# BACKORDERS
# ============================================================================

@router.get(
    "/backorders",
    response_model=BackorderListResponse,
    dependencies=[Depends(require_permissions("orders:view"))]
)
async def list_backorders(
    db: DB,
    current_user: CurrentUser,
    status: Optional[str] = Query(None, description="Filter by status"),
    product_id: Optional[uuid.UUID] = Query(None),
    order_id: Optional[uuid.UUID] = Query(None),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
):
    """List backorders with optional filters."""
    service = DOMService(db)
    backorders, total = await service.get_backorders(
        status=status,
        product_id=product_id,
        order_id=order_id,
        page=page,
        size=size,
    )
    return BackorderListResponse(
        items=[BackorderResponse.model_validate(b) for b in backorders],
        total=total,
        page=page,
        size=size,
        pages=(total + size - 1) // size,
    )


@router.post(
    "/backorders",
    response_model=BackorderResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permissions("orders:create"))]
)
async def create_backorder(
    data: BackorderCreate,
    db: DB,
    current_user: CurrentUser,
):
    """Create a backorder manually."""
    service = DOMService(db)
    backorder = await service.create_backorder(data)
    return BackorderResponse.model_validate(backorder)


@router.post(
    "/backorders/allocate",
    response_model=BackorderAllocateResponse,
    dependencies=[Depends(require_permissions("orders:update"))]
)
async def allocate_to_backorders(
    request: BackorderAllocateRequest,
    db: DB,
    current_user: CurrentUser,
):
    """
    Allocate incoming inventory to pending backorders.

    Call this when new inventory is received (e.g., GRN posted)
    to automatically fulfill waiting backorders.
    """
    service = DOMService(db)
    result = await service.allocate_to_backorders(
        product_id=request.product_id,
        variant_id=request.variant_id,
        quantity=request.quantity,
    )
    return BackorderAllocateResponse(**result)


# ============================================================================
# PREORDERS
# ============================================================================

@router.get(
    "/preorders",
    response_model=PreorderListResponse,
    dependencies=[Depends(require_permissions("orders:view"))]
)
async def list_preorders(
    db: DB,
    current_user: CurrentUser,
    status: Optional[str] = Query(None),
    product_id: Optional[uuid.UUID] = Query(None),
    customer_id: Optional[uuid.UUID] = Query(None),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
):
    """List pre-orders with optional filters."""
    service = DOMService(db)
    preorders, total = await service.get_preorders(
        status=status,
        product_id=product_id,
        customer_id=customer_id,
        page=page,
        size=size,
    )
    return PreorderListResponse(
        items=[PreorderResponse.model_validate(p) for p in preorders],
        total=total,
        page=page,
        size=size,
        pages=(total + size - 1) // size,
    )


@router.post(
    "/preorders",
    response_model=PreorderResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permissions("orders:create"))]
)
async def create_preorder(
    data: PreorderCreate,
    db: DB,
    current_user: CurrentUser,
):
    """Create a new pre-order."""
    service = DOMService(db)
    preorder = await service.create_preorder(data, created_by=current_user.id)
    return PreorderResponse.model_validate(preorder)


@router.post(
    "/preorders/{preorder_id}/convert",
    response_model=PreorderConvertResponse,
    dependencies=[Depends(require_permissions("orders:create"))]
)
async def convert_preorder(
    preorder_id: uuid.UUID,
    db: DB,
    current_user: CurrentUser,
):
    """Convert a pre-order to a regular order."""
    service = DOMService(db)
    result = await service.convert_preorder_to_order(preorder_id)
    if not result:
        raise HTTPException(
            status_code=400,
            detail="Pre-order not found or not in convertible status"
        )
    return PreorderConvertResponse(
        preorder_id=preorder_id,
        order_id=uuid.UUID(result.get('order_id', str(uuid.uuid4()))),
        order_number=result.get('order_number', ''),
        remaining_amount=result.get('remaining_amount', 0),
    )


# ============================================================================
# STATS & DASHBOARD
# ============================================================================

@router.get(
    "/stats",
    response_model=DOMStats,
    dependencies=[Depends(require_permissions("orders:view"))]
)
async def get_dom_stats(
    db: DB,
    current_user: CurrentUser,
):
    """Get DOM statistics and KPIs."""
    service = DOMService(db)
    return await service.get_stats()


@router.get(
    "/stats/node-types",
    dependencies=[Depends(require_permissions("orders:view"))]
)
async def get_node_type_distribution(
    db: DB,
    current_user: CurrentUser,
):
    """Get distribution of fulfillment nodes by type."""
    service = DOMService(db)
    nodes, _ = await service.get_fulfillment_nodes(is_active=True, page=1, size=1000)

    distribution = {}
    for node in nodes:
        node_type = node.node_type
        distribution[node_type] = distribution.get(node_type, 0) + 1

    return distribution


@router.get(
    "/logs",
    response_model=OrchestrationLogListResponse,
    dependencies=[Depends(require_permissions("orders:view"))]
)
async def list_orchestration_logs(
    db: DB,
    current_user: CurrentUser,
    order_id: Optional[uuid.UUID] = Query(None),
    status: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
):
    """List orchestration logs for audit and debugging."""
    from sqlalchemy import select, func
    from app.models.dom import OrchestrationLog

    query = select(OrchestrationLog)

    if order_id:
        query = query.where(OrchestrationLog.order_id == order_id)
    if status:
        query = query.where(OrchestrationLog.status == status)

    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar() or 0

    query = query.order_by(OrchestrationLog.created_at.desc())
    query = query.offset((page - 1) * size).limit(size)

    result = await db.execute(query)
    logs = list(result.scalars().all())

    return OrchestrationLogListResponse(
        items=[OrchestrationLogResponse.model_validate(log) for log in logs],
        total=total,
        page=page,
        size=size,
        pages=(total + size - 1) // size,
    )
