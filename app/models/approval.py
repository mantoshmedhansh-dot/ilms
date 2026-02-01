"""
Multi-level Approval Workflow Model.

Implements a generic approval system that can be used for:
- Purchase Orders (PO)
- Stock Transfers
- Stock Adjustments
- Vendor Onboarding
- Any other entity requiring approval workflow

Approval Levels based on amount thresholds:
- LEVEL_1: Up to ₹50,000 - Manager approval
- LEVEL_2: ₹50,001 to ₹5,00,000 - Senior Manager approval
- LEVEL_3: Above ₹5,00,000 - Finance Head approval
"""
import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import TYPE_CHECKING, Optional, List
from decimal import Decimal

from sqlalchemy import String, Boolean, DateTime, ForeignKey, Integer, Text, Numeric, Date
from sqlalchemy import UniqueConstraint, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.user import User


class ApprovalEntityType(str, Enum):
    """Types of entities that can require approval."""
    PURCHASE_ORDER = "PURCHASE_ORDER"
    PURCHASE_REQUISITION = "PURCHASE_REQUISITION"
    STOCK_TRANSFER = "STOCK_TRANSFER"
    STOCK_ADJUSTMENT = "STOCK_ADJUSTMENT"
    VENDOR_ONBOARDING = "VENDOR_ONBOARDING"
    VENDOR_DELETION = "VENDOR_DELETION"
    DEALER_ONBOARDING = "DEALER_ONBOARDING"
    FRANCHISEE_CONTRACT = "FRANCHISEE_CONTRACT"
    JOURNAL_ENTRY = "JOURNAL_ENTRY"
    CREDIT_NOTE = "CREDIT_NOTE"
    DEBIT_NOTE = "DEBIT_NOTE"
    SALES_CHANNEL = "SALES_CHANNEL"


class ApprovalLevel(str, Enum):
    """Approval level based on amount thresholds."""
    LEVEL_1 = "LEVEL_1"  # Up to ₹50,000 - Manager approval
    LEVEL_2 = "LEVEL_2"  # ₹50,001 to ₹5,00,000 - Senior Manager approval
    LEVEL_3 = "LEVEL_3"  # Above ₹5,00,000 - Finance Head approval


class ApprovalStatus(str, Enum):
    """Status of an approval request."""
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    CANCELLED = "CANCELLED"
    ESCALATED = "ESCALATED"


class ApprovalRequest(Base):
    """
    Generic approval request for any entity.

    Tracks the approval workflow including:
    - What entity needs approval (entity_type + entity_id)
    - Current approval level and status
    - Requester and approver information
    - Approval/rejection timestamps and comments
    """
    __tablename__ = "approval_requests"
    __table_args__ = (
        Index("ix_approval_entity", "entity_type", "entity_id"),
        Index("ix_approval_status_level", "status", "approval_level"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )

    # Request Number (auto-generated)
    request_number: Mapped[str] = mapped_column(
        String(30),
        unique=True,
        nullable=False,
        index=True,
        comment="Auto-generated: APR-YYYYMMDD-XXXX"
    )

    # Entity being approved
    entity_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
        comment="PURCHASE_ORDER, PURCHASE_REQUISITION, STOCK_TRANSFER, STOCK_ADJUSTMENT, VENDOR_ONBOARDING, VENDOR_DELETION, DEALER_ONBOARDING, FRANCHISEE_CONTRACT, JOURNAL_ENTRY, CREDIT_NOTE, DEBIT_NOTE, SALES_CHANNEL"
    )
    entity_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
        comment="ID of the entity (PO, Transfer, etc.)"
    )
    entity_number: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="Display number (PO number, Transfer number, etc.)"
    )

    # Amount for threshold-based approval level
    amount: Mapped[Decimal] = mapped_column(
        Numeric(14, 2),
        nullable=False,
        comment="Amount that determines approval level"
    )

    # Approval Level
    approval_level: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
        comment="LEVEL_1 (up to ₹50K), LEVEL_2 (₹50K-₹5L), LEVEL_3 (above ₹5L)"
    )

    # Current Status
    status: Mapped[str] = mapped_column(
        String(50),
        default="PENDING",
        nullable=False,
        index=True,
        comment="PENDING, APPROVED, REJECTED, CANCELLED, ESCALATED"
    )

    # Priority (1=Urgent, 5=Normal, 10=Low)
    priority: Mapped[int] = mapped_column(
        Integer,
        default=5,
        nullable=False
    )

    # Description/Purpose
    title: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
        comment="Short description of what needs approval"
    )
    description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Detailed description/justification"
    )

    # Requester
    requested_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False
    )
    requested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    # Current Approver (who should approve at current level)
    current_approver_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        comment="Specific approver assigned, NULL means any approver with permission"
    )

    # Approval/Rejection
    approved_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )
    approved_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )
    approval_comments: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True
    )

    # Rejection details
    rejected_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )
    rejected_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )
    rejection_reason: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True
    )

    # SLA
    due_date: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Expected approval deadline"
    )
    is_overdue: Mapped[bool] = mapped_column(
        Boolean,
        default=False
    )

    # Escalation
    escalated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )
    escalated_to: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )
    escalation_reason: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True
    )

    # Extra Info
    extra_info: Mapped[Optional[dict]] = mapped_column(
        JSONB,
        nullable=True,
        comment="Additional context (vendor name, product details, etc.)"
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

    # Relationships
    requester: Mapped["User"] = relationship(
        "User",
        foreign_keys=[requested_by]
    )
    approver: Mapped[Optional["User"]] = relationship(
        "User",
        foreign_keys=[approved_by]
    )
    rejecter: Mapped[Optional["User"]] = relationship(
        "User",
        foreign_keys=[rejected_by]
    )
    current_approver: Mapped[Optional["User"]] = relationship(
        "User",
        foreign_keys=[current_approver_id]
    )
    escalated_to_user: Mapped[Optional["User"]] = relationship(
        "User",
        foreign_keys=[escalated_to]
    )
    history: Mapped[List["ApprovalHistory"]] = relationship(
        "ApprovalHistory",
        back_populates="approval_request",
        cascade="all, delete-orphan",
        order_by="ApprovalHistory.created_at"
    )

    def __repr__(self) -> str:
        return f"<ApprovalRequest(number='{self.request_number}', type='{self.entity_type}', status='{self.status}')>"


class ApprovalHistory(Base):
    """
    Audit trail for approval workflow.

    Records every action taken on an approval request.
    """
    __tablename__ = "approval_history"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )

    approval_request_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("approval_requests.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Action
    action: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="SUBMITTED, APPROVED, REJECTED, ESCALATED, CANCELLED, REASSIGNED"
    )

    # Previous and new status
    from_status: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    to_status: Mapped[str] = mapped_column(String(20), nullable=False)

    # Who performed the action
    performed_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False
    )

    # Comments
    comments: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Timestamp
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    # Relationships
    approval_request: Mapped["ApprovalRequest"] = relationship(
        "ApprovalRequest",
        back_populates="history"
    )
    actor: Mapped["User"] = relationship("User")

    def __repr__(self) -> str:
        return f"<ApprovalHistory(action='{self.action}', status='{self.to_status}')>"


# Helper functions for approval level determination
def get_approval_level(amount: Decimal) -> ApprovalLevel:
    """
    Determine approval level based on amount thresholds.

    - LEVEL_1: Up to ₹50,000
    - LEVEL_2: ₹50,001 to ₹5,00,000
    - LEVEL_3: Above ₹5,00,000
    """
    if amount <= Decimal("50000"):
        return ApprovalLevel.LEVEL_1
    elif amount <= Decimal("500000"):
        return ApprovalLevel.LEVEL_2
    else:
        return ApprovalLevel.LEVEL_3


def get_approval_level_name(level: ApprovalLevel) -> str:
    """Get human-readable name for approval level."""
    names = {
        ApprovalLevel.LEVEL_1: "Manager Approval (up to ₹50,000)",
        ApprovalLevel.LEVEL_2: "Senior Manager Approval (₹50,001 - ₹5,00,000)",
        ApprovalLevel.LEVEL_3: "Finance Head Approval (above ₹5,00,000)",
    }
    return names.get(level, str(level))
