"""Pydantic schemas for Campaign Management module."""
from datetime import datetime, date
from typing import Optional, List
from decimal import Decimal
from uuid import UUID
from pydantic import BaseModel, Field, ConfigDict

from app.schemas.base import BaseResponseSchema

from app.models.campaign import (
    CampaignType, CampaignStatus, CampaignCategory,
    AudienceType, DeliveryStatus
)


# ==================== Campaign Template Schemas ====================

class CampaignTemplateBase(BaseModel):
    """Base schema for CampaignTemplate."""
    name: str = Field(..., min_length=2, max_length=200)
    description: Optional[str] = None
    campaign_type: CampaignType
    category: CampaignCategory
    subject: Optional[str] = Field(None, max_length=500)
    content: str = Field(..., min_length=10)
    html_content: Optional[str] = None
    variables: Optional[List[str]] = None  # ["customer_name", "product_name", etc.]
    media_urls: Optional[List[str]] = None
    is_active: bool = True


class CampaignTemplateCreate(CampaignTemplateBase):
    """Schema for creating CampaignTemplate."""
    pass


class CampaignTemplateUpdate(BaseModel):
    """Schema for updating CampaignTemplate."""
    name: Optional[str] = None
    description: Optional[str] = None
    subject: Optional[str] = None
    content: Optional[str] = None
    html_content: Optional[str] = None
    variables: Optional[List[str]] = None
    media_urls: Optional[List[str]] = None
    is_active: Optional[bool] = None


class CampaignTemplateResponse(BaseResponseSchema):
    """Response schema for CampaignTemplate."""
    id: UUID
    name: str
    description: Optional[str] = None
    campaign_type: CampaignType
    category: str
    subject: Optional[str] = None
    content: str
    html_content: Optional[str] = None
    variables: Optional[List[str]] = None
    media_urls: Optional[List[str]] = None
    is_active: bool
    is_system: bool
    created_at: datetime


# ==================== Audience Segment Schemas ====================

class SegmentCondition(BaseModel):
    """A single segment condition."""
    field: str  # customer field: total_orders, city, last_order_date, etc.
    operator: str  # EQUALS, GREATER_THAN, etc.
    value: str  # The value to compare


class AudienceSegmentBase(BaseModel):
    """Base schema for AudienceSegment."""
    name: str = Field(..., min_length=2, max_length=200)
    description: Optional[str] = None
    segment_type: AudienceType = AudienceType.DYNAMIC
    conditions: Optional[List[SegmentCondition]] = None
    condition_logic: str = "AND"  # AND or OR
    customer_ids: Optional[List[UUID]] = None  # For MANUAL_LIST type
    is_active: bool = True


class AudienceSegmentCreate(AudienceSegmentBase):
    """Schema for creating AudienceSegment."""
    pass


class AudienceSegmentUpdate(BaseModel):
    """Schema for updating AudienceSegment."""
    name: Optional[str] = None
    description: Optional[str] = None
    conditions: Optional[List[SegmentCondition]] = None
    condition_logic: Optional[str] = None
    customer_ids: Optional[List[UUID]] = None
    is_active: Optional[bool] = None


class AudienceSegmentResponse(BaseResponseSchema):
    """Response schema for AudienceSegment."""
    id: UUID
    name: str
    description: Optional[str] = None
    segment_type: AudienceType
    conditions: Optional[List[dict]] = None
    condition_logic: str
    estimated_size: int
    last_calculated_at: Optional[datetime] = None
    is_active: bool
    created_at: datetime


# ==================== Campaign Schemas ====================

class CampaignBase(BaseModel):
    """Base schema for Campaign."""
    name: str = Field(..., min_length=2, max_length=200)
    description: Optional[str] = None
    campaign_type: CampaignType
    category: CampaignCategory
    template_id: Optional[UUID] = None
    subject: Optional[str] = Field(None, max_length=500)
    content: str = Field(..., min_length=10)
    html_content: Optional[str] = None
    media_urls: Optional[List[str]] = None
    cta_text: Optional[str] = Field(None, max_length=100)
    cta_url: Optional[str] = Field(None, max_length=500)
    audience_type: AudienceType = AudienceType.ALL_CUSTOMERS
    segment_id: Optional[UUID] = None
    sender_name: Optional[str] = Field(None, max_length=100)
    sender_email: Optional[str] = Field(None, max_length=255)
    sender_phone: Optional[str] = Field(None, max_length=20)
    reply_to: Optional[str] = Field(None, max_length=255)
    tags: Optional[List[str]] = None


class CampaignCreate(CampaignBase):
    """Schema for creating Campaign."""
    scheduled_at: Optional[datetime] = None
    is_recurring: bool = False
    recurrence_pattern: Optional[str] = None  # DAILY, WEEKLY, MONTHLY
    recurrence_config: Optional[dict] = None
    budget_amount: Optional[Decimal] = None
    daily_limit: Optional[int] = None
    hourly_limit: Optional[int] = None


class CampaignUpdate(BaseModel):
    """Schema for updating Campaign."""
    name: Optional[str] = None
    description: Optional[str] = None
    subject: Optional[str] = None
    content: Optional[str] = None
    html_content: Optional[str] = None
    media_urls: Optional[List[str]] = None
    cta_text: Optional[str] = None
    cta_url: Optional[str] = None
    scheduled_at: Optional[datetime] = None
    sender_name: Optional[str] = None
    sender_email: Optional[str] = None
    sender_phone: Optional[str] = None
    reply_to: Optional[str] = None
    budget_amount: Optional[Decimal] = None
    daily_limit: Optional[int] = None
    hourly_limit: Optional[int] = None
    tags: Optional[List[str]] = None


class CampaignScheduleRequest(BaseModel):
    """Request to schedule a campaign."""
    scheduled_at: datetime


class CampaignResponse(BaseResponseSchema):
    """Response schema for Campaign."""
    id: UUID
    campaign_code: str
    name: str
    description: Optional[str] = None
    campaign_type: CampaignType
    category: str
    status: str
    template_id: Optional[UUID] = None
    subject: Optional[str] = None
    content: str
    cta_text: Optional[str] = None
    cta_url: Optional[str] = None
    audience_type: AudienceType
    segment_id: Optional[UUID] = None
    target_count: int
    scheduled_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    is_recurring: bool
    total_sent: int
    total_delivered: int
    total_opened: int
    total_clicked: int
    total_bounced: int
    total_unsubscribed: int
    total_failed: int
    total_cost: Decimal
    tags: Optional[List[str]] = None
    created_at: datetime
    updated_at: datetime


class CampaignDetailResponse(CampaignResponse):
    """Detailed campaign response."""
    html_content: Optional[str] = None
    media_urls: Optional[List[str]] = None
    sender_name: Optional[str] = None
    sender_email: Optional[str] = None
    sender_phone: Optional[str] = None
    reply_to: Optional[str] = None
    recurrence_pattern: Optional[str] = None
    recurrence_config: Optional[dict] = None
    budget_amount: Optional[Decimal] = None
    daily_limit: Optional[int] = None
    hourly_limit: Optional[int] = None
    is_ab_test: bool = False
    ab_test_config: Optional[dict] = None


class CampaignListResponse(BaseModel):
    """Paginated campaign list."""
    items: List[CampaignResponse]
    total: int
    page: int = 1
    size: int = 50
    pages: int = 1


# ==================== Campaign Recipient Schemas ====================

class CampaignRecipientResponse(BaseResponseSchema):
    """Response schema for CampaignRecipient."""
    id: UUID
    campaign_id: UUID
    customer_id: Optional[UUID] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    name: Optional[str] = None
    status: str
    sent_at: Optional[datetime] = None
    delivered_at: Optional[datetime] = None
    opened_at: Optional[datetime] = None
    clicked_at: Optional[datetime] = None
    open_count: int
    click_count: int
    failure_reason: Optional[str] = None
    ab_variant: Optional[str] = None


class CampaignRecipientListResponse(BaseModel):
    """Paginated recipient list."""
    items: List[CampaignRecipientResponse]
    total: int
    page: int = 1
    size: int = 50
    pages: int = 1


# ==================== Campaign Automation Schemas ====================

class CampaignAutomationBase(BaseModel):
    """Base schema for CampaignAutomation."""
    name: str = Field(..., min_length=2, max_length=200)
    description: Optional[str] = None
    trigger_type: str  # ORDER_PLACED, AMC_EXPIRING, BIRTHDAY, etc.
    trigger_conditions: Optional[dict] = None
    delay_minutes: int = 0
    template_id: UUID
    campaign_type: CampaignType
    is_active: bool = True
    max_per_customer: int = 1
    cooldown_days: int = 7


class CampaignAutomationCreate(CampaignAutomationBase):
    """Schema for creating CampaignAutomation."""
    pass


class CampaignAutomationUpdate(BaseModel):
    """Schema for updating CampaignAutomation."""
    name: Optional[str] = None
    description: Optional[str] = None
    trigger_conditions: Optional[dict] = None
    delay_minutes: Optional[int] = None
    template_id: Optional[UUID] = None
    is_active: Optional[bool] = None
    max_per_customer: Optional[int] = None
    cooldown_days: Optional[int] = None


class CampaignAutomationResponse(BaseResponseSchema):
    """Response schema for CampaignAutomation."""
    id: UUID
    name: str
    description: Optional[str] = None
    trigger_type: str
    trigger_conditions: Optional[dict] = None
    delay_minutes: int
    template_id: UUID
    campaign_type: CampaignType
    is_active: bool
    max_per_customer: int
    cooldown_days: int
    total_triggered: int
    total_sent: int
    created_at: datetime


# ==================== Unsubscribe Schemas ====================

class UnsubscribeRequest(BaseModel):
    """Request to unsubscribe."""
    email: Optional[str] = None
    phone: Optional[str] = None
    channel: CampaignType
    reason: Optional[str] = None
    campaign_id: Optional[UUID] = None


class UnsubscribeResponse(BaseResponseSchema):
    """Response for unsubscribe."""
    id: UUID
    customer_id: Optional[UUID] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    channel: str
    reason: Optional[str] = None
    unsubscribed_at: datetime


# ==================== Dashboard & Analytics Schemas ====================

class CampaignDashboardResponse(BaseModel):
    """Campaign dashboard metrics."""
    date: date

    # Volume
    total_campaigns: int = 0
    active_campaigns: int = 0
    scheduled_campaigns: int = 0
    completed_campaigns: int = 0

    # By Status
    by_status: dict = {}

    # By Type
    by_type: dict = {}

    # Delivery metrics (today/period)
    total_sent: int = 0
    total_delivered: int = 0
    total_opened: int = 0
    total_clicked: int = 0
    total_bounced: int = 0
    total_unsubscribed: int = 0

    # Rates
    delivery_rate: Decimal = Decimal("0")
    open_rate: Decimal = Decimal("0")
    click_rate: Decimal = Decimal("0")
    bounce_rate: Decimal = Decimal("0")

    # Cost
    total_cost: Decimal = Decimal("0")

    # Top performing campaigns
    top_campaigns: List[dict] = []


class CampaignPerformanceResponse(BaseModel):
    """Campaign performance metrics."""
    campaign_id: UUID
    campaign_name: str
    campaign_type: CampaignType
    status: str

    # Audience
    target_count: int = 0
    total_sent: int = 0

    # Delivery
    delivered: int = 0
    delivery_rate: Decimal = Decimal("0")

    # Engagement
    opened: int = 0
    open_rate: Decimal = Decimal("0")
    unique_opens: int = 0

    clicked: int = 0
    click_rate: Decimal = Decimal("0")
    unique_clicks: int = 0
    click_to_open_rate: Decimal = Decimal("0")

    # Negative
    bounced: int = 0
    bounce_rate: Decimal = Decimal("0")
    unsubscribed: int = 0
    unsubscribe_rate: Decimal = Decimal("0")
    failed: int = 0

    # Cost
    total_cost: Decimal = Decimal("0")
    cost_per_send: Decimal = Decimal("0")
    cost_per_click: Decimal = Decimal("0")

    # Timeline
    sent_timeline: List[dict] = []  # [{hour/date, count}]
    open_timeline: List[dict] = []
    click_timeline: List[dict] = []
