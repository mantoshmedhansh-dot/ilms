"""
Returns Management Models - Phase 9: Reverse Logistics & Return Processing.

This module implements return management operations:
- ReturnAuthorization: RMA/Return authorization
- ReturnReceipt: Receiving returned items
- ReturnInspection: Inspection and grading
- RefurbishmentOrder: Refurbishment/repair tracking
- DispositionRecord: Final disposition decisions
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
    from app.models.customer import Customer
    from app.models.vendor import Vendor


# ============================================================================
# ENUMS
# ============================================================================

class ReturnType(str, Enum):
    """Types of returns."""
    CUSTOMER_RETURN = "CUSTOMER_RETURN"       # B2C/D2C return
    B2B_RETURN = "B2B_RETURN"                 # B2B/dealer return
    VENDOR_RETURN = "VENDOR_RETURN"           # Return to vendor
    INTERNAL_TRANSFER = "INTERNAL_TRANSFER"   # Inter-warehouse
    WARRANTY_RETURN = "WARRANTY_RETURN"       # Warranty claim
    RECALL = "RECALL"                         # Product recall


class ReturnReason(str, Enum):
    """Reasons for return."""
    DEFECTIVE = "DEFECTIVE"
    DAMAGED = "DAMAGED"
    WRONG_ITEM = "WRONG_ITEM"
    SIZE_FIT = "SIZE_FIT"
    NOT_AS_DESCRIBED = "NOT_AS_DESCRIBED"
    CHANGED_MIND = "CHANGED_MIND"
    QUALITY_ISSUE = "QUALITY_ISSUE"
    MISSING_PARTS = "MISSING_PARTS"
    WARRANTY_CLAIM = "WARRANTY_CLAIM"
    RECALL = "RECALL"
    OTHER = "OTHER"


class RMAStatus(str, Enum):
    """Return authorization status."""
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    PARTIAL = "PARTIAL"
    EXPIRED = "EXPIRED"
    CANCELLED = "CANCELLED"
    RECEIVED = "RECEIVED"
    CLOSED = "CLOSED"


class ReturnReceiptStatus(str, Enum):
    """Return receipt status."""
    PENDING = "PENDING"
    IN_TRANSIT = "IN_TRANSIT"
    RECEIVED = "RECEIVED"
    INSPECTING = "INSPECTING"
    COMPLETED = "COMPLETED"


class InspectionGrade(str, Enum):
    """Inspection grade for returned items."""
    A_NEW = "A_NEW"               # Like new, can be resold
    B_GOOD = "B_GOOD"             # Minor issues, can be resold as open-box
    C_FAIR = "C_FAIR"             # Visible wear, needs refurbishment
    D_POOR = "D_POOR"             # Significant issues, needs repair
    F_SCRAP = "F_SCRAP"           # Not salvageable, scrap


class InspectionStatus(str, Enum):
    """Inspection status."""
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    DISPUTED = "DISPUTED"


class DispositionAction(str, Enum):
    """Disposition actions for returned items."""
    RESTOCK = "RESTOCK"                   # Return to sellable inventory
    RESTOCK_OPEN_BOX = "RESTOCK_OPEN_BOX" # Sell as open-box
    REFURBISH = "REFURBISH"               # Send for refurbishment
    REPAIR = "REPAIR"                     # Send for repair
    RETURN_TO_VENDOR = "RETURN_TO_VENDOR" # Return to vendor
    DONATE = "DONATE"                     # Donate
    SCRAP = "SCRAP"                       # Write off/scrap
    DESTROY = "DESTROY"                   # Destroy (compliance)
    HOLD = "HOLD"                         # Hold for review


class RefurbishmentStatus(str, Enum):
    """Refurbishment order status."""
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class RefundType(str, Enum):
    """Types of refunds."""
    FULL = "FULL"
    PARTIAL = "PARTIAL"
    STORE_CREDIT = "STORE_CREDIT"
    EXCHANGE = "EXCHANGE"
    REPLACEMENT = "REPLACEMENT"
    NO_REFUND = "NO_REFUND"


class RefundStatus(str, Enum):
    """Refund processing status."""
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


# ============================================================================
# MODELS
# ============================================================================

class ReturnAuthorization(Base):
    """
    Return Merchandise Authorization (RMA).

    Authorization for customers/dealers to return items.
    """
    __tablename__ = "return_authorizations"
    __table_args__ = (
        Index('ix_return_authorizations_status', 'status'),
        Index('ix_return_authorizations_type', 'return_type'),
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

    # RMA Identity
    rma_number: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        unique=True,
        index=True
    )
    return_type: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        index=True
    )
    status: Mapped[str] = mapped_column(
        String(30),
        default="PENDING",
        nullable=False,
        index=True
    )

    # Source Reference
    order_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
        index=True
    )
    order_number: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    invoice_number: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    # Customer/Dealer
    customer_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("customers.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    customer_name: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    customer_email: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    customer_phone: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)

    # Destination Warehouse
    warehouse_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("warehouses.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Return Details
    return_reason: Mapped[str] = mapped_column(String(50), nullable=False)
    reason_detail: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Quantities
    total_items: Mapped[int] = mapped_column(Integer, default=0)
    approved_items: Mapped[int] = mapped_column(Integer, default=0)
    received_items: Mapped[int] = mapped_column(Integer, default=0)

    # Values
    original_order_value: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        default=0
    )
    return_value: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        default=0
    )

    # Refund
    refund_type: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    refund_amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        default=0
    )
    refund_status: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)

    # Shipping
    return_shipping_method: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True
    )
    return_tracking_number: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True
    )
    shipping_paid_by: Mapped[Optional[str]] = mapped_column(
        String(30),
        nullable=True,
        comment="CUSTOMER, COMPANY, VENDOR"
    )
    shipping_cost: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        default=0
    )

    # Pickup (if applicable)
    pickup_required: Mapped[bool] = mapped_column(Boolean, default=False)
    pickup_address: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=True
    )
    pickup_scheduled_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    pickup_completed_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)

    # Dates
    request_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
        index=True
    )
    approval_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    expiry_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)

    # Approval
    approved_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )
    rejection_reason: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # Photos/Evidence
    photos: Mapped[Optional[List[str]]] = mapped_column(JSONB, nullable=True)
    documents: Mapped[Optional[List[str]]] = mapped_column(JSONB, nullable=True)

    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    internal_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

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
    warehouse: Mapped["Warehouse"] = relationship("Warehouse")
    customer: Mapped[Optional["Customer"]] = relationship("Customer")
    items: Mapped[List["ReturnAuthorizationItem"]] = relationship(
        "ReturnAuthorizationItem",
        back_populates="rma",
        cascade="all, delete-orphan"
    )


class ReturnAuthorizationItem(Base):
    """
    Individual item in a return authorization.
    """
    __tablename__ = "return_authorization_items"

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

    # RMA Reference
    rma_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("return_authorizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True
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

    # Quantities
    ordered_quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    requested_quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    approved_quantity: Mapped[int] = mapped_column(Integer, default=0)
    received_quantity: Mapped[int] = mapped_column(Integer, default=0)

    # Values
    unit_price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    total_value: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    refund_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)

    # Return Details
    return_reason: Mapped[str] = mapped_column(String(50), nullable=False)
    reason_detail: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Item Identity
    serial_numbers: Mapped[Optional[List[str]]] = mapped_column(JSONB, nullable=True)
    lot_number: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    # Status
    status: Mapped[str] = mapped_column(String(30), default="PENDING", nullable=False)

    # Evidence
    photos: Mapped[Optional[List[str]]] = mapped_column(JSONB, nullable=True)

    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    rma: Mapped["ReturnAuthorization"] = relationship(
        "ReturnAuthorization",
        back_populates="items"
    )
    product: Mapped["Product"] = relationship("Product")


class ReturnReceipt(Base):
    """
    Receipt of returned items at warehouse.

    Records the physical receipt of returns.
    """
    __tablename__ = "return_receipts"
    __table_args__ = (
        Index('ix_return_receipts_status', 'status'),
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

    # Receipt Identity
    receipt_number: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        unique=True,
        index=True
    )
    status: Mapped[str] = mapped_column(
        String(30),
        default="PENDING",
        nullable=False,
        index=True
    )

    # RMA Reference
    rma_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("return_authorizations.id", ondelete="CASCADE"),
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
    receiving_zone_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("warehouse_zones.id", ondelete="SET NULL"),
        nullable=True
    )
    receiving_bin_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("warehouse_bins.id", ondelete="SET NULL"),
        nullable=True
    )

    # Shipping
    carrier: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    tracking_number: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # Dates
    expected_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    receipt_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)

    # Quantities
    expected_quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    received_quantity: Mapped[int] = mapped_column(Integer, default=0)
    damaged_quantity: Mapped[int] = mapped_column(Integer, default=0)
    missing_quantity: Mapped[int] = mapped_column(Integer, default=0)

    # Package Condition
    package_condition: Mapped[Optional[str]] = mapped_column(
        String(30),
        nullable=True,
        comment="INTACT, DAMAGED, OPENED"
    )
    condition_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    package_photos: Mapped[Optional[List[str]]] = mapped_column(JSONB, nullable=True)

    # Receiver
    received_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
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
    rma: Mapped["ReturnAuthorization"] = relationship("ReturnAuthorization")
    warehouse: Mapped["Warehouse"] = relationship("Warehouse")
    receiving_zone: Mapped[Optional["WarehouseZone"]] = relationship("WarehouseZone")
    receiving_bin: Mapped[Optional["WarehouseBin"]] = relationship("WarehouseBin")
    items: Mapped[List["ReturnReceiptItem"]] = relationship(
        "ReturnReceiptItem",
        back_populates="receipt",
        cascade="all, delete-orphan"
    )


class ReturnReceiptItem(Base):
    """
    Individual item received in a return receipt.
    """
    __tablename__ = "return_receipt_items"

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

    # Receipt Reference
    receipt_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("return_receipts.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # RMA Item Reference
    rma_item_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("return_authorization_items.id", ondelete="CASCADE"),
        nullable=False
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
    expected_quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    received_quantity: Mapped[int] = mapped_column(Integer, default=0)
    damaged_quantity: Mapped[int] = mapped_column(Integer, default=0)

    # Item Identity
    serial_numbers: Mapped[Optional[List[str]]] = mapped_column(JSONB, nullable=True)
    lot_number: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    # Condition
    initial_condition: Mapped[Optional[str]] = mapped_column(
        String(30),
        nullable=True,
        comment="Initial visual assessment"
    )
    condition_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Location
    put_away_bin_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("warehouse_bins.id", ondelete="SET NULL"),
        nullable=True
    )

    # Inspection Status
    needs_inspection: Mapped[bool] = mapped_column(Boolean, default=True)
    inspection_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        nullable=True
    )

    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    receipt: Mapped["ReturnReceipt"] = relationship(
        "ReturnReceipt",
        back_populates="items"
    )
    product: Mapped["Product"] = relationship("Product")
    put_away_bin: Mapped[Optional["WarehouseBin"]] = relationship("WarehouseBin")


class ReturnInspection(Base):
    """
    Inspection of returned items.

    Quality assessment and grading of returns.
    """
    __tablename__ = "return_inspections"
    __table_args__ = (
        Index('ix_return_inspections_status', 'status'),
        Index('ix_return_inspections_grade', 'grade'),
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
    status: Mapped[str] = mapped_column(
        String(30),
        default="PENDING",
        nullable=False,
        index=True
    )

    # References
    receipt_item_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("return_receipt_items.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    rma_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False
    )

    # Warehouse
    warehouse_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("warehouses.id", ondelete="CASCADE"),
        nullable=False,
        index=True
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

    # Item Identity
    serial_number: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    lot_number: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    # Inspection
    inspection_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    inspector_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )

    # Grade
    grade: Mapped[Optional[str]] = mapped_column(
        String(20),
        nullable=True,
        index=True
    )

    # Checklist Results
    checklist_results: Mapped[Optional[List[Dict[str, Any]]]] = mapped_column(
        JSONB,
        nullable=True
    )

    # Defects Found
    defects_found: Mapped[Optional[List[Dict[str, Any]]]] = mapped_column(
        JSONB,
        nullable=True,
        comment="List of defects with severity"
    )
    defect_count: Mapped[int] = mapped_column(Integer, default=0)

    # Customer Claim Verification
    claim_verified: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    claim_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Functional Testing
    functional_test_passed: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    test_results: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)

    # Cosmetic Assessment
    cosmetic_condition: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    cosmetic_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Packaging
    original_packaging: Mapped[bool] = mapped_column(Boolean, default=False)
    packaging_condition: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    accessories_complete: Mapped[bool] = mapped_column(Boolean, default=True)
    missing_accessories: Mapped[Optional[List[str]]] = mapped_column(JSONB, nullable=True)

    # Photos/Evidence
    photos: Mapped[Optional[List[str]]] = mapped_column(JSONB, nullable=True)

    # Disposition Recommendation
    recommended_disposition: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    disposition_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Actual Disposition
    final_disposition: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    disposition_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )
    disposition_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )

    # Refund Impact
    refund_eligible: Mapped[bool] = mapped_column(Boolean, default=True)
    refund_deduction: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        default=0,
        comment="Deduction due to condition"
    )
    refund_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

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
    product: Mapped["Product"] = relationship("Product")
    inspector: Mapped[Optional["User"]] = relationship(
        "User",
        foreign_keys=[inspector_id]
    )


class RefurbishmentOrder(Base):
    """
    Order for refurbishment/repair of returned items.
    """
    __tablename__ = "refurbishment_orders"
    __table_args__ = (
        Index('ix_refurbishment_orders_status', 'status'),
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

    # Order Identity
    order_number: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        unique=True,
        index=True
    )
    status: Mapped[str] = mapped_column(
        String(30),
        default="PENDING",
        nullable=False,
        index=True
    )

    # Reference
    inspection_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("return_inspections.id", ondelete="CASCADE"),
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

    # Product
    product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("products.id", ondelete="RESTRICT"),
        nullable=False,
        index=True
    )
    sku: Mapped[str] = mapped_column(String(100), nullable=False)
    serial_number: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # Refurbishment Type
    refurbishment_type: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        comment="CLEAN, REPAIR, REPACKAGE, FULL"
    )

    # Work Required
    work_description: Mapped[str] = mapped_column(Text, nullable=False)
    work_items: Mapped[Optional[List[Dict[str, Any]]]] = mapped_column(
        JSONB,
        nullable=True
    )

    # Parts Required
    parts_required: Mapped[Optional[List[Dict[str, Any]]]] = mapped_column(
        JSONB,
        nullable=True
    )
    parts_cost: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=0)

    # Labor
    estimated_labor_hours: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(6, 2),
        nullable=True
    )
    actual_labor_hours: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(6, 2),
        nullable=True
    )
    labor_cost: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=0)

    # Total Cost
    total_cost: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=0)

    # Assignment
    assigned_to: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )
    assigned_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )

    # Vendor (if external)
    vendor_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("vendors.id", ondelete="SET NULL"),
        nullable=True
    )

    # Dates
    created_date: Mapped[date] = mapped_column(Date, nullable=False)
    due_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    started_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )

    # Result
    result_grade: Mapped[Optional[str]] = mapped_column(
        String(20),
        nullable=True,
        comment="Grade after refurbishment"
    )
    result_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Destination
    destination_bin_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("warehouse_bins.id", ondelete="SET NULL"),
        nullable=True
    )

    # QC
    qc_required: Mapped[bool] = mapped_column(Boolean, default=True)
    qc_passed: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
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

    # Photos
    before_photos: Mapped[Optional[List[str]]] = mapped_column(JSONB, nullable=True)
    after_photos: Mapped[Optional[List[str]]] = mapped_column(JSONB, nullable=True)

    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

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
    inspection: Mapped["ReturnInspection"] = relationship("ReturnInspection")
    warehouse: Mapped["Warehouse"] = relationship("Warehouse")
    product: Mapped["Product"] = relationship("Product")
    vendor: Mapped[Optional["Vendor"]] = relationship("Vendor")
    destination_bin: Mapped[Optional["WarehouseBin"]] = relationship("WarehouseBin")


class DispositionRecord(Base):
    """
    Record of final disposition for returned items.
    """
    __tablename__ = "disposition_records"
    __table_args__ = (
        Index('ix_disposition_records_action', 'disposition_action'),
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

    # Record Identity
    disposition_number: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        unique=True,
        index=True
    )

    # Reference
    inspection_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("return_inspections.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    refurbishment_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("refurbishment_orders.id", ondelete="SET NULL"),
        nullable=True
    )

    # Warehouse
    warehouse_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("warehouses.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Product
    product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("products.id", ondelete="RESTRICT"),
        nullable=False,
        index=True
    )
    sku: Mapped[str] = mapped_column(String(100), nullable=False)
    serial_number: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    lot_number: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    # Quantity
    quantity: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

    # Disposition
    disposition_action: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        index=True
    )
    disposition_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)

    # Grade at Disposition
    grade: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)

    # Value
    original_value: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    recovered_value: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    loss_value: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)

    # Destination Details
    destination_bin_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("warehouse_bins.id", ondelete="SET NULL"),
        nullable=True
    )

    # For RETURN_TO_VENDOR
    vendor_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("vendors.id", ondelete="SET NULL"),
        nullable=True
    )
    vendor_rma_number: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    vendor_credit_amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=0)

    # For DONATE
    donation_recipient: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    donation_reference: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    # For SCRAP/DESTROY
    destruction_method: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    destruction_certificate: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    environmental_compliance: Mapped[bool] = mapped_column(Boolean, default=True)

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

    # Execution
    executed_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )
    executed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )

    # Photos/Evidence
    photos: Mapped[Optional[List[str]]] = mapped_column(JSONB, nullable=True)

    reason: Mapped[str] = mapped_column(String(200), nullable=False)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

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

    # Relationships
    inspection: Mapped["ReturnInspection"] = relationship("ReturnInspection")
    refurbishment: Mapped[Optional["RefurbishmentOrder"]] = relationship("RefurbishmentOrder")
    warehouse: Mapped["Warehouse"] = relationship("Warehouse")
    product: Mapped["Product"] = relationship("Product")
    vendor: Mapped[Optional["Vendor"]] = relationship("Vendor")
    destination_bin: Mapped[Optional["WarehouseBin"]] = relationship("WarehouseBin")
