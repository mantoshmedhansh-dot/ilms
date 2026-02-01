"""
Abandoned Cart Model

Persists cart data for recovery and analytics.
Tracks when carts are abandoned and recovery attempts.
"""

import uuid
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import TYPE_CHECKING, Optional, List

from sqlalchemy import String, Boolean, DateTime, ForeignKey, Text, Integer
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import Numeric

from app.database import Base

if TYPE_CHECKING:
    from app.models.customer import Customer
    from app.models.order import Order


class CartStatus(str, Enum):
    """Cart status enumeration."""
    ACTIVE = "ACTIVE"              # Currently being modified
    ABANDONED = "ABANDONED"        # No activity for abandonment threshold
    RECOVERED = "RECOVERED"        # Customer returned and completed checkout
    CONVERTED = "CONVERTED"        # Order placed from this cart
    EXPIRED = "EXPIRED"            # Too old, no longer recoverable


class RecoveryChannel(str, Enum):
    """Recovery notification channel."""
    EMAIL = "EMAIL"
    SMS = "SMS"
    WHATSAPP = "WHATSAPP"
    PUSH = "PUSH"


class RecoveryStatus(str, Enum):
    """Recovery attempt status."""
    PENDING = "PENDING"
    SENT = "SENT"
    DELIVERED = "DELIVERED"
    OPENED = "OPENED"
    CLICKED = "CLICKED"
    CONVERTED = "CONVERTED"
    FAILED = "FAILED"
    BOUNCED = "BOUNCED"


class AbandonedCart(Base):
    """
    Abandoned Cart model for tracking and recovery.
    Stores cart contents and enables remarketing.
    """
    __tablename__ = "abandoned_carts"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )

    # Customer - can be null for guest carts
    customer_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("customers.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )

    # Session/Device identification for guests
    session_id: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        index=True,
        comment="Browser session ID for guest tracking"
    )
    device_fingerprint: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        comment="Device fingerprint for cross-session tracking"
    )

    # Contact info (may be from checkout form or customer)
    email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)
    phone: Mapped[Optional[str]] = mapped_column(String(20), nullable=True, index=True)
    customer_name: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)

    # Cart contents - JSONB for flexibility
    items: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
        comment="Array of cart items with product details"
    )

    # Pricing snapshot
    subtotal: Mapped[Decimal] = mapped_column(
        Numeric(18, 2),
        default=Decimal("0.00"),
        nullable=False
    )
    tax_amount: Mapped[Decimal] = mapped_column(
        Numeric(18, 2),
        default=Decimal("0.00"),
        nullable=False
    )
    shipping_amount: Mapped[Decimal] = mapped_column(
        Numeric(18, 2),
        default=Decimal("0.00"),
        nullable=False
    )
    discount_amount: Mapped[Decimal] = mapped_column(
        Numeric(18, 2),
        default=Decimal("0.00"),
        nullable=False
    )
    total_amount: Mapped[Decimal] = mapped_column(
        Numeric(18, 2),
        default=Decimal("0.00"),
        nullable=False
    )

    # Applied coupon
    coupon_code: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    # Status tracking
    status: Mapped[str] = mapped_column(
        String(50),
        default="ACTIVE",
        nullable=False,
        index=True,
        comment="ACTIVE, ABANDONED, RECOVERED, CONVERTED, EXPIRED"
    )

    # Item count for quick queries
    items_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Checkout progress tracking
    checkout_step: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        comment="Last checkout step reached: ADDRESS, SHIPPING, PAYMENT, REVIEW"
    )
    shipping_address: Mapped[Optional[dict]] = mapped_column(
        JSONB,
        nullable=True,
        comment="Shipping address if entered"
    )
    selected_payment_method: Mapped[Optional[str]] = mapped_column(
        String(50),
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
    last_activity_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True
    )
    abandoned_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="When cart was marked as abandoned"
    )
    recovered_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="When customer returned to cart"
    )
    converted_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="When order was placed"
    )

    # Conversion tracking
    converted_order_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("orders.id", ondelete="SET NULL"),
        nullable=True
    )

    # Analytics
    source: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        comment="Traffic source: direct, google, facebook, etc."
    )
    utm_source: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    utm_medium: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    utm_campaign: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    referrer_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Device info
    user_agent: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    ip_address: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    device_type: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        comment="desktop, mobile, tablet"
    )

    # Recovery tracking
    recovery_attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_recovery_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )
    recovery_token: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        unique=True,
        comment="Token for recovery link"
    )
    recovery_token_expires_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )

    # Relationships
    customer: Mapped[Optional["Customer"]] = relationship("Customer")
    converted_order: Mapped[Optional["Order"]] = relationship("Order")
    recovery_emails: Mapped[List["CartRecoveryEmail"]] = relationship(
        "CartRecoveryEmail",
        back_populates="cart",
        cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<AbandonedCart(id={self.id}, status='{self.status}', items={self.items_count})>"


class CartRecoveryEmail(Base):
    """
    Tracks recovery email/SMS attempts for abandoned carts.
    """
    __tablename__ = "cart_recovery_emails"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )

    cart_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("abandoned_carts.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Recovery sequence
    sequence_number: Mapped[int] = mapped_column(
        Integer,
        default=1,
        nullable=False,
        comment="1st, 2nd, 3rd recovery attempt"
    )

    # Channel
    channel: Mapped[str] = mapped_column(
        String(50),
        default="EMAIL",
        nullable=False,
        comment="EMAIL, SMS, WHATSAPP, PUSH"
    )

    # Status
    status: Mapped[str] = mapped_column(
        String(50),
        default="PENDING",
        nullable=False,
        comment="PENDING, SENT, DELIVERED, OPENED, CLICKED, CONVERTED, FAILED, BOUNCED"
    )

    # Recipient
    recipient: Mapped[str] = mapped_column(String(255), nullable=False)

    # Content reference
    template_used: Mapped[str] = mapped_column(String(100), nullable=False)
    subject: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Offer/incentive
    discount_code: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    discount_value: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 2), nullable=True)

    # Timestamps
    scheduled_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False
    )
    sent_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )
    delivered_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )
    opened_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )
    clicked_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )

    # Provider info
    provider: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    provider_message_id: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

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
    cart: Mapped["AbandonedCart"] = relationship(
        "AbandonedCart",
        back_populates="recovery_emails"
    )

    def __repr__(self) -> str:
        return f"<CartRecoveryEmail(cart_id={self.cart_id}, seq={self.sequence_number}, status='{self.status}')>"
