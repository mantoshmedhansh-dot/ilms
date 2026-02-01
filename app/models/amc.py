"""AMC (Annual Maintenance Contract) model."""
from enum import Enum
from datetime import datetime, date, timezone
from sqlalchemy import Column, String, Text, Boolean, ForeignKey, Integer, DateTime, Date, Float, Numeric
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
import uuid

from app.database import Base, TimestampMixin


class AMCType(str, Enum):
    """AMC type enum."""
    STANDARD = "STANDARD"  # Basic AMC
    COMPREHENSIVE = "COMPREHENSIVE"  # Parts + Labor included
    EXTENDED_WARRANTY = "EXTENDED_WARRANTY"
    PLATINUM = "PLATINUM"  # Premium service


class AMCStatus(str, Enum):
    """AMC status enum."""
    DRAFT = "DRAFT"
    PENDING_PAYMENT = "PENDING_PAYMENT"
    ACTIVE = "ACTIVE"
    EXPIRED = "EXPIRED"
    CANCELLED = "CANCELLED"
    RENEWED = "RENEWED"


class AMCContract(Base, TimestampMixin):
    """AMC Contract model."""

    __tablename__ = "amc_contracts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Identification
    contract_number = Column(String(50), unique=True, nullable=False, index=True)
    amc_type = Column(
        String(50), default="STANDARD",
        comment="STANDARD, COMPREHENSIVE, EXTENDED_WARRANTY, PLATINUM"
    )
    status = Column(
        String(50), default="DRAFT", index=True,
        comment="DRAFT, PENDING_PAYMENT, ACTIVE, EXPIRED, CANCELLED, RENEWED"
    )

    # Customer
    customer_id = Column(UUID(as_uuid=True), ForeignKey("customers.id"), nullable=False, index=True)
    customer_address_id = Column(UUID(as_uuid=True), ForeignKey("customer_addresses.id"))

    # Product/Installation
    product_id = Column(UUID(as_uuid=True), ForeignKey("products.id"), nullable=False)
    installation_id = Column(UUID(as_uuid=True), ForeignKey("installations.id"))
    serial_number = Column(String(100), nullable=False, index=True)  # Required - links AMC to specific product unit

    # Duration
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    duration_months = Column(Integer, default=12)

    # Services included
    total_services = Column(Integer, default=2)  # Number of services included
    services_used = Column(Integer, default=0)
    services_remaining = Column(Integer, default=2)

    # Pricing
    base_price = Column(Numeric(12, 2), default=0)
    tax_amount = Column(Numeric(12, 2), default=0)
    discount_amount = Column(Numeric(12, 2), default=0)
    total_amount = Column(Numeric(12, 2), default=0)

    # Payment
    payment_status = Column(String(50), default="pending")
    payment_mode = Column(String(50))
    payment_reference = Column(String(100))
    paid_at = Column(DateTime)

    # Benefits
    parts_covered = Column(Boolean, default=False)
    labor_covered = Column(Boolean, default=True)
    emergency_support = Column(Boolean, default=False)
    priority_service = Column(Boolean, default=False)
    discount_on_parts = Column(Numeric(5, 2), default=0)  # Percentage
    terms_and_conditions = Column(Text)

    # Renewal
    is_renewable = Column(Boolean, default=True)
    renewal_reminder_sent = Column(Boolean, default=False)
    renewed_from_id = Column(UUID(as_uuid=True), ForeignKey("amc_contracts.id"))
    renewed_to_id = Column(UUID(as_uuid=True), ForeignKey("amc_contracts.id"))

    # Service schedule
    service_schedule = Column(JSONB)  # [{"month": 1, "scheduled_date": null, "completed_date": null}]
    next_service_due = Column(Date)

    notes = Column(Text)
    internal_notes = Column(Text)

    # Audit
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    approved_by = Column(UUID(as_uuid=True), ForeignKey("users.id"))

    # Relationships
    customer = relationship("Customer", back_populates="amc_contracts")
    customer_address = relationship("CustomerAddress")
    product = relationship("Product")
    installation = relationship("Installation", back_populates="amc_contracts")
    service_requests = relationship("ServiceRequest", back_populates="amc")
    renewed_from = relationship("AMCContract", foreign_keys=[renewed_from_id], remote_side=[id])
    renewed_to = relationship("AMCContract", foreign_keys=[renewed_to_id], remote_side=[id])
    creator = relationship("User", foreign_keys=[created_by])
    approver = relationship("User", foreign_keys=[approved_by])

    @property
    def is_active(self) -> bool:
        """Check if AMC is currently active."""
        today = date.today()
        return self.status == AMCStatus.ACTIVE and self.start_date <= today <= self.end_date

    @property
    def days_remaining(self) -> int:
        """Get days remaining in contract."""
        if self.end_date:
            return max(0, (self.end_date - date.today()).days)
        return 0

    def __repr__(self):
        return f"<AMCContract {self.contract_number}>"


class AMCPlan(Base, TimestampMixin):
    """AMC plan templates."""

    __tablename__ = "amc_plans"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    name = Column(String(200), nullable=False)
    code = Column(String(20), unique=True, nullable=False)
    amc_type = Column(
        String(50), default="STANDARD",
        comment="STANDARD, COMPREHENSIVE, EXTENDED_WARRANTY, PLATINUM"
    )

    # Applicable products
    category_id = Column(UUID(as_uuid=True), ForeignKey("categories.id"))  # If specific to category
    product_ids = Column(JSONB)  # List of specific product IDs if applicable

    # Duration options
    duration_months = Column(Integer, default=12)

    # Pricing
    base_price = Column(Numeric(12, 2), default=0)
    tax_rate = Column(Numeric(5, 2), default=18)

    # Services
    services_included = Column(Integer, default=2)

    # Benefits
    parts_covered = Column(Boolean, default=False)
    labor_covered = Column(Boolean, default=True)
    emergency_support = Column(Boolean, default=False)
    priority_service = Column(Boolean, default=False)
    discount_on_parts = Column(Numeric(5, 2), default=0)

    # Terms
    terms_and_conditions = Column(Text)
    description = Column(Text)

    is_active = Column(Boolean, default=True)
    sort_order = Column(Integer, default=0)

    # Relationships
    category = relationship("Category")

    def __repr__(self):
        return f"<AMCPlan {self.code}: {self.name}>"
