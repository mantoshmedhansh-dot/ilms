"""
Pydantic schemas for Return Orders and Refunds.
"""

from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Optional, List
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.base import BaseResponseSchema


# ==================== Enums ====================

class ReturnType(str, Enum):
    RETURN = "RETURN"
    EXCHANGE = "EXCHANGE"
    REPLACEMENT = "REPLACEMENT"


class ReturnReason(str, Enum):
    DAMAGED = "DAMAGED"
    DEFECTIVE = "DEFECTIVE"
    WRONG_ITEM = "WRONG_ITEM"
    NOT_AS_DESCRIBED = "NOT_AS_DESCRIBED"
    CHANGED_MIND = "CHANGED_MIND"
    SIZE_FIT_ISSUE = "SIZE_FIT_ISSUE"
    QUALITY_ISSUE = "QUALITY_ISSUE"
    OTHER = "OTHER"


class ReturnStatus(str, Enum):
    INITIATED = "INITIATED"
    AUTHORIZED = "AUTHORIZED"
    PICKUP_SCHEDULED = "PICKUP_SCHEDULED"
    PICKED_UP = "PICKED_UP"
    IN_TRANSIT = "IN_TRANSIT"
    RECEIVED = "RECEIVED"
    UNDER_INSPECTION = "UNDER_INSPECTION"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    REFUND_INITIATED = "REFUND_INITIATED"
    REFUND_PROCESSED = "REFUND_PROCESSED"
    CLOSED = "CLOSED"
    CANCELLED = "CANCELLED"


class ItemCondition(str, Enum):
    UNOPENED = "UNOPENED"
    OPENED_UNUSED = "OPENED_UNUSED"
    USED = "USED"
    DAMAGED = "DAMAGED"
    DEFECTIVE = "DEFECTIVE"


class InspectionResult(str, Enum):
    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"
    PARTIAL = "PARTIAL"


class ResolutionType(str, Enum):
    FULL_REFUND = "FULL_REFUND"
    PARTIAL_REFUND = "PARTIAL_REFUND"
    STORE_CREDIT = "STORE_CREDIT"
    REPLACEMENT = "REPLACEMENT"
    EXCHANGE = "EXCHANGE"


class RefundType(str, Enum):
    FULL = "FULL"
    PARTIAL = "PARTIAL"
    CANCELLATION = "CANCELLATION"
    RETURN = "RETURN"


class RefundMethod(str, Enum):
    ORIGINAL_PAYMENT = "ORIGINAL_PAYMENT"
    BANK_TRANSFER = "BANK_TRANSFER"
    STORE_CREDIT = "STORE_CREDIT"
    WALLET = "WALLET"


class RefundStatus(str, Enum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


# ==================== Return Item Schemas ====================

class ReturnItemCreate(BaseModel):
    """Schema for creating a return item."""
    order_item_id: UUID
    quantity_returned: int = Field(..., ge=1)
    condition: ItemCondition = ItemCondition.UNOPENED
    condition_notes: Optional[str] = None
    customer_images: Optional[List[str]] = None


class ReturnItemResponse(BaseResponseSchema):
    """Schema for return item response."""
    id: UUID
    order_item_id: UUID
    product_id: UUID
    product_name: str
    sku: str
    quantity_ordered: int
    quantity_returned: int
    condition: str
    condition_notes: Optional[str]
    inspection_result: Optional[str]
    inspection_notes: Optional[str]
    accepted_quantity: Optional[int]
    unit_price: Decimal
    total_amount: Decimal
    refund_amount: Decimal
    serial_number: Optional[str]
    customer_images: Optional[List[str]]
# ==================== Pickup Address Schema ====================

class PickupAddress(BaseModel):
    """Pickup address for return."""
    full_name: str
    phone: str
    address_line1: str
    address_line2: Optional[str] = None
    city: str
    state: str
    pincode: str
    country: str = "India"


# ==================== Return Order Schemas ====================

class ReturnOrderCreate(BaseModel):
    """Schema for creating a return request (customer-facing)."""
    order_id: UUID
    return_type: ReturnType = ReturnType.RETURN
    return_reason: ReturnReason
    return_reason_details: Optional[str] = None
    items: List[ReturnItemCreate]
    pickup_address: Optional[PickupAddress] = None


class ReturnOrderUpdate(BaseModel):
    """Schema for updating a return order (admin)."""
    status: Optional[ReturnStatus] = None
    inspection_notes: Optional[str] = None
    inspection_images: Optional[List[str]] = None
    rejection_reason: Optional[str] = None
    resolution_type: Optional[ResolutionType] = None
    resolution_notes: Optional[str] = None
    restocking_fee: Optional[Decimal] = None
    shipping_deduction: Optional[Decimal] = None


class ReturnItemInspection(BaseModel):
    """Schema for inspecting a return item."""
    return_item_id: UUID
    inspection_result: InspectionResult
    inspection_notes: Optional[str] = None
    accepted_quantity: Optional[int] = None


class ReturnInspectionRequest(BaseModel):
    """Schema for submitting return inspection."""
    return_order_id: UUID
    items: List[ReturnItemInspection]
    overall_notes: Optional[str] = None


class ReturnStatusHistoryResponse(BaseResponseSchema):
    """Schema for return status history."""
    id: UUID
    from_status: Optional[str]
    to_status: str
    notes: Optional[str]
    created_at: datetime

class ReturnOrderResponse(BaseResponseSchema):
    """Schema for return order response."""
    id: UUID
    rma_number: str
    order_id: UUID
    customer_id: Optional[UUID]
    return_type: str
    return_reason: str
    return_reason_details: Optional[str]
    status: str
    requested_at: datetime
    authorized_at: Optional[datetime]
    pickup_scheduled_at: Optional[datetime]
    picked_up_at: Optional[datetime]
    received_at: Optional[datetime]
    inspected_at: Optional[datetime]
    closed_at: Optional[datetime]
    return_tracking_number: Optional[str]
    return_courier: Optional[str]
    pickup_address: Optional[dict]
    inspection_notes: Optional[str]
    rejection_reason: Optional[str]
    resolution_type: Optional[str]
    resolution_notes: Optional[str]
    total_return_amount: Decimal
    restocking_fee: Decimal
    shipping_deduction: Decimal
    net_refund_amount: Decimal
    store_credit_amount: Decimal
    store_credit_code: Optional[str]
    replacement_order_id: Optional[UUID]
    created_at: datetime
    updated_at: datetime
    items: List[ReturnItemResponse] = []
    status_history: List[ReturnStatusHistoryResponse] = []

class ReturnOrderListResponse(BaseResponseSchema):
    """Schema for return order list item (summary)."""
    id: UUID
    rma_number: str
    order_id: UUID
    order_number: Optional[str] = None
    return_type: str
    return_reason: str
    status: str
    requested_at: datetime
    total_return_amount: Decimal
    net_refund_amount: Decimal
    items_count: int = 0
# ==================== Refund Schemas ====================

class RefundCreate(BaseModel):
    """Schema for creating a refund (admin)."""
    order_id: UUID
    return_order_id: Optional[UUID] = None
    refund_type: RefundType
    refund_method: RefundMethod = RefundMethod.ORIGINAL_PAYMENT
    refund_amount: Decimal
    reason: str
    notes: Optional[str] = None
    # For bank transfer
    bank_account_number: Optional[str] = None
    bank_ifsc: Optional[str] = None
    bank_account_name: Optional[str] = None


class RefundResponse(BaseResponseSchema):
    """Schema for refund response."""
    id: UUID
    refund_number: str
    order_id: UUID
    return_order_id: Optional[UUID]
    customer_id: Optional[UUID]
    refund_type: str
    refund_method: str
    order_amount: Decimal
    refund_amount: Decimal
    processing_fee: Decimal
    net_refund: Decimal
    tax_refund: Decimal
    status: str
    original_payment_id: Optional[str]
    refund_transaction_id: Optional[str]
    reason: str
    notes: Optional[str]
    initiated_at: datetime
    processed_at: Optional[datetime]
    completed_at: Optional[datetime]
    failed_at: Optional[datetime]
    failure_reason: Optional[str]
    retry_count: int
    created_at: datetime
    updated_at: datetime

class RefundListResponse(BaseResponseSchema):
    """Schema for refund list item (summary)."""
    id: UUID
    refund_number: str
    order_id: UUID
    order_number: Optional[str] = None
    refund_type: str
    net_refund: Decimal
    status: str
    initiated_at: datetime
    completed_at: Optional[datetime]
# ==================== Customer-Facing Schemas ====================

class CustomerReturnRequest(BaseModel):
    """Schema for customer initiating a return (D2C storefront)."""
    order_number: str
    phone: str  # For verification
    return_reason: ReturnReason
    return_reason_details: Optional[str] = None
    items: List[ReturnItemCreate]
    pickup_address: Optional[PickupAddress] = None


class CustomerReturnStatus(BaseResponseSchema):
    """Simplified return status for customers."""
    rma_number: str
    status: str
    status_message: str
    requested_at: datetime
    estimated_refund_date: Optional[datetime] = None
    refund_amount: Optional[Decimal] = None
    refund_status: Optional[str] = None
    tracking_number: Optional[str] = None
    courier: Optional[str] = None
    items: List[ReturnItemResponse] = []
    timeline: List[ReturnStatusHistoryResponse] = []
# ==================== Paginated Response ====================

class PaginatedReturnOrdersResponse(BaseModel):
    """Paginated response for return orders."""
    items: List[ReturnOrderListResponse]
    total: int
    page: int
    size: int
    pages: int


class PaginatedRefundsResponse(BaseModel):
    """Paginated response for refunds."""
    items: List[RefundListResponse]
    total: int
    page: int
    size: int
    pages: int
