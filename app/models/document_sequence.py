"""
Document Sequence Model for Atomic Number Generation

INDUSTRY BEST PRACTICE:
━━━━━━━━━━━━━━━━━━━━━━━
• Financial year based numbering (April-March)
• Continuous sequence within financial year (NO daily reset)
• Atomic number generation with database-level locking
• Format: {PREFIX}/{COMPANY_CODE}/{FY}/{SEQUENCE}

DOCUMENT FORMATS:
━━━━━━━━━━━━━━━━
• PR:  PR/APL/25-26/00001  (Purchase Requisition)
• PO:  PO/APL/25-26/00001  (Purchase Order)
• GRN: GRN/APL/25-26/00001 (Goods Receipt Note)
• SRN: SRN/APL/25-26/00001 (Sales Return Note)
• INV: INV/APL/25-26/00001 (Invoice - already exists separately)

USAGE:
━━━━━━
    from app.services.document_sequence_service import DocumentSequenceService

    async def create_pr(db):
        service = DocumentSequenceService(db)
        pr_number = await service.get_next_number("PR")
        # Returns: PR/APL/25-26/00001
"""

import uuid
from datetime import datetime, timezone
from typing import Optional
from enum import Enum

from sqlalchemy import String, Integer, Boolean, DateTime, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class DocumentType(str, Enum):
    """Document types that use sequence numbering."""
    PURCHASE_REQUISITION = "PR"
    PURCHASE_ORDER = "PO"
    GOODS_RECEIPT_NOTE = "GRN"
    SALES_RETURN_NOTE = "SRN"
    STOCK_TRANSFER = "ST"
    STOCK_ADJUSTMENT = "SA"
    MANIFEST = "MF"
    PICKLIST = "PL"


class DocumentSequenceAudit(Base):
    """
    Audit log for document sequence operations.

    Tracks all sequence number generations, previews, and manual updates
    for compliance and debugging purposes.
    """
    __tablename__ = "document_sequence_audit"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )

    document_type: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
        index=True
    )
    financial_year: Mapped[str] = mapped_column(
        String(10),
        nullable=False
    )
    operation: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        comment="GET_NEXT, PREVIEW, MANUAL_UPDATE, SYNC_FROM_TRIGGER"
    )
    old_number: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True
    )
    new_number: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True
    )
    document_number: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True
    )
    source: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        comment="API, TRIGGER, MANUAL"
    )
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        nullable=True
    )
    ip_address: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )


class DocumentSequence(Base):
    """
    Document sequence management for atomic number generation.

    Each document type has one sequence per financial year.
    Uses database-level locking for concurrent safety.

    Example:
        document_type = "PR"
        financial_year = "25-26"
        current_number = 42
        → Next PR number: PR/APL/25-26/00043
    """
    __tablename__ = "document_sequences"
    __table_args__ = (
        UniqueConstraint(
            "document_type", "financial_year",
            name="uq_document_type_fy"
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )

    # Document Identification
    document_type: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
        index=True,
        comment="PR, PO, GRN, SRN, ST, SA, MF, PL"
    )
    document_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="Human readable name"
    )

    # Company/Branch Code
    company_code: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
        default="APL",
        comment="Company code in document number"
    )

    # Financial Year (April-March)
    financial_year: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
        comment="e.g., 25-26 for FY 2025-26"
    )

    # Sequence Counter
    current_number: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        comment="Last used sequence number"
    )

    # Formatting
    padding_length: Mapped[int] = mapped_column(
        Integer,
        default=5,
        comment="Zero padding for sequence (5 = 00001)"
    )
    separator: Mapped[str] = mapped_column(
        String(5),
        default="/",
        comment="Separator between parts"
    )

    # Status
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True
    )

    # Metadata
    description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    def get_next_number(self) -> str:
        """
        Generate next document number.

        NOTE: This method increments current_number but does NOT
        commit to database. The caller must handle the transaction.

        Returns:
            Formatted document number, e.g., PR/APL/25-26/00001
        """
        self.current_number += 1
        seq = str(self.current_number).zfill(self.padding_length)
        sep = self.separator
        return f"{self.document_type}{sep}{self.company_code}{sep}{self.financial_year}{sep}{seq}"

    def preview_next_number(self) -> str:
        """
        Preview next number without incrementing.

        Returns:
            What the next number would be
        """
        next_num = self.current_number + 1
        seq = str(next_num).zfill(self.padding_length)
        sep = self.separator
        return f"{self.document_type}{sep}{self.company_code}{sep}{self.financial_year}{sep}{seq}"

    @staticmethod
    def get_financial_year() -> str:
        """
        Get current financial year string.

        Indian financial year: April to March
        - Jan 2026 → FY 25-26
        - Apr 2026 → FY 26-27

        Returns:
            Financial year string, e.g., "25-26"
        """
        now = datetime.now(timezone.utc)
        year = now.year
        month = now.month

        if month >= 4:  # April onwards
            fy_start = year
            fy_end = year + 1
        else:  # Jan-Mar
            fy_start = year - 1
            fy_end = year

        return f"{fy_start % 100:02d}-{fy_end % 100:02d}"

    def __repr__(self) -> str:
        return f"<DocumentSequence({self.document_type}/{self.financial_year}: {self.current_number})>"
