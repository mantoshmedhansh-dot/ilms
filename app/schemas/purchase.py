"""Pydantic schemas for Purchase/Procurement module."""
from datetime import datetime, date
from typing import Optional, List
from decimal import Decimal
from uuid import UUID
from pydantic import BaseModel, Field, ConfigDict

from app.schemas.base import BaseResponseSchema

from app.models.purchase import (
    RequisitionStatus, POStatus, GRNStatus, VendorInvoiceStatus, QualityCheckResult, ProformaStatus,
    DeliveryLotStatus, SRNStatus, ReturnReason, ItemCondition, RestockDecision, PickupStatus, ResolutionType
)


# ==================== Purchase Requisition Schemas ====================

class PRItemBase(BaseModel):
    """Base schema for PR item."""
    product_id: UUID
    variant_id: Optional[UUID] = None
    product_name: str
    sku: str
    quantity_requested: int = Field(..., gt=0)
    uom: str = "PCS"
    estimated_unit_price: Decimal = Field(Decimal("0"), ge=0)
    preferred_vendor_id: Optional[UUID] = None
    notes: Optional[str] = None
    # Month-wise quantity breakdown for multi-delivery PRs
    # Format: {"2026-01": 1500, "2026-02": 1500, "2026-03": 1000}
    monthly_quantities: Optional[dict] = Field(
        None,
        description="Month-wise quantity breakdown (YYYY-MM: quantity)"
    )


class PRItemCreate(PRItemBase):
    """Schema for creating PR item."""
    pass


class PRItemUpdate(BaseModel):
    """Schema for updating PR item. All fields optional."""
    id: Optional[UUID] = None  # If provided, update existing; if None, create new
    product_id: Optional[UUID] = None
    variant_id: Optional[UUID] = None
    product_name: Optional[str] = None
    sku: Optional[str] = None
    quantity_requested: Optional[int] = Field(None, gt=0)
    uom: Optional[str] = None
    estimated_unit_price: Optional[Decimal] = Field(None, ge=0)
    preferred_vendor_id: Optional[UUID] = None
    notes: Optional[str] = None
    monthly_quantities: Optional[dict] = None


class PRItemResponse(BaseResponseSchema):
    """Response schema for PR item."""
    id: UUID
    product_id: UUID
    variant_id: Optional[UUID] = None
    product_name: str
    sku: str
    quantity_requested: int
    uom: str = "PCS"
    estimated_unit_price: Decimal
    estimated_total: Decimal
    preferred_vendor_id: Optional[UUID] = None
    notes: Optional[str] = None
    monthly_quantities: Optional[dict] = None


class PurchaseRequisitionBase(BaseModel):
    """Base schema for Purchase Requisition."""
    requesting_department: Optional[str] = None
    required_by_date: Optional[date] = None
    delivery_warehouse_id: UUID
    priority: int = Field(5, ge=1, le=10)
    reason: Optional[str] = None
    notes: Optional[str] = None


class PurchaseRequisitionCreate(PurchaseRequisitionBase):
    """Schema for creating PR."""
    items: List[PRItemCreate]


class PurchaseRequisitionUpdate(BaseModel):
    """Schema for updating PR. Supports full editing including items."""
    requesting_department: Optional[str] = None
    required_by_date: Optional[date] = None
    delivery_warehouse_id: Optional[UUID] = None
    priority: Optional[int] = Field(None, ge=1, le=10)
    reason: Optional[str] = None
    notes: Optional[str] = None
    # Items - if provided, replaces all existing items
    items: Optional[List[PRItemCreate]] = None


class PurchaseRequisitionResponse(BaseResponseSchema):
    """Response schema for PR."""
    id: UUID
    requisition_number: str
    status: str
    request_date: date
    requested_by: UUID
    requested_by_name: Optional[str] = None  # Computed from relationship
    requesting_department: Optional[str] = None
    required_by_date: Optional[date] = None
    delivery_warehouse_id: Optional[UUID] = None
    delivery_warehouse_name: Optional[str] = None  # Computed from relationship
    priority: int = 5
    reason: Optional[str] = None
    notes: Optional[str] = None
    estimated_total: Decimal
    approved_by: Optional[UUID] = None
    approved_at: Optional[datetime] = None
    rejection_reason: Optional[str] = None
    converted_to_po_id: Optional[UUID] = None
    items: List[PRItemResponse] = []
    created_at: datetime
    updated_at: datetime


class PRListResponse(BaseModel):
    """Response for listing PRs."""
    items: List[PurchaseRequisitionResponse]
    total: int
    page: int = 1
    size: int = 50
    pages: int = 1


class PRApproveRequest(BaseModel):
    """Request to approve/reject PR."""
    action: str = Field(..., pattern="^(APPROVE|REJECT)$")
    rejection_reason: Optional[str] = None


# ==================== Purchase Order Schemas ====================

class POItemBase(BaseModel):
    """Base schema for PO item."""
    product_id: Optional[UUID] = None  # Nullable - vendor items may not be in our catalog
    variant_id: Optional[UUID] = None
    product_name: str
    sku: str
    hsn_code: Optional[str] = None
    quantity_ordered: int = Field(..., gt=0)
    uom: str = "PCS"
    unit_price: Decimal = Field(..., ge=0)
    discount_percentage: Decimal = Field(Decimal("0"), ge=0, le=100)
    gst_rate: Decimal = Field(Decimal("18"), ge=0, le=28)
    expected_date: Optional[date] = None
    notes: Optional[str] = None
    # Month-wise quantity breakdown for multi-delivery POs
    # Format: {"2026-01": 1500, "2026-02": 1500, "2026-03": 1000}
    monthly_quantities: Optional[dict] = Field(
        None,
        description="Month-wise quantity breakdown (YYYY-MM: quantity)"
    )


class POItemCreate(POItemBase):
    """Schema for creating PO item."""
    pass


class POItemResponse(BaseResponseSchema):
    """Response schema for PO item."""
    id: UUID
    # Product info
    product_id: Optional[UUID] = None
    variant_id: Optional[UUID] = None
    product_name: str
    sku: str
    hsn_code: Optional[str] = None
    # Quantity
    line_number: int
    quantity_ordered: int
    quantity_received: int
    quantity_accepted: int
    quantity_rejected: int
    quantity_pending: int
    uom: str = "PCS"
    # Pricing
    unit_price: Decimal
    discount_percentage: Decimal = Decimal("0")
    discount_amount: Decimal
    gst_rate: Decimal = Decimal("18")
    taxable_amount: Decimal
    cgst_rate: Decimal
    sgst_rate: Decimal
    igst_rate: Decimal
    cgst_amount: Decimal
    sgst_amount: Decimal
    igst_amount: Decimal
    cess_amount: Decimal
    total_amount: Decimal
    # Status
    is_closed: bool
    expected_date: Optional[date] = None
    notes: Optional[str] = None
    monthly_quantities: Optional[dict] = None


# ==================== PO Delivery Schedule (Lot-wise) Schemas ====================

class PODeliveryScheduleBase(BaseModel):
    """Base schema for PO Delivery Schedule."""
    lot_name: str = Field(..., description="e.g., 'JAN 2026', 'Batch 1'")
    month_code: Optional[str] = Field(None, description="YYYY-MM format")
    expected_delivery_date: date
    delivery_window_start: Optional[date] = None
    delivery_window_end: Optional[date] = None
    total_quantity: int = Field(..., gt=0)
    advance_percentage: Decimal = Field(Decimal("25"), ge=0, le=100)
    balance_due_days: int = Field(45, ge=0)
    notes: Optional[str] = None


class PODeliveryScheduleCreate(PODeliveryScheduleBase):
    """Schema for creating delivery schedule."""
    pass


class PODeliveryScheduleResponse(BaseResponseSchema):
    """Response schema for delivery schedule."""
    id: UUID
    lot_number: int
    lot_value: Decimal
    lot_tax: Decimal
    lot_total: Decimal
    advance_amount: Decimal
    balance_amount: Decimal
    advance_paid: Decimal
    advance_paid_date: Optional[date] = None
    advance_payment_ref: Optional[str] = None
    balance_paid: Decimal
    balance_paid_date: Optional[date] = None
    balance_payment_ref: Optional[str] = None
    balance_due_date: Optional[date] = None
    status: str
    actual_delivery_date: Optional[date] = None
    quantity_received: int
    grn_id: Optional[UUID] = None
    # Serial number range for this lot
    serial_number_start: Optional[int] = None
    serial_number_end: Optional[int] = None
    serial_number_range: Optional[str] = None  # Computed property
    created_at: datetime
    updated_at: datetime

    # Computed properties
    pending_advance: Optional[Decimal] = None
    pending_balance: Optional[Decimal] = None
    is_advance_paid: Optional[bool] = None
    is_fully_paid: Optional[bool] = None


class PODeliveryScheduleBrief(BaseResponseSchema):
    """Brief schema for delivery schedule list."""
    id: UUID
    lot_number: int
    lot_name: str
    expected_delivery_date: date
    total_quantity: int
    lot_total: Decimal
    advance_amount: Decimal
    balance_amount: Decimal
    status: str
    # Serial number range
    serial_number_start: Optional[int] = None
    serial_number_end: Optional[int] = None
    serial_number_range: Optional[str] = None


class PODeliveryPaymentRequest(BaseModel):
    """Request to record payment for a delivery lot."""
    payment_type: str = Field(..., pattern="^(ADVANCE|BALANCE)$")
    amount: Decimal = Field(..., gt=0)
    payment_date: date
    payment_reference: str = Field(..., max_length=100)
    notes: Optional[str] = None


# ==================== Purchase Order Schemas ====================

class PurchaseOrderBase(BaseModel):
    """Base schema for Purchase Order."""
    vendor_id: UUID
    delivery_warehouse_id: UUID
    expected_delivery_date: Optional[date] = None
    delivery_address: Optional[dict] = None
    # Bill To & Ship To addresses
    # Format: {"name": "", "address_line1": "", "address_line2": "", "city": "", "state": "", "pincode": "", "gstin": "", "state_code": ""}
    bill_to: Optional[dict] = Field(
        None,
        description="Bill To address (buyer's registered office for invoicing)"
    )
    ship_to: Optional[dict] = Field(
        None,
        description="Ship To address (delivery location, defaults to warehouse if not provided)"
    )
    payment_terms: Optional[str] = None
    credit_days: int = 30
    advance_required: Decimal = Field(Decimal("0"), ge=0)
    advance_paid: Decimal = Field(Decimal("0"), ge=0, description="Advance amount already paid")
    quotation_reference: Optional[str] = None
    quotation_date: Optional[date] = None
    freight_charges: Decimal = Field(Decimal("0"), ge=0)
    packing_charges: Decimal = Field(Decimal("0"), ge=0)
    other_charges: Decimal = Field(Decimal("0"), ge=0)
    terms_and_conditions: Optional[str] = None
    special_instructions: Optional[str] = None
    internal_notes: Optional[str] = None


class PurchaseOrderCreate(PurchaseOrderBase):
    """Schema for creating PO."""
    requisition_id: Optional[UUID] = None
    items: List[POItemCreate]
    # Delivery schedules for lot-wise tracking (auto-generated from monthly_quantities if not provided)
    delivery_schedules: Optional[List[PODeliveryScheduleCreate]] = None


class PurchaseOrderUpdate(BaseModel):
    """Schema for updating PO - supports full editing including vendor and items."""
    vendor_id: Optional[UUID] = None
    expected_delivery_date: Optional[date] = None
    credit_days: Optional[int] = None
    payment_terms: Optional[str] = None
    advance_required: Optional[Decimal] = None
    advance_paid: Optional[Decimal] = None
    freight_charges: Optional[Decimal] = None
    packing_charges: Optional[Decimal] = None
    other_charges: Optional[Decimal] = None
    terms_and_conditions: Optional[str] = None
    special_instructions: Optional[str] = None
    internal_notes: Optional[str] = None
    # Items - if provided, replaces all existing items
    items: Optional[List[POItemCreate]] = None


class PurchaseOrderResponse(BaseResponseSchema):
    """Response schema for PO.

    IMPORTANT: This schema must ONLY include fields that exist as columns
    or properties in the PurchaseOrder model. Do NOT add fields that would
    need to come from relationships - those must be loaded separately.
    """
    # Core identifiers
    id: UUID
    po_number: str
    po_date: date
    status: str
    requisition_id: Optional[UUID] = None

    # Vendor info (snapshot stored on PO)
    vendor_id: UUID
    vendor_name: str
    vendor_gstin: Optional[str] = None
    vendor_address: Optional[dict] = None  # JSON field in model

    # Warehouse/Delivery info
    delivery_warehouse_id: UUID
    expected_delivery_date: Optional[date] = None
    delivery_address: Optional[dict] = None
    bill_to: Optional[dict] = None
    ship_to: Optional[dict] = None

    # Financial terms
    payment_terms: Optional[str] = None
    credit_days: int = 30
    advance_required: Decimal = Decimal("0")
    advance_paid: Decimal = Decimal("0")
    quotation_reference: Optional[str] = None
    quotation_date: Optional[date] = None
    freight_charges: Decimal = Decimal("0")
    packing_charges: Decimal = Decimal("0")
    other_charges: Decimal = Decimal("0")

    # Calculated amounts (all exist in model)
    subtotal: Decimal
    discount_amount: Decimal
    taxable_amount: Decimal
    cgst_amount: Decimal
    sgst_amount: Decimal
    igst_amount: Decimal
    cess_amount: Decimal
    total_tax: Decimal
    grand_total: Decimal
    total_received_value: Decimal = Decimal("0")

    # Documents & Status
    po_pdf_url: Optional[str] = None
    sent_to_vendor_at: Optional[datetime] = None
    vendor_acknowledged_at: Optional[datetime] = None

    # Notes
    terms_and_conditions: Optional[str] = None
    special_instructions: Optional[str] = None
    internal_notes: Optional[str] = None

    # Nested items and schedules
    items: List[POItemResponse] = []
    delivery_schedules: List[PODeliveryScheduleResponse] = []

    # Approval workflow
    approval_request_id: Optional[UUID] = None
    approval_level: Optional[str] = None
    submitted_for_approval_at: Optional[datetime] = None
    rejection_reason: Optional[str] = None

    # Audit fields
    created_by: UUID
    approved_by: Optional[UUID] = None
    approved_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    closed_at: Optional[datetime] = None

    # Nested objects for frontend compatibility
    vendor: Optional["POVendorBrief"] = None
    warehouse: Optional["POWarehouseBrief"] = None


class POVendorBrief(BaseModel):
    """Brief vendor info for PO list."""
    id: Optional[UUID] = None
    name: Optional[str] = None
    code: Optional[str] = None


class POWarehouseBrief(BaseModel):
    """Brief warehouse info for PO list."""
    id: Optional[UUID] = None
    name: Optional[str] = None


class POBrief(BaseResponseSchema):
    """Brief PO for list display."""
    id: UUID
    po_number: str
    po_date: date
    vendor_name: str
    status: str
    grand_total: Decimal
    total_received_value: Decimal
    expected_delivery_date: Optional[date] = None
    gst_amount: Optional[Decimal] = None
    # Nested objects for frontend compatibility
    vendor: Optional[POVendorBrief] = None
    warehouse: Optional[POWarehouseBrief] = None


class POListResponse(BaseModel):
    """Response for listing POs."""
    items: List[POBrief]
    total: int
    total_value: Decimal
    page: int = 1
    size: int = 50
    pages: int = 1


class POApproveRequest(BaseModel):
    """Request to approve/reject PO."""
    action: str = Field(default="APPROVE", pattern="^(APPROVE|REJECT)$")
    rejection_reason: Optional[str] = None


class POSendToVendorRequest(BaseModel):
    """Request to send PO to vendor."""
    send_email: bool = True
    email_recipients: Optional[List[str]] = None
    email_subject: Optional[str] = None
    email_body: Optional[str] = None


# ==================== GRN Schemas ====================

class GRNItemBase(BaseModel):
    """Base schema for GRN item."""
    po_item_id: UUID
    product_id: UUID
    variant_id: Optional[UUID] = None
    product_name: str
    sku: str
    quantity_expected: int
    quantity_received: int = Field(..., ge=0)
    quantity_accepted: int = Field(0, ge=0)
    quantity_rejected: int = Field(0, ge=0)
    uom: str = "PCS"
    batch_number: Optional[str] = None
    manufacturing_date: Optional[date] = None
    expiry_date: Optional[date] = None
    serial_numbers: Optional[List[str]] = None
    bin_id: Optional[UUID] = None
    bin_location: Optional[str] = None
    rejection_reason: Optional[str] = None
    remarks: Optional[str] = None


class GRNItemCreate(GRNItemBase):
    """Schema for creating GRN item."""
    pass


class GRNItemResponse(BaseResponseSchema):
    """Response schema for GRN item."""
    id: UUID
    unit_price: Decimal
    accepted_value: Decimal
    qc_result: Optional[QualityCheckResult] = None


class GoodsReceiptBase(BaseModel):
    """Base schema for GRN."""
    purchase_order_id: UUID
    warehouse_id: UUID
    vendor_challan_number: Optional[str] = None
    vendor_challan_date: Optional[date] = None
    transporter_name: Optional[str] = None
    vehicle_number: Optional[str] = None
    lr_number: Optional[str] = None
    e_way_bill_number: Optional[str] = None
    qc_required: bool = True
    receiving_remarks: Optional[str] = None


class GoodsReceiptCreate(GoodsReceiptBase):
    """Schema for creating GRN."""
    grn_date: date
    items: List[GRNItemCreate]


class GoodsReceiptUpdate(BaseModel):
    """Schema for updating GRN."""
    vendor_challan_number: Optional[str] = None
    vendor_challan_date: Optional[date] = None
    transporter_name: Optional[str] = None
    vehicle_number: Optional[str] = None
    receiving_remarks: Optional[str] = None


class GoodsReceiptResponse(BaseResponseSchema):
    """Response schema for GRN."""
    id: UUID
    grn_number: str
    grn_date: date
    status: str
    vendor_id: UUID
    total_items: int
    total_quantity_received: int
    total_quantity_accepted: int
    total_quantity_rejected: int
    total_value: Decimal
    qc_status: Optional[QualityCheckResult] = None
    qc_done_by: Optional[UUID] = None
    qc_done_at: Optional[datetime] = None
    qc_remarks: Optional[str] = None
    received_by: UUID
    put_away_complete: bool
    put_away_at: Optional[datetime] = None
    items: List[GRNItemResponse] = []
    grn_pdf_url: Optional[str] = None
    photos_urls: Optional[List[str]] = None
    created_at: datetime
    updated_at: datetime


class GRNBrief(BaseResponseSchema):
    """Brief GRN for listing."""
    id: UUID
    grn_number: str
    grn_date: date
    po_number: str
    vendor_name: str
    status: str
    total_quantity_received: int
    total_value: Decimal


class GRNListResponse(BaseModel):
    """Response for listing GRNs."""
    items: List[GRNBrief]
    total: int
    total_value: Decimal
    page: int = 1
    size: int = 50
    pages: int = 1


class GRNQualityCheckRequest(BaseModel):
    """Request for QC on GRN."""
    item_results: List[dict]  # [{item_id, qc_result, rejection_reason}]
    overall_remarks: Optional[str] = None


class GRNPutAwayRequest(BaseModel):
    """Request for put-away after GRN."""
    item_locations: List[dict]  # [{item_id, bin_id, bin_location}]


# ==================== Vendor Invoice Schemas ====================

class VendorInvoiceBase(BaseModel):
    """Base schema for Vendor Invoice."""
    vendor_id: UUID
    invoice_number: str = Field(..., max_length=50)
    invoice_date: date
    purchase_order_id: Optional[UUID] = None
    grn_id: Optional[UUID] = None
    subtotal: Decimal = Field(..., ge=0)
    discount_amount: Decimal = Field(Decimal("0"), ge=0)
    cgst_amount: Decimal = Field(Decimal("0"), ge=0)
    sgst_amount: Decimal = Field(Decimal("0"), ge=0)
    igst_amount: Decimal = Field(Decimal("0"), ge=0)
    cess_amount: Decimal = Field(Decimal("0"), ge=0)
    freight_charges: Decimal = Field(Decimal("0"), ge=0)
    other_charges: Decimal = Field(Decimal("0"), ge=0)
    round_off: Decimal = Field(Decimal("0"))
    grand_total: Decimal = Field(..., ge=0)
    due_date: date
    tds_applicable: bool = True
    tds_section: Optional[str] = None
    tds_rate: Decimal = Field(Decimal("0"), ge=0, le=100)
    vendor_irn: Optional[str] = None
    vendor_ack_number: Optional[str] = None
    invoice_pdf_url: Optional[str] = None
    internal_notes: Optional[str] = None


class VendorInvoiceCreate(VendorInvoiceBase):
    """Schema for creating vendor invoice."""
    pass


class VendorInvoiceUpdate(BaseModel):
    """Schema for updating vendor invoice."""
    due_date: Optional[date] = None
    tds_rate: Optional[Decimal] = None
    internal_notes: Optional[str] = None


class VendorInvoiceResponse(BaseResponseSchema):
    """Response schema for Vendor Invoice."""
    id: UUID
    our_reference: str
    status: str
    taxable_amount: Decimal
    total_tax: Decimal
    tds_amount: Decimal
    net_payable: Decimal
    amount_paid: Decimal
    balance_due: Decimal
    po_matched: bool
    grn_matched: bool
    is_fully_matched: bool
    matching_variance: Decimal
    variance_reason: Optional[str] = None
    received_by: UUID
    received_at: datetime
    verified_by: Optional[UUID] = None
    verified_at: Optional[datetime] = None
    approved_by: Optional[UUID] = None
    approved_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime


class VendorInvoiceBrief(BaseResponseSchema):
    """Brief vendor invoice."""
    id: UUID
    our_reference: str
    invoice_number: str
    invoice_date: date
    vendor_name: str
    grand_total: Decimal
    balance_due: Decimal
    due_date: date
    status: str


class VendorInvoiceListResponse(BaseModel):
    """Response for listing vendor invoices."""
    items: List[VendorInvoiceBrief]
    total: int
    total_value: Decimal
    total_balance: Decimal
    page: int = 1
    size: int = 50
    pages: int = 1


class ThreeWayMatchRequest(BaseModel):
    """Request for 3-way matching."""
    vendor_invoice_id: UUID
    purchase_order_id: UUID
    grn_id: UUID
    tolerance_percentage: Decimal = Field(Decimal("2"), ge=0, le=10)


class ThreeWayMatchResponse(BaseModel):
    """Response for 3-way matching."""
    is_matched: bool
    po_total: Decimal
    grn_value: Decimal
    invoice_total: Decimal
    variance_amount: Decimal
    variance_percentage: Decimal
    discrepancies: List[dict] = []
    recommendations: List[str] = []


# ==================== Report Schemas ====================

class POSummaryRequest(BaseModel):
    """Request for PO summary."""
    start_date: date
    end_date: date
    vendor_id: Optional[UUID] = None
    warehouse_id: Optional[UUID] = None


class POSummaryResponse(BaseModel):
    """PO summary response."""
    period_start: date
    period_end: date
    total_po_count: int
    total_po_value: Decimal
    pending_count: int
    pending_value: Decimal
    received_count: int
    received_value: Decimal
    cancelled_count: int
    cancelled_value: Decimal
    by_vendor: List[dict] = []
    by_status: dict = {}


class GRNSummaryResponse(BaseModel):
    """GRN summary response."""
    period_start: date
    period_end: date
    total_grn_count: int
    total_received_value: Decimal
    total_accepted_value: Decimal
    total_rejected_value: Decimal
    rejection_rate: Decimal
    by_vendor: List[dict] = []
    by_warehouse: List[dict] = []


class PendingGRNResponse(BaseModel):
    """Pending GRNs against POs."""
    po_id: UUID
    po_number: str
    vendor_name: str
    po_date: date
    expected_date: Optional[date]
    total_ordered: int
    total_received: int
    pending_quantity: int
    pending_value: Decimal
    days_pending: int


# ==================== Vendor Proforma Invoice Schemas ====================

class VendorProformaItemBase(BaseModel):
    """Base schema for Vendor Proforma item."""
    product_id: Optional[UUID] = None
    item_code: Optional[str] = None
    description: str
    hsn_code: Optional[str] = None
    uom: str = "PCS"
    quantity: int = Field(..., gt=0)
    unit_price: Decimal = Field(..., ge=0)
    discount_percent: Decimal = Field(Decimal("0"), ge=0, le=100)
    gst_rate: Decimal = Field(Decimal("18"), ge=0, le=28)
    lead_time_days: Optional[int] = None


class VendorProformaItemCreate(VendorProformaItemBase):
    """Schema for creating Vendor Proforma item."""
    pass


class VendorProformaItemResponse(BaseResponseSchema):
    """Response schema for Vendor Proforma item."""
    id: UUID
    proforma_id: UUID
    discount_amount: Decimal
    taxable_amount: Decimal
    cgst_amount: Decimal
    sgst_amount: Decimal
    igst_amount: Decimal
    total_amount: Decimal


class VendorProformaBase(BaseModel):
    """Base schema for Vendor Proforma Invoice."""
    vendor_id: UUID
    proforma_number: str = Field(..., max_length=50)
    proforma_date: date
    validity_date: Optional[date] = None
    delivery_warehouse_id: Optional[UUID] = None
    delivery_days: Optional[int] = None
    delivery_terms: Optional[str] = None
    payment_terms: Optional[str] = None
    credit_days: int = 30
    freight_charges: Decimal = Field(Decimal("0"), ge=0)
    packing_charges: Decimal = Field(Decimal("0"), ge=0)
    other_charges: Decimal = Field(Decimal("0"), ge=0)
    round_off: Decimal = Field(Decimal("0"))
    proforma_pdf_url: Optional[str] = None
    vendor_remarks: Optional[str] = None
    internal_notes: Optional[str] = None


class VendorProformaCreate(VendorProformaBase):
    """Schema for creating Vendor Proforma Invoice."""
    proforma_number: Optional[str] = None  # Generated server-side if not provided
    vendor_pi_number: Optional[str] = None  # Vendor's original PI/quotation number
    requisition_id: Optional[UUID] = None
    items: List[VendorProformaItemCreate]


class VendorProformaUpdate(BaseModel):
    """Schema for updating Vendor Proforma Invoice."""
    validity_date: Optional[date] = None
    delivery_days: Optional[int] = None
    delivery_terms: Optional[str] = None
    payment_terms: Optional[str] = None
    credit_days: Optional[int] = None
    internal_notes: Optional[str] = None


class VendorProformaResponse(BaseResponseSchema):
    """Response schema for Vendor Proforma Invoice."""
    id: UUID
    our_reference: str
    status: str
    requisition_id: Optional[UUID] = None
    purchase_order_id: Optional[UUID] = None
    subtotal: Decimal
    discount_amount: Decimal
    discount_percent: Decimal
    taxable_amount: Decimal
    cgst_amount: Decimal
    sgst_amount: Decimal
    igst_amount: Decimal
    total_tax: Decimal
    grand_total: Decimal
    received_by: Optional[UUID] = None
    received_at: Optional[datetime] = None
    approved_by: Optional[UUID] = None
    approved_at: Optional[datetime] = None
    rejection_reason: Optional[str] = None
    items: List[VendorProformaItemResponse] = []
    created_at: datetime
    updated_at: datetime


class VendorProformaBrief(BaseResponseSchema):
    """Brief vendor proforma for listing."""
    id: UUID
    our_reference: str
    proforma_number: str
    proforma_date: date
    vendor_name: str
    grand_total: Decimal
    validity_date: Optional[date] = None
    status: str


class VendorProformaListResponse(BaseModel):
    """Response for listing vendor proformas."""
    items: List[VendorProformaBrief]
    total: int
    total_value: Decimal
    page: int = 1
    size: int = 50
    pages: int = 1


class VendorProformaApproveRequest(BaseModel):
    """Request to approve/reject vendor proforma."""
    action: str = Field(..., pattern="^(APPROVE|REJECT)$")
    rejection_reason: Optional[str] = None


class VendorProformaConvertToPORequest(BaseModel):
    """Request to convert vendor proforma to PO."""
    expected_delivery_date: Optional[date] = None
    delivery_warehouse_id: Optional[UUID] = None
    special_instructions: Optional[str] = None


# ==================== Sales Return Note (SRN) Schemas ====================

class SRNItemCreate(BaseModel):
    """Schema for creating SRN item."""
    order_item_id: Optional[UUID] = None
    invoice_item_id: Optional[UUID] = None
    product_id: UUID
    variant_id: Optional[UUID] = None
    product_name: str
    sku: str
    hsn_code: Optional[str] = None
    serial_numbers: Optional[List[str]] = None
    quantity_sold: int = Field(..., gt=0, description="Original sale quantity")
    quantity_returned: int = Field(..., gt=0, description="Quantity being returned")
    unit_price: Decimal = Field(..., ge=0)
    uom: str = "PCS"
    remarks: Optional[str] = None


class SRNItemResponse(BaseResponseSchema):
    """Response schema for SRN item."""
    id: UUID
    srn_id: UUID
    order_item_id: Optional[UUID] = None
    invoice_item_id: Optional[UUID] = None
    product_id: UUID
    variant_id: Optional[UUID] = None
    product_name: str
    sku: str
    hsn_code: Optional[str] = None
    serial_numbers: Optional[List[str]] = None
    quantity_sold: int
    quantity_returned: int
    quantity_accepted: int = 0
    quantity_rejected: int = 0
    uom: str = "PCS"
    unit_price: Decimal
    return_value: Decimal = Decimal("0")
    item_condition: Optional[str] = None
    restock_decision: Optional[str] = None
    qc_result: Optional[str] = None
    rejection_reason: Optional[str] = None
    bin_id: Optional[UUID] = None
    bin_location: Optional[str] = None
    remarks: Optional[str] = None


class SRNItemQCResult(BaseModel):
    """QC result for individual SRN item."""
    item_id: UUID
    qc_result: str = Field(..., description="PASSED, FAILED, CONDITIONAL")
    item_condition: Optional[str] = Field(None, description="LIKE_NEW, GOOD, DAMAGED, DEFECTIVE, UNSALVAGEABLE")
    restock_decision: Optional[str] = Field(None, description="RESTOCK_AS_NEW, RESTOCK_AS_REFURB, SEND_FOR_REPAIR, RETURN_TO_VENDOR, SCRAP")
    quantity_accepted: Optional[int] = None
    quantity_rejected: Optional[int] = None
    rejection_reason: Optional[str] = None


class SalesReturnCreate(BaseModel):
    """Schema for creating Sales Return Note."""
    srn_date: date
    order_id: Optional[UUID] = Field(None, description="Reference to original order")
    invoice_id: Optional[UUID] = Field(None, description="Reference to original invoice")
    customer_id: UUID
    warehouse_id: UUID
    return_reason: str = Field(..., description="Reason for return")
    return_reason_detail: Optional[str] = None
    pickup_required: bool = False
    pickup_scheduled_date: Optional[date] = None
    pickup_scheduled_slot: Optional[str] = Field(None, description="Time slot e.g., 10AM-12PM")
    pickup_address: Optional[dict] = None
    pickup_contact_name: Optional[str] = None
    pickup_contact_phone: Optional[str] = None
    qc_required: bool = True
    receiving_remarks: Optional[str] = None
    items: List[SRNItemCreate]


class SalesReturnResponse(BaseResponseSchema):
    """Response schema for Sales Return Note."""
    id: UUID
    srn_number: str
    srn_date: date
    order_id: Optional[UUID] = None
    invoice_id: Optional[UUID] = None
    customer_id: UUID
    warehouse_id: UUID
    status: str
    return_reason: str
    return_reason_detail: Optional[str] = None
    resolution_type: Optional[str] = None
    credit_note_id: Optional[UUID] = None
    replacement_order_id: Optional[UUID] = None

    # Pickup/Reverse Logistics
    pickup_required: bool = False
    pickup_status: Optional[str] = None
    pickup_scheduled_date: Optional[date] = None
    pickup_scheduled_slot: Optional[str] = None
    pickup_address: Optional[dict] = None
    pickup_contact_name: Optional[str] = None
    pickup_contact_phone: Optional[str] = None
    courier_id: Optional[UUID] = None
    courier_name: Optional[str] = None
    courier_tracking_number: Optional[str] = None
    pickup_requested_at: Optional[datetime] = None
    pickup_completed_at: Optional[datetime] = None

    # QC
    qc_required: bool = True
    qc_status: Optional[str] = None
    qc_done_by: Optional[UUID] = None
    qc_done_at: Optional[datetime] = None
    qc_remarks: Optional[str] = None

    # Quantities
    total_items: int = 0
    total_quantity_returned: int = 0
    total_quantity_accepted: int = 0
    total_quantity_rejected: int = 0
    total_value: Decimal = Decimal("0")

    # Put-away
    put_away_complete: bool = False
    put_away_at: Optional[datetime] = None

    # Receiving
    received_by: Optional[UUID] = None
    received_at: Optional[datetime] = None
    receiving_remarks: Optional[str] = None

    # Documents
    srn_pdf_url: Optional[str] = None
    photos_urls: Optional[List[str]] = None

    # Computed fields (populated from relationships)
    customer_name: Optional[str] = None
    warehouse_name: Optional[str] = None
    order_number: Optional[str] = None
    invoice_number: Optional[str] = None

    # Items
    items: List[SRNItemResponse] = []

    # Audit
    created_by: UUID
    created_at: datetime
    updated_at: datetime


class SRNBrief(BaseResponseSchema):
    """Brief SRN for listing."""
    id: UUID
    srn_number: str
    srn_date: date
    customer_id: UUID
    customer_name: Optional[str] = None
    order_id: Optional[UUID] = None
    order_number: Optional[str] = None
    invoice_number: Optional[str] = None
    warehouse_name: Optional[str] = None
    status: str
    return_reason: str
    pickup_required: bool = False
    pickup_status: Optional[str] = None
    total_quantity_returned: int = 0
    total_quantity_accepted: int = 0
    total_value: Decimal = Decimal("0")
    resolution_type: Optional[str] = None


class SRNListResponse(BaseModel):
    """Response for listing SRNs."""
    items: List[SRNBrief]
    total: int
    total_value: Decimal = Decimal("0")
    page: int = 1
    size: int = 50
    pages: int = 1


class SRNQualityCheckRequest(BaseModel):
    """Request to process QC for SRN."""
    item_results: List[SRNItemQCResult]
    overall_remarks: Optional[str] = None


class SRNItemPutAway(BaseModel):
    """Put-away location for SRN item."""
    item_id: UUID
    bin_id: Optional[UUID] = None
    bin_location: Optional[str] = None


class SRNPutAwayRequest(BaseModel):
    """Request to process put-away for SRN."""
    item_locations: List[SRNItemPutAway]


class PickupScheduleRequest(BaseModel):
    """Request to schedule pickup for SRN."""
    pickup_date: date
    pickup_slot: Optional[str] = Field(None, description="Time slot e.g., 10AM-12PM, 12PM-3PM, 3PM-6PM")
    pickup_address: Optional[dict] = Field(None, description="Override pickup address (uses customer address if None)")
    pickup_contact_name: Optional[str] = None
    pickup_contact_phone: Optional[str] = None
    courier_id: Optional[UUID] = None


class PickupUpdateRequest(BaseModel):
    """Request to update pickup status for SRN."""
    pickup_status: Optional[str] = Field(None, description="SCHEDULED, PICKUP_FAILED, PICKED_UP, IN_TRANSIT, DELIVERED")
    courier_id: Optional[UUID] = None
    courier_name: Optional[str] = None
    courier_tracking_number: Optional[str] = Field(None, description="AWB Number")


class SRNReceiveRequest(BaseModel):
    """Request to mark SRN as received."""
    receiving_remarks: Optional[str] = None


class SRNResolveRequest(BaseModel):
    """Request to resolve SRN (issue credit note, replacement, or refund)."""
    resolution_type: str = Field(..., description="CREDIT_NOTE, REPLACEMENT, REFUND, REPAIR, REJECT")
    notes: Optional[str] = None
