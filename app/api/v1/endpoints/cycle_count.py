"""
Cycle Counting API Endpoints - Phase 11: Cycle Counting & Physical Inventory.

API endpoints for cycle counting operations including:
- Count plans and scheduling
- Count sessions and tasks
- Variance investigation and resolution
- ABC classification
"""
from datetime import date
from typing import Optional, List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies.auth import get_current_user, require_permissions
from app.models.user import User
from app.models.cycle_count import (
    CountType, CountFrequency, CountPlanStatus, CountTaskStatus, VarianceStatus
)
from app.schemas.cycle_count import (
    CycleCountPlanCreate, CycleCountPlanUpdate, CycleCountPlanResponse,
    CountSessionCreate, CountSessionUpdate, CountSessionResponse,
    CountTaskCreate, CountTaskAssign, CountTaskCount, CountTaskRecount,
    CountTaskApprove, CountTaskResponse,
    CountDetailCreate, CountDetailResponse,
    VarianceInvestigate, VarianceApprove, VarianceWriteOff, InventoryVarianceResponse,
    ABCClassificationCreate, ABCClassificationUpdate, ABCClassificationResponse,
    ABCRecalculate,
    CycleCountDashboard, GenerateCountTasks
)
from app.services.cycle_count_service import CycleCountService

router = APIRouter()


# ============================================================================
# CYCLE COUNT PLANS
# ============================================================================

@router.post(
    "/plans",
    response_model=CycleCountPlanResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Cycle Count Plan"
)
async def create_plan(
    data: CycleCountPlanCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions(["wms:manage"]))
):
    """Create a new cycle count plan."""
    service = CycleCountService(db, current_user.tenant_id)
    return await service.create_plan(data, current_user.id)


@router.get(
    "/plans",
    response_model=List[CycleCountPlanResponse],
    summary="List Cycle Count Plans"
)
async def list_plans(
    warehouse_id: Optional[UUID] = None,
    status: Optional[CountPlanStatus] = None,
    count_type: Optional[CountType] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions(["wms:read"]))
):
    """List cycle count plans."""
    service = CycleCountService(db, current_user.tenant_id)
    plans, _ = await service.list_plans(
        warehouse_id=warehouse_id,
        status=status,
        count_type=count_type,
        skip=skip,
        limit=limit
    )
    return plans


@router.get(
    "/plans/{plan_id}",
    response_model=CycleCountPlanResponse,
    summary="Get Cycle Count Plan"
)
async def get_plan(
    plan_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions(["wms:read"]))
):
    """Get cycle count plan details."""
    service = CycleCountService(db, current_user.tenant_id)
    plan = await service.get_plan(plan_id)
    if not plan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Plan not found"
        )
    return plan


@router.patch(
    "/plans/{plan_id}",
    response_model=CycleCountPlanResponse,
    summary="Update Cycle Count Plan"
)
async def update_plan(
    plan_id: UUID,
    data: CycleCountPlanUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions(["wms:manage"]))
):
    """Update a cycle count plan."""
    service = CycleCountService(db, current_user.tenant_id)
    plan = await service.update_plan(plan_id, data)
    if not plan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Plan not found"
        )
    return plan


@router.post(
    "/plans/{plan_id}/activate",
    response_model=CycleCountPlanResponse,
    summary="Activate Cycle Count Plan"
)
async def activate_plan(
    plan_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions(["wms:manage"]))
):
    """Activate a cycle count plan."""
    service = CycleCountService(db, current_user.tenant_id)
    plan = await service.activate_plan(plan_id)
    if not plan:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Plan not found or cannot be activated"
        )
    return plan


@router.post(
    "/plans/{plan_id}/pause",
    response_model=CycleCountPlanResponse,
    summary="Pause Cycle Count Plan"
)
async def pause_plan(
    plan_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions(["wms:manage"]))
):
    """Pause a cycle count plan."""
    service = CycleCountService(db, current_user.tenant_id)
    plan = await service.pause_plan(plan_id)
    if not plan:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Plan not found or cannot be paused"
        )
    return plan


@router.post(
    "/plans/{plan_id}/generate-tasks",
    response_model=CountSessionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Generate Count Tasks from Plan"
)
async def generate_tasks_from_plan(
    plan_id: UUID,
    count_date: date = Query(default=None),
    assigned_to: Optional[UUID] = None,
    max_tasks: Optional[int] = Query(None, ge=1, le=1000),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions(["wms:manage"]))
):
    """Generate count tasks from a plan."""
    service = CycleCountService(db, current_user.tenant_id)
    data = GenerateCountTasks(
        plan_id=plan_id,
        count_date=count_date or date.today(),
        assigned_to=assigned_to,
        max_tasks=max_tasks
    )
    try:
        return await service.generate_tasks_from_plan(data, current_user.id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


# ============================================================================
# COUNT SESSIONS
# ============================================================================

@router.post(
    "/sessions",
    response_model=CountSessionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Count Session"
)
async def create_session(
    data: CountSessionCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions(["wms:manage"]))
):
    """Create a new count session."""
    service = CycleCountService(db, current_user.tenant_id)
    return await service.create_session(data, current_user.id)


@router.get(
    "/sessions",
    response_model=List[CountSessionResponse],
    summary="List Count Sessions"
)
async def list_sessions(
    warehouse_id: Optional[UUID] = None,
    plan_id: Optional[UUID] = None,
    status: Optional[CountTaskStatus] = None,
    from_date: Optional[date] = None,
    to_date: Optional[date] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions(["wms:read"]))
):
    """List count sessions."""
    service = CycleCountService(db, current_user.tenant_id)
    sessions, _ = await service.list_sessions(
        warehouse_id=warehouse_id,
        plan_id=plan_id,
        status=status,
        from_date=from_date,
        to_date=to_date,
        skip=skip,
        limit=limit
    )
    return sessions


@router.get(
    "/sessions/{session_id}",
    response_model=CountSessionResponse,
    summary="Get Count Session"
)
async def get_session(
    session_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions(["wms:read"]))
):
    """Get count session details."""
    service = CycleCountService(db, current_user.tenant_id)
    session = await service.get_session(session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )
    return session


@router.post(
    "/sessions/{session_id}/start",
    response_model=CountSessionResponse,
    summary="Start Count Session"
)
async def start_session(
    session_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions(["wms:manage"]))
):
    """Start a count session."""
    service = CycleCountService(db, current_user.tenant_id)
    session = await service.start_session(session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Session not found or cannot be started"
        )
    return session


@router.post(
    "/sessions/{session_id}/complete",
    response_model=CountSessionResponse,
    summary="Complete Count Session"
)
async def complete_session(
    session_id: UUID,
    notes: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions(["wms:manage"]))
):
    """Complete a count session."""
    service = CycleCountService(db, current_user.tenant_id)
    session = await service.complete_session(session_id, current_user.id, notes)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Session not found or has pending tasks"
        )
    return session


# ============================================================================
# COUNT TASKS
# ============================================================================

@router.post(
    "/tasks",
    response_model=CountTaskResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Count Task"
)
async def create_task(
    data: CountTaskCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions(["wms:manage"]))
):
    """Create a new count task."""
    service = CycleCountService(db, current_user.tenant_id)
    try:
        return await service.create_task(data)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get(
    "/tasks",
    response_model=List[CountTaskResponse],
    summary="List Count Tasks"
)
async def list_tasks(
    session_id: Optional[UUID] = None,
    assigned_to: Optional[UUID] = None,
    status: Optional[CountTaskStatus] = None,
    has_variance: Optional[bool] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions(["wms:read"]))
):
    """List count tasks."""
    service = CycleCountService(db, current_user.tenant_id)
    tasks, _ = await service.list_tasks(
        session_id=session_id,
        assigned_to=assigned_to,
        status=status,
        has_variance=has_variance,
        skip=skip,
        limit=limit
    )
    return tasks


@router.get(
    "/tasks/my-tasks",
    response_model=List[CountTaskResponse],
    summary="Get My Count Tasks"
)
async def get_my_tasks(
    status: Optional[CountTaskStatus] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions(["wms:read"]))
):
    """Get tasks assigned to current user."""
    service = CycleCountService(db, current_user.tenant_id)
    tasks, _ = await service.list_tasks(
        assigned_to=current_user.id,
        status=status,
        skip=skip,
        limit=limit
    )
    return tasks


@router.get(
    "/tasks/{task_id}",
    response_model=CountTaskResponse,
    summary="Get Count Task"
)
async def get_task(
    task_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions(["wms:read"]))
):
    """Get count task details."""
    service = CycleCountService(db, current_user.tenant_id)
    task = await service.get_task(task_id)
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )
    return task


@router.post(
    "/tasks/{task_id}/assign",
    response_model=CountTaskResponse,
    summary="Assign Count Task"
)
async def assign_task(
    task_id: UUID,
    data: CountTaskAssign,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions(["wms:manage"]))
):
    """Assign a count task to a user."""
    service = CycleCountService(db, current_user.tenant_id)
    task = await service.assign_task(task_id, data.assigned_to)
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )
    return task


@router.post(
    "/tasks/{task_id}/count",
    response_model=CountTaskResponse,
    summary="Record Count"
)
async def record_count(
    task_id: UUID,
    data: CountTaskCount,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions(["wms:manage"]))
):
    """Record a count for a task."""
    service = CycleCountService(db, current_user.tenant_id)
    task = await service.record_count(task_id, data, current_user.id)
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )
    return task


@router.post(
    "/tasks/{task_id}/recount",
    response_model=CountTaskResponse,
    summary="Record Recount"
)
async def record_recount(
    task_id: UUID,
    data: CountTaskRecount,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions(["wms:manage"]))
):
    """Record a recount for a task."""
    service = CycleCountService(db, current_user.tenant_id)
    task = await service.record_recount(task_id, data, current_user.id)
    if not task:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Task not found or recount not required"
        )
    return task


@router.post(
    "/tasks/{task_id}/approve",
    response_model=CountTaskResponse,
    summary="Approve Count Task"
)
async def approve_task(
    task_id: UUID,
    data: CountTaskApprove,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions(["wms:manage"]))
):
    """Approve or reject a count task."""
    service = CycleCountService(db, current_user.tenant_id)
    task = await service.approve_task(task_id, data, current_user.id)
    if not task:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Task not found or not pending review"
        )
    return task


# ============================================================================
# VARIANCES
# ============================================================================

@router.get(
    "/variances",
    response_model=List[InventoryVarianceResponse],
    summary="List Inventory Variances"
)
async def list_variances(
    warehouse_id: Optional[UUID] = None,
    session_id: Optional[UUID] = None,
    status: Optional[VarianceStatus] = None,
    product_id: Optional[UUID] = None,
    from_date: Optional[date] = None,
    to_date: Optional[date] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions(["wms:read"]))
):
    """List inventory variances."""
    service = CycleCountService(db, current_user.tenant_id)
    variances, _ = await service.list_variances(
        warehouse_id=warehouse_id,
        session_id=session_id,
        status=status,
        product_id=product_id,
        from_date=from_date,
        to_date=to_date,
        skip=skip,
        limit=limit
    )
    return variances


@router.get(
    "/variances/{variance_id}",
    response_model=InventoryVarianceResponse,
    summary="Get Variance"
)
async def get_variance(
    variance_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions(["wms:read"]))
):
    """Get variance details."""
    service = CycleCountService(db, current_user.tenant_id)
    variance = await service.get_variance(variance_id)
    if not variance:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Variance not found"
        )
    return variance


@router.post(
    "/variances/{variance_id}/investigate",
    response_model=InventoryVarianceResponse,
    summary="Investigate Variance"
)
async def investigate_variance(
    variance_id: UUID,
    data: VarianceInvestigate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions(["wms:manage"]))
):
    """Record investigation details for a variance."""
    service = CycleCountService(db, current_user.tenant_id)
    variance = await service.investigate_variance(variance_id, data, current_user.id)
    if not variance:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Variance not found"
        )
    return variance


@router.post(
    "/variances/{variance_id}/approve",
    response_model=InventoryVarianceResponse,
    summary="Approve Variance"
)
async def approve_variance(
    variance_id: UUID,
    data: VarianceApprove,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions(["wms:approve"]))
):
    """Approve variance for adjustment."""
    service = CycleCountService(db, current_user.tenant_id)
    variance = await service.approve_variance(variance_id, data, current_user.id)
    if not variance:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Variance not found"
        )
    return variance


@router.post(
    "/variances/{variance_id}/write-off",
    response_model=InventoryVarianceResponse,
    summary="Write Off Variance"
)
async def write_off_variance(
    variance_id: UUID,
    data: VarianceWriteOff,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions(["finance:manage"]))
):
    """Write off a variance."""
    service = CycleCountService(db, current_user.tenant_id)
    variance = await service.write_off_variance(variance_id, data, current_user.id)
    if not variance:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Variance not found"
        )
    return variance


# ============================================================================
# ABC CLASSIFICATION
# ============================================================================

@router.post(
    "/abc/recalculate",
    summary="Recalculate ABC Classification"
)
async def recalculate_abc(
    data: ABCRecalculate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions(["wms:manage"]))
):
    """Recalculate ABC classification for products."""
    service = CycleCountService(db, current_user.tenant_id)
    count = await service.recalculate_abc(data)
    return {"message": f"ABC classification recalculated for {count} products"}


# ============================================================================
# DASHBOARD
# ============================================================================

@router.get(
    "/dashboard",
    response_model=CycleCountDashboard,
    summary="Get Cycle Count Dashboard"
)
async def get_dashboard(
    warehouse_id: Optional[UUID] = None,
    from_date: date = Query(default=None),
    to_date: date = Query(default=None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions(["wms:read"]))
):
    """Get cycle counting dashboard statistics."""
    service = CycleCountService(db, current_user.tenant_id)
    return await service.get_dashboard(warehouse_id, from_date, to_date)
