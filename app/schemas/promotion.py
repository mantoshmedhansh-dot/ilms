"""Pydantic schemas for Unified Promotion & Channel Commission module."""
from datetime import datetime, date
from typing import Optional, List
from decimal import Decimal
from uuid import UUID
from pydantic import BaseModel, Field, ConfigDict

from app.schemas.base import BaseResponseSchema

from app.models.promotion import (
    PromotionType, PromotionScope, DiscountApplication, PromotionStatus,
    CommissionBeneficiary
)


# ==================== Promotion Schemas ====================

class PromotionBase(BaseModel):
    """Base schema for Promotion."""
    promo_code: str = Field(..., min_length=3, max_length=30)
    name: str = Field(..., min_length=3, max_length=200)
    description: Optional[str] = None
    short_description: Optional[str] = Field(None, max_length=500)

    # Type & Scope
    promotion_type: PromotionType
    promotion_scope: PromotionScope = PromotionScope.ALL_PRODUCTS
    discount_application: DiscountApplication = DiscountApplication.ON_SELLING_PRICE

    # Validity
    start_date: datetime
    end_date: datetime
    is_recurring: bool = False
    recurring_schedule: Optional[dict] = None

    # Channel applicability
    applicable_channels: Optional[List[str]] = None
    excluded_channels: Optional[List[str]] = None
    is_d2c: bool = True
    is_marketplace: bool = False
    is_dealer: bool = False
    is_retail: bool = False
    is_corporate: bool = False

    # Discount configuration
    discount_percentage: Optional[Decimal] = Field(None, ge=0, le=100)
    max_discount_amount: Optional[Decimal] = Field(None, ge=0)
    discount_amount: Optional[Decimal] = Field(None, ge=0)
    cashback_percentage: Optional[Decimal] = Field(None, ge=0, le=100)
    cashback_amount: Optional[Decimal] = Field(None, ge=0)
    max_cashback: Optional[Decimal] = Field(None, ge=0)

    # BOGO / Bundle
    buy_quantity: Optional[int] = Field(None, ge=1)
    get_quantity: Optional[int] = Field(None, ge=1)
    get_discount_percentage: Optional[Decimal] = Field(None, ge=0, le=100)

    # Eligibility rules
    min_order_value: Optional[Decimal] = Field(None, ge=0)
    min_quantity: Optional[int] = Field(None, ge=1)
    applicable_products: Optional[List[UUID]] = None
    applicable_categories: Optional[List[UUID]] = None
    applicable_brands: Optional[List[UUID]] = None
    excluded_products: Optional[List[UUID]] = None
    excluded_categories: Optional[List[UUID]] = None
    customer_segments: Optional[List[str]] = None
    applicable_regions: Optional[List[str]] = None
    applicable_pincodes: Optional[List[str]] = None

    # Dealer eligibility (B2B)
    applicable_dealer_types: Optional[List[str]] = None
    applicable_dealer_tiers: Optional[List[str]] = None
    applicable_dealers: Optional[List[UUID]] = None

    # Payment restrictions
    applicable_payment_methods: Optional[List[str]] = None
    applicable_banks: Optional[List[str]] = None
    applicable_card_types: Optional[List[str]] = None

    # Usage limits
    total_usage_limit: Optional[int] = Field(None, ge=1)
    per_customer_limit: int = Field(1, ge=1)
    per_order_limit: int = Field(1, ge=1)
    total_budget: Optional[Decimal] = Field(None, ge=0)

    # Display & Marketing
    display_priority: int = Field(0, ge=0)
    is_featured: bool = False
    is_stackable: bool = False
    show_on_product_page: bool = True
    show_on_checkout: bool = True
    requires_coupon_code: bool = False
    coupon_code: Optional[str] = Field(None, max_length=30)
    banner_image_url: Optional[str] = None
    terms_and_conditions: Optional[str] = None


class PromotionCreate(PromotionBase):
    """Schema for creating Promotion."""
    pass


class PromotionUpdate(BaseModel):
    """Schema for updating Promotion."""
    name: Optional[str] = None
    description: Optional[str] = None
    short_description: Optional[str] = None
    status: Optional[PromotionStatus] = None
    end_date: Optional[datetime] = None

    # Discount adjustments
    discount_percentage: Optional[Decimal] = None
    max_discount_amount: Optional[Decimal] = None
    discount_amount: Optional[Decimal] = None

    # Usage adjustments
    total_usage_limit: Optional[int] = None
    per_customer_limit: Optional[int] = None
    total_budget: Optional[Decimal] = None

    # Display
    display_priority: Optional[int] = None
    is_featured: Optional[bool] = None
    banner_image_url: Optional[str] = None
    terms_and_conditions: Optional[str] = None


class PromotionResponse(BaseResponseSchema):
    """Response schema for Promotion."""
    id: UUID
    status: str
    current_usage_count: int
    utilized_budget: Decimal
    is_active: bool
    budget_remaining: Optional[Decimal] = None
    created_by: Optional[UUID] = None
    approved_by: Optional[UUID] = None
    approved_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime


class PromotionListResponse(BaseModel):
    """Response for listing promotions."""
    items: List[PromotionResponse]
    total: int
    page: int = 1
    size: int = 50
    pages: int = 1


class PromotionBrief(BaseModel):
    """Brief promotion for dropdowns."""
    id: UUID
    code: str
    name: str
    promotion_type: PromotionType
    discount_type: DiscountApplication
    discount_value: Decimal
    is_active: bool


class PromotionValidateRequest(BaseModel):
    """Request to validate promotion code."""
    promo_code: str
    channel_code: str
    customer_id: Optional[UUID] = None
    cart_value: Decimal = Field(..., gt=0)


class PromotionApplyRequest(BaseModel):
    """Request to apply promotion to cart/order."""
    promo_code: Optional[str] = None
    promotion_id: Optional[UUID] = None
    channel_code: str
    customer_id: Optional[UUID] = None
    dealer_id: Optional[UUID] = None
    cart_value: Decimal = Field(..., gt=0)
    cart_items: List[dict]  # [{"product_id": uuid, "quantity": 2, "price": 1000}]
    payment_method: Optional[str] = None
    bank_code: Optional[str] = None


class PromotionApplyResponse(BaseModel):
    """Response for promotion application."""
    promotion_id: UUID
    promo_code: str
    promotion_name: str
    is_applicable: bool
    discount_amount: Decimal
    cashback_amount: Decimal
    message: str
    breakdown: Optional[dict] = None  # Detailed discount breakdown


class PromotionValidateResponse(BaseModel):
    """Response for multiple promotion validation."""
    applicable_promotions: List[PromotionApplyResponse]
    best_promotion: Optional[PromotionApplyResponse] = None
    total_savings: Decimal
    stackable_savings: Decimal


# ==================== Promotion Usage Schemas ====================

class PromotionUsageResponse(BaseResponseSchema):
    """Response schema for PromotionUsage."""
    id: UUID
    promotion_id: UUID
    order_id: UUID
    customer_id: Optional[UUID] = None
    dealer_id: Optional[UUID] = None
    channel_code: str
    usage_date: datetime
    order_value: Decimal
    discount_applied: Decimal
    cashback_earned: Decimal
    is_reversed: bool
    reversed_at: Optional[datetime] = None
    reversal_reason: Optional[str] = None
    created_at: datetime


# ==================== Channel Commission Plan Schemas ====================

class ChannelCommissionPlanBase(BaseModel):
    """Base schema for ChannelCommissionPlan."""
    name: str = Field(..., min_length=3, max_length=200)
    description: Optional[str] = None
    channel_code: str = Field(..., max_length=30)
    beneficiary_type: CommissionBeneficiary
    effective_from: date
    effective_to: Optional[date] = None
    is_active: bool = True

    # Commission structure
    commission_type: str = Field("PERCENTAGE", pattern="^(PERCENTAGE|FIXED|SLAB|TIERED)$")
    base_rate: Decimal = Field(Decimal("0"), ge=0, le=100)
    fixed_amount: Optional[Decimal] = Field(None, ge=0)
    rate_slabs: Optional[List[dict]] = None

    # Calculation basis
    calculate_on: str = Field("NET_REVENUE", pattern="^(NET_REVENUE|GROSS_REVENUE|MARGIN|QUANTITY)$")
    exclude_tax: bool = True
    exclude_shipping: bool = True
    exclude_discounts: bool = False

    # Eligibility
    min_order_value: Optional[Decimal] = Field(None, ge=0)
    applicable_categories: Optional[List[UUID]] = None
    applicable_products: Optional[List[UUID]] = None
    excluded_products: Optional[List[UUID]] = None

    # Payout rules
    payout_frequency: str = Field("MONTHLY", pattern="^(WEEKLY|FORTNIGHTLY|MONTHLY)$")
    payout_after_days: int = Field(30, ge=0)
    min_payout_amount: Decimal = Field(Decimal("100"), ge=0)
    clawback_days: int = Field(30, ge=0)

    # TDS
    tds_applicable: bool = True
    tds_rate: Decimal = Field(Decimal("10"), ge=0, le=100)
    tds_section: Optional[str] = None


class ChannelCommissionPlanCreate(ChannelCommissionPlanBase):
    """Schema for creating ChannelCommissionPlan."""
    pass


class ChannelCommissionPlanUpdate(BaseModel):
    """Schema for updating ChannelCommissionPlan."""
    name: Optional[str] = None
    description: Optional[str] = None
    effective_to: Optional[date] = None
    is_active: Optional[bool] = None
    base_rate: Optional[Decimal] = None
    fixed_amount: Optional[Decimal] = None
    rate_slabs: Optional[List[dict]] = None
    min_order_value: Optional[Decimal] = None
    payout_after_days: Optional[int] = None
    clawback_days: Optional[int] = None
    tds_rate: Optional[Decimal] = None


class ChannelCommissionPlanResponse(BaseResponseSchema):
    """Response schema for ChannelCommissionPlan."""
    id: UUID
    created_at: datetime
    updated_at: datetime


class ChannelCommissionPlanListResponse(BaseModel):
    """Response for listing commission plans."""
    items: List[ChannelCommissionPlanResponse]
    total: int
    page: int = 1
    size: int = 50
    pages: int = 1


# ==================== Channel Commission Category Rate Schemas ====================

class ChannelCommissionCategoryRateBase(BaseModel):
    """Base schema for category rate."""
    plan_id: UUID
    category_id: UUID
    commission_rate: Decimal = Field(..., ge=0, le=100)
    fixed_amount: Optional[Decimal] = Field(None, ge=0)
    is_active: bool = True


class ChannelCommissionCategoryRateCreate(ChannelCommissionCategoryRateBase):
    """Schema for creating category rate."""
    pass


class ChannelCommissionCategoryRateResponse(BaseResponseSchema):
    """Response schema for category rate."""
    id: UUID
    created_at: datetime


# ==================== Channel Commission Earning Schemas ====================

class ChannelCommissionEarningBase(BaseModel):
    """Base schema for commission earning."""
    plan_id: UUID
    channel_code: str
    beneficiary_type: CommissionBeneficiary
    beneficiary_id: UUID
    beneficiary_name: str
    order_id: Optional[UUID] = None
    order_number: str
    order_date: date
    earning_date: date
    order_value: Decimal = Field(..., gt=0)
    commission_base: Decimal = Field(..., gt=0)
    commission_rate: Decimal = Field(..., ge=0)
    commission_amount: Decimal = Field(..., ge=0)


class ChannelCommissionEarningCreate(ChannelCommissionEarningBase):
    """Schema for creating commission earning."""
    tds_rate: Decimal = Field(Decimal("0"), ge=0)
    other_deductions: Decimal = Field(Decimal("0"), ge=0)
    parent_earning_id: Optional[UUID] = None
    level: int = Field(1, ge=1)


class ChannelCommissionEarningResponse(BaseResponseSchema):
    """Response schema for commission earning."""
    id: UUID
    tds_rate: Decimal
    tds_amount: Decimal
    other_deductions: Decimal
    net_amount: Decimal
    status: str
    eligible_date: Optional[date] = None
    is_paid: bool
    paid_at: Optional[datetime] = None
    payout_reference: Optional[str] = None
    is_clawed_back: bool
    clawback_date: Optional[date] = None
    clawback_reason: Optional[str] = None
    clawback_amount: Decimal
    parent_earning_id: Optional[UUID] = None
    level: int
    created_at: datetime
    updated_at: datetime


class ChannelCommissionEarningListResponse(BaseModel):
    """Response for listing earnings."""
    items: List[ChannelCommissionEarningResponse]
    total: int
    total_commission: Decimal
    total_tds: Decimal
    total_net: Decimal
    page: int = 1
    size: int = 50
    pages: int = 1


# ==================== Loyalty Program Schemas ====================

class LoyaltyProgramBase(BaseModel):
    """Base schema for LoyaltyProgram."""
    name: str = Field(..., min_length=3, max_length=200)
    description: Optional[str] = None
    applicable_channels: Optional[List[str]] = None

    # Points configuration
    points_per_rupee: Decimal = Field(Decimal("1"), ge=0)
    point_value: Decimal = Field(Decimal("0.25"), ge=0)
    min_points_redeem: int = Field(100, ge=1)
    max_points_per_order: Optional[int] = Field(None, ge=1)
    max_discount_percentage: Optional[Decimal] = Field(None, ge=0, le=100)
    points_expiry_months: int = Field(12, ge=1)

    # Tiers
    tier_config: Optional[List[dict]] = None

    # Status
    is_active: bool = True
    effective_from: date
    effective_to: Optional[date] = None


class LoyaltyProgramCreate(LoyaltyProgramBase):
    """Schema for creating LoyaltyProgram."""
    pass


class LoyaltyProgramResponse(BaseResponseSchema):
    """Response schema for LoyaltyProgram."""
    id: UUID
    created_at: datetime
    updated_at: datetime


class LoyaltyPointsAdjustRequest(BaseModel):
    """Request to adjust loyalty points."""
    customer_id: UUID
    points: int = Field(..., description="Positive to add, negative to deduct")
    reason: str = Field(..., min_length=5, max_length=200)
    reference_type: Optional[str] = None
    reference_id: Optional[UUID] = None


class LoyaltyRedeemRequest(BaseModel):
    """Request to redeem loyalty points."""
    customer_id: UUID
    points_to_redeem: int = Field(..., gt=0)
    order_id: Optional[UUID] = None


# ==================== Referral Program Schemas ====================

class ReferralProgramBase(BaseModel):
    """Base schema for ReferralProgram."""
    name: str = Field(..., min_length=3, max_length=200)
    description: Optional[str] = None
    applicable_channels: Optional[List[str]] = None

    # Referrer reward
    referrer_reward_type: str = Field("CASHBACK", pattern="^(CASHBACK|DISCOUNT|POINTS|FIXED)$")
    referrer_reward_value: Decimal = Field(..., ge=0)
    referrer_max_reward: Optional[Decimal] = Field(None, ge=0)

    # Referee reward
    referee_reward_type: str = Field("DISCOUNT", pattern="^(CASHBACK|DISCOUNT|POINTS|FIXED)$")
    referee_reward_value: Decimal = Field(..., ge=0)
    referee_max_reward: Optional[Decimal] = Field(None, ge=0)

    # Conditions
    min_order_value: Optional[Decimal] = Field(None, ge=0)
    max_referrals_per_user: Optional[int] = Field(None, ge=1)
    reward_after_delivery: bool = True

    # Status
    is_active: bool = True
    effective_from: date
    effective_to: Optional[date] = None


class ReferralProgramCreate(ReferralProgramBase):
    """Schema for creating ReferralProgram."""
    pass


class ReferralProgramResponse(BaseResponseSchema):
    """Response schema for ReferralProgram."""
    id: UUID
    created_at: datetime
    updated_at: datetime


# ==================== Customer Referral Schemas ====================

class CustomerReferralBase(BaseModel):
    """Base schema for CustomerReferral."""
    program_id: UUID
    referrer_id: UUID
    referral_code: str = Field(..., max_length=20)
    referee_email: Optional[str] = None
    referee_phone: Optional[str] = None


class CustomerReferralCreate(CustomerReferralBase):
    """Schema for creating CustomerReferral."""
    pass


class CustomerReferralResponse(BaseResponseSchema):
    """Response schema for CustomerReferral."""
    id: UUID
    referee_id: Optional[UUID] = None
    channel_code: Optional[str] = None
    order_id: Optional[UUID] = None
    order_value: Optional[Decimal] = None
    status: str
    referrer_reward: Decimal
    referrer_rewarded_at: Optional[datetime] = None
    referee_reward: Decimal
    referee_rewarded_at: Optional[datetime] = None
    referred_at: datetime
    registered_at: Optional[datetime] = None
    ordered_at: Optional[datetime] = None
    delivered_at: Optional[datetime] = None


class CustomerReferralListResponse(BaseModel):
    """Response for listing referrals."""
    items: List[CustomerReferralResponse]
    total: int
    page: int = 1
    size: int = 50
    pages: int = 1


# ==================== Report Schemas ====================

class ChannelPromotionSummary(BaseModel):
    """Promotion summary per channel."""
    channel_code: str
    channel_name: str
    total_promotions: int
    active_promotions: int
    total_discount_given: Decimal
    total_cashback_given: Decimal
    total_orders_with_promo: int
    average_discount_per_order: Decimal


class ChannelCommissionSummary(BaseModel):
    """Commission summary per channel."""
    channel_code: str
    channel_name: str
    total_orders: int
    total_order_value: Decimal
    total_commission: Decimal
    total_tds: Decimal
    total_net_payable: Decimal
    pending_payout: Decimal
    paid_amount: Decimal
    by_beneficiary: dict  # {"SALES_EXECUTIVE": 5000, "DEALER": 10000}
