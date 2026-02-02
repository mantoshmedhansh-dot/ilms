"""
Serialization Models for Product and Spare Parts Barcodes

Barcode Structure: APFSZAIEL000001 (15 characters)
- AP: Brand Prefix (Aquapurite)
- FS: Supplier Code (2 letters)
- Z: Year Code (A=2000, Z=2025, AA=2026...)
- A: Month Code (A=Jan, L=Dec)
- IEL: Model Code (3 letters)
- 000001: Serial Number (6 digits, 000001-999999)
"""

import enum
import uuid
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import String, Integer, Boolean, DateTime, ForeignKey, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship, Mapped, mapped_column
from app.database import Base


class SerialStatus(str, enum.Enum):
    """Status of a serial/barcode"""
    GENERATED = "GENERATED"      # Serial generated, not yet printed
    PRINTED = "PRINTED"          # Barcode printed/exported
    SENT_TO_VENDOR = "SENT_TO_VENDOR"  # Sent to vendor for application
    RECEIVED = "RECEIVED"        # Received in GRN, scanned
    ASSIGNED = "ASSIGNED"        # Assigned to stock item
    SOLD = "SOLD"               # Item sold to customer
    RETURNED = "RETURNED"        # Item returned
    DAMAGED = "DAMAGED"          # Item damaged/scrapped
    CANCELLED = "CANCELLED"      # Serial cancelled


class ItemType(str, enum.Enum):
    """Type of item being serialized"""
    FINISHED_GOODS = "FG"        # Finished Goods (Water Purifiers)
    SPARE_PART = "SP"            # Spare Parts (Sub Assemblies)
    COMPONENT = "CO"             # Components (Electrical, etc.)


class SerialSequence(Base):
    """
    LEGACY: Tracks serial number by model + supplier + year + month.
    Kept for backward compatibility with existing data.
    New POs should use ProductSerialSequence instead.
    """
    __tablename__ = "serial_sequences"

    # Production uses VARCHAR for id, not UUID
    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4())
    )

    # Product identification
    product_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("products.id"),
        nullable=True
    )
    model_code: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    item_type: Mapped[str] = mapped_column(String(10), default="FG", comment="FG, SP, CO")

    # Sequence key components
    supplier_code: Mapped[str] = mapped_column(String(2), nullable=False, index=True)
    year_code: Mapped[str] = mapped_column(String(2), nullable=False)
    month_code: Mapped[str] = mapped_column(String(1), nullable=False)

    # Sequence tracking
    last_serial: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_generated: Mapped[int] = mapped_column(Integer, default=0)

    # Metadata
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    product = relationship("Product", backref="serial_sequences")

    def __repr__(self):
        return f"<SerialSequence {self.supplier_code}{self.year_code}{self.month_code}{self.model_code}: {self.last_serial}>"


class ProductSerialSequence(Base):
    """
    Tracks serial numbers at PRODUCT/MODEL level.
    Each product model (Aura, Elige, etc.) has its own independent serial sequence.

    Serial numbers are continuous and do NOT reset by year/month.
    Each model can have serials from 1 to 99,999,999.

    Separate sequences for FG and SP:
    - FG Aura (IEL): 00000001 to 99999999
    - SP Aura (IEL): 00000001 to 99999999 (separate sequence)

    Example:
    - FG: Aura (IEL): 00000001 to 99999999
    - FG: Elige (ELG): 00000001 to 99999999
    - SP: Motor Assembly (MTR): 00000001 to 99999999
    """
    __tablename__ = "product_serial_sequences"

    # Production uses VARCHAR for id, not UUID
    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4())
    )

    # Product identification - unique per (model_code + item_type) combination
    product_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("products.id"),
        nullable=True
    )
    model_code: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    item_type: Mapped[str] = mapped_column(String(10), nullable=False, default="FG", comment="FG, SP, CO")

    # Unique constraint on model_code + item_type (FG and SP can have same model_code)
    __table_args__ = (
        UniqueConstraint('model_code', 'item_type', name='uq_model_code_item_type'),
    )

    # Product info (denormalized for quick access)
    product_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    product_sku: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    # Sequence tracking - continuous across all time
    last_serial: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_generated: Mapped[int] = mapped_column(Integer, default=0)
    max_serial: Mapped[int] = mapped_column(Integer, default=99999999)

    # Metadata
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    product = relationship("Product", backref="product_serial_sequence")

    @property
    def available_serials(self):
        """How many serial numbers are still available"""
        return self.max_serial - self.last_serial

    @property
    def utilization_percentage(self):
        """Percentage of serial numbers used"""
        if self.max_serial > 0:
            return (self.last_serial / self.max_serial) * 100
        return 0

    def __repr__(self):
        return f"<ProductSerialSequence {self.model_code}: {self.last_serial}/{self.max_serial}>"


class POSerial(Base):
    """
    Individual serial numbers/barcodes generated for Purchase Orders.
    Each row represents one unique barcode that will be applied to one unit.
    """
    __tablename__ = "po_serials"

    # Production uses VARCHAR for id, not UUID
    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4())
    )

    # PO linkage - using UUID to match multi-tenant database schema
    po_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("purchase_orders.id"),
        nullable=False,
        index=True
    )
    po_item_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("purchase_order_items.id"),
        nullable=True
    )

    # Product identification - using UUID to match multi-tenant database schema
    product_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("products.id"),
        nullable=True
    )
    product_sku: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    model_code: Mapped[str] = mapped_column(String(10), nullable=False)
    item_type: Mapped[str] = mapped_column(String(10), default="FG", comment="FG, SP, CO")

    # Barcode components
    brand_prefix: Mapped[str] = mapped_column(String(2), default="AP")
    supplier_code: Mapped[str] = mapped_column(String(2), nullable=False)
    year_code: Mapped[str] = mapped_column(String(2), nullable=False)
    month_code: Mapped[str] = mapped_column(String(1), nullable=False)
    serial_number: Mapped[int] = mapped_column(Integer, nullable=False)

    # Full barcode (computed: APFSZAIEL000001)
    barcode: Mapped[str] = mapped_column(String(20), unique=True, nullable=False, index=True)

    # Status tracking
    status: Mapped[str] = mapped_column(String(30), default="GENERATED", comment="GENERATED, PRINTED, SENT_TO_VENDOR, RECEIVED, ASSIGNED, SOLD, RETURNED, DAMAGED, CANCELLED")

    # GRN linkage (when received) - using UUID to match multi-tenant database schema
    grn_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("goods_receipt_notes.id"),
        nullable=True
    )
    grn_item_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True)
    received_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    received_by: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True)

    # Stock item linkage (when assigned to inventory) - using UUID to match multi-tenant database schema
    stock_item_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("stock_items.id"),
        nullable=True
    )
    assigned_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Sale linkage (when sold) - UUID for multi-tenant database
    order_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True)
    order_item_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True)
    sold_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    customer_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True)

    # Warranty tracking
    warranty_start_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    warranty_end_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Metadata
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    purchase_order = relationship("PurchaseOrder", backref="serials")
    product = relationship("Product", backref="serials")
    stock_item = relationship("StockItem", backref="serial_info")
    grn = relationship("GoodsReceiptNote", backref="scanned_serials")

    def __repr__(self):
        return f"<POSerial {self.barcode} ({self.status})>"


class ModelCodeReference(Base):
    """
    Reference table mapping product SKUs to their 3-letter model codes.
    This helps in generating correct barcodes for products.
    """
    __tablename__ = "model_code_references"

    # Production uses VARCHAR for id, not UUID
    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4())
    )

    # Product linkage
    product_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("products.id"),
        nullable=True,
        unique=True
    )
    product_sku: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, index=True)

    # FG/Item Code (full code like WPRAIEL001)
    fg_code: Mapped[Optional[str]] = mapped_column(String(20), nullable=True, unique=True, index=True)

    # Model code for barcode (3 letters: IEL, IPR, PRG)
    model_code: Mapped[str] = mapped_column(String(10), nullable=False, index=True)

    # Note: item_type column removed - does not exist in production database
    # Item type is determined from fg_code prefix (WP=FG, SP=SP)

    # Description
    description: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Active flag
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Metadata
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Relationship
    product = relationship("Product", backref="model_code_ref")

    def __repr__(self):
        return f"<ModelCodeReference {self.fg_code} -> {self.model_code}>"


class SupplierCode(Base):
    """
    Supplier codes for barcode generation.
    Each supplier gets a unique 2-letter code.
    """
    __tablename__ = "supplier_codes"

    # Production uses VARCHAR for id, not UUID
    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4())
    )

    # Vendor linkage
    vendor_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("vendors.id"),
        nullable=True,
        unique=True
    )

    # 2-letter supplier code
    code: Mapped[str] = mapped_column(String(2), unique=True, nullable=False, index=True)

    # Supplier name
    name: Mapped[str] = mapped_column(String(100), nullable=False)

    # Description
    description: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Active flag
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Metadata
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Relationship
    vendor = relationship("Vendor", backref="supplier_code_ref")

    def __repr__(self):
        return f"<SupplierCode {self.code} ({self.name})>"
