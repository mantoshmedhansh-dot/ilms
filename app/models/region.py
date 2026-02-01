import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import TYPE_CHECKING, Optional, List

from sqlalchemy import String, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID

from app.database import Base

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.warehouse import Warehouse


class RegionType(str, Enum):
    """Types of regions in hierarchy."""
    COUNTRY = "COUNTRY"
    ZONE = "ZONE"
    STATE = "STATE"
    CITY = "CITY"
    AREA = "AREA"


class Region(Base):
    """
    Region model for geographic hierarchy.
    Supports: Country > Zone > State > City > Area
    """
    __tablename__ = "regions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    code: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="STATE",
        comment="COUNTRY, ZONE, STATE, CITY, AREA"
    )

    # Self-referential for hierarchy
    parent_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("regions.id", ondelete="SET NULL"),
        nullable=True
    )

    # Additional fields
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

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
    parent: Mapped[Optional["Region"]] = relationship(
        "Region",
        remote_side=[id],
        back_populates="children"
    )
    children: Mapped[List["Region"]] = relationship(
        "Region",
        back_populates="parent",
        cascade="all, delete-orphan"
    )
    users: Mapped[List["User"]] = relationship(
        "User",
        back_populates="region"
    )
    warehouses: Mapped[List["Warehouse"]] = relationship(
        "Warehouse",
        back_populates="region"
    )

    def __repr__(self) -> str:
        return f"<Region(name='{self.name}', type='{self.type}', code='{self.code}')>"
