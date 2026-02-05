"""
Omnichannel Models - Phase 3: BOPIS/BORIS & Ship-from-Store.

This module implements omnichannel fulfillment capabilities:
- StoreLocation: Physical store as fulfillment node
- BOPISOrder: Buy Online, Pick up In Store
- ShipFromStoreOrder: Use store inventory for online orders
- StoreInventoryReservation: Reserve store inventory for orders
- StoreReturn: In-store returns for online orders (BORIS)
"""
import uuid
from datetime import datetime, timezone, date, timedelta
from decimal import Decimal
from enum import Enum
from typing import TYPE_CHECKING, Optional, List, Dict, Any

from sqlalchemy import (
    String, Boolean, DateTime, ForeignKey, Integer, Text,
    Numeric, Date, Time, Index, UniqueConstraint
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.warehouse import Warehouse
    from app.models.order import Order
    from app.models.customer import Customer
    from app.models.product import Product, ProductVariant
    from app.models.user import User


# ============================================================================
# ENUMS
# ============================================================================

class StoreType(str, Enum):
    """Store type classification."""
    FLAGSHIP = "FLAGSHIP"           # Large format stores
    STANDARD = "STANDARD"           # Regular retail stores
    EXPRESS = "EXPRESS"             # Small format/convenience
    OUTLET = "OUTLET"               # Factory outlet
    FRANCHISE = "FRANCHISE"         # Franchised stores
    SHOP_IN_SHOP = "SHOP_IN_SHOP"  # Store within another store
    POP_UP = "POP_UP"              # Temporary/seasonal


class StoreStatus(str, Enum):
    """Store operational status."""
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    TEMPORARILY_CLOSED = "TEMPORARILY_CLOSED"
    COMING_SOON = "COMING_SOON"
    PERMANENTLY_CLOSED = "PERMANENTLY_CLOSED"


class BOPISStatus(str, Enum):
    """BOPIS order lifecycle status."""
    PENDING = "PENDING"             # Order placed, awaiting store confirmation
    CONFIRMED = "CONFIRMED"         # Store confirmed availability
    PICKING = "PICKING"             # Store staff picking items
    READY = "READY"                 # Ready for customer pickup
    NOTIFIED = "NOTIFIED"           # Customer notified
    PICKED_UP = "PICKED_UP"         # Customer collected order
    PARTIALLY_PICKED_UP = "PARTIALLY_PICKED_UP"  # Partial pickup
    EXPIRED = "EXPIRED"             # Pickup window expired
    CANCELLED = "CANCELLED"         # Order cancelled


class ShipFromStoreStatus(str, Enum):
    """Ship-from-store order status."""
    PENDING = "PENDING"             # Awaiting store acceptance
    ACCEPTED = "ACCEPTED"           # Store accepted fulfillment
    REJECTED = "REJECTED"           # Store rejected (out of stock, etc.)
    PICKING = "PICKING"             # Staff picking items
    PACKED = "PACKED"               # Items packed
    SHIPPED = "SHIPPED"             # Handed to carrier
    DELIVERED = "DELIVERED"         # Delivered to customer
    CANCELLED = "CANCELLED"


class StoreReturnStatus(str, Enum):
    """In-store return (BORIS) status."""
    INITIATED = "INITIATED"         # Customer initiated return
    SCHEDULED = "SCHEDULED"         # Return scheduled at store
    RECEIVED = "RECEIVED"           # Store received items
    INSPECTING = "INSPECTING"       # Quality inspection
    APPROVED = "APPROVED"           # Return approved
    REJECTED = "REJECTED"           # Return rejected
    REFUNDED = "REFUNDED"           # Refund processed
    COMPLETED = "COMPLETED"         # Return completed


class InventoryReservationType(str, Enum):
    """Store inventory reservation type."""
    BOPIS = "BOPIS"                 # Reserved for in-store pickup
    SHIP_FROM_STORE = "SHIP_FROM_STORE"  # Reserved for ship-from-store
    ENDLESS_AISLE = "ENDLESS_AISLE"      # Reserved via endless aisle
    HOLD = "HOLD"                   # Customer hold (layaway)


class PickupLocationType(str, Enum):
    """Where customer can pick up."""
    IN_STORE = "IN_STORE"           # Inside the store
    CURBSIDE = "CURBSIDE"           # Curbside pickup
    LOCKER = "LOCKER"               # Pickup locker
    DRIVE_THRU = "DRIVE_THRU"       # Drive-through


# ============================================================================
# MODELS
# ============================================================================

class StoreLocation(Base):
    """
    Physical retail store location.

    Stores can serve as fulfillment nodes for:
    - BOPIS (Buy Online, Pick up In Store)
    - Ship-from-Store
    - BORIS (Buy Online, Return In Store)
    """
    __tablename__ = "store_locations"
    __table_args__ = (
        Index('ix_store_locations_geo', 'latitude', 'longitude'),
        Index('ix_store_locations_pincode', 'pincode'),
        UniqueConstraint('tenant_id', 'store_code', name='uq_store_code'),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
        index=True
    )

    # Identification
    store_code: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        index=True,
        comment="Unique store identifier e.g., ST-DEL-001"
    )
    name: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
        comment="Store display name"
    )
    store_type: Mapped[str] = mapped_column(
        String(30),
        default="STANDARD",
        nullable=False
    )
    status: Mapped[str] = mapped_column(
        String(30),
        default="ACTIVE",
        nullable=False,
        index=True
    )

    # Link to warehouse (store inventory)
    warehouse_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("warehouses.id", ondelete="SET NULL"),
        nullable=True,
        comment="Linked warehouse for inventory"
    )

    # Contact Information
    phone: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    email: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    manager_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    manager_phone: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)

    # Address
    address_line1: Mapped[str] = mapped_column(String(255), nullable=False)
    address_line2: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    city: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    state: Mapped[str] = mapped_column(String(100), nullable=False)
    pincode: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    country: Mapped[str] = mapped_column(String(50), default="India", nullable=False)

    # Geo Location
    latitude: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(10, 7),
        nullable=True
    )
    longitude: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(10, 7),
        nullable=True
    )

    # Store Hours (JSON for flexibility)
    operating_hours: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=True,
        comment="Daily operating hours e.g., {'monday': {'open': '10:00', 'close': '21:00'}}"
    )
    holiday_schedule: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=True,
        comment="Holiday closures"
    )

    # Omnichannel Capabilities
    bopis_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    ship_from_store_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    boris_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    endless_aisle_enabled: Mapped[bool] = mapped_column(Boolean, default=False)

    # Pickup Options
    curbside_pickup: Mapped[bool] = mapped_column(Boolean, default=False)
    locker_pickup: Mapped[bool] = mapped_column(Boolean, default=False)
    drive_thru: Mapped[bool] = mapped_column(Boolean, default=False)

    # BOPIS Settings
    bopis_prep_time_minutes: Mapped[int] = mapped_column(
        Integer,
        default=120,
        comment="Time to prepare order for pickup"
    )
    bopis_pickup_window_hours: Mapped[int] = mapped_column(
        Integer,
        default=72,
        comment="Hours customer has to pick up"
    )
    bopis_max_items: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        comment="Max items per BOPIS order"
    )

    # Ship-from-Store Settings
    sfs_max_orders_per_day: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        comment="Daily ship-from-store capacity"
    )
    sfs_priority: Mapped[int] = mapped_column(
        Integer,
        default=50,
        comment="Priority for ship-from-store allocation (1-100)"
    )
    sfs_serviceable_pincodes: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=True,
        comment="Pincodes this store can ship to"
    )

    # Performance Metrics
    avg_bopis_prep_time_minutes: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    bopis_completion_rate: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 2), nullable=True)
    sfs_completion_rate: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 2), nullable=True)
    customer_rating: Mapped[Optional[Decimal]] = mapped_column(Numeric(3, 2), nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    warehouse: Mapped[Optional["Warehouse"]] = relationship("Warehouse")
    bopis_orders: Mapped[List["BOPISOrder"]] = relationship(
        "BOPISOrder",
        back_populates="store",
        foreign_keys="BOPISOrder.store_id"
    )
    ship_from_store_orders: Mapped[List["ShipFromStoreOrder"]] = relationship(
        "ShipFromStoreOrder",
        back_populates="store"
    )
    store_returns: Mapped[List["StoreReturn"]] = relationship(
        "StoreReturn",
        back_populates="store"
    )

    @property
    def is_open(self) -> bool:
        """Check if store is currently open (simplified)."""
        return self.status == "ACTIVE"

    @property
    def full_address(self) -> str:
        """Get formatted full address."""
        parts = [self.address_line1]
        if self.address_line2:
            parts.append(self.address_line2)
        parts.extend([self.city, self.state, self.pincode])
        return ", ".join(parts)


class BOPISOrder(Base):
    """
    Buy Online, Pick up In Store order.

    Tracks the entire BOPIS lifecycle from order placement to pickup.
    """
    __tablename__ = "bopis_orders"
    __table_args__ = (
        Index('ix_bopis_orders_store_status', 'store_id', 'status'),
        Index('ix_bopis_orders_pickup_code', 'pickup_code'),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
        index=True
    )

    # References
    order_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("orders.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    store_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("store_locations.id", ondelete="RESTRICT"),
        nullable=False,
        index=True
    )
    customer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("customers.id", ondelete="RESTRICT"),
        nullable=False,
        index=True
    )

    # Status
    status: Mapped[str] = mapped_column(
        String(30),
        default="PENDING",
        nullable=False,
        index=True
    )

    # Pickup Details
    pickup_code: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        unique=True,
        index=True,
        comment="Code for customer to show at pickup"
    )
    pickup_location_type: Mapped[str] = mapped_column(
        String(30),
        default="IN_STORE",
        nullable=False
    )
    pickup_instructions: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Timing
    estimated_ready_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )
    actual_ready_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )
    pickup_deadline: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="When order expires if not picked up"
    )
    picked_up_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )

    # Customer Notifications
    ready_notification_sent: Mapped[bool] = mapped_column(Boolean, default=False)
    ready_notification_sent_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )
    reminder_sent: Mapped[bool] = mapped_column(Boolean, default=False)
    reminder_sent_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )

    # Items
    items: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=True,
        comment="BOPIS items with quantities"
    )
    total_items: Mapped[int] = mapped_column(Integer, default=0)
    picked_items: Mapped[int] = mapped_column(Integer, default=0)

    # Person who picks up
    picked_up_by_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    picked_up_by_phone: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    id_verification_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    id_verification_number: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    # Staff Assignment
    assigned_to: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )
    picked_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )
    handed_over_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )

    # Storage Location
    storage_location: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        comment="Where order is stored in store (shelf/bin)"
    )

    # Cancellation
    cancelled_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )
    cancellation_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    cancelled_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        nullable=True
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc)
    )

    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    order: Mapped["Order"] = relationship("Order")
    store: Mapped["StoreLocation"] = relationship("StoreLocation", back_populates="bopis_orders")
    customer: Mapped["Customer"] = relationship("Customer")
    reservations: Mapped[List["StoreInventoryReservation"]] = relationship(
        "StoreInventoryReservation",
        back_populates="bopis_order",
        foreign_keys="StoreInventoryReservation.bopis_order_id"
    )

    @property
    def is_expired(self) -> bool:
        """Check if pickup window has expired."""
        if self.pickup_deadline and self.status not in ["PICKED_UP", "CANCELLED"]:
            return datetime.now(timezone.utc) > self.pickup_deadline
        return False


class ShipFromStoreOrder(Base):
    """
    Ship-from-Store fulfillment order.

    Uses store inventory to fulfill online orders for shipping.
    """
    __tablename__ = "ship_from_store_orders"
    __table_args__ = (
        Index('ix_sfs_orders_store_status', 'store_id', 'status'),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
        index=True
    )

    # References
    order_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("orders.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    store_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("store_locations.id", ondelete="RESTRICT"),
        nullable=False,
        index=True
    )

    # Status
    status: Mapped[str] = mapped_column(
        String(30),
        default="PENDING",
        nullable=False,
        index=True
    )

    # Fulfillment Number
    sfs_number: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        unique=True,
        index=True
    )

    # Items
    items: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=True,
        comment="Items to be fulfilled from store"
    )
    total_items: Mapped[int] = mapped_column(Integer, default=0)
    picked_items: Mapped[int] = mapped_column(Integer, default=0)
    packed_items: Mapped[int] = mapped_column(Integer, default=0)

    # Shipping
    shipping_address: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=True
    )
    carrier_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        nullable=True
    )
    tracking_number: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    shipment_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        nullable=True
    )

    # Staff Assignment
    accepted_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )
    picked_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )
    packed_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )
    shipped_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )

    # Rejection
    rejection_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    rejected_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        nullable=True
    )
    rejected_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )

    # Timing
    accepted_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )
    picking_started_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )
    packed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )
    shipped_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )
    delivered_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )

    # SLA
    sla_deadline: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Deadline to ship"
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc)
    )

    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    order: Mapped["Order"] = relationship("Order")
    store: Mapped["StoreLocation"] = relationship("StoreLocation", back_populates="ship_from_store_orders")


class StoreInventoryReservation(Base):
    """
    Store inventory reservation for omnichannel orders.

    Reserves store inventory for BOPIS, ship-from-store, or endless aisle orders.
    """
    __tablename__ = "store_inventory_reservations"
    __table_args__ = (
        Index('ix_store_reservations_product', 'store_id', 'product_id'),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
        index=True
    )

    # Store and Product
    store_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("store_locations.id", ondelete="CASCADE"),
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
        nullable=True
    )
    sku: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # Quantity
    quantity_reserved: Mapped[int] = mapped_column(Integer, default=0)
    quantity_fulfilled: Mapped[int] = mapped_column(Integer, default=0)
    quantity_released: Mapped[int] = mapped_column(Integer, default=0)

    # Reservation Type
    reservation_type: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        comment="BOPIS, SHIP_FROM_STORE, ENDLESS_AISLE, HOLD"
    )

    # Reference to Order
    order_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("orders.id", ondelete="SET NULL"),
        nullable=True
    )
    bopis_order_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("bopis_orders.id", ondelete="SET NULL"),
        nullable=True
    )
    sfs_order_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("ship_from_store_orders.id", ondelete="SET NULL"),
        nullable=True
    )

    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    expires_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="When reservation expires if not fulfilled"
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc)
    )
    fulfilled_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )
    released_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )

    # Relationships
    store: Mapped["StoreLocation"] = relationship("StoreLocation")
    product: Mapped["Product"] = relationship("Product")
    order: Mapped[Optional["Order"]] = relationship("Order")
    bopis_order: Mapped[Optional["BOPISOrder"]] = relationship(
        "BOPISOrder",
        back_populates="reservations"
    )


class StoreReturn(Base):
    """
    In-store return for online orders (BORIS - Buy Online, Return In Store).

    Allows customers to return online purchases at physical stores.
    """
    __tablename__ = "store_returns"
    __table_args__ = (
        Index('ix_store_returns_status', 'store_id', 'status'),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
        index=True
    )

    # Return Number
    return_number: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        unique=True,
        index=True
    )

    # References
    order_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("orders.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    store_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("store_locations.id", ondelete="RESTRICT"),
        nullable=False,
        index=True
    )
    customer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("customers.id", ondelete="RESTRICT"),
        nullable=False,
        index=True
    )

    # Original Order Info
    original_channel: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        comment="Channel where original order was placed"
    )

    # Status
    status: Mapped[str] = mapped_column(
        String(30),
        default="INITIATED",
        nullable=False,
        index=True
    )

    # Items
    items: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=True,
        comment="Items being returned"
    )
    total_items: Mapped[int] = mapped_column(Integer, default=0)
    inspected_items: Mapped[int] = mapped_column(Integer, default=0)
    approved_items: Mapped[int] = mapped_column(Integer, default=0)
    rejected_items: Mapped[int] = mapped_column(Integer, default=0)

    # Return Reason
    return_reason: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    return_comments: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Refund
    refund_amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        default=0
    )
    refund_method: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        comment="ORIGINAL_PAYMENT, STORE_CREDIT, CASH"
    )
    refund_transaction_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    refunded_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )

    # Inspection
    inspection_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    item_condition: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        comment="NEW, GOOD, DAMAGED, DEFECTIVE"
    )

    # Store Staff
    received_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )
    inspected_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )
    approved_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )

    # Restocking
    restock_decision: Mapped[Optional[str]] = mapped_column(
        String(30),
        nullable=True,
        comment="RESTOCK, RETURN_TO_WAREHOUSE, DISPOSE, REFURBISH"
    )
    restocked_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )

    # Scheduling
    scheduled_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    scheduled_time_slot: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True
    )
    received_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )
    inspected_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc)
    )

    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    order: Mapped["Order"] = relationship("Order")
    store: Mapped["StoreLocation"] = relationship("StoreLocation", back_populates="store_returns")
    customer: Mapped["Customer"] = relationship("Customer")
