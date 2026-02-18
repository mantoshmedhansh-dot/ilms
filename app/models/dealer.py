"""Dealer/Distributor management models for B2B sales.

Supports:
- Dealer and Distributor onboarding
- Multi-tier pricing (MRP → Retail → Dealer → Distributor)
- Credit limit and credit management
- Territory/Region assignment
- Sales targets and performance tracking
- Scheme management
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
    from app.models.product import Product, Category
    from app.models.warehouse import Warehouse
    from app.models.order import Order


class DealerType(str, Enum):
    """Dealer type enumeration."""
    DISTRIBUTOR = "DISTRIBUTOR"           # Regional distributor (buys in bulk)
    DEALER = "DEALER"                     # Authorized dealer
    SUB_DEALER = "SUB_DEALER"             # Sub-dealer under dealer
    RETAILER = "RETAILER"                 # Retail shop
    FRANCHISE = "FRANCHISE"               # Franchise store
    MODERN_TRADE = "MODERN_TRADE"         # Croma, Reliance Digital, etc.
    INSTITUTIONAL = "INSTITUTIONAL"        # Corporate/Institutional buyer
    GOVERNMENT = "GOVERNMENT"             # Govt buyer


class DealerStatus(str, Enum):
    """Dealer status enumeration."""
    PENDING_APPROVAL = "PENDING_APPROVAL"
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    SUSPENDED = "SUSPENDED"
    BLACKLISTED = "BLACKLISTED"
    TERMINATED = "TERMINATED"


class DealerTier(str, Enum):
    """Dealer tier for pricing."""
    PLATINUM = "PLATINUM"
    GOLD = "GOLD"
    SILVER = "SILVER"
    BRONZE = "BRONZE"
    STANDARD = "STANDARD"


class CreditStatus(str, Enum):
    """Credit account status."""
    ACTIVE = "ACTIVE"
    ON_HOLD = "ON_HOLD"
    BLOCKED = "BLOCKED"
    CLOSED = "CLOSED"


class TransactionType(str, Enum):
    """Credit transaction type."""
    INVOICE = "INVOICE"               # Sale invoice (increases outstanding)
    PAYMENT = "PAYMENT"               # Payment received (decreases outstanding)
    CREDIT_NOTE = "CREDIT_NOTE"       # Return/adjustment (decreases outstanding)
    DEBIT_NOTE = "DEBIT_NOTE"         # Additional charge (increases outstanding)
    OPENING_BALANCE = "OPENING_BALANCE"
    ADJUSTMENT = "ADJUSTMENT"


class SchemeType(str, Enum):
    """Dealer scheme type."""
    QUANTITY_DISCOUNT = "QUANTITY_DISCOUNT"     # Buy X, get Y% off
    SLAB_DISCOUNT = "SLAB_DISCOUNT"            # Volume-based slabs
    CASH_DISCOUNT = "CASH_DISCOUNT"            # Prompt payment discount
    EARLY_PAYMENT = "EARLY_PAYMENT"            # Early payment incentive
    FESTIVE_SCHEME = "FESTIVE_SCHEME"          # Festival special
    TARGET_INCENTIVE = "TARGET_INCENTIVE"      # Target achievement
    PRODUCT_COMBO = "PRODUCT_COMBO"            # Bundle scheme
    FOC = "FOC"                                 # Free of cost (buy X get Y free)


class Dealer(Base):
    """
    Dealer/Distributor master model.
    Manages B2B channel partners.
    """
    __tablename__ = "dealers"
    __table_args__ = (
        Index("ix_dealers_region", "region", "state"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )

    # Identification
    dealer_code: Mapped[str] = mapped_column(
        String(30),
        unique=True,
        nullable=False,
        index=True,
        comment="Unique dealer code e.g., DLR-MH-00001"
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    legal_name: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
        comment="Registered business name"
    )
    display_name: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)

    # Type & Status
    dealer_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
        comment="DISTRIBUTOR, DEALER, SUB_DEALER, RETAILER, FRANCHISE, MODERN_TRADE, INSTITUTIONAL, GOVERNMENT"
    )
    status: Mapped[str] = mapped_column(
        String(50),
        default="PENDING_APPROVAL",
        nullable=False,
        index=True,
        comment="PENDING_APPROVAL, ACTIVE, INACTIVE, SUSPENDED, BLACKLISTED, TERMINATED"
    )
    tier: Mapped[str] = mapped_column(
        String(50),
        default="STANDARD",
        nullable=False,
        comment="PLATINUM, GOLD, SILVER, BRONZE, STANDARD"
    )

    # Hierarchy (for sub-dealers)
    parent_dealer_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("dealers.id", ondelete="SET NULL"),
        nullable=True,
        comment="Parent dealer for sub-dealers"
    )

    # User Account (for portal login)
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        unique=True
    )

    # GST & Tax
    gstin: Mapped[str] = mapped_column(
        String(15),
        nullable=False,
        index=True,
        comment="GSTIN number"
    )
    pan: Mapped[str] = mapped_column(String(10), nullable=False)
    tan: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    gst_registration_type: Mapped[str] = mapped_column(
        String(30),
        default="REGULAR",
        comment="REGULAR, COMPOSITION, SEZ, etc."
    )
    is_msme: Mapped[bool] = mapped_column(Boolean, default=False)
    msme_number: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)

    # Contact
    contact_person: Mapped[str] = mapped_column(String(200), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    phone: Mapped[str] = mapped_column(String(20), nullable=False)
    alternate_phone: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    whatsapp: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)

    # Address - Registered
    registered_address_line1: Mapped[str] = mapped_column(String(255), nullable=False)
    registered_address_line2: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    registered_city: Mapped[str] = mapped_column(String(100), nullable=False)
    registered_district: Mapped[str] = mapped_column(String(100), nullable=False)
    registered_state: Mapped[str] = mapped_column(String(100), nullable=False)
    registered_state_code: Mapped[str] = mapped_column(String(2), nullable=False)
    registered_pincode: Mapped[str] = mapped_column(String(10), nullable=False)

    # Address - Shipping/Godown (if different)
    shipping_address_line1: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    shipping_address_line2: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    shipping_city: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    shipping_state: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    shipping_pincode: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)

    # Territory Assignment
    region: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="Sales region (North, South, East, West)"
    )
    state: Mapped[str] = mapped_column(String(100), nullable=False)
    territory: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        comment="Specific territory/zone"
    )
    assigned_pincodes: Mapped[Optional[dict]] = mapped_column(
        JSONB,
        nullable=True,
        comment="List of assigned pincode ranges"
    )

    # Business Details
    business_type: Mapped[str] = mapped_column(
        String(50),
        default="PROPRIETORSHIP",
        comment="PROPRIETORSHIP, PARTNERSHIP, PVT_LTD, LLP, etc."
    )
    establishment_year: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    annual_turnover: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(14, 2),
        nullable=True,
        comment="Annual turnover in lakhs"
    )
    shop_area_sqft: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    no_of_employees: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    existing_brands: Mapped[Optional[dict]] = mapped_column(
        JSONB,
        nullable=True,
        comment="Other brands dealer sells"
    )

    # Bank Details
    bank_name: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    bank_branch: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    bank_account_number: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    bank_ifsc: Mapped[Optional[str]] = mapped_column(String(11), nullable=True)
    bank_account_name: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)

    # Credit Terms
    credit_limit: Mapped[Decimal] = mapped_column(
        Numeric(14, 2),
        default=Decimal("0"),
        comment="Maximum credit limit"
    )
    credit_days: Mapped[int] = mapped_column(
        Integer,
        default=30,
        comment="Credit period in days"
    )
    credit_status: Mapped[str] = mapped_column(
        String(50),
        default="ACTIVE",
        nullable=False,
        comment="ACTIVE, ON_HOLD, BLOCKED, CLOSED"
    )
    outstanding_amount: Mapped[Decimal] = mapped_column(
        Numeric(14, 2),
        default=Decimal("0"),
        comment="Current outstanding"
    )
    overdue_amount: Mapped[Decimal] = mapped_column(
        Numeric(14, 2),
        default=Decimal("0"),
        comment="Overdue amount"
    )

    # Security Deposit
    security_deposit: Mapped[Decimal] = mapped_column(
        Numeric(14, 2),
        default=Decimal("0")
    )
    security_deposit_paid: Mapped[bool] = mapped_column(Boolean, default=False)

    # Assigned Warehouse
    default_warehouse_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("warehouses.id", ondelete="SET NULL"),
        nullable=True
    )

    # Sales Representative
    sales_rep_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        comment="Assigned sales representative"
    )
    area_sales_manager_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )

    # Agreement
    agreement_start_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    agreement_end_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    agreement_document_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # Documents
    gst_certificate_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    pan_card_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    shop_photo_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    cancelled_cheque_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # KYC Status
    kyc_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    kyc_verified_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    kyc_verified_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        nullable=True
    )

    # Performance
    total_orders: Mapped[int] = mapped_column(Integer, default=0)
    total_revenue: Mapped[Decimal] = mapped_column(
        Numeric(14, 2),
        default=Decimal("0")
    )
    last_order_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    average_order_value: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(12, 2),
        nullable=True
    )

    # Rating
    dealer_rating: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(3, 2),
        nullable=True,
        comment="Internal rating 1-5"
    )
    payment_rating: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(3, 2),
        nullable=True,
        comment="Payment behavior rating"
    )

    # Settings
    can_place_orders: Mapped[bool] = mapped_column(Boolean, default=True)
    receive_promotions: Mapped[bool] = mapped_column(Boolean, default=True)
    portal_access: Mapped[bool] = mapped_column(Boolean, default=True)

    # Remarks
    internal_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Timestamps
    onboarded_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
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
    parent_dealer: Mapped[Optional["Dealer"]] = relationship(
        "Dealer",
        remote_side=[id],
        backref="sub_dealers"
    )
    user: Mapped[Optional["User"]] = relationship("User", foreign_keys=[user_id])
    default_warehouse: Mapped[Optional["Warehouse"]] = relationship("Warehouse")
    pricing: Mapped[List["DealerPricing"]] = relationship(
        "DealerPricing",
        back_populates="dealer",
        cascade="all, delete-orphan"
    )
    credit_ledger: Mapped[List["DealerCreditLedger"]] = relationship(
        "DealerCreditLedger",
        back_populates="dealer",
        cascade="all, delete-orphan"
    )
    targets: Mapped[List["DealerTarget"]] = relationship(
        "DealerTarget",
        back_populates="dealer",
        cascade="all, delete-orphan"
    )
    orders: Mapped[List["Order"]] = relationship(
        "Order",
        back_populates="dealer"
    )

    @property
    def available_credit(self) -> Decimal:
        """Calculate available credit."""
        return max(Decimal("0"), self.credit_limit - self.outstanding_amount)

    @property
    def credit_utilization_percentage(self) -> Decimal:
        """Calculate credit utilization percentage."""
        if self.credit_limit > 0:
            return (self.outstanding_amount / self.credit_limit) * 100
        return Decimal("0")

    def __repr__(self) -> str:
        return f"<Dealer(code='{self.dealer_code}', name='{self.name}')>"


class DealerPricing(Base):
    """
    Dealer-specific product pricing.
    Supports different pricing for different dealers/tiers.
    """
    __tablename__ = "dealer_pricing"
    __table_args__ = (
        UniqueConstraint("dealer_id", "product_id", "variant_id", name="uq_dealer_product_pricing"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )

    dealer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("dealers.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("products.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    variant_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("product_variants.id", ondelete="CASCADE"),
        nullable=True
    )

    # Pricing
    mrp: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
        comment="Maximum Retail Price"
    )
    dealer_price: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
        comment="Price to dealer"
    )
    special_price: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(12, 2),
        nullable=True,
        comment="Special negotiated price"
    )

    # Margin
    margin_percentage: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(5, 2),
        nullable=True,
        comment="Dealer margin %"
    )
    minimum_margin: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(5, 2),
        nullable=True,
        comment="Minimum margin to maintain"
    )

    # MOQ
    moq: Mapped[int] = mapped_column(
        Integer,
        default=1,
        comment="Minimum Order Quantity"
    )

    # Validity
    effective_from: Mapped[date] = mapped_column(Date, nullable=False)
    effective_to: Mapped[Optional[date]] = mapped_column(Date, nullable=True)

    # Status
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
    dealer: Mapped["Dealer"] = relationship("Dealer", back_populates="pricing")
    product: Mapped["Product"] = relationship("Product")

    @property
    def dealer_margin(self) -> Decimal:
        """Calculate dealer margin."""
        if self.mrp > 0:
            return ((self.mrp - self.dealer_price) / self.mrp) * 100
        return Decimal("0")

    def __repr__(self) -> str:
        return f"<DealerPricing(dealer={self.dealer_id}, product={self.product_id})>"


class DealerTierPricing(Base):
    """
    Tier-based product pricing.
    Applies to all dealers of a specific tier.
    """
    __tablename__ = "dealer_tier_pricing"
    __table_args__ = (
        UniqueConstraint("tier", "product_id", "variant_id", name="uq_tier_product_pricing"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )

    tier: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
        comment="PLATINUM, GOLD, SILVER, BRONZE, STANDARD"
    )

    product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("products.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    variant_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("product_variants.id", ondelete="CASCADE"),
        nullable=True
    )

    # Discount from MRP
    discount_percentage: Mapped[Decimal] = mapped_column(
        Numeric(5, 2),
        nullable=False,
        comment="Discount % from MRP"
    )

    # Or fixed price
    fixed_price: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(12, 2),
        nullable=True,
        comment="Fixed dealer price (overrides discount)"
    )

    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    effective_from: Mapped[date] = mapped_column(Date, nullable=False)
    effective_to: Mapped[Optional[date]] = mapped_column(Date, nullable=True)

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
    product: Mapped["Product"] = relationship("Product")

    def __repr__(self) -> str:
        return f"<DealerTierPricing(tier='{self.tier}', product={self.product_id})>"


class DealerCreditLedger(Base):
    """
    Dealer credit transaction ledger.
    Maintains running balance for credit management.
    """
    __tablename__ = "dealer_credit_ledger"
    __table_args__ = (
        Index("ix_dealer_credit_ledger_date", "dealer_id", "transaction_date"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )

    dealer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("dealers.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Transaction Details
    transaction_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="INVOICE, PAYMENT, CREDIT_NOTE, DEBIT_NOTE, OPENING_BALANCE, ADJUSTMENT"
    )
    transaction_date: Mapped[date] = mapped_column(Date, nullable=False)
    due_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)

    # Reference
    reference_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="INVOICE, PAYMENT, CREDIT_NOTE, etc."
    )
    reference_number: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="Invoice/Receipt number"
    )
    reference_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        nullable=True
    )

    # Amounts
    debit_amount: Mapped[Decimal] = mapped_column(
        Numeric(14, 2),
        default=Decimal("0"),
        comment="Increases outstanding"
    )
    credit_amount: Mapped[Decimal] = mapped_column(
        Numeric(14, 2),
        default=Decimal("0"),
        comment="Decreases outstanding"
    )
    balance: Mapped[Decimal] = mapped_column(
        Numeric(14, 2),
        nullable=False,
        comment="Running balance after this transaction"
    )

    # Payment Details (for payment transactions)
    payment_mode: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    cheque_number: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    transaction_reference: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # Status
    is_settled: Mapped[bool] = mapped_column(Boolean, default=False)
    settled_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    days_overdue: Mapped[int] = mapped_column(Integer, default=0)

    # Remarks
    remarks: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    # Relationships
    dealer: Mapped["Dealer"] = relationship("Dealer", back_populates="credit_ledger")

    def __repr__(self) -> str:
        return f"<DealerCreditLedger(dealer={self.dealer_id}, ref='{self.reference_number}')>"


class DealerTarget(Base):
    """
    Dealer sales target and achievement tracking.
    Monthly/Quarterly/Annual targets.
    """
    __tablename__ = "dealer_targets"
    __table_args__ = (
        UniqueConstraint(
            "dealer_id", "target_period", "target_year", "target_month",
            name="uq_dealer_target"
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )

    dealer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("dealers.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Period
    target_period: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        comment="MONTHLY, QUARTERLY, ANNUAL"
    )
    target_year: Mapped[int] = mapped_column(Integer, nullable=False)
    target_month: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        comment="1-12 for monthly targets"
    )
    target_quarter: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        comment="1-4 for quarterly targets"
    )

    # Target Type
    target_type: Mapped[str] = mapped_column(
        String(30),
        default="REVENUE",
        comment="REVENUE, QUANTITY, BOTH"
    )

    # Category/Product specific (optional)
    category_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("categories.id", ondelete="SET NULL"),
        nullable=True
    )
    product_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("products.id", ondelete="SET NULL"),
        nullable=True
    )

    # Targets
    revenue_target: Mapped[Decimal] = mapped_column(
        Numeric(14, 2),
        default=Decimal("0"),
        comment="Revenue target in INR"
    )
    quantity_target: Mapped[int] = mapped_column(
        Integer,
        default=0,
        comment="Quantity target in units"
    )

    # Achievement
    revenue_achieved: Mapped[Decimal] = mapped_column(
        Numeric(14, 2),
        default=Decimal("0")
    )
    quantity_achieved: Mapped[int] = mapped_column(Integer, default=0)

    # Incentive
    incentive_percentage: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(5, 2),
        nullable=True,
        comment="Incentive % on achievement"
    )
    incentive_earned: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        default=Decimal("0")
    )
    is_incentive_paid: Mapped[bool] = mapped_column(Boolean, default=False)

    # Status
    is_finalized: Mapped[bool] = mapped_column(Boolean, default=False)

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
    dealer: Mapped["Dealer"] = relationship("Dealer", back_populates="targets")

    @property
    def revenue_achievement_percentage(self) -> Decimal:
        """Calculate revenue achievement percentage."""
        if self.revenue_target > 0:
            return (self.revenue_achieved / self.revenue_target) * 100
        return Decimal("0")

    @property
    def quantity_achievement_percentage(self) -> Decimal:
        """Calculate quantity achievement percentage."""
        if self.quantity_target > 0:
            return (Decimal(self.quantity_achieved) / Decimal(self.quantity_target)) * 100
        return Decimal("0")

    def __repr__(self) -> str:
        return f"<DealerTarget(dealer={self.dealer_id}, period='{self.target_period}')>"


class DealerScheme(Base):
    """
    Dealer schemes and promotions.
    Volume discounts, early payment, festive schemes.
    """
    __tablename__ = "dealer_schemes"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )

    # Scheme Identification
    scheme_code: Mapped[str] = mapped_column(
        String(30),
        unique=True,
        nullable=False,
        index=True
    )
    scheme_name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Type
    scheme_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="QUANTITY_DISCOUNT, SLAB_DISCOUNT, CASH_DISCOUNT, EARLY_PAYMENT, FESTIVE_SCHEME, TARGET_INCENTIVE, PRODUCT_COMBO, FOC"
    )

    # Validity
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Eligibility
    applicable_dealer_types: Mapped[Optional[dict]] = mapped_column(
        JSONB,
        nullable=True,
        comment="List of applicable dealer types"
    )
    applicable_tiers: Mapped[Optional[dict]] = mapped_column(
        JSONB,
        nullable=True,
        comment="List of applicable tiers"
    )
    applicable_regions: Mapped[Optional[dict]] = mapped_column(
        JSONB,
        nullable=True,
        comment="List of applicable regions"
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

    # Scheme Rules (JSONB structure depends on scheme_type)
    rules: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        comment="Scheme rules/slabs in JSONB"
    )
    # Example rules for QUANTITY_DISCOUNT:
    # {"buy_quantity": 10, "discount_percentage": 5}
    # Example rules for SLAB_DISCOUNT:
    # {"slabs": [{"min": 1, "max": 10, "discount": 5}, {"min": 11, "max": 50, "discount": 8}]}

    # Budget
    total_budget: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(14, 2),
        nullable=True,
        comment="Total scheme budget"
    )
    utilized_budget: Mapped[Decimal] = mapped_column(
        Numeric(14, 2),
        default=Decimal("0")
    )

    # Terms
    terms_and_conditions: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    can_combine: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        comment="Can combine with other schemes"
    )

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

    @property
    def is_valid(self) -> bool:
        """Check if scheme is currently valid."""
        today = date.today()
        return self.is_active and self.start_date <= today <= self.end_date

    @property
    def budget_remaining(self) -> Optional[Decimal]:
        """Calculate remaining budget."""
        if self.total_budget:
            return self.total_budget - self.utilized_budget
        return None

    def __repr__(self) -> str:
        return f"<DealerScheme(code='{self.scheme_code}', type='{self.scheme_type}')>"


class DealerSchemeApplication(Base):
    """
    Track scheme applications/utilization by dealers.
    """
    __tablename__ = "dealer_scheme_applications"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )

    scheme_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("dealer_schemes.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    dealer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("dealers.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Order Reference
    order_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("orders.id", ondelete="SET NULL"),
        nullable=True
    )

    # Application Details
    application_date: Mapped[date] = mapped_column(Date, nullable=False)
    order_value: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    discount_calculated: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
        comment="Discount amount calculated"
    )

    # Status
    is_approved: Mapped[bool] = mapped_column(Boolean, default=True)
    approved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    # Relationships
    scheme: Mapped["DealerScheme"] = relationship("DealerScheme")
    dealer: Mapped["Dealer"] = relationship("Dealer")

    def __repr__(self) -> str:
        return f"<DealerSchemeApplication(scheme={self.scheme_id}, dealer={self.dealer_id})>"


class ClaimType(str, Enum):
    """Dealer claim type."""
    PRODUCT_DEFECT = "PRODUCT_DEFECT"
    TRANSIT_DAMAGE = "TRANSIT_DAMAGE"
    QUANTITY_SHORT = "QUANTITY_SHORT"
    PRICING_ERROR = "PRICING_ERROR"
    SCHEME_DISPUTE = "SCHEME_DISPUTE"
    WARRANTY = "WARRANTY"


class ClaimStatus(str, Enum):
    """Dealer claim status."""
    SUBMITTED = "SUBMITTED"
    UNDER_REVIEW = "UNDER_REVIEW"
    APPROVED = "APPROVED"
    PARTIALLY_APPROVED = "PARTIALLY_APPROVED"
    REJECTED = "REJECTED"
    SETTLED = "SETTLED"


class ClaimResolution(str, Enum):
    """Claim resolution type."""
    REPLACEMENT = "REPLACEMENT"
    CREDIT_NOTE = "CREDIT_NOTE"
    REFUND = "REFUND"
    REPAIR = "REPAIR"


class OutletType(str, Enum):
    """Retailer outlet type."""
    KIRANA = "KIRANA"
    MODERN_TRADE = "MODERN_TRADE"
    SUPERMARKET = "SUPERMARKET"
    PHARMACY = "PHARMACY"
    HARDWARE = "HARDWARE"
    ELECTRONICS = "ELECTRONICS"
    GENERAL_STORE = "GENERAL_STORE"
    OTHER = "OTHER"


class OutletStatus(str, Enum):
    """Retailer outlet status."""
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    CLOSED = "CLOSED"


class BeatDay(str, Enum):
    """Beat day for retailer visits."""
    MONDAY = "MONDAY"
    TUESDAY = "TUESDAY"
    WEDNESDAY = "WEDNESDAY"
    THURSDAY = "THURSDAY"
    FRIDAY = "FRIDAY"
    SATURDAY = "SATURDAY"
    SUNDAY = "SUNDAY"


class DealerClaim(Base):
    """
    Dealer claims management.
    Handles product defects, transit damage, quantity shortages, pricing errors, etc.
    """
    __tablename__ = "dealer_claims"
    __table_args__ = (
        Index("ix_dealer_claims_dealer", "dealer_id", "status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )

    claim_number: Mapped[str] = mapped_column(
        String(30),
        unique=True,
        nullable=False,
        index=True,
        comment="Auto: CLM-YYYYMMDD-00001"
    )

    dealer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("dealers.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    claim_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="PRODUCT_DEFECT, TRANSIT_DAMAGE, QUANTITY_SHORT, PRICING_ERROR, SCHEME_DISPUTE, WARRANTY"
    )

    status: Mapped[str] = mapped_column(
        String(50),
        default="SUBMITTED",
        nullable=False,
        index=True,
        comment="SUBMITTED, UNDER_REVIEW, APPROVED, PARTIALLY_APPROVED, REJECTED, SETTLED"
    )

    # Related order (optional)
    order_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("orders.id", ondelete="SET NULL"),
        nullable=True
    )

    # Items in the claim
    items: Mapped[Optional[dict]] = mapped_column(
        JSONB,
        nullable=True,
        comment="[{product_id, product_name, quantity, issue_description}]"
    )

    # Evidence/attachments
    evidence_urls: Mapped[Optional[dict]] = mapped_column(
        JSONB,
        nullable=True,
        comment="List of photo/document URLs"
    )

    # Amounts
    amount_claimed: Mapped[Decimal] = mapped_column(
        Numeric(14, 2),
        nullable=False,
        comment="Total amount claimed"
    )
    amount_approved: Mapped[Decimal] = mapped_column(
        Numeric(14, 2),
        default=Decimal("0"),
        comment="Approved amount"
    )

    # Resolution
    resolution: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        comment="REPLACEMENT, CREDIT_NOTE, REFUND, REPAIR"
    )
    resolution_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Timestamps
    submitted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    settled_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Assignment
    assigned_to: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )

    # Audit
    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        nullable=True
    )
    remarks: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

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
    dealer: Mapped["Dealer"] = relationship("Dealer", foreign_keys=[dealer_id])

    def __repr__(self) -> str:
        return f"<DealerClaim(number='{self.claim_number}', type='{self.claim_type}')>"


class RetailerOutlet(Base):
    """
    Retailer outlets managed by dealers/distributors.
    Tracks the secondary sales network (dealer → retailer).
    """
    __tablename__ = "retailer_outlets"
    __table_args__ = (
        Index("ix_retailer_outlets_dealer", "dealer_id", "status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )

    outlet_code: Mapped[str] = mapped_column(
        String(30),
        unique=True,
        nullable=False,
        index=True,
        comment="Auto: RTL-00001"
    )

    # Parent distributor
    dealer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("dealers.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Outlet details
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    owner_name: Mapped[str] = mapped_column(String(200), nullable=False)
    outlet_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="KIRANA, MODERN_TRADE, SUPERMARKET, PHARMACY, HARDWARE, ELECTRONICS, GENERAL_STORE, OTHER"
    )

    # Contact
    phone: Mapped[str] = mapped_column(String(20), nullable=False)
    email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Address
    address_line1: Mapped[str] = mapped_column(String(255), nullable=False)
    city: Mapped[str] = mapped_column(String(100), nullable=False)
    state: Mapped[str] = mapped_column(String(100), nullable=False)
    pincode: Mapped[str] = mapped_column(String(10), nullable=False)

    # Geolocation
    latitude: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 7), nullable=True)
    longitude: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 7), nullable=True)

    # Beat planning
    beat_day: Mapped[Optional[str]] = mapped_column(
        String(20),
        nullable=True,
        comment="MONDAY..SUNDAY"
    )

    # Status
    status: Mapped[str] = mapped_column(
        String(20),
        default="ACTIVE",
        nullable=False,
        comment="ACTIVE, INACTIVE, CLOSED"
    )

    # Performance
    last_order_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    total_orders: Mapped[int] = mapped_column(Integer, default=0)
    total_revenue: Mapped[Decimal] = mapped_column(
        Numeric(14, 2),
        default=Decimal("0")
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
    dealer: Mapped["Dealer"] = relationship("Dealer", foreign_keys=[dealer_id])

    def __repr__(self) -> str:
        return f"<RetailerOutlet(code='{self.outlet_code}', name='{self.name}')>"
