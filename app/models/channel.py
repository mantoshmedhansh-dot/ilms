"""Sales Channel models for multi-channel commerce management.

Supports: D2C Website, Mobile App, Amazon, Flipkart, Dealer Network,
Retail Stores, Franchise, Corporate Sales, etc.
"""
import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import TYPE_CHECKING, Optional, List
from decimal import Decimal

from sqlalchemy import String, Boolean, DateTime, ForeignKey, Integer, Text, Numeric, Float
from sqlalchemy import UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.warehouse import Warehouse
    from app.models.product import Product


class ChannelType(str, Enum):
    """Sales channel type enumeration."""
    # Simplified types (for UI compatibility)
    D2C = "D2C"                         # Direct to Consumer (general)
    MARKETPLACE = "MARKETPLACE"         # Marketplace (general)
    B2B = "B2B"                         # Business to Business
    OFFLINE = "OFFLINE"                 # Offline/Retail (general)
    # Detailed D2C types
    D2C_WEBSITE = "D2C_WEBSITE"         # Own website (Shopify, custom)
    D2C_APP = "D2C_APP"                 # Own mobile app
    # Specific marketplaces
    AMAZON = "AMAZON"
    FLIPKART = "FLIPKART"
    MYNTRA = "MYNTRA"
    TATACLIQ = "TATACLIQ"
    JIOMART = "JIOMART"
    MEESHO = "MEESHO"
    NYKAA = "NYKAA"
    AJIO = "AJIO"
    # Other channel types
    RETAIL_STORE = "RETAIL_STORE"       # Own retail stores
    FRANCHISE = "FRANCHISE"             # Franchise stores
    DEALER = "DEALER"                   # Authorized dealers
    DEALER_PORTAL = "DEALER_PORTAL"     # Dealer portal
    DISTRIBUTOR = "DISTRIBUTOR"         # Regional distributors
    MODERN_TRADE = "MODERN_TRADE"       # Croma, Reliance Digital, Vijay Sales
    CORPORATE = "CORPORATE"             # B2B corporate sales
    B2B_PORTAL = "B2B_PORTAL"           # B2B portal
    GOVERNMENT = "GOVERNMENT"           # Govt tenders/GeM
    EXPORT = "EXPORT"                   # International sales
    QUICK_COMMERCE = "QUICK_COMMERCE"   # Blinkit, Zepto, Instamart
    OTHER = "OTHER"                     # Other channels


class ChannelStatus(str, Enum):
    """Channel status enumeration."""
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    SUSPENDED = "SUSPENDED"
    PENDING_SETUP = "PENDING_SETUP"


class SalesChannel(Base):
    """
    Sales Channel master model.
    Manages all sales channels for omnichannel commerce.
    """
    __tablename__ = "sales_channels"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )

    # Identification
    code: Mapped[str] = mapped_column(
        String(30),
        unique=True,
        nullable=False,
        index=True,
        comment="Unique channel code e.g., AMAZON_IN, FLIPKART, D2C_WEB"
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    display_name: Mapped[str] = mapped_column(String(200), nullable=False)

    # Type & Status
    channel_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
        comment="D2C, MARKETPLACE, B2B, OFFLINE, D2C_WEBSITE, D2C_APP, AMAZON, FLIPKART, MYNTRA, TATACLIQ, JIOMART, MEESHO, NYKAA, AJIO, RETAIL_STORE, FRANCHISE, DEALER, DEALER_PORTAL, DISTRIBUTOR, MODERN_TRADE, CORPORATE, B2B_PORTAL, GOVERNMENT, EXPORT, QUICK_COMMERCE, OTHER"
    )
    status: Mapped[str] = mapped_column(
        String(50),
        default="ACTIVE",
        nullable=False,
        comment="ACTIVE, INACTIVE, SUSPENDED, PENDING_SETUP"
    )

    # Marketplace Integration (for marketplace channels)
    seller_id: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        comment="Seller ID on marketplace"
    )
    api_endpoint: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    api_key: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    api_secret: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    webhook_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # Fulfillment Settings
    default_warehouse_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("warehouses.id", ondelete="SET NULL"),
        nullable=True
    )
    fulfillment_type: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        comment="SELF, FBA, FLIPKART_ASSURED, etc."
    )
    auto_confirm_orders: Mapped[bool] = mapped_column(Boolean, default=False)
    auto_allocate_inventory: Mapped[bool] = mapped_column(Boolean, default=True)

    # Commission & Fees (for marketplace)
    commission_percentage: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(5, 2),
        nullable=True,
        comment="Marketplace commission %"
    )
    fixed_fee_per_order: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(10, 2),
        nullable=True
    )
    payment_cycle_days: Mapped[int] = mapped_column(
        Integer,
        default=7,
        comment="Settlement cycle in days"
    )

    # Pricing Rules
    price_markup_percentage: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(5, 2),
        nullable=True,
        comment="% markup over base price"
    )
    price_discount_percentage: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(5, 2),
        nullable=True,
        comment="% discount from MRP"
    )
    use_channel_specific_pricing: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        comment="Use ChannelPricing table instead of product price"
    )

    # Return Policy
    return_window_days: Mapped[int] = mapped_column(Integer, default=7)
    replacement_window_days: Mapped[int] = mapped_column(Integer, default=7)
    supports_return_pickup: Mapped[bool] = mapped_column(Boolean, default=True)

    # Tax Settings
    tax_inclusive_pricing: Mapped[bool] = mapped_column(Boolean, default=True)
    collect_tcs: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        comment="TCS collection for marketplace"
    )
    tcs_rate: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(5, 2),
        nullable=True,
        comment="TCS rate (typically 1%)"
    )

    # Contact
    contact_name: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    contact_email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    contact_phone: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)

    # Configuration (JSONB for flexible settings)
    config: Mapped[Optional[dict]] = mapped_column(
        JSONB,
        nullable=True,
        comment="Channel-specific configuration"
    )

    # Sync Settings
    last_sync_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    sync_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    sync_interval_minutes: Mapped[int] = mapped_column(Integer, default=30)

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
    pricing: Mapped[List["ChannelPricing"]] = relationship(
        "ChannelPricing",
        back_populates="channel",
        cascade="all, delete-orphan"
    )
    inventory_allocation: Mapped[List["ChannelInventory"]] = relationship(
        "ChannelInventory",
        back_populates="channel",
        cascade="all, delete-orphan"
    )

    @property
    def is_marketplace(self) -> bool:
        """Check if channel is a marketplace."""
        return self.channel_type.startswith("MARKETPLACE_")

    def __repr__(self) -> str:
        return f"<SalesChannel(code='{self.code}', type='{self.channel_type}')>"


class ChannelPricing(Base):
    """
    Channel-specific product pricing.
    Allows different prices per channel (MRP - Margin model).
    """
    __tablename__ = "channel_pricing"
    __table_args__ = (
        UniqueConstraint("channel_id", "product_id", "variant_id", name="uq_channel_product_pricing"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )

    channel_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sales_channels.id", ondelete="CASCADE"),
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
    mrp: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    selling_price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    transfer_price: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(12, 2),
        nullable=True,
        comment="Price for dealer/distributor channels"
    )

    # Discounts
    discount_percentage: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 2), nullable=True)
    max_discount_percentage: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(5, 2),
        nullable=True,
        comment="Maximum allowed discount"
    )

    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_listed: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        comment="Product listed on this channel"
    )

    # Effective dates
    effective_from: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    effective_to: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

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
    channel: Mapped["SalesChannel"] = relationship(
        "SalesChannel",
        back_populates="pricing"
    )
    product: Mapped["Product"] = relationship("Product")

    @property
    def margin_percentage(self) -> Decimal:
        """Calculate margin percentage."""
        if self.mrp > 0:
            return ((self.mrp - self.selling_price) / self.mrp) * 100
        return Decimal("0")

    def __repr__(self) -> str:
        return f"<ChannelPricing(channel={self.channel_id}, product={self.product_id})>"


class ChannelInventory(Base):
    """
    Channel-specific inventory allocation.
    Allows splitting inventory across channels (buffer stock).
    """
    __tablename__ = "channel_inventory"
    __table_args__ = (
        UniqueConstraint(
            "channel_id", "warehouse_id", "product_id", "variant_id",
            name="uq_channel_inventory"
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )

    channel_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sales_channels.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    warehouse_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("warehouses.id", ondelete="CASCADE"),
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

    # Allocation
    allocated_quantity: Mapped[int] = mapped_column(
        Integer,
        default=0,
        comment="Quantity allocated to this channel"
    )
    buffer_quantity: Mapped[int] = mapped_column(
        Integer,
        default=0,
        comment="Safety buffer stock"
    )
    reserved_quantity: Mapped[int] = mapped_column(
        Integer,
        default=0,
        comment="Reserved for pending orders"
    )

    # Sync
    marketplace_quantity: Mapped[int] = mapped_column(
        Integer,
        default=0,
        comment="Quantity synced to marketplace"
    )
    last_synced_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Auto-replenish settings (quantity-based)
    safety_stock: Mapped[Optional[int]] = mapped_column(
        Integer,
        default=0,
        nullable=True,
        comment="Target level for auto-replenish"
    )
    reorder_point: Mapped[Optional[int]] = mapped_column(
        Integer,
        default=0,
        nullable=True,
        comment="Trigger auto-replenish below this level"
    )
    auto_replenish_enabled: Mapped[Optional[bool]] = mapped_column(
        Boolean,
        default=True,
        nullable=True,
        comment="Enable auto-replenishment for this channel-product"
    )

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
    channel: Mapped["SalesChannel"] = relationship(
        "SalesChannel",
        back_populates="inventory_allocation"
    )
    warehouse: Mapped["Warehouse"] = relationship("Warehouse")
    product: Mapped["Product"] = relationship("Product")

    @property
    def available_quantity(self) -> int:
        """Calculate available quantity for this channel."""
        return max(0, self.allocated_quantity - self.buffer_quantity - self.reserved_quantity)

    def __repr__(self) -> str:
        return f"<ChannelInventory(channel={self.channel_id}, product={self.product_id})>"


class ChannelOrder(Base):
    """
    Marketplace order reference mapping.
    Links internal order to marketplace order ID.
    """
    __tablename__ = "channel_orders"
    __table_args__ = (
        UniqueConstraint("channel_id", "channel_order_id", name="uq_channel_order"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )

    channel_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sales_channels.id", ondelete="RESTRICT"),
        nullable=False,
        index=True
    )

    order_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("orders.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Marketplace Reference
    channel_order_id: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
        comment="Order ID on marketplace"
    )
    channel_order_item_id: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        comment="Line item ID on marketplace"
    )

    # Financials
    channel_selling_price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    channel_shipping_fee: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=Decimal("0"))
    channel_commission: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=Decimal("0"))
    channel_tcs: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=Decimal("0"))
    net_receivable: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)

    # Status Mapping
    channel_status: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        comment="Order status on marketplace"
    )

    # Sync
    raw_order_data: Mapped[Optional[dict]] = mapped_column(
        JSONB,
        nullable=True,
        comment="Raw order data from marketplace"
    )
    synced_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )
    last_status_sync_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Settlement
    settlement_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    settlement_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    is_settled: Mapped[bool] = mapped_column(Boolean, default=False)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    # Relationships
    channel: Mapped["SalesChannel"] = relationship("SalesChannel")

    def __repr__(self) -> str:
        return f"<ChannelOrder(channel_order_id='{self.channel_order_id}')>"


class ProductChannelSettings(Base):
    """
    Per-product settings for each sales channel.
    Controls allocation defaults and auto-replenishment.
    """
    __tablename__ = "product_channel_settings"
    __table_args__ = (
        UniqueConstraint(
            "product_id", "channel_id", "warehouse_id",
            name="uq_product_channel_warehouse_settings"
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )

    product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("products.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    channel_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sales_channels.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    warehouse_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("warehouses.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Allocation defaults for GRN
    default_allocation_percentage: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        comment="Default % of GRN to allocate to this channel"
    )
    default_allocation_qty: Mapped[int] = mapped_column(
        Integer,
        default=0,
        comment="Default fixed qty to allocate on GRN"
    )

    # Auto-replenish settings (quantity-based)
    safety_stock: Mapped[int] = mapped_column(
        Integer,
        default=0,
        comment="Target level to maintain (e.g., 50 units)"
    )
    reorder_point: Mapped[int] = mapped_column(
        Integer,
        default=0,
        comment="Trigger replenishment when below this (e.g., 10 units)"
    )
    max_allocation: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        comment="Never exceed this allocation"
    )

    # Auto-replenish flags
    auto_replenish_enabled: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        comment="Enable auto-replenishment from shared pool"
    )
    replenish_from_shared_pool: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        comment="Can borrow from unallocated FG inventory"
    )

    # Sync settings (for marketplaces)
    sync_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    sync_buffer_percentage: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        comment="Additional buffer % when syncing to marketplace"
    )

    # Active status
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
    product: Mapped["Product"] = relationship("Product")
    channel: Mapped["SalesChannel"] = relationship("SalesChannel")
    warehouse: Mapped["Warehouse"] = relationship("Warehouse")

    def __repr__(self) -> str:
        return f"<ProductChannelSettings(product={self.product_id}, channel={self.channel_id})>"


class MarketplaceIntegration(Base):
    """
    Marketplace API integration credentials and settings.

    Stores encrypted credentials for marketplace APIs:
    - Amazon SP-API
    - Flipkart Seller API
    - Meesho API
    - Snapdeal API
    """
    __tablename__ = "marketplace_integrations"
    __table_args__ = (
        UniqueConstraint("company_id", "marketplace_type", name="uq_company_marketplace"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )

    # Company
    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Marketplace
    marketplace_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
        comment="AMAZON, FLIPKART, MEESHO, SNAPDEAL"
    )

    # Credentials (encrypted)
    client_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    client_secret: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Encrypted client secret"
    )
    refresh_token: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Encrypted refresh token (Amazon)"
    )
    api_key: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Encrypted API key"
    )

    # Seller Info
    seller_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    marketplace_seller_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Settings
    is_sandbox: Mapped[bool] = mapped_column(Boolean, default=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Sync Settings
    auto_sync_orders: Mapped[bool] = mapped_column(Boolean, default=True)
    auto_sync_inventory: Mapped[bool] = mapped_column(Boolean, default=True)
    sync_interval_minutes: Mapped[int] = mapped_column(Integer, default=30)

    # Last Sync Timestamps
    last_order_sync_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    last_inventory_sync_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    last_sync_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    last_sync_status: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    last_sync_error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Audit
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
    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=True
    )

    def __repr__(self) -> str:
        return f"<MarketplaceIntegration({self.marketplace_type}, active={self.is_active})>"


class PricingRuleType(str, Enum):
    """Pricing rule types."""
    VOLUME_DISCOUNT = "VOLUME_DISCOUNT"       # Quantity-based discounts
    CUSTOMER_SEGMENT = "CUSTOMER_SEGMENT"     # Customer type discounts (VIP, DEALER)
    PROMOTIONAL = "PROMOTIONAL"               # Promo codes and campaigns
    BUNDLE = "BUNDLE"                         # Product bundle discounts
    TIME_BASED = "TIME_BASED"                 # Weekend, festival, etc.
    CATEGORY = "CATEGORY"                     # Category-wide discounts
    BRAND = "BRAND"                           # Brand-wide discounts


class PricingRule(Base):
    """
    Pricing Rules Engine for dynamic pricing.

    Supports volume discounts, customer segments, promotions, etc.
    Rules are applied in priority order (lower priority = higher precedence).
    """
    __tablename__ = "pricing_rules"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )

    # Rule identification
    code: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        nullable=False,
        comment="Unique rule code"
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Rule type
    rule_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="VOLUME_DISCOUNT, CUSTOMER_SEGMENT, PROMOTIONAL, BUNDLE, TIME_BASED"
    )

    # Scope (what this rule applies to - NULL means all)
    channel_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sales_channels.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
        comment="NULL = applies to all channels"
    )
    category_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("categories.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
        comment="NULL = applies to all categories"
    )
    product_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("products.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
        comment="NULL = applies to all products"
    )
    brand_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("brands.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
        comment="NULL = applies to all brands"
    )

    # Conditions (JSONB for flexibility)
    conditions: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        comment="Rule conditions as JSON: min_qty, max_qty, customer_segments, promo_code, etc."
    )

    # Action (discount to apply)
    discount_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        comment="PERCENTAGE or FIXED_AMOUNT"
    )
    discount_value: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        nullable=False,
        comment="Discount value (% or fixed amount)"
    )

    # Validity period
    effective_from: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )
    effective_to: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )

    # Priority (lower = higher priority)
    priority: Mapped[int] = mapped_column(
        Integer,
        default=100,
        comment="Lower number = higher priority"
    )

    # Combinability
    is_combinable: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        comment="Can combine with other rules?"
    )

    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Usage limits
    max_uses: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        comment="Max total uses (NULL = unlimited)"
    )
    max_uses_per_customer: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        comment="Max uses per customer (NULL = unlimited)"
    )
    current_uses: Mapped[int] = mapped_column(Integer, default=0)

    # Audit
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
    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=True
    )

    def __repr__(self) -> str:
        return f"<PricingRule({self.code}, type={self.rule_type}, active={self.is_active})>"


class PricingHistory(Base):
    """
    Audit trail for pricing changes.

    Tracks all changes to ChannelPricing and PricingRule records.
    """
    __tablename__ = "pricing_history"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )

    # What changed
    entity_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
        comment="CHANNEL_PRICING, PRICING_RULE, PRODUCT_PRICE"
    )
    entity_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
        index=True
    )

    # Change details
    field_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="Field that was changed"
    )
    old_value: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    new_value: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Who/when
    changed_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=True
    )
    changed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    # Why (optional reason for change)
    change_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    def __repr__(self) -> str:
        return f"<PricingHistory({self.entity_type}:{self.entity_id}, {self.field_name})>"
