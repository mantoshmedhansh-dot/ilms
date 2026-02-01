"""Pydantic schemas for Call Center CRM module."""
from datetime import datetime, date, time
from typing import Optional, List
from decimal import Decimal
from uuid import UUID
from pydantic import BaseModel, Field, ConfigDict, field_validator

from app.schemas.base import BaseResponseSchema

from app.models.call_center import (
    CallType, CallCategory, CallStatus, CallOutcome,
    CustomerSentiment, CallPriority, CallbackStatus, QAStatus
)


# ==================== CallDisposition Schemas ====================

class CallDispositionBase(BaseModel):
    """Base schema for CallDisposition."""
    code: str = Field(..., min_length=2, max_length=20)
    name: str = Field(..., min_length=2, max_length=100)
    description: Optional[str] = None
    category: CallCategory
    requires_callback: bool = False
    auto_create_ticket: bool = False
    auto_create_lead: bool = False
    requires_escalation: bool = False
    is_resolution: bool = False
    is_active: bool = True
    sort_order: int = 0


class CallDispositionCreate(CallDispositionBase):
    """Schema for creating CallDisposition."""
    pass


class CallDispositionUpdate(BaseModel):
    """Schema for updating CallDisposition."""
    name: Optional[str] = None
    description: Optional[str] = None
    requires_callback: Optional[bool] = None
    auto_create_ticket: Optional[bool] = None
    auto_create_lead: Optional[bool] = None
    requires_escalation: Optional[bool] = None
    is_resolution: Optional[bool] = None
    is_active: Optional[bool] = None
    sort_order: Optional[int] = None


class CallDispositionResponse(BaseResponseSchema):
    """Response schema for CallDisposition."""
    id: UUID
    created_at: datetime
    updated_at: datetime


class CallDispositionListResponse(BaseModel):
    """Paginated disposition list response."""
    items: List[CallDispositionResponse]
    total: int


# ==================== Call Schemas ====================

class CallBase(BaseModel):
    """Base schema for Call."""
    call_type: CallType
    category: CallCategory
    sub_category: Optional[str] = None
    customer_phone: str = Field(..., min_length=10, max_length=20)
    customer_name: Optional[str] = None
    customer_email: Optional[str] = None
    customer_address: Optional[str] = None
    customer_id: Optional[UUID] = None
    priority: CallPriority = CallPriority.NORMAL
    call_reason: Optional[str] = None
    product_id: Optional[UUID] = None
    serial_number: Optional[str] = None


class CallCreate(CallBase):
    """Schema for creating/logging a call."""
    call_start_time: Optional[datetime] = None  # Defaults to now
    linked_ticket_id: Optional[UUID] = None
    linked_order_id: Optional[UUID] = None
    campaign_id: Optional[UUID] = None


class CallUpdate(BaseModel):
    """Schema for updating a call."""
    category: Optional[CallCategory] = None
    sub_category: Optional[str] = None
    priority: Optional[CallPriority] = None
    sentiment: Optional[CustomerSentiment] = None
    urgency_level: Optional[int] = Field(None, ge=1, le=5)
    call_notes: Optional[str] = None
    resolution_notes: Optional[str] = None
    internal_notes: Optional[str] = None
    product_id: Optional[UUID] = None
    serial_number: Optional[str] = None


class CallCompleteRequest(BaseModel):
    """Request to complete/end a call."""
    outcome: CallOutcome
    disposition_id: Optional[UUID] = None
    call_notes: Optional[str] = None
    resolution_notes: Optional[str] = None
    sentiment: Optional[CustomerSentiment] = None
    is_resolved_first_call: bool = False
    follow_up_required: bool = False
    consent_confirmed: bool = False
    disclosure_read: bool = False
    # Auto-create options
    create_ticket: bool = False
    ticket_details: Optional[dict] = None
    create_callback: bool = False
    callback_datetime: Optional[datetime] = None
    callback_reason: Optional[str] = None


class CallTransferRequest(BaseModel):
    """Request to transfer a call."""
    transfer_to_agent_id: UUID
    transfer_reason: str = Field(..., min_length=5, max_length=200)
    notes: Optional[str] = None


class CallResponse(BaseResponseSchema):
    """Response schema for Call."""
    id: UUID
    call_id: str
    call_type: CallType
    category: str
    sub_category: Optional[str] = None

    # Customer
    customer_id: Optional[UUID] = None
    customer_name: Optional[str] = None
    customer_phone: str
    customer_email: Optional[str] = None

    # Agent
    agent_id: UUID
    agent_name: Optional[str] = None

    # Timing
    call_start_time: datetime
    call_end_time: Optional[datetime] = None
    duration_seconds: Optional[int] = None
    hold_time_seconds: int = 0
    talk_time_seconds: Optional[int] = None

    # Status
    status: str
    outcome: Optional[CallOutcome] = None
    disposition_id: Optional[UUID] = None
    disposition_name: Optional[str] = None

    # Priority & Sentiment
    priority: str
    sentiment: Optional[CustomerSentiment] = None
    urgency_level: int = 1

    # Notes
    call_reason: Optional[str] = None
    call_notes: Optional[str] = None
    resolution_notes: Optional[str] = None

    # Linked Records
    linked_ticket_id: Optional[UUID] = None
    linked_lead_id: Optional[UUID] = None
    linked_order_id: Optional[UUID] = None

    # Product
    product_id: Optional[UUID] = None
    serial_number: Optional[str] = None

    # FCR
    is_first_contact: bool = True
    is_resolved_first_call: bool = False
    follow_up_required: bool = False

    # Recording
    recording_url: Optional[str] = None

    # Timestamps
    created_at: datetime
    updated_at: datetime


class CallDetailResponse(CallResponse):
    """Detailed call response with related data."""
    customer: Optional[dict] = None
    agent: Optional[dict] = None
    disposition: Optional[CallDispositionResponse] = None
    linked_ticket: Optional[dict] = None
    callbacks: List["CallbackResponse"] = []
    qa_reviews: List["CallQAReviewResponse"] = []


class CallListResponse(BaseModel):
    """Paginated call list response."""
    items: List[CallResponse]
    total: int
    page: int = 1
    size: int = 50
    pages: int = 1


# ==================== Callback Schemas ====================

class CallbackBase(BaseModel):
    """Base schema for CallbackSchedule."""
    customer_phone: str = Field(..., min_length=10, max_length=20)
    customer_name: str = Field(..., min_length=2, max_length=200)
    customer_id: Optional[UUID] = None
    scheduled_datetime: datetime
    reason: str = Field(..., min_length=5, max_length=500)
    category: CallCategory
    priority: CallPriority = CallPriority.NORMAL
    notes: Optional[str] = None
    time_window_start: Optional[time] = None
    time_window_end: Optional[time] = None


class CallbackCreate(CallbackBase):
    """Schema for creating a callback."""
    call_id: Optional[UUID] = None
    assigned_agent_id: Optional[UUID] = None  # Defaults to current user
    max_attempts: int = Field(3, ge=1, le=10)


class CallbackUpdate(BaseModel):
    """Schema for updating a callback."""
    scheduled_datetime: Optional[datetime] = None
    reason: Optional[str] = None
    priority: Optional[CallPriority] = None
    notes: Optional[str] = None
    assigned_agent_id: Optional[UUID] = None
    time_window_start: Optional[time] = None
    time_window_end: Optional[time] = None


class CallbackCompleteRequest(BaseModel):
    """Request to mark callback as completed."""
    completed_call_id: Optional[UUID] = None
    completion_notes: Optional[str] = None
    outcome: str = Field(..., description="Outcome of the callback")


class CallbackRescheduleRequest(BaseModel):
    """Request to reschedule a callback."""
    new_datetime: datetime
    reason: str = Field(..., min_length=5, max_length=200)
    notes: Optional[str] = None


class CallbackResponse(BaseResponseSchema):
    """Response schema for CallbackSchedule."""
    id: UUID
    call_id: Optional[UUID] = None
    customer_id: Optional[UUID] = None
    customer_name: str
    customer_phone: str

    assigned_agent_id: UUID
    assigned_agent_name: Optional[str] = None
    created_by_id: UUID

    scheduled_date: date
    scheduled_datetime: datetime
    time_window_start: Optional[time] = None
    time_window_end: Optional[time] = None

    reason: str
    category: str
    priority: str
    notes: Optional[str] = None

    status: str
    attempt_count: int = 0
    max_attempts: int = 3
    last_attempt_at: Optional[datetime] = None

    completed_at: Optional[datetime] = None
    completion_notes: Optional[str] = None

    reschedule_count: int = 0
    reminder_sent: bool = False

    created_at: datetime
    updated_at: datetime


class CallbackListResponse(BaseModel):
    """Paginated callback list response."""
    items: List[CallbackResponse]
    total: int
    page: int = 1
    size: int = 50
    pages: int = 1
    # Summary counts
    scheduled_count: int = 0
    overdue_count: int = 0
    completed_today: int = 0


# ==================== Call QA Review Schemas ====================

class CallQAReviewBase(BaseModel):
    """Base schema for CallQAReview."""
    greeting_score: int = Field(..., ge=1, le=5)
    communication_score: int = Field(..., ge=1, le=5)
    product_knowledge_score: int = Field(..., ge=1, le=5)
    problem_solving_score: int = Field(..., ge=1, le=5)
    empathy_score: int = Field(..., ge=1, le=5)
    compliance_score: int = Field(..., ge=1, le=5)
    closing_score: int = Field(..., ge=1, le=5)
    strengths: Optional[str] = None
    areas_for_improvement: Optional[str] = None
    reviewer_comments: Optional[str] = None


class CallQAReviewCreate(CallQAReviewBase):
    """Schema for creating QA review."""
    call_id: UUID


class CallQAReviewUpdate(BaseModel):
    """Schema for updating QA review."""
    greeting_score: Optional[int] = Field(None, ge=1, le=5)
    communication_score: Optional[int] = Field(None, ge=1, le=5)
    product_knowledge_score: Optional[int] = Field(None, ge=1, le=5)
    problem_solving_score: Optional[int] = Field(None, ge=1, le=5)
    empathy_score: Optional[int] = Field(None, ge=1, le=5)
    compliance_score: Optional[int] = Field(None, ge=1, le=5)
    closing_score: Optional[int] = Field(None, ge=1, le=5)
    strengths: Optional[str] = None
    areas_for_improvement: Optional[str] = None
    reviewer_comments: Optional[str] = None


class CallQAReviewResponse(BaseResponseSchema):
    """Response schema for CallQAReview."""
    id: UUID
    call_id: UUID
    reviewer_id: UUID
    reviewer_name: Optional[str] = None

    # Scores
    greeting_score: int
    communication_score: int
    product_knowledge_score: int
    problem_solving_score: int
    empathy_score: int
    compliance_score: int
    closing_score: int

    overall_score: Decimal
    total_points: int
    max_points: int = 35

    # Feedback
    strengths: Optional[str] = None
    areas_for_improvement: Optional[str] = None
    reviewer_comments: Optional[str] = None

    # Status
    status: str
    acknowledged_by_agent: bool = False
    acknowledged_at: Optional[datetime] = None
    agent_comments: Optional[str] = None

    # Dispute
    is_disputed: bool = False
    dispute_reason: Optional[str] = None

    reviewed_at: datetime
    created_at: datetime


class AgentAcknowledgeRequest(BaseModel):
    """Agent acknowledges QA review."""
    comments: Optional[str] = None


class QADisputeRequest(BaseModel):
    """Agent disputes QA review."""
    reason: str = Field(..., min_length=10, max_length=500)


# ==================== Dashboard & Report Schemas ====================

class AgentDashboardResponse(BaseModel):
    """Agent dashboard metrics."""
    agent_id: UUID
    agent_name: str
    date: date

    # Today's Stats
    total_calls_today: int = 0
    inbound_calls: int = 0
    outbound_calls: int = 0
    resolved_calls: int = 0
    pending_callbacks: int = 0
    overdue_callbacks: int = 0

    # Performance
    avg_handle_time_seconds: int = 0
    avg_talk_time_seconds: int = 0
    fcr_rate: Decimal = Decimal("0")
    csat_avg: Optional[Decimal] = None

    # QA
    qa_score_avg: Optional[Decimal] = None
    reviews_pending_acknowledgment: int = 0


class CallCenterDashboardResponse(BaseModel):
    """Call center overall dashboard."""
    date: date

    # Volume
    total_calls_today: int = 0
    inbound_calls: int = 0
    outbound_calls: int = 0
    calls_in_progress: int = 0

    # Resolution
    resolved_calls: int = 0
    tickets_created: int = 0
    leads_created: int = 0
    escalated_calls: int = 0

    # Callbacks
    callbacks_scheduled: int = 0
    callbacks_completed: int = 0
    callbacks_overdue: int = 0

    # Performance
    avg_handle_time_seconds: int = 0
    avg_wait_time_seconds: int = 0
    fcr_rate: Decimal = Decimal("0")
    abandonment_rate: Decimal = Decimal("0")

    # By Category
    calls_by_category: dict = {}
    calls_by_outcome: dict = {}

    # Agent Stats
    agents_active: int = 0
    agents_on_call: int = 0


class FCRReportRequest(BaseModel):
    """Request for FCR report."""
    start_date: date
    end_date: date
    agent_id: Optional[UUID] = None
    category: Optional[CallCategory] = None


class FCRReportResponse(BaseModel):
    """First Call Resolution report."""
    start_date: date
    end_date: date
    total_calls: int = 0
    first_contact_calls: int = 0
    resolved_first_call: int = 0
    fcr_rate: Decimal = Decimal("0")
    fcr_by_category: dict = {}
    fcr_by_agent: List[dict] = []


class AHTReportRequest(BaseModel):
    """Request for AHT report."""
    start_date: date
    end_date: date
    agent_id: Optional[UUID] = None
    category: Optional[CallCategory] = None


class AHTReportResponse(BaseModel):
    """Average Handle Time report."""
    start_date: date
    end_date: date
    total_calls: int = 0
    total_talk_time_seconds: int = 0
    total_hold_time_seconds: int = 0
    avg_handle_time_seconds: int = 0
    avg_talk_time_seconds: int = 0
    avg_hold_time_seconds: int = 0
    aht_by_category: dict = {}
    aht_by_agent: List[dict] = []


class CallVolumeReportResponse(BaseModel):
    """Call volume report."""
    start_date: date
    end_date: date
    total_calls: int = 0
    inbound_calls: int = 0
    outbound_calls: int = 0
    by_date: List[dict] = []
    by_hour: List[dict] = []
    by_category: dict = {}
    by_disposition: dict = {}
