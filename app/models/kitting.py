"""
Kitting & Assembly Models - Phase 8: Kit Management & Assembly Operations.

This module implements kitting and assembly operations:
- KitDefinition: Kit/bundle product definitions
- KitComponent: Components that make up a kit
- KitWorkOrder: Work orders for kit assembly/disassembly
- KitBuildRecord: Individual kit build tracking
- AssemblyStation: Assembly workstation management
"""
import uuid
from datetime import datetime, timezone, date
from decimal import Decimal
from enum import Enum
from typing import TYPE_CHECKING, Optional, List, Dict, Any

from sqlalchemy import (
    String, Boolean, DateTime, ForeignKey, Integer, Text,
    Numeric, Date, Index, UniqueConstraint
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.warehouse import Warehouse
    from app.models.wms import WarehouseZone, WarehouseBin
    from app.models.user import User
    from app.models.product import Product


# ============================================================================
# ENUMS
# ============================================================================

class KitType(str, Enum):
    """Types of kits."""
    STANDARD = "STANDARD"           # Pre-defined fixed kit
    CONFIGURABLE = "CONFIGURABLE"   # Customer-configurable
    PROMOTIONAL = "PROMOTIONAL"     # Promotional bundle
    SEASONAL = "SEASONAL"           # Seasonal kit
    SUBSCRIPTION = "SUBSCRIPTION"   # Subscription box
    CUSTOM = "CUSTOM"               # One-off custom kit


class KitStatus(str, Enum):
    """Kit definition status."""
    DRAFT = "DRAFT"
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    DISCONTINUED = "DISCONTINUED"


class ComponentType(str, Enum):
    """Types of kit components."""
    REQUIRED = "REQUIRED"           # Must be included
    OPTIONAL = "OPTIONAL"           # Customer choice
    SUBSTITUTE = "SUBSTITUTE"       # Can substitute another
    ADD_ON = "ADD_ON"               # Optional add-on


class WorkOrderType(str, Enum):
    """Types of kit work orders."""
    ASSEMBLY = "ASSEMBLY"           # Build kit from components
    DISASSEMBLY = "DISASSEMBLY"     # Break kit into components
    REWORK = "REWORK"               # Fix/modify existing kit
    REPACK = "REPACK"               # Repackage kit


class WorkOrderStatus(str, Enum):
    """Work order status."""
    DRAFT = "DRAFT"
    PENDING = "PENDING"
    RELEASED = "RELEASED"
    IN_PROGRESS = "IN_PROGRESS"
    ON_HOLD = "ON_HOLD"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


class WorkOrderPriority(str, Enum):
    """Work order priority."""
    LOW = "LOW"
    NORMAL = "NORMAL"
    HIGH = "HIGH"
    URGENT = "URGENT"


class BuildStatus(str, Enum):
    """Individual kit build status."""
    PENDING = "PENDING"
    PICKING = "PICKING"
    ASSEMBLING = "ASSEMBLING"
    QC_PENDING = "QC_PENDING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class StationStatus(str, Enum):
    """Assembly station status."""
    AVAILABLE = "AVAILABLE"
    OCCUPIED = "OCCUPIED"
    MAINTENANCE = "MAINTENANCE"
    OFFLINE = "OFFLINE"


# ============================================================================
# MODELS
# ============================================================================

class KitDefinition(Base):
    """
    Kit/bundle product definition.

    Defines what components make up a kit product.
    """
    __tablename__ = "kit_definitions"
    __table_args__ = (
        UniqueConstraint('tenant_id', 'kit_sku', name='uq_kit_sku'),
        Index('ix_kit_definitions_status', 'status'),
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

    # Kit Identity
    kit_sku: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True
    )
    kit_name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    kit_type: Mapped[str] = mapped_column(
        String(30),
        default="STANDARD",
        nullable=False
    )
    status: Mapped[str] = mapped_column(
        String(30),
        default="DRAFT",
        nullable=False,
        index=True
    )

    # Link to kit product (if kit is a sellable product)
    product_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("products.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )

    # Warehouse
    warehouse_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("warehouses.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )

    # Assembly Info
    assembly_time_minutes: Mapped[int] = mapped_column(
        Integer,
        default=10,
        comment="Standard assembly time"
    )
    labor_cost: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        default=0
    )
    packaging_cost: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        default=0
    )

    # Assembly Instructions
    instructions: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    instruction_images: Mapped[Optional[List[str]]] = mapped_column(
        JSONB,
        nullable=True
    )
    instruction_video_url: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True
    )

    # Packaging
    packaging_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    package_weight: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(10, 3),
        nullable=True
    )
    package_length: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(10, 2),
        nullable=True
    )
    package_width: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(10, 2),
        nullable=True
    )
    package_height: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(10, 2),
        nullable=True
    )

    # QC Requirements
    requires_qc: Mapped[bool] = mapped_column(Boolean, default=False)
    qc_checklist: Mapped[Optional[List[Dict[str, Any]]]] = mapped_column(
        JSONB,
        nullable=True
    )

    # Validity
    effective_from: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    effective_to: Mapped[Optional[date]] = mapped_column(Date, nullable=True)

    # Stats
    total_builds: Mapped[int] = mapped_column(Integer, default=0)
    avg_build_time_minutes: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(8, 2),
        nullable=True
    )

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
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )

    # Relationships
    warehouse: Mapped[Optional["Warehouse"]] = relationship("Warehouse")
    product: Mapped[Optional["Product"]] = relationship("Product")
    components: Mapped[List["KitComponent"]] = relationship(
        "KitComponent",
        back_populates="kit",
        cascade="all, delete-orphan"
    )


class KitComponent(Base):
    """
    Component that makes up a kit.

    Defines quantity and options for each component.
    """
    __tablename__ = "kit_components"
    __table_args__ = (
        Index('ix_kit_components_kit', 'kit_id'),
        Index('ix_kit_components_product', 'product_id'),
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

    # Kit Reference
    kit_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("kit_definitions.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Component Product
    product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("products.id", ondelete="RESTRICT"),
        nullable=False,
        index=True
    )
    sku: Mapped[str] = mapped_column(String(100), nullable=False)
    product_name: Mapped[str] = mapped_column(String(255), nullable=False)

    # Quantity
    quantity: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    uom: Mapped[str] = mapped_column(String(20), default="EACH", nullable=False)

    # Component Type
    component_type: Mapped[str] = mapped_column(
        String(30),
        default="REQUIRED",
        nullable=False
    )

    # Substitution
    substitute_group: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        comment="Group for interchangeable components"
    )
    substitute_priority: Mapped[int] = mapped_column(
        Integer,
        default=1,
        comment="Preference order for substitutes"
    )

    # Sequence
    sequence: Mapped[int] = mapped_column(
        Integer,
        default=0,
        comment="Assembly order"
    )

    # Cost
    component_cost: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        default=0
    )

    # Special Handling
    special_instructions: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    requires_serial: Mapped[bool] = mapped_column(Boolean, default=False)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

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
    kit: Mapped["KitDefinition"] = relationship(
        "KitDefinition",
        back_populates="components"
    )
    product: Mapped["Product"] = relationship("Product")


class AssemblyStation(Base):
    """
    Assembly workstation.

    Physical stations where kitting occurs.
    """
    __tablename__ = "assembly_stations"
    __table_args__ = (
        UniqueConstraint('tenant_id', 'warehouse_id', 'station_code', name='uq_station_code'),
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

    warehouse_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("warehouses.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Station Identity
    station_code: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        index=True
    )
    station_name: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[str] = mapped_column(
        String(30),
        default="AVAILABLE",
        nullable=False,
        index=True
    )

    # Location
    zone_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("warehouse_zones.id", ondelete="SET NULL"),
        nullable=True
    )

    # Equipment
    equipment: Mapped[Optional[List[str]]] = mapped_column(
        JSONB,
        nullable=True
    )
    tools_required: Mapped[Optional[List[str]]] = mapped_column(
        JSONB,
        nullable=True
    )

    # Capacity
    max_concurrent_builds: Mapped[int] = mapped_column(Integer, default=1)
    current_builds: Mapped[int] = mapped_column(Integer, default=0)

    # Assignment
    assigned_worker_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )
    assigned_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )

    # Current Work Order
    current_work_order_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        nullable=True
    )

    # Stats
    total_builds_today: Mapped[int] = mapped_column(Integer, default=0)
    avg_build_time_today: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(8, 2),
        nullable=True
    )

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
    zone: Mapped[Optional["WarehouseZone"]] = relationship("WarehouseZone")
    assigned_worker: Mapped[Optional["User"]] = relationship("User")


class KitWorkOrder(Base):
    """
    Work order for kit assembly/disassembly.

    Batch work order to build multiple kits.
    """
    __tablename__ = "kit_work_orders"
    __table_args__ = (
        Index('ix_kit_work_orders_status', 'status'),
        Index('ix_kit_work_orders_date', 'scheduled_date'),
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

    # Work Order Identity
    work_order_number: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        unique=True,
        index=True
    )
    work_order_type: Mapped[str] = mapped_column(
        String(30),
        default="ASSEMBLY",
        nullable=False
    )
    status: Mapped[str] = mapped_column(
        String(30),
        default="DRAFT",
        nullable=False,
        index=True
    )
    priority: Mapped[str] = mapped_column(
        String(20),
        default="NORMAL",
        nullable=False
    )

    # Kit Reference
    kit_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("kit_definitions.id", ondelete="RESTRICT"),
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

    # Station
    station_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("assembly_stations.id", ondelete="SET NULL"),
        nullable=True
    )

    # Quantities
    quantity_ordered: Mapped[int] = mapped_column(Integer, nullable=False)
    quantity_completed: Mapped[int] = mapped_column(Integer, default=0)
    quantity_failed: Mapped[int] = mapped_column(Integer, default=0)
    quantity_remaining: Mapped[int] = mapped_column(Integer, nullable=False)

    # Scheduling
    scheduled_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
        index=True
    )
    due_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    started_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )

    # Source Reference
    order_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
        comment="Sales order if kit is for specific order"
    )

    # Assignment
    assigned_to: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )

    # Component Availability
    components_available: Mapped[bool] = mapped_column(Boolean, default=False)
    component_shortage: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=True
    )

    # Destination
    destination_bin_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("warehouse_bins.id", ondelete="SET NULL"),
        nullable=True
    )

    # Time Tracking
    estimated_hours: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(6, 2),
        nullable=True
    )
    actual_hours: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(6, 2),
        nullable=True
    )

    # Cost
    estimated_cost: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        default=0
    )
    actual_cost: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        default=0
    )

    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    cancellation_reason: Mapped[Optional[str]] = mapped_column(
        String(200),
        nullable=True
    )

    # Audit
    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
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
    kit: Mapped["KitDefinition"] = relationship("KitDefinition")
    warehouse: Mapped["Warehouse"] = relationship("Warehouse")
    station: Mapped[Optional["AssemblyStation"]] = relationship("AssemblyStation")
    destination_bin: Mapped[Optional["WarehouseBin"]] = relationship("WarehouseBin")
    assigned_user: Mapped[Optional["User"]] = relationship(
        "User",
        foreign_keys=[assigned_to]
    )
    builds: Mapped[List["KitBuildRecord"]] = relationship(
        "KitBuildRecord",
        back_populates="work_order"
    )


class KitBuildRecord(Base):
    """
    Individual kit build record.

    Tracks each kit built under a work order.
    """
    __tablename__ = "kit_build_records"
    __table_args__ = (
        Index('ix_kit_build_records_work_order', 'work_order_id'),
        Index('ix_kit_build_records_status', 'status'),
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

    # Work Order Reference
    work_order_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("kit_work_orders.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Build Identity
    build_number: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Sequence within work order"
    )
    status: Mapped[str] = mapped_column(
        String(30),
        default="PENDING",
        nullable=False,
        index=True
    )

    # Kit Info (denormalized)
    kit_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False
    )
    kit_sku: Mapped[str] = mapped_column(String(100), nullable=False)

    # Serial/LPN
    serial_number: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        unique=True
    )
    lpn: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        comment="License Plate Number"
    )

    # Components Used
    components_used: Mapped[Optional[List[Dict[str, Any]]]] = mapped_column(
        JSONB,
        nullable=True,
        comment="Actual components with serials/lots"
    )

    # Station
    station_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("assembly_stations.id", ondelete="SET NULL"),
        nullable=True
    )

    # Builder
    built_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )

    # Timing
    started_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )
    build_time_minutes: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # QC
    qc_status: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    qc_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )
    qc_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )
    qc_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Destination
    destination_bin_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("warehouse_bins.id", ondelete="SET NULL"),
        nullable=True
    )

    # Failure
    failure_reason: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)

    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    work_order: Mapped["KitWorkOrder"] = relationship(
        "KitWorkOrder",
        back_populates="builds"
    )
    station: Mapped[Optional["AssemblyStation"]] = relationship("AssemblyStation")
    destination_bin: Mapped[Optional["WarehouseBin"]] = relationship("WarehouseBin")
    builder: Mapped[Optional["User"]] = relationship(
        "User",
        foreign_keys=[built_by]
    )
