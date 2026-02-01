"""Vendor/Supplier management models for Procure-to-Pay cycle.

Supports:
- Vendor master with GST compliance
- Vendor categorization and grading
- Payment terms and credit management
- TDS compliance tracking
- Vendor ledger for Accounts Payable
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

from app.database import Base

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.warehouse import Warehouse
    from app.models.product import Product, Category
    from app.models.accounting import ChartOfAccount


class VendorType(str, Enum):
    """Vendor type enumeration."""
    MANUFACTURER = "MANUFACTURER"           # OEM/Brand manufacturer
    IMPORTER = "IMPORTER"                  # Goods importer
    DISTRIBUTOR = "DISTRIBUTOR"            # Wholesale distributor
    TRADER = "TRADER"                      # Trading company
    SERVICE_PROVIDER = "SERVICE_PROVIDER"  # Service vendor (logistics, etc.)
    RAW_MATERIAL = "RAW_MATERIAL"          # Raw material supplier
    SPARE_PARTS = "SPARE_PARTS"            # Spare parts vendor
    CONSUMABLES = "CONSUMABLES"            # Office/packing consumables
    TRANSPORTER = "TRANSPORTER"            # Logistics partner
    CONTRACTOR = "CONTRACTOR"              # Contract workers


class VendorStatus(str, Enum):
    """Vendor status enumeration."""
    PENDING_APPROVAL = "PENDING_APPROVAL"
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    SUSPENDED = "SUSPENDED"
    BLACKLISTED = "BLACKLISTED"


class VendorGrade(str, Enum):
    """Vendor performance grade."""
    A_PLUS = "A+"    # Excellent - priority vendor
    A = "A"          # Very Good
    B = "B"          # Good
    C = "C"          # Average
    D = "D"          # Poor - under observation


class PaymentTerms(str, Enum):
    """Standard payment terms."""
    ADVANCE = "ADVANCE"                    # 100% advance
    PARTIAL_ADVANCE = "PARTIAL_ADVANCE"    # X% advance, balance on delivery
    ON_DELIVERY = "ON_DELIVERY"            # Payment on delivery
    NET_7 = "NET_7"                         # Net 7 days
    NET_15 = "NET_15"
    NET_30 = "NET_30"
    NET_45 = "NET_45"
    NET_60 = "NET_60"
    NET_90 = "NET_90"
    CUSTOM = "CUSTOM"


class VendorTransactionType(str, Enum):
    """Vendor ledger transaction types."""
    OPENING_BALANCE = "OPENING_BALANCE"
    PURCHASE_INVOICE = "PURCHASE_INVOICE"     # Bill received (credit to vendor)
    PAYMENT = "PAYMENT"                        # Payment made (debit to vendor)
    ADVANCE = "ADVANCE"                        # Advance payment
    DEBIT_NOTE = "DEBIT_NOTE"                 # Return/rejection
    CREDIT_NOTE = "CREDIT_NOTE"               # Additional charges
    TDS_DEDUCTED = "TDS_DEDUCTED"             # TDS deduction
    ADJUSTMENT = "ADJUSTMENT"


class Vendor(Base):
    """
    Vendor/Supplier master model.
    Central repository for all supplier information.
    """
    __tablename__ = "vendors"
    # Note: gstin and state columns already have index=True on them

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )

    # Identification
    vendor_code: Mapped[str] = mapped_column(
        String(30),
        unique=True,
        nullable=False,
        index=True,
        comment="Unique vendor code e.g., VND-00001"
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    legal_name: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
        comment="Registered business name as per GST"
    )
    trade_name: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)

    # Type & Status
    vendor_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
        comment="MANUFACTURER, IMPORTER, DISTRIBUTOR, TRADER, SERVICE_PROVIDER, RAW_MATERIAL, SPARE_PARTS, CONSUMABLES, TRANSPORTER, CONTRACTOR"
    )
    status: Mapped[str] = mapped_column(
        String(50),
        default="PENDING_APPROVAL",
        nullable=False,
        index=True,
        comment="PENDING_APPROVAL, ACTIVE, INACTIVE, SUSPENDED, BLACKLISTED"
    )
    grade: Mapped[str] = mapped_column(
        String(10),
        default="B",
        nullable=False,
        comment="A+, A, B, C, D"
    )

    # GST Compliance (Critical for India)
    gstin: Mapped[Optional[str]] = mapped_column(
        String(15),
        nullable=True,
        index=True,
        comment="15-digit GSTIN"
    )
    gst_registered: Mapped[bool] = mapped_column(Boolean, default=True)
    gst_state_code: Mapped[Optional[str]] = mapped_column(
        String(2),
        nullable=True,
        comment="First 2 digits of GSTIN"
    )
    pan: Mapped[Optional[str]] = mapped_column(
        String(10),
        nullable=True,
        comment="PAN (mandatory if GSTIN not available)"
    )
    tan: Mapped[Optional[str]] = mapped_column(
        String(10),
        nullable=True,
        comment="TAN for TDS"
    )

    # MSME (Micro, Small, Medium Enterprise)
    msme_registered: Mapped[bool] = mapped_column(Boolean, default=False)
    msme_number: Mapped[Optional[str]] = mapped_column(
        String(30),
        nullable=True,
        comment="Udyam Registration Number"
    )
    msme_category: Mapped[Optional[str]] = mapped_column(
        String(20),
        nullable=True,
        comment="MICRO, SMALL, MEDIUM"
    )

    # Contact Details
    contact_person: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    designation: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    email: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    phone: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    mobile: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    website: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)

    # Registered Address
    address_line1: Mapped[str] = mapped_column(String(255), nullable=False)
    address_line2: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    city: Mapped[str] = mapped_column(String(100), nullable=False)
    state: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    state_code: Mapped[Optional[str]] = mapped_column(
        String(2),
        nullable=True,
        comment="GST state code"
    )
    pincode: Mapped[str] = mapped_column(String(10), nullable=False)
    country: Mapped[str] = mapped_column(String(50), default="India")

    # Warehouse Address (if different)
    warehouse_address: Mapped[Optional[dict]] = mapped_column(
        JSONB,
        nullable=True,
        comment="Pickup/dispatch address"
    )

    # Bank Details (for payments)
    bank_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    bank_branch: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    bank_account_number: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    bank_ifsc: Mapped[Optional[str]] = mapped_column(String(11), nullable=True)
    bank_account_type: Mapped[Optional[str]] = mapped_column(
        String(20),
        nullable=True,
        comment="SAVINGS, CURRENT, OD"
    )
    beneficiary_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # Payment Terms
    payment_terms: Mapped[str] = mapped_column(
        String(50),
        default="NET_30",
        nullable=False,
        comment="ADVANCE, PARTIAL_ADVANCE, ON_DELIVERY, NET_7, NET_15, NET_30, NET_45, NET_60, NET_90, CUSTOM"
    )
    credit_days: Mapped[int] = mapped_column(
        Integer,
        default=30,
        comment="Credit period in days"
    )
    credit_limit: Mapped[Decimal] = mapped_column(
        Numeric(14, 2),
        default=Decimal("0"),
        comment="Maximum credit limit"
    )
    advance_percentage: Mapped[Decimal] = mapped_column(
        Numeric(5, 2),
        default=Decimal("0"),
        comment="Advance payment percentage required"
    )

    # TDS Compliance
    tds_applicable: Mapped[bool] = mapped_column(Boolean, default=True)
    tds_section: Mapped[Optional[str]] = mapped_column(
        String(10),
        nullable=True,
        comment="TDS section: 194C, 194H, 194I, 194J"
    )
    tds_rate: Mapped[Decimal] = mapped_column(
        Numeric(5, 2),
        default=Decimal("2"),
        comment="TDS rate percentage"
    )
    lower_tds_certificate: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        comment="Has lower TDS certificate"
    )
    lower_tds_rate: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(5, 2),
        nullable=True
    )
    lower_tds_valid_till: Mapped[Optional[date]] = mapped_column(Date, nullable=True)

    # Outstanding Tracking
    opening_balance: Mapped[Decimal] = mapped_column(
        Numeric(14, 2),
        default=Decimal("0"),
        comment="Opening balance (credit = we owe)"
    )
    current_balance: Mapped[Decimal] = mapped_column(
        Numeric(14, 2),
        default=Decimal("0"),
        comment="Current outstanding (positive = we owe)"
    )
    advance_balance: Mapped[Decimal] = mapped_column(
        Numeric(14, 2),
        default=Decimal("0"),
        comment="Advance paid (to be adjusted)"
    )

    # Products & Categories (what they supply)
    product_categories: Mapped[Optional[List[uuid.UUID]]] = mapped_column(
        JSONB,
        nullable=True,
        comment="Category IDs they supply"
    )
    primary_products: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Description of products supplied"
    )

    # Lead Time
    default_lead_days: Mapped[int] = mapped_column(
        Integer,
        default=7,
        comment="Default delivery lead time"
    )
    min_order_value: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(12, 2),
        nullable=True,
        comment="Minimum order value"
    )
    min_order_quantity: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True
    )

    # Preferred Warehouse (for delivery)
    default_warehouse_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("warehouses.id", ondelete="SET NULL"),
        nullable=True
    )

    # GL Account Link (for Finance Integration)
    gl_account_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("chart_of_accounts.id", ondelete="SET NULL"),
        nullable=True,
        comment="Linked GL account for Accounts Payable (Creditors)"
    )

    # Auto-generated supplier code for barcode generation (for SPARE_PARTS vendors)
    supplier_code: Mapped[Optional[str]] = mapped_column(
        String(2),
        nullable=True,
        unique=True,
        index=True,
        comment="2-char code for barcode generation (auto-created for SPARE_PARTS vendors on approval)"
    )

    # Documents
    gst_certificate_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    pan_card_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    msme_certificate_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    cancelled_cheque_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    agreement_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # Verification Status
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    verified_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    verified_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )

    # Performance Metrics
    total_po_count: Mapped[int] = mapped_column(Integer, default=0)
    total_po_value: Mapped[Decimal] = mapped_column(
        Numeric(14, 2),
        default=Decimal("0")
    )
    on_time_delivery_rate: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(5, 2),
        nullable=True,
        comment="Percentage of on-time deliveries"
    )
    quality_rejection_rate: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(5, 2),
        nullable=True,
        comment="Percentage of rejected goods"
    )
    last_po_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    last_payment_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Internal Notes
    internal_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Approval Workflow
    approved_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )
    approved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

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
    default_warehouse: Mapped[Optional["Warehouse"]] = relationship("Warehouse")
    gl_account: Mapped[Optional["ChartOfAccount"]] = relationship("ChartOfAccount")
    verified_by_user: Mapped[Optional["User"]] = relationship(
        "User",
        foreign_keys=[verified_by]
    )
    approved_by_user: Mapped[Optional["User"]] = relationship(
        "User",
        foreign_keys=[approved_by]
    )
    ledger_entries: Mapped[List["VendorLedger"]] = relationship(
        "VendorLedger",
        back_populates="vendor",
        cascade="all, delete-orphan"
    )
    purchase_orders: Mapped[List["PurchaseOrder"]] = relationship(
        "PurchaseOrder",
        back_populates="vendor"
    )

    @property
    def is_gst_compliant(self) -> bool:
        """Check if vendor has valid GST/PAN."""
        return bool(self.gstin or self.pan)

    @property
    def effective_tds_rate(self) -> Decimal:
        """Get effective TDS rate (considering lower deduction certificate)."""
        if self.lower_tds_certificate and self.lower_tds_valid_till:
            if self.lower_tds_valid_till >= date.today():
                return self.lower_tds_rate or self.tds_rate
        return self.tds_rate

    def __repr__(self) -> str:
        return f"<Vendor(code='{self.vendor_code}', name='{self.name}')>"


class VendorLedger(Base):
    """
    Vendor ledger for Accounts Payable tracking.
    Tracks all transactions with vendors.
    """
    __tablename__ = "vendor_ledger"
    __table_args__ = (
        Index("ix_vendor_ledger_date", "vendor_id", "transaction_date"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )

    vendor_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("vendors.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Transaction Details
    transaction_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
        comment="OPENING_BALANCE, PURCHASE_INVOICE, PAYMENT, ADVANCE, DEBIT_NOTE, CREDIT_NOTE, TDS_DEDUCTED, ADJUSTMENT"
    )
    transaction_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    due_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)

    # Reference Document
    reference_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="PO, GRN, INVOICE, PAYMENT, DN, CN"
    )
    reference_number: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True
    )
    reference_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
        comment="ID of the reference document"
    )

    # Vendor Invoice Details (if applicable)
    vendor_invoice_number: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        comment="Vendor's bill/invoice number"
    )
    vendor_invoice_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)

    # Amounts (Credit = we owe more, Debit = we owe less)
    debit_amount: Mapped[Decimal] = mapped_column(
        Numeric(14, 2),
        default=Decimal("0"),
        comment="Decreases payable (payments, returns)"
    )
    credit_amount: Mapped[Decimal] = mapped_column(
        Numeric(14, 2),
        default=Decimal("0"),
        comment="Increases payable (invoices)"
    )
    running_balance: Mapped[Decimal] = mapped_column(
        Numeric(14, 2),
        default=Decimal("0"),
        comment="Balance after this transaction"
    )

    # TDS (if applicable)
    tds_amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        default=Decimal("0")
    )
    tds_section: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)

    # Payment Details (if transaction is a payment)
    payment_mode: Mapped[Optional[str]] = mapped_column(
        String(20),
        nullable=True,
        comment="NEFT, RTGS, CHEQUE, UPI"
    )
    payment_reference: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        comment="UTR/Transaction reference"
    )
    bank_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    cheque_number: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    cheque_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)

    # Status
    is_settled: Mapped[bool] = mapped_column(Boolean, default=False)
    settled_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    days_overdue: Mapped[int] = mapped_column(Integer, default=0)

    # Narration
    narration: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Audit
    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    # Relationships
    vendor: Mapped["Vendor"] = relationship("Vendor", back_populates="ledger_entries")
    creator: Mapped[Optional["User"]] = relationship("User")

    @property
    def is_overdue(self) -> bool:
        """Check if transaction is overdue."""
        if self.due_date and not self.is_settled:
            return date.today() > self.due_date
        return False

    def __repr__(self) -> str:
        return f"<VendorLedger(ref='{self.reference_number}', type='{self.transaction_type}')>"


class VendorContact(Base):
    """
    Additional contacts for a vendor.
    For large vendors with multiple contact persons.
    """
    __tablename__ = "vendor_contacts"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )

    vendor_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("vendors.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Contact Details
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    designation: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    department: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        comment="SALES, ACCOUNTS, DISPATCH, QUALITY"
    )
    email: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    phone: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    mobile: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)

    is_primary: Mapped[bool] = mapped_column(Boolean, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    # Relationships
    vendor: Mapped["Vendor"] = relationship("Vendor")

    def __repr__(self) -> str:
        return f"<VendorContact(name='{self.name}', vendor_id='{self.vendor_id}')>"
