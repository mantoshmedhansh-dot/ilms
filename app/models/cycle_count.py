"""
Cycle Counting Models - Phase 11: Cycle Counting & Physical Inventory.

Models for inventory counting operations including:
- Cycle count plans and schedules
- Count tasks and assignments
- Variance tracking and reconciliation
- Physical inventory (wall-to-wall counts)
"""
from datetime import datetime, date
from decimal import Decimal
from enum import Enum
from typing import Optional, List
from uuid import UUID, uuid4

from sqlalchemy import (
    String, Integer, DateTime, ForeignKey, Index, Text, Boolean,
    Numeric, Date, UniqueConstraint, JSON
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


# ============================================================================
# ENUMS
# ============================================================================

class CountType(str, Enum):
    """Type of inventory count."""
    CYCLE_COUNT = "cycle_count"              # Regular cycle counting
    PHYSICAL_INVENTORY = "physical_inventory" # Wall-to-wall count
    SPOT_CHECK = "spot_check"                # Random verification
    BLIND_COUNT = "blind_count"              # Counter doesn't see expected qty
    RECOUNT = "recount"                      # Follow-up count for variances
    ABC_COUNT = "abc_count"                  # ABC classification-based counting


class CountFrequency(str, Enum):
    """Frequency of cycle counts."""
    DAILY = "daily"
    WEEKLY = "weekly"
    BIWEEKLY = "biweekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    ANNUALLY = "annually"
    ON_DEMAND = "on_demand"


class CountMethod(str, Enum):
    """Method used for counting."""
    MANUAL = "manual"                # Paper-based manual count
    RF_SCANNER = "rf_scanner"        # RF scanner/mobile device
    BARCODE = "barcode"              # Barcode scanning
    RFID = "rfid"                    # RFID scanning
    SCALE = "scale"                  # Weight-based counting
    VISION = "vision"                # Computer vision/AI counting


class CountPlanStatus(str, Enum):
    """Status of count plan."""
    DRAFT = "draft"
    SCHEDULED = "scheduled"
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class CountTaskStatus(str, Enum):
    """Status of count task."""
    PENDING = "pending"
    ASSIGNED = "assigned"
    IN_PROGRESS = "in_progress"
    COUNTING = "counting"
    RECOUNTING = "recounting"
    PENDING_REVIEW = "pending_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class VarianceStatus(str, Enum):
    """Status of variance investigation."""
    PENDING = "pending"
    INVESTIGATING = "investigating"
    ROOT_CAUSE_IDENTIFIED = "root_cause_identified"
    ADJUSTMENT_PENDING = "adjustment_pending"
    ADJUSTED = "adjusted"
    WRITTEN_OFF = "written_off"
    RESOLVED = "resolved"
    ESCALATED = "escalated"


class VarianceReason(str, Enum):
    """Reason for inventory variance."""
    MISCOUNT = "miscount"
    MISPLACEMENT = "misplacement"
    DAMAGED = "damaged"
    THEFT = "theft"
    RECEIVING_ERROR = "receiving_error"
    SHIPPING_ERROR = "shipping_error"
    DATA_ENTRY_ERROR = "data_entry_error"
    UNIT_OF_MEASURE = "unit_of_measure"
    SYSTEM_ERROR = "system_error"
    UNKNOWN = "unknown"
    OTHER = "other"


class ABCClass(str, Enum):
    """ABC classification for items."""
    A = "A"  # High value/velocity
    B = "B"  # Medium value/velocity
    C = "C"  # Low value/velocity
    D = "D"  # Dead stock/obsolete


class ApprovalLevel(str, Enum):
    """Approval level based on variance threshold."""
    AUTO = "auto"              # Auto-approve within threshold
    SUPERVISOR = "supervisor"   # Supervisor approval
    MANAGER = "manager"         # Manager approval
    DIRECTOR = "director"       # Director approval
    EXECUTIVE = "executive"     # Executive approval


# ============================================================================
# MODELS
# ============================================================================

class CycleCountPlan(Base):
    """
    Cycle count plan defining what and when to count.

    Plans can be:
    - ABC-based: Different frequencies for A, B, C items
    - Zone-based: Rotate through warehouse zones
    - Product-based: Specific SKUs or categories
    - Random: Statistical sampling
    """
    __tablename__ = "cycle_count_plans"
    __table_args__ = (
        Index("idx_ccp_tenant_warehouse", "tenant_id", "warehouse_id"),
        Index("idx_ccp_status", "tenant_id", "status"),
        {"schema": "public"}
    )

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    tenant_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("public.tenants.id"), nullable=False
    )
    warehouse_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("public.warehouses.id"), nullable=False
    )

    # Plan Details
    plan_name: Mapped[str] = mapped_column(String(200), nullable=False)
    plan_code: Mapped[str] = mapped_column(String(50), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    count_type: Mapped[CountType] = mapped_column(
        String(30), nullable=False, default=CountType.CYCLE_COUNT
    )

    # Scheduling
    frequency: Mapped[CountFrequency] = mapped_column(
        String(20), nullable=False, default=CountFrequency.WEEKLY
    )
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[Optional[date]] = mapped_column(Date)
    next_count_date: Mapped[Optional[date]] = mapped_column(Date)

    # ABC Settings
    count_a_frequency: Mapped[Optional[str]] = mapped_column(String(20))  # e.g., "weekly"
    count_b_frequency: Mapped[Optional[str]] = mapped_column(String(20))  # e.g., "monthly"
    count_c_frequency: Mapped[Optional[str]] = mapped_column(String(20))  # e.g., "quarterly"

    # Selection Criteria
    zone_ids: Mapped[Optional[List]] = mapped_column(JSONB)          # List of zone UUIDs
    category_ids: Mapped[Optional[List]] = mapped_column(JSONB)      # List of category UUIDs
    product_ids: Mapped[Optional[List]] = mapped_column(JSONB)       # List of product UUIDs
    bin_ids: Mapped[Optional[List]] = mapped_column(JSONB)           # List of bin UUIDs
    abc_classes: Mapped[Optional[List]] = mapped_column(JSONB)       # List of ABC classes

    # Sampling (for random/statistical counts)
    sample_percentage: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 2))
    min_items_per_count: Mapped[int] = mapped_column(Integer, default=10)
    max_items_per_count: Mapped[int] = mapped_column(Integer, default=100)

    # Count Settings
    count_method: Mapped[CountMethod] = mapped_column(
        String(20), nullable=False, default=CountMethod.RF_SCANNER
    )
    blind_count: Mapped[bool] = mapped_column(Boolean, default=False)
    require_recount_on_variance: Mapped[bool] = mapped_column(Boolean, default=True)
    recount_threshold_percent: Mapped[Decimal] = mapped_column(
        Numeric(5, 2), default=Decimal("5.0")
    )
    recount_threshold_value: Mapped[Decimal] = mapped_column(
        Numeric(15, 2), default=Decimal("100.0")
    )

    # Approval Thresholds
    auto_approve_threshold_percent: Mapped[Decimal] = mapped_column(
        Numeric(5, 2), default=Decimal("1.0")
    )
    auto_approve_threshold_value: Mapped[Decimal] = mapped_column(
        Numeric(15, 2), default=Decimal("50.0")
    )
    supervisor_threshold_percent: Mapped[Decimal] = mapped_column(
        Numeric(5, 2), default=Decimal("5.0")
    )
    manager_threshold_percent: Mapped[Decimal] = mapped_column(
        Numeric(5, 2), default=Decimal("10.0")
    )
    director_threshold_value: Mapped[Decimal] = mapped_column(
        Numeric(15, 2), default=Decimal("10000.0")
    )

    status: Mapped[CountPlanStatus] = mapped_column(
        String(20), nullable=False, default=CountPlanStatus.DRAFT
    )

    # Statistics
    total_counts_completed: Mapped[int] = mapped_column(Integer, default=0)
    total_items_counted: Mapped[int] = mapped_column(Integer, default=0)
    total_variances_found: Mapped[int] = mapped_column(Integer, default=0)
    accuracy_rate: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 2))
    last_count_date: Mapped[Optional[date]] = mapped_column(Date)

    notes: Mapped[Optional[str]] = mapped_column(Text)

    # Audit
    created_by: Mapped[Optional[UUID]] = mapped_column(PG_UUID(as_uuid=True))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    schedules: Mapped[List["CountSchedule"]] = relationship(back_populates="plan")
    count_sessions: Mapped[List["CountSession"]] = relationship(back_populates="plan")


class CountSchedule(Base):
    """
    Schedule for generating count tasks.
    Links plan to specific dates and assignments.
    """
    __tablename__ = "count_schedules"
    __table_args__ = (
        Index("idx_cs_tenant_plan", "tenant_id", "plan_id"),
        Index("idx_cs_date", "tenant_id", "scheduled_date"),
        {"schema": "public"}
    )

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    tenant_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("public.tenants.id"), nullable=False
    )
    plan_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("public.cycle_count_plans.id"), nullable=False
    )
    warehouse_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("public.warehouses.id"), nullable=False
    )

    scheduled_date: Mapped[date] = mapped_column(Date, nullable=False)
    scheduled_time: Mapped[Optional[str]] = mapped_column(String(10))  # HH:MM format

    # Assignment
    assigned_to: Mapped[Optional[UUID]] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("public.users.id")
    )
    team_ids: Mapped[Optional[List]] = mapped_column(JSONB)  # Multiple assignees

    # Scope for this schedule
    zone_ids: Mapped[Optional[List]] = mapped_column(JSONB)
    bin_ids: Mapped[Optional[List]] = mapped_column(JSONB)
    product_ids: Mapped[Optional[List]] = mapped_column(JSONB)
    estimated_item_count: Mapped[int] = mapped_column(Integer, default=0)

    status: Mapped[str] = mapped_column(String(20), default="pending")
    session_id: Mapped[Optional[UUID]] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("public.count_sessions.id")
    )

    notes: Mapped[Optional[str]] = mapped_column(Text)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    plan: Mapped["CycleCountPlan"] = relationship(back_populates="schedules")


class CountSession(Base):
    """
    A counting session containing multiple count tasks.
    Represents a single execution of a count plan.
    """
    __tablename__ = "count_sessions"
    __table_args__ = (
        Index("idx_csess_tenant_warehouse", "tenant_id", "warehouse_id"),
        Index("idx_csess_status", "tenant_id", "status"),
        Index("idx_csess_date", "tenant_id", "count_date"),
        {"schema": "public"}
    )

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    tenant_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("public.tenants.id"), nullable=False
    )
    warehouse_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("public.warehouses.id"), nullable=False
    )
    plan_id: Mapped[Optional[UUID]] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("public.cycle_count_plans.id")
    )

    # Session Details
    session_number: Mapped[str] = mapped_column(String(50), nullable=False)
    session_name: Mapped[str] = mapped_column(String(200), nullable=False)
    count_type: Mapped[CountType] = mapped_column(
        String(30), nullable=False, default=CountType.CYCLE_COUNT
    )
    count_method: Mapped[CountMethod] = mapped_column(
        String(20), nullable=False, default=CountMethod.RF_SCANNER
    )
    blind_count: Mapped[bool] = mapped_column(Boolean, default=False)

    count_date: Mapped[date] = mapped_column(Date, nullable=False)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime)

    # Scope
    zone_ids: Mapped[Optional[List]] = mapped_column(JSONB)
    bin_ids: Mapped[Optional[List]] = mapped_column(JSONB)
    category_ids: Mapped[Optional[List]] = mapped_column(JSONB)

    # Progress Tracking
    total_tasks: Mapped[int] = mapped_column(Integer, default=0)
    completed_tasks: Mapped[int] = mapped_column(Integer, default=0)
    total_items: Mapped[int] = mapped_column(Integer, default=0)
    items_counted: Mapped[int] = mapped_column(Integer, default=0)
    items_with_variance: Mapped[int] = mapped_column(Integer, default=0)

    # Variance Summary
    total_variance_qty: Mapped[Decimal] = mapped_column(Numeric(15, 3), default=Decimal("0"))
    total_variance_value: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=Decimal("0"))
    positive_variance_qty: Mapped[Decimal] = mapped_column(Numeric(15, 3), default=Decimal("0"))
    negative_variance_qty: Mapped[Decimal] = mapped_column(Numeric(15, 3), default=Decimal("0"))

    # Accuracy Metrics
    accuracy_rate: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 2))
    first_count_accuracy: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 2))

    status: Mapped[CountTaskStatus] = mapped_column(
        String(20), nullable=False, default=CountTaskStatus.PENDING
    )

    # Approval
    approved_by: Mapped[Optional[UUID]] = mapped_column(PG_UUID(as_uuid=True))
    approved_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    approval_notes: Mapped[Optional[str]] = mapped_column(Text)

    notes: Mapped[Optional[str]] = mapped_column(Text)

    # Audit
    created_by: Mapped[Optional[UUID]] = mapped_column(PG_UUID(as_uuid=True))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    plan: Mapped[Optional["CycleCountPlan"]] = relationship(back_populates="count_sessions")
    tasks: Mapped[List["CountTask"]] = relationship(back_populates="session")
    variances: Mapped[List["InventoryVariance"]] = relationship(back_populates="session")


class CountTask(Base):
    """
    Individual count task for a specific location/item.
    """
    __tablename__ = "count_tasks"
    __table_args__ = (
        Index("idx_ct_tenant_session", "tenant_id", "session_id"),
        Index("idx_ct_status", "tenant_id", "status"),
        Index("idx_ct_assignee", "tenant_id", "assigned_to"),
        Index("idx_ct_bin", "tenant_id", "bin_id"),
        {"schema": "public"}
    )

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    tenant_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("public.tenants.id"), nullable=False
    )
    session_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("public.count_sessions.id"), nullable=False
    )
    warehouse_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("public.warehouses.id"), nullable=False
    )

    # Task Details
    task_number: Mapped[str] = mapped_column(String(50), nullable=False)
    sequence: Mapped[int] = mapped_column(Integer, default=0)  # Order in session

    # Location
    zone_id: Mapped[Optional[UUID]] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("public.warehouse_zones.id")
    )
    bin_id: Mapped[Optional[UUID]] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("public.warehouse_bins.id")
    )
    location_code: Mapped[str] = mapped_column(String(50), nullable=False)

    # Item (if item-level count, otherwise bin-level)
    product_id: Mapped[Optional[UUID]] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("public.products.id")
    )
    variant_id: Mapped[Optional[UUID]] = mapped_column(PG_UUID(as_uuid=True))
    lot_number: Mapped[Optional[str]] = mapped_column(String(50))
    serial_number: Mapped[Optional[str]] = mapped_column(String(100))

    # Expected (system) quantity - hidden in blind count
    expected_qty: Mapped[Decimal] = mapped_column(Numeric(15, 3), default=Decimal("0"))
    expected_uom: Mapped[str] = mapped_column(String(20), default="EACH")
    expected_value: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=Decimal("0"))

    # First Count
    first_count_qty: Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 3))
    first_count_by: Mapped[Optional[UUID]] = mapped_column(PG_UUID(as_uuid=True))
    first_count_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    first_count_method: Mapped[Optional[str]] = mapped_column(String(20))

    # Recount (if variance exceeds threshold)
    recount_required: Mapped[bool] = mapped_column(Boolean, default=False)
    recount_qty: Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 3))
    recount_by: Mapped[Optional[UUID]] = mapped_column(PG_UUID(as_uuid=True))
    recount_at: Mapped[Optional[datetime]] = mapped_column(DateTime)

    # Final Count
    final_count_qty: Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 3))
    final_count_value: Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 2))

    # Variance
    variance_qty: Mapped[Decimal] = mapped_column(Numeric(15, 3), default=Decimal("0"))
    variance_value: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=Decimal("0"))
    variance_percent: Mapped[Decimal] = mapped_column(Numeric(8, 4), default=Decimal("0"))
    has_variance: Mapped[bool] = mapped_column(Boolean, default=False)

    # Assignment
    assigned_to: Mapped[Optional[UUID]] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("public.users.id")
    )
    assigned_at: Mapped[Optional[datetime]] = mapped_column(DateTime)

    status: Mapped[CountTaskStatus] = mapped_column(
        String(20), nullable=False, default=CountTaskStatus.PENDING
    )

    # Approval
    approval_level: Mapped[Optional[str]] = mapped_column(String(20))
    approved_by: Mapped[Optional[UUID]] = mapped_column(PG_UUID(as_uuid=True))
    approved_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    rejection_reason: Mapped[Optional[str]] = mapped_column(Text)

    notes: Mapped[Optional[str]] = mapped_column(Text)
    photos: Mapped[Optional[List]] = mapped_column(JSONB)  # Evidence photos

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    session: Mapped["CountSession"] = relationship(back_populates="tasks")
    count_details: Mapped[List["CountDetail"]] = relationship(back_populates="task")


class CountDetail(Base):
    """
    Detailed count entries for a task.
    Captures each individual scan/entry during counting.
    """
    __tablename__ = "count_details"
    __table_args__ = (
        Index("idx_cd_tenant_task", "tenant_id", "task_id"),
        {"schema": "public"}
    )

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    tenant_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("public.tenants.id"), nullable=False
    )
    task_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("public.count_tasks.id"), nullable=False
    )

    # Count Entry
    count_sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    is_recount: Mapped[bool] = mapped_column(Boolean, default=False)

    # Item Details
    product_id: Mapped[Optional[UUID]] = mapped_column(PG_UUID(as_uuid=True))
    barcode_scanned: Mapped[Optional[str]] = mapped_column(String(100))
    lot_number: Mapped[Optional[str]] = mapped_column(String(50))
    serial_number: Mapped[Optional[str]] = mapped_column(String(100))
    expiry_date: Mapped[Optional[date]] = mapped_column(Date)

    # Quantity
    quantity: Mapped[Decimal] = mapped_column(Numeric(15, 3), nullable=False)
    uom: Mapped[str] = mapped_column(String(20), default="EACH")

    # Count Method
    count_method: Mapped[CountMethod] = mapped_column(
        String(20), nullable=False, default=CountMethod.RF_SCANNER
    )
    device_id: Mapped[Optional[str]] = mapped_column(String(50))

    # Counter
    counted_by: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("public.users.id"), nullable=False
    )
    counted_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Location (if moved)
    found_in_bin: Mapped[Optional[str]] = mapped_column(String(50))

    notes: Mapped[Optional[str]] = mapped_column(Text)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    task: Mapped["CountTask"] = relationship(back_populates="count_details")


class InventoryVariance(Base):
    """
    Inventory variance record for investigation and resolution.
    """
    __tablename__ = "inventory_variances"
    __table_args__ = (
        Index("idx_iv_tenant_session", "tenant_id", "session_id"),
        Index("idx_iv_status", "tenant_id", "status"),
        Index("idx_iv_product", "tenant_id", "product_id"),
        {"schema": "public"}
    )

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    tenant_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("public.tenants.id"), nullable=False
    )
    warehouse_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("public.warehouses.id"), nullable=False
    )
    session_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("public.count_sessions.id"), nullable=False
    )
    task_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("public.count_tasks.id"), nullable=False
    )

    # Variance Details
    variance_number: Mapped[str] = mapped_column(String(50), nullable=False)
    variance_date: Mapped[date] = mapped_column(Date, nullable=False)

    # Location
    zone_id: Mapped[Optional[UUID]] = mapped_column(PG_UUID(as_uuid=True))
    bin_id: Mapped[Optional[UUID]] = mapped_column(PG_UUID(as_uuid=True))
    location_code: Mapped[str] = mapped_column(String(50), nullable=False)

    # Item
    product_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("public.products.id"), nullable=False
    )
    variant_id: Mapped[Optional[UUID]] = mapped_column(PG_UUID(as_uuid=True))
    lot_number: Mapped[Optional[str]] = mapped_column(String(50))

    # Quantities
    system_qty: Mapped[Decimal] = mapped_column(Numeric(15, 3), nullable=False)
    counted_qty: Mapped[Decimal] = mapped_column(Numeric(15, 3), nullable=False)
    variance_qty: Mapped[Decimal] = mapped_column(Numeric(15, 3), nullable=False)
    uom: Mapped[str] = mapped_column(String(20), default="EACH")

    # Values
    unit_cost: Mapped[Decimal] = mapped_column(Numeric(15, 4), default=Decimal("0"))
    variance_value: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    variance_percent: Mapped[Decimal] = mapped_column(Numeric(8, 4), nullable=False)

    # Classification
    abc_class: Mapped[Optional[str]] = mapped_column(String(1))
    is_positive: Mapped[bool] = mapped_column(Boolean, default=False)  # Overcount
    is_negative: Mapped[bool] = mapped_column(Boolean, default=True)   # Shortage

    # Investigation
    status: Mapped[VarianceStatus] = mapped_column(
        String(30), nullable=False, default=VarianceStatus.PENDING
    )
    variance_reason: Mapped[Optional[VarianceReason]] = mapped_column(String(30))
    root_cause: Mapped[Optional[str]] = mapped_column(Text)
    corrective_action: Mapped[Optional[str]] = mapped_column(Text)

    # Approval
    approval_level: Mapped[ApprovalLevel] = mapped_column(
        String(20), nullable=False, default=ApprovalLevel.SUPERVISOR
    )
    approved_by: Mapped[Optional[UUID]] = mapped_column(PG_UUID(as_uuid=True))
    approved_at: Mapped[Optional[datetime]] = mapped_column(DateTime)

    # Adjustment
    adjustment_id: Mapped[Optional[UUID]] = mapped_column(PG_UUID(as_uuid=True))
    adjusted_by: Mapped[Optional[UUID]] = mapped_column(PG_UUID(as_uuid=True))
    adjusted_at: Mapped[Optional[datetime]] = mapped_column(DateTime)

    # Financial
    written_off: Mapped[bool] = mapped_column(Boolean, default=False)
    write_off_gl_account: Mapped[Optional[str]] = mapped_column(String(50))
    write_off_amount: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=Decimal("0"))

    investigated_by: Mapped[Optional[UUID]] = mapped_column(PG_UUID(as_uuid=True))
    investigation_notes: Mapped[Optional[str]] = mapped_column(Text)
    evidence_photos: Mapped[Optional[List]] = mapped_column(JSONB)

    notes: Mapped[Optional[str]] = mapped_column(Text)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    session: Mapped["CountSession"] = relationship(back_populates="variances")


class ABCClassification(Base):
    """
    ABC classification for products for cycle counting prioritization.
    """
    __tablename__ = "abc_classifications"
    __table_args__ = (
        UniqueConstraint("tenant_id", "warehouse_id", "product_id", name="uq_abc_product"),
        Index("idx_abc_tenant_warehouse", "tenant_id", "warehouse_id"),
        Index("idx_abc_class", "tenant_id", "abc_class"),
        {"schema": "public"}
    )

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    tenant_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("public.tenants.id"), nullable=False
    )
    warehouse_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("public.warehouses.id"), nullable=False
    )
    product_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("public.products.id"), nullable=False
    )

    # Classification
    abc_class: Mapped[ABCClass] = mapped_column(String(1), nullable=False)
    classification_method: Mapped[str] = mapped_column(String(30), default="value")  # value, velocity, both

    # Metrics
    annual_value: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=Decimal("0"))
    annual_velocity: Mapped[int] = mapped_column(Integer, default=0)
    cumulative_value_percent: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=Decimal("0"))
    cumulative_velocity_percent: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=Decimal("0"))

    # Count Requirements
    count_frequency: Mapped[CountFrequency] = mapped_column(String(20))
    last_count_date: Mapped[Optional[date]] = mapped_column(Date)
    next_count_date: Mapped[Optional[date]] = mapped_column(Date)
    times_counted_ytd: Mapped[int] = mapped_column(Integer, default=0)

    # Accuracy
    accuracy_rate: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 2))
    variance_history: Mapped[Optional[List]] = mapped_column(JSONB)

    calculated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )
