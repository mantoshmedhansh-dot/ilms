"""Fixed Assets module models.

Supports:
- Asset categories with depreciation settings
- Asset register with detailed tracking
- Depreciation schedules (SLM, WDV)
- Asset transfers between locations
- Asset disposal and write-off
- Asset maintenance tracking
"""
import uuid
from datetime import datetime, date, timezone
from enum import Enum
from typing import TYPE_CHECKING, Optional, List
from decimal import Decimal

from sqlalchemy import String, Boolean, DateTime, ForeignKey, Integer, Text, Numeric, Date
from sqlalchemy import UniqueConstraint, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.user import User


# ==================== Enums ====================

class DepreciationMethod(str, Enum):
    """Depreciation calculation methods."""
    SLM = "SLM"  # Straight Line Method
    WDV = "WDV"  # Written Down Value


class AssetStatus(str, Enum):
    """Asset lifecycle status."""
    ACTIVE = "ACTIVE"
    UNDER_MAINTENANCE = "UNDER_MAINTENANCE"
    DISPOSED = "DISPOSED"
    WRITTEN_OFF = "WRITTEN_OFF"
    TRANSFERRED = "TRANSFERRED"


class TransferStatus(str, Enum):
    """Asset transfer status."""
    PENDING = "PENDING"
    IN_TRANSIT = "IN_TRANSIT"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


class MaintenanceStatus(str, Enum):
    """Maintenance record status."""
    SCHEDULED = "SCHEDULED"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


# ==================== Asset Category ====================

class AssetCategory(Base):
    """
    Categories for fixed assets with depreciation settings.
    Examples: Furniture, Vehicles, Office Equipment, Plant & Machinery
    """
    __tablename__ = "asset_categories"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )

    # Category Details
    code: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Depreciation Settings
    depreciation_method: Mapped[str] = mapped_column(
        String(50),
        default="SLM",
        nullable=False,
        comment="SLM (Straight Line), WDV (Written Down Value)"
    )
    depreciation_rate: Mapped[Decimal] = mapped_column(
        Numeric(5, 2),
        nullable=False,
        comment="Annual depreciation rate in percentage"
    )
    useful_life_years: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Expected useful life in years"
    )

    # Accounting
    asset_account_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
        comment="GL Account for Asset"
    )
    depreciation_account_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
        comment="GL Account for Accumulated Depreciation"
    )
    expense_account_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
        comment="GL Account for Depreciation Expense"
    )

    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

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
    assets: Mapped[List["Asset"]] = relationship("Asset", back_populates="category")

    def __repr__(self) -> str:
        return f"<AssetCategory(code='{self.code}', name='{self.name}')>"


# ==================== Asset ====================

class Asset(Base):
    """
    Fixed Asset register with full lifecycle tracking.
    """
    __tablename__ = "assets"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )

    # Asset Identification
    asset_code: Mapped[str] = mapped_column(
        String(30),
        unique=True,
        nullable=False,
        comment="FA-YYYYMM-XXXX"
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    category_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("asset_categories.id", ondelete="RESTRICT"),
        nullable=False,
        index=True
    )

    # Serial/Model Info
    serial_number: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    model_number: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    manufacturer: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # Location
    warehouse_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
        comment="Current location warehouse"
    )
    location_details: Mapped[Optional[str]] = mapped_column(
        String(200),
        nullable=True,
        comment="Room, floor, department etc."
    )

    # Custodian
    custodian_employee_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
        comment="Employee responsible for the asset"
    )
    department_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
        comment="Department using the asset"
    )

    # Purchase Details
    purchase_date: Mapped[date] = mapped_column(Date, nullable=False)
    purchase_price: Mapped[Decimal] = mapped_column(
        Numeric(14, 2),
        nullable=False,
        comment="Original purchase price"
    )
    purchase_invoice_no: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    vendor_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        nullable=True
    )
    po_number: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    # Capitalization
    capitalization_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
        comment="Date when asset was put to use"
    )
    installation_cost: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        default=0,
        comment="Installation and setup costs"
    )
    other_costs: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        default=0,
        comment="Freight, customs, etc."
    )
    capitalized_value: Mapped[Decimal] = mapped_column(
        Numeric(14, 2),
        nullable=False,
        comment="Total capitalized value = Purchase + Installation + Other"
    )

    # Depreciation Settings (can override category defaults)
    depreciation_method: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        comment="Override category method: SLM, WDV"
    )
    depreciation_rate: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(5, 2),
        nullable=True,
        comment="Override category rate"
    )
    useful_life_years: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        comment="Override category useful life"
    )
    salvage_value: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        default=0,
        comment="Expected value at end of useful life"
    )

    # Current Values (updated monthly)
    accumulated_depreciation: Mapped[Decimal] = mapped_column(
        Numeric(14, 2),
        default=0,
        nullable=False
    )
    current_book_value: Mapped[Decimal] = mapped_column(
        Numeric(14, 2),
        nullable=False,
        comment="Capitalized Value - Accumulated Depreciation"
    )
    last_depreciation_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)

    # Warranty
    warranty_start_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    warranty_end_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    warranty_details: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Insurance
    insured: Mapped[bool] = mapped_column(Boolean, default=False)
    insurance_policy_no: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    insurance_value: Mapped[Optional[Decimal]] = mapped_column(Numeric(14, 2), nullable=True)
    insurance_expiry: Mapped[Optional[date]] = mapped_column(Date, nullable=True)

    # Status
    status: Mapped[str] = mapped_column(
        String(50),
        default="ACTIVE",
        nullable=False,
        index=True,
        comment="ACTIVE, UNDER_MAINTENANCE, DISPOSED, WRITTEN_OFF, TRANSFERRED"
    )

    # Disposal (if disposed)
    disposal_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    disposal_price: Mapped[Optional[Decimal]] = mapped_column(Numeric(14, 2), nullable=True)
    disposal_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    gain_loss_on_disposal: Mapped[Optional[Decimal]] = mapped_column(Numeric(14, 2), nullable=True)

    # Documents
    documents: Mapped[Optional[dict]] = mapped_column(
        JSONB,
        nullable=True,
        comment="Array of document URLs"
    )
    images: Mapped[Optional[dict]] = mapped_column(
        JSONB,
        nullable=True,
        comment="Array of image URLs"
    )

    # Notes
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

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
    category: Mapped["AssetCategory"] = relationship("AssetCategory", back_populates="assets")
    depreciation_entries: Mapped[List["DepreciationEntry"]] = relationship(
        "DepreciationEntry",
        back_populates="asset",
        order_by="DepreciationEntry.period_date"
    )
    transfers: Mapped[List["AssetTransfer"]] = relationship(
        "AssetTransfer",
        back_populates="asset",
        foreign_keys="AssetTransfer.asset_id"
    )
    maintenance_records: Mapped[List["AssetMaintenance"]] = relationship(
        "AssetMaintenance",
        back_populates="asset"
    )

    __table_args__ = (
        Index('idx_assets_category', 'category_id'),
        Index('idx_assets_status', 'status'),
        Index('idx_assets_warehouse', 'warehouse_id'),
    )

    def __repr__(self) -> str:
        return f"<Asset(code='{self.asset_code}', name='{self.name}')>"


# ==================== Depreciation Entry ====================

class DepreciationEntry(Base):
    """
    Monthly depreciation entries for assets.
    """
    __tablename__ = "depreciation_entries"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )

    # References
    asset_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("assets.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Period
    period_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
        comment="First of the month"
    )
    financial_year: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
        comment="2025-26"
    )

    # Values at start of period
    opening_book_value: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)

    # Depreciation
    depreciation_method: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="SLM, WDV"
    )
    depreciation_rate: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)
    depreciation_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)

    # Values at end of period
    closing_book_value: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    accumulated_depreciation: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)

    # Journal Entry (if posted)
    journal_entry_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
        comment="Related journal entry"
    )
    is_posted: Mapped[bool] = mapped_column(Boolean, default=False)

    # Processing
    processed_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )
    processed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    # Relationships
    asset: Mapped["Asset"] = relationship("Asset", back_populates="depreciation_entries")

    __table_args__ = (
        UniqueConstraint('asset_id', 'period_date', name='uq_depreciation_asset_period'),
        Index('idx_depreciation_period', 'period_date'),
        Index('idx_depreciation_fy', 'financial_year'),
    )

    def __repr__(self) -> str:
        return f"<DepreciationEntry(asset_id='{self.asset_id}', period='{self.period_date}', amount={self.depreciation_amount})>"


# ==================== Asset Transfer ====================

class AssetTransfer(Base):
    """
    Transfer of assets between locations/departments.
    """
    __tablename__ = "asset_transfers"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )

    # Asset
    asset_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("assets.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Transfer Number
    transfer_number: Mapped[str] = mapped_column(
        String(30),
        unique=True,
        nullable=False,
        comment="AT-YYYYMMDD-XXXX"
    )

    # From Location
    from_warehouse_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True)
    from_department_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True)
    from_custodian_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True)
    from_location_details: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)

    # To Location
    to_warehouse_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True)
    to_department_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True)
    to_custodian_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True)
    to_location_details: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)

    # Transfer Details
    transfer_date: Mapped[date] = mapped_column(Date, nullable=False)
    reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Status
    status: Mapped[str] = mapped_column(
        String(50),
        default="PENDING",
        nullable=False,
        comment="PENDING, IN_TRANSIT, COMPLETED, CANCELLED"
    )

    # Approval
    requested_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=False
    )
    approved_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )
    approved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Completion
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    received_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )

    # Notes
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

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
    asset: Mapped["Asset"] = relationship("Asset", back_populates="transfers")
    requester: Mapped["User"] = relationship("User", foreign_keys=[requested_by])

    def __repr__(self) -> str:
        return f"<AssetTransfer(number='{self.transfer_number}', status='{self.status}')>"


# ==================== Asset Maintenance ====================

class AssetMaintenance(Base):
    """
    Maintenance records for assets.
    """
    __tablename__ = "asset_maintenance"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )

    # Asset
    asset_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("assets.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Maintenance Number
    maintenance_number: Mapped[str] = mapped_column(
        String(30),
        unique=True,
        nullable=False,
        comment="AM-YYYYMMDD-XXXX"
    )

    # Maintenance Type
    maintenance_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="PREVENTIVE, CORRECTIVE, EMERGENCY"
    )
    description: Mapped[str] = mapped_column(Text, nullable=False)

    # Schedule
    scheduled_date: Mapped[date] = mapped_column(Date, nullable=False)
    started_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    completed_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)

    # Cost
    estimated_cost: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    actual_cost: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)

    # Vendor
    vendor_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True)
    vendor_invoice_no: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    # Status
    status: Mapped[str] = mapped_column(
        String(50),
        default="SCHEDULED",
        nullable=False,
        comment="SCHEDULED, IN_PROGRESS, COMPLETED, CANCELLED"
    )

    # Findings
    findings: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    parts_replaced: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    recommendations: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Assigned
    assigned_to: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )

    # Documents
    documents: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)

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
    asset: Mapped["Asset"] = relationship("Asset", back_populates="maintenance_records")

    __table_args__ = (
        Index('idx_maintenance_asset', 'asset_id'),
        Index('idx_maintenance_status', 'status'),
    )

    def __repr__(self) -> str:
        return f"<AssetMaintenance(number='{self.maintenance_number}', type='{self.maintenance_type}')>"
