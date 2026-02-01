"""
Partner Authentication Service

Handles OTP-based authentication for Community Partners.
Uses the same OTP service as D2C customers but with a different purpose.
"""

import logging
import uuid
from datetime import datetime, timezone, timedelta
from typing import Optional, Tuple

import jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import settings
from app.models.community_partner import CommunityPartner
from app.models.customer_otp import CustomerOTP
from app.services.otp_service import OTPService, send_otp_sms

logger = logging.getLogger(__name__)

# JWT Configuration for Partners
PARTNER_TOKEN_EXPIRE_HOURS = 24 * 7  # 7 days
PARTNER_REFRESH_TOKEN_EXPIRE_DAYS = 30


class PartnerAuthService:
    """
    Service for partner authentication operations.
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        self.otp_service = OTPService(db)

    # ========================================================================
    # JWT Token Management
    # ========================================================================

    @staticmethod
    def create_partner_token(partner_id: str, partner_code: str) -> str:
        """Create JWT access token for partner."""
        payload = {
            "sub": partner_id,
            "partner_code": partner_code,
            "type": "partner_access",
            "exp": datetime.now(timezone.utc) + timedelta(hours=PARTNER_TOKEN_EXPIRE_HOURS),
            "iat": datetime.now(timezone.utc),
        }
        return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

    @staticmethod
    def create_partner_refresh_token(partner_id: str) -> str:
        """Create JWT refresh token for partner."""
        payload = {
            "sub": partner_id,
            "type": "partner_refresh",
            "exp": datetime.now(timezone.utc) + timedelta(days=PARTNER_REFRESH_TOKEN_EXPIRE_DAYS),
            "iat": datetime.now(timezone.utc),
        }
        return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

    @staticmethod
    def decode_partner_token(token: str) -> Optional[dict]:
        """Decode and validate partner token."""
        try:
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
            if payload.get("type") not in ("partner_access", "partner_refresh"):
                return None
            return payload
        except jwt.ExpiredSignatureError:
            return None
        except jwt.InvalidTokenError:
            return None

    @staticmethod
    def get_partner_id_from_token(token: str) -> Optional[str]:
        """Extract partner ID from token."""
        payload = PartnerAuthService.decode_partner_token(token)
        if payload:
            return payload.get("sub")
        return None

    # ========================================================================
    # OTP Operations
    # ========================================================================

    async def send_otp(self, phone: str) -> Tuple[bool, str, Optional[int]]:
        """
        Send OTP to partner phone number.

        Returns:
            Tuple of (success, message, cooldown_seconds)
        """
        # Check if partner exists with this phone
        partner = await self.get_partner_by_phone(phone)
        if not partner:
            return False, "Phone number not registered. Please register first.", None

        # Check cooldown
        can_resend, remaining = await self.otp_service.can_resend_otp(phone, purpose="PARTNER_LOGIN")
        if not can_resend:
            return False, f"Please wait {remaining} seconds before requesting a new OTP", remaining

        # Create and send OTP
        otp_code, otp_record = await self.otp_service.create_otp(phone, purpose="PARTNER_LOGIN")

        # Send via SMS
        sms_sent = await send_otp_sms(phone, otp_code)

        if not sms_sent:
            logger.error(f"Failed to send OTP SMS to partner {phone[-4:].rjust(10, '*')}")
            # Still return success since OTP was created (for dev testing)

        return True, "OTP sent successfully", self.otp_service.RESEND_COOLDOWN_SECONDS

    async def verify_otp(self, phone: str, otp: str) -> Tuple[bool, str, Optional[dict]]:
        """
        Verify OTP and return authentication tokens.

        Returns:
            Tuple of (success, message, auth_data)
        """
        # Verify OTP
        success, message = await self.otp_service.verify_otp(phone, otp, purpose="PARTNER_LOGIN")

        if not success:
            return False, message, None

        # Get partner
        partner = await self.get_partner_by_phone(phone)
        if not partner:
            return False, "Partner not found", None

        # Update last login
        partner.last_login_at = datetime.now(timezone.utc)
        await self.db.commit()

        # Generate tokens
        access_token = self.create_partner_token(str(partner.id), partner.partner_code)
        refresh_token = self.create_partner_refresh_token(str(partner.id))

        auth_data = {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "expires_in": PARTNER_TOKEN_EXPIRE_HOURS * 3600,
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

        logger.info(f"Partner {partner.partner_code} logged in successfully")
        return True, "Login successful", auth_data

    async def refresh_token(self, refresh_token: str) -> Tuple[bool, str, Optional[dict]]:
        """
        Refresh access token using refresh token.

        Returns:
            Tuple of (success, message, new_tokens)
        """
        partner_id = self.get_partner_id_from_token(refresh_token)
        if not partner_id:
            return False, "Invalid or expired refresh token", None

        # Verify partner exists and is active
        partner = await self.get_partner_by_id(uuid.UUID(partner_id))
        if not partner:
            return False, "Partner not found", None

        if partner.status in ["BLOCKED", "SUSPENDED"]:
            return False, f"Partner account is {partner.status.lower()}", None

        # Generate new access token
        access_token = self.create_partner_token(str(partner.id), partner.partner_code)

        return True, "Token refreshed", {
            "access_token": access_token,
            "token_type": "bearer",
            "expires_in": PARTNER_TOKEN_EXPIRE_HOURS * 3600,
        }

    # ========================================================================
    # Partner Queries
    # ========================================================================

    async def get_partner_by_phone(self, phone: str) -> Optional[CommunityPartner]:
        """Get partner by phone number."""
        result = await self.db.execute(
            select(CommunityPartner)
            .options(selectinload(CommunityPartner.tier))
            .where(CommunityPartner.phone == phone)
        )
        return result.scalar_one_or_none()

    async def get_partner_by_id(self, partner_id: uuid.UUID) -> Optional[CommunityPartner]:
        """Get partner by ID."""
        result = await self.db.execute(
            select(CommunityPartner)
            .options(selectinload(CommunityPartner.tier))
            .where(CommunityPartner.id == partner_id)
        )
        return result.scalar_one_or_none()

    async def get_current_partner_from_token(self, token: str) -> Optional[CommunityPartner]:
        """Get current partner from access token."""
        partner_id = self.get_partner_id_from_token(token)
        if not partner_id:
            return None

        try:
            return await self.get_partner_by_id(uuid.UUID(partner_id))
        except ValueError:
            return None
