"""
Lead Management Models.

This module contains models for:
- Lead capture and tracking
- Lead scoring and qualification
- Lead assignment and routing
- Lead activity logging
- Lead conversion
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


class LeadSource(str, enum.Enum):
    """Source of lead."""
    WEBSITE = "WEBSITE"
    PHONE_CALL = "PHONE_CALL"
    WALK_IN = "WALK_IN"
    REFERRAL = "REFERRAL"
    SOCIAL_MEDIA = "SOCIAL_MEDIA"
    EMAIL_CAMPAIGN = "EMAIL_CAMPAIGN"
    SMS_CAMPAIGN = "SMS_CAMPAIGN"
    EXHIBITION = "EXHIBITION"
    ADVERTISEMENT = "ADVERTISEMENT"
    PARTNER = "PARTNER"
    DEALER = "DEALER"
    FRANCHISEE = "FRANCHISEE"
    AMAZON = "AMAZON"
    FLIPKART = "FLIPKART"
    OTHER_MARKETPLACE = "OTHER_MARKETPLACE"
    COLD_CALL = "COLD_CALL"
    OTHER = "OTHER"


class LeadStatus(str, enum.Enum):
    """Status of lead in pipeline."""
    NEW = "NEW"
    CONTACTED = "CONTACTED"
    QUALIFIED = "QUALIFIED"
    PROPOSAL_SENT = "PROPOSAL_SENT"
    NEGOTIATION = "NEGOTIATION"
    WON = "WON"
    LOST = "LOST"
    NURTURING = "NURTURING"
    DISQUALIFIED = "DISQUALIFIED"
    DUPLICATE = "DUPLICATE"


class LeadPriority(str, enum.Enum):
    """Priority of lead."""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class LeadType(str, enum.Enum):
    """Type of lead."""
    INDIVIDUAL = "INDIVIDUAL"
    BUSINESS = "BUSINESS"
    GOVERNMENT = "GOVERNMENT"
    INSTITUTIONAL = "INSTITUTIONAL"


class LeadInterest(str, enum.Enum):
    """Product interest level."""
    NEW_PURCHASE = "NEW_PURCHASE"
    REPLACEMENT = "REPLACEMENT"
    UPGRADE = "UPGRADE"
    AMC = "AMC"
    DEMO = "DEMO"
    INQUIRY = "INQUIRY"


class ActivityType(str, enum.Enum):
    """Type of lead activity."""
    CALL = "CALL"
    EMAIL = "EMAIL"
    SMS = "SMS"
    WHATSAPP = "WHATSAPP"
    MEETING = "MEETING"
    DEMO = "DEMO"
    SITE_VISIT = "SITE_VISIT"
    PROPOSAL = "PROPOSAL"
    NEGOTIATION = "NEGOTIATION"
    FOLLOW_UP = "FOLLOW_UP"
    NOTE = "NOTE"
    STATUS_CHANGE = "STATUS_CHANGE"
    ASSIGNMENT = "ASSIGNMENT"
    CONVERSION = "CONVERSION"


class LostReason(str, enum.Enum):
    """Reason for losing lead."""
    PRICE_TOO_HIGH = "PRICE_TOO_HIGH"
    COMPETITOR_CHOSEN = "COMPETITOR_CHOSEN"
    BUDGET_CONSTRAINTS = "BUDGET_CONSTRAINTS"
    NOT_INTERESTED = "NOT_INTERESTED"
    NO_RESPONSE = "NO_RESPONSE"
    WRONG_TIMING = "WRONG_TIMING"
    PRODUCT_NOT_FIT = "PRODUCT_NOT_FIT"
    LOCATION_NOT_SERVICEABLE = "LOCATION_NOT_SERVICEABLE"
    CUSTOMER_POSTPONED = "CUSTOMER_POSTPONED"
    OTHER = "OTHER"


class Lead(Base):
    """Lead/Prospect model."""
    __tablename__ = "leads"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    lead_number: Mapped[str] = mapped_column(
        String(30), unique=True, index=True
    )  # LEAD-YYYYMMDD-XXXX

    # Lead Type & Source
    lead_type: Mapped[str] = mapped_column(
        String(50), default="INDIVIDUAL",
        comment="INDIVIDUAL, BUSINESS, GOVERNMENT, INSTITUTIONAL"
    )
    source: Mapped[str] = mapped_column(
        String(50),
        comment="WEBSITE, PHONE_CALL, WALK_IN, REFERRAL, SOCIAL_MEDIA, EMAIL_CAMPAIGN, SMS_CAMPAIGN, EXHIBITION, ADVERTISEMENT, PARTNER, DEALER, FRANCHISEE, AMAZON, FLIPKART, OTHER_MARKETPLACE, COLD_CALL, OTHER"
    )
    source_details: Mapped[Optional[str]] = mapped_column(String(200))
    campaign_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True))
    referral_code: Mapped[Optional[str]] = mapped_column(String(50))

    # Contact Information
    first_name: Mapped[str] = mapped_column(String(100))
    last_name: Mapped[Optional[str]] = mapped_column(String(100))
    email: Mapped[Optional[str]] = mapped_column(String(255), index=True)
    phone: Mapped[str] = mapped_column(String(20), index=True)
    alternate_phone: Mapped[Optional[str]] = mapped_column(String(20))
    whatsapp_number: Mapped[Optional[str]] = mapped_column(String(20))

    # Business Information (for B2B leads)
    company_name: Mapped[Optional[str]] = mapped_column(String(200))
    designation: Mapped[Optional[str]] = mapped_column(String(100))
    industry: Mapped[Optional[str]] = mapped_column(String(100))
    employee_count: Mapped[Optional[str]] = mapped_column(String(50))
    gst_number: Mapped[Optional[str]] = mapped_column(String(20))

    # Address
    address_line1: Mapped[Optional[str]] = mapped_column(String(255))
    address_line2: Mapped[Optional[str]] = mapped_column(String(255))
    city: Mapped[Optional[str]] = mapped_column(String(100), index=True)
    state: Mapped[Optional[str]] = mapped_column(String(100))
    pincode: Mapped[Optional[str]] = mapped_column(String(10), index=True)
    country: Mapped[str] = mapped_column(String(50), default="India")

    # Product Interest
    interest: Mapped[str] = mapped_column(
        String(50), default="NEW_PURCHASE",
        comment="NEW_PURCHASE, REPLACEMENT, UPGRADE, AMC, DEMO, INQUIRY"
    )
    interested_products: Mapped[Optional[dict]] = mapped_column(JSONB)  # List of product IDs
    interested_category_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("categories.id", ondelete="SET NULL")
    )
    budget_min: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 2))
    budget_max: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 2))
    quantity_required: Mapped[int] = mapped_column(Integer, default=1)
    expected_purchase_date: Mapped[Optional[datetime]] = mapped_column(Date)

    # Status & Priority
    status: Mapped[str] = mapped_column(
        String(50), default="NEW", index=True,
        comment="NEW, CONTACTED, QUALIFIED, PROPOSAL_SENT, NEGOTIATION, WON, LOST, NURTURING, DISQUALIFIED, DUPLICATE"
    )
    priority: Mapped[str] = mapped_column(
        String(50), default="MEDIUM",
        comment="LOW, MEDIUM, HIGH, CRITICAL"
    )

    # Lead Scoring
    score: Mapped[int] = mapped_column(Integer, default=0)
    score_breakdown: Mapped[Optional[dict]] = mapped_column(JSONB)  # Individual scores
    is_qualified: Mapped[bool] = mapped_column(Boolean, default=False)
    qualification_date: Mapped[Optional[datetime]] = mapped_column(DateTime)
    qualified_by_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )

    # Assignment
    assigned_to_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), index=True
    )
    assigned_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    assigned_by_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    team_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True))
    region_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("regions.id", ondelete="SET NULL")
    )

    # Follow-up
    next_follow_up_date: Mapped[Optional[datetime]] = mapped_column(DateTime, index=True)
    next_follow_up_notes: Mapped[Optional[str]] = mapped_column(Text)
    last_contacted_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    contact_attempts: Mapped[int] = mapped_column(Integer, default=0)

    # Conversion
    converted_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    converted_by_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    converted_customer_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("customers.id", ondelete="SET NULL")
    )
    converted_order_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("orders.id", ondelete="SET NULL")
    )

    # Lost Information
    lost_reason: Mapped[Optional[str]] = mapped_column(
        String(50),
        comment="PRICE_TOO_HIGH, COMPETITOR_CHOSEN, BUDGET_CONSTRAINTS, NOT_INTERESTED, NO_RESPONSE, WRONG_TIMING, PRODUCT_NOT_FIT, LOCATION_NOT_SERVICEABLE, CUSTOMER_POSTPONED, OTHER"
    )
    lost_reason_details: Mapped[Optional[str]] = mapped_column(Text)
    lost_to_competitor: Mapped[Optional[str]] = mapped_column(String(100))
    lost_at: Mapped[Optional[datetime]] = mapped_column(DateTime)

    # Notes & Remarks
    description: Mapped[Optional[str]] = mapped_column(Text)
    internal_notes: Mapped[Optional[str]] = mapped_column(Text)
    special_requirements: Mapped[Optional[str]] = mapped_column(Text)
    tags: Mapped[Optional[dict]] = mapped_column(JSONB)  # List of tags

    # Call Integration
    source_call_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("calls.id", ondelete="SET NULL")
    )

    # Dealer/Franchisee Reference
    dealer_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("dealers.id", ondelete="SET NULL")
    )

    # Value Estimation
    estimated_value: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 2))
    actual_value: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 2))

    # Timestamps
    created_by_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    assigned_to = relationship("User", foreign_keys=[assigned_to_id], lazy="selectin")
    created_by = relationship("User", foreign_keys=[created_by_id], lazy="selectin")
    converted_customer = relationship("Customer", foreign_keys=[converted_customer_id])
    converted_order = relationship("Order", foreign_keys=[converted_order_id])
    interested_category = relationship("Category", lazy="selectin")
    activities = relationship("LeadActivity", back_populates="lead", lazy="selectin")
    region = relationship("Region", lazy="selectin")

    @property
    def full_name(self) -> str:
        """Get full name."""
        if self.last_name:
            return f"{self.first_name} {self.last_name}"
        return self.first_name

    @property
    def is_converted(self) -> bool:
        """Check if lead is converted."""
        return self.status == LeadStatus.WON and self.converted_customer_id is not None


class LeadActivity(Base):
    """Lead activity/interaction log."""
    __tablename__ = "lead_activities"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    lead_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("leads.id", ondelete="CASCADE"), index=True
    )

    # Activity Details
    activity_type: Mapped[str] = mapped_column(
        String(50),
        comment="CALL, EMAIL, SMS, WHATSAPP, MEETING, DEMO, SITE_VISIT, PROPOSAL, NEGOTIATION, FOLLOW_UP, NOTE, STATUS_CHANGE, ASSIGNMENT, CONVERSION"
    )
    subject: Mapped[str] = mapped_column(String(200))
    description: Mapped[Optional[str]] = mapped_column(Text)
    outcome: Mapped[Optional[str]] = mapped_column(String(100))

    # Timing
    activity_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    duration_minutes: Mapped[Optional[int]] = mapped_column(Integer)

    # Status Change (if activity is status change)
    old_status: Mapped[Optional[str]] = mapped_column(String(50))
    new_status: Mapped[Optional[str]] = mapped_column(String(50))

    # Assignment Change (if activity is assignment)
    old_assignee_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True))
    new_assignee_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True))

    # Call Reference
    call_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("calls.id", ondelete="SET NULL")
    )

    # Follow-up scheduled
    follow_up_date: Mapped[Optional[datetime]] = mapped_column(DateTime)
    follow_up_notes: Mapped[Optional[str]] = mapped_column(Text)

    # Created by
    created_by_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    lead = relationship("Lead", back_populates="activities")
    created_by = relationship("User", lazy="selectin")


class LeadScoreRule(Base):
    """Rules for automatic lead scoring."""
    __tablename__ = "lead_score_rules"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(100))
    description: Mapped[Optional[str]] = mapped_column(Text)

    # Rule Criteria
    field: Mapped[str] = mapped_column(String(50))  # e.g., 'source', 'budget_max', 'city'
    operator: Mapped[str] = mapped_column(String(20))  # eq, ne, gt, lt, gte, lte, in, contains
    value: Mapped[str] = mapped_column(String(255))  # Value to compare

    # Score Impact
    score_points: Mapped[int] = mapped_column(Integer)  # Points to add/subtract

    # Priority (for rule ordering)
    priority: Mapped[int] = mapped_column(Integer, default=0)

    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc)
    )


class LeadAssignmentRule(Base):
    """Rules for automatic lead assignment."""
    __tablename__ = "lead_assignment_rules"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(100))
    description: Mapped[Optional[str]] = mapped_column(Text)

    # Criteria
    source: Mapped[Optional[str]] = mapped_column(String(50))
    lead_type: Mapped[Optional[str]] = mapped_column(String(50))
    region_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("regions.id", ondelete="SET NULL")
    )
    pincode_pattern: Mapped[Optional[str]] = mapped_column(String(50))  # Regex or prefix
    category_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("categories.id", ondelete="SET NULL")
    )
    min_score: Mapped[Optional[int]] = mapped_column(Integer)
    max_score: Mapped[Optional[int]] = mapped_column(Integer)

    # Assignment Target
    assign_to_user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    assign_to_team_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True))
    round_robin: Mapped[bool] = mapped_column(Boolean, default=False)
    round_robin_users: Mapped[Optional[dict]] = mapped_column(JSONB)  # List of user IDs

    # Priority & Status
    priority: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    assign_to_user = relationship("User", lazy="selectin")
    region = relationship("Region", lazy="selectin")
