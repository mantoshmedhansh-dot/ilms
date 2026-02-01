"""Inventory models for stock management."""
from enum import Enum
from datetime import datetime, date, timezone
from sqlalchemy import Column, String, Text, Boolean, ForeignKey, Integer, DateTime, Date, Float, Numeric
from sqlalchemy import UniqueConstraint, CheckConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid

from app.database import Base, TimestampMixin


class StockItemStatus(str, Enum):
    """Stock item status enum."""
    AVAILABLE = "AVAILABLE"  # Ready for sale/allocation
    RESERVED = "RESERVED"  # Reserved for an order
    ALLOCATED = "ALLOCATED"  # Allocated to an order
    PICKED = "PICKED"  # Picked from bin
    PACKED = "PACKED"  # Packed and ready to ship
    IN_TRANSIT = "IN_TRANSIT"  # Being transferred
    SHIPPED = "SHIPPED"  # Shipped to customer
    DAMAGED = "DAMAGED"  # Damaged, needs inspection
    DEFECTIVE = "DEFECTIVE"  # Defective, needs return
    SOLD = "SOLD"  # Sold to customer (delivered)
    RETURNED = "RETURNED"  # Returned by customer
    QUARANTINE = "QUARANTINE"  # In quality hold
    SCRAPPED = "SCRAPPED"  # Written off


class StockItem(Base, TimestampMixin):
    """Individual stock item with serial number tracking."""

    __tablename__ = "stock_items"
    __table_args__ = (
        UniqueConstraint("serial_number", name="uq_stock_item_serial"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Product reference
    product_id = Column(UUID(as_uuid=True), ForeignKey("products.id"), nullable=False, index=True)
    variant_id = Column(UUID(as_uuid=True), ForeignKey("product_variants.id"))

    # Warehouse location
    warehouse_id = Column(UUID(as_uuid=True), ForeignKey("warehouses.id"), nullable=False, index=True)

    # Serial/Batch tracking
    serial_number = Column(String(100), unique=True, index=True)  # Unique per item
    batch_number = Column(String(50), index=True)  # Batch/Lot number
    barcode = Column(String(100), index=True)

    # Status
    status = Column(
        String(50), default="AVAILABLE", index=True,
        comment="AVAILABLE, RESERVED, ALLOCATED, PICKED, PACKED, IN_TRANSIT, SHIPPED, DAMAGED, DEFECTIVE, SOLD, RETURNED, QUARANTINE, SCRAPPED"
    )

    # Procurement info
    purchase_order_id = Column(UUID(as_uuid=True))  # Reference to PO
    grn_number = Column(String(50))  # Goods Receipt Note
    vendor_id = Column(UUID(as_uuid=True))  # Supplier reference

    # Cost tracking
    purchase_price = Column(Numeric(12, 2), default=0)
    landed_cost = Column(Numeric(12, 2), default=0)  # Including freight, duties etc.

    # Dates
    manufacturing_date = Column(Date)
    expiry_date = Column(Date)
    warranty_start_date = Column(Date)
    warranty_end_date = Column(Date)
    received_date = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    # Order allocation
    order_id = Column(UUID(as_uuid=True), ForeignKey("orders.id"))
    order_item_id = Column(UUID(as_uuid=True))
    allocated_at = Column(DateTime)

    # Channel allocation - tracks which channel this stock item is allocated to
    allocated_channel_id = Column(
        UUID(as_uuid=True),
        ForeignKey("sales_channels.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="Channel this stock item is allocated to"
    )

    # Location within warehouse (WMS integration)
    bin_id = Column(UUID(as_uuid=True), ForeignKey("warehouse_bins.id"), index=True)
    rack_location = Column(String(50))  # e.g., "A1-B2-C3" (legacy, use bin_id)
    bin_number = Column(String(50))  # legacy, use bin_id

    # Quality
    quality_grade = Column(String(20))  # A, B, C etc.
    inspection_status = Column(String(50))
    inspection_notes = Column(Text)

    # Tracking
    last_movement_date = Column(DateTime)
    last_counted_date = Column(DateTime)

    notes = Column(Text)

    # Timestamps
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    product = relationship("Product", back_populates="stock_items")
    variant = relationship("ProductVariant")
    warehouse = relationship("Warehouse", back_populates="stock_items")
    bin = relationship("WarehouseBin", back_populates="stock_items")
    order = relationship("Order")

    def __repr__(self):
        return f"<StockItem {self.serial_number or self.id}>"


class InventorySummary(Base, TimestampMixin):
    """Aggregated inventory summary per product per warehouse."""

    __tablename__ = "inventory_summary"
    __table_args__ = (
        UniqueConstraint("warehouse_id", "product_id", "variant_id", name="uq_inventory_summary"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    warehouse_id = Column(UUID(as_uuid=True), ForeignKey("warehouses.id"), nullable=False, index=True)
    product_id = Column(UUID(as_uuid=True), ForeignKey("products.id"), nullable=False, index=True)
    variant_id = Column(UUID(as_uuid=True), ForeignKey("product_variants.id"))

    # Stock levels
    total_quantity = Column(Integer, default=0)
    available_quantity = Column(Integer, default=0)
    reserved_quantity = Column(Integer, default=0)
    allocated_quantity = Column(Integer, default=0)
    damaged_quantity = Column(Integer, default=0)
    in_transit_quantity = Column(Integer, default=0)

    # Thresholds
    reorder_level = Column(Integer, default=10)
    minimum_stock = Column(Integer, default=5)
    maximum_stock = Column(Integer, default=1000)

    # Valuation
    average_cost = Column(Float, default=0)
    total_value = Column(Float, default=0)

    # Last activity
    last_stock_in_date = Column(DateTime)
    last_stock_out_date = Column(DateTime)
    last_audit_date = Column(DateTime)

    # Relationships
    warehouse = relationship("Warehouse")
    product = relationship("Product")
    variant = relationship("ProductVariant")

    @property
    def is_low_stock(self) -> bool:
        """Check if stock is below reorder level."""
        return self.available_quantity <= self.reorder_level

    @property
    def is_out_of_stock(self) -> bool:
        """Check if out of stock."""
        return self.available_quantity == 0


class StockMovementType(str, Enum):
    """Stock movement type enum."""
    RECEIPT = "RECEIPT"  # GRN - Goods received
    ISSUE = "ISSUE"  # Goods issued (sale, transfer out)
    TRANSFER_IN = "TRANSFER_IN"
    TRANSFER_OUT = "TRANSFER_OUT"
    RETURN_IN = "RETURN_IN"  # Customer return
    RETURN_OUT = "RETURN_OUT"  # Return to vendor
    ADJUSTMENT_PLUS = "ADJUSTMENT_PLUS"
    ADJUSTMENT_MINUS = "ADJUSTMENT_MINUS"
    DAMAGE = "DAMAGE"
    SCRAP = "SCRAP"
    CYCLE_COUNT = "CYCLE_COUNT"


class StockMovement(Base, TimestampMixin):
    """Stock movement history/ledger."""

    __tablename__ = "stock_movements"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Reference
    movement_number = Column(String(50), unique=True, nullable=False, index=True)
    movement_type = Column(
        String(50), nullable=False, index=True,
        comment="RECEIPT, ISSUE, TRANSFER_IN, TRANSFER_OUT, RETURN_IN, RETURN_OUT, ADJUSTMENT_PLUS, ADJUSTMENT_MINUS, DAMAGE, SCRAP, CYCLE_COUNT"
    )
    movement_date = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    # Location
    warehouse_id = Column(UUID(as_uuid=True), ForeignKey("warehouses.id"), nullable=False, index=True)

    # Product
    product_id = Column(UUID(as_uuid=True), ForeignKey("products.id"), nullable=False)
    variant_id = Column(UUID(as_uuid=True), ForeignKey("product_variants.id"))
    stock_item_id = Column(UUID(as_uuid=True), ForeignKey("stock_items.id"))

    # Quantity
    quantity = Column(Integer, nullable=False)  # Positive for in, negative for out

    # Stock levels after movement
    balance_before = Column(Integer, default=0)
    balance_after = Column(Integer, default=0)

    # Related documents
    reference_type = Column(String(50))  # order, transfer, adjustment, grn, etc.
    reference_id = Column(UUID(as_uuid=True))
    reference_number = Column(String(100))

    # Cost
    unit_cost = Column(Float, default=0)
    total_cost = Column(Float, default=0)

    # User
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"))

    notes = Column(Text)

    # Relationships
    warehouse = relationship("Warehouse")
    product = relationship("Product")
    stock_item = relationship("StockItem")
    creator = relationship("User")

    def __repr__(self):
        return f"<StockMovement {self.movement_number}>"
