"""Manifest models for shipping handover management."""
import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import TYPE_CHECKING, Optional, List

from sqlalchemy import String, Boolean, DateTime, ForeignKey, Integer, Text, Float, Date
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.warehouse import Warehouse
    from app.models.transporter import Transporter
    from app.models.shipment import Shipment
    from app.models.user import User


class ManifestStatus(str, Enum):
    """Manifest status enumeration."""
    DRAFT = "DRAFT"               # Being prepared
    PENDING = "PENDING"           # Ready for handover
    CONFIRMED = "CONFIRMED"       # Confirmed, awaiting pickup
    HANDED_OVER = "HANDED_OVER"   # Handed to transporter
    IN_TRANSIT = "IN_TRANSIT"     # All shipments in transit
    COMPLETED = "COMPLETED"       # All shipments delivered
    CANCELLED = "CANCELLED"       # Manifest cancelled


class BusinessType(str, Enum):
    """Business type for manifest."""
    B2C = "B2C"     # Business to Consumer
    B2B = "B2B"     # Business to Business


class Manifest(Base):
    """
    Manifest model for grouping shipments for transporter handover.
    Similar to Vinculum's Manage Manifest feature.
    """
    __tablename__ = "manifests"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )

    # Identification
    manifest_number: Mapped[str] = mapped_column(
        String(30),
        unique=True,
        nullable=False,
        index=True,
        comment="Unique manifest number e.g., MF-20240101-0001"
    )

    # Warehouse
    warehouse_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("warehouses.id", ondelete="RESTRICT"),
        nullable=False,
        index=True
    )

    # Transporter
    transporter_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("transporters.id", ondelete="RESTRICT"),
        nullable=False,
        index=True
    )

    # Status
    status: Mapped[str] = mapped_column(
        String(50),
        default="DRAFT",
        nullable=False,
        index=True,
        comment="DRAFT, PENDING, CONFIRMED, HANDED_OVER, IN_TRANSIT, COMPLETED, CANCELLED"
    )

    # Business type
    business_type: Mapped[str] = mapped_column(
        String(50),
        default="B2C",
        nullable=False,
        comment="B2C, B2B"
    )

    # Manifest date
    manifest_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    # Counts
    total_shipments: Mapped[int] = mapped_column(Integer, default=0)
    scanned_shipments: Mapped[int] = mapped_column(
        Integer,
        default=0,
        comment="Shipments scanned for handover"
    )

    # Weight
    total_weight_kg: Mapped[float] = mapped_column(Float, default=0.0)
    total_boxes: Mapped[int] = mapped_column(Integer, default=0)

    # Vehicle details
    vehicle_number: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    driver_name: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    driver_phone: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)

    # Remarks
    remarks: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Created by
    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )

    # Confirmed by
    confirmed_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )
    confirmed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Handover
    handover_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    handover_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False
    )
    cancelled_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    cancellation_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    warehouse: Mapped["Warehouse"] = relationship("Warehouse")
    transporter: Mapped["Transporter"] = relationship(
        "Transporter",
        back_populates="manifests"
    )
    created_by_user: Mapped[Optional["User"]] = relationship(
        "User",
        foreign_keys=[created_by]
    )
    confirmed_by_user: Mapped[Optional["User"]] = relationship(
        "User",
        foreign_keys=[confirmed_by]
    )
    handover_by_user: Mapped[Optional["User"]] = relationship(
        "User",
        foreign_keys=[handover_by]
    )
    items: Mapped[List["ManifestItem"]] = relationship(
        "ManifestItem",
        back_populates="manifest",
        cascade="all, delete-orphan"
    )
    shipments: Mapped[List["Shipment"]] = relationship(
        "Shipment",
        back_populates="manifest"
    )

    @property
    def all_scanned(self) -> bool:
        """Check if all shipments are scanned."""
        return self.scanned_shipments >= self.total_shipments

    @property
    def scan_progress(self) -> float:
        """Get scanning progress percentage."""
        if self.total_shipments > 0:
            return (self.scanned_shipments / self.total_shipments) * 100
        return 0.0

    def __repr__(self) -> str:
        return f"<Manifest(number='{self.manifest_number}', status='{self.status}')>"


class ManifestItem(Base):
    """
    Manifest item model.
    Individual shipments in a manifest.
    """
    __tablename__ = "manifest_items"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )

    manifest_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("manifests.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    shipment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("shipments.id", ondelete="RESTRICT"),
        nullable=False,
        index=True
    )

    # AWB/Tracking
    awb_number: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    tracking_number: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # Order reference
    order_number: Mapped[str] = mapped_column(String(50), nullable=False)

    # Weight
    weight_kg: Mapped[float] = mapped_column(Float, default=0.0)
    no_of_boxes: Mapped[int] = mapped_column(Integer, default=1)

    # Scan status
    is_scanned: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        comment="Scanned for handover confirmation"
    )
    scanned_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    scanned_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )

    # Handover status
    is_handed_over: Mapped[bool] = mapped_column(Boolean, default=False)
    handed_over_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Destination
    destination_pincode: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    destination_city: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    # Relationships
    manifest: Mapped["Manifest"] = relationship(
        "Manifest",
        back_populates="items"
    )
    shipment: Mapped["Shipment"] = relationship(
        "Shipment",
        back_populates="manifest_item"
    )
    scanned_by_user: Mapped[Optional["User"]] = relationship("User")

    def __repr__(self) -> str:
        return f"<ManifestItem(awb='{self.awb_number}', scanned={self.is_scanned})>"
