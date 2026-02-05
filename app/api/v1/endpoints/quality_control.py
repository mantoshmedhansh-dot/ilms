"""
Quality Control API Endpoints - Phase 7: Inspection & Quality Management.

API endpoints for quality control including:
- QC configurations
- Inspections
- Defects
- Hold management
"""
from datetime import date
from typing import Optional, List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.api.deps import get_current_user, require_permissions
from app.models.user import User
from app.models.quality_control import (
    InspectionType, InspectionStatus, DefectSeverity, DefectCategory,
    HoldReason, HoldStatus
)
from app.schemas.quality_control import (
    QCConfigurationCreate, QCConfigurationUpdate, QCConfigurationResponse,
    QCInspectionCreate, QCInspectionUpdate, QCInspectionResponse,
    InspectionStart, InspectionResult, InspectionDisposition,
    QCDefectCreate, QCDefectResponse,
    QCHoldAreaCreate, QCHoldAreaUpdate, QCHoldAreaResponse, HoldRelease,
    QCDashboard
)
from app.services.quality_control_service import QualityControlService

router = APIRouter()


# ============================================================================
# QC CONFIGURATIONS
# ============================================================================

@router.post(
    "/configs",
    response_model=QCConfigurationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create QC Configuration"
)
async def create_config(
    data: QCConfigurationCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions(["wms:manage"]))
):
    """Create a QC configuration."""
    service = QualityControlService(db, current_user.tenant_id)
    return await service.create_config(data)


@router.get(
    "/configs",
    response_model=List[QCConfigurationResponse],
    summary="List QC Configurations"
)
async def list_configs(
    warehouse_id: Optional[UUID] = None,
    product_id: Optional[UUID] = None,
    vendor_id: Optional[UUID] = None,
    inspection_type: Optional[InspectionType] = None,
    is_active: bool = True,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions(["wms:read"]))
):
    """List QC configurations."""
    service = QualityControlService(db, current_user.tenant_id)
    configs, _ = await service.list_configs(
        warehouse_id=warehouse_id,
        product_id=product_id,
        vendor_id=vendor_id,
        inspection_type=inspection_type,
        is_active=is_active,
        skip=skip,
        limit=limit
    )
    return configs


@router.get(
    "/configs/{config_id}",
    response_model=QCConfigurationResponse,
    summary="Get QC Configuration"
)
async def get_config(
    config_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions(["wms:read"]))
):
    """Get QC configuration details."""
    service = QualityControlService(db, current_user.tenant_id)
    config = await service.get_config(config_id)
    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="QC configuration not found"
        )
    return config


@router.patch(
    "/configs/{config_id}",
    response_model=QCConfigurationResponse,
    summary="Update QC Configuration"
)
async def update_config(
    config_id: UUID,
    data: QCConfigurationUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions(["wms:manage"]))
):
    """Update QC configuration."""
    service = QualityControlService(db, current_user.tenant_id)
    config = await service.update_config(config_id, data)
    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="QC configuration not found"
        )
    return config


# ============================================================================
# INSPECTIONS
# ============================================================================

@router.post(
    "/inspections",
    response_model=QCInspectionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Inspection"
)
async def create_inspection(
    data: QCInspectionCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions(["wms:manage"]))
):
    """Create a QC inspection."""
    service = QualityControlService(db, current_user.tenant_id)
    return await service.create_inspection(data)


@router.get(
    "/inspections",
    response_model=List[QCInspectionResponse],
    summary="List Inspections"
)
async def list_inspections(
    warehouse_id: Optional[UUID] = None,
    inspection_type: Optional[InspectionType] = None,
    status: Optional[InspectionStatus] = None,
    product_id: Optional[UUID] = None,
    vendor_id: Optional[UUID] = None,
    from_date: Optional[date] = None,
    to_date: Optional[date] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions(["wms:read"]))
):
    """List QC inspections."""
    service = QualityControlService(db, current_user.tenant_id)
    inspections, _ = await service.list_inspections(
        warehouse_id=warehouse_id,
        inspection_type=inspection_type,
        status=status,
        product_id=product_id,
        vendor_id=vendor_id,
        from_date=from_date,
        to_date=to_date,
        skip=skip,
        limit=limit
    )
    return inspections


@router.get(
    "/inspections/{inspection_id}",
    response_model=QCInspectionResponse,
    summary="Get Inspection"
)
async def get_inspection(
    inspection_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions(["wms:read"]))
):
    """Get inspection details."""
    service = QualityControlService(db, current_user.tenant_id)
    inspection = await service.get_inspection(inspection_id)
    if not inspection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Inspection not found"
        )
    return inspection


@router.post(
    "/inspections/{inspection_id}/start",
    response_model=QCInspectionResponse,
    summary="Start Inspection"
)
async def start_inspection(
    inspection_id: UUID,
    data: Optional[InspectionStart] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions(["wms:manage"]))
):
    """Start an inspection."""
    service = QualityControlService(db, current_user.tenant_id)
    inspection = await service.start_inspection(
        inspection_id, current_user.id, data
    )
    if not inspection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Inspection not found"
        )
    return inspection


@router.post(
    "/inspections/{inspection_id}/results",
    response_model=QCInspectionResponse,
    summary="Record Results"
)
async def record_results(
    inspection_id: UUID,
    data: InspectionResult,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions(["wms:manage"]))
):
    """Record inspection results."""
    service = QualityControlService(db, current_user.tenant_id)
    inspection = await service.record_results(inspection_id, data)
    if not inspection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Inspection not found"
        )
    return inspection


@router.post(
    "/inspections/{inspection_id}/complete",
    response_model=QCInspectionResponse,
    summary="Complete Inspection"
)
async def complete_inspection(
    inspection_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions(["wms:manage"]))
):
    """Complete an inspection."""
    service = QualityControlService(db, current_user.tenant_id)
    inspection = await service.complete_inspection(inspection_id)
    if not inspection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Inspection not found"
        )
    return inspection


@router.post(
    "/inspections/{inspection_id}/disposition",
    response_model=QCInspectionResponse,
    summary="Set Disposition"
)
async def set_disposition(
    inspection_id: UUID,
    data: InspectionDisposition,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions(["wms:manage"]))
):
    """Set inspection disposition."""
    service = QualityControlService(db, current_user.tenant_id)
    inspection = await service.set_disposition(
        inspection_id, data, current_user.id
    )
    if not inspection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Inspection not found"
        )
    return inspection


# ============================================================================
# DEFECTS
# ============================================================================

@router.post(
    "/defects",
    response_model=QCDefectResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Record Defect"
)
async def create_defect(
    data: QCDefectCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions(["wms:manage"]))
):
    """Record a defect."""
    service = QualityControlService(db, current_user.tenant_id)
    return await service.create_defect(data, current_user.id)


@router.get(
    "/defects",
    response_model=List[QCDefectResponse],
    summary="List Defects"
)
async def list_defects(
    inspection_id: Optional[UUID] = None,
    severity: Optional[DefectSeverity] = None,
    category: Optional[DefectCategory] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions(["wms:read"]))
):
    """List defects."""
    service = QualityControlService(db, current_user.tenant_id)
    defects, _ = await service.list_defects(
        inspection_id=inspection_id,
        severity=severity,
        category=category,
        skip=skip,
        limit=limit
    )
    return defects


# ============================================================================
# HOLD MANAGEMENT
# ============================================================================

@router.post(
    "/holds",
    response_model=QCHoldAreaResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create QC Hold"
)
async def create_hold(
    data: QCHoldAreaCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions(["wms:manage"]))
):
    """Create a QC hold."""
    service = QualityControlService(db, current_user.tenant_id)
    return await service.create_hold(data, current_user.id)


@router.get(
    "/holds",
    response_model=List[QCHoldAreaResponse],
    summary="List QC Holds"
)
async def list_holds(
    warehouse_id: Optional[UUID] = None,
    status: Optional[HoldStatus] = None,
    product_id: Optional[UUID] = None,
    hold_reason: Optional[HoldReason] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions(["wms:read"]))
):
    """List QC holds."""
    service = QualityControlService(db, current_user.tenant_id)
    holds, _ = await service.list_holds(
        warehouse_id=warehouse_id,
        status=status,
        product_id=product_id,
        hold_reason=hold_reason,
        skip=skip,
        limit=limit
    )
    return holds


@router.get(
    "/holds/{hold_id}",
    response_model=QCHoldAreaResponse,
    summary="Get QC Hold"
)
async def get_hold(
    hold_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions(["wms:read"]))
):
    """Get QC hold details."""
    service = QualityControlService(db, current_user.tenant_id)
    hold = await service.get_hold(hold_id)
    if not hold:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="QC hold not found"
        )
    return hold


@router.post(
    "/holds/{hold_id}/release",
    response_model=QCHoldAreaResponse,
    summary="Release from Hold"
)
async def release_hold(
    hold_id: UUID,
    data: HoldRelease,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions(["wms:manage"]))
):
    """Release items from QC hold."""
    service = QualityControlService(db, current_user.tenant_id)
    hold = await service.release_hold(hold_id, data, current_user.id)
    if not hold:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="QC hold not found or insufficient quantity"
        )
    return hold


# ============================================================================
# DASHBOARD
# ============================================================================

@router.get(
    "/dashboard/{warehouse_id}",
    response_model=QCDashboard,
    summary="Get QC Dashboard"
)
async def get_dashboard(
    warehouse_id: UUID,
    from_date: date = Query(default=None),
    to_date: date = Query(default=None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions(["wms:read"]))
):
    """Get QC dashboard statistics."""
    if not from_date:
        from_date = date.today().replace(day=1)
    if not to_date:
        to_date = date.today()

    service = QualityControlService(db, current_user.tenant_id)
    return await service.get_dashboard(warehouse_id, from_date, to_date)
