"""
Advanced WMS API Endpoints - Phase 2: Wave Picking & Task Interleaving.

Provides endpoints for:
- Wave Management (create, release, complete, cancel)
- Task Interleaving (get next task, start, complete, pause)
- Slot Optimization (run analysis, get recommendations)
- Cross-Docking workflows
- Worker Location tracking
"""
import uuid
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.deps import DB, CurrentUser, require_permissions
from app.services.wave_picking_service import WavePickingService
from app.schemas.wms_advanced import (
    # Wave
    WaveCreate,
    WaveUpdate,
    WaveResponse,
    WaveListResponse,
    WaveReleaseRequest,
    WaveReleaseResponse,
    WaveType,
    WaveStatus,
    # Task
    TaskCreate,
    TaskUpdate,
    TaskResponse,
    TaskListResponse,
    TaskStartRequest,
    TaskCompleteRequest,
    NextTaskRequest,
    NextTaskResponse,
    TaskType,
    TaskStatus,
    TaskPriority,
    # Slot Optimization
    SlotScoreResponse,
    SlotOptimizationRequest,
    SlotOptimizationResult,
    RelocationTaskCreate,
    # Cross-Dock
    CrossDockCreate,
    CrossDockResponse,
    # Worker
    WorkerLocationUpdate,
    WorkerLocationResponse,
    # Stats
    WMSAdvancedStats,
)

router = APIRouter(tags=["Advanced WMS"])


# ============================================================================
# WAVE PICKING
# ============================================================================

@router.get(
    "/waves",
    response_model=WaveListResponse,
    dependencies=[Depends(require_permissions("wms:view"))]
)
async def list_waves(
    db: DB,
    current_user: CurrentUser,
    warehouse_id: Optional[uuid.UUID] = Query(None),
    status: Optional[str] = Query(None),
    wave_type: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
):
    """List picking waves with optional filters."""
    service = WavePickingService(db)
    waves, total = await service.get_waves(
        warehouse_id=warehouse_id,
        status=status,
        wave_type=wave_type,
        page=page,
        size=size,
    )
    return WaveListResponse(
        items=[WaveResponse.model_validate(w) for w in waves],
        total=total,
        page=page,
        size=size,
        pages=(total + size - 1) // size,
    )


@router.get(
    "/waves/{wave_id}",
    response_model=WaveResponse,
    dependencies=[Depends(require_permissions("wms:view"))]
)
async def get_wave(
    wave_id: uuid.UUID,
    db: DB,
    current_user: CurrentUser,
):
    """Get wave details by ID."""
    service = WavePickingService(db)
    wave = await service.get_wave(wave_id)
    if not wave:
        raise HTTPException(status_code=404, detail="Wave not found")
    return WaveResponse.model_validate(wave)


@router.post(
    "/waves",
    response_model=WaveResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permissions("wms:create"))]
)
async def create_wave(
    data: WaveCreate,
    db: DB,
    current_user: CurrentUser,
):
    """
    Create a new picking wave.

    Wave types:
    - CARRIER_CUTOFF: Group orders by carrier pickup time
    - PRIORITY: Group by order priority/SLA
    - ZONE: Group by warehouse zone
    - PRODUCT: Group by product category
    - CHANNEL: Group by sales channel
    - CUSTOM: Custom rule-based grouping

    Set `auto_select_orders=true` to automatically select eligible orders.
    Set `auto_release=true` to immediately release the wave.
    """
    service = WavePickingService(db)

    # Get tenant_id from request state (set by middleware)
    tenant_id = getattr(current_user, 'tenant_id', None)
    if not tenant_id:
        # Fallback - use first role's tenant if available
        for role in current_user.roles:
            if hasattr(role, 'tenant_id'):
                tenant_id = role.tenant_id
                break

    if not tenant_id:
        raise HTTPException(status_code=400, detail="Tenant context required")

    wave = await service.create_wave(
        data=data,
        tenant_id=tenant_id,
        created_by=current_user.id
    )
    return WaveResponse.model_validate(wave)


@router.put(
    "/waves/{wave_id}",
    response_model=WaveResponse,
    dependencies=[Depends(require_permissions("wms:update"))]
)
async def update_wave(
    wave_id: uuid.UUID,
    data: WaveUpdate,
    db: DB,
    current_user: CurrentUser,
):
    """Update wave configuration (only for DRAFT/PLANNED waves)."""
    service = WavePickingService(db)
    wave = await service.get_wave(wave_id)

    if not wave:
        raise HTTPException(status_code=404, detail="Wave not found")

    if wave.status not in [WaveStatus.DRAFT.value, WaveStatus.PLANNED.value]:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot update wave in status: {wave.status}"
        )

    # Update allowed fields
    if data.name is not None:
        wave.name = data.name
    if data.cutoff_time is not None:
        wave.cutoff_time = data.cutoff_time
    if data.cutoff_date is not None:
        wave.cutoff_date = data.cutoff_date
    if data.optimize_route is not None:
        wave.optimize_route = data.optimize_route
    if data.group_by_zone is not None:
        wave.group_by_zone = data.group_by_zone
    if data.max_picks_per_trip is not None:
        wave.max_picks_per_trip = data.max_picks_per_trip
    if data.notes is not None:
        wave.notes = data.notes

    await db.commit()
    await db.refresh(wave)
    return WaveResponse.model_validate(wave)


@router.post(
    "/waves/{wave_id}/release",
    response_model=WaveReleaseResponse,
    dependencies=[Depends(require_permissions("wms:update"))]
)
async def release_wave(
    wave_id: uuid.UUID,
    request: WaveReleaseRequest,
    db: DB,
    current_user: CurrentUser,
):
    """
    Release wave to warehouse floor.

    This creates pick tasks for all picklist items and optionally
    assigns pickers to the tasks.
    """
    service = WavePickingService(db)
    try:
        result = await service.release_wave(
            wave_id=wave_id,
            request=request,
            released_by=current_user.id
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post(
    "/waves/{wave_id}/complete",
    response_model=WaveResponse,
    dependencies=[Depends(require_permissions("wms:update"))]
)
async def complete_wave(
    wave_id: uuid.UUID,
    db: DB,
    current_user: CurrentUser,
):
    """Mark wave as completed."""
    service = WavePickingService(db)
    try:
        wave = await service.complete_wave(wave_id)
        return WaveResponse.model_validate(wave)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post(
    "/waves/{wave_id}/cancel",
    response_model=WaveResponse,
    dependencies=[Depends(require_permissions("wms:delete"))]
)
async def cancel_wave(
    wave_id: uuid.UUID,
    reason: str = Query(..., min_length=1),
    db: DB = None,
    current_user: CurrentUser = None,
):
    """Cancel a wave with reason."""
    service = WavePickingService(db)
    try:
        wave = await service.cancel_wave(wave_id, reason)
        return WaveResponse.model_validate(wave)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get(
    "/waves/stats",
    dependencies=[Depends(require_permissions("wms:view"))]
)
async def get_waves_stats(
    db: DB,
    current_user: CurrentUser,
    warehouse_id: Optional[uuid.UUID] = Query(None),
):
    """Get wave statistics for dashboard."""
    from sqlalchemy import select, func, and_, Integer
    from app.models.wms_advanced import PickWave, WaveStatus
    from app.models.orders import Order, OrderStatus
    from datetime import datetime, timezone

    today_start = datetime.now(timezone.utc).replace(
        hour=0, minute=0, second=0, microsecond=0
    )

    # Build base filter
    wave_filters = []
    if warehouse_id:
        wave_filters.append(PickWave.warehouse_id == warehouse_id)

    # Total waves count
    total_result = await db.execute(
        select(func.count()).select_from(PickWave).where(and_(*wave_filters) if wave_filters else True)
    )
    total_waves = total_result.scalar() or 0

    # Active waves (IN_PROGRESS or RELEASED)
    active_filters = wave_filters.copy()
    active_filters.append(PickWave.status.in_([WaveStatus.IN_PROGRESS.value, WaveStatus.RELEASED.value]))
    active_result = await db.execute(
        select(func.count()).select_from(PickWave).where(and_(*active_filters) if active_filters else True)
    )
    active_waves = active_result.scalar() or 0

    # Completed today
    completed_filters = wave_filters.copy()
    completed_filters.extend([
        PickWave.status == WaveStatus.COMPLETED.value,
        PickWave.completed_at >= today_start
    ])
    completed_result = await db.execute(
        select(func.count()).select_from(PickWave).where(and_(*completed_filters))
    )
    completed_today = completed_result.scalar() or 0

    # Pending orders (orders ready to be added to waves)
    try:
        pending_result = await db.execute(
            select(func.count()).select_from(Order).where(
                and_(
                    Order.status.in_([OrderStatus.CONFIRMED.value, OrderStatus.PROCESSING.value]),
                    Order.is_active == True
                )
            )
        )
        pending_orders = pending_result.scalar() or 0
    except Exception:
        pending_orders = 0

    return {
        "total_waves": total_waves,
        "active_waves": active_waves,
        "completed_today": completed_today,
        "pending_orders": pending_orders
    }


# ============================================================================
# TASK INTERLEAVING
# ============================================================================

@router.get(
    "/tasks",
    response_model=TaskListResponse,
    dependencies=[Depends(require_permissions("wms:view"))]
)
async def list_tasks(
    db: DB,
    current_user: CurrentUser,
    warehouse_id: Optional[uuid.UUID] = Query(None),
    task_type: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    assigned_to: Optional[uuid.UUID] = Query(None),
    wave_id: Optional[uuid.UUID] = Query(None),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
):
    """List warehouse tasks with filters."""
    from sqlalchemy import select, func
    from app.models.wms_advanced import WarehouseTask

    query = select(WarehouseTask)

    if warehouse_id:
        query = query.where(WarehouseTask.warehouse_id == warehouse_id)
    if task_type:
        query = query.where(WarehouseTask.task_type == task_type)
    if status:
        query = query.where(WarehouseTask.status == status)
    if assigned_to:
        query = query.where(WarehouseTask.assigned_to == assigned_to)
    if wave_id:
        query = query.where(WarehouseTask.wave_id == wave_id)

    # Count
    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar() or 0

    # Paginate
    query = (
        query
        .order_by(WarehouseTask.created_at.desc())
        .offset((page - 1) * size)
        .limit(size)
    )
    result = await db.execute(query)
    tasks = list(result.scalars().all())

    return TaskListResponse(
        items=[TaskResponse.model_validate(t) for t in tasks],
        total=total,
        page=page,
        size=size,
        pages=(total + size - 1) // size,
    )


@router.get(
    "/tasks/{task_id}",
    response_model=TaskResponse,
    dependencies=[Depends(require_permissions("wms:view"))]
)
async def get_task(
    task_id: uuid.UUID,
    db: DB,
    current_user: CurrentUser,
):
    """Get task details by ID."""
    from sqlalchemy import select
    from app.models.wms_advanced import WarehouseTask

    result = await db.execute(
        select(WarehouseTask).where(WarehouseTask.id == task_id)
    )
    task = result.scalar_one_or_none()

    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    return TaskResponse.model_validate(task)


@router.post(
    "/tasks/next",
    response_model=NextTaskResponse,
    dependencies=[Depends(require_permissions("wms:update"))]
)
async def get_next_task(
    request: NextTaskRequest,
    db: DB,
    current_user: CurrentUser,
):
    """
    Get the optimal next task for a worker.

    Uses task interleaving to minimize travel time by considering:
    - Task priority and SLA deadlines
    - Worker's current location in the warehouse
    - Distance to task location
    - Equipment requirements

    Returns the best task along with travel estimates and alternatives.
    """
    service = WavePickingService(db)

    # Get tenant_id
    tenant_id = getattr(current_user, 'tenant_id', None)
    if not tenant_id:
        for role in current_user.roles:
            if hasattr(role, 'tenant_id'):
                tenant_id = role.tenant_id
                break

    if not tenant_id:
        raise HTTPException(status_code=400, detail="Tenant context required")

    result = await service.get_next_task(request, tenant_id)
    return result


@router.post(
    "/tasks/{task_id}/start",
    response_model=TaskResponse,
    dependencies=[Depends(require_permissions("wms:update"))]
)
async def start_task(
    task_id: uuid.UUID,
    request: TaskStartRequest,
    db: DB,
    current_user: CurrentUser,
):
    """Start working on a task."""
    service = WavePickingService(db)
    try:
        task = await service.start_task(
            task_id=task_id,
            worker_id=current_user.id,
            equipment_type=request.equipment_type,
            equipment_id=request.equipment_id
        )
        return TaskResponse.model_validate(task)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post(
    "/tasks/{task_id}/complete",
    response_model=TaskResponse,
    dependencies=[Depends(require_permissions("wms:update"))]
)
async def complete_task(
    task_id: uuid.UUID,
    request: TaskCompleteRequest,
    db: DB,
    current_user: CurrentUser,
):
    """
    Complete a task.

    For pick tasks, specify:
    - quantity_completed: Items successfully picked
    - quantity_exception: Items not found/damaged
    - picked_serials: Serial numbers (if applicable)

    For putaway tasks, specify:
    - destination_bin_id: Actual bin where items were placed
    """
    service = WavePickingService(db)
    try:
        task = await service.complete_task(
            task_id=task_id,
            worker_id=current_user.id,
            data=request
        )
        return TaskResponse.model_validate(task)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post(
    "/tasks/{task_id}/pause",
    response_model=TaskResponse,
    dependencies=[Depends(require_permissions("wms:update"))]
)
async def pause_task(
    task_id: uuid.UUID,
    reason: str = Query(..., min_length=1),
    db: DB = None,
    current_user: CurrentUser = None,
):
    """Pause a task with reason."""
    service = WavePickingService(db)
    try:
        task = await service.pause_task(task_id, reason)
        return TaskResponse.model_validate(task)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ============================================================================
# SLOT OPTIMIZATION
# ============================================================================

@router.post(
    "/slot-optimization/analyze",
    response_model=SlotOptimizationResult,
    dependencies=[Depends(require_permissions("wms:create"))]
)
async def run_slot_optimization(
    request: SlotOptimizationRequest,
    db: DB,
    current_user: CurrentUser,
):
    """
    Run slot optimization analysis.

    Analyzes pick history to classify products by velocity (ABC) and
    recommends optimal bin placements to minimize pick travel time.

    Parameters:
    - analysis_days: Number of days of pick history to analyze (7-365)
    - min_picks_threshold: Minimum picks to be included in analysis
    - abc_thresholds: Custom ABC cutoffs (default: A=80%, B=95%)
    """
    service = WavePickingService(db)

    tenant_id = getattr(current_user, 'tenant_id', None)
    if not tenant_id:
        for role in current_user.roles:
            if hasattr(role, 'tenant_id'):
                tenant_id = role.tenant_id
                break

    if not tenant_id:
        raise HTTPException(status_code=400, detail="Tenant context required")

    result = await service.run_slot_optimization(request, tenant_id)
    return result


@router.get(
    "/slot-optimization/scores",
    response_model=List[SlotScoreResponse],
    dependencies=[Depends(require_permissions("wms:view"))]
)
async def get_slot_scores(
    warehouse_id: uuid.UUID,
    db: DB,
    current_user: CurrentUser,
    velocity_class: Optional[str] = Query(None),
    needs_relocation: Optional[bool] = Query(None),
    limit: int = Query(100, ge=1, le=500),
):
    """Get slot optimization scores for products."""
    from sqlalchemy import select
    from app.models.wms_advanced import SlotScore

    query = select(SlotScore).where(SlotScore.warehouse_id == warehouse_id)

    if velocity_class:
        query = query.where(SlotScore.velocity_class == velocity_class)

    if needs_relocation is True:
        query = query.where(
            SlotScore.recommended_bin_id.isnot(None),
            SlotScore.recommended_bin_id != SlotScore.current_bin_id
        )

    query = query.order_by(SlotScore.total_score.desc()).limit(limit)

    result = await db.execute(query)
    scores = list(result.scalars().all())

    return [SlotScoreResponse.model_validate(s) for s in scores]


@router.post(
    "/slot-optimization/create-relocation-tasks",
    response_model=dict,
    dependencies=[Depends(require_permissions("wms:create"))]
)
async def create_relocation_tasks(
    request: RelocationTaskCreate,
    db: DB,
    current_user: CurrentUser,
):
    """Create relocation tasks from slot optimization recommendations."""
    from sqlalchemy import select
    from app.models.wms_advanced import SlotScore, WarehouseTask, TaskType, TaskStatus
    from datetime import datetime, timezone

    tenant_id = getattr(current_user, 'tenant_id', None)
    if not tenant_id:
        for role in current_user.roles:
            if hasattr(role, 'tenant_id'):
                tenant_id = role.tenant_id
                break

    if not tenant_id:
        raise HTTPException(status_code=400, detail="Tenant context required")

    # Get slot scores
    result = await db.execute(
        select(SlotScore).where(SlotScore.id.in_(request.slot_score_ids))
    )
    scores = list(result.scalars().all())

    tasks_created = 0
    for score in scores:
        if score.recommended_bin_id and score.recommended_bin_id != score.current_bin_id:
            task_number = f"TK-{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"

            task = WarehouseTask(
                tenant_id=tenant_id,
                task_number=task_number,
                task_type=TaskType.RELOCATE.value,
                status=TaskStatus.PENDING.value,
                priority=request.priority.value,
                warehouse_id=score.warehouse_id,
                source_bin_id=score.current_bin_id,
                destination_bin_id=score.recommended_bin_id,
                product_id=score.product_id,
                variant_id=score.variant_id,
                sku=score.sku,
                quantity_required=0,  # Will be determined at execution
                due_at=request.schedule_for,
                instruction=f"Relocate SKU {score.sku} to optimize pick efficiency",
                created_by=current_user.id,
            )
            db.add(task)
            tasks_created += 1

    await db.commit()

    return {"tasks_created": tasks_created}


# ============================================================================
# CROSS-DOCKING
# ============================================================================

@router.post(
    "/cross-dock",
    response_model=CrossDockResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permissions("wms:create"))]
)
async def create_cross_dock(
    data: CrossDockCreate,
    db: DB,
    current_user: CurrentUser,
):
    """
    Create a cross-docking workflow.

    Cross-docking enables direct dock-to-dock flow for JIT orders,
    bypassing storage to reduce handling time.

    Types:
    - FLOW_THROUGH: Direct transfer (no storage)
    - MERGE_IN_TRANSIT: Consolidate multiple inbound shipments
    - BREAK_BULK: Split large shipments for multiple orders
    - OPPORTUNISTIC: JIT for urgent orders
    """
    from app.models.wms_advanced import CrossDock
    from datetime import datetime, timezone

    tenant_id = getattr(current_user, 'tenant_id', None)
    if not tenant_id:
        for role in current_user.roles:
            if hasattr(role, 'tenant_id'):
                tenant_id = role.tenant_id
                break

    if not tenant_id:
        raise HTTPException(status_code=400, detail="Tenant context required")

    cross_dock_number = f"XD-{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"

    cross_dock = CrossDock(
        tenant_id=tenant_id,
        cross_dock_number=cross_dock_number,
        cross_dock_type=data.cross_dock_type.value,
        warehouse_id=data.warehouse_id,
        inbound_grn_id=data.inbound_grn_id,
        inbound_po_id=data.inbound_po_id,
        inbound_dock=data.inbound_dock,
        expected_arrival=data.expected_arrival,
        outbound_order_ids={"ids": [str(o) for o in data.outbound_order_ids]} if data.outbound_order_ids else None,
        outbound_dock=data.outbound_dock,
        scheduled_departure=data.scheduled_departure,
        items=data.items,
        notes=data.notes,
        created_by=current_user.id,
    )
    db.add(cross_dock)
    await db.commit()
    await db.refresh(cross_dock)

    return CrossDockResponse.model_validate(cross_dock)


@router.get(
    "/cross-dock/{cross_dock_id}",
    response_model=CrossDockResponse,
    dependencies=[Depends(require_permissions("wms:view"))]
)
async def get_cross_dock(
    cross_dock_id: uuid.UUID,
    db: DB,
    current_user: CurrentUser,
):
    """Get cross-dock details."""
    from sqlalchemy import select
    from app.models.wms_advanced import CrossDock

    result = await db.execute(
        select(CrossDock).where(CrossDock.id == cross_dock_id)
    )
    cross_dock = result.scalar_one_or_none()

    if not cross_dock:
        raise HTTPException(status_code=404, detail="Cross-dock not found")

    return CrossDockResponse.model_validate(cross_dock)


# ============================================================================
# WORKER LOCATION
# ============================================================================

@router.post(
    "/worker/location",
    response_model=WorkerLocationResponse,
    dependencies=[Depends(require_permissions("wms:update"))]
)
async def update_worker_location(
    request: WorkerLocationUpdate,
    db: DB,
    current_user: CurrentUser,
):
    """
    Update worker location (from RF gun scan).

    Called when worker scans a bin to update their location for
    task interleaving optimization.
    """
    from sqlalchemy import select
    from app.models.wms_advanced import WorkerLocation
    from datetime import datetime, timezone

    tenant_id = getattr(current_user, 'tenant_id', None)
    if not tenant_id:
        for role in current_user.roles:
            if hasattr(role, 'tenant_id'):
                tenant_id = role.tenant_id
                break

    if not tenant_id:
        raise HTTPException(status_code=400, detail="Tenant context required")

    # Get or create worker location
    result = await db.execute(
        select(WorkerLocation).where(
            WorkerLocation.user_id == current_user.id,
            WorkerLocation.warehouse_id == request.warehouse_id
        )
    )
    worker_loc = result.scalar_one_or_none()

    if worker_loc:
        worker_loc.current_bin_code = request.bin_code
        worker_loc.current_zone_id = request.zone_id
        worker_loc.equipment_type = request.equipment_type
        worker_loc.equipment_id = request.equipment_id
        worker_loc.last_scan_at = datetime.now(timezone.utc)
        worker_loc.is_active = True
    else:
        worker_loc = WorkerLocation(
            tenant_id=tenant_id,
            user_id=current_user.id,
            warehouse_id=request.warehouse_id,
            current_bin_code=request.bin_code,
            current_zone_id=request.zone_id,
            equipment_type=request.equipment_type,
            equipment_id=request.equipment_id,
            is_active=True,
        )
        db.add(worker_loc)

    await db.commit()
    await db.refresh(worker_loc)

    return WorkerLocationResponse.model_validate(worker_loc)


@router.get(
    "/worker/location",
    response_model=WorkerLocationResponse,
    dependencies=[Depends(require_permissions("wms:view"))]
)
async def get_worker_location(
    warehouse_id: uuid.UUID,
    db: DB,
    current_user: CurrentUser,
):
    """Get current worker location and stats."""
    from sqlalchemy import select
    from app.models.wms_advanced import WorkerLocation

    result = await db.execute(
        select(WorkerLocation).where(
            WorkerLocation.user_id == current_user.id,
            WorkerLocation.warehouse_id == warehouse_id
        )
    )
    worker_loc = result.scalar_one_or_none()

    if not worker_loc:
        raise HTTPException(status_code=404, detail="Worker location not found")

    return WorkerLocationResponse.model_validate(worker_loc)


# ============================================================================
# STATISTICS
# ============================================================================

@router.get(
    "/stats",
    response_model=WMSAdvancedStats,
    dependencies=[Depends(require_permissions("wms:view"))]
)
async def get_wms_stats(
    warehouse_id: uuid.UUID,
    db: DB,
    current_user: CurrentUser,
):
    """Get advanced WMS statistics."""
    from sqlalchemy import select, func, and_
    from app.models.wms_advanced import (
        PickWave, WarehouseTask, SlotScore, CrossDock,
        WaveStatus, TaskStatus, WorkerLocation
    )
    from datetime import datetime, timezone, timedelta

    today_start = datetime.now(timezone.utc).replace(
        hour=0, minute=0, second=0, microsecond=0
    )

    # Wave stats
    wave_result = await db.execute(
        select(
            func.count().label('total'),
            func.sum(func.cast(PickWave.status == WaveStatus.IN_PROGRESS.value, Integer)).label('in_progress'),
            func.sum(func.cast(PickWave.status == WaveStatus.COMPLETED.value, Integer)).label('completed'),
        )
        .where(
            and_(
                PickWave.warehouse_id == warehouse_id,
                PickWave.created_at >= today_start
            )
        )
    )
    wave_row = wave_result.one()

    # Task stats
    task_result = await db.execute(
        select(
            func.count().label('total'),
            func.sum(func.cast(WarehouseTask.status == TaskStatus.COMPLETED.value, Integer)).label('completed'),
            func.sum(func.cast(WarehouseTask.status == TaskStatus.IN_PROGRESS.value, Integer)).label('in_progress'),
        )
        .where(
            and_(
                WarehouseTask.warehouse_id == warehouse_id,
                WarehouseTask.created_at >= today_start
            )
        )
    )
    task_row = task_result.one()

    # Active workers
    worker_result = await db.execute(
        select(func.count())
        .select_from(WorkerLocation)
        .where(
            and_(
                WorkerLocation.warehouse_id == warehouse_id,
                WorkerLocation.is_active == True,
                WorkerLocation.last_scan_at >= today_start - timedelta(hours=1)
            )
        )
    )
    active_workers = worker_result.scalar() or 0

    # Slot optimization needs
    slot_result = await db.execute(
        select(func.count())
        .select_from(SlotScore)
        .where(
            and_(
                SlotScore.warehouse_id == warehouse_id,
                SlotScore.recommended_bin_id.isnot(None),
                SlotScore.recommended_bin_id != SlotScore.current_bin_id
            )
        )
    )
    relocation_needed = slot_result.scalar() or 0

    # Cross-dock stats
    cross_dock_result = await db.execute(
        select(func.count())
        .select_from(CrossDock)
        .where(
            and_(
                CrossDock.warehouse_id == warehouse_id,
                CrossDock.status.notin_(['COMPLETED', 'CANCELLED'])
            )
        )
    )
    active_cross_docks = cross_dock_result.scalar() or 0

    from app.schemas.wms_advanced import WaveStats, TaskInterleavingStats

    return WMSAdvancedStats(
        wave_stats=WaveStats(
            total_waves_today=wave_row.total or 0,
            waves_in_progress=wave_row.in_progress or 0,
            waves_completed=wave_row.completed or 0,
            waves_past_cutoff=0,  # TODO: Calculate
            total_orders_in_waves=0,
            total_items_to_pick=0,
            total_items_picked=0,
            average_wave_completion_minutes=None,
            on_time_completion_rate=0.0,
        ),
        task_stats=TaskInterleavingStats(
            total_tasks_today=task_row.total or 0,
            tasks_by_type={},
            tasks_completed=task_row.completed or 0,
            tasks_in_progress=task_row.in_progress or 0,
            average_travel_time_seconds=None,
            average_execution_time_seconds=None,
            average_efficiency_score=None,
            active_workers=active_workers,
            tasks_per_worker_avg=0.0,
        ),
        products_needing_relocation=relocation_needed,
        pending_relocation_tasks=0,
        active_cross_docks=active_cross_docks,
        cross_docks_completed_today=0,
    )
