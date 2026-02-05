"""
Distributed Order Management (DOM) Models.

DOM is the brain of order fulfillment, handling:
1. Fulfillment Node Management - Unified view of all fulfillment locations (warehouses, stores, dealers, 3PLs)
2. Order Routing - Rule-based routing to optimal fulfillment nodes
3. Order Splitting - Splitting orders across multiple nodes when inventory is distributed
4. Backorder Management - Capturing demand when inventory is unavailable
5. Pre-order Management - Taking orders for upcoming products

Architecture inspired by:
- Unicommerce OMS
- Vinculum DOM
- Oracle Order Orchestration
"""
import uuid
from datetime import datetime, date, timezone
from decimal import Decimal
from enum import Enum
from typing import TYPE_CHECKING, Optional, List

from sqlalchemy import String, Boolean, DateTime, Date, ForeignKey, Integer, Text, Numeric, Float
from sqlalchemy import UniqueConstraint, Index, CheckConstraint
from sqlalchemy.dialects.postgresql import UUID, JSONB, ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.warehouse import Warehouse
    from app.models.order import Order, OrderItem
    from app.models.dealer import Dealer
    from app.models.channel import SalesChannel
    from app.models.product import Product, ProductVariant
    from app.models.customer import Customer
    from app.models.user import User


# ============================================================================
# ENUMS
# ============================================================================

class FulfillmentNodeType(str, Enum):
    """Types of fulfillment nodes."""
    WAREHOUSE = "WAREHOUSE"           # Main/Regional warehouse
    STORE = "STORE"                   # Retail store (for BOPIS/Ship-from-Store)
    DEALER = "DEALER"                 # Dealer/Distributor location
    THIRD_PARTY_LOGISTICS = "3PL"     # 3PL partner warehouse
    DROPSHIP = "DROPSHIP"             # Dropship vendor
    VIRTUAL = "VIRTUAL"               # Virtual/Aggregated inventory


class RoutingStrategy(str, Enum):
    """Order routing strategies."""
    NEAREST = "NEAREST"               # Nearest node to customer
    CHEAPEST = "CHEAPEST"             # Lowest shipping cost
    FASTEST = "FASTEST"               # Fastest delivery (SLA)
    SPECIFIC_NODE = "SPECIFIC_NODE"   # Route to specific node
    ROUND_ROBIN = "ROUND_ROBIN"       # Distribute evenly
    INVENTORY_PRIORITY = "INVENTORY"  # Node with most inventory
    FIFO = "FIFO"                     # First-in-first-out (oldest stock)
    COST_OPTIMIZED = "COST_OPTIMIZED" # Balance cost + SLA + split


class SplitReason(str, Enum):
    """Reasons for order splitting."""
    INVENTORY_SHORTAGE = "INVENTORY_SHORTAGE"   # Single node doesn't have all items
    COST_OPTIMIZATION = "COST_OPTIMIZATION"     # Cheaper to split
    SLA_REQUIREMENT = "SLA_REQUIREMENT"         # Faster delivery via split
    CHANNEL_ROUTING = "CHANNEL_ROUTING"         # Channel-specific routing
    MANUAL_SPLIT = "MANUAL_SPLIT"               # Admin manually split


class BackorderStatus(str, Enum):
    """Backorder status."""
    PENDING = "PENDING"               # Waiting for inventory
    PARTIALLY_AVAILABLE = "PARTIALLY_AVAILABLE"  # Some qty available
    AVAILABLE = "AVAILABLE"           # Full qty available, ready to allocate
    ALLOCATED = "ALLOCATED"           # Allocated to order
    CANCELLED = "CANCELLED"           # Cancelled by customer/admin
    EXPIRED = "EXPIRED"               # Past expected date, auto-cancelled


class PreorderStatus(str, Enum):
    """Pre-order status."""
    ACTIVE = "ACTIVE"                 # Pre-order is active
    READY = "READY"                   # Product available, ready to convert
    CONVERTED = "CONVERTED"           # Converted to regular order
    CANCELLED = "CANCELLED"           # Cancelled
    REFUNDED = "REFUNDED"             # Refunded


class OrchestrationStatus(str, Enum):
    """Order orchestration status."""
    PENDING = "PENDING"               # Awaiting orchestration
    IN_PROGRESS = "IN_PROGRESS"       # Currently being orchestrated
    ROUTED = "ROUTED"                 # Successfully routed to node(s)
    SPLIT = "SPLIT"                   # Order was split
    BACKORDER = "BACKORDER"           # Sent to backorder
    FAILED = "FAILED"                 # Orchestration failed
    MANUAL_REQUIRED = "MANUAL_REQUIRED"  # Needs manual intervention


# ============================================================================
# MODELS
# ============================================================================

class FulfillmentNode(Base):
    """
    Unified view of all fulfillment locations.

    Aggregates warehouses, stores, dealers, and 3PLs into a single
    abstraction layer for order routing decisions.
    """
    __tablename__ = "fulfillment_nodes"
    __table_args__ = (
        Index("ix_fulfillment_node_type_active", "node_type", "is_active"),
        Index("ix_fulfillment_node_region", "region_id", "is_active"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )

    # Node identification
    node_code: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        nullable=False,
        index=True,
        comment="Unique code for the fulfillment node"
    )
    node_name: Mapped[str] = mapped_column(
        String(200),
        nullable=False
    )
    node_type: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        index=True,
        comment="WAREHOUSE, STORE, DEALER, 3PL, DROPSHIP, VIRTUAL"
    )

    # References to actual entities (only one should be set based on node_type)
    warehouse_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("warehouses.id", ondelete="SET NULL"),
        nullable=True
    )
    dealer_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("dealers.id", ondelete="SET NULL"),
        nullable=True
    )
    # store_id would be added when store locations are implemented
    external_reference: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        comment="External ID for 3PL/Dropship nodes"
    )

    # Location
    region_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("regions.id", ondelete="SET NULL"),
        nullable=True
    )
    latitude: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    longitude: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    pincode: Mapped[Optional[str]] = mapped_column(String(10), nullable=True, index=True)
    city: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    state: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # Capabilities
    can_fulfill_b2c: Mapped[bool] = mapped_column(Boolean, default=True)
    can_fulfill_b2b: Mapped[bool] = mapped_column(Boolean, default=True)
    supports_cod: Mapped[bool] = mapped_column(Boolean, default=True)
    supports_prepaid: Mapped[bool] = mapped_column(Boolean, default=True)
    supports_bopis: Mapped[bool] = mapped_column(Boolean, default=False, comment="Buy Online Pick Up In Store")
    supports_boris: Mapped[bool] = mapped_column(Boolean, default=False, comment="Buy Online Return In Store")
    supports_ship_from_store: Mapped[bool] = mapped_column(Boolean, default=False)
    supports_same_day: Mapped[bool] = mapped_column(Boolean, default=False)
    supports_next_day: Mapped[bool] = mapped_column(Boolean, default=True)

    # Capacity management
    daily_order_capacity: Mapped[int] = mapped_column(
        Integer,
        default=1000,
        comment="Max orders per day"
    )
    current_day_orders: Mapped[int] = mapped_column(
        Integer,
        default=0,
        comment="Orders allocated today (reset daily)"
    )
    max_concurrent_picks: Mapped[int] = mapped_column(
        Integer,
        default=50,
        comment="Max concurrent picking operations"
    )

    # Priority and scoring
    priority: Mapped[int] = mapped_column(
        Integer,
        default=100,
        comment="Lower = Higher priority for allocation"
    )
    fulfillment_score: Mapped[float] = mapped_column(
        Float,
        default=100.0,
        comment="Performance score (0-100) based on SLA adherence"
    )

    # Operating hours (JSON: {"mon": {"open": "09:00", "close": "21:00"}, ...})
    operating_hours: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)

    # Cutoff times (JSON: {"same_day": "14:00", "next_day": "18:00"})
    cutoff_times: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)

    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    is_accepting_orders: Mapped[bool] = mapped_column(Boolean, default=True)

    # Metadata
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
    warehouse: Mapped[Optional["Warehouse"]] = relationship(
        "Warehouse",
        foreign_keys=[warehouse_id]
    )
    dealer: Mapped[Optional["Dealer"]] = relationship(
        "Dealer",
        foreign_keys=[dealer_id]
    )


class RoutingRule(Base):
    """
    Order routing rules for DOM engine.

    Rules are evaluated in priority order (lower = higher priority).
    First matching rule determines the routing strategy.
    """
    __tablename__ = "routing_rules"
    __table_args__ = (
        Index("ix_routing_rule_priority_active", "priority", "is_active"),
        Index("ix_routing_rule_channel", "channel_id", "is_active"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )

    # Rule identification
    rule_name: Mapped[str] = mapped_column(
        String(200),
        nullable=False
    )
    rule_code: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        nullable=False,
        index=True
    )
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Priority (lower = evaluated first)
    priority: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=100,
        index=True
    )

    # ============================================
    # CONDITIONS (when to apply this rule)
    # ============================================

    # Channel condition
    channel_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sales_channels.id", ondelete="CASCADE"),
        nullable=True,
        comment="Apply to specific channel (NULL = all channels)"
    )
    channel_codes: Mapped[Optional[list]] = mapped_column(
        ARRAY(String),
        nullable=True,
        comment="Apply to these channel codes: ['AMAZON', 'FLIPKART']"
    )

    # Region condition
    region_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("regions.id", ondelete="CASCADE"),
        nullable=True
    )
    pincode_patterns: Mapped[Optional[list]] = mapped_column(
        ARRAY(String),
        nullable=True,
        comment="Pincode patterns: ['110*', '400001-400100']"
    )

    # Product/Category condition
    product_category_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("categories.id", ondelete="CASCADE"),
        nullable=True
    )
    product_ids: Mapped[Optional[list]] = mapped_column(
        ARRAY(UUID(as_uuid=True)),
        nullable=True,
        comment="Apply to specific products"
    )
    brand_ids: Mapped[Optional[list]] = mapped_column(
        ARRAY(UUID(as_uuid=True)),
        nullable=True,
        comment="Apply to specific brands"
    )

    # Order value condition
    min_order_value: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(12, 2),
        nullable=True
    )
    max_order_value: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(12, 2),
        nullable=True
    )

    # Payment method condition
    payment_methods: Mapped[Optional[list]] = mapped_column(
        ARRAY(String),
        nullable=True,
        comment="Apply to payment methods: ['COD', 'PREPAID']"
    )

    # Customer segment condition
    customer_segments: Mapped[Optional[list]] = mapped_column(
        ARRAY(String),
        nullable=True,
        comment="Apply to customer segments: ['VIP', 'REGULAR']"
    )

    # ============================================
    # ACTIONS (what to do when rule matches)
    # ============================================

    # Routing strategy
    routing_strategy: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default="NEAREST",
        comment="NEAREST, CHEAPEST, FASTEST, SPECIFIC_NODE, ROUND_ROBIN, INVENTORY, FIFO, COST_OPTIMIZED"
    )

    # Target node (for SPECIFIC_NODE strategy)
    target_node_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("fulfillment_nodes.id", ondelete="SET NULL"),
        nullable=True
    )

    # Preferred nodes (prioritize these nodes)
    preferred_node_ids: Mapped[Optional[list]] = mapped_column(
        ARRAY(UUID(as_uuid=True)),
        nullable=True,
        comment="List of preferred node IDs in priority order"
    )

    # Excluded nodes (never use these)
    excluded_node_ids: Mapped[Optional[list]] = mapped_column(
        ARRAY(UUID(as_uuid=True)),
        nullable=True,
        comment="Nodes to exclude from routing"
    )

    # Split configuration
    allow_split: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        comment="Allow order splitting across nodes"
    )
    max_splits: Mapped[int] = mapped_column(
        Integer,
        default=3,
        comment="Maximum number of split shipments"
    )
    min_split_value: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(12, 2),
        nullable=True,
        comment="Minimum order value per split"
    )

    # SLA requirements
    max_delivery_days: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        comment="Maximum delivery days allowed"
    )

    # Backorder configuration
    allow_backorder: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        comment="Allow backordering if inventory unavailable"
    )
    max_backorder_days: Mapped[int] = mapped_column(
        Integer,
        default=7,
        comment="Max days to wait for backorder inventory"
    )

    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)

    # Validity period
    valid_from: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )
    valid_until: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )

    # Audit
    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )
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
    channel: Mapped[Optional["SalesChannel"]] = relationship(
        "SalesChannel",
        foreign_keys=[channel_id]
    )
    target_node: Mapped[Optional["FulfillmentNode"]] = relationship(
        "FulfillmentNode",
        foreign_keys=[target_node_id]
    )


class OrderSplit(Base):
    """
    Tracks order splitting decisions.

    When an order is split across multiple fulfillment nodes,
    this table links the parent order to child orders.
    """
    __tablename__ = "order_splits"
    __table_args__ = (
        Index("ix_order_split_parent", "parent_order_id"),
        Index("ix_order_split_child", "child_order_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )

    # Parent order (original order that was split)
    parent_order_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("orders.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Child order (split portion)
    child_order_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("orders.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Split details
    split_number: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Split sequence number (1, 2, 3...)"
    )
    split_reason: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="INVENTORY_SHORTAGE, COST_OPTIMIZATION, SLA_REQUIREMENT, CHANNEL_ROUTING, MANUAL_SPLIT"
    )

    # Fulfillment node assigned
    fulfillment_node_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("fulfillment_nodes.id", ondelete="SET NULL"),
        nullable=True
    )

    # Value breakdown
    split_subtotal: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False
    )
    split_shipping: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        default=Decimal("0.00")
    )
    split_total: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False
    )

    # Items in this split (JSON array of item IDs)
    item_ids: Mapped[list] = mapped_column(
        ARRAY(UUID(as_uuid=True)),
        nullable=False
    )

    # Decision metadata
    decision_factors: Mapped[Optional[dict]] = mapped_column(
        JSONB,
        nullable=True,
        comment="Factors that led to this split decision"
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    parent_order: Mapped["Order"] = relationship(
        "Order",
        foreign_keys=[parent_order_id],
        backref="child_splits"
    )
    child_order: Mapped["Order"] = relationship(
        "Order",
        foreign_keys=[child_order_id],
        backref="parent_split"
    )
    fulfillment_node: Mapped[Optional["FulfillmentNode"]] = relationship(
        "FulfillmentNode"
    )


class OrchestrationLog(Base):
    """
    Logs all order orchestration decisions.

    Provides audit trail and analytics for DOM decisions.
    """
    __tablename__ = "orchestration_logs"
    __table_args__ = (
        Index("ix_orchestration_log_order", "order_id"),
        Index("ix_orchestration_log_created", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )

    # Order reference
    order_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("orders.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    order_number: Mapped[str] = mapped_column(
        String(30),
        nullable=False
    )

    # Orchestration result
    status: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        comment="PENDING, IN_PROGRESS, ROUTED, SPLIT, BACKORDER, FAILED, MANUAL_REQUIRED"
    )

    # Rule that was applied
    routing_rule_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("routing_rules.id", ondelete="SET NULL"),
        nullable=True
    )
    routing_rule_name: Mapped[Optional[str]] = mapped_column(
        String(200),
        nullable=True
    )
    routing_strategy: Mapped[str] = mapped_column(
        String(30),
        nullable=False
    )

    # Selected node(s)
    selected_node_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("fulfillment_nodes.id", ondelete="SET NULL"),
        nullable=True
    )
    selected_node_code: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True
    )

    # If split, number of splits created
    split_count: Mapped[int] = mapped_column(
        Integer,
        default=0
    )

    # Inventory availability at time of decision
    inventory_snapshot: Mapped[Optional[dict]] = mapped_column(
        JSONB,
        nullable=True,
        comment="Inventory state at decision time"
    )

    # Nodes that were evaluated
    evaluated_nodes: Mapped[Optional[list]] = mapped_column(
        JSONB,
        nullable=True,
        comment="List of nodes evaluated with scores"
    )

    # Decision factors and scores
    decision_factors: Mapped[Optional[dict]] = mapped_column(
        JSONB,
        nullable=True,
        comment="Factors considered: distance, cost, sla, inventory"
    )

    # If failed, reason
    failure_reason: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True
    )

    # Processing time
    processing_time_ms: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        comment="Time taken to orchestrate in milliseconds"
    )

    # Timestamp
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    order: Mapped["Order"] = relationship("Order")
    routing_rule: Mapped[Optional["RoutingRule"]] = relationship("RoutingRule")
    selected_node: Mapped[Optional["FulfillmentNode"]] = relationship("FulfillmentNode")


class Backorder(Base):
    """
    Backorder tracking for items without inventory.

    When an order item cannot be fulfilled due to inventory shortage,
    it can be placed on backorder to capture the demand.
    """
    __tablename__ = "backorders"
    __table_args__ = (
        Index("ix_backorder_order", "order_id"),
        Index("ix_backorder_product", "product_id"),
        Index("ix_backorder_status", "status"),
        Index("ix_backorder_expected", "expected_date", "status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )

    # Order and item reference
    order_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("orders.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    order_item_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("order_items.id", ondelete="CASCADE"),
        nullable=False
    )

    # Product reference
    product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("products.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    variant_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("product_variants.id", ondelete="SET NULL"),
        nullable=True
    )

    # Quantity
    quantity_ordered: Mapped[int] = mapped_column(
        Integer,
        nullable=False
    )
    quantity_available: Mapped[int] = mapped_column(
        Integer,
        default=0,
        comment="Quantity that has become available"
    )
    quantity_allocated: Mapped[int] = mapped_column(
        Integer,
        default=0,
        comment="Quantity allocated to this backorder"
    )

    # Status
    status: Mapped[str] = mapped_column(
        String(30),
        default="PENDING",
        nullable=False,
        index=True,
        comment="PENDING, PARTIALLY_AVAILABLE, AVAILABLE, ALLOCATED, CANCELLED, EXPIRED"
    )

    # Expected availability
    expected_date: Mapped[Optional[date]] = mapped_column(
        Date,
        nullable=True,
        comment="Expected date when inventory will be available"
    )
    source_po_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("purchase_orders.id", ondelete="SET NULL"),
        nullable=True,
        comment="Purchase order that will fulfill this backorder"
    )

    # Customer communication
    customer_notified: Mapped[bool] = mapped_column(
        Boolean,
        default=False
    )
    customer_consent: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        comment="Customer agreed to wait for backorder"
    )

    # Priority
    priority: Mapped[int] = mapped_column(
        Integer,
        default=100,
        comment="Lower = Higher priority for allocation"
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
    available_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="When inventory became available"
    )
    allocated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )
    cancelled_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )
    cancellation_reason: Mapped[Optional[str]] = mapped_column(
        String(200),
        nullable=True
    )

    # Relationships
    order: Mapped["Order"] = relationship("Order")
    order_item: Mapped["OrderItem"] = relationship("OrderItem")
    product: Mapped["Product"] = relationship("Product")


class Preorder(Base):
    """
    Pre-order management for upcoming products.

    Allows capturing demand for products not yet available,
    with optional deposit collection.
    """
    __tablename__ = "preorders"
    __table_args__ = (
        Index("ix_preorder_product", "product_id"),
        Index("ix_preorder_customer", "customer_id"),
        Index("ix_preorder_status", "status"),
        Index("ix_preorder_release", "expected_release_date", "status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )

    # Pre-order number
    preorder_number: Mapped[str] = mapped_column(
        String(30),
        unique=True,
        nullable=False,
        index=True
    )

    # Product reference
    product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("products.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    variant_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("product_variants.id", ondelete="SET NULL"),
        nullable=True
    )

    # Customer reference
    customer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("customers.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Quantity and pricing
    quantity: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1
    )
    unit_price: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
        comment="Locked-in price at time of pre-order"
    )
    total_amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False
    )

    # Deposit
    deposit_required: Mapped[bool] = mapped_column(
        Boolean,
        default=False
    )
    deposit_percentage: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
        comment="Deposit as percentage of total"
    )
    deposit_amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        default=Decimal("0.00")
    )
    deposit_paid: Mapped[bool] = mapped_column(
        Boolean,
        default=False
    )
    deposit_paid_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )
    deposit_payment_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("payments.id", ondelete="SET NULL"),
        nullable=True
    )

    # Expected release
    expected_release_date: Mapped[Optional[date]] = mapped_column(
        Date,
        nullable=True,
        index=True
    )
    actual_release_date: Mapped[Optional[date]] = mapped_column(
        Date,
        nullable=True
    )

    # Status
    status: Mapped[str] = mapped_column(
        String(30),
        default="ACTIVE",
        nullable=False,
        index=True,
        comment="ACTIVE, READY, CONVERTED, CANCELLED, REFUNDED"
    )

    # Conversion to order
    converted_order_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("orders.id", ondelete="SET NULL"),
        nullable=True
    )
    converted_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )

    # Cancellation
    cancelled_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )
    cancellation_reason: Mapped[Optional[str]] = mapped_column(
        String(200),
        nullable=True
    )
    refund_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("refunds.id", ondelete="SET NULL"),
        nullable=True
    )

    # Notification tracking
    notified_ready: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        comment="Customer notified when product ready"
    )
    notified_ready_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )

    # Priority (first-come-first-serve by default)
    queue_position: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Position in pre-order queue"
    )

    # Channel/Source
    channel_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sales_channels.id", ondelete="SET NULL"),
        nullable=True
    )
    source: Mapped[str] = mapped_column(
        String(50),
        default="WEBSITE"
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
    product: Mapped["Product"] = relationship("Product")
    customer: Mapped["Customer"] = relationship("Customer")
    converted_order: Mapped[Optional["Order"]] = relationship(
        "Order",
        foreign_keys=[converted_order_id]
    )
    channel: Mapped[Optional["SalesChannel"]] = relationship("SalesChannel")


class GlobalInventoryView(Base):
    """
    Aggregated inventory view across all fulfillment nodes.

    Provides ATP (Available to Promise) and ATF (Available to Fulfill)
    calculations for DOM decision making.

    This is a materialized/cached view refreshed periodically.
    """
    __tablename__ = "global_inventory_view"
    __table_args__ = (
        UniqueConstraint("product_id", "variant_id", "fulfillment_node_id", name="uq_global_inventory"),
        Index("ix_global_inventory_product", "product_id"),
        Index("ix_global_inventory_node", "fulfillment_node_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )

    # Product reference
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
    sku: Mapped[str] = mapped_column(String(100), nullable=False, index=True)

    # Fulfillment node reference
    fulfillment_node_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("fulfillment_nodes.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Inventory quantities
    total_quantity: Mapped[int] = mapped_column(
        Integer,
        default=0,
        comment="Total physical quantity"
    )
    available_quantity: Mapped[int] = mapped_column(
        Integer,
        default=0,
        comment="Available for sale"
    )
    reserved_quantity: Mapped[int] = mapped_column(
        Integer,
        default=0,
        comment="Reserved for orders"
    )
    allocated_quantity: Mapped[int] = mapped_column(
        Integer,
        default=0,
        comment="Allocated to specific orders"
    )
    in_transit_quantity: Mapped[int] = mapped_column(
        Integer,
        default=0,
        comment="In transit to this node"
    )
    backorder_quantity: Mapped[int] = mapped_column(
        Integer,
        default=0,
        comment="Quantity on backorder"
    )

    # ATP/ATF calculations
    atp: Mapped[int] = mapped_column(
        Integer,
        default=0,
        comment="Available to Promise = available - reserved - allocated"
    )
    atf: Mapped[int] = mapped_column(
        Integer,
        default=0,
        comment="Available to Fulfill = available - allocated"
    )

    # Safety stock
    safety_stock: Mapped[int] = mapped_column(
        Integer,
        default=0
    )
    reorder_point: Mapped[int] = mapped_column(
        Integer,
        default=0
    )

    # Flags
    is_in_stock: Mapped[bool] = mapped_column(Boolean, default=False)
    is_low_stock: Mapped[bool] = mapped_column(Boolean, default=False)

    # Last update
    last_updated: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    product: Mapped["Product"] = relationship("Product")
    fulfillment_node: Mapped["FulfillmentNode"] = relationship("FulfillmentNode")
