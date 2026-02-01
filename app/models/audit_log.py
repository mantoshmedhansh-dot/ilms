import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Optional, Any

from sqlalchemy import String, DateTime, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB

from app.database import Base

if TYPE_CHECKING:
    from app.models.user import User


class AuditLog(Base):
    """
    Audit log model for tracking all access control changes.
    Records: role assignments, permission changes, user modifications, etc.
    """
    __tablename__ = "audit_logs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )

    # Who performed the action
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )

    # Action details
    action: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    # Actions: CREATE, UPDATE, DELETE, ASSIGN_ROLE, REVOKE_ROLE,
    #          GRANT_PERMISSION, REVOKE_PERMISSION, LOGIN, LOGOUT, etc.

    # Entity being modified
    entity_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    # Entity types: USER, ROLE, PERMISSION, MODULE, REGION, etc.

    entity_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        nullable=True
    )

    # Change tracking
    old_values: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    new_values: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)

    # Additional context
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Request metadata
    ip_address: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    user_agent: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # Timestamp
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True
    )

    # Relationships
    user: Mapped[Optional["User"]] = relationship("User", foreign_keys=[user_id])

    def __repr__(self) -> str:
        return f"<AuditLog(action='{self.action}', entity='{self.entity_type}', id='{self.entity_id}')>"
