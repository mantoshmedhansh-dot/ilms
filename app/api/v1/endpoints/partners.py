"""
Community Partner API Endpoints

Endpoints for the Meesho-style Community Sales Channel:
- Partner registration (public)
- OTP-based authentication
- KYC submission
- Profile management
- Commission tracking
- Payout requests
- Admin management
"""

import uuid
from typing import Optional
from uuid import UUID
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field

from app.api.deps import get_db, get_current_user
from app.models.user import User
from app.models.community_partner import CommunityPartner, PartnerTier, PartnerCommission, PartnerPayout, PartnerOrder
from app.models.order import Order
from app.services.partner_service import PartnerService
from app.services.partner_auth_service import PartnerAuthService
from app.schemas.community_partner import (

    CommunityPartnerCreate,
    CommunityPartnerUpdate,
    CommunityPartnerResponse,
    CommunityPartnerList,
    KYCSubmission,
    KYCVerification,
    PartnerTierResponse,
    PartnerCommissionResponse,
    CommissionSummary,
    PayoutRequest,
    PartnerPayoutResponse,
    PayoutList,
    ReferralSummary,
    PartnerOrderResponse,
    PartnerOrderList,
    PartnerDashboard,
    PartnerAnalytics,
)
from app.core.module_decorators import require_module


router = APIRouter(prefix="/partners", tags=["Community Partners"])
security = HTTPBearer(auto_error=False)


# ============================================================================
# Pydantic Schemas for Auth
# ============================================================================

class SendOTPRequest(BaseModel):
    """Request to send OTP"""
    phone: str = Field(..., pattern=r"^\+?[1-9]\d{9,14}$", description="Phone number")


class VerifyOTPRequest(BaseModel):
    """Request to verify OTP"""
    phone: str = Field(..., pattern=r"^\+?[1-9]\d{9,14}$")
    otp: str = Field(..., min_length=4, max_length=6)


class PartnerAuthResponse(BaseModel):
    """Authentication response"""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    partner: dict


class RefreshTokenRequest(BaseModel):
    """Refresh token request"""
    refresh_token: str


# ============================================================================
# Authentication Dependency
# ============================================================================

async def get_current_partner(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> Optional[CommunityPartner]:
    """Get current authenticated partner from JWT token."""
    if not credentials:
        return None

    auth_service = PartnerAuthService(db)
    partner = await auth_service.get_current_partner_from_token(credentials.credentials)
    return partner


async def require_partner(
    partner: Optional[CommunityPartner] = Depends(get_current_partner),
) -> CommunityPartner:
    """Require authenticated partner."""
    if not partner:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return partner


async def require_active_partner(
    partner: CommunityPartner = Depends(require_partner),
) -> CommunityPartner:
    """Require authenticated and active partner."""
    if partner.status in ["BLOCKED", "SUSPENDED"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Partner account is {partner.status.lower()}",
        )
    return partner


# ============================================================================
# Public Endpoints - Registration & Authentication
# ============================================================================

@router.post("/register", response_model=CommunityPartnerResponse, status_code=status.HTTP_201_CREATED)
@require_module("sales_distribution")
async def register_partner(
    data: CommunityPartnerCreate,
    db: AsyncSession = Depends(get_db)
):
    """
    Register a new community partner.

    Public endpoint - no authentication required.

    Steps:
    1. Submit basic details (name, mobile, email, address)
    2. Optionally provide referral code
    3. System generates partner code and referral code
    4. Partner starts in PENDING_KYC status
    """
    service = PartnerService(db)
    try:
        partner = await service.register_partner(data)
        return partner
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/auth/send-otp")
@require_module("sales_distribution")
async def send_login_otp(
    request: SendOTPRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Send OTP for partner login.

    Phone number must be registered first via /partners/register.
    """
    auth_service = PartnerAuthService(db)
    success, message, cooldown = await auth_service.send_otp(request.phone)

    if not success:
        raise HTTPException(
            status_code=400 if cooldown else 404,
            detail=message
        )

    return {
        "success": True,
        "message": message,
        "expires_in_seconds": 600,  # 10 minutes
        "resend_in_seconds": cooldown,
    }


@router.post("/auth/verify-otp", response_model=PartnerAuthResponse)
@require_module("sales_distribution")
async def verify_login_otp(
    request: VerifyOTPRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Verify OTP and return JWT tokens.

    Returns access_token and refresh_token for authenticated API calls.
    """
    auth_service = PartnerAuthService(db)
    success, message, auth_data = await auth_service.verify_otp(request.phone, request.otp)

    if not success:
        raise HTTPException(status_code=400, detail=message)

    return auth_data


@router.post("/auth/refresh")
@require_module("sales_distribution")
async def refresh_access_token(
    request: RefreshTokenRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Refresh access token using refresh token.
    """
    auth_service = PartnerAuthService(db)
    success, message, tokens = await auth_service.refresh_token(request.refresh_token)

    if not success:
        raise HTTPException(status_code=401, detail=message)

    return tokens


@router.post("/auth/login-direct", response_model=PartnerAuthResponse)
@require_module("sales_distribution")
async def login_direct(
    request: SendOTPRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Direct login without OTP (temporary - for demo/testing).

    Partner must be registered first. This bypasses OTP verification.
    """
    auth_service = PartnerAuthService(db)
    partner = await auth_service.get_partner_by_phone(request.phone)

    if not partner:
        raise HTTPException(
            status_code=404,
            detail="Phone number not registered. Please register first."
        )

    if partner.status in ["BLOCKED", "SUSPENDED"]:
        raise HTTPException(
            status_code=403,
            detail=f"Partner account is {partner.status.lower()}"
        )

    # Update last login
    partner.last_login_at = datetime.now(timezone.utc)
    await db.commit()

    # Generate tokens
    access_token = auth_service.create_partner_token(str(partner.id), partner.partner_code)
    refresh_token = auth_service.create_partner_refresh_token(str(partner.id))

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "expires_in": 24 * 7 * 3600,  # 7 days
        "partner": {
            "id": str(partner.id),
            "partner_code": partner.partner_code,
            "full_name": partner.full_name,
            "phone": partner.phone,
            "email": partner.email,
            "status": partner.status,
            "kyc_status": partner.kyc_status,
            "referral_code": partner.referral_code,
            "tier_code": partner.tier.code if partner.tier else "BRONZE",
        }
    }


@router.post("/auth/logout")
@require_module("sales_distribution")
async def logout_partner(
    partner: CommunityPartner = Depends(require_partner),
):
    """
    Logout partner.

    Note: JWT tokens are stateless, so this is mainly for client-side cleanup.
    """
    return {"message": "Logged out successfully"}


# ============================================================================
# Partner Profile Endpoints (Authenticated)
# ============================================================================

@router.get("/me", response_model=CommunityPartnerResponse)
@require_module("sales_distribution")
async def get_my_profile(
    partner: CommunityPartner = Depends(require_partner),
    db: AsyncSession = Depends(get_db)
):
    """
    Get current partner's profile.
    """
    return partner


@router.put("/me", response_model=CommunityPartnerResponse)
@require_module("sales_distribution")
async def update_my_profile(
    data: CommunityPartnerUpdate,
    partner: CommunityPartner = Depends(require_partner),
    db: AsyncSession = Depends(get_db)
):
    """
    Update current partner's profile.
    """
    service = PartnerService(db)
    try:
        updated = await service.update_partner(partner.id, data)
        return updated
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/me/kyc", response_model=CommunityPartnerResponse)
@require_module("sales_distribution")
async def submit_kyc(
    data: KYCSubmission,
    partner: CommunityPartner = Depends(require_partner),
    db: AsyncSession = Depends(get_db)
):
    """
    Submit KYC documents for verification.

    Required documents:
    - Aadhaar (front and back images)
    - Bank account details
    - PAN card (optional but recommended)
    - Selfie (optional)
    """
    service = PartnerService(db)
    try:
        updated = await service.submit_kyc(partner.id, data)
        return updated
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ============================================================================
# Commission & Earnings Endpoints
# ============================================================================

@router.get("/me/commissions", response_model=CommissionSummary)
@require_module("sales_distribution")
async def get_my_commission_summary(
    partner: CommunityPartner = Depends(require_partner),
    db: AsyncSession = Depends(get_db)
):
    """
    Get commission summary for current partner.
    """
    service = PartnerService(db)
    summary = await service.get_commission_summary(partner.id)
    return summary


@router.get("/me/commission-history")
@require_module("sales_distribution")
async def get_commission_history(
    partner: CommunityPartner = Depends(require_partner),
    status: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db)
):
    """
    Get commission transaction history.
    """
    query = select(PartnerCommission).where(PartnerCommission.partner_id == partner.id)

    if status:
        query = query.where(PartnerCommission.status == status)

    query = query.order_by(PartnerCommission.created_at.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)

    result = await db.execute(query)
    commissions = result.scalars().all()

    return {
        "items": [PartnerCommissionResponse.model_validate(c) for c in commissions],
        "page": page,
        "page_size": page_size,
    }


# ============================================================================
# Payout Endpoints
# ============================================================================

@router.post("/me/payouts", response_model=PartnerPayoutResponse)
@require_module("sales_distribution")
async def request_payout(
    request: PayoutRequest,
    partner: CommunityPartner = Depends(require_active_partner),
    db: AsyncSession = Depends(get_db)
):
    """
    Request payout for approved commissions.
    """
    service = PartnerService(db)
    try:
        payout = await service.create_payout(partner.id, request)
        return payout
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/me/payouts")
@require_module("sales_distribution")
async def get_my_payouts(
    partner: CommunityPartner = Depends(require_partner),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db)
):
    """
    Get payout history.
    """
    query = select(PartnerPayout).where(PartnerPayout.partner_id == partner.id)
    query = query.order_by(PartnerPayout.created_at.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)

    result = await db.execute(query)
    payouts = result.scalars().all()

    return {
        "items": [PartnerPayoutResponse.model_validate(p) for p in payouts],
        "page": page,
        "page_size": page_size,
    }


# ============================================================================
# Tier & Progress Endpoints
# ============================================================================

@router.get("/me/tier-progress")
@require_module("sales_distribution")
async def get_tier_progress(
    partner: CommunityPartner = Depends(require_partner),
    db: AsyncSession = Depends(get_db)
):
    """
    Get progress towards next tier.
    """
    service = PartnerService(db)
    progress = await service.get_tier_progress(partner.id)
    return progress


@router.get("/tiers", response_model=list[PartnerTierResponse])
@require_module("sales_distribution")
async def get_all_tiers(
    db: AsyncSession = Depends(get_db)
):
    """
    Get all partner tiers with benefits.
    """
    result = await db.execute(
        select(PartnerTier)
        .where(PartnerTier.is_active == True)
        .order_by(PartnerTier.level.asc())
    )
    tiers = result.scalars().all()
    return tiers


class PartnerTierCreate(BaseModel):
    """Schema for creating a partner tier."""
    code: str = Field(..., min_length=2, max_length=20)
    name: str = Field(..., min_length=2, max_length=100)
    min_monthly_sales: int = Field(0, ge=0)
    min_monthly_value: float = Field(0.0, ge=0)
    commission_percentage: float = Field(..., ge=0, le=100)
    bonus_percentage: float = Field(0.0, ge=0, le=100)
    is_active: bool = True


class PartnerTierUpdate(BaseModel):
    """Schema for updating a partner tier."""
    name: Optional[str] = None
    min_monthly_sales: Optional[int] = None
    min_monthly_value: Optional[float] = None
    commission_percentage: Optional[float] = None
    bonus_percentage: Optional[float] = None
    is_active: Optional[bool] = None


@router.post("/tiers", response_model=PartnerTierResponse, status_code=status.HTTP_201_CREATED)
@require_module("sales_distribution")
async def create_tier(
    data: PartnerTierCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Create a new partner tier (Admin only).
    """
    # Check if code already exists
    existing = await db.execute(
        select(PartnerTier).where(PartnerTier.code == data.code.upper())
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail=f"Tier with code '{data.code}' already exists")

    # Get the next level
    max_level_result = await db.execute(
        select(PartnerTier.level).order_by(PartnerTier.level.desc()).limit(1)
    )
    max_level = max_level_result.scalar_one_or_none() or 0

    tier = PartnerTier(
        id=uuid.uuid4(),
        code=data.code.upper(),
        name=data.name,
        level=max_level + 1,
        min_monthly_sales=data.min_monthly_sales,
        min_monthly_value=data.min_monthly_value,
        commission_percentage=data.commission_percentage,
        bonus_percentage=data.bonus_percentage,
        is_active=data.is_active,
    )

    db.add(tier)
    await db.commit()
    await db.refresh(tier)

    return tier


@router.put("/tiers/{tier_id}", response_model=PartnerTierResponse)
@require_module("sales_distribution")
async def update_tier(
    tier_id: UUID,
    data: PartnerTierUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Update a partner tier (Admin only).
    """
    result = await db.execute(select(PartnerTier).where(PartnerTier.id == tier_id))
    tier = result.scalar_one_or_none()

    if not tier:
        raise HTTPException(status_code=404, detail="Tier not found")

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(tier, field, value)

    await db.commit()
    await db.refresh(tier)

    return tier


@router.delete("/tiers/{tier_id}", status_code=status.HTTP_204_NO_CONTENT)
@require_module("sales_distribution")
async def delete_tier(
    tier_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Delete a partner tier (Admin only).

    Note: Tiers with assigned partners cannot be deleted.
    """
    result = await db.execute(select(PartnerTier).where(PartnerTier.id == tier_id))
    tier = result.scalar_one_or_none()

    if not tier:
        raise HTTPException(status_code=404, detail="Tier not found")

    # Check if any partners are assigned to this tier
    partners_count_result = await db.execute(
        select(CommunityPartner).where(CommunityPartner.tier_id == tier_id).limit(1)
    )
    if partners_count_result.scalar_one_or_none():
        raise HTTPException(
            status_code=400,
            detail="Cannot delete tier with assigned partners. Reassign partners first."
        )

    await db.delete(tier)
    await db.commit()


# ============================================================================
# Referral Endpoints
# ============================================================================

@router.get("/me/referrals")
@require_module("sales_distribution")
async def get_my_referrals(
    partner: CommunityPartner = Depends(require_partner),
    db: AsyncSession = Depends(get_db)
):
    """
    Get referral summary and list of referred partners.
    """
    from app.models.community_partner import PartnerReferral

    # Get referrals
    referrals_result = await db.execute(
        select(PartnerReferral, CommunityPartner)
        .join(CommunityPartner, CommunityPartner.id == PartnerReferral.referred_id)
        .where(PartnerReferral.referrer_id == partner.id)
        .order_by(PartnerReferral.created_at.desc())
    )
    referrals = referrals_result.fetchall()

    # Count qualified
    qualified_count = sum(1 for r in referrals if r[0].referred_qualified)

    # Total bonus earned
    total_bonus = sum(r[0].bonus_amount for r in referrals)

    return {
        "referral_code": partner.referral_code,
        "total_referrals": len(referrals),
        "qualified_referrals": qualified_count,
        "pending_referrals": len(referrals) - qualified_count,
        "total_bonus_earned": float(total_bonus),
        "referrals": [
            {
                "name": r[1].full_name,
                "registered_at": r[0].created_at,
                "is_qualified": r[0].referred_qualified,
                "qualified_at": r[0].qualification_date,
                "bonus": float(r[0].bonus_amount),
            }
            for r in referrals
        ]
    }


@router.get("/me/referral-link/{product_slug}")
@require_module("sales_distribution")
async def get_referral_link(
    product_slug: str,
    partner: CommunityPartner = Depends(require_partner),
):
    """
    Generate referral link for a product.
    """
    base_url = "https://www.ilms.ai"
    referral_link = f"{base_url}/products/{product_slug}?ref={partner.referral_code}"

    return {
        "referral_link": referral_link,
        "referral_code": partner.referral_code,
        "product_slug": product_slug,
    }


# ============================================================================
# Orders Endpoints
# ============================================================================

@router.get("/me/orders")
@require_module("sales_distribution")
async def get_my_orders(
    partner: CommunityPartner = Depends(require_partner),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db)
):
    """
    Get orders attributed to this partner.
    """
    query = (
        select(PartnerOrder, Order)
        .join(Order, Order.id == PartnerOrder.order_id)
        .where(PartnerOrder.partner_id == partner.id)
        .order_by(PartnerOrder.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )

    result = await db.execute(query)
    orders = result.fetchall()

    return {
        "items": [
            {
                "id": str(po.id),
                "order_id": str(po.order_id),
                "order_number": o.order_number,
                "order_amount": float(o.grand_total),
                "customer_name": o.customer_name,
                "order_status": o.status,
                "created_at": po.created_at,
            }
            for po, o in orders
        ],
        "page": page,
        "page_size": page_size,
    }


# ============================================================================
# Products for Sharing
# ============================================================================

@router.get("/me/products")
@require_module("sales_distribution")
async def get_products_for_sharing(
    partner: CommunityPartner = Depends(require_partner),
    category_id: Optional[UUID] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db)
):
    """
    Get active products for partner to share.
    """
    from app.models.product import Product

    query = select(Product).where(Product.is_active == True)

    if category_id:
        query = query.where(Product.category_id == category_id)

    query = query.order_by(Product.name.asc())
    query = query.offset((page - 1) * page_size).limit(page_size)

    result = await db.execute(query)
    products = result.scalars().all()

    base_url = "https://www.ilms.ai"

    return {
        "items": [
            {
                "id": str(p.id),
                "name": p.name,
                "slug": p.slug,
                "mrp": float(p.mrp) if p.mrp else 0,
                "selling_price": float(p.selling_price) if p.selling_price else 0,
                "image_url": p.thumbnail_url,
                "referral_link": f"{base_url}/products/{p.slug}?ref={partner.referral_code}",
            }
            for p in products
        ],
        "page": page,
        "page_size": page_size,
    }


# ============================================================================
# Dashboard Endpoint
# ============================================================================

@router.get("/me/dashboard")
@require_module("sales_distribution")
async def get_partner_dashboard(
    partner: CommunityPartner = Depends(require_partner),
    db: AsyncSession = Depends(get_db)
):
    """
    Get complete dashboard data for partner mobile app.
    """
    service = PartnerService(db)

    commission_summary = await service.get_commission_summary(partner.id)
    tier_progress = await service.get_tier_progress(partner.id)

    # Recent orders (last 5)
    orders_result = await db.execute(
        select(PartnerOrder, Order)
        .join(Order, Order.id == PartnerOrder.order_id)
        .where(PartnerOrder.partner_id == partner.id)
        .order_by(PartnerOrder.created_at.desc())
        .limit(5)
    )
    recent_orders = [
        {
            "order_id": str(po.order_id),
            "order_number": o.order_number,
            "amount": float(o.grand_total),
            "status": o.status,
            "date": po.created_at.isoformat(),
        }
        for po, o in orders_result.fetchall()
    ]

    return {
        "partner": CommunityPartnerResponse.model_validate(partner),
        "commission_summary": commission_summary,
        "tier_progress": tier_progress,
        "recent_orders": recent_orders,
        "referral_code": partner.referral_code,
        "wallet_balance": float(partner.wallet_balance),
    }


# ============================================================================
# Admin Endpoints (ERP Users)
# ============================================================================

@router.get("", response_model=CommunityPartnerList)
@require_module("sales_distribution")
async def list_partners(
    status: Optional[str] = Query(None, description="Filter by status"),
    kyc_status: Optional[str] = Query(None, description="Filter by KYC status"),
    state: Optional[str] = Query(None, description="Filter by state"),
    search: Optional[str] = Query(None, description="Search by name, phone, code, email"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    List all partners with filters (Admin only).
    """
    service = PartnerService(db)
    partners, total = await service.list_partners(
        status=status,
        kyc_status=kyc_status,
        state=state,
        search=search,
        page=page,
        page_size=page_size
    )

    total_pages = (total + page_size - 1) // page_size

    return CommunityPartnerList(
        items=[CommunityPartnerResponse.model_validate(p) for p in partners],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages
    )


@router.get("/{partner_id}", response_model=CommunityPartnerResponse)
@require_module("sales_distribution")
async def get_partner(
    partner_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get partner details by ID (Admin only).
    """
    service = PartnerService(db)
    partner = await service.get_partner_by_id(partner_id)

    if not partner:
        raise HTTPException(status_code=404, detail="Partner not found")

    return partner


@router.put("/{partner_id}", response_model=CommunityPartnerResponse)
@require_module("sales_distribution")
async def update_partner_admin(
    partner_id: UUID,
    data: CommunityPartnerUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Update partner details (Admin only).
    """
    service = PartnerService(db)
    try:
        partner = await service.update_partner(partner_id, data)
        if not partner:
            raise HTTPException(status_code=404, detail="Partner not found")
        return partner
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{partner_id}", status_code=status.HTTP_204_NO_CONTENT)
@require_module("sales_distribution")
async def delete_partner(
    partner_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Delete a partner (Super Admin only).

    Note: This permanently deletes the partner and all associated data.

    STRUCTURAL ANALYSIS (2026-01-25):
    - All FK constraints in production are NO ACTION (not CASCADE)
    - Must explicitly delete in correct order respecting FK chains:
      1. partner_orders (has FK to partner_commissions via commission_id)
      2. partner_commissions (has FK to partner_payouts via payout_id)
      3. partner_payouts
      4. partner_referrals
      5. partner_training
      6. Clear self-referential FKs (referred_by AND referred_by_id columns)
      7. Finally delete the partner
    """
    from app.models.community_partner import (
        PartnerCommission, PartnerPayout, PartnerReferral, PartnerOrder, PartnerTraining
    )
    from sqlalchemy import delete, update, text

    # Get partner
    result = await db.execute(
        select(CommunityPartner).where(CommunityPartner.id == partner_id)
    )
    partner = result.scalar_one_or_none()

    if not partner:
        raise HTTPException(status_code=404, detail="Partner not found")

    try:
        # ============================================================
        # STEP 1: Clear FK references in partner_orders before deleting commissions
        # partner_orders.commission_id -> partner_commissions.id (NO ACTION)
        # ============================================================
        await db.execute(
            text("UPDATE partner_orders SET commission_id = NULL WHERE partner_id = :pid"),
            {"pid": str(partner_id)}
        )

        # ============================================================
        # STEP 2: Delete partner_orders (must be before partner_commissions)
        # ============================================================
        await db.execute(
            delete(PartnerOrder).where(PartnerOrder.partner_id == partner_id)
        )

        # ============================================================
        # STEP 3: Clear FK references in partner_commissions before deleting payouts
        # partner_commissions.payout_id -> partner_payouts.id (NO ACTION)
        # ============================================================
        await db.execute(
            text("UPDATE partner_commissions SET payout_id = NULL WHERE partner_id = :pid"),
            {"pid": str(partner_id)}
        )

        # ============================================================
        # STEP 4: Delete partner_commissions (must be before partner_payouts)
        # ============================================================
        await db.execute(
            delete(PartnerCommission).where(PartnerCommission.partner_id == partner_id)
        )

        # ============================================================
        # STEP 5: Delete partner_payouts
        # ============================================================
        await db.execute(
            delete(PartnerPayout).where(PartnerPayout.partner_id == partner_id)
        )

        # ============================================================
        # STEP 6: Clear FK references in partner_referrals before deleting
        # partner_referrals.payout_id -> partner_payouts.id (NO ACTION)
        # ============================================================
        await db.execute(
            text("""
                UPDATE partner_referrals SET payout_id = NULL
                WHERE referrer_id = :pid OR referred_id = :pid
            """),
            {"pid": str(partner_id)}
        )

        # ============================================================
        # STEP 7: Delete partner_referrals
        # ============================================================
        await db.execute(
            delete(PartnerReferral).where(
                (PartnerReferral.referrer_id == partner_id) | (PartnerReferral.referred_id == partner_id)
            )
        )

        # ============================================================
        # STEP 8: Delete partner_training
        # ============================================================
        await db.execute(
            delete(PartnerTraining).where(PartnerTraining.partner_id == partner_id)
        )

        # ============================================================
        # STEP 9: Clear self-referential FK in community_partners
        # Database has BOTH referred_by AND referred_by_id columns
        # FK constraint is on referred_by column (not referred_by_id)
        # ============================================================
        await db.execute(
            text("""
                UPDATE community_partners
                SET referred_by = NULL, referred_by_id = NULL
                WHERE referred_by = :pid OR referred_by_id = :pid
            """),
            {"pid": str(partner_id)}
        )

        # ============================================================
        # STEP 10: Finally delete the partner
        # ============================================================
        await db.execute(
            text("DELETE FROM community_partners WHERE id = :pid"),
            {"pid": str(partner_id)}
        )

        await db.commit()

    except Exception as e:
        await db.rollback()
        import traceback
        error_detail = f"Failed to delete partner: {str(e)}\n{traceback.format_exc()}"
        raise HTTPException(status_code=500, detail=error_detail)


@router.post("/{partner_id}/verify-kyc", response_model=CommunityPartnerResponse)
@require_module("sales_distribution")
async def verify_partner_kyc(
    partner_id: UUID,
    verification: KYCVerification,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Verify or reject partner KYC (Admin only).
    """
    service = PartnerService(db)
    try:
        partner = await service.verify_kyc(partner_id, verification, current_user.id)
        return partner
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{partner_id}/suspend", response_model=CommunityPartnerResponse)
@require_module("sales_distribution")
async def suspend_partner(
    partner_id: UUID,
    reason: str = Query(..., description="Reason for suspension"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Suspend a partner (Admin only).
    """
    service = PartnerService(db)
    partner = await service.get_partner_by_id(partner_id)

    if not partner:
        raise HTTPException(status_code=404, detail="Partner not found")

    partner.status = "SUSPENDED"
    partner.notes = f"Suspended by {current_user.email}: {reason}"

    await db.commit()
    await db.refresh(partner)

    return partner


@router.post("/{partner_id}/activate", response_model=CommunityPartnerResponse)
@require_module("sales_distribution")
async def activate_partner(
    partner_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Reactivate a suspended partner (Admin only).
    """
    service = PartnerService(db)
    partner = await service.get_partner_by_id(partner_id)

    if not partner:
        raise HTTPException(status_code=404, detail="Partner not found")

    if partner.kyc_status != "VERIFIED":
        raise HTTPException(status_code=400, detail="Partner KYC is not verified")

    partner.status = "ACTIVE"
    partner.activated_at = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(partner)

    return partner


@router.get("/analytics/summary", response_model=PartnerAnalytics)
@require_module("sales_distribution")
async def get_partner_analytics(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get overall partner program analytics (Admin only).
    """
    service = PartnerService(db)
    analytics = await service.get_partner_analytics()
    return analytics


# ============================================================================
# Commission Admin Endpoints
# ============================================================================

@router.get("/{partner_id}/commissions")
@require_module("sales_distribution")
async def get_partner_commissions(
    partner_id: UUID,
    status: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get commission history for a partner (Admin only).
    """
    query = select(PartnerCommission).where(PartnerCommission.partner_id == partner_id)

    if status:
        query = query.where(PartnerCommission.status == status)

    query = query.order_by(PartnerCommission.created_at.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)

    result = await db.execute(query)
    commissions = result.scalars().all()

    return {
        "items": [PartnerCommissionResponse.model_validate(c) for c in commissions],
        "page": page,
        "page_size": page_size,
    }


@router.post("/commissions/{commission_id}/approve")
@require_module("sales_distribution")
async def approve_commission(
    commission_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Approve a pending commission (Admin only).
    """
    service = PartnerService(db)
    try:
        commission = await service.approve_commission(commission_id)
        return PartnerCommissionResponse.model_validate(commission)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{partner_id}/payouts")
@require_module("sales_distribution")
async def get_partner_payouts(
    partner_id: UUID,
    status: Optional[str] = Query(None, description="Filter by payout status"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get payout history for a specific partner (Admin only).

    Used by ERP admin panel to view partner's payout history.
    """
    from sqlalchemy import func

    # Count total payouts
    count_query = select(func.count(PartnerPayout.id)).where(
        PartnerPayout.partner_id == partner_id
    )
    if status:
        count_query = count_query.where(PartnerPayout.status == status)

    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # Fetch payouts
    query = select(PartnerPayout).where(PartnerPayout.partner_id == partner_id)

    if status:
        query = query.where(PartnerPayout.status == status)

    query = query.order_by(PartnerPayout.created_at.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)

    result = await db.execute(query)
    payouts = result.scalars().all()

    return {
        "items": [PartnerPayoutResponse.model_validate(p) for p in payouts],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.post("/payouts/{payout_id}/process")
@require_module("sales_distribution")
async def process_payout(
    payout_id: UUID,
    reference: str = Query(None, description="Bank transfer reference"),
    success: bool = Query(True, description="Whether transfer was successful"),
    failure_reason: str = Query(None, description="Reason for failure"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Mark payout as processed after bank transfer (Admin only).
    """
    service = PartnerService(db)
    try:
        payout = await service.process_payout(payout_id, reference, success, failure_reason)
        return PartnerPayoutResponse.model_validate(payout)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
