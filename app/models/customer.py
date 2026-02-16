import uuid
from datetime import datetime, date, timezone
from decimal import Decimal
from enum import Enum
from typing import TYPE_CHECKING, Optional, List

from sqlalchemy import String, Boolean, DateTime, Date, ForeignKey, Text, Numeric, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID

from app.database import Base

if TYPE_CHECKING:
    from app.models.order import Order
    from app.models.region import Region
    from app.models.service_request import ServiceRequest
    from app.models.installation import Installation
    from app.models.amc import AMCContract
    from app.models.accounting import ChartOfAccount


class CustomerType(str, Enum):
    """Customer type enumeration."""
    INDIVIDUAL = "INDIVIDUAL"
    BUSINESS = "BUSINESS"
    DEALER = "DEALER"
    DISTRIBUTOR = "DISTRIBUTOR"


class CustomerSource(str, Enum):
    """Customer acquisition source."""
    WEBSITE = "WEBSITE"
    WALK_IN = "WALK_IN"
    REFERRAL = "REFERRAL"
    DEALER = "DEALER"
    CAMPAIGN = "CAMPAIGN"
    SOCIAL_MEDIA = "SOCIAL_MEDIA"
    OTHER = "OTHER"


class AddressType(str, Enum):
    """Address type enumeration."""
    HOME = "HOME"
    OFFICE = "OFFICE"
    BILLING = "BILLING"
    SHIPPING = "SHIPPING"
    OTHER = "OTHER"


class Customer(Base):
    """
    Customer model for CRM and orders.
    Stores customer information and relationships.
    """
    __tablename__ = "customers"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )

    # Basic Info
    customer_code: Mapped[str] = mapped_column(
        String(20),
        unique=True,
        nullable=False,
        index=True
    )
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # Contact
    email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)
    phone: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    alternate_phone: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)

    # Type & Source
    customer_type: Mapped[str] = mapped_column(
        String(50),
        default="INDIVIDUAL",
        nullable=False,
        comment="INDIVIDUAL, BUSINESS, DEALER, DISTRIBUTOR"
    )
    source: Mapped[str] = mapped_column(
        String(50),
        default="WEBSITE",
        nullable=False,
        comment="WEBSITE, WALK_IN, REFERRAL, DEALER, CAMPAIGN, SOCIAL_MEDIA, OTHER"
    )

    # Business Info (for business customers)
    company_name: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    gst_number: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)

    # Demographics
    date_of_birth: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    anniversary_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)

    # Region for filtering
    region_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("regions.id", ondelete="SET NULL"),
        nullable=True
    )

    # GL Account Link (for Finance Integration)
    gl_account_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("chart_of_accounts.id", ondelete="SET NULL"),
        nullable=True,
        comment="Linked GL account for Accounts Receivable (Debtors)"
    )

    # Credit Management
    credit_limit: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(14, 2),
        nullable=True,
        default=None,
        comment="Max credit allowed. NULL = unlimited"
    )
    credit_used: Mapped[Decimal] = mapped_column(
        Numeric(14, 2),
        default=Decimal("0"),
        server_default="0",
        comment="Current outstanding AR balance"
    )

    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False)

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
    region: Mapped[Optional["Region"]] = relationship("Region")
    gl_account: Mapped[Optional["ChartOfAccount"]] = relationship("ChartOfAccount")
    addresses: Mapped[List["CustomerAddress"]] = relationship(
        "CustomerAddress",
        back_populates="customer",
        cascade="all, delete-orphan"
    )
    orders: Mapped[List["Order"]] = relationship(
        "Order",
        back_populates="customer"
    )
    service_requests: Mapped[List["ServiceRequest"]] = relationship(
        "ServiceRequest",
        back_populates="customer"
    )
    installations: Mapped[List["Installation"]] = relationship(
        "Installation",
        back_populates="customer"
    )
    amc_contracts: Mapped[List["AMCContract"]] = relationship(
        "AMCContract",
        back_populates="customer"
    )

    @property
    def full_name(self) -> str:
        """Get customer's full name."""
        if self.last_name:
            return f"{self.first_name} {self.last_name}"
        return self.first_name

    @property
    def default_address(self) -> Optional["CustomerAddress"]:
        """Get default address."""
        for addr in self.addresses:
            if addr.is_default:
                return addr
        return self.addresses[0] if self.addresses else None

    def __repr__(self) -> str:
        return f"<Customer(code='{self.customer_code}', name='{self.full_name}')>"


class CustomerAddress(Base):
    """Customer address model."""
    __tablename__ = "customer_addresses"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    customer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("customers.id", ondelete="CASCADE"),
        nullable=False
    )

    # Address Type
    address_type: Mapped[str] = mapped_column(
        String(50),
        default="HOME",
        nullable=False,
        comment="HOME, OFFICE, BILLING, SHIPPING, OTHER"
    )

    # Contact for this address
    contact_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    contact_phone: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)

    # Address Lines
    address_line1: Mapped[str] = mapped_column(String(255), nullable=False)
    address_line2: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    landmark: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)

    # Location
    city: Mapped[str] = mapped_column(String(100), nullable=False)
    state: Mapped[str] = mapped_column(String(100), nullable=False)
    pincode: Mapped[str] = mapped_column(String(10), nullable=False)
    country: Mapped[str] = mapped_column(String(100), default="India", nullable=False)

    # Coordinates (for delivery tracking)
    latitude: Mapped[Optional[float]] = mapped_column(nullable=True)
    longitude: Mapped[Optional[float]] = mapped_column(nullable=True)

    # Flags
    is_default: Mapped[bool] = mapped_column(Boolean, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

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
    customer: Mapped["Customer"] = relationship("Customer", back_populates="addresses")

    @property
    def full_address(self) -> str:
        """Get formatted full address."""
        parts = [self.address_line1]
        if self.address_line2:
            parts.append(self.address_line2)
        if self.landmark:
            parts.append(f"Near {self.landmark}")
        parts.append(f"{self.city}, {self.state} - {self.pincode}")
        return ", ".join(parts)

    def __repr__(self) -> str:
        return f"<CustomerAddress(type='{self.address_type}', city='{self.city}')>"


class CustomerTransactionType(str, Enum):
    """Customer transaction types for AR ledger."""
    OPENING_BALANCE = "OPENING_BALANCE"
    INVOICE = "INVOICE"               # Sales invoice (increases AR)
    PAYMENT = "PAYMENT"               # Payment received (decreases AR)
    CREDIT_NOTE = "CREDIT_NOTE"       # Credit note (decreases AR)
    DEBIT_NOTE = "DEBIT_NOTE"         # Debit note (increases AR)
    ADVANCE = "ADVANCE"               # Advance payment (decreases AR)
    ADJUSTMENT = "ADJUSTMENT"         # Manual adjustment
    REFUND = "REFUND"                 # Refund to customer (increases AR)
    WRITE_OFF = "WRITE_OFF"           # Bad debt write-off


class CustomerLedger(Base):
    """
    Customer ledger for Accounts Receivable tracking.
    Maintains running balance for customer credit management.
    """
    __tablename__ = "customer_ledger"
    __table_args__ = (
        Index("ix_customer_ledger_date", "customer_id", "transaction_date"),
        Index("ix_customer_ledger_due_date", "due_date"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )

    customer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("customers.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Transaction Details
    transaction_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="OPENING_BALANCE, INVOICE, PAYMENT, CREDIT_NOTE, DEBIT_NOTE, ADVANCE, ADJUSTMENT, REFUND, WRITE_OFF"
    )
    transaction_date: Mapped[date] = mapped_column(Date, nullable=False)
    due_date: Mapped[Optional[date]] = mapped_column(
        Date,
        nullable=True,
        comment="Due date for payment (for invoices)"
    )

    # Reference to source document
    reference_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="INVOICE, PAYMENT_RECEIPT, CREDIT_NOTE, DEBIT_NOTE, ORDER, MANUAL"
    )
    reference_number: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="Invoice/Receipt/Order number"
    )
    reference_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
        comment="UUID of the source document"
    )

    # Order reference (for linking to orders)
    order_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("orders.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )

    # Amounts (Debit = Increases AR, Credit = Decreases AR)
    debit_amount: Mapped[Decimal] = mapped_column(
        Numeric(14, 2),
        default=Decimal("0"),
        comment="Increases outstanding (invoices, debit notes)"
    )
    credit_amount: Mapped[Decimal] = mapped_column(
        Numeric(14, 2),
        default=Decimal("0"),
        comment="Decreases outstanding (payments, credit notes)"
    )
    balance: Mapped[Decimal] = mapped_column(
        Numeric(14, 2),
        default=Decimal("0"),
        comment="Running balance after this transaction"
    )

    # Tax amounts (for GST tracking)
    tax_amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        default=Decimal("0"),
        comment="Tax portion of the amount"
    )

    # Settlement tracking
    is_settled: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        comment="True if invoice is fully paid"
    )
    settled_date: Mapped[Optional[date]] = mapped_column(
        Date,
        nullable=True,
        comment="Date when fully settled"
    )
    settled_against_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
        comment="Reference to payment/credit that settled this"
    )

    # Description and notes
    description: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True
    )
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Channel tracking (for channel-wise reporting)
    channel_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sales_channels.id", ondelete="SET NULL"),
        nullable=True
    )

    # Created by
    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
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
    customer: Mapped["Customer"] = relationship("Customer", foreign_keys=[customer_id])
    order: Mapped[Optional["Order"]] = relationship("Order", foreign_keys=[order_id])

    @property
    def is_overdue(self) -> bool:
        """Check if the invoice is overdue."""
        if self.is_settled or not self.due_date:
            return False
        return date.today() > self.due_date

    @property
    def days_overdue(self) -> int:
        """Get number of days overdue."""
        if not self.is_overdue:
            return 0
        return (date.today() - self.due_date).days

    @property
    def aging_bucket(self) -> str:
        """Get aging bucket for the transaction."""
        if self.is_settled:
            return "SETTLED"
        if not self.due_date:
            return "NOT_DUE"

        days = (date.today() - self.due_date).days
        if days <= 0:
            return "CURRENT"
        elif days <= 30:
            return "1_30"
        elif days <= 60:
            return "31_60"
        elif days <= 90:
            return "61_90"
        else:
            return "OVER_90"

    def __repr__(self) -> str:
        return f"<CustomerLedger(customer_id='{self.customer_id}', ref='{self.reference_number}', balance={self.balance})>"
