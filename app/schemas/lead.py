"""Pydantic schemas for Lead Management module."""
from datetime import datetime, date
from typing import Optional, List
from decimal import Decimal
from uuid import UUID
from pydantic import BaseModel, Field, ConfigDict, field_validator

from app.schemas.base import BaseResponseSchema

from app.models.lead import (
    LeadSource, LeadStatus, LeadPriority, LeadType,
    LeadInterest, ActivityType, LostReason
)


# ==================== Lead Schemas ====================

class LeadBase(BaseModel):
    """Base schema for Lead."""
    lead_type: LeadType = LeadType.INDIVIDUAL
    source: LeadSource
    source_details: Optional[str] = None
    campaign_id: Optional[UUID] = None
    referral_code: Optional[str] = None

    # Contact
    first_name: str = Field(..., min_length=2, max_length=100)
    last_name: Optional[str] = None
    email: Optional[str] = None
    phone: str = Field(..., min_length=10, max_length=20)
    alternate_phone: Optional[str] = None
    whatsapp_number: Optional[str] = None

    # Business (B2B)
    company_name: Optional[str] = None
    designation: Optional[str] = None
    industry: Optional[str] = None
    employee_count: Optional[str] = None
    gst_number: Optional[str] = None

    # Address
    address_line1: Optional[str] = None
    address_line2: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    pincode: Optional[str] = None
    country: str = "India"

    # Interest
    interest: LeadInterest = LeadInterest.NEW_PURCHASE
    interested_products: Optional[List[UUID]] = None
    interested_category_id: Optional[UUID] = None
    budget_min: Optional[Decimal] = None
    budget_max: Optional[Decimal] = None
    quantity_required: int = 1
    expected_purchase_date: Optional[date] = None

    # Priority
    priority: LeadPriority = LeadPriority.MEDIUM

    # Notes
    description: Optional[str] = None
    special_requirements: Optional[str] = None
    tags: Optional[List[str]] = None


class LeadCreate(LeadBase):
    """Schema for creating a lead."""
    assigned_to_id: Optional[UUID] = None
    estimated_value: Optional[Decimal] = None
    source_call_id: Optional[UUID] = None
    dealer_id: Optional[UUID] = None


class LeadUpdate(BaseModel):
    """Schema for updating a lead."""
    lead_type: Optional[LeadType] = None
    source_details: Optional[str] = None

    # Contact
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    alternate_phone: Optional[str] = None
    whatsapp_number: Optional[str] = None

    # Business
    company_name: Optional[str] = None
    designation: Optional[str] = None
    industry: Optional[str] = None

    # Address
    address_line1: Optional[str] = None
    address_line2: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    pincode: Optional[str] = None

    # Interest
    interest: Optional[LeadInterest] = None
    interested_products: Optional[List[UUID]] = None
    interested_category_id: Optional[UUID] = None
    budget_min: Optional[Decimal] = None
    budget_max: Optional[Decimal] = None
    quantity_required: Optional[int] = None
    expected_purchase_date: Optional[date] = None

    # Priority
    priority: Optional[LeadPriority] = None

    # Notes
    description: Optional[str] = None
    internal_notes: Optional[str] = None
    special_requirements: Optional[str] = None
    tags: Optional[List[str]] = None

    # Value
    estimated_value: Optional[Decimal] = None


class LeadAssignRequest(BaseModel):
    """Request to assign lead to a user."""
    assigned_to_id: UUID
    notes: Optional[str] = None


class LeadStatusUpdateRequest(BaseModel):
    """Request to update lead status."""
    status: LeadStatus
    notes: Optional[str] = None
    follow_up_date: Optional[datetime] = None
    follow_up_notes: Optional[str] = None


class LeadQualifyRequest(BaseModel):
    """Request to qualify a lead."""
    is_qualified: bool = True
    score: Optional[int] = None
    notes: Optional[str] = None


class LeadConvertRequest(BaseModel):
    """Request to convert lead to customer/order."""
    create_customer: bool = True
    create_order: bool = False
    order_details: Optional[dict] = None
    notes: Optional[str] = None


class LeadLostRequest(BaseModel):
    """Request to mark lead as lost."""
    lost_reason: LostReason
    lost_reason_details: Optional[str] = None
    lost_to_competitor: Optional[str] = None


class LeadResponse(BaseResponseSchema):
    """Response schema for Lead."""
    id: UUID
    lead_number: str
    lead_type: LeadType
    source: str
    source_details: Optional[str] = None

    # Contact
    first_name: str
    last_name: Optional[str] = None
    full_name: str
    email: Optional[str] = None
    phone: str
    alternate_phone: Optional[str] = None
    whatsapp_number: Optional[str] = None

    # Business
    company_name: Optional[str] = None
    designation: Optional[str] = None
    industry: Optional[str] = None

    # Address
    city: Optional[str] = None
    state: Optional[str] = None
    pincode: Optional[str] = None

    # Interest
    interest: LeadInterest
    interested_category_id: Optional[UUID] = None
    budget_min: Optional[Decimal] = None
    budget_max: Optional[Decimal] = None
    quantity_required: int = 1
    expected_purchase_date: Optional[date] = None

    # Status & Priority
    status: str
    priority: str

    # Scoring
    score: int = 0
    is_qualified: bool = False

    # Assignment
    assigned_to_id: Optional[UUID] = None
    assigned_to_name: Optional[str] = None
    assigned_at: Optional[datetime] = None

    # Follow-up
    next_follow_up_date: Optional[datetime] = None
    last_contacted_at: Optional[datetime] = None
    contact_attempts: int = 0

    # Value
    estimated_value: Optional[Decimal] = None

    # Conversion
    is_converted: bool = False
    converted_at: Optional[datetime] = None
    converted_customer_id: Optional[UUID] = None

    # Timestamps
    created_at: datetime
    updated_at: datetime


class LeadDetailResponse(LeadResponse):
    """Detailed lead response with activities."""
    # Full address
    address_line1: Optional[str] = None
    address_line2: Optional[str] = None
    country: str = "India"

    # Full business info
    employee_count: Optional[str] = None
    gst_number: Optional[str] = None

    # Source & Campaign
    campaign_id: Optional[UUID] = None
    referral_code: Optional[str] = None
    source_call_id: Optional[UUID] = None

    # Full scoring
    score_breakdown: Optional[dict] = None
    qualification_date: Optional[datetime] = None
    qualified_by_id: Optional[UUID] = None

    # Assignment details
    assigned_by_id: Optional[UUID] = None
    team_id: Optional[UUID] = None
    region_id: Optional[UUID] = None
    dealer_id: Optional[UUID] = None
    next_follow_up_notes: Optional[str] = None

    # Conversion details
    converted_order_id: Optional[UUID] = None
    converted_by_id: Optional[UUID] = None
    actual_value: Optional[Decimal] = None

    # Lost details
    lost_reason: Optional[LostReason] = None
    lost_reason_details: Optional[str] = None
    lost_to_competitor: Optional[str] = None
    lost_at: Optional[datetime] = None

    # Notes
    description: Optional[str] = None
    internal_notes: Optional[str] = None
    special_requirements: Optional[str] = None
    tags: Optional[List[str]] = None

    # Audit
    created_by_id: Optional[UUID] = None

    # Related data
    interested_products: Optional[List[UUID]] = None
    activities: List["LeadActivityResponse"] = []


class LeadListResponse(BaseModel):
    """Paginated lead list response."""
    items: List[LeadResponse]
    total: int
    page: int = 1
    size: int = 50
    pages: int = 1


# ==================== Lead Activity Schemas ====================

class LeadActivityBase(BaseModel):
    """Base schema for LeadActivity."""
    activity_type: ActivityType
    subject: str = Field(..., min_length=2, max_length=200)
    description: Optional[str] = None
    outcome: Optional[str] = None
    duration_minutes: Optional[int] = None


class LeadActivityCreate(LeadActivityBase):
    """Schema for creating lead activity."""
    follow_up_date: Optional[datetime] = None
    follow_up_notes: Optional[str] = None
    call_id: Optional[UUID] = None


class LeadActivityResponse(BaseResponseSchema):
    """Response schema for LeadActivity."""
    id: UUID
    lead_id: UUID
    activity_type: ActivityType
    subject: str
    description: Optional[str] = None
    outcome: Optional[str] = None

    activity_date: datetime
    duration_minutes: Optional[int] = None

    old_status: Optional[LeadStatus] = None
    new_status: Optional[LeadStatus] = None

    follow_up_date: Optional[datetime] = None
    follow_up_notes: Optional[str] = None

    created_by_id: UUID
    created_by_name: Optional[str] = None
    created_at: datetime


# ==================== Lead Scoring Rule Schemas ====================

class LeadScoreRuleCreate(BaseModel):
    """Schema for creating score rule."""
    name: str = Field(..., min_length=2, max_length=100)
    description: Optional[str] = None
    field: str = Field(..., min_length=1, max_length=50)
    operator: str = Field(..., min_length=1, max_length=20)
    value: str = Field(..., min_length=1, max_length=255)
    score_points: int
    priority: int = 0
    is_active: bool = True


class LeadScoreRuleResponse(BaseResponseSchema):
    """Response schema for score rule."""
    id: UUID
    name: str
    description: Optional[str] = None
    field: str
    operator: str
    value: str
    score_points: int
    priority: int
    is_active: bool
    created_at: datetime


# ==================== Lead Assignment Rule Schemas ====================

class LeadAssignmentRuleCreate(BaseModel):
    """Schema for creating assignment rule."""
    name: str = Field(..., min_length=2, max_length=100)
    description: Optional[str] = None
    source: Optional[LeadSource] = None
    lead_type: Optional[LeadType] = None
    region_id: Optional[UUID] = None
    pincode_pattern: Optional[str] = None
    category_id: Optional[UUID] = None
    min_score: Optional[int] = None
    max_score: Optional[int] = None
    assign_to_user_id: Optional[UUID] = None
    assign_to_team_id: Optional[UUID] = None
    round_robin: bool = False
    round_robin_users: Optional[List[UUID]] = None
    priority: int = 0
    is_active: bool = True


class LeadAssignmentRuleResponse(BaseResponseSchema):
    """Response schema for assignment rule."""
    id: UUID
    name: str
    description: Optional[str] = None
    source: Optional[str] = None
    lead_type: Optional[LeadType] = None
    region_id: Optional[UUID] = None
    pincode_pattern: Optional[str] = None
    category_id: Optional[UUID] = None
    min_score: Optional[int] = None
    max_score: Optional[int] = None
    assign_to_user_id: Optional[UUID] = None
    assign_to_team_id: Optional[UUID] = None
    round_robin: bool = False
    priority: int
    is_active: bool
    created_at: datetime


# ==================== Dashboard & Report Schemas ====================

class LeadDashboardResponse(BaseModel):
    """Lead management dashboard."""
    date: date

    # Volume
    total_leads: int = 0
    new_leads_today: int = 0
    leads_in_pipeline: int = 0

    # By Status
    leads_by_status: dict = {}

    # Conversion
    converted_today: int = 0
    conversion_rate: Decimal = Decimal("0")
    total_value_won: Decimal = Decimal("0")

    # Follow-ups
    pending_follow_ups: int = 0
    overdue_follow_ups: int = 0

    # By Source
    leads_by_source: dict = {}

    # Performance
    avg_conversion_time_days: int = 0
    qualified_leads: int = 0


class LeadPipelineResponse(BaseModel):
    """Lead pipeline/funnel report."""
    start_date: date
    end_date: date

    pipeline: List[dict] = []  # {status, count, value}
    conversion_funnel: List[dict] = []  # {stage, count, percentage}


class LeadSourceReportResponse(BaseModel):
    """Lead source performance report."""
    start_date: date
    end_date: date

    by_source: List[dict] = []  # {source, total, converted, conversion_rate, value}
    best_performing_source: Optional[str] = None
    total_leads: int = 0
    total_converted: int = 0


class LeadAgentReportResponse(BaseModel):
    """Agent performance report for leads."""
    start_date: date
    end_date: date

    by_agent: List[dict] = []  # {agent_id, name, assigned, converted, rate, value}
    top_performer: Optional[dict] = None


# ==================== Auto Assignment Schemas ====================

class AutoAssignRequest(BaseModel):
    """Request for auto-assigning a lead."""
    strategy: str = Field("ROUND_ROBIN", description="Assignment strategy: ROUND_ROBIN, LOAD_BALANCED, GEOGRAPHIC")
    team_id: Optional[UUID] = Field(None, description="Team ID to assign within")


class BulkAutoAssignRequest(BaseModel):
    """Request for bulk auto-assignment."""
    lead_ids: Optional[List[UUID]] = Field(None, description="Specific lead IDs to assign")
    assign_all_unassigned: bool = Field(False, description="Assign all unassigned leads")
    strategy: str = Field("ROUND_ROBIN", description="Assignment strategy")
    team_id: Optional[UUID] = Field(None, description="Team ID to assign within")


# Update forward references
LeadDetailResponse.model_rebuild()
