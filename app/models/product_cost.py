"""Product Cost model for tracking COGS using inventory valuation methods.

Implements Weighted Average Cost (WAC) for calculating product COGS from GRN receipts.
This provides automatic cost calculation from Purchase Orders instead of static cost_price.
"""
import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import TYPE_CHECKING, Optional, List
from decimal import Decimal

from sqlalchemy import String, DateTime, ForeignKey, Integer, Numeric, Index, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.product import Product, ProductVariant
    from app.models.warehouse import Warehouse
    from app.models.purchase import GoodsReceiptNote


class ValuationMethod(str, Enum):
    """Inventory valuation method."""
    WEIGHTED_AVG = "WEIGHTED_AVG"  # Weighted Average Cost (recommended for spare parts)
    FIFO = "FIFO"                   # First In First Out
    SPECIFIC_ID = "SPECIFIC_ID"     # Specific Identification (for serialized items)


class ProductCost(Base):
    """
    Tracks calculated COGS for products using inventory valuation.

    This table stores the calculated cost based on GRN receipts using
    the Weighted Average Cost method:

    New Avg Cost = (Current Stock Value + New Purchase Value) / (Current Qty + New Qty)

    Where:
    - Current Stock Value = quantity_on_hand × average_cost
    - New Purchase Value = GRN Accepted Qty × GRN Unit Price

    Example:
    - Old: 100 units @ ₹50 = ₹5,000
    - New GRN: 50 units @ ₹55 = ₹2,750
    - New Avg = ₹7,750 / 150 = ₹51.67/unit
    """
    __tablename__ = "product_costs"
    __table_args__ = (
        UniqueConstraint("product_id", "variant_id", "warehouse_id", name="uq_product_cost"),
        Index("idx_product_costs_product", "product_id"),
        Index("idx_product_costs_warehouse", "warehouse_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )

    # Product Reference
    product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("products.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    variant_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("product_variants.id", ondelete="CASCADE"),
        nullable=True
    )

    # Warehouse (NULL = company-wide aggregate)
    warehouse_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("warehouses.id", ondelete="SET NULL"),
        nullable=True
    )

    # Valuation Method
    valuation_method: Mapped[str] = mapped_column(
        String(20),
        default="WEIGHTED_AVG",
        nullable=False,
        comment="WEIGHTED_AVG, FIFO, SPECIFIC_ID"
    )

    # Cost Fields - Auto-calculated
    average_cost: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        default=Decimal("0"),
        nullable=False,
        comment="Current weighted average cost"
    )
    last_purchase_cost: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(12, 2),
        nullable=True,
        comment="Most recent GRN unit price"
    )
    standard_cost: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(12, 2),
        nullable=True,
        comment="Budgeted/standard cost for variance analysis"
    )

    # Inventory Position
    quantity_on_hand: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        comment="Current stock quantity"
    )
    total_value: Mapped[Decimal] = mapped_column(
        Numeric(14, 2),
        default=Decimal("0"),
        nullable=False,
        comment="quantity_on_hand × average_cost"
    )

    # Tracking
    last_grn_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("goods_receipt_notes.id", ondelete="SET NULL"),
        nullable=True,
        comment="Last GRN that updated this cost"
    )
    last_calculated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )

    # Cost History (JSONB)
    # Format: [{"date": "2026-01-19T10:30:00", "quantity": 50, "unit_cost": 55.00, "grn_id": "uuid", "running_average": 51.67}]
    cost_history: Mapped[Optional[List[dict]]] = mapped_column(
        JSONB,
        default=list,
        nullable=True,
        comment="Historical cost movements from GRN receipts"
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
    product: Mapped["Product"] = relationship("Product")
    variant: Mapped[Optional["ProductVariant"]] = relationship("ProductVariant")
    warehouse: Mapped[Optional["Warehouse"]] = relationship("Warehouse")
    last_grn: Mapped[Optional["GoodsReceiptNote"]] = relationship("GoodsReceiptNote")

    @property
    def cost_variance(self) -> Optional[Decimal]:
        """Calculate variance between average and standard cost."""
        if self.standard_cost and self.standard_cost > 0:
            return self.average_cost - self.standard_cost
        return None

    @property
    def cost_variance_percentage(self) -> Optional[float]:
        """Calculate variance percentage."""
        if self.standard_cost and self.standard_cost > 0:
            variance = float(self.average_cost - self.standard_cost)
            return round((variance / float(self.standard_cost)) * 100, 2)
        return None

    def recalculate_total_value(self) -> None:
        """Recalculate total value from quantity and average cost."""
        self.total_value = Decimal(str(self.quantity_on_hand)) * self.average_cost

    def __repr__(self) -> str:
        return f"<ProductCost(product_id={self.product_id}, avg_cost={self.average_cost}, qty={self.quantity_on_hand})>"
