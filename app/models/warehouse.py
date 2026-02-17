"""Warehouse model for inventory management."""
from enum import Enum
from datetime import datetime, timezone
from sqlalchemy import Column, String, Text, Boolean, ForeignKey, Float, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid

from app.database import Base, TimestampMixin


class WarehouseType(str, Enum):
    """Warehouse type enum."""
    MAIN = "MAIN"  # Central warehouse
    REGIONAL = "REGIONAL"  # Regional distribution center
    SERVICE_CENTER = "SERVICE_CENTER"  # Service center warehouse
    DEALER = "DEALER"  # Dealer warehouse
    VIRTUAL = "VIRTUAL"  # Virtual/Transit warehouse


class Warehouse(Base, TimestampMixin):
    """Warehouse model for storing inventory locations."""

    __tablename__ = "warehouses"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    code = Column(String(20), unique=True, nullable=False, index=True)
    name = Column(String(200), nullable=False)
    warehouse_type = Column(String(50), default="REGIONAL")

    # Address
    address_line1 = Column(String(255), nullable=False)
    address_line2 = Column(String(255))
    city = Column(String(100), nullable=False)
    state = Column(String(100), nullable=False)
    pincode = Column(String(10), nullable=False)
    country = Column(String(100), default="India")

    # Geo coordinates
    latitude = Column(Float)
    longitude = Column(Float)

    # Contact info
    contact_name = Column(String(100))
    contact_phone = Column(String(20))
    contact_email = Column(String(100))

    # Region association
    region_id = Column(UUID(as_uuid=True), ForeignKey("regions.id"))

    # Manager
    manager_id = Column(UUID(as_uuid=True), ForeignKey("users.id"))

    # Capacity
    total_capacity = Column(Float, default=0)  # In square feet or units
    current_utilization = Column(Float, default=0)

    # Status
    is_active = Column(Boolean, default=True)
    is_default = Column(Boolean, default=False)  # Default receiving warehouse
    can_fulfill_orders = Column(Boolean, default=True)  # Can ship to customers
    can_receive_transfers = Column(Boolean, default=True)

    notes = Column(Text)

    # Timestamps
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    region = relationship("Region", back_populates="warehouses")
    manager = relationship("User", foreign_keys=[manager_id])
    stock_items = relationship("StockItem", back_populates="warehouse", cascade="all, delete-orphan")
    outgoing_transfers = relationship(
        "StockTransfer",
        foreign_keys="StockTransfer.from_warehouse_id",
        back_populates="from_warehouse"
    )
    incoming_transfers = relationship(
        "StockTransfer",
        foreign_keys="StockTransfer.to_warehouse_id",
        back_populates="to_warehouse"
    )
    # Cost center link
    cost_centers = relationship(
        "CostCenter",
        back_populates="warehouse"
    )
    # WMS relationships
    zones = relationship(
        "WarehouseZone",
        back_populates="warehouse",
        cascade="all, delete-orphan"
    )
    bins = relationship(
        "WarehouseBin",
        back_populates="warehouse",
        cascade="all, delete-orphan"
    )

    @property
    def full_address(self) -> str:
        """Get formatted full address."""
        parts = [self.address_line1]
        if self.address_line2:
            parts.append(self.address_line2)
        parts.extend([self.city, self.state, self.pincode])
        return ", ".join(parts)

    def __repr__(self):
        return f"<Warehouse {self.code}: {self.name}>"
