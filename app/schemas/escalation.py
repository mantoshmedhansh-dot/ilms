"""Pydantic schemas for Escalation Management module."""
from datetime import datetime, date
from typing import Optional, List
from decimal import Decimal
from uuid import UUID
from pydantic import BaseModel, Field, ConfigDict

from app.schemas.base import BaseResponseSchema

from app.models.escalation import (
    EscalationLevel, EscalationStatus, EscalationPriority,
    EscalationSource, EscalationReason, NotificationChannel
)


# ==================== Escalation Matrix Schemas ====================

class EscalationMatrixBase(BaseModel):
    """Base schema for EscalationMatrix."""
    name: str = Field(..., min_length=2, max_length=100)
    description: Optional[str] = None
    source_type: EscalationSource
    category_id: Optional[UUID] = None
    priority: Optional[EscalationPriority] = None
    region_id: Optional[UUID] = None
    level: EscalationLevel
    trigger_after_minutes: int = Field(..., ge=0)
    response_sla_minutes: int = Field(..., ge=0)
    resolution_sla_minutes: int = Field(..., ge=0)
    notify_user_id: Optional[UUID] = None
    notify_role_id: Optional[UUID] = None
    assign_to_user_id: Optional[UUID] = None
    assign_to_role_id: Optional[UUID] = None
    additional_notify_emails: Optional[List[str]] = None
    notification_channels: Optional[List[NotificationChannel]] = None
    auto_escalate: bool = True
    auto_assign: bool = False
    require_acknowledgment: bool = True
    acknowledgment_sla_minutes: Optional[int] = None
    is_active: bool = True
    sort_order: int = 0


class EscalationMatrixCreate(EscalationMatrixBase):
    """Schema for creating EscalationMatrix."""
    pass


class EscalationMatrixUpdate(BaseModel):
    """Schema for updating EscalationMatrix."""
    name: Optional[str] = None
    description: Optional[str] = None
    trigger_after_minutes: Optional[int] = None
    response_sla_minutes: Optional[int] = None
    resolution_sla_minutes: Optional[int] = None
    notify_user_id: Optional[UUID] = None
    notify_role_id: Optional[UUID] = None
    assign_to_user_id: Optional[UUID] = None
    assign_to_role_id: Optional[UUID] = None
    additional_notify_emails: Optional[List[str]] = None
    notification_channels: Optional[List[NotificationChannel]] = None
    auto_escalate: Optional[bool] = None
    auto_assign: Optional[bool] = None
    require_acknowledgment: Optional[bool] = None
    acknowledgment_sla_minutes: Optional[int] = None
    is_active: Optional[bool] = None
    sort_order: Optional[int] = None


class EscalationMatrixResponse(BaseResponseSchema):
    """Response schema for EscalationMatrix."""
    id: UUID
    name: str
    description: Optional[str] = None
    source_type: EscalationSource
    category_id: Optional[UUID] = None
    priority: Optional[str] = None
    region_id: Optional[UUID] = None
    level: str
    trigger_after_minutes: int
    response_sla_minutes: int
    resolution_sla_minutes: int
    notify_user_id: Optional[UUID] = None
    assign_to_user_id: Optional[UUID] = None
    auto_escalate: bool
    auto_assign: bool
    require_acknowledgment: bool
    is_active: bool
    sort_order: int
    created_at: datetime


# ==================== Escalation Schemas ====================

class EscalationBase(BaseModel):
    """Base schema for Escalation."""
    source_type: EscalationSource
    source_id: Optional[UUID] = None
    source_reference: Optional[str] = None
    customer_id: Optional[UUID] = None
    customer_name: str = Field(..., min_length=2, max_length=200)
    customer_phone: str = Field(..., min_length=10, max_length=20)
    customer_email: Optional[str] = None
    subject: str = Field(..., min_length=5, max_length=255)
    description: str = Field(..., min_length=10)
    priority: EscalationPriority = EscalationPriority.MEDIUM
    reason: EscalationReason
    reason_details: Optional[str] = None
    product_id: Optional[UUID] = None
    category_id: Optional[UUID] = None
    region_id: Optional[UUID] = None
    dealer_id: Optional[UUID] = None
    tags: Optional[List[str]] = None


class EscalationCreate(EscalationBase):
    """Schema for creating an Escalation."""
    assigned_to_id: Optional[UUID] = None
    internal_notes: Optional[str] = None


class EscalationUpdate(BaseModel):
    """Schema for updating an Escalation."""
    subject: Optional[str] = None
    description: Optional[str] = None
    priority: Optional[EscalationPriority] = None
    internal_notes: Optional[str] = None
    tags: Optional[List[str]] = None


class EscalationAssignRequest(BaseModel):
    """Request to assign escalation."""
    assigned_to_id: UUID
    notes: Optional[str] = None


class EscalationEscalateRequest(BaseModel):
    """Request to escalate to next level."""
    reason: str = Field(..., min_length=5, max_length=500)
    notes: Optional[str] = None
    assign_to_id: Optional[UUID] = None


class EscalationDeEscalateRequest(BaseModel):
    """Request to de-escalate to lower level."""
    reason: str = Field(..., min_length=5, max_length=500)
    notes: Optional[str] = None


class EscalationAcknowledgeRequest(BaseModel):
    """Request to acknowledge escalation."""
    notes: Optional[str] = None


class EscalationResolveRequest(BaseModel):
    """Request to resolve escalation."""
    resolution_notes: str = Field(..., min_length=10)
    resolution_type: Optional[str] = None


class EscalationReopenRequest(BaseModel):
    """Request to reopen escalation."""
    reason: str = Field(..., min_length=10, max_length=500)


class EscalationFeedbackRequest(BaseModel):
    """Customer feedback on resolution."""
    satisfied: bool
    rating: int = Field(..., ge=1, le=5)
    feedback: Optional[str] = None


class EscalationResponse(BaseResponseSchema):
    """Response schema for Escalation."""
    id: UUID
    escalation_number: str
    source_type: EscalationSource
    source_id: Optional[UUID] = None
    source_reference: Optional[str] = None

    customer_id: Optional[UUID] = None
    customer_name: str
    customer_phone: str
    customer_email: Optional[str] = None

    subject: str
    description: str
    current_level: EscalationLevel
    priority: str
    reason: EscalationReason
    reason_details: Optional[str] = None

    status: str
    assigned_to_id: Optional[UUID] = None
    assigned_to_name: Optional[str] = None
    assigned_at: Optional[datetime] = None

    response_due_at: Optional[datetime] = None
    resolution_due_at: Optional[datetime] = None
    first_response_at: Optional[datetime] = None
    is_response_sla_breached: bool = False
    is_resolution_sla_breached: bool = False

    acknowledged_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None
    resolution_notes: Optional[str] = None

    reopen_count: int = 0

    product_id: Optional[UUID] = None
    category_id: Optional[UUID] = None

    created_at: datetime
    updated_at: datetime


class EscalationDetailResponse(EscalationResponse):
    """Detailed escalation response."""
    internal_notes: Optional[str] = None
    tags: Optional[List[str]] = None

    customer_satisfied: Optional[bool] = None
    satisfaction_rating: Optional[int] = None
    customer_feedback: Optional[str] = None

    history: List["EscalationHistoryResponse"] = []
    comments: List["EscalationCommentResponse"] = []


class EscalationListResponse(BaseModel):
    """Paginated escalation list."""
    items: List[EscalationResponse]
    total: int
    page: int = 1
    size: int = 50
    pages: int = 1


# ==================== Escalation History Schemas ====================

class EscalationHistoryResponse(BaseResponseSchema):
    """Response schema for EscalationHistory."""
    id: UUID
    escalation_id: UUID
    from_level: Optional[EscalationLevel] = None
    to_level: EscalationLevel
    from_status: Optional[EscalationStatus] = None
    to_status: EscalationStatus
    action: str
    reason: Optional[str] = None
    notes: Optional[str] = None
    is_auto: bool = False
    changed_by_id: UUID
    changed_by_name: Optional[str] = None
    changed_at: datetime


# ==================== Escalation Comment Schemas ====================

class EscalationCommentCreate(BaseModel):
    """Schema for creating comment."""
    comment: str = Field(..., min_length=2)
    is_internal: bool = True
    attachments: Optional[List[str]] = None


class EscalationCommentResponse(BaseResponseSchema):
    """Response schema for EscalationComment."""
    id: UUID
    escalation_id: UUID
    comment: str
    is_internal: bool
    is_system: bool
    attachments: Optional[List[str]] = None
    created_by_id: UUID
    created_by_name: Optional[str] = None
    created_at: datetime


# ==================== SLA Configuration Schemas ====================

class SLAConfigurationCreate(BaseModel):
    """Schema for creating SLA configuration."""
    name: str = Field(..., min_length=2, max_length=100)
    description: Optional[str] = None
    source_type: EscalationSource
    priority: EscalationPriority
    category_id: Optional[UUID] = None
    response_time_minutes: int = Field(..., ge=1)
    resolution_time_minutes: int = Field(..., ge=1)
    business_hours_only: bool = True
    business_start_hour: int = Field(9, ge=0, le=23)
    business_end_hour: int = Field(18, ge=0, le=23)
    exclude_weekends: bool = True
    exclude_holidays: bool = True
    penalty_percentage: Optional[Decimal] = None
    impact_score: int = Field(1, ge=1, le=10)
    is_active: bool = True


class SLAConfigurationResponse(BaseResponseSchema):
    """Response schema for SLA configuration."""
    id: UUID
    name: str
    description: Optional[str] = None
    source_type: EscalationSource
    priority: str
    category_id: Optional[UUID] = None
    response_time_minutes: int
    resolution_time_minutes: int
    business_hours_only: bool
    business_start_hour: int
    business_end_hour: int
    exclude_weekends: bool
    is_active: bool
    created_at: datetime


# ==================== Dashboard & Report Schemas ====================

class EscalationDashboardResponse(BaseModel):
    """Escalation dashboard metrics."""
    date: date

    # Volume
    total_escalations: int = 0
    open_escalations: int = 0
    new_today: int = 0
    resolved_today: int = 0

    # By Status
    by_status: dict = {}

    # By Level
    by_level: dict = {}

    # By Priority
    by_priority: dict = {}

    # SLA
    sla_breached_response: int = 0
    sla_breached_resolution: int = 0
    sla_compliance_rate: Decimal = Decimal("0")

    # Aging
    pending_acknowledgment: int = 0
    overdue_response: int = 0
    overdue_resolution: int = 0

    # Average times (in minutes)
    avg_response_time_minutes: int = 0
    avg_resolution_time_minutes: int = 0

    # By Source
    by_source: dict = {}


class EscalationAgingReportResponse(BaseModel):
    """Escalation aging report."""
    start_date: date
    end_date: date

    aging_buckets: List[dict] = []  # {bucket, count, percentage}
    # e.g., 0-24h, 24-48h, 48-72h, 72h+

    by_level: List[dict] = []
    by_priority: List[dict] = []


class SLAComplianceReportResponse(BaseModel):
    """SLA compliance report."""
    start_date: date
    end_date: date

    total_escalations: int = 0
    response_sla_met: int = 0
    response_sla_breached: int = 0
    resolution_sla_met: int = 0
    resolution_sla_breached: int = 0

    response_compliance_rate: Decimal = Decimal("0")
    resolution_compliance_rate: Decimal = Decimal("0")
    overall_compliance_rate: Decimal = Decimal("0")

    by_source: List[dict] = []
    by_priority: List[dict] = []
    by_agent: List[dict] = []


# Update forward references
EscalationDetailResponse.model_rebuild()
