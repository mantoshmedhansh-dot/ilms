"""
Customer Wishlist Model

Stores customer's saved/favorite products for D2C storefront.
"""

import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Optional

from sqlalchemy import String, DateTime, ForeignKey, Index, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID

from app.database import Base

if TYPE_CHECKING:
    from app.models.customer import Customer
    from app.models.product import Product


class WishlistItem(Base):
    """
    Customer wishlist item.
    Stores products that customers have saved for later.
    """
    __tablename__ = "wishlist_items"
    __table_args__ = (
        UniqueConstraint('customer_id', 'product_id', name='uq_wishlist_customer_product'),
        Index('ix_wishlist_customer_id', 'customer_id'),
        Index('ix_wishlist_product_id', 'product_id'),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )

    # Customer who saved the product
    customer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("customers.id", ondelete="CASCADE"),
        nullable=False
    )

    # Product saved to wishlist
    product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("products.id", ondelete="CASCADE"),
        nullable=False
    )

    # Optional: Specific variant saved
    variant_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("product_variants.id", ondelete="SET NULL"),
        nullable=True
    )

    # Price at time of adding (for price drop alerts)
    price_when_added: Mapped[Optional[float]] = mapped_column(nullable=True)

    # Notes (optional user notes about why they saved it)
    notes: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    # Relationships
    customer: Mapped["Customer"] = relationship("Customer", lazy="joined")
    product: Mapped["Product"] = relationship("Product", lazy="joined")

    def __repr__(self) -> str:
        return f"<WishlistItem(customer_id={self.customer_id}, product_id={self.product_id})>"
