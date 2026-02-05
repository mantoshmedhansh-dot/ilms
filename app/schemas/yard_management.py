"""
Yard Management Schemas - Phase 6: Dock Scheduling & Yard Operations.

Pydantic schemas for yard management including:
- Yard locations
- Dock doors
- Appointments
- Yard moves
- Gate transactions
"""
from datetime import datetime, date, time
from decimal import Decimal
from typing import Optional, List, Dict, Any
from uuid import UUID

from pydantic import BaseModel, Field

from app.models.yard_management import (
    YardLocationType, YardLocationStatus, DockDoorType,
    AppointmentStatus, AppointmentType, YardMoveType,
    YardMoveStatus, GateTransactionType, VehicleType
)


# ============================================================================
# YARD LOCATION SCHEMAS
# ============================================================================

class YardLocationBase(BaseModel):
    """Base schema for yard location."""
    location_code: str = Field(..., max_length=30)
    location_name: str = Field(..., max_length=100)
    location_type: YardLocationType
    zone: Optional[str] = Field(None, max_length=30)
    row: Optional[str] = Field(None, max_length=10)
    column: Optional[str] = Field(None, max_length=10)
    level: Optional[int] = None
    max_length_feet: Optional[Decimal] = None
    max_width_feet: Optional[Decimal] = None
    max_height_feet: Optional[Decimal] = None
    max_weight_lbs: Optional[Decimal] = None
    latitude: Optional[Decimal] = None
    longitude: Optional[Decimal] = None
    has_power: bool = False
    has_refrigeration: bool = False
    has_fuel: bool = False
    is_hazmat_approved: bool = False
    sequence: int = 0
    notes: Optional[str] = None


class YardLocationCreate(YardLocationBase):
    """Schema for creating yard location."""
    warehouse_id: UUID


class YardLocationUpdate(BaseModel):
    """Schema for updating yard location."""
    location_name: Optional[str] = Field(None, max_length=100)
    status: Optional[YardLocationStatus] = None
    zone: Optional[str] = Field(None, max_length=30)
    max_length_feet: Optional[Decimal] = None
    max_width_feet: Optional[Decimal] = None
    max_height_feet: Optional[Decimal] = None
    max_weight_lbs: Optional[Decimal] = None
    latitude: Optional[Decimal] = None
    longitude: Optional[Decimal] = None
    has_power: Optional[bool] = None
    has_refrigeration: Optional[bool] = None
    has_fuel: Optional[bool] = None
    is_hazmat_approved: Optional[bool] = None
    is_active: Optional[bool] = None
    notes: Optional[str] = None


class YardLocationResponse(YardLocationBase):
    """Response schema for yard location."""
    id: UUID
    tenant_id: UUID
    warehouse_id: UUID
    status: YardLocationStatus
    current_vehicle_id: Optional[str] = None
    current_vehicle_type: Optional[str] = None
    occupied_since: Optional[datetime] = None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ============================================================================
# DOCK DOOR SCHEMAS
# ============================================================================

class DockDoorBase(BaseModel):
    """Base schema for dock door."""
    door_number: str = Field(..., max_length=20)
    door_name: str = Field(..., max_length=100)
    door_type: DockDoorType = DockDoorType.DUAL
    door_height_feet: Optional[Decimal] = None
    door_width_feet: Optional[Decimal] = None
    dock_height_inches: Optional[int] = None
    has_leveler: bool = True
    has_shelter: bool = True
    has_restraint: bool = False
    has_lights: bool = True
    leveler_capacity_lbs: Optional[int] = None
    default_appointment_duration_mins: int = 60
    max_appointments_per_hour: int = 1
    operating_start_time: Optional[time] = None
    operating_end_time: Optional[time] = None
    operating_days: Optional[List[int]] = None
    preferred_carriers: Optional[List[str]] = None
    blocked_carriers: Optional[List[str]] = None
    notes: Optional[str] = None


class DockDoorCreate(DockDoorBase):
    """Schema for creating dock door."""
    warehouse_id: UUID
    yard_location_id: UUID
    linked_zone_id: Optional[UUID] = None


class DockDoorUpdate(BaseModel):
    """Schema for updating dock door."""
    door_name: Optional[str] = Field(None, max_length=100)
    door_type: Optional[DockDoorType] = None
    status: Optional[YardLocationStatus] = None
    door_height_feet: Optional[Decimal] = None
    door_width_feet: Optional[Decimal] = None
    dock_height_inches: Optional[int] = None
    has_leveler: Optional[bool] = None
    has_shelter: Optional[bool] = None
    has_restraint: Optional[bool] = None
    has_lights: Optional[bool] = None
    leveler_capacity_lbs: Optional[int] = None
    linked_zone_id: Optional[UUID] = None
    default_appointment_duration_mins: Optional[int] = None
    max_appointments_per_hour: Optional[int] = None
    operating_start_time: Optional[time] = None
    operating_end_time: Optional[time] = None
    operating_days: Optional[List[int]] = None
    preferred_carriers: Optional[List[str]] = None
    blocked_carriers: Optional[List[str]] = None
    is_active: Optional[bool] = None
    notes: Optional[str] = None


class DockDoorResponse(DockDoorBase):
    """Response schema for dock door."""
    id: UUID
    tenant_id: UUID
    warehouse_id: UUID
    yard_location_id: UUID
    linked_zone_id: Optional[UUID] = None
    status: str
    current_appointment_id: Optional[UUID] = None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ============================================================================
# DOCK APPOINTMENT SCHEMAS
# ============================================================================

class DockAppointmentBase(BaseModel):
    """Base schema for dock appointment."""
    appointment_type: AppointmentType
    appointment_date: date
    scheduled_arrival: time
    scheduled_departure: Optional[time] = None
    duration_minutes: int = 60
    carrier_name: str = Field(..., max_length=100)
    carrier_code: Optional[str] = Field(None, max_length=30)
    driver_name: Optional[str] = Field(None, max_length=100)
    driver_phone: Optional[str] = Field(None, max_length=20)
    vehicle_number: Optional[str] = Field(None, max_length=50)
    trailer_number: Optional[str] = Field(None, max_length=50)
    vehicle_type: Optional[VehicleType] = None
    reference_numbers: Optional[List[str]] = None
    expected_pallets: Optional[int] = None
    expected_cases: Optional[int] = None
    expected_units: Optional[int] = None
    expected_weight_lbs: Optional[Decimal] = None
    special_instructions: Optional[str] = None
    handling_instructions: Optional[str] = None
    notes: Optional[str] = None


class DockAppointmentCreate(DockAppointmentBase):
    """Schema for creating dock appointment."""
    warehouse_id: UUID
    dock_door_id: Optional[UUID] = None
    transporter_id: Optional[UUID] = None
    shipment_id: Optional[UUID] = None
    purchase_order_id: Optional[UUID] = None


class DockAppointmentUpdate(BaseModel):
    """Schema for updating dock appointment."""
    appointment_date: Optional[date] = None
    scheduled_arrival: Optional[time] = None
    scheduled_departure: Optional[time] = None
    duration_minutes: Optional[int] = None
    dock_door_id: Optional[UUID] = None
    driver_name: Optional[str] = Field(None, max_length=100)
    driver_phone: Optional[str] = Field(None, max_length=20)
    vehicle_number: Optional[str] = Field(None, max_length=50)
    trailer_number: Optional[str] = Field(None, max_length=50)
    reference_numbers: Optional[List[str]] = None
    expected_pallets: Optional[int] = None
    expected_cases: Optional[int] = None
    expected_units: Optional[int] = None
    expected_weight_lbs: Optional[Decimal] = None
    special_instructions: Optional[str] = None
    handling_instructions: Optional[str] = None
    notes: Optional[str] = None


class AppointmentCheckIn(BaseModel):
    """Schema for checking in an appointment."""
    vehicle_number: str = Field(..., max_length=50)
    trailer_number: Optional[str] = Field(None, max_length=50)
    driver_name: Optional[str] = Field(None, max_length=100)
    driver_phone: Optional[str] = Field(None, max_length=20)
    assigned_location_id: Optional[UUID] = None


class AppointmentStatusUpdate(BaseModel):
    """Schema for updating appointment status."""
    status: AppointmentStatus
    reason: Optional[str] = Field(None, max_length=200)
    dock_door_id: Optional[UUID] = None


class DockAppointmentResponse(DockAppointmentBase):
    """Response schema for dock appointment."""
    id: UUID
    tenant_id: UUID
    warehouse_id: UUID
    appointment_number: str
    status: AppointmentStatus
    dock_door_id: Optional[UUID] = None
    transporter_id: Optional[UUID] = None
    shipment_id: Optional[UUID] = None
    purchase_order_id: Optional[UUID] = None
    actual_arrival: Optional[datetime] = None
    check_in_time: Optional[datetime] = None
    dock_time: Optional[datetime] = None
    load_start_time: Optional[datetime] = None
    load_end_time: Optional[datetime] = None
    departure_time: Optional[datetime] = None
    wait_time_minutes: Optional[int] = None
    dock_time_minutes: Optional[int] = None
    turnaround_time_minutes: Optional[int] = None
    is_late: bool
    late_reason: Optional[str] = None
    created_by: Optional[UUID] = None
    checked_in_by: Optional[UUID] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ============================================================================
# YARD MOVE SCHEMAS
# ============================================================================

class YardMoveBase(BaseModel):
    """Base schema for yard move."""
    move_type: YardMoveType
    vehicle_id: str = Field(..., max_length=50)
    vehicle_type: VehicleType
    priority: int = Field(50, ge=0, le=100)
    estimated_duration_mins: int = 15
    notes: Optional[str] = None


class YardMoveCreate(YardMoveBase):
    """Schema for creating yard move."""
    warehouse_id: UUID
    from_location_id: UUID
    to_location_id: UUID
    appointment_id: Optional[UUID] = None


class YardMoveUpdate(BaseModel):
    """Schema for updating yard move."""
    to_location_id: Optional[UUID] = None
    priority: Optional[int] = Field(None, ge=0, le=100)
    assigned_to: Optional[UUID] = None
    notes: Optional[str] = None


class YardMoveStatusUpdate(BaseModel):
    """Schema for updating yard move status."""
    status: YardMoveStatus
    cancellation_reason: Optional[str] = Field(None, max_length=200)


class YardMoveResponse(YardMoveBase):
    """Response schema for yard move."""
    id: UUID
    tenant_id: UUID
    warehouse_id: UUID
    move_number: str
    status: YardMoveStatus
    from_location_id: UUID
    to_location_id: UUID
    appointment_id: Optional[UUID] = None
    assigned_to: Optional[UUID] = None
    assigned_at: Optional[datetime] = None
    requested_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    actual_duration_mins: Optional[int] = None
    cancelled_at: Optional[datetime] = None
    cancellation_reason: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ============================================================================
# GATE TRANSACTION SCHEMAS
# ============================================================================

class GateTransactionBase(BaseModel):
    """Base schema for gate transaction."""
    vehicle_number: str = Field(..., max_length=50)
    trailer_number: Optional[str] = Field(None, max_length=50)
    vehicle_type: VehicleType
    driver_name: Optional[str] = Field(None, max_length=100)
    driver_license: Optional[str] = Field(None, max_length=50)
    driver_phone: Optional[str] = Field(None, max_length=20)
    carrier_name: Optional[str] = Field(None, max_length=100)
    seal_number: Optional[str] = Field(None, max_length=50)
    seal_intact: Optional[bool] = None
    is_loaded: Optional[bool] = None
    load_description: Optional[str] = Field(None, max_length=200)
    inspection_notes: Optional[str] = None
    notes: Optional[str] = None


class GateEntryCreate(GateTransactionBase):
    """Schema for gate entry."""
    warehouse_id: UUID
    gate_location_id: Optional[UUID] = None
    gate_name: Optional[str] = Field(None, max_length=50)
    appointment_id: Optional[UUID] = None
    transporter_id: Optional[UUID] = None
    assigned_location_id: Optional[UUID] = None
    photos: Optional[List[str]] = None


class GateExitCreate(BaseModel):
    """Schema for gate exit."""
    warehouse_id: UUID
    vehicle_number: str = Field(..., max_length=50)
    trailer_number: Optional[str] = Field(None, max_length=50)
    gate_location_id: Optional[UUID] = None
    gate_name: Optional[str] = Field(None, max_length=50)
    entry_transaction_id: Optional[UUID] = None
    new_seal_number: Optional[str] = Field(None, max_length=50)
    is_loaded: Optional[bool] = None
    load_description: Optional[str] = Field(None, max_length=200)
    inspection_notes: Optional[str] = None
    photos: Optional[List[str]] = None
    notes: Optional[str] = None


class GateTransactionResponse(GateTransactionBase):
    """Response schema for gate transaction."""
    id: UUID
    tenant_id: UUID
    warehouse_id: UUID
    transaction_number: str
    transaction_type: str
    gate_location_id: Optional[UUID] = None
    gate_name: Optional[str] = None
    transporter_id: Optional[UUID] = None
    appointment_id: Optional[UUID] = None
    assigned_location_id: Optional[UUID] = None
    new_seal_number: Optional[str] = None
    transaction_time: datetime
    entry_transaction_id: Optional[UUID] = None
    processed_by: Optional[UUID] = None
    id_verified: bool
    photos: Optional[List[str]] = None
    created_at: datetime

    class Config:
        from_attributes = True


# ============================================================================
# DASHBOARD & STATS SCHEMAS
# ============================================================================

class YardOverview(BaseModel):
    """Yard overview dashboard."""
    warehouse_id: UUID
    total_locations: int
    available_locations: int
    occupied_locations: int
    reserved_locations: int
    total_dock_doors: int
    available_docks: int
    occupied_docks: int
    vehicles_in_yard: int
    pending_appointments_today: int
    active_appointments: int
    completed_appointments_today: int
    pending_yard_moves: int
    active_yard_moves: int


class DockSchedule(BaseModel):
    """Dock schedule for a day."""
    dock_door_id: UUID
    door_number: str
    door_name: str
    door_type: str
    appointments: List[DockAppointmentResponse]


class DailySchedule(BaseModel):
    """Daily dock schedule."""
    date: date
    warehouse_id: UUID
    dock_schedules: List[DockSchedule]
    total_appointments: int
    inbound_count: int
    outbound_count: int


class YardLocationMap(BaseModel):
    """Yard location map data."""
    locations: List[YardLocationResponse]
    total: int
    by_type: Dict[str, int]
    by_status: Dict[str, int]
