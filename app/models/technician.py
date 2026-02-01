"""Technician model for service operations."""
from enum import Enum
from datetime import datetime, date, timezone as tz
from sqlalchemy import Column, String, Text, Boolean, ForeignKey, Integer, DateTime, Date, Float
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
import uuid

from app.database import Base, TimestampMixin


class TechnicianStatus(str, Enum):
    """Technician status enum."""
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    ON_LEAVE = "ON_LEAVE"
    TRAINING = "TRAINING"
    RESIGNED = "RESIGNED"


class TechnicianType(str, Enum):
    """Technician type enum."""
    INTERNAL = "INTERNAL"  # Company employee
    EXTERNAL = "EXTERNAL"  # Outsourced/Contract
    FREELANCE = "FREELANCE"


class SkillLevel(str, Enum):
    """Skill level enum."""
    TRAINEE = "TRAINEE"
    JUNIOR = "JUNIOR"
    SENIOR = "SENIOR"
    EXPERT = "EXPERT"
    MASTER = "MASTER"


class Technician(Base, TimestampMixin):
    """Technician model for service personnel."""

    __tablename__ = "technicians"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Basic Info
    employee_code = Column(String(20), unique=True, nullable=False, index=True)
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100))
    phone = Column(String(20), nullable=False, index=True)
    alternate_phone = Column(String(20))
    email = Column(String(100))

    # Link to User account (if they have system access)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), unique=True)

    # Employment
    technician_type = Column(String(50), default="INTERNAL", comment="INTERNAL, EXTERNAL, FREELANCE")
    status = Column(String(50), default="ACTIVE", index=True, comment="ACTIVE, INACTIVE, ON_LEAVE, TRAINING, RESIGNED")
    date_of_joining = Column(Date)
    date_of_leaving = Column(Date)

    # Skills
    skill_level = Column(String(50), default="JUNIOR", comment="TRAINEE, JUNIOR, SENIOR, EXPERT, MASTER")
    specializations = Column(JSONB)  # ["RO Systems", "Water Purifiers", "AC"]
    certifications = Column(JSONB)  # [{"name": "...", "date": "...", "expiry": "..."}]

    # Location/Assignment
    region_id = Column(UUID(as_uuid=True), ForeignKey("regions.id"))
    assigned_warehouse_id = Column(UUID(as_uuid=True), ForeignKey("warehouses.id"))
    service_pincodes = Column(JSONB)  # List of serviceable pincodes

    # Address
    address = Column(Text)
    city = Column(String(100))
    state = Column(String(100))
    pincode = Column(String(10))

    # Documents
    aadhaar_number = Column(String(20))
    pan_number = Column(String(20))
    driving_license = Column(String(50))
    id_proof_url = Column(String(500))
    photo_url = Column(String(500))

    # Bank Details
    bank_name = Column(String(100))
    bank_account_number = Column(String(50))
    ifsc_code = Column(String(20))

    # Performance metrics (updated periodically)
    total_jobs_completed = Column(Integer, default=0)
    average_rating = Column(Float, default=0)
    total_ratings = Column(Integer, default=0)
    current_month_jobs = Column(Integer, default=0)

    # Availability
    is_available = Column(Boolean, default=True)
    last_job_date = Column(DateTime(timezone=True))
    current_location_lat = Column(Float)
    current_location_lng = Column(Float)
    location_updated_at = Column(DateTime(timezone=True))

    notes = Column(Text)

    # Relationships
    user = relationship("User", back_populates="technician_profile")
    region = relationship("Region")
    warehouse = relationship("Warehouse")
    service_requests = relationship("ServiceRequest", back_populates="technician")
    job_history = relationship("TechnicianJobHistory", back_populates="technician")

    @property
    def full_name(self) -> str:
        """Get full name."""
        if self.last_name:
            return f"{self.first_name} {self.last_name}"
        return self.first_name

    def __repr__(self):
        return f"<Technician {self.employee_code}: {self.full_name}>"


class TechnicianJobHistory(Base, TimestampMixin):
    """Technician job history for tracking assignments."""

    __tablename__ = "technician_job_history"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    technician_id = Column(UUID(as_uuid=True), ForeignKey("technicians.id"), nullable=False, index=True)
    service_request_id = Column(UUID(as_uuid=True), ForeignKey("service_requests.id"), nullable=False)

    # Assignment
    assigned_at = Column(DateTime(timezone=True), default=lambda: datetime.now(tz.utc))
    assigned_by = Column(UUID(as_uuid=True), ForeignKey("users.id"))

    # Timing
    started_at = Column(DateTime(timezone=True))
    completed_at = Column(DateTime(timezone=True))
    time_taken_minutes = Column(Integer)

    # Status
    status = Column(String(50))  # assigned, started, completed, cancelled, reassigned
    reassignment_reason = Column(Text)

    # Rating
    customer_rating = Column(Integer)  # 1-5
    customer_feedback = Column(Text)

    notes = Column(Text)

    # Relationships
    technician = relationship("Technician", back_populates="job_history")
    service_request = relationship("ServiceRequest", back_populates="technician_history")
    assigner = relationship("User")

    def __repr__(self):
        return f"<TechnicianJobHistory {self.id}>"


class TechnicianLeave(Base, TimestampMixin):
    """Technician leave records."""

    __tablename__ = "technician_leaves"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    technician_id = Column(UUID(as_uuid=True), ForeignKey("technicians.id"), nullable=False, index=True)

    leave_type = Column(String(50))  # sick, casual, earned, emergency
    from_date = Column(Date, nullable=False)
    to_date = Column(Date, nullable=False)
    reason = Column(Text)

    status = Column(String(50), default="pending")  # pending, approved, rejected, cancelled
    approved_by = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    approved_at = Column(DateTime(timezone=True))
    rejection_reason = Column(Text)

    # Relationships
    technician = relationship("Technician")
    approver = relationship("User")

    def __repr__(self):
        return f"<TechnicianLeave {self.id}>"
