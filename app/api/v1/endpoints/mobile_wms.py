"""
Mobile WMS API Endpoints - Phase 5: RF Scanner & Mobile Operations.

API endpoints for mobile warehouse operations including:
- Device registration and management
- Barcode scanning and validation
- Task queue management
- Pick confirmations
- Offline sync
"""
from datetime import datetime
from typing import Optional, List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies.auth import get_current_user, require_permissions
from app.models.user import User
from app.models.mobile_wms import DeviceType, DeviceStatus, ScanType
from app.schemas.mobile_wms import (
    MobileDeviceCreate, MobileDeviceUpdate, MobileDeviceAssign,
    MobileDeviceHeartbeat, MobileDeviceResponse,
    ScanLogCreate, ScanLogResponse, ScanValidationRequest, ScanValidationResponse,
    TaskQueueCreate, TaskQueueUpdate, TaskQueueResponse, WorkerTaskQueue,
    PickConfirmationCreate, PickConfirmationResponse,
    OfflineSyncBatch, OfflineSyncResponse, SyncBatchResult,
    MobileDashboard, DeviceStats, WarehouseDeviceStats
)
from app.services.mobile_wms_service import MobileWMSService

router = APIRouter()


# ============================================================================
# DEVICE MANAGEMENT
# ============================================================================

@router.post(
    "/devices",
    response_model=MobileDeviceResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register Mobile Device"
)
async def create_device(
    data: MobileDeviceCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions(["wms:manage"]))
):
    """Register a new mobile device (RF scanner, tablet, etc.)."""
    service = MobileWMSService(db, current_user.tenant_id)

    # Check for duplicate device code
    existing = await service.get_device_by_code(data.device_code)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Device with code {data.device_code} already exists"
        )

    return await service.create_device(data)


@router.get(
    "/devices",
    response_model=List[MobileDeviceResponse],
    summary="List Mobile Devices"
)
async def list_devices(
    warehouse_id: Optional[UUID] = None,
    status: Optional[DeviceStatus] = None,
    device_type: Optional[DeviceType] = None,
    is_online: Optional[bool] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions(["wms:read"]))
):
    """List mobile devices with filters."""
    service = MobileWMSService(db, current_user.tenant_id)
    devices, _ = await service.list_devices(
        warehouse_id=warehouse_id,
        status=status,
        device_type=device_type.value if device_type else None,
        is_online=is_online,
        skip=skip,
        limit=limit
    )
    return devices


@router.get(
    "/devices/{device_id}",
    response_model=MobileDeviceResponse,
    summary="Get Device Details"
)
async def get_device(
    device_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions(["wms:read"]))
):
    """Get mobile device details."""
    service = MobileWMSService(db, current_user.tenant_id)
    device = await service.get_device(device_id)
    if not device:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Device not found"
        )
    return device


@router.patch(
    "/devices/{device_id}",
    response_model=MobileDeviceResponse,
    summary="Update Device"
)
async def update_device(
    device_id: UUID,
    data: MobileDeviceUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions(["wms:manage"]))
):
    """Update mobile device details."""
    service = MobileWMSService(db, current_user.tenant_id)
    device = await service.update_device(device_id, data)
    if not device:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Device not found"
        )
    return device


@router.post(
    "/devices/{device_id}/assign",
    response_model=MobileDeviceResponse,
    summary="Assign Device to Worker"
)
async def assign_device(
    device_id: UUID,
    data: MobileDeviceAssign,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions(["wms:manage"]))
):
    """Assign device to a warehouse worker."""
    service = MobileWMSService(db, current_user.tenant_id)
    device = await service.assign_device(device_id, data.user_id)
    if not device:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Device not found"
        )
    return device


@router.post(
    "/devices/{device_id}/unassign",
    response_model=MobileDeviceResponse,
    summary="Unassign Device"
)
async def unassign_device(
    device_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions(["wms:manage"]))
):
    """Unassign device from worker."""
    service = MobileWMSService(db, current_user.tenant_id)
    device = await service.unassign_device(device_id)
    if not device:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Device not found"
        )
    return device


@router.post(
    "/devices/{device_id}/heartbeat",
    response_model=MobileDeviceResponse,
    summary="Update Device Heartbeat"
)
async def update_heartbeat(
    device_id: UUID,
    data: MobileDeviceHeartbeat,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update device heartbeat (battery, connectivity)."""
    service = MobileWMSService(db, current_user.tenant_id)
    device = await service.update_heartbeat(device_id, data)
    if not device:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Device not found"
        )
    return device


@router.get(
    "/devices/{device_id}/stats",
    response_model=DeviceStats,
    summary="Get Device Statistics"
)
async def get_device_stats(
    device_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions(["wms:read"]))
):
    """Get statistics for a mobile device."""
    service = MobileWMSService(db, current_user.tenant_id)
    stats = await service.get_device_stats(device_id)
    if not stats:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Device not found"
        )
    return stats


# ============================================================================
# BARCODE SCANNING
# ============================================================================

@router.post(
    "/scans",
    response_model=ScanLogResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Log Barcode Scan"
)
async def log_scan(
    data: ScanLogCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Log a barcode scan from mobile device."""
    service = MobileWMSService(db, current_user.tenant_id)
    return await service.log_scan(data, current_user.id)


@router.post(
    "/scans/validate",
    response_model=ScanValidationResponse,
    summary="Validate Barcode"
)
async def validate_scan(
    data: ScanValidationRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Validate a scanned barcode without logging."""
    service = MobileWMSService(db, current_user.tenant_id)
    return await service.validate_scan(data)


@router.get(
    "/scans",
    response_model=List[ScanLogResponse],
    summary="List Scan Logs"
)
async def list_scan_logs(
    device_id: Optional[UUID] = None,
    user_id: Optional[UUID] = None,
    warehouse_id: Optional[UUID] = None,
    scan_type: Optional[ScanType] = None,
    from_date: Optional[datetime] = None,
    to_date: Optional[datetime] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions(["wms:read"]))
):
    """List barcode scan logs with filters."""
    service = MobileWMSService(db, current_user.tenant_id)
    logs, _ = await service.get_scan_logs(
        device_id=device_id,
        user_id=user_id,
        warehouse_id=warehouse_id,
        scan_type=scan_type.value if scan_type else None,
        from_date=from_date,
        to_date=to_date,
        skip=skip,
        limit=limit
    )
    return logs


# ============================================================================
# TASK QUEUE MANAGEMENT
# ============================================================================

@router.post(
    "/task-queue",
    response_model=TaskQueueResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add Task to Queue"
)
async def create_task_queue(
    data: TaskQueueCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions(["wms:manage"]))
):
    """Add a task to worker's mobile queue."""
    service = MobileWMSService(db, current_user.tenant_id)
    return await service.create_task_queue(data)


@router.get(
    "/task-queue/my-tasks",
    response_model=WorkerTaskQueue,
    summary="Get My Task Queue"
)
async def get_my_task_queue(
    warehouse_id: Optional[UUID] = None,
    include_completed: bool = False,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get current user's task queue."""
    service = MobileWMSService(db, current_user.tenant_id)
    return await service.get_worker_queue(
        worker_id=current_user.id,
        warehouse_id=warehouse_id,
        include_completed=include_completed
    )


@router.get(
    "/task-queue/worker/{worker_id}",
    response_model=WorkerTaskQueue,
    summary="Get Worker's Task Queue"
)
async def get_worker_task_queue(
    worker_id: UUID,
    warehouse_id: Optional[UUID] = None,
    include_completed: bool = False,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions(["wms:read"]))
):
    """Get a worker's task queue."""
    service = MobileWMSService(db, current_user.tenant_id)
    return await service.get_worker_queue(
        worker_id=worker_id,
        warehouse_id=warehouse_id,
        include_completed=include_completed
    )


@router.get(
    "/task-queue/next",
    response_model=Optional[TaskQueueResponse],
    summary="Get Next Task"
)
async def get_next_task(
    warehouse_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get the next task for current worker."""
    service = MobileWMSService(db, current_user.tenant_id)
    return await service.get_next_task(current_user.id, warehouse_id)


@router.post(
    "/task-queue/{task_queue_id}/start",
    response_model=TaskQueueResponse,
    summary="Start Task"
)
async def start_task(
    task_queue_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Start working on a task."""
    service = MobileWMSService(db, current_user.tenant_id)
    task = await service.start_task(task_queue_id)
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )
    return task


@router.post(
    "/task-queue/{task_queue_id}/complete",
    response_model=TaskQueueResponse,
    summary="Complete Task"
)
async def complete_task(
    task_queue_id: UUID,
    quantity_completed: int = Query(..., ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Complete a task."""
    service = MobileWMSService(db, current_user.tenant_id)
    task = await service.complete_task(task_queue_id, quantity_completed)
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )
    return task


@router.post(
    "/task-queue/{task_queue_id}/skip",
    response_model=TaskQueueResponse,
    summary="Skip Task"
)
async def skip_task(
    task_queue_id: UUID,
    skip_reason: str = Query(..., max_length=200),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Skip a task with reason."""
    service = MobileWMSService(db, current_user.tenant_id)
    task = await service.skip_task(task_queue_id, skip_reason)
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )
    return task


# ============================================================================
# PICK CONFIRMATIONS
# ============================================================================

@router.post(
    "/pick-confirmations",
    response_model=PickConfirmationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Pick Confirmation"
)
async def create_pick_confirmation(
    data: PickConfirmationCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a pick confirmation from mobile device."""
    service = MobileWMSService(db, current_user.tenant_id)
    return await service.create_pick_confirmation(data, current_user.id)


@router.get(
    "/pick-confirmations",
    response_model=List[PickConfirmationResponse],
    summary="List Pick Confirmations"
)
async def list_pick_confirmations(
    task_id: Optional[UUID] = None,
    picklist_id: Optional[UUID] = None,
    user_id: Optional[UUID] = None,
    warehouse_id: Optional[UUID] = None,
    from_date: Optional[datetime] = None,
    to_date: Optional[datetime] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions(["wms:read"]))
):
    """List pick confirmations with filters."""
    service = MobileWMSService(db, current_user.tenant_id)
    confirmations, _ = await service.get_pick_confirmations(
        task_id=task_id,
        picklist_id=picklist_id,
        user_id=user_id,
        warehouse_id=warehouse_id,
        from_date=from_date,
        to_date=to_date,
        skip=skip,
        limit=limit
    )
    return confirmations


# ============================================================================
# OFFLINE SYNC
# ============================================================================

@router.post(
    "/sync",
    response_model=SyncBatchResult,
    summary="Sync Offline Data"
)
async def sync_offline_data(
    data: OfflineSyncBatch,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Sync offline data from mobile device."""
    service = MobileWMSService(db, current_user.tenant_id)
    return await service.process_offline_sync(data, current_user.id)


@router.get(
    "/sync/pending/{device_id}",
    response_model=List[OfflineSyncResponse],
    summary="Get Pending Sync Items"
)
async def get_pending_sync_items(
    device_id: UUID,
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get pending sync items for a device."""
    service = MobileWMSService(db, current_user.tenant_id)
    return await service.get_pending_sync_items(device_id, limit)


# ============================================================================
# MOBILE DASHBOARD
# ============================================================================

@router.get(
    "/dashboard",
    response_model=MobileDashboard,
    summary="Get Mobile Dashboard"
)
async def get_mobile_dashboard(
    warehouse_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get mobile dashboard for current worker."""
    service = MobileWMSService(db, current_user.tenant_id)
    return await service.get_worker_dashboard(current_user.id, warehouse_id)


@router.get(
    "/warehouse/{warehouse_id}/device-stats",
    response_model=WarehouseDeviceStats,
    summary="Get Warehouse Device Stats"
)
async def get_warehouse_device_stats(
    warehouse_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions(["wms:read"]))
):
    """Get device statistics for a warehouse."""
    service = MobileWMSService(db, current_user.tenant_id)
    return await service.get_warehouse_device_stats(warehouse_id)


# ============================================================================
# MAINTENANCE OPERATIONS
# ============================================================================

@router.post(
    "/devices/mark-offline",
    summary="Mark Offline Devices"
)
async def mark_offline_devices(
    timeout_minutes: int = Query(5, ge=1, le=60),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions(["wms:manage"]))
):
    """Mark devices as offline if no heartbeat in timeout period."""
    service = MobileWMSService(db, current_user.tenant_id)
    count = await service.mark_offline_devices(timeout_minutes)
    return {"marked_offline": count}


@router.post(
    "/devices/reset-daily-counts",
    summary="Reset Daily Scan Counts"
)
async def reset_daily_counts(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions(["wms:manage"]))
):
    """Reset daily scan counts for all devices (run at midnight)."""
    service = MobileWMSService(db, current_user.tenant_id)
    count = await service.reset_daily_scan_counts()
    return {"devices_reset": count}
