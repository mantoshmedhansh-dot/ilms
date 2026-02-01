"""Commission and Incentive models for sales team and partners.

Supports:
- Sales representative commissions
- Dealer/Distributor incentives
- Affiliate/Referral program
- Service engineer incentives
- Multi-tier commission structures
- Payout management
"""
import uuid
from datetime import datetime, date, timezone
from enum import Enum
from typing import TYPE_CHECKING, Optional, List
from decimal import Decimal

from sqlalchemy import String, Boolean, DateTime, ForeignKey, Integer, Text, Numeric, Date
from sqlalchemy import UniqueConstraint, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.dealer import Dealer
    from app.models.order import Order
    from app.models.product import Product, Category


class CommissionType(str, Enum):
    """Commission type enumeration."""
    SALES_REP = "SALES_REP"                 # Direct sales representative
    AREA_MANAGER = "AREA_MANAGER"           # Area sales manager
    REGIONAL_MANAGER = "REGIONAL_MANAGER"   # Regional manager
    DEALER = "DEALER"                       # Dealer commission
    DISTRIBUTOR = "DISTRIBUTOR"             # Distributor commission
    AFFILIATE = "AFFILIATE"                 # Affiliate referral
    INFLUENCER = "INFLUENCER"               # Influencer commission
    SERVICE_ENGINEER = "SERVICE_ENGINEER"   # Service/installation commission
    REFERRAL = "REFERRAL"                   # Customer referral


class CalculationBasis(str, Enum):
    """How commission is calculated."""
    PERCENTAGE_OF_REVENUE = "PERCENTAGE_OF_REVENUE"
    PERCENTAGE_OF_MARGIN = "PERCENTAGE_OF_MARGIN"
    FIXED_PER_UNIT = "FIXED_PER_UNIT"
    FIXED_PER_ORDER = "FIXED_PER_ORDER"
    SLAB_BASED = "SLAB_BASED"
    TIERED = "TIERED"


class CommissionStatus(str, Enum):
    """Commission transaction status."""
    PENDING = "PENDING"             # Order not yet delivered
    ELIGIBLE = "ELIGIBLE"           # Eligible for payout
    APPROVED = "APPROVED"           # Approved for payout
    PROCESSING = "PROCESSING"       # Payout in progress
    PAID = "PAID"                   # Paid out
    CANCELLED = "CANCELLED"         # Cancelled (order cancelled)
    ON_HOLD = "ON_HOLD"             # On hold (dispute/review)
    CLAWBACK = "CLAWBACK"           # Reversed/clawed back


class PayoutStatus(str, Enum):
    """Payout batch status."""
    DRAFT = "DRAFT"
    PENDING_APPROVAL = "PENDING_APPROVAL"
    APPROVED = "APPROVED"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class CommissionPlan(Base):
    """
    Commission plan/structure definition.
    Defines how commissions are calculated for different roles.
    """
    __tablename__ = "commission_plans"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )

    # Plan Identification
    plan_code: Mapped[str] = mapped_column(
        String(30),
        unique=True,
        nullable=False,
        index=True,
        comment="Unique plan code e.g., SALES_REP_2024"
    )
    plan_name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Type & Basis
    commission_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
        default="SALES_REP"
    )
    calculation_basis: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="PERCENTAGE_OF_REVENUE"
    )

    # Validity
    effective_from: Mapped[date] = mapped_column(Date, nullable=False)
    effective_to: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Default Commission Rates
    default_rate: Mapped[Decimal] = mapped_column(
        Numeric(5, 2),
        default=Decimal("0"),
        comment="Default commission % or fixed amount"
    )
    min_rate: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(5, 2),
        nullable=True
    )
    max_rate: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(5, 2),
        nullable=True
    )

    # Slab/Tier Configuration (JSONB)
    rate_slabs: Mapped[Optional[dict]] = mapped_column(
        JSONB,
        nullable=True,
        comment="Commission rate slabs"
    )
    # Example: [{"min": 0, "max": 100000, "rate": 2}, {"min": 100001, "max": 500000, "rate": 3}]

    # Eligibility Rules
    min_order_value: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(12, 2),
        nullable=True,
        comment="Minimum order value for commission"
    )
    applicable_products: Mapped[Optional[dict]] = mapped_column(
        JSONB,
        nullable=True,
        comment="List of applicable product IDs"
    )
    applicable_categories: Mapped[Optional[dict]] = mapped_column(
        JSONB,
        nullable=True,
        comment="List of applicable category IDs"
    )
    excluded_products: Mapped[Optional[dict]] = mapped_column(
        JSONB,
        nullable=True,
        comment="List of excluded product IDs"
    )

    # Payout Rules
    payout_after_days: Mapped[int] = mapped_column(
        Integer,
        default=30,
        comment="Days after delivery to process payout"
    )
    requires_full_payment: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        comment="Require full payment before commission"
    )
    clawback_period_days: Mapped[int] = mapped_column(
        Integer,
        default=30,
        comment="Days within which commission can be clawed back"
    )

    # TDS
    tds_applicable: Mapped[bool] = mapped_column(Boolean, default=True)
    tds_rate: Mapped[Decimal] = mapped_column(
        Numeric(5, 2),
        default=Decimal("10"),
        comment="TDS rate %"
    )
    tds_section: Mapped[Optional[str]] = mapped_column(
        String(20),
        nullable=True,
        default="194H"
    )

    # Terms
    terms_and_conditions: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

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
    category_rates: Mapped[List["CommissionCategoryRate"]] = relationship(
        "CommissionCategoryRate",
        back_populates="plan",
        cascade="all, delete-orphan"
    )
    product_rates: Mapped[List["CommissionProductRate"]] = relationship(
        "CommissionProductRate",
        back_populates="plan",
        cascade="all, delete-orphan"
    )

    @property
    def is_valid(self) -> bool:
        """Check if plan is currently valid."""
        today = date.today()
        if self.effective_to:
            return self.is_active and self.effective_from <= today <= self.effective_to
        return self.is_active and self.effective_from <= today

    def __repr__(self) -> str:
        return f"<CommissionPlan(code='{self.plan_code}', type='{self.commission_type}')>"


class CommissionCategoryRate(Base):
    """
    Category-specific commission rates.
    Different rates for different product categories.
    """
    __tablename__ = "commission_category_rates"
    __table_args__ = (
        UniqueConstraint("plan_id", "category_id", name="uq_plan_category_rate"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )

    plan_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("commission_plans.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    category_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("categories.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Rate
    commission_rate: Mapped[Decimal] = mapped_column(
        Numeric(5, 2),
        nullable=False,
        comment="Commission rate for this category"
    )

    # Slabs (optional override)
    rate_slabs: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)

    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    # Relationships
    plan: Mapped["CommissionPlan"] = relationship(
        "CommissionPlan",
        back_populates="category_rates"
    )
    category: Mapped["Category"] = relationship("Category")

    def __repr__(self) -> str:
        return f"<CommissionCategoryRate(plan={self.plan_id}, category={self.category_id})>"


class CommissionProductRate(Base):
    """
    Product-specific commission rates.
    Override for specific products.
    """
    __tablename__ = "commission_product_rates"
    __table_args__ = (
        UniqueConstraint("plan_id", "product_id", name="uq_plan_product_rate"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )

    plan_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("commission_plans.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("products.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Rate
    commission_rate: Mapped[Decimal] = mapped_column(
        Numeric(5, 2),
        nullable=False
    )
    fixed_amount: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(10, 2),
        nullable=True,
        comment="Fixed amount per unit (overrides rate)"
    )

    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    # Relationships
    plan: Mapped["CommissionPlan"] = relationship(
        "CommissionPlan",
        back_populates="product_rates"
    )
    product: Mapped["Product"] = relationship("Product")

    def __repr__(self) -> str:
        return f"<CommissionProductRate(plan={self.plan_id}, product={self.product_id})>"


class CommissionEarner(Base):
    """
    Commission earner profile.
    Links users/dealers to commission plans.
    """
    __tablename__ = "commission_earners"
    __table_args__ = (
        Index("ix_commission_earners_type", "earner_type"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )

    # Earner Type
    earner_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="SALES_REP"
    )

    # Link to User or Dealer
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=True,
        index=True
    )
    dealer_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("dealers.id", ondelete="CASCADE"),
        nullable=True,
        index=True
    )

    # Earner Details (for affiliates without user account)
    earner_name: Mapped[str] = mapped_column(String(200), nullable=False)
    earner_email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    earner_phone: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)

    # Referral/Affiliate Code
    referral_code: Mapped[Optional[str]] = mapped_column(
        String(30),
        unique=True,
        nullable=True,
        index=True,
        comment="Unique referral code for affiliate"
    )

    # Commission Plan
    plan_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("commission_plans.id", ondelete="RESTRICT"),
        nullable=False,
        index=True
    )

    # Custom Rate (override plan default)
    custom_rate: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(5, 2),
        nullable=True,
        comment="Custom commission rate for this earner"
    )

    # Bank Details for Payout
    bank_name: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    bank_account_number: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    bank_ifsc: Mapped[Optional[str]] = mapped_column(String(11), nullable=True)
    bank_account_name: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)

    # UPI for small payouts
    upi_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # PAN for TDS
    pan_number: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    tds_rate_override: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(5, 2),
        nullable=True,
        comment="Override TDS rate for this earner"
    )

    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    verified_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Performance
    total_earnings: Mapped[Decimal] = mapped_column(
        Numeric(14, 2),
        default=Decimal("0")
    )
    total_paid: Mapped[Decimal] = mapped_column(
        Numeric(14, 2),
        default=Decimal("0")
    )
    pending_payout: Mapped[Decimal] = mapped_column(
        Numeric(14, 2),
        default=Decimal("0")
    )
    total_orders: Mapped[int] = mapped_column(Integer, default=0)

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
    user: Mapped[Optional["User"]] = relationship("User")
    dealer: Mapped[Optional["Dealer"]] = relationship("Dealer")
    plan: Mapped["CommissionPlan"] = relationship("CommissionPlan")
    transactions: Mapped[List["CommissionTransaction"]] = relationship(
        "CommissionTransaction",
        back_populates="earner",
        cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<CommissionEarner(name='{self.earner_name}', type='{self.earner_type}')>"


class CommissionTransaction(Base):
    """
    Individual commission transaction.
    One record per order/service for each earner.
    """
    __tablename__ = "commission_transactions"
    __table_args__ = (
        Index("ix_commission_transactions_date", "transaction_date"),
        Index("ix_commission_transactions_status", "status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )

    # Earner
    earner_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("commission_earners.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Order/Service Reference
    order_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("orders.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    service_request_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
        comment="For service engineer commissions"
    )

    # Transaction Details
    transaction_date: Mapped[date] = mapped_column(Date, nullable=False)
    transaction_reference: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="Order number or reference"
    )

    # Values
    order_value: Mapped[Decimal] = mapped_column(
        Numeric(14, 2),
        nullable=False,
        comment="Order/Invoice value"
    )
    commission_base: Mapped[Decimal] = mapped_column(
        Numeric(14, 2),
        nullable=False,
        comment="Base value for commission calculation"
    )

    # Commission Calculation
    commission_rate: Mapped[Decimal] = mapped_column(
        Numeric(5, 2),
        nullable=False,
        comment="Applied commission rate %"
    )
    commission_amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
        comment="Gross commission amount"
    )

    # Deductions
    tds_rate: Mapped[Decimal] = mapped_column(
        Numeric(5, 2),
        default=Decimal("0")
    )
    tds_amount: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        default=Decimal("0")
    )
    other_deductions: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        default=Decimal("0")
    )
    deduction_remarks: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # Net Amount
    net_amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
        comment="Net commission after deductions"
    )

    # Status
    status: Mapped[str] = mapped_column(
        String(50),
        default="PENDING",
        nullable=False
    )
    status_reason: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # Eligibility
    eligible_date: Mapped[Optional[date]] = mapped_column(
        Date,
        nullable=True,
        comment="Date when eligible for payout"
    )
    is_eligible: Mapped[bool] = mapped_column(Boolean, default=False)

    # Payout Reference
    payout_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("commission_payouts.id", ondelete="SET NULL"),
        nullable=True
    )
    paid_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Clawback
    is_clawed_back: Mapped[bool] = mapped_column(Boolean, default=False)
    clawback_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    clawback_reason: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # Multi-level (for hierarchical commissions)
    parent_transaction_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("commission_transactions.id", ondelete="SET NULL"),
        nullable=True,
        comment="Parent transaction for override commissions"
    )
    level: Mapped[int] = mapped_column(
        Integer,
        default=1,
        comment="Level in commission hierarchy"
    )

    # Remarks
    remarks: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

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
    earner: Mapped["CommissionEarner"] = relationship(
        "CommissionEarner",
        back_populates="transactions"
    )
    order: Mapped[Optional["Order"]] = relationship("Order")
    payout: Mapped[Optional["CommissionPayout"]] = relationship(
        "CommissionPayout",
        back_populates="transactions"
    )

    def __repr__(self) -> str:
        return f"<CommissionTransaction(earner={self.earner_id}, amount={self.commission_amount})>"


class CommissionPayout(Base):
    """
    Commission payout batch.
    Groups multiple transactions for single payout.
    """
    __tablename__ = "commission_payouts"
    __table_args__ = (
        Index("ix_commission_payouts_date", "payout_date"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )

    # Payout Identification
    payout_number: Mapped[str] = mapped_column(
        String(30),
        unique=True,
        nullable=False,
        index=True,
        comment="Payout batch number"
    )

    # Period
    period_start: Mapped[date] = mapped_column(Date, nullable=False)
    period_end: Mapped[date] = mapped_column(Date, nullable=False)
    payout_date: Mapped[date] = mapped_column(Date, nullable=False)

    # Status
    status: Mapped[str] = mapped_column(
        String(50),
        default="DRAFT",
        nullable=False
    )

    # Totals
    total_gross: Mapped[Decimal] = mapped_column(
        Numeric(14, 2),
        default=Decimal("0"),
        comment="Total gross commission"
    )
    total_tds: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        default=Decimal("0"),
        comment="Total TDS deducted"
    )
    total_deductions: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        default=Decimal("0")
    )
    total_net: Mapped[Decimal] = mapped_column(
        Numeric(14, 2),
        default=Decimal("0"),
        comment="Total net payout"
    )

    # Transaction Count
    transaction_count: Mapped[int] = mapped_column(Integer, default=0)
    earner_count: Mapped[int] = mapped_column(Integer, default=0)

    # Payment Details
    payment_mode: Mapped[Optional[str]] = mapped_column(
        String(30),
        nullable=True,
        comment="BANK_TRANSFER, UPI, CHEQUE"
    )
    payment_reference: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        comment="UTR/Transaction ID"
    )
    payment_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)

    # Remarks
    remarks: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Audit
    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )
    approved_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        nullable=True
    )
    approved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    processed_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        nullable=True
    )
    processed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

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
    transactions: Mapped[List["CommissionTransaction"]] = relationship(
        "CommissionTransaction",
        back_populates="payout"
    )
    line_items: Mapped[List["CommissionPayoutLine"]] = relationship(
        "CommissionPayoutLine",
        back_populates="payout",
        cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<CommissionPayout(number='{self.payout_number}', status='{self.status}')>"


class CommissionPayoutLine(Base):
    """
    Individual payout line per earner.
    Summary of all transactions for one earner in a payout.
    """
    __tablename__ = "commission_payout_lines"
    __table_args__ = (
        UniqueConstraint("payout_id", "earner_id", name="uq_payout_earner"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )

    payout_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("commission_payouts.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    earner_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("commission_earners.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Amounts
    gross_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    tds_amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=Decimal("0"))
    other_deductions: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=Decimal("0"))
    net_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)

    # Transaction Count
    transaction_count: Mapped[int] = mapped_column(Integer, default=0)

    # Payment Details
    payment_mode: Mapped[str] = mapped_column(String(30), nullable=False)
    bank_name: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    account_number: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    ifsc_code: Mapped[Optional[str]] = mapped_column(String(11), nullable=True)
    upi_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # Status
    payment_status: Mapped[str] = mapped_column(
        String(20),
        default="PENDING",
        comment="PENDING, SUCCESS, FAILED"
    )
    payment_reference: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    payment_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    failure_reason: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    # Relationships
    payout: Mapped["CommissionPayout"] = relationship(
        "CommissionPayout",
        back_populates="line_items"
    )
    earner: Mapped["CommissionEarner"] = relationship("CommissionEarner")

    def __repr__(self) -> str:
        return f"<CommissionPayoutLine(payout={self.payout_id}, earner={self.earner_id})>"


class AffiliateReferral(Base):
    """
    Track affiliate/referral conversions.
    Links referral codes to orders.
    """
    __tablename__ = "affiliate_referrals"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )

    # Affiliate
    earner_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("commission_earners.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    referral_code: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        index=True
    )

    # Referred Customer
    customer_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    customer_email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    customer_phone: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)

    # Order
    order_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("orders.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )

    # Click/Visit Tracking
    click_timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    source_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    landing_page: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    utm_source: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    utm_medium: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    utm_campaign: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # Device Info
    ip_address: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    user_agent: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    device_type: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)

    # Conversion
    is_converted: Mapped[bool] = mapped_column(Boolean, default=False)
    converted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    conversion_value: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(14, 2),
        nullable=True
    )

    # Attribution
    attribution_window_days: Mapped[int] = mapped_column(
        Integer,
        default=30,
        comment="Days within which conversion is attributed"
    )
    is_first_order: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        comment="Is this customer's first order"
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    # Relationships
    earner: Mapped["CommissionEarner"] = relationship("CommissionEarner")
    customer: Mapped[Optional["User"]] = relationship("User")
    order: Mapped[Optional["Order"]] = relationship("Order")

    def __repr__(self) -> str:
        return f"<AffiliateReferral(code='{self.referral_code}', converted={self.is_converted})>"
