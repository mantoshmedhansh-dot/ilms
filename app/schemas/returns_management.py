"""
Returns Management Schemas - Phase 9: Reverse Logistics & Return Processing.

Pydantic schemas for returns management operations.
"""
from datetime import datetime, date
from decimal import Decimal
from typing import Optional, List, Dict, Any
from uuid import UUID

from pydantic import BaseModel, Field, ConfigDict

from app.models.returns_management import (
    ReturnType, ReturnReason, RMAStatus, ReturnReceiptStatus,
    InspectionGrade, InspectionStatus, DispositionAction,
    RefurbishmentStatus, RefundType, RefundStatus
)


# ============================================================================
# RETURN AUTHORIZATION SCHEMAS
# ============================================================================

class ReturnAuthorizationItemBase(BaseModel):
    """Base schema for RMA item."""
    product_id: UUID
    sku: str = Field(..., max_length=100)
    product_name: str = Field(..., max_length=255)
    ordered_quantity: int = Field(..., ge=1)
    requested_quantity: int = Field(..., ge=1)
    unit_price: Decimal
    total_value: Decimal
    return_reason: ReturnReason
    reason_detail: Optional[str] = None
    serial_numbers: Optional[List[str]] = None
    lot_number: Optional[str] = Field(None, max_length=50)
    photos: Optional[List[str]] = None
    notes: Optional[str] = None


class ReturnAuthorizationItemCreate(ReturnAuthorizationItemBase):
    """Schema for creating an RMA item."""
    pass


class ReturnAuthorizationItemResponse(ReturnAuthorizationItemBase):
    """Schema for RMA item response."""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    rma_id: UUID
    approved_quantity: int
    received_quantity: int
    refund_amount: Decimal
    status: str
    created_at: datetime


class ReturnAuthorizationBase(BaseModel):
    """Base schema for return authorization."""
    return_type: ReturnType
    order_id: Optional[UUID] = None
    order_number: Optional[str] = Field(None, max_length=50)
    invoice_number: Optional[str] = Field(None, max_length=50)
    customer_id: Optional[UUID] = None
    customer_name: Optional[str] = Field(None, max_length=200)
    customer_email: Optional[str] = Field(None, max_length=200)
    customer_phone: Optional[str] = Field(None, max_length=20)
    warehouse_id: UUID
    return_reason: ReturnReason
    reason_detail: Optional[str] = None
    refund_type: Optional[RefundType] = None
    return_shipping_method: Optional[str] = Field(None, max_length=50)
    shipping_paid_by: Optional[str] = Field(None, max_length=30)
    pickup_required: bool = False
    pickup_address: Optional[Dict[str, Any]] = None
    pickup_scheduled_date: Optional[date] = None
    photos: Optional[List[str]] = None
    documents: Optional[List[str]] = None
    notes: Optional[str] = None


class ReturnAuthorizationCreate(ReturnAuthorizationBase):
    """Schema for creating a return authorization."""
    items: List[ReturnAuthorizationItemCreate]


class ReturnAuthorizationUpdate(BaseModel):
    """Schema for updating a return authorization."""
    return_reason: Optional[ReturnReason] = None
    reason_detail: Optional[str] = None
    refund_type: Optional[RefundType] = None
    return_shipping_method: Optional[str] = Field(None, max_length=50)
    return_tracking_number: Optional[str] = Field(None, max_length=100)
    shipping_paid_by: Optional[str] = Field(None, max_length=30)
    shipping_cost: Optional[Decimal] = None
    pickup_scheduled_date: Optional[date] = None
    pickup_completed_date: Optional[date] = None
    photos: Optional[List[str]] = None
    documents: Optional[List[str]] = None
    notes: Optional[str] = None
    internal_notes: Optional[str] = None


class ReturnAuthorizationResponse(ReturnAuthorizationBase):
    """Schema for return authorization response."""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    rma_number: str
    status: RMAStatus
    total_items: int
    approved_items: int
    received_items: int
    original_order_value: Decimal
    return_value: Decimal
    refund_amount: Decimal
    refund_status: Optional[RefundStatus]
    return_tracking_number: Optional[str]
    shipping_cost: Decimal
    request_date: date
    approval_date: Optional[date]
    expiry_date: Optional[date]
    approved_by: Optional[UUID]
    rejection_reason: Optional[str]
    internal_notes: Optional[str]
    created_by: Optional[UUID]
    created_at: datetime
    updated_at: datetime
    items: Optional[List[ReturnAuthorizationItemResponse]] = None


class RMAApproval(BaseModel):
    """Schema for approving/rejecting RMA."""
    approved: bool
    item_approvals: Optional[List[Dict[str, Any]]] = None
    expiry_days: int = Field(default=30, ge=7, le=90)
    rejection_reason: Optional[str] = Field(None, max_length=500)
    notes: Optional[str] = None


# ============================================================================
# RETURN RECEIPT SCHEMAS
# ============================================================================

class ReturnReceiptItemBase(BaseModel):
    """Base schema for return receipt item."""
    rma_item_id: UUID
    product_id: UUID
    sku: str = Field(..., max_length=100)
    expected_quantity: int = Field(..., ge=1)
    received_quantity: int = Field(default=0, ge=0)
    damaged_quantity: int = Field(default=0, ge=0)
    serial_numbers: Optional[List[str]] = None
    lot_number: Optional[str] = Field(None, max_length=50)
    initial_condition: Optional[str] = Field(None, max_length=30)
    condition_notes: Optional[str] = None
    needs_inspection: bool = True
    notes: Optional[str] = None


class ReturnReceiptItemCreate(ReturnReceiptItemBase):
    """Schema for creating a return receipt item."""
    pass


class ReturnReceiptItemResponse(ReturnReceiptItemBase):
    """Schema for return receipt item response."""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    receipt_id: UUID
    put_away_bin_id: Optional[UUID]
    inspection_id: Optional[UUID]
    created_at: datetime


class ReturnReceiptBase(BaseModel):
    """Base schema for return receipt."""
    rma_id: UUID
    warehouse_id: UUID
    receiving_zone_id: Optional[UUID] = None
    receiving_bin_id: Optional[UUID] = None
    carrier: Optional[str] = Field(None, max_length=100)
    tracking_number: Optional[str] = Field(None, max_length=100)
    expected_date: Optional[date] = None
    receipt_date: date
    package_condition: Optional[str] = Field(None, max_length=30)
    condition_notes: Optional[str] = None
    package_photos: Optional[List[str]] = None
    notes: Optional[str] = None


class ReturnReceiptCreate(ReturnReceiptBase):
    """Schema for creating a return receipt."""
    items: List[ReturnReceiptItemCreate]


class ReturnReceiptUpdate(BaseModel):
    """Schema for updating a return receipt."""
    receiving_zone_id: Optional[UUID] = None
    receiving_bin_id: Optional[UUID] = None
    package_condition: Optional[str] = Field(None, max_length=30)
    condition_notes: Optional[str] = None
    package_photos: Optional[List[str]] = None
    notes: Optional[str] = None


class ReturnReceiptResponse(ReturnReceiptBase):
    """Schema for return receipt response."""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    receipt_number: str
    status: ReturnReceiptStatus
    expected_quantity: int
    received_quantity: int
    damaged_quantity: int
    missing_quantity: int
    received_by: Optional[UUID]
    created_at: datetime
    updated_at: datetime
    items: Optional[List[ReturnReceiptItemResponse]] = None


class ReceiveItems(BaseModel):
    """Schema for receiving items."""
    items: List[Dict[str, Any]]


# ============================================================================
# RETURN INSPECTION SCHEMAS
# ============================================================================

class ReturnInspectionBase(BaseModel):
    """Base schema for return inspection."""
    receipt_item_id: UUID
    rma_id: UUID
    warehouse_id: UUID
    product_id: UUID
    sku: str = Field(..., max_length=100)
    product_name: str = Field(..., max_length=255)
    serial_number: Optional[str] = Field(None, max_length=100)
    lot_number: Optional[str] = Field(None, max_length=50)
    inspection_date: date


class ReturnInspectionCreate(ReturnInspectionBase):
    """Schema for creating a return inspection."""
    pass


class ReturnInspectionUpdate(BaseModel):
    """Schema for updating a return inspection."""
    checklist_results: Optional[List[Dict[str, Any]]] = None
    defects_found: Optional[List[Dict[str, Any]]] = None
    claim_verified: Optional[bool] = None
    claim_notes: Optional[str] = None
    functional_test_passed: Optional[bool] = None
    test_results: Optional[Dict[str, Any]] = None
    cosmetic_condition: Optional[str] = Field(None, max_length=30)
    cosmetic_notes: Optional[str] = None
    original_packaging: Optional[bool] = None
    packaging_condition: Optional[str] = Field(None, max_length=30)
    accessories_complete: Optional[bool] = None
    missing_accessories: Optional[List[str]] = None
    photos: Optional[List[str]] = None
    notes: Optional[str] = None


class ReturnInspectionResponse(ReturnInspectionBase):
    """Schema for return inspection response."""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    inspection_number: str
    status: InspectionStatus
    inspector_id: Optional[UUID]
    grade: Optional[InspectionGrade]
    checklist_results: Optional[List[Dict[str, Any]]]
    defects_found: Optional[List[Dict[str, Any]]]
    defect_count: int
    claim_verified: Optional[bool]
    claim_notes: Optional[str]
    functional_test_passed: Optional[bool]
    test_results: Optional[Dict[str, Any]]
    cosmetic_condition: Optional[str]
    cosmetic_notes: Optional[str]
    original_packaging: bool
    packaging_condition: Optional[str]
    accessories_complete: bool
    missing_accessories: Optional[List[str]]
    photos: Optional[List[str]]
    recommended_disposition: Optional[DispositionAction]
    disposition_notes: Optional[str]
    final_disposition: Optional[DispositionAction]
    disposition_by: Optional[UUID]
    disposition_at: Optional[datetime]
    refund_eligible: bool
    refund_deduction: Decimal
    refund_notes: Optional[str]
    notes: Optional[str]
    created_at: datetime
    updated_at: datetime


class InspectionComplete(BaseModel):
    """Schema for completing an inspection."""
    grade: InspectionGrade
    checklist_results: Optional[List[Dict[str, Any]]] = None
    defects_found: Optional[List[Dict[str, Any]]] = None
    claim_verified: bool
    functional_test_passed: Optional[bool] = None
    cosmetic_condition: str = Field(..., max_length=30)
    original_packaging: bool
    accessories_complete: bool
    missing_accessories: Optional[List[str]] = None
    recommended_disposition: DispositionAction
    refund_eligible: bool = True
    refund_deduction: Decimal = Field(default=Decimal("0"))
    photos: Optional[List[str]] = None
    notes: Optional[str] = None


class InspectionDisposition(BaseModel):
    """Schema for setting inspection disposition."""
    disposition: DispositionAction
    notes: Optional[str] = None


# ============================================================================
# REFURBISHMENT SCHEMAS
# ============================================================================

class RefurbishmentOrderBase(BaseModel):
    """Base schema for refurbishment order."""
    inspection_id: UUID
    warehouse_id: UUID
    product_id: UUID
    sku: str = Field(..., max_length=100)
    serial_number: Optional[str] = Field(None, max_length=100)
    refurbishment_type: str = Field(..., max_length=30)
    work_description: str
    work_items: Optional[List[Dict[str, Any]]] = None
    parts_required: Optional[List[Dict[str, Any]]] = None
    estimated_labor_hours: Optional[Decimal] = None
    due_date: Optional[date] = None
    vendor_id: Optional[UUID] = None
    qc_required: bool = True
    notes: Optional[str] = None


class RefurbishmentOrderCreate(RefurbishmentOrderBase):
    """Schema for creating a refurbishment order."""
    pass


class RefurbishmentOrderUpdate(BaseModel):
    """Schema for updating a refurbishment order."""
    work_description: Optional[str] = None
    work_items: Optional[List[Dict[str, Any]]] = None
    parts_required: Optional[List[Dict[str, Any]]] = None
    parts_cost: Optional[Decimal] = None
    estimated_labor_hours: Optional[Decimal] = None
    due_date: Optional[date] = None
    assigned_to: Optional[UUID] = None
    vendor_id: Optional[UUID] = None
    notes: Optional[str] = None


class RefurbishmentOrderResponse(RefurbishmentOrderBase):
    """Schema for refurbishment order response."""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    order_number: str
    status: RefurbishmentStatus
    parts_cost: Decimal
    actual_labor_hours: Optional[Decimal]
    labor_cost: Decimal
    total_cost: Decimal
    assigned_to: Optional[UUID]
    assigned_at: Optional[datetime]
    created_date: date
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    result_grade: Optional[InspectionGrade]
    result_notes: Optional[str]
    destination_bin_id: Optional[UUID]
    qc_passed: Optional[bool]
    qc_by: Optional[UUID]
    qc_at: Optional[datetime]
    qc_notes: Optional[str]
    before_photos: Optional[List[str]]
    after_photos: Optional[List[str]]
    created_by: Optional[UUID]
    created_at: datetime
    updated_at: datetime


class RefurbishmentComplete(BaseModel):
    """Schema for completing a refurbishment."""
    result_grade: InspectionGrade
    actual_labor_hours: Decimal
    parts_cost: Decimal
    result_notes: Optional[str] = None
    destination_bin_id: Optional[UUID] = None
    after_photos: Optional[List[str]] = None


class RefurbishmentQC(BaseModel):
    """Schema for QC on refurbishment."""
    passed: bool
    notes: Optional[str] = None


# ============================================================================
# DISPOSITION SCHEMAS
# ============================================================================

class DispositionRecordBase(BaseModel):
    """Base schema for disposition record."""
    inspection_id: UUID
    refurbishment_id: Optional[UUID] = None
    warehouse_id: UUID
    product_id: UUID
    sku: str = Field(..., max_length=100)
    serial_number: Optional[str] = Field(None, max_length=100)
    lot_number: Optional[str] = Field(None, max_length=50)
    quantity: int = Field(default=1, ge=1)
    disposition_action: DispositionAction
    grade: Optional[InspectionGrade] = None
    original_value: Decimal = Field(default=Decimal("0"))
    recovered_value: Decimal = Field(default=Decimal("0"))
    destination_bin_id: Optional[UUID] = None
    vendor_id: Optional[UUID] = None
    vendor_rma_number: Optional[str] = Field(None, max_length=50)
    vendor_credit_amount: Decimal = Field(default=Decimal("0"))
    donation_recipient: Optional[str] = Field(None, max_length=200)
    donation_reference: Optional[str] = Field(None, max_length=50)
    destruction_method: Optional[str] = Field(None, max_length=100)
    destruction_certificate: Optional[str] = Field(None, max_length=200)
    environmental_compliance: bool = True
    requires_approval: bool = False
    reason: str = Field(..., max_length=200)
    notes: Optional[str] = None
    photos: Optional[List[str]] = None


class DispositionRecordCreate(DispositionRecordBase):
    """Schema for creating a disposition record."""
    pass


class DispositionRecordResponse(DispositionRecordBase):
    """Schema for disposition record response."""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    disposition_number: str
    disposition_date: date
    loss_value: Decimal
    approved_by: Optional[UUID]
    approved_at: Optional[datetime]
    executed_by: Optional[UUID]
    executed_at: Optional[datetime]
    created_by: Optional[UUID]
    created_at: datetime


class DispositionApproval(BaseModel):
    """Schema for approving disposition."""
    approved: bool
    notes: Optional[str] = None


class DispositionExecute(BaseModel):
    """Schema for executing disposition."""
    destination_bin_id: Optional[UUID] = None
    photos: Optional[List[str]] = None
    notes: Optional[str] = None


# ============================================================================
# DASHBOARD SCHEMAS
# ============================================================================

class ReturnsDashboard(BaseModel):
    """Dashboard statistics for returns."""
    # RMA Stats
    pending_rmas: int
    approved_rmas: int
    total_rmas_mtd: int
    total_items_returned_mtd: int

    # Receipt Stats
    pending_receipts: int
    received_today: int

    # Inspection Stats
    pending_inspections: int
    completed_inspections_mtd: int

    # Grade Distribution
    grade_a_count: int
    grade_b_count: int
    grade_c_count: int
    grade_d_count: int
    grade_f_count: int

    # Disposition Stats
    restocked_count: int
    refurbished_count: int
    scrapped_count: int
    vendor_returned_count: int

    # Financial
    total_return_value_mtd: Decimal
    total_refund_amount_mtd: Decimal
    recovery_rate: Optional[Decimal]

    # Recent Activity
    recent_rmas: List[ReturnAuthorizationResponse]
    recent_inspections: List[ReturnInspectionResponse]
