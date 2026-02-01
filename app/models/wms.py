"""WMS (Warehouse Management System) models for zone, bin, and putaway management."""
import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import TYPE_CHECKING, Optional, List

from sqlalchemy import String, Boolean, DateTime, ForeignKey, Integer, Text, Float
from sqlalchemy import UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.warehouse import Warehouse
    from app.models.category import Category
    from app.models.inventory import StockItem


class ZoneType(str, Enum):
    """Warehouse zone type enumeration."""
    RECEIVING = "RECEIVING"       # Inbound goods receiving area
    STORAGE = "STORAGE"          # Main storage area
    PICKING = "PICKING"          # Order picking area
    PACKING = "PACKING"          # Packing station area
    SHIPPING = "SHIPPING"        # Outbound shipping area
    RETURNS = "RETURNS"          # Returns processing area
    QUARANTINE = "QUARANTINE"    # Quality hold area
    COLD_STORAGE = "COLD_STORAGE"  # Temperature controlled
    HAZMAT = "HAZMAT"            # Hazardous materials


class BinType(str, Enum):
    """Bin/Storage location type enumeration."""
    SHELF = "SHELF"              # Standard shelf location
    RACK = "RACK"                # Pallet rack
    FLOOR = "FLOOR"              # Floor storage
    PALLET = "PALLET"            # Pallet location
    CONTAINER = "CONTAINER"      # Storage container
    CAGE = "CAGE"                # Security cage
    BULK = "BULK"                # Bulk storage


class WarehouseZone(Base):
    """
    Warehouse Zone model.
    Logical division of warehouse into functional areas.
    """
    __tablename__ = "warehouse_zones"
    __table_args__ = (
        UniqueConstraint("warehouse_id", "zone_code", name="uq_warehouse_zone_code"),
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

    # Zone identification
    zone_code: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        index=True,
        comment="Zone code e.g., A, B, RCV, PACK"
    )
    zone_name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Zone type
    zone_type: Mapped[str] = mapped_column(
        String(50),
        default="STORAGE",
        nullable=False,
        comment="RECEIVING, STORAGE, PICKING, PACKING, SHIPPING, RETURNS, QUARANTINE, COLD_STORAGE, HAZMAT"
    )

    # Physical attributes
    floor_number: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    area_sqft: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Capacity
    max_capacity: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        comment="Maximum number of items/units"
    )
    current_capacity: Mapped[int] = mapped_column(Integer, default=0)

    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_pickable: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        comment="Can items be picked from this zone"
    )
    is_receivable: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        comment="Can items be received into this zone"
    )

    # Display order
    sort_order: Mapped[int] = mapped_column(Integer, default=0)

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
    warehouse: Mapped["Warehouse"] = relationship("Warehouse", back_populates="zones")
    bins: Mapped[List["WarehouseBin"]] = relationship(
        "WarehouseBin",
        back_populates="zone",
        cascade="all, delete-orphan"
    )
    putaway_rules: Mapped[List["PutAwayRule"]] = relationship(
        "PutAwayRule",
        back_populates="target_zone",
        cascade="all, delete-orphan"
    )

    @property
    def utilization_percent(self) -> float:
        """Calculate zone utilization percentage."""
        if self.max_capacity and self.max_capacity > 0:
            return (self.current_capacity / self.max_capacity) * 100
        return 0.0

    def __repr__(self) -> str:
        return f"<WarehouseZone(code='{self.zone_code}', type='{self.zone_type}')>"


class WarehouseBin(Base):
    """
    Warehouse Bin/Storage Location model.
    Specific storage locations within a zone.
    """
    __tablename__ = "warehouse_bins"
    __table_args__ = (
        UniqueConstraint("warehouse_id", "bin_code", name="uq_warehouse_bin_code"),
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

    zone_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("warehouse_zones.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )

    # Bin identification
    bin_code: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
        comment="Bin code e.g., A1-B2-C3, RACK-01-SHELF-02"
    )
    bin_name: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    barcode: Mapped[Optional[str]] = mapped_column(
        String(100),
        unique=True,
        nullable=True,
        index=True
    )

    # Location breakdown
    aisle: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    rack: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    shelf: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    position: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)

    # Bin type
    bin_type: Mapped[str] = mapped_column(
        String(50),
        default="SHELF",
        nullable=False,
        comment="SHELF, RACK, FLOOR, PALLET, CONTAINER, CAGE, BULK"
    )

    # Dimensions (in cm)
    length: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    width: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    height: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Capacity
    max_capacity: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        comment="Maximum items/units"
    )
    max_weight_kg: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    current_items: Mapped[int] = mapped_column(Integer, default=0)
    current_weight_kg: Mapped[float] = mapped_column(Float, default=0.0)

    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_reserved: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        comment="Reserved for specific product/order"
    )
    is_pickable: Mapped[bool] = mapped_column(Boolean, default=True)
    is_receivable: Mapped[bool] = mapped_column(Boolean, default=True)

    # Reserved for specific product (optional)
    reserved_product_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("products.id", ondelete="SET NULL"),
        nullable=True
    )

    # Pick sequence (for optimized picking path)
    pick_sequence: Mapped[int] = mapped_column(
        Integer,
        default=0,
        comment="Order in picking route"
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
    last_activity_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    warehouse: Mapped["Warehouse"] = relationship("Warehouse", back_populates="bins")
    zone: Mapped[Optional["WarehouseZone"]] = relationship(
        "WarehouseZone",
        back_populates="bins"
    )
    stock_items: Mapped[List["StockItem"]] = relationship(
        "StockItem",
        back_populates="bin",
        foreign_keys="StockItem.bin_id"
    )

    @property
    def is_empty(self) -> bool:
        """Check if bin is empty."""
        return self.current_items == 0

    @property
    def is_full(self) -> bool:
        """Check if bin is at capacity."""
        if self.max_capacity:
            return self.current_items >= self.max_capacity
        return False

    @property
    def available_capacity(self) -> Optional[int]:
        """Get remaining capacity."""
        if self.max_capacity:
            return self.max_capacity - self.current_items
        return None

    def __repr__(self) -> str:
        return f"<WarehouseBin(code='{self.bin_code}', items={self.current_items})>"


class PutAwayRule(Base):
    """
    PutAway Rule model.
    Defines automatic bin assignment rules for received goods.
    """
    __tablename__ = "putaway_rules"
    __table_args__ = (
        UniqueConstraint(
            "warehouse_id", "category_id", "priority",
            name="uq_putaway_rule"
        ),
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

    # Rule name/description
    rule_name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Criteria - what to match
    category_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("categories.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    product_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("products.id", ondelete="SET NULL"),
        nullable=True
    )
    brand_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("brands.id", ondelete="SET NULL"),
        nullable=True
    )

    # Target location
    target_zone_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("warehouse_zones.id", ondelete="CASCADE"),
        nullable=False
    )
    target_bin_pattern: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        comment="Bin code pattern e.g., A1-*, RACK-01-*"
    )

    # Priority (lower = higher priority)
    priority: Mapped[int] = mapped_column(
        Integer,
        default=100,
        comment="Lower value = higher priority"
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
    warehouse: Mapped["Warehouse"] = relationship("Warehouse")
    category: Mapped[Optional["Category"]] = relationship("Category")
    target_zone: Mapped["WarehouseZone"] = relationship(
        "WarehouseZone",
        back_populates="putaway_rules"
    )

    def __repr__(self) -> str:
        return f"<PutAwayRule(name='{self.rule_name}', priority={self.priority})>"
