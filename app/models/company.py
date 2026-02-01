"""Company/Business Entity model for ERP configuration.

This is the central entity that owns the ERP system.
All invoices, POs, GST filings are done in the name of this company.
Supports multi-branch/multi-GSTIN setup for companies operating in multiple states.
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
    from app.models.warehouse import Warehouse
    from app.models.user import User
    from app.models.tds import TDSDeduction
    from app.models.accounting import ChartOfAccount


class CompanyType(str, Enum):
    """Type of company/business entity."""
    PRIVATE_LIMITED = "PRIVATE_LIMITED"           # Pvt Ltd
    PUBLIC_LIMITED = "PUBLIC_LIMITED"             # Ltd
    LLP = "LLP"                                   # Limited Liability Partnership
    PARTNERSHIP = "PARTNERSHIP"                   # Partnership Firm
    PROPRIETORSHIP = "PROPRIETORSHIP"             # Sole Proprietorship
    OPC = "OPC"                                   # One Person Company
    TRUST = "TRUST"
    SOCIETY = "SOCIETY"
    HUF = "HUF"                                   # Hindu Undivided Family
    GOVERNMENT = "GOVERNMENT"


class GSTRegistrationType(str, Enum):
    """GST Registration type."""
    REGULAR = "REGULAR"                           # Regular taxpayer
    COMPOSITION = "COMPOSITION"                   # Composition scheme
    CASUAL = "CASUAL"                             # Casual taxable person
    SEZ_UNIT = "SEZ_UNIT"                        # SEZ Unit
    SEZ_DEVELOPER = "SEZ_DEVELOPER"              # SEZ Developer
    INPUT_SERVICE_DISTRIBUTOR = "ISD"             # Input Service Distributor
    TDS_DEDUCTOR = "TDS_DEDUCTOR"                 # TDS Deductor
    TCS_COLLECTOR = "TCS_COLLECTOR"              # E-commerce TCS collector
    NON_RESIDENT = "NON_RESIDENT"                # Non-resident taxable person
    UNREGISTERED = "UNREGISTERED"                # Unregistered (< threshold)


class Company(Base):
    """
    Company Master - The business entity operating this ERP.

    This stores all legal, tax, and compliance details needed for:
    - GST invoicing and filing
    - E-Invoice generation (IRN)
    - E-Way Bill generation
    - TDS compliance
    - Financial reporting
    """
    __tablename__ = "companies"
    __table_args__ = (
        Index("ix_companies_gstin", "gstin"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )

    # ==================== Basic Information ====================

    # Legal Name (as per GST/MCA registration)
    legal_name: Mapped[str] = mapped_column(
        String(300),
        nullable=False,
        comment="Legal name as per GST/MCA registration"
    )

    # Trade Name (Brand name / DBA)
    trade_name: Mapped[Optional[str]] = mapped_column(
        String(300),
        nullable=True,
        comment="Trade name / Brand name"
    )

    # Short Code (for internal reference)
    code: Mapped[str] = mapped_column(
        String(20),
        unique=True,
        nullable=False,
        index=True,
        comment="Short code e.g., AQUA, HVL"
    )

    company_type: Mapped[str] = mapped_column(
        String(50),
        default="PRIVATE_LIMITED",
        nullable=False,
        comment="PRIVATE_LIMITED, PUBLIC_LIMITED, LLP, PARTNERSHIP, PROPRIETORSHIP, OPC, TRUST, SOCIETY, HUF, GOVERNMENT"
    )

    # ==================== Tax Registration (India) ====================

    # GSTIN - 15 digit GST Identification Number
    gstin: Mapped[str] = mapped_column(
        String(15),
        nullable=False,
        comment="15-digit GSTIN e.g., 27AAACT1234M1Z5"
    )

    gst_registration_type: Mapped[str] = mapped_column(
        String(50),
        default="REGULAR",
        nullable=False,
        comment="REGULAR, COMPOSITION, CASUAL, SEZ_UNIT, SEZ_DEVELOPER, ISD, TDS_DEDUCTOR, TCS_COLLECTOR, NON_RESIDENT, UNREGISTERED"
    )

    # State Code (first 2 digits of GSTIN)
    state_code: Mapped[str] = mapped_column(
        String(2),
        nullable=False,
        comment="GST State code e.g., 27 for Maharashtra"
    )

    # PAN - 10 character Permanent Account Number
    pan: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
        comment="10-character PAN e.g., AAACT1234M"
    )

    # TAN - Tax Deduction Account Number (for TDS)
    tan: Mapped[Optional[str]] = mapped_column(
        String(10),
        nullable=True,
        comment="10-character TAN for TDS"
    )

    # CIN - Corporate Identification Number (for companies)
    cin: Mapped[Optional[str]] = mapped_column(
        String(21),
        nullable=True,
        comment="21-character CIN e.g., U12345MH2020PTC123456"
    )

    # LLPIN - For LLP
    llpin: Mapped[Optional[str]] = mapped_column(
        String(10),
        nullable=True,
        comment="LLP Identification Number"
    )

    # MSME/Udyam Registration
    msme_registered: Mapped[bool] = mapped_column(Boolean, default=False)
    udyam_number: Mapped[Optional[str]] = mapped_column(
        String(30),
        nullable=True,
        comment="Udyam Registration Number e.g., UDYAM-MH-01-0012345"
    )
    msme_category: Mapped[Optional[str]] = mapped_column(
        String(20),
        nullable=True,
        comment="MICRO, SMALL, MEDIUM"
    )

    # ==================== Registered Address ====================

    address_line1: Mapped[str] = mapped_column(String(255), nullable=False)
    address_line2: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    city: Mapped[str] = mapped_column(String(100), nullable=False)
    district: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    state: Mapped[str] = mapped_column(String(100), nullable=False)
    pincode: Mapped[str] = mapped_column(String(10), nullable=False)
    country: Mapped[str] = mapped_column(String(50), default="India")

    # ==================== Contact Information ====================

    email: Mapped[str] = mapped_column(String(255), nullable=False)
    phone: Mapped[str] = mapped_column(String(20), nullable=False)
    mobile: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    fax: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    website: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # ==================== Bank Details (Primary) ====================

    bank_name: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    bank_branch: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    bank_account_number: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    bank_ifsc: Mapped[Optional[str]] = mapped_column(String(11), nullable=True)
    bank_account_type: Mapped[Optional[str]] = mapped_column(
        String(20),
        nullable=True,
        comment="CURRENT, SAVINGS, OD, CC"
    )
    bank_account_name: Mapped[Optional[str]] = mapped_column(
        String(200),
        nullable=True,
        comment="Name as per bank account"
    )

    # ==================== Branding ====================

    logo_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    logo_small_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    favicon_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    signature_url: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
        comment="Authorized signatory signature image"
    )

    # ==================== E-Invoice Configuration ====================

    einvoice_enabled: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        comment="Enable GST E-Invoice generation"
    )
    einvoice_username: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    einvoice_password_encrypted: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    einvoice_api_mode: Mapped[str] = mapped_column(
        String(20),
        default="SANDBOX",
        comment="SANDBOX or PRODUCTION"
    )

    # ==================== E-Way Bill Configuration ====================

    ewb_enabled: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        comment="Enable E-Way Bill generation"
    )
    ewb_username: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    ewb_password_encrypted: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    ewb_api_mode: Mapped[str] = mapped_column(
        String(20),
        default="SANDBOX",
        comment="SANDBOX or PRODUCTION"
    )

    # ==================== Invoice Settings ====================

    invoice_prefix: Mapped[str] = mapped_column(
        String(20),
        default="INV",
        comment="Invoice number prefix"
    )
    invoice_suffix: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    financial_year_start_month: Mapped[int] = mapped_column(
        Integer,
        default=4,
        comment="FY start month (4 = April for India)"
    )

    # Invoice Terms & Conditions
    invoice_terms: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Default terms on invoices"
    )
    invoice_notes: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Default notes on invoices"
    )
    invoice_footer: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Invoice footer text"
    )

    # ==================== PO Settings ====================

    po_prefix: Mapped[str] = mapped_column(
        String(20),
        default="PO",
        comment="Purchase Order prefix"
    )
    po_terms: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Default PO terms"
    )

    # ==================== Additional Config ====================

    # Default currency
    currency_code: Mapped[str] = mapped_column(String(3), default="INR")
    currency_symbol: Mapped[str] = mapped_column(String(5), default="₹")

    # Tax configuration
    default_cgst_rate: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=Decimal("9.00"))
    default_sgst_rate: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=Decimal("9.00"))
    default_igst_rate: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=Decimal("18.00"))

    # TDS settings
    tds_deductor: Mapped[bool] = mapped_column(Boolean, default=True)
    default_tds_rate: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=Decimal("10.00"))

    # Misc
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_primary: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        comment="Primary company for multi-company setup"
    )

    # Additional data stored as JSONB
    extra_data: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)

    # ==================== Audit ====================

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

    # ==================== Relationships ====================

    branches: Mapped[List["CompanyBranch"]] = relationship(
        "CompanyBranch",
        back_populates="company",
        cascade="all, delete-orphan"
    )
    bank_accounts: Mapped[List["CompanyBankAccount"]] = relationship(
        "CompanyBankAccount",
        back_populates="company",
        cascade="all, delete-orphan"
    )
    tds_deductions: Mapped[List["TDSDeduction"]] = relationship(
        "TDSDeduction",
        back_populates="company",
        cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Company(code='{self.code}', name='{self.legal_name}')>"

    @property
    def full_address(self) -> str:
        """Get formatted full address."""
        parts = [self.address_line1]
        if self.address_line2:
            parts.append(self.address_line2)
        parts.append(f"{self.city}, {self.state} - {self.pincode}")
        return ", ".join(parts)

    @property
    def gst_state_name(self) -> str:
        """Get state name from state code."""
        state_map = {
            "01": "Jammu & Kashmir", "02": "Himachal Pradesh", "03": "Punjab",
            "04": "Chandigarh", "05": "Uttarakhand", "06": "Haryana",
            "07": "Delhi", "08": "Rajasthan", "09": "Uttar Pradesh",
            "10": "Bihar", "11": "Sikkim", "12": "Arunachal Pradesh",
            "13": "Nagaland", "14": "Manipur", "15": "Mizoram",
            "16": "Tripura", "17": "Meghalaya", "18": "Assam",
            "19": "West Bengal", "20": "Jharkhand", "21": "Odisha",
            "22": "Chhattisgarh", "23": "Madhya Pradesh", "24": "Gujarat",
            "26": "Dadra & Nagar Haveli and Daman & Diu", "27": "Maharashtra",
            "28": "Andhra Pradesh (Old)", "29": "Karnataka", "30": "Goa",
            "31": "Lakshadweep", "32": "Kerala", "33": "Tamil Nadu",
            "34": "Puducherry", "35": "Andaman & Nicobar Islands",
            "36": "Telangana", "37": "Andhra Pradesh",
            "38": "Ladakh", "97": "Other Territory"
        }
        return state_map.get(self.state_code, self.state)


class CompanyBranch(Base):
    """
    Company Branch/Location for multi-state operations.

    Each branch can have its own GSTIN (for different states),
    address, and linked warehouse.
    """
    __tablename__ = "company_branches"
    __table_args__ = (
        UniqueConstraint("company_id", "code", name="uq_company_branch_code"),
        Index("ix_company_branches_gstin", "gstin"),
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

    # Branch Identification
    code: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        comment="Branch code e.g., MUM-HQ, DEL-01"
    )
    name: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
        comment="Branch name e.g., Mumbai Head Office"
    )
    branch_type: Mapped[str] = mapped_column(
        String(50),
        default="OFFICE",
        comment="OFFICE, WAREHOUSE, FACTORY, SHOWROOM, SERVICE_CENTER"
    )

    # GSTIN (can be different from head office for different states)
    gstin: Mapped[Optional[str]] = mapped_column(
        String(15),
        nullable=True,
        comment="Branch GSTIN (if different state)"
    )
    state_code: Mapped[str] = mapped_column(String(2), nullable=False)

    # Address
    address_line1: Mapped[str] = mapped_column(String(255), nullable=False)
    address_line2: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    city: Mapped[str] = mapped_column(String(100), nullable=False)
    state: Mapped[str] = mapped_column(String(100), nullable=False)
    pincode: Mapped[str] = mapped_column(String(10), nullable=False)

    # Contact
    email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    phone: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    contact_person: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # Linked Warehouse
    warehouse_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("warehouses.id", ondelete="SET NULL"),
        nullable=True
    )

    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_billing_address: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        comment="Use this address on invoices"
    )
    is_shipping_address: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        comment="Use this as dispatch address"
    )

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    company: Mapped["Company"] = relationship("Company", back_populates="branches")
    warehouse: Mapped[Optional["Warehouse"]] = relationship("Warehouse")

    def __repr__(self) -> str:
        return f"<CompanyBranch(code='{self.code}', name='{self.name}')>"


class CompanyBankAccount(Base):
    """
    Multiple bank accounts for the company.
    Used for receiving payments and making vendor payments.
    """
    __tablename__ = "company_bank_accounts"

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

    # Bank Details
    bank_name: Mapped[str] = mapped_column(String(200), nullable=False)
    branch_name: Mapped[str] = mapped_column(String(200), nullable=False)
    account_number: Mapped[str] = mapped_column(String(30), nullable=False)
    ifsc_code: Mapped[str] = mapped_column(String(11), nullable=False)
    account_type: Mapped[str] = mapped_column(
        String(20),
        default="CURRENT",
        comment="CURRENT, SAVINGS, OD, CC"
    )
    account_name: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
        comment="Name as per bank"
    )

    # UPI
    upi_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # SWIFT (for international transactions)
    swift_code: Mapped[Optional[str]] = mapped_column(String(15), nullable=True)

    # Purpose
    purpose: Mapped[str] = mapped_column(
        String(50),
        default="GENERAL",
        comment="GENERAL, COLLECTIONS, PAYMENTS, SALARY, TAX"
    )

    is_primary: Mapped[bool] = mapped_column(Boolean, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # For display on invoices
    show_on_invoice: Mapped[bool] = mapped_column(Boolean, default=True)

    # Link to Chart of Accounts (for Journal Entries)
    ledger_account_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("chart_of_accounts.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="Linked ledger account for journal entries"
    )

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    # Relationships
    company: Mapped["Company"] = relationship("Company", back_populates="bank_accounts")
    ledger_account: Mapped[Optional["ChartOfAccount"]] = relationship("ChartOfAccount", foreign_keys=[ledger_account_id])

    def __repr__(self) -> str:
        return f"<CompanyBankAccount(bank='{self.bank_name}', account='{self.account_number[-4:]}')>"
