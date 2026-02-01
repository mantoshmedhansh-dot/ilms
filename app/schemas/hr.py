"""Pydantic schemas for HR & Payroll module."""
from datetime import datetime, date
from typing import Optional, List
from decimal import Decimal
from uuid import UUID
from pydantic import BaseModel, Field, ConfigDict, EmailStr

from app.schemas.base import BaseResponseSchema

from app.models.hr import (
    EmploymentType, EmployeeStatus, LeaveType, LeaveStatus,
    AttendanceStatus, PayrollStatus, Gender, MaritalStatus,
    AppraisalCycleStatus, GoalStatus, AppraisalStatus
)


# ==================== Department Schemas ====================

class DepartmentBase(BaseModel):
    """Base schema for Department."""
    code: str = Field(..., max_length=20)
    name: str = Field(..., max_length=100)
    description: Optional[str] = None
    parent_id: Optional[UUID] = None
    head_id: Optional[UUID] = None
    is_active: bool = True


class DepartmentCreate(DepartmentBase):
    """Schema for creating Department."""
    pass


class DepartmentUpdate(BaseModel):
    """Schema for updating Department."""
    name: Optional[str] = Field(None, max_length=100)
    description: Optional[str] = None
    parent_id: Optional[UUID] = None
    head_id: Optional[UUID] = None
    is_active: Optional[bool] = None


class DepartmentResponse(BaseResponseSchema):
    """Response schema for Department."""
    id: UUID
    parent_name: Optional[str] = None
    head_name: Optional[str] = None
    employee_count: int = 0
    created_at: datetime
    updated_at: datetime


class DepartmentListResponse(BaseModel):
    """Response for listing Departments."""
    items: List[DepartmentResponse]
    total: int
    page: int = 1
    size: int = 50
    pages: int = 1


class DepartmentDropdown(BaseResponseSchema):
    """Dropdown item for Department selection."""
    id: UUID
    code: str
    name: str


# ==================== Employee Schemas ====================

class AddressSchema(BaseModel):
    """Schema for address fields."""
    line1: Optional[str] = None
    line2: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    pincode: Optional[str] = None
    country: str = "India"


class EmployeeBase(BaseModel):
    """Base schema for Employee."""
    # Personal Info
    date_of_birth: Optional[date] = None
    gender: Optional[Gender] = None
    blood_group: Optional[str] = Field(None, max_length=5)
    marital_status: Optional[MaritalStatus] = None
    nationality: str = "Indian"

    # Personal Contact
    personal_email: Optional[EmailStr] = None
    personal_phone: Optional[str] = Field(None, max_length=20)

    # Emergency Contact
    emergency_contact_name: Optional[str] = Field(None, max_length=100)
    emergency_contact_phone: Optional[str] = Field(None, max_length=20)
    emergency_contact_relation: Optional[str] = Field(None, max_length=50)

    # Address
    current_address: Optional[AddressSchema] = None
    permanent_address: Optional[AddressSchema] = None

    # Employment
    department_id: Optional[UUID] = None
    designation: Optional[str] = Field(None, max_length=100)
    employment_type: EmploymentType = EmploymentType.FULL_TIME
    joining_date: date
    confirmation_date: Optional[date] = None
    reporting_manager_id: Optional[UUID] = None

    # Indian Documents
    pan_number: Optional[str] = Field(None, max_length=10)
    aadhaar_number: Optional[str] = Field(None, max_length=12)
    uan_number: Optional[str] = Field(None, max_length=12)
    esic_number: Optional[str] = Field(None, max_length=17)

    # Bank Details
    bank_name: Optional[str] = Field(None, max_length=100)
    bank_account_number: Optional[str] = Field(None, max_length=20)
    bank_ifsc_code: Optional[str] = Field(None, max_length=11)


class EmployeeCreateWithUser(BaseModel):
    """Schema for creating Employee with new User account."""
    # User account details
    email: EmailStr
    password: str = Field(..., min_length=8)
    first_name: str = Field(..., max_length=100)
    last_name: Optional[str] = Field(None, max_length=100)
    phone: Optional[str] = Field(None, max_length=20)

    # Employee details (extends EmployeeBase)
    date_of_birth: Optional[date] = None
    gender: Optional[Gender] = None
    blood_group: Optional[str] = Field(None, max_length=5)
    marital_status: Optional[MaritalStatus] = None
    nationality: str = "Indian"

    personal_email: Optional[EmailStr] = None
    personal_phone: Optional[str] = Field(None, max_length=20)

    emergency_contact_name: Optional[str] = Field(None, max_length=100)
    emergency_contact_phone: Optional[str] = Field(None, max_length=20)
    emergency_contact_relation: Optional[str] = Field(None, max_length=50)

    current_address: Optional[AddressSchema] = None
    permanent_address: Optional[AddressSchema] = None

    department_id: Optional[UUID] = None
    designation: Optional[str] = Field(None, max_length=100)
    employment_type: EmploymentType = EmploymentType.FULL_TIME
    joining_date: date
    confirmation_date: Optional[date] = None
    reporting_manager_id: Optional[UUID] = None

    pan_number: Optional[str] = Field(None, max_length=10)
    aadhaar_number: Optional[str] = Field(None, max_length=12)
    uan_number: Optional[str] = Field(None, max_length=12)
    esic_number: Optional[str] = Field(None, max_length=17)

    bank_name: Optional[str] = Field(None, max_length=100)
    bank_account_number: Optional[str] = Field(None, max_length=20)
    bank_ifsc_code: Optional[str] = Field(None, max_length=11)

    # Role assignment
    role_ids: Optional[List[UUID]] = None


class EmployeeUpdate(BaseModel):
    """Schema for updating Employee."""
    date_of_birth: Optional[date] = None
    gender: Optional[Gender] = None
    blood_group: Optional[str] = Field(None, max_length=5)
    marital_status: Optional[MaritalStatus] = None
    nationality: Optional[str] = None

    personal_email: Optional[EmailStr] = None
    personal_phone: Optional[str] = Field(None, max_length=20)

    emergency_contact_name: Optional[str] = Field(None, max_length=100)
    emergency_contact_phone: Optional[str] = Field(None, max_length=20)
    emergency_contact_relation: Optional[str] = Field(None, max_length=50)

    current_address: Optional[AddressSchema] = None
    permanent_address: Optional[AddressSchema] = None

    department_id: Optional[UUID] = None
    designation: Optional[str] = Field(None, max_length=100)
    employment_type: Optional[EmploymentType] = None
    status: Optional[EmployeeStatus] = None
    confirmation_date: Optional[date] = None
    resignation_date: Optional[date] = None
    last_working_date: Optional[date] = None
    reporting_manager_id: Optional[UUID] = None

    pan_number: Optional[str] = Field(None, max_length=10)
    aadhaar_number: Optional[str] = Field(None, max_length=12)
    uan_number: Optional[str] = Field(None, max_length=12)
    esic_number: Optional[str] = Field(None, max_length=17)

    bank_name: Optional[str] = Field(None, max_length=100)
    bank_account_number: Optional[str] = Field(None, max_length=20)
    bank_ifsc_code: Optional[str] = Field(None, max_length=11)

    profile_photo_url: Optional[str] = None


class EmployeeResponse(BaseResponseSchema):
    """Response schema for Employee (list view)."""
    id: UUID
    employee_code: str
    user_id: UUID

    # User details
    email: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    full_name: Optional[str] = None
    phone: Optional[str] = None
    avatar_url: Optional[str] = None

    # Employment
    department_id: Optional[UUID] = None
    department_name: Optional[str] = None
    designation: Optional[str] = None
    employment_type: EmploymentType
    status: str
    joining_date: date

    # Manager
    reporting_manager_id: Optional[UUID] = None
    reporting_manager_name: Optional[str] = None

    created_at: datetime
    updated_at: datetime


class EmployeeDetailResponse(EmployeeResponse):
    """Detailed response schema for Employee (profile view)."""
    # Personal
    date_of_birth: Optional[date] = None
    gender: Optional[str] = None
    blood_group: Optional[str] = None
    marital_status: Optional[MaritalStatus] = None
    nationality: Optional[str] = None

    # Contact
    personal_email: Optional[str] = None
    personal_phone: Optional[str] = None

    # Emergency
    emergency_contact_name: Optional[str] = None
    emergency_contact_phone: Optional[str] = None
    emergency_contact_relation: Optional[str] = None

    # Address
    current_address: Optional[dict] = None
    permanent_address: Optional[dict] = None

    # Dates
    confirmation_date: Optional[date] = None
    resignation_date: Optional[date] = None
    last_working_date: Optional[date] = None

    # Documents
    pan_number: Optional[str] = None
    aadhaar_number: Optional[str] = None
    uan_number: Optional[str] = None
    esic_number: Optional[str] = None

    # Bank
    bank_name: Optional[str] = None
    bank_account_number: Optional[str] = None
    bank_ifsc_code: Optional[str] = None

    profile_photo_url: Optional[str] = None
    documents: Optional[dict] = None


class EmployeeListResponse(BaseModel):
    """Response for listing Employees."""
    items: List[EmployeeResponse]
    total: int
    page: int = 1
    size: int = 50
    pages: int = 1


class EmployeeDropdown(BaseResponseSchema):
    """Dropdown item for Employee selection."""
    id: UUID
    employee_code: str
    full_name: str
    designation: Optional[str] = None
    department_name: Optional[str] = None


# ==================== Salary Structure Schemas ====================

class SalaryStructureBase(BaseModel):
    """Base schema for Salary Structure."""
    effective_from: date

    # CTC Components
    basic_salary: Decimal = Field(..., ge=0)
    hra: Decimal = Field(Decimal("0"), ge=0)
    conveyance: Decimal = Field(Decimal("0"), ge=0)
    medical_allowance: Decimal = Field(Decimal("0"), ge=0)
    special_allowance: Decimal = Field(Decimal("0"), ge=0)
    other_allowances: Decimal = Field(Decimal("0"), ge=0)

    # Statutory
    pf_applicable: bool = True
    esic_applicable: bool = False
    pt_applicable: bool = True


class SalaryStructureCreate(SalaryStructureBase):
    """Schema for creating Salary Structure."""
    employee_id: UUID


class SalaryStructureUpdate(BaseModel):
    """Schema for updating Salary Structure."""
    effective_from: Optional[date] = None
    basic_salary: Optional[Decimal] = Field(None, ge=0)
    hra: Optional[Decimal] = Field(None, ge=0)
    conveyance: Optional[Decimal] = Field(None, ge=0)
    medical_allowance: Optional[Decimal] = Field(None, ge=0)
    special_allowance: Optional[Decimal] = Field(None, ge=0)
    other_allowances: Optional[Decimal] = Field(None, ge=0)
    pf_applicable: Optional[bool] = None
    esic_applicable: Optional[bool] = None
    pt_applicable: Optional[bool] = None


class SalaryStructureResponse(BaseResponseSchema):
    """Response schema for Salary Structure."""
    id: UUID
    employee_id: UUID

    # Computed
    gross_salary: Decimal
    employer_pf: Decimal
    employer_esic: Decimal
    monthly_ctc: Decimal
    annual_ctc: Decimal

    is_active: bool
    created_at: datetime
    updated_at: datetime


# ==================== Attendance Schemas ====================

class AttendanceBase(BaseModel):
    """Base schema for Attendance."""
    employee_id: UUID
    attendance_date: date
    status: AttendanceStatus
    remarks: Optional[str] = None


class AttendanceCheckIn(BaseModel):
    """Schema for check-in."""
    employee_id: Optional[UUID] = None  # Auto from token if not provided
    location: Optional[dict] = None  # {lat, lng, address}
    remarks: Optional[str] = None


class AttendanceCheckOut(BaseModel):
    """Schema for check-out."""
    employee_id: Optional[UUID] = None
    location: Optional[dict] = None
    remarks: Optional[str] = None


class AttendanceBulkCreate(BaseModel):
    """Schema for bulk attendance entry."""
    attendance_date: date
    records: List[dict]  # [{employee_id, status, remarks}]


class AttendanceUpdate(BaseModel):
    """Schema for updating Attendance."""
    status: Optional[AttendanceStatus] = None
    check_in: Optional[datetime] = None
    check_out: Optional[datetime] = None
    remarks: Optional[str] = None


class AttendanceResponse(BaseResponseSchema):
    """Response schema for Attendance."""
    id: UUID
    check_in: Optional[datetime] = None
    check_out: Optional[datetime] = None
    work_hours: Optional[Decimal] = None

    is_late: bool = False
    late_minutes: int = 0
    is_early_out: bool = False
    early_out_minutes: int = 0

    location_in: Optional[dict] = None
    location_out: Optional[dict] = None

    approved_by: Optional[UUID] = None
    approved_by_name: Optional[str] = None

    # Employee info
    employee_code: Optional[str] = None
    employee_name: Optional[str] = None
    department_name: Optional[str] = None

    created_at: datetime
    updated_at: datetime


class AttendanceListResponse(BaseModel):
    """Response for listing Attendance."""
    items: List[AttendanceResponse]
    total: int
    page: int = 1
    size: int = 50
    pages: int = 1


class AttendanceReportResponse(BaseModel):
    """Response for attendance report/summary."""
    employee_id: UUID
    employee_code: str
    employee_name: str
    department: Optional[str] = None

    # Monthly summary
    total_days: int
    present_days: Decimal
    absent_days: Decimal
    half_days: Decimal
    leaves: Decimal
    holidays: int
    weekends: int
    late_count: int
    early_out_count: int


# ==================== Leave Schemas ====================

class LeaveBalanceResponse(BaseResponseSchema):
    """Response schema for Leave Balance."""
    id: UUID
    employee_id: UUID
    leave_type: LeaveType
    financial_year: str

    opening_balance: Decimal
    accrued: Decimal
    taken: Decimal
    adjusted: Decimal
    closing_balance: Decimal
    carry_forward_limit: Decimal


class LeaveBalanceSummary(BaseModel):
    """Summary of all leave balances for an employee."""
    employee_id: UUID
    financial_year: str
    balances: List[LeaveBalanceResponse]


class LeaveRequestBase(BaseModel):
    """Base schema for Leave Request."""
    leave_type: LeaveType
    from_date: date
    to_date: date
    is_half_day: bool = False
    half_day_type: Optional[str] = Field(None, pattern="^(FIRST_HALF|SECOND_HALF)$")
    reason: Optional[str] = None


class LeaveRequestCreate(LeaveRequestBase):
    """Schema for creating Leave Request."""
    employee_id: Optional[UUID] = None  # Auto from token if not provided


class LeaveRequestResponse(BaseResponseSchema):
    """Response schema for Leave Request."""
    id: UUID
    employee_id: UUID
    days: Decimal
    status: str

    applied_on: datetime
    approved_by: Optional[UUID] = None
    approved_by_name: Optional[str] = None
    approved_on: Optional[datetime] = None
    rejection_reason: Optional[str] = None

    # Employee info
    employee_code: Optional[str] = None
    employee_name: Optional[str] = None
    department_name: Optional[str] = None

    created_at: datetime
    updated_at: datetime


class LeaveRequestListResponse(BaseModel):
    """Response for listing Leave Requests."""
    items: List[LeaveRequestResponse]
    total: int
    page: int = 1
    size: int = 50
    pages: int = 1


class LeaveApproveRequest(BaseModel):
    """Request to approve/reject leave."""
    action: str = Field(..., pattern="^(APPROVE|REJECT)$")
    rejection_reason: Optional[str] = None


# ==================== Payroll Schemas ====================

class PayrollProcessRequest(BaseModel):
    """Schema for processing payroll."""
    payroll_month: date  # First of month
    financial_year: str  # 2025-26
    employee_ids: Optional[List[UUID]] = None  # If None, process all active


class PayrollResponse(BaseResponseSchema):
    """Response schema for Payroll."""
    id: UUID
    payroll_month: date
    financial_year: str
    status: str

    total_employees: int
    total_gross: Decimal
    total_deductions: Decimal
    total_net: Decimal

    processed_by: Optional[UUID] = None
    processed_by_name: Optional[str] = None
    processed_at: Optional[datetime] = None
    approved_by: Optional[UUID] = None
    approved_by_name: Optional[str] = None
    approved_at: Optional[datetime] = None

    created_at: datetime
    updated_at: datetime


class PayrollListResponse(BaseModel):
    """Response for listing Payrolls."""
    items: List[PayrollResponse]
    total: int
    page: int = 1
    size: int = 50
    pages: int = 1


class PayrollDetailResponse(PayrollResponse):
    """Detailed response with payslips."""
    payslips: List["PayslipResponse"] = []


# ==================== Payslip Schemas ====================

class PayslipResponse(BaseResponseSchema):
    """Response schema for Payslip."""
    id: UUID
    payroll_id: UUID
    employee_id: UUID
    payslip_number: str

    # Employee info
    employee_code: Optional[str] = None
    employee_name: Optional[str] = None
    department_name: Optional[str] = None
    designation: Optional[str] = None

    # Attendance
    working_days: int
    days_present: Decimal
    days_absent: Decimal
    leaves_taken: Decimal

    # Earnings
    basic_earned: Decimal
    hra_earned: Decimal
    conveyance_earned: Decimal
    medical_earned: Decimal
    special_earned: Decimal
    other_earned: Decimal
    overtime_amount: Decimal
    arrears: Decimal
    bonus: Decimal
    gross_earnings: Decimal

    # Deductions - Statutory
    employee_pf: Decimal
    employer_pf: Decimal
    employee_esic: Decimal
    employer_esic: Decimal
    professional_tax: Decimal
    tds: Decimal

    # Deductions - Other
    loan_deduction: Decimal
    advance_deduction: Decimal
    other_deductions: Decimal
    total_deductions: Decimal

    # Net
    net_salary: Decimal

    # Payment
    payment_mode: Optional[str] = None
    payment_date: Optional[date] = None
    payment_reference: Optional[str] = None

    payslip_pdf_url: Optional[str] = None

    created_at: datetime
    updated_at: datetime


class PayslipListResponse(BaseModel):
    """Response for listing Payslips."""
    items: List[PayslipResponse]
    total: int
    page: int = 1
    size: int = 50
    pages: int = 1


# ==================== Dashboard & Reports ====================

class HRDashboardStats(BaseModel):
    """HR Dashboard statistics."""
    total_employees: int
    active_employees: int
    on_leave_today: int
    new_joinings_this_month: int
    exits_this_month: int

    # Attendance today
    present_today: int
    absent_today: int
    not_marked: int

    # Pending actions
    pending_leave_requests: int
    pending_payroll_approval: int

    # Department distribution
    department_wise: List[dict]  # [{department, count}]


class AttendanceReportRequest(BaseModel):
    """Request for attendance report."""
    from_date: date
    to_date: date
    department_id: Optional[UUID] = None
    employee_ids: Optional[List[UUID]] = None


class PFReportResponse(BaseModel):
    """PF ECR report format."""
    employee_id: UUID
    employee_code: str
    employee_name: str
    uan_number: Optional[str] = None

    gross_wages: Decimal
    epf_wages: Decimal  # Basic (capped)
    eps_wages: Decimal
    edli_wages: Decimal

    epf_contribution_employee: Decimal  # 12% EPF
    epf_contribution_employer: Decimal  # 3.67% EPF
    eps_contribution: Decimal  # 8.33% EPS
    edli_contribution: Decimal
    admin_charges: Decimal

    ncp_days: int  # Non-contributing days


class ESICReportResponse(BaseModel):
    """ESIC report format."""
    employee_id: UUID
    employee_code: str
    employee_name: str
    esic_number: Optional[str] = None

    gross_wages: Decimal
    employee_contribution: Decimal  # 0.75%
    employer_contribution: Decimal  # 3.25%
    total_contribution: Decimal

    days_worked: int


# ==================== Performance Management Schemas ====================

# Appraisal Cycle
class AppraisalCycleBase(BaseModel):
    """Base schema for Appraisal Cycle."""
    name: str = Field(..., max_length=100)
    description: Optional[str] = None
    financial_year: str = Field(..., max_length=10)
    start_date: date
    end_date: date
    review_start_date: Optional[date] = None
    review_end_date: Optional[date] = None


class AppraisalCycleCreate(AppraisalCycleBase):
    """Schema for creating Appraisal Cycle."""
    pass


class AppraisalCycleUpdate(BaseModel):
    """Schema for updating Appraisal Cycle."""
    name: Optional[str] = Field(None, max_length=100)
    description: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    review_start_date: Optional[date] = None
    review_end_date: Optional[date] = None
    status: Optional[AppraisalCycleStatus] = None


class AppraisalCycleResponse(BaseResponseSchema):
    """Response schema for Appraisal Cycle."""
    id: UUID
    status: str
    created_at: datetime
    updated_at: datetime


class AppraisalCycleListResponse(BaseModel):
    """Response for listing Appraisal Cycles."""
    items: List[AppraisalCycleResponse]
    total: int
    page: int = 1
    size: int = 50
    pages: int = 1


# KPI
class KPIBase(BaseModel):
    """Base schema for KPI."""
    name: str = Field(..., max_length=200)
    description: Optional[str] = None
    category: str = Field(..., max_length=50)
    unit_of_measure: str = Field(..., max_length=50)
    target_value: Optional[Decimal] = None
    weightage: Decimal = Field(Decimal("0"), ge=0, le=100)
    department_id: Optional[UUID] = None
    designation: Optional[str] = Field(None, max_length=100)


class KPICreate(KPIBase):
    """Schema for creating KPI."""
    pass


class KPIUpdate(BaseModel):
    """Schema for updating KPI."""
    name: Optional[str] = Field(None, max_length=200)
    description: Optional[str] = None
    category: Optional[str] = Field(None, max_length=50)
    unit_of_measure: Optional[str] = Field(None, max_length=50)
    target_value: Optional[Decimal] = None
    weightage: Optional[Decimal] = Field(None, ge=0, le=100)
    department_id: Optional[UUID] = None
    designation: Optional[str] = Field(None, max_length=100)
    is_active: Optional[bool] = None


class KPIResponse(BaseResponseSchema):
    """Response schema for KPI."""
    id: UUID
    is_active: bool
    department_name: Optional[str] = None
    created_at: datetime


class KPIListResponse(BaseModel):
    """Response for listing KPIs."""
    items: List[KPIResponse]
    total: int
    page: int = 1
    size: int = 50
    pages: int = 1


# Goal
class GoalBase(BaseModel):
    """Base schema for Goal."""
    title: str = Field(..., max_length=200)
    description: Optional[str] = None
    category: str = Field(..., max_length=50)
    kpi_id: Optional[UUID] = None
    target_value: Optional[Decimal] = None
    unit_of_measure: Optional[str] = Field(None, max_length=50)
    weightage: Decimal = Field(Decimal("0"), ge=0, le=100)
    start_date: date
    due_date: date


class GoalCreate(GoalBase):
    """Schema for creating Goal."""
    employee_id: UUID
    cycle_id: UUID


class GoalUpdate(BaseModel):
    """Schema for updating Goal."""
    title: Optional[str] = Field(None, max_length=200)
    description: Optional[str] = None
    category: Optional[str] = Field(None, max_length=50)
    target_value: Optional[Decimal] = None
    achieved_value: Optional[Decimal] = None
    unit_of_measure: Optional[str] = Field(None, max_length=50)
    weightage: Optional[Decimal] = Field(None, ge=0, le=100)
    start_date: Optional[date] = None
    due_date: Optional[date] = None
    completed_date: Optional[date] = None
    status: Optional[GoalStatus] = None
    completion_percentage: Optional[int] = Field(None, ge=0, le=100)


class GoalResponse(BaseResponseSchema):
    """Response schema for Goal."""
    id: UUID
    employee_id: UUID
    cycle_id: UUID
    achieved_value: Optional[Decimal] = None
    status: str
    completion_percentage: int
    completed_date: Optional[date] = None

    # Related info
    employee_name: Optional[str] = None
    employee_code: Optional[str] = None
    kpi_name: Optional[str] = None
    cycle_name: Optional[str] = None

    created_at: datetime
    updated_at: datetime


class GoalListResponse(BaseModel):
    """Response for listing Goals."""
    items: List[GoalResponse]
    total: int
    page: int = 1
    size: int = 50
    pages: int = 1


# Appraisal
class AppraisalCreate(BaseModel):
    """Schema for creating Appraisal."""
    employee_id: UUID
    cycle_id: UUID
    manager_id: Optional[UUID] = None


class AppraisalSelfReview(BaseModel):
    """Schema for self review submission."""
    self_rating: Decimal = Field(..., ge=1, le=5)
    self_comments: Optional[str] = None


class AppraisalManagerReview(BaseModel):
    """Schema for manager review submission."""
    manager_rating: Decimal = Field(..., ge=1, le=5)
    manager_comments: Optional[str] = None
    strengths: Optional[str] = None
    areas_of_improvement: Optional[str] = None
    development_plan: Optional[str] = None
    recommended_for_promotion: bool = False
    recommended_increment_percentage: Optional[Decimal] = Field(None, ge=0, le=100)


class AppraisalHRReview(BaseModel):
    """Schema for HR review submission."""
    final_rating: Decimal = Field(..., ge=1, le=5)
    performance_band: str = Field(..., pattern="^(OUTSTANDING|EXCEEDS|MEETS|NEEDS_IMPROVEMENT|UNSATISFACTORY)$")
    hr_comments: Optional[str] = None


class AppraisalResponse(BaseResponseSchema):
    """Response schema for Appraisal."""
    id: UUID
    employee_id: UUID
    cycle_id: UUID
    status: str

    # Self Review
    self_rating: Optional[Decimal] = None
    self_comments: Optional[str] = None
    self_review_date: Optional[datetime] = None

    # Manager Review
    manager_id: Optional[UUID] = None
    manager_rating: Optional[Decimal] = None
    manager_comments: Optional[str] = None
    manager_review_date: Optional[datetime] = None

    # Final Rating
    final_rating: Optional[Decimal] = None
    performance_band: Optional[str] = None

    # Goals
    goals_achieved: int
    goals_total: int
    overall_goal_score: Optional[Decimal] = None

    # Development
    strengths: Optional[str] = None
    areas_of_improvement: Optional[str] = None
    development_plan: Optional[str] = None

    # Recommendations
    recommended_for_promotion: bool
    recommended_increment_percentage: Optional[Decimal] = None

    # HR Review
    hr_reviewed_by: Optional[UUID] = None
    hr_review_date: Optional[datetime] = None
    hr_comments: Optional[str] = None

    # Related info
    employee_name: Optional[str] = None
    employee_code: Optional[str] = None
    manager_name: Optional[str] = None
    cycle_name: Optional[str] = None

    created_at: datetime
    updated_at: datetime


class AppraisalListResponse(BaseModel):
    """Response for listing Appraisals."""
    items: List[AppraisalResponse]
    total: int
    page: int = 1
    size: int = 50
    pages: int = 1


# Performance Feedback
class FeedbackCreate(BaseModel):
    """Schema for creating feedback."""
    employee_id: UUID
    feedback_type: str = Field(..., pattern="^(APPRECIATION|IMPROVEMENT|SUGGESTION)$")
    title: str = Field(..., max_length=200)
    content: str
    is_private: bool = False
    goal_id: Optional[UUID] = None


class FeedbackResponse(BaseResponseSchema):
    """Response schema for Feedback."""
    id: UUID
    employee_id: UUID
    given_by: UUID
    feedback_type: str
    title: str
    content: str
    is_private: bool
    goal_id: Optional[UUID] = None

    # Related info
    employee_name: Optional[str] = None
    employee_code: Optional[str] = None
    given_by_name: Optional[str] = None
    goal_title: Optional[str] = None

    created_at: datetime


class FeedbackListResponse(BaseModel):
    """Response for listing Feedback."""
    items: List[FeedbackResponse]
    total: int
    page: int = 1
    size: int = 50
    pages: int = 1


# Performance Dashboard
class PerformanceDashboardStats(BaseModel):
    """Performance management dashboard statistics."""
    active_cycles: int
    pending_self_reviews: int
    pending_manager_reviews: int
    pending_hr_reviews: int

    # Goals summary
    total_goals: int
    completed_goals: int
    in_progress_goals: int
    overdue_goals: int

    # Rating distribution
    rating_distribution: List[dict]  # [{band: "EXCEEDS", count: 10}]

    # Recent feedback count
    recent_feedback_count: int


# Update forward references
PayrollDetailResponse.model_rebuild()
