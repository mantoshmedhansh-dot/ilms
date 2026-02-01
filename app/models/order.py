import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import TYPE_CHECKING, Optional, List
from decimal import Decimal

from sqlalchemy import String, Boolean, DateTime, ForeignKey, Integer, Text, Numeric, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB

from app.database import Base

if TYPE_CHECKING:
    from app.models.customer import Customer
    from app.models.product import Product, ProductVariant
    from app.models.user import User
    from app.models.region import Region
    from app.models.warehouse import Warehouse
    from app.models.shipment import Shipment
    from app.models.dealer import Dealer
    from app.models.return_order import ReturnOrder, Refund


class OrderStatus(str, Enum):
    """Order status enumeration - Vinculum OMS style flow."""
    # Initial states
    NEW = "NEW"                       # Order received
    PENDING_PAYMENT = "PENDING_PAYMENT"  # Awaiting payment confirmation
    CONFIRMED = "CONFIRMED"           # Payment confirmed, ready for processing

    # Warehouse processing states
    ALLOCATED = "ALLOCATED"           # Inventory allocated from warehouse
    PICKLIST_CREATED = "PICKLIST_CREATED"  # Added to picklist for picking
    PICKING = "PICKING"               # Currently being picked
    PICKED = "PICKED"                 # All items picked
    PACKING = "PACKING"               # Being packed
    PACKED = "PACKED"                 # Packing complete

    # Shipping states
    MANIFESTED = "MANIFESTED"         # Added to manifest for handover
    READY_TO_SHIP = "READY_TO_SHIP"   # Manifest confirmed, awaiting pickup
    SHIPPED = "SHIPPED"               # Handed to transporter
    IN_TRANSIT = "IN_TRANSIT"         # In transit to destination
    OUT_FOR_DELIVERY = "OUT_FOR_DELIVERY"  # Out for final delivery

    # Final states
    DELIVERED = "DELIVERED"           # Successfully delivered
    PARTIALLY_DELIVERED = "PARTIALLY_DELIVERED"  # Some items delivered

    # Return states
    RTO_INITIATED = "RTO_INITIATED"   # Return to origin initiated
    RTO_IN_TRANSIT = "RTO_IN_TRANSIT"  # RTO shipment in transit
    RTO_DELIVERED = "RTO_DELIVERED"   # Returned to warehouse
    RETURNED = "RETURNED"             # Customer return

    # Cancel/Refund
    CANCELLED = "CANCELLED"           # Order cancelled
    REFUNDED = "REFUNDED"             # Refund processed

    # Hold states
    ON_HOLD = "ON_HOLD"               # Order on hold (payment/fraud check)


class PaymentStatus(str, Enum):
    """Payment status enumeration."""
    PENDING = "PENDING"
    AUTHORIZED = "AUTHORIZED"
    CAPTURED = "CAPTURED"
    PARTIALLY_PAID = "PARTIALLY_PAID"
    PAID = "PAID"
    FAILED = "FAILED"
    REFUNDED = "REFUNDED"
    CANCELLED = "CANCELLED"


class PaymentMethod(str, Enum):
    """Payment method enumeration."""
    CASH = "CASH"
    CARD = "CARD"
    UPI = "UPI"
    NET_BANKING = "NET_BANKING"
    WALLET = "WALLET"
    EMI = "EMI"
    COD = "COD"
    CREDIT = "CREDIT"
    CHEQUE = "CHEQUE"


class OrderSource(str, Enum):
    """Order source/channel."""
    WEBSITE = "WEBSITE"
    MOBILE_APP = "MOBILE_APP"
    STORE = "STORE"
    PHONE = "PHONE"
    DEALER = "DEALER"
    AMAZON = "AMAZON"
    FLIPKART = "FLIPKART"
    OTHER = "OTHER"


class Order(Base):
    """
    Order model for sales management.
    Tracks orders from creation to delivery.
    """
    __tablename__ = "orders"
    __table_args__ = (
        Index('ix_order_status_created', 'status', 'created_at'),
        Index('ix_order_customer_created', 'customer_id', 'created_at'),
        Index('ix_order_payment_status', 'payment_status', 'created_at'),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )

    # Order Identification
    order_number: Mapped[str] = mapped_column(
        String(30),
        unique=True,
        nullable=False,
        index=True
    )

    # Customer
    customer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("customers.id", ondelete="RESTRICT"),
        nullable=False
    )

    # Status
    status: Mapped[str] = mapped_column(
        String(50),
        default="NEW",
        nullable=False,
        index=True,
        comment="Order status: NEW, PENDING_PAYMENT, CONFIRMED, ALLOCATED, etc."
    )

    # Source/Channel
    source: Mapped[str] = mapped_column(
        String(50),
        default="WEBSITE",
        nullable=False,
        comment="WEBSITE, MOBILE_APP, STORE, PHONE, DEALER, AMAZON, FLIPKART, OTHER"
    )

    # Warehouse (fulfillment location)
    warehouse_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("warehouses.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="Assigned warehouse for fulfillment"
    )

    # Dealer (for B2B orders)
    dealer_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("dealers.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="For dealer/distributor orders"
    )

    # Sales Channel (for channel-specific pricing)
    channel_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sales_channels.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="Sales channel for channel-specific pricing"
    )

    # Pricing (all in INR)
    subtotal: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
        comment="Sum of item totals before tax"
    )
    tax_amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        default=Decimal("0.00"),
        nullable=False
    )
    discount_amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        default=Decimal("0.00"),
        nullable=False
    )
    shipping_amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        default=Decimal("0.00"),
        nullable=False
    )
    total_amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
        comment="Final amount to be paid"
    )

    # Discount
    discount_code: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    discount_type: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)

    # Payment
    payment_method: Mapped[str] = mapped_column(
        String(50),
        default="COD",
        nullable=False,
        comment="CASH, CARD, UPI, NET_BANKING, WALLET, EMI, COD, CREDIT, CHEQUE"
    )
    payment_status: Mapped[str] = mapped_column(
        String(50),
        default="PENDING",
        nullable=False,
        comment="PENDING, AUTHORIZED, CAPTURED, PARTIALLY_PAID, PAID, FAILED, REFUNDED, CANCELLED"
    )
    amount_paid: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        default=Decimal("0.00"),
        nullable=False
    )

    # Razorpay Integration
    razorpay_order_id: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        index=True,
        comment="Razorpay order ID (order_xxx)"
    )
    razorpay_payment_id: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        index=True,
        comment="Razorpay payment ID (pay_xxx)"
    )
    paid_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Timestamp when payment was confirmed"
    )

    # Addresses (stored as JSONB for historical record)
    shipping_address: Mapped[dict] = mapped_column(JSONB, nullable=False)
    billing_address: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)

    # Delivery
    expected_delivery_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    delivered_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Region for filtering
    region_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("regions.id", ondelete="SET NULL"),
        nullable=True
    )

    # Notes
    customer_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    internal_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Tracking
    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
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
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False
    )
    confirmed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    cancelled_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # OMS tracking timestamps
    allocated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="When inventory was allocated"
    )
    picked_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="When order was picked"
    )
    packed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="When order was packed"
    )
    shipped_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="When order was shipped"
    )

    # Shiprocket Integration - VARCHAR per production schema
    shiprocket_order_id: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        index=True,
        comment="Shiprocket order ID"
    )
    shiprocket_shipment_id: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        index=True,
        comment="Shiprocket shipment ID"
    )
    awb_code: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        index=True,
        comment="Airway Bill number from courier"
    )
    courier_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
        comment="Transporter/courier ID - references transporters table"
    )
    courier_name: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        comment="Courier company name (e.g., Delhivery, BlueDart)"
    )
    tracking_status: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        comment="Current tracking status from courier"
    )
    tracking_status_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        comment="Shiprocket status ID"
    )
    last_tracking_update: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Last tracking sync timestamp"
    )
    last_tracking_location: Mapped[Optional[str]] = mapped_column(
        String(200),
        nullable=True,
        comment="Last known shipment location"
    )
    last_tracking_activity: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
        comment="Last tracking activity description"
    )
    estimated_delivery: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Estimated delivery date from courier"
    )
    weight_kg: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(8, 3),
        nullable=True,
        default=Decimal("0.500"),
        comment="Package weight in kg"
    )

    # Relationships
    customer: Mapped["Customer"] = relationship("Customer", back_populates="orders")
    region: Mapped[Optional["Region"]] = relationship("Region")
    warehouse: Mapped[Optional["Warehouse"]] = relationship("Warehouse")
    dealer: Mapped[Optional["Dealer"]] = relationship("Dealer", back_populates="orders")
    created_by_user: Mapped[Optional["User"]] = relationship("User", foreign_keys=[created_by])
    items: Mapped[List["OrderItem"]] = relationship(
        "OrderItem",
        back_populates="order",
        cascade="all, delete-orphan"
    )
    status_history: Mapped[List["OrderStatusHistory"]] = relationship(
        "OrderStatusHistory",
        back_populates="order",
        cascade="all, delete-orphan",
        order_by="OrderStatusHistory.created_at"
    )
    payments: Mapped[List["Payment"]] = relationship(
        "Payment",
        back_populates="order",
        cascade="all, delete-orphan"
    )
    invoice: Mapped[Optional["Invoice"]] = relationship(
        "Invoice",
        back_populates="order",
        uselist=False
    )
    shipments: Mapped[List["Shipment"]] = relationship(
        "Shipment",
        back_populates="order",
        cascade="all, delete-orphan"
    )
    returns: Mapped[List["ReturnOrder"]] = relationship(
        "ReturnOrder",
        back_populates="order",
        cascade="all, delete-orphan"
    )
    refunds: Mapped[List["Refund"]] = relationship(
        "Refund",
        back_populates="order",
        cascade="all, delete-orphan"
    )

    @property
    def item_count(self) -> int:
        """Get total number of items."""
        return sum(item.quantity for item in self.items)

    @property
    def balance_due(self) -> Decimal:
        """Get remaining balance to be paid."""
        return self.total_amount - self.amount_paid

    @property
    def is_paid(self) -> bool:
        """Check if order is fully paid."""
        return self.payment_status == PaymentStatus.PAID

    def __repr__(self) -> str:
        return f"<Order(number='{self.order_number}', status='{self.status}')>"


class OrderItem(Base):
    """Order line item model."""
    __tablename__ = "order_items"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    order_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("orders.id", ondelete="CASCADE"),
        nullable=False
    )
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

    # Product snapshot (stored for historical record)
    product_name: Mapped[str] = mapped_column(String(255), nullable=False)
    product_sku: Mapped[str] = mapped_column(String(50), nullable=False)
    variant_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Quantity & Pricing
    quantity: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    unit_mrp: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    discount_amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        default=Decimal("0.00"),
        nullable=False
    )
    tax_rate: Mapped[Decimal] = mapped_column(
        Numeric(5, 2),
        default=Decimal("18.00"),
        nullable=False
    )
    tax_amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        default=Decimal("0.00"),
        nullable=False
    )
    total_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)

    # HSN for invoicing
    hsn_code: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)

    # Warranty
    warranty_months: Mapped[int] = mapped_column(Integer, default=12)

    # Serial number (assigned after dispatch)
    serial_number: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    # Relationships
    order: Mapped["Order"] = relationship("Order", back_populates="items")
    product: Mapped["Product"] = relationship("Product")
    variant: Mapped[Optional["ProductVariant"]] = relationship("ProductVariant")

    def __repr__(self) -> str:
        return f"<OrderItem(product='{self.product_name}', qty={self.quantity})>"


class OrderStatusHistory(Base):
    """Order status change history."""
    __tablename__ = "order_status_history"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    order_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("orders.id", ondelete="CASCADE"),
        nullable=False
    )

    from_status: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True
    )
    to_status: Mapped[str] = mapped_column(
        String(50),
        nullable=False
    )

    changed_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )

    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    # Relationships
    order: Mapped["Order"] = relationship("Order", back_populates="status_history")
    changed_by_user: Mapped[Optional["User"]] = relationship("User")

    def __repr__(self) -> str:
        return f"<OrderStatusHistory(from='{self.from_status}', to='{self.to_status}')>"


class Payment(Base):
    """Payment transaction model."""
    __tablename__ = "payments"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    order_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("orders.id", ondelete="CASCADE"),
        nullable=False
    )

    # Payment Details
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    method: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="CASH, CARD, UPI, NET_BANKING, WALLET, EMI, COD, CREDIT, CHEQUE"
    )
    status: Mapped[str] = mapped_column(
        String(50),
        default="PENDING",
        nullable=False,
        comment="PENDING, AUTHORIZED, CAPTURED, PARTIALLY_PAID, PAID, FAILED, REFUNDED, CANCELLED"
    )

    # Transaction Info
    transaction_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    gateway: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    gateway_response: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)

    # Reference
    reference_number: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    order: Mapped["Order"] = relationship("Order", back_populates="payments")

    def __repr__(self) -> str:
        return f"<Payment(amount={self.amount}, status='{self.status}')>"


class Invoice(Base):
    """Invoice model for orders."""
    __tablename__ = "invoices"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    order_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("orders.id", ondelete="CASCADE"),
        nullable=False,
        unique=True
    )

    # Invoice Number
    invoice_number: Mapped[str] = mapped_column(
        String(30),
        unique=True,
        nullable=False,
        index=True
    )

    # Amounts
    subtotal: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    tax_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    discount_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"))
    total_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)

    # Tax breakdown
    cgst_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"))
    sgst_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"))
    igst_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"))

    # Document
    pdf_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # Dates
    invoice_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )
    due_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Status
    is_cancelled: Mapped[bool] = mapped_column(Boolean, default=False)
    cancelled_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    # Relationships
    order: Mapped["Order"] = relationship("Order", back_populates="invoice")

    def __repr__(self) -> str:
        return f"<Invoice(number='{self.invoice_number}', total={self.total_amount})>"
