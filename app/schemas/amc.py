"""AMC (Annual Maintenance Contract) schemas for API requests/responses."""
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime, date
import uuid

from app.models.amc import AMCType, AMCStatus
from app.schemas.customer import CustomerBrief
from app.schemas.base import BaseResponseSchema


class AMCContractCreate(BaseModel):
    """AMC contract creation schema."""
    amc_type: AMCType = AMCType.STANDARD
    customer_id: uuid.UUID
    customer_address_id: Optional[uuid.UUID] = None
    product_id: uuid.UUID
    installation_id: Optional[uuid.UUID] = None
    serial_number: str = Field(
        ...,
        min_length=1,
        description="Serial number of the product. Required to link AMC to specific unit."
    )
    start_date: date
    duration_months: int = Field(12, ge=1, le=60)
    total_services: int = Field(2, ge=1, le=12)
    base_price: float = Field(..., ge=0)
    tax_amount: float = Field(0, ge=0)
    discount_amount: float = Field(0, ge=0)
    parts_covered: bool = False
    labor_covered: bool = True
    emergency_support: bool = False
    priority_service: bool = False
    discount_on_parts: float = Field(0, ge=0, le=100)
    terms_and_conditions: Optional[str] = None
    notes: Optional[str] = None


class AMCContractUpdate(BaseModel):
    """AMC contract update schema."""
    customer_address_id: Optional[uuid.UUID] = None
    total_services: Optional[int] = None
    parts_covered: Optional[bool] = None
    labor_covered: Optional[bool] = None
    emergency_support: Optional[bool] = None
    priority_service: Optional[bool] = None
    discount_on_parts: Optional[float] = None
    terms_and_conditions: Optional[str] = None
    notes: Optional[str] = None
    internal_notes: Optional[str] = None


class AMCPayment(BaseModel):
    """AMC payment data."""
    payment_mode: str
    payment_reference: Optional[str] = None


class AMCServiceSchedule(BaseModel):
    """AMC service scheduling."""
    scheduled_date: date
    notes: Optional[str] = None


class AMCContractResponse(BaseResponseSchema):
    """AMC contract response schema."""
    id: uuid.UUID
    contract_number: str
    amc_type: str  # VARCHAR in DB
    status: str
    customer: CustomerBrief
    product_id: uuid.UUID
    serial_number: str  # Required - links AMC to specific product unit
    start_date: date
    end_date: date
    duration_months: int
    total_services: int
    services_used: int
    services_remaining: int
    total_amount: float
    payment_status: str
    is_active: bool
    days_remaining: int
    next_service_due: Optional[date] = None
    created_at: datetime
    updated_at: datetime

class AMCContractDetail(AMCContractResponse):
    """Detailed AMC contract response."""
    installation_id: Optional[uuid.UUID] = None
    base_price: float
    tax_amount: float
    discount_amount: float
    payment_mode: Optional[str] = None
    payment_reference: Optional[str] = None
    paid_at: Optional[datetime] = None
    parts_covered: bool
    labor_covered: bool
    emergency_support: bool
    priority_service: bool
    discount_on_parts: float
    terms_and_conditions: Optional[str] = None
    is_renewable: bool
    renewal_reminder_sent: bool
    renewed_from_id: Optional[uuid.UUID] = None
    renewed_to_id: Optional[uuid.UUID] = None
    service_schedule: Optional[List[dict]] = None
    notes: Optional[str] = None
    product_name: Optional[str] = None


class AMCContractListResponse(BaseModel):
    """Paginated AMC contract list."""
    items: List[AMCContractResponse]
    total: int
    page: int
    size: int
    pages: int


# ==================== AMC PLAN SCHEMAS ====================

class AMCPlanCreate(BaseModel):
    """AMC plan creation schema."""
    name: str = Field(..., max_length=200)
    code: str = Field(..., max_length=20)
    amc_type: AMCType = AMCType.STANDARD
    category_id: Optional[uuid.UUID] = None
    product_ids: Optional[List[uuid.UUID]] = None
    duration_months: int = 12
    base_price: float = Field(..., ge=0)
    tax_rate: float = Field(18, ge=0, le=100)
    services_included: int = Field(2, ge=1)
    parts_covered: bool = False
    labor_covered: bool = True
    emergency_support: bool = False
    priority_service: bool = False
    discount_on_parts: float = Field(0, ge=0, le=100)
    terms_and_conditions: Optional[str] = None
    description: Optional[str] = None


class AMCPlanUpdate(BaseModel):
    """AMC plan update schema."""
    name: Optional[str] = None
    base_price: Optional[float] = None
    tax_rate: Optional[float] = None
    services_included: Optional[int] = None
    parts_covered: Optional[bool] = None
    labor_covered: Optional[bool] = None
    emergency_support: Optional[bool] = None
    priority_service: Optional[bool] = None
    discount_on_parts: Optional[float] = None
    terms_and_conditions: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None
    sort_order: Optional[int] = None


class AMCPlanResponse(BaseResponseSchema):
    """AMC plan response schema."""
    id: uuid.UUID
    name: str
    code: str
    amc_type: str  # VARCHAR in DB
    category_id: Optional[uuid.UUID] = None
    duration_months: int
    base_price: float
    tax_rate: float
    services_included: int
    parts_covered: bool
    labor_covered: bool
    emergency_support: bool
    priority_service: bool
    discount_on_parts: float
    description: Optional[str] = None
    is_active: bool
    sort_order: int
    created_at: datetime

class AMCPlanListResponse(BaseModel):
    """Paginated AMC plan list."""
    items: List[AMCPlanResponse]
    total: int
    page: int
    size: int
    pages: int
