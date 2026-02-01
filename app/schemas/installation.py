"""Installation and Warranty schemas for API requests/responses."""
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime, date
import uuid

from app.models.installation import InstallationStatus
from app.schemas.customer import CustomerBrief
from app.schemas.base import BaseResponseSchema


# ==================== INSTALLATION SCHEMAS ====================

class InstallationCreate(BaseModel):
    """Installation creation schema."""
    customer_id: uuid.UUID
    order_id: Optional[uuid.UUID] = None
    order_item_id: Optional[uuid.UUID] = None
    product_id: uuid.UUID
    variant_id: Optional[uuid.UUID] = None
    serial_number: Optional[str] = None
    stock_item_id: Optional[uuid.UUID] = None
    address_id: Optional[uuid.UUID] = None
    installation_address: Optional[dict] = None
    installation_pincode: Optional[str] = None
    preferred_date: Optional[date] = None
    preferred_time_slot: Optional[str] = None
    region_id: Optional[uuid.UUID] = None
    notes: Optional[str] = None


class InstallationUpdate(BaseModel):
    """Installation update schema."""
    address_id: Optional[uuid.UUID] = None
    installation_address: Optional[dict] = None
    scheduled_date: Optional[date] = None
    scheduled_time_slot: Optional[str] = None
    notes: Optional[str] = None
    internal_notes: Optional[str] = None


class InstallationAssignment(BaseModel):
    """Assign technician to installation."""
    technician_id: uuid.UUID
    scheduled_date: Optional[date] = None
    scheduled_time_slot: Optional[str] = None


class InstallationCompletion(BaseModel):
    """Installation completion data."""
    installation_date: date
    installation_notes: Optional[str] = None
    pre_installation_checklist: Optional[List[dict]] = None
    post_installation_checklist: Optional[List[dict]] = None
    installation_photos: Optional[List[str]] = None
    accessories_used: Optional[List[dict]] = None
    input_tds: Optional[int] = None
    output_tds: Optional[int] = None
    warranty_months: int = 12
    extended_warranty_months: int = 0
    demo_given: bool = False
    demo_notes: Optional[str] = None
    customer_signature_url: Optional[str] = None
    customer_feedback: Optional[str] = None
    customer_rating: Optional[int] = Field(None, ge=1, le=5)


class InstallationResponse(BaseResponseSchema):
    """Installation response schema."""
    id: uuid.UUID
    installation_number: str
    status: str
    customer: CustomerBrief
    product_id: uuid.UUID
    serial_number: Optional[str] = None
    installation_pincode: Optional[str] = None
    installation_city: Optional[str] = None
    technician_id: Optional[uuid.UUID] = None
    scheduled_date: Optional[date] = None
    scheduled_time_slot: Optional[str] = None
    installation_date: Optional[date] = None
    warranty_start_date: Optional[date] = None
    warranty_end_date: Optional[date] = None
    is_under_warranty: bool
    warranty_days_remaining: int
    customer_rating: Optional[int] = None
    created_at: datetime
    updated_at: datetime

class InstallationDetail(InstallationResponse):
    """Detailed installation response."""
    order_id: Optional[uuid.UUID] = None
    variant_id: Optional[uuid.UUID] = None
    stock_item_id: Optional[uuid.UUID] = None
    address_id: Optional[uuid.UUID] = None
    installation_address: Optional[dict] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    preferred_date: Optional[date] = None
    preferred_time_slot: Optional[str] = None
    assigned_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    installation_notes: Optional[str] = None
    pre_installation_checklist: Optional[List[dict]] = None
    post_installation_checklist: Optional[List[dict]] = None
    installation_photos: Optional[List[str]] = None
    accessories_used: Optional[List[dict]] = None
    input_tds: Optional[int] = None
    output_tds: Optional[int] = None
    warranty_months: int
    extended_warranty_months: int
    warranty_card_number: Optional[str] = None
    warranty_card_url: Optional[str] = None
    customer_signature_url: Optional[str] = None
    customer_feedback: Optional[str] = None
    demo_given: bool
    demo_notes: Optional[str] = None
    notes: Optional[str] = None
    product_name: Optional[str] = None
    technician_name: Optional[str] = None


class InstallationListResponse(BaseModel):
    """Paginated installation list."""
    items: List[InstallationResponse]
    total: int
    page: int
    size: int
    pages: int


# ==================== ENDPOINT-SPECIFIC SCHEMAS ====================

class InstallationBase(BaseModel):
    """Base installation schema for endpoint."""
    customer_id: uuid.UUID
    order_id: Optional[uuid.UUID] = None
    product_id: uuid.UUID
    serial_number: Optional[str] = None
    installation_pincode: str
    installation_city: Optional[str] = None
    installation_address: Optional[dict] = None
    preferred_date: Optional[date] = None
    preferred_time_slot: Optional[str] = None
    notes: Optional[str] = None


class InstallationScheduleRequest(BaseModel):
    """Schedule installation request."""
    scheduled_date: date
    scheduled_time_slot: str
    technician_id: Optional[uuid.UUID] = None
    notes: Optional[str] = None


class InstallationAssignRequest(BaseModel):
    """Assign technician request."""
    technician_id: uuid.UUID


class InstallationCompleteRequest(BaseModel):
    """Complete installation request."""
    installation_notes: Optional[str] = None
    pre_installation_checklist: Optional[dict] = None
    post_installation_checklist: Optional[dict] = None
    installation_photos: Optional[list] = None
    accessories_used: Optional[list] = None
    input_tds: Optional[int] = None
    output_tds: Optional[int] = None
    customer_signature_url: Optional[str] = None
    customer_feedback: Optional[str] = None
    customer_rating: Optional[int] = Field(None, ge=1, le=5)
    demo_given: bool = True
    demo_notes: Optional[str] = None
    warranty_months: int = 12


class InstallationEndpointResponse(BaseResponseSchema):
    """Installation response schema for endpoint."""
    model_config = {"from_attributes": True}

    id: uuid.UUID
    installation_number: str
    status: str
    customer_id: uuid.UUID
    order_id: Optional[uuid.UUID] = None
    product_id: uuid.UUID
    serial_number: Optional[str] = None
    installation_pincode: Optional[str] = None
    installation_city: Optional[str] = None
    installation_address: Optional[dict] = None
    preferred_date: Optional[date] = None
    preferred_time_slot: Optional[str] = None
    scheduled_date: Optional[date] = None
    scheduled_time_slot: Optional[str] = None
    technician_id: Optional[uuid.UUID] = None
    assigned_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    installation_date: Optional[date] = None
    warranty_start_date: Optional[date] = None
    warranty_end_date: Optional[date] = None
    warranty_card_number: Optional[str] = None
    customer_rating: Optional[int] = None
    notes: Optional[str] = None
    created_at: Optional[datetime] = None


class InstallationEndpointDetailResponse(InstallationEndpointResponse):
    """Detailed installation response for endpoint."""
    customer_name: Optional[str] = None
    product_name: Optional[str] = None
    technician_name: Optional[str] = None
    order_number: Optional[str] = None
    installation_notes: Optional[str] = None
    input_tds: Optional[int] = None
    output_tds: Optional[int] = None
    demo_given: Optional[bool] = None
    demo_notes: Optional[str] = None
    customer_feedback: Optional[str] = None


class InstallationEndpointListResponse(BaseModel):
    """Paginated installation list for endpoint."""
    items: List[InstallationEndpointResponse]
    total: int
    page: int
    size: int
    pages: int


class InstallationDashboardResponse(BaseModel):
    """Installation dashboard stats."""
    total_pending: int
    total_scheduled: int
    total_in_progress: int
    total_completed_today: int
    total_completed_week: int
    total_completed_month: int
    avg_completion_days: float
    avg_customer_rating: float
    pending_assignments: int


class InstallationWarrantyStatusResponse(BaseModel):
    """Warranty status response."""
    installation_id: uuid.UUID
    installation_number: str
    serial_number: Optional[str] = None
    warranty_card_number: Optional[str] = None
    warranty_start_date: Optional[date] = None
    warranty_end_date: Optional[date] = None
    warranty_months: Optional[int] = None
    extended_warranty_months: Optional[int] = None
    is_under_warranty: bool
    days_remaining: int


class InstallationWarrantyExtendResponse(BaseModel):
    """Warranty extension response."""
    success: bool
    installation_id: uuid.UUID
    new_warranty_end_date: date
    total_warranty_months: int
    message: str


class InstallationWarrantyLookupResponse(BaseModel):
    """Warranty lookup response."""
    installation_id: uuid.UUID
    installation_number: str
    serial_number: Optional[str] = None
    product_name: Optional[str] = None
    customer_name: Optional[str] = None
    warranty_start_date: Optional[date] = None
    warranty_end_date: Optional[date] = None
    is_under_warranty: bool
    days_remaining: int


# ==================== WARRANTY CLAIM SCHEMAS ====================

class WarrantyClaimCreate(BaseModel):
    """Warranty claim creation schema."""
    installation_id: uuid.UUID
    customer_id: uuid.UUID
    product_id: uuid.UUID
    serial_number: str = Field(
        ...,
        min_length=1,
        description="Serial number of the product. Required to validate warranty and track product lifecycle."
    )
    claim_type: str  # repair, replacement, refund
    issue_description: str = Field(..., min_length=10)


class WarrantyClaimUpdate(BaseModel):
    """Warranty claim update schema."""
    diagnosis: Optional[str] = None
    notes: Optional[str] = None


class WarrantyClaimApproval(BaseModel):
    """Warranty claim approval/rejection."""
    is_valid_claim: bool
    rejection_reason: Optional[str] = None
    notes: Optional[str] = None


class WarrantyClaimResolution(BaseModel):
    """Warranty claim resolution data."""
    resolution_type: str  # repaired, replaced, refunded
    resolution_notes: Optional[str] = None
    replacement_serial: Optional[str] = None
    refund_amount: Optional[float] = None
    parts_cost: float = 0
    labor_cost: float = 0


class WarrantyClaimResponse(BaseResponseSchema):
    """Warranty claim response schema."""
    id: uuid.UUID
    claim_number: str
    installation_id: uuid.UUID
    service_request_id: Optional[uuid.UUID] = None
    customer_id: uuid.UUID
    product_id: uuid.UUID
    serial_number: str  # Required - links warranty to specific product unit
    claim_type: str
    issue_description: str
    diagnosis: Optional[str] = None
    status: str
    is_valid_claim: Optional[bool] = None
    rejection_reason: Optional[str] = None
    resolution_type: Optional[str] = None
    resolution_notes: Optional[str] = None
    replacement_serial: Optional[str] = None
    refund_amount: Optional[float] = None
    total_cost: float
    claim_date: Optional[date] = None
    resolved_date: Optional[date] = None
    created_at: datetime
    updated_at: datetime

class WarrantyClaimListResponse(BaseModel):
    """Paginated warranty claim list."""
    items: List[WarrantyClaimResponse]
    total: int
    page: int
    size: int
    pages: int
