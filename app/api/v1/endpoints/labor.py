"""
Labor Management API Endpoints - Phase 4: Workforce Optimization.

Endpoints for:
- Worker profiles and skills
- Shift scheduling and time tracking
- Labor standards
- Productivity metrics
- Leave management
"""
import uuid
from typing import Optional, List
from datetime import date

from fastapi import APIRouter, Depends, Query, HTTPException, status

from app.api.deps import DB, CurrentUser, require_permissions
from app.services.labor_service import LaborService
from app.schemas.labor import (
    # Worker
    WorkerCreate, WorkerUpdate, WorkerResponse, WorkerListResponse,
    # Shift
    ShiftCreate, ShiftUpdate, ClockInRequest, ClockOutRequest,
    BulkShiftCreate, ShiftResponse, ShiftListResponse,
    # Template
    ShiftTemplateCreate, ShiftTemplateResponse,
    # Labor Standard
    LaborStandardCreate, LaborStandardResponse,
    # Productivity
    ProductivityMetricResponse, ProductivityMetricListResponse,
    # Leave
    LeaveRequestCreate, LeaveRequestUpdate, LeaveRequestResponse, LeaveRequestListResponse,
    # Stats
    LaborDashboardStats
)

router = APIRouter()


# ============================================================================
# WORKER ENDPOINTS
# ============================================================================

@router.post(
    "/workers",
    response_model=WorkerResponse,
    dependencies=[Depends(require_permissions("labor.workers.create"))]
)
async def create_worker(
    data: WorkerCreate,
    db: DB,
    current_user: CurrentUser
):
    """Create a warehouse worker profile."""
    service = LaborService(db, current_user.tenant_id)
    worker = await service.create_worker(data, current_user.id)
    await db.commit()
    return worker


@router.get(
    "/workers",
    response_model=WorkerListResponse,
    dependencies=[Depends(require_permissions("labor.workers.read"))]
)
async def list_workers(
    db: DB,
    current_user: CurrentUser,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    warehouse_id: Optional[uuid.UUID] = None,
    status: Optional[str] = None,
    worker_type: Optional[str] = None,
    supervisor_id: Optional[uuid.UUID] = None,
    search: Optional[str] = None
):
    """List warehouse workers."""
    service = LaborService(db, current_user.tenant_id)
    skip = (page - 1) * size
    workers, total = await service.get_workers(
        skip=skip,
        limit=size,
        warehouse_id=warehouse_id,
        status=status,
        worker_type=worker_type,
        supervisor_id=supervisor_id,
        search=search
    )
    pages = (total + size - 1) // size

    return WorkerListResponse(
        items=workers,
        total=total,
        page=page,
        size=size,
        pages=pages
    )


@router.get(
    "/workers/{worker_id}",
    response_model=WorkerResponse,
    dependencies=[Depends(require_permissions("labor.workers.read"))]
)
async def get_worker(
    worker_id: uuid.UUID,
    db: DB,
    current_user: CurrentUser
):
    """Get worker by ID."""
    service = LaborService(db, current_user.tenant_id)
    return await service.get_worker(worker_id)


@router.patch(
    "/workers/{worker_id}",
    response_model=WorkerResponse,
    dependencies=[Depends(require_permissions("labor.workers.update"))]
)
async def update_worker(
    worker_id: uuid.UUID,
    data: WorkerUpdate,
    db: DB,
    current_user: CurrentUser
):
    """Update worker profile."""
    service = LaborService(db, current_user.tenant_id)
    worker = await service.update_worker(worker_id, data)
    await db.commit()
    return worker


@router.post(
    "/workers/{worker_id}/terminate",
    response_model=WorkerResponse,
    dependencies=[Depends(require_permissions("labor.workers.update"))]
)
async def terminate_worker(
    worker_id: uuid.UUID,
    termination_date: date,
    reason: Optional[str] = None,
    db: DB = None,
    current_user: CurrentUser = None
):
    """Terminate a worker."""
    service = LaborService(db, current_user.tenant_id)
    worker = await service.terminate_worker(worker_id, termination_date, reason)
    await db.commit()
    return worker


# ============================================================================
# SHIFT ENDPOINTS
# ============================================================================

@router.post(
    "/shifts",
    response_model=ShiftResponse,
    dependencies=[Depends(require_permissions("labor.shifts.create"))]
)
async def create_shift(
    data: ShiftCreate,
    db: DB,
    current_user: CurrentUser
):
    """Create a work shift."""
    service = LaborService(db, current_user.tenant_id)
    shift = await service.create_shift(data, current_user.id)
    await db.commit()
    return shift


@router.post(
    "/shifts/bulk",
    response_model=List[ShiftResponse],
    dependencies=[Depends(require_permissions("labor.shifts.create"))]
)
async def create_bulk_shifts(
    data: BulkShiftCreate,
    db: DB,
    current_user: CurrentUser
):
    """Create shifts for multiple workers."""
    service = LaborService(db, current_user.tenant_id)
    shifts = await service.create_bulk_shifts(data, current_user.id)
    await db.commit()
    return shifts


@router.get(
    "/shifts",
    response_model=ShiftListResponse,
    dependencies=[Depends(require_permissions("labor.shifts.read"))]
)
async def list_shifts(
    db: DB,
    current_user: CurrentUser,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    worker_id: Optional[uuid.UUID] = None,
    warehouse_id: Optional[uuid.UUID] = None,
    shift_date: Optional[date] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    status: Optional[str] = None
):
    """List work shifts."""
    service = LaborService(db, current_user.tenant_id)
    skip = (page - 1) * size
    shifts, total = await service.get_shifts(
        skip=skip,
        limit=size,
        worker_id=worker_id,
        warehouse_id=warehouse_id,
        shift_date=shift_date,
        date_from=date_from,
        date_to=date_to,
        status=status
    )
    pages = (total + size - 1) // size

    return ShiftListResponse(
        items=shifts,
        total=total,
        page=page,
        size=size,
        pages=pages
    )


@router.get(
    "/shifts/{shift_id}",
    response_model=ShiftResponse,
    dependencies=[Depends(require_permissions("labor.shifts.read"))]
)
async def get_shift(
    shift_id: uuid.UUID,
    db: DB,
    current_user: CurrentUser
):
    """Get shift by ID."""
    service = LaborService(db, current_user.tenant_id)
    return await service.get_shift(shift_id)


@router.post(
    "/shifts/{shift_id}/clock-in",
    response_model=ShiftResponse,
    dependencies=[Depends(require_permissions("labor.shifts.update"))]
)
async def clock_in(
    shift_id: uuid.UUID,
    data: ClockInRequest,
    db: DB,
    current_user: CurrentUser
):
    """Clock in for a shift."""
    service = LaborService(db, current_user.tenant_id)
    shift = await service.clock_in(shift_id, data)
    await db.commit()
    return shift


@router.post(
    "/shifts/{shift_id}/clock-out",
    response_model=ShiftResponse,
    dependencies=[Depends(require_permissions("labor.shifts.update"))]
)
async def clock_out(
    shift_id: uuid.UUID,
    data: ClockOutRequest,
    db: DB,
    current_user: CurrentUser
):
    """Clock out from a shift."""
    service = LaborService(db, current_user.tenant_id)
    shift = await service.clock_out(shift_id, data)
    await db.commit()
    return shift


@router.post(
    "/shifts/{shift_id}/no-show",
    response_model=ShiftResponse,
    dependencies=[Depends(require_permissions("labor.shifts.update"))]
)
async def mark_no_show(
    shift_id: uuid.UUID,
    reason: Optional[str] = None,
    db: DB = None,
    current_user: CurrentUser = None
):
    """Mark shift as no-show."""
    service = LaborService(db, current_user.tenant_id)
    shift = await service.mark_no_show(shift_id, reason)
    await db.commit()
    return shift


@router.post(
    "/shifts/{shift_id}/cancel",
    response_model=ShiftResponse,
    dependencies=[Depends(require_permissions("labor.shifts.update"))]
)
async def cancel_shift(
    shift_id: uuid.UUID,
    reason: Optional[str] = None,
    db: DB = None,
    current_user: CurrentUser = None
):
    """Cancel a shift."""
    service = LaborService(db, current_user.tenant_id)
    shift = await service.cancel_shift(shift_id, reason)
    await db.commit()
    return shift


# ============================================================================
# SHIFT TEMPLATE ENDPOINTS
# ============================================================================

@router.post(
    "/shift-templates",
    response_model=ShiftTemplateResponse,
    dependencies=[Depends(require_permissions("labor.templates.create"))]
)
async def create_shift_template(
    data: ShiftTemplateCreate,
    db: DB,
    current_user: CurrentUser
):
    """Create a shift template."""
    service = LaborService(db, current_user.tenant_id)
    template = await service.create_shift_template(data)
    await db.commit()
    return template


@router.get(
    "/shift-templates",
    response_model=List[ShiftTemplateResponse],
    dependencies=[Depends(require_permissions("labor.templates.read"))]
)
async def list_shift_templates(
    db: DB,
    current_user: CurrentUser,
    warehouse_id: Optional[uuid.UUID] = None
):
    """List shift templates."""
    service = LaborService(db, current_user.tenant_id)
    return await service.get_shift_templates(warehouse_id)


# ============================================================================
# LABOR STANDARD ENDPOINTS
# ============================================================================

@router.post(
    "/standards",
    response_model=LaborStandardResponse,
    dependencies=[Depends(require_permissions("labor.standards.create"))]
)
async def create_labor_standard(
    data: LaborStandardCreate,
    db: DB,
    current_user: CurrentUser
):
    """Create a labor standard."""
    service = LaborService(db, current_user.tenant_id)
    standard = await service.create_labor_standard(data, current_user.id)
    await db.commit()
    return standard


@router.get(
    "/standards",
    response_model=List[LaborStandardResponse],
    dependencies=[Depends(require_permissions("labor.standards.read"))]
)
async def list_labor_standards(
    db: DB,
    current_user: CurrentUser,
    warehouse_id: Optional[uuid.UUID] = None,
    function: Optional[str] = None,
    active_only: bool = True
):
    """List labor standards."""
    service = LaborService(db, current_user.tenant_id)
    return await service.get_labor_standards(
        warehouse_id=warehouse_id,
        function=function,
        active_only=active_only
    )


# ============================================================================
# PRODUCTIVITY METRICS ENDPOINTS
# ============================================================================

@router.get(
    "/productivity",
    response_model=ProductivityMetricListResponse,
    dependencies=[Depends(require_permissions("labor.productivity.read"))]
)
async def list_productivity_metrics(
    db: DB,
    current_user: CurrentUser,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    worker_id: Optional[uuid.UUID] = None,
    warehouse_id: Optional[uuid.UUID] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    function: Optional[str] = None
):
    """List productivity metrics."""
    service = LaborService(db, current_user.tenant_id)
    skip = (page - 1) * size
    metrics, total = await service.get_productivity_metrics(
        skip=skip,
        limit=size,
        worker_id=worker_id,
        warehouse_id=warehouse_id,
        date_from=date_from,
        date_to=date_to,
        function=function
    )
    pages = (total + size - 1) // size

    return ProductivityMetricListResponse(
        items=metrics,
        total=total,
        page=page,
        size=size,
        pages=pages
    )


@router.post(
    "/productivity/calculate/{worker_id}",
    response_model=ProductivityMetricResponse,
    dependencies=[Depends(require_permissions("labor.productivity.update"))]
)
async def calculate_productivity(
    worker_id: uuid.UUID,
    metric_date: date,
    db: DB,
    current_user: CurrentUser
):
    """Calculate daily productivity for a worker."""
    service = LaborService(db, current_user.tenant_id)
    metric = await service.calculate_daily_productivity(worker_id, metric_date)
    if not metric:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No completed shift found for this date"
        )
    await db.commit()
    return metric


# ============================================================================
# LEAVE REQUEST ENDPOINTS
# ============================================================================

@router.post(
    "/leave-requests",
    response_model=LeaveRequestResponse,
    dependencies=[Depends(require_permissions("labor.leave.create"))]
)
async def create_leave_request(
    data: LeaveRequestCreate,
    db: DB,
    current_user: CurrentUser
):
    """Create a leave request."""
    service = LaborService(db, current_user.tenant_id)
    leave_req = await service.create_leave_request(data)
    await db.commit()
    return leave_req


@router.get(
    "/leave-requests",
    response_model=LeaveRequestListResponse,
    dependencies=[Depends(require_permissions("labor.leave.read"))]
)
async def list_leave_requests(
    db: DB,
    current_user: CurrentUser,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    worker_id: Optional[uuid.UUID] = None,
    status: Optional[str] = None
):
    """List leave requests."""
    service = LaborService(db, current_user.tenant_id)
    skip = (page - 1) * size
    requests, total = await service.get_leave_requests(
        skip=skip,
        limit=size,
        worker_id=worker_id,
        status=status
    )
    pages = (total + size - 1) // size

    return LeaveRequestListResponse(
        items=requests,
        total=total,
        page=page,
        size=size,
        pages=pages
    )


@router.get(
    "/leave-requests/{request_id}",
    response_model=LeaveRequestResponse,
    dependencies=[Depends(require_permissions("labor.leave.read"))]
)
async def get_leave_request(
    request_id: uuid.UUID,
    db: DB,
    current_user: CurrentUser
):
    """Get leave request by ID."""
    service = LaborService(db, current_user.tenant_id)
    return await service.get_leave_request(request_id)


@router.post(
    "/leave-requests/{request_id}/approve",
    response_model=LeaveRequestResponse,
    dependencies=[Depends(require_permissions("labor.leave.approve"))]
)
async def approve_leave_request(
    request_id: uuid.UUID,
    db: DB,
    current_user: CurrentUser
):
    """Approve a leave request."""
    service = LaborService(db, current_user.tenant_id)
    leave_req = await service.approve_leave_request(request_id, current_user.id)
    await db.commit()
    return leave_req


@router.post(
    "/leave-requests/{request_id}/reject",
    response_model=LeaveRequestResponse,
    dependencies=[Depends(require_permissions("labor.leave.approve"))]
)
async def reject_leave_request(
    request_id: uuid.UUID,
    reason: str,
    db: DB,
    current_user: CurrentUser
):
    """Reject a leave request."""
    service = LaborService(db, current_user.tenant_id)
    leave_req = await service.reject_leave_request(request_id, reason, current_user.id)
    await db.commit()
    return leave_req


# ============================================================================
# DASHBOARD ENDPOINTS
# ============================================================================

@router.get(
    "/stats",
    response_model=LaborDashboardStats,
    dependencies=[Depends(require_permissions("labor.stats.read"))]
)
async def get_labor_dashboard(
    db: DB,
    current_user: CurrentUser,
    warehouse_id: Optional[uuid.UUID] = None
):
    """Get labor management dashboard statistics."""
    service = LaborService(db, current_user.tenant_id)
    return await service.get_labor_dashboard_stats(warehouse_id)
