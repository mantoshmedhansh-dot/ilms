"""Unified Promotion, Scheme & Commission models for ALL sales channels.

Supports:
- Channel-wise promotions (D2C, Marketplace, Dealer, etc.)
- Customer-facing offers (Discounts, Cashback, BOGO)
- Trade schemes (Dealer/Distributor incentives)
- Sales team commissions
- Affiliate/Influencer programs
- Loyalty & Referral rewards
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
    from app.models.channel import SalesChannel
    from app.models.dealer import Dealer
    from app.models.order import Order


# ==================== ENUMS ====================

class PromotionType(str, Enum):
    """Type of promotion/scheme."""
    # Customer-facing (B2C)
    PERCENTAGE_DISCOUNT = "PERCENTAGE_DISCOUNT"
    FLAT_DISCOUNT = "FLAT_DISCOUNT"
    BOGO = "BOGO"                           # Buy One Get One
    BUNDLE = "BUNDLE"                        # Product bundle
    CASHBACK = "CASHBACK"
    FREE_GIFT = "FREE_GIFT"
    FREE_SHIPPING = "FREE_SHIPPING"
    FLASH_SALE = "FLASH_SALE"
    SEASONAL = "SEASONAL"                    # Diwali, Summer, etc.
    FIRST_ORDER = "FIRST_ORDER"
    LOYALTY_REWARD = "LOYALTY_REWARD"
    REFERRAL_REWARD = "REFERRAL_REWARD"
    EXCHANGE_OFFER = "EXCHANGE_OFFER"        # Old product exchange
    EMI_DISCOUNT = "EMI_DISCOUNT"            # No-cost EMI subsidy
    BANK_OFFER = "BANK_OFFER"                # Bank card offers

    # Trade/B2B schemes
    TRADE_DISCOUNT = "TRADE_DISCOUNT"        # Dealer trade discount
    VOLUME_REBATE = "VOLUME_REBATE"          # Volume-based rebate
    EARLY_PAYMENT = "EARLY_PAYMENT"          # Early payment discount
    TARGET_INCENTIVE = "TARGET_INCENTIVE"    # Target achievement
    DISPLAY_INCENTIVE = "DISPLAY_INCENTIVE"  # Shop display incentive
    LAUNCH_SCHEME = "LAUNCH_SCHEME"          # New product launch
    CLEARANCE = "CLEARANCE"                  # Stock clearance
    FOC = "FOC"                              # Free of cost goods


class PromotionScope(str, Enum):
    """Scope of promotion."""
    ALL_PRODUCTS = "ALL_PRODUCTS"
    SPECIFIC_PRODUCTS = "SPECIFIC_PRODUCTS"
    SPECIFIC_CATEGORIES = "SPECIFIC_CATEGORIES"
    SPECIFIC_BRANDS = "SPECIFIC_BRANDS"
    CART_LEVEL = "CART_LEVEL"                # Applies to cart total
    SHIPPING = "SHIPPING"


class DiscountApplication(str, Enum):
    """How discount is applied."""
    ON_MRP = "ON_MRP"
    ON_SELLING_PRICE = "ON_SELLING_PRICE"
    ON_CART_TOTAL = "ON_CART_TOTAL"
    ON_SHIPPING = "ON_SHIPPING"
    POST_PURCHASE = "POST_PURCHASE"          # Cashback after delivery


class PromotionStatus(str, Enum):
    """Promotion status."""
    DRAFT = "DRAFT"
    PENDING_APPROVAL = "PENDING_APPROVAL"
    APPROVED = "APPROVED"
    ACTIVE = "ACTIVE"
    PAUSED = "PAUSED"
    EXPIRED = "EXPIRED"
    CANCELLED = "CANCELLED"


class CommissionBeneficiary(str, Enum):
    """Who earns commission."""
    SALES_EXECUTIVE = "SALES_EXECUTIVE"
    AREA_MANAGER = "AREA_MANAGER"
    REGIONAL_MANAGER = "REGIONAL_MANAGER"
    ZONAL_HEAD = "ZONAL_HEAD"
    DEALER = "DEALER"
    DISTRIBUTOR = "DISTRIBUTOR"
    RETAILER = "RETAILER"
    FRANCHISE = "FRANCHISE"
    AFFILIATE = "AFFILIATE"
    INFLUENCER = "INFLUENCER"
    REFERRER = "REFERRER"                    # Customer referral
    SERVICE_PARTNER = "SERVICE_PARTNER"
    INSTALLATION_TEAM = "INSTALLATION_TEAM"


# ==================== PROMOTION MASTER ====================

class Promotion(Base):
    """
    Unified Promotion/Scheme master.
    Applicable across all sales channels.
    """
    __tablename__ = "promotions"
    __table_args__ = (
        Index("ix_promotions_dates", "start_date", "end_date"),
        Index("ix_promotions_status", "status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )

    # Identification
    promo_code: Mapped[str] = mapped_column(
        String(30),
        unique=True,
        nullable=False,
        index=True,
        comment="Unique promotion code"
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    short_description: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
        comment="For display on product page"
    )

    # Type & Scope
    promotion_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
        comment="PERCENTAGE_DISCOUNT, FLAT_DISCOUNT, BOGO, BUNDLE, CASHBACK, FREE_GIFT, FREE_SHIPPING, FLASH_SALE, SEASONAL, FIRST_ORDER, LOYALTY_REWARD, REFERRAL_REWARD, EXCHANGE_OFFER, EMI_DISCOUNT, BANK_OFFER, TRADE_DISCOUNT, VOLUME_REBATE, EARLY_PAYMENT, TARGET_INCENTIVE, DISPLAY_INCENTIVE, LAUNCH_SCHEME, CLEARANCE, FOC"
    )
    promotion_scope: Mapped[str] = mapped_column(
        String(50),
        default="ALL_PRODUCTS",
        nullable=False,
        comment="ALL_PRODUCTS, SPECIFIC_PRODUCTS, SPECIFIC_CATEGORIES, SPECIFIC_BRANDS, CART_LEVEL, SHIPPING"
    )
    discount_application: Mapped[str] = mapped_column(
        String(50),
        default="ON_SELLING_PRICE",
        nullable=False,
        comment="ON_MRP, ON_SELLING_PRICE, ON_CART_TOTAL, ON_SHIPPING, POST_PURCHASE"
    )

    # Status
    status: Mapped[str] = mapped_column(
        String(50),
        default="DRAFT",
        nullable=False,
        comment="DRAFT, PENDING_APPROVAL, APPROVED, ACTIVE, PAUSED, EXPIRED, CANCELLED"
    )

    # Validity
    start_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    end_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    is_recurring: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        comment="For daily/weekly flash sales"
    )
    recurring_schedule: Mapped[Optional[dict]] = mapped_column(
        JSONB,
        nullable=True,
        comment="Cron-like schedule for recurring promos"
    )

    # ==================== CHANNEL APPLICABILITY ====================
    # Which channels this promotion applies to

    applicable_channels: Mapped[Optional[dict]] = mapped_column(
        JSONB,
        nullable=True,
        comment="List of channel codes, null = all channels"
    )
    # Example: ["D2C_WEB", "D2C_APP", "AMAZON_IN"]

    excluded_channels: Mapped[Optional[dict]] = mapped_column(
        JSONB,
        nullable=True,
        comment="Channels to exclude"
    )

    # Channel-specific flags
    is_d2c: Mapped[bool] = mapped_column(Boolean, default=True)
    is_marketplace: Mapped[bool] = mapped_column(Boolean, default=False)
    is_dealer: Mapped[bool] = mapped_column(Boolean, default=False)
    is_retail: Mapped[bool] = mapped_column(Boolean, default=False)
    is_corporate: Mapped[bool] = mapped_column(Boolean, default=False)

    # ==================== DISCOUNT CONFIGURATION ====================

    # Percentage discount
    discount_percentage: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(5, 2),
        nullable=True,
        comment="Discount % (e.g., 10.00 for 10%)"
    )
    max_discount_amount: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(12, 2),
        nullable=True,
        comment="Cap on discount amount"
    )

    # Flat discount
    discount_amount: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(12, 2),
        nullable=True,
        comment="Flat discount amount"
    )

    # Cashback
    cashback_percentage: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(5, 2),
        nullable=True
    )
    cashback_amount: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(12, 2),
        nullable=True
    )
    max_cashback: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(12, 2),
        nullable=True
    )

    # BOGO / Bundle
    buy_quantity: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        comment="Buy X quantity"
    )
    get_quantity: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        comment="Get Y free/discounted"
    )
    get_discount_percentage: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(5, 2),
        nullable=True,
        comment="Discount on 'get' items (100 = free)"
    )

    # ==================== ELIGIBILITY RULES ====================

    # Minimum requirements
    min_order_value: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(12, 2),
        nullable=True,
        comment="Minimum cart/order value"
    )
    min_quantity: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        comment="Minimum product quantity"
    )

    # Product/Category applicability
    applicable_products: Mapped[Optional[dict]] = mapped_column(
        JSONB,
        nullable=True,
        comment="List of product IDs"
    )
    applicable_categories: Mapped[Optional[dict]] = mapped_column(
        JSONB,
        nullable=True,
        comment="List of category IDs"
    )
    applicable_brands: Mapped[Optional[dict]] = mapped_column(
        JSONB,
        nullable=True,
        comment="List of brand IDs"
    )
    excluded_products: Mapped[Optional[dict]] = mapped_column(
        JSONB,
        nullable=True
    )
    excluded_categories: Mapped[Optional[dict]] = mapped_column(
        JSONB,
        nullable=True
    )

    # Customer eligibility
    customer_segments: Mapped[Optional[dict]] = mapped_column(
        JSONB,
        nullable=True,
        comment="NEW, RETURNING, VIP, etc."
    )
    applicable_regions: Mapped[Optional[dict]] = mapped_column(
        JSONB,
        nullable=True,
        comment="State/region codes"
    )
    applicable_pincodes: Mapped[Optional[dict]] = mapped_column(
        JSONB,
        nullable=True
    )

    # Dealer/Partner eligibility (for B2B)
    applicable_dealer_types: Mapped[Optional[dict]] = mapped_column(
        JSONB,
        nullable=True
    )
    applicable_dealer_tiers: Mapped[Optional[dict]] = mapped_column(
        JSONB,
        nullable=True
    )
    applicable_dealers: Mapped[Optional[dict]] = mapped_column(
        JSONB,
        nullable=True,
        comment="Specific dealer IDs"
    )

    # Payment method restrictions
    applicable_payment_methods: Mapped[Optional[dict]] = mapped_column(
        JSONB,
        nullable=True,
        comment="CREDIT_CARD, UPI, EMI, etc."
    )
    applicable_banks: Mapped[Optional[dict]] = mapped_column(
        JSONB,
        nullable=True,
        comment="For bank offers"
    )
    applicable_card_types: Mapped[Optional[dict]] = mapped_column(
        JSONB,
        nullable=True,
        comment="VISA, MASTERCARD, RUPAY"
    )

    # ==================== USAGE LIMITS ====================

    total_usage_limit: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        comment="Total times promo can be used"
    )
    per_customer_limit: Mapped[int] = mapped_column(
        Integer,
        default=1,
        comment="Uses per customer"
    )
    per_order_limit: Mapped[int] = mapped_column(
        Integer,
        default=1,
        comment="Max times applicable per order"
    )
    current_usage_count: Mapped[int] = mapped_column(
        Integer,
        default=0
    )

    # Budget
    total_budget: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(14, 2),
        nullable=True,
        comment="Total discount budget"
    )
    utilized_budget: Mapped[Decimal] = mapped_column(
        Numeric(14, 2),
        default=Decimal("0")
    )

    # ==================== DISPLAY & MARKETING ====================

    display_priority: Mapped[int] = mapped_column(
        Integer,
        default=0,
        comment="Higher = shown first"
    )
    is_featured: Mapped[bool] = mapped_column(Boolean, default=False)
    is_stackable: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        comment="Can combine with other promos"
    )
    show_on_product_page: Mapped[bool] = mapped_column(Boolean, default=True)
    show_on_checkout: Mapped[bool] = mapped_column(Boolean, default=True)
    requires_coupon_code: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        comment="Customer must enter code"
    )
    coupon_code: Mapped[Optional[str]] = mapped_column(
        String(30),
        nullable=True,
        index=True,
        comment="Customer-facing coupon code"
    )
    banner_image_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    terms_and_conditions: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # ==================== AUDIT ====================

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
    usage_history: Mapped[List["PromotionUsage"]] = relationship(
        "PromotionUsage",
        back_populates="promotion",
        cascade="all, delete-orphan"
    )

    @property
    def is_active(self) -> bool:
        """Check if promotion is currently active."""
        now = datetime.now(timezone.utc)
        return (
            self.status == PromotionStatus.ACTIVE and
            self.start_date <= now <= self.end_date and
            (self.total_usage_limit is None or self.current_usage_count < self.total_usage_limit) and
            (self.total_budget is None or self.utilized_budget < self.total_budget)
        )

    @property
    def budget_remaining(self) -> Optional[Decimal]:
        """Get remaining budget."""
        if self.total_budget:
            return self.total_budget - self.utilized_budget
        return None

    def __repr__(self) -> str:
        return f"<Promotion(code='{self.promo_code}', type='{self.promotion_type}')>"


class PromotionUsage(Base):
    """
    Track promotion usage per order/customer.
    """
    __tablename__ = "promotion_usage"
    __table_args__ = (
        Index("ix_promotion_usage_customer", "promotion_id", "customer_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )

    promotion_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("promotions.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Order/Customer
    order_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("orders.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    customer_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    dealer_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("dealers.id", ondelete="SET NULL"),
        nullable=True
    )

    # Channel
    channel_code: Mapped[str] = mapped_column(String(30), nullable=False)

    # Usage Details
    usage_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    order_value: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    discount_applied: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    cashback_earned: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        default=Decimal("0")
    )

    # Status
    is_reversed: Mapped[bool] = mapped_column(Boolean, default=False)
    reversed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    reversal_reason: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    # Relationships
    promotion: Mapped["Promotion"] = relationship(
        "Promotion",
        back_populates="usage_history"
    )

    def __repr__(self) -> str:
        return f"<PromotionUsage(promo={self.promotion_id}, order={self.order_id})>"


# ==================== CHANNEL COMMISSION ====================

class ChannelCommissionPlan(Base):
    """
    Commission plan per sales channel.
    Different commission structures for D2C, Marketplace, Dealer, etc.
    """
    __tablename__ = "channel_commission_plans"
    __table_args__ = (
        UniqueConstraint("channel_code", "beneficiary_type", "name", name="uq_channel_commission_plan"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )

    # Identification
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Channel
    channel_code: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        index=True,
        comment="Channel code or 'ALL' for all channels"
    )

    # Who earns
    beneficiary_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
        comment="SALES_EXECUTIVE, AREA_MANAGER, REGIONAL_MANAGER, ZONAL_HEAD, DEALER, DISTRIBUTOR, RETAILER, FRANCHISE, AFFILIATE, INFLUENCER, REFERRER, SERVICE_PARTNER, INSTALLATION_TEAM"
    )

    # Validity
    effective_from: Mapped[date] = mapped_column(Date, nullable=False)
    effective_to: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Commission Structure
    commission_type: Mapped[str] = mapped_column(
        String(30),
        default="PERCENTAGE",
        comment="PERCENTAGE, FIXED, SLAB, TIERED"
    )
    base_rate: Mapped[Decimal] = mapped_column(
        Numeric(5, 2),
        default=Decimal("0"),
        comment="Base commission rate %"
    )
    fixed_amount: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(10, 2),
        nullable=True,
        comment="Fixed amount per order/unit"
    )

    # Slab configuration
    rate_slabs: Mapped[Optional[dict]] = mapped_column(
        JSONB,
        nullable=True,
        comment="Volume/value based slabs"
    )
    # Example: [{"min": 0, "max": 100000, "rate": 2}, {"min": 100001, "rate": 3}]

    # Calculation basis
    calculate_on: Mapped[str] = mapped_column(
        String(30),
        default="NET_REVENUE",
        comment="NET_REVENUE, GROSS_REVENUE, MARGIN, QUANTITY"
    )
    exclude_tax: Mapped[bool] = mapped_column(Boolean, default=True)
    exclude_shipping: Mapped[bool] = mapped_column(Boolean, default=True)
    exclude_discounts: Mapped[bool] = mapped_column(Boolean, default=False)

    # Eligibility
    min_order_value: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(12, 2),
        nullable=True
    )
    applicable_categories: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    applicable_products: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    excluded_products: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)

    # Payout Rules
    payout_frequency: Mapped[str] = mapped_column(
        String(20),
        default="MONTHLY",
        comment="WEEKLY, FORTNIGHTLY, MONTHLY"
    )
    payout_after_days: Mapped[int] = mapped_column(
        Integer,
        default=30,
        comment="Days after order completion"
    )
    min_payout_amount: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        default=Decimal("100"),
        comment="Minimum amount to trigger payout"
    )
    clawback_days: Mapped[int] = mapped_column(
        Integer,
        default=30,
        comment="Clawback period for returns"
    )

    # TDS
    tds_applicable: Mapped[bool] = mapped_column(Boolean, default=True)
    tds_rate: Mapped[Decimal] = mapped_column(
        Numeric(5, 2),
        default=Decimal("10")
    )
    tds_section: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)

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
    category_rates: Mapped[List["ChannelCommissionCategoryRate"]] = relationship(
        "ChannelCommissionCategoryRate",
        back_populates="plan",
        cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<ChannelCommissionPlan(channel='{self.channel_code}', type='{self.beneficiary_type}')>"


class ChannelCommissionCategoryRate(Base):
    """
    Category-wise commission rates per channel plan.
    """
    __tablename__ = "channel_commission_category_rates"
    __table_args__ = (
        UniqueConstraint("plan_id", "category_id", name="uq_channel_commission_category"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )

    plan_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("channel_commission_plans.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    category_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("categories.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Rate override
    commission_rate: Mapped[Decimal] = mapped_column(
        Numeric(5, 2),
        nullable=False
    )
    fixed_amount: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(10, 2),
        nullable=True
    )

    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    # Relationships
    plan: Mapped["ChannelCommissionPlan"] = relationship(
        "ChannelCommissionPlan",
        back_populates="category_rates"
    )

    def __repr__(self) -> str:
        return f"<ChannelCommissionCategoryRate(plan={self.plan_id}, category={self.category_id})>"


class ChannelCommissionEarning(Base):
    """
    Individual commission earnings per order.
    """
    __tablename__ = "channel_commission_earnings"
    __table_args__ = (
        Index("ix_channel_commission_earnings_date", "earning_date"),
        Index("ix_channel_commission_earnings_beneficiary", "beneficiary_type", "beneficiary_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )

    # Plan & Channel
    plan_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("channel_commission_plans.id", ondelete="RESTRICT"),
        nullable=False,
        index=True
    )
    channel_code: Mapped[str] = mapped_column(String(30), nullable=False, index=True)

    # Beneficiary
    beneficiary_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="SALES_EXECUTIVE, AREA_MANAGER, REGIONAL_MANAGER, ZONAL_HEAD, DEALER, DISTRIBUTOR, RETAILER, FRANCHISE, AFFILIATE, INFLUENCER, REFERRER, SERVICE_PARTNER, INSTALLATION_TEAM"
    )
    beneficiary_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
        index=True,
        comment="User ID, Dealer ID, etc."
    )
    beneficiary_name: Mapped[str] = mapped_column(String(200), nullable=False)

    # Order Reference
    order_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("orders.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    order_number: Mapped[str] = mapped_column(String(50), nullable=False)
    order_date: Mapped[date] = mapped_column(Date, nullable=False)

    # Earning Details
    earning_date: Mapped[date] = mapped_column(Date, nullable=False)
    order_value: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    commission_base: Mapped[Decimal] = mapped_column(
        Numeric(14, 2),
        nullable=False,
        comment="Value on which commission calculated"
    )
    commission_rate: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)
    commission_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)

    # Deductions
    tds_rate: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=Decimal("0"))
    tds_amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=Decimal("0"))
    other_deductions: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=Decimal("0"))
    net_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)

    # Status
    status: Mapped[str] = mapped_column(
        String(30),
        default="PENDING",
        comment="PENDING, ELIGIBLE, APPROVED, PAID, CLAWBACK"
    )
    eligible_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    is_paid: Mapped[bool] = mapped_column(Boolean, default=False)
    paid_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    payout_reference: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    # Clawback
    is_clawed_back: Mapped[bool] = mapped_column(Boolean, default=False)
    clawback_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    clawback_reason: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    clawback_amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        default=Decimal("0")
    )

    # Hierarchy (for multi-level commissions)
    parent_earning_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("channel_commission_earnings.id", ondelete="SET NULL"),
        nullable=True
    )
    level: Mapped[int] = mapped_column(Integer, default=1)

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

    def __repr__(self) -> str:
        return f"<ChannelCommissionEarning(order={self.order_number}, amount={self.commission_amount})>"


# ==================== LOYALTY & REFERRAL ====================

class LoyaltyProgram(Base):
    """
    Customer loyalty program configuration.
    """
    __tablename__ = "loyalty_programs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Applicable channels
    applicable_channels: Mapped[Optional[dict]] = mapped_column(
        JSONB,
        nullable=True,
        comment="Channel codes, null = all"
    )

    # Points configuration
    points_per_rupee: Mapped[Decimal] = mapped_column(
        Numeric(5, 2),
        default=Decimal("1"),
        comment="Points earned per INR spent"
    )
    point_value: Mapped[Decimal] = mapped_column(
        Numeric(5, 2),
        default=Decimal("0.25"),
        comment="INR value of 1 point"
    )
    min_points_redeem: Mapped[int] = mapped_column(
        Integer,
        default=100,
        comment="Minimum points to redeem"
    )
    max_points_per_order: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        comment="Max points redeemable per order"
    )
    max_discount_percentage: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(5, 2),
        nullable=True,
        comment="Max % of order payable via points"
    )

    # Point expiry
    points_expiry_months: Mapped[int] = mapped_column(
        Integer,
        default=12,
        comment="Months after which points expire"
    )

    # Tiers
    tier_config: Mapped[Optional[dict]] = mapped_column(
        JSONB,
        nullable=True,
        comment="Tier configuration with benefits"
    )
    # Example: [{"tier": "SILVER", "min_points": 1000, "multiplier": 1.25}, ...]

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

    def __repr__(self) -> str:
        return f"<LoyaltyProgram(name='{self.name}')>"


class ReferralProgram(Base):
    """
    Customer referral program configuration.
    """
    __tablename__ = "referral_programs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Applicable channels
    applicable_channels: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)

    # Referrer reward (existing customer)
    referrer_reward_type: Mapped[str] = mapped_column(
        String(30),
        default="CASHBACK",
        comment="CASHBACK, DISCOUNT, POINTS, FIXED"
    )
    referrer_reward_value: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        nullable=False
    )
    referrer_max_reward: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(10, 2),
        nullable=True
    )

    # Referee reward (new customer)
    referee_reward_type: Mapped[str] = mapped_column(
        String(30),
        default="DISCOUNT",
        comment="CASHBACK, DISCOUNT, POINTS, FIXED"
    )
    referee_reward_value: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        nullable=False
    )
    referee_max_reward: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(10, 2),
        nullable=True
    )

    # Conditions
    min_order_value: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(12, 2),
        nullable=True,
        comment="Min order value for referee"
    )
    max_referrals_per_user: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        comment="Max successful referrals per referrer"
    )
    reward_after_delivery: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        comment="Credit reward only after delivery"
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

    def __repr__(self) -> str:
        return f"<ReferralProgram(name='{self.name}')>"


class CustomerReferral(Base):
    """
    Track individual customer referrals.
    """
    __tablename__ = "customer_referrals"
    __table_args__ = (
        Index("ix_customer_referrals_code", "referral_code"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )

    program_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("referral_programs.id", ondelete="RESTRICT"),
        nullable=False,
        index=True
    )

    # Referrer (existing customer)
    referrer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    referral_code: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        index=True
    )

    # Referee (new customer)
    referee_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    referee_email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    referee_phone: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)

    # Channel & Order
    channel_code: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    order_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("orders.id", ondelete="SET NULL"),
        nullable=True
    )
    order_value: Mapped[Optional[Decimal]] = mapped_column(Numeric(14, 2), nullable=True)

    # Status
    status: Mapped[str] = mapped_column(
        String(30),
        default="PENDING",
        comment="PENDING, REGISTERED, ORDERED, DELIVERED, REWARDED, EXPIRED"
    )

    # Rewards
    referrer_reward: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        default=Decimal("0")
    )
    referrer_rewarded_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    referee_reward: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        default=Decimal("0")
    )
    referee_rewarded_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Timestamps
    referred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )
    registered_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    ordered_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    delivered_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    def __repr__(self) -> str:
        return f"<CustomerReferral(code='{self.referral_code}', status='{self.status}')>"
