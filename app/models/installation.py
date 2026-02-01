"""Installation and Warranty model."""
from enum import Enum
from datetime import datetime, date, timezone
from sqlalchemy import Column, String, Text, Boolean, ForeignKey, Integer, DateTime, Date, Float, Numeric
from sqlalchemy.dialects.postgresql import UUID, JSONB
# Note: franchisee_id uses String(36) because franchisees.id is VARCHAR in production
from sqlalchemy.orm import relationship
import uuid

from app.database import Base, TimestampMixin


class InstallationStatus(str, Enum):
    """Installation status enum."""
    PENDING = "PENDING"
    SCHEDULED = "SCHEDULED"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"
    FAILED = "FAILED"


class Installation(Base, TimestampMixin):
    """Installation record for products."""

    __tablename__ = "installations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Identification
    installation_number = Column(String(50), unique=True, nullable=False, index=True)
    status = Column(
        String(50), default="PENDING", index=True,
        comment="PENDING, SCHEDULED, IN_PROGRESS, COMPLETED, CANCELLED, FAILED"
    )

    # Customer & Order
    customer_id = Column(UUID(as_uuid=True), ForeignKey("customers.id"), nullable=False, index=True)
    order_id = Column(UUID(as_uuid=True), ForeignKey("orders.id"))
    order_item_id = Column(UUID(as_uuid=True))

    # Product
    product_id = Column(UUID(as_uuid=True), ForeignKey("products.id"), nullable=False)
    variant_id = Column(UUID(as_uuid=True), ForeignKey("product_variants.id"))
    serial_number = Column(String(100), unique=True, index=True)
    stock_item_id = Column(UUID(as_uuid=True), ForeignKey("stock_items.id"))

    # Installation Address
    address_id = Column(UUID(as_uuid=True), ForeignKey("customer_addresses.id"))
    installation_address = Column(JSONB)  # Address snapshot
    installation_pincode = Column(String(10), index=True)
    installation_city = Column(String(100))
    latitude = Column(Float)
    longitude = Column(Float)

    # Scheduling
    preferred_date = Column(Date)
    preferred_time_slot = Column(String(50))
    scheduled_date = Column(Date)
    scheduled_time_slot = Column(String(50))

    # Assignment (Technician or Franchisee)
    technician_id = Column(UUID(as_uuid=True), ForeignKey("technicians.id"))
    franchisee_id = Column(String(36), ForeignKey("franchisees.id"))  # For franchisee allocation (VARCHAR in production)
    assigned_at = Column(DateTime)

    # Execution
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    installation_date = Column(Date)  # Actual installation date

    # Installation details
    installation_notes = Column(Text)
    pre_installation_checklist = Column(JSONB)  # Checklist items
    post_installation_checklist = Column(JSONB)
    installation_photos = Column(JSONB)  # URLs

    # Accessories installed
    accessories_used = Column(JSONB)  # [{"item": "", "quantity": 1}]

    # Water quality (for water purifiers)
    input_tds = Column(Integer)  # TDS before installation
    output_tds = Column(Integer)  # TDS after installation

    # Warranty
    warranty_start_date = Column(Date)
    warranty_end_date = Column(Date)
    warranty_months = Column(Integer, default=12)
    extended_warranty_months = Column(Integer, default=0)
    warranty_card_number = Column(String(50), unique=True)
    warranty_card_url = Column(String(500))

    # Customer sign-off
    customer_signature_url = Column(String(500))
    customer_feedback = Column(Text)
    customer_rating = Column(Integer)

    # Demo given
    demo_given = Column(Boolean, default=False)
    demo_notes = Column(Text)

    # Region
    region_id = Column(UUID(as_uuid=True), ForeignKey("regions.id"))

    notes = Column(Text)
    internal_notes = Column(Text)

    # Timestamps
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Audit
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"))

    # Relationships
    customer = relationship("Customer", back_populates="installations")
    order = relationship("Order")
    product = relationship("Product")
    variant = relationship("ProductVariant")
    stock_item = relationship("StockItem")
    address = relationship("CustomerAddress")
    technician = relationship("Technician")
    region = relationship("Region")
    creator = relationship("User")
    service_requests = relationship("ServiceRequest", back_populates="installation")
    amc_contracts = relationship("AMCContract", back_populates="installation")
    warranty_claims = relationship("WarrantyClaim", back_populates="installation")

    @property
    def is_under_warranty(self) -> bool:
        """Check if product is under warranty."""
        if self.warranty_end_date:
            return date.today() <= self.warranty_end_date
        return False

    @property
    def warranty_days_remaining(self) -> int:
        """Get warranty days remaining."""
        if self.warranty_end_date:
            return max(0, (self.warranty_end_date - date.today()).days)
        return 0

    def __repr__(self):
        return f"<Installation {self.installation_number}>"


class WarrantyClaim(Base, TimestampMixin):
    """Warranty claim records."""

    __tablename__ = "warranty_claims"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    claim_number = Column(String(50), unique=True, nullable=False, index=True)

    # References
    installation_id = Column(UUID(as_uuid=True), ForeignKey("installations.id"), nullable=False, index=True)
    service_request_id = Column(UUID(as_uuid=True), ForeignKey("service_requests.id"))
    customer_id = Column(UUID(as_uuid=True), ForeignKey("customers.id"), nullable=False)

    # Product
    product_id = Column(UUID(as_uuid=True), ForeignKey("products.id"), nullable=False)
    serial_number = Column(String(100), nullable=False, index=True)  # Required - links warranty claim to specific product unit

    # Claim details
    claim_type = Column(String(50))  # repair, replacement, refund
    issue_description = Column(Text, nullable=False)
    diagnosis = Column(Text)

    # Status
    status = Column(String(50), default="pending")  # pending, approved, rejected, in_progress, completed

    # Decision
    is_valid_claim = Column(Boolean)
    rejection_reason = Column(Text)
    approved_by = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    approved_at = Column(DateTime)

    # Resolution
    resolution_type = Column(String(50))  # repaired, replaced, refunded
    resolution_notes = Column(Text)
    replacement_serial = Column(String(100))  # If replaced
    refund_amount = Column(Numeric(12, 2))  # If refunded

    # Costs (internal tracking)
    parts_cost = Column(Numeric(12, 2), default=0)
    labor_cost = Column(Numeric(12, 2), default=0)
    total_cost = Column(Numeric(12, 2), default=0)

    # Dates
    claim_date = Column(Date)
    resolved_date = Column(Date)

    notes = Column(Text)

    # Audit
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"))

    # Relationships
    installation = relationship("Installation", back_populates="warranty_claims")
    service_request = relationship("ServiceRequest")
    customer = relationship("Customer")
    product = relationship("Product")
    approver = relationship("User", foreign_keys=[approved_by])
    creator = relationship("User", foreign_keys=[created_by])

    def __repr__(self):
        return f"<WarrantyClaim {self.claim_number}>"
