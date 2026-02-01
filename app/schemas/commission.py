"""Pydantic schemas for Commission and Incentive module."""
from datetime import datetime, date
from typing import Optional, List
from decimal import Decimal
from uuid import UUID
from pydantic import BaseModel, Field, ConfigDict, EmailStr

from app.schemas.base import BaseResponseSchema

from app.models.commission import (
    CommissionType, CalculationBasis, CommissionStatus, PayoutStatus
)


# ==================== CommissionPlan Schemas ====================

class CommissionPlanBase(BaseModel):
    """Base schema for CommissionPlan."""
    plan_code: str = Field(..., min_length=3, max_length=30)
    plan_name: str = Field(..., min_length=3, max_length=200)
    description: Optional[str] = None
    commission_type: CommissionType
    calculation_basis: CalculationBasis
    effective_from: date
    effective_to: Optional[date] = None
    is_active: bool = True

    # Default Rates
    default_rate: Decimal = Field(Decimal("0"), ge=0)
    min_rate: Optional[Decimal] = Field(None, ge=0)
    max_rate: Optional[Decimal] = Field(None, ge=0)
    rate_slabs: Optional[List[dict]] = None

    # Eligibility Rules
    min_order_value: Optional[Decimal] = Field(None, ge=0)
    applicable_products: Optional[List[UUID]] = None
    applicable_categories: Optional[List[UUID]] = None
    excluded_products: Optional[List[UUID]] = None

    # Payout Rules
    payout_after_days: int = Field(30, ge=0)
    requires_full_payment: bool = True
    clawback_period_days: int = Field(30, ge=0)

    # TDS
    tds_applicable: bool = True
    tds_rate: Decimal = Field(Decimal("10"), ge=0, le=100)
    tds_section: Optional[str] = None

    terms_and_conditions: Optional[str] = None


class CommissionPlanCreate(CommissionPlanBase):
    """Schema for creating CommissionPlan."""
    pass


class CommissionPlanUpdate(BaseModel):
    """Schema for updating CommissionPlan."""
    plan_name: Optional[str] = None
    description: Optional[str] = None
    effective_to: Optional[date] = None
    is_active: Optional[bool] = None
    default_rate: Optional[Decimal] = None
    rate_slabs: Optional[List[dict]] = None
    min_order_value: Optional[Decimal] = None
    payout_after_days: Optional[int] = None
    clawback_period_days: Optional[int] = None
    tds_rate: Optional[Decimal] = None
    terms_and_conditions: Optional[str] = None


class CommissionPlanResponse(BaseResponseSchema):
    """Response schema for CommissionPlan."""
    id: UUID
    is_valid: bool
    created_at: datetime
    updated_at: datetime


class CommissionPlanListResponse(BaseModel):
    """Response for listing plans."""
    items: List[CommissionPlanResponse]
    total: int
    page: int = 1
    size: int = 50
    pages: int = 1


# ==================== CommissionCategoryRate Schemas ====================

class CommissionCategoryRateBase(BaseModel):
    """Base schema for CommissionCategoryRate."""
    category_id: UUID
    commission_rate: Decimal = Field(..., ge=0, le=100)
    rate_slabs: Optional[List[dict]] = None
    is_active: bool = True


class CommissionCategoryRateCreate(CommissionCategoryRateBase):
    """Schema for creating category rate."""
    # Note: plan_id comes from URL path, not request body
    pass


class CommissionCategoryRateResponse(BaseResponseSchema):
    """Response schema for category rate."""
    id: UUID
    plan_id: UUID  # Included in response from database
    created_at: datetime


# ==================== CommissionProductRate Schemas ====================

class CommissionProductRateBase(BaseModel):
    """Base schema for CommissionProductRate."""
    product_id: UUID
    commission_rate: Decimal = Field(..., ge=0, le=100)
    fixed_amount: Optional[Decimal] = Field(None, ge=0)
    is_active: bool = True


class CommissionProductRateCreate(CommissionProductRateBase):
    """Schema for creating product rate."""
    # Note: plan_id comes from URL path, not request body
    pass


class CommissionProductRateResponse(BaseResponseSchema):
    """Response schema for product rate."""
    id: UUID
    plan_id: UUID  # Included in response from database
    created_at: datetime


# ==================== CommissionEarner Schemas ====================

class CommissionEarnerBase(BaseModel):
    """Base schema for CommissionEarner."""
    earner_type: CommissionType
    earner_name: str = Field(..., min_length=2, max_length=200)
    earner_email: Optional[EmailStr] = None
    earner_phone: Optional[str] = None
    plan_id: UUID
    custom_rate: Optional[Decimal] = Field(None, ge=0, le=100)

    # Bank Details
    bank_name: Optional[str] = None
    bank_account_number: Optional[str] = None
    bank_ifsc: Optional[str] = None
    bank_account_name: Optional[str] = None
    upi_id: Optional[str] = None

    # PAN for TDS
    pan_number: Optional[str] = Field(None, min_length=10, max_length=10)
    tds_rate_override: Optional[Decimal] = Field(None, ge=0, le=100)

    is_active: bool = True


class CommissionEarnerCreate(CommissionEarnerBase):
    """Schema for creating CommissionEarner."""
    user_id: Optional[UUID] = None
    dealer_id: Optional[UUID] = None
    referral_code: Optional[str] = None


class CommissionEarnerUpdate(BaseModel):
    """Schema for updating CommissionEarner."""
    earner_name: Optional[str] = None
    earner_email: Optional[EmailStr] = None
    earner_phone: Optional[str] = None
    plan_id: Optional[UUID] = None
    custom_rate: Optional[Decimal] = None
    bank_name: Optional[str] = None
    bank_account_number: Optional[str] = None
    bank_ifsc: Optional[str] = None
    bank_account_name: Optional[str] = None
    upi_id: Optional[str] = None
    pan_number: Optional[str] = None
    tds_rate_override: Optional[Decimal] = None
    is_active: Optional[bool] = None


class CommissionEarnerResponse(BaseResponseSchema):
    """Response schema for CommissionEarner."""
    id: UUID
    earner_type: Optional[str] = None
    earner_name: Optional[str] = None
    earner_email: Optional[str] = None
    earner_phone: Optional[str] = None
    user_id: Optional[UUID] = None
    dealer_id: Optional[UUID] = None
    referral_code: Optional[str] = None
    plan_id: Optional[UUID] = None
    custom_rate: Optional[Decimal] = None

    # Bank Details
    bank_name: Optional[str] = None
    bank_account_number: Optional[str] = None
    bank_ifsc: Optional[str] = None
    bank_account_name: Optional[str] = None
    upi_id: Optional[str] = None

    # TDS
    pan_number: Optional[str] = None
    tds_rate_override: Optional[Decimal] = None

    # Status
    is_active: bool = True
    is_verified: bool = False
    verified_at: Optional[datetime] = None

    # Performance
    total_earnings: Decimal = Decimal("0")
    total_paid: Decimal = Decimal("0")
    pending_payout: Decimal = Decimal("0")
    total_orders: int = 0

    created_at: datetime
    updated_at: datetime


class CommissionEarnerListResponse(BaseModel):
    """Response for listing earners."""
    items: List[CommissionEarnerResponse]
    total: int
    page: int = 1
    size: int = 50
    pages: int = 1


class GenerateReferralCodeRequest(BaseModel):
    """Request to generate referral code."""
    earner_id: UUID
    custom_code: Optional[str] = Field(None, min_length=5, max_length=20)


# ==================== CommissionTransaction Schemas ====================

class CommissionTransactionBase(BaseModel):
    """Base schema for CommissionTransaction."""
    earner_id: UUID
    order_id: Optional[UUID] = None
    service_request_id: Optional[UUID] = None
    transaction_date: date
    transaction_reference: str = Field(..., max_length=50)
    order_value: Decimal = Field(..., gt=0)
    commission_base: Decimal = Field(..., gt=0)
    commission_rate: Decimal = Field(..., ge=0)
    commission_amount: Decimal = Field(..., ge=0)
    tds_rate: Decimal = Field(Decimal("0"), ge=0)
    other_deductions: Decimal = Field(Decimal("0"), ge=0)
    deduction_remarks: Optional[str] = None
    remarks: Optional[str] = None


class CommissionTransactionCreate(CommissionTransactionBase):
    """Schema for creating CommissionTransaction."""
    parent_transaction_id: Optional[UUID] = None
    level: int = Field(1, ge=1)


class CommissionTransactionResponse(BaseResponseSchema):
    """Response schema for CommissionTransaction."""
    id: UUID
    tds_amount: Decimal
    net_amount: Decimal
    status: str
    status_reason: Optional[str] = None
    eligible_date: Optional[date] = None
    is_eligible: bool
    payout_id: Optional[UUID] = None
    paid_at: Optional[datetime] = None
    is_clawed_back: bool
    clawback_date: Optional[date] = None
    clawback_reason: Optional[str] = None
    parent_transaction_id: Optional[UUID] = None
    level: int
    created_at: datetime
    updated_at: datetime


class CommissionTransactionListResponse(BaseModel):
    """Response for listing transactions."""
    items: List[CommissionTransactionResponse]
    total: int
    total_commission: Decimal
    total_tds: Decimal
    total_net: Decimal
    page: int = 1
    size: int = 50
    pages: int = 1


class CommissionApproveRequest(BaseModel):
    """Request to approve commissions."""
    transaction_ids: List[UUID]


class CommissionClawbackRequest(BaseModel):
    """Request to clawback commission."""
    transaction_id: UUID
    reason: str = Field(..., min_length=10, max_length=500)


# ==================== CommissionPayout Schemas ====================

class CommissionPayoutBase(BaseModel):
    """Base schema for CommissionPayout."""
    period_start: date
    period_end: date
    payout_date: date
    payment_mode: Optional[str] = None
    remarks: Optional[str] = None


class CommissionPayoutCreate(CommissionPayoutBase):
    """Schema for creating CommissionPayout."""
    earner_ids: Optional[List[UUID]] = None  # If None, include all eligible


class CommissionPayoutLineResponse(BaseResponseSchema):
    """Response schema for payout line."""
    id: UUID
    earner_id: UUID
    earner_name: Optional[str] = None
    gross_amount: Decimal
    tds_amount: Decimal
    other_deductions: Decimal
    net_amount: Decimal
    transaction_count: int
    payment_mode: str
    bank_name: Optional[str] = None
    account_number: Optional[str] = None
    upi_id: Optional[str] = None
    payment_status: str
    payment_reference: Optional[str] = None
    payment_date: Optional[datetime] = None
    failure_reason: Optional[str] = None
    created_at: datetime


class CommissionPayoutResponse(BaseResponseSchema):
    """Response schema for CommissionPayout."""
    id: UUID
    payout_number: str
    status: str
    total_gross: Decimal
    total_tds: Decimal
    total_deductions: Decimal
    total_net: Decimal
    transaction_count: int
    earner_count: int
    payment_reference: Optional[str] = None
    payment_date: Optional[date] = None
    line_items: List[CommissionPayoutLineResponse] = []
    created_by: Optional[UUID] = None
    approved_by: Optional[UUID] = None
    approved_at: Optional[datetime] = None
    processed_by: Optional[UUID] = None
    processed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime


class CommissionPayoutListResponse(BaseModel):
    """Response for listing payouts."""
    items: List[CommissionPayoutResponse]
    total: int
    page: int = 1
    size: int = 50
    pages: int = 1


class PayoutApproveRequest(BaseModel):
    """Request to approve payout."""
    payout_id: UUID


class PayoutProcessRequest(BaseModel):
    """Request to process payout."""
    payout_id: UUID
    payment_reference: str
    payment_date: date


class PayoutLineUpdateRequest(BaseModel):
    """Request to update individual payout line."""
    payout_line_id: UUID
    payment_status: str = Field(..., pattern="^(PENDING|SUCCESS|FAILED)$")
    payment_reference: Optional[str] = None
    failure_reason: Optional[str] = None


# ==================== AffiliateReferral Schemas ====================

class AffiliateReferralBase(BaseModel):
    """Base schema for AffiliateReferral."""
    earner_id: UUID
    referral_code: str = Field(..., max_length=30)
    customer_email: Optional[EmailStr] = None
    customer_phone: Optional[str] = None
    source_url: Optional[str] = None
    landing_page: Optional[str] = None
    utm_source: Optional[str] = None
    utm_medium: Optional[str] = None
    utm_campaign: Optional[str] = None


class AffiliateReferralCreate(AffiliateReferralBase):
    """Schema for creating AffiliateReferral (click tracking)."""
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    device_type: Optional[str] = None


class AffiliateReferralResponse(BaseResponseSchema):
    """Response schema for AffiliateReferral."""
    id: UUID
    customer_id: Optional[UUID] = None
    order_id: Optional[UUID] = None
    click_timestamp: datetime
    is_converted: bool
    converted_at: Optional[datetime] = None
    conversion_value: Optional[Decimal] = None
    attribution_window_days: int
    is_first_order: bool
    created_at: datetime


class AffiliateReferralListResponse(BaseModel):
    """Response for listing referrals."""
    items: List[AffiliateReferralResponse]
    total: int
    total_clicks: int
    total_conversions: int
    conversion_rate: Decimal
    total_value: Decimal
    page: int = 1
    size: int = 50
    pages: int = 1


class ReferralConversionRequest(BaseModel):
    """Request to record referral conversion."""
    referral_id: UUID
    customer_id: UUID
    order_id: UUID
    conversion_value: Decimal = Field(..., gt=0)


# ==================== Report Schemas ====================

class CommissionSummaryRequest(BaseModel):
    """Request for commission summary report."""
    earner_id: Optional[UUID] = None
    start_date: date
    end_date: date
    commission_type: Optional[CommissionType] = None


class CommissionSummaryResponse(BaseModel):
    """Commission summary response."""
    period_start: date
    period_end: date
    total_orders: int
    total_order_value: Decimal
    total_commission_base: Decimal
    total_commission: Decimal
    total_tds: Decimal
    total_deductions: Decimal
    total_net: Decimal
    pending_amount: Decimal
    paid_amount: Decimal
    clawback_amount: Decimal
    by_status: dict  # {"PENDING": 1000, "PAID": 5000, ...}


class EarnerPerformanceRequest(BaseModel):
    """Request for earner performance report."""
    earner_id: UUID
    start_date: date
    end_date: date


class EarnerPerformanceResponse(BaseModel):
    """Earner performance response."""
    earner_id: UUID
    earner_name: str
    period_start: date
    period_end: date
    total_orders: int
    total_revenue_generated: Decimal
    total_commission_earned: Decimal
    average_order_value: Decimal
    commission_rate_effective: Decimal
    monthly_trend: List[dict]  # [{"month": "2024-01", "orders": 10, "commission": 5000}]
