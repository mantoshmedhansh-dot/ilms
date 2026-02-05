"""
Quality Control Schemas - Phase 7: Inspection & Quality Management.

Pydantic schemas for quality control including:
- QC configurations
- Inspections
- Defects
- Hold areas
- Sampling
"""
from datetime import datetime, date
from decimal import Decimal
from typing import Optional, List, Dict, Any
from uuid import UUID

from pydantic import BaseModel, Field

from app.models.quality_control import (
    InspectionType, InspectionStatus, DefectSeverity, DefectCategory,
    HoldReason, HoldStatus, SamplingPlan, DispositionAction
)


# ============================================================================
# QC CONFIGURATION SCHEMAS
# ============================================================================

class CheckpointConfig(BaseModel):
    """Checkpoint configuration."""
    checkpoint_id: str
    name: str
    description: Optional[str] = None
    is_required: bool = True
    fail_on_no: bool = True


class MeasurementConfig(BaseModel):
    """Measurement configuration."""
    measurement_id: str
    name: str
    unit: str
    min_value: Optional[Decimal] = None
    max_value: Optional[Decimal] = None
    target_value: Optional[Decimal] = None
    tolerance: Optional[Decimal] = None
    is_required: bool = True


class QCConfigurationBase(BaseModel):
    """Base schema for QC configuration."""
    config_code: str = Field(..., max_length=30)
    config_name: str = Field(..., max_length=100)
    description: Optional[str] = None
    inspection_type: InspectionType = InspectionType.RECEIVING
    sampling_plan: SamplingPlan = SamplingPlan.FULL
    sample_size_percent: Optional[Decimal] = None
    sample_size_quantity: Optional[int] = None
    aql_level: Optional[Decimal] = None
    max_defect_percent: Decimal = Decimal("0")
    max_critical_defects: int = 0
    max_major_defects: int = 0
    max_minor_defects: Optional[int] = None
    checkpoints: Optional[List[CheckpointConfig]] = None
    measurements: Optional[List[MeasurementConfig]] = None
    auto_release_on_pass: bool = True
    auto_hold_on_fail: bool = True
    require_supervisor_approval: bool = False
    is_receiving_required: bool = True
    is_shipping_required: bool = False
    notes: Optional[str] = None


class QCConfigurationCreate(QCConfigurationBase):
    """Schema for creating QC configuration."""
    warehouse_id: Optional[UUID] = None
    product_id: Optional[UUID] = None
    category_id: Optional[UUID] = None
    vendor_id: Optional[UUID] = None


class QCConfigurationUpdate(BaseModel):
    """Schema for updating QC configuration."""
    config_name: Optional[str] = Field(None, max_length=100)
    description: Optional[str] = None
    sampling_plan: Optional[SamplingPlan] = None
    sample_size_percent: Optional[Decimal] = None
    sample_size_quantity: Optional[int] = None
    aql_level: Optional[Decimal] = None
    max_defect_percent: Optional[Decimal] = None
    max_critical_defects: Optional[int] = None
    max_major_defects: Optional[int] = None
    max_minor_defects: Optional[int] = None
    checkpoints: Optional[List[CheckpointConfig]] = None
    measurements: Optional[List[MeasurementConfig]] = None
    auto_release_on_pass: Optional[bool] = None
    auto_hold_on_fail: Optional[bool] = None
    require_supervisor_approval: Optional[bool] = None
    is_receiving_required: Optional[bool] = None
    is_shipping_required: Optional[bool] = None
    is_active: Optional[bool] = None
    notes: Optional[str] = None


class QCConfigurationResponse(QCConfigurationBase):
    """Response schema for QC configuration."""
    id: UUID
    tenant_id: UUID
    warehouse_id: Optional[UUID] = None
    product_id: Optional[UUID] = None
    category_id: Optional[UUID] = None
    vendor_id: Optional[UUID] = None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ============================================================================
# QC INSPECTION SCHEMAS
# ============================================================================

class CheckpointResult(BaseModel):
    """Result of a checkpoint."""
    checkpoint_id: str
    name: str
    passed: bool
    notes: Optional[str] = None


class MeasurementResult(BaseModel):
    """Result of a measurement."""
    measurement_id: str
    name: str
    value: Decimal
    unit: str
    in_spec: bool
    notes: Optional[str] = None


class QCInspectionBase(BaseModel):
    """Base schema for QC inspection."""
    inspection_type: InspectionType
    product_id: UUID
    sku: str = Field(..., max_length=100)
    product_name: str = Field(..., max_length=255)
    total_quantity: int = Field(..., ge=1)
    lot_number: Optional[str] = Field(None, max_length=50)
    batch_number: Optional[str] = Field(None, max_length=50)
    manufacture_date: Optional[date] = None
    expiry_date: Optional[date] = None
    notes: Optional[str] = None


class QCInspectionCreate(QCInspectionBase):
    """Schema for creating QC inspection."""
    warehouse_id: UUID
    zone_id: Optional[UUID] = None
    config_id: Optional[UUID] = None
    grn_id: Optional[UUID] = None
    shipment_id: Optional[UUID] = None
    order_id: Optional[UUID] = None
    return_order_id: Optional[UUID] = None
    vendor_id: Optional[UUID] = None
    sample_quantity: Optional[int] = None


class QCInspectionUpdate(BaseModel):
    """Schema for updating QC inspection."""
    zone_id: Optional[UUID] = None
    lot_number: Optional[str] = Field(None, max_length=50)
    batch_number: Optional[str] = Field(None, max_length=50)
    manufacture_date: Optional[date] = None
    expiry_date: Optional[date] = None
    notes: Optional[str] = None


class InspectionStart(BaseModel):
    """Schema for starting inspection."""
    sample_quantity: Optional[int] = None


class InspectionResult(BaseModel):
    """Schema for recording inspection results."""
    passed_quantity: int = Field(..., ge=0)
    failed_quantity: int = Field(..., ge=0)
    checkpoint_results: Optional[List[CheckpointResult]] = None
    measurement_results: Optional[List[MeasurementResult]] = None
    photos: Optional[List[str]] = None
    notes: Optional[str] = None


class InspectionDisposition(BaseModel):
    """Schema for inspection disposition."""
    disposition: DispositionAction
    disposition_notes: Optional[str] = None
    hold_bin_id: Optional[UUID] = None


class QCInspectionResponse(QCInspectionBase):
    """Response schema for QC inspection."""
    id: UUID
    tenant_id: UUID
    inspection_number: str
    status: InspectionStatus
    warehouse_id: UUID
    zone_id: Optional[UUID] = None
    config_id: Optional[UUID] = None
    grn_id: Optional[UUID] = None
    shipment_id: Optional[UUID] = None
    order_id: Optional[UUID] = None
    return_order_id: Optional[UUID] = None
    vendor_id: Optional[UUID] = None
    sample_quantity: int
    passed_quantity: int
    failed_quantity: int
    pending_quantity: int
    inspection_date: date
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    inspector_id: Optional[UUID] = None
    defect_count: int
    critical_defects: int
    major_defects: int
    minor_defects: int
    defect_rate: Optional[Decimal] = None
    checkpoint_results: Optional[List[Dict[str, Any]]] = None
    measurement_results: Optional[List[Dict[str, Any]]] = None
    disposition: Optional[str] = None
    disposition_notes: Optional[str] = None
    disposition_by: Optional[UUID] = None
    disposition_at: Optional[datetime] = None
    requires_approval: bool
    approved_by: Optional[UUID] = None
    approved_at: Optional[datetime] = None
    photos: Optional[List[str]] = None
    documents: Optional[List[str]] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ============================================================================
# QC DEFECT SCHEMAS
# ============================================================================

class QCDefectBase(BaseModel):
    """Base schema for QC defect."""
    defect_code: str = Field(..., max_length=30)
    defect_name: str = Field(..., max_length=100)
    category: DefectCategory
    severity: DefectSeverity
    description: Optional[str] = None
    defect_quantity: int = Field(1, ge=1)
    defect_location: Optional[str] = Field(None, max_length=100)
    serial_numbers: Optional[List[str]] = None
    root_cause: Optional[str] = Field(None, max_length=200)
    is_vendor_related: bool = False
    photos: Optional[List[str]] = None
    notes: Optional[str] = None


class QCDefectCreate(QCDefectBase):
    """Schema for creating QC defect."""
    inspection_id: UUID


class QCDefectResponse(QCDefectBase):
    """Response schema for QC defect."""
    id: UUID
    tenant_id: UUID
    inspection_id: UUID
    recorded_by: Optional[UUID] = None
    recorded_at: datetime

    class Config:
        from_attributes = True


# ============================================================================
# QC HOLD AREA SCHEMAS
# ============================================================================

class QCHoldAreaBase(BaseModel):
    """Base schema for QC hold area."""
    hold_reason: HoldReason
    reason_detail: Optional[str] = None
    product_id: UUID
    sku: str = Field(..., max_length=100)
    hold_quantity: int = Field(..., ge=1)
    lot_number: Optional[str] = Field(None, max_length=50)
    serial_numbers: Optional[List[str]] = None
    target_resolution_date: Optional[date] = None
    notes: Optional[str] = None


class QCHoldAreaCreate(QCHoldAreaBase):
    """Schema for creating QC hold area."""
    warehouse_id: UUID
    hold_bin_id: Optional[UUID] = None
    inspection_id: Optional[UUID] = None
    grn_id: Optional[UUID] = None
    return_order_id: Optional[UUID] = None
    vendor_id: Optional[UUID] = None


class QCHoldAreaUpdate(BaseModel):
    """Schema for updating QC hold area."""
    hold_bin_id: Optional[UUID] = None
    reason_detail: Optional[str] = None
    target_resolution_date: Optional[date] = None
    notes: Optional[str] = None


class HoldRelease(BaseModel):
    """Schema for releasing hold."""
    release_quantity: int = Field(..., ge=1)
    resolution_action: DispositionAction
    resolution_notes: Optional[str] = None
    destination_bin_id: Optional[UUID] = None


class QCHoldAreaResponse(QCHoldAreaBase):
    """Response schema for QC hold area."""
    id: UUID
    tenant_id: UUID
    hold_number: str
    status: HoldStatus
    warehouse_id: UUID
    hold_bin_id: Optional[UUID] = None
    inspection_id: Optional[UUID] = None
    grn_id: Optional[UUID] = None
    return_order_id: Optional[UUID] = None
    vendor_id: Optional[UUID] = None
    released_quantity: int
    scrapped_quantity: int
    returned_quantity: int
    remaining_quantity: int
    hold_date: date
    resolved_date: Optional[date] = None
    created_by: Optional[UUID] = None
    resolved_by: Optional[UUID] = None
    resolution_action: Optional[str] = None
    resolution_notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ============================================================================
# QC SAMPLING SCHEMAS
# ============================================================================

class QCSamplingCreate(BaseModel):
    """Schema for creating QC sampling."""
    inspection_id: UUID
    sample_number: int = Field(..., ge=1)
    sample_quantity: int = Field(..., ge=1)
    serial_numbers: Optional[List[str]] = None
    lpn: Optional[str] = Field(None, max_length=50)


class QCSamplingResult(BaseModel):
    """Schema for recording sampling result."""
    passed_quantity: int = Field(..., ge=0)
    failed_quantity: int = Field(..., ge=0)
    checkpoint_results: Optional[List[CheckpointResult]] = None
    measurements: Optional[List[MeasurementResult]] = None
    defect_count: int = 0
    photos: Optional[List[str]] = None
    notes: Optional[str] = None


class QCSamplingResponse(BaseModel):
    """Response schema for QC sampling."""
    id: UUID
    tenant_id: UUID
    inspection_id: UUID
    sample_number: int
    sample_quantity: int
    passed_quantity: int
    failed_quantity: int
    serial_numbers: Optional[List[str]] = None
    lpn: Optional[str] = None
    checkpoint_results: Optional[List[Dict[str, Any]]] = None
    measurements: Optional[List[Dict[str, Any]]] = None
    result: str
    defect_count: int
    inspected_by: Optional[UUID] = None
    inspected_at: datetime
    photos: Optional[List[str]] = None
    notes: Optional[str] = None

    class Config:
        from_attributes = True


# ============================================================================
# DASHBOARD & STATS SCHEMAS
# ============================================================================

class QCDashboard(BaseModel):
    """QC dashboard statistics."""
    warehouse_id: UUID
    date_range_start: date
    date_range_end: date

    # Totals
    total_inspections: int
    completed_inspections: int
    pending_inspections: int
    in_progress_inspections: int

    # Results
    passed_inspections: int
    failed_inspections: int
    partial_pass_inspections: int
    pass_rate: Optional[Decimal] = None

    # Defects
    total_defects: int
    critical_defects: int
    major_defects: int
    minor_defects: int
    avg_defect_rate: Optional[Decimal] = None

    # Hold
    items_on_hold: int
    hold_quantity: int

    # By Type
    by_inspection_type: Dict[str, int]
    by_defect_category: Dict[str, int]


class VendorQualityStats(BaseModel):
    """Quality statistics by vendor."""
    vendor_id: UUID
    vendor_name: str
    total_inspections: int
    passed: int
    failed: int
    pass_rate: Decimal
    total_defects: int
    critical_defects: int
    avg_defect_rate: Decimal


class ProductQualityStats(BaseModel):
    """Quality statistics by product."""
    product_id: UUID
    sku: str
    product_name: str
    total_inspections: int
    passed: int
    failed: int
    pass_rate: Decimal
    common_defects: List[str]
