"""
Advanced WMS Models - Phase 2: Wave Picking & Task Interleaving.

This module implements enterprise-grade WMS capabilities:
- PickWave: Wave picking management with carrier cutoff and optimization
- WarehouseTask: Generic task model for interleaving (pick, putaway, count, replenish)
- SlotScore: Bin slotting optimization with velocity scoring
- CrossDock: Cross-docking workflows for JIT fulfillment
"""
import uuid
from datetime import datetime, timezone, time, date
from decimal import Decimal
from enum import Enum
from typing import TYPE_CHECKING, Optional, List, Dict, Any

from sqlalchemy import (
    String, Boolean, DateTime, ForeignKey, Integer, Text,
    Numeric, Date, Time, Index, UniqueConstraint, CheckConstraint
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.warehouse import Warehouse
    from app.models.wms import WarehouseZone, WarehouseBin
    from app.models.picklist import Picklist
    from app.models.user import User
    from app.models.transporter import Transporter
    from app.models.product import Product


# ============================================================================
# ENUMS
# ============================================================================

class WaveType(str, Enum):
    """Wave creation strategy types."""
    CARRIER_CUTOFF = "CARRIER_CUTOFF"   # Group by carrier pickup time
    PRIORITY = "PRIORITY"               # Group by order priority/SLA
    ZONE = "ZONE"                       # Group by warehouse zone
    PRODUCT = "PRODUCT"                 # Group by product category
    CHANNEL = "CHANNEL"                 # Group by sales channel
    CUSTOMER = "CUSTOMER"               # Group by customer type (B2B/D2C)
    CUSTOM = "CUSTOM"                   # Custom rule-based


class WaveStatus(str, Enum):
    """Wave lifecycle status."""
    DRAFT = "DRAFT"                     # Being configured
    PLANNED = "PLANNED"                 # Orders assigned, not released
    RELEASED = "RELEASED"               # Released to floor
    IN_PROGRESS = "IN_PROGRESS"         # Picking started
    PARTIALLY_COMPLETE = "PARTIALLY_COMPLETE"  # Some picklists done
    COMPLETED = "COMPLETED"             # All picklists complete
    CANCELLED = "CANCELLED"             # Wave cancelled


class TaskType(str, Enum):
    """Warehouse task types for interleaving."""
    PICK = "PICK"                       # Order picking
    PUTAWAY = "PUTAWAY"                 # Inbound putaway
    REPLENISH = "REPLENISH"             # Forward pick replenishment
    CYCLE_COUNT = "CYCLE_COUNT"         # Inventory cycle count
    TRANSFER = "TRANSFER"               # Internal bin transfer
    RELOCATE = "RELOCATE"               # Slot relocation
    AUDIT = "AUDIT"                     # Inventory audit
    PACK = "PACK"                       # Packing task
    LOAD = "LOAD"                       # Truck loading


class TaskStatus(str, Enum):
    """Task lifecycle status."""
    PENDING = "PENDING"                 # Created, not assigned
    ASSIGNED = "ASSIGNED"               # Assigned to worker
    IN_PROGRESS = "IN_PROGRESS"         # Work started
    PAUSED = "PAUSED"                   # Temporarily paused
    COMPLETED = "COMPLETED"             # Successfully completed
    FAILED = "FAILED"                   # Failed/exception
    CANCELLED = "CANCELLED"             # Cancelled


class TaskPriority(str, Enum):
    """Task priority levels."""
    URGENT = "URGENT"                   # Immediate (SLA breach risk)
    HIGH = "HIGH"                       # Same-day orders
    NORMAL = "NORMAL"                   # Standard priority
    LOW = "LOW"                         # Can wait


class SlotClass(str, Enum):
    """Bin slotting velocity classes (ABC)."""
    A = "A"                             # High velocity (20% SKUs, 80% picks)
    B = "B"                             # Medium velocity
    C = "C"                             # Low velocity
    D = "D"                             # Dead stock


class CrossDockType(str, Enum):
    """Cross-docking workflow types."""
    FLOW_THROUGH = "FLOW_THROUGH"       # Direct dock-to-dock (no storage)
    MERGE_IN_TRANSIT = "MERGE_IN_TRANSIT"  # Consolidate shipments
    BREAK_BULK = "BREAK_BULK"           # Split large shipments
    OPPORTUNISTIC = "OPPORTUNISTIC"     # JIT for urgent orders


class CrossDockStatus(str, Enum):
    """Cross-docking workflow status."""
    PENDING = "PENDING"                 # Awaiting inbound
    RECEIVING = "RECEIVING"             # Receiving in progress
    STAGED = "STAGED"                   # Items staged for outbound
    PROCESSING = "PROCESSING"           # Being sorted/consolidated
    READY_TO_SHIP = "READY_TO_SHIP"    # Ready for outbound
    COMPLETED = "COMPLETED"             # Shipped
    CANCELLED = "CANCELLED"             # Cancelled


# ============================================================================
# MODELS
# ============================================================================

class PickWave(Base):
    """
    Wave picking management.

    A wave groups multiple orders/picklists for efficient batch processing.
    Supports carrier cutoff times, zone-based picking, and optimization.
    """
    __tablename__ = "pick_waves"
    __table_args__ = (
        Index('ix_pick_waves_warehouse_status', 'warehouse_id', 'status'),
        Index('ix_pick_waves_cutoff_time', 'cutoff_time'),
        UniqueConstraint('tenant_id', 'wave_number', name='uq_pick_waves_tenant_number'),
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

    # Identification
    wave_number: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        index=True,
        comment="Unique wave number e.g., WV-20260205-001"
    )
    name: Mapped[Optional[str]] = mapped_column(
        String(200),
        nullable=True,
        comment="Descriptive name e.g., 'Morning DHL Cutoff'"
    )

    # Warehouse
    warehouse_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("warehouses.id", ondelete="RESTRICT"),
        nullable=False,
        index=True
    )

    # Wave Configuration
    wave_type: Mapped[str] = mapped_column(
        String(50),
        default="CARRIER_CUTOFF",
        nullable=False,
        comment="Wave grouping strategy"
    )
    status: Mapped[str] = mapped_column(
        String(50),
        default="DRAFT",
        nullable=False,
        index=True
    )

    # Carrier Cutoff (for CARRIER_CUTOFF type)
    carrier_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("transporters.id", ondelete="SET NULL"),
        nullable=True,
        comment="Target carrier for this wave"
    )
    cutoff_time: Mapped[Optional[time]] = mapped_column(
        Time,
        nullable=True,
        comment="Carrier pickup cutoff time"
    )
    cutoff_date: Mapped[Optional[date]] = mapped_column(
        Date,
        nullable=True,
        comment="Cutoff date (if not today)"
    )

    # Zone Filtering (for ZONE type)
    zone_ids: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=True,
        comment="List of zone IDs to include"
    )

    # Priority Filtering
    min_priority: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        comment="Minimum order priority (1=highest)"
    )
    max_priority: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True
    )

    # Channel/Customer Filtering
    channel_ids: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=True,
        comment="Filter by sales channel IDs"
    )
    customer_types: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=True,
        comment="Filter by customer type (B2B, D2C)"
    )

    # Wave Metrics
    total_orders: Mapped[int] = mapped_column(Integer, default=0)
    total_picklists: Mapped[int] = mapped_column(Integer, default=0)
    total_items: Mapped[int] = mapped_column(Integer, default=0)
    total_quantity: Mapped[int] = mapped_column(Integer, default=0)
    completed_picklists: Mapped[int] = mapped_column(Integer, default=0)
    picked_quantity: Mapped[int] = mapped_column(Integer, default=0)

    # Optimization Settings
    optimize_route: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        comment="Enable pick route optimization"
    )
    group_by_zone: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        comment="Group picks by zone for efficiency"
    )
    max_picks_per_trip: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        comment="Max items per picker trip"
    )
    max_weight_per_trip: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(10, 2),
        nullable=True,
        comment="Max weight (kg) per picker trip"
    )

    # Assignment
    assigned_pickers: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=True,
        comment="Assigned picker user IDs"
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc)
    )
    released_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )
    started_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )
    cancelled_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )

    # Audit
    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        nullable=True
    )
    released_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        nullable=True
    )
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    cancellation_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    warehouse: Mapped["Warehouse"] = relationship("Warehouse")
    carrier: Mapped[Optional["Transporter"]] = relationship("Transporter")
    picklists: Mapped[List["WavePicklist"]] = relationship(
        "WavePicklist",
        back_populates="wave",
        cascade="all, delete-orphan"
    )
    tasks: Mapped[List["WarehouseTask"]] = relationship(
        "WarehouseTask",
        back_populates="wave",
        foreign_keys="WarehouseTask.wave_id"
    )

    @property
    def progress_percentage(self) -> float:
        """Calculate wave completion percentage."""
        if self.total_quantity > 0:
            return (self.picked_quantity / self.total_quantity) * 100
        return 0.0

    @property
    def is_past_cutoff(self) -> bool:
        """Check if cutoff time has passed."""
        if self.cutoff_time and self.cutoff_date:
            cutoff_dt = datetime.combine(self.cutoff_date, self.cutoff_time)
            return datetime.now() > cutoff_dt
        elif self.cutoff_time:
            cutoff_dt = datetime.combine(date.today(), self.cutoff_time)
            return datetime.now() > cutoff_dt
        return False


class WavePicklist(Base):
    """
    Association between waves and picklists.
    Tracks which picklists belong to which wave.
    """
    __tablename__ = "wave_picklists"
    __table_args__ = (
        UniqueConstraint('wave_id', 'picklist_id', name='uq_wave_picklist'),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    wave_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("pick_waves.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    picklist_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("picklists.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Sequence within wave
    sequence: Mapped[int] = mapped_column(
        Integer,
        default=0,
        comment="Order in wave processing"
    )

    # Zone assignment for zone-based waves
    zone_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("warehouse_zones.id", ondelete="SET NULL"),
        nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    wave: Mapped["PickWave"] = relationship("PickWave", back_populates="picklists")
    picklist: Mapped["Picklist"] = relationship("Picklist")
    zone: Mapped[Optional["WarehouseZone"]] = relationship("WarehouseZone")


class WarehouseTask(Base):
    """
    Generic warehouse task for task interleaving.

    Supports all task types: picking, putaway, cycle count, replenishment.
    Enables interleaving to reduce empty travel time.
    """
    __tablename__ = "warehouse_tasks"
    __table_args__ = (
        Index('ix_warehouse_tasks_status_priority', 'status', 'priority'),
        Index('ix_warehouse_tasks_assigned', 'assigned_to', 'status'),
        Index('ix_warehouse_tasks_zone', 'zone_id', 'status'),
        Index('ix_warehouse_tasks_type_status', 'task_type', 'status'),
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

    # Task Identification
    task_number: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        index=True,
        comment="Unique task number e.g., TK-20260205-0001"
    )
    task_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
        comment="PICK, PUTAWAY, REPLENISH, CYCLE_COUNT, etc."
    )
    status: Mapped[str] = mapped_column(
        String(50),
        default="PENDING",
        nullable=False,
        index=True
    )
    priority: Mapped[str] = mapped_column(
        String(20),
        default="NORMAL",
        nullable=False,
        index=True,
        comment="URGENT, HIGH, NORMAL, LOW"
    )

    # Location
    warehouse_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("warehouses.id", ondelete="RESTRICT"),
        nullable=False,
        index=True
    )
    zone_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("warehouse_zones.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )

    # Source and Destination Bins
    source_bin_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("warehouse_bins.id", ondelete="SET NULL"),
        nullable=True,
        comment="Pick from / Count at"
    )
    source_bin_code: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True
    )
    destination_bin_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("warehouse_bins.id", ondelete="SET NULL"),
        nullable=True,
        comment="Put to / Stage at"
    )
    destination_bin_code: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True
    )

    # Product (for item-specific tasks)
    product_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("products.id", ondelete="SET NULL"),
        nullable=True
    )
    variant_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        nullable=True
    )
    sku: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    product_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Quantities
    quantity_required: Mapped[int] = mapped_column(Integer, default=0)
    quantity_completed: Mapped[int] = mapped_column(Integer, default=0)
    quantity_exception: Mapped[int] = mapped_column(
        Integer,
        default=0,
        comment="Short/damaged/missing"
    )

    # Reference to parent entities
    wave_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("pick_waves.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    picklist_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("picklists.id", ondelete="SET NULL"),
        nullable=True
    )
    picklist_item_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        nullable=True
    )
    grn_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
        comment="For putaway tasks from GRN"
    )
    cross_dock_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cross_docks.id", ondelete="SET NULL"),
        nullable=True
    )

    # Assignment
    assigned_to: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    assigned_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )

    # Task Interleaving - Next Task Suggestion
    suggested_next_task_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
        comment="AI-suggested next task to minimize travel"
    )

    # Equipment (for tasks requiring specific equipment)
    equipment_type: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        comment="FORKLIFT, CART, RF_GUN, etc."
    )
    equipment_id: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True
    )

    # SLA
    due_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Task deadline"
    )
    sla_priority_boost: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        comment="Auto-boosted due to SLA risk"
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc)
    )
    started_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )
    paused_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )

    # Performance Metrics
    travel_time_seconds: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        comment="Time to reach task location"
    )
    execution_time_seconds: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        comment="Time to complete task"
    )
    total_time_seconds: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True
    )

    # Exception Handling
    exception_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    exception_handled_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        nullable=True
    )
    exception_handled_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )

    # Notes
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    instruction: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Special instructions for worker"
    )

    # Audit
    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        nullable=True
    )

    # Relationships
    warehouse: Mapped["Warehouse"] = relationship("Warehouse")
    zone: Mapped[Optional["WarehouseZone"]] = relationship("WarehouseZone")
    source_bin: Mapped[Optional["WarehouseBin"]] = relationship(
        "WarehouseBin",
        foreign_keys=[source_bin_id]
    )
    destination_bin: Mapped[Optional["WarehouseBin"]] = relationship(
        "WarehouseBin",
        foreign_keys=[destination_bin_id]
    )
    product: Mapped[Optional["Product"]] = relationship("Product")
    wave: Mapped[Optional["PickWave"]] = relationship(
        "PickWave",
        back_populates="tasks",
        foreign_keys=[wave_id]
    )
    picklist: Mapped[Optional["Picklist"]] = relationship("Picklist")
    assigned_user: Mapped[Optional["User"]] = relationship("User", foreign_keys=[assigned_to])
    cross_dock: Mapped[Optional["CrossDock"]] = relationship("CrossDock", back_populates="tasks")

    @property
    def is_overdue(self) -> bool:
        """Check if task is past due."""
        if self.due_at and self.status not in ["COMPLETED", "CANCELLED"]:
            return datetime.now(timezone.utc) > self.due_at
        return False

    @property
    def efficiency_score(self) -> Optional[float]:
        """Calculate task efficiency (lower travel time = higher score)."""
        if self.total_time_seconds and self.execution_time_seconds:
            if self.total_time_seconds > 0:
                return (self.execution_time_seconds / self.total_time_seconds) * 100
        return None


class SlotScore(Base):
    """
    Bin slotting optimization scores.

    Tracks product velocity and optimal bin placement for efficiency.
    Supports ABC analysis and dynamic reslotting.
    """
    __tablename__ = "slot_scores"
    __table_args__ = (
        UniqueConstraint('tenant_id', 'product_id', 'warehouse_id', name='uq_slot_score_product_warehouse'),
        Index('ix_slot_scores_velocity', 'velocity_class', 'pick_frequency'),
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

    # Product
    product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("products.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    variant_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        nullable=True
    )
    sku: Mapped[str] = mapped_column(String(100), nullable=False, index=True)

    # Warehouse
    warehouse_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("warehouses.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Velocity Classification (ABC)
    velocity_class: Mapped[str] = mapped_column(
        String(1),
        default="C",
        nullable=False,
        index=True,
        comment="A/B/C/D velocity class"
    )
    pick_frequency: Mapped[int] = mapped_column(
        Integer,
        default=0,
        comment="Picks in analysis period"
    )
    pick_quantity: Mapped[int] = mapped_column(
        Integer,
        default=0,
        comment="Total units picked"
    )

    # Scoring Factors
    velocity_score: Mapped[Decimal] = mapped_column(
        Numeric(10, 4),
        default=0,
        comment="0-100 velocity score"
    )
    affinity_score: Mapped[Decimal] = mapped_column(
        Numeric(10, 4),
        default=0,
        comment="Co-pick affinity with other products"
    )
    ergonomic_score: Mapped[Decimal] = mapped_column(
        Numeric(10, 4),
        default=0,
        comment="Weight/size ergonomic factor"
    )
    seasonality_score: Mapped[Decimal] = mapped_column(
        Numeric(10, 4),
        default=0,
        comment="Seasonal demand adjustment"
    )
    total_score: Mapped[Decimal] = mapped_column(
        Numeric(10, 4),
        default=0,
        comment="Combined optimization score"
    )

    # Current Slot
    current_bin_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("warehouse_bins.id", ondelete="SET NULL"),
        nullable=True
    )
    current_zone_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("warehouse_zones.id", ondelete="SET NULL"),
        nullable=True
    )

    # Recommended Slot (from optimization)
    recommended_bin_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("warehouse_bins.id", ondelete="SET NULL"),
        nullable=True
    )
    recommended_zone_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("warehouse_zones.id", ondelete="SET NULL"),
        nullable=True
    )
    relocation_priority: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        comment="Priority for relocation (1=highest)"
    )
    relocation_reason: Mapped[Optional[str]] = mapped_column(
        String(200),
        nullable=True
    )

    # Analysis Period
    analysis_start: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    analysis_end: Mapped[Optional[date]] = mapped_column(Date, nullable=True)

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
    last_analyzed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )

    # Relationships
    product: Mapped["Product"] = relationship("Product")
    warehouse: Mapped["Warehouse"] = relationship("Warehouse")
    current_bin: Mapped[Optional["WarehouseBin"]] = relationship(
        "WarehouseBin",
        foreign_keys=[current_bin_id]
    )
    recommended_bin: Mapped[Optional["WarehouseBin"]] = relationship(
        "WarehouseBin",
        foreign_keys=[recommended_bin_id]
    )

    @property
    def needs_relocation(self) -> bool:
        """Check if product should be relocated."""
        return (
            self.recommended_bin_id is not None and
            self.recommended_bin_id != self.current_bin_id
        )


class CrossDock(Base):
    """
    Cross-docking workflow management.

    Enables direct dock-to-dock flow for JIT orders, reducing handling.
    """
    __tablename__ = "cross_docks"
    __table_args__ = (
        Index('ix_cross_docks_status', 'status'),
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

    # Identification
    cross_dock_number: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        unique=True,
        index=True
    )
    cross_dock_type: Mapped[str] = mapped_column(
        String(50),
        default="FLOW_THROUGH",
        nullable=False
    )
    status: Mapped[str] = mapped_column(
        String(50),
        default="PENDING",
        nullable=False,
        index=True
    )

    # Warehouse
    warehouse_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("warehouses.id", ondelete="RESTRICT"),
        nullable=False,
        index=True
    )

    # Inbound Reference
    inbound_grn_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
        comment="Incoming GRN"
    )
    inbound_po_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
        comment="Associated PO"
    )
    inbound_dock: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        comment="Receiving dock"
    )
    expected_arrival: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )
    actual_arrival: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )

    # Outbound Reference
    outbound_order_ids: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=True,
        comment="Target order IDs"
    )
    outbound_shipment_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        nullable=True
    )
    outbound_dock: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        comment="Shipping dock"
    )
    scheduled_departure: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )
    actual_departure: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )

    # Items
    items: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=True,
        comment="Cross-dock item details"
    )
    total_quantity: Mapped[int] = mapped_column(Integer, default=0)
    processed_quantity: Mapped[int] = mapped_column(Integer, default=0)

    # Staging
    staging_bin_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("warehouse_bins.id", ondelete="SET NULL"),
        nullable=True,
        comment="Temporary staging location"
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
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )

    # Audit
    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        nullable=True
    )
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    warehouse: Mapped["Warehouse"] = relationship("Warehouse")
    staging_bin: Mapped[Optional["WarehouseBin"]] = relationship("WarehouseBin")
    tasks: Mapped[List["WarehouseTask"]] = relationship(
        "WarehouseTask",
        back_populates="cross_dock"
    )

    @property
    def is_complete(self) -> bool:
        """Check if cross-dock is complete."""
        return self.processed_quantity >= self.total_quantity


class WorkerLocation(Base):
    """
    Real-time worker location tracking for task interleaving optimization.
    """
    __tablename__ = "worker_locations"

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
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
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

    # Current Location
    current_zone_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("warehouse_zones.id", ondelete="SET NULL"),
        nullable=True
    )
    current_bin_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("warehouse_bins.id", ondelete="SET NULL"),
        nullable=True
    )
    current_bin_code: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True
    )

    # Current Task
    current_task_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("warehouse_tasks.id", ondelete="SET NULL"),
        nullable=True
    )

    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_on_break: Mapped[bool] = mapped_column(Boolean, default=False)
    shift_start: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )
    shift_end: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )

    # Equipment
    equipment_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    equipment_id: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    # Performance (today)
    tasks_completed_today: Mapped[int] = mapped_column(Integer, default=0)
    items_picked_today: Mapped[int] = mapped_column(Integer, default=0)
    distance_traveled_meters: Mapped[int] = mapped_column(Integer, default=0)

    # Timestamps
    last_scan_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    user: Mapped["User"] = relationship("User")
    warehouse: Mapped["Warehouse"] = relationship("Warehouse")
    current_zone: Mapped[Optional["WarehouseZone"]] = relationship("WarehouseZone")
    current_bin: Mapped[Optional["WarehouseBin"]] = relationship("WarehouseBin")
    current_task: Mapped[Optional["WarehouseTask"]] = relationship("WarehouseTask")
