"""Pydantic schemas for Dealer/Distributor module."""
from datetime import datetime, date
from typing import Optional, List
from decimal import Decimal
from uuid import UUID
from pydantic import BaseModel, Field, ConfigDict, EmailStr, field_validator

from app.schemas.base import BaseResponseSchema

from app.models.dealer import (
    DealerType, DealerStatus, DealerTier, CreditStatus,
    TransactionType, SchemeType
)


# ==================== Dealer Schemas ====================

class DealerBase(BaseModel):
    """Base schema for Dealer."""
    model_config = ConfigDict(populate_by_name=True)

    name: str = Field(..., min_length=2, max_length=200)
    legal_name: str = Field(..., min_length=2, max_length=200)
    display_name: Optional[str] = None
    dealer_type: str  # VARCHAR in DB: DISTRIBUTOR, RETAILER, FRANCHISE, etc.
    tier: str = "STANDARD"  # VARCHAR in DB: PLATINUM, GOLD, SILVER, BRONZE, STANDARD

    # GST & Tax
    gstin: str = Field(..., min_length=15, max_length=15, alias="gst_number")
    pan: str = Field(..., min_length=10, max_length=10)
    tan: Optional[str] = Field(None, min_length=10, max_length=10)
    gst_registration_type: str = Field("REGULAR", max_length=30)
    is_msme: bool = False
    msme_number: Optional[str] = None

    # Contact
    contact_person: str = Field(..., min_length=2, max_length=200)
    email: EmailStr
    phone: str = Field(..., min_length=10, max_length=20)
    alternate_phone: Optional[str] = None
    whatsapp: Optional[str] = None

    # Registered Address
    registered_address_line1: str = Field(..., min_length=5, max_length=255)
    registered_address_line2: Optional[str] = None
    registered_city: str = Field(..., max_length=100)
    registered_district: str = Field(..., max_length=100)
    registered_state: str = Field(..., max_length=100)
    registered_state_code: str = Field(..., min_length=2, max_length=2)
    registered_pincode: str = Field(..., min_length=6, max_length=10)

    # Shipping Address
    shipping_address_line1: Optional[str] = None
    shipping_address_line2: Optional[str] = None
    shipping_city: Optional[str] = None
    shipping_state: Optional[str] = None
    shipping_pincode: Optional[str] = None

    # Territory
    region: str = Field(..., max_length=50)
    state: str = Field(..., max_length=100)
    territory: Optional[str] = None
    assigned_pincodes: Optional[List[str]] = None

    # Business Details
    business_type: str = Field("PROPRIETORSHIP", max_length=50)
    establishment_year: Optional[int] = Field(None, ge=1900, le=2100)
    annual_turnover: Optional[Decimal] = Field(None, ge=0)
    shop_area_sqft: Optional[int] = Field(None, ge=0)
    no_of_employees: Optional[int] = Field(None, ge=0)
    existing_brands: Optional[List[str]] = None


class DealerCreate(DealerBase):
    """Schema for creating Dealer."""
    parent_dealer_id: Optional[UUID] = None
    user_id: Optional[UUID] = None

    # Bank Details
    bank_name: Optional[str] = None
    bank_branch: Optional[str] = None
    bank_account_number: Optional[str] = None
    bank_ifsc: Optional[str] = None
    bank_account_name: Optional[str] = None

    # Credit Terms
    credit_limit: Decimal = Field(Decimal("0"), ge=0)
    credit_days: int = Field(30, ge=0)
    opening_balance: Decimal = Field(Decimal("0"))

    # Security Deposit
    security_deposit: Decimal = Field(Decimal("0"), ge=0)

    # Assignment
    default_warehouse_id: Optional[UUID] = None
    sales_rep_id: Optional[UUID] = None
    area_sales_manager_id: Optional[UUID] = None

    # Agreement
    agreement_start_date: Optional[date] = None
    agreement_end_date: Optional[date] = None

    # Settings
    can_place_orders: bool = True
    receive_promotions: bool = True
    portal_access: bool = True
    internal_notes: Optional[str] = None


class DealerUpdate(BaseModel):
    """Schema for updating Dealer."""
    name: Optional[str] = None
    legal_name: Optional[str] = None
    display_name: Optional[str] = None
    status: Optional[str] = None  # VARCHAR: ACTIVE, INACTIVE, SUSPENDED, PENDING
    tier: Optional[str] = None  # VARCHAR: PLATINUM, GOLD, SILVER, BRONZE, STANDARD
    contact_person: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    alternate_phone: Optional[str] = None
    whatsapp: Optional[str] = None

    # Address updates
    registered_address_line1: Optional[str] = None
    registered_address_line2: Optional[str] = None
    registered_city: Optional[str] = None
    registered_state: Optional[str] = None
    registered_pincode: Optional[str] = None

    shipping_address_line1: Optional[str] = None
    shipping_city: Optional[str] = None
    shipping_state: Optional[str] = None
    shipping_pincode: Optional[str] = None

    # Territory
    region: Optional[str] = None
    territory: Optional[str] = None
    assigned_pincodes: Optional[List[str]] = None

    # Bank Details
    bank_name: Optional[str] = None
    bank_branch: Optional[str] = None
    bank_account_number: Optional[str] = None
    bank_ifsc: Optional[str] = None

    # Credit
    credit_limit: Optional[Decimal] = None
    credit_days: Optional[int] = None
    credit_status: Optional[CreditStatus] = None

    # Assignment
    default_warehouse_id: Optional[UUID] = None
    sales_rep_id: Optional[UUID] = None
    area_sales_manager_id: Optional[UUID] = None

    # Agreement
    agreement_end_date: Optional[date] = None

    # Settings
    can_place_orders: Optional[bool] = None
    receive_promotions: Optional[bool] = None
    portal_access: Optional[bool] = None
    internal_notes: Optional[str] = None


class DealerResponse(BaseResponseSchema):
    """Response schema for Dealer."""
    id: UUID
    dealer_code: str
    status: str
    parent_dealer_id: Optional[UUID] = None
    user_id: Optional[UUID] = None

    # Basic Info
    name: Optional[str] = None
    legal_name: Optional[str] = None
    display_name: Optional[str] = None
    dealer_type: Optional[str] = None
    tier: Optional[str] = None

    # GST & Tax
    gstin: Optional[str] = None
    pan: Optional[str] = None
    tan: Optional[str] = None
    gst_registration_type: Optional[str] = None
    is_msme: Optional[bool] = None
    msme_number: Optional[str] = None

    # Contact
    contact_person: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    alternate_phone: Optional[str] = None
    whatsapp: Optional[str] = None

    # Registered Address
    registered_address_line1: Optional[str] = None
    registered_address_line2: Optional[str] = None
    registered_city: Optional[str] = None
    registered_district: Optional[str] = None
    registered_state: Optional[str] = None
    registered_state_code: Optional[str] = None
    registered_pincode: Optional[str] = None

    # Shipping Address
    shipping_address_line1: Optional[str] = None
    shipping_address_line2: Optional[str] = None
    shipping_city: Optional[str] = None
    shipping_state: Optional[str] = None
    shipping_pincode: Optional[str] = None

    # Territory
    region: Optional[str] = None
    state: Optional[str] = None
    territory: Optional[str] = None
    assigned_pincodes: Optional[List[str]] = None

    # Business Details
    business_type: Optional[str] = None
    establishment_year: Optional[int] = None
    annual_turnover: Optional[Decimal] = None
    shop_area_sqft: Optional[int] = None
    no_of_employees: Optional[int] = None
    existing_brands: Optional[List[str]] = None

    # Bank Details
    bank_name: Optional[str] = None
    bank_branch: Optional[str] = None
    bank_account_number: Optional[str] = None
    bank_ifsc: Optional[str] = None
    bank_account_name: Optional[str] = None

    # Credit
    credit_limit: Decimal
    credit_days: int
    credit_status: CreditStatus
    outstanding_amount: Decimal
    overdue_amount: Decimal
    available_credit: Decimal
    credit_utilization_percentage: Decimal
    opening_balance: Optional[Decimal] = None

    # Security
    security_deposit: Decimal
    security_deposit_paid: bool

    # Assignment
    default_warehouse_id: Optional[UUID] = None
    sales_rep_id: Optional[UUID] = None
    area_sales_manager_id: Optional[UUID] = None

    # Agreement
    agreement_start_date: Optional[date] = None
    agreement_end_date: Optional[date] = None

    # Settings
    can_place_orders: Optional[bool] = None
    receive_promotions: Optional[bool] = None
    portal_access: Optional[bool] = None
    internal_notes: Optional[str] = None

    # KYC
    kyc_verified: bool
    kyc_verified_at: Optional[datetime] = None
    kyc_verified_by: Optional[UUID] = None

    # Performance
    total_orders: int
    total_revenue: Decimal
    last_order_date: Optional[datetime] = None
    average_order_value: Optional[Decimal] = None
    dealer_rating: Optional[Decimal] = None
    payment_rating: Optional[Decimal] = None

    # Documents
    gst_certificate_url: Optional[str] = None
    pan_card_url: Optional[str] = None
    shop_photo_url: Optional[str] = None
    agreement_document_url: Optional[str] = None
    cancelled_cheque_url: Optional[str] = None

    # Timestamps
    onboarded_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime


class DealerListResponse(BaseModel):
    """Response for listing dealers."""
    items: List[DealerResponse]
    total: int
    page: int = 1
    size: int = 50
    pages: int = 1


class DealerBrief(BaseModel):
    """Brief dealer for dropdowns and list views."""
    id: UUID
    dealer_code: str
    name: str
    legal_name: Optional[str] = None
    dealer_type: Optional[str] = None
    tier: Optional[str] = None
    status: str
    # Contact
    contact_person: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    # Location
    registered_city: Optional[str] = None
    registered_state: Optional[str] = None
    region: Optional[str] = None
    # Tax IDs
    gstin: Optional[str] = None
    pan: Optional[str] = None
    # Credit
    credit_limit: Optional[Decimal] = None
    outstanding_amount: Optional[Decimal] = None
    available_credit: Optional[Decimal] = None
    # Bank Details (for edit)
    bank_name: Optional[str] = None
    bank_branch: Optional[str] = None
    bank_account_number: Optional[str] = None
    bank_ifsc: Optional[str] = None
    bank_account_name: Optional[str] = None


class DealerApproveRequest(BaseModel):
    """Request to approve dealer."""
    dealer_id: UUID
    credit_limit: Optional[Decimal] = None
    credit_days: Optional[int] = None
    tier: Optional[str] = None  # VARCHAR: PLATINUM, GOLD, SILVER, BRONZE, STANDARD


class DealerKYCRequest(BaseModel):
    """Request to verify KYC."""
    dealer_id: UUID
    verified: bool
    remarks: Optional[str] = None


# ==================== DealerPricing Schemas ====================

class DealerPricingBase(BaseModel):
    """Base schema for DealerPricing."""
    dealer_id: UUID
    product_id: UUID
    variant_id: Optional[UUID] = None
    mrp: Decimal = Field(..., gt=0)
    dealer_price: Decimal = Field(..., gt=0)
    special_price: Optional[Decimal] = Field(None, gt=0)
    margin_percentage: Optional[Decimal] = Field(None, ge=0, le=100)
    minimum_margin: Optional[Decimal] = Field(None, ge=0, le=100)
    moq: int = Field(1, ge=1)
    effective_from: date
    effective_to: Optional[date] = None
    is_active: bool = True


class DealerPricingCreate(DealerPricingBase):
    """Schema for creating DealerPricing."""
    pass


class DealerPricingUpdate(BaseModel):
    """Schema for updating DealerPricing."""
    dealer_price: Optional[Decimal] = None
    special_price: Optional[Decimal] = None
    margin_percentage: Optional[Decimal] = None
    moq: Optional[int] = None
    effective_to: Optional[date] = None
    is_active: Optional[bool] = None


class DealerPricingResponse(BaseResponseSchema):
    """Response schema for DealerPricing."""
    id: UUID
    dealer_margin: Decimal
    created_at: datetime
    updated_at: datetime


class DealerPricingBulkCreate(BaseModel):
    """Bulk create dealer pricing."""
    dealer_id: UUID
    items: List[dict]  # [{"product_id": uuid, "mrp": 1000, "dealer_price": 800}]


# ==================== DealerTierPricing Schemas ====================

class DealerTierPricingBase(BaseModel):
    """Base schema for DealerTierPricing."""
    tier: str = Field(..., pattern="^(PLATINUM|GOLD|SILVER|BRONZE|STANDARD)$")  # VARCHAR in DB
    product_id: UUID
    variant_id: Optional[UUID] = None
    discount_percentage: Decimal = Field(..., ge=0, le=100)
    fixed_price: Optional[Decimal] = Field(None, gt=0)
    is_active: bool = True
    effective_from: date
    effective_to: Optional[date] = None


class DealerTierPricingCreate(DealerTierPricingBase):
    """Schema for creating tier pricing."""
    pass


class DealerTierPricingResponse(BaseResponseSchema):
    """Response schema for tier pricing."""
    id: UUID
    created_at: datetime
    updated_at: datetime


# ==================== DealerCreditLedger Schemas ====================

class DealerCreditLedgerBase(BaseModel):
    """Base schema for DealerCreditLedger."""
    dealer_id: UUID
    transaction_type: TransactionType
    transaction_date: date
    due_date: Optional[date] = None
    reference_type: str = Field(..., max_length=50)
    reference_number: str = Field(..., max_length=50)
    reference_id: Optional[UUID] = None
    debit_amount: Decimal = Field(Decimal("0"), ge=0)
    credit_amount: Decimal = Field(Decimal("0"), ge=0)
    payment_mode: Optional[str] = None
    cheque_number: Optional[str] = None
    transaction_reference: Optional[str] = None
    remarks: Optional[str] = None


class DealerCreditLedgerCreate(DealerCreditLedgerBase):
    """Schema for creating ledger entry."""
    pass


class DealerCreditLedgerResponse(BaseResponseSchema):
    """Response schema for ledger entry."""
    id: UUID
    balance: Decimal
    is_settled: bool
    settled_date: Optional[date] = None
    days_overdue: int
    created_at: datetime


class DealerLedgerListResponse(BaseModel):
    """Response for dealer ledger."""
    items: List[DealerCreditLedgerResponse]
    total: int
    opening_balance: Decimal
    total_debit: Decimal
    total_credit: Decimal
    closing_balance: Decimal


# Alias for backward compatibility
DealerCreditLedgerListResponse = DealerLedgerListResponse


class DealerPaymentCreate(BaseModel):
    """Schema for recording dealer payment."""
    dealer_id: UUID
    amount: Decimal = Field(..., gt=0)
    payment_date: date
    payment_mode: str
    reference_number: str
    cheque_number: Optional[str] = None
    cheque_date: Optional[date] = None
    bank_name: Optional[str] = None
    remarks: Optional[str] = None


# ==================== DealerTarget Schemas ====================

class DealerTargetBase(BaseModel):
    """Base schema for DealerTarget."""
    dealer_id: UUID
    target_period: str = Field(..., pattern="^(MONTHLY|QUARTERLY|ANNUAL)$")
    target_year: int = Field(..., ge=2020, le=2100)
    target_month: Optional[int] = Field(None, ge=1, le=12)
    target_quarter: Optional[int] = Field(None, ge=1, le=4)
    target_type: str = Field("REVENUE", pattern="^(REVENUE|QUANTITY|BOTH)$")
    category_id: Optional[UUID] = None
    product_id: Optional[UUID] = None
    revenue_target: Decimal = Field(Decimal("0"), ge=0)
    quantity_target: int = Field(0, ge=0)
    incentive_percentage: Optional[Decimal] = Field(None, ge=0, le=100)


class DealerTargetCreate(DealerTargetBase):
    """Schema for creating DealerTarget."""
    pass


class DealerTargetUpdate(BaseModel):
    """Schema for updating DealerTarget."""
    revenue_target: Optional[Decimal] = None
    quantity_target: Optional[int] = None
    incentive_percentage: Optional[Decimal] = None


class DealerTargetResponse(BaseResponseSchema):
    """Response schema for DealerTarget."""
    id: UUID
    revenue_achieved: Decimal
    quantity_achieved: int
    revenue_achievement_percentage: Decimal
    quantity_achievement_percentage: Decimal
    incentive_earned: Decimal
    is_incentive_paid: bool
    is_finalized: bool
    created_at: datetime
    updated_at: datetime


class DealerTargetListResponse(BaseModel):
    """Response for listing targets."""
    items: List[DealerTargetResponse]
    total: int


# ==================== DealerScheme Schemas ====================

class DealerSchemeBase(BaseModel):
    """Base schema for DealerScheme."""
    scheme_code: str = Field(..., min_length=3, max_length=30)
    scheme_name: str = Field(..., min_length=3, max_length=200)
    description: Optional[str] = None
    scheme_type: SchemeType
    start_date: date
    end_date: date
    is_active: bool = True
    applicable_dealer_types: Optional[List[str]] = None
    applicable_tiers: Optional[List[str]] = None
    applicable_regions: Optional[List[str]] = None
    applicable_products: Optional[List[UUID]] = None
    applicable_categories: Optional[List[UUID]] = None
    rules: dict  # JSON rules based on scheme_type
    total_budget: Optional[Decimal] = Field(None, ge=0)
    terms_and_conditions: Optional[str] = None
    can_combine: bool = False


class DealerSchemeCreate(DealerSchemeBase):
    """Schema for creating DealerScheme."""
    pass


class DealerSchemeUpdate(BaseModel):
    """Schema for updating DealerScheme."""
    scheme_name: Optional[str] = None
    description: Optional[str] = None
    end_date: Optional[date] = None
    is_active: Optional[bool] = None
    rules: Optional[dict] = None
    total_budget: Optional[Decimal] = None
    terms_and_conditions: Optional[str] = None


class DealerSchemeResponse(BaseResponseSchema):
    """Response schema for DealerScheme."""
    id: UUID
    utilized_budget: Decimal
    budget_remaining: Optional[Decimal] = None
    is_valid: bool
    created_by: Optional[UUID] = None
    approved_by: Optional[UUID] = None
    created_at: datetime
    updated_at: datetime


class DealerSchemeListResponse(BaseModel):
    """Response for listing schemes."""
    items: List[DealerSchemeResponse]
    total: int
    page: int = 1
    size: int = 50
    pages: int = 1


class DealerSchemeApplicationCreate(BaseModel):
    """Schema for applying to a scheme."""
    dealer_id: UUID
    order_id: Optional[UUID] = None
    order_value: Decimal = Field(..., gt=0)
    product_ids: List[UUID] = []


class DealerSchemeApplicationResponse(BaseResponseSchema):
    """Response schema for scheme application."""
    id: UUID
    scheme_id: UUID
    dealer_id: UUID
    order_id: Optional[UUID] = None
    order_value: Decimal
    discount_amount: Decimal
    is_approved: bool
    approved_at: Optional[datetime] = None
    created_at: datetime


class SchemeEligibilityCheck(BaseModel):
    """Check scheme eligibility."""
    dealer_id: UUID
    product_ids: List[UUID]
    order_value: Decimal


class SchemeEligibilityResponse(BaseModel):
    """Scheme eligibility response."""
    dealer_id: UUID
    eligible_schemes: List[dict]  # [{"scheme_id": uuid, "discount": 100}]
    total_discount: Decimal


# ==================== Report Schemas ====================

class DealerPerformanceResponse(BaseModel):
    """Dealer performance report response."""
    dealer_id: UUID
    dealer_code: str
    dealer_name: str
    tier: Optional[str] = None
    total_orders: int = 0
    total_value: Decimal = Decimal("0")
    total_units: int = 0
    target_achievement: Decimal = Decimal("0")
    avg_order_value: Decimal = Decimal("0")


class DealerAgingResponse(BaseModel):
    """Dealer aging report response."""
    dealer_id: UUID
    dealer_code: str
    dealer_name: str
    total_outstanding: Decimal
    current: Decimal = Decimal("0")
    days_1_30: Decimal = Decimal("0")
    days_31_60: Decimal = Decimal("0")
    days_61_90: Decimal = Decimal("0")
    days_90_plus: Decimal = Decimal("0")
