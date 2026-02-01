from pydantic import BaseModel, Field, EmailStr, computed_field, ConfigDict

from app.schemas.base import BaseResponseSchema
from typing import Optional, List
from datetime import datetime, date
from decimal import Decimal
import uuid

from app.models.customer import CustomerType, CustomerSource, AddressType, CustomerTransactionType


# ==================== ADDRESS SCHEMAS ====================

class AddressBase(BaseModel):
    """Base address schema."""
    address_type: AddressType = AddressType.HOME
    contact_name: Optional[str] = Field(None, max_length=100)
    contact_phone: Optional[str] = Field(None, max_length=20)
    address_line1: str = Field(..., max_length=255)
    address_line2: Optional[str] = Field(None, max_length=255)
    landmark: Optional[str] = Field(None, max_length=200)
    city: str = Field(..., max_length=100)
    state: str = Field(..., max_length=100)
    pincode: str = Field(..., max_length=10)
    country: str = Field(default="India", max_length=100)
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    is_default: bool = False


class AddressCreate(AddressBase):
    """Address creation schema."""
    pass


class AddressUpdate(BaseModel):
    """Address update schema."""
    address_type: Optional[AddressType] = None
    contact_name: Optional[str] = None
    contact_phone: Optional[str] = None
    address_line1: Optional[str] = None
    address_line2: Optional[str] = None
    landmark: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    pincode: Optional[str] = None
    is_default: Optional[bool] = None
    is_active: Optional[bool] = None


class AddressResponse(BaseResponseSchema):
    """Address response schema."""
    id: uuid.UUID
    address_type: Optional[str] = None  # VARCHAR in DB
    contact_name: Optional[str] = None
    contact_phone: Optional[str] = None
    address_line1: Optional[str] = None
    address_line2: Optional[str] = None
    landmark: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    pincode: Optional[str] = None
    country: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    is_default: bool = False
    is_active: bool = True
    full_address: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
# ==================== CUSTOMER SCHEMAS ====================

class CustomerBase(BaseModel):
    """Base customer schema."""
    model_config = ConfigDict(populate_by_name=True)

    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: Optional[str] = Field(None, max_length=100)
    email: Optional[EmailStr] = None
    phone: str = Field(..., min_length=10, max_length=20)
    alternate_phone: Optional[str] = Field(None, max_length=20)
    customer_type: CustomerType = CustomerType.INDIVIDUAL
    source: CustomerSource = CustomerSource.WEBSITE
    company_name: Optional[str] = Field(None, max_length=200)
    gst_number: Optional[str] = Field(None, max_length=20, alias="gstin")
    date_of_birth: Optional[date] = None
    anniversary_date: Optional[date] = None
    region_id: Optional[uuid.UUID] = None
    gl_account_id: Optional[uuid.UUID] = None  # GL Account Link for Finance Integration
    notes: Optional[str] = None


class CustomerCreate(CustomerBase):
    """Customer creation schema."""
    addresses: Optional[List[AddressCreate]] = []


class CustomerUpdate(BaseModel):
    """Customer update schema."""
    model_config = ConfigDict(populate_by_name=True)

    first_name: Optional[str] = Field(None, max_length=100)
    last_name: Optional[str] = Field(None, max_length=100)
    email: Optional[EmailStr] = None
    phone: Optional[str] = Field(None, max_length=20)
    alternate_phone: Optional[str] = None
    customer_type: Optional[CustomerType] = None
    source: Optional[CustomerSource] = None
    company_name: Optional[str] = None
    gst_number: Optional[str] = Field(None, alias="gstin")
    date_of_birth: Optional[date] = None
    anniversary_date: Optional[date] = None
    region_id: Optional[uuid.UUID] = None
    gl_account_id: Optional[uuid.UUID] = None  # GL Account Link
    notes: Optional[str] = None
    is_active: Optional[bool] = None


class CustomerResponse(BaseResponseSchema):
    """Customer response schema."""
    id: uuid.UUID
    customer_code: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    full_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    alternate_phone: Optional[str] = None
    customer_type: Optional[str] = None  # VARCHAR in DB
    source: Optional[str] = None
    company_name: Optional[str] = None
    gst_number: Optional[str] = None
    date_of_birth: Optional[date] = None
    anniversary_date: Optional[date] = None
    is_active: bool = True
    is_verified: bool = False
    notes: Optional[str] = None
    gl_account_id: Optional[uuid.UUID] = None  # Linked GL account
    addresses: List[AddressResponse] = []
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    # Frontend compatibility alias
    @computed_field
    @property
    def name(self) -> str:
        """Alias for full_name - frontend expects 'name'."""
        return self.full_name

class CustomerBrief(BaseResponseSchema):
    """Brief customer info."""
    id: uuid.UUID
    customer_code: str
    full_name: str
    phone: str
    email: Optional[str] = None

    # Frontend compatibility alias
    @computed_field
    @property
    def name(self) -> str:
        """Alias for full_name - frontend expects 'name'."""
        return self.full_name
class CustomerListResponse(BaseModel):
    """Paginated customer list."""
    items: List[CustomerResponse]
    total: int
    page: int
    size: int
    pages: int


# ==================== CUSTOMER 360 SCHEMAS ====================

class Customer360OrderSummary(BaseResponseSchema):
    """Order summary for Customer 360."""
    id: uuid.UUID
    order_number: str
    status: str
    total_amount: float
    payment_status: Optional[str] = None
    items_count: int = 0
    created_at: Optional[datetime] = None
class Customer360OrderStatusHistory(BaseResponseSchema):
    """Order status history entry."""
    from_status: Optional[str] = None
    to_status: str
    notes: Optional[str] = None
    changed_by: Optional[str] = None
    created_at: Optional[datetime] = None
class Customer360ShipmentSummary(BaseResponseSchema):
    """Shipment summary for Customer 360."""
    id: uuid.UUID
    shipment_number: str
    order_number: Optional[str] = None
    status: str
    awb_number: Optional[str] = None
    transporter_name: Optional[str] = None
    delivered_to: Optional[str] = None
    delivered_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
class Customer360ShipmentTracking(BaseResponseSchema):
    """Shipment tracking entry."""
    status: str
    location: Optional[str] = None
    city: Optional[str] = None
    remarks: Optional[str] = None
    event_time: Optional[datetime] = None
class Customer360InstallationSummary(BaseResponseSchema):
    """Installation summary for Customer 360."""
    id: uuid.UUID
    installation_number: str
    status: str
    product_name: Optional[str] = None
    installation_pincode: Optional[str] = None
    franchisee_name: Optional[str] = None
    scheduled_date: Optional[date] = None
    completed_at: Optional[datetime] = None
    customer_rating: Optional[int] = None
    warranty_end_date: Optional[date] = None
    created_at: Optional[datetime] = None
class Customer360ServiceRequestSummary(BaseResponseSchema):
    """Service request summary for Customer 360."""
    id: uuid.UUID
    ticket_number: str
    service_type: str
    status: str
    priority: Optional[str] = None
    title: Optional[str] = None
    franchisee_name: Optional[str] = None
    technician_name: Optional[str] = None
    scheduled_date: Optional[date] = None
    completed_at: Optional[datetime] = None
    customer_rating: Optional[int] = None
    created_at: Optional[datetime] = None
class Customer360ServiceStatusHistory(BaseResponseSchema):
    """Service request status history entry."""
    from_status: Optional[str] = None
    to_status: str
    notes: Optional[str] = None
    changed_by: Optional[str] = None
    created_at: Optional[datetime] = None
class Customer360CallSummary(BaseResponseSchema):
    """Call summary for Customer 360."""
    id: uuid.UUID
    call_id: Optional[str] = None
    call_type: str
    category: str
    status: str
    outcome: Optional[str] = None
    duration_seconds: Optional[int] = None
    agent_name: Optional[str] = None
    call_start_time: Optional[datetime] = None
    sentiment: Optional[str] = None
class Customer360PaymentSummary(BaseResponseSchema):
    """Payment summary for Customer 360."""
    id: uuid.UUID
    order_number: Optional[str] = None
    amount: float
    method: Optional[str] = None
    status: str
    transaction_id: Optional[str] = None
    gateway: Optional[str] = None
    completed_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
class Customer360AMCSummary(BaseResponseSchema):
    """AMC contract summary for Customer 360."""
    id: uuid.UUID
    contract_number: str
    plan_name: str
    status: str
    start_date: date
    end_date: date
    total_services: int
    services_used: int
    services_remaining: int
    next_service_due: Optional[date] = None
class Customer360LeadSummary(BaseResponseSchema):
    """Lead summary (if converted from lead)."""
    id: uuid.UUID
    lead_number: str
    status: str
    source: str
    converted_at: Optional[datetime] = None
class Customer360LeadActivity(BaseResponseSchema):
    """Lead activity entry."""
    activity_type: str
    subject: str
    outcome: Optional[str] = None
    old_status: Optional[str] = None
    new_status: Optional[str] = None
    activity_date: datetime
class Customer360Stats(BaseModel):
    """Customer statistics summary."""
    total_orders: int = 0
    total_order_value: float = 0.0
    delivered_orders: int = 0
    pending_orders: int = 0
    total_installations: int = 0
    completed_installations: int = 0
    total_service_requests: int = 0
    open_service_requests: int = 0
    total_calls: int = 0
    active_amc_contracts: int = 0
    average_rating: Optional[float] = None
    customer_since_days: int = 0


class Customer360Timeline(BaseModel):
    """Timeline event for customer journey."""
    event_type: str  # ORDER, SHIPMENT, INSTALLATION, SERVICE, CALL, PAYMENT
    event_id: uuid.UUID
    title: str
    description: Optional[str] = None
    status: str
    timestamp: datetime
    metadata: Optional[dict] = None


class Customer360Response(BaseResponseSchema):
    """
    Complete Customer 360 view with all journey data.
    """
    # Customer Profile
    customer: CustomerResponse

    # Statistics Summary
    stats: Customer360Stats

    # Journey Timeline (chronological events)
    timeline: List[Customer360Timeline] = []

    # Orders
    orders: List[Customer360OrderSummary] = []
    recent_order_history: List[Customer360OrderStatusHistory] = []

    # Shipments
    shipments: List[Customer360ShipmentSummary] = []
    recent_shipment_tracking: List[Customer360ShipmentTracking] = []

    # Installations
    installations: List[Customer360InstallationSummary] = []

    # Service Requests
    service_requests: List[Customer360ServiceRequestSummary] = []
    recent_service_history: List[Customer360ServiceStatusHistory] = []

    # Calls
    calls: List[Customer360CallSummary] = []

    # Payments
    payments: List[Customer360PaymentSummary] = []

    # AMC Contracts
    amc_contracts: List[Customer360AMCSummary] = []

    # Lead Info (if converted from lead)
    lead: Optional[Customer360LeadSummary] = None
    lead_activities: List[Customer360LeadActivity] = []
# ==================== CUSTOMER LEDGER SCHEMAS ====================

class CustomerLedgerBase(BaseModel):
    """Base schema for CustomerLedger."""
    customer_id: uuid.UUID
    transaction_type: CustomerTransactionType
    transaction_date: date
    due_date: Optional[date] = None
    reference_type: str = Field(..., max_length=50)
    reference_number: str = Field(..., max_length=50)
    reference_id: Optional[uuid.UUID] = None
    order_id: Optional[uuid.UUID] = None
    debit_amount: Decimal = Field(Decimal("0"), ge=0)
    credit_amount: Decimal = Field(Decimal("0"), ge=0)
    tax_amount: Decimal = Field(Decimal("0"), ge=0)
    description: Optional[str] = Field(None, max_length=500)
    notes: Optional[str] = None
    channel_id: Optional[uuid.UUID] = None


class CustomerLedgerCreate(CustomerLedgerBase):
    """Schema for creating customer ledger entry."""
    pass


class CustomerLedgerResponse(BaseResponseSchema):
    """Response schema for customer ledger entry."""
    id: uuid.UUID
    customer_id: uuid.UUID
    transaction_type: str  # VARCHAR in DB
    transaction_date: date
    due_date: Optional[date] = None
    reference_type: str
    reference_number: str
    reference_id: Optional[uuid.UUID] = None
    order_id: Optional[uuid.UUID] = None
    debit_amount: Decimal
    credit_amount: Decimal
    balance: Decimal
    tax_amount: Decimal = Decimal("0")
    is_settled: bool
    settled_date: Optional[date] = None
    description: Optional[str] = None
    notes: Optional[str] = None
    channel_id: Optional[uuid.UUID] = None
    created_at: datetime

    # Computed fields
    @computed_field
    @property
    def is_overdue(self) -> bool:
        """Check if overdue."""
        if self.is_settled or not self.due_date:
            return False
        return date.today() > self.due_date

    @computed_field
    @property
    def days_overdue(self) -> int:
        """Days overdue."""
        if not self.is_overdue:
            return 0
        return (date.today() - self.due_date).days


class CustomerLedgerListResponse(BaseModel):
    """Response for customer ledger list."""
    items: List[CustomerLedgerResponse]
    total: int
    opening_balance: Decimal
    total_debit: Decimal
    total_credit: Decimal
    closing_balance: Decimal


class CustomerPaymentCreate(BaseModel):
    """Schema for recording customer payment."""
    customer_id: uuid.UUID
    amount: Decimal = Field(..., gt=0)
    payment_date: date
    payment_mode: str = Field(..., description="CASH, CHEQUE, RTGS, NEFT, UPI, CARD, NET_BANKING")
    reference_number: str = Field(..., max_length=50)
    order_id: Optional[uuid.UUID] = None
    invoice_id: Optional[uuid.UUID] = None
    cheque_number: Optional[str] = None
    cheque_date: Optional[date] = None
    bank_name: Optional[str] = None
    remarks: Optional[str] = None


# ==================== AR AGING SCHEMAS ====================

class ARAgingBucket(BaseModel):
    """Single aging bucket."""
    bucket: str  # CURRENT, 1_30, 31_60, 61_90, OVER_90
    amount: Decimal
    count: int


class CustomerAgingResponse(BaseModel):
    """Aging details for a single customer."""
    customer_id: uuid.UUID
    customer_code: str
    customer_name: str
    customer_type: str
    total_outstanding: Decimal
    current: Decimal = Decimal("0")
    days_1_30: Decimal = Decimal("0")
    days_31_60: Decimal = Decimal("0")
    days_61_90: Decimal = Decimal("0")
    over_90_days: Decimal = Decimal("0")
    buckets: List[ARAgingBucket] = []


class ARAgingReport(BaseModel):
    """Complete AR Aging Report."""
    as_of_date: date
    total_outstanding: Decimal
    total_current: Decimal
    total_1_30: Decimal
    total_31_60: Decimal
    total_61_90: Decimal
    total_over_90: Decimal
    customers: List[CustomerAgingResponse]
    summary_buckets: List[ARAgingBucket]


class ARAgingSummary(BaseModel):
    """Summary of AR Aging for dashboard."""
    as_of_date: date
    total_outstanding: Decimal
    total_customers_with_outstanding: int
    buckets: List[ARAgingBucket]
    top_overdue_customers: List[CustomerAgingResponse] = []
