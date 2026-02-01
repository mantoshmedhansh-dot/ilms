"""Pydantic schemas for Vendor/Supplier module."""
from datetime import datetime, date
from typing import Optional, List
from decimal import Decimal
from uuid import UUID
from pydantic import BaseModel, Field, ConfigDict, EmailStr

from app.schemas.base import BaseResponseSchema

from app.models.vendor import (
    VendorType, VendorStatus, VendorGrade, PaymentTerms, VendorTransactionType
)


# ==================== Vendor Schemas ====================

class VendorBase(BaseModel):
    """Base schema for Vendor."""
    name: str = Field(..., min_length=2, max_length=200)
    legal_name: str = Field(..., min_length=2, max_length=200)
    trade_name: Optional[str] = None
    vendor_type: VendorType

    # GST Compliance
    gstin: Optional[str] = Field(None, min_length=15, max_length=15)
    gst_registered: bool = True
    pan: Optional[str] = Field(None, min_length=10, max_length=10)
    tan: Optional[str] = Field(None, min_length=10, max_length=10)

    # MSME
    msme_registered: bool = False
    msme_number: Optional[str] = None
    msme_category: Optional[str] = None

    # Contact
    contact_person: Optional[str] = None
    designation: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    mobile: Optional[str] = None
    website: Optional[str] = None

    # Address
    address_line1: str = Field(..., max_length=255)
    address_line2: Optional[str] = None
    city: str = Field(..., max_length=100)
    state: str = Field(..., max_length=100)
    state_code: Optional[str] = Field(None, max_length=2)
    pincode: str = Field(..., max_length=10)
    country: str = "India"

    # Warehouse Address
    warehouse_address: Optional[dict] = None

    # Bank Details
    bank_name: Optional[str] = None
    bank_branch: Optional[str] = None
    bank_account_number: Optional[str] = None
    bank_ifsc: Optional[str] = Field(None, max_length=11)
    bank_account_type: Optional[str] = None
    beneficiary_name: Optional[str] = None

    # Payment Terms
    payment_terms: PaymentTerms = PaymentTerms.NET_30
    credit_days: int = Field(30, ge=0)
    credit_limit: Decimal = Field(Decimal("0"), ge=0)
    advance_percentage: Decimal = Field(Decimal("0"), ge=0, le=100)

    # TDS
    tds_applicable: bool = True
    tds_section: Optional[str] = None
    tds_rate: Decimal = Field(Decimal("2"), ge=0, le=100)
    lower_tds_certificate: bool = False
    lower_tds_rate: Optional[Decimal] = None
    lower_tds_valid_till: Optional[date] = None

    # Products
    product_categories: Optional[List[UUID]] = None
    primary_products: Optional[str] = None

    # Lead Time
    default_lead_days: int = Field(7, ge=0)
    min_order_value: Optional[Decimal] = Field(None, ge=0)
    min_order_quantity: Optional[int] = Field(None, ge=0)

    # Warehouse
    default_warehouse_id: Optional[UUID] = None

    # GL Account Link (for Finance Integration)
    gl_account_id: Optional[UUID] = None

    # Notes
    internal_notes: Optional[str] = None


class VendorCreate(VendorBase):
    """Schema for creating Vendor."""
    opening_balance: Decimal = Field(Decimal("0"), ge=0)


class VendorUpdate(BaseModel):
    """Schema for updating Vendor."""
    name: Optional[str] = None
    legal_name: Optional[str] = None
    trade_name: Optional[str] = None
    vendor_type: Optional[VendorType] = None
    status: Optional[VendorStatus] = None
    grade: Optional[VendorGrade] = None

    # GST
    gstin: Optional[str] = None
    pan: Optional[str] = None

    # Contact
    contact_person: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    mobile: Optional[str] = None

    # Address
    address_line1: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    pincode: Optional[str] = None

    # Bank Details
    bank_name: Optional[str] = None
    bank_branch: Optional[str] = None
    bank_account_number: Optional[str] = None
    bank_ifsc: Optional[str] = None
    bank_account_type: Optional[str] = None
    beneficiary_name: Optional[str] = None

    # Payment
    payment_terms: Optional[PaymentTerms] = None
    credit_days: Optional[int] = None
    credit_limit: Optional[Decimal] = None

    # TDS
    tds_applicable: Optional[bool] = None
    tds_section: Optional[str] = None
    tds_rate: Optional[Decimal] = None

    # Lead Time
    default_lead_days: Optional[int] = None
    min_order_value: Optional[Decimal] = None

    # GL Account Link
    gl_account_id: Optional[UUID] = None

    internal_notes: Optional[str] = None


class VendorResponse(BaseResponseSchema):
    """Response schema for Vendor."""
    id: UUID
    vendor_code: str
    status: str
    grade: str  # VARCHAR in DB
    gst_state_code: Optional[str] = None
    opening_balance: Decimal
    current_balance: Decimal
    advance_balance: Decimal
    is_verified: bool
    verified_at: Optional[datetime] = None
    total_po_count: int
    total_po_value: Decimal
    on_time_delivery_rate: Optional[Decimal] = None
    quality_rejection_rate: Optional[Decimal] = None
    last_po_date: Optional[datetime] = None
    last_payment_date: Optional[datetime] = None
    gl_account_id: Optional[UUID] = None  # Linked GL account
    supplier_code: Optional[str] = None  # Auto-generated 2-char code for barcode (SPARE_PARTS vendors)
    # Bank Details
    bank_name: Optional[str] = None
    bank_branch: Optional[str] = None
    bank_account_number: Optional[str] = None
    bank_ifsc: Optional[str] = None
    bank_account_type: Optional[str] = None
    beneficiary_name: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class VendorBrief(BaseResponseSchema):
    """Brief vendor info for list and dropdowns."""
    id: UUID
    vendor_code: str
    name: str
    vendor_type: str  # VARCHAR in DB
    status: str
    grade: str = "B"  # VARCHAR in DB
    gstin: Optional[str] = None
    pan: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    contact_person: Optional[str] = None
    city: str
    state: str
    current_balance: Decimal
    credit_limit: Decimal
    supplier_code: Optional[str] = None  # 2-char code for barcode (SPARE_PARTS vendors)
    # Bank Details (for edit)
    bank_name: Optional[str] = None
    bank_branch: Optional[str] = None
    bank_account_number: Optional[str] = None
    bank_ifsc: Optional[str] = None
    bank_account_type: Optional[str] = None
    beneficiary_name: Optional[str] = None


class VendorListResponse(BaseModel):
    """Response for listing vendors."""
    items: List[VendorBrief]
    total: int
    page: int = 1
    size: int = 50
    pages: int = 1


# ==================== Vendor Ledger Schemas ====================

class VendorLedgerBase(BaseModel):
    """Base schema for VendorLedger."""
    vendor_id: UUID
    transaction_type: VendorTransactionType
    transaction_date: date
    due_date: Optional[date] = None
    reference_type: str = Field(..., max_length=50)
    reference_number: str = Field(..., max_length=50)
    reference_id: Optional[UUID] = None
    vendor_invoice_number: Optional[str] = None
    vendor_invoice_date: Optional[date] = None
    debit_amount: Decimal = Field(Decimal("0"), ge=0)
    credit_amount: Decimal = Field(Decimal("0"), ge=0)
    tds_amount: Decimal = Field(Decimal("0"), ge=0)
    tds_section: Optional[str] = None
    payment_mode: Optional[str] = None
    payment_reference: Optional[str] = None
    bank_name: Optional[str] = None
    cheque_number: Optional[str] = None
    cheque_date: Optional[date] = None
    narration: Optional[str] = None


class VendorLedgerCreate(VendorLedgerBase):
    """Schema for creating ledger entry."""
    pass


class VendorLedgerResponse(BaseResponseSchema):
    """Response schema for VendorLedger."""
    id: UUID
    running_balance: Decimal
    is_settled: bool
    settled_date: Optional[date] = None
    days_overdue: int
    created_at: datetime


class VendorLedgerListResponse(BaseModel):
    """Response for listing ledger entries."""
    items: List[VendorLedgerResponse]
    total: int
    total_debit: Decimal
    total_credit: Decimal
    closing_balance: Decimal
    page: int = 1
    size: int = 50
    pages: int = 1


# ==================== Vendor Contact Schemas ====================

class VendorContactBase(BaseModel):
    """Base schema for VendorContact."""
    name: str = Field(..., min_length=2, max_length=100)
    designation: Optional[str] = None
    department: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    mobile: Optional[str] = None
    is_primary: bool = False


class VendorContactCreate(VendorContactBase):
    """Schema for creating contact."""
    # Note: vendor_id comes from URL path, not request body
    pass


class VendorContactResponse(BaseResponseSchema):
    """Response schema for VendorContact."""
    id: UUID
    vendor_id: UUID  # Included in response from database
    is_active: bool
    created_at: datetime


# ==================== Vendor Payment Schemas ====================

class VendorPaymentCreate(BaseModel):
    """Schema for recording vendor payment."""
    # Note: vendor_id comes from URL path, not request body
    amount: Decimal = Field(..., gt=0)
    payment_date: date
    payment_mode: str = Field(..., pattern="^(NEFT|RTGS|CHEQUE|UPI|CASH)$")
    payment_reference: Optional[str] = None
    bank_name: Optional[str] = None
    cheque_number: Optional[str] = None
    cheque_date: Optional[date] = None

    # Against invoices
    invoice_ids: Optional[List[UUID]] = None

    # TDS
    tds_amount: Decimal = Field(Decimal("0"), ge=0)
    tds_section: Optional[str] = None

    narration: Optional[str] = None


class VendorPaymentResponse(BaseModel):
    """Response for vendor payment."""
    id: UUID
    vendor_id: UUID
    vendor_name: str
    amount: Decimal
    tds_amount: Decimal
    net_amount: Decimal
    payment_date: date
    payment_mode: str
    payment_reference: Optional[str] = None
    ledger_entry_id: UUID
    created_at: datetime


# ==================== Vendor Aging Report ====================

class VendorAgingBucket(BaseModel):
    """Single aging bucket."""
    bucket: str  # "0-30", "31-60", "61-90", "90+"
    amount: Decimal
    count: int


class VendorAgingResponse(BaseModel):
    """Vendor aging response."""
    vendor_id: UUID
    vendor_code: str
    vendor_name: str
    total_outstanding: Decimal
    buckets: List[VendorAgingBucket]


class VendorAgingReport(BaseModel):
    """Full aging report."""
    as_of_date: date
    vendors: List[VendorAgingResponse]
    summary: List[VendorAgingBucket]
    total_outstanding: Decimal
