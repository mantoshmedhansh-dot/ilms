"""
Pydantic schemas for Labor Management - Phase 4: Workforce Optimization.
"""
import uuid
from datetime import datetime, date, time
from decimal import Decimal
from typing import Optional, List, Dict, Any
from enum import Enum

from pydantic import BaseModel, Field, ConfigDict


# ============================================================================
# ENUMS
# ============================================================================

class WorkerType(str, Enum):
    FULL_TIME = "FULL_TIME"
    PART_TIME = "PART_TIME"
    TEMPORARY = "TEMPORARY"
    CONTRACT = "CONTRACT"
    SEASONAL = "SEASONAL"


class WorkerStatus(str, Enum):
    ACTIVE = "ACTIVE"
    ON_LEAVE = "ON_LEAVE"
    SUSPENDED = "SUSPENDED"
    TERMINATED = "TERMINATED"
    TRAINING = "TRAINING"


class SkillCategory(str, Enum):
    PICKING = "PICKING"
    PACKING = "PACKING"
    RECEIVING = "RECEIVING"
    PUTAWAY = "PUTAWAY"
    SHIPPING = "SHIPPING"
    FORKLIFT = "FORKLIFT"
    REACH_TRUCK = "REACH_TRUCK"
    ORDER_PICKER = "ORDER_PICKER"
    RF_SCANNER = "RF_SCANNER"
    HAZMAT = "HAZMAT"
    COLD_STORAGE = "COLD_STORAGE"
    QUALITY_CHECK = "QUALITY_CHECK"
    INVENTORY_COUNT = "INVENTORY_COUNT"
    SUPERVISION = "SUPERVISION"


class SkillLevel(str, Enum):
    NOVICE = "NOVICE"
    INTERMEDIATE = "INTERMEDIATE"
    PROFICIENT = "PROFICIENT"
    EXPERT = "EXPERT"
    MASTER = "MASTER"


class ShiftType(str, Enum):
    MORNING = "MORNING"
    AFTERNOON = "AFTERNOON"
    NIGHT = "NIGHT"
    SPLIT = "SPLIT"
    FLEX = "FLEX"
    OVERTIME = "OVERTIME"


class ShiftStatus(str, Enum):
    SCHEDULED = "SCHEDULED"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    NO_SHOW = "NO_SHOW"
    CANCELLED = "CANCELLED"
    PARTIAL = "PARTIAL"


class LeaveType(str, Enum):
    ANNUAL = "ANNUAL"
    SICK = "SICK"
    CASUAL = "CASUAL"
    MATERNITY = "MATERNITY"
    PATERNITY = "PATERNITY"
    UNPAID = "UNPAID"
    COMPENSATORY = "COMPENSATORY"


class LeaveStatus(str, Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    CANCELLED = "CANCELLED"


# ============================================================================
# WORKER SCHEMAS
# ============================================================================

class WorkerSkill(BaseModel):
    """Worker skill entry."""
    skill: SkillCategory
    level: SkillLevel
    certified_date: Optional[date] = None
    expiry_date: Optional[date] = None


class WorkerCertification(BaseModel):
    """Worker certification."""
    name: str
    issuer: Optional[str] = None
    issue_date: date
    expiry_date: Optional[date] = None
    certificate_number: Optional[str] = None


class WorkerCreate(BaseModel):
    """Create a warehouse worker."""
    employee_code: str = Field(..., min_length=2, max_length=30)
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    email: Optional[str] = None
    phone: Optional[str] = None

    worker_type: WorkerType = WorkerType.FULL_TIME
    hire_date: date

    primary_warehouse_id: uuid.UUID
    primary_zone_id: Optional[uuid.UUID] = None
    supervisor_id: Optional[uuid.UUID] = None
    user_id: Optional[uuid.UUID] = None

    skills: Optional[Dict[str, str]] = Field(
        None,
        description="Skill matrix: {skill: level}"
    )
    certifications: Optional[List[WorkerCertification]] = None
    equipment_certified: Optional[List[str]] = None

    preferred_shift: Optional[ShiftType] = None
    max_hours_per_week: int = Field(40, ge=10, le=60)
    can_work_overtime: bool = True
    can_work_weekends: bool = True

    hourly_rate: Decimal = Field(Decimal("0"), ge=0)
    overtime_multiplier: Decimal = Field(Decimal("1.5"), ge=1, le=3)

    annual_leave_balance: Decimal = Field(Decimal("0"), ge=0)
    sick_leave_balance: Decimal = Field(Decimal("0"), ge=0)
    casual_leave_balance: Decimal = Field(Decimal("0"), ge=0)

    notes: Optional[str] = None


class WorkerUpdate(BaseModel):
    """Update worker profile."""
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None

    worker_type: Optional[WorkerType] = None
    status: Optional[WorkerStatus] = None

    primary_warehouse_id: Optional[uuid.UUID] = None
    primary_zone_id: Optional[uuid.UUID] = None
    supervisor_id: Optional[uuid.UUID] = None

    skills: Optional[Dict[str, str]] = None
    certifications: Optional[List[Dict[str, Any]]] = None
    equipment_certified: Optional[List[str]] = None

    preferred_shift: Optional[ShiftType] = None
    max_hours_per_week: Optional[int] = None
    can_work_overtime: Optional[bool] = None
    can_work_weekends: Optional[bool] = None

    hourly_rate: Optional[Decimal] = None
    overtime_multiplier: Optional[Decimal] = None

    annual_leave_balance: Optional[Decimal] = None
    sick_leave_balance: Optional[Decimal] = None
    casual_leave_balance: Optional[Decimal] = None

    notes: Optional[str] = None


class WorkerResponse(BaseModel):
    """Worker response."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: Optional[uuid.UUID] = None
    employee_code: str
    first_name: str
    last_name: str
    full_name: str
    email: Optional[str] = None
    phone: Optional[str] = None

    worker_type: str
    status: str
    hire_date: date
    termination_date: Optional[date] = None
    years_of_service: float

    primary_warehouse_id: uuid.UUID
    primary_zone_id: Optional[uuid.UUID] = None
    supervisor_id: Optional[uuid.UUID] = None

    skills: Optional[Dict[str, Any]] = None
    certifications: Optional[Dict[str, Any]] = None
    equipment_certified: Optional[List[str]] = None

    preferred_shift: Optional[str] = None
    max_hours_per_week: int
    can_work_overtime: bool
    can_work_weekends: bool

    hourly_rate: Decimal
    overtime_multiplier: Decimal

    # Performance
    avg_picks_per_hour: Optional[Decimal] = None
    avg_units_per_hour: Optional[Decimal] = None
    accuracy_rate: Optional[Decimal] = None
    productivity_score: Optional[Decimal] = None

    # Attendance
    attendance_rate: Optional[Decimal] = None
    tardiness_count_ytd: int
    absence_count_ytd: int

    # Leave Balances
    annual_leave_balance: Decimal
    sick_leave_balance: Decimal
    casual_leave_balance: Decimal

    created_at: datetime
    updated_at: datetime


class WorkerListResponse(BaseModel):
    """Paginated worker list."""
    items: List[WorkerResponse]
    total: int
    page: int
    size: int
    pages: int


# ============================================================================
# SHIFT SCHEMAS
# ============================================================================

class ShiftCreate(BaseModel):
    """Create a work shift."""
    worker_id: uuid.UUID
    warehouse_id: uuid.UUID
    shift_date: date
    shift_type: ShiftType

    scheduled_start: time
    scheduled_end: time
    scheduled_break_minutes: int = Field(30, ge=0, le=120)

    assigned_zone_id: Optional[uuid.UUID] = None
    assigned_function: Optional[str] = None
    supervisor_id: Optional[uuid.UUID] = None

    is_overtime: bool = False
    notes: Optional[str] = None


class ShiftUpdate(BaseModel):
    """Update a shift."""
    shift_type: Optional[ShiftType] = None
    status: Optional[ShiftStatus] = None

    scheduled_start: Optional[time] = None
    scheduled_end: Optional[time] = None
    scheduled_break_minutes: Optional[int] = None

    assigned_zone_id: Optional[uuid.UUID] = None
    assigned_function: Optional[str] = None
    supervisor_id: Optional[uuid.UUID] = None

    is_overtime: Optional[bool] = None
    notes: Optional[str] = None


class ClockInRequest(BaseModel):
    """Clock in request."""
    notes: Optional[str] = None


class ClockOutRequest(BaseModel):
    """Clock out request."""
    break_minutes: int = Field(0, ge=0, le=120)
    notes: Optional[str] = None


class ShiftResponse(BaseModel):
    """Shift response."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    worker_id: uuid.UUID
    warehouse_id: uuid.UUID

    shift_date: date
    shift_type: str
    status: str

    scheduled_start: time
    scheduled_end: time
    scheduled_break_minutes: int
    scheduled_hours: float

    actual_start: Optional[datetime] = None
    actual_end: Optional[datetime] = None
    actual_break_minutes: Optional[int] = None
    actual_hours: Optional[float] = None

    assigned_zone_id: Optional[uuid.UUID] = None
    assigned_function: Optional[str] = None
    supervisor_id: Optional[uuid.UUID] = None

    tasks_completed: int
    units_processed: int
    errors_count: int

    productive_minutes: Optional[int] = None
    idle_minutes: Optional[int] = None
    travel_minutes: Optional[int] = None

    is_overtime: bool
    overtime_hours: Decimal
    is_late: bool

    created_at: datetime
    updated_at: datetime
    notes: Optional[str] = None


class ShiftListResponse(BaseModel):
    """Paginated shift list."""
    items: List[ShiftResponse]
    total: int
    page: int
    size: int
    pages: int


class BulkShiftCreate(BaseModel):
    """Create shifts for multiple workers."""
    worker_ids: List[uuid.UUID]
    warehouse_id: uuid.UUID
    shift_date: date
    shift_type: ShiftType

    scheduled_start: time
    scheduled_end: time
    scheduled_break_minutes: int = Field(30, ge=0, le=120)

    assigned_function: Optional[str] = None


# ============================================================================
# SHIFT TEMPLATE SCHEMAS
# ============================================================================

class ShiftTemplateCreate(BaseModel):
    """Create a shift template."""
    name: str = Field(..., min_length=2, max_length=100)
    shift_type: ShiftType
    warehouse_id: uuid.UUID

    start_time: time
    end_time: time
    break_duration_minutes: int = Field(30, ge=0, le=120)

    days_of_week: List[int] = Field(
        ...,
        description="0=Monday, 6=Sunday"
    )

    min_workers: int = Field(1, ge=1)
    max_workers: int = Field(10, ge=1)
    ideal_workers: int = Field(5, ge=1)

    notes: Optional[str] = None


class ShiftTemplateResponse(BaseModel):
    """Shift template response."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    shift_type: str
    warehouse_id: uuid.UUID

    start_time: time
    end_time: time
    break_duration_minutes: int

    days_of_week: List[int]

    min_workers: int
    max_workers: int
    ideal_workers: int

    is_active: bool
    created_at: datetime
    notes: Optional[str] = None


# ============================================================================
# LABOR STANDARD SCHEMAS
# ============================================================================

class LaborStandardCreate(BaseModel):
    """Create a labor standard."""
    warehouse_id: uuid.UUID
    function: str = Field(..., description="PICKING, PACKING, etc.")
    zone_id: Optional[uuid.UUID] = None

    units_per_hour: Decimal = Field(..., gt=0)
    lines_per_hour: Optional[Decimal] = None
    orders_per_hour: Optional[Decimal] = None

    travel_time_per_pick: int = Field(15, ge=0)
    pick_time_per_unit: int = Field(5, ge=0)
    setup_time: int = Field(60, ge=0)

    threshold_minimum: Decimal = Field(Decimal("70"), ge=0, le=100)
    threshold_target: Decimal = Field(Decimal("100"), ge=0, le=200)
    threshold_excellent: Decimal = Field(Decimal("120"), ge=0, le=200)

    effective_from: date
    effective_to: Optional[date] = None

    notes: Optional[str] = None


class LaborStandardResponse(BaseModel):
    """Labor standard response."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    warehouse_id: uuid.UUID
    function: str
    zone_id: Optional[uuid.UUID] = None

    units_per_hour: Decimal
    lines_per_hour: Optional[Decimal] = None
    orders_per_hour: Optional[Decimal] = None

    travel_time_per_pick: int
    pick_time_per_unit: int
    setup_time: int

    threshold_minimum: Decimal
    threshold_target: Decimal
    threshold_excellent: Decimal

    effective_from: date
    effective_to: Optional[date] = None
    is_active: bool

    created_at: datetime
    updated_at: datetime


# ============================================================================
# PRODUCTIVITY METRIC SCHEMAS
# ============================================================================

class ProductivityMetricResponse(BaseModel):
    """Productivity metric response."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    worker_id: uuid.UUID
    warehouse_id: uuid.UUID

    metric_date: date
    function: str

    hours_worked: Decimal
    productive_hours: Decimal
    idle_hours: Decimal

    units_processed: int
    lines_processed: int
    orders_processed: int
    tasks_completed: int

    units_per_hour: Decimal
    lines_per_hour: Decimal

    standard_units_per_hour: Decimal
    performance_percentage: Decimal

    errors_count: int
    accuracy_rate: Decimal

    labor_cost: Decimal
    cost_per_unit: Decimal

    created_at: datetime


class ProductivityMetricListResponse(BaseModel):
    """Paginated productivity metrics."""
    items: List[ProductivityMetricResponse]
    total: int
    page: int
    size: int
    pages: int


# ============================================================================
# LEAVE REQUEST SCHEMAS
# ============================================================================

class LeaveRequestCreate(BaseModel):
    """Create a leave request."""
    worker_id: uuid.UUID
    leave_type: LeaveType
    start_date: date
    end_date: date
    reason: Optional[str] = None


class LeaveRequestUpdate(BaseModel):
    """Update leave request (for approval/rejection)."""
    status: LeaveStatus
    rejection_reason: Optional[str] = None


class LeaveRequestResponse(BaseModel):
    """Leave request response."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    worker_id: uuid.UUID
    leave_type: str
    status: str

    start_date: date
    end_date: date
    days_requested: Decimal
    reason: Optional[str] = None

    approved_by: Optional[uuid.UUID] = None
    approved_at: Optional[datetime] = None
    rejection_reason: Optional[str] = None

    created_at: datetime
    updated_at: datetime


class LeaveRequestListResponse(BaseModel):
    """Paginated leave requests."""
    items: List[LeaveRequestResponse]
    total: int
    page: int
    size: int
    pages: int


# ============================================================================
# STATISTICS SCHEMAS
# ============================================================================

class WorkerDashboardStats(BaseModel):
    """Dashboard stats for a worker."""
    worker_id: uuid.UUID
    worker_name: str

    # Today
    shift_today: Optional[ShiftResponse] = None
    is_clocked_in: bool
    hours_today: Decimal

    # This Week
    shifts_this_week: int
    hours_this_week: Decimal
    tasks_this_week: int
    units_this_week: int

    # Performance
    avg_performance_percentage: Decimal
    accuracy_rate: Decimal

    # Leave
    pending_leave_requests: int
    leave_balance: Dict[str, Decimal]


class LaborDashboardStats(BaseModel):
    """Overall labor management dashboard stats."""
    # Workers
    total_workers: int
    active_workers: int
    workers_on_leave: int
    workers_clocked_in: int

    # Today's Shifts
    shifts_scheduled_today: int
    shifts_in_progress: int
    shifts_completed_today: int
    no_shows_today: int

    # Productivity
    avg_performance_percentage: Decimal
    total_units_today: int
    avg_units_per_worker: Decimal

    # Overtime
    overtime_hours_today: Decimal
    workers_on_overtime: int

    # Labor Cost
    estimated_labor_cost_today: Decimal

    # Leave
    pending_leave_requests: int
    workers_on_approved_leave: int


class SchedulingForecast(BaseModel):
    """Staffing forecast for a date range."""
    date: date
    day_of_week: str
    expected_volume: int  # Expected units/orders
    recommended_workers: int
    scheduled_workers: int
    gap: int  # Positive = overstaffed, Negative = understaffed
    estimated_labor_cost: Decimal
