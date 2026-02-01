"""Pydantic schemas for Enhanced Billing module with E-Invoice support."""
from datetime import datetime, date
from typing import Optional, List
from decimal import Decimal
from uuid import UUID
from pydantic import BaseModel, Field, ConfigDict, field_validator

from app.schemas.base import BaseResponseSchema

from app.models.billing import (
    InvoiceType, InvoiceStatus, DocumentType, NoteReason,
    EWayBillStatus, PaymentMode
)


# ==================== Invoice Schemas ====================

class InvoiceItemBase(BaseModel):
    """Base schema for InvoiceItem."""
    model_config = ConfigDict(populate_by_name=True)

    product_id: Optional[UUID] = None
    variant_id: Optional[UUID] = None
    sku: str = Field(..., min_length=1, max_length=50)
    item_name: str = Field(..., min_length=1, max_length=300)
    item_description: Optional[str] = None
    hsn_code: str = Field(..., min_length=4, max_length=8)
    is_service: bool = False
    quantity: Decimal = Field(..., gt=0)
    uom: str = Field("NOS", max_length=10)
    unit_price: Decimal = Field(..., gt=0)
    mrp: Optional[Decimal] = Field(None, gt=0)
    discount_percentage: Decimal = Field(Decimal("0"), ge=0, le=100)
    gst_rate: Decimal = Field(..., ge=0, le=28, alias="tax_rate")
    cess_rate: Optional[Decimal] = Field(None, ge=0, le=100, description="GST Compensation Cess rate")
    serial_numbers: Optional[List[str]] = None
    warranty_months: Optional[int] = Field(None, ge=0)
    order_item_id: Optional[UUID] = None


class InvoiceItemCreate(InvoiceItemBase):
    """Schema for creating InvoiceItem."""
    pass


class InvoiceItemResponse(BaseResponseSchema):
    """Response schema for InvoiceItem."""
    id: UUID
    discount_amount: Decimal
    taxable_value: Decimal
    cgst_rate: Decimal
    cgst_amount: Decimal
    sgst_rate: Decimal
    sgst_amount: Decimal
    igst_rate: Decimal
    igst_amount: Decimal
    cess_rate: Decimal
    cess_amount: Decimal
    total_tax: Decimal
    line_total: Decimal
    warranty_end_date: Optional[date] = None
    created_at: datetime


class InvoiceBase(BaseModel):
    """Base schema for Invoice."""
    invoice_type: InvoiceType = InvoiceType.TAX_INVOICE
    invoice_date: date
    due_date: Optional[date] = None
    supply_date: Optional[date] = None
    order_id: Optional[UUID] = None
    warehouse_id: Optional[UUID] = None

    # Customer Details
    customer_id: Optional[UUID] = None
    customer_name: str = Field(..., min_length=1, max_length=200)
    customer_gstin: Optional[str] = Field(None, min_length=15, max_length=15)
    customer_pan: Optional[str] = Field(None, min_length=10, max_length=10)

    # Billing Address
    billing_address_line1: str = Field(..., min_length=1, max_length=255)
    billing_address_line2: Optional[str] = None
    billing_city: str = Field(..., min_length=1, max_length=100)
    billing_state: str = Field(..., min_length=1, max_length=100)
    billing_state_code: str = Field(..., min_length=2, max_length=2)
    billing_pincode: str = Field(..., min_length=6, max_length=10)
    billing_country: str = Field("India", max_length=100)

    # Shipping Address (optional)
    shipping_address_line1: Optional[str] = None
    shipping_address_line2: Optional[str] = None
    shipping_city: Optional[str] = None
    shipping_state: Optional[str] = None
    shipping_state_code: Optional[str] = None
    shipping_pincode: Optional[str] = None

    # Seller Details
    seller_gstin: str = Field(..., min_length=15, max_length=15)
    seller_name: str = Field(..., min_length=1, max_length=200)
    seller_address: str = Field(..., min_length=1, max_length=500)
    seller_state_code: str = Field(..., min_length=2, max_length=2)

    # Place of Supply
    place_of_supply: str = Field(..., max_length=100)
    place_of_supply_code: str = Field(..., min_length=2, max_length=2)
    is_reverse_charge: bool = False

    # Other Charges
    shipping_charges: Decimal = Field(Decimal("0"), ge=0)
    packaging_charges: Decimal = Field(Decimal("0"), ge=0)
    installation_charges: Decimal = Field(Decimal("0"), ge=0)
    other_charges: Decimal = Field(Decimal("0"), ge=0)

    # Payment Terms
    payment_terms: Optional[str] = None
    payment_due_days: int = Field(30, ge=0)

    # Remarks
    terms_and_conditions: Optional[str] = None
    internal_notes: Optional[str] = None
    customer_notes: Optional[str] = None

    # Channel Reference
    channel_code: Optional[str] = None
    channel_invoice_id: Optional[str] = None


class InvoiceCreate(InvoiceBase):
    """Schema for creating Invoice."""
    items: List[InvoiceItemCreate] = Field(..., min_length=1)
    generate_einvoice: bool = False


class InvoiceUpdate(BaseModel):
    """Schema for updating Invoice (only draft)."""
    due_date: Optional[date] = None
    customer_notes: Optional[str] = None
    internal_notes: Optional[str] = None
    payment_terms: Optional[str] = None


class InvoiceResponse(BaseResponseSchema):
    """Response schema for Invoice."""
    id: UUID
    invoice_number: str
    invoice_series: Optional[str] = None
    status: str
    is_interstate: bool

    # Shipment Reference (for goods issue triggered invoices)
    shipment_id: Optional[UUID] = None
    generation_trigger: Optional[str] = None  # MANUAL, GOODS_ISSUE, etc.

    # Amounts
    subtotal: Decimal
    discount_amount: Decimal
    taxable_amount: Decimal
    cgst_amount: Decimal
    sgst_amount: Decimal
    igst_amount: Decimal
    cess_amount: Decimal
    total_tax: Decimal
    grand_total: Decimal
    amount_in_words: Optional[str] = None
    currency: str
    round_off: Decimal

    # Payment Status
    amount_paid: Decimal
    amount_due: Decimal

    # E-Invoice
    irn: Optional[str] = None
    irn_generated_at: Optional[datetime] = None
    ack_number: Optional[str] = None
    ack_date: Optional[datetime] = None
    signed_qr_code: Optional[str] = None
    einvoice_status: Optional[str] = None
    einvoice_error: Optional[str] = None

    # E-Way Bill
    eway_bill_number: Optional[str] = None

    # Documents
    pdf_url: Optional[str] = None

    # Audit
    created_by: Optional[UUID] = None
    approved_by: Optional[UUID] = None
    approved_at: Optional[datetime] = None
    cancelled_by: Optional[UUID] = None
    cancelled_at: Optional[datetime] = None
    cancellation_reason: Optional[str] = None

    # Items
    items: List[InvoiceItemResponse] = []

    created_at: datetime
    updated_at: datetime

    # Computed
    is_b2b: bool = False
    is_paid: bool = False


class InvoiceListResponse(BaseModel):
    """Response for listing invoices."""
    items: List["InvoiceBrief"]
    total: int
    page: int = 1
    size: int = 50
    pages: int = 1
    total_value: Decimal = Decimal("0")


class InvoiceBrief(BaseResponseSchema):
    """Brief invoice for listing."""
    id: UUID
    invoice_number: str
    invoice_date: date
    customer_name: str
    grand_total: Decimal
    status: str
    generation_trigger: Optional[str] = None  # MANUAL, GOODS_ISSUE, etc.


class InvoiceApproveRequest(BaseModel):
    """Request to approve invoice."""
    invoice_ids: List[UUID]


class InvoiceCancelRequest(BaseModel):
    """Request to cancel invoice."""
    invoice_id: UUID
    reason: str = Field(..., min_length=10, max_length=500)


class EInvoiceGenerateRequest(BaseModel):
    """Request to generate e-invoice."""
    invoice_id: UUID


class EInvoiceResponse(BaseModel):
    """E-Invoice generation response."""
    invoice_id: UUID
    invoice_number: str
    irn: str
    ack_number: str
    ack_date: datetime
    signed_qr_code: str
    status: str


# ==================== Credit/Debit Note Schemas ====================

class CreditDebitNoteItemBase(BaseModel):
    """Base schema for CreditDebitNoteItem."""
    product_id: Optional[UUID] = None
    sku: str = Field(..., max_length=50)
    item_name: str = Field(..., max_length=300)
    hsn_code: str = Field(..., min_length=4, max_length=8)
    quantity: Decimal = Field(..., gt=0)
    uom: str = Field("NOS", max_length=10)
    unit_price: Decimal = Field(..., gt=0)
    gst_rate: Decimal = Field(..., ge=0, le=28)
    original_invoice_item_id: Optional[UUID] = None


class CreditDebitNoteItemCreate(CreditDebitNoteItemBase):
    """Schema for creating note item."""
    pass


class CreditDebitNoteItemResponse(BaseResponseSchema):
    """Response schema for note item."""
    id: UUID
    taxable_value: Decimal
    cgst_amount: Decimal
    sgst_amount: Decimal
    igst_amount: Decimal
    total_tax: Decimal
    line_total: Decimal
    created_at: datetime


class CreditDebitNoteBase(BaseModel):
    """Base schema for CreditDebitNote."""
    document_type: DocumentType
    invoice_id: UUID
    original_invoice_number: str
    original_invoice_date: date
    note_date: date
    reason: NoteReason
    reason_description: Optional[str] = None
    customer_id: Optional[UUID] = None
    customer_name: str = Field(..., max_length=200)
    customer_gstin: Optional[str] = None
    place_of_supply: str
    place_of_supply_code: str = Field(..., min_length=2, max_length=2)
    pre_gst: bool = False


class CreditDebitNoteCreate(CreditDebitNoteBase):
    """Schema for creating CreditDebitNote."""
    items: List[CreditDebitNoteItemCreate] = Field(..., min_length=1)


class CreditDebitNoteResponse(BaseResponseSchema):
    """Response schema for CreditDebitNote."""
    id: UUID
    note_number: str
    status: str
    is_interstate: bool
    taxable_amount: Decimal
    cgst_amount: Decimal
    sgst_amount: Decimal
    igst_amount: Decimal
    cess_amount: Decimal
    total_tax: Decimal
    grand_total: Decimal
    irn: Optional[str] = None
    ack_number: Optional[str] = None
    ack_date: Optional[datetime] = None
    pdf_url: Optional[str] = None
    items: List[CreditDebitNoteItemResponse] = []
    created_by: Optional[UUID] = None
    approved_by: Optional[UUID] = None
    approved_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime


class CreditDebitNoteListResponse(BaseModel):
    """Response for listing credit/debit notes."""
    items: List[CreditDebitNoteResponse]
    total: int
    page: int = 1
    size: int = 50
    pages: int = 1


# ==================== E-Way Bill Schemas ====================

class EWayBillItemBase(BaseModel):
    """Base schema for EWayBillItem."""
    product_name: str = Field(..., max_length=300)
    hsn_code: str = Field(..., min_length=4, max_length=8)
    quantity: Decimal = Field(..., gt=0)
    uom: str = Field("NOS", max_length=10)
    taxable_value: Decimal = Field(..., gt=0)
    gst_rate: Decimal = Field(..., ge=0, le=28)


class EWayBillItemCreate(EWayBillItemBase):
    """Schema for creating EWayBillItem."""
    pass


class EWayBillItemResponse(BaseResponseSchema):
    """Response schema for EWayBillItem."""
    id: UUID
    cgst_amount: Decimal
    sgst_amount: Decimal
    igst_amount: Decimal


class EWayBillBase(BaseModel):
    """Base schema for EWayBill."""
    invoice_id: UUID
    document_type: str = Field("INV", max_length=20)
    document_number: str = Field(..., max_length=50)
    document_date: date
    supply_type: str = Field("O", max_length=10)
    sub_supply_type: str = Field("1", max_length=10)
    transaction_type: str = Field("1", max_length=10)

    # From Address
    from_gstin: str = Field(..., min_length=15, max_length=15)
    from_name: str = Field(..., max_length=200)
    from_address1: str = Field(..., max_length=255)
    from_address2: Optional[str] = None
    from_place: str = Field(..., max_length=100)
    from_pincode: str = Field(..., min_length=6, max_length=10)
    from_state_code: str = Field(..., min_length=2, max_length=2)

    # To Address
    to_gstin: Optional[str] = None
    to_name: str = Field(..., max_length=200)
    to_address1: str = Field(..., max_length=255)
    to_address2: Optional[str] = None
    to_place: str = Field(..., max_length=100)
    to_pincode: str = Field(..., min_length=6, max_length=10)
    to_state_code: str = Field(..., min_length=2, max_length=2)

    # Transport Details
    transporter_id: Optional[UUID] = None
    transporter_name: Optional[str] = None
    transporter_gstin: Optional[str] = None
    transport_mode: str = Field("1", max_length=10)
    vehicle_number: Optional[str] = None
    vehicle_type: Optional[str] = None
    transport_doc_number: Optional[str] = None
    transport_doc_date: Optional[date] = None
    distance_km: int = Field(..., ge=1)


class EWayBillCreate(EWayBillBase):
    """Schema for creating EWayBill."""
    items: List[EWayBillItemCreate] = Field(..., min_length=1)


class EWayBillResponse(BaseResponseSchema):
    """Response schema for EWayBill."""
    id: UUID
    eway_bill_number: Optional[str] = None
    status: str
    total_value: Decimal
    cgst_amount: Decimal
    sgst_amount: Decimal
    igst_amount: Decimal
    cess_amount: Decimal
    valid_from: Optional[datetime] = None
    valid_until: Optional[datetime] = None
    extension_count: int
    extended_until: Optional[datetime] = None
    cancelled_at: Optional[datetime] = None
    cancellation_reason: Optional[str] = None
    generated_at: Optional[datetime] = None
    items: List[EWayBillItemResponse] = []
    is_valid: bool
    created_at: datetime
    updated_at: datetime


class EWayBillListResponse(BaseModel):
    """Response for listing E-Way Bills."""
    items: List[EWayBillResponse]
    total: int
    page: int = 1
    size: int = 50
    pages: int = 1


class EWayBillUpdate(BaseModel):
    """Update schema for E-Way Bill."""
    vehicle_number: Optional[str] = None
    vehicle_type: Optional[str] = None
    transporter_name: Optional[str] = None
    transporter_id: Optional[str] = None


class EWayBillGenerateRequest(BaseModel):
    """Request to generate E-Way Bill."""
    eway_bill_id: UUID


class EWayBillExtendRequest(BaseModel):
    """Request to extend E-Way Bill validity."""
    eway_bill_id: UUID
    from_place: str
    from_state_code: str
    remaining_distance: int
    reason: str = Field(..., min_length=10)
    vehicle_number: Optional[str] = None


class EWayBillCancelRequest(BaseModel):
    """Request to cancel E-Way Bill."""
    eway_bill_id: UUID
    reason: str = Field(..., min_length=10)


# ==================== Payment Receipt Schemas ====================

class PaymentReceiptBase(BaseModel):
    """Base schema for PaymentReceipt."""
    invoice_id: UUID
    customer_id: Optional[UUID] = None
    payment_date: date
    payment_mode: PaymentMode
    amount: Decimal = Field(..., gt=0)
    currency: str = Field("INR", max_length=3)
    bank_name: Optional[str] = None
    bank_branch: Optional[str] = None
    cheque_number: Optional[str] = None
    cheque_date: Optional[date] = None
    transaction_reference: Optional[str] = None
    tds_applicable: bool = False
    tds_rate: Optional[Decimal] = Field(None, ge=0, le=100)
    tds_section: Optional[str] = None
    remarks: Optional[str] = None


class PaymentReceiptCreate(PaymentReceiptBase):
    """Schema for creating PaymentReceipt."""
    pass


class PaymentReceiptResponse(BaseResponseSchema):
    """Response schema for PaymentReceipt."""
    id: UUID
    receipt_number: str
    invoice_id: Optional[UUID] = None
    customer_id: Optional[UUID] = None

    # Payment details
    payment_date: Optional[date] = None
    payment_mode: Optional[str] = None
    amount: Optional[Decimal] = None
    currency: str = "INR"

    # Bank details
    bank_name: Optional[str] = None
    bank_branch: Optional[str] = None
    cheque_number: Optional[str] = None
    cheque_date: Optional[date] = None
    transaction_reference: Optional[str] = None

    # TDS
    tds_applicable: bool = False
    tds_rate: Optional[Decimal] = None
    tds_amount: Optional[Decimal] = None
    tds_section: Optional[str] = None
    net_amount: Decimal

    # Status
    is_confirmed: bool
    confirmed_at: Optional[datetime] = None
    is_bounced: bool
    bounced_at: Optional[datetime] = None
    bounce_reason: Optional[str] = None

    remarks: Optional[str] = None
    created_by: Optional[UUID] = None
    created_at: datetime
    updated_at: datetime


class PaymentReceiptListResponse(BaseModel):
    """Response for listing payment receipts."""
    items: List[PaymentReceiptResponse]
    total: int
    page: int = 1
    size: int = 50
    pages: int = 1


# ==================== Invoice Number Sequence Schemas ====================

class InvoiceNumberSequenceBase(BaseModel):
    """Base schema for InvoiceNumberSequence."""
    series_code: str = Field(..., max_length=20)
    series_name: str = Field(..., max_length=100)
    financial_year: str = Field(..., max_length=10)
    prefix: str = Field(..., max_length=20)
    suffix: Optional[str] = None
    padding_length: int = Field(5, ge=1, le=10)
    warehouse_id: Optional[UUID] = None
    is_active: bool = True


class InvoiceNumberSequenceCreate(InvoiceNumberSequenceBase):
    """Schema for creating InvoiceNumberSequence."""
    pass


class InvoiceNumberSequenceResponse(BaseResponseSchema):
    """Response schema for InvoiceNumberSequence."""
    id: UUID
    current_number: int
    created_at: datetime
    updated_at: datetime


# ==================== GST Report Schemas ====================

class GSTReportRequest(BaseModel):
    """Request for GST report."""
    month: int = Field(..., ge=1, le=12)
    year: int = Field(..., ge=2017)


class GSTR1Response(BaseModel):
    """GSTR-1 (Outward Supplies) report response."""
    period: str
    b2b_invoices: List[dict] = []
    b2c_invoices: List[dict] = []
    credit_notes: List[dict] = []
    debit_notes: List[dict] = []
    nil_rated: List[dict] = []
    hsn_summary: List[dict] = []


class GSTR3BResponse(BaseModel):
    """GSTR-3B (Monthly Summary) report response."""
    period: str
    outward_supplies: dict = {}
    inward_supplies: dict = {}
    eligible_itc: dict = {}
    ineligible_itc: dict = {}
    tax_payable: dict = {}
    paid_details: dict = {}


# ==================== E-Invoice/E-Way Bill Operation Schemas ====================

class IRNCancelRequest(BaseModel):
    """Request body for IRN cancellation."""
    reason: str = Field(
        ...,
        description="Reason code: 1=Duplicate, 2=Data Entry Mistake, 3=Order Cancelled, 4=Others"
    )
    remarks: str = Field("", description="Additional remarks")


class PartBUpdateRequest(BaseModel):
    """Request body for Part-B (vehicle) update on E-Way Bill."""
    vehicle_number: str = Field(..., description="Vehicle registration number")
    transport_mode: str = Field("1", description="1=Road, 2=Rail, 3=Air, 4=Ship")
    reason_code: str = Field("4", description="1=Breakdown, 2=Transshipment, 3=Others, 4=First time")
    reason_remarks: str = Field("", description="Reason remarks")
    from_place: str = Field("", description="From place")
    from_state: str = Field("", description="From state")


class EWBCancelRequest(BaseModel):
    """Request body for E-Way Bill cancellation."""
    reason_code: str = Field(
        ...,
        description="Cancel reason: 1=Duplicate, 2=Order Cancelled, 3=Data Entry Mistake, 4=Others"
    )
    remarks: str = Field("", description="Cancellation remarks")


class EWBExtendRequest(BaseModel):
    """Request body for E-Way Bill validity extension."""
    from_place: str = Field(..., description="Current location")
    from_state: int = Field(..., description="State code")
    remaining_distance: int = Field(..., description="Remaining distance in km")
    reason_code: str = Field(
        "99",
        description="1=Natural calamity, 2=Law and order, 3=Transshipment, 4=Accident, 99=Others"
    )
    reason_remarks: str = Field("", description="Extension reason remarks")
    transit_type: str = Field("C", description="C=In-transit, R=Reached destination")
    vehicle_number: str = Field("", description="Current vehicle number")
