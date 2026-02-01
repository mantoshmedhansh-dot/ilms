"""
Customer OTP Model for D2C Authentication

Stores OTPs for customer phone verification and login.
"""

import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import String, Boolean, DateTime, ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID

from app.database import Base


class CustomerOTP(Base):
    """
    OTP storage for customer authentication.
    OTPs expire after a configured time and have attempt limits.
    """
    __tablename__ = "customer_otps"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )

    # Phone number (indexed for lookups)
    phone: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        index=True
    )

    # OTP code (hashed for security)
    otp_hash: Mapped[str] = mapped_column(
        String(255),
        nullable=False
    )

    # Purpose of OTP
    purpose: Mapped[str] = mapped_column(
        String(50),
        default="LOGIN",
        nullable=False,
        comment="LOGIN, REGISTER, VERIFY_PHONE, RESET"
    )

    # Verification status
    is_verified: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False
    )

    # Attempt tracking
    attempts: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False
    )
    max_attempts: Mapped[int] = mapped_column(
        Integer,
        default=3,
        nullable=False
    )

    # Expiry
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )
    verified_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )

    @property
    def is_expired(self) -> bool:
        """Check if OTP has expired."""
        return datetime.now(timezone.utc) > self.expires_at

    @property
    def can_attempt(self) -> bool:
        """Check if more attempts are allowed."""
        return self.attempts < self.max_attempts and not self.is_expired

    def __repr__(self) -> str:
        return f"<CustomerOTP(phone='{self.phone}', purpose='{self.purpose}', verified={self.is_verified})>"
