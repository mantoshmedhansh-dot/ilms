"""Transporter/Carrier models for shipping management."""
import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import TYPE_CHECKING, Optional, List

from sqlalchemy import String, Boolean, DateTime, ForeignKey, Integer, Text, Float
from sqlalchemy import UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.shipment import Shipment
    from app.models.manifest import Manifest


class TransporterType(str, Enum):
    """Transporter type enumeration."""
    COURIER = "COURIER"           # Third-party courier (Delhivery, BlueDart, etc.)
    SELF_SHIP = "SELF_SHIP"       # Own delivery fleet
    MARKETPLACE = "MARKETPLACE"    # Marketplace logistics (Amazon, Flipkart)
    LOCAL = "LOCAL"               # Local delivery partner
    FRANCHISE = "FRANCHISE"       # Franchise delivery


class Transporter(Base):
    """
    Transporter/Carrier model for shipping partners.
    Manages logistics partners like Delhivery, BlueDart, Self-ship, etc.
    """
    __tablename__ = "transporters"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )

    # Identification
    code: Mapped[str] = mapped_column(
        String(20),
        unique=True,
        nullable=False,
        index=True,
        comment="Unique transporter code e.g., DELHIVERY, SELF_SHIP"
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)

    # Type
    transporter_type: Mapped[str] = mapped_column(
        String(50),
        default="COURIER",
        nullable=False,
        comment="COURIER, SELF_SHIP, MARKETPLACE, LOCAL, FRANCHISE"
    )

    # API Integration
    api_endpoint: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    api_key: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    api_secret: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    webhook_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # Capabilities
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    supports_cod: Mapped[bool] = mapped_column(Boolean, default=True)
    supports_prepaid: Mapped[bool] = mapped_column(Boolean, default=True)
    supports_reverse_pickup: Mapped[bool] = mapped_column(Boolean, default=False)
    supports_surface: Mapped[bool] = mapped_column(Boolean, default=True)
    supports_express: Mapped[bool] = mapped_column(Boolean, default=False)

    # Weight limits
    max_weight_kg: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    min_weight_kg: Mapped[Optional[float]] = mapped_column(Float, default=0.0)

    # Pricing
    base_rate: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    rate_per_kg: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    cod_charges: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    cod_percentage: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Contact
    contact_name: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    contact_phone: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    contact_email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Address
    address: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Tracking URL template
    tracking_url_template: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
        comment="URL template with {awb} placeholder"
    )

    # AWB Generation
    awb_prefix: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    awb_sequence_start: Mapped[int] = mapped_column(Integer, default=1)
    awb_sequence_current: Mapped[int] = mapped_column(Integer, default=1)

    # Priority (for auto-selection)
    priority: Mapped[int] = mapped_column(Integer, default=100)

    # GST Details (for E-Way Bill)
    transporter_gstin: Mapped[Optional[str]] = mapped_column(
        String(15),
        nullable=True,
        comment="Transporter GSTIN for E-Way Bill"
    )
    transporter_id_nic: Mapped[Optional[str]] = mapped_column(
        String(15),
        nullable=True,
        comment="Transporter ID registered on NIC E-Way Bill portal"
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
    serviceability: Mapped[List["TransporterServiceability"]] = relationship(
        "TransporterServiceability",
        back_populates="transporter",
        cascade="all, delete-orphan"
    )
    shipments: Mapped[List["Shipment"]] = relationship(
        "Shipment",
        back_populates="transporter"
    )
    manifests: Mapped[List["Manifest"]] = relationship(
        "Manifest",
        back_populates="transporter"
    )

    def get_tracking_url(self, awb: str) -> Optional[str]:
        """Generate tracking URL for AWB number."""
        if self.tracking_url_template:
            return self.tracking_url_template.replace("{awb}", awb)
        return None

    def __repr__(self) -> str:
        return f"<Transporter(code='{self.code}', name='{self.name}')>"


class TransporterServiceability(Base):
    """
    Transporter serviceability mapping.
    Defines which pin codes a transporter can service.
    """
    __tablename__ = "transporter_serviceability"
    __table_args__ = (
        UniqueConstraint(
            "transporter_id", "origin_pincode", "destination_pincode",
            name="uq_transporter_serviceability"
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )

    transporter_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("transporters.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Pin codes
    origin_pincode: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
        index=True
    )
    destination_pincode: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
        index=True
    )

    # Service details
    is_serviceable: Mapped[bool] = mapped_column(Boolean, default=True)
    estimated_days: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    cod_available: Mapped[bool] = mapped_column(Boolean, default=True)
    prepaid_available: Mapped[bool] = mapped_column(Boolean, default=True)
    surface_available: Mapped[bool] = mapped_column(Boolean, default=True)
    express_available: Mapped[bool] = mapped_column(Boolean, default=False)

    # Rates for this route
    rate: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    cod_charge: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # State mapping
    origin_state: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    destination_state: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    origin_city: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    destination_city: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # Zone
    zone: Mapped[Optional[str]] = mapped_column(
        String(20),
        nullable=True,
        comment="Delivery zone: LOCAL, REGIONAL, NATIONAL, METRO"
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
    transporter: Mapped["Transporter"] = relationship(
        "Transporter",
        back_populates="serviceability"
    )

    def __repr__(self) -> str:
        return f"<TransporterServiceability({self.origin_pincode} -> {self.destination_pincode})>"
