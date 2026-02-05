"""
Kitting & Assembly Schemas - Phase 8: Kit Management & Assembly Operations.

Pydantic schemas for kitting and assembly operations.
"""
from datetime import datetime, date
from decimal import Decimal
from typing import Optional, List, Dict, Any
from uuid import UUID

from pydantic import BaseModel, Field, ConfigDict

from app.models.kitting import (
    KitType, KitStatus, ComponentType, WorkOrderType,
    WorkOrderStatus, WorkOrderPriority, BuildStatus, StationStatus
)


# ============================================================================
# KIT DEFINITION SCHEMAS
# ============================================================================

class KitComponentBase(BaseModel):
    """Base schema for kit component."""
    product_id: UUID
    sku: str = Field(..., max_length=100)
    product_name: str = Field(..., max_length=255)
    quantity: int = Field(default=1, ge=1)
    uom: str = Field(default="EACH", max_length=20)
    component_type: ComponentType = ComponentType.REQUIRED
    substitute_group: Optional[str] = Field(None, max_length=50)
    substitute_priority: int = Field(default=1, ge=1)
    sequence: int = Field(default=0, ge=0)
    component_cost: Decimal = Field(default=Decimal("0"))
    special_instructions: Optional[str] = None
    requires_serial: bool = False


class KitComponentCreate(KitComponentBase):
    """Schema for creating a kit component."""
    pass


class KitComponentUpdate(BaseModel):
    """Schema for updating a kit component."""
    quantity: Optional[int] = Field(None, ge=1)
    uom: Optional[str] = Field(None, max_length=20)
    component_type: Optional[ComponentType] = None
    substitute_group: Optional[str] = Field(None, max_length=50)
    substitute_priority: Optional[int] = Field(None, ge=1)
    sequence: Optional[int] = Field(None, ge=0)
    component_cost: Optional[Decimal] = None
    special_instructions: Optional[str] = None
    requires_serial: Optional[bool] = None
    is_active: Optional[bool] = None


class KitComponentResponse(KitComponentBase):
    """Schema for kit component response."""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    kit_id: UUID
    is_active: bool
    created_at: datetime
    updated_at: datetime


class KitDefinitionBase(BaseModel):
    """Base schema for kit definition."""
    kit_sku: str = Field(..., max_length=100)
    kit_name: str = Field(..., max_length=255)
    description: Optional[str] = None
    kit_type: KitType = KitType.STANDARD
    product_id: Optional[UUID] = None
    warehouse_id: Optional[UUID] = None
    assembly_time_minutes: int = Field(default=10, ge=1)
    labor_cost: Decimal = Field(default=Decimal("0"))
    packaging_cost: Decimal = Field(default=Decimal("0"))
    instructions: Optional[str] = None
    instruction_images: Optional[List[str]] = None
    instruction_video_url: Optional[str] = Field(None, max_length=500)
    packaging_type: Optional[str] = Field(None, max_length=50)
    package_weight: Optional[Decimal] = None
    package_length: Optional[Decimal] = None
    package_width: Optional[Decimal] = None
    package_height: Optional[Decimal] = None
    requires_qc: bool = False
    qc_checklist: Optional[List[Dict[str, Any]]] = None
    effective_from: Optional[date] = None
    effective_to: Optional[date] = None
    notes: Optional[str] = None


class KitDefinitionCreate(KitDefinitionBase):
    """Schema for creating a kit definition."""
    components: Optional[List[KitComponentCreate]] = None


class KitDefinitionUpdate(BaseModel):
    """Schema for updating a kit definition."""
    kit_name: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = None
    kit_type: Optional[KitType] = None
    status: Optional[KitStatus] = None
    product_id: Optional[UUID] = None
    warehouse_id: Optional[UUID] = None
    assembly_time_minutes: Optional[int] = Field(None, ge=1)
    labor_cost: Optional[Decimal] = None
    packaging_cost: Optional[Decimal] = None
    instructions: Optional[str] = None
    instruction_images: Optional[List[str]] = None
    instruction_video_url: Optional[str] = Field(None, max_length=500)
    packaging_type: Optional[str] = Field(None, max_length=50)
    package_weight: Optional[Decimal] = None
    package_length: Optional[Decimal] = None
    package_width: Optional[Decimal] = None
    package_height: Optional[Decimal] = None
    requires_qc: Optional[bool] = None
    qc_checklist: Optional[List[Dict[str, Any]]] = None
    effective_from: Optional[date] = None
    effective_to: Optional[date] = None
    notes: Optional[str] = None


class KitDefinitionResponse(KitDefinitionBase):
    """Schema for kit definition response."""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    status: KitStatus
    total_builds: int
    avg_build_time_minutes: Optional[Decimal]
    created_at: datetime
    updated_at: datetime
    created_by: Optional[UUID]
    components: Optional[List[KitComponentResponse]] = None


# ============================================================================
# ASSEMBLY STATION SCHEMAS
# ============================================================================

class AssemblyStationBase(BaseModel):
    """Base schema for assembly station."""
    station_code: str = Field(..., max_length=30)
    station_name: str = Field(..., max_length=100)
    warehouse_id: UUID
    zone_id: Optional[UUID] = None
    equipment: Optional[List[str]] = None
    tools_required: Optional[List[str]] = None
    max_concurrent_builds: int = Field(default=1, ge=1)
    notes: Optional[str] = None


class AssemblyStationCreate(AssemblyStationBase):
    """Schema for creating an assembly station."""
    pass


class AssemblyStationUpdate(BaseModel):
    """Schema for updating an assembly station."""
    station_name: Optional[str] = Field(None, max_length=100)
    status: Optional[StationStatus] = None
    zone_id: Optional[UUID] = None
    equipment: Optional[List[str]] = None
    tools_required: Optional[List[str]] = None
    max_concurrent_builds: Optional[int] = Field(None, ge=1)
    is_active: Optional[bool] = None
    notes: Optional[str] = None


class AssemblyStationResponse(AssemblyStationBase):
    """Schema for assembly station response."""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    status: StationStatus
    current_builds: int
    assigned_worker_id: Optional[UUID]
    assigned_at: Optional[datetime]
    current_work_order_id: Optional[UUID]
    total_builds_today: int
    avg_build_time_today: Optional[Decimal]
    is_active: bool
    created_at: datetime
    updated_at: datetime


class StationAssignment(BaseModel):
    """Schema for assigning worker to station."""
    worker_id: UUID


# ============================================================================
# WORK ORDER SCHEMAS
# ============================================================================

class KitWorkOrderBase(BaseModel):
    """Base schema for kit work order."""
    work_order_type: WorkOrderType = WorkOrderType.ASSEMBLY
    priority: WorkOrderPriority = WorkOrderPriority.NORMAL
    kit_id: UUID
    warehouse_id: UUID
    station_id: Optional[UUID] = None
    quantity_ordered: int = Field(..., ge=1)
    scheduled_date: date
    due_date: Optional[date] = None
    order_id: Optional[UUID] = None
    assigned_to: Optional[UUID] = None
    destination_bin_id: Optional[UUID] = None
    notes: Optional[str] = None


class KitWorkOrderCreate(KitWorkOrderBase):
    """Schema for creating a kit work order."""
    pass


class KitWorkOrderUpdate(BaseModel):
    """Schema for updating a kit work order."""
    priority: Optional[WorkOrderPriority] = None
    station_id: Optional[UUID] = None
    scheduled_date: Optional[date] = None
    due_date: Optional[date] = None
    assigned_to: Optional[UUID] = None
    destination_bin_id: Optional[UUID] = None
    notes: Optional[str] = None


class KitWorkOrderResponse(KitWorkOrderBase):
    """Schema for kit work order response."""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    work_order_number: str
    status: WorkOrderStatus
    quantity_completed: int
    quantity_failed: int
    quantity_remaining: int
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    components_available: bool
    component_shortage: Optional[Dict[str, Any]]
    estimated_hours: Optional[Decimal]
    actual_hours: Optional[Decimal]
    estimated_cost: Decimal
    actual_cost: Decimal
    cancellation_reason: Optional[str]
    created_by: Optional[UUID]
    created_at: datetime
    updated_at: datetime


class WorkOrderRelease(BaseModel):
    """Schema for releasing a work order."""
    station_id: Optional[UUID] = None
    assigned_to: Optional[UUID] = None


class WorkOrderCancel(BaseModel):
    """Schema for cancelling a work order."""
    reason: str = Field(..., max_length=200)


# ============================================================================
# BUILD RECORD SCHEMAS
# ============================================================================

class KitBuildRecordBase(BaseModel):
    """Base schema for kit build record."""
    serial_number: Optional[str] = Field(None, max_length=100)
    lpn: Optional[str] = Field(None, max_length=50)
    notes: Optional[str] = None


class KitBuildRecordCreate(KitBuildRecordBase):
    """Schema for creating a kit build record."""
    work_order_id: UUID
    station_id: Optional[UUID] = None


class BuildStart(BaseModel):
    """Schema for starting a build."""
    station_id: Optional[UUID] = None
    serial_number: Optional[str] = Field(None, max_length=100)
    lpn: Optional[str] = Field(None, max_length=50)


class BuildComplete(BaseModel):
    """Schema for completing a build."""
    components_used: List[Dict[str, Any]]
    destination_bin_id: Optional[UUID] = None
    notes: Optional[str] = None


class BuildFail(BaseModel):
    """Schema for failing a build."""
    failure_reason: str = Field(..., max_length=200)
    components_used: Optional[List[Dict[str, Any]]] = None


class BuildQC(BaseModel):
    """Schema for QC on a build."""
    qc_status: str = Field(..., max_length=30)
    qc_notes: Optional[str] = None


class KitBuildRecordResponse(KitBuildRecordBase):
    """Schema for kit build record response."""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    work_order_id: UUID
    build_number: int
    status: BuildStatus
    kit_id: UUID
    kit_sku: str
    components_used: Optional[List[Dict[str, Any]]]
    station_id: Optional[UUID]
    built_by: Optional[UUID]
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    build_time_minutes: Optional[int]
    qc_status: Optional[str]
    qc_by: Optional[UUID]
    qc_at: Optional[datetime]
    qc_notes: Optional[str]
    destination_bin_id: Optional[UUID]
    failure_reason: Optional[str]
    created_at: datetime


# ============================================================================
# DASHBOARD SCHEMAS
# ============================================================================

class KitDashboard(BaseModel):
    """Dashboard statistics for kitting."""
    total_kits: int
    active_kits: int
    total_stations: int
    available_stations: int
    occupied_stations: int

    # Work Order Stats
    pending_work_orders: int
    in_progress_work_orders: int
    completed_today: int
    quantity_built_today: int

    # Performance
    avg_build_time_minutes: Optional[Decimal]
    builds_per_hour: Optional[Decimal]

    # Component Availability
    work_orders_with_shortage: int

    # Recent Activity
    recent_work_orders: List[KitWorkOrderResponse]
    recent_builds: List[KitBuildRecordResponse]


class ComponentAvailability(BaseModel):
    """Component availability for a kit."""
    kit_id: UUID
    kit_sku: str
    quantity_requested: int
    can_build: int
    shortage: Optional[Dict[str, Any]]
    components: List[Dict[str, Any]]
