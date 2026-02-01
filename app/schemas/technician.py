"""Technician schemas for API requests/responses."""
from pydantic import BaseModel, Field, ConfigDict

from app.schemas.base import BaseResponseSchema
from typing import Optional, List
from datetime import datetime, date
import uuid

from app.models.technician import TechnicianStatus, TechnicianType, SkillLevel


class TechnicianCreate(BaseModel):
    """Technician creation schema."""
    first_name: str = Field(..., max_length=100)
    last_name: Optional[str] = Field(None, max_length=100)
    phone: str = Field(..., max_length=20)
    alternate_phone: Optional[str] = None
    email: Optional[str] = None
    user_id: Optional[uuid.UUID] = None
    technician_type: TechnicianType = TechnicianType.INTERNAL
    date_of_joining: Optional[date] = None
    skill_level: SkillLevel = SkillLevel.JUNIOR
    specializations: Optional[List[str]] = None
    region_id: Optional[uuid.UUID] = None
    assigned_warehouse_id: Optional[uuid.UUID] = None
    service_pincodes: Optional[List[str]] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    pincode: Optional[str] = None
    aadhaar_number: Optional[str] = None
    pan_number: Optional[str] = None
    driving_license: Optional[str] = None
    bank_name: Optional[str] = None
    bank_account_number: Optional[str] = None
    ifsc_code: Optional[str] = None
    notes: Optional[str] = None


class TechnicianUpdate(BaseModel):
    """Technician update schema."""
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone: Optional[str] = None
    alternate_phone: Optional[str] = None
    email: Optional[str] = None
    status: Optional[TechnicianStatus] = None
    skill_level: Optional[SkillLevel] = None
    specializations: Optional[List[str]] = None
    certifications: Optional[List[dict]] = None
    region_id: Optional[uuid.UUID] = None
    assigned_warehouse_id: Optional[uuid.UUID] = None
    service_pincodes: Optional[List[str]] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    pincode: Optional[str] = None
    is_available: Optional[bool] = None
    notes: Optional[str] = None


class TechnicianResponse(BaseResponseSchema):
    """Technician response schema."""
    id: uuid.UUID
    employee_code: str
    first_name: str
    last_name: Optional[str] = None
    full_name: str
    phone: str
    alternate_phone: Optional[str] = None
    email: Optional[str] = None
    technician_type: str  # VARCHAR in DB
    status: str
    skill_level: str  # VARCHAR in DB
    specializations: Optional[List[str]] = None
    region_id: Optional[uuid.UUID] = None
    assigned_warehouse_id: Optional[uuid.UUID] = None
    service_pincodes: Optional[List[str]] = None
    city: Optional[str] = None
    state: Optional[str] = None
    total_jobs_completed: int
    average_rating: float
    current_month_jobs: int
    is_available: bool
    created_at: datetime
    updated_at: datetime

class TechnicianDetail(TechnicianResponse):
    """Detailed technician response."""
    user_id: Optional[uuid.UUID] = None
    date_of_joining: Optional[date] = None
    date_of_leaving: Optional[date] = None
    certifications: Optional[List[dict]] = None
    address: Optional[str] = None
    pincode: Optional[str] = None
    aadhaar_number: Optional[str] = None
    pan_number: Optional[str] = None
    driving_license: Optional[str] = None
    id_proof_url: Optional[str] = None
    photo_url: Optional[str] = None
    bank_name: Optional[str] = None
    bank_account_number: Optional[str] = None
    ifsc_code: Optional[str] = None
    total_ratings: int
    last_job_date: Optional[datetime] = None
    notes: Optional[str] = None


class TechnicianBrief(BaseResponseSchema):
    """Brief technician info for dropdowns."""
    id: uuid.UUID
    employee_code: str
    full_name: str
    phone: str
    skill_level: str  # VARCHAR in DB
    is_available: bool
    average_rating: float
class TechnicianListResponse(BaseModel):
    """Paginated technician list."""
    items: List[TechnicianResponse]
    total: int
    page: int
    size: int
    pages: int


class TechnicianLocationUpdate(BaseModel):
    """Update technician location."""
    latitude: float
    longitude: float


class TechnicianLeaveCreate(BaseModel):
    """Technician leave creation schema."""
    leave_type: str  # sick, casual, earned, emergency
    from_date: date
    to_date: date
    reason: Optional[str] = None


class TechnicianLeaveResponse(BaseResponseSchema):
    """Technician leave response schema."""
    id: uuid.UUID
    technician_id: uuid.UUID
    leave_type: str
    from_date: date
    to_date: date
    reason: Optional[str] = None
    status: str
    approved_by: Optional[uuid.UUID] = None
    approved_at: Optional[datetime] = None
    rejection_reason: Optional[str] = None
    created_at: datetime

class TechnicianPerformance(BaseModel):
    """Technician performance metrics."""
    technician_id: uuid.UUID
    total_jobs: int
    completed_jobs: int
    pending_jobs: int
    average_rating: float
    total_ratings: int
    on_time_completion_rate: float
    average_job_time_minutes: float
    monthly_earnings: float
