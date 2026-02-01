"""Picklist models for warehouse order picking operations."""
import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import TYPE_CHECKING, Optional, List

from sqlalchemy import String, Boolean, DateTime, ForeignKey, Integer, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.warehouse import Warehouse
    from app.models.order import Order, OrderItem
    from app.models.product import Product, ProductVariant
    from app.models.user import User


class PicklistStatus(str, Enum):
    """Picklist status enumeration."""
    PENDING = "PENDING"           # Generated, waiting to be picked
    ASSIGNED = "ASSIGNED"         # Assigned to picker
    IN_PROGRESS = "IN_PROGRESS"   # Picking in progress
    COMPLETED = "COMPLETED"       # All items picked
    PARTIALLY_PICKED = "PARTIALLY_PICKED"  # Some items picked
    CANCELLED = "CANCELLED"       # Picklist cancelled


class PicklistType(str, Enum):
    """Picklist type enumeration."""
    SINGLE_ORDER = "SINGLE_ORDER"   # One order per picklist
    BATCH = "BATCH"                 # Multiple orders per picklist
    WAVE = "WAVE"                   # Wave picking (by zone/product)


class Picklist(Base):
    """
    Picklist model for warehouse picking operations.
    Groups orders/items for efficient warehouse picking.
    """
    __tablename__ = "picklists"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )

    # Identification
    picklist_number: Mapped[str] = mapped_column(
        String(30),
        unique=True,
        nullable=False,
        index=True,
        comment="Unique picklist number e.g., PL-20240101-0001"
    )

    # Warehouse
    warehouse_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("warehouses.id", ondelete="RESTRICT"),
        nullable=False,
        index=True
    )

    # Status
    status: Mapped[str] = mapped_column(
        String(50),
        default="PENDING",
        nullable=False,
        index=True,
        comment="PENDING, ASSIGNED, IN_PROGRESS, COMPLETED, PARTIALLY_PICKED, CANCELLED"
    )

    # Type
    picklist_type: Mapped[str] = mapped_column(
        String(50),
        default="SINGLE_ORDER",
        nullable=False,
        comment="SINGLE_ORDER, BATCH, WAVE"
    )

    # Priority (1 = highest)
    priority: Mapped[int] = mapped_column(
        Integer,
        default=5,
        comment="Priority 1-10, lower is higher priority"
    )

    # Counts
    total_orders: Mapped[int] = mapped_column(Integer, default=0)
    total_items: Mapped[int] = mapped_column(
        Integer,
        default=0,
        comment="Total unique items/SKUs"
    )
    total_quantity: Mapped[int] = mapped_column(
        Integer,
        default=0,
        comment="Total quantity to pick"
    )
    picked_quantity: Mapped[int] = mapped_column(Integer, default=0)

    # Assignment
    assigned_to: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        comment="Assigned picker"
    )
    assigned_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Timestamps
    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False
    )
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    cancelled_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Notes
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    cancellation_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    warehouse: Mapped["Warehouse"] = relationship("Warehouse")
    assigned_user: Mapped[Optional["User"]] = relationship(
        "User",
        foreign_keys=[assigned_to]
    )
    created_by_user: Mapped[Optional["User"]] = relationship(
        "User",
        foreign_keys=[created_by]
    )
    items: Mapped[List["PicklistItem"]] = relationship(
        "PicklistItem",
        back_populates="picklist",
        cascade="all, delete-orphan",
        order_by="PicklistItem.pick_sequence"
    )

    @property
    def is_complete(self) -> bool:
        """Check if all items are picked."""
        return self.picked_quantity >= self.total_quantity

    @property
    def pick_progress(self) -> float:
        """Get picking progress percentage."""
        if self.total_quantity > 0:
            return (self.picked_quantity / self.total_quantity) * 100
        return 0.0

    @property
    def pending_quantity(self) -> int:
        """Get remaining quantity to pick."""
        return max(0, self.total_quantity - self.picked_quantity)

    def __repr__(self) -> str:
        return f"<Picklist(number='{self.picklist_number}', status='{self.status}')>"


class PicklistItem(Base):
    """
    Picklist item model.
    Individual items/SKUs to be picked.
    """
    __tablename__ = "picklist_items"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )

    picklist_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("picklists.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Order reference
    order_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("orders.id", ondelete="RESTRICT"),
        nullable=False,
        index=True
    )
    order_item_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("order_items.id", ondelete="RESTRICT"),
        nullable=False
    )

    # Product reference
    product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("products.id", ondelete="RESTRICT"),
        nullable=False
    )
    variant_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("product_variants.id", ondelete="SET NULL"),
        nullable=True
    )

    # Product snapshot
    sku: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    product_name: Mapped[str] = mapped_column(String(255), nullable=False)
    variant_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Bin location
    bin_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("warehouse_bins.id", ondelete="SET NULL"),
        nullable=True
    )
    bin_location: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        comment="Bin code/location e.g., A1-B2-C3"
    )

    # Quantities
    quantity_required: Mapped[int] = mapped_column(Integer, nullable=False)
    quantity_picked: Mapped[int] = mapped_column(Integer, default=0)
    quantity_short: Mapped[int] = mapped_column(
        Integer,
        default=0,
        comment="Quantity not found/short"
    )

    # Picking status
    is_picked: Mapped[bool] = mapped_column(Boolean, default=False)
    is_short: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        comment="Item not found in bin"
    )

    # Serial numbers picked (comma-separated)
    picked_serials: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Comma-separated serial numbers"
    )

    # Pick sequence for optimized route
    pick_sequence: Mapped[int] = mapped_column(
        Integer,
        default=0,
        comment="Order in picking route"
    )

    # Picked by
    picked_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )
    picked_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Notes
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    short_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

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
    picklist: Mapped["Picklist"] = relationship(
        "Picklist",
        back_populates="items"
    )
    order: Mapped["Order"] = relationship("Order")
    order_item: Mapped["OrderItem"] = relationship("OrderItem")
    product: Mapped["Product"] = relationship("Product")
    variant: Mapped[Optional["ProductVariant"]] = relationship("ProductVariant")
    picked_by_user: Mapped[Optional["User"]] = relationship("User")

    @property
    def is_complete(self) -> bool:
        """Check if item is fully picked."""
        return self.quantity_picked >= self.quantity_required

    @property
    def pending_quantity(self) -> int:
        """Get remaining quantity to pick."""
        return max(0, self.quantity_required - self.quantity_picked)

    def __repr__(self) -> str:
        return f"<PicklistItem(sku='{self.sku}', qty={self.quantity_required}, picked={self.quantity_picked})>"
