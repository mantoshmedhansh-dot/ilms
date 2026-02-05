"""
Yard Management Models - Phase 6: Dock Scheduling & Yard Operations.

This module implements yard management operations:
- YardLocation: Parking spots, staging areas, dock doors
- DockDoor: Dock door configuration and scheduling
- DockAppointment: Carrier appointment scheduling
- YardMove: Trailer/vehicle movement tracking
- GateTransaction: Gate in/out logging
"""
import uuid
from datetime import datetime, timezone, date, time
from decimal import Decimal
from enum import Enum
from typing import TYPE_CHECKING, Optional, List, Dict, Any

from sqlalchemy import (
    String, Boolean, DateTime, ForeignKey, Integer, Text,
    Numeric, Date, Time, Index, UniqueConstraint
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.warehouse import Warehouse
    from app.models.user import User
    from app.models.transporter import Transporter


# ============================================================================
# ENUMS
# ============================================================================

class YardLocationType(str, Enum):
    """Types of yard locations."""
    DOCK_DOOR = "DOCK_DOOR"             # Loading/unloading dock
    STAGING_AREA = "STAGING_AREA"       # Staging area
    PARKING_SPOT = "PARKING_SPOT"       # Trailer parking
    DROP_YARD = "DROP_YARD"             # Drop trailer yard
    FUEL_STATION = "FUEL_STATION"       # Fueling area
    WEIGH_STATION = "WEIGH_STATION"     # Scale/weighbridge
    GATE = "GATE"                       # Entry/exit gate
    HOLDING_AREA = "HOLDING_AREA"       # Temporary holding


class YardLocationStatus(str, Enum):
    """Yard location availability status."""
    AVAILABLE = "AVAILABLE"
    OCCUPIED = "OCCUPIED"
    RESERVED = "RESERVED"
    MAINTENANCE = "MAINTENANCE"
    BLOCKED = "BLOCKED"


class DockDoorType(str, Enum):
    """Types of dock doors."""
    INBOUND = "INBOUND"                 # Receiving only
    OUTBOUND = "OUTBOUND"               # Shipping only
    DUAL = "DUAL"                       # Both inbound/outbound
    CROSS_DOCK = "CROSS_DOCK"           # Cross-docking


class AppointmentStatus(str, Enum):
    """Dock appointment status."""
    SCHEDULED = "SCHEDULED"
    CONFIRMED = "CONFIRMED"
    CHECKED_IN = "CHECKED_IN"
    AT_DOCK = "AT_DOCK"
    LOADING = "LOADING"
    UNLOADING = "UNLOADING"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"
    NO_SHOW = "NO_SHOW"
    RESCHEDULED = "RESCHEDULED"


class AppointmentType(str, Enum):
    """Type of dock appointment."""
    INBOUND = "INBOUND"                 # Receiving delivery
    OUTBOUND = "OUTBOUND"               # Shipping pickup
    CROSS_DOCK = "CROSS_DOCK"           # Cross-dock transfer
    LIVE_LOAD = "LIVE_LOAD"             # Live loading
    LIVE_UNLOAD = "LIVE_UNLOAD"         # Live unloading
    DROP_TRAILER = "DROP_TRAILER"       # Drop and hook
    PICK_TRAILER = "PICK_TRAILER"       # Pick up trailer


class YardMoveType(str, Enum):
    """Types of yard moves."""
    GATE_TO_DOCK = "GATE_TO_DOCK"       # From gate to dock
    DOCK_TO_GATE = "DOCK_TO_GATE"       # From dock to gate
    DOCK_TO_PARKING = "DOCK_TO_PARKING" # Dock to parking
    PARKING_TO_DOCK = "PARKING_TO_DOCK" # Parking to dock
    SPOT_TO_SPOT = "SPOT_TO_SPOT"       # Between parking spots
    INTERNAL = "INTERNAL"               # Internal move


class YardMoveStatus(str, Enum):
    """Status of yard move."""
    REQUESTED = "REQUESTED"
    ASSIGNED = "ASSIGNED"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


class GateTransactionType(str, Enum):
    """Type of gate transaction."""
    ENTRY = "ENTRY"
    EXIT = "EXIT"


class VehicleType(str, Enum):
    """Types of vehicles."""
    TRACTOR = "TRACTOR"                 # Truck tractor
    TRAILER = "TRAILER"                 # Trailer only
    STRAIGHT_TRUCK = "STRAIGHT_TRUCK"   # Box truck
    VAN = "VAN"                         # Cargo van
    FLATBED = "FLATBED"                 # Flatbed truck
    TANKER = "TANKER"                   # Tanker truck
    CONTAINER = "CONTAINER"             # Container
    COURIER = "COURIER"                 # Small courier
    PERSONAL = "PERSONAL"               # Personal vehicle


# ============================================================================
# MODELS
# ============================================================================

class YardLocation(Base):
    """
    Yard location definition.

    Defines all locations in the yard including docks, parking, staging.
    """
    __tablename__ = "yard_locations"
    __table_args__ = (
        UniqueConstraint('tenant_id', 'warehouse_id', 'location_code', name='uq_yard_location_code'),
        Index('ix_yard_locations_status', 'status'),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
        index=True
    )

    warehouse_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("warehouses.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Location Identity
    location_code: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        index=True,
        comment="e.g., DOCK-01, PARK-A1"
    )
    location_name: Mapped[str] = mapped_column(String(100), nullable=False)
    location_type: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        index=True
    )
    status: Mapped[str] = mapped_column(
        String(30),
        default="AVAILABLE",
        nullable=False,
        index=True
    )

    # Physical Properties
    zone: Mapped[Optional[str]] = mapped_column(
        String(30),
        nullable=True,
        comment="Yard zone grouping"
    )
    row: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    column: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    level: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Capacity
    max_length_feet: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(6, 1),
        nullable=True
    )
    max_width_feet: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(6, 1),
        nullable=True
    )
    max_height_feet: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(6, 1),
        nullable=True
    )
    max_weight_lbs: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(10, 2),
        nullable=True
    )

    # Current Occupancy
    current_vehicle_id: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        comment="License plate or trailer ID"
    )
    current_vehicle_type: Mapped[Optional[str]] = mapped_column(
        String(30),
        nullable=True
    )
    occupied_since: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )

    # GPS Coordinates
    latitude: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(10, 7),
        nullable=True
    )
    longitude: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(10, 7),
        nullable=True
    )

    # Capabilities
    has_power: Mapped[bool] = mapped_column(Boolean, default=False)
    has_refrigeration: Mapped[bool] = mapped_column(Boolean, default=False)
    has_fuel: Mapped[bool] = mapped_column(Boolean, default=False)
    is_hazmat_approved: Mapped[bool] = mapped_column(Boolean, default=False)

    # Configuration
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    sequence: Mapped[int] = mapped_column(Integer, default=0)

    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    warehouse: Mapped["Warehouse"] = relationship("Warehouse")


class DockDoor(Base):
    """
    Dock door configuration.

    Specific configuration for dock doors including equipment and scheduling.
    """
    __tablename__ = "dock_doors"
    __table_args__ = (
        UniqueConstraint('tenant_id', 'warehouse_id', 'door_number', name='uq_dock_door_number'),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
        index=True
    )

    warehouse_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("warehouses.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Link to yard location
    yard_location_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("yard_locations.id", ondelete="CASCADE"),
        nullable=False
    )

    # Door Identity
    door_number: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        index=True
    )
    door_name: Mapped[str] = mapped_column(String(100), nullable=False)
    door_type: Mapped[str] = mapped_column(
        String(30),
        default="DUAL",
        nullable=False
    )
    status: Mapped[str] = mapped_column(
        String(30),
        default="AVAILABLE",
        nullable=False,
        index=True
    )

    # Physical Properties
    door_height_feet: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(5, 1),
        nullable=True
    )
    door_width_feet: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(5, 1),
        nullable=True
    )
    dock_height_inches: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        comment="Dock height from ground"
    )

    # Equipment
    has_leveler: Mapped[bool] = mapped_column(Boolean, default=True)
    has_shelter: Mapped[bool] = mapped_column(Boolean, default=True)
    has_restraint: Mapped[bool] = mapped_column(Boolean, default=False)
    has_lights: Mapped[bool] = mapped_column(Boolean, default=True)
    leveler_capacity_lbs: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Linked Zone
    linked_zone_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("warehouse_zones.id", ondelete="SET NULL"),
        nullable=True,
        comment="Primary zone for this dock"
    )

    # Scheduling
    default_appointment_duration_mins: Mapped[int] = mapped_column(
        Integer,
        default=60
    )
    max_appointments_per_hour: Mapped[int] = mapped_column(Integer, default=1)

    # Operating Hours
    operating_start_time: Mapped[Optional[time]] = mapped_column(Time, nullable=True)
    operating_end_time: Mapped[Optional[time]] = mapped_column(Time, nullable=True)
    operating_days: Mapped[Optional[List[int]]] = mapped_column(
        JSONB,
        nullable=True,
        comment="Days of week (0=Mon, 6=Sun)"
    )

    # Current Assignment
    current_appointment_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        nullable=True
    )

    # Preferences
    preferred_carriers: Mapped[Optional[List[str]]] = mapped_column(
        JSONB,
        nullable=True
    )
    blocked_carriers: Mapped[Optional[List[str]]] = mapped_column(
        JSONB,
        nullable=True
    )

    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    warehouse: Mapped["Warehouse"] = relationship("Warehouse")
    yard_location: Mapped["YardLocation"] = relationship("YardLocation")


class DockAppointment(Base):
    """
    Dock appointment for carriers.

    Manages scheduling of inbound/outbound appointments.
    """
    __tablename__ = "dock_appointments"
    __table_args__ = (
        Index('ix_dock_appointments_date', 'appointment_date'),
        Index('ix_dock_appointments_status', 'status'),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
        index=True
    )

    warehouse_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("warehouses.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Appointment Identity
    appointment_number: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        unique=True,
        index=True
    )
    appointment_type: Mapped[str] = mapped_column(
        String(30),
        nullable=False
    )
    status: Mapped[str] = mapped_column(
        String(30),
        default="SCHEDULED",
        nullable=False,
        index=True
    )

    # Scheduling
    appointment_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
        index=True
    )
    scheduled_arrival: Mapped[time] = mapped_column(Time, nullable=False)
    scheduled_departure: Mapped[Optional[time]] = mapped_column(Time, nullable=True)
    duration_minutes: Mapped[int] = mapped_column(Integer, default=60)

    # Assigned Dock
    dock_door_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("dock_doors.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )

    # Carrier Info
    transporter_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("transporters.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    carrier_name: Mapped[str] = mapped_column(String(100), nullable=False)
    carrier_code: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)

    # Vehicle/Driver
    driver_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    driver_phone: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    vehicle_number: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    trailer_number: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    vehicle_type: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)

    # Shipment Reference
    reference_numbers: Mapped[Optional[List[str]]] = mapped_column(
        JSONB,
        nullable=True,
        comment="PO numbers, BOL numbers, etc."
    )
    shipment_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        nullable=True
    )
    purchase_order_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        nullable=True
    )

    # Load Details
    expected_pallets: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    expected_cases: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    expected_units: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    expected_weight_lbs: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(12, 2),
        nullable=True
    )

    # Actual Times
    actual_arrival: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )
    check_in_time: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )
    dock_time: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )
    load_start_time: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )
    load_end_time: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )
    departure_time: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )

    # Performance Metrics
    wait_time_minutes: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    dock_time_minutes: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    turnaround_time_minutes: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Status Tracking
    is_late: Mapped[bool] = mapped_column(Boolean, default=False)
    late_reason: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    no_show_reason: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    cancellation_reason: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)

    # Special Instructions
    special_instructions: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    handling_instructions: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Audit
    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )
    checked_in_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )

    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    warehouse: Mapped["Warehouse"] = relationship("Warehouse")
    dock_door: Mapped[Optional["DockDoor"]] = relationship("DockDoor")
    transporter: Mapped[Optional["Transporter"]] = relationship("Transporter")


class YardMove(Base):
    """
    Yard move request/tracking.

    Tracks movement of trailers/vehicles within the yard.
    """
    __tablename__ = "yard_moves"
    __table_args__ = (
        Index('ix_yard_moves_status', 'status'),
        Index('ix_yard_moves_created', 'created_at'),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
        index=True
    )

    warehouse_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("warehouses.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Move Identity
    move_number: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        unique=True,
        index=True
    )
    move_type: Mapped[str] = mapped_column(String(30), nullable=False)
    status: Mapped[str] = mapped_column(
        String(30),
        default="REQUESTED",
        nullable=False,
        index=True
    )
    priority: Mapped[int] = mapped_column(
        Integer,
        default=50,
        comment="Lower = higher priority"
    )

    # Locations
    from_location_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("yard_locations.id", ondelete="RESTRICT"),
        nullable=False
    )
    to_location_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("yard_locations.id", ondelete="RESTRICT"),
        nullable=False
    )

    # Vehicle
    vehicle_id: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="Trailer/vehicle identifier"
    )
    vehicle_type: Mapped[str] = mapped_column(String(30), nullable=False)

    # Related Appointment
    appointment_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("dock_appointments.id", ondelete="SET NULL"),
        nullable=True
    )

    # Assignment
    assigned_to: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        comment="Yard jockey"
    )
    assigned_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )

    # Timing
    requested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc)
    )
    started_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )
    estimated_duration_mins: Mapped[int] = mapped_column(Integer, default=15)
    actual_duration_mins: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Cancellation
    cancelled_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )
    cancellation_reason: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)

    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    warehouse: Mapped["Warehouse"] = relationship("Warehouse")
    from_location: Mapped["YardLocation"] = relationship(
        "YardLocation",
        foreign_keys=[from_location_id]
    )
    to_location: Mapped["YardLocation"] = relationship(
        "YardLocation",
        foreign_keys=[to_location_id]
    )
    appointment: Mapped[Optional["DockAppointment"]] = relationship("DockAppointment")
    assigned_user: Mapped[Optional["User"]] = relationship("User")


class GateTransaction(Base):
    """
    Gate in/out transaction log.

    Records all gate entries and exits.
    """
    __tablename__ = "gate_transactions"
    __table_args__ = (
        Index('ix_gate_transactions_time', 'transaction_time'),
        Index('ix_gate_transactions_vehicle', 'vehicle_number'),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
        index=True
    )

    warehouse_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("warehouses.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Transaction Identity
    transaction_number: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        unique=True,
        index=True
    )
    transaction_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        comment="ENTRY or EXIT"
    )

    # Gate Info
    gate_location_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("yard_locations.id", ondelete="SET NULL"),
        nullable=True
    )
    gate_name: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    # Vehicle Info
    vehicle_number: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True
    )
    trailer_number: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    vehicle_type: Mapped[str] = mapped_column(String(30), nullable=False)

    # Driver Info
    driver_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    driver_license: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    driver_phone: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)

    # Carrier Info
    carrier_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    transporter_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("transporters.id", ondelete="SET NULL"),
        nullable=True
    )

    # Related Appointment
    appointment_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("dock_appointments.id", ondelete="SET NULL"),
        nullable=True
    )

    # Assigned Location (on entry)
    assigned_location_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("yard_locations.id", ondelete="SET NULL"),
        nullable=True
    )

    # Seal Info
    seal_number: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    seal_intact: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    new_seal_number: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        comment="New seal applied on exit"
    )

    # Load Info
    is_loaded: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    load_description: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)

    # Timing
    transaction_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True
    )

    # Matching Entry (for exit transactions)
    entry_transaction_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
        comment="Link to entry for exit transactions"
    )

    # Security
    processed_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )
    id_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    inspection_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Photo Evidence
    photos: Mapped[Optional[List[str]]] = mapped_column(
        JSONB,
        nullable=True,
        comment="URLs to photos"
    )

    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    warehouse: Mapped["Warehouse"] = relationship("Warehouse")
    gate_location: Mapped[Optional["YardLocation"]] = relationship(
        "YardLocation",
        foreign_keys=[gate_location_id]
    )
    assigned_location: Mapped[Optional["YardLocation"]] = relationship(
        "YardLocation",
        foreign_keys=[assigned_location_id]
    )
    transporter: Mapped[Optional["Transporter"]] = relationship("Transporter")
    appointment: Mapped[Optional["DockAppointment"]] = relationship("DockAppointment")
