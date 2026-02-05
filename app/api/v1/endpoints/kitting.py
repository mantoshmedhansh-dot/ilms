"""
Kitting & Assembly API Endpoints - Phase 8: Kit Management & Assembly Operations.

API endpoints for kitting and assembly including:
- Kit definitions and components
- Assembly stations
- Work orders
- Build records
"""
from datetime import date
from typing import Optional, List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.api.deps import get_current_user, require_permissions
from app.models.user import User
from app.models.kitting import (
    KitType, KitStatus, ComponentType, WorkOrderType,
    WorkOrderStatus, WorkOrderPriority, BuildStatus, StationStatus
)
from app.schemas.kitting import (
    KitDefinitionCreate, KitDefinitionUpdate, KitDefinitionResponse,
    KitComponentCreate, KitComponentUpdate, KitComponentResponse,
    AssemblyStationCreate, AssemblyStationUpdate, AssemblyStationResponse, StationAssignment,
    KitWorkOrderCreate, KitWorkOrderUpdate, KitWorkOrderResponse,
    WorkOrderRelease, WorkOrderCancel,
    KitBuildRecordCreate, KitBuildRecordResponse,
    BuildStart, BuildComplete, BuildFail, BuildQC,
    KitDashboard
)
from app.services.kitting_service import KittingService

router = APIRouter()


# ============================================================================
# KIT DEFINITIONS
# ============================================================================

@router.post(
    "/kits",
    response_model=KitDefinitionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Kit Definition"
)
async def create_kit(
    data: KitDefinitionCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions(["wms:manage"]))
):
    """Create a new kit definition."""
    service = KittingService(db, current_user.tenant_id)
    return await service.create_kit(data, current_user.id)


@router.get(
    "/kits",
    response_model=List[KitDefinitionResponse],
    summary="List Kit Definitions"
)
async def list_kits(
    warehouse_id: Optional[UUID] = None,
    kit_type: Optional[KitType] = None,
    status: Optional[KitStatus] = None,
    search: Optional[str] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions(["wms:read"]))
):
    """List kit definitions."""
    service = KittingService(db, current_user.tenant_id)
    kits, _ = await service.list_kits(
        warehouse_id=warehouse_id,
        kit_type=kit_type,
        status=status,
        search=search,
        skip=skip,
        limit=limit
    )
    return kits


@router.get(
    "/kits/{kit_id}",
    response_model=KitDefinitionResponse,
    summary="Get Kit Definition"
)
async def get_kit(
    kit_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions(["wms:read"]))
):
    """Get kit definition details."""
    service = KittingService(db, current_user.tenant_id)
    kit = await service.get_kit(kit_id)
    if not kit:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Kit definition not found"
        )
    return kit


@router.patch(
    "/kits/{kit_id}",
    response_model=KitDefinitionResponse,
    summary="Update Kit Definition"
)
async def update_kit(
    kit_id: UUID,
    data: KitDefinitionUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions(["wms:manage"]))
):
    """Update kit definition."""
    service = KittingService(db, current_user.tenant_id)
    kit = await service.update_kit(kit_id, data)
    if not kit:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Kit definition not found"
        )
    return kit


@router.post(
    "/kits/{kit_id}/activate",
    response_model=KitDefinitionResponse,
    summary="Activate Kit"
)
async def activate_kit(
    kit_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions(["wms:manage"]))
):
    """Activate a kit definition."""
    service = KittingService(db, current_user.tenant_id)
    kit = await service.activate_kit(kit_id)
    if not kit:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Kit definition not found"
        )
    return kit


@router.post(
    "/kits/{kit_id}/deactivate",
    response_model=KitDefinitionResponse,
    summary="Deactivate Kit"
)
async def deactivate_kit(
    kit_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions(["wms:manage"]))
):
    """Deactivate a kit definition."""
    service = KittingService(db, current_user.tenant_id)
    kit = await service.deactivate_kit(kit_id)
    if not kit:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Kit definition not found"
        )
    return kit


# ============================================================================
# KIT COMPONENTS
# ============================================================================

@router.post(
    "/kits/{kit_id}/components",
    response_model=KitComponentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add Component"
)
async def add_component(
    kit_id: UUID,
    data: KitComponentCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions(["wms:manage"]))
):
    """Add component to kit."""
    service = KittingService(db, current_user.tenant_id)
    component = await service.add_component(kit_id, data)
    if not component:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Kit definition not found"
        )
    return component


@router.patch(
    "/components/{component_id}",
    response_model=KitComponentResponse,
    summary="Update Component"
)
async def update_component(
    component_id: UUID,
    data: KitComponentUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions(["wms:manage"]))
):
    """Update kit component."""
    service = KittingService(db, current_user.tenant_id)
    component = await service.update_component(component_id, data)
    if not component:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Component not found"
        )
    return component


@router.delete(
    "/components/{component_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove Component"
)
async def remove_component(
    component_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions(["wms:manage"]))
):
    """Remove component from kit."""
    service = KittingService(db, current_user.tenant_id)
    removed = await service.remove_component(component_id)
    if not removed:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Component not found"
        )


# ============================================================================
# ASSEMBLY STATIONS
# ============================================================================

@router.post(
    "/stations",
    response_model=AssemblyStationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Assembly Station"
)
async def create_station(
    data: AssemblyStationCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions(["wms:manage"]))
):
    """Create an assembly station."""
    service = KittingService(db, current_user.tenant_id)
    return await service.create_station(data)


@router.get(
    "/stations",
    response_model=List[AssemblyStationResponse],
    summary="List Assembly Stations"
)
async def list_stations(
    warehouse_id: Optional[UUID] = None,
    status: Optional[StationStatus] = None,
    is_active: bool = True,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions(["wms:read"]))
):
    """List assembly stations."""
    service = KittingService(db, current_user.tenant_id)
    stations, _ = await service.list_stations(
        warehouse_id=warehouse_id,
        status=status,
        is_active=is_active,
        skip=skip,
        limit=limit
    )
    return stations


@router.get(
    "/stations/{station_id}",
    response_model=AssemblyStationResponse,
    summary="Get Assembly Station"
)
async def get_station(
    station_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions(["wms:read"]))
):
    """Get assembly station details."""
    service = KittingService(db, current_user.tenant_id)
    station = await service.get_station(station_id)
    if not station:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Assembly station not found"
        )
    return station


@router.patch(
    "/stations/{station_id}",
    response_model=AssemblyStationResponse,
    summary="Update Assembly Station"
)
async def update_station(
    station_id: UUID,
    data: AssemblyStationUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions(["wms:manage"]))
):
    """Update assembly station."""
    service = KittingService(db, current_user.tenant_id)
    station = await service.update_station(station_id, data)
    if not station:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Assembly station not found"
        )
    return station


@router.post(
    "/stations/{station_id}/assign",
    response_model=AssemblyStationResponse,
    summary="Assign Worker to Station"
)
async def assign_worker(
    station_id: UUID,
    data: StationAssignment,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions(["wms:manage"]))
):
    """Assign worker to assembly station."""
    service = KittingService(db, current_user.tenant_id)
    station = await service.assign_worker_to_station(station_id, data)
    if not station:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Assembly station not found"
        )
    return station


@router.post(
    "/stations/{station_id}/release",
    response_model=AssemblyStationResponse,
    summary="Release Station"
)
async def release_station(
    station_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions(["wms:manage"]))
):
    """Release worker from assembly station."""
    service = KittingService(db, current_user.tenant_id)
    station = await service.release_station(station_id)
    if not station:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Assembly station not found"
        )
    return station


# ============================================================================
# WORK ORDERS
# ============================================================================

@router.post(
    "/work-orders",
    response_model=KitWorkOrderResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Work Order"
)
async def create_work_order(
    data: KitWorkOrderCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions(["wms:manage"]))
):
    """Create a kit work order."""
    service = KittingService(db, current_user.tenant_id)
    return await service.create_work_order(data, current_user.id)


@router.get(
    "/work-orders",
    response_model=List[KitWorkOrderResponse],
    summary="List Work Orders"
)
async def list_work_orders(
    warehouse_id: Optional[UUID] = None,
    kit_id: Optional[UUID] = None,
    status: Optional[WorkOrderStatus] = None,
    work_order_type: Optional[WorkOrderType] = None,
    priority: Optional[WorkOrderPriority] = None,
    from_date: Optional[date] = None,
    to_date: Optional[date] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions(["wms:read"]))
):
    """List kit work orders."""
    service = KittingService(db, current_user.tenant_id)
    work_orders, _ = await service.list_work_orders(
        warehouse_id=warehouse_id,
        kit_id=kit_id,
        status=status,
        work_order_type=work_order_type,
        priority=priority,
        from_date=from_date,
        to_date=to_date,
        skip=skip,
        limit=limit
    )
    return work_orders


@router.get(
    "/work-orders/{work_order_id}",
    response_model=KitWorkOrderResponse,
    summary="Get Work Order"
)
async def get_work_order(
    work_order_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions(["wms:read"]))
):
    """Get work order details."""
    service = KittingService(db, current_user.tenant_id)
    work_order = await service.get_work_order(work_order_id)
    if not work_order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Work order not found"
        )
    return work_order


@router.patch(
    "/work-orders/{work_order_id}",
    response_model=KitWorkOrderResponse,
    summary="Update Work Order"
)
async def update_work_order(
    work_order_id: UUID,
    data: KitWorkOrderUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions(["wms:manage"]))
):
    """Update work order."""
    service = KittingService(db, current_user.tenant_id)
    work_order = await service.update_work_order(work_order_id, data)
    if not work_order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Work order not found"
        )
    return work_order


@router.post(
    "/work-orders/{work_order_id}/release",
    response_model=KitWorkOrderResponse,
    summary="Release Work Order"
)
async def release_work_order(
    work_order_id: UUID,
    data: Optional[WorkOrderRelease] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions(["wms:manage"]))
):
    """Release work order for production."""
    service = KittingService(db, current_user.tenant_id)
    work_order = await service.release_work_order(work_order_id, data)
    if not work_order:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Work order not found or cannot be released"
        )
    return work_order


@router.post(
    "/work-orders/{work_order_id}/start",
    response_model=KitWorkOrderResponse,
    summary="Start Work Order"
)
async def start_work_order(
    work_order_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions(["wms:manage"]))
):
    """Start work on a work order."""
    service = KittingService(db, current_user.tenant_id)
    work_order = await service.start_work_order(work_order_id)
    if not work_order:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Work order not found or cannot be started"
        )
    return work_order


@router.post(
    "/work-orders/{work_order_id}/complete",
    response_model=KitWorkOrderResponse,
    summary="Complete Work Order"
)
async def complete_work_order(
    work_order_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions(["wms:manage"]))
):
    """Complete a work order."""
    service = KittingService(db, current_user.tenant_id)
    work_order = await service.complete_work_order(work_order_id)
    if not work_order:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Work order not found or cannot be completed"
        )
    return work_order


@router.post(
    "/work-orders/{work_order_id}/cancel",
    response_model=KitWorkOrderResponse,
    summary="Cancel Work Order"
)
async def cancel_work_order(
    work_order_id: UUID,
    data: WorkOrderCancel,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions(["wms:manage"]))
):
    """Cancel a work order."""
    service = KittingService(db, current_user.tenant_id)
    work_order = await service.cancel_work_order(work_order_id, data)
    if not work_order:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Work order not found or cannot be cancelled"
        )
    return work_order


# ============================================================================
# BUILD RECORDS
# ============================================================================

@router.post(
    "/builds",
    response_model=KitBuildRecordResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Build Record"
)
async def create_build(
    data: KitBuildRecordCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions(["wms:manage"]))
):
    """Create a kit build record."""
    service = KittingService(db, current_user.tenant_id)
    build = await service.create_build(data, current_user.id)
    if not build:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Work order not found"
        )
    return build


@router.get(
    "/builds",
    response_model=List[KitBuildRecordResponse],
    summary="List Build Records"
)
async def list_builds(
    work_order_id: Optional[UUID] = None,
    status: Optional[BuildStatus] = None,
    station_id: Optional[UUID] = None,
    from_date: Optional[date] = None,
    to_date: Optional[date] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions(["wms:read"]))
):
    """List kit build records."""
    service = KittingService(db, current_user.tenant_id)
    builds, _ = await service.list_builds(
        work_order_id=work_order_id,
        status=status,
        station_id=station_id,
        from_date=from_date,
        to_date=to_date,
        skip=skip,
        limit=limit
    )
    return builds


@router.get(
    "/builds/{build_id}",
    response_model=KitBuildRecordResponse,
    summary="Get Build Record"
)
async def get_build(
    build_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions(["wms:read"]))
):
    """Get build record details."""
    service = KittingService(db, current_user.tenant_id)
    build = await service.get_build(build_id)
    if not build:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Build record not found"
        )
    return build


@router.post(
    "/builds/{build_id}/start",
    response_model=KitBuildRecordResponse,
    summary="Start Build"
)
async def start_build(
    build_id: UUID,
    data: BuildStart,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions(["wms:manage"]))
):
    """Start a build."""
    service = KittingService(db, current_user.tenant_id)
    build = await service.start_build(build_id, data, current_user.id)
    if not build:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Build not found or cannot be started"
        )
    return build


@router.post(
    "/builds/{build_id}/complete",
    response_model=KitBuildRecordResponse,
    summary="Complete Build"
)
async def complete_build(
    build_id: UUID,
    data: BuildComplete,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions(["wms:manage"]))
):
    """Complete a build."""
    service = KittingService(db, current_user.tenant_id)
    build = await service.complete_build(build_id, data, current_user.id)
    if not build:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Build not found or cannot be completed"
        )
    return build


@router.post(
    "/builds/{build_id}/fail",
    response_model=KitBuildRecordResponse,
    summary="Fail Build"
)
async def fail_build(
    build_id: UUID,
    data: BuildFail,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions(["wms:manage"]))
):
    """Mark a build as failed."""
    service = KittingService(db, current_user.tenant_id)
    build = await service.fail_build(build_id, data)
    if not build:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Build not found or cannot be marked as failed"
        )
    return build


@router.post(
    "/builds/{build_id}/qc",
    response_model=KitBuildRecordResponse,
    summary="QC Build"
)
async def qc_build(
    build_id: UUID,
    data: BuildQC,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions(["wms:manage"]))
):
    """Record QC results for a build."""
    service = KittingService(db, current_user.tenant_id)
    build = await service.qc_build(build_id, data, current_user.id)
    if not build:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Build not found or not pending QC"
        )
    return build


# ============================================================================
# DASHBOARD
# ============================================================================

@router.get(
    "/dashboard/{warehouse_id}",
    response_model=KitDashboard,
    summary="Get Kitting Dashboard"
)
async def get_dashboard(
    warehouse_id: UUID,
    from_date: date = Query(default=None),
    to_date: date = Query(default=None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions(["wms:read"]))
):
    """Get kitting dashboard statistics."""
    if not from_date:
        from_date = date.today().replace(day=1)
    if not to_date:
        to_date = date.today()

    service = KittingService(db, current_user.tenant_id)
    return await service.get_dashboard(warehouse_id, from_date, to_date)
