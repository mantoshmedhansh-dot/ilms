"""
Cycle Counting Schemas - Phase 11: Cycle Counting & Physical Inventory.

Pydantic schemas for cycle counting operations.
"""
from datetime import datetime, date
from decimal import Decimal
from typing import Optional, List, Dict, Any
from uuid import UUID

from pydantic import BaseModel, Field, ConfigDict

from app.models.cycle_count import (
    CountType, CountFrequency, CountMethod, CountPlanStatus,
    CountTaskStatus, VarianceStatus, VarianceReason, ABCClass, ApprovalLevel
)


# ============================================================================
# CYCLE COUNT PLAN SCHEMAS
# ============================================================================

class CycleCountPlanBase(BaseModel):
    """Base schema for cycle count plan."""
    plan_name: str = Field(..., max_length=200)
    plan_code: str = Field(..., max_length=50)
    description: Optional[str] = None
    count_type: CountType = CountType.CYCLE_COUNT

    # Scheduling
    frequency: CountFrequency = CountFrequency.WEEKLY
    start_date: date
    end_date: Optional[date] = None

    # ABC Settings
    count_a_frequency: Optional[str] = None
    count_b_frequency: Optional[str] = None
    count_c_frequency: Optional[str] = None

    # Selection Criteria
    zone_ids: Optional[List[UUID]] = None
    category_ids: Optional[List[UUID]] = None
    product_ids: Optional[List[UUID]] = None
    bin_ids: Optional[List[UUID]] = None
    abc_classes: Optional[List[str]] = None

    # Sampling
    sample_percentage: Optional[Decimal] = None
    min_items_per_count: int = Field(default=10, ge=1)
    max_items_per_count: int = Field(default=100, ge=1)

    # Count Settings
    count_method: CountMethod = CountMethod.RF_SCANNER
    blind_count: bool = False
    require_recount_on_variance: bool = True
    recount_threshold_percent: Decimal = Field(default=Decimal("5.0"))
    recount_threshold_value: Decimal = Field(default=Decimal("100.0"))

    # Approval Thresholds
    auto_approve_threshold_percent: Decimal = Field(default=Decimal("1.0"))
    auto_approve_threshold_value: Decimal = Field(default=Decimal("50.0"))
    supervisor_threshold_percent: Decimal = Field(default=Decimal("5.0"))
    manager_threshold_percent: Decimal = Field(default=Decimal("10.0"))
    director_threshold_value: Decimal = Field(default=Decimal("10000.0"))

    notes: Optional[str] = None


class CycleCountPlanCreate(CycleCountPlanBase):
    """Schema for creating a cycle count plan."""
    warehouse_id: UUID


class CycleCountPlanUpdate(BaseModel):
    """Schema for updating a cycle count plan."""
    plan_name: Optional[str] = Field(None, max_length=200)
    description: Optional[str] = None
    frequency: Optional[CountFrequency] = None
    end_date: Optional[date] = None

    count_a_frequency: Optional[str] = None
    count_b_frequency: Optional[str] = None
    count_c_frequency: Optional[str] = None

    zone_ids: Optional[List[UUID]] = None
    category_ids: Optional[List[UUID]] = None
    product_ids: Optional[List[UUID]] = None
    bin_ids: Optional[List[UUID]] = None
    abc_classes: Optional[List[str]] = None

    sample_percentage: Optional[Decimal] = None
    min_items_per_count: Optional[int] = Field(None, ge=1)
    max_items_per_count: Optional[int] = Field(None, ge=1)

    count_method: Optional[CountMethod] = None
    blind_count: Optional[bool] = None
    require_recount_on_variance: Optional[bool] = None
    recount_threshold_percent: Optional[Decimal] = None
    recount_threshold_value: Optional[Decimal] = None

    auto_approve_threshold_percent: Optional[Decimal] = None
    auto_approve_threshold_value: Optional[Decimal] = None
    supervisor_threshold_percent: Optional[Decimal] = None
    manager_threshold_percent: Optional[Decimal] = None
    director_threshold_value: Optional[Decimal] = None

    notes: Optional[str] = None


class CycleCountPlanResponse(CycleCountPlanBase):
    """Schema for cycle count plan response."""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    warehouse_id: UUID
    status: CountPlanStatus
    next_count_date: Optional[date]

    # Statistics
    total_counts_completed: int
    total_items_counted: int
    total_variances_found: int
    accuracy_rate: Optional[Decimal]
    last_count_date: Optional[date]

    created_by: Optional[UUID]
    created_at: datetime
    updated_at: datetime


# ============================================================================
# COUNT SESSION SCHEMAS
# ============================================================================

class CountSessionCreate(BaseModel):
    """Schema for creating a count session."""
    warehouse_id: UUID
    plan_id: Optional[UUID] = None
    session_name: str = Field(..., max_length=200)
    count_type: CountType = CountType.CYCLE_COUNT
    count_method: CountMethod = CountMethod.RF_SCANNER
    blind_count: bool = False
    count_date: date

    # Scope
    zone_ids: Optional[List[UUID]] = None
    bin_ids: Optional[List[UUID]] = None
    category_ids: Optional[List[UUID]] = None
    product_ids: Optional[List[UUID]] = None

    notes: Optional[str] = None


class CountSessionUpdate(BaseModel):
    """Schema for updating a count session."""
    session_name: Optional[str] = Field(None, max_length=200)
    count_date: Optional[date] = None
    notes: Optional[str] = None


class CountSessionResponse(BaseModel):
    """Schema for count session response."""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    warehouse_id: UUID
    plan_id: Optional[UUID]
    session_number: str
    session_name: str
    count_type: str
    count_method: str
    blind_count: bool
    count_date: date
    started_at: Optional[datetime]
    completed_at: Optional[datetime]

    # Scope
    zone_ids: Optional[List[UUID]]
    bin_ids: Optional[List[UUID]]
    category_ids: Optional[List[UUID]]

    # Progress
    total_tasks: int
    completed_tasks: int
    total_items: int
    items_counted: int
    items_with_variance: int

    # Variance Summary
    total_variance_qty: Decimal
    total_variance_value: Decimal
    positive_variance_qty: Decimal
    negative_variance_qty: Decimal

    # Accuracy
    accuracy_rate: Optional[Decimal]
    first_count_accuracy: Optional[Decimal]

    status: str
    approved_by: Optional[UUID]
    approved_at: Optional[datetime]
    approval_notes: Optional[str]
    notes: Optional[str]

    created_by: Optional[UUID]
    created_at: datetime
    updated_at: datetime


# ============================================================================
# COUNT TASK SCHEMAS
# ============================================================================

class CountTaskCreate(BaseModel):
    """Schema for creating a count task."""
    session_id: UUID
    zone_id: Optional[UUID] = None
    bin_id: Optional[UUID] = None
    location_code: str = Field(..., max_length=50)

    product_id: Optional[UUID] = None
    variant_id: Optional[UUID] = None
    lot_number: Optional[str] = Field(None, max_length=50)
    serial_number: Optional[str] = Field(None, max_length=100)

    expected_qty: Decimal = Field(default=Decimal("0"))
    expected_uom: str = Field(default="EACH", max_length=20)
    expected_value: Decimal = Field(default=Decimal("0"))

    assigned_to: Optional[UUID] = None
    notes: Optional[str] = None


class CountTaskAssign(BaseModel):
    """Schema for assigning a count task."""
    assigned_to: UUID


class CountTaskCount(BaseModel):
    """Schema for recording a count."""
    counted_qty: Decimal
    count_method: CountMethod = CountMethod.RF_SCANNER
    notes: Optional[str] = None
    photos: Optional[List[str]] = None


class CountTaskRecount(BaseModel):
    """Schema for recording a recount."""
    recount_qty: Decimal
    notes: Optional[str] = None


class CountTaskApprove(BaseModel):
    """Schema for approving a count task."""
    approved: bool = True
    notes: Optional[str] = None


class CountTaskResponse(BaseModel):
    """Schema for count task response."""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    session_id: UUID
    warehouse_id: UUID
    task_number: str
    sequence: int

    # Location
    zone_id: Optional[UUID]
    bin_id: Optional[UUID]
    location_code: str

    # Item
    product_id: Optional[UUID]
    variant_id: Optional[UUID]
    lot_number: Optional[str]
    serial_number: Optional[str]

    # Expected
    expected_qty: Decimal
    expected_uom: str
    expected_value: Decimal

    # Counts
    first_count_qty: Optional[Decimal]
    first_count_by: Optional[UUID]
    first_count_at: Optional[datetime]
    first_count_method: Optional[str]

    recount_required: bool
    recount_qty: Optional[Decimal]
    recount_by: Optional[UUID]
    recount_at: Optional[datetime]

    final_count_qty: Optional[Decimal]
    final_count_value: Optional[Decimal]

    # Variance
    variance_qty: Decimal
    variance_value: Decimal
    variance_percent: Decimal
    has_variance: bool

    # Assignment
    assigned_to: Optional[UUID]
    assigned_at: Optional[datetime]
    status: str

    # Approval
    approval_level: Optional[str]
    approved_by: Optional[UUID]
    approved_at: Optional[datetime]
    rejection_reason: Optional[str]

    notes: Optional[str]
    photos: Optional[List[str]]

    created_at: datetime
    updated_at: datetime


# ============================================================================
# COUNT DETAIL SCHEMAS
# ============================================================================

class CountDetailCreate(BaseModel):
    """Schema for creating a count detail entry."""
    task_id: UUID
    is_recount: bool = False

    product_id: Optional[UUID] = None
    barcode_scanned: Optional[str] = Field(None, max_length=100)
    lot_number: Optional[str] = Field(None, max_length=50)
    serial_number: Optional[str] = Field(None, max_length=100)
    expiry_date: Optional[date] = None

    quantity: Decimal
    uom: str = Field(default="EACH", max_length=20)

    count_method: CountMethod = CountMethod.RF_SCANNER
    device_id: Optional[str] = Field(None, max_length=50)
    found_in_bin: Optional[str] = Field(None, max_length=50)

    notes: Optional[str] = None


class CountDetailResponse(BaseModel):
    """Schema for count detail response."""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    task_id: UUID
    count_sequence: int
    is_recount: bool

    product_id: Optional[UUID]
    barcode_scanned: Optional[str]
    lot_number: Optional[str]
    serial_number: Optional[str]
    expiry_date: Optional[date]

    quantity: Decimal
    uom: str
    count_method: str
    device_id: Optional[str]
    counted_by: UUID
    counted_at: datetime
    found_in_bin: Optional[str]

    notes: Optional[str]
    created_at: datetime


# ============================================================================
# VARIANCE SCHEMAS
# ============================================================================

class VarianceInvestigate(BaseModel):
    """Schema for investigating a variance."""
    variance_reason: VarianceReason
    root_cause: Optional[str] = None
    corrective_action: Optional[str] = None
    investigation_notes: Optional[str] = None
    evidence_photos: Optional[List[str]] = None


class VarianceApprove(BaseModel):
    """Schema for approving a variance adjustment."""
    approved: bool = True
    notes: Optional[str] = None


class VarianceWriteOff(BaseModel):
    """Schema for writing off a variance."""
    write_off_gl_account: str = Field(..., max_length=50)
    notes: Optional[str] = None


class InventoryVarianceResponse(BaseModel):
    """Schema for inventory variance response."""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    warehouse_id: UUID
    session_id: UUID
    task_id: UUID
    variance_number: str
    variance_date: date

    # Location
    zone_id: Optional[UUID]
    bin_id: Optional[UUID]
    location_code: str

    # Item
    product_id: UUID
    variant_id: Optional[UUID]
    lot_number: Optional[str]

    # Quantities
    system_qty: Decimal
    counted_qty: Decimal
    variance_qty: Decimal
    uom: str

    # Values
    unit_cost: Decimal
    variance_value: Decimal
    variance_percent: Decimal

    # Classification
    abc_class: Optional[str]
    is_positive: bool
    is_negative: bool

    # Investigation
    status: str
    variance_reason: Optional[str]
    root_cause: Optional[str]
    corrective_action: Optional[str]

    # Approval
    approval_level: str
    approved_by: Optional[UUID]
    approved_at: Optional[datetime]

    # Adjustment
    adjustment_id: Optional[UUID]
    adjusted_by: Optional[UUID]
    adjusted_at: Optional[datetime]

    # Financial
    written_off: bool
    write_off_gl_account: Optional[str]
    write_off_amount: Decimal

    investigated_by: Optional[UUID]
    investigation_notes: Optional[str]
    evidence_photos: Optional[List[str]]
    notes: Optional[str]

    created_at: datetime
    updated_at: datetime


# ============================================================================
# ABC CLASSIFICATION SCHEMAS
# ============================================================================

class ABCClassificationCreate(BaseModel):
    """Schema for creating ABC classification."""
    warehouse_id: UUID
    product_id: UUID
    abc_class: ABCClass
    classification_method: str = Field(default="value", max_length=30)


class ABCClassificationUpdate(BaseModel):
    """Schema for updating ABC classification."""
    abc_class: Optional[ABCClass] = None
    count_frequency: Optional[CountFrequency] = None


class ABCClassificationResponse(BaseModel):
    """Schema for ABC classification response."""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    warehouse_id: UUID
    product_id: UUID
    abc_class: str
    classification_method: str

    annual_value: Decimal
    annual_velocity: int
    cumulative_value_percent: Decimal
    cumulative_velocity_percent: Decimal

    count_frequency: Optional[str]
    last_count_date: Optional[date]
    next_count_date: Optional[date]
    times_counted_ytd: int
    accuracy_rate: Optional[Decimal]

    calculated_at: datetime
    created_at: datetime
    updated_at: datetime


class ABCRecalculate(BaseModel):
    """Schema for recalculating ABC classification."""
    warehouse_id: UUID
    classification_method: str = Field(default="value")  # value, velocity, both
    a_threshold_percent: Decimal = Field(default=Decimal("80"))
    b_threshold_percent: Decimal = Field(default=Decimal("95"))


# ============================================================================
# DASHBOARD SCHEMAS
# ============================================================================

class CycleCountDashboard(BaseModel):
    """Dashboard statistics for cycle counting."""
    # Plan Stats
    active_plans: int
    total_plans: int

    # Session Stats
    sessions_today: int
    sessions_this_week: int
    sessions_this_month: int

    # Task Stats
    pending_tasks: int
    in_progress_tasks: int
    completed_tasks_today: int

    # Variance Stats
    open_variances: int
    pending_approval_variances: int
    total_variance_value_mtd: Decimal

    # Accuracy Metrics
    overall_accuracy_rate: Optional[Decimal]
    accuracy_by_zone: List[Dict[str, Any]]
    accuracy_by_abc_class: Dict[str, Decimal]

    # Count Coverage
    items_counted_mtd: int
    items_due_for_count: int
    overdue_items: int

    # Recent Activity
    recent_sessions: List[CountSessionResponse]
    recent_variances: List[InventoryVarianceResponse]


class GenerateCountTasks(BaseModel):
    """Schema for generating count tasks from a plan."""
    plan_id: UUID
    count_date: date
    assigned_to: Optional[UUID] = None
    max_tasks: Optional[int] = Field(None, ge=1, le=1000)
