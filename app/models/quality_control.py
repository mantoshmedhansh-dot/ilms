"""
Quality Control Models - Phase 7: Inspection & Quality Management.

This module implements quality control operations:
- QCConfiguration: Quality standards and parameters
- QCInspection: Inspection records for receiving/shipping
- QCDefect: Defect recording and categorization
- QCHoldArea: Quarantine/hold management
- QCSampling: Sample-based inspection
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
    from app.models.vendor import Vendor
    from app.models.purchase import GoodsReceiptNote


# ============================================================================
# ENUMS
# ============================================================================

class InspectionType(str, Enum):
    """Types of QC inspection."""
    RECEIVING = "RECEIVING"             # Inbound receiving inspection
    SHIPPING = "SHIPPING"               # Outbound shipping inspection
    IN_PROCESS = "IN_PROCESS"           # In-process QC
    FINAL = "FINAL"                     # Final inspection
    RANDOM = "RANDOM"                   # Random sampling
    PERIODIC = "PERIODIC"               # Periodic quality check
    CUSTOMER_RETURN = "CUSTOMER_RETURN" # Return inspection
    CYCLE_COUNT = "CYCLE_COUNT"         # Inventory accuracy


class InspectionStatus(str, Enum):
    """Status of QC inspection."""
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    PASSED = "PASSED"
    FAILED = "FAILED"
    PARTIAL_PASS = "PARTIAL_PASS"
    ON_HOLD = "ON_HOLD"
    CANCELLED = "CANCELLED"


class DefectSeverity(str, Enum):
    """Severity of defects."""
    CRITICAL = "CRITICAL"       # Safety/compliance issues
    MAJOR = "MAJOR"             # Affects functionality
    MINOR = "MINOR"             # Cosmetic/minor issues
    OBSERVATION = "OBSERVATION" # Noted but acceptable


class DefectCategory(str, Enum):
    """Categories of defects."""
    DAMAGE = "DAMAGE"           # Physical damage
    COSMETIC = "COSMETIC"       # Appearance defects
    DIMENSIONAL = "DIMENSIONAL" # Size/spec out of range
    FUNCTIONAL = "FUNCTIONAL"   # Doesn't work properly
    PACKAGING = "PACKAGING"     # Packaging issues
    LABELING = "LABELING"       # Label/marking issues
    CONTAMINATION = "CONTAMINATION"
    EXPIRY = "EXPIRY"           # Expired or near-expiry
    DOCUMENTATION = "DOCUMENTATION"
    OTHER = "OTHER"


class HoldReason(str, Enum):
    """Reasons for QC hold."""
    PENDING_INSPECTION = "PENDING_INSPECTION"
    FAILED_QC = "FAILED_QC"
    CUSTOMER_RETURN = "CUSTOMER_RETURN"
    DAMAGE = "DAMAGE"
    RECALL = "RECALL"
    EXPIRY = "EXPIRY"
    VENDOR_DISPUTE = "VENDOR_DISPUTE"
    INVESTIGATION = "INVESTIGATION"
    OTHER = "OTHER"


class HoldStatus(str, Enum):
    """Status of QC hold."""
    ACTIVE = "ACTIVE"
    RELEASED = "RELEASED"
    SCRAPPED = "SCRAPPED"
    RETURNED_TO_VENDOR = "RETURNED_TO_VENDOR"
    REWORKED = "REWORKED"
    DISPOSED = "DISPOSED"


class SamplingPlan(str, Enum):
    """Sampling inspection plans."""
    FULL = "FULL"               # 100% inspection
    AQL_NORMAL = "AQL_NORMAL"   # AQL normal sampling
    AQL_TIGHTENED = "AQL_TIGHTENED"
    AQL_REDUCED = "AQL_REDUCED"
    SKIP_LOT = "SKIP_LOT"       # Skip lot sampling
    CUSTOM = "CUSTOM"


class DispositionAction(str, Enum):
    """Disposition actions for failed items."""
    ACCEPT = "ACCEPT"           # Accept as-is
    REJECT = "REJECT"           # Full rejection
    RETURN_TO_VENDOR = "RETURN_TO_VENDOR"
    REWORK = "REWORK"
    SCRAP = "SCRAP"
    DOWNGRADE = "DOWNGRADE"     # Sell as lower grade
    HOLD = "HOLD"


# ============================================================================
# MODELS
# ============================================================================

class QCConfiguration(Base):
    """
    Quality control configuration and standards.

    Defines QC parameters for products/vendors.
    """
    __tablename__ = "qc_configurations"
    __table_args__ = (
        UniqueConstraint('tenant_id', 'config_code', name='uq_qc_config_code'),
        Index('ix_qc_configurations_product', 'product_id'),
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

    # Identity
    config_code: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        index=True
    )
    config_name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Scope
    warehouse_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("warehouses.id", ondelete="CASCADE"),
        nullable=True,
        index=True
    )
    product_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("products.id", ondelete="CASCADE"),
        nullable=True,
        index=True
    )
    category_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("categories.id", ondelete="CASCADE"),
        nullable=True
    )
    vendor_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("vendors.id", ondelete="CASCADE"),
        nullable=True
    )

    # Inspection Settings
    inspection_type: Mapped[str] = mapped_column(
        String(30),
        default="RECEIVING",
        nullable=False
    )
    sampling_plan: Mapped[str] = mapped_column(
        String(30),
        default="FULL",
        nullable=False
    )
    sample_size_percent: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(5, 2),
        nullable=True,
        comment="For percentage-based sampling"
    )
    sample_size_quantity: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        comment="For fixed-quantity sampling"
    )
    aql_level: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(4, 2),
        nullable=True,
        comment="Acceptable Quality Level"
    )

    # Pass/Fail Criteria
    max_defect_percent: Mapped[Decimal] = mapped_column(
        Numeric(5, 2),
        default=0,
        comment="Max defect % to pass"
    )
    max_critical_defects: Mapped[int] = mapped_column(Integer, default=0)
    max_major_defects: Mapped[int] = mapped_column(Integer, default=0)
    max_minor_defects: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Checkpoints
    checkpoints: Mapped[Optional[List[Dict[str, Any]]]] = mapped_column(
        JSONB,
        nullable=True,
        comment="List of inspection checkpoints"
    )

    # Measurements
    measurements: Mapped[Optional[List[Dict[str, Any]]]] = mapped_column(
        JSONB,
        nullable=True,
        comment="Required measurements with tolerances"
    )

    # Auto-actions
    auto_release_on_pass: Mapped[bool] = mapped_column(Boolean, default=True)
    auto_hold_on_fail: Mapped[bool] = mapped_column(Boolean, default=True)
    require_supervisor_approval: Mapped[bool] = mapped_column(Boolean, default=False)

    # Triggers
    is_receiving_required: Mapped[bool] = mapped_column(Boolean, default=True)
    is_shipping_required: Mapped[bool] = mapped_column(Boolean, default=False)

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
    warehouse: Mapped[Optional["Warehouse"]] = relationship("Warehouse")
    product: Mapped[Optional["Product"]] = relationship("Product")
    vendor: Mapped[Optional["Vendor"]] = relationship("Vendor")


class QCInspection(Base):
    """
    QC inspection record.

    Records inspection results for receiving/shipping.
    """
    __tablename__ = "qc_inspections"
    __table_args__ = (
        Index('ix_qc_inspections_date', 'inspection_date'),
        Index('ix_qc_inspections_status', 'status'),
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

    # Inspection Identity
    inspection_number: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        unique=True,
        index=True
    )
    inspection_type: Mapped[str] = mapped_column(String(30), nullable=False)
    status: Mapped[str] = mapped_column(
        String(30),
        default="PENDING",
        nullable=False,
        index=True
    )

    # Location
    warehouse_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("warehouses.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    zone_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("warehouse_zones.id", ondelete="SET NULL"),
        nullable=True
    )

    # QC Configuration
    config_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("qc_configurations.id", ondelete="SET NULL"),
        nullable=True
    )

    # Source Reference
    grn_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("goods_receipt_notes.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    shipment_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        nullable=True
    )
    order_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        nullable=True
    )
    return_order_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        nullable=True
    )

    # Product
    product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("products.id", ondelete="RESTRICT"),
        nullable=False,
        index=True
    )
    sku: Mapped[str] = mapped_column(String(100), nullable=False)
    product_name: Mapped[str] = mapped_column(String(255), nullable=False)

    # Vendor (for receiving)
    vendor_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("vendors.id", ondelete="SET NULL"),
        nullable=True
    )

    # Quantities
    total_quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    sample_quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    passed_quantity: Mapped[int] = mapped_column(Integer, default=0)
    failed_quantity: Mapped[int] = mapped_column(Integer, default=0)
    pending_quantity: Mapped[int] = mapped_column(Integer, default=0)

    # Lot/Batch
    lot_number: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    batch_number: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    manufacture_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    expiry_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)

    # Timing
    inspection_date: Mapped[date] = mapped_column(
        Date,
        default=date.today,
        nullable=False,
        index=True
    )
    started_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )

    # Inspector
    inspector_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )

    # Results
    defect_count: Mapped[int] = mapped_column(Integer, default=0)
    critical_defects: Mapped[int] = mapped_column(Integer, default=0)
    major_defects: Mapped[int] = mapped_column(Integer, default=0)
    minor_defects: Mapped[int] = mapped_column(Integer, default=0)
    defect_rate: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(5, 2),
        nullable=True
    )

    # Checkpoints Results
    checkpoint_results: Mapped[Optional[List[Dict[str, Any]]]] = mapped_column(
        JSONB,
        nullable=True
    )

    # Measurements
    measurement_results: Mapped[Optional[List[Dict[str, Any]]]] = mapped_column(
        JSONB,
        nullable=True
    )

    # Disposition
    disposition: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    disposition_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    disposition_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )
    disposition_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )

    # Approval
    requires_approval: Mapped[bool] = mapped_column(Boolean, default=False)
    approved_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )
    approved_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )

    # Photos/Documents
    photos: Mapped[Optional[List[str]]] = mapped_column(
        JSONB,
        nullable=True
    )
    documents: Mapped[Optional[List[str]]] = mapped_column(
        JSONB,
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

    # Relationships
    warehouse: Mapped["Warehouse"] = relationship("Warehouse")
    zone: Mapped[Optional["WarehouseZone"]] = relationship("WarehouseZone")
    config: Mapped[Optional["QCConfiguration"]] = relationship("QCConfiguration")
    product: Mapped["Product"] = relationship("Product")
    vendor: Mapped[Optional["Vendor"]] = relationship("Vendor")
    grn: Mapped[Optional["GoodsReceiptNote"]] = relationship("GoodsReceiptNote")
    inspector: Mapped[Optional["User"]] = relationship(
        "User",
        foreign_keys=[inspector_id]
    )
    defects: Mapped[List["QCDefect"]] = relationship(
        "QCDefect",
        back_populates="inspection"
    )


class QCDefect(Base):
    """
    QC defect record.

    Records individual defects found during inspection.
    """
    __tablename__ = "qc_defects"
    __table_args__ = (
        Index('ix_qc_defects_inspection', 'inspection_id'),
        Index('ix_qc_defects_severity', 'severity'),
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

    # Inspection Reference
    inspection_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("qc_inspections.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Defect Details
    defect_code: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        index=True
    )
    defect_name: Mapped[str] = mapped_column(String(100), nullable=False)
    category: Mapped[str] = mapped_column(String(30), nullable=False)
    severity: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        index=True
    )
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Quantity
    defect_quantity: Mapped[int] = mapped_column(Integer, default=1)

    # Location on product
    defect_location: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        comment="Where on the product"
    )

    # Serial/LPN affected
    serial_numbers: Mapped[Optional[List[str]]] = mapped_column(
        JSONB,
        nullable=True
    )

    # Root Cause
    root_cause: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    is_vendor_related: Mapped[bool] = mapped_column(Boolean, default=False)

    # Photos
    photos: Mapped[Optional[List[str]]] = mapped_column(
        JSONB,
        nullable=True
    )

    # Recorded by
    recorded_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc)
    )

    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    inspection: Mapped["QCInspection"] = relationship(
        "QCInspection",
        back_populates="defects"
    )


class QCHoldArea(Base):
    """
    QC hold/quarantine area.

    Manages inventory on QC hold.
    """
    __tablename__ = "qc_hold_areas"
    __table_args__ = (
        Index('ix_qc_hold_areas_status', 'status'),
        Index('ix_qc_hold_areas_product', 'product_id'),
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

    # Hold Identity
    hold_number: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        unique=True,
        index=True
    )
    status: Mapped[str] = mapped_column(
        String(30),
        default="ACTIVE",
        nullable=False,
        index=True
    )

    # Location
    warehouse_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("warehouses.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    hold_bin_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("warehouse_bins.id", ondelete="SET NULL"),
        nullable=True
    )

    # Reason
    hold_reason: Mapped[str] = mapped_column(String(30), nullable=False)
    reason_detail: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Source
    inspection_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("qc_inspections.id", ondelete="SET NULL"),
        nullable=True
    )
    grn_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        nullable=True
    )
    return_order_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        nullable=True
    )

    # Product
    product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("products.id", ondelete="RESTRICT"),
        nullable=False,
        index=True
    )
    sku: Mapped[str] = mapped_column(String(100), nullable=False)

    # Quantities
    hold_quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    released_quantity: Mapped[int] = mapped_column(Integer, default=0)
    scrapped_quantity: Mapped[int] = mapped_column(Integer, default=0)
    returned_quantity: Mapped[int] = mapped_column(Integer, default=0)
    remaining_quantity: Mapped[int] = mapped_column(Integer, nullable=False)

    # Lot/Batch
    lot_number: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    serial_numbers: Mapped[Optional[List[str]]] = mapped_column(
        JSONB,
        nullable=True
    )

    # Vendor (if return to vendor)
    vendor_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("vendors.id", ondelete="SET NULL"),
        nullable=True
    )

    # Timing
    hold_date: Mapped[date] = mapped_column(
        Date,
        default=date.today,
        nullable=False
    )
    target_resolution_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    resolved_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)

    # Created/Resolved by
    created_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )
    resolved_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )

    # Resolution
    resolution_action: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    resolution_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

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
    hold_bin: Mapped[Optional["WarehouseBin"]] = relationship("WarehouseBin")
    inspection: Mapped[Optional["QCInspection"]] = relationship("QCInspection")
    product: Mapped["Product"] = relationship("Product")
    vendor: Mapped[Optional["Vendor"]] = relationship("Vendor")


class QCSampling(Base):
    """
    QC sampling results.

    Records sample-based inspection results.
    """
    __tablename__ = "qc_samplings"
    __table_args__ = (
        Index('ix_qc_samplings_inspection', 'inspection_id'),
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

    # Inspection Reference
    inspection_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("qc_inspections.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Sample Identity
    sample_number: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Sample sequence in inspection"
    )

    # Sample Details
    sample_quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    passed_quantity: Mapped[int] = mapped_column(Integer, default=0)
    failed_quantity: Mapped[int] = mapped_column(Integer, default=0)

    # Serial/LPN
    serial_numbers: Mapped[Optional[List[str]]] = mapped_column(
        JSONB,
        nullable=True
    )
    lpn: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    # Checkpoint Results
    checkpoint_results: Mapped[Optional[List[Dict[str, Any]]]] = mapped_column(
        JSONB,
        nullable=True
    )

    # Measurements
    measurements: Mapped[Optional[List[Dict[str, Any]]]] = mapped_column(
        JSONB,
        nullable=True
    )

    # Result
    result: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        comment="PASS, FAIL, PARTIAL"
    )
    defect_count: Mapped[int] = mapped_column(Integer, default=0)

    # Inspector
    inspected_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )
    inspected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc)
    )

    # Photos
    photos: Mapped[Optional[List[str]]] = mapped_column(
        JSONB,
        nullable=True
    )

    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    inspection: Mapped["QCInspection"] = relationship("QCInspection")
