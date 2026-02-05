"""
Warehouse Billing Models - Phase 10: Storage & Operations Billing.

This module implements warehouse billing operations:
- BillingContract: Customer/3PL billing agreements
- StorageCharge: Storage space charges
- HandlingCharge: Activity-based handling fees
- ValueAddedService: VAS charges (kitting, labeling, etc.)
- BillingInvoice: Generated invoices
"""
import uuid
from datetime import datetime, timezone, date
from decimal import Decimal
from enum import Enum
from typing import TYPE_CHECKING, Optional, List, Dict, Any

from sqlalchemy import (
    String, Boolean, DateTime, ForeignKey, Integer, Text,
    Numeric, Date, Index, UniqueConstraint
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.warehouse import Warehouse
    from app.models.user import User
    from app.models.customer import Customer


# ============================================================================
# ENUMS
# ============================================================================

class BillingType(str, Enum):
    """Types of billing arrangements."""
    STORAGE = "STORAGE"               # Storage fees
    HANDLING = "HANDLING"             # Handling/transaction fees
    VAS = "VAS"                       # Value-added services
    SUBSCRIPTION = "SUBSCRIPTION"     # Monthly subscription
    HYBRID = "HYBRID"                 # Combination


class StorageBillingModel(str, Enum):
    """How storage is billed."""
    PER_PALLET = "PER_PALLET"
    PER_BIN = "PER_BIN"
    PER_SQFT = "PER_SQFT"
    PER_CUBIC_FT = "PER_CUBIC_FT"
    PER_UNIT = "PER_UNIT"
    TIERED = "TIERED"


class HandlingBillingModel(str, Enum):
    """How handling is billed."""
    PER_ORDER = "PER_ORDER"
    PER_LINE = "PER_LINE"
    PER_UNIT = "PER_UNIT"
    PER_PIECE = "PER_PIECE"
    PER_CARTON = "PER_CARTON"
    PER_PALLET = "PER_PALLET"
    PER_WEIGHT = "PER_WEIGHT"


class ChargeCategory(str, Enum):
    """Categories of charges."""
    INBOUND = "INBOUND"
    OUTBOUND = "OUTBOUND"
    STORAGE = "STORAGE"
    VAS = "VAS"
    RETURNS = "RETURNS"
    INVENTORY = "INVENTORY"
    LABOR = "LABOR"
    ACCESSORIAL = "ACCESSORIAL"


class ChargeType(str, Enum):
    """Types of charges."""
    # Inbound
    RECEIVING = "RECEIVING"
    PUTAWAY = "PUTAWAY"
    UNLOADING = "UNLOADING"

    # Outbound
    PICKING = "PICKING"
    PACKING = "PACKING"
    LOADING = "LOADING"

    # Storage
    PALLET_STORAGE = "PALLET_STORAGE"
    BIN_STORAGE = "BIN_STORAGE"
    FLOOR_STORAGE = "FLOOR_STORAGE"
    COLD_STORAGE = "COLD_STORAGE"
    HAZMAT_STORAGE = "HAZMAT_STORAGE"

    # VAS
    LABELING = "LABELING"
    KITTING = "KITTING"
    BUNDLING = "BUNDLING"
    GIFT_WRAP = "GIFT_WRAP"
    REWORK = "REWORK"
    QUALITY_CHECK = "QUALITY_CHECK"

    # Other
    INVENTORY_COUNT = "INVENTORY_COUNT"
    SPECIAL_HANDLING = "SPECIAL_HANDLING"
    OVERTIME_LABOR = "OVERTIME_LABOR"
    RUSH_ORDER = "RUSH_ORDER"
    RETURNS_PROCESSING = "RETURNS_PROCESSING"


class ContractStatus(str, Enum):
    """Billing contract status."""
    DRAFT = "DRAFT"
    ACTIVE = "ACTIVE"
    SUSPENDED = "SUSPENDED"
    EXPIRED = "EXPIRED"
    TERMINATED = "TERMINATED"


class InvoiceStatus(str, Enum):
    """Billing invoice status."""
    DRAFT = "DRAFT"
    PENDING = "PENDING"
    SENT = "SENT"
    PARTIAL = "PARTIAL"
    PAID = "PAID"
    OVERDUE = "OVERDUE"
    CANCELLED = "CANCELLED"
    DISPUTED = "DISPUTED"


class BillingPeriod(str, Enum):
    """Billing period frequency."""
    DAILY = "DAILY"
    WEEKLY = "WEEKLY"
    BIWEEKLY = "BIWEEKLY"
    MONTHLY = "MONTHLY"
    QUARTERLY = "QUARTERLY"


# ============================================================================
# MODELS
# ============================================================================

class BillingContract(Base):
    """
    Billing contract/agreement with customer.

    Defines rates and billing terms for a customer.
    """
    __tablename__ = "billing_contracts"
    __table_args__ = (
        UniqueConstraint('tenant_id', 'contract_number', name='uq_billing_contract_number'),
        Index('ix_billing_contracts_status', 'status'),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
        index=True
    )

    # Contract Identity
    contract_number: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        index=True
    )
    contract_name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(
        String(30),
        default="DRAFT",
        nullable=False,
        index=True
    )

    # Customer
    customer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("customers.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Warehouse (optional - for specific warehouse contracts)
    warehouse_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("warehouses.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )

    # Billing Model
    billing_type: Mapped[str] = mapped_column(
        String(30),
        default="HYBRID",
        nullable=False
    )
    billing_period: Mapped[str] = mapped_column(
        String(20),
        default="MONTHLY",
        nullable=False
    )
    billing_day: Mapped[int] = mapped_column(
        Integer,
        default=1,
        comment="Day of period to generate invoice"
    )

    # Contract Dates
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    renewal_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    auto_renew: Mapped[bool] = mapped_column(Boolean, default=False)

    # Minimums
    minimum_storage_fee: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        default=0
    )
    minimum_handling_fee: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        default=0
    )
    minimum_monthly_fee: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        default=0
    )

    # Payment Terms
    payment_terms_days: Mapped[int] = mapped_column(Integer, default=30)
    currency: Mapped[str] = mapped_column(String(3), default="INR")

    # Late Payment
    late_fee_percent: Mapped[Decimal] = mapped_column(
        Numeric(5, 2),
        default=Decimal("1.5")
    )
    grace_period_days: Mapped[int] = mapped_column(Integer, default=5)

    # Volume Discounts
    volume_discounts: Mapped[Optional[List[Dict[str, Any]]]] = mapped_column(
        JSONB,
        nullable=True,
        comment="Tiered discount based on volume"
    )

    # Special Terms
    special_terms: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Audit
    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )
    approved_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )
    approved_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    customer: Mapped["Customer"] = relationship("Customer")
    warehouse: Mapped[Optional["Warehouse"]] = relationship("Warehouse")
    rate_cards: Mapped[List["BillingRateCard"]] = relationship(
        "BillingRateCard",
        back_populates="contract",
        cascade="all, delete-orphan"
    )


class BillingRateCard(Base):
    """
    Rate card for billing charges.

    Defines rates for specific charge types.
    """
    __tablename__ = "billing_rate_cards"
    __table_args__ = (
        Index('ix_billing_rate_cards_contract', 'contract_id'),
        Index('ix_billing_rate_cards_charge', 'charge_type'),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
        index=True
    )

    # Contract Reference
    contract_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("billing_contracts.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Charge Definition
    charge_category: Mapped[str] = mapped_column(String(30), nullable=False)
    charge_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True
    )
    charge_name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Billing Model
    billing_model: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        comment="How this charge is billed"
    )
    uom: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        comment="Unit of measure"
    )

    # Rates
    base_rate: Mapped[Decimal] = mapped_column(
        Numeric(12, 4),
        nullable=False
    )
    min_charge: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        default=0
    )
    max_charge: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(10, 2),
        nullable=True
    )

    # Tiered Rates (optional)
    tiered_rates: Mapped[Optional[List[Dict[str, Any]]]] = mapped_column(
        JSONB,
        nullable=True,
        comment="Volume-based tiered rates"
    )

    # Time-based Rates (e.g., storage after X days)
    time_based_rates: Mapped[Optional[List[Dict[str, Any]]]] = mapped_column(
        JSONB,
        nullable=True,
        comment="Time-based rate adjustments"
    )

    # Effective Dates
    effective_from: Mapped[date] = mapped_column(Date, nullable=False)
    effective_to: Mapped[Optional[date]] = mapped_column(Date, nullable=True)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    contract: Mapped["BillingContract"] = relationship(
        "BillingContract",
        back_populates="rate_cards"
    )


class StorageCharge(Base):
    """
    Storage charge record.

    Daily/periodic storage charges.
    """
    __tablename__ = "storage_charges"
    __table_args__ = (
        Index('ix_storage_charges_date', 'charge_date'),
        Index('ix_storage_charges_customer', 'customer_id'),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
        index=True
    )

    # References
    contract_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("billing_contracts.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    customer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("customers.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    warehouse_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("warehouses.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    rate_card_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("billing_rate_cards.id", ondelete="SET NULL"),
        nullable=True
    )

    # Charge Date
    charge_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
        index=True
    )

    # Storage Details
    storage_type: Mapped[str] = mapped_column(String(50), nullable=False)
    zone_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        nullable=True
    )

    # Quantities
    quantity: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False
    )
    uom: Mapped[str] = mapped_column(String(20), nullable=False)

    # Rates
    rate: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)

    # Breakdown (optional)
    breakdown: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=True,
        comment="Detailed breakdown by bin/pallet"
    )

    # Invoice Reference
    invoice_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("billing_invoices.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    is_billed: Mapped[bool] = mapped_column(Boolean, default=False)

    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    contract: Mapped["BillingContract"] = relationship("BillingContract")
    customer: Mapped["Customer"] = relationship("Customer")
    warehouse: Mapped["Warehouse"] = relationship("Warehouse")


class HandlingCharge(Base):
    """
    Handling/activity charge record.

    Transaction-based charges (receiving, picking, etc.).
    """
    __tablename__ = "handling_charges"
    __table_args__ = (
        Index('ix_handling_charges_date', 'charge_date'),
        Index('ix_handling_charges_customer', 'customer_id'),
        Index('ix_handling_charges_type', 'charge_type'),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
        index=True
    )

    # References
    contract_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("billing_contracts.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    customer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("customers.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    warehouse_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("warehouses.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    rate_card_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("billing_rate_cards.id", ondelete="SET NULL"),
        nullable=True
    )

    # Charge Date
    charge_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
        index=True
    )

    # Charge Details
    charge_category: Mapped[str] = mapped_column(String(30), nullable=False)
    charge_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True
    )
    charge_description: Mapped[str] = mapped_column(String(200), nullable=False)

    # Source Reference
    source_type: Mapped[Optional[str]] = mapped_column(
        String(30),
        nullable=True,
        comment="ORDER, GRN, PICKLIST, etc."
    )
    source_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        nullable=True
    )
    source_number: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    # Quantities
    quantity: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False
    )
    uom: Mapped[str] = mapped_column(String(20), nullable=False)

    # Rates
    rate: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)

    # Labor (optional)
    labor_hours: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(6, 2),
        nullable=True
    )
    labor_rate: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(10, 2),
        nullable=True
    )
    labor_amount: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        default=0
    )

    # Invoice Reference
    invoice_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("billing_invoices.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    is_billed: Mapped[bool] = mapped_column(Boolean, default=False)

    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    contract: Mapped["BillingContract"] = relationship("BillingContract")
    customer: Mapped["Customer"] = relationship("Customer")
    warehouse: Mapped["Warehouse"] = relationship("Warehouse")


class ValueAddedServiceCharge(Base):
    """
    Value-added service charge record.

    VAS charges (kitting, labeling, special handling).
    """
    __tablename__ = "vas_charges"
    __table_args__ = (
        Index('ix_vas_charges_date', 'charge_date'),
        Index('ix_vas_charges_customer', 'customer_id'),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
        index=True
    )

    # References
    contract_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("billing_contracts.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    customer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("customers.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    warehouse_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("warehouses.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    rate_card_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("billing_rate_cards.id", ondelete="SET NULL"),
        nullable=True
    )

    # Charge Date
    charge_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
        index=True
    )

    # Service Details
    service_type: Mapped[str] = mapped_column(String(50), nullable=False)
    service_name: Mapped[str] = mapped_column(String(100), nullable=False)
    service_description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Source Reference
    source_type: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    source_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        nullable=True
    )
    source_number: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    # Quantities
    quantity: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False
    )
    uom: Mapped[str] = mapped_column(String(20), nullable=False)

    # Rates
    rate: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)

    # Materials (optional)
    materials_cost: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        default=0
    )
    materials_detail: Mapped[Optional[List[Dict[str, Any]]]] = mapped_column(
        JSONB,
        nullable=True
    )

    # Invoice Reference
    invoice_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("billing_invoices.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    is_billed: Mapped[bool] = mapped_column(Boolean, default=False)

    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    contract: Mapped["BillingContract"] = relationship("BillingContract")
    customer: Mapped["Customer"] = relationship("Customer")
    warehouse: Mapped["Warehouse"] = relationship("Warehouse")


class BillingInvoice(Base):
    """
    Billing invoice for warehouse services.
    """
    __tablename__ = "billing_invoices"
    __table_args__ = (
        Index('ix_billing_invoices_status', 'status'),
        Index('ix_billing_invoices_customer', 'customer_id'),
        Index('ix_billing_invoices_date', 'invoice_date'),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
        index=True
    )

    # Invoice Identity
    invoice_number: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        unique=True,
        index=True
    )
    status: Mapped[str] = mapped_column(
        String(30),
        default="DRAFT",
        nullable=False,
        index=True
    )

    # References
    contract_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("billing_contracts.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    customer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("customers.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    warehouse_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("warehouses.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )

    # Billing Period
    period_start: Mapped[date] = mapped_column(Date, nullable=False)
    period_end: Mapped[date] = mapped_column(Date, nullable=False)

    # Invoice Dates
    invoice_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
        index=True
    )
    due_date: Mapped[date] = mapped_column(Date, nullable=False)

    # Amounts
    storage_amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        default=0
    )
    handling_amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        default=0
    )
    vas_amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        default=0
    )
    labor_amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        default=0
    )

    subtotal: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False
    )

    # Adjustments
    discount_amount: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        default=0
    )
    discount_reason: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)

    adjustment_amount: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        default=0
    )
    adjustment_reason: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)

    # Tax
    tax_amount: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        default=0
    )
    tax_rate: Mapped[Decimal] = mapped_column(
        Numeric(5, 2),
        default=0
    )

    # Total
    total_amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False
    )

    # Payment
    paid_amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        default=0
    )
    balance_due: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False
    )

    # Late Fee
    late_fee: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        default=0
    )

    # Currency
    currency: Mapped[str] = mapped_column(String(3), default="INR")

    # Summary
    summary: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=True,
        comment="Breakdown summary"
    )

    # Sent Info
    sent_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )
    sent_to: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)

    # Payment Info
    last_payment_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    payment_reference: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    internal_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Dispute
    disputed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )
    dispute_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    dispute_resolved_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )

    # Audit
    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )
    approved_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )
    approved_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    contract: Mapped["BillingContract"] = relationship("BillingContract")
    customer: Mapped["Customer"] = relationship("Customer")
    warehouse: Mapped[Optional["Warehouse"]] = relationship("Warehouse")
    line_items: Mapped[List["BillingInvoiceItem"]] = relationship(
        "BillingInvoiceItem",
        back_populates="invoice",
        cascade="all, delete-orphan"
    )


class BillingInvoiceItem(Base):
    """
    Line item on a billing invoice.
    """
    __tablename__ = "billing_invoice_items"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
        index=True
    )

    # Invoice Reference
    invoice_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("billing_invoices.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Item Details
    charge_category: Mapped[str] = mapped_column(String(30), nullable=False)
    charge_type: Mapped[str] = mapped_column(String(50), nullable=False)
    description: Mapped[str] = mapped_column(String(500), nullable=False)

    # Quantities
    quantity: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False
    )
    uom: Mapped[str] = mapped_column(String(20), nullable=False)

    # Rates
    rate: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)

    # Sequence
    line_number: Mapped[int] = mapped_column(Integer, nullable=False)

    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    invoice: Mapped["BillingInvoice"] = relationship(
        "BillingInvoice",
        back_populates="line_items"
    )
