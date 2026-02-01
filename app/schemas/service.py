"""Service Request schemas for API requests/responses."""
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime, date
import uuid

from app.models.service_request import ServiceType, ServicePriority, ServiceStatus, ServiceSource
from app.schemas.customer import CustomerBrief
from app.schemas.base import BaseResponseSchema


# ==================== SERVICE REQUEST SCHEMAS ====================

class ServiceRequestCreate(BaseModel):
    """Service request creation schema."""
    service_type: ServiceType
    priority: ServicePriority = ServicePriority.NORMAL
    source: ServiceSource = ServiceSource.CALL_CENTER
    customer_id: uuid.UUID
    customer_address_id: Optional[uuid.UUID] = None
    order_id: Optional[uuid.UUID] = None
    product_id: Optional[uuid.UUID] = None
    serial_number: Optional[str] = None
    installation_id: Optional[uuid.UUID] = None
    amc_id: Optional[uuid.UUID] = None
    title: str = Field(..., max_length=255)
    description: Optional[str] = None
    symptoms: Optional[List[str]] = None
    customer_reported_issue: Optional[str] = None
    service_address: Optional[dict] = None
    service_pincode: Optional[str] = None
    preferred_date: Optional[date] = None
    preferred_time_slot: Optional[str] = None
    region_id: Optional[uuid.UUID] = None
    internal_notes: Optional[str] = None


class ServiceRequestUpdate(BaseModel):
    """Service request update schema."""
    priority: Optional[ServicePriority] = None
    title: Optional[str] = None
    description: Optional[str] = None
    symptoms: Optional[List[str]] = None
    scheduled_date: Optional[date] = None
    scheduled_time_slot: Optional[str] = None
    internal_notes: Optional[str] = None


class ServiceStatusUpdate(BaseModel):
    """Service status update schema."""
    status: ServiceStatus
    notes: Optional[str] = None


class TechnicianAssignment(BaseModel):
    """Assign technician to service request."""
    technician_id: uuid.UUID
    scheduled_date: Optional[date] = None
    scheduled_time_slot: Optional[str] = None
    notes: Optional[str] = None


class ServiceCompletion(BaseModel):
    """Service completion data."""
    resolution_type: str  # repaired, replaced, no_issue_found, etc.
    resolution_notes: Optional[str] = None
    root_cause: Optional[str] = None
    action_taken: Optional[str] = None
    parts_used: Optional[List[dict]] = None  # [{"part_id": "", "quantity": 1}]
    labor_charges: float = 0
    service_charges: float = 0
    travel_charges: float = 0
    is_chargeable: bool = False
    payment_collected: float = 0
    payment_mode: Optional[str] = None
    images_before: Optional[List[str]] = None
    images_after: Optional[List[str]] = None
    customer_signature_url: Optional[str] = None


class ServiceFeedback(BaseModel):
    """Customer feedback for service."""
    rating: int = Field(..., ge=1, le=5)
    feedback: Optional[str] = None


class ServiceRequestResponse(BaseResponseSchema):
    """Service request response schema."""
    id: uuid.UUID
    ticket_number: str
    service_type: str  # VARCHAR in DB
    source: str
    priority: str
    status: str
    customer: CustomerBrief
    product_id: Optional[uuid.UUID] = None
    serial_number: Optional[str] = None
    title: str
    description: Optional[str] = None
    service_pincode: Optional[str] = None
    service_city: Optional[str] = None
    technician_id: Optional[uuid.UUID] = None
    scheduled_date: Optional[date] = None
    scheduled_time_slot: Optional[str] = None
    is_sla_breached: bool
    customer_rating: Optional[int] = None
    total_charges: float
    created_at: datetime
    updated_at: datetime

class ServiceRequestDetail(ServiceRequestResponse):
    """Detailed service request response."""
    customer_address_id: Optional[uuid.UUID] = None
    order_id: Optional[uuid.UUID] = None
    installation_id: Optional[uuid.UUID] = None
    amc_id: Optional[uuid.UUID] = None
    symptoms: Optional[List[str]] = None
    customer_reported_issue: Optional[str] = None
    service_address: Optional[dict] = None
    preferred_date: Optional[date] = None
    preferred_time_slot: Optional[str] = None
    assigned_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    closed_at: Optional[datetime] = None
    resolution_type: Optional[str] = None
    resolution_notes: Optional[str] = None
    root_cause: Optional[str] = None
    action_taken: Optional[str] = None
    parts_used: Optional[List[dict]] = None
    total_parts_cost: float
    labor_charges: float
    service_charges: float
    travel_charges: float
    is_chargeable: bool
    payment_status: Optional[str] = None
    payment_collected: float
    customer_feedback: Optional[str] = None
    images_before: Optional[List[str]] = None
    images_after: Optional[List[str]] = None
    internal_notes: Optional[str] = None
    escalation_level: int
    product_name: Optional[str] = None
    technician_name: Optional[str] = None


class ServiceRequestListResponse(BaseModel):
    """Paginated service request list."""
    items: List[ServiceRequestResponse]
    total: int
    page: int
    size: int
    pages: int


class ServiceStatusHistoryResponse(BaseResponseSchema):
    """Service status history response."""
    id: uuid.UUID
    from_status: Optional[str] = None  # VARCHAR in DB
    to_status: str  # VARCHAR in DB
    changed_by: Optional[uuid.UUID] = None
    notes: Optional[str] = None
    created_at: datetime
# ==================== SERVICE STATS ====================

class ServiceStats(BaseModel):
    """Service statistics."""
    total_requests: int
    pending_requests: int
    assigned_requests: int
    in_progress_requests: int
    completed_today: int
    sla_breached: int
    average_resolution_time_hours: float
    average_rating: float
