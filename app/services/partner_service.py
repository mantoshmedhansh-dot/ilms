"""
Community Partner Service

Handles all business logic for the Community Sales Channel:
- Partner registration
- KYC verification
- Commission calculation and payouts
- Tier progression
- Referral tracking
"""

import uuid
import random
import string
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional, List, Tuple

from sqlalchemy import select, func, and_, or_
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.community_partner import (
    CommunityPartner,
    PartnerTier,
    PartnerCommission,
    PartnerPayout,
    PartnerReferral,
    PartnerTraining,
    PartnerOrder,
)
from app.models.order import Order
from app.schemas.community_partner import (
    CommunityPartnerCreate,
    CommunityPartnerUpdate,
    KYCSubmission,
    KYCVerification,
    PayoutRequest,
)


class PartnerService:
    """Service for Community Partner operations"""

    def __init__(self, db: AsyncSession):
        self.db = db

    # ========================================================================
    # Partner Code Generation
    # ========================================================================

    async def generate_partner_code(self) -> str:
        """
        Generate unique partner code: AP + 6 alphanumeric characters
        Example: APKR7X2M
        """
        while True:
            suffix = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
            code = f"AP{suffix}"

            # Check uniqueness
            result = await self.db.execute(
                select(CommunityPartner.id).where(CommunityPartner.partner_code == code)
            )
            if not result.scalar_one_or_none():
                return code

    async def generate_referral_code(self, name: str) -> str:
        """
        Generate unique referral code from partner name
        Example: RAVI2K5M (first 4 letters of name + 4 random)
        """
        prefix = ''.join(c for c in name.upper() if c.isalpha())[:4]
        if len(prefix) < 4:
            prefix = prefix.ljust(4, 'X')

        while True:
            suffix = ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
            code = f"{prefix}{suffix}"

            result = await self.db.execute(
                select(CommunityPartner.id).where(CommunityPartner.referral_code == code)
            )
            if not result.scalar_one_or_none():
                return code

    # ========================================================================
    # Partner Registration
    # ========================================================================

    async def register_partner(
        self,
        data: CommunityPartnerCreate
    ) -> CommunityPartner:
        """
        Register a new community partner.

        Flow:
        1. Validate phone is not already registered
        2. Generate unique partner code
        3. Generate referral code
        4. Link to referring partner if referral code provided
        5. Assign to Bronze tier (default)
        6. Create partner record
        """
        # Check if phone already exists
        existing = await self.db.execute(
            select(CommunityPartner).where(CommunityPartner.phone == data.phone)
        )
        if existing.scalar_one_or_none():
            raise ValueError(f"Phone number {data.phone} is already registered")

        # Check if email already exists (if provided)
        if data.email:
            existing = await self.db.execute(
                select(CommunityPartner).where(CommunityPartner.email == data.email)
            )
            if existing.scalar_one_or_none():
                raise ValueError(f"Email {data.email} is already registered")

        # Get Bronze tier (default for new partners)
        bronze_tier = await self.db.execute(
            select(PartnerTier).where(PartnerTier.code == "BRONZE")
        )
        bronze = bronze_tier.scalar_one_or_none()

        # Handle referral
        referred_by_id = None
        if data.referred_by_code:
            referrer = await self.db.execute(
                select(CommunityPartner).where(
                    CommunityPartner.referral_code == data.referred_by_code
                )
            )
            referrer_partner = referrer.scalar_one_or_none()
            if referrer_partner:
                referred_by_id = referrer_partner.id

        # Generate codes
        partner_code = await self.generate_partner_code()
        referral_code = await self.generate_referral_code(data.full_name)

        # Create partner
        partner = CommunityPartner(
            id=uuid.uuid4(),
            partner_code=partner_code,
            full_name=data.full_name,
            phone=data.phone,
            email=data.email,
            address_line1=data.address_line1,
            address_line2=data.address_line2,
            city=data.city,
            district=data.district,
            state=data.state,
            pincode=data.pincode,
            date_of_birth=data.date_of_birth,
            gender=data.gender,
            partner_type=data.partner_type,
            occupation=data.occupation,
            status="PENDING_KYC",
            kyc_status="NOT_SUBMITTED",
            tier_id=bronze.id if bronze else None,
            referred_by_id=referred_by_id,
            referred_by_code=data.referred_by_code,
            referral_code=referral_code,
            registered_at=datetime.now(timezone.utc),
        )

        # If KYC details provided during registration
        if data.aadhaar_number:
            partner.aadhaar_number = data.aadhaar_number
        if data.pan_number:
            partner.pan_number = data.pan_number
        if data.bank_account_number:
            partner.bank_account_number = data.bank_account_number
            partner.bank_ifsc = data.bank_ifsc
            partner.bank_account_holder_name = data.bank_account_holder_name
            partner.bank_name = data.bank_name

        self.db.add(partner)
        await self.db.commit()
        await self.db.refresh(partner)

        # Create referral record if referred
        if referred_by_id:
            referral = PartnerReferral(
                id=uuid.uuid4(),
                referrer_id=referred_by_id,
                referred_id=partner.id,
                referral_code=data.referred_by_code,
                bonus_amount=Decimal("0"),  # Bonus awarded after first order
                referred_qualified=False,
            )
            self.db.add(referral)
            await self.db.commit()

        # Re-fetch partner with tier relationship loaded for response serialization
        result = await self.db.execute(
            select(CommunityPartner)
            .options(selectinload(CommunityPartner.tier))
            .where(CommunityPartner.id == partner.id)
        )
        partner = result.scalar_one()

        return partner

    # ========================================================================
    # KYC Management
    # ========================================================================

    async def submit_kyc(
        self,
        partner_id: uuid.UUID,
        data: KYCSubmission
    ) -> CommunityPartner:
        """
        Submit KYC documents for verification.
        Updates partner status to KYC_SUBMITTED.
        """
        partner = await self.get_partner_by_id(partner_id)
        if not partner:
            raise ValueError("Partner not found")

        if partner.kyc_status == "VERIFIED":
            raise ValueError("KYC is already verified")

        # Update KYC details
        partner.aadhaar_number = data.aadhaar_number
        partner.aadhaar_front_url = data.aadhaar_front_url
        partner.aadhaar_back_url = data.aadhaar_back_url

        if data.pan_number:
            partner.pan_number = data.pan_number
            partner.pan_document_url = data.pan_card_url

        # Update bank details
        partner.bank_account_number = data.bank_account_number
        partner.bank_ifsc = data.bank_ifsc
        partner.bank_account_holder_name = data.bank_account_name
        partner.bank_name = data.bank_name

        # Update status
        partner.kyc_status = "PENDING"
        partner.status = "KYC_SUBMITTED"

        await self.db.commit()

        # Re-fetch with tier loaded for response serialization
        result = await self.db.execute(
            select(CommunityPartner)
            .options(selectinload(CommunityPartner.tier))
            .where(CommunityPartner.id == partner_id)
        )
        partner = result.scalar_one()

        return partner

    async def verify_kyc(
        self,
        partner_id: uuid.UUID,
        verification: KYCVerification,
        verified_by_id: uuid.UUID
    ) -> CommunityPartner:
        """
        Admin action to verify or reject KYC.
        """
        partner = await self.get_partner_by_id(partner_id)
        if not partner:
            raise ValueError("Partner not found")

        partner.kyc_status = verification.kyc_status.value if hasattr(verification.kyc_status, 'value') else verification.kyc_status
        partner.kyc_verified_by = verified_by_id

        if verification.kyc_status in ["VERIFIED", "verified"]:
            partner.status = "ACTIVE"
            partner.kyc_verified_at = datetime.now(timezone.utc)
            partner.activated_at = datetime.now(timezone.utc)
            partner.aadhaar_verified = True
            partner.pan_verified = bool(partner.pan_number)
            partner.bank_verified = True
        elif verification.kyc_status in ["REJECTED", "rejected"]:
            partner.status = "KYC_REJECTED"
            partner.kyc_rejection_reason = verification.kyc_rejection_reason

        await self.db.commit()

        # Re-fetch with tier loaded for response serialization
        result = await self.db.execute(
            select(CommunityPartner)
            .options(selectinload(CommunityPartner.tier))
            .where(CommunityPartner.id == partner_id)
        )
        partner = result.scalar_one()

        return partner

    # ========================================================================
    # Partner Queries
    # ========================================================================

    async def get_partner_by_id(self, partner_id: uuid.UUID) -> Optional[CommunityPartner]:
        """Get partner by ID with tier loaded"""
        result = await self.db.execute(
            select(CommunityPartner)
            .options(selectinload(CommunityPartner.tier))
            .where(CommunityPartner.id == partner_id)
        )
        return result.scalar_one_or_none()

    async def get_partner_by_phone(self, phone: str) -> Optional[CommunityPartner]:
        """Get partner by phone number"""
        result = await self.db.execute(
            select(CommunityPartner)
            .options(selectinload(CommunityPartner.tier))
            .where(CommunityPartner.phone == phone)
        )
        return result.scalar_one_or_none()

    async def get_partner_by_code(self, partner_code: str) -> Optional[CommunityPartner]:
        """Get partner by partner code"""
        result = await self.db.execute(
            select(CommunityPartner)
            .options(selectinload(CommunityPartner.tier))
            .where(CommunityPartner.partner_code == partner_code)
        )
        return result.scalar_one_or_none()

    async def list_partners(
        self,
        status: Optional[str] = None,
        kyc_status: Optional[str] = None,
        state: Optional[str] = None,
        search: Optional[str] = None,
        page: int = 1,
        page_size: int = 20
    ) -> Tuple[List[CommunityPartner], int]:
        """
        List partners with filters and pagination.
        """
        query = select(CommunityPartner).options(selectinload(CommunityPartner.tier))

        # Apply filters
        filters = []
        if status:
            filters.append(CommunityPartner.status == status)
        if kyc_status:
            filters.append(CommunityPartner.kyc_status == kyc_status)
        if state:
            filters.append(CommunityPartner.state == state)
        if search:
            search_filter = or_(
                CommunityPartner.full_name.ilike(f"%{search}%"),
                CommunityPartner.phone.ilike(f"%{search}%"),
                CommunityPartner.partner_code.ilike(f"%{search}%"),
                CommunityPartner.email.ilike(f"%{search}%"),
            )
            filters.append(search_filter)

        if filters:
            query = query.where(and_(*filters))

        # Get total count
        count_query = select(func.count(CommunityPartner.id))
        if filters:
            count_query = count_query.where(and_(*filters))
        total_result = await self.db.execute(count_query)
        total = total_result.scalar()

        # Apply pagination
        query = query.order_by(CommunityPartner.registered_at.desc())
        query = query.offset((page - 1) * page_size).limit(page_size)

        result = await self.db.execute(query)
        partners = result.scalars().all()

        return list(partners), total

    async def update_partner(
        self,
        partner_id: uuid.UUID,
        data: CommunityPartnerUpdate
    ) -> CommunityPartner:
        """Update partner profile"""
        partner = await self.get_partner_by_id(partner_id)
        if not partner:
            raise ValueError("Partner not found")

        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            if hasattr(partner, field):
                setattr(partner, field, value)

        partner.updated_at = datetime.now(timezone.utc)
        await self.db.commit()

        # Re-fetch with tier loaded for response serialization
        result = await self.db.execute(
            select(CommunityPartner)
            .options(selectinload(CommunityPartner.tier))
            .where(CommunityPartner.id == partner_id)
        )
        partner = result.scalar_one()

        return partner

    # ========================================================================
    # Commission Management
    # ========================================================================

    async def calculate_commission(
        self,
        partner_id: uuid.UUID,
        order_id: uuid.UUID,
        order_amount: Decimal
    ) -> PartnerCommission:
        """
        Calculate and record commission for an order.
        """
        partner = await self.get_partner_by_id(partner_id)
        if not partner:
            raise ValueError("Partner not found")

        if partner.status != "ACTIVE":
            raise ValueError("Partner is not active")

        # Get commission rate from tier
        commission_rate = Decimal("10.00")  # Default
        bonus_rate = Decimal("0")
        if partner.tier:
            commission_rate = partner.tier.commission_percentage
            bonus_rate = partner.tier.bonus_percentage

        commission_amount = (order_amount * commission_rate / Decimal("100")).quantize(Decimal("0.01"))
        bonus_amount = (order_amount * bonus_rate / Decimal("100")).quantize(Decimal("0.01"))

        # TDS calculation (5% if commission > 15000 in FY)
        tds_rate = Decimal("0")
        tds_amount = Decimal("0")

        # Check total commission this FY
        fy_start = datetime(datetime.now().year if datetime.now().month >= 4 else datetime.now().year - 1, 4, 1, tzinfo=timezone.utc)
        fy_total_result = await self.db.execute(
            select(func.coalesce(func.sum(PartnerCommission.commission_amount), 0))
            .where(
                PartnerCommission.partner_id == partner_id,
                PartnerCommission.created_at >= fy_start
            )
        )
        fy_total = fy_total_result.scalar() or Decimal("0")

        if fy_total + commission_amount > Decimal("15000"):
            tds_rate = Decimal("5.00")
            tds_amount = (commission_amount * tds_rate / Decimal("100")).quantize(Decimal("0.01"))

        total_earnings = commission_amount + bonus_amount
        net_earnings = total_earnings - tds_amount

        # Get order details for commission record
        order_result = await self.db.execute(
            select(Order).where(Order.id == order_id)
        )
        order = order_result.scalar_one_or_none()

        # Create commission record
        commission = PartnerCommission(
            id=uuid.uuid4(),
            partner_id=partner_id,
            order_id=order_id,
            order_number=order.order_number if order else f"ORD-{order_id}",
            order_date=order.created_at if order else datetime.now(timezone.utc),
            order_amount=order_amount,
            order_items_count=len(order.items) if order and hasattr(order, 'items') else 1,
            commission_rate=commission_rate,
            commission_amount=commission_amount,
            bonus_amount=bonus_amount,
            total_earnings=total_earnings,
            tds_rate=tds_rate,
            tds_amount=tds_amount,
            net_earnings=net_earnings,
            tier_id=partner.tier_id,
            tier_code=partner.tier.code if partner.tier else None,
            status="PENDING",
        )

        self.db.add(commission)

        # Update partner totals
        partner.total_commission_earned = (partner.total_commission_earned or Decimal("0")) + net_earnings
        partner.wallet_balance = (partner.wallet_balance or Decimal("0")) + net_earnings

        await self.db.commit()
        await self.db.refresh(commission)

        # Check for tier upgrade
        await self.check_tier_upgrade(partner_id)

        return commission

    async def approve_commission(self, commission_id: uuid.UUID) -> PartnerCommission:
        """Admin approves commission for payout"""
        result = await self.db.execute(
            select(PartnerCommission).where(PartnerCommission.id == commission_id)
        )
        commission = result.scalar_one_or_none()
        if not commission:
            raise ValueError("Commission not found")

        commission.status = "APPROVED"
        commission.approved_at = datetime.now(timezone.utc)

        await self.db.commit()
        await self.db.refresh(commission)
        return commission

    async def get_commission_summary(self, partner_id: uuid.UUID) -> dict:
        """Get commission summary for a partner"""
        # Total earned
        total_result = await self.db.execute(
            select(func.coalesce(func.sum(PartnerCommission.net_earnings), 0))
            .where(PartnerCommission.partner_id == partner_id)
        )
        total_earned = total_result.scalar()

        # Pending
        pending_result = await self.db.execute(
            select(func.coalesce(func.sum(PartnerCommission.net_earnings), 0))
            .where(
                PartnerCommission.partner_id == partner_id,
                PartnerCommission.status.in_(["PENDING", "APPROVED"])
            )
        )
        pending = pending_result.scalar()

        # Paid
        paid_result = await self.db.execute(
            select(func.coalesce(func.sum(PartnerCommission.net_earnings), 0))
            .where(
                PartnerCommission.partner_id == partner_id,
                PartnerCommission.status == "PAID"
            )
        )
        paid = paid_result.scalar()

        # TDS
        tds_result = await self.db.execute(
            select(func.coalesce(func.sum(PartnerCommission.tds_amount), 0))
            .where(PartnerCommission.partner_id == partner_id)
        )
        tds = tds_result.scalar()

        # This month
        month_start = datetime.now(timezone.utc).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        month_result = await self.db.execute(
            select(func.coalesce(func.sum(PartnerCommission.net_earnings), 0))
            .where(
                PartnerCommission.partner_id == partner_id,
                PartnerCommission.created_at >= month_start
            )
        )
        this_month = month_result.scalar()

        return {
            "total_earned": total_earned,
            "pending_amount": pending,
            "paid_amount": paid,
            "tds_deducted": tds,
            "this_month_earned": this_month,
        }

    # ========================================================================
    # Payout Management
    # ========================================================================

    async def create_payout(
        self,
        partner_id: uuid.UUID,
        request: PayoutRequest
    ) -> PartnerPayout:
        """
        Create a payout for approved commissions.
        """
        partner = await self.get_partner_by_id(partner_id)
        if not partner:
            raise ValueError("Partner not found")

        if not partner.bank_account_number or not partner.bank_ifsc:
            raise ValueError("Bank details not verified")

        # Get approved commissions
        approved_result = await self.db.execute(
            select(PartnerCommission)
            .where(
                PartnerCommission.partner_id == partner_id,
                PartnerCommission.status == "APPROVED",
                PartnerCommission.payout_id.is_(None)
            )
        )
        approved_commissions = approved_result.scalars().all()

        if not approved_commissions:
            raise ValueError("No approved commissions available for payout")

        # Calculate totals
        gross_amount = sum(c.commission_amount + c.bonus_amount for c in approved_commissions)
        tds_amount = sum(c.tds_amount for c in approved_commissions)
        net_amount = sum(c.net_earnings for c in approved_commissions)

        # Generate payout number
        payout_number = f"PAY{datetime.now().strftime('%Y%m%d')}{random.randint(1000, 9999)}"

        # Create payout
        payout = PartnerPayout(
            id=uuid.uuid4(),
            partner_id=partner_id,
            payout_number=payout_number,
            gross_amount=gross_amount,
            tds_amount=tds_amount,
            net_amount=net_amount,
            status="PENDING",
            payout_method=request.payout_method.value if hasattr(request.payout_method, 'value') else request.payout_method,
            # Bank details snapshot
            bank_account_number=partner.bank_account_number,
            bank_ifsc=partner.bank_ifsc,
            bank_name=partner.bank_name,
            upi_id=partner.upi_id,
        )

        self.db.add(payout)
        await self.db.flush()

        # Link commissions to payout
        for commission in approved_commissions:
            commission.payout_id = payout.id
            commission.status = "PAID"
            commission.paid_at = datetime.now(timezone.utc)

        # Update partner totals
        partner.total_commission_paid = (partner.total_commission_paid or Decimal("0")) + net_amount
        partner.wallet_balance = (partner.wallet_balance or Decimal("0")) - net_amount

        await self.db.commit()
        await self.db.refresh(payout)

        return payout

    async def process_payout(
        self,
        payout_id: uuid.UUID,
        reference: str = None,
        success: bool = True,
        failure_reason: str = None
    ) -> PartnerPayout:
        """
        Mark payout as processed (called after bank transfer).
        """
        result = await self.db.execute(
            select(PartnerPayout).where(PartnerPayout.id == payout_id)
        )
        payout = result.scalar_one_or_none()
        if not payout:
            raise ValueError("Payout not found")

        if success:
            payout.status = "COMPLETED"
            payout.processed_at = datetime.now(timezone.utc)
            payout.gateway_transaction_id = reference
        else:
            payout.status = "FAILED"
            payout.failed_at = datetime.now(timezone.utc)
            payout.failure_reason = failure_reason
            payout.retry_count = (payout.retry_count or 0) + 1

        await self.db.commit()
        await self.db.refresh(payout)
        return payout

    # ========================================================================
    # Tier Management
    # ========================================================================

    async def check_tier_upgrade(self, partner_id: uuid.UUID) -> Optional[PartnerTier]:
        """
        Check if partner qualifies for tier upgrade based on performance.
        """
        partner = await self.get_partner_by_id(partner_id)
        if not partner:
            return None

        # Get all tiers ordered by commission percentage (ascending = lower tiers first)
        tiers_result = await self.db.execute(
            select(PartnerTier)
            .where(PartnerTier.is_active == True)
            .order_by(PartnerTier.commission_percentage.desc())  # Highest tier first
        )
        tiers = tiers_result.scalars().all()

        # Check qualification for each tier (highest first)
        for tier in tiers:
            if ((partner.total_sales_count or 0) >= tier.min_monthly_sales and
                (partner.total_sales_value or Decimal("0")) >= tier.min_monthly_value):
                if partner.tier_id != tier.id:
                    partner.tier_id = tier.id
                    await self.db.commit()
                    return tier
                break

        return None

    async def get_tier_progress(self, partner_id: uuid.UUID) -> dict:
        """
        Get progress towards next tier.
        """
        partner = await self.get_partner_by_id(partner_id)
        if not partner:
            return {}

        current_tier = partner.tier

        # Get next tier
        if current_tier:
            next_tier_result = await self.db.execute(
                select(PartnerTier)
                .where(
                    PartnerTier.is_active == True,
                    PartnerTier.commission_percentage > current_tier.commission_percentage
                )
                .order_by(PartnerTier.commission_percentage.asc())
                .limit(1)
            )
            next_tier = next_tier_result.scalar_one_or_none()
        else:
            # Get first tier
            next_tier_result = await self.db.execute(
                select(PartnerTier)
                .where(PartnerTier.is_active == True)
                .order_by(PartnerTier.commission_percentage.asc())
                .limit(1)
            )
            next_tier = next_tier_result.scalar_one_or_none()

        if not next_tier:
            return {
                "current_tier": current_tier.name if current_tier else "None",
                "next_tier": None,
                "is_max_tier": True,
            }

        orders_progress = min(100, int(((partner.total_sales_count or 0) / next_tier.min_monthly_sales) * 100)) if next_tier.min_monthly_sales > 0 else 100
        sales_progress = min(100, int(((partner.total_sales_value or Decimal("0")) / next_tier.min_monthly_value) * 100)) if next_tier.min_monthly_value > 0 else 100

        return {
            "current_tier": current_tier.name if current_tier else "None",
            "next_tier": next_tier.name,
            "orders_required": next_tier.min_monthly_sales,
            "orders_completed": partner.total_sales_count or 0,
            "orders_progress": orders_progress,
            "revenue_required": float(next_tier.min_monthly_value),
            "revenue_completed": float(partner.total_sales_value or 0),
            "revenue_progress": sales_progress,
            "is_max_tier": False,
        }

    # ========================================================================
    # Analytics
    # ========================================================================

    async def get_partner_analytics(self) -> dict:
        """
        Get overall partner program analytics.
        """
        # Total partners
        total_result = await self.db.execute(select(func.count(CommunityPartner.id)))
        total_partners = total_result.scalar()

        # Active partners
        active_result = await self.db.execute(
            select(func.count(CommunityPartner.id))
            .where(CommunityPartner.status == "ACTIVE")
        )
        active_partners = active_result.scalar()

        # Pending KYC
        pending_kyc_result = await self.db.execute(
            select(func.count(CommunityPartner.id))
            .where(CommunityPartner.kyc_status == "PENDING")
        )
        pending_kyc = pending_kyc_result.scalar()

        # Total sales through partners
        total_sales_result = await self.db.execute(
            select(func.coalesce(func.sum(CommunityPartner.total_sales_value), 0))
        )
        total_sales = total_sales_result.scalar()

        # Total commissions
        total_commissions_result = await self.db.execute(
            select(func.coalesce(func.sum(PartnerCommission.net_earnings), 0))
        )
        total_commissions = total_commissions_result.scalar()

        # This month sales - use partner commission order amounts
        month_start = datetime.now(timezone.utc).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        month_sales_result = await self.db.execute(
            select(func.coalesce(func.sum(PartnerCommission.order_amount), 0))
            .where(PartnerCommission.created_at >= month_start)
        )
        this_month_sales = month_sales_result.scalar()

        # Tier distribution
        tier_dist_result = await self.db.execute(
            select(PartnerTier.name, func.count(CommunityPartner.id))
            .join(CommunityPartner, CommunityPartner.tier_id == PartnerTier.id)
            .group_by(PartnerTier.name)
        )
        tier_distribution = {r[0]: r[1] for r in tier_dist_result.fetchall()}

        # Top 5 partners by sales
        top_partners_result = await self.db.execute(
            select(CommunityPartner.full_name, CommunityPartner.total_sales_value, CommunityPartner.total_sales_count)
            .where(CommunityPartner.status == "ACTIVE")
            .order_by(CommunityPartner.total_sales_value.desc())
            .limit(5)
        )
        top_partners = [
            {"name": r[0], "sales": float(r[1] or 0), "orders": r[2] or 0}
            for r in top_partners_result.fetchall()
        ]

        return {
            "total_partners": total_partners,
            "active_partners": active_partners,
            "pending_kyc": pending_kyc,
            "total_sales": float(total_sales or 0),
            "total_commissions": float(total_commissions or 0),
            "this_month_sales": float(this_month_sales or 0),
            "tier_distribution": tier_distribution,
            "top_partners": top_partners,
        }

    # ========================================================================
    # Order Attribution
    # ========================================================================

    async def create_partner_order(
        self,
        partner_code: str,
        order_id: uuid.UUID,
        order_amount: float,
    ) -> Optional[PartnerOrder]:
        """
        Create a partner order record for attribution.
        Called when an order is placed with a partner referral code.

        Args:
            partner_code: Partner's referral code or partner code
            order_id: UUID of the order
            order_amount: Order total amount

        Returns:
            PartnerOrder record if partner found, None otherwise
        """
        # Find partner by referral code or partner code
        result = await self.db.execute(
            select(CommunityPartner)
            .options(selectinload(CommunityPartner.tier))
            .where(
                or_(
                    CommunityPartner.partner_code == partner_code,
                    CommunityPartner.referral_code == partner_code,
                )
            )
        )
        partner = result.scalar_one_or_none()

        if not partner:
            return None

        if partner.status != "ACTIVE":
            return None

        # Create partner order record
        partner_order = PartnerOrder(
            id=uuid.uuid4(),
            partner_id=partner.id,
            order_id=order_id,
            attribution_source="PARTNER_LINK",
            partner_code_used=partner_code,
        )

        self.db.add(partner_order)

        # Update partner stats
        partner.total_sales_count = (partner.total_sales_count or 0) + 1
        partner.total_sales_value = (partner.total_sales_value or Decimal("0")) + Decimal(str(order_amount))

        await self.db.commit()
        await self.db.refresh(partner_order)

        return partner_order

    async def get_partner_by_code(self, partner_code: str) -> Optional[CommunityPartner]:
        """Get partner by partner code or referral code."""
        result = await self.db.execute(
            select(CommunityPartner)
            .options(selectinload(CommunityPartner.tier))
            .where(
                or_(
                    CommunityPartner.partner_code == partner_code,
                    CommunityPartner.referral_code == partner_code,
                )
            )
        )
        return result.scalar_one_or_none()
