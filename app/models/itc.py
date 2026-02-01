"""ITC (Input Tax Credit) Ledger models for GST compliance.

Tracks:
- Available ITC from purchases
- ITC utilization against output tax
- ITC reversal as per GST rules
- GSTR-2A/2B matching
"""
import uuid
from datetime import datetime, date, timezone
from decimal import Decimal
from enum import Enum
from typing import TYPE_CHECKING, Optional, List

from sqlalchemy import String, Boolean, DateTime, ForeignKey, Integer, Text, Numeric, Date
from sqlalchemy import UniqueConstraint, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.company import Company
    from app.models.vendor import Vendor
    from app.models.user import User


class ITCStatus(str, Enum):
    """ITC status enumeration."""
    AVAILABLE = "AVAILABLE"      # ITC available for utilization
    UTILIZED = "UTILIZED"        # ITC utilized against output tax
    REVERSED = "REVERSED"        # ITC reversed as per rules
    BLOCKED = "BLOCKED"          # ITC blocked (not eligible)
    PENDING = "PENDING"          # Pending verification


class ITCType(str, Enum):
    """ITC type enumeration."""
    INPUTS = "INPUTS"            # ITC on inputs (raw materials)
    INPUT_SERVICES = "INPUT_SERVICES"  # ITC on input services
    CAPITAL_GOODS = "CAPITAL_GOODS"    # ITC on capital goods
    ISD = "ISD"                  # Input Service Distributor


class ITCMatchStatus(str, Enum):
    """GSTR-2A/2B matching status."""
    MATCHED = "MATCHED"          # Matched with GSTR-2A/2B
    UNMATCHED = "UNMATCHED"      # Not found in GSTR-2A/2B
    PARTIAL_MATCH = "PARTIAL_MATCH"  # Partial match (amount difference)
    PENDING = "PENDING"          # Pending verification


class ITCLedger(Base):
    """
    ITC Ledger for tracking Input Tax Credit.

    Each record represents ITC from a single vendor invoice.
    """
    __tablename__ = "itc_ledger"
    __table_args__ = (
        UniqueConstraint("company_id", "vendor_gstin", "invoice_number", name="uq_itc_invoice"),
        Index("ix_itc_ledger_period", "period"),
        Index("ix_itc_ledger_status", "status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )

    # Company
    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Period (YYYYMM format)
    period: Mapped[str] = mapped_column(
        String(6),
        nullable=False,
        comment="Return period in YYYYMM format e.g., 202601"
    )

    # Vendor Details
    vendor_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("vendors.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    vendor_gstin: Mapped[str] = mapped_column(
        String(15),
        nullable=False,
        index=True,
        comment="Vendor GSTIN"
    )
    vendor_name: Mapped[str] = mapped_column(
        String(200),
        nullable=False
    )

    # Invoice Details
    invoice_number: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="Vendor invoice number"
    )
    invoice_date: Mapped[date] = mapped_column(
        Date,
        nullable=False
    )
    invoice_value: Mapped[Decimal] = mapped_column(
        Numeric(14, 2),
        nullable=False,
        comment="Total invoice value"
    )

    # ITC Type
    itc_type: Mapped[str] = mapped_column(
        String(50),
        default="INPUTS",
        nullable=False,
        comment="INPUTS, INPUT_SERVICES, CAPITAL_GOODS, ISD"
    )

    # Taxable Value
    taxable_value: Mapped[Decimal] = mapped_column(
        Numeric(14, 2),
        nullable=False
    )

    # ITC Amounts
    cgst_itc: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        default=Decimal("0"),
        comment="CGST ITC amount"
    )
    sgst_itc: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        default=Decimal("0"),
        comment="SGST ITC amount"
    )
    igst_itc: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        default=Decimal("0"),
        comment="IGST ITC amount"
    )
    cess_itc: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        default=Decimal("0"),
        comment="Cess ITC amount"
    )
    total_itc: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
        comment="Total ITC amount"
    )

    # Status
    status: Mapped[str] = mapped_column(
        String(50),
        default="AVAILABLE",
        nullable=False,
        comment="AVAILABLE, UTILIZED, REVERSED, BLOCKED, PENDING"
    )

    # GSTR-2A/2B Matching
    gstr2a_matched: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        comment="Matched with GSTR-2A"
    )
    gstr2b_matched: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        comment="Matched with GSTR-2B"
    )
    match_status: Mapped[str] = mapped_column(
        String(50),
        default="PENDING",
        nullable=False,
        comment="MATCHED, UNMATCHED, PARTIAL_MATCH, PENDING"
    )
    match_date: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )
    match_difference: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(12, 2),
        nullable=True,
        comment="Difference in amount if partial match"
    )

    # Utilization Details
    utilized_amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        default=Decimal("0"),
        comment="Amount utilized against output tax"
    )
    utilized_in_period: Mapped[Optional[str]] = mapped_column(
        String(6),
        nullable=True,
        comment="Period in which ITC was utilized"
    )
    utilized_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )

    # Reversal Details
    reversed_amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        default=Decimal("0"),
        comment="Amount reversed"
    )
    reversal_reason: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True
    )
    reversed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )

    # HSN Details
    hsn_code: Mapped[Optional[str]] = mapped_column(
        String(8),
        nullable=True
    )
    description: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True
    )

    # Place of Supply
    place_of_supply: Mapped[Optional[str]] = mapped_column(
        String(2),
        nullable=True,
        comment="State code"
    )
    is_interstate: Mapped[bool] = mapped_column(
        Boolean,
        default=False
    )

    # Reference to purchase invoice (if linked)
    purchase_invoice_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        nullable=True
    )

    # GSTR-2A/2B Raw Data
    gstr2a_data: Mapped[Optional[dict]] = mapped_column(
        JSONB,
        nullable=True,
        comment="Raw GSTR-2A data for this invoice"
    )
    gstr2b_data: Mapped[Optional[dict]] = mapped_column(
        JSONB,
        nullable=True,
        comment="Raw GSTR-2B data for this invoice"
    )

    # Audit
    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )
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
    company: Mapped["Company"] = relationship("Company")
    vendor: Mapped[Optional["Vendor"]] = relationship("Vendor")

    @property
    def available_itc(self) -> Decimal:
        """Calculate available ITC after utilization and reversal."""
        return self.total_itc - self.utilized_amount - self.reversed_amount

    @property
    def is_eligible(self) -> bool:
        """Check if ITC is eligible for utilization."""
        return self.status == ITCStatus.AVAILABLE and self.gstr2b_matched

    def __repr__(self) -> str:
        return f"<ITCLedger(vendor={self.vendor_gstin}, invoice={self.invoice_number}, itc={self.total_itc})>"


class ITCSummary(Base):
    """
    Monthly ITC summary for reporting.

    Aggregates ITC by period and type.
    """
    __tablename__ = "itc_summary"
    __table_args__ = (
        UniqueConstraint("company_id", "period", name="uq_itc_summary_period"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )

    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    period: Mapped[str] = mapped_column(
        String(6),
        nullable=False,
        comment="Return period in YYYYMM format"
    )

    # Opening Balance
    opening_cgst: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=Decimal("0"))
    opening_sgst: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=Decimal("0"))
    opening_igst: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=Decimal("0"))
    opening_cess: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=Decimal("0"))

    # ITC Availed (from purchases)
    availed_cgst: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=Decimal("0"))
    availed_sgst: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=Decimal("0"))
    availed_igst: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=Decimal("0"))
    availed_cess: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=Decimal("0"))

    # ITC Reversed
    reversed_cgst: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=Decimal("0"))
    reversed_sgst: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=Decimal("0"))
    reversed_igst: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=Decimal("0"))
    reversed_cess: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=Decimal("0"))

    # ITC Utilized
    utilized_cgst: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=Decimal("0"))
    utilized_sgst: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=Decimal("0"))
    utilized_igst: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=Decimal("0"))
    utilized_cess: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=Decimal("0"))

    # Closing Balance
    closing_cgst: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=Decimal("0"))
    closing_sgst: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=Decimal("0"))
    closing_igst: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=Decimal("0"))
    closing_cess: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=Decimal("0"))

    # Matching Statistics
    total_invoices: Mapped[int] = mapped_column(Integer, default=0)
    matched_invoices: Mapped[int] = mapped_column(Integer, default=0)
    unmatched_invoices: Mapped[int] = mapped_column(Integer, default=0)

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
    def total_opening(self) -> Decimal:
        return self.opening_cgst + self.opening_sgst + self.opening_igst + self.opening_cess

    @property
    def total_availed(self) -> Decimal:
        return self.availed_cgst + self.availed_sgst + self.availed_igst + self.availed_cess

    @property
    def total_reversed(self) -> Decimal:
        return self.reversed_cgst + self.reversed_sgst + self.reversed_igst + self.reversed_cess

    @property
    def total_utilized(self) -> Decimal:
        return self.utilized_cgst + self.utilized_sgst + self.utilized_igst + self.utilized_cess

    @property
    def total_closing(self) -> Decimal:
        return self.closing_cgst + self.closing_sgst + self.closing_igst + self.closing_cess

    def __repr__(self) -> str:
        return f"<ITCSummary(period={self.period}, closing={self.total_closing})>"


class GSTFiling(Base):
    """
    GST Filing tracking model.

    Records all GST return filing attempts and status.
    """
    __tablename__ = "gst_filings"
    __table_args__ = (
        UniqueConstraint("company_id", "return_type", "period", name="uq_gst_filing"),
        Index("ix_gst_filings_period", "period"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )

    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Return Details
    return_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        comment="GSTR1, GSTR3B, GSTR2A, GSTR9, etc."
    )
    period: Mapped[str] = mapped_column(
        String(6),
        nullable=False,
        comment="Return period in MMYYYY format"
    )
    financial_year: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
        comment="e.g., 2025-26"
    )

    # Filing Status
    status: Mapped[str] = mapped_column(
        String(50),
        default="DRAFT",
        nullable=False,
        comment="DRAFT, PENDING, IN_PROGRESS, SUBMITTED, FILED, ACCEPTED, REJECTED, ERROR"
    )

    # Filing Reference
    arn: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        comment="Acknowledgement Reference Number"
    )
    reference_id: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True
    )

    # Filing Dates
    due_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    submitted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    filed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Summary Values
    total_taxable_value: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=Decimal("0"))
    total_cgst: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0"))
    total_sgst: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0"))
    total_igst: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0"))
    total_cess: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0"))
    total_tax: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=Decimal("0"))

    # Invoice Counts
    b2b_invoice_count: Mapped[int] = mapped_column(Integer, default=0)
    b2c_invoice_count: Mapped[int] = mapped_column(Integer, default=0)
    total_invoice_count: Mapped[int] = mapped_column(Integer, default=0)

    # Filing Data (stored JSON)
    filing_data: Mapped[Optional[dict]] = mapped_column(
        JSONB,
        nullable=True,
        comment="Complete filing JSON data"
    )

    # Response from portal
    portal_response: Mapped[Optional[dict]] = mapped_column(
        JSONB,
        nullable=True
    )

    # Error details
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    error_details: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)

    # Audit
    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )
    filed_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )
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

    def __repr__(self) -> str:
        return f"<GSTFiling(type={self.return_type}, period={self.period}, status={self.status})>"
