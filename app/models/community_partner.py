"""Community Partner models for Community Sales Channel.

This module enables the community-driven sales model where anyone can become
a sales partner with zero investment, similar to Meesho's reseller model.

Key Features:
- Zero investment registration
- KYC-based verification
- Tiered commission structure
- Performance-based bonuses
- Referral program
- Training tracking
"""
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import TYPE_CHECKING, Optional, List

from sqlalchemy import (
    String, Boolean, DateTime, ForeignKey, Integer, Text,
    Numeric, Date, UniqueConstraint, Index
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.order import Order


# ==================== ENUMS (stored as VARCHAR) ====================

class PartnerStatus(str, Enum):
    """Partner registration status."""
    PENDING_KYC = "PENDING_KYC"          # Registered, awaiting KYC
    KYC_SUBMITTED = "KYC_SUBMITTED"      # KYC submitted, under review
    KYC_REJECTED = "KYC_REJECTED"        # KYC rejected, needs resubmission
    ACTIVE = "ACTIVE"                     # Fully verified, can sell
    SUSPENDED = "SUSPENDED"               # Temporarily suspended
    INACTIVE = "INACTIVE"                 # Voluntarily inactive
    BLOCKED = "BLOCKED"                   # Permanently blocked


class KYCStatus(str, Enum):
    """KYC verification status."""
    NOT_SUBMITTED = "NOT_SUBMITTED"
    PENDING = "PENDING"
    VERIFIED = "VERIFIED"
    REJECTED = "REJECTED"


class CommissionStatus(str, Enum):
    """Commission payout status."""
    PENDING = "PENDING"           # Order delivered, commission calculated
    APPROVED = "APPROVED"         # Approved for payout
    PROCESSING = "PROCESSING"     # Payout in progress
    PAID = "PAID"                 # Successfully paid
    FAILED = "FAILED"             # Payout failed
    CANCELLED = "CANCELLED"       # Cancelled (e.g., order returned)


class PayoutStatus(str, Enum):
    """Payout batch status."""
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    PARTIAL = "PARTIAL"


class PayoutMethod(str, Enum):
    """Payout method."""
    BANK_TRANSFER = "BANK_TRANSFER"
    UPI = "UPI"
    WALLET = "WALLET"


# ==================== MODELS ====================

class CommunityPartner(Base):
    """
    Community Partner registration and profile.

    Anyone can register as a community partner with zero investment.
    KYC verification is required before they can start earning commissions.
    """
    __tablename__ = "community_partners"
    __table_args__ = (
        Index('ix_community_partners_referral_code', 'referral_code'),
        Index('ix_community_partners_status', 'status'),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )

    # Unique partner code (e.g., AQP-12345)
    partner_code: Mapped[str] = mapped_column(
        String(20),
        unique=True,
        nullable=False,
        index=True,
        comment="Unique partner identifier"
    )

    # Linked user account (optional - created after registration)
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        unique=True
    )

    # Personal Information
    full_name: Mapped[str] = mapped_column(String(200), nullable=False)
    phone: Mapped[str] = mapped_column(
        String(15),
        unique=True,
        nullable=False,
        index=True
    )
    email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    date_of_birth: Mapped[Optional[datetime]] = mapped_column(Date, nullable=True)
    gender: Mapped[Optional[str]] = mapped_column(
        String(20),
        nullable=True,
        comment="MALE, FEMALE, OTHER"
    )
    profile_photo_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # Address
    address_line1: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    address_line2: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    city: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    district: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    state: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    pincode: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)

    # Partner Type/Category
    partner_type: Mapped[str] = mapped_column(
        String(50),
        default="INDIVIDUAL",
        comment="INDIVIDUAL, SERVICE_ENGINEER, RETAILER, INFLUENCER, STUDENT"
    )
    occupation: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # Status
    status: Mapped[str] = mapped_column(
        String(50),
        default="PENDING_KYC",
        nullable=False,
        comment="PENDING_KYC, KYC_SUBMITTED, KYC_REJECTED, ACTIVE, SUSPENDED, INACTIVE, BLOCKED"
    )

    # KYC Information
    kyc_status: Mapped[str] = mapped_column(
        String(50),
        default="NOT_SUBMITTED",
        comment="NOT_SUBMITTED, PENDING, VERIFIED, REJECTED"
    )

    # Aadhaar KYC
    aadhaar_number: Mapped[Optional[str]] = mapped_column(
        String(12),
        nullable=True,
        comment="Encrypted Aadhaar number"
    )
    aadhaar_name: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    aadhaar_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    aadhaar_front_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    aadhaar_back_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # PAN KYC
    pan_number: Mapped[Optional[str]] = mapped_column(
        String(10),
        nullable=True,
        comment="PAN number for TDS compliance"
    )
    pan_name: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    pan_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    pan_document_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # Bank Account Details
    bank_account_number: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    bank_ifsc: Mapped[Optional[str]] = mapped_column(String(11), nullable=True)
    bank_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    bank_branch: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    bank_account_holder_name: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    bank_verified: Mapped[bool] = mapped_column(Boolean, default=False)

    # UPI Details (Alternative payout)
    upi_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    upi_verified: Mapped[bool] = mapped_column(Boolean, default=False)

    # Referral System
    referral_code: Mapped[str] = mapped_column(
        String(20),
        unique=True,
        nullable=False,
        comment="Partner's own referral code to share"
    )
    referred_by_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("community_partners.id", ondelete="SET NULL"),
        nullable=True,
        comment="Partner who referred this person"
    )
    referred_by_code: Mapped[Optional[str]] = mapped_column(
        String(20),
        nullable=True,
        comment="Referral code used during registration"
    )

    # Commission Tier (linked to PartnerTier)
    tier_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("partner_tiers.id", ondelete="SET NULL"),
        nullable=True
    )

    # Performance Metrics (denormalized for quick access)
    total_sales_count: Mapped[int] = mapped_column(Integer, default=0)
    total_sales_value: Mapped[Decimal] = mapped_column(
        Numeric(15, 2),
        default=Decimal("0.00")
    )
    total_commission_earned: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        default=Decimal("0.00")
    )
    total_commission_paid: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        default=Decimal("0.00")
    )
    current_month_sales: Mapped[int] = mapped_column(Integer, default=0)
    current_month_value: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        default=Decimal("0.00")
    )

    # Wallet Balance (pending payouts)
    wallet_balance: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        default=Decimal("0.00"),
        comment="Available balance for withdrawal"
    )

    # Training & Certification
    training_completed: Mapped[bool] = mapped_column(Boolean, default=False)
    training_completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )
    certification_level: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        comment="BRONZE, SILVER, GOLD, PLATINUM"
    )

    # App & Device Info
    app_version: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    device_type: Mapped[Optional[str]] = mapped_column(
        String(20),
        nullable=True,
        comment="ANDROID, IOS, WEB"
    )
    fcm_token: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
        comment="Firebase Cloud Messaging token for push notifications"
    )
    last_login_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )

    # Verification & Audit
    kyc_verified_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )
    kyc_verified_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )
    kyc_rejection_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Extra Data
    extra_data: Mapped[Optional[dict]] = mapped_column(
        JSONB,
        nullable=True,
        comment="Additional partner data"
    )
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Timestamps
    registered_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )
    activated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="When partner became ACTIVE"
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
    user: Mapped[Optional["User"]] = relationship("User", foreign_keys=[user_id])
    tier: Mapped[Optional["PartnerTier"]] = relationship("PartnerTier", back_populates="partners")
    referred_by: Mapped[Optional["CommunityPartner"]] = relationship(
        "CommunityPartner",
        remote_side=[id],
        foreign_keys=[referred_by_id]
    )
    commissions: Mapped[List["PartnerCommission"]] = relationship(
        "PartnerCommission",
        back_populates="partner",
        cascade="all, delete-orphan"
    )
    payouts: Mapped[List["PartnerPayout"]] = relationship(
        "PartnerPayout",
        back_populates="partner",
        cascade="all, delete-orphan"
    )
    training_records: Mapped[List["PartnerTraining"]] = relationship(
        "PartnerTraining",
        back_populates="partner",
        cascade="all, delete-orphan"
    )

    @property
    def pending_commission(self) -> Decimal:
        """Calculate pending (unpaid) commission."""
        return self.total_commission_earned - self.total_commission_paid

    @property
    def is_kyc_complete(self) -> bool:
        """Check if KYC is fully verified."""
        return (
            self.aadhaar_verified and
            self.pan_verified and
            self.bank_verified
        )

    def __repr__(self) -> str:
        return f"<CommunityPartner(code={self.partner_code}, name={self.full_name})>"


class PartnerTier(Base):
    """
    Commission tier configuration.

    Defines tiered commission rates based on performance.
    Partners automatically move to higher tiers as they achieve targets.
    """
    __tablename__ = "partner_tiers"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )

    # Tier Identification
    code: Mapped[str] = mapped_column(
        String(20),
        unique=True,
        nullable=False,
        comment="Tier code: BRONZE, SILVER, GOLD, PLATINUM"
    )
    name: Mapped[str] = mapped_column(String(50), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Display
    badge_color: Mapped[Optional[str]] = mapped_column(
        String(20),
        nullable=True,
        comment="Hex color for badge"
    )
    badge_icon_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # Tier Level (for ordering)
    level: Mapped[int] = mapped_column(
        Integer,
        default=1,
        comment="1=lowest, higher=better"
    )

    # Qualification Criteria (monthly)
    min_monthly_sales: Mapped[int] = mapped_column(
        Integer,
        default=0,
        comment="Minimum sales count to qualify"
    )
    max_monthly_sales: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        comment="Maximum sales for this tier (NULL=unlimited)"
    )
    min_monthly_value: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        default=Decimal("0.00"),
        comment="Minimum sales value to qualify"
    )

    # Commission Rates
    commission_percentage: Mapped[Decimal] = mapped_column(
        Numeric(5, 2),
        nullable=False,
        comment="Base commission percentage"
    )
    bonus_percentage: Mapped[Decimal] = mapped_column(
        Numeric(5, 2),
        default=Decimal("0.00"),
        comment="Additional bonus percentage"
    )

    # Fixed Bonuses
    milestone_bonus: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        default=Decimal("0.00"),
        comment="One-time bonus when reaching this tier"
    )

    # Referral Commission
    referral_bonus: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        default=Decimal("0.00"),
        comment="Bonus per successful referral"
    )

    # Benefits (JSONB for flexibility)
    benefits: Mapped[Optional[dict]] = mapped_column(
        JSONB,
        nullable=True,
        comment="Additional tier benefits as JSON"
    )

    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_default: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        comment="Default tier for new partners"
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
    partners: Mapped[List["CommunityPartner"]] = relationship(
        "CommunityPartner",
        back_populates="tier"
    )

    def __repr__(self) -> str:
        return f"<PartnerTier(code={self.code}, commission={self.commission_percentage}%)>"


class PartnerCommission(Base):
    """
    Commission record for each sale.

    Tracks commission for every order attributed to a partner.
    Commission is calculated when order is delivered.
    """
    __tablename__ = "partner_commissions"
    __table_args__ = (
        UniqueConstraint("partner_id", "order_id", name="uq_partner_order_commission"),
        Index('ix_partner_commissions_status', 'status'),
        Index('ix_partner_commissions_created', 'created_at'),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )

    # Partner & Order Reference
    partner_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("community_partners.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    order_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("orders.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Order Details (denormalized for reporting)
    order_number: Mapped[str] = mapped_column(String(50), nullable=False)
    order_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    order_amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
        comment="Order total amount"
    )
    order_items_count: Mapped[int] = mapped_column(Integer, default=1)

    # Commission Calculation
    commission_rate: Mapped[Decimal] = mapped_column(
        Numeric(5, 2),
        nullable=False,
        comment="Commission percentage applied"
    )
    commission_amount: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        nullable=False,
        comment="Calculated commission"
    )
    bonus_amount: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        default=Decimal("0.00"),
        comment="Additional bonus (milestone, etc.)"
    )
    total_earnings: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        nullable=False,
        comment="commission_amount + bonus_amount"
    )

    # TDS Deduction (if applicable)
    tds_rate: Mapped[Decimal] = mapped_column(
        Numeric(5, 2),
        default=Decimal("0.00"),
        comment="TDS percentage (5% if PAN provided, 20% otherwise)"
    )
    tds_amount: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        default=Decimal("0.00")
    )
    net_earnings: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        nullable=False,
        comment="total_earnings - tds_amount"
    )

    # Tier at time of commission
    tier_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("partner_tiers.id", ondelete="SET NULL"),
        nullable=True
    )
    tier_code: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)

    # Status
    status: Mapped[str] = mapped_column(
        String(50),
        default="PENDING",
        nullable=False,
        comment="PENDING, APPROVED, PROCESSING, PAID, FAILED, CANCELLED"
    )

    # Payout Reference (when paid)
    payout_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("partner_payouts.id", ondelete="SET NULL"),
        nullable=True
    )

    # Status History
    approved_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )
    paid_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )
    cancelled_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )
    cancellation_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

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
    partner: Mapped["CommunityPartner"] = relationship(
        "CommunityPartner",
        back_populates="commissions"
    )
    order: Mapped["Order"] = relationship("Order")
    tier: Mapped[Optional["PartnerTier"]] = relationship("PartnerTier")
    payout: Mapped[Optional["PartnerPayout"]] = relationship(
        "PartnerPayout",
        back_populates="commissions"
    )

    def __repr__(self) -> str:
        return f"<PartnerCommission(partner={self.partner_id}, order={self.order_number}, amount={self.net_earnings})>"


class PartnerPayout(Base):
    """
    Payout record for commission disbursement.

    Batches multiple commissions into a single payout.
    Supports bank transfer and UPI payouts.
    """
    __tablename__ = "partner_payouts"
    __table_args__ = (
        Index('ix_partner_payouts_status', 'status'),
        Index('ix_partner_payouts_created', 'created_at'),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )

    # Payout Reference
    payout_number: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        nullable=False,
        comment="Unique payout reference"
    )

    # Partner
    partner_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("community_partners.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Payout Details
    gross_amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
        comment="Total commission before deductions"
    )
    tds_amount: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        default=Decimal("0.00"),
        comment="TDS deducted"
    )
    other_deductions: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        default=Decimal("0.00")
    )
    net_amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
        comment="Amount to be paid"
    )

    # Payout Method
    payout_method: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="BANK_TRANSFER, UPI, WALLET"
    )

    # Bank Details (snapshot at time of payout)
    bank_account_number: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    bank_ifsc: Mapped[Optional[str]] = mapped_column(String(11), nullable=True)
    bank_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    upi_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # Status
    status: Mapped[str] = mapped_column(
        String(50),
        default="PENDING",
        nullable=False,
        comment="PENDING, PROCESSING, COMPLETED, FAILED, PARTIAL"
    )

    # Payment Gateway Reference
    payment_gateway: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        comment="RAZORPAY, CASHFREE, etc."
    )
    gateway_transaction_id: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True
    )
    gateway_response: Mapped[Optional[dict]] = mapped_column(
        JSONB,
        nullable=True,
        comment="Raw gateway response"
    )

    # Processing Details
    initiated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )
    processed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )
    failed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )
    failure_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    retry_count: Mapped[int] = mapped_column(Integer, default=0)

    # Audit
    initiated_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )
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
    partner: Mapped["CommunityPartner"] = relationship(
        "CommunityPartner",
        back_populates="payouts"
    )
    commissions: Mapped[List["PartnerCommission"]] = relationship(
        "PartnerCommission",
        back_populates="payout"
    )

    def __repr__(self) -> str:
        return f"<PartnerPayout(number={self.payout_number}, amount={self.net_amount}, status={self.status})>"


class PartnerReferral(Base):
    """
    Tracks partner referrals.

    When a partner refers someone who successfully registers and makes sales,
    the referrer earns a bonus.
    """
    __tablename__ = "partner_referrals"
    __table_args__ = (
        UniqueConstraint("referrer_id", "referred_id", name="uq_partner_referral"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )

    # Referrer (existing partner)
    referrer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("community_partners.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Referred (new partner)
    referred_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("community_partners.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Referral Code Used
    referral_code: Mapped[str] = mapped_column(String(20), nullable=False)

    # Status
    status: Mapped[str] = mapped_column(
        String(50),
        default="PENDING",
        comment="PENDING, ACTIVATED, QUALIFIED, BONUS_PAID, EXPIRED"
    )

    # Qualification (referred partner must complete certain actions)
    referred_activated: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        comment="Referred partner completed KYC"
    )
    referred_first_sale: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        comment="Referred partner made first sale"
    )
    referred_qualified: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        comment="Referred partner met qualification criteria"
    )
    qualification_date: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )

    # Bonus
    bonus_amount: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        default=Decimal("0.00")
    )
    bonus_paid: Mapped[bool] = mapped_column(Boolean, default=False)
    bonus_paid_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )
    payout_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("partner_payouts.id", ondelete="SET NULL"),
        nullable=True
    )

    # Timestamps
    referred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
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
    referrer: Mapped["CommunityPartner"] = relationship(
        "CommunityPartner",
        foreign_keys=[referrer_id]
    )
    referred: Mapped["CommunityPartner"] = relationship(
        "CommunityPartner",
        foreign_keys=[referred_id]
    )

    def __repr__(self) -> str:
        return f"<PartnerReferral(referrer={self.referrer_id}, referred={self.referred_id})>"


class PartnerTraining(Base):
    """
    Training and certification tracking.

    Partners must complete training before they can start selling.
    Additional certifications unlock higher tiers and benefits.
    """
    __tablename__ = "partner_training"
    __table_args__ = (
        UniqueConstraint("partner_id", "module_code", name="uq_partner_training_module"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )

    # Partner
    partner_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("community_partners.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Training Module
    module_code: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="ONBOARDING, PRODUCT_101, SALES_BASICS, ADVANCED_SALES"
    )
    module_name: Mapped[str] = mapped_column(String(200), nullable=False)
    module_type: Mapped[str] = mapped_column(
        String(50),
        default="VIDEO",
        comment="VIDEO, QUIZ, DOCUMENT, WEBINAR"
    )

    # Progress
    status: Mapped[str] = mapped_column(
        String(50),
        default="NOT_STARTED",
        comment="NOT_STARTED, IN_PROGRESS, COMPLETED, FAILED"
    )
    progress_percentage: Mapped[int] = mapped_column(Integer, default=0)

    # Quiz/Assessment
    quiz_score: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        comment="Score out of 100"
    )
    quiz_passed: Mapped[bool] = mapped_column(Boolean, default=False)
    attempts: Mapped[int] = mapped_column(Integer, default=0)

    # Certification
    certificate_issued: Mapped[bool] = mapped_column(Boolean, default=False)
    certificate_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    certificate_number: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    # Timestamps
    started_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )
    expires_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Certification expiry date"
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
    partner: Mapped["CommunityPartner"] = relationship(
        "CommunityPartner",
        back_populates="training_records"
    )

    def __repr__(self) -> str:
        return f"<PartnerTraining(partner={self.partner_id}, module={self.module_code}, status={self.status})>"


class PartnerOrder(Base):
    """
    Links orders to community partners for attribution.

    Tracks which partner referred/generated each order.
    """
    __tablename__ = "partner_orders"
    __table_args__ = (
        UniqueConstraint("order_id", name="uq_partner_order"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )

    # Partner & Order
    partner_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("community_partners.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    order_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("orders.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True
    )

    # Attribution Source
    attribution_source: Mapped[str] = mapped_column(
        String(50),
        default="PARTNER_LINK",
        comment="PARTNER_LINK, PARTNER_CODE, QR_CODE, MANUAL"
    )
    partner_code_used: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    referral_link: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # Commission Reference
    commission_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("partner_commissions.id", ondelete="SET NULL"),
        nullable=True
    )

    # Timestamps
    attributed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    # Relationships
    partner: Mapped["CommunityPartner"] = relationship("CommunityPartner")
    order: Mapped["Order"] = relationship("Order")

    def __repr__(self) -> str:
        return f"<PartnerOrder(partner={self.partner_id}, order={self.order_id})>"
