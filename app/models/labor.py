"""
Labor Management Models - Phase 4: Workforce Optimization.

This module implements warehouse labor management capabilities:
- Worker: Warehouse worker profiles with skills and certifications
- WorkShift: Shift scheduling and time tracking
- WorkAssignment: Task-worker assignments with performance tracking
- LaborStandard: Engineered labor standards for productivity measurement
- ProductivityMetric: Worker and team productivity analytics
"""
import uuid
from datetime import datetime, timezone, date, time, timedelta
from decimal import Decimal
from enum import Enum
from typing import TYPE_CHECKING, Optional, List, Dict, Any

from sqlalchemy import (
    String, Boolean, DateTime, ForeignKey, Integer, Text,
    Numeric, Date, Time, Index, UniqueConstraint
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.warehouse import Warehouse
    from app.models.wms import WarehouseZone
    from app.models.user import User


# ============================================================================
# ENUMS
# ============================================================================

class WorkerType(str, Enum):
    """Worker employment type."""
    FULL_TIME = "FULL_TIME"
    PART_TIME = "PART_TIME"
    TEMPORARY = "TEMPORARY"
    CONTRACT = "CONTRACT"
    SEASONAL = "SEASONAL"


class WorkerStatus(str, Enum):
    """Worker status."""
    ACTIVE = "ACTIVE"
    ON_LEAVE = "ON_LEAVE"
    SUSPENDED = "SUSPENDED"
    TERMINATED = "TERMINATED"
    TRAINING = "TRAINING"


class SkillCategory(str, Enum):
    """Skill categories for warehouse workers."""
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
    """Skill proficiency levels."""
    NOVICE = "NOVICE"           # Learning
    INTERMEDIATE = "INTERMEDIATE"  # Can work independently
    PROFICIENT = "PROFICIENT"   # Efficient and accurate
    EXPERT = "EXPERT"           # Can train others
    MASTER = "MASTER"           # Subject matter expert


class ShiftType(str, Enum):
    """Shift types."""
    MORNING = "MORNING"         # 6 AM - 2 PM
    AFTERNOON = "AFTERNOON"     # 2 PM - 10 PM
    NIGHT = "NIGHT"             # 10 PM - 6 AM
    SPLIT = "SPLIT"             # Split shift
    FLEX = "FLEX"               # Flexible hours
    OVERTIME = "OVERTIME"       # Overtime shift


class ShiftStatus(str, Enum):
    """Shift status."""
    SCHEDULED = "SCHEDULED"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    NO_SHOW = "NO_SHOW"
    CANCELLED = "CANCELLED"
    PARTIAL = "PARTIAL"         # Partial shift worked


class AssignmentType(str, Enum):
    """Work assignment type."""
    ZONE = "ZONE"               # Assigned to a zone
    TASK = "TASK"               # Assigned specific tasks
    FUNCTION = "FUNCTION"       # Assigned a function (picking, packing)
    FLOAT = "FLOAT"             # Floater - as needed


class LeaveType(str, Enum):
    """Leave types."""
    ANNUAL = "ANNUAL"
    SICK = "SICK"
    CASUAL = "CASUAL"
    MATERNITY = "MATERNITY"
    PATERNITY = "PATERNITY"
    UNPAID = "UNPAID"
    COMPENSATORY = "COMPENSATORY"


class LeaveStatus(str, Enum):
    """Leave request status."""
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    CANCELLED = "CANCELLED"


# ============================================================================
# MODELS
# ============================================================================

class WarehouseWorker(Base):
    """
    Warehouse worker profile.

    Tracks worker information, skills, certifications, and performance.
    """
    __tablename__ = "warehouse_workers"
    __table_args__ = (
        UniqueConstraint('tenant_id', 'employee_code', name='uq_worker_employee_code'),
        Index('ix_warehouse_workers_status', 'status'),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
        index=True
    )

    # Link to user account
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )

    # Employee Information
    employee_code: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        index=True
    )
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)
    email: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    phone: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)

    # Employment
    worker_type: Mapped[str] = mapped_column(
        String(30),
        default="FULL_TIME",
        nullable=False
    )
    status: Mapped[str] = mapped_column(
        String(30),
        default="ACTIVE",
        nullable=False,
        index=True
    )
    hire_date: Mapped[date] = mapped_column(Date, nullable=False)
    termination_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)

    # Assignment
    primary_warehouse_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("warehouses.id", ondelete="RESTRICT"),
        nullable=False,
        index=True
    )
    primary_zone_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("warehouse_zones.id", ondelete="SET NULL"),
        nullable=True
    )
    supervisor_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("warehouse_workers.id", ondelete="SET NULL"),
        nullable=True
    )

    # Skills (stored as JSONB for flexibility)
    skills: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=True,
        comment="Skill matrix: {skill: level}"
    )
    certifications: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=True,
        comment="Certifications with expiry dates"
    )
    equipment_certified: Mapped[Optional[List[str]]] = mapped_column(
        JSONB,
        nullable=True,
        comment="List of equipment worker can operate"
    )

    # Preferences
    preferred_shift: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    max_hours_per_week: Mapped[int] = mapped_column(Integer, default=40)
    can_work_overtime: Mapped[bool] = mapped_column(Boolean, default=True)
    can_work_weekends: Mapped[bool] = mapped_column(Boolean, default=True)

    # Pay Rate (for labor cost calculations)
    hourly_rate: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        default=0,
        comment="Base hourly rate"
    )
    overtime_multiplier: Mapped[Decimal] = mapped_column(
        Numeric(3, 2),
        default=Decimal("1.5"),
        comment="OT pay multiplier"
    )

    # Performance Metrics (rolling averages)
    avg_picks_per_hour: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2), nullable=True)
    avg_units_per_hour: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2), nullable=True)
    accuracy_rate: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(5, 2),
        nullable=True,
        comment="Accuracy percentage"
    )
    productivity_score: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(5, 2),
        nullable=True,
        comment="Overall productivity score 0-100"
    )

    # Attendance
    attendance_rate: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(5, 2),
        nullable=True,
        comment="Attendance percentage"
    )
    tardiness_count_ytd: Mapped[int] = mapped_column(Integer, default=0)
    absence_count_ytd: Mapped[int] = mapped_column(Integer, default=0)

    # Leave Balances
    annual_leave_balance: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=0)
    sick_leave_balance: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=0)
    casual_leave_balance: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=0)

    # Notes
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    user: Mapped[Optional["User"]] = relationship("User")
    primary_warehouse: Mapped["Warehouse"] = relationship("Warehouse")
    primary_zone: Mapped[Optional["WarehouseZone"]] = relationship("WarehouseZone")
    supervisor: Mapped[Optional["WarehouseWorker"]] = relationship(
        "WarehouseWorker",
        remote_side=[id]
    )
    shifts: Mapped[List["WorkShift"]] = relationship(
        "WorkShift",
        back_populates="worker",
        foreign_keys="WorkShift.worker_id"
    )
    leave_requests: Mapped[List["WarehouseLeaveRequest"]] = relationship(
        "WarehouseLeaveRequest",
        back_populates="worker",
        foreign_keys="WarehouseLeaveRequest.worker_id"
    )

    @property
    def full_name(self) -> str:
        """Get worker's full name."""
        return f"{self.first_name} {self.last_name}"

    @property
    def years_of_service(self) -> float:
        """Calculate years of service."""
        end_date = self.termination_date or date.today()
        return (end_date - self.hire_date).days / 365.25


class WorkShift(Base):
    """
    Worker shift schedule and time tracking.

    Tracks scheduled and actual work hours.
    """
    __tablename__ = "work_shifts"
    __table_args__ = (
        Index('ix_work_shifts_date', 'shift_date'),
        Index('ix_work_shifts_worker', 'worker_id', 'shift_date'),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
        index=True
    )

    # Worker
    worker_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("warehouse_workers.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Warehouse
    warehouse_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("warehouses.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Shift Details
    shift_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    shift_type: Mapped[str] = mapped_column(String(30), nullable=False)
    status: Mapped[str] = mapped_column(
        String(30),
        default="SCHEDULED",
        nullable=False
    )

    # Scheduled Time
    scheduled_start: Mapped[time] = mapped_column(Time, nullable=False)
    scheduled_end: Mapped[time] = mapped_column(Time, nullable=False)
    scheduled_break_minutes: Mapped[int] = mapped_column(Integer, default=30)

    # Actual Time (clock in/out)
    actual_start: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )
    actual_end: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )
    actual_break_minutes: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Zone/Function Assignment
    assigned_zone_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("warehouse_zones.id", ondelete="SET NULL"),
        nullable=True
    )
    assigned_function: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        comment="PICKING, PACKING, RECEIVING, etc."
    )

    # Supervisor
    supervisor_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("warehouse_workers.id", ondelete="SET NULL"),
        nullable=True
    )

    # Performance during shift
    tasks_completed: Mapped[int] = mapped_column(Integer, default=0)
    units_processed: Mapped[int] = mapped_column(Integer, default=0)
    errors_count: Mapped[int] = mapped_column(Integer, default=0)

    # Time breakdown
    productive_minutes: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    idle_minutes: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    travel_minutes: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Overtime
    is_overtime: Mapped[bool] = mapped_column(Boolean, default=False)
    overtime_hours: Mapped[Decimal] = mapped_column(Numeric(4, 2), default=0)
    overtime_approved_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        nullable=True
    )

    # Notes
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    no_show_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    worker: Mapped["WarehouseWorker"] = relationship(
        "WarehouseWorker",
        back_populates="shifts",
        foreign_keys=[worker_id]
    )
    warehouse: Mapped["Warehouse"] = relationship("Warehouse")
    assigned_zone: Mapped[Optional["WarehouseZone"]] = relationship("WarehouseZone")

    @property
    def scheduled_hours(self) -> float:
        """Calculate scheduled work hours."""
        start_dt = datetime.combine(self.shift_date, self.scheduled_start)
        end_dt = datetime.combine(self.shift_date, self.scheduled_end)
        if end_dt < start_dt:
            end_dt += timedelta(days=1)  # Night shift crossing midnight
        total_minutes = (end_dt - start_dt).total_seconds() / 60
        return (total_minutes - self.scheduled_break_minutes) / 60

    @property
    def actual_hours(self) -> Optional[float]:
        """Calculate actual worked hours."""
        if not self.actual_start or not self.actual_end:
            return None
        total_minutes = (self.actual_end - self.actual_start).total_seconds() / 60
        break_minutes = self.actual_break_minutes or 0
        return (total_minutes - break_minutes) / 60

    @property
    def is_late(self) -> bool:
        """Check if worker was late."""
        if not self.actual_start:
            return False
        scheduled_dt = datetime.combine(self.shift_date, self.scheduled_start)
        scheduled_dt = scheduled_dt.replace(tzinfo=timezone.utc)
        return self.actual_start > scheduled_dt + timedelta(minutes=5)


class LaborStandard(Base):
    """
    Engineered labor standards for productivity measurement.

    Defines expected productivity rates for different tasks/functions.
    """
    __tablename__ = "labor_standards"
    __table_args__ = (
        UniqueConstraint(
            'tenant_id', 'warehouse_id', 'function', 'zone_id',
            name='uq_labor_standard'
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
        index=True
    )

    # Warehouse
    warehouse_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("warehouses.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Standard Details
    function: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="PICKING, PACKING, PUTAWAY, etc."
    )
    zone_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("warehouse_zones.id", ondelete="SET NULL"),
        nullable=True
    )

    # Standard Rates
    units_per_hour: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        nullable=False,
        comment="Expected units per hour"
    )
    lines_per_hour: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(10, 2),
        nullable=True,
        comment="Expected order lines per hour"
    )
    orders_per_hour: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(10, 2),
        nullable=True,
        comment="Expected orders per hour"
    )

    # Time Components (in seconds)
    travel_time_per_pick: Mapped[int] = mapped_column(
        Integer,
        default=15,
        comment="Average travel time seconds"
    )
    pick_time_per_unit: Mapped[int] = mapped_column(
        Integer,
        default=5,
        comment="Time to pick one unit seconds"
    )
    setup_time: Mapped[int] = mapped_column(
        Integer,
        default=60,
        comment="Task setup time seconds"
    )

    # Thresholds for performance evaluation
    threshold_minimum: Mapped[Decimal] = mapped_column(
        Numeric(5, 2),
        default=Decimal("70"),
        comment="Below this is underperforming %"
    )
    threshold_target: Mapped[Decimal] = mapped_column(
        Numeric(5, 2),
        default=Decimal("100"),
        comment="Target performance %"
    )
    threshold_excellent: Mapped[Decimal] = mapped_column(
        Numeric(5, 2),
        default=Decimal("120"),
        comment="Excellent performance %"
    )

    # Active period
    effective_from: Mapped[date] = mapped_column(Date, nullable=False)
    effective_to: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Notes
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc)
    )
    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        nullable=True
    )

    # Relationships
    warehouse: Mapped["Warehouse"] = relationship("Warehouse")
    zone: Mapped[Optional["WarehouseZone"]] = relationship("WarehouseZone")


class ProductivityMetric(Base):
    """
    Worker productivity metrics (daily/weekly/monthly rollups).

    Tracks actual vs. standard performance for analytics.
    """
    __tablename__ = "productivity_metrics"
    __table_args__ = (
        UniqueConstraint(
            'tenant_id', 'worker_id', 'metric_date', 'function',
            name='uq_productivity_metric'
        ),
        Index('ix_productivity_metrics_date', 'metric_date'),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
        index=True
    )

    # Worker
    worker_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("warehouse_workers.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Warehouse
    warehouse_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("warehouses.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Date and Function
    metric_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    function: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="PICKING, PACKING, etc."
    )

    # Time
    hours_worked: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=0)
    productive_hours: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=0)
    idle_hours: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=0)

    # Volume
    units_processed: Mapped[int] = mapped_column(Integer, default=0)
    lines_processed: Mapped[int] = mapped_column(Integer, default=0)
    orders_processed: Mapped[int] = mapped_column(Integer, default=0)
    tasks_completed: Mapped[int] = mapped_column(Integer, default=0)

    # Rates
    units_per_hour: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=0)
    lines_per_hour: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=0)

    # Performance vs. Standard
    standard_units_per_hour: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=0)
    performance_percentage: Mapped[Decimal] = mapped_column(
        Numeric(6, 2),
        default=0,
        comment="Actual vs. standard %"
    )

    # Quality
    errors_count: Mapped[int] = mapped_column(Integer, default=0)
    accuracy_rate: Mapped[Decimal] = mapped_column(
        Numeric(5, 2),
        default=Decimal("100"),
        comment="Accuracy %"
    )

    # Cost
    labor_cost: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        default=0,
        comment="Total labor cost"
    )
    cost_per_unit: Mapped[Decimal] = mapped_column(
        Numeric(10, 4),
        default=0,
        comment="Labor cost per unit"
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    worker: Mapped["WarehouseWorker"] = relationship("WarehouseWorker")
    warehouse: Mapped["Warehouse"] = relationship("Warehouse")


class WarehouseLeaveRequest(Base):
    """
    Worker leave requests.
    """
    __tablename__ = "warehouse_leave_requests"
    __table_args__ = (
        Index('ix_warehouse_leave_requests_worker', 'worker_id', 'start_date'),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
        index=True
    )

    # Worker
    worker_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("warehouse_workers.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Leave Details
    leave_type: Mapped[str] = mapped_column(String(30), nullable=False)
    status: Mapped[str] = mapped_column(
        String(30),
        default="PENDING",
        nullable=False
    )

    # Dates
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    days_requested: Mapped[Decimal] = mapped_column(Numeric(4, 1), nullable=False)

    # Reason
    reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Approval
    approved_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("warehouse_workers.id", ondelete="SET NULL"),
        nullable=True
    )
    approved_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )
    rejection_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    worker: Mapped["WarehouseWorker"] = relationship(
        "WarehouseWorker",
        back_populates="leave_requests",
        foreign_keys=[worker_id]
    )


class ShiftTemplate(Base):
    """
    Shift templates for scheduling.

    Defines standard shift patterns that can be applied to workers.
    """
    __tablename__ = "shift_templates"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
        index=True
    )

    # Template Info
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    shift_type: Mapped[str] = mapped_column(String(30), nullable=False)

    # Warehouse
    warehouse_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("warehouses.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Schedule
    start_time: Mapped[time] = mapped_column(Time, nullable=False)
    end_time: Mapped[time] = mapped_column(Time, nullable=False)
    break_duration_minutes: Mapped[int] = mapped_column(Integer, default=30)

    # Days (which days this template applies)
    days_of_week: Mapped[List[int]] = mapped_column(
        JSONB,
        nullable=False,
        comment="0=Monday, 6=Sunday"
    )

    # Staffing
    min_workers: Mapped[int] = mapped_column(Integer, default=1)
    max_workers: Mapped[int] = mapped_column(Integer, default=10)
    ideal_workers: Mapped[int] = mapped_column(Integer, default=5)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    warehouse: Mapped["Warehouse"] = relationship("Warehouse")
