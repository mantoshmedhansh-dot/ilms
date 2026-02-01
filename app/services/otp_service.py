"""
OTP Service for D2C Customer Authentication

Handles OTP generation, sending via SMS, and verification.
"""

import logging
import hashlib
import secrets
from datetime import datetime, timezone, timedelta
from typing import Optional, Tuple

from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.customer_otp import CustomerOTP
from app.config import settings

logger = logging.getLogger(__name__)


class OTPService:
    """
    Service for handling OTP operations.
    """

    # OTP Configuration
    OTP_LENGTH = 6
    OTP_EXPIRY_MINUTES = 10
    MAX_ATTEMPTS = 3
    RESEND_COOLDOWN_SECONDS = 30

    def __init__(self, db: AsyncSession):
        self.db = db

    def _generate_otp(self) -> str:
        """Generate a random numeric OTP."""
        return "".join([str(secrets.randbelow(10)) for _ in range(self.OTP_LENGTH)])

    def _hash_otp(self, otp: str) -> str:
        """Hash OTP for secure storage."""
        return hashlib.sha256(otp.encode()).hexdigest()

    def _verify_hash(self, otp: str, otp_hash: str) -> bool:
        """Verify OTP against stored hash."""
        return self._hash_otp(otp) == otp_hash

    async def create_otp(
        self,
        phone: str,
        purpose: str = "LOGIN"
    ) -> Tuple[str, CustomerOTP]:
        """
        Create a new OTP for the given phone number.

        Args:
            phone: Customer phone number
            purpose: Purpose of OTP (LOGIN, REGISTER, VERIFY_PHONE, RESET)

        Returns:
            Tuple of (otp_code, otp_record)
        """
        # Invalidate any existing OTPs for this phone and purpose
        await self.db.execute(
            delete(CustomerOTP).where(
                CustomerOTP.phone == phone,
                CustomerOTP.purpose == purpose,
                CustomerOTP.is_verified == False
            )
        )

        # Generate new OTP
        otp_code = self._generate_otp()
        otp_hash = self._hash_otp(otp_code)

        # Calculate expiry
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=self.OTP_EXPIRY_MINUTES)

        # Create OTP record
        otp_record = CustomerOTP(
            phone=phone,
            otp_hash=otp_hash,
            purpose=purpose,
            expires_at=expires_at,
            max_attempts=self.MAX_ATTEMPTS
        )

        self.db.add(otp_record)
        await self.db.commit()
        await self.db.refresh(otp_record)

        logger.info(f"OTP created for phone {phone[-4:].rjust(10, '*')} purpose={purpose}")

        return otp_code, otp_record

    async def verify_otp(
        self,
        phone: str,
        otp_code: str,
        purpose: str = "LOGIN"
    ) -> Tuple[bool, str]:
        """
        Verify an OTP.

        Args:
            phone: Customer phone number
            otp_code: OTP code to verify
            purpose: Purpose of OTP

        Returns:
            Tuple of (success, message)
        """
        # Find the latest unverified OTP for this phone and purpose
        result = await self.db.execute(
            select(CustomerOTP)
            .where(
                CustomerOTP.phone == phone,
                CustomerOTP.purpose == purpose,
                CustomerOTP.is_verified == False
            )
            .order_by(CustomerOTP.created_at.desc())
            .limit(1)
        )
        otp_record = result.scalar_one_or_none()

        if not otp_record:
            logger.warning(f"No OTP found for phone {phone[-4:].rjust(10, '*')}")
            return False, "No OTP found. Please request a new one."

        # Check if expired
        if otp_record.is_expired:
            logger.warning(f"OTP expired for phone {phone[-4:].rjust(10, '*')}")
            return False, "OTP has expired. Please request a new one."

        # Check attempts
        if not otp_record.can_attempt:
            logger.warning(f"Max attempts exceeded for phone {phone[-4:].rjust(10, '*')}")
            return False, "Maximum attempts exceeded. Please request a new OTP."

        # Increment attempts
        otp_record.attempts += 1

        # Verify OTP
        if not self._verify_hash(otp_code, otp_record.otp_hash):
            await self.db.commit()
            remaining = otp_record.max_attempts - otp_record.attempts
            logger.warning(f"Invalid OTP attempt for phone {phone[-4:].rjust(10, '*')}, {remaining} left")
            return False, f"Invalid OTP. {remaining} attempts remaining."

        # Mark as verified
        otp_record.is_verified = True
        otp_record.verified_at = datetime.now(timezone.utc)
        await self.db.commit()

        logger.info(f"OTP verified for phone {phone[-4:].rjust(10, '*')}")
        return True, "OTP verified successfully."

    async def can_resend_otp(self, phone: str, purpose: str = "LOGIN") -> Tuple[bool, int]:
        """
        Check if OTP can be resent (cooldown check).

        Returns:
            Tuple of (can_resend, seconds_remaining)
        """
        result = await self.db.execute(
            select(CustomerOTP)
            .where(
                CustomerOTP.phone == phone,
                CustomerOTP.purpose == purpose,
            )
            .order_by(CustomerOTP.created_at.desc())
            .limit(1)
        )
        otp_record = result.scalar_one_or_none()

        if not otp_record:
            return True, 0

        # Calculate time since last OTP
        time_since = (datetime.now(timezone.utc) - otp_record.created_at).total_seconds()
        if time_since < self.RESEND_COOLDOWN_SECONDS:
            remaining = int(self.RESEND_COOLDOWN_SECONDS - time_since)
            return False, remaining

        return True, 0


async def send_otp_sms(phone: str, otp: str) -> bool:
    """
    Send OTP via SMS using MSG91.

    Args:
        phone: Customer phone number
        otp: OTP code

    Returns:
        True if sent successfully, False otherwise
    """
    import httpx

    auth_key = settings.MSG91_AUTH_KEY
    template_id = settings.MSG91_TEMPLATE_ID_OTP

    if not auth_key or not template_id:
        logger.warning("MSG91 not configured, OTP SMS not sent")
        # In development, log the OTP
        logger.info(f"DEV MODE - OTP for {phone}: {otp}")
        return True

    try:
        # Format phone for MSG91 (add 91 if not present)
        formatted_phone = phone
        if not phone.startswith("91") and not phone.startswith("+91"):
            formatted_phone = f"91{phone}"
        formatted_phone = formatted_phone.replace("+", "")

        url = "https://control.msg91.com/api/v5/flow/"
        headers = {
            "authkey": auth_key,
            "Content-Type": "application/json"
        }
        payload = {
            "template_id": template_id,
            "short_url": "0",
            "recipients": [
                {
                    "mobiles": formatted_phone,
                    "otp": otp
                }
            ]
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=payload, headers=headers, timeout=10)
            response.raise_for_status()

            result = response.json()
            if result.get("type") == "success":
                logger.info(f"OTP SMS sent to {phone[-4:].rjust(10, '*')}")
                return True
            else:
                logger.error(f"MSG91 error: {result}")
                return False

    except Exception as e:
        logger.error(f"Failed to send OTP SMS: {e}")
        return False
