"""
Lot/Batch Tracking Models - Phase 13: Lot Tracking & Expiration Management.

Models for lot/batch management including:
- Lot definitions and attributes
- Expiration tracking and alerts
- FIFO/FEFO allocation
- Lot holds and quarantine
- Recall management
"""
from datetime import datetime, date
from decimal import Decimal
from enum import Enum
from typing import Optional, List
from uuid import UUID, uuid4

from sqlalchemy import (
    String, Integer, DateTime, ForeignKey, Index, Text, Boolean,
    Numeric, Date, UniqueConstraint, JSON
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


# ============================================================================
# ENUMS
# ============================================================================

class LotStatus(str, Enum):
    """Status of a lot."""
    ACTIVE = "active"
    ON_HOLD = "on_hold"
    QUARANTINE = "quarantine"
    EXPIRED = "expired"
    RECALLED = "recalled"
    CONSUMED = "consumed"
    DESTROYED = "destroyed"


class HoldReason(str, Enum):
    """Reason for lot hold."""
    QUALITY_ISSUE = "quality_issue"
    PENDING_QC = "pending_qc"
    CUSTOMER_COMPLAINT = "customer_complaint"
    REGULATORY_HOLD = "regulatory_hold"
    SUPPLIER_ISSUE = "supplier_issue"
    RECALL = "recall"
    INVESTIGATION = "investigation"
    DAMAGED = "damaged"
    OTHER = "other"


class AllocationStrategy(str, Enum):
    """Inventory allocation strategy."""
    FIFO = "fifo"                    # First In First Out
    FEFO = "fefo"                    # First Expiry First Out
    LIFO = "lifo"                    # Last In First Out
    LEFO = "lefo"                    # Last Expiry First Out
    MANUAL = "manual"                # Manual selection


class RecallType(str, Enum):
    """Type of recall."""
    VOLUNTARY = "voluntary"
    MANDATORY = "mandatory"
    MARKET_WITHDRAWAL = "market_withdrawal"


class RecallClass(str, Enum):
    """FDA recall classification."""
    CLASS_I = "class_i"              # Serious health hazard
    CLASS_II = "class_ii"            # Temporary/reversible health effects
    CLASS_III = "class_iii"          # Not likely to cause health problems


class RecallStatus(str, Enum):
    """Status of recall."""
    INITIATED = "initiated"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CLOSED = "closed"


class ExpirationAction(str, Enum):
    """Action for expiring lots."""
    NOTIFY = "notify"
    HOLD = "hold"
    QUARANTINE = "quarantine"
    AUTO_DISPOSE = "auto_dispose"


# ============================================================================
# MODELS
# ============================================================================

class LotMaster(Base):
    """
    Master lot/batch record.

    Central repository for all lot information across the system.
    """
    __tablename__ = "lot_masters"
    __table_args__ = (
        UniqueConstraint("tenant_id", "lot_number", name="uq_lot_number"),
        Index("idx_lm_tenant_product", "tenant_id", "product_id"),
        Index("idx_lm_expiry", "tenant_id", "expiration_date"),
        Index("idx_lm_status", "tenant_id", "status"),
        {"schema": "public"}
    )

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    tenant_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("public.tenants.id"), nullable=False
    )

    # Lot Identity
    lot_number: Mapped[str] = mapped_column(String(100), nullable=False)
    batch_number: Mapped[Optional[str]] = mapped_column(String(100))
    lot_code: Mapped[Optional[str]] = mapped_column(String(50))  # Internal code

    # Product
    product_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("public.products.id"), nullable=False
    )
    variant_id: Mapped[Optional[UUID]] = mapped_column(PG_UUID(as_uuid=True))

    # Dates
    manufacture_date: Mapped[Optional[date]] = mapped_column(Date)
    expiration_date: Mapped[Optional[date]] = mapped_column(Date)
    best_before_date: Mapped[Optional[date]] = mapped_column(Date)
    receive_date: Mapped[date] = mapped_column(Date, nullable=False)

    # Shelf Life
    shelf_life_days: Mapped[Optional[int]] = mapped_column(Integer)
    remaining_shelf_life_days: Mapped[Optional[int]] = mapped_column(Integer)
    shelf_life_percent: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 2))

    # Origin
    supplier_id: Mapped[Optional[UUID]] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("public.vendors.id")
    )
    supplier_lot_number: Mapped[Optional[str]] = mapped_column(String(100))
    country_of_origin: Mapped[Optional[str]] = mapped_column(String(3))  # ISO code
    po_number: Mapped[Optional[str]] = mapped_column(String(50))
    grn_number: Mapped[Optional[str]] = mapped_column(String(50))

    # Quantity Tracking
    initial_quantity: Mapped[Decimal] = mapped_column(Numeric(15, 3), nullable=False)
    current_quantity: Mapped[Decimal] = mapped_column(Numeric(15, 3), nullable=False)
    reserved_quantity: Mapped[Decimal] = mapped_column(Numeric(15, 3), default=Decimal("0"))
    allocated_quantity: Mapped[Decimal] = mapped_column(Numeric(15, 3), default=Decimal("0"))
    uom: Mapped[str] = mapped_column(String(20), default="EACH")

    # Status
    status: Mapped[LotStatus] = mapped_column(
        String(20), nullable=False, default=LotStatus.ACTIVE
    )
    hold_reason: Mapped[Optional[HoldReason]] = mapped_column(String(30))
    hold_notes: Mapped[Optional[str]] = mapped_column(Text)
    held_by: Mapped[Optional[UUID]] = mapped_column(PG_UUID(as_uuid=True))
    held_at: Mapped[Optional[datetime]] = mapped_column(DateTime)

    # Quality
    qc_status: Mapped[Optional[str]] = mapped_column(String(20))  # passed, failed, pending
    qc_date: Mapped[Optional[date]] = mapped_column(Date)
    qc_reference: Mapped[Optional[str]] = mapped_column(String(50))
    certificate_of_analysis: Mapped[Optional[str]] = mapped_column(String(500))  # URL

    # Cost
    unit_cost: Mapped[Decimal] = mapped_column(Numeric(15, 4), default=Decimal("0"))
    total_cost: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=Decimal("0"))

    # Custom Attributes (JSONB for flexibility)
    attributes: Mapped[Optional[dict]] = mapped_column(JSONB)
    # Example attributes: temperature_zone, potency, concentration, color_code

    # Recall
    is_recalled: Mapped[bool] = mapped_column(Boolean, default=False)
    recall_id: Mapped[Optional[UUID]] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("public.lot_recalls.id")
    )

    notes: Mapped[Optional[str]] = mapped_column(Text)

    # Audit
    created_by: Mapped[Optional[UUID]] = mapped_column(PG_UUID(as_uuid=True))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    inventory_lots: Mapped[List["InventoryLot"]] = relationship(back_populates="lot_master")
    transactions: Mapped[List["LotTransaction"]] = relationship(back_populates="lot")
    holds: Mapped[List["LotHold"]] = relationship(back_populates="lot")


class InventoryLot(Base):
    """
    Lot inventory at specific location.

    Tracks lot quantities at warehouse/zone/bin level.
    """
    __tablename__ = "inventory_lots"
    __table_args__ = (
        UniqueConstraint("tenant_id", "lot_id", "warehouse_id", "bin_id",
                        name="uq_inventory_lot_location"),
        Index("idx_il_tenant_warehouse", "tenant_id", "warehouse_id"),
        Index("idx_il_lot", "tenant_id", "lot_id"),
        {"schema": "public"}
    )

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    tenant_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("public.tenants.id"), nullable=False
    )
    lot_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("public.lot_masters.id"), nullable=False
    )

    # Location
    warehouse_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("public.warehouses.id"), nullable=False
    )
    zone_id: Mapped[Optional[UUID]] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("public.warehouse_zones.id")
    )
    bin_id: Mapped[Optional[UUID]] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("public.warehouse_bins.id")
    )

    # Quantities
    quantity: Mapped[Decimal] = mapped_column(Numeric(15, 3), nullable=False)
    reserved_quantity: Mapped[Decimal] = mapped_column(Numeric(15, 3), default=Decimal("0"))
    allocated_quantity: Mapped[Decimal] = mapped_column(Numeric(15, 3), default=Decimal("0"))
    available_quantity: Mapped[Decimal] = mapped_column(Numeric(15, 3), default=Decimal("0"))

    # Status
    is_available: Mapped[bool] = mapped_column(Boolean, default=True)
    is_on_hold: Mapped[bool] = mapped_column(Boolean, default=False)

    # License Plate (if using LPN tracking)
    lpn: Mapped[Optional[str]] = mapped_column(String(50))

    received_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    last_movement_at: Mapped[Optional[datetime]] = mapped_column(DateTime)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    lot_master: Mapped["LotMaster"] = relationship(back_populates="inventory_lots")


class LotTransaction(Base):
    """
    Lot transaction history.

    Tracks all movements and changes to lots.
    """
    __tablename__ = "lot_transactions"
    __table_args__ = (
        Index("idx_lt_tenant_lot", "tenant_id", "lot_id"),
        Index("idx_lt_date", "tenant_id", "transaction_date"),
        Index("idx_lt_type", "tenant_id", "transaction_type"),
        {"schema": "public"}
    )

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    tenant_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("public.tenants.id"), nullable=False
    )
    lot_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("public.lot_masters.id"), nullable=False
    )

    # Transaction Details
    transaction_number: Mapped[str] = mapped_column(String(50), nullable=False)
    transaction_date: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    transaction_type: Mapped[str] = mapped_column(String(30), nullable=False)
    # Types: receive, pick, ship, transfer, adjust, hold, release, expire, recall, destroy

    # Quantity
    quantity: Mapped[Decimal] = mapped_column(Numeric(15, 3), nullable=False)
    quantity_before: Mapped[Decimal] = mapped_column(Numeric(15, 3), nullable=False)
    quantity_after: Mapped[Decimal] = mapped_column(Numeric(15, 3), nullable=False)

    # Location
    from_warehouse_id: Mapped[Optional[UUID]] = mapped_column(PG_UUID(as_uuid=True))
    from_bin_id: Mapped[Optional[UUID]] = mapped_column(PG_UUID(as_uuid=True))
    to_warehouse_id: Mapped[Optional[UUID]] = mapped_column(PG_UUID(as_uuid=True))
    to_bin_id: Mapped[Optional[UUID]] = mapped_column(PG_UUID(as_uuid=True))

    # Reference
    source_type: Mapped[Optional[str]] = mapped_column(String(30))  # order, transfer, grn, adjustment
    source_id: Mapped[Optional[UUID]] = mapped_column(PG_UUID(as_uuid=True))
    source_number: Mapped[Optional[str]] = mapped_column(String(50))

    # User
    performed_by: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("public.users.id"), nullable=False
    )

    notes: Mapped[Optional[str]] = mapped_column(Text)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    lot: Mapped["LotMaster"] = relationship(back_populates="transactions")


class LotHold(Base):
    """
    Lot hold records.

    Tracks holds placed on lots with reasons and resolution.
    """
    __tablename__ = "lot_holds"
    __table_args__ = (
        Index("idx_lh_tenant_lot", "tenant_id", "lot_id"),
        Index("idx_lh_active", "tenant_id", "is_active"),
        {"schema": "public"}
    )

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    tenant_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("public.tenants.id"), nullable=False
    )
    lot_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("public.lot_masters.id"), nullable=False
    )

    # Hold Details
    hold_number: Mapped[str] = mapped_column(String(50), nullable=False)
    hold_reason: Mapped[HoldReason] = mapped_column(String(30), nullable=False)
    hold_description: Mapped[Optional[str]] = mapped_column(Text)

    # Quantity (can hold partial lot)
    quantity_held: Mapped[Decimal] = mapped_column(Numeric(15, 3), nullable=False)

    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    held_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    held_by: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("public.users.id"), nullable=False
    )

    # Release
    released_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    released_by: Mapped[Optional[UUID]] = mapped_column(PG_UUID(as_uuid=True))
    release_notes: Mapped[Optional[str]] = mapped_column(Text)

    # Investigation
    investigation_required: Mapped[bool] = mapped_column(Boolean, default=False)
    investigation_notes: Mapped[Optional[str]] = mapped_column(Text)
    investigation_result: Mapped[Optional[str]] = mapped_column(String(30))  # pass, fail, dispose

    # Reference
    reference_type: Mapped[Optional[str]] = mapped_column(String(30))
    reference_id: Mapped[Optional[UUID]] = mapped_column(PG_UUID(as_uuid=True))

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    lot: Mapped["LotMaster"] = relationship(back_populates="holds")


class LotRecall(Base):
    """
    Product recall management.

    Tracks recalls and affected lots.
    """
    __tablename__ = "lot_recalls"
    __table_args__ = (
        Index("idx_lr_tenant_status", "tenant_id", "status"),
        Index("idx_lr_product", "tenant_id", "product_id"),
        {"schema": "public"}
    )

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    tenant_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("public.tenants.id"), nullable=False
    )

    # Recall Identity
    recall_number: Mapped[str] = mapped_column(String(50), nullable=False)
    recall_name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)

    # Classification
    recall_type: Mapped[RecallType] = mapped_column(String(30), nullable=False)
    recall_class: Mapped[Optional[RecallClass]] = mapped_column(String(20))

    # Product
    product_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("public.products.id"), nullable=False
    )

    # Lot Criteria
    lot_numbers: Mapped[Optional[List]] = mapped_column(JSONB)  # Specific lots
    manufacture_date_from: Mapped[Optional[date]] = mapped_column(Date)
    manufacture_date_to: Mapped[Optional[date]] = mapped_column(Date)
    expiration_date_from: Mapped[Optional[date]] = mapped_column(Date)
    expiration_date_to: Mapped[Optional[date]] = mapped_column(Date)

    # Dates
    recall_date: Mapped[date] = mapped_column(Date, nullable=False)
    effective_date: Mapped[date] = mapped_column(Date, nullable=False)
    completion_target_date: Mapped[Optional[date]] = mapped_column(Date)
    actual_completion_date: Mapped[Optional[date]] = mapped_column(Date)

    # Reason
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    health_hazard: Mapped[Optional[str]] = mapped_column(Text)
    regulatory_reference: Mapped[Optional[str]] = mapped_column(String(100))

    # Status
    status: Mapped[RecallStatus] = mapped_column(
        String(20), nullable=False, default=RecallStatus.INITIATED
    )

    # Statistics
    total_lots_affected: Mapped[int] = mapped_column(Integer, default=0)
    total_quantity_affected: Mapped[Decimal] = mapped_column(Numeric(15, 3), default=Decimal("0"))
    quantity_in_warehouse: Mapped[Decimal] = mapped_column(Numeric(15, 3), default=Decimal("0"))
    quantity_in_transit: Mapped[Decimal] = mapped_column(Numeric(15, 3), default=Decimal("0"))
    quantity_shipped: Mapped[Decimal] = mapped_column(Numeric(15, 3), default=Decimal("0"))
    quantity_recovered: Mapped[Decimal] = mapped_column(Numeric(15, 3), default=Decimal("0"))
    quantity_destroyed: Mapped[Decimal] = mapped_column(Numeric(15, 3), default=Decimal("0"))

    # Contact
    contact_name: Mapped[Optional[str]] = mapped_column(String(100))
    contact_phone: Mapped[Optional[str]] = mapped_column(String(20))
    contact_email: Mapped[Optional[str]] = mapped_column(String(100))

    # Actions
    action_required: Mapped[Optional[str]] = mapped_column(Text)
    customer_notification: Mapped[Optional[str]] = mapped_column(Text)

    notes: Mapped[Optional[str]] = mapped_column(Text)

    # Audit
    initiated_by: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("public.users.id"), nullable=False
    )
    approved_by: Mapped[Optional[UUID]] = mapped_column(PG_UUID(as_uuid=True))
    approved_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    closed_by: Mapped[Optional[UUID]] = mapped_column(PG_UUID(as_uuid=True))
    closed_at: Mapped[Optional[datetime]] = mapped_column(DateTime)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    affected_lots: Mapped[List["RecallAffectedLot"]] = relationship(back_populates="recall")


class RecallAffectedLot(Base):
    """
    Lots affected by a recall.
    """
    __tablename__ = "recall_affected_lots"
    __table_args__ = (
        UniqueConstraint("tenant_id", "recall_id", "lot_id", name="uq_recall_lot"),
        Index("idx_ral_tenant_recall", "tenant_id", "recall_id"),
        {"schema": "public"}
    )

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    tenant_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("public.tenants.id"), nullable=False
    )
    recall_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("public.lot_recalls.id"), nullable=False
    )
    lot_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("public.lot_masters.id"), nullable=False
    )

    # Quantities
    quantity_affected: Mapped[Decimal] = mapped_column(Numeric(15, 3), nullable=False)
    quantity_in_warehouse: Mapped[Decimal] = mapped_column(Numeric(15, 3), default=Decimal("0"))
    quantity_shipped: Mapped[Decimal] = mapped_column(Numeric(15, 3), default=Decimal("0"))
    quantity_recovered: Mapped[Decimal] = mapped_column(Numeric(15, 3), default=Decimal("0"))
    quantity_destroyed: Mapped[Decimal] = mapped_column(Numeric(15, 3), default=Decimal("0"))

    # Status
    status: Mapped[str] = mapped_column(String(30), default="identified")
    # identified, held, recovered, destroyed, accounted

    # Actions
    action_taken: Mapped[Optional[str]] = mapped_column(Text)
    action_date: Mapped[Optional[datetime]] = mapped_column(DateTime)
    action_by: Mapped[Optional[UUID]] = mapped_column(PG_UUID(as_uuid=True))

    notes: Mapped[Optional[str]] = mapped_column(Text)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    recall: Mapped["LotRecall"] = relationship(back_populates="affected_lots")


class ExpirationRule(Base):
    """
    Expiration rules for products.

    Defines how to handle expiring inventory.
    """
    __tablename__ = "expiration_rules"
    __table_args__ = (
        UniqueConstraint("tenant_id", "product_id", "warehouse_id", name="uq_expiration_rule"),
        Index("idx_er_tenant_product", "tenant_id", "product_id"),
        {"schema": "public"}
    )

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    tenant_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("public.tenants.id"), nullable=False
    )

    # Scope
    product_id: Mapped[Optional[UUID]] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("public.products.id")
    )
    category_id: Mapped[Optional[UUID]] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("public.categories.id")
    )
    warehouse_id: Mapped[Optional[UUID]] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("public.warehouses.id")
    )

    rule_name: Mapped[str] = mapped_column(String(100), nullable=False)

    # Allocation Strategy
    allocation_strategy: Mapped[AllocationStrategy] = mapped_column(
        String(20), nullable=False, default=AllocationStrategy.FEFO
    )

    # Minimum Shelf Life for Receiving
    min_receiving_shelf_life_days: Mapped[Optional[int]] = mapped_column(Integer)
    min_receiving_shelf_life_percent: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 2))

    # Minimum Shelf Life for Shipping
    min_shipping_shelf_life_days: Mapped[Optional[int]] = mapped_column(Integer)
    min_shipping_shelf_life_percent: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 2))

    # Alert Thresholds
    warning_days_before_expiry: Mapped[int] = mapped_column(Integer, default=30)
    critical_days_before_expiry: Mapped[int] = mapped_column(Integer, default=7)

    # Actions
    warning_action: Mapped[ExpirationAction] = mapped_column(
        String(20), default=ExpirationAction.NOTIFY
    )
    critical_action: Mapped[ExpirationAction] = mapped_column(
        String(20), default=ExpirationAction.HOLD
    )
    expiration_action: Mapped[ExpirationAction] = mapped_column(
        String(20), default=ExpirationAction.QUARANTINE
    )

    # Notifications
    notify_emails: Mapped[Optional[List]] = mapped_column(JSONB)
    notify_roles: Mapped[Optional[List]] = mapped_column(JSONB)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    notes: Mapped[Optional[str]] = mapped_column(Text)

    created_by: Mapped[Optional[UUID]] = mapped_column(PG_UUID(as_uuid=True))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )


class ExpirationAlert(Base):
    """
    Expiration alerts generated for lots.
    """
    __tablename__ = "expiration_alerts"
    __table_args__ = (
        Index("idx_ea_tenant_status", "tenant_id", "status"),
        Index("idx_ea_lot", "tenant_id", "lot_id"),
        {"schema": "public"}
    )

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    tenant_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("public.tenants.id"), nullable=False
    )
    lot_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("public.lot_masters.id"), nullable=False
    )
    rule_id: Mapped[Optional[UUID]] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("public.expiration_rules.id")
    )

    # Alert Details
    alert_type: Mapped[str] = mapped_column(String(20), nullable=False)  # warning, critical, expired
    alert_date: Mapped[date] = mapped_column(Date, nullable=False)
    expiration_date: Mapped[date] = mapped_column(Date, nullable=False)
    days_until_expiry: Mapped[int] = mapped_column(Integer, nullable=False)

    # Lot Info
    product_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False)
    warehouse_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False)
    quantity_at_risk: Mapped[Decimal] = mapped_column(Numeric(15, 3), nullable=False)
    value_at_risk: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=Decimal("0"))

    # Status
    status: Mapped[str] = mapped_column(String(20), default="open")  # open, acknowledged, resolved

    # Action Taken
    action_taken: Mapped[Optional[str]] = mapped_column(String(50))
    action_date: Mapped[Optional[datetime]] = mapped_column(DateTime)
    action_by: Mapped[Optional[UUID]] = mapped_column(PG_UUID(as_uuid=True))
    action_notes: Mapped[Optional[str]] = mapped_column(Text)

    # Notifications
    notified_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    notified_to: Mapped[Optional[List]] = mapped_column(JSONB)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )
