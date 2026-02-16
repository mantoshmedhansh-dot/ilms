"""Purchase/Procurement models for Procure-to-Pay cycle.

Supports:
- Purchase Requisition (Internal request)
- Purchase Order (PO)
- Goods Receipt Note (GRN)
- Vendor Invoice matching
- 3-Way Matching (PO-GRN-Invoice)
"""
import uuid
from datetime import datetime, date, timezone
from enum import Enum
from typing import TYPE_CHECKING, Optional, List
from decimal import Decimal

from sqlalchemy import String, Boolean, DateTime, ForeignKey, Integer, Text, Numeric, Date
from sqlalchemy import UniqueConstraint, Index, CheckConstraint
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import inspect as sa_inspect

from app.database import Base

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.warehouse import Warehouse
    from app.models.product import Product, ProductVariant
    from app.models.vendor import Vendor
    from app.models.wms import WarehouseBin
    from app.models.approval import ApprovalRequest
    from app.models.order import Order, OrderItem
    from app.models.billing import TaxInvoice, InvoiceItem, CreditDebitNote
    from app.models.customer import Customer
    from app.models.transporter import Transporter


# ==================== Enums ====================

class RequisitionStatus(str, Enum):
    """Purchase Requisition status."""
    DRAFT = "DRAFT"
    SUBMITTED = "SUBMITTED"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    CONVERTED = "CONVERTED"  # Converted to PO
    CANCELLED = "CANCELLED"


class POStatus(str, Enum):
    """Purchase Order status."""
    DRAFT = "DRAFT"
    PENDING_APPROVAL = "PENDING_APPROVAL"
    APPROVED = "APPROVED"
    SENT_TO_VENDOR = "SENT_TO_VENDOR"
    ACKNOWLEDGED = "ACKNOWLEDGED"  # Vendor acknowledged
    PARTIALLY_RECEIVED = "PARTIALLY_RECEIVED"
    FULLY_RECEIVED = "FULLY_RECEIVED"
    CLOSED = "CLOSED"
    CANCELLED = "CANCELLED"


class GRNStatus(str, Enum):
    """Goods Receipt Note status."""
    DRAFT = "DRAFT"
    PENDING_QC = "PENDING_QC"  # Quality check pending
    QC_PASSED = "QC_PASSED"
    QC_FAILED = "QC_FAILED"
    PARTIALLY_ACCEPTED = "PARTIALLY_ACCEPTED"
    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"
    PUT_AWAY_PENDING = "PUT_AWAY_PENDING"
    PUT_AWAY_COMPLETE = "PUT_AWAY_COMPLETE"
    CANCELLED = "CANCELLED"


class VendorInvoiceStatus(str, Enum):
    """Vendor Invoice status."""
    RECEIVED = "RECEIVED"
    UNDER_VERIFICATION = "UNDER_VERIFICATION"
    MATCHED = "MATCHED"  # 3-way matched
    PARTIALLY_MATCHED = "PARTIALLY_MATCHED"
    MISMATCH = "MISMATCH"  # Discrepancy found
    APPROVED = "APPROVED"
    PAYMENT_INITIATED = "PAYMENT_INITIATED"
    PAID = "PAID"
    DISPUTED = "DISPUTED"
    CANCELLED = "CANCELLED"


class QualityCheckResult(str, Enum):
    """Quality inspection result."""
    PASSED = "PASSED"
    FAILED = "FAILED"
    CONDITIONAL = "CONDITIONAL"  # Accepted with deviation
    PENDING = "PENDING"


# ==================== Sales Return Note (SRN) Enums ====================

class SRNStatus(str, Enum):
    """Sales Return Note status - workflow states."""
    DRAFT = "DRAFT"
    PENDING_RECEIPT = "PENDING_RECEIPT"    # Awaiting goods arrival (pickup scheduled)
    RECEIVED = "RECEIVED"                  # Goods physically received at warehouse
    PENDING_QC = "PENDING_QC"              # Quality inspection pending
    QC_PASSED = "QC_PASSED"
    QC_FAILED = "QC_FAILED"
    PARTIALLY_ACCEPTED = "PARTIALLY_ACCEPTED"
    ACCEPTED = "ACCEPTED"
    PUT_AWAY_PENDING = "PUT_AWAY_PENDING"
    PUT_AWAY_COMPLETE = "PUT_AWAY_COMPLETE"
    CREDITED = "CREDITED"                   # Credit note issued
    REPLACED = "REPLACED"                   # Replacement order created
    REFUNDED = "REFUNDED"                   # Refund processed
    CANCELLED = "CANCELLED"


class ReturnReason(str, Enum):
    """Reason for customer return."""
    DEFECTIVE = "DEFECTIVE"
    DAMAGED_IN_TRANSIT = "DAMAGED_IN_TRANSIT"
    WRONG_ITEM = "WRONG_ITEM"
    NOT_AS_DESCRIBED = "NOT_AS_DESCRIBED"
    CHANGE_OF_MIND = "CHANGE_OF_MIND"
    WARRANTY_CLAIM = "WARRANTY_CLAIM"
    SIZE_ISSUE = "SIZE_ISSUE"
    QUALITY_ISSUE = "QUALITY_ISSUE"
    OTHER = "OTHER"


class ItemCondition(str, Enum):
    """Condition of returned item after inspection."""
    LIKE_NEW = "LIKE_NEW"              # Can restock as new
    GOOD = "GOOD"                       # Minor wear, can resell
    DAMAGED = "DAMAGED"                 # Needs repair/refurbish
    DEFECTIVE = "DEFECTIVE"             # Manufacturing defect
    UNSALVAGEABLE = "UNSALVAGEABLE"     # Scrap


class RestockDecision(str, Enum):
    """Decision on how to handle returned item."""
    RESTOCK_AS_NEW = "RESTOCK_AS_NEW"
    RESTOCK_AS_REFURB = "RESTOCK_AS_REFURB"
    SEND_FOR_REPAIR = "SEND_FOR_REPAIR"
    RETURN_TO_VENDOR = "RETURN_TO_VENDOR"
    SCRAP = "SCRAP"


class PickupStatus(str, Enum):
    """Reverse logistics pickup status."""
    NOT_REQUIRED = "NOT_REQUIRED"       # Customer bringing item directly
    SCHEDULED = "SCHEDULED"             # Pickup scheduled with courier
    PICKUP_FAILED = "PICKUP_FAILED"     # Pickup attempt failed
    PICKED_UP = "PICKED_UP"             # Courier has picked up item
    IN_TRANSIT = "IN_TRANSIT"           # In transit to warehouse
    DELIVERED = "DELIVERED"             # Received at warehouse


class ResolutionType(str, Enum):
    """How the return is resolved."""
    CREDIT_NOTE = "CREDIT_NOTE"
    REPLACEMENT = "REPLACEMENT"
    REFUND = "REFUND"
    REPAIR = "REPAIR"
    REJECT = "REJECT"


# ==================== Purchase Requisition ====================

class PurchaseRequisition(Base):
    """
    Internal purchase request model.
    Created by departments to request purchases.
    """
    __tablename__ = "purchase_requisitions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )

    # Identification
    requisition_number: Mapped[str] = mapped_column(
        String(30),
        unique=True,
        nullable=False,
        index=True,
        comment="PR-YYYYMMDD-XXXX"
    )

    # Status
    status: Mapped[str] = mapped_column(
        String(50),
        default="DRAFT",
        nullable=False,
        index=True,
        comment="DRAFT, SUBMITTED, APPROVED, REJECTED, CONVERTED, CANCELLED"
    )

    # Requesting Details
    requesting_department: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        comment="WAREHOUSE, SERVICE, MARKETING etc."
    )
    requested_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False
    )
    request_date: Mapped[date] = mapped_column(
        Date,
        default=date.today,
        nullable=False
    )

    # Delivery Requirements
    required_by_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    delivery_warehouse_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("warehouses.id", ondelete="RESTRICT"),
        nullable=False
    )

    # Priority
    priority: Mapped[int] = mapped_column(
        Integer,
        default=5,
        comment="1=Urgent, 5=Normal, 10=Low"
    )

    # Total (for approval limits)
    estimated_total: Mapped[Decimal] = mapped_column(
        Numeric(14, 2),
        default=Decimal("0")
    )

    # Reason/Justification
    reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Approval
    approved_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )
    approved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    rejection_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Conversion to PO
    converted_to_po_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
        comment="PO ID if converted"
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    # Relationships
    requested_by_user: Mapped["User"] = relationship(
        "User",
        foreign_keys=[requested_by]
    )
    approved_by_user: Mapped[Optional["User"]] = relationship(
        "User",
        foreign_keys=[approved_by]
    )
    delivery_warehouse: Mapped["Warehouse"] = relationship("Warehouse")
    items: Mapped[List["PurchaseRequisitionItem"]] = relationship(
        "PurchaseRequisitionItem",
        back_populates="requisition",
        cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        try:
            if sa_inspect(self).detached:
                return f"<PurchaseRequisition(id={self.id})>"
            return f"<PurchaseRequisition(number='{self.requisition_number}')>"
        except Exception:
            return f"<PurchaseRequisition(id={getattr(self, 'id', 'unknown')})>"


class PurchaseRequisitionItem(Base):
    """Line items in a Purchase Requisition."""
    __tablename__ = "purchase_requisition_items"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )

    requisition_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("purchase_requisitions.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Product
    product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("products.id", ondelete="RESTRICT"),
        nullable=False
    )
    variant_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("product_variants.id", ondelete="SET NULL"),
        nullable=True
    )

    # Snapshot
    product_name: Mapped[str] = mapped_column(String(255), nullable=False)
    sku: Mapped[str] = mapped_column(String(50), nullable=False)

    # Quantity
    quantity_requested: Mapped[int] = mapped_column(Integer, nullable=False)
    uom: Mapped[str] = mapped_column(
        String(20),
        default="PCS",
        comment="Unit of measure"
    )

    # Estimated Price
    estimated_unit_price: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        default=Decimal("0")
    )
    estimated_total: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        default=Decimal("0")
    )

    # Preferred Vendor (optional suggestion)
    preferred_vendor_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("vendors.id", ondelete="SET NULL"),
        nullable=True
    )

    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Monthly Quantities - for multi-month PRs (same pattern as PO)
    # Format: {"2026-01": 1500, "2026-02": 1500, "2026-03": 0}
    monthly_quantities: Mapped[Optional[dict]] = mapped_column(
        JSONB,
        nullable=True,
        comment="Month-wise quantity breakdown for multi-delivery PRs"
    )

    # Relationships
    requisition: Mapped["PurchaseRequisition"] = relationship(
        "PurchaseRequisition",
        back_populates="items"
    )
    product: Mapped["Product"] = relationship("Product")
    variant: Mapped[Optional["ProductVariant"]] = relationship("ProductVariant")
    preferred_vendor: Mapped[Optional["Vendor"]] = relationship("Vendor")


# ==================== Purchase Order ====================

class PurchaseOrder(Base):
    """
    Purchase Order model.
    Official order placed with vendor.
    """
    __tablename__ = "purchase_orders"
    __table_args__ = (
        Index("ix_po_vendor_date", "vendor_id", "po_date"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )

    # Identification
    po_number: Mapped[str] = mapped_column(
        String(30),
        unique=True,
        nullable=False,
        index=True,
        comment="PO-YYYYMMDD-XXXX"
    )
    po_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)

    # Status
    status: Mapped[str] = mapped_column(
        String(50),
        default="DRAFT",
        nullable=False,
        index=True,
        comment="DRAFT, PENDING_APPROVAL, APPROVED, SENT_TO_VENDOR, ACKNOWLEDGED, PARTIALLY_RECEIVED, FULLY_RECEIVED, CLOSED, CANCELLED"
    )

    # Vendor
    vendor_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("vendors.id", ondelete="RESTRICT"),
        nullable=False,
        index=True
    )

    # From Requisition (optional)
    requisition_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("purchase_requisitions.id", ondelete="SET NULL"),
        nullable=True
    )

    # From S&OP Supply Plan (traceability)
    supply_plan_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("supply_plans.id", ondelete="SET NULL"),
        nullable=True,
        comment="S&OP supply plan that triggered this PO"
    )

    # Delivery
    delivery_warehouse_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("warehouses.id", ondelete="RESTRICT"),
        nullable=False
    )
    expected_delivery_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    delivery_address: Mapped[Optional[dict]] = mapped_column(
        JSONB,
        nullable=True,
        comment="Delivery address if different from warehouse"
    )

    # Vendor Details Snapshot
    vendor_name: Mapped[str] = mapped_column(String(200), nullable=False)
    vendor_gstin: Mapped[Optional[str]] = mapped_column(String(15), nullable=True)
    vendor_address: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)

    # Bill To & Ship To (JSONB format)
    # Format: {"name": "", "address_line1": "", "address_line2": "", "city": "", "state": "", "pincode": "", "gstin": "", "state_code": ""}
    bill_to: Mapped[Optional[dict]] = mapped_column(
        JSONB,
        nullable=True,
        comment="Bill To address (buyer details)"
    )
    ship_to: Mapped[Optional[dict]] = mapped_column(
        JSONB,
        nullable=True,
        comment="Ship To address (delivery location, defaults to bill_to if not provided)"
    )

    # Amounts (Taxable)
    subtotal: Mapped[Decimal] = mapped_column(
        Numeric(14, 2),
        nullable=False,
        comment="Sum of line totals before tax"
    )
    discount_amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        default=Decimal("0")
    )
    taxable_amount: Mapped[Decimal] = mapped_column(
        Numeric(14, 2),
        nullable=False,
        comment="Subtotal - Discount"
    )

    # GST Breakup
    cgst_amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        default=Decimal("0")
    )
    sgst_amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        default=Decimal("0")
    )
    igst_amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        default=Decimal("0")
    )
    cess_amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        default=Decimal("0")
    )
    total_tax: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        default=Decimal("0")
    )

    # Other Charges
    freight_charges: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        default=Decimal("0")
    )
    packing_charges: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        default=Decimal("0")
    )
    other_charges: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        default=Decimal("0")
    )

    # Grand Total
    grand_total: Mapped[Decimal] = mapped_column(
        Numeric(14, 2),
        nullable=False
    )

    # Received Tracking
    total_received_value: Mapped[Decimal] = mapped_column(
        Numeric(14, 2),
        default=Decimal("0")
    )

    # Payment Terms
    payment_terms: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    credit_days: Mapped[int] = mapped_column(Integer, default=30)
    advance_required: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        default=Decimal("0"),
        comment="Advance amount if required"
    )
    advance_paid: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        default=Decimal("0")
    )

    # Reference
    quotation_reference: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        comment="Vendor's quotation reference"
    )
    quotation_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)

    # Terms & Conditions
    terms_and_conditions: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    special_instructions: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Communication
    sent_to_vendor_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    vendor_acknowledged_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Documents
    po_pdf_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # Approval Workflow
    created_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False
    )
    approved_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )
    approved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Multi-level Approval
    approval_request_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("approval_requests.id", ondelete="SET NULL"),
        nullable=True,
        comment="Reference to approval request for multi-level approval"
    )
    approval_level: Mapped[Optional[str]] = mapped_column(
        String(20),
        nullable=True,
        comment="LEVEL_1, LEVEL_2, LEVEL_3 based on amount"
    )
    submitted_for_approval_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime,
        nullable=True,
        comment="When PO was submitted for approval"
    )
    rejection_reason: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Reason if PO is rejected"
    )

    # Internal Notes
    internal_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False
    )
    closed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    vendor: Mapped["Vendor"] = relationship("Vendor", back_populates="purchase_orders")
    requisition: Mapped[Optional["PurchaseRequisition"]] = relationship("PurchaseRequisition")
    delivery_warehouse: Mapped["Warehouse"] = relationship("Warehouse")
    created_by_user: Mapped["User"] = relationship("User", foreign_keys=[created_by])
    approved_by_user: Mapped[Optional["User"]] = relationship("User", foreign_keys=[approved_by])
    items: Mapped[List["PurchaseOrderItem"]] = relationship(
        "PurchaseOrderItem",
        back_populates="purchase_order",
        cascade="all, delete-orphan"
    )
    grns: Mapped[List["GoodsReceiptNote"]] = relationship(
        "GoodsReceiptNote",
        back_populates="purchase_order"
    )
    delivery_schedules: Mapped[List["PODeliverySchedule"]] = relationship(
        "PODeliverySchedule",
        back_populates="purchase_order",
        cascade="all, delete-orphan",
        order_by="PODeliverySchedule.lot_number"
    )
    approval_request: Mapped[Optional["ApprovalRequest"]] = relationship(
        "ApprovalRequest",
        foreign_keys=[approval_request_id]
    )

    @property
    def is_fully_received(self) -> bool:
        """Check if PO is fully received."""
        return all(
            item.quantity_received >= item.quantity_ordered
            for item in self.items
        )

    @property
    def receipt_percentage(self) -> Decimal:
        """Calculate receipt completion percentage."""
        if self.grand_total > 0:
            return (self.total_received_value / self.grand_total) * 100
        return Decimal("0")

    def __repr__(self) -> str:
        try:
            # Check if object is detached from session
            if sa_inspect(self).detached:
                return f"<PurchaseOrder(id={self.id})>"
            return f"<PurchaseOrder(number='{self.po_number}', status='{self.status}')>"
        except Exception:
            return f"<PurchaseOrder(id={getattr(self, 'id', 'unknown')})>"


class PurchaseOrderItem(Base):
    """Line items in a Purchase Order."""
    __tablename__ = "purchase_order_items"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )

    purchase_order_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("purchase_orders.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Product (nullable - vendor items may not be in our catalog)
    product_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("products.id", ondelete="RESTRICT"),
        nullable=True
    )
    variant_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("product_variants.id", ondelete="SET NULL"),
        nullable=True
    )

    # Snapshot
    product_name: Mapped[str] = mapped_column(String(255), nullable=False)
    sku: Mapped[str] = mapped_column(String(50), nullable=False)
    part_code: Mapped[Optional[str]] = mapped_column(
        String(20),
        nullable=True,
        comment="Vendor's part code e.g., AFGPSW2001"
    )
    hsn_code: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)

    # Line Number
    line_number: Mapped[int] = mapped_column(Integer, default=1)

    # Quantity
    quantity_ordered: Mapped[int] = mapped_column(Integer, nullable=False)
    quantity_received: Mapped[int] = mapped_column(Integer, default=0)
    quantity_accepted: Mapped[int] = mapped_column(Integer, default=0)
    quantity_rejected: Mapped[int] = mapped_column(Integer, default=0)
    quantity_pending: Mapped[int] = mapped_column(Integer, default=0)
    uom: Mapped[str] = mapped_column(String(20), default="PCS")

    # Pricing
    unit_price: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False
    )
    discount_percentage: Mapped[Decimal] = mapped_column(
        Numeric(5, 2),
        default=Decimal("0")
    )
    discount_amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        default=Decimal("0")
    )
    taxable_amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False
    )

    # GST
    gst_rate: Mapped[Decimal] = mapped_column(
        Numeric(5, 2),
        default=Decimal("18")
    )
    cgst_rate: Mapped[Decimal] = mapped_column(
        Numeric(5, 2),
        default=Decimal("0")
    )
    sgst_rate: Mapped[Decimal] = mapped_column(
        Numeric(5, 2),
        default=Decimal("0")
    )
    igst_rate: Mapped[Decimal] = mapped_column(
        Numeric(5, 2),
        default=Decimal("0")
    )
    cgst_amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        default=Decimal("0")
    )
    sgst_amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        default=Decimal("0")
    )
    igst_amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        default=Decimal("0")
    )
    cess_amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        default=Decimal("0")
    )

    # Line Total
    total_amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False
    )

    # Delivery
    expected_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)

    # Monthly Quantities - for multi-month POs
    # Format: {"2026-01": 1500, "2026-02": 1500, "2026-03": 0}
    monthly_quantities: Mapped[Optional[dict]] = mapped_column(
        JSONB,
        nullable=True,
        comment="Month-wise quantity breakdown for multi-delivery POs"
    )

    # Status
    is_closed: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        comment="Manually closed (no more receipts expected)"
    )

    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    purchase_order: Mapped["PurchaseOrder"] = relationship(
        "PurchaseOrder",
        back_populates="items"
    )
    product: Mapped["Product"] = relationship("Product")
    variant: Mapped[Optional["ProductVariant"]] = relationship("ProductVariant")

    def __repr__(self) -> str:
        try:
            if sa_inspect(self).detached:
                return f"<PurchaseOrderItem(id={self.id})>"
            return f"<PurchaseOrderItem(sku='{self.sku}', qty={self.quantity_ordered})>"
        except Exception:
            return f"<PurchaseOrderItem(id={getattr(self, 'id', 'unknown')})>"


# ==================== PO Delivery Schedule (Lot-wise) ====================

class DeliveryLotStatus(str, Enum):
    """Status of a delivery lot."""
    PENDING = "PENDING"                 # Not yet due
    ADVANCE_PENDING = "ADVANCE_PENDING" # Advance payment pending
    ADVANCE_PAID = "ADVANCE_PAID"       # Advance paid, awaiting delivery
    DELIVERED = "DELIVERED"             # Goods delivered
    PAYMENT_PENDING = "PAYMENT_PENDING" # Balance payment pending
    COMPLETED = "COMPLETED"             # Fully paid and delivered
    CANCELLED = "CANCELLED"


class PODeliverySchedule(Base):
    """
    Delivery Schedule / Lot for a Purchase Order.

    Each lot represents a scheduled delivery with its own:
    - Expected delivery date
    - Quantity allocation
    - Advance payment
    - Balance payment

    Payment Flow per Lot:
    1. PENDING -> ADVANCE_PENDING (when lot comes due)
    2. ADVANCE_PENDING -> ADVANCE_PAID (after advance payment)
    3. ADVANCE_PAID -> DELIVERED (after GRN)
    4. DELIVERED -> PAYMENT_PENDING (balance due)
    5. PAYMENT_PENDING -> COMPLETED (after full payment)
    """
    __tablename__ = "po_delivery_schedules"
    __table_args__ = (
        Index("ix_po_delivery_po", "purchase_order_id"),
        Index("ix_po_delivery_date", "expected_delivery_date"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )

    # Parent PO
    purchase_order_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("purchase_orders.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Lot Identification
    lot_number: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Lot sequence: 1, 2, 3..."
    )
    lot_name: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="e.g., 'JAN 2026', 'Batch 1', 'Lot A'"
    )
    month_code: Mapped[Optional[str]] = mapped_column(
        String(7),
        nullable=True,
        comment="YYYY-MM format for monthly POs"
    )

    # Schedule
    expected_delivery_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
        comment="Expected delivery date for this lot"
    )
    delivery_window_start: Mapped[Optional[date]] = mapped_column(
        Date,
        nullable=True,
        comment="Start of delivery window (e.g., 15th Jan)"
    )
    delivery_window_end: Mapped[Optional[date]] = mapped_column(
        Date,
        nullable=True,
        comment="End of delivery window (e.g., 25th Jan)"
    )
    actual_delivery_date: Mapped[Optional[date]] = mapped_column(
        Date,
        nullable=True
    )

    # Quantity for this Lot
    total_quantity: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Total pieces in this lot"
    )
    quantity_received: Mapped[int] = mapped_column(
        Integer,
        default=0
    )

    # Value for this Lot (calculated from items)
    lot_value: Mapped[Decimal] = mapped_column(
        Numeric(14, 2),
        nullable=False,
        comment="Taxable value for this lot"
    )
    lot_tax: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
        comment="Tax amount for this lot"
    )
    lot_total: Mapped[Decimal] = mapped_column(
        Numeric(14, 2),
        nullable=False,
        comment="Total including tax for this lot"
    )

    # Payment Terms for this Lot
    advance_percentage: Mapped[Decimal] = mapped_column(
        Numeric(5, 2),
        default=Decimal("25"),
        comment="Advance payment percentage"
    )
    advance_amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
        comment="Advance payment amount for this lot"
    )
    balance_amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
        comment="Balance payment amount for this lot"
    )
    balance_due_days: Mapped[int] = mapped_column(
        Integer,
        default=45,
        comment="Days after delivery for balance payment"
    )

    # Payment Status
    advance_paid: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        default=Decimal("0")
    )
    advance_paid_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    advance_payment_ref: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    balance_paid: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        default=Decimal("0")
    )
    balance_paid_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    balance_payment_ref: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    balance_due_date: Mapped[Optional[date]] = mapped_column(
        Date,
        nullable=True,
        comment="Calculated: delivery_date + balance_due_days"
    )

    # Status
    status: Mapped[str] = mapped_column(
        String(50),
        default="PENDING",
        nullable=False,
        index=True,
        comment="PENDING, ADVANCE_PENDING, ADVANCE_PAID, DELIVERED, PAYMENT_PENDING, COMPLETED, CANCELLED"
    )

    # GRN Reference
    grn_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("goods_receipt_notes.id", ondelete="SET NULL"),
        nullable=True
    )

    # Serial Number Range for this Lot
    # These represent the range of product serial numbers to be supplied
    # Serial numbers are auto-incremented based on last PO's ending serial
    serial_number_start: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        comment="Starting serial number for this lot (e.g., 101)"
    )
    serial_number_end: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        comment="Ending serial number for this lot (e.g., 200)"
    )

    # Notes
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    # Relationships
    purchase_order: Mapped["PurchaseOrder"] = relationship(
        "PurchaseOrder",
        back_populates="delivery_schedules"
    )
    grn: Mapped[Optional["GoodsReceiptNote"]] = relationship("GoodsReceiptNote")

    @property
    def is_advance_paid(self) -> bool:
        """Check if advance is fully paid."""
        return self.advance_paid >= self.advance_amount

    @property
    def is_balance_paid(self) -> bool:
        """Check if balance is fully paid."""
        return self.balance_paid >= self.balance_amount

    @property
    def is_fully_paid(self) -> bool:
        """Check if lot is fully paid."""
        return self.is_advance_paid and self.is_balance_paid

    @property
    def pending_advance(self) -> Decimal:
        """Pending advance amount."""
        return max(Decimal("0"), self.advance_amount - self.advance_paid)

    @property
    def pending_balance(self) -> Decimal:
        """Pending balance amount."""
        return max(Decimal("0"), self.balance_amount - self.balance_paid)

    @property
    def serial_number_range(self) -> Optional[str]:
        """Get formatted serial number range string."""
        if self.serial_number_start is not None and self.serial_number_end is not None:
            return f"{self.serial_number_start} - {self.serial_number_end}"
        return None

    def __repr__(self) -> str:
        try:
            if sa_inspect(self).detached:
                return f"<PODeliverySchedule(id={self.id})>"
            return f"<PODeliverySchedule(lot={self.lot_name}, status={self.status})>"
        except Exception:
            return f"<PODeliverySchedule(id={getattr(self, 'id', 'unknown')})>"


# ==================== Goods Receipt Note (GRN) ====================

class GoodsReceiptNote(Base):
    """
    Goods Receipt Note model.
    Records material received against PO.
    """
    __tablename__ = "goods_receipt_notes"
    __table_args__ = (
        Index("ix_grn_po", "purchase_order_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )

    # Identification
    grn_number: Mapped[str] = mapped_column(
        String(30),
        unique=True,
        nullable=False,
        index=True,
        comment="GRN-YYYYMMDD-XXXX"
    )
    grn_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)

    # Status
    status: Mapped[str] = mapped_column(
        String(50),
        default="DRAFT",
        nullable=False,
        index=True,
        comment="DRAFT, PENDING_QC, QC_PASSED, QC_FAILED, PARTIALLY_ACCEPTED, ACCEPTED, REJECTED, PUT_AWAY_PENDING, PUT_AWAY_COMPLETE, CANCELLED"
    )

    # Against PO
    purchase_order_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("purchase_orders.id", ondelete="RESTRICT"),
        nullable=False,
        index=True
    )

    # Vendor
    vendor_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("vendors.id", ondelete="RESTRICT"),
        nullable=False
    )

    # Receiving Warehouse
    warehouse_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("warehouses.id", ondelete="RESTRICT"),
        nullable=False
    )

    # Vendor's Delivery Reference
    vendor_challan_number: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        comment="Vendor's delivery challan/DC number"
    )
    vendor_challan_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)

    # Transport Details
    transporter_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    vehicle_number: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    lr_number: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        comment="Lorry Receipt number"
    )
    e_way_bill_number: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)

    # Quantities Summary
    total_items: Mapped[int] = mapped_column(Integer, default=0)
    total_quantity_received: Mapped[int] = mapped_column(Integer, default=0)
    total_quantity_accepted: Mapped[int] = mapped_column(Integer, default=0)
    total_quantity_rejected: Mapped[int] = mapped_column(Integer, default=0)

    # Value
    total_value: Mapped[Decimal] = mapped_column(
        Numeric(14, 2),
        default=Decimal("0"),
        comment="Value of accepted goods"
    )

    # Quality Check
    qc_required: Mapped[bool] = mapped_column(Boolean, default=True)
    qc_status: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        comment="PASSED, FAILED, CONDITIONAL, PENDING"
    )
    qc_done_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )
    qc_done_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    qc_remarks: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Receiving
    received_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False
    )
    receiving_remarks: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Put Away Status
    put_away_complete: Mapped[bool] = mapped_column(Boolean, default=False)
    put_away_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Forced GRN (when serials don't match PO serials)
    is_forced: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        comment="True if GRN was forced without serial validation"
    )
    force_reason: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Reason for forcing GRN (required if is_forced=True)"
    )
    forced_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        comment="Supply Chain Head who forced the GRN"
    )

    # Serial Validation Status
    serial_validation_status: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        comment="VALIDATED, PARTIAL_MATCH, NO_MATCH, SKIPPED"
    )
    serial_mismatch_details: Mapped[Optional[dict]] = mapped_column(
        JSONB,
        nullable=True,
        comment="Details of serial mismatches if any"
    )

    # Stock Items Created flag
    stock_items_created: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        comment="True after stock_items have been created from this GRN"
    )

    # Documents
    grn_pdf_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    photos_urls: Mapped[Optional[List[str]]] = mapped_column(
        JSONB,
        nullable=True,
        comment="Photos of received goods"
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    # Relationships
    purchase_order: Mapped["PurchaseOrder"] = relationship(
        "PurchaseOrder",
        back_populates="grns"
    )
    vendor: Mapped["Vendor"] = relationship("Vendor")
    warehouse: Mapped["Warehouse"] = relationship("Warehouse")
    received_by_user: Mapped["User"] = relationship(
        "User",
        foreign_keys=[received_by]
    )
    qc_done_by_user: Mapped[Optional["User"]] = relationship(
        "User",
        foreign_keys=[qc_done_by]
    )
    items: Mapped[List["GRNItem"]] = relationship(
        "GRNItem",
        back_populates="grn",
        cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        try:
            if sa_inspect(self).detached:
                return f"<GoodsReceiptNote(id={self.id})>"
            return f"<GoodsReceiptNote(number='{self.grn_number}', status='{self.status}')>"
        except Exception:
            return f"<GoodsReceiptNote(id={getattr(self, 'id', 'unknown')})>"


class GRNItem(Base):
    """Line items in a GRN."""
    __tablename__ = "grn_items"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )

    grn_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("goods_receipt_notes.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Link to PO Item
    po_item_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("purchase_order_items.id", ondelete="RESTRICT"),
        nullable=False
    )

    # Product
    product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("products.id", ondelete="RESTRICT"),
        nullable=False
    )
    variant_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("product_variants.id", ondelete="SET NULL"),
        nullable=True
    )

    # Snapshot
    product_name: Mapped[str] = mapped_column(String(255), nullable=False)
    sku: Mapped[str] = mapped_column(String(50), nullable=False)
    part_code: Mapped[Optional[str]] = mapped_column(
        String(20),
        nullable=True,
        comment="Vendor's part code e.g., AFGPSW2001"
    )
    hsn_code: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)

    # Quantities
    quantity_expected: Mapped[int] = mapped_column(
        Integer,
        comment="Qty expected from PO"
    )
    quantity_received: Mapped[int] = mapped_column(Integer, nullable=False)
    quantity_accepted: Mapped[int] = mapped_column(Integer, default=0)
    quantity_rejected: Mapped[int] = mapped_column(Integer, default=0)
    uom: Mapped[str] = mapped_column(String(20), default="PCS")

    # Unit Price (from PO)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    accepted_value: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        default=Decimal("0")
    )

    # Batch/Serial
    batch_number: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    manufacturing_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    expiry_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    serial_numbers: Mapped[Optional[List[str]]] = mapped_column(
        JSONB,
        nullable=True,
        comment="List of serial numbers received"
    )

    # Put Away Location
    bin_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("warehouse_bins.id", ondelete="SET NULL"),
        nullable=True
    )
    bin_location: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    # Quality Check
    qc_result: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        comment="PASSED, FAILED, CONDITIONAL, PENDING"
    )
    rejection_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    remarks: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    grn: Mapped["GoodsReceiptNote"] = relationship("GoodsReceiptNote", back_populates="items")
    po_item: Mapped["PurchaseOrderItem"] = relationship("PurchaseOrderItem")
    product: Mapped["Product"] = relationship("Product")
    variant: Mapped[Optional["ProductVariant"]] = relationship("ProductVariant")
    bin: Mapped[Optional["WarehouseBin"]] = relationship("WarehouseBin")

    def __repr__(self) -> str:
        try:
            if sa_inspect(self).detached:
                return f"<GRNItem(id={self.id})>"
            return f"<GRNItem(sku='{self.sku}', received={self.quantity_received})>"
        except Exception:
            return f"<GRNItem(id={getattr(self, 'id', 'unknown')})>"


# ==================== Vendor Invoice ====================

class VendorInvoice(Base):
    """
    Vendor Invoice model for 3-way matching.
    Records invoices received from vendors.
    """
    __tablename__ = "vendor_invoices"
    __table_args__ = (
        UniqueConstraint("vendor_id", "invoice_number", name="uq_vendor_invoice"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )

    # Vendor's Invoice Details
    invoice_number: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
        comment="Vendor's invoice number"
    )
    invoice_date: Mapped[date] = mapped_column(Date, nullable=False)

    # Our Reference
    our_reference: Mapped[str] = mapped_column(
        String(30),
        unique=True,
        nullable=False,
        index=True,
        comment="Our internal reference VI-YYYYMMDD-XXXX"
    )

    # Status
    status: Mapped[str] = mapped_column(
        String(50),
        default="RECEIVED",
        nullable=False,
        index=True,
        comment="RECEIVED, UNDER_VERIFICATION, MATCHED, PARTIALLY_MATCHED, MISMATCH, APPROVED, PAYMENT_INITIATED, PAID, DISPUTED, CANCELLED"
    )

    # Vendor
    vendor_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("vendors.id", ondelete="RESTRICT"),
        nullable=False,
        index=True
    )

    # Linked Documents
    purchase_order_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("purchase_orders.id", ondelete="SET NULL"),
        nullable=True
    )
    grn_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("goods_receipt_notes.id", ondelete="SET NULL"),
        nullable=True
    )

    # Invoice Amounts
    subtotal: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    discount_amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        default=Decimal("0")
    )
    taxable_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)

    # GST
    cgst_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0"))
    sgst_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0"))
    igst_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0"))
    cess_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0"))
    total_tax: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0"))

    # Other Charges
    freight_charges: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0"))
    other_charges: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0"))

    # Round Off
    round_off: Mapped[Decimal] = mapped_column(
        Numeric(8, 2),
        default=Decimal("0")
    )

    # Grand Total
    grand_total: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)

    # Payment
    due_date: Mapped[date] = mapped_column(Date, nullable=False)
    amount_paid: Mapped[Decimal] = mapped_column(
        Numeric(14, 2),
        default=Decimal("0")
    )
    balance_due: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)

    # TDS
    tds_applicable: Mapped[bool] = mapped_column(Boolean, default=True)
    tds_section: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    tds_rate: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=Decimal("0"))
    tds_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0"))
    net_payable: Mapped[Decimal] = mapped_column(
        Numeric(14, 2),
        comment="Grand Total - TDS"
    )

    # 3-Way Matching
    po_matched: Mapped[bool] = mapped_column(Boolean, default=False)
    grn_matched: Mapped[bool] = mapped_column(Boolean, default=False)
    is_fully_matched: Mapped[bool] = mapped_column(Boolean, default=False)
    matching_variance: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        default=Decimal("0"),
        comment="Difference if any"
    )
    variance_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # E-Invoice Details (if received from vendor)
    vendor_irn: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    vendor_ack_number: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)

    # Documents
    invoice_pdf_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # Workflow
    received_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False
    )
    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )
    verified_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )
    verified_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    approved_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )
    approved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Internal
    internal_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    # Relationships
    vendor: Mapped["Vendor"] = relationship("Vendor")
    purchase_order: Mapped[Optional["PurchaseOrder"]] = relationship("PurchaseOrder")
    grn: Mapped[Optional["GoodsReceiptNote"]] = relationship("GoodsReceiptNote")
    received_by_user: Mapped["User"] = relationship("User", foreign_keys=[received_by])
    verified_by_user: Mapped[Optional["User"]] = relationship("User", foreign_keys=[verified_by])
    approved_by_user: Mapped[Optional["User"]] = relationship("User", foreign_keys=[approved_by])

    @property
    def is_overdue(self) -> bool:
        """Check if invoice is overdue."""
        return date.today() > self.due_date and self.balance_due > 0

    @property
    def days_overdue(self) -> int:
        """Calculate days overdue."""
        if self.is_overdue:
            return (date.today() - self.due_date).days
        return 0

    def __repr__(self) -> str:
        try:
            if sa_inspect(self).detached:
                return f"<VendorInvoice(id={self.id})>"
            return f"<VendorInvoice(ref='{self.our_reference}', vendor_inv='{self.invoice_number}')>"
        except Exception:
            return f"<VendorInvoice(id={getattr(self, 'id', 'unknown')})>"


# ==================== Vendor Proforma Invoice ====================

class ProformaStatus(str, Enum):
    """Vendor Proforma Invoice status."""
    RECEIVED = "RECEIVED"
    UNDER_REVIEW = "UNDER_REVIEW"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    CONVERTED_TO_PO = "CONVERTED_TO_PO"
    EXPIRED = "EXPIRED"
    CANCELLED = "CANCELLED"


class VendorProformaInvoice(Base):
    """
    Vendor Proforma Invoice model.
    Quotations/Proforma invoices received from vendors before placing PO.
    """
    __tablename__ = "vendor_proforma_invoices"
    __table_args__ = (
        UniqueConstraint("vendor_id", "proforma_number", name="uq_vendor_proforma"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )

    # Proforma Identification
    proforma_number: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
        comment="Vendor's proforma/quotation number"
    )
    our_reference: Mapped[str] = mapped_column(
        String(30),
        unique=True,
        nullable=False,
        index=True,
        comment="Our internal reference VPI-YYYYMMDD-XXXX"
    )

    # Status
    status: Mapped[str] = mapped_column(
        String(50),
        default="RECEIVED",
        nullable=False,
        index=True,
        comment="RECEIVED, UNDER_REVIEW, APPROVED, REJECTED, CONVERTED_TO_PO, EXPIRED, CANCELLED"
    )

    # Vendor
    vendor_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("vendors.id", ondelete="RESTRICT"),
        nullable=False,
        index=True
    )

    # Dates
    proforma_date: Mapped[date] = mapped_column(Date, nullable=False)
    validity_date: Mapped[Optional[date]] = mapped_column(
        Date,
        nullable=True,
        comment="Quote valid until date"
    )

    # Purchase Requisition Reference (if from PR)
    requisition_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("purchase_requisitions.id", ondelete="SET NULL"),
        nullable=True
    )

    # Converted PO (if converted)
    purchase_order_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("purchase_orders.id", ondelete="SET NULL"),
        nullable=True
    )

    # Delivery Terms
    delivery_warehouse_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("warehouses.id", ondelete="SET NULL"),
        nullable=True
    )
    delivery_days: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    delivery_terms: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)

    # Bill To & Ship To (JSONB format)
    # Format: {"name": "", "address_line1": "", "address_line2": "", "city": "", "state": "", "pincode": "", "gstin": "", "state_code": ""}
    bill_to: Mapped[Optional[dict]] = mapped_column(
        JSONB,
        nullable=True,
        comment="Bill To address (buyer details)"
    )
    ship_to: Mapped[Optional[dict]] = mapped_column(
        JSONB,
        nullable=True,
        comment="Ship To address (delivery location, defaults to bill_to if not provided)"
    )

    # Payment Terms
    payment_terms: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    credit_days: Mapped[int] = mapped_column(Integer, default=30)

    # Amounts
    subtotal: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    discount_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0"))
    discount_percent: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=Decimal("0"))
    taxable_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)

    # GST
    cgst_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0"))
    sgst_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0"))
    igst_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0"))
    total_tax: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0"))

    # Other Charges
    freight_charges: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0"))
    packing_charges: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0"))
    other_charges: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0"))

    # Round Off & Total
    round_off: Mapped[Decimal] = mapped_column(Numeric(8, 2), default=Decimal("0"))
    grand_total: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)

    # Documents
    proforma_pdf_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # Notes
    vendor_remarks: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    internal_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Workflow
    received_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False
    )
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    approved_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )
    approved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    rejection_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    vendor: Mapped["Vendor"] = relationship("Vendor")
    requisition: Mapped[Optional["PurchaseRequisition"]] = relationship("PurchaseRequisition")
    purchase_order: Mapped[Optional["PurchaseOrder"]] = relationship("PurchaseOrder")
    warehouse: Mapped[Optional["Warehouse"]] = relationship("Warehouse")
    received_by_user: Mapped["User"] = relationship("User", foreign_keys=[received_by])
    approved_by_user: Mapped[Optional["User"]] = relationship("User", foreign_keys=[approved_by])
    items: Mapped[List["VendorProformaItem"]] = relationship(
        "VendorProformaItem",
        back_populates="proforma",
        cascade="all, delete-orphan"
    )

    @property
    def is_expired(self) -> bool:
        """Check if proforma is expired."""
        if self.validity_date:
            return date.today() > self.validity_date
        return False

    @property
    def days_to_expiry(self) -> int:
        """Calculate days until expiry."""
        if self.validity_date:
            return max(0, (self.validity_date - date.today()).days)
        return -1  # No expiry set

    def __repr__(self) -> str:
        try:
            if sa_inspect(self).detached:
                return f"<VendorProformaInvoice(id={self.id})>"
            return f"<VendorProformaInvoice(ref='{self.our_reference}', vendor_pi='{self.proforma_number}')>"
        except Exception:
            return f"<VendorProformaInvoice(id={getattr(self, 'id', 'unknown')})>"


class VendorProformaItem(Base):
    """Line items in vendor proforma invoice."""
    __tablename__ = "vendor_proforma_items"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )

    proforma_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("vendor_proforma_invoices.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Product (optional - might be new product from vendor)
    product_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("products.id", ondelete="SET NULL"),
        nullable=True
    )

    # Item Details
    part_code: Mapped[Optional[str]] = mapped_column(
        String(20),
        nullable=True,
        comment="Vendor's part code e.g., AFGPSW2001"
    )
    description: Mapped[str] = mapped_column(String(500), nullable=False)
    hsn_code: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    uom: Mapped[str] = mapped_column(String(20), default="NOS")

    # Quantity & Price
    quantity: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    discount_percent: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=Decimal("0"))
    discount_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0"))
    taxable_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)

    # GST
    gst_rate: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=Decimal("18"))
    cgst_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0"))
    sgst_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0"))
    igst_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0"))

    # Total
    total_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)

    # Delivery
    lead_time_days: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Relationships
    proforma: Mapped["VendorProformaInvoice"] = relationship(
        "VendorProformaInvoice",
        back_populates="items"
    )
    product: Mapped[Optional["Product"]] = relationship("Product")

    def __repr__(self) -> str:
        try:
            if sa_inspect(self).detached:
                return f"<VendorProformaItem(id={self.id})>"
            desc = self.description[:30] if self.description else ''
            return f"<VendorProformaItem(desc='{desc}...', qty={self.quantity})>"
        except Exception:
            return f"<VendorProformaItem(id={getattr(self, 'id', 'unknown')})>"


# ==================== Sales Return Note (SRN) ====================

class SalesReturnNote(Base):
    """
    Sales Return Note - tracks goods returned from customers.
    Can be created against a Sales Order or Tax Invoice.
    Supports full reverse logistics with pickup tracking.
    """
    __tablename__ = "sales_return_notes"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )

    # Identification
    srn_number: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        nullable=False,
        index=True,
        comment="SRN-YYYYMMDD-XXXX"
    )
    srn_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)

    # Source References (either order or invoice - at least one required)
    order_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("orders.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    invoice_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tax_invoices.id", ondelete="SET NULL"),
        nullable=True
    )

    # Customer
    customer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("customers.id", ondelete="RESTRICT"),
        nullable=False,
        index=True
    )

    # Warehouse (Returns area)
    warehouse_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("warehouses.id", ondelete="RESTRICT"),
        nullable=False
    )

    # Status & Workflow
    status: Mapped[str] = mapped_column(
        String(50),
        default="DRAFT",
        nullable=False,
        index=True,
        comment="DRAFT, PENDING_RECEIPT, RECEIVED, PENDING_QC, QC_PASSED, QC_FAILED, PARTIALLY_ACCEPTED, ACCEPTED, PUT_AWAY_PENDING, PUT_AWAY_COMPLETE, CREDITED, REPLACED, REFUNDED, CANCELLED"
    )

    # Return Details
    return_reason: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="DEFECTIVE, DAMAGED_IN_TRANSIT, WRONG_ITEM, NOT_AS_DESCRIBED, CHANGE_OF_MIND, WARRANTY_CLAIM, SIZE_ISSUE, QUALITY_ISSUE, OTHER"
    )
    return_reason_detail: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Resolution (manual choice per SRN)
    resolution_type: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        comment="CREDIT_NOTE, REPLACEMENT, REFUND, REPAIR, REJECT"
    )
    credit_note_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("credit_debit_notes.id", ondelete="SET NULL"),
        nullable=True
    )
    replacement_order_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("orders.id", ondelete="SET NULL"),
        nullable=True
    )

    # Pickup/Reverse Logistics (Full Tracking)
    pickup_required: Mapped[bool] = mapped_column(Boolean, default=False)
    pickup_status: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        comment="NOT_REQUIRED, SCHEDULED, PICKUP_FAILED, PICKED_UP, IN_TRANSIT, DELIVERED"
    )
    pickup_scheduled_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    pickup_scheduled_slot: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        comment="Time slot e.g., 10AM-12PM"
    )
    pickup_address: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    pickup_contact_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    pickup_contact_phone: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    courier_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("transporters.id", ondelete="SET NULL"),
        nullable=True
    )
    courier_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    courier_tracking_number: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        comment="AWB Number"
    )
    pickup_requested_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    pickup_completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Quality Control
    qc_required: Mapped[bool] = mapped_column(Boolean, default=True)
    qc_status: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        comment="PASSED, FAILED, CONDITIONAL, PENDING"
    )
    qc_done_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )
    qc_done_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    qc_remarks: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Quantities Summary
    total_items: Mapped[int] = mapped_column(Integer, default=0)
    total_quantity_returned: Mapped[int] = mapped_column(Integer, default=0)
    total_quantity_accepted: Mapped[int] = mapped_column(Integer, default=0)
    total_quantity_rejected: Mapped[int] = mapped_column(Integer, default=0)

    # Value
    total_value: Mapped[Decimal] = mapped_column(
        Numeric(14, 2),
        default=Decimal("0"),
        comment="Value of accepted returns"
    )

    # Put-away
    put_away_complete: Mapped[bool] = mapped_column(Boolean, default=False)
    put_away_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Receiving
    received_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )
    received_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    receiving_remarks: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Documents
    srn_pdf_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    photos_urls: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True)

    # Audit
    created_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    # Relationships
    order: Mapped[Optional["Order"]] = relationship(
        "Order",
        foreign_keys=[order_id],
        backref="sales_returns"
    )
    invoice: Mapped[Optional["TaxInvoice"]] = relationship("TaxInvoice")
    customer: Mapped["Customer"] = relationship("Customer")
    warehouse: Mapped["Warehouse"] = relationship("Warehouse")
    courier: Mapped[Optional["Transporter"]] = relationship("Transporter")
    credit_note: Mapped[Optional["CreditDebitNote"]] = relationship("CreditDebitNote")
    replacement_order: Mapped[Optional["Order"]] = relationship(
        "Order",
        foreign_keys=[replacement_order_id]
    )
    qc_inspector: Mapped[Optional["User"]] = relationship(
        "User",
        foreign_keys=[qc_done_by]
    )
    receiver: Mapped[Optional["User"]] = relationship(
        "User",
        foreign_keys=[received_by]
    )
    creator: Mapped["User"] = relationship(
        "User",
        foreign_keys=[created_by]
    )
    items: Mapped[List["SRNItem"]] = relationship(
        "SRNItem",
        back_populates="srn",
        cascade="all, delete-orphan"
    )

    # Indexes
    __table_args__ = (
        Index("idx_srn_customer_date", "customer_id", "srn_date"),
        Index("idx_srn_pickup_status", "pickup_required", "pickup_status"),
    )

    def __repr__(self) -> str:
        try:
            if sa_inspect(self).detached:
                return f"<SalesReturnNote(id={self.id})>"
            return f"<SalesReturnNote(srn='{self.srn_number}', status='{self.status}')>"
        except Exception:
            return f"<SalesReturnNote(id={getattr(self, 'id', 'unknown')})>"


class SRNItem(Base):
    """Line item for Sales Return Note."""
    __tablename__ = "srn_items"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )

    srn_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sales_return_notes.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Original Order/Invoice Reference
    order_item_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("order_items.id", ondelete="SET NULL"),
        nullable=True
    )
    invoice_item_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("invoice_items.id", ondelete="SET NULL"),
        nullable=True
    )

    # Product
    product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("products.id", ondelete="RESTRICT"),
        nullable=False
    )
    variant_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("product_variants.id", ondelete="SET NULL"),
        nullable=True
    )

    # Product Snapshot (for historical record)
    product_name: Mapped[str] = mapped_column(String(255), nullable=False)
    sku: Mapped[str] = mapped_column(String(50), nullable=False)
    hsn_code: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)

    # Serial Numbers Being Returned
    serial_numbers: Mapped[Optional[list]] = mapped_column(
        JSONB,
        nullable=True,
        comment="List of serial numbers being returned"
    )

    # Quantities
    quantity_sold: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Original sale quantity"
    )
    quantity_returned: Mapped[int] = mapped_column(Integer, nullable=False)
    quantity_accepted: Mapped[int] = mapped_column(Integer, default=0)
    quantity_rejected: Mapped[int] = mapped_column(Integer, default=0)
    uom: Mapped[str] = mapped_column(String(20), default="PCS")

    # Pricing (from original sale)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    return_value: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        default=Decimal("0"),
        comment="qty_accepted * unit_price"
    )

    # Condition Assessment (set during QC)
    item_condition: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        comment="LIKE_NEW, GOOD, DAMAGED, DEFECTIVE, UNSALVAGEABLE"
    )
    restock_decision: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        comment="RESTOCK_AS_NEW, RESTOCK_AS_REFURB, SEND_FOR_REPAIR, RETURN_TO_VENDOR, SCRAP"
    )

    # QC Result
    qc_result: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        comment="PASSED, FAILED, CONDITIONAL, PENDING"
    )
    rejection_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Put-away Location
    bin_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("warehouse_bins.id", ondelete="SET NULL"),
        nullable=True
    )
    bin_location: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        comment="Human-readable bin location"
    )

    # Notes
    remarks: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    srn: Mapped["SalesReturnNote"] = relationship(
        "SalesReturnNote",
        back_populates="items"
    )
    product: Mapped["Product"] = relationship("Product")
    variant: Mapped[Optional["ProductVariant"]] = relationship("ProductVariant")
    order_item: Mapped[Optional["OrderItem"]] = relationship("OrderItem")
    invoice_item: Mapped[Optional["InvoiceItem"]] = relationship("InvoiceItem")
    bin: Mapped[Optional["WarehouseBin"]] = relationship("WarehouseBin")

    def __repr__(self) -> str:
        try:
            if sa_inspect(self).detached:
                return f"<SRNItem(id={self.id})>"
            return f"<SRNItem(sku='{self.sku}', qty_returned={self.quantity_returned})>"
        except Exception:
            return f"<SRNItem(id={getattr(self, 'id', 'unknown')})>"
