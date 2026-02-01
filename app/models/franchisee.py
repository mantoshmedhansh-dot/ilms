"""
Franchisee CRM Models for Consumer Durable ERP.

This module handles:
- Franchisee registration and profiles
- Territory/area assignments
- Contracts and agreements
- Performance tracking
- Training and certifications
- Support tickets
- Compliance audits
"""
import enum
import uuid
from datetime import datetime, date, timezone
from decimal import Decimal
from typing import Optional, List

from sqlalchemy import (
    String, Text, Boolean, Integer, DateTime, Date,
    ForeignKey, Numeric, Index, Float,
)
from sqlalchemy.dialects.postgresql import UUID as PGUUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


# ==================== Enums ====================

class FranchiseeStatus(str, enum.Enum):
    """Status of franchisee."""
    PROSPECT = "PROSPECT"
    APPLICATION_PENDING = "APPLICATION_PENDING"
    UNDER_REVIEW = "UNDER_REVIEW"
    APPROVED = "APPROVED"
    ONBOARDING = "ONBOARDING"
    ACTIVE = "ACTIVE"
    SUSPENDED = "SUSPENDED"
    TERMINATED = "TERMINATED"
    INACTIVE = "INACTIVE"


class FranchiseeType(str, enum.Enum):
    """Type of franchisee."""
    EXCLUSIVE = "EXCLUSIVE"
    NON_EXCLUSIVE = "NON_EXCLUSIVE"
    MASTER = "MASTER"
    SUB_FRANCHISEE = "SUB_FRANCHISEE"
    DEALER = "DEALER"
    DISTRIBUTOR = "DISTRIBUTOR"


class FranchiseeTier(str, enum.Enum):
    """Tier/level of franchisee."""
    PLATINUM = "PLATINUM"
    GOLD = "GOLD"
    SILVER = "SILVER"
    BRONZE = "BRONZE"
    STANDARD = "STANDARD"


class ContractStatus(str, enum.Enum):
    """Status of franchisee contract."""
    DRAFT = "DRAFT"
    PENDING_APPROVAL = "PENDING_APPROVAL"
    ACTIVE = "ACTIVE"
    EXPIRED = "EXPIRED"
    RENEWED = "RENEWED"
    TERMINATED = "TERMINATED"
    CANCELLED = "CANCELLED"


class TerritoryStatus(str, enum.Enum):
    """Status of territory assignment."""
    PROPOSED = "PROPOSED"
    ACTIVE = "ACTIVE"
    DISPUTED = "DISPUTED"
    REVOKED = "REVOKED"
    EXPIRED = "EXPIRED"


class TrainingStatus(str, enum.Enum):
    """Status of training."""
    SCHEDULED = "SCHEDULED"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
    EXPIRED = "EXPIRED"


class TrainingType(str, enum.Enum):
    """Type of training."""
    ONBOARDING = "ONBOARDING"
    PRODUCT = "PRODUCT"
    SALES = "SALES"
    SERVICE = "SERVICE"
    COMPLIANCE = "COMPLIANCE"
    CERTIFICATION = "CERTIFICATION"
    REFRESHER = "REFRESHER"


class SupportTicketStatus(str, enum.Enum):
    """Status of support ticket."""
    OPEN = "OPEN"
    IN_PROGRESS = "IN_PROGRESS"
    WAITING_ON_FRANCHISEE = "WAITING_ON_FRANCHISEE"
    ESCALATED = "ESCALATED"
    RESOLVED = "RESOLVED"
    CLOSED = "CLOSED"


class SupportTicketPriority(str, enum.Enum):
    """Priority of support ticket."""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class SupportTicketCategory(str, enum.Enum):
    """Category of support ticket."""
    TECHNICAL = "TECHNICAL"
    BILLING = "BILLING"
    INVENTORY = "INVENTORY"
    MARKETING = "MARKETING"
    OPERATIONS = "OPERATIONS"
    COMPLIANCE = "COMPLIANCE"
    OTHER = "OTHER"


class AuditStatus(str, enum.Enum):
    """Status of compliance audit."""
    SCHEDULED = "SCHEDULED"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    ACTION_REQUIRED = "ACTION_REQUIRED"
    CLOSED = "CLOSED"
    CANCELLED = "CANCELLED"


class AuditType(str, enum.Enum):
    """Type of audit."""
    INITIAL = "INITIAL"
    PERIODIC = "PERIODIC"
    SURPRISE = "SURPRISE"
    COMPLIANCE = "COMPLIANCE"
    QUALITY = "QUALITY"
    FINANCIAL = "FINANCIAL"


class AuditResult(str, enum.Enum):
    """Result of audit."""
    PASSED = "PASSED"
    PASSED_WITH_OBSERVATIONS = "PASSED_WITH_OBSERVATIONS"
    FAILED = "FAILED"
    REQUIRES_FOLLOW_UP = "REQUIRES_FOLLOW_UP"


class ServiceCapability(str, enum.Enum):
    """Types of services a franchisee can provide."""
    INSTALLATION = "INSTALLATION"
    REPAIR = "REPAIR"
    MAINTENANCE = "MAINTENANCE"
    AMC_SERVICE = "AMC_SERVICE"
    DEMO = "DEMO"
    FULL_SERVICE = "FULL_SERVICE"  # All services


# ==================== Models ====================

class Franchisee(Base):
    """Franchisee master entity."""
    __tablename__ = "franchisees"

    # Production uses VARCHAR for id, not UUID
    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )

    # Identification
    franchisee_code: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(200), index=True)
    legal_name: Mapped[Optional[str]] = mapped_column(String(300))

    # Type and Status
    franchisee_type: Mapped[str] = mapped_column(
        String(50), default="DEALER", comment="EXCLUSIVE, NON_EXCLUSIVE, MASTER, SUB_FRANCHISEE, DEALER, DISTRIBUTOR"
    )
    status: Mapped[str] = mapped_column(
        String(50), default="PROSPECT", index=True, comment="PROSPECT, APPLICATION_PENDING, UNDER_REVIEW, APPROVED, ONBOARDING, ACTIVE, SUSPENDED, TERMINATED, INACTIVE"
    )
    tier: Mapped[str] = mapped_column(
        String(50), default="STANDARD", comment="PLATINUM, GOLD, SILVER, BRONZE, STANDARD"
    )

    # Contact Information
    contact_person: Mapped[str] = mapped_column(String(200))
    email: Mapped[str] = mapped_column(String(255), index=True)
    phone: Mapped[str] = mapped_column(String(20), index=True)
    alternate_phone: Mapped[Optional[str]] = mapped_column(String(20))
    website: Mapped[Optional[str]] = mapped_column(String(500))

    # Address
    address_line1: Mapped[str] = mapped_column(String(500))
    address_line2: Mapped[Optional[str]] = mapped_column(String(500))
    city: Mapped[str] = mapped_column(String(100), index=True)
    state: Mapped[str] = mapped_column(String(100), index=True)
    pincode: Mapped[str] = mapped_column(String(10), index=True)
    country: Mapped[str] = mapped_column(String(100), default="India")
    latitude: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 7))
    longitude: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 7))

    # Business Details
    gst_number: Mapped[Optional[str]] = mapped_column(String(20))
    pan_number: Mapped[Optional[str]] = mapped_column(String(20))
    cin_number: Mapped[Optional[str]] = mapped_column(String(30))
    bank_name: Mapped[Optional[str]] = mapped_column(String(200))
    bank_account_number: Mapped[Optional[str]] = mapped_column(String(50))
    bank_ifsc: Mapped[Optional[str]] = mapped_column(String(20))

    # Hierarchy (VARCHAR FK to match parent table)
    parent_franchisee_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("franchisees.id"), nullable=True
    )
    region_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("regions.id"), nullable=True
    )

    # Commercial Terms
    credit_limit: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=0)
    current_outstanding: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=0)
    payment_terms_days: Mapped[int] = mapped_column(Integer, default=30)
    commission_rate: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=0)
    security_deposit: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=0)

    # Performance Metrics (cached)
    total_orders: Mapped[int] = mapped_column(Integer, default=0)
    total_revenue: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=0)
    avg_monthly_revenue: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=0)
    customer_rating: Mapped[Decimal] = mapped_column(Numeric(3, 2), default=0)
    compliance_score: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=0)

    # Dates
    application_date: Mapped[Optional[date]] = mapped_column(Date)
    approval_date: Mapped[Optional[date]] = mapped_column(Date)
    activation_date: Mapped[Optional[date]] = mapped_column(Date)
    termination_date: Mapped[Optional[date]] = mapped_column(Date)
    last_order_date: Mapped[Optional[date]] = mapped_column(Date)
    last_audit_date: Mapped[Optional[date]] = mapped_column(Date)

    # Documents and Notes
    documents: Mapped[Optional[dict]] = mapped_column(JSONB)  # {type: url}
    notes: Mapped[Optional[str]] = mapped_column(Text)

    # Tracking
    created_by_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    approved_by_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    account_manager_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    parent_franchisee = relationship("Franchisee", remote_side=[id], backref="sub_franchisees")
    contracts = relationship("FranchiseeContract", back_populates="franchisee")
    territories = relationship("FranchiseeTerritory", back_populates="franchisee")
    trainings = relationship("FranchiseeTraining", back_populates="franchisee")
    support_tickets = relationship("FranchiseeSupport", back_populates="franchisee")
    audits = relationship("FranchiseeAudit", back_populates="franchisee")
    performance_records = relationship("FranchiseePerformance", back_populates="franchisee")
    serviceability = relationship("FranchiseeServiceability", back_populates="franchisee")

    __table_args__ = (
        Index("ix_franchisee_status_tier", "status", "tier"),
        Index("ix_franchisee_city_state", "city", "state"),
    )


class FranchiseeContract(Base):
    """Franchisee contract/agreement."""
    __tablename__ = "franchisee_contracts"

    # Production uses VARCHAR for id, not UUID
    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    franchisee_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("franchisees.id"), index=True
    )

    # Contract Details
    contract_number: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    contract_type: Mapped[str] = mapped_column(String(50))  # FRANCHISE_AGREEMENT, DEALER_AGREEMENT, etc.
    status: Mapped[str] = mapped_column(
        String(50), default="DRAFT", index=True, comment="DRAFT, PENDING_APPROVAL, ACTIVE, EXPIRED, RENEWED, TERMINATED, CANCELLED"
    )

    # Terms
    start_date: Mapped[date] = mapped_column(Date)
    end_date: Mapped[date] = mapped_column(Date)
    auto_renewal: Mapped[bool] = mapped_column(Boolean, default=False)
    renewal_terms_days: Mapped[int] = mapped_column(Integer, default=365)
    notice_period_days: Mapped[int] = mapped_column(Integer, default=90)

    # Financial Terms
    franchise_fee: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=0)
    royalty_percentage: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=0)
    marketing_fee_percentage: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=0)
    minimum_purchase_commitment: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=0)

    # Territory
    territory_exclusive: Mapped[bool] = mapped_column(Boolean, default=False)
    territory_description: Mapped[Optional[str]] = mapped_column(Text)

    # Documents
    document_url: Mapped[Optional[str]] = mapped_column(String(500))
    signed_document_url: Mapped[Optional[str]] = mapped_column(String(500))

    # Approval
    approved_by_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    approved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    # Termination
    terminated_by_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    termination_reason: Mapped[Optional[str]] = mapped_column(Text)
    terminated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    notes: Mapped[Optional[str]] = mapped_column(Text)
    created_by_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    franchisee = relationship("Franchisee", back_populates="contracts")


class FranchiseeTerritory(Base):
    """Territory/area assignment for franchisee."""
    __tablename__ = "franchisee_territories"

    # Production uses VARCHAR for id, not UUID
    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    franchisee_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("franchisees.id"), index=True
    )

    # Territory Definition
    territory_name: Mapped[str] = mapped_column(String(200))
    territory_type: Mapped[str] = mapped_column(String(50))  # PINCODE, CITY, DISTRICT, STATE
    status: Mapped[str] = mapped_column(
        String(50), default="ACTIVE", index=True, comment="PROPOSED, ACTIVE, DISPUTED, REVOKED, EXPIRED"
    )
    is_exclusive: Mapped[bool] = mapped_column(Boolean, default=False)

    # Geographic Boundaries
    pincodes: Mapped[Optional[List[str]]] = mapped_column(JSONB)  # List of pincodes
    cities: Mapped[Optional[List[str]]] = mapped_column(JSONB)
    districts: Mapped[Optional[List[str]]] = mapped_column(JSONB)
    states: Mapped[Optional[List[str]]] = mapped_column(JSONB)
    geo_boundary: Mapped[Optional[dict]] = mapped_column(JSONB)  # GeoJSON polygon

    # Validity
    effective_from: Mapped[date] = mapped_column(Date)
    effective_to: Mapped[Optional[date]] = mapped_column(Date)

    # Performance in Territory
    total_customers: Mapped[int] = mapped_column(Integer, default=0)
    total_orders: Mapped[int] = mapped_column(Integer, default=0)
    total_revenue: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=0)

    notes: Mapped[Optional[str]] = mapped_column(Text)
    created_by_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    franchisee = relationship("Franchisee", back_populates="territories")


class FranchiseeServiceability(Base):
    """
    Pincode-level serviceability mapping for franchisees.

    This table enables efficient pincode-based service request allocation:
    - One row per pincode per franchisee
    - Indexed for fast lookups
    - Supports service type filtering
    - Includes priority for load balancing
    """
    __tablename__ = "franchisee_serviceability"

    # Production uses VARCHAR for id, not UUID
    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    franchisee_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("franchisees.id"), index=True
    )
    territory_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("franchisee_territories.id"), nullable=True
    )

    # Pincode mapping (indexed for fast lookups)
    pincode: Mapped[str] = mapped_column(String(10), index=True, nullable=False)
    city: Mapped[Optional[str]] = mapped_column(String(100))
    district: Mapped[Optional[str]] = mapped_column(String(100))
    state: Mapped[Optional[str]] = mapped_column(String(100))

    # Service capabilities for this pincode
    service_types: Mapped[List[str]] = mapped_column(
        JSONB, default=list
    )  # ["INSTALLATION", "REPAIR", "MAINTENANCE", "AMC_SERVICE"]

    # Availability and priority
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    priority: Mapped[int] = mapped_column(Integer, default=1)  # Lower = higher priority
    max_daily_capacity: Mapped[int] = mapped_column(Integer, default=10)  # Max jobs per day
    current_load: Mapped[int] = mapped_column(Integer, default=0)  # Current assigned jobs

    # SLA settings for this pincode
    expected_response_hours: Mapped[int] = mapped_column(Integer, default=4)  # Hours to respond
    expected_completion_hours: Mapped[int] = mapped_column(Integer, default=48)  # Hours to complete

    # Performance metrics for this pincode
    total_jobs_completed: Mapped[int] = mapped_column(Integer, default=0)
    avg_rating: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    on_time_completion_rate: Mapped[float] = mapped_column(Float, default=100.0)  # Percentage

    # Timestamps
    effective_from: Mapped[date] = mapped_column(Date, default=date.today)
    effective_to: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    franchisee = relationship("Franchisee", back_populates="serviceability")
    territory = relationship("FranchiseeTerritory")

    # Unique constraint: One entry per pincode per franchisee
    __table_args__ = (
        Index("ix_franchisee_pincode_active", "pincode", "is_active"),
        Index("ix_franchisee_serviceability_lookup", "pincode", "is_active", "priority"),
    )


class FranchiseePerformance(Base):
    """Monthly/periodic performance tracking."""
    __tablename__ = "franchisee_performance"

    # Production uses VARCHAR for id, not UUID
    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    franchisee_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("franchisees.id"), index=True
    )

    # Period
    period_type: Mapped[str] = mapped_column(String(20))  # MONTHLY, QUARTERLY, YEARLY
    period_start: Mapped[date] = mapped_column(Date, index=True)
    period_end: Mapped[date] = mapped_column(Date)

    # Sales Metrics
    total_orders: Mapped[int] = mapped_column(Integer, default=0)
    total_units_sold: Mapped[int] = mapped_column(Integer, default=0)
    gross_revenue: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=0)
    net_revenue: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=0)
    returns_value: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=0)

    # Targets
    target_revenue: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=0)
    target_orders: Mapped[int] = mapped_column(Integer, default=0)
    target_achievement_percentage: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=0)

    # Customer Metrics
    new_customers: Mapped[int] = mapped_column(Integer, default=0)
    repeat_customers: Mapped[int] = mapped_column(Integer, default=0)
    customer_complaints: Mapped[int] = mapped_column(Integer, default=0)
    avg_customer_rating: Mapped[Decimal] = mapped_column(Numeric(3, 2), default=0)

    # Service Metrics
    installations_completed: Mapped[int] = mapped_column(Integer, default=0)
    service_calls_handled: Mapped[int] = mapped_column(Integer, default=0)
    avg_response_time_hours: Mapped[Decimal] = mapped_column(Numeric(6, 2), default=0)
    first_time_fix_rate: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=0)

    # Financial
    commission_earned: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=0)
    incentives_earned: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=0)
    penalties_applied: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=0)

    # Scores
    overall_score: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=0)
    sales_score: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=0)
    service_score: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=0)
    compliance_score: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=0)

    # Ranking
    rank_in_region: Mapped[Optional[int]] = mapped_column(Integer)
    rank_overall: Mapped[Optional[int]] = mapped_column(Integer)

    notes: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    franchisee = relationship("Franchisee", back_populates="performance_records")

    __table_args__ = (
        Index("ix_franchisee_performance_period", "franchisee_id", "period_start"),
    )


class FranchiseeTraining(Base):
    """Training and certification tracking."""
    __tablename__ = "franchisee_trainings"

    # Production uses VARCHAR for id, not UUID
    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    franchisee_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("franchisees.id"), index=True
    )

    # Training Details
    training_code: Mapped[str] = mapped_column(String(50), index=True)
    training_name: Mapped[str] = mapped_column(String(200))
    training_type: Mapped[str] = mapped_column(String(50), index=True, comment="ONBOARDING, PRODUCT, SALES, SERVICE, COMPLIANCE, CERTIFICATION, REFRESHER")
    status: Mapped[str] = mapped_column(
        String(50), default="SCHEDULED", index=True, comment="SCHEDULED, IN_PROGRESS, COMPLETED, FAILED, CANCELLED, EXPIRED"
    )

    # Description
    description: Mapped[Optional[str]] = mapped_column(Text)
    objectives: Mapped[Optional[List[str]]] = mapped_column(JSONB)

    # Schedule
    scheduled_date: Mapped[date] = mapped_column(Date)
    start_time: Mapped[Optional[str]] = mapped_column(String(10))
    duration_hours: Mapped[Decimal] = mapped_column(Numeric(4, 1), default=1)

    # Location/Mode
    mode: Mapped[str] = mapped_column(String(20))  # ONLINE, IN_PERSON, HYBRID
    location: Mapped[Optional[str]] = mapped_column(String(500))
    meeting_link: Mapped[Optional[str]] = mapped_column(String(500))

    # Attendance
    attendee_name: Mapped[str] = mapped_column(String(200))
    attendee_email: Mapped[Optional[str]] = mapped_column(String(255))
    attendee_phone: Mapped[Optional[str]] = mapped_column(String(20))
    attended: Mapped[bool] = mapped_column(Boolean, default=False)
    attendance_percentage: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=0)

    # Assessment
    has_assessment: Mapped[bool] = mapped_column(Boolean, default=False)
    assessment_score: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 2))
    passing_score: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=70)
    passed: Mapped[bool] = mapped_column(Boolean, default=False)
    attempts: Mapped[int] = mapped_column(Integer, default=0)

    # Certification
    certificate_issued: Mapped[bool] = mapped_column(Boolean, default=False)
    certificate_number: Mapped[Optional[str]] = mapped_column(String(50))
    certificate_url: Mapped[Optional[str]] = mapped_column(String(500))
    certificate_expiry: Mapped[Optional[date]] = mapped_column(Date)

    # Completion
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    feedback: Mapped[Optional[str]] = mapped_column(Text)
    feedback_rating: Mapped[Optional[int]] = mapped_column(Integer)

    # Trainer
    trainer_name: Mapped[Optional[str]] = mapped_column(String(200))
    trainer_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )

    notes: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    franchisee = relationship("Franchisee", back_populates="trainings")


class FranchiseeSupport(Base):
    """Support tickets from franchisees."""
    __tablename__ = "franchisee_support_tickets"

    # Production uses VARCHAR for id, not UUID
    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    franchisee_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("franchisees.id"), index=True
    )

    # Ticket Details
    ticket_number: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    subject: Mapped[str] = mapped_column(String(500))
    description: Mapped[str] = mapped_column(Text)

    # Classification
    category: Mapped[str] = mapped_column(
        String(50), index=True, comment="TECHNICAL, BILLING, INVENTORY, MARKETING, OPERATIONS, COMPLIANCE, OTHER"
    )
    priority: Mapped[str] = mapped_column(
        String(20), default="MEDIUM", index=True, comment="LOW, MEDIUM, HIGH, CRITICAL"
    )
    status: Mapped[str] = mapped_column(
        String(50), default="OPEN", index=True, comment="OPEN, IN_PROGRESS, WAITING_ON_FRANCHISEE, ESCALATED, RESOLVED, CLOSED"
    )

    # Contact
    contact_name: Mapped[str] = mapped_column(String(200))
    contact_email: Mapped[Optional[str]] = mapped_column(String(255))
    contact_phone: Mapped[Optional[str]] = mapped_column(String(20))

    # Assignment
    assigned_to_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    assigned_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    # SLA
    sla_due_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    sla_breached: Mapped[bool] = mapped_column(Boolean, default=False)

    # Resolution
    resolution: Mapped[Optional[str]] = mapped_column(Text)
    resolved_by_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    resolved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    resolution_time_hours: Mapped[Optional[Decimal]] = mapped_column(Numeric(8, 2))

    # Feedback
    satisfaction_rating: Mapped[Optional[int]] = mapped_column(Integer)  # 1-5
    feedback: Mapped[Optional[str]] = mapped_column(Text)

    # Escalation
    is_escalated: Mapped[bool] = mapped_column(Boolean, default=False)
    escalated_to_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    escalated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    escalation_reason: Mapped[Optional[str]] = mapped_column(Text)

    # Attachments
    attachments: Mapped[Optional[List[str]]] = mapped_column(JSONB)

    # Tracking
    first_response_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    closed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    reopen_count: Mapped[int] = mapped_column(Integer, default=0)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    franchisee = relationship("Franchisee", back_populates="support_tickets")
    comments = relationship("FranchiseeSupportComment", back_populates="ticket")

    __table_args__ = (
        Index("ix_support_status_priority", "status", "priority"),
    )


class FranchiseeSupportComment(Base):
    """Comments on support tickets."""
    __tablename__ = "franchisee_support_comments"

    # Production uses VARCHAR for id, not UUID
    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    ticket_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("franchisee_support_tickets.id"), index=True
    )

    comment: Mapped[str] = mapped_column(Text)
    is_internal: Mapped[bool] = mapped_column(Boolean, default=False)  # Internal vs visible to franchisee

    # Author
    author_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    author_type: Mapped[str] = mapped_column(String(20))  # STAFF, FRANCHISEE
    author_name: Mapped[str] = mapped_column(String(200))

    attachments: Mapped[Optional[List[str]]] = mapped_column(JSONB)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    # Relationships
    ticket = relationship("FranchiseeSupport", back_populates="comments")


class FranchiseeAudit(Base):
    """Compliance and quality audits."""
    __tablename__ = "franchisee_audits"

    # Production uses VARCHAR for id, not UUID
    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    franchisee_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("franchisees.id"), index=True
    )

    # Audit Details
    audit_number: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    audit_type: Mapped[str] = mapped_column(String(50), index=True, comment="INITIAL, PERIODIC, SURPRISE, COMPLIANCE, QUALITY, FINANCIAL")
    status: Mapped[str] = mapped_column(
        String(50), default="SCHEDULED", index=True, comment="SCHEDULED, IN_PROGRESS, COMPLETED, ACTION_REQUIRED, CLOSED, CANCELLED"
    )

    # Schedule
    scheduled_date: Mapped[date] = mapped_column(Date)
    actual_date: Mapped[Optional[date]] = mapped_column(Date)

    # Auditor
    auditor_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    auditor_name: Mapped[str] = mapped_column(String(200))

    # Checklist and Findings
    checklist: Mapped[Optional[List[dict]]] = mapped_column(JSONB)  # [{item, score, remarks}]
    findings: Mapped[Optional[str]] = mapped_column(Text)
    observations: Mapped[Optional[List[str]]] = mapped_column(JSONB)
    non_conformities: Mapped[Optional[List[dict]]] = mapped_column(JSONB)  # [{item, severity, action}]

    # Scores
    overall_score: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 2))
    compliance_score: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 2))
    quality_score: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 2))

    # Result
    result: Mapped[Optional[str]] = mapped_column(String(50), comment="PASSED, PASSED_WITH_OBSERVATIONS, FAILED, REQUIRES_FOLLOW_UP")

    # Corrective Actions
    corrective_actions: Mapped[Optional[List[dict]]] = mapped_column(JSONB)  # [{action, due_date, status}]
    follow_up_required: Mapped[bool] = mapped_column(Boolean, default=False)
    follow_up_date: Mapped[Optional[date]] = mapped_column(Date)

    # Documents
    report_url: Mapped[Optional[str]] = mapped_column(String(500))
    evidence_urls: Mapped[Optional[List[str]]] = mapped_column(JSONB)

    # Completion
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    closed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    notes: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    franchisee = relationship("Franchisee", back_populates="audits")
