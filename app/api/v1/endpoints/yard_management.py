"""
Yard Management API Endpoints - Phase 6: Dock Scheduling & Yard Operations.

API endpoints for yard management including:
- Yard location management
- Dock door configuration
- Appointment scheduling
- Yard move operations
- Gate transactions
"""
from datetime import datetime, date
from typing import Optional, List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies.auth import get_current_user, require_permissions
from app.models.user import User
from app.models.yard_management import (
    YardLocationType, YardLocationStatus, DockDoorType,
    AppointmentStatus, AppointmentType, YardMoveStatus,
    GateTransactionType, VehicleType
)
from app.schemas.yard_management import (
    YardLocationCreate, YardLocationUpdate, YardLocationResponse,
    DockDoorCreate, DockDoorUpdate, DockDoorResponse,
    DockAppointmentCreate, DockAppointmentUpdate, DockAppointmentResponse,
    AppointmentCheckIn, AppointmentStatusUpdate,
    YardMoveCreate, YardMoveUpdate, YardMoveResponse, YardMoveStatusUpdate,
    GateEntryCreate, GateExitCreate, GateTransactionResponse,
    YardOverview, DailySchedule, YardLocationMap
)
from app.services.yard_management_service import YardManagementService

router = APIRouter()


# ============================================================================
# YARD LOCATIONS
# ============================================================================

@router.post(
    "/locations",
    response_model=YardLocationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Yard Location"
)
async def create_yard_location(
    data: YardLocationCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions(["wms:manage"]))
):
    """Create a new yard location (dock, parking, staging)."""
    service = YardManagementService(db, current_user.tenant_id)
    return await service.create_yard_location(data)


@router.get(
    "/locations",
    response_model=List[YardLocationResponse],
    summary="List Yard Locations"
)
async def list_yard_locations(
    warehouse_id: UUID,
    location_type: Optional[YardLocationType] = None,
    status: Optional[YardLocationStatus] = None,
    zone: Optional[str] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions(["wms:read"]))
):
    """List yard locations with filters."""
    service = YardManagementService(db, current_user.tenant_id)
    locations, _ = await service.list_yard_locations(
        warehouse_id=warehouse_id,
        location_type=location_type,
        status=status,
        zone=zone,
        skip=skip,
        limit=limit
    )
    return locations


@router.get(
    "/locations/{location_id}",
    response_model=YardLocationResponse,
    summary="Get Yard Location"
)
async def get_yard_location(
    location_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions(["wms:read"]))
):
    """Get yard location details."""
    service = YardManagementService(db, current_user.tenant_id)
    location = await service.get_yard_location(location_id)
    if not location:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Yard location not found"
        )
    return location


@router.patch(
    "/locations/{location_id}",
    response_model=YardLocationResponse,
    summary="Update Yard Location"
)
async def update_yard_location(
    location_id: UUID,
    data: YardLocationUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions(["wms:manage"]))
):
    """Update yard location details."""
    service = YardManagementService(db, current_user.tenant_id)
    location = await service.update_yard_location(location_id, data)
    if not location:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Yard location not found"
        )
    return location


@router.post(
    "/locations/{location_id}/occupy",
    response_model=YardLocationResponse,
    summary="Occupy Location"
)
async def occupy_location(
    location_id: UUID,
    vehicle_id: str = Query(..., max_length=50),
    vehicle_type: VehicleType = Query(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions(["wms:manage"]))
):
    """Mark a location as occupied by a vehicle."""
    service = YardManagementService(db, current_user.tenant_id)
    location = await service.occupy_location(location_id, vehicle_id, vehicle_type.value)
    if not location:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Yard location not found"
        )
    return location


@router.post(
    "/locations/{location_id}/release",
    response_model=YardLocationResponse,
    summary="Release Location"
)
async def release_location(
    location_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions(["wms:manage"]))
):
    """Release a location (mark as available)."""
    service = YardManagementService(db, current_user.tenant_id)
    location = await service.release_location(location_id)
    if not location:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Yard location not found"
        )
    return location


# ============================================================================
# DOCK DOORS
# ============================================================================

@router.post(
    "/dock-doors",
    response_model=DockDoorResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Dock Door"
)
async def create_dock_door(
    data: DockDoorCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions(["wms:manage"]))
):
    """Create a new dock door configuration."""
    service = YardManagementService(db, current_user.tenant_id)
    return await service.create_dock_door(data)


@router.get(
    "/dock-doors",
    response_model=List[DockDoorResponse],
    summary="List Dock Doors"
)
async def list_dock_doors(
    warehouse_id: UUID,
    door_type: Optional[DockDoorType] = None,
    status: Optional[str] = None,
    is_active: bool = True,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions(["wms:read"]))
):
    """List dock doors with filters."""
    service = YardManagementService(db, current_user.tenant_id)
    doors, _ = await service.list_dock_doors(
        warehouse_id=warehouse_id,
        door_type=door_type,
        status=status,
        is_active=is_active,
        skip=skip,
        limit=limit
    )
    return doors


@router.get(
    "/dock-doors/{door_id}",
    response_model=DockDoorResponse,
    summary="Get Dock Door"
)
async def get_dock_door(
    door_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions(["wms:read"]))
):
    """Get dock door details."""
    service = YardManagementService(db, current_user.tenant_id)
    door = await service.get_dock_door(door_id)
    if not door:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Dock door not found"
        )
    return door


@router.patch(
    "/dock-doors/{door_id}",
    response_model=DockDoorResponse,
    summary="Update Dock Door"
)
async def update_dock_door(
    door_id: UUID,
    data: DockDoorUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions(["wms:manage"]))
):
    """Update dock door configuration."""
    service = YardManagementService(db, current_user.tenant_id)
    door = await service.update_dock_door(door_id, data)
    if not door:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Dock door not found"
        )
    return door


@router.get(
    "/dock-doors/available",
    response_model=List[DockDoorResponse],
    summary="Find Available Dock Doors"
)
async def find_available_dock_doors(
    warehouse_id: UUID,
    appointment_type: AppointmentType,
    appointment_date: date,
    appointment_time: str = Query(..., description="Time in HH:MM format"),
    duration_minutes: int = Query(60, ge=15, le=480),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions(["wms:read"]))
):
    """Find available dock doors for a time slot."""
    from datetime import time as dt_time
    hours, minutes = map(int, appointment_time.split(':'))
    appt_time = dt_time(hours, minutes)

    service = YardManagementService(db, current_user.tenant_id)
    return await service.get_available_dock_doors(
        warehouse_id=warehouse_id,
        appointment_type=appointment_type,
        appointment_date=appointment_date,
        appointment_time=appt_time,
        duration_minutes=duration_minutes
    )


# ============================================================================
# APPOINTMENTS
# ============================================================================

@router.post(
    "/appointments",
    response_model=DockAppointmentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Appointment"
)
async def create_appointment(
    data: DockAppointmentCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions(["wms:manage"]))
):
    """Create a dock appointment."""
    service = YardManagementService(db, current_user.tenant_id)
    return await service.create_appointment(data, current_user.id)


@router.get(
    "/appointments",
    response_model=List[DockAppointmentResponse],
    summary="List Appointments"
)
async def list_appointments(
    warehouse_id: UUID,
    appointment_date: Optional[date] = None,
    status: Optional[AppointmentStatus] = None,
    appointment_type: Optional[AppointmentType] = None,
    dock_door_id: Optional[UUID] = None,
    carrier_name: Optional[str] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions(["wms:read"]))
):
    """List appointments with filters."""
    service = YardManagementService(db, current_user.tenant_id)
    appointments, _ = await service.list_appointments(
        warehouse_id=warehouse_id,
        appointment_date=appointment_date,
        status=status,
        appointment_type=appointment_type,
        dock_door_id=dock_door_id,
        carrier_name=carrier_name,
        skip=skip,
        limit=limit
    )
    return appointments


@router.get(
    "/appointments/{appointment_id}",
    response_model=DockAppointmentResponse,
    summary="Get Appointment"
)
async def get_appointment(
    appointment_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions(["wms:read"]))
):
    """Get appointment details."""
    service = YardManagementService(db, current_user.tenant_id)
    appointment = await service.get_appointment(appointment_id)
    if not appointment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Appointment not found"
        )
    return appointment


@router.patch(
    "/appointments/{appointment_id}",
    response_model=DockAppointmentResponse,
    summary="Update Appointment"
)
async def update_appointment(
    appointment_id: UUID,
    data: DockAppointmentUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions(["wms:manage"]))
):
    """Update appointment details."""
    service = YardManagementService(db, current_user.tenant_id)
    appointment = await service.update_appointment(appointment_id, data)
    if not appointment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Appointment not found"
        )
    return appointment


@router.post(
    "/appointments/{appointment_id}/check-in",
    response_model=DockAppointmentResponse,
    summary="Check In Appointment"
)
async def check_in_appointment(
    appointment_id: UUID,
    data: AppointmentCheckIn,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions(["wms:manage"]))
):
    """Check in an appointment when carrier arrives."""
    service = YardManagementService(db, current_user.tenant_id)
    appointment = await service.check_in_appointment(
        appointment_id, data, current_user.id
    )
    if not appointment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Appointment not found"
        )
    return appointment


@router.post(
    "/appointments/{appointment_id}/status",
    response_model=DockAppointmentResponse,
    summary="Update Appointment Status"
)
async def update_appointment_status(
    appointment_id: UUID,
    data: AppointmentStatusUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions(["wms:manage"]))
):
    """Update appointment status (at dock, loading, completed, etc.)."""
    service = YardManagementService(db, current_user.tenant_id)
    appointment = await service.update_appointment_status(appointment_id, data)
    if not appointment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Appointment not found"
        )
    return appointment


# ============================================================================
# YARD MOVES
# ============================================================================

@router.post(
    "/moves",
    response_model=YardMoveResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Yard Move"
)
async def create_yard_move(
    data: YardMoveCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions(["wms:manage"]))
):
    """Create a yard move request."""
    service = YardManagementService(db, current_user.tenant_id)
    return await service.create_yard_move(data)


@router.get(
    "/moves",
    response_model=List[YardMoveResponse],
    summary="List Yard Moves"
)
async def list_yard_moves(
    warehouse_id: UUID,
    status: Optional[YardMoveStatus] = None,
    assigned_to: Optional[UUID] = None,
    include_completed: bool = False,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions(["wms:read"]))
):
    """List yard moves with filters."""
    service = YardManagementService(db, current_user.tenant_id)
    moves, _ = await service.list_yard_moves(
        warehouse_id=warehouse_id,
        status=status,
        assigned_to=assigned_to,
        include_completed=include_completed,
        skip=skip,
        limit=limit
    )
    return moves


@router.get(
    "/moves/{move_id}",
    response_model=YardMoveResponse,
    summary="Get Yard Move"
)
async def get_yard_move(
    move_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions(["wms:read"]))
):
    """Get yard move details."""
    service = YardManagementService(db, current_user.tenant_id)
    move = await service.get_yard_move(move_id)
    if not move:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Yard move not found"
        )
    return move


@router.post(
    "/moves/{move_id}/assign",
    response_model=YardMoveResponse,
    summary="Assign Yard Move"
)
async def assign_yard_move(
    move_id: UUID,
    assigned_to: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions(["wms:manage"]))
):
    """Assign yard move to a yard jockey."""
    service = YardManagementService(db, current_user.tenant_id)
    move = await service.assign_yard_move(move_id, assigned_to)
    if not move:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Yard move not found"
        )
    return move


@router.post(
    "/moves/{move_id}/start",
    response_model=YardMoveResponse,
    summary="Start Yard Move"
)
async def start_yard_move(
    move_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Start a yard move."""
    service = YardManagementService(db, current_user.tenant_id)
    move = await service.start_yard_move(move_id)
    if not move:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Yard move not found"
        )
    return move


@router.post(
    "/moves/{move_id}/complete",
    response_model=YardMoveResponse,
    summary="Complete Yard Move"
)
async def complete_yard_move(
    move_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Complete a yard move."""
    service = YardManagementService(db, current_user.tenant_id)
    move = await service.complete_yard_move(move_id)
    if not move:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Yard move not found"
        )
    return move


@router.post(
    "/moves/{move_id}/cancel",
    response_model=YardMoveResponse,
    summary="Cancel Yard Move"
)
async def cancel_yard_move(
    move_id: UUID,
    reason: str = Query(..., max_length=200),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions(["wms:manage"]))
):
    """Cancel a yard move."""
    service = YardManagementService(db, current_user.tenant_id)
    move = await service.cancel_yard_move(move_id, reason)
    if not move:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Yard move not found"
        )
    return move


# ============================================================================
# GATE TRANSACTIONS
# ============================================================================

@router.post(
    "/gate/entry",
    response_model=GateTransactionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Record Gate Entry"
)
async def create_gate_entry(
    data: GateEntryCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions(["wms:manage"]))
):
    """Record a gate entry (vehicle arriving)."""
    service = YardManagementService(db, current_user.tenant_id)
    return await service.create_gate_entry(data, current_user.id)


@router.post(
    "/gate/exit",
    response_model=GateTransactionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Record Gate Exit"
)
async def create_gate_exit(
    data: GateExitCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions(["wms:manage"]))
):
    """Record a gate exit (vehicle departing)."""
    service = YardManagementService(db, current_user.tenant_id)
    return await service.create_gate_exit(data, current_user.id)


@router.get(
    "/gate/transactions",
    response_model=List[GateTransactionResponse],
    summary="List Gate Transactions"
)
async def list_gate_transactions(
    warehouse_id: UUID,
    transaction_type: Optional[GateTransactionType] = None,
    from_date: Optional[datetime] = None,
    to_date: Optional[datetime] = None,
    vehicle_number: Optional[str] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions(["wms:read"]))
):
    """List gate transactions with filters."""
    service = YardManagementService(db, current_user.tenant_id)
    transactions, _ = await service.list_gate_transactions(
        warehouse_id=warehouse_id,
        transaction_type=transaction_type,
        from_date=from_date,
        to_date=to_date,
        vehicle_number=vehicle_number,
        skip=skip,
        limit=limit
    )
    return transactions


# ============================================================================
# DASHBOARD & SCHEDULE
# ============================================================================

@router.get(
    "/overview/{warehouse_id}",
    response_model=YardOverview,
    summary="Get Yard Overview"
)
async def get_yard_overview(
    warehouse_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions(["wms:read"]))
):
    """Get yard overview dashboard."""
    service = YardManagementService(db, current_user.tenant_id)
    return await service.get_yard_overview(warehouse_id)


@router.get(
    "/schedule/{warehouse_id}",
    response_model=DailySchedule,
    summary="Get Daily Dock Schedule"
)
async def get_daily_schedule(
    warehouse_id: UUID,
    schedule_date: date = Query(default=None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions(["wms:read"]))
):
    """Get dock schedule for a day."""
    if not schedule_date:
        schedule_date = date.today()
    service = YardManagementService(db, current_user.tenant_id)
    return await service.get_daily_schedule(warehouse_id, schedule_date)
