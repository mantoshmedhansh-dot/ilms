"""Pydantic schemas for Franchisee CRM module."""
from datetime import datetime, date
from typing import Optional, List
from decimal import Decimal
from uuid import UUID
from pydantic import BaseModel, Field, ConfigDict, EmailStr

from app.schemas.base import BaseResponseSchema

# Note: Franchisee tables use VARCHAR(36) for IDs in production database
# - Response schemas use `str` for franchisee id/franchisee_id (matches DB VARCHAR)
# - Input schemas use `UUID` for franchisee_id (validated by Pydantic, then converted to str in endpoint)

from app.models.franchisee import (
    FranchiseeStatus, FranchiseeType, FranchiseeTier,
    ContractStatus, TerritoryStatus,
    TrainingStatus, TrainingType,
    SupportTicketStatus, SupportTicketPriority, SupportTicketCategory,
    AuditStatus, AuditType, AuditResult,
)


# ==================== Franchisee Schemas ====================

class FranchiseeBase(BaseModel):
    """Base schema for Franchisee."""
    name: str = Field(..., min_length=2, max_length=200)
    legal_name: Optional[str] = None
    franchisee_type: FranchiseeType = FranchiseeType.DEALER
    tier: FranchiseeTier = FranchiseeTier.STANDARD

    # Contact
    contact_person: str = Field(..., min_length=2, max_length=200)
    email: EmailStr
    phone: str = Field(..., min_length=10, max_length=20)
    alternate_phone: Optional[str] = None
    website: Optional[str] = None

    # Address
    address_line1: str = Field(..., min_length=5, max_length=500)
    address_line2: Optional[str] = None
    city: str = Field(..., min_length=2, max_length=100)
    state: str = Field(..., min_length=2, max_length=100)
    pincode: str = Field(..., min_length=5, max_length=10)
    country: str = "India"
    latitude: Optional[Decimal] = None
    longitude: Optional[Decimal] = None

    # Business Details
    gst_number: Optional[str] = None
    pan_number: Optional[str] = None
    cin_number: Optional[str] = None
    bank_name: Optional[str] = None
    bank_account_number: Optional[str] = None
    bank_ifsc: Optional[str] = None

    # Hierarchy
    parent_franchisee_id: Optional[UUID] = None
    region_id: Optional[UUID] = None

    # Commercial
    credit_limit: Decimal = Decimal("0")
    payment_terms_days: int = 30
    commission_rate: Decimal = Decimal("0")
    security_deposit: Decimal = Decimal("0")

    notes: Optional[str] = None


class FranchiseeCreate(FranchiseeBase):
    """Schema for creating Franchisee."""
    pass


class FranchiseeUpdate(BaseModel):
    """Schema for updating Franchisee."""
    name: Optional[str] = None
    legal_name: Optional[str] = None
    franchisee_type: Optional[FranchiseeType] = None
    tier: Optional[FranchiseeTier] = None
    status: Optional[FranchiseeStatus] = None

    contact_person: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    alternate_phone: Optional[str] = None
    website: Optional[str] = None

    address_line1: Optional[str] = None
    address_line2: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    pincode: Optional[str] = None

    gst_number: Optional[str] = None
    pan_number: Optional[str] = None
    bank_name: Optional[str] = None
    bank_account_number: Optional[str] = None
    bank_ifsc: Optional[str] = None

    parent_franchisee_id: Optional[UUID] = None
    region_id: Optional[UUID] = None
    account_manager_id: Optional[UUID] = None

    credit_limit: Optional[Decimal] = None
    payment_terms_days: Optional[int] = None
    commission_rate: Optional[Decimal] = None
    security_deposit: Optional[Decimal] = None

    notes: Optional[str] = None


class FranchiseeResponse(BaseResponseSchema):
    """Response schema for Franchisee."""
    id: str  # VARCHAR in production
    franchisee_code: str
    name: str
    legal_name: Optional[str] = None
    franchisee_type: FranchiseeType
    status: str
    tier: str

    contact_person: str
    email: str
    phone: str
    alternate_phone: Optional[str] = None

    address_line1: str
    city: str
    state: str
    pincode: str
    country: str

    gst_number: Optional[str] = None

    credit_limit: Decimal
    current_outstanding: Decimal
    commission_rate: Decimal

    total_orders: int
    total_revenue: Decimal
    customer_rating: Decimal
    compliance_score: Decimal

    activation_date: Optional[date] = None
    last_order_date: Optional[date] = None

    created_at: datetime
    updated_at: datetime


class FranchiseeDetailResponse(FranchiseeResponse):
    """Detailed franchisee response."""
    website: Optional[str] = None
    latitude: Optional[Decimal] = None
    longitude: Optional[Decimal] = None

    pan_number: Optional[str] = None
    cin_number: Optional[str] = None
    bank_name: Optional[str] = None
    bank_account_number: Optional[str] = None
    bank_ifsc: Optional[str] = None

    parent_franchisee_id: Optional[str] = None  # VARCHAR FK
    region_id: Optional[str] = None
    account_manager_id: Optional[str] = None

    payment_terms_days: int
    security_deposit: Decimal
    avg_monthly_revenue: Decimal

    application_date: Optional[date] = None
    approval_date: Optional[date] = None
    termination_date: Optional[date] = None
    last_audit_date: Optional[date] = None

    documents: Optional[dict] = None
    notes: Optional[str] = None


class FranchiseeListResponse(BaseModel):
    """Paginated franchisee list."""
    items: List[FranchiseeResponse]
    total: int
    page: int = 1
    size: int = 50
    pages: int = 1


class FranchiseeStatusUpdate(BaseModel):
    """Update franchisee status."""
    status: FranchiseeStatus
    reason: Optional[str] = None


class FranchiseeApproveRequest(BaseModel):
    """Approve franchisee application."""
    tier: Optional[FranchiseeTier] = None
    credit_limit: Optional[Decimal] = None
    commission_rate: Optional[Decimal] = None
    notes: Optional[str] = None


# ==================== Contract Schemas ====================

class FranchiseeContractBase(BaseModel):
    """Base schema for Contract."""
    contract_type: str = Field(..., min_length=2, max_length=50)
    start_date: date
    end_date: date
    auto_renewal: bool = False
    renewal_terms_days: int = 365
    notice_period_days: int = 90

    franchise_fee: Decimal = Decimal("0")
    royalty_percentage: Decimal = Decimal("0")
    marketing_fee_percentage: Decimal = Decimal("0")
    minimum_purchase_commitment: Decimal = Decimal("0")

    territory_exclusive: bool = False
    territory_description: Optional[str] = None

    document_url: Optional[str] = None
    notes: Optional[str] = None


class FranchiseeContractCreate(FranchiseeContractBase):
    """Schema for creating Contract."""
    franchisee_id: UUID


class FranchiseeContractUpdate(BaseModel):
    """Schema for updating Contract."""
    end_date: Optional[date] = None
    auto_renewal: Optional[bool] = None
    renewal_terms_days: Optional[int] = None
    notice_period_days: Optional[int] = None

    franchise_fee: Optional[Decimal] = None
    royalty_percentage: Optional[Decimal] = None
    marketing_fee_percentage: Optional[Decimal] = None
    minimum_purchase_commitment: Optional[Decimal] = None

    territory_exclusive: Optional[bool] = None
    territory_description: Optional[str] = None

    document_url: Optional[str] = None
    signed_document_url: Optional[str] = None
    notes: Optional[str] = None


class FranchiseeContractResponse(BaseResponseSchema):
    """Response schema for Contract."""
    id: str  # VARCHAR in production
    franchisee_id: str  # VARCHAR FK
    contract_number: str
    contract_type: str
    status: str

    start_date: date
    end_date: date
    auto_renewal: bool

    franchise_fee: Decimal
    royalty_percentage: Decimal
    minimum_purchase_commitment: Decimal

    territory_exclusive: bool
    document_url: Optional[str] = None
    signed_document_url: Optional[str] = None

    approved_at: Optional[datetime] = None
    created_at: datetime


class ContractApproveRequest(BaseModel):
    """Approve contract."""
    notes: Optional[str] = None


class ContractTerminateRequest(BaseModel):
    """Terminate contract."""
    reason: str = Field(..., min_length=10)


# ==================== Territory Schemas ====================

class FranchiseeTerritoryBase(BaseModel):
    """Base schema for Territory."""
    territory_name: str = Field(..., min_length=2, max_length=200)
    territory_type: str = Field(..., min_length=2, max_length=50)
    is_exclusive: bool = False

    pincodes: Optional[List[str]] = None
    cities: Optional[List[str]] = None
    districts: Optional[List[str]] = None
    states: Optional[List[str]] = None
    geo_boundary: Optional[dict] = None

    effective_from: date
    effective_to: Optional[date] = None

    notes: Optional[str] = None


class FranchiseeTerritoryCreate(FranchiseeTerritoryBase):
    """Schema for creating Territory."""
    franchisee_id: UUID


class FranchiseeTerritoryUpdate(BaseModel):
    """Schema for updating Territory."""
    territory_name: Optional[str] = None
    is_exclusive: Optional[bool] = None
    status: Optional[TerritoryStatus] = None

    pincodes: Optional[List[str]] = None
    cities: Optional[List[str]] = None
    districts: Optional[List[str]] = None
    states: Optional[List[str]] = None

    effective_to: Optional[date] = None
    notes: Optional[str] = None


class FranchiseeTerritoryResponse(BaseResponseSchema):
    """Response schema for Territory."""
    id: str  # VARCHAR in production
    franchisee_id: str  # VARCHAR FK
    territory_name: str
    territory_type: str
    status: str
    is_exclusive: bool

    pincodes: Optional[List[str]] = None
    cities: Optional[List[str]] = None
    districts: Optional[List[str]] = None
    states: Optional[List[str]] = None

    effective_from: date
    effective_to: Optional[date] = None

    total_customers: int
    total_orders: int
    total_revenue: Decimal

    created_at: datetime


# ==================== Performance Schemas ====================

class FranchiseePerformanceCreate(BaseModel):
    """Schema for creating Performance record."""
    franchisee_id: UUID
    period_type: str = "MONTHLY"
    period_start: date
    period_end: date

    total_orders: int = 0
    total_units_sold: int = 0
    gross_revenue: Decimal = Decimal("0")
    net_revenue: Decimal = Decimal("0")
    returns_value: Decimal = Decimal("0")

    target_revenue: Decimal = Decimal("0")
    target_orders: int = 0

    new_customers: int = 0
    repeat_customers: int = 0
    customer_complaints: int = 0
    avg_customer_rating: Decimal = Decimal("0")

    installations_completed: int = 0
    service_calls_handled: int = 0

    commission_earned: Decimal = Decimal("0")
    incentives_earned: Decimal = Decimal("0")
    penalties_applied: Decimal = Decimal("0")


class FranchiseePerformanceResponse(BaseResponseSchema):
    """Response schema for Performance."""
    id: str  # VARCHAR in production
    franchisee_id: str  # VARCHAR FK
    period_type: str
    period_start: date
    period_end: date

    total_orders: int
    total_units_sold: int
    gross_revenue: Decimal
    net_revenue: Decimal

    target_revenue: Decimal
    target_orders: int
    target_achievement_percentage: Decimal

    new_customers: int
    repeat_customers: int
    avg_customer_rating: Decimal

    overall_score: Decimal
    sales_score: Decimal
    service_score: Decimal
    compliance_score: Decimal

    rank_in_region: Optional[int] = None
    rank_overall: Optional[int] = None

    commission_earned: Decimal
    incentives_earned: Decimal


# ==================== Training Schemas ====================

class FranchiseeTrainingBase(BaseModel):
    """Base schema for Training."""
    training_name: str = Field(..., min_length=2, max_length=200)
    training_type: TrainingType
    description: Optional[str] = None
    objectives: Optional[List[str]] = None

    scheduled_date: date
    start_time: Optional[str] = None
    duration_hours: Decimal = Decimal("1")

    mode: str = "ONLINE"
    location: Optional[str] = None
    meeting_link: Optional[str] = None

    attendee_name: str = Field(..., min_length=2, max_length=200)
    attendee_email: Optional[str] = None
    attendee_phone: Optional[str] = None

    has_assessment: bool = False
    passing_score: Decimal = Decimal("70")

    trainer_name: Optional[str] = None
    trainer_id: Optional[UUID] = None

    notes: Optional[str] = None


class FranchiseeTrainingCreate(FranchiseeTrainingBase):
    """Schema for creating Training."""
    franchisee_id: UUID


class FranchiseeTrainingUpdate(BaseModel):
    """Schema for updating Training."""
    training_name: Optional[str] = None
    description: Optional[str] = None
    status: Optional[TrainingStatus] = None

    scheduled_date: Optional[date] = None
    start_time: Optional[str] = None
    duration_hours: Optional[Decimal] = None

    mode: Optional[str] = None
    location: Optional[str] = None
    meeting_link: Optional[str] = None

    trainer_name: Optional[str] = None
    trainer_id: Optional[UUID] = None

    notes: Optional[str] = None


class FranchiseeTrainingResponse(BaseResponseSchema):
    """Response schema for Training."""
    id: str  # VARCHAR in production
    franchisee_id: str  # VARCHAR FK
    training_code: str
    training_name: str
    training_type: TrainingType
    status: str

    scheduled_date: date
    duration_hours: Decimal
    mode: str

    attendee_name: str
    attended: bool
    attendance_percentage: Decimal

    has_assessment: bool
    assessment_score: Optional[Decimal] = None
    passing_score: Decimal
    passed: bool

    certificate_issued: bool
    certificate_number: Optional[str] = None
    certificate_expiry: Optional[date] = None

    completed_at: Optional[datetime] = None
    created_at: datetime


class TrainingCompleteRequest(BaseModel):
    """Complete training."""
    attended: bool = True
    attendance_percentage: Decimal = Decimal("100")
    assessment_score: Optional[Decimal] = None
    feedback: Optional[str] = None
    feedback_rating: Optional[int] = Field(None, ge=1, le=5)


class TrainingCertificateRequest(BaseModel):
    """Issue certificate."""
    certificate_expiry: Optional[date] = None


# ==================== Support Ticket Schemas ====================

class FranchiseeSupportBase(BaseModel):
    """Base schema for Support Ticket."""
    subject: str = Field(..., min_length=5, max_length=500)
    description: str = Field(..., min_length=10)
    category: SupportTicketCategory
    priority: SupportTicketPriority = SupportTicketPriority.MEDIUM

    contact_name: str = Field(..., min_length=2, max_length=200)
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None

    attachments: Optional[List[str]] = None


class FranchiseeSupportCreate(FranchiseeSupportBase):
    """Schema for creating Support Ticket."""
    franchisee_id: UUID


class FranchiseeSupportUpdate(BaseModel):
    """Schema for updating Support Ticket."""
    subject: Optional[str] = None
    description: Optional[str] = None
    category: Optional[SupportTicketCategory] = None
    priority: Optional[SupportTicketPriority] = None
    attachments: Optional[List[str]] = None


class FranchiseeSupportResponse(BaseResponseSchema):
    """Response schema for Support Ticket."""
    id: str  # VARCHAR in production
    franchisee_id: str  # VARCHAR FK
    ticket_number: str
    subject: str
    description: str

    category: str
    priority: str
    status: str

    contact_name: str
    contact_email: Optional[str] = None

    assigned_to_id: Optional[str] = None
    assigned_at: Optional[datetime] = None

    sla_due_at: Optional[datetime] = None
    sla_breached: bool

    resolution: Optional[str] = None
    resolved_at: Optional[datetime] = None
    resolution_time_hours: Optional[Decimal] = None

    is_escalated: bool
    reopen_count: int

    satisfaction_rating: Optional[int] = None

    created_at: datetime
    updated_at: datetime


class FranchiseeSupportListResponse(BaseModel):
    """Paginated support ticket list."""
    items: List[FranchiseeSupportResponse]
    total: int
    page: int = 1
    size: int = 50
    pages: int = 1


class SupportAssignRequest(BaseModel):
    """Assign support ticket."""
    assigned_to_id: UUID


class SupportResolveRequest(BaseModel):
    """Resolve support ticket."""
    resolution: str = Field(..., min_length=10)


class SupportEscalateRequest(BaseModel):
    """Escalate support ticket."""
    escalated_to_id: UUID
    reason: str = Field(..., min_length=10)


class SupportFeedbackRequest(BaseModel):
    """Submit feedback for ticket."""
    satisfaction_rating: int = Field(..., ge=1, le=5)
    feedback: Optional[str] = None


class SupportCommentCreate(BaseModel):
    """Create comment on ticket."""
    comment: str = Field(..., min_length=1)
    is_internal: bool = False
    attachments: Optional[List[str]] = None


class SupportCommentResponse(BaseResponseSchema):
    """Response for comment."""
    id: str  # VARCHAR in production
    ticket_id: str  # VARCHAR FK
    comment: str
    is_internal: bool
    author_type: str
    author_name: str
    attachments: Optional[List[str]] = None
    created_at: datetime


# ==================== Audit Schemas ====================

class FranchiseeAuditBase(BaseModel):
    """Base schema for Audit."""
    audit_type: AuditType
    scheduled_date: date
    auditor_name: str = Field(..., min_length=2, max_length=200)
    auditor_id: Optional[UUID] = None
    notes: Optional[str] = None


class FranchiseeAuditCreate(FranchiseeAuditBase):
    """Schema for creating Audit."""
    franchisee_id: UUID


class FranchiseeAuditUpdate(BaseModel):
    """Schema for updating Audit."""
    scheduled_date: Optional[date] = None
    auditor_name: Optional[str] = None
    auditor_id: Optional[UUID] = None
    notes: Optional[str] = None


class FranchiseeAuditResponse(BaseResponseSchema):
    """Response schema for Audit."""
    id: str  # VARCHAR in production
    franchisee_id: str  # VARCHAR FK
    audit_number: str
    audit_type: AuditType
    status: str

    scheduled_date: date
    actual_date: Optional[date] = None
    auditor_name: str

    overall_score: Optional[Decimal] = None
    compliance_score: Optional[Decimal] = None
    quality_score: Optional[Decimal] = None
    result: Optional[AuditResult] = None

    follow_up_required: bool
    follow_up_date: Optional[date] = None

    completed_at: Optional[datetime] = None
    created_at: datetime


class AuditCompleteRequest(BaseModel):
    """Complete audit."""
    actual_date: date
    checklist: Optional[List[dict]] = None
    findings: Optional[str] = None
    observations: Optional[List[str]] = None
    non_conformities: Optional[List[dict]] = None

    overall_score: Decimal = Field(..., ge=0, le=100)
    compliance_score: Optional[Decimal] = Field(None, ge=0, le=100)
    quality_score: Optional[Decimal] = Field(None, ge=0, le=100)

    result: AuditResult
    corrective_actions: Optional[List[dict]] = None
    follow_up_required: bool = False
    follow_up_date: Optional[date] = None

    report_url: Optional[str] = None
    evidence_urls: Optional[List[str]] = None


# ==================== Dashboard Schemas ====================

class FranchiseeDashboardResponse(BaseModel):
    """Franchisee dashboard metrics."""
    date: date

    # Counts
    total_franchisees: int = 0
    active_franchisees: int = 0
    pending_applications: int = 0
    suspended_franchisees: int = 0

    # By Status
    by_status: dict = {}

    # By Type
    by_type: dict = {}

    # By Tier
    by_tier: dict = {}

    # Performance
    total_revenue_mtd: Decimal = Decimal("0")
    total_orders_mtd: int = 0
    avg_order_value: Decimal = Decimal("0")

    # Support
    open_tickets: int = 0
    sla_breached_tickets: int = 0

    # Training
    trainings_scheduled: int = 0
    trainings_completed_mtd: int = 0

    # Audits
    audits_scheduled: int = 0
    audits_pending_action: int = 0

    # Top Performers
    top_franchisees: List[dict] = []


class FranchiseeLeaderboardResponse(BaseModel):
    """Franchisee leaderboard."""
    period: str
    period_start: date
    period_end: date

    rankings: List[dict] = []  # [{rank, franchisee_id, name, revenue, orders, score}]


# ==================== Serviceability Schemas ====================

class ServiceabilityRequest(BaseModel):
    """Request body for adding serviceability pincodes."""
    pincodes: List[str] = Field(..., description="List of pincodes to add")
    service_types: Optional[List[str]] = Field(None, description="Service types to enable")
    priority: int = Field(1, ge=1, le=10, description="Priority level")
    max_daily_capacity: int = Field(10, ge=1, description="Max daily service capacity")
    expected_response_hours: int = Field(4, ge=1, description="Expected response time in hours")
    expected_completion_hours: int = Field(48, ge=1, description="Expected completion time in hours")
