"""Pydantic schemas for Company/Business Entity module."""
from datetime import datetime
from typing import Optional, List, Annotated
from decimal import Decimal
from uuid import UUID
from pydantic import BaseModel, Field, ConfigDict, EmailStr, PlainSerializer, field_validator

from app.schemas.base import BaseResponseSchema
import re

from app.models.company import CompanyType, GSTRegistrationType

# Custom serializer for Decimal to ensure JSON compatibility
DecimalAsFloat = Annotated[Decimal, PlainSerializer(lambda x: float(x), return_type=float)]


# ==================== Company Schemas ====================

class CompanyBase(BaseModel):
    """Base schema for Company."""
    # Basic Info
    legal_name: str = Field(..., min_length=2, max_length=300, description="Legal name as per GST/MCA registration")
    trade_name: Optional[str] = Field(None, max_length=300, description="Trade/Brand name")
    code: str = Field(..., min_length=2, max_length=20, description="Short code e.g., AQUA, HVL")
    company_type: CompanyType = CompanyType.PRIVATE_LIMITED

    # Tax Registration (India)
    gstin: str = Field(..., min_length=15, max_length=15, description="15-digit GSTIN")
    gst_registration_type: GSTRegistrationType = GSTRegistrationType.REGULAR
    state_code: str = Field(..., min_length=2, max_length=2, description="GST State code")
    pan: str = Field(..., min_length=10, max_length=10, description="10-character PAN")
    tan: Optional[str] = Field(None, min_length=10, max_length=10, description="TAN for TDS")
    cin: Optional[str] = Field(None, max_length=21, description="Company Identification Number")
    llpin: Optional[str] = Field(None, max_length=10, description="LLP Identification Number")

    # MSME
    msme_registered: bool = False
    udyam_number: Optional[str] = Field(None, max_length=30, description="Udyam Registration Number")
    msme_category: Optional[str] = Field(None, description="MICRO, SMALL, MEDIUM")

    # Registered Address
    address_line1: str = Field(..., max_length=255)
    address_line2: Optional[str] = Field(None, max_length=255)
    city: str = Field(..., max_length=100)
    district: Optional[str] = Field(None, max_length=100)
    state: str = Field(..., max_length=100)
    pincode: str = Field(..., max_length=10)
    country: str = "India"

    # Contact
    email: EmailStr
    phone: str = Field(..., max_length=20)
    mobile: Optional[str] = Field(None, max_length=20)
    fax: Optional[str] = Field(None, max_length=20)
    website: Optional[str] = Field(None, max_length=255)

    # Primary Bank Details
    bank_name: Optional[str] = Field(None, max_length=200)
    bank_branch: Optional[str] = Field(None, max_length=200)
    bank_account_number: Optional[str] = Field(None, max_length=30)
    bank_ifsc: Optional[str] = Field(None, max_length=11)
    bank_account_type: Optional[str] = Field(None, description="CURRENT, SAVINGS, OD, CC")
    bank_account_name: Optional[str] = Field(None, max_length=200)

    # Branding
    logo_url: Optional[str] = Field(None, max_length=500)
    logo_small_url: Optional[str] = Field(None, max_length=500)
    favicon_url: Optional[str] = Field(None, max_length=500)
    signature_url: Optional[str] = Field(None, max_length=500, description="Authorized signatory signature")

    # E-Invoice Config
    einvoice_enabled: bool = False
    einvoice_username: Optional[str] = Field(None, max_length=100)
    einvoice_api_mode: str = Field("SANDBOX", description="SANDBOX or PRODUCTION")

    # E-Way Bill Config
    ewb_enabled: bool = False
    ewb_username: Optional[str] = Field(None, max_length=100)
    ewb_api_mode: str = Field("SANDBOX", description="SANDBOX or PRODUCTION")

    # Invoice Settings
    invoice_prefix: str = Field("INV", max_length=20)
    invoice_suffix: Optional[str] = Field(None, max_length=20)
    financial_year_start_month: int = Field(4, ge=1, le=12, description="FY start month (4 = April)")
    invoice_terms: Optional[str] = None
    invoice_notes: Optional[str] = None
    invoice_footer: Optional[str] = None

    # PO Settings
    po_prefix: str = Field("PO", max_length=20)
    po_terms: Optional[str] = None

    # Currency
    currency_code: str = Field("INR", max_length=3)
    currency_symbol: str = Field("₹", max_length=5)

    # Tax Defaults (use DecimalAsFloat for JSON serialization)
    default_cgst_rate: DecimalAsFloat = Field(Decimal("9.00"), ge=0, le=100)
    default_sgst_rate: DecimalAsFloat = Field(Decimal("9.00"), ge=0, le=100)
    default_igst_rate: DecimalAsFloat = Field(Decimal("18.00"), ge=0, le=100)

    # TDS
    tds_deductor: bool = True
    default_tds_rate: DecimalAsFloat = Field(Decimal("10.00"), ge=0, le=100)


# URL validation mixin - only for input schemas, not response schemas
def validate_url_format(v):
    """Validate that URL fields contain valid URLs, not just filenames."""
    if v is None or v == '':
        return v
    # Check if it looks like a URL (starts with http://, https://, or /)
    if not re.match(r'^(https?://|/)', v, re.IGNORECASE):
        raise ValueError(
            f"Invalid URL format. Please enter a complete URL starting with "
            f"'http://' or 'https://'. Got: '{v}'"
        )
    return v


class CompanyCreate(CompanyBase):
    """Schema for creating Company."""
    einvoice_password: Optional[str] = Field(None, description="E-Invoice portal password")
    ewb_password: Optional[str] = Field(None, description="E-Way Bill portal password")
    is_primary: bool = False


class CompanyUpdate(BaseModel):
    """Schema for updating Company."""
    legal_name: Optional[str] = Field(None, max_length=300)
    trade_name: Optional[str] = Field(None, max_length=300)
    company_type: Optional[CompanyType] = None

    # Tax
    gstin: Optional[str] = Field(None, min_length=15, max_length=15)
    gst_registration_type: Optional[GSTRegistrationType] = None
    state_code: Optional[str] = Field(None, max_length=2)
    pan: Optional[str] = Field(None, max_length=10)
    tan: Optional[str] = Field(None, max_length=10)
    cin: Optional[str] = Field(None, max_length=21)

    # MSME
    msme_registered: Optional[bool] = None
    udyam_number: Optional[str] = None
    msme_category: Optional[str] = None

    # Address
    address_line1: Optional[str] = Field(None, max_length=255)
    address_line2: Optional[str] = Field(None, max_length=255)
    city: Optional[str] = Field(None, max_length=100)
    state: Optional[str] = Field(None, max_length=100)
    pincode: Optional[str] = Field(None, max_length=10)

    # Contact
    email: Optional[EmailStr] = None
    phone: Optional[str] = Field(None, max_length=20)
    mobile: Optional[str] = Field(None, max_length=20)
    website: Optional[str] = Field(None, max_length=255)

    # Bank
    bank_name: Optional[str] = Field(None, max_length=200)
    bank_branch: Optional[str] = Field(None, max_length=200)
    bank_account_number: Optional[str] = Field(None, max_length=30)
    bank_ifsc: Optional[str] = Field(None, max_length=11)
    bank_account_type: Optional[str] = None
    bank_account_name: Optional[str] = Field(None, max_length=200)

    # Branding
    logo_url: Optional[str] = Field(None, max_length=500)
    logo_small_url: Optional[str] = Field(None, max_length=500)
    signature_url: Optional[str] = Field(None, max_length=500)

    # E-Invoice
    einvoice_enabled: Optional[bool] = None
    einvoice_username: Optional[str] = Field(None, max_length=100)
    einvoice_password: Optional[str] = None
    einvoice_api_mode: Optional[str] = None

    # E-Way Bill
    ewb_enabled: Optional[bool] = None
    ewb_username: Optional[str] = Field(None, max_length=100)
    ewb_password: Optional[str] = None
    ewb_api_mode: Optional[str] = None

    # Invoice Settings
    invoice_prefix: Optional[str] = Field(None, max_length=20)
    invoice_terms: Optional[str] = None
    invoice_notes: Optional[str] = None
    invoice_footer: Optional[str] = None

    # PO Settings
    po_prefix: Optional[str] = Field(None, max_length=20)
    po_terms: Optional[str] = None

    # Tax Defaults
    default_cgst_rate: Optional[Decimal] = None
    default_sgst_rate: Optional[Decimal] = None
    default_igst_rate: Optional[Decimal] = None
    default_tds_rate: Optional[Decimal] = None

    is_active: Optional[bool] = None
    is_primary: Optional[bool] = None

    @field_validator('logo_url', 'logo_small_url', 'signature_url', mode='before')
    @classmethod
    def validate_url_fields(cls, v):
        """Validate that URL fields contain valid URLs, not just filenames."""
        if v is None or v == '':
            return v
        # Check if it looks like a URL (starts with http://, https://, or /)
        if not re.match(r'^(https?://|/)', v, re.IGNORECASE):
            raise ValueError(
                f"Invalid URL format. Please enter a complete URL starting with "
                f"'http://' or 'https://'. Got: '{v}'"
            )
        return v


class CompanyResponse(BaseResponseSchema):
    """Response schema for Company."""
    id: UUID

    # Basic Info
    legal_name: Optional[str] = None
    trade_name: Optional[str] = None
    code: Optional[str] = None
    company_type: Optional[str] = None

    # Tax Registration
    gstin: Optional[str] = None
    gst_registration_type: Optional[str] = None
    state_code: Optional[str] = None
    pan: Optional[str] = None
    tan: Optional[str] = None
    cin: Optional[str] = None
    llpin: Optional[str] = None

    # MSME
    msme_registered: bool = False
    udyam_number: Optional[str] = None
    msme_category: Optional[str] = None

    # Address
    address_line1: Optional[str] = None
    address_line2: Optional[str] = None
    city: Optional[str] = None
    district: Optional[str] = None
    state: Optional[str] = None
    pincode: Optional[str] = None
    country: Optional[str] = None

    # Contact
    email: Optional[str] = None
    phone: Optional[str] = None
    mobile: Optional[str] = None
    fax: Optional[str] = None
    website: Optional[str] = None

    # Bank Details
    bank_name: Optional[str] = None
    bank_branch: Optional[str] = None
    bank_account_number: Optional[str] = None
    bank_ifsc: Optional[str] = None
    bank_account_type: Optional[str] = None
    bank_account_name: Optional[str] = None

    # Branding
    logo_url: Optional[str] = None
    logo_small_url: Optional[str] = None
    favicon_url: Optional[str] = None
    signature_url: Optional[str] = None

    # E-Invoice Config
    einvoice_enabled: bool = False
    einvoice_username: Optional[str] = None
    einvoice_api_mode: Optional[str] = None

    # E-Way Bill Config
    ewb_enabled: bool = False
    ewb_username: Optional[str] = None
    ewb_api_mode: Optional[str] = None

    # Invoice Settings
    invoice_prefix: Optional[str] = None
    invoice_suffix: Optional[str] = None
    financial_year_start_month: int = 4
    invoice_terms: Optional[str] = None
    invoice_notes: Optional[str] = None
    invoice_footer: Optional[str] = None

    # PO Settings
    po_prefix: Optional[str] = None
    po_terms: Optional[str] = None

    # Currency
    currency_code: Optional[str] = None
    currency_symbol: Optional[str] = None

    # Tax Defaults
    default_cgst_rate: Optional[Decimal] = None
    default_sgst_rate: Optional[Decimal] = None
    default_igst_rate: Optional[Decimal] = None
    tds_deductor: bool = True
    default_tds_rate: Optional[Decimal] = None

    is_active: bool
    is_primary: bool
    created_at: datetime
    updated_at: datetime

    # Computed properties
    full_address: Optional[str] = None
    gst_state_name: Optional[str] = None


class CompanyBrief(BaseResponseSchema):
    """Brief company info for dropdowns."""
    id: UUID
    code: str
    legal_name: str
    trade_name: Optional[str] = None
    gstin: str
    state_code: str
    city: str
    is_active: bool
    is_primary: bool


class CompanyListResponse(BaseModel):
    """Response for listing companies."""
    items: List[CompanyBrief]
    total: int


# ==================== Company Branch Schemas ====================

class CompanyBranchBase(BaseModel):
    """Base schema for CompanyBranch."""
    code: str = Field(..., min_length=2, max_length=20, description="Branch code e.g., MUM-HQ")
    name: str = Field(..., min_length=2, max_length=200, description="Branch name")
    branch_type: str = Field("OFFICE", description="OFFICE, WAREHOUSE, FACTORY, SHOWROOM, SERVICE_CENTER")

    # GSTIN (for different state)
    gstin: Optional[str] = Field(None, min_length=15, max_length=15)
    state_code: str = Field(..., min_length=2, max_length=2)

    # Address
    address_line1: str = Field(..., max_length=255)
    address_line2: Optional[str] = Field(None, max_length=255)
    city: str = Field(..., max_length=100)
    state: str = Field(..., max_length=100)
    pincode: str = Field(..., max_length=10)

    # Contact
    email: Optional[EmailStr] = None
    phone: Optional[str] = Field(None, max_length=20)
    contact_person: Optional[str] = Field(None, max_length=100)

    # Linked Warehouse
    warehouse_id: Optional[UUID] = None

    is_billing_address: bool = False
    is_shipping_address: bool = False


class CompanyBranchCreate(CompanyBranchBase):
    """Schema for creating CompanyBranch."""
    # Note: company_id comes from URL path, not request body
    pass


class CompanyBranchUpdate(BaseModel):
    """Schema for updating CompanyBranch."""
    name: Optional[str] = Field(None, max_length=200)
    branch_type: Optional[str] = None
    gstin: Optional[str] = Field(None, max_length=15)

    address_line1: Optional[str] = Field(None, max_length=255)
    address_line2: Optional[str] = Field(None, max_length=255)
    city: Optional[str] = Field(None, max_length=100)
    state: Optional[str] = Field(None, max_length=100)
    pincode: Optional[str] = Field(None, max_length=10)

    email: Optional[EmailStr] = None
    phone: Optional[str] = Field(None, max_length=20)
    contact_person: Optional[str] = Field(None, max_length=100)

    warehouse_id: Optional[UUID] = None
    is_billing_address: Optional[bool] = None
    is_shipping_address: Optional[bool] = None
    is_active: Optional[bool] = None


class CompanyBranchResponse(BaseResponseSchema):
    """Response schema for CompanyBranch."""
    id: UUID
    company_id: UUID
    is_active: bool
    created_at: datetime
    updated_at: datetime


class CompanyBranchBrief(BaseResponseSchema):
    """Brief branch info for dropdowns."""
    id: UUID
    code: str
    name: str
    branch_type: str
    city: str
    state: str
    gstin: Optional[str] = None
    is_active: bool


# ==================== Company Bank Account Schemas ====================

class CompanyBankAccountBase(BaseModel):
    """Base schema for CompanyBankAccount."""
    bank_name: str = Field(..., max_length=200)
    branch_name: str = Field(..., max_length=200)
    account_number: str = Field(..., max_length=30)
    ifsc_code: str = Field(..., min_length=11, max_length=11)
    account_type: str = Field("CURRENT", description="CURRENT, SAVINGS, OD, CC")
    account_name: str = Field(..., max_length=200, description="Name as per bank")

    upi_id: Optional[str] = Field(None, max_length=100)
    swift_code: Optional[str] = Field(None, max_length=15)

    purpose: str = Field("GENERAL", description="GENERAL, COLLECTIONS, PAYMENTS, SALARY, TAX")
    is_primary: bool = False
    show_on_invoice: bool = True


class CompanyBankAccountCreate(CompanyBankAccountBase):
    """Schema for creating CompanyBankAccount."""
    # Note: company_id comes from URL path, not request body
    is_active: bool = True


class CompanyBankAccountUpdate(BaseModel):
    """Schema for updating CompanyBankAccount."""
    bank_name: Optional[str] = Field(None, max_length=200)
    branch_name: Optional[str] = Field(None, max_length=200)
    account_number: Optional[str] = Field(None, max_length=30)
    ifsc_code: Optional[str] = Field(None, max_length=11)
    account_type: Optional[str] = None
    account_name: Optional[str] = Field(None, max_length=200)

    upi_id: Optional[str] = Field(None, max_length=100)
    swift_code: Optional[str] = Field(None, max_length=15)

    purpose: Optional[str] = None
    is_primary: Optional[bool] = None
    is_active: Optional[bool] = None
    show_on_invoice: Optional[bool] = None


class CompanyBankAccountResponse(BaseResponseSchema):
    """Response schema for CompanyBankAccount."""
    id: UUID
    company_id: UUID
    is_active: bool
    created_at: datetime
    ledger_account_id: Optional[UUID] = None  # Link to Chart of Accounts for Journal Entries


class CompanyBankAccountBrief(BaseResponseSchema):
    """Brief bank account info."""
    id: UUID
    bank_name: str
    account_number: str  # Last 4 digits only in actual response
    ifsc_code: str
    account_type: str
    purpose: str
    is_primary: bool


# ==================== Company Details Response (Full) ====================

class CompanyFullResponse(CompanyResponse):
    """Full company response with branches and bank accounts."""
    branches: List[CompanyBranchBrief] = []
    bank_accounts: List[CompanyBankAccountBrief] = []


# ==================== E-Invoice/E-Way Bill Config ====================

class EInvoiceConfigUpdate(BaseModel):
    """Update E-Invoice configuration."""
    einvoice_enabled: bool
    einvoice_username: Optional[str] = None
    einvoice_password: Optional[str] = None
    einvoice_api_mode: str = Field("SANDBOX", pattern="^(SANDBOX|PRODUCTION)$")


class EWayBillConfigUpdate(BaseModel):
    """Update E-Way Bill configuration."""
    ewb_enabled: bool
    ewb_username: Optional[str] = None
    ewb_password: Optional[str] = None
    ewb_api_mode: str = Field("SANDBOX", pattern="^(SANDBOX|PRODUCTION)$")
