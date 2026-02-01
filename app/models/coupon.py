"""
Coupon Model for D2C Storefront

Supports various discount types, usage limits, and conditions.
"""

import uuid
from datetime import datetime, date, timezone
from enum import Enum
from typing import TYPE_CHECKING, Optional, List

from sqlalchemy import String, Boolean, DateTime, Date, Integer, Text, Numeric
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID, JSONB

from app.database import Base


class DiscountType(str, Enum):
    """Discount type enumeration."""
    PERCENTAGE = "PERCENTAGE"  # e.g., 10% off
    FIXED_AMOUNT = "FIXED_AMOUNT"  # e.g., ₹100 off
    FREE_SHIPPING = "FREE_SHIPPING"  # Free shipping


class Coupon(Base):
    """
    Coupon/Promo code model for D2C storefront.
    """
    __tablename__ = "coupons"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )

    # Coupon Code
    code: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        nullable=False,
        index=True,
        comment="Unique coupon code (case-insensitive)"
    )

    # Display Info
    name: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
        comment="Display name for the coupon"
    )
    description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Description shown to customers"
    )

    # Discount Type & Value
    discount_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="PERCENTAGE",
        comment="PERCENTAGE, FIXED_AMOUNT, FREE_SHIPPING"
    )
    discount_value: Mapped[float] = mapped_column(
        Numeric(10, 2),
        nullable=False,
        default=0,
        comment="Discount value (percentage or amount)"
    )
    max_discount_amount: Mapped[Optional[float]] = mapped_column(
        Numeric(10, 2),
        nullable=True,
        comment="Cap on discount for PERCENTAGE type"
    )

    # Minimum Requirements
    minimum_order_amount: Mapped[Optional[float]] = mapped_column(
        Numeric(10, 2),
        nullable=True,
        comment="Minimum cart value to apply coupon"
    )
    minimum_items: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        comment="Minimum number of items in cart"
    )

    # Usage Limits
    usage_limit: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        comment="Total times this coupon can be used"
    )
    usage_limit_per_customer: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
        comment="Times each customer can use this coupon"
    )
    used_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        comment="Number of times coupon has been used"
    )

    # Validity Period
    valid_from: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc)
    )
    valid_until: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Expiry date (null = never expires)"
    )

    # Restrictions (stored as JSON)
    applicable_products: Mapped[Optional[list]] = mapped_column(
        JSONB,
        nullable=True,
        comment="List of product IDs this coupon applies to"
    )
    applicable_categories: Mapped[Optional[list]] = mapped_column(
        JSONB,
        nullable=True,
        comment="List of category IDs this coupon applies to"
    )
    excluded_products: Mapped[Optional[list]] = mapped_column(
        JSONB,
        nullable=True,
        comment="List of product IDs excluded from this coupon"
    )

    # Customer Restrictions
    first_order_only: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        comment="Only for first-time customers"
    )
    specific_customers: Mapped[Optional[list]] = mapped_column(
        JSONB,
        nullable=True,
        comment="List of customer IDs who can use this coupon"
    )

    # Status
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True
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

    @property
    def is_valid(self) -> bool:
        """Check if coupon is currently valid."""
        now = datetime.now(timezone.utc)
        if not self.is_active:
            return False
        if now < self.valid_from:
            return False
        if self.valid_until and now > self.valid_until:
            return False
        if self.usage_limit and self.used_count >= self.usage_limit:
            return False
        return True

    def __repr__(self) -> str:
        return f"<Coupon(code='{self.code}', type='{self.discount_type}', value={self.discount_value})>"


class CouponUsage(Base):
    """
    Tracks coupon usage by customers.
    """
    __tablename__ = "coupon_usage"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    coupon_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
        index=True
    )
    customer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
        index=True
    )
    order_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False
    )
    discount_amount: Mapped[float] = mapped_column(
        Numeric(10, 2),
        nullable=False,
        comment="Actual discount applied"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )
