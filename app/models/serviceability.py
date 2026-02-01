"""
Serviceability and Allocation models for OMS/WMS.

Three-tier serviceability architecture (Vinculum/Unicommerce style):
1. WarehouseServiceability - Which pincodes each warehouse can serve
2. TransporterServiceability - Which routes each courier covers (already in transporter.py)
3. AllocationRule - Channel-wise allocation logic

Order Flow:
NEW → Check Serviceability → Allocate Warehouse → Check Stock → Allocate Inventory
"""
import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import TYPE_CHECKING, Optional, List

from sqlalchemy import String, Boolean, DateTime, ForeignKey, Integer, Text, Float
from sqlalchemy import UniqueConstraint, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.warehouse import Warehouse
    from app.models.channel import SalesChannel


class AllocationType(str, Enum):
    """Allocation type for order routing."""
    NEAREST = "NEAREST"           # Nearest warehouse to customer pincode
    ROUND_ROBIN = "ROUND_ROBIN"   # Distribute evenly across warehouses
    FIFO = "FIFO"                 # First In First Out - oldest stock first
    FIXED = "FIXED"               # Fixed warehouse assignment
    PRIORITY = "PRIORITY"         # Based on warehouse priority
    COST_OPTIMIZED = "COST_OPTIMIZED"  # Lowest shipping cost


class AllocationPriority(str, Enum):
    """Priority factors for allocation."""
    CHANNEL = "CHANNEL"           # Channel-specific allocation
    PROXIMITY = "PROXIMITY"       # Distance-based
    INVENTORY = "INVENTORY"       # Stock availability
    COST = "COST"                 # Shipping cost
    SLA = "SLA"                   # Delivery time/SLA


class ChannelCode(str, Enum):
    """Sales channel codes."""
    D2C = "D2C"                   # Direct to Consumer (own website)
    AMAZON = "AMAZON"             # Amazon marketplace
    FLIPKART = "FLIPKART"         # Flipkart marketplace
    MYNTRA = "MYNTRA"             # Myntra
    MEESHO = "MEESHO"             # Meesho
    TATACLIQ = "TATACLIQ"         # TataCliq
    DEALER = "DEALER"             # B2B Dealer orders
    STORE = "STORE"               # Retail store orders
    ALL = "ALL"                   # Apply to all channels


class WarehouseServiceability(Base):
    """
    Warehouse Serviceability mapping.
    Defines which pin codes a warehouse can serve.

    Example:
    - Mumbai Warehouse serves 400001-400099 (Mumbai pincodes)
    - Delhi Warehouse serves 110001-110099 (Delhi pincodes)
    """
    __tablename__ = "warehouse_serviceability"
    __table_args__ = (
        UniqueConstraint(
            "warehouse_id", "pincode",
            name="uq_warehouse_serviceability"
        ),
        Index("ix_warehouse_serviceability_pincode", "pincode"),
        Index("ix_warehouse_serviceability_pincode_active", "pincode", "is_serviceable", "is_active"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )

    warehouse_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("warehouses.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Pincode (single pincode per row for easier querying)
    # Note: Index defined in __table_args__ as ix_warehouse_serviceability_pincode
    pincode: Mapped[str] = mapped_column(
        String(10),
        nullable=False
    )

    # Service details
    is_serviceable: Mapped[bool] = mapped_column(Boolean, default=True)
    cod_available: Mapped[bool] = mapped_column(Boolean, default=True)
    prepaid_available: Mapped[bool] = mapped_column(Boolean, default=True)

    # Delivery estimates
    estimated_days: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        comment="Estimated delivery days from warehouse to pincode"
    )

    # Priority (lower = higher priority)
    priority: Mapped[int] = mapped_column(
        Integer,
        default=100,
        comment="Lower value = higher priority for this warehouse-pincode"
    )

    # Shipping cost estimate
    shipping_cost: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
        comment="Estimated shipping cost to this pincode"
    )

    # Geographic info (cached for proximity calculation)
    city: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    state: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    zone: Mapped[Optional[str]] = mapped_column(
        String(20),
        nullable=True,
        comment="Delivery zone: LOCAL, REGIONAL, NATIONAL, METRO"
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
    warehouse: Mapped["Warehouse"] = relationship(
        "Warehouse",
        backref="serviceability"
    )

    def __repr__(self) -> str:
        return f"<WarehouseServiceability(warehouse={self.warehouse_id}, pincode={self.pincode})>"


class AllocationRule(Base):
    """
    Allocation rules for order routing.
    Defines how orders from different channels should be allocated to warehouses.

    Priority-based allocation:
    1. Channel-specific (Amazon FBA → Amazon warehouse)
    2. Proximity (Nearest warehouse)
    3. Inventory (Warehouse with available stock)
    4. Cost (Lowest shipping cost)
    5. SLA (Fastest delivery)
    """
    __tablename__ = "allocation_rules"
    __table_args__ = (
        UniqueConstraint(
            "channel_code", "priority",
            name="uq_allocation_rule_channel_priority"
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )

    # Rule identification
    name: Mapped[str] = mapped_column(
        String(200),
        nullable=False
    )
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Channel (which sales channel this rule applies to)
    channel_code: Mapped[str] = mapped_column(
        String(50),
        default="ALL",
        nullable=False,
        index=True,
        comment="D2C, AMAZON, FLIPKART, MYNTRA, MEESHO, TATACLIQ, DEALER, STORE, ALL"
    )

    # Optional: Link to SalesChannel for marketplace-specific rules
    channel_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sales_channels.id", ondelete="SET NULL"),
        nullable=True
    )

    # Priority (lower = executes first)
    priority: Mapped[int] = mapped_column(
        Integer,
        default=100,
        nullable=False,
        comment="Lower value = higher priority"
    )

    # Allocation type
    allocation_type: Mapped[str] = mapped_column(
        String(50),
        default="NEAREST",
        nullable=False,
        comment="NEAREST, ROUND_ROBIN, FIFO, FIXED, PRIORITY, COST_OPTIMIZED"
    )

    # Fixed warehouse (if allocation_type is FIXED)
    fixed_warehouse_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("warehouses.id", ondelete="SET NULL"),
        nullable=True,
        comment="Fixed warehouse for FIXED allocation type"
    )

    # Allocation priorities (comma-separated order)
    # e.g., "PROXIMITY,INVENTORY,COST" means check proximity first, then stock, then cost
    priority_factors: Mapped[Optional[str]] = mapped_column(
        String(200),
        nullable=True,
        comment="Comma-separated priority factors: PROXIMITY,INVENTORY,COST,SLA"
    )

    # Conditions
    min_order_value: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
        comment="Minimum order value for this rule to apply"
    )
    max_order_value: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
        comment="Maximum order value for this rule to apply"
    )

    # Payment mode condition
    payment_mode: Mapped[Optional[str]] = mapped_column(
        String(20),
        nullable=True,
        comment="COD, PREPAID, or null for all"
    )

    # Split order handling
    allow_split: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        comment="Allow splitting order across multiple warehouses"
    )
    max_splits: Mapped[int] = mapped_column(
        Integer,
        default=2,
        comment="Maximum number of warehouses for split orders"
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
    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )

    # Relationships
    fixed_warehouse: Mapped[Optional["Warehouse"]] = relationship(
        "Warehouse",
        foreign_keys=[fixed_warehouse_id]
    )
    channel: Mapped[Optional["SalesChannel"]] = relationship(
        "SalesChannel",
        foreign_keys=[channel_id]
    )

    def get_priority_factors(self) -> List[str]:
        """Get priority factors as list."""
        if self.priority_factors:
            return [f.strip() for f in self.priority_factors.split(",")]
        return ["PROXIMITY", "INVENTORY"]  # Default

    def __repr__(self) -> str:
        return f"<AllocationRule(name='{self.name}', channel={self.channel_code})>"


class AllocationLog(Base):
    """
    Log of allocation decisions for orders.
    Tracks which warehouse was selected and why.
    """
    __tablename__ = "allocation_logs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )

    order_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("orders.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Applied rule
    rule_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("allocation_rules.id", ondelete="SET NULL"),
        nullable=True
    )

    # Selected warehouse
    warehouse_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("warehouses.id", ondelete="SET NULL"),
        nullable=True
    )

    # Customer pincode
    customer_pincode: Mapped[str] = mapped_column(
        String(10),
        nullable=False
    )

    # Allocation result
    is_successful: Mapped[bool] = mapped_column(Boolean, default=False)
    failure_reason: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
        comment="Reason if allocation failed"
    )

    # Decision factors (JSON-like info stored as text)
    decision_factors: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Factors considered: proximity, stock, cost, etc."
    )

    # Candidate warehouses considered
    candidates_considered: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="List of warehouses considered with scores"
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    # Relationships
    order: Mapped["Order"] = relationship("Order", backref="allocation_logs")
    rule: Mapped[Optional["AllocationRule"]] = relationship("AllocationRule")
    warehouse: Mapped[Optional["Warehouse"]] = relationship("Warehouse")

    def __repr__(self) -> str:
        return f"<AllocationLog(order={self.order_id}, warehouse={self.warehouse_id})>"


# Import Order for type hints
from app.models.order import Order
