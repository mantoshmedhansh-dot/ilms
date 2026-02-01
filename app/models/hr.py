"""HR & Payroll models with Indian compliance.

Supports:
- Department hierarchy
- Employee management (linked to User accounts)
- Attendance tracking
- Leave management
- Payroll processing with PF, ESIC, TDS, Professional Tax
"""
import uuid
from datetime import datetime, date, timezone
from enum import Enum
from typing import TYPE_CHECKING, Optional, List
from decimal import Decimal

from sqlalchemy import String, Boolean, DateTime, ForeignKey, Integer, Text, Numeric, Date
from sqlalchemy import UniqueConstraint, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.user import User


# ==================== Enums ====================

class EmploymentType(str, Enum):
    """Type of employment."""
    FULL_TIME = "FULL_TIME"
    PART_TIME = "PART_TIME"
    CONTRACT = "CONTRACT"
    INTERN = "INTERN"
    CONSULTANT = "CONSULTANT"


class EmployeeStatus(str, Enum):
    """Employee status in organization."""
    ACTIVE = "ACTIVE"
    ON_NOTICE = "ON_NOTICE"
    ON_LEAVE = "ON_LEAVE"
    SUSPENDED = "SUSPENDED"
    RESIGNED = "RESIGNED"
    TERMINATED = "TERMINATED"


class LeaveType(str, Enum):
    """Types of leave available."""
    CASUAL = "CASUAL"
    SICK = "SICK"
    EARNED = "EARNED"
    MATERNITY = "MATERNITY"
    PATERNITY = "PATERNITY"
    COMPENSATORY = "COMPENSATORY"
    UNPAID = "UNPAID"


class LeaveStatus(str, Enum):
    """Leave request status."""
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    CANCELLED = "CANCELLED"


class AttendanceStatus(str, Enum):
    """Daily attendance status."""
    PRESENT = "PRESENT"
    ABSENT = "ABSENT"
    HALF_DAY = "HALF_DAY"
    ON_LEAVE = "ON_LEAVE"
    HOLIDAY = "HOLIDAY"
    WEEKEND = "WEEKEND"


class PayrollStatus(str, Enum):
    """Payroll processing status."""
    DRAFT = "DRAFT"
    PROCESSING = "PROCESSING"
    PROCESSED = "PROCESSED"
    APPROVED = "APPROVED"
    PAID = "PAID"


class Gender(str, Enum):
    """Gender options."""
    MALE = "MALE"
    FEMALE = "FEMALE"
    OTHER = "OTHER"


class MaritalStatus(str, Enum):
    """Marital status options."""
    SINGLE = "SINGLE"
    MARRIED = "MARRIED"
    DIVORCED = "DIVORCED"
    WIDOWED = "WIDOWED"


# ==================== Department ====================

class Department(Base):
    """
    Department model with hierarchy support.
    """
    __tablename__ = "departments"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )

    # Identification
    code: Mapped[str] = mapped_column(
        String(20),
        unique=True,
        nullable=False,
        index=True,
        comment="HR, SALES, OPS, etc."
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Hierarchy
    parent_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("departments.id", ondelete="SET NULL"),
        nullable=True
    )

    # Department Head
    head_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )

    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    # Relationships
    parent: Mapped[Optional["Department"]] = relationship(
        "Department",
        remote_side=[id],
        back_populates="children"
    )
    children: Mapped[List["Department"]] = relationship(
        "Department",
        back_populates="parent"
    )
    head: Mapped[Optional["User"]] = relationship("User", foreign_keys=[head_id])
    employees: Mapped[List["Employee"]] = relationship("Employee", back_populates="department")

    def __repr__(self) -> str:
        return f"<Department(code='{self.code}', name='{self.name}')>"


# ==================== Employee ====================

class Employee(Base):
    """
    Employee model linked to User account.
    Contains personal, employment, and compliance details.
    """
    __tablename__ = "employees"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )

    # Identification
    employee_code: Mapped[str] = mapped_column(
        String(20),
        unique=True,
        nullable=False,
        index=True,
        comment="EMP-0001"
    )

    # Link to User (1:1)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        nullable=False
    )

    # Personal Information
    date_of_birth: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    gender: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        comment="MALE, FEMALE, OTHER"
    )
    blood_group: Mapped[Optional[str]] = mapped_column(String(5), nullable=True)
    marital_status: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        comment="SINGLE, MARRIED, DIVORCED, WIDOWED"
    )
    nationality: Mapped[str] = mapped_column(String(50), default="Indian")

    # Personal Contact
    personal_email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    personal_phone: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)

    # Emergency Contact
    emergency_contact_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    emergency_contact_phone: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    emergency_contact_relation: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    # Address (JSON: {line1, line2, city, state, pincode, country})
    current_address: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    permanent_address: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)

    # Employment Details
    department_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("departments.id", ondelete="SET NULL"),
        nullable=True
    )
    designation: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    employment_type: Mapped[str] = mapped_column(
        String(50),
        default="FULL_TIME",
        nullable=False,
        comment="FULL_TIME, PART_TIME, CONTRACT, INTERN, CONSULTANT"
    )
    status: Mapped[str] = mapped_column(
        String(50),
        default="ACTIVE",
        nullable=False,
        index=True,
        comment="ACTIVE, ON_NOTICE, ON_LEAVE, SUSPENDED, RESIGNED, TERMINATED"
    )

    # Employment Dates
    joining_date: Mapped[date] = mapped_column(Date, nullable=False)
    confirmation_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    resignation_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    last_working_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)

    # Reporting
    reporting_manager_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("employees.id", ondelete="SET NULL"),
        nullable=True
    )

    # Indian Compliance Documents
    pan_number: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    aadhaar_number: Mapped[Optional[str]] = mapped_column(String(12), nullable=True)
    uan_number: Mapped[Optional[str]] = mapped_column(
        String(12),
        nullable=True,
        comment="PF Universal Account Number"
    )
    esic_number: Mapped[Optional[str]] = mapped_column(
        String(17),
        nullable=True,
        comment="ESIC IP Number"
    )

    # Bank Details
    bank_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    bank_account_number: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    bank_ifsc_code: Mapped[Optional[str]] = mapped_column(String(11), nullable=True)

    # Other
    profile_photo_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    documents: Mapped[Optional[dict]] = mapped_column(
        JSONB,
        nullable=True,
        comment="Array of document URLs"
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    # Relationships
    user: Mapped["User"] = relationship("User", foreign_keys=[user_id])
    department: Mapped[Optional["Department"]] = relationship(
        "Department",
        back_populates="employees"
    )
    reporting_manager: Mapped[Optional["Employee"]] = relationship(
        "Employee",
        remote_side=[id],
        back_populates="direct_reports"
    )
    direct_reports: Mapped[List["Employee"]] = relationship(
        "Employee",
        back_populates="reporting_manager"
    )
    salary_structure: Mapped[Optional["SalaryStructure"]] = relationship(
        "SalaryStructure",
        back_populates="employee",
        uselist=False
    )
    attendance_records: Mapped[List["Attendance"]] = relationship(
        "Attendance",
        back_populates="employee"
    )
    leave_balances: Mapped[List["LeaveBalance"]] = relationship(
        "LeaveBalance",
        back_populates="employee"
    )
    leave_requests: Mapped[List["LeaveRequest"]] = relationship(
        "LeaveRequest",
        back_populates="employee"
    )
    payslips: Mapped[List["Payslip"]] = relationship(
        "Payslip",
        back_populates="employee"
    )
    goals: Mapped[List["Goal"]] = relationship(
        "Goal",
        back_populates="employee"
    )
    appraisals: Mapped[List["Appraisal"]] = relationship(
        "Appraisal",
        back_populates="employee",
        foreign_keys="Appraisal.employee_id"
    )

    def __repr__(self) -> str:
        return f"<Employee(code='{self.employee_code}')>"


# ==================== Salary Structure ====================

class SalaryStructure(Base):
    """
    Employee salary structure with Indian compliance components.
    """
    __tablename__ = "salary_structures"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )

    # Employee link (1:1 active structure)
    employee_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("employees.id", ondelete="CASCADE"),
        unique=True,
        nullable=False
    )
    effective_from: Mapped[date] = mapped_column(Date, nullable=False)

    # CTC Breakdown (Monthly amounts)
    basic_salary: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
        comment="Basic salary"
    )
    hra: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        default=0,
        comment="House Rent Allowance"
    )
    conveyance: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        default=0,
        comment="Conveyance Allowance"
    )
    medical_allowance: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        default=0
    )
    special_allowance: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        default=0
    )
    other_allowances: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        default=0
    )
    gross_salary: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
        comment="Sum of all earnings"
    )

    # Employer Contributions (for cost calculation)
    employer_pf: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        default=0,
        comment="12% of Basic (capped at 15000)"
    )
    employer_esic: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        default=0,
        comment="3.25% of Gross (if applicable)"
    )

    # CTC
    annual_ctc: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    monthly_ctc: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)

    # Statutory Applicability
    pf_applicable: Mapped[bool] = mapped_column(Boolean, default=True)
    esic_applicable: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        comment="Applicable if Gross <= 21000"
    )
    pt_applicable: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        comment="Professional Tax"
    )

    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    # Relationships
    employee: Mapped["Employee"] = relationship(
        "Employee",
        back_populates="salary_structure"
    )

    def __repr__(self) -> str:
        return f"<SalaryStructure(employee_id='{self.employee_id}', gross={self.gross_salary})>"


# ==================== Attendance ====================

class Attendance(Base):
    """
    Daily attendance record for employees.
    """
    __tablename__ = "attendance"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )

    # Employee & Date
    employee_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("employees.id", ondelete="CASCADE"),
        nullable=False
    )
    attendance_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)

    # Time tracking
    check_in: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    check_out: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    work_hours: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(4, 2),
        nullable=True,
        comment="Calculated work hours"
    )

    # Status
    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
        comment="PRESENT, ABSENT, HALF_DAY, ON_LEAVE, HOLIDAY, WEEKEND"
    )

    # Late/Early tracking
    is_late: Mapped[bool] = mapped_column(Boolean, default=False)
    late_minutes: Mapped[int] = mapped_column(Integer, default=0)
    is_early_out: Mapped[bool] = mapped_column(Boolean, default=False)
    early_out_minutes: Mapped[int] = mapped_column(Integer, default=0)

    # Location tracking (JSON: {lat, lng, address})
    location_in: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    location_out: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)

    # Notes
    remarks: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    approved_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    # Relationships
    employee: Mapped["Employee"] = relationship(
        "Employee",
        back_populates="attendance_records"
    )
    approver: Mapped[Optional["User"]] = relationship("User", foreign_keys=[approved_by])

    __table_args__ = (
        UniqueConstraint('employee_id', 'attendance_date', name='uq_attendance_employee_date'),
        Index('idx_attendance_employee', 'employee_id'),
        Index('idx_attendance_date', 'attendance_date'),
    )

    def __repr__(self) -> str:
        return f"<Attendance(employee_id='{self.employee_id}', date='{self.attendance_date}', status='{self.status}')>"


# ==================== Leave Balance ====================

class LeaveBalance(Base):
    """
    Leave balance for employees by type and financial year.
    """
    __tablename__ = "leave_balances"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )

    # Employee & Type
    employee_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("employees.id", ondelete="CASCADE"),
        nullable=False
    )
    leave_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="CASUAL, SICK, EARNED, MATERNITY, PATERNITY, COMPENSATORY, UNPAID"
    )
    financial_year: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
        comment="2025-26"
    )

    # Balance tracking
    opening_balance: Mapped[Decimal] = mapped_column(Numeric(4, 1), default=0)
    accrued: Mapped[Decimal] = mapped_column(
        Numeric(4, 1),
        default=0,
        comment="Monthly accrual"
    )
    taken: Mapped[Decimal] = mapped_column(Numeric(4, 1), default=0)
    adjusted: Mapped[Decimal] = mapped_column(
        Numeric(4, 1),
        default=0,
        comment="Manual adjustments"
    )
    closing_balance: Mapped[Decimal] = mapped_column(
        Numeric(4, 1),
        default=0,
        comment="Calculated balance"
    )

    # Policy
    carry_forward_limit: Mapped[Decimal] = mapped_column(
        Numeric(4, 1),
        default=0,
        comment="Max carry forward to next year"
    )

    __table_args__ = (
        UniqueConstraint('employee_id', 'leave_type', 'financial_year', name='uq_leave_balance'),
    )

    # Relationships
    employee: Mapped["Employee"] = relationship(
        "Employee",
        back_populates="leave_balances"
    )

    def __repr__(self) -> str:
        return f"<LeaveBalance(employee='{self.employee_id}', type='{self.leave_type}', balance={self.closing_balance})>"


# ==================== Leave Request ====================

class LeaveRequest(Base):
    """
    Employee leave application and approval.
    """
    __tablename__ = "leave_requests"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )

    # Employee & Type
    employee_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("employees.id", ondelete="CASCADE"),
        nullable=False
    )
    leave_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="CASUAL, SICK, EARNED, MATERNITY, PATERNITY, COMPENSATORY, UNPAID"
    )

    # Leave Period
    from_date: Mapped[date] = mapped_column(Date, nullable=False)
    to_date: Mapped[date] = mapped_column(Date, nullable=False)
    days: Mapped[Decimal] = mapped_column(
        Numeric(4, 1),
        nullable=False,
        comment="0.5 for half day"
    )
    is_half_day: Mapped[bool] = mapped_column(Boolean, default=False)
    half_day_type: Mapped[Optional[str]] = mapped_column(
        String(15),
        nullable=True,
        comment="FIRST_HALF or SECOND_HALF"
    )

    # Details
    reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(
        String(50),
        default="PENDING",
        nullable=False,
        index=True,
        comment="PENDING, APPROVED, REJECTED, CANCELLED"
    )

    # Application tracking
    applied_on: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    # Approval tracking
    approved_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )
    approved_on: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    rejection_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    # Relationships
    employee: Mapped["Employee"] = relationship(
        "Employee",
        back_populates="leave_requests"
    )
    approver: Mapped[Optional["User"]] = relationship("User", foreign_keys=[approved_by])

    def __repr__(self) -> str:
        return f"<LeaveRequest(employee='{self.employee_id}', type='{self.leave_type}', status='{self.status}')>"


# ==================== Payroll ====================

class Payroll(Base):
    """
    Monthly payroll batch for processing.
    """
    __tablename__ = "payrolls"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )

    # Period
    payroll_month: Mapped[date] = mapped_column(
        Date,
        nullable=False,
        comment="1st of the month"
    )
    financial_year: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
        comment="2025-26"
    )

    # Status
    status: Mapped[str] = mapped_column(
        String(50),
        default="DRAFT",
        nullable=False,
        index=True,
        comment="DRAFT, PROCESSING, PROCESSED, APPROVED, PAID"
    )

    # Summary
    total_employees: Mapped[int] = mapped_column(Integer, default=0)
    total_gross: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0)
    total_deductions: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0)
    total_net: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0)

    # Processing tracking
    processed_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )
    processed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    approved_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )
    approved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    # Relationships
    processor: Mapped[Optional["User"]] = relationship("User", foreign_keys=[processed_by])
    approver: Mapped[Optional["User"]] = relationship("User", foreign_keys=[approved_by])
    payslips: Mapped[List["Payslip"]] = relationship("Payslip", back_populates="payroll")

    def __repr__(self) -> str:
        return f"<Payroll(month='{self.payroll_month}', status='{self.status}')>"


# ==================== Payslip ====================

class Payslip(Base):
    """
    Individual employee payslip with Indian compliance deductions.
    """
    __tablename__ = "payslips"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )

    # References
    payroll_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("payrolls.id", ondelete="CASCADE"),
        nullable=False
    )
    employee_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("employees.id", ondelete="CASCADE"),
        nullable=False
    )
    payslip_number: Mapped[str] = mapped_column(
        String(30),
        unique=True,
        nullable=False,
        comment="PS-YYYYMM-XXXX"
    )

    # Attendance Summary
    working_days: Mapped[int] = mapped_column(Integer, nullable=False)
    days_present: Mapped[Decimal] = mapped_column(Numeric(4, 1), nullable=False)
    days_absent: Mapped[Decimal] = mapped_column(Numeric(4, 1), default=0)
    leaves_taken: Mapped[Decimal] = mapped_column(Numeric(4, 1), default=0)

    # Earnings
    basic_earned: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    hra_earned: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    conveyance_earned: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    medical_earned: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    special_earned: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    other_earned: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    overtime_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    arrears: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    bonus: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    gross_earnings: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)

    # Deductions - Statutory (Indian Compliance)
    employee_pf: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        default=0,
        comment="12% of Basic (max Basic 15000)"
    )
    employer_pf: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        default=0,
        comment="12% employer contribution (for records)"
    )
    employee_esic: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        default=0,
        comment="0.75% of Gross (if applicable)"
    )
    employer_esic: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        default=0,
        comment="3.25% employer contribution (for records)"
    )
    professional_tax: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        default=0,
        comment="State-wise slab"
    )
    tds: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        default=0,
        comment="Income Tax (TDS)"
    )

    # Deductions - Other
    loan_deduction: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    advance_deduction: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    other_deductions: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    total_deductions: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)

    # Net Pay
    net_salary: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)

    # Payment Details
    payment_mode: Mapped[Optional[str]] = mapped_column(
        String(20),
        nullable=True,
        comment="BANK, CASH, CHEQUE"
    )
    payment_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    payment_reference: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    # PDF
    payslip_pdf_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    # Relationships
    payroll: Mapped["Payroll"] = relationship("Payroll", back_populates="payslips")
    employee: Mapped["Employee"] = relationship("Employee", back_populates="payslips")

    __table_args__ = (
        Index('idx_payslips_payroll', 'payroll_id'),
        Index('idx_payslips_employee', 'employee_id'),
    )

    def __repr__(self) -> str:
        return f"<Payslip(number='{self.payslip_number}', net={self.net_salary})>"


# ==================== Performance Management ====================

class AppraisalCycleStatus(str, Enum):
    """Appraisal cycle status."""
    DRAFT = "DRAFT"
    ACTIVE = "ACTIVE"
    CLOSED = "CLOSED"


class GoalStatus(str, Enum):
    """Goal status."""
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


class AppraisalStatus(str, Enum):
    """Appraisal status."""
    NOT_STARTED = "NOT_STARTED"
    SELF_REVIEW = "SELF_REVIEW"
    MANAGER_REVIEW = "MANAGER_REVIEW"
    HR_REVIEW = "HR_REVIEW"
    COMPLETED = "COMPLETED"


class AppraisalCycle(Base):
    """
    Appraisal cycle/period for performance reviews.
    Typically annual or semi-annual.
    """
    __tablename__ = "appraisal_cycles"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )

    # Cycle Details
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    financial_year: Mapped[str] = mapped_column(String(10), nullable=False)

    # Dates
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    review_start_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    review_end_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)

    # Status
    status: Mapped[str] = mapped_column(
        String(50),
        default="DRAFT",
        nullable=False,
        comment="DRAFT, ACTIVE, CLOSED"
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    # Relationships
    appraisals: Mapped[List["Appraisal"]] = relationship("Appraisal", back_populates="cycle")

    def __repr__(self) -> str:
        return f"<AppraisalCycle(name='{self.name}', year='{self.financial_year}')>"


class KPI(Base):
    """
    Key Performance Indicator templates.
    Used for goal setting and performance measurement.
    """
    __tablename__ = "kpis"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )

    # KPI Details
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    category: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="SALES, QUALITY, PRODUCTIVITY, CUSTOMER, LEARNING"
    )

    # Measurement
    unit_of_measure: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="PERCENTAGE, NUMBER, CURRENCY, RATING"
    )
    target_value: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 2), nullable=True)
    weightage: Mapped[Decimal] = mapped_column(
        Numeric(5, 2),
        default=Decimal("0"),
        comment="Weightage in overall performance"
    )

    # Applicability
    department_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("departments.id", ondelete="SET NULL"),
        nullable=True,
        comment="Department-specific KPI"
    )
    designation: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        comment="Role-specific KPI"
    )

    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    def __repr__(self) -> str:
        return f"<KPI(name='{self.name}', category='{self.category}')>"


class Goal(Base):
    """
    Individual employee goals for a performance period.
    """
    __tablename__ = "goals"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )

    # Employee & Cycle
    employee_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("employees.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    cycle_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("appraisal_cycles.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Goal Details
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    category: Mapped[str] = mapped_column(String(50), nullable=False)

    # Linked KPI (optional)
    kpi_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("kpis.id", ondelete="SET NULL"),
        nullable=True
    )

    # Target
    target_value: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 2), nullable=True)
    achieved_value: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 2), nullable=True)
    unit_of_measure: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    weightage: Mapped[Decimal] = mapped_column(
        Numeric(5, 2),
        default=Decimal("0"),
        comment="Weightage in overall performance"
    )

    # Timeline
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    due_date: Mapped[date] = mapped_column(Date, nullable=False)
    completed_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)

    # Status
    status: Mapped[str] = mapped_column(
        String(50),
        default="PENDING",
        nullable=False,
        comment="PENDING, IN_PROGRESS, COMPLETED, CANCELLED"
    )
    completion_percentage: Mapped[int] = mapped_column(Integer, default=0)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    # Relationships
    employee: Mapped["Employee"] = relationship("Employee", back_populates="goals")
    kpi: Mapped[Optional["KPI"]] = relationship("KPI")

    def __repr__(self) -> str:
        return f"<Goal(title='{self.title}', status='{self.status}')>"


class Appraisal(Base):
    """
    Performance appraisal record for an employee in a cycle.
    """
    __tablename__ = "appraisals"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )

    # Employee & Cycle
    employee_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("employees.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    cycle_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("appraisal_cycles.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Status
    status: Mapped[str] = mapped_column(
        String(50),
        default="NOT_STARTED",
        nullable=False,
        comment="NOT_STARTED, SELF_REVIEW, MANAGER_REVIEW, HR_REVIEW, COMPLETED"
    )

    # Self Review
    self_rating: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(3, 1),
        nullable=True,
        comment="Self rating 1-5"
    )
    self_comments: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    self_review_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Manager Review
    manager_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("employees.id", ondelete="SET NULL"),
        nullable=True
    )
    manager_rating: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(3, 1),
        nullable=True,
        comment="Manager rating 1-5"
    )
    manager_comments: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    manager_review_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Final Rating
    final_rating: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(3, 1),
        nullable=True,
        comment="Final rating 1-5"
    )
    performance_band: Mapped[Optional[str]] = mapped_column(
        String(20),
        nullable=True,
        comment="OUTSTANDING, EXCEEDS, MEETS, NEEDS_IMPROVEMENT, UNSATISFACTORY"
    )

    # Goals Achievement
    goals_achieved: Mapped[int] = mapped_column(Integer, default=0)
    goals_total: Mapped[int] = mapped_column(Integer, default=0)
    overall_goal_score: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 2), nullable=True)

    # Development Areas
    strengths: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    areas_of_improvement: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    development_plan: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Promotion/Increment Recommendation
    recommended_for_promotion: Mapped[bool] = mapped_column(Boolean, default=False)
    recommended_increment_percentage: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(5, 2),
        nullable=True
    )

    # HR Review
    hr_reviewed_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )
    hr_review_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    hr_comments: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    # Relationships
    employee: Mapped["Employee"] = relationship(
        "Employee",
        foreign_keys=[employee_id],
        back_populates="appraisals"
    )
    manager: Mapped[Optional["Employee"]] = relationship(
        "Employee",
        foreign_keys=[manager_id]
    )
    cycle: Mapped["AppraisalCycle"] = relationship("AppraisalCycle", back_populates="appraisals")

    __table_args__ = (
        UniqueConstraint('employee_id', 'cycle_id', name='uq_appraisal_employee_cycle'),
    )

    def __repr__(self) -> str:
        return f"<Appraisal(employee={self.employee_id}, status='{self.status}')>"


class PerformanceFeedback(Base):
    """
    Continuous feedback for employees.
    Can be given anytime, not just during appraisal.
    """
    __tablename__ = "performance_feedback"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )

    # Employee receiving feedback
    employee_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("employees.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Feedback giver
    given_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False
    )

    # Feedback Type
    feedback_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        comment="APPRECIATION, IMPROVEMENT, SUGGESTION"
    )

    # Content
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)

    # Visibility
    is_private: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        comment="Only visible to employee and HR"
    )

    # Related Goal (optional)
    goal_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("goals.id", ondelete="SET NULL"),
        nullable=True
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    # Relationships
    employee: Mapped["Employee"] = relationship("Employee")

    def __repr__(self) -> str:
        return f"<PerformanceFeedback(employee={self.employee_id}, type='{self.feedback_type}')>"
