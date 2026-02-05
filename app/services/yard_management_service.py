"""
Yard Management Service - Phase 6: Dock Scheduling & Yard Operations.

Business logic for yard management including:
- Yard location management
- Dock door scheduling
- Appointment management
- Yard move operations
- Gate transactions
"""
import uuid
from datetime import datetime, timezone, date, time, timedelta
from decimal import Decimal
from typing import Optional, List, Dict, Any, Tuple

from sqlalchemy import select, func, and_, or_, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.yard_management import (
    YardLocation, DockDoor, DockAppointment, YardMove, GateTransaction,
    YardLocationType, YardLocationStatus, DockDoorType,
    AppointmentStatus, AppointmentType, YardMoveType, YardMoveStatus,
    GateTransactionType, VehicleType
)
from app.schemas.yard_management import (
    YardLocationCreate, YardLocationUpdate,
    DockDoorCreate, DockDoorUpdate,
    DockAppointmentCreate, DockAppointmentUpdate, AppointmentCheckIn,
    AppointmentStatusUpdate,
    YardMoveCreate, YardMoveUpdate, YardMoveStatusUpdate,
    GateEntryCreate, GateExitCreate,
    YardOverview, DockSchedule, DailySchedule, YardLocationMap
)


class YardManagementService:
    """Service for yard management operations."""

    def __init__(self, db: AsyncSession, tenant_id: uuid.UUID):
        self.db = db
        self.tenant_id = tenant_id

    # ========================================================================
    # YARD LOCATION MANAGEMENT
    # ========================================================================

    async def create_yard_location(
        self,
        data: YardLocationCreate
    ) -> YardLocation:
        """Create a new yard location."""
        location = YardLocation(
            id=uuid.uuid4(),
            tenant_id=self.tenant_id,
            warehouse_id=data.warehouse_id,
            location_code=data.location_code,
            location_name=data.location_name,
            location_type=data.location_type.value,
            status=YardLocationStatus.AVAILABLE.value,
            zone=data.zone,
            row=data.row,
            column=data.column,
            level=data.level,
            max_length_feet=data.max_length_feet,
            max_width_feet=data.max_width_feet,
            max_height_feet=data.max_height_feet,
            max_weight_lbs=data.max_weight_lbs,
            latitude=data.latitude,
            longitude=data.longitude,
            has_power=data.has_power,
            has_refrigeration=data.has_refrigeration,
            has_fuel=data.has_fuel,
            is_hazmat_approved=data.is_hazmat_approved,
            sequence=data.sequence,
            notes=data.notes,
            is_active=True
        )
        self.db.add(location)
        await self.db.commit()
        await self.db.refresh(location)
        return location

    async def get_yard_location(
        self,
        location_id: uuid.UUID
    ) -> Optional[YardLocation]:
        """Get yard location by ID."""
        result = await self.db.execute(
            select(YardLocation)
            .where(
                YardLocation.id == location_id,
                YardLocation.tenant_id == self.tenant_id
            )
        )
        return result.scalar_one_or_none()

    async def list_yard_locations(
        self,
        warehouse_id: uuid.UUID,
        location_type: Optional[YardLocationType] = None,
        status: Optional[YardLocationStatus] = None,
        zone: Optional[str] = None,
        skip: int = 0,
        limit: int = 100
    ) -> Tuple[List[YardLocation], int]:
        """List yard locations with filters."""
        query = select(YardLocation).where(
            YardLocation.tenant_id == self.tenant_id,
            YardLocation.warehouse_id == warehouse_id
        )

        if location_type:
            query = query.where(YardLocation.location_type == location_type.value)
        if status:
            query = query.where(YardLocation.status == status.value)
        if zone:
            query = query.where(YardLocation.zone == zone)

        # Count
        count_query = select(func.count()).select_from(query.subquery())
        total = (await self.db.execute(count_query)).scalar() or 0

        # Paginate
        query = query.order_by(YardLocation.sequence, YardLocation.location_code)
        query = query.offset(skip).limit(limit)
        result = await self.db.execute(query)
        locations = result.scalars().all()

        return list(locations), total

    async def update_yard_location(
        self,
        location_id: uuid.UUID,
        data: YardLocationUpdate
    ) -> Optional[YardLocation]:
        """Update yard location."""
        location = await self.get_yard_location(location_id)
        if not location:
            return None

        update_data = data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            if hasattr(location, key):
                if key == 'status' and value:
                    setattr(location, key, value.value)
                else:
                    setattr(location, key, value)

        location.updated_at = datetime.now(timezone.utc)
        await self.db.commit()
        await self.db.refresh(location)
        return location

    async def occupy_location(
        self,
        location_id: uuid.UUID,
        vehicle_id: str,
        vehicle_type: str
    ) -> Optional[YardLocation]:
        """Mark location as occupied."""
        location = await self.get_yard_location(location_id)
        if not location:
            return None

        location.status = YardLocationStatus.OCCUPIED.value
        location.current_vehicle_id = vehicle_id
        location.current_vehicle_type = vehicle_type
        location.occupied_since = datetime.now(timezone.utc)
        location.updated_at = datetime.now(timezone.utc)

        await self.db.commit()
        await self.db.refresh(location)
        return location

    async def release_location(
        self,
        location_id: uuid.UUID
    ) -> Optional[YardLocation]:
        """Release location (mark as available)."""
        location = await self.get_yard_location(location_id)
        if not location:
            return None

        location.status = YardLocationStatus.AVAILABLE.value
        location.current_vehicle_id = None
        location.current_vehicle_type = None
        location.occupied_since = None
        location.updated_at = datetime.now(timezone.utc)

        await self.db.commit()
        await self.db.refresh(location)
        return location

    # ========================================================================
    # DOCK DOOR MANAGEMENT
    # ========================================================================

    async def create_dock_door(
        self,
        data: DockDoorCreate
    ) -> DockDoor:
        """Create a new dock door."""
        door = DockDoor(
            id=uuid.uuid4(),
            tenant_id=self.tenant_id,
            warehouse_id=data.warehouse_id,
            yard_location_id=data.yard_location_id,
            door_number=data.door_number,
            door_name=data.door_name,
            door_type=data.door_type.value,
            status=YardLocationStatus.AVAILABLE.value,
            door_height_feet=data.door_height_feet,
            door_width_feet=data.door_width_feet,
            dock_height_inches=data.dock_height_inches,
            has_leveler=data.has_leveler,
            has_shelter=data.has_shelter,
            has_restraint=data.has_restraint,
            has_lights=data.has_lights,
            leveler_capacity_lbs=data.leveler_capacity_lbs,
            linked_zone_id=data.linked_zone_id,
            default_appointment_duration_mins=data.default_appointment_duration_mins,
            max_appointments_per_hour=data.max_appointments_per_hour,
            operating_start_time=data.operating_start_time,
            operating_end_time=data.operating_end_time,
            operating_days=data.operating_days,
            preferred_carriers=data.preferred_carriers,
            blocked_carriers=data.blocked_carriers,
            notes=data.notes,
            is_active=True
        )
        self.db.add(door)
        await self.db.commit()
        await self.db.refresh(door)
        return door

    async def get_dock_door(
        self,
        door_id: uuid.UUID
    ) -> Optional[DockDoor]:
        """Get dock door by ID."""
        result = await self.db.execute(
            select(DockDoor)
            .where(
                DockDoor.id == door_id,
                DockDoor.tenant_id == self.tenant_id
            )
        )
        return result.scalar_one_or_none()

    async def list_dock_doors(
        self,
        warehouse_id: uuid.UUID,
        door_type: Optional[DockDoorType] = None,
        status: Optional[str] = None,
        is_active: bool = True,
        skip: int = 0,
        limit: int = 100
    ) -> Tuple[List[DockDoor], int]:
        """List dock doors with filters."""
        query = select(DockDoor).where(
            DockDoor.tenant_id == self.tenant_id,
            DockDoor.warehouse_id == warehouse_id
        )

        if door_type:
            query = query.where(DockDoor.door_type == door_type.value)
        if status:
            query = query.where(DockDoor.status == status)
        if is_active is not None:
            query = query.where(DockDoor.is_active == is_active)

        # Count
        count_query = select(func.count()).select_from(query.subquery())
        total = (await self.db.execute(count_query)).scalar() or 0

        # Paginate
        query = query.order_by(DockDoor.door_number).offset(skip).limit(limit)
        result = await self.db.execute(query)
        doors = result.scalars().all()

        return list(doors), total

    async def update_dock_door(
        self,
        door_id: uuid.UUID,
        data: DockDoorUpdate
    ) -> Optional[DockDoor]:
        """Update dock door."""
        door = await self.get_dock_door(door_id)
        if not door:
            return None

        update_data = data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            if hasattr(door, key):
                if key == 'door_type' and value:
                    setattr(door, key, value.value)
                elif key == 'status' and value:
                    setattr(door, key, value.value)
                else:
                    setattr(door, key, value)

        door.updated_at = datetime.now(timezone.utc)
        await self.db.commit()
        await self.db.refresh(door)
        return door

    async def get_available_dock_doors(
        self,
        warehouse_id: uuid.UUID,
        appointment_type: AppointmentType,
        appointment_date: date,
        appointment_time: time,
        duration_minutes: int = 60
    ) -> List[DockDoor]:
        """Find available dock doors for a time slot."""
        # Determine required door type
        door_types = []
        if appointment_type in [AppointmentType.INBOUND, AppointmentType.LIVE_UNLOAD]:
            door_types = [DockDoorType.INBOUND.value, DockDoorType.DUAL.value]
        elif appointment_type in [AppointmentType.OUTBOUND, AppointmentType.LIVE_LOAD]:
            door_types = [DockDoorType.OUTBOUND.value, DockDoorType.DUAL.value]
        else:
            door_types = [DockDoorType.CROSS_DOCK.value, DockDoorType.DUAL.value]

        # Get all matching doors
        doors_query = select(DockDoor).where(
            DockDoor.tenant_id == self.tenant_id,
            DockDoor.warehouse_id == warehouse_id,
            DockDoor.door_type.in_(door_types),
            DockDoor.is_active == True
        )
        result = await self.db.execute(doors_query)
        all_doors = result.scalars().all()

        # Check for conflicting appointments
        end_time = (
            datetime.combine(date.today(), appointment_time) +
            timedelta(minutes=duration_minutes)
        ).time()

        available = []
        for door in all_doors:
            # Check if operating hours allow
            if door.operating_start_time and appointment_time < door.operating_start_time:
                continue
            if door.operating_end_time and end_time > door.operating_end_time:
                continue

            # Check for overlapping appointments
            conflict_query = select(DockAppointment).where(
                DockAppointment.tenant_id == self.tenant_id,
                DockAppointment.dock_door_id == door.id,
                DockAppointment.appointment_date == appointment_date,
                DockAppointment.status.notin_([
                    AppointmentStatus.CANCELLED.value,
                    AppointmentStatus.COMPLETED.value,
                    AppointmentStatus.NO_SHOW.value
                ])
            )
            conflicts = await self.db.execute(conflict_query)
            existing = list(conflicts.scalars().all())

            has_conflict = False
            for appt in existing:
                appt_start = appt.scheduled_arrival
                appt_end = (
                    datetime.combine(date.today(), appt.scheduled_arrival) +
                    timedelta(minutes=appt.duration_minutes)
                ).time()

                # Check overlap
                if not (end_time <= appt_start or appointment_time >= appt_end):
                    has_conflict = True
                    break

            if not has_conflict:
                available.append(door)

        return available

    # ========================================================================
    # APPOINTMENT MANAGEMENT
    # ========================================================================

    async def _generate_appointment_number(self) -> str:
        """Generate unique appointment number."""
        today = date.today()
        prefix = f"APT-{today.strftime('%Y%m%d')}"

        result = await self.db.execute(
            select(func.count(DockAppointment.id))
            .where(
                DockAppointment.tenant_id == self.tenant_id,
                DockAppointment.appointment_number.like(f"{prefix}%")
            )
        )
        count = (result.scalar() or 0) + 1
        return f"{prefix}-{count:04d}"

    async def create_appointment(
        self,
        data: DockAppointmentCreate,
        created_by: uuid.UUID
    ) -> DockAppointment:
        """Create a dock appointment."""
        appointment_number = await self._generate_appointment_number()

        appointment = DockAppointment(
            id=uuid.uuid4(),
            tenant_id=self.tenant_id,
            warehouse_id=data.warehouse_id,
            appointment_number=appointment_number,
            appointment_type=data.appointment_type.value,
            status=AppointmentStatus.SCHEDULED.value,
            appointment_date=data.appointment_date,
            scheduled_arrival=data.scheduled_arrival,
            scheduled_departure=data.scheduled_departure,
            duration_minutes=data.duration_minutes,
            dock_door_id=data.dock_door_id,
            transporter_id=data.transporter_id,
            carrier_name=data.carrier_name,
            carrier_code=data.carrier_code,
            driver_name=data.driver_name,
            driver_phone=data.driver_phone,
            vehicle_number=data.vehicle_number,
            trailer_number=data.trailer_number,
            vehicle_type=data.vehicle_type.value if data.vehicle_type else None,
            reference_numbers=data.reference_numbers,
            shipment_id=data.shipment_id,
            purchase_order_id=data.purchase_order_id,
            expected_pallets=data.expected_pallets,
            expected_cases=data.expected_cases,
            expected_units=data.expected_units,
            expected_weight_lbs=data.expected_weight_lbs,
            special_instructions=data.special_instructions,
            handling_instructions=data.handling_instructions,
            notes=data.notes,
            created_by=created_by,
            is_late=False
        )
        self.db.add(appointment)
        await self.db.commit()
        await self.db.refresh(appointment)
        return appointment

    async def get_appointment(
        self,
        appointment_id: uuid.UUID
    ) -> Optional[DockAppointment]:
        """Get appointment by ID."""
        result = await self.db.execute(
            select(DockAppointment)
            .where(
                DockAppointment.id == appointment_id,
                DockAppointment.tenant_id == self.tenant_id
            )
        )
        return result.scalar_one_or_none()

    async def list_appointments(
        self,
        warehouse_id: uuid.UUID,
        appointment_date: Optional[date] = None,
        status: Optional[AppointmentStatus] = None,
        appointment_type: Optional[AppointmentType] = None,
        dock_door_id: Optional[uuid.UUID] = None,
        carrier_name: Optional[str] = None,
        skip: int = 0,
        limit: int = 100
    ) -> Tuple[List[DockAppointment], int]:
        """List appointments with filters."""
        query = select(DockAppointment).where(
            DockAppointment.tenant_id == self.tenant_id,
            DockAppointment.warehouse_id == warehouse_id
        )

        if appointment_date:
            query = query.where(DockAppointment.appointment_date == appointment_date)
        if status:
            query = query.where(DockAppointment.status == status.value)
        if appointment_type:
            query = query.where(DockAppointment.appointment_type == appointment_type.value)
        if dock_door_id:
            query = query.where(DockAppointment.dock_door_id == dock_door_id)
        if carrier_name:
            query = query.where(DockAppointment.carrier_name.ilike(f"%{carrier_name}%"))

        # Count
        count_query = select(func.count()).select_from(query.subquery())
        total = (await self.db.execute(count_query)).scalar() or 0

        # Paginate
        query = query.order_by(
            DockAppointment.appointment_date.desc(),
            DockAppointment.scheduled_arrival
        )
        query = query.offset(skip).limit(limit)
        result = await self.db.execute(query)
        appointments = result.scalars().all()

        return list(appointments), total

    async def update_appointment(
        self,
        appointment_id: uuid.UUID,
        data: DockAppointmentUpdate
    ) -> Optional[DockAppointment]:
        """Update appointment details."""
        appointment = await self.get_appointment(appointment_id)
        if not appointment:
            return None

        update_data = data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            if hasattr(appointment, key):
                setattr(appointment, key, value)

        appointment.updated_at = datetime.now(timezone.utc)
        await self.db.commit()
        await self.db.refresh(appointment)
        return appointment

    async def check_in_appointment(
        self,
        appointment_id: uuid.UUID,
        data: AppointmentCheckIn,
        checked_in_by: uuid.UUID
    ) -> Optional[DockAppointment]:
        """Check in an appointment."""
        appointment = await self.get_appointment(appointment_id)
        if not appointment:
            return None

        now = datetime.now(timezone.utc)

        appointment.status = AppointmentStatus.CHECKED_IN.value
        appointment.actual_arrival = now
        appointment.check_in_time = now
        appointment.vehicle_number = data.vehicle_number
        appointment.trailer_number = data.trailer_number
        if data.driver_name:
            appointment.driver_name = data.driver_name
        if data.driver_phone:
            appointment.driver_phone = data.driver_phone
        appointment.checked_in_by = checked_in_by

        # Check if late
        scheduled = datetime.combine(
            appointment.appointment_date,
            appointment.scheduled_arrival
        ).replace(tzinfo=timezone.utc)
        if now > scheduled + timedelta(minutes=15):
            appointment.is_late = True

        appointment.updated_at = now
        await self.db.commit()
        await self.db.refresh(appointment)
        return appointment

    async def update_appointment_status(
        self,
        appointment_id: uuid.UUID,
        data: AppointmentStatusUpdate
    ) -> Optional[DockAppointment]:
        """Update appointment status."""
        appointment = await self.get_appointment(appointment_id)
        if not appointment:
            return None

        now = datetime.now(timezone.utc)
        old_status = appointment.status
        appointment.status = data.status.value

        # Set timing based on status
        if data.status == AppointmentStatus.AT_DOCK:
            appointment.dock_time = now
            if data.dock_door_id:
                appointment.dock_door_id = data.dock_door_id
            # Calculate wait time
            if appointment.check_in_time:
                wait = (now - appointment.check_in_time).total_seconds() / 60
                appointment.wait_time_minutes = int(wait)

        elif data.status in [AppointmentStatus.LOADING, AppointmentStatus.UNLOADING]:
            appointment.load_start_time = now

        elif data.status == AppointmentStatus.COMPLETED:
            appointment.load_end_time = now
            appointment.departure_time = now
            # Calculate dock time
            if appointment.dock_time:
                dock_mins = (now - appointment.dock_time).total_seconds() / 60
                appointment.dock_time_minutes = int(dock_mins)
            # Calculate turnaround
            if appointment.actual_arrival:
                turnaround = (now - appointment.actual_arrival).total_seconds() / 60
                appointment.turnaround_time_minutes = int(turnaround)

        elif data.status == AppointmentStatus.CANCELLED:
            appointment.cancellation_reason = data.reason

        elif data.status == AppointmentStatus.NO_SHOW:
            appointment.no_show_reason = data.reason

        elif data.status == AppointmentStatus.RESCHEDULED:
            appointment.late_reason = data.reason

        appointment.updated_at = now
        await self.db.commit()
        await self.db.refresh(appointment)
        return appointment

    # ========================================================================
    # YARD MOVE MANAGEMENT
    # ========================================================================

    async def _generate_move_number(self) -> str:
        """Generate unique move number."""
        today = date.today()
        prefix = f"YM-{today.strftime('%Y%m%d')}"

        result = await self.db.execute(
            select(func.count(YardMove.id))
            .where(
                YardMove.tenant_id == self.tenant_id,
                YardMove.move_number.like(f"{prefix}%")
            )
        )
        count = (result.scalar() or 0) + 1
        return f"{prefix}-{count:04d}"

    async def create_yard_move(
        self,
        data: YardMoveCreate
    ) -> YardMove:
        """Create a yard move request."""
        move_number = await self._generate_move_number()

        move = YardMove(
            id=uuid.uuid4(),
            tenant_id=self.tenant_id,
            warehouse_id=data.warehouse_id,
            move_number=move_number,
            move_type=data.move_type.value,
            status=YardMoveStatus.REQUESTED.value,
            priority=data.priority,
            from_location_id=data.from_location_id,
            to_location_id=data.to_location_id,
            vehicle_id=data.vehicle_id,
            vehicle_type=data.vehicle_type.value,
            appointment_id=data.appointment_id,
            estimated_duration_mins=data.estimated_duration_mins,
            notes=data.notes
        )
        self.db.add(move)
        await self.db.commit()
        await self.db.refresh(move)
        return move

    async def get_yard_move(
        self,
        move_id: uuid.UUID
    ) -> Optional[YardMove]:
        """Get yard move by ID."""
        result = await self.db.execute(
            select(YardMove)
            .where(
                YardMove.id == move_id,
                YardMove.tenant_id == self.tenant_id
            )
        )
        return result.scalar_one_or_none()

    async def list_yard_moves(
        self,
        warehouse_id: uuid.UUID,
        status: Optional[YardMoveStatus] = None,
        assigned_to: Optional[uuid.UUID] = None,
        include_completed: bool = False,
        skip: int = 0,
        limit: int = 100
    ) -> Tuple[List[YardMove], int]:
        """List yard moves with filters."""
        query = select(YardMove).where(
            YardMove.tenant_id == self.tenant_id,
            YardMove.warehouse_id == warehouse_id
        )

        if status:
            query = query.where(YardMove.status == status.value)
        elif not include_completed:
            query = query.where(YardMove.status.notin_([
                YardMoveStatus.COMPLETED.value,
                YardMoveStatus.CANCELLED.value
            ]))
        if assigned_to:
            query = query.where(YardMove.assigned_to == assigned_to)

        # Count
        count_query = select(func.count()).select_from(query.subquery())
        total = (await self.db.execute(count_query)).scalar() or 0

        # Paginate
        query = query.order_by(YardMove.priority, YardMove.created_at)
        query = query.offset(skip).limit(limit)
        result = await self.db.execute(query)
        moves = result.scalars().all()

        return list(moves), total

    async def assign_yard_move(
        self,
        move_id: uuid.UUID,
        assigned_to: uuid.UUID
    ) -> Optional[YardMove]:
        """Assign yard move to a worker."""
        move = await self.get_yard_move(move_id)
        if not move:
            return None

        move.assigned_to = assigned_to
        move.assigned_at = datetime.now(timezone.utc)
        move.status = YardMoveStatus.ASSIGNED.value
        move.updated_at = datetime.now(timezone.utc)

        await self.db.commit()
        await self.db.refresh(move)
        return move

    async def start_yard_move(
        self,
        move_id: uuid.UUID
    ) -> Optional[YardMove]:
        """Start a yard move."""
        move = await self.get_yard_move(move_id)
        if not move:
            return None

        move.status = YardMoveStatus.IN_PROGRESS.value
        move.started_at = datetime.now(timezone.utc)
        move.updated_at = datetime.now(timezone.utc)

        await self.db.commit()
        await self.db.refresh(move)
        return move

    async def complete_yard_move(
        self,
        move_id: uuid.UUID
    ) -> Optional[YardMove]:
        """Complete a yard move."""
        move = await self.get_yard_move(move_id)
        if not move:
            return None

        now = datetime.now(timezone.utc)
        move.status = YardMoveStatus.COMPLETED.value
        move.completed_at = now
        move.updated_at = now

        # Calculate actual duration
        if move.started_at:
            duration = (now - move.started_at).total_seconds() / 60
            move.actual_duration_mins = int(duration)

        # Update locations
        # Release source location
        await self.release_location(move.from_location_id)

        # Occupy destination location
        await self.occupy_location(
            move.to_location_id,
            move.vehicle_id,
            move.vehicle_type
        )

        await self.db.commit()
        await self.db.refresh(move)
        return move

    async def cancel_yard_move(
        self,
        move_id: uuid.UUID,
        reason: str
    ) -> Optional[YardMove]:
        """Cancel a yard move."""
        move = await self.get_yard_move(move_id)
        if not move:
            return None

        move.status = YardMoveStatus.CANCELLED.value
        move.cancelled_at = datetime.now(timezone.utc)
        move.cancellation_reason = reason
        move.updated_at = datetime.now(timezone.utc)

        await self.db.commit()
        await self.db.refresh(move)
        return move

    # ========================================================================
    # GATE TRANSACTIONS
    # ========================================================================

    async def _generate_transaction_number(self, txn_type: str) -> str:
        """Generate unique transaction number."""
        today = date.today()
        prefix = f"GT{txn_type[0]}-{today.strftime('%Y%m%d')}"

        result = await self.db.execute(
            select(func.count(GateTransaction.id))
            .where(
                GateTransaction.tenant_id == self.tenant_id,
                GateTransaction.transaction_number.like(f"{prefix}%")
            )
        )
        count = (result.scalar() or 0) + 1
        return f"{prefix}-{count:04d}"

    async def create_gate_entry(
        self,
        data: GateEntryCreate,
        processed_by: uuid.UUID
    ) -> GateTransaction:
        """Create gate entry transaction."""
        txn_number = await self._generate_transaction_number("ENTRY")

        transaction = GateTransaction(
            id=uuid.uuid4(),
            tenant_id=self.tenant_id,
            warehouse_id=data.warehouse_id,
            transaction_number=txn_number,
            transaction_type=GateTransactionType.ENTRY.value,
            gate_location_id=data.gate_location_id,
            gate_name=data.gate_name,
            vehicle_number=data.vehicle_number,
            trailer_number=data.trailer_number,
            vehicle_type=data.vehicle_type.value,
            driver_name=data.driver_name,
            driver_license=data.driver_license,
            driver_phone=data.driver_phone,
            carrier_name=data.carrier_name,
            transporter_id=data.transporter_id,
            appointment_id=data.appointment_id,
            assigned_location_id=data.assigned_location_id,
            seal_number=data.seal_number,
            seal_intact=data.seal_intact,
            is_loaded=data.is_loaded,
            load_description=data.load_description,
            processed_by=processed_by,
            id_verified=data.driver_license is not None,
            inspection_notes=data.inspection_notes,
            photos=data.photos,
            notes=data.notes
        )
        self.db.add(transaction)

        # Occupy assigned location if provided
        if data.assigned_location_id:
            await self.occupy_location(
                data.assigned_location_id,
                data.vehicle_number,
                data.vehicle_type.value
            )

        await self.db.commit()
        await self.db.refresh(transaction)
        return transaction

    async def create_gate_exit(
        self,
        data: GateExitCreate,
        processed_by: uuid.UUID
    ) -> GateTransaction:
        """Create gate exit transaction."""
        txn_number = await self._generate_transaction_number("EXIT")

        # Find matching entry if not provided
        entry_id = data.entry_transaction_id
        vehicle_type = VehicleType.STRAIGHT_TRUCK.value

        if not entry_id:
            entry_result = await self.db.execute(
                select(GateTransaction)
                .where(
                    GateTransaction.tenant_id == self.tenant_id,
                    GateTransaction.warehouse_id == data.warehouse_id,
                    GateTransaction.vehicle_number == data.vehicle_number,
                    GateTransaction.transaction_type == GateTransactionType.ENTRY.value
                )
                .order_by(GateTransaction.transaction_time.desc())
                .limit(1)
            )
            entry = entry_result.scalar_one_or_none()
            if entry:
                entry_id = entry.id
                vehicle_type = entry.vehicle_type
                # Release the assigned location
                if entry.assigned_location_id:
                    await self.release_location(entry.assigned_location_id)

        transaction = GateTransaction(
            id=uuid.uuid4(),
            tenant_id=self.tenant_id,
            warehouse_id=data.warehouse_id,
            transaction_number=txn_number,
            transaction_type=GateTransactionType.EXIT.value,
            gate_location_id=data.gate_location_id,
            gate_name=data.gate_name,
            vehicle_number=data.vehicle_number,
            trailer_number=data.trailer_number,
            vehicle_type=vehicle_type,
            entry_transaction_id=entry_id,
            new_seal_number=data.new_seal_number,
            is_loaded=data.is_loaded,
            load_description=data.load_description,
            processed_by=processed_by,
            inspection_notes=data.inspection_notes,
            photos=data.photos,
            notes=data.notes
        )
        self.db.add(transaction)
        await self.db.commit()
        await self.db.refresh(transaction)
        return transaction

    async def list_gate_transactions(
        self,
        warehouse_id: uuid.UUID,
        transaction_type: Optional[GateTransactionType] = None,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None,
        vehicle_number: Optional[str] = None,
        skip: int = 0,
        limit: int = 100
    ) -> Tuple[List[GateTransaction], int]:
        """List gate transactions with filters."""
        query = select(GateTransaction).where(
            GateTransaction.tenant_id == self.tenant_id,
            GateTransaction.warehouse_id == warehouse_id
        )

        if transaction_type:
            query = query.where(GateTransaction.transaction_type == transaction_type.value)
        if from_date:
            query = query.where(GateTransaction.transaction_time >= from_date)
        if to_date:
            query = query.where(GateTransaction.transaction_time <= to_date)
        if vehicle_number:
            query = query.where(GateTransaction.vehicle_number.ilike(f"%{vehicle_number}%"))

        # Count
        count_query = select(func.count()).select_from(query.subquery())
        total = (await self.db.execute(count_query)).scalar() or 0

        # Paginate
        query = query.order_by(GateTransaction.transaction_time.desc())
        query = query.offset(skip).limit(limit)
        result = await self.db.execute(query)
        transactions = result.scalars().all()

        return list(transactions), total

    # ========================================================================
    # DASHBOARD & STATS
    # ========================================================================

    async def get_yard_overview(
        self,
        warehouse_id: uuid.UUID
    ) -> YardOverview:
        """Get yard overview dashboard."""
        today = date.today()

        # Location stats
        loc_result = await self.db.execute(
            select(
                func.count(YardLocation.id).label('total'),
                func.count(YardLocation.id).filter(
                    YardLocation.status == YardLocationStatus.AVAILABLE.value
                ).label('available'),
                func.count(YardLocation.id).filter(
                    YardLocation.status == YardLocationStatus.OCCUPIED.value
                ).label('occupied'),
                func.count(YardLocation.id).filter(
                    YardLocation.status == YardLocationStatus.RESERVED.value
                ).label('reserved')
            )
            .where(
                YardLocation.tenant_id == self.tenant_id,
                YardLocation.warehouse_id == warehouse_id,
                YardLocation.is_active == True
            )
        )
        loc_stats = loc_result.one()

        # Dock stats
        dock_result = await self.db.execute(
            select(
                func.count(DockDoor.id).label('total'),
                func.count(DockDoor.id).filter(
                    DockDoor.status == YardLocationStatus.AVAILABLE.value
                ).label('available'),
                func.count(DockDoor.id).filter(
                    DockDoor.status == YardLocationStatus.OCCUPIED.value
                ).label('occupied')
            )
            .where(
                DockDoor.tenant_id == self.tenant_id,
                DockDoor.warehouse_id == warehouse_id,
                DockDoor.is_active == True
            )
        )
        dock_stats = dock_result.one()

        # Vehicles in yard
        vehicles_result = await self.db.execute(
            select(func.count(YardLocation.id))
            .where(
                YardLocation.tenant_id == self.tenant_id,
                YardLocation.warehouse_id == warehouse_id,
                YardLocation.current_vehicle_id != None
            )
        )
        vehicles_in_yard = vehicles_result.scalar() or 0

        # Appointment stats for today
        appt_result = await self.db.execute(
            select(
                func.count(DockAppointment.id).filter(
                    DockAppointment.status == AppointmentStatus.SCHEDULED.value
                ).label('pending'),
                func.count(DockAppointment.id).filter(
                    DockAppointment.status.in_([
                        AppointmentStatus.CHECKED_IN.value,
                        AppointmentStatus.AT_DOCK.value,
                        AppointmentStatus.LOADING.value,
                        AppointmentStatus.UNLOADING.value
                    ])
                ).label('active'),
                func.count(DockAppointment.id).filter(
                    DockAppointment.status == AppointmentStatus.COMPLETED.value
                ).label('completed')
            )
            .where(
                DockAppointment.tenant_id == self.tenant_id,
                DockAppointment.warehouse_id == warehouse_id,
                DockAppointment.appointment_date == today
            )
        )
        appt_stats = appt_result.one()

        # Yard move stats
        move_result = await self.db.execute(
            select(
                func.count(YardMove.id).filter(
                    YardMove.status.in_([
                        YardMoveStatus.REQUESTED.value,
                        YardMoveStatus.ASSIGNED.value
                    ])
                ).label('pending'),
                func.count(YardMove.id).filter(
                    YardMove.status == YardMoveStatus.IN_PROGRESS.value
                ).label('active')
            )
            .where(
                YardMove.tenant_id == self.tenant_id,
                YardMove.warehouse_id == warehouse_id
            )
        )
        move_stats = move_result.one()

        return YardOverview(
            warehouse_id=warehouse_id,
            total_locations=loc_stats.total or 0,
            available_locations=loc_stats.available or 0,
            occupied_locations=loc_stats.occupied or 0,
            reserved_locations=loc_stats.reserved or 0,
            total_dock_doors=dock_stats.total or 0,
            available_docks=dock_stats.available or 0,
            occupied_docks=dock_stats.occupied or 0,
            vehicles_in_yard=vehicles_in_yard,
            pending_appointments_today=appt_stats.pending or 0,
            active_appointments=appt_stats.active or 0,
            completed_appointments_today=appt_stats.completed or 0,
            pending_yard_moves=move_stats.pending or 0,
            active_yard_moves=move_stats.active or 0
        )

    async def get_daily_schedule(
        self,
        warehouse_id: uuid.UUID,
        schedule_date: date
    ) -> DailySchedule:
        """Get dock schedule for a day."""
        # Get all dock doors
        doors, _ = await self.list_dock_doors(warehouse_id)

        schedules = []
        total_inbound = 0
        total_outbound = 0

        for door in doors:
            # Get appointments for this door
            appts, _ = await self.list_appointments(
                warehouse_id=warehouse_id,
                appointment_date=schedule_date,
                dock_door_id=door.id
            )

            schedules.append(DockSchedule(
                dock_door_id=door.id,
                door_number=door.door_number,
                door_name=door.door_name,
                door_type=door.door_type,
                appointments=appts
            ))

            for appt in appts:
                if appt.appointment_type in ['INBOUND', 'LIVE_UNLOAD']:
                    total_inbound += 1
                elif appt.appointment_type in ['OUTBOUND', 'LIVE_LOAD']:
                    total_outbound += 1

        # Get unassigned appointments
        unassigned, _ = await self.list_appointments(
            warehouse_id=warehouse_id,
            appointment_date=schedule_date
        )
        unassigned_appts = [a for a in unassigned if not a.dock_door_id]

        if unassigned_appts:
            schedules.append(DockSchedule(
                dock_door_id=uuid.UUID('00000000-0000-0000-0000-000000000000'),
                door_number="UNASSIGNED",
                door_name="Unassigned Appointments",
                door_type="DUAL",
                appointments=unassigned_appts
            ))

        total_appointments = sum(len(s.appointments) for s in schedules)

        return DailySchedule(
            date=schedule_date,
            warehouse_id=warehouse_id,
            dock_schedules=schedules,
            total_appointments=total_appointments,
            inbound_count=total_inbound,
            outbound_count=total_outbound
        )
