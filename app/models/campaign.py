"""
Campaign Management Models.

This module contains models for:
- Marketing campaigns (Email, SMS, WhatsApp, Push)
- Campaign templates
- Audience segments
- Campaign scheduling and automation
- Campaign analytics
"""
import uuid
import enum
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional, List

from sqlalchemy import (
    String, Text, Integer, Boolean, DateTime, Date,
    ForeignKey, Numeric
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class CampaignType(str, enum.Enum):
    """Type of marketing campaign."""
    EMAIL = "EMAIL"
    SMS = "SMS"
    WHATSAPP = "WHATSAPP"
    PUSH_NOTIFICATION = "PUSH_NOTIFICATION"
    IN_APP = "IN_APP"
    VOICE = "VOICE"
    MULTI_CHANNEL = "MULTI_CHANNEL"


class CampaignStatus(str, enum.Enum):
    """Status of campaign."""
    DRAFT = "DRAFT"
    SCHEDULED = "SCHEDULED"
    RUNNING = "RUNNING"
    PAUSED = "PAUSED"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"
    FAILED = "FAILED"


class CampaignCategory(str, enum.Enum):
    """Category of campaign."""
    PROMOTIONAL = "PROMOTIONAL"
    TRANSACTIONAL = "TRANSACTIONAL"
    INFORMATIONAL = "INFORMATIONAL"
    REMINDER = "REMINDER"
    FEEDBACK = "FEEDBACK"
    WELCOME = "WELCOME"
    REACTIVATION = "REACTIVATION"
    LOYALTY = "LOYALTY"
    SEASONAL = "SEASONAL"
    PRODUCT_LAUNCH = "PRODUCT_LAUNCH"
    SERVICE_UPDATE = "SERVICE_UPDATE"
    AMC_RENEWAL = "AMC_RENEWAL"


class AudienceType(str, enum.Enum):
    """Type of audience selection."""
    ALL_CUSTOMERS = "ALL_CUSTOMERS"
    SEGMENT = "SEGMENT"
    MANUAL_LIST = "MANUAL_LIST"
    IMPORTED = "IMPORTED"
    DYNAMIC = "DYNAMIC"


class SegmentOperator(str, enum.Enum):
    """Operators for segment conditions."""
    EQUALS = "EQUALS"
    NOT_EQUALS = "NOT_EQUALS"
    CONTAINS = "CONTAINS"
    NOT_CONTAINS = "NOT_CONTAINS"
    GREATER_THAN = "GREATER_THAN"
    LESS_THAN = "LESS_THAN"
    BETWEEN = "BETWEEN"
    IN_LIST = "IN_LIST"
    NOT_IN_LIST = "NOT_IN_LIST"
    IS_NULL = "IS_NULL"
    IS_NOT_NULL = "IS_NOT_NULL"


class DeliveryStatus(str, enum.Enum):
    """Delivery status of campaign message."""
    PENDING = "PENDING"
    SENT = "SENT"
    DELIVERED = "DELIVERED"
    OPENED = "OPENED"
    CLICKED = "CLICKED"
    BOUNCED = "BOUNCED"
    FAILED = "FAILED"
    UNSUBSCRIBED = "UNSUBSCRIBED"
    COMPLAINED = "COMPLAINED"


class CampaignTemplate(Base):
    """Reusable campaign templates."""
    __tablename__ = "campaign_templates"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(200))
    description: Mapped[Optional[str]] = mapped_column(Text)

    # Template type
    campaign_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="EMAIL, SMS, WHATSAPP, PUSH_NOTIFICATION, IN_APP, VOICE, MULTI_CHANNEL"
    )
    category: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="PROMOTIONAL, TRANSACTIONAL, INFORMATIONAL, REMINDER, FEEDBACK, WELCOME, REACTIVATION, LOYALTY, SEASONAL, PRODUCT_LAUNCH, SERVICE_UPDATE, AMC_RENEWAL"
    )

    # Content
    subject: Mapped[Optional[str]] = mapped_column(String(500))  # For email
    content: Mapped[str] = mapped_column(Text)  # Main content/body
    html_content: Mapped[Optional[str]] = mapped_column(Text)  # HTML version for email

    # Placeholders/Variables
    variables: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)  # {{customer_name}}, {{product}}, etc.

    # Media
    media_urls: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)  # Images, attachments

    # Metadata
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_system: Mapped[bool] = mapped_column(Boolean, default=False)  # System templates

    # Creator
    created_by_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    created_by = relationship("User", lazy="selectin")


class AudienceSegment(Base):
    """Customer segments for targeted campaigns."""
    __tablename__ = "audience_segments"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(200))
    description: Mapped[Optional[str]] = mapped_column(Text)

    # Segment definition
    segment_type: Mapped[str] = mapped_column(
        String(50),
        default="DYNAMIC",
        comment="ALL_CUSTOMERS, SEGMENT, MANUAL_LIST, IMPORTED, DYNAMIC"
    )

    # Dynamic segment conditions (JSON array of conditions)
    # [{"field": "total_orders", "operator": "GREATER_THAN", "value": 5}, ...]
    conditions: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    condition_logic: Mapped[str] = mapped_column(String(10), default="AND")  # AND/OR

    # Static list (for MANUAL_LIST type)
    customer_ids: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)  # List of customer IDs

    # Estimated size
    estimated_size: Mapped[int] = mapped_column(Integer, default=0)
    last_calculated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Creator
    created_by_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    created_by = relationship("User", lazy="selectin")


class Campaign(Base):
    """Marketing campaign."""
    __tablename__ = "campaigns"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    campaign_code: Mapped[str] = mapped_column(
        String(30), unique=True, index=True
    )  # CAMP-YYYYMMDD-XXXX
    name: Mapped[str] = mapped_column(String(200))
    description: Mapped[Optional[str]] = mapped_column(Text)

    # Type and category
    campaign_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="EMAIL, SMS, WHATSAPP, PUSH_NOTIFICATION, IN_APP, VOICE, MULTI_CHANNEL"
    )
    category: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="PROMOTIONAL, TRANSACTIONAL, INFORMATIONAL, REMINDER, FEEDBACK, WELCOME, REACTIVATION, LOYALTY, SEASONAL, PRODUCT_LAUNCH, SERVICE_UPDATE, AMC_RENEWAL"
    )

    # Status
    status: Mapped[str] = mapped_column(
        String(50),
        default="DRAFT",
        comment="DRAFT, SCHEDULED, RUNNING, PAUSED, COMPLETED, CANCELLED, FAILED"
    )

    # Template (optional)
    template_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("campaign_templates.id", ondelete="SET NULL")
    )

    # Content
    subject: Mapped[Optional[str]] = mapped_column(String(500))
    content: Mapped[str] = mapped_column(Text)
    html_content: Mapped[Optional[str]] = mapped_column(Text)
    media_urls: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)

    # Call to Action
    cta_text: Mapped[Optional[str]] = mapped_column(String(100))
    cta_url: Mapped[Optional[str]] = mapped_column(String(500))

    # Audience
    audience_type: Mapped[str] = mapped_column(
        String(50),
        default="ALL_CUSTOMERS",
        comment="ALL_CUSTOMERS, SEGMENT, MANUAL_LIST, IMPORTED, DYNAMIC"
    )
    segment_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("audience_segments.id", ondelete="SET NULL")
    )
    target_count: Mapped[int] = mapped_column(Integer, default=0)

    # Scheduling
    scheduled_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Recurring campaign settings
    is_recurring: Mapped[bool] = mapped_column(Boolean, default=False)
    recurrence_pattern: Mapped[Optional[str]] = mapped_column(String(50))  # DAILY, WEEKLY, MONTHLY
    recurrence_config: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)  # {day_of_week: 1, time: "10:00"}

    # Sending configuration
    sender_name: Mapped[Optional[str]] = mapped_column(String(100))
    sender_email: Mapped[Optional[str]] = mapped_column(String(255))
    sender_phone: Mapped[Optional[str]] = mapped_column(String(20))
    reply_to: Mapped[Optional[str]] = mapped_column(String(255))

    # A/B Testing
    is_ab_test: Mapped[bool] = mapped_column(Boolean, default=False)
    ab_test_config: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)  # Variants, split percentage

    # Budget and limits
    budget_amount: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 2))
    daily_limit: Mapped[Optional[int]] = mapped_column(Integer)  # Max sends per day
    hourly_limit: Mapped[Optional[int]] = mapped_column(Integer)  # Max sends per hour

    # Metrics (aggregated)
    total_sent: Mapped[int] = mapped_column(Integer, default=0)
    total_delivered: Mapped[int] = mapped_column(Integer, default=0)
    total_opened: Mapped[int] = mapped_column(Integer, default=0)
    total_clicked: Mapped[int] = mapped_column(Integer, default=0)
    total_bounced: Mapped[int] = mapped_column(Integer, default=0)
    total_unsubscribed: Mapped[int] = mapped_column(Integer, default=0)
    total_failed: Mapped[int] = mapped_column(Integer, default=0)

    # Cost tracking
    total_cost: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0"))

    # Tags for organization
    tags: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)

    # Creator
    created_by_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    template = relationship("CampaignTemplate", lazy="selectin")
    segment = relationship("AudienceSegment", lazy="selectin")
    created_by = relationship("User", lazy="selectin")
    recipients = relationship("CampaignRecipient", back_populates="campaign", lazy="selectin")


class CampaignRecipient(Base):
    """Individual recipient in a campaign."""
    __tablename__ = "campaign_recipients"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    campaign_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("campaigns.id", ondelete="CASCADE"), index=True
    )
    customer_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("customers.id", ondelete="SET NULL"), index=True
    )

    # Contact details (stored for record)
    email: Mapped[Optional[str]] = mapped_column(String(255))
    phone: Mapped[Optional[str]] = mapped_column(String(20))
    name: Mapped[Optional[str]] = mapped_column(String(200))

    # Personalization data
    personalization_data: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)

    # Delivery status
    status: Mapped[str] = mapped_column(
        String(50),
        default="PENDING",
        index=True,
        comment="PENDING, SENT, DELIVERED, OPENED, CLICKED, BOUNCED, FAILED, UNSUBSCRIBED, COMPLAINED"
    )

    # Tracking timestamps
    sent_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    delivered_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    opened_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    clicked_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    bounced_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    unsubscribed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    failed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Engagement metrics
    open_count: Mapped[int] = mapped_column(Integer, default=0)
    click_count: Mapped[int] = mapped_column(Integer, default=0)

    # Failure details
    failure_reason: Mapped[Optional[str]] = mapped_column(Text)

    # External references
    external_message_id: Mapped[Optional[str]] = mapped_column(String(100))  # From SMS/Email provider

    # A/B test variant
    ab_variant: Mapped[Optional[str]] = mapped_column(String(10))  # A, B, C...

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    campaign = relationship("Campaign", back_populates="recipients")
    customer = relationship("Customer", lazy="selectin")


class CampaignAutomation(Base):
    """Automated campaign triggers."""
    __tablename__ = "campaign_automations"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(200))
    description: Mapped[Optional[str]] = mapped_column(Text)

    # Trigger type
    trigger_type: Mapped[str] = mapped_column(String(50))
    # ORDER_PLACED, ORDER_DELIVERED, SERVICE_COMPLETED, AMC_EXPIRING,
    # BIRTHDAY, ANNIVERSARY, CART_ABANDONED, INACTIVE_CUSTOMER, etc.

    # Trigger conditions
    trigger_conditions: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    # e.g., {"days_before": 30} for AMC_EXPIRING

    # Delay after trigger
    delay_minutes: Mapped[int] = mapped_column(Integer, default=0)

    # Campaign to send
    template_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("campaign_templates.id", ondelete="CASCADE")
    )

    # Channel
    campaign_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="EMAIL, SMS, WHATSAPP, PUSH_NOTIFICATION, IN_APP, VOICE, MULTI_CHANNEL"
    )

    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Limits
    max_per_customer: Mapped[int] = mapped_column(Integer, default=1)  # Max times to send to same customer
    cooldown_days: Mapped[int] = mapped_column(Integer, default=7)  # Days between sends to same customer

    # Stats
    total_triggered: Mapped[int] = mapped_column(Integer, default=0)
    total_sent: Mapped[int] = mapped_column(Integer, default=0)

    # Creator
    created_by_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    template = relationship("CampaignTemplate", lazy="selectin")
    created_by = relationship("User", lazy="selectin")


class CampaignAutomationLog(Base):
    """Log of automated campaign executions."""
    __tablename__ = "campaign_automation_logs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    automation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("campaign_automations.id", ondelete="CASCADE"), index=True
    )
    customer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("customers.id", ondelete="CASCADE"), index=True
    )

    # Trigger details
    trigger_entity_type: Mapped[Optional[str]] = mapped_column(String(50))  # ORDER, SERVICE, etc.
    trigger_entity_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True))

    # Status
    status: Mapped[str] = mapped_column(String(20))  # TRIGGERED, SENT, SKIPPED, FAILED
    skip_reason: Mapped[Optional[str]] = mapped_column(Text)  # Why skipped (cooldown, limit, etc.)

    # Sent message reference
    recipient_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("campaign_recipients.id", ondelete="SET NULL")
    )

    # Timestamps
    triggered_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc)
    )
    sent_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    automation = relationship("CampaignAutomation", lazy="selectin")
    customer = relationship("Customer", lazy="selectin")


class UnsubscribeList(Base):
    """Customers who have unsubscribed from campaigns."""
    __tablename__ = "unsubscribe_list"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    # Contact
    customer_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("customers.id", ondelete="SET NULL"), index=True
    )
    email: Mapped[Optional[str]] = mapped_column(String(255), index=True)
    phone: Mapped[Optional[str]] = mapped_column(String(20), index=True)

    # Channel-specific unsubscribe
    channel: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="EMAIL, SMS, WHATSAPP, PUSH_NOTIFICATION, IN_APP, VOICE, MULTI_CHANNEL"
    )

    # Reason
    reason: Mapped[Optional[str]] = mapped_column(Text)

    # Source
    source_campaign_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("campaigns.id", ondelete="SET NULL")
    )

    # Timestamps
    unsubscribed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    customer = relationship("Customer", lazy="selectin")
