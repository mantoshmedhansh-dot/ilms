"""
Return Order Model for D2C Storefront

Handles customer return requests, inspections, and refunds.
"""

import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Optional, List
from decimal import Decimal

from sqlalchemy import String, Boolean, DateTime, Integer, Text, Numeric, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB

from app.database import Base

if TYPE_CHECKING:
    from app.models.order import Order, OrderItem
    from app.models.shipment import Shipment
    from app.models.customer import Customer


class ReturnOrder(Base):
    """
    Return order/RMA (Return Merchandise Authorization) model.
    Tracks return requests from customers.
    """
    __tablename__ = "return_orders"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )

    # Return Number (RMA)
    rma_number: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        nullable=False,
        index=True,
        comment="Return Merchandise Authorization number"
    )

    # Related Order
    order_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("orders.id"),
        nullable=False,
        index=True
    )

    # Customer
    customer_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("customers.id"),
        nullable=True,
        index=True
    )

    # Return Type
    return_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="RETURN",
        comment="RETURN, EXCHANGE, REPLACEMENT"
    )

    # Return Reason
    return_reason: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="DAMAGED, DEFECTIVE, WRONG_ITEM, NOT_AS_DESCRIBED, CHANGED_MIND, SIZE_FIT_ISSUE, QUALITY_ISSUE, OTHER"
    )
    return_reason_details: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Detailed description from customer"
    )

    # Return Status
    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="INITIATED",
        index=True,
        comment="INITIATED, AUTHORIZED, PICKUP_SCHEDULED, PICKED_UP, IN_TRANSIT, RECEIVED, UNDER_INSPECTION, APPROVED, REJECTED, REFUND_INITIATED, REFUND_PROCESSED, CLOSED, CANCELLED"
    )

    # Dates
    requested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )
    authorized_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )
    pickup_scheduled_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )
    picked_up_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )
    received_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )
    inspected_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )
    closed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )

    # Return Shipping
    return_shipment_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("shipments.id"),
        nullable=True
    )
    return_tracking_number: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True
    )
    return_courier: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True
    )

    # Pickup Address (if different from order address)
    pickup_address: Mapped[Optional[dict]] = mapped_column(
        JSONB,
        nullable=True,
        comment="Pickup address if different from order shipping address"
    )

    # Inspection
    inspection_notes: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True
    )
    inspection_images: Mapped[Optional[list]] = mapped_column(
        JSONB,
        nullable=True,
        comment="Array of image URLs from inspection"
    )
    inspected_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        nullable=True
    )

    # Rejection (if applicable)
    rejection_reason: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True
    )

    # Resolution
    resolution_type: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        comment="FULL_REFUND, PARTIAL_REFUND, STORE_CREDIT, REPLACEMENT, EXCHANGE"
    )
    resolution_notes: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True
    )

    # Amounts
    total_return_amount: Mapped[Decimal] = mapped_column(
        Numeric(18, 2),
        nullable=False,
        default=Decimal("0.00"),
        comment="Total amount to be refunded"
    )
    restocking_fee: Mapped[Decimal] = mapped_column(
        Numeric(18, 2),
        nullable=False,
        default=Decimal("0.00"),
        comment="Deduction for restocking"
    )
    shipping_deduction: Mapped[Decimal] = mapped_column(
        Numeric(18, 2),
        nullable=False,
        default=Decimal("0.00"),
        comment="Deduction for return shipping"
    )
    net_refund_amount: Mapped[Decimal] = mapped_column(
        Numeric(18, 2),
        nullable=False,
        default=Decimal("0.00"),
        comment="Final refund amount after deductions"
    )

    # Store Credit (if applicable)
    store_credit_amount: Mapped[Decimal] = mapped_column(
        Numeric(18, 2),
        nullable=False,
        default=Decimal("0.00")
    )
    store_credit_code: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True
    )

    # Replacement Order (if applicable)
    replacement_order_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        nullable=True
    )

    # Communication
    customer_notified_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
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

    # Relationships
    order: Mapped["Order"] = relationship("Order", back_populates="returns")
    customer: Mapped[Optional["Customer"]] = relationship("Customer")
    return_shipment: Mapped[Optional["Shipment"]] = relationship("Shipment")
    items: Mapped[List["ReturnItem"]] = relationship(
        "ReturnItem",
        back_populates="return_order",
        cascade="all, delete-orphan"
    )
    refund: Mapped[Optional["Refund"]] = relationship(
        "Refund",
        back_populates="return_order",
        uselist=False
    )
    status_history: Mapped[List["ReturnStatusHistory"]] = relationship(
        "ReturnStatusHistory",
        back_populates="return_order",
        cascade="all, delete-orphan",
        order_by="ReturnStatusHistory.created_at"
    )

    @property
    def is_refundable(self) -> bool:
        """Check if return is eligible for refund."""
        return self.status == "APPROVED" and self.net_refund_amount > 0

    @property
    def can_be_cancelled(self) -> bool:
        """Check if return can still be cancelled."""
        return self.status in ["INITIATED", "AUTHORIZED"]

    def __repr__(self) -> str:
        return f"<ReturnOrder(rma='{self.rma_number}', status='{self.status}')>"


class ReturnItem(Base):
    """
    Individual items in a return request.
    """
    __tablename__ = "return_items"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )

    # Parent Return
    return_order_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("return_orders.id"),
        nullable=False,
        index=True
    )

    # Original Order Item
    order_item_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("order_items.id"),
        nullable=False
    )

    # Product Info (snapshot)
    product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False
    )
    product_name: Mapped[str] = mapped_column(
        String(500),
        nullable=False
    )
    sku: Mapped[str] = mapped_column(
        String(100),
        nullable=False
    )

    # Quantities
    quantity_ordered: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Original quantity in order"
    )
    quantity_returned: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Quantity being returned"
    )

    # Item Condition
    condition: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="UNOPENED",
        comment="UNOPENED, OPENED_UNUSED, USED, DAMAGED, DEFECTIVE"
    )
    condition_notes: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True
    )

    # Inspection
    inspection_result: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        comment="ACCEPTED, REJECTED, PARTIAL"
    )
    inspection_notes: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True
    )
    accepted_quantity: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        comment="Quantity accepted after inspection"
    )

    # Pricing
    unit_price: Mapped[Decimal] = mapped_column(
        Numeric(18, 2),
        nullable=False
    )
    total_amount: Mapped[Decimal] = mapped_column(
        Numeric(18, 2),
        nullable=False,
        comment="unit_price * quantity_returned"
    )
    refund_amount: Mapped[Decimal] = mapped_column(
        Numeric(18, 2),
        nullable=False,
        default=Decimal("0.00"),
        comment="Final refund for this item"
    )

    # Serial Number (if applicable)
    serial_number: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True
    )

    # Images
    customer_images: Mapped[Optional[list]] = mapped_column(
        JSONB,
        nullable=True,
        comment="Images uploaded by customer"
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    # Relationships
    return_order: Mapped["ReturnOrder"] = relationship(
        "ReturnOrder",
        back_populates="items"
    )
    order_item: Mapped["OrderItem"] = relationship("OrderItem")

    def __repr__(self) -> str:
        return f"<ReturnItem(sku='{self.sku}', qty={self.quantity_returned})>"


class ReturnStatusHistory(Base):
    """
    Tracks all status changes for a return order.
    """
    __tablename__ = "return_status_history"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )

    return_order_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("return_orders.id"),
        nullable=False,
        index=True
    )

    from_status: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True
    )
    to_status: Mapped[str] = mapped_column(
        String(50),
        nullable=False
    )
    notes: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True
    )
    changed_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
        comment="User who made the change"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    # Relationships
    return_order: Mapped["ReturnOrder"] = relationship(
        "ReturnOrder",
        back_populates="status_history"
    )

    def __repr__(self) -> str:
        return f"<ReturnStatusHistory(from='{self.from_status}', to='{self.to_status}')>"


class Refund(Base):
    """
    Refund transaction model.
    Tracks refund processing and status.
    """
    __tablename__ = "refunds"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )

    # Refund Number
    refund_number: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        nullable=False,
        index=True
    )

    # Related Entities
    order_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("orders.id"),
        nullable=False,
        index=True
    )
    return_order_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("return_orders.id"),
        nullable=True,
        index=True
    )
    customer_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("customers.id"),
        nullable=True,
        index=True
    )

    # Refund Type
    refund_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="FULL, PARTIAL, CANCELLATION, RETURN"
    )

    # Refund Method
    refund_method: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="ORIGINAL_PAYMENT, BANK_TRANSFER, STORE_CREDIT, WALLET"
    )

    # Amounts
    order_amount: Mapped[Decimal] = mapped_column(
        Numeric(18, 2),
        nullable=False,
        comment="Original order amount"
    )
    refund_amount: Mapped[Decimal] = mapped_column(
        Numeric(18, 2),
        nullable=False,
        comment="Amount to be refunded"
    )
    processing_fee: Mapped[Decimal] = mapped_column(
        Numeric(18, 2),
        nullable=False,
        default=Decimal("0.00"),
        comment="Any processing fee deducted"
    )
    net_refund: Mapped[Decimal] = mapped_column(
        Numeric(18, 2),
        nullable=False,
        comment="Final refund amount"
    )

    # Tax Breakdown (for accounting)
    tax_refund: Mapped[Decimal] = mapped_column(
        Numeric(18, 2),
        nullable=False,
        default=Decimal("0.00")
    )

    # Status
    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="PENDING",
        index=True,
        comment="PENDING, PROCESSING, COMPLETED, FAILED, CANCELLED"
    )

    # Payment Gateway Details
    original_payment_id: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        comment="Original payment transaction ID"
    )
    refund_transaction_id: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        comment="Gateway refund transaction ID"
    )
    gateway_response: Mapped[Optional[dict]] = mapped_column(
        JSONB,
        nullable=True,
        comment="Full gateway response"
    )

    # Bank Details (for bank transfer)
    bank_account_number: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True
    )
    bank_ifsc: Mapped[Optional[str]] = mapped_column(
        String(20),
        nullable=True
    )
    bank_account_name: Mapped[Optional[str]] = mapped_column(
        String(200),
        nullable=True
    )

    # Reason
    reason: Mapped[str] = mapped_column(
        String(200),
        nullable=False
    )
    notes: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True
    )

    # Dates
    initiated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )
    processed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )
    failed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )

    # Failure Details
    failure_reason: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True
    )
    retry_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0
    )

    # Accounting
    accounting_entry_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
        comment="Link to accounting journal entry"
    )

    # Initiated By
    initiated_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
        comment="User who initiated the refund"
    )
    approved_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
        comment="User who approved the refund"
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

    # Relationships
    order: Mapped["Order"] = relationship("Order", back_populates="refunds")
    return_order: Mapped[Optional["ReturnOrder"]] = relationship(
        "ReturnOrder",
        back_populates="refund"
    )
    customer: Mapped[Optional["Customer"]] = relationship("Customer")

    @property
    def is_completed(self) -> bool:
        return self.status == "COMPLETED"

    @property
    def can_retry(self) -> bool:
        return self.status == "FAILED" and self.retry_count < 3

    def __repr__(self) -> str:
        return f"<Refund(number='{self.refund_number}', amount={self.net_refund}, status='{self.status}')>"
