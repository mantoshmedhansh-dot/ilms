"""Rate Card models for logistics pricing across D2C, B2B, and FTL segments."""
import uuid
from datetime import datetime, date, timezone
from decimal import Decimal
from enum import Enum
from typing import TYPE_CHECKING, Optional, List

from sqlalchemy import (
    String, Boolean, DateTime, Date, ForeignKey, Integer, Text,
    Numeric, UniqueConstraint, Index
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.transporter import Transporter


# ============================================
# ENUMS
# ============================================

class D2CServiceType(str, Enum):
    """D2C service type enumeration."""
    STANDARD = "STANDARD"
    EXPRESS = "EXPRESS"
    ECONOMY = "ECONOMY"
    SAME_DAY = "SAME_DAY"
    NEXT_DAY = "NEXT_DAY"


# Alias for backward compatibility
ServiceType = D2CServiceType


class ZoneCode(str, Enum):
    """Zone classification for delivery."""
    A = "A"  # Local / Within City
    B = "B"  # Within State
    C = "C"  # Regional / Adjacent States
    D = "D"  # National Metro
    E = "E"  # Special (NE / J&K / Remote)
    F = "F"  # Remote / ODA


class SurchargeType(str, Enum):
    """Types of surcharges applicable."""
    FUEL = "FUEL"
    COD_HANDLING = "COD_HANDLING"
    COD_PERCENTAGE = "COD_PERCENTAGE"
    RTO = "RTO"
    ODA = "ODA"  # Out of Delivery Area
    INSURANCE = "INSURANCE"
    HANDLING = "HANDLING"
    DOCKET = "DOCKET"
    LOADING = "LOADING"
    UNLOADING = "UNLOADING"
    POD_COPY = "POD_COPY"
    DETENTION = "DETENTION"
    DEMURRAGE = "DEMURRAGE"


class CalculationType(str, Enum):
    """How the charge is calculated."""
    PERCENTAGE = "PERCENTAGE"
    FIXED = "FIXED"
    PER_KG = "PER_KG"
    PER_UNIT = "PER_UNIT"
    PER_PKG = "PER_PKG"


class B2BServiceType(str, Enum):
    """B2B service type enumeration."""
    LTL = "LTL"  # Less Than Truckload
    PTL = "PTL"  # Part Truck Load
    PARCEL = "PARCEL"


class TransportMode(str, Enum):
    """Mode of transport."""
    SURFACE = "SURFACE"
    AIR = "AIR"
    RAIL = "RAIL"
    MULTIMODAL = "MULTIMODAL"


class B2BRateType(str, Enum):
    """B2B rate calculation type."""
    PER_KG = "PER_KG"
    PER_CFT = "PER_CFT"  # Per Cubic Feet
    FLAT_RATE = "FLAT_RATE"


class FTLRateType(str, Enum):
    """FTL rate type enumeration."""
    CONTRACT = "CONTRACT"
    SPOT = "SPOT"
    TENDER = "TENDER"


class VehicleCategory(str, Enum):
    """Vehicle category for FTL."""
    MINI = "MINI"      # < 2 Tons
    SMALL = "SMALL"    # 2-5 Tons
    MEDIUM = "MEDIUM"  # 5-10 Tons
    LARGE = "LARGE"    # 10-20 Tons
    HEAVY = "HEAVY"    # 20+ Tons
    TRAILER = "TRAILER"


# ============================================
# D2C RATE CARDS (Courier Partners)
# ============================================

class D2CRateCard(Base):
    """
    D2C Rate Card for courier partners.
    Contains weight slabs and surcharges for last-mile delivery pricing.
    """
    __tablename__ = "d2c_rate_cards"
    __table_args__ = (
        UniqueConstraint(
            "transporter_id", "code", "effective_from",
            name="uq_d2c_rate_card"
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )

    # Transporter Reference
    transporter_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("transporters.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Identification
    code: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
        comment="Unique rate card code e.g., DELHIVERY-STD-2024"
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Service Type
    service_type: Mapped[str] = mapped_column(
        String(50),
        default="STANDARD",
        nullable=False,
        comment="STANDARD, EXPRESS, ECONOMY, SAME_DAY, NEXT_DAY"
    )

    # Zone Type (how zones are defined)
    zone_type: Mapped[str] = mapped_column(
        String(20),
        default="DISTANCE",
        comment="DISTANCE (A-F), REGIONAL (N/S/E/W), PINCODE_RANGE"
    )

    # Validity Period
    effective_from: Mapped[date] = mapped_column(Date, nullable=False)
    effective_to: Mapped[Optional[date]] = mapped_column(Date, nullable=True)

    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_default: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        comment="Default rate card for this transporter"
    )

    # Audit
    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )
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
        backref="d2c_rate_cards"
    )
    weight_slabs: Mapped[List["D2CWeightSlab"]] = relationship(
        "D2CWeightSlab",
        back_populates="rate_card",
        cascade="all, delete-orphan"
    )
    surcharges: Mapped[List["D2CSurcharge"]] = relationship(
        "D2CSurcharge",
        back_populates="rate_card",
        cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<D2CRateCard(code='{self.code}', transporter_id='{self.transporter_id}')>"


class D2CWeightSlab(Base):
    """
    Weight-based rate slabs for D2C shipments.
    Defines pricing for different weight ranges per zone.
    """
    __tablename__ = "d2c_weight_slabs"
    __table_args__ = (
        UniqueConstraint(
            "rate_card_id", "zone", "min_weight_kg",
            name="uq_d2c_weight_slab"
        ),
        Index("idx_d2c_weight_slab_lookup", "rate_card_id", "zone", "min_weight_kg"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )

    rate_card_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("d2c_rate_cards.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Zone (A-F or custom zone code)
    zone: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        comment="Zone code: A, B, C, D, E, F"
    )

    # Weight Range (in kg)
    min_weight_kg: Mapped[Decimal] = mapped_column(
        Numeric(10, 3),
        default=0,
        nullable=False
    )
    max_weight_kg: Mapped[Decimal] = mapped_column(
        Numeric(10, 3),
        nullable=False
    )

    # Pricing
    base_rate: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        nullable=False,
        comment="Base rate for this slab in INR"
    )
    additional_rate_per_kg: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        default=0,
        comment="Rate per additional kg beyond base weight"
    )
    additional_weight_unit_kg: Mapped[Decimal] = mapped_column(
        Numeric(10, 3),
        default=Decimal("0.5"),
        comment="Weight unit for additional charge (0.5kg, 1kg)"
    )

    # Payment Mode Availability
    cod_available: Mapped[bool] = mapped_column(Boolean, default=True)
    prepaid_available: Mapped[bool] = mapped_column(Boolean, default=True)

    # SLA (Estimated Delivery)
    estimated_days_min: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    estimated_days_max: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    # Relationship
    rate_card: Mapped["D2CRateCard"] = relationship(
        "D2CRateCard",
        back_populates="weight_slabs"
    )

    def __repr__(self) -> str:
        return f"<D2CWeightSlab(zone='{self.zone}', weight={self.min_weight_kg}-{self.max_weight_kg}kg)>"


class D2CSurcharge(Base):
    """
    Surcharges and additional charges for D2C shipments.
    Includes fuel surcharge, COD charges, ODA, RTO, etc.
    """
    __tablename__ = "d2c_surcharges"
    __table_args__ = (
        UniqueConstraint(
            "rate_card_id", "surcharge_type", "zone",
            name="uq_d2c_surcharge"
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )

    rate_card_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("d2c_rate_cards.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    surcharge_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="FUEL, COD_HANDLING, COD_PERCENTAGE, RTO, ODA, INSURANCE, HANDLING, DOCKET, LOADING, UNLOADING, POD_COPY, DETENTION, DEMURRAGE"
    )

    # Calculation Method
    calculation_type: Mapped[str] = mapped_column(
        String(50),
        default="PERCENTAGE",
        nullable=False,
        comment="PERCENTAGE, FIXED, PER_KG, PER_UNIT, PER_PKG"
    )

    # Value
    value: Mapped[Decimal] = mapped_column(
        Numeric(10, 4),
        nullable=False,
        comment="Value based on calculation_type (percentage or fixed amount)"
    )
    min_amount: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(10, 2),
        nullable=True,
        comment="Minimum charge amount"
    )
    max_amount: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(10, 2),
        nullable=True,
        comment="Maximum charge amount"
    )

    # Applicability
    applies_to_cod: Mapped[bool] = mapped_column(Boolean, default=True)
    applies_to_prepaid: Mapped[bool] = mapped_column(Boolean, default=True)

    # Zone specific (NULL means all zones)
    zone: Mapped[Optional[str]] = mapped_column(
        String(20),
        nullable=True,
        comment="Specific zone or NULL for all zones"
    )

    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    effective_from: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    effective_to: Mapped[Optional[date]] = mapped_column(Date, nullable=True)

    # Relationship
    rate_card: Mapped["D2CRateCard"] = relationship(
        "D2CRateCard",
        back_populates="surcharges"
    )

    def __repr__(self) -> str:
        return f"<D2CSurcharge(type='{self.surcharge_type}', value={self.value})>"


# ============================================
# ZONE MAPPINGS
# ============================================

class ZoneMapping(Base):
    """
    Pincode to Zone mapping for delivery pricing.
    Maps origin-destination pairs to zone codes (A-F).
    """
    __tablename__ = "zone_mappings"
    __table_args__ = (
        UniqueConstraint(
            "origin_pincode", "destination_pincode",
            name="uq_zone_mapping"
        ),
        Index("idx_zone_mapping_dest", "destination_pincode"),
        Index("idx_zone_mapping_origin", "origin_pincode"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )

    # Origin
    origin_pincode: Mapped[Optional[str]] = mapped_column(
        String(10),
        nullable=True,
        comment="Origin pincode (NULL for state-level mapping)"
    )
    origin_city: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    origin_state: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # Destination
    destination_pincode: Mapped[Optional[str]] = mapped_column(
        String(10),
        nullable=True,
        comment="Destination pincode (NULL for state-level mapping)"
    )
    destination_city: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    destination_state: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # Zone Classification
    zone: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        comment="Zone: A (Local), B (State), C (Regional), D (Metro), E (NE/J&K), F (Remote)"
    )

    # Additional Info
    distance_km: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    is_oda: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        comment="Out of Delivery Area flag"
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    def __repr__(self) -> str:
        return f"<ZoneMapping({self.origin_pincode} -> {self.destination_pincode} = Zone {self.zone})>"


# ============================================
# B2B RATE CARDS (LTL/PTL)
# ============================================

class B2BRateCard(Base):
    """
    B2B Rate Card for LTL/PTL shipments.
    Contains lane rates and additional charges for business shipments.
    """
    __tablename__ = "b2b_rate_cards"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )

    # Transporter Reference
    transporter_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("transporters.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Identification
    code: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Service Type
    service_type: Mapped[str] = mapped_column(
        String(50),
        default="LTL",
        nullable=False,
        comment="LTL, PTL, PARCEL"
    )

    # Transport Mode
    transport_mode: Mapped[str] = mapped_column(
        String(50),
        default="SURFACE",
        nullable=False,
        comment="SURFACE, AIR, RAIL, MULTIMODAL"
    )

    # Minimum Requirements
    min_chargeable_weight_kg: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        default=Decimal("25"),
        comment="Minimum chargeable weight in kg"
    )
    min_invoice_value: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(12, 2),
        nullable=True
    )

    # Validity
    effective_from: Mapped[date] = mapped_column(Date, nullable=False)
    effective_to: Mapped[Optional[date]] = mapped_column(Date, nullable=True)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )
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
        backref="b2b_rate_cards"
    )
    rate_slabs: Mapped[List["B2BRateSlab"]] = relationship(
        "B2BRateSlab",
        back_populates="rate_card",
        cascade="all, delete-orphan"
    )
    additional_charges: Mapped[List["B2BAdditionalCharge"]] = relationship(
        "B2BAdditionalCharge",
        back_populates="rate_card",
        cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<B2BRateCard(code='{self.code}', type='{self.service_type}')>"


class B2BRateSlab(Base):
    """
    Rate slabs for B2B shipments.
    Defines pricing for different weight/volume ranges per lane or zone.
    """
    __tablename__ = "b2b_rate_slabs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )

    rate_card_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("b2b_rate_cards.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Lane Definition (Origin-Destination)
    origin_city: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    origin_state: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    destination_city: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    destination_state: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # OR Zone-based (alternative to lane)
    zone: Mapped[Optional[str]] = mapped_column(
        String(20),
        nullable=True,
        comment="Zone code if using zone-based pricing"
    )

    # Weight Slab
    min_weight_kg: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        default=0,
        nullable=False
    )
    max_weight_kg: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(10, 2),
        nullable=True,
        comment="NULL means unlimited"
    )

    # Rate Structure
    rate_type: Mapped[str] = mapped_column(
        String(50),
        default="PER_KG",
        nullable=False,
        comment="PER_KG, PER_CFT, FLAT_RATE"
    )
    rate: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        nullable=False,
        comment="Rate per unit (kg/cft/flat)"
    )
    min_charge: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(10, 2),
        nullable=True,
        comment="Minimum charge for this slab"
    )

    # Transit Time
    transit_days_min: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    transit_days_max: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    # Relationship
    rate_card: Mapped["B2BRateCard"] = relationship(
        "B2BRateCard",
        back_populates="rate_slabs"
    )

    def __repr__(self) -> str:
        if self.origin_city and self.destination_city:
            return f"<B2BRateSlab({self.origin_city} -> {self.destination_city}, {self.rate}/kg)>"
        return f"<B2BRateSlab(zone={self.zone}, {self.rate}/kg)>"


class B2BAdditionalCharge(Base):
    """
    Additional charges for B2B shipments.
    Includes handling, docket, loading/unloading, etc.
    """
    __tablename__ = "b2b_additional_charges"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )

    rate_card_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("b2b_rate_cards.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    charge_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="FUEL, COD_HANDLING, COD_PERCENTAGE, RTO, ODA, INSURANCE, HANDLING, DOCKET, LOADING, UNLOADING, POD_COPY, DETENTION, DEMURRAGE"
    )

    calculation_type: Mapped[str] = mapped_column(
        String(50),
        default="FIXED",
        nullable=False,
        comment="PERCENTAGE, FIXED, PER_KG, PER_UNIT, PER_PKG"
    )

    value: Mapped[Decimal] = mapped_column(
        Numeric(10, 4),
        nullable=False
    )
    per_unit: Mapped[Optional[str]] = mapped_column(
        String(20),
        nullable=True,
        comment="PER_KG, PER_PKG, PER_INVOICE"
    )

    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Relationship
    rate_card: Mapped["B2BRateCard"] = relationship(
        "B2BRateCard",
        back_populates="additional_charges"
    )

    def __repr__(self) -> str:
        return f"<B2BAdditionalCharge(type='{self.charge_type}', value={self.value})>"


# ============================================
# FTL RATE CARDS (Full Truck Load)
# ============================================

class FTLRateCard(Base):
    """
    FTL Rate Card for full truck load shipments.
    Contains lane rates for different vehicle types.
    """
    __tablename__ = "ftl_rate_cards"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )

    # Transporter Reference (optional - can be market rates)
    transporter_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("transporters.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )

    # Identification
    code: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Rate Type
    rate_type: Mapped[str] = mapped_column(
        String(50),
        default="CONTRACT",
        nullable=False,
        comment="CONTRACT, SPOT, TENDER"
    )

    # Payment Terms
    payment_terms: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        comment="30 DAYS, ADVANCE, ON_DELIVERY"
    )

    # Validity
    effective_from: Mapped[date] = mapped_column(Date, nullable=False)
    effective_to: Mapped[Optional[date]] = mapped_column(Date, nullable=True)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )
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
    transporter: Mapped[Optional["Transporter"]] = relationship(
        "Transporter",
        backref="ftl_rate_cards"
    )
    lane_rates: Mapped[List["FTLLaneRate"]] = relationship(
        "FTLLaneRate",
        back_populates="rate_card",
        cascade="all, delete-orphan"
    )
    additional_charges: Mapped[List["FTLAdditionalCharge"]] = relationship(
        "FTLAdditionalCharge",
        back_populates="rate_card",
        cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<FTLRateCard(code='{self.code}', type='{self.rate_type}')>"


class FTLLaneRate(Base):
    """
    Lane-to-lane rates for FTL shipments.
    Point-to-point pricing by vehicle type.
    """
    __tablename__ = "ftl_lane_rates"
    __table_args__ = (
        UniqueConstraint(
            "rate_card_id", "origin_city", "destination_city", "vehicle_type",
            name="uq_ftl_lane_rate"
        ),
        Index("idx_ftl_lane_lookup", "rate_card_id", "origin_city", "destination_city"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )

    rate_card_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("ftl_rate_cards.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Origin
    origin_city: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    origin_state: Mapped[str] = mapped_column(String(100), nullable=False)
    origin_pincode: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)

    # Destination
    destination_city: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    destination_state: Mapped[str] = mapped_column(String(100), nullable=False)
    destination_pincode: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)

    # Distance
    distance_km: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Vehicle Type
    vehicle_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="TATA_ACE, EICHER_14FT, CONTAINER_20FT, etc."
    )
    vehicle_capacity_tons: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(10, 2),
        nullable=True
    )
    vehicle_capacity_cft: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Pricing
    rate_per_trip: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
        comment="Fixed rate per trip in INR"
    )
    rate_per_km: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(10, 2),
        nullable=True,
        comment="Alternative rate per KM"
    )

    # Minimum Guarantee
    min_running_km: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        comment="Minimum guaranteed KM"
    )
    extra_km_rate: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(10, 2),
        nullable=True,
        comment="Rate for extra KM beyond minimum"
    )

    # Transit Time
    transit_hours: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Multi-Point Charges
    loading_points_included: Mapped[int] = mapped_column(Integer, default=1)
    unloading_points_included: Mapped[int] = mapped_column(Integer, default=1)
    extra_point_charge: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(10, 2),
        nullable=True
    )

    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    # Relationship
    rate_card: Mapped["FTLRateCard"] = relationship(
        "FTLRateCard",
        back_populates="lane_rates"
    )

    def __repr__(self) -> str:
        return f"<FTLLaneRate({self.origin_city} -> {self.destination_city}, {self.vehicle_type})>"


class FTLAdditionalCharge(Base):
    """
    Additional charges for FTL shipments.
    Includes detention, halt, toll, driver bata, etc.
    """
    __tablename__ = "ftl_additional_charges"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )

    rate_card_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("ftl_rate_cards.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    charge_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="LOADING_DETENTION, UNLOADING_DETENTION, OVERNIGHT_HALT, TOLL, DRIVER_BATA, EMPTY_RETURN"
    )

    calculation_type: Mapped[str] = mapped_column(
        String(50),
        default="FIXED",
        nullable=False,
        comment="PERCENTAGE, FIXED, PER_KG, PER_UNIT, PER_PKG"
    )

    value: Mapped[Decimal] = mapped_column(
        Numeric(10, 4),
        nullable=False
    )
    per_unit: Mapped[Optional[str]] = mapped_column(
        String(20),
        nullable=True,
        comment="PER_HOUR, PER_DAY, PER_TRIP"
    )

    # Free hours before charge applies
    free_hours: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        comment="Free hours for detention charges"
    )

    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Relationship
    rate_card: Mapped["FTLRateCard"] = relationship(
        "FTLRateCard",
        back_populates="additional_charges"
    )

    def __repr__(self) -> str:
        return f"<FTLAdditionalCharge(type='{self.charge_type}', value={self.value})>"


class FTLVehicleType(Base):
    """
    Master table for FTL vehicle types.
    Defines dimensions and capacity for different vehicle categories.
    """
    __tablename__ = "ftl_vehicle_types"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )

    code: Mapped[str] = mapped_column(
        String(30),
        unique=True,
        nullable=False,
        comment="TATA_ACE, EICHER_14FT, CONTAINER_20FT, etc."
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)

    # Dimensions (in feet)
    length_ft: Mapped[Optional[Decimal]] = mapped_column(Numeric(6, 2), nullable=True)
    width_ft: Mapped[Optional[Decimal]] = mapped_column(Numeric(6, 2), nullable=True)
    height_ft: Mapped[Optional[Decimal]] = mapped_column(Numeric(6, 2), nullable=True)

    # Capacity
    capacity_tons: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2), nullable=True)
    capacity_cft: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Category
    category: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        comment="MINI, SMALL, MEDIUM, LARGE, HEAVY, TRAILER"
    )

    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    def __repr__(self) -> str:
        return f"<FTLVehicleType(code='{self.code}', capacity={self.capacity_tons}T)>"


# ============================================
# CARRIER PERFORMANCE TRACKING
# ============================================

class CarrierPerformance(Base):
    """
    Carrier performance metrics for scoring and analytics.
    Tracks delivery performance, RTO rates, damage rates, etc.
    """
    __tablename__ = "carrier_performance"
    __table_args__ = (
        UniqueConstraint(
            "transporter_id", "period_start", "zone",
            name="uq_carrier_performance"
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

    # Time Period
    period_start: Mapped[date] = mapped_column(Date, nullable=False)
    period_end: Mapped[date] = mapped_column(Date, nullable=False)

    # Zone/Lane (optional for granular tracking)
    zone: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    origin_city: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    destination_city: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # Volume Metrics
    total_shipments: Mapped[int] = mapped_column(Integer, default=0)
    total_weight_kg: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0)
    total_revenue: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0)

    # Performance Metrics
    on_time_delivery_count: Mapped[int] = mapped_column(Integer, default=0)
    on_time_pickup_count: Mapped[int] = mapped_column(Integer, default=0)
    total_delivered: Mapped[int] = mapped_column(Integer, default=0)

    # Issue Metrics
    rto_count: Mapped[int] = mapped_column(Integer, default=0)
    damage_count: Mapped[int] = mapped_column(Integer, default=0)
    lost_count: Mapped[int] = mapped_column(Integer, default=0)
    ndr_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        comment="Non-Delivery Report count"
    )

    # Derived Scores (0-100)
    delivery_score: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 2), nullable=True)
    pickup_score: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 2), nullable=True)
    rto_score: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 2), nullable=True)
    damage_score: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 2), nullable=True)

    # Overall Score (weighted average)
    overall_score: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 2), nullable=True)

    # Trend
    score_trend: Mapped[Optional[str]] = mapped_column(
        String(10),
        nullable=True,
        comment="UP, DOWN, STABLE"
    )

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

    # Relationship
    transporter: Mapped["Transporter"] = relationship(
        "Transporter",
        backref="performance_records"
    )

    def __repr__(self) -> str:
        return f"<CarrierPerformance(transporter_id='{self.transporter_id}', score={self.overall_score})>"
