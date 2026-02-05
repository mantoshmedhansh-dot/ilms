"""
Kitting & Assembly Service - Phase 8: Kit Management & Assembly Operations.

Business logic for kitting and assembly operations.
"""
import uuid
from datetime import datetime, timezone, date
from decimal import Decimal
from typing import Optional, List, Tuple, Dict, Any

from sqlalchemy import select, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.kitting import (
    KitDefinition, KitComponent, AssemblyStation, KitWorkOrder, KitBuildRecord,
    KitType, KitStatus, ComponentType, WorkOrderType,
    WorkOrderStatus, WorkOrderPriority, BuildStatus, StationStatus
)
from app.schemas.kitting import (
    KitDefinitionCreate, KitDefinitionUpdate, KitComponentCreate, KitComponentUpdate,
    AssemblyStationCreate, AssemblyStationUpdate, StationAssignment,
    KitWorkOrderCreate, KitWorkOrderUpdate, WorkOrderRelease, WorkOrderCancel,
    KitBuildRecordCreate, BuildStart, BuildComplete, BuildFail, BuildQC,
    KitDashboard, ComponentAvailability
)


class KittingService:
    """Service for kitting and assembly operations."""

    def __init__(self, db: AsyncSession, tenant_id: uuid.UUID):
        self.db = db
        self.tenant_id = tenant_id

    # =========================================================================
    # KIT DEFINITIONS
    # =========================================================================

    async def create_kit(
        self,
        data: KitDefinitionCreate,
        user_id: Optional[uuid.UUID] = None
    ) -> KitDefinition:
        """Create a new kit definition."""
        kit = KitDefinition(
            tenant_id=self.tenant_id,
            kit_sku=data.kit_sku,
            kit_name=data.kit_name,
            description=data.description,
            kit_type=data.kit_type.value,
            status=KitStatus.DRAFT.value,
            product_id=data.product_id,
            warehouse_id=data.warehouse_id,
            assembly_time_minutes=data.assembly_time_minutes,
            labor_cost=data.labor_cost,
            packaging_cost=data.packaging_cost,
            instructions=data.instructions,
            instruction_images=data.instruction_images,
            instruction_video_url=data.instruction_video_url,
            packaging_type=data.packaging_type,
            package_weight=data.package_weight,
            package_length=data.package_length,
            package_width=data.package_width,
            package_height=data.package_height,
            requires_qc=data.requires_qc,
            qc_checklist=data.qc_checklist,
            effective_from=data.effective_from,
            effective_to=data.effective_to,
            notes=data.notes,
            created_by=user_id
        )
        self.db.add(kit)
        await self.db.flush()

        # Add components if provided
        if data.components:
            for seq, comp_data in enumerate(data.components):
                component = KitComponent(
                    tenant_id=self.tenant_id,
                    kit_id=kit.id,
                    product_id=comp_data.product_id,
                    sku=comp_data.sku,
                    product_name=comp_data.product_name,
                    quantity=comp_data.quantity,
                    uom=comp_data.uom,
                    component_type=comp_data.component_type.value,
                    substitute_group=comp_data.substitute_group,
                    substitute_priority=comp_data.substitute_priority,
                    sequence=comp_data.sequence or seq,
                    component_cost=comp_data.component_cost,
                    special_instructions=comp_data.special_instructions,
                    requires_serial=comp_data.requires_serial
                )
                self.db.add(component)

        await self.db.commit()
        await self.db.refresh(kit)
        return kit

    async def get_kit(
        self,
        kit_id: uuid.UUID,
        include_components: bool = True
    ) -> Optional[KitDefinition]:
        """Get kit definition by ID."""
        query = select(KitDefinition).where(
            and_(
                KitDefinition.id == kit_id,
                KitDefinition.tenant_id == self.tenant_id
            )
        )
        if include_components:
            query = query.options(selectinload(KitDefinition.components))

        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def list_kits(
        self,
        warehouse_id: Optional[uuid.UUID] = None,
        kit_type: Optional[KitType] = None,
        status: Optional[KitStatus] = None,
        search: Optional[str] = None,
        skip: int = 0,
        limit: int = 100
    ) -> Tuple[List[KitDefinition], int]:
        """List kit definitions with filters."""
        query = select(KitDefinition).where(
            KitDefinition.tenant_id == self.tenant_id
        )

        if warehouse_id:
            query = query.where(KitDefinition.warehouse_id == warehouse_id)
        if kit_type:
            query = query.where(KitDefinition.kit_type == kit_type.value)
        if status:
            query = query.where(KitDefinition.status == status.value)
        if search:
            query = query.where(
                or_(
                    KitDefinition.kit_sku.ilike(f"%{search}%"),
                    KitDefinition.kit_name.ilike(f"%{search}%")
                )
            )

        # Count
        count_query = select(func.count()).select_from(query.subquery())
        total = await self.db.scalar(count_query) or 0

        # Fetch
        query = query.options(selectinload(KitDefinition.components))
        query = query.order_by(KitDefinition.kit_name).offset(skip).limit(limit)
        result = await self.db.execute(query)
        return list(result.scalars().all()), total

    async def update_kit(
        self,
        kit_id: uuid.UUID,
        data: KitDefinitionUpdate
    ) -> Optional[KitDefinition]:
        """Update kit definition."""
        kit = await self.get_kit(kit_id)
        if not kit:
            return None

        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            if field == "status" and value:
                value = value.value
            elif field == "kit_type" and value:
                value = value.value
            setattr(kit, field, value)

        kit.updated_at = datetime.now(timezone.utc)
        await self.db.commit()
        await self.db.refresh(kit)
        return kit

    async def activate_kit(self, kit_id: uuid.UUID) -> Optional[KitDefinition]:
        """Activate a kit definition."""
        kit = await self.get_kit(kit_id)
        if not kit:
            return None

        kit.status = KitStatus.ACTIVE.value
        kit.updated_at = datetime.now(timezone.utc)
        await self.db.commit()
        await self.db.refresh(kit)
        return kit

    async def deactivate_kit(self, kit_id: uuid.UUID) -> Optional[KitDefinition]:
        """Deactivate a kit definition."""
        kit = await self.get_kit(kit_id)
        if not kit:
            return None

        kit.status = KitStatus.INACTIVE.value
        kit.updated_at = datetime.now(timezone.utc)
        await self.db.commit()
        await self.db.refresh(kit)
        return kit

    # =========================================================================
    # KIT COMPONENTS
    # =========================================================================

    async def add_component(
        self,
        kit_id: uuid.UUID,
        data: KitComponentCreate
    ) -> Optional[KitComponent]:
        """Add component to kit."""
        kit = await self.get_kit(kit_id, include_components=False)
        if not kit:
            return None

        component = KitComponent(
            tenant_id=self.tenant_id,
            kit_id=kit_id,
            product_id=data.product_id,
            sku=data.sku,
            product_name=data.product_name,
            quantity=data.quantity,
            uom=data.uom,
            component_type=data.component_type.value,
            substitute_group=data.substitute_group,
            substitute_priority=data.substitute_priority,
            sequence=data.sequence,
            component_cost=data.component_cost,
            special_instructions=data.special_instructions,
            requires_serial=data.requires_serial
        )
        self.db.add(component)
        await self.db.commit()
        await self.db.refresh(component)
        return component

    async def update_component(
        self,
        component_id: uuid.UUID,
        data: KitComponentUpdate
    ) -> Optional[KitComponent]:
        """Update kit component."""
        query = select(KitComponent).where(
            and_(
                KitComponent.id == component_id,
                KitComponent.tenant_id == self.tenant_id
            )
        )
        result = await self.db.execute(query)
        component = result.scalar_one_or_none()
        if not component:
            return None

        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            if field == "component_type" and value:
                value = value.value
            setattr(component, field, value)

        component.updated_at = datetime.now(timezone.utc)
        await self.db.commit()
        await self.db.refresh(component)
        return component

    async def remove_component(self, component_id: uuid.UUID) -> bool:
        """Remove component from kit."""
        query = select(KitComponent).where(
            and_(
                KitComponent.id == component_id,
                KitComponent.tenant_id == self.tenant_id
            )
        )
        result = await self.db.execute(query)
        component = result.scalar_one_or_none()
        if not component:
            return False

        await self.db.delete(component)
        await self.db.commit()
        return True

    # =========================================================================
    # ASSEMBLY STATIONS
    # =========================================================================

    async def create_station(self, data: AssemblyStationCreate) -> AssemblyStation:
        """Create an assembly station."""
        station = AssemblyStation(
            tenant_id=self.tenant_id,
            warehouse_id=data.warehouse_id,
            station_code=data.station_code,
            station_name=data.station_name,
            status=StationStatus.AVAILABLE.value,
            zone_id=data.zone_id,
            equipment=data.equipment,
            tools_required=data.tools_required,
            max_concurrent_builds=data.max_concurrent_builds,
            notes=data.notes
        )
        self.db.add(station)
        await self.db.commit()
        await self.db.refresh(station)
        return station

    async def get_station(self, station_id: uuid.UUID) -> Optional[AssemblyStation]:
        """Get assembly station by ID."""
        query = select(AssemblyStation).where(
            and_(
                AssemblyStation.id == station_id,
                AssemblyStation.tenant_id == self.tenant_id
            )
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def list_stations(
        self,
        warehouse_id: Optional[uuid.UUID] = None,
        status: Optional[StationStatus] = None,
        is_active: bool = True,
        skip: int = 0,
        limit: int = 100
    ) -> Tuple[List[AssemblyStation], int]:
        """List assembly stations."""
        query = select(AssemblyStation).where(
            and_(
                AssemblyStation.tenant_id == self.tenant_id,
                AssemblyStation.is_active == is_active
            )
        )

        if warehouse_id:
            query = query.where(AssemblyStation.warehouse_id == warehouse_id)
        if status:
            query = query.where(AssemblyStation.status == status.value)

        # Count
        count_query = select(func.count()).select_from(query.subquery())
        total = await self.db.scalar(count_query) or 0

        # Fetch
        query = query.order_by(AssemblyStation.station_code).offset(skip).limit(limit)
        result = await self.db.execute(query)
        return list(result.scalars().all()), total

    async def update_station(
        self,
        station_id: uuid.UUID,
        data: AssemblyStationUpdate
    ) -> Optional[AssemblyStation]:
        """Update assembly station."""
        station = await self.get_station(station_id)
        if not station:
            return None

        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            if field == "status" and value:
                value = value.value
            setattr(station, field, value)

        station.updated_at = datetime.now(timezone.utc)
        await self.db.commit()
        await self.db.refresh(station)
        return station

    async def assign_worker_to_station(
        self,
        station_id: uuid.UUID,
        data: StationAssignment
    ) -> Optional[AssemblyStation]:
        """Assign worker to station."""
        station = await self.get_station(station_id)
        if not station:
            return None

        station.assigned_worker_id = data.worker_id
        station.assigned_at = datetime.now(timezone.utc)
        station.status = StationStatus.OCCUPIED.value
        station.updated_at = datetime.now(timezone.utc)

        await self.db.commit()
        await self.db.refresh(station)
        return station

    async def release_station(
        self,
        station_id: uuid.UUID
    ) -> Optional[AssemblyStation]:
        """Release worker from station."""
        station = await self.get_station(station_id)
        if not station:
            return None

        station.assigned_worker_id = None
        station.assigned_at = None
        station.current_work_order_id = None
        station.status = StationStatus.AVAILABLE.value
        station.updated_at = datetime.now(timezone.utc)

        await self.db.commit()
        await self.db.refresh(station)
        return station

    # =========================================================================
    # WORK ORDERS
    # =========================================================================

    async def _generate_work_order_number(self) -> str:
        """Generate unique work order number."""
        today = datetime.now(timezone.utc).strftime("%Y%m%d")
        prefix = f"WO-{today}"

        query = select(func.count(KitWorkOrder.id)).where(
            KitWorkOrder.work_order_number.like(f"{prefix}%")
        )
        count = await self.db.scalar(query) or 0
        return f"{prefix}-{count + 1:04d}"

    async def create_work_order(
        self,
        data: KitWorkOrderCreate,
        user_id: Optional[uuid.UUID] = None
    ) -> KitWorkOrder:
        """Create a kit work order."""
        # Get kit details for cost estimation
        kit = await self.get_kit(data.kit_id)
        estimated_hours = None
        estimated_cost = Decimal("0")

        if kit:
            assembly_time = kit.assembly_time_minutes * data.quantity_ordered
            estimated_hours = Decimal(str(assembly_time / 60))
            estimated_cost = (kit.labor_cost + kit.packaging_cost) * data.quantity_ordered

        work_order = KitWorkOrder(
            tenant_id=self.tenant_id,
            work_order_number=await self._generate_work_order_number(),
            work_order_type=data.work_order_type.value,
            status=WorkOrderStatus.DRAFT.value,
            priority=data.priority.value,
            kit_id=data.kit_id,
            warehouse_id=data.warehouse_id,
            station_id=data.station_id,
            quantity_ordered=data.quantity_ordered,
            quantity_remaining=data.quantity_ordered,
            scheduled_date=data.scheduled_date,
            due_date=data.due_date,
            order_id=data.order_id,
            assigned_to=data.assigned_to,
            destination_bin_id=data.destination_bin_id,
            estimated_hours=estimated_hours,
            estimated_cost=estimated_cost,
            notes=data.notes,
            created_by=user_id
        )
        self.db.add(work_order)
        await self.db.commit()
        await self.db.refresh(work_order)
        return work_order

    async def get_work_order(
        self,
        work_order_id: uuid.UUID,
        include_builds: bool = False
    ) -> Optional[KitWorkOrder]:
        """Get work order by ID."""
        query = select(KitWorkOrder).where(
            and_(
                KitWorkOrder.id == work_order_id,
                KitWorkOrder.tenant_id == self.tenant_id
            )
        )
        if include_builds:
            query = query.options(selectinload(KitWorkOrder.builds))

        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def list_work_orders(
        self,
        warehouse_id: Optional[uuid.UUID] = None,
        kit_id: Optional[uuid.UUID] = None,
        status: Optional[WorkOrderStatus] = None,
        work_order_type: Optional[WorkOrderType] = None,
        priority: Optional[WorkOrderPriority] = None,
        from_date: Optional[date] = None,
        to_date: Optional[date] = None,
        skip: int = 0,
        limit: int = 100
    ) -> Tuple[List[KitWorkOrder], int]:
        """List work orders with filters."""
        query = select(KitWorkOrder).where(
            KitWorkOrder.tenant_id == self.tenant_id
        )

        if warehouse_id:
            query = query.where(KitWorkOrder.warehouse_id == warehouse_id)
        if kit_id:
            query = query.where(KitWorkOrder.kit_id == kit_id)
        if status:
            query = query.where(KitWorkOrder.status == status.value)
        if work_order_type:
            query = query.where(KitWorkOrder.work_order_type == work_order_type.value)
        if priority:
            query = query.where(KitWorkOrder.priority == priority.value)
        if from_date:
            query = query.where(KitWorkOrder.scheduled_date >= from_date)
        if to_date:
            query = query.where(KitWorkOrder.scheduled_date <= to_date)

        # Count
        count_query = select(func.count()).select_from(query.subquery())
        total = await self.db.scalar(count_query) or 0

        # Fetch
        query = query.order_by(
            KitWorkOrder.priority.desc(),
            KitWorkOrder.scheduled_date
        ).offset(skip).limit(limit)
        result = await self.db.execute(query)
        return list(result.scalars().all()), total

    async def update_work_order(
        self,
        work_order_id: uuid.UUID,
        data: KitWorkOrderUpdate
    ) -> Optional[KitWorkOrder]:
        """Update work order."""
        work_order = await self.get_work_order(work_order_id)
        if not work_order:
            return None

        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            if field == "priority" and value:
                value = value.value
            setattr(work_order, field, value)

        work_order.updated_at = datetime.now(timezone.utc)
        await self.db.commit()
        await self.db.refresh(work_order)
        return work_order

    async def release_work_order(
        self,
        work_order_id: uuid.UUID,
        data: Optional[WorkOrderRelease] = None
    ) -> Optional[KitWorkOrder]:
        """Release work order for production."""
        work_order = await self.get_work_order(work_order_id)
        if not work_order or work_order.status not in [
            WorkOrderStatus.DRAFT.value, WorkOrderStatus.PENDING.value
        ]:
            return None

        work_order.status = WorkOrderStatus.RELEASED.value
        if data:
            if data.station_id:
                work_order.station_id = data.station_id
            if data.assigned_to:
                work_order.assigned_to = data.assigned_to

        work_order.updated_at = datetime.now(timezone.utc)
        await self.db.commit()
        await self.db.refresh(work_order)
        return work_order

    async def start_work_order(
        self,
        work_order_id: uuid.UUID
    ) -> Optional[KitWorkOrder]:
        """Start work on a work order."""
        work_order = await self.get_work_order(work_order_id)
        if not work_order or work_order.status != WorkOrderStatus.RELEASED.value:
            return None

        work_order.status = WorkOrderStatus.IN_PROGRESS.value
        work_order.started_at = datetime.now(timezone.utc)
        work_order.updated_at = datetime.now(timezone.utc)

        # Update station if assigned
        if work_order.station_id:
            station = await self.get_station(work_order.station_id)
            if station:
                station.current_work_order_id = work_order_id
                station.status = StationStatus.OCCUPIED.value

        await self.db.commit()
        await self.db.refresh(work_order)
        return work_order

    async def complete_work_order(
        self,
        work_order_id: uuid.UUID
    ) -> Optional[KitWorkOrder]:
        """Complete a work order."""
        work_order = await self.get_work_order(work_order_id)
        if not work_order or work_order.status != WorkOrderStatus.IN_PROGRESS.value:
            return None

        work_order.status = WorkOrderStatus.COMPLETED.value
        work_order.completed_at = datetime.now(timezone.utc)

        # Calculate actual hours
        if work_order.started_at:
            duration = work_order.completed_at - work_order.started_at
            work_order.actual_hours = Decimal(str(duration.total_seconds() / 3600))

        work_order.updated_at = datetime.now(timezone.utc)

        # Release station
        if work_order.station_id:
            station = await self.get_station(work_order.station_id)
            if station:
                station.current_work_order_id = None

        await self.db.commit()
        await self.db.refresh(work_order)
        return work_order

    async def cancel_work_order(
        self,
        work_order_id: uuid.UUID,
        data: WorkOrderCancel
    ) -> Optional[KitWorkOrder]:
        """Cancel a work order."""
        work_order = await self.get_work_order(work_order_id)
        if not work_order or work_order.status in [
            WorkOrderStatus.COMPLETED.value, WorkOrderStatus.CANCELLED.value
        ]:
            return None

        work_order.status = WorkOrderStatus.CANCELLED.value
        work_order.cancellation_reason = data.reason
        work_order.updated_at = datetime.now(timezone.utc)

        # Release station
        if work_order.station_id:
            station = await self.get_station(work_order.station_id)
            if station and station.current_work_order_id == work_order_id:
                station.current_work_order_id = None

        await self.db.commit()
        await self.db.refresh(work_order)
        return work_order

    # =========================================================================
    # BUILD RECORDS
    # =========================================================================

    async def create_build(
        self,
        data: KitBuildRecordCreate,
        user_id: Optional[uuid.UUID] = None
    ) -> Optional[KitBuildRecord]:
        """Create a new build record."""
        work_order = await self.get_work_order(data.work_order_id, include_builds=True)
        if not work_order:
            return None

        # Get kit info
        kit = await self.get_kit(work_order.kit_id, include_components=False)
        if not kit:
            return None

        # Determine build number
        build_number = len(work_order.builds) + 1 if work_order.builds else 1

        build = KitBuildRecord(
            tenant_id=self.tenant_id,
            work_order_id=data.work_order_id,
            build_number=build_number,
            status=BuildStatus.PENDING.value,
            kit_id=work_order.kit_id,
            kit_sku=kit.kit_sku,
            serial_number=data.serial_number,
            lpn=data.lpn,
            station_id=data.station_id,
            notes=data.notes
        )
        self.db.add(build)
        await self.db.commit()
        await self.db.refresh(build)
        return build

    async def get_build(self, build_id: uuid.UUID) -> Optional[KitBuildRecord]:
        """Get build record by ID."""
        query = select(KitBuildRecord).where(
            and_(
                KitBuildRecord.id == build_id,
                KitBuildRecord.tenant_id == self.tenant_id
            )
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def list_builds(
        self,
        work_order_id: Optional[uuid.UUID] = None,
        status: Optional[BuildStatus] = None,
        station_id: Optional[uuid.UUID] = None,
        from_date: Optional[date] = None,
        to_date: Optional[date] = None,
        skip: int = 0,
        limit: int = 100
    ) -> Tuple[List[KitBuildRecord], int]:
        """List build records."""
        query = select(KitBuildRecord).where(
            KitBuildRecord.tenant_id == self.tenant_id
        )

        if work_order_id:
            query = query.where(KitBuildRecord.work_order_id == work_order_id)
        if status:
            query = query.where(KitBuildRecord.status == status.value)
        if station_id:
            query = query.where(KitBuildRecord.station_id == station_id)
        if from_date:
            query = query.where(func.date(KitBuildRecord.created_at) >= from_date)
        if to_date:
            query = query.where(func.date(KitBuildRecord.created_at) <= to_date)

        # Count
        count_query = select(func.count()).select_from(query.subquery())
        total = await self.db.scalar(count_query) or 0

        # Fetch
        query = query.order_by(KitBuildRecord.created_at.desc()).offset(skip).limit(limit)
        result = await self.db.execute(query)
        return list(result.scalars().all()), total

    async def start_build(
        self,
        build_id: uuid.UUID,
        data: BuildStart,
        user_id: uuid.UUID
    ) -> Optional[KitBuildRecord]:
        """Start a build."""
        build = await self.get_build(build_id)
        if not build or build.status != BuildStatus.PENDING.value:
            return None

        build.status = BuildStatus.ASSEMBLING.value
        build.started_at = datetime.now(timezone.utc)
        build.built_by = user_id

        if data.station_id:
            build.station_id = data.station_id
        if data.serial_number:
            build.serial_number = data.serial_number
        if data.lpn:
            build.lpn = data.lpn

        # Update station
        if build.station_id:
            station = await self.get_station(build.station_id)
            if station:
                station.current_builds += 1

        await self.db.commit()
        await self.db.refresh(build)
        return build

    async def complete_build(
        self,
        build_id: uuid.UUID,
        data: BuildComplete,
        user_id: uuid.UUID
    ) -> Optional[KitBuildRecord]:
        """Complete a build."""
        build = await self.get_build(build_id)
        if not build or build.status != BuildStatus.ASSEMBLING.value:
            return None

        now = datetime.now(timezone.utc)
        build.components_used = data.components_used
        build.destination_bin_id = data.destination_bin_id
        build.notes = data.notes
        build.completed_at = now

        # Calculate build time
        if build.started_at:
            duration = now - build.started_at
            build.build_time_minutes = int(duration.total_seconds() / 60)

        # Get kit to check if QC required
        work_order = await self.get_work_order(build.work_order_id)
        if work_order:
            kit = await self.get_kit(work_order.kit_id, include_components=False)
            if kit and kit.requires_qc:
                build.status = BuildStatus.QC_PENDING.value
            else:
                build.status = BuildStatus.COMPLETED.value
                # Update work order
                work_order.quantity_completed += 1
                work_order.quantity_remaining -= 1

                # Check if work order is complete
                if work_order.quantity_remaining == 0:
                    work_order.status = WorkOrderStatus.COMPLETED.value
                    work_order.completed_at = now

                # Update kit stats
                if kit:
                    kit.total_builds += 1
                    if build.build_time_minutes:
                        if kit.avg_build_time_minutes:
                            kit.avg_build_time_minutes = (
                                kit.avg_build_time_minutes + Decimal(str(build.build_time_minutes))
                            ) / 2
                        else:
                            kit.avg_build_time_minutes = Decimal(str(build.build_time_minutes))

        # Update station
        if build.station_id:
            station = await self.get_station(build.station_id)
            if station:
                station.current_builds = max(0, station.current_builds - 1)
                station.total_builds_today += 1

        await self.db.commit()
        await self.db.refresh(build)
        return build

    async def fail_build(
        self,
        build_id: uuid.UUID,
        data: BuildFail
    ) -> Optional[KitBuildRecord]:
        """Mark a build as failed."""
        build = await self.get_build(build_id)
        if not build or build.status == BuildStatus.COMPLETED.value:
            return None

        build.status = BuildStatus.FAILED.value
        build.failure_reason = data.failure_reason
        build.completed_at = datetime.now(timezone.utc)
        if data.components_used:
            build.components_used = data.components_used

        # Update work order
        work_order = await self.get_work_order(build.work_order_id)
        if work_order:
            work_order.quantity_failed += 1
            work_order.quantity_remaining -= 1

        # Update station
        if build.station_id:
            station = await self.get_station(build.station_id)
            if station:
                station.current_builds = max(0, station.current_builds - 1)

        await self.db.commit()
        await self.db.refresh(build)
        return build

    async def qc_build(
        self,
        build_id: uuid.UUID,
        data: BuildQC,
        user_id: uuid.UUID
    ) -> Optional[KitBuildRecord]:
        """Record QC results for a build."""
        build = await self.get_build(build_id)
        if not build or build.status != BuildStatus.QC_PENDING.value:
            return None

        build.qc_status = data.qc_status
        build.qc_notes = data.qc_notes
        build.qc_by = user_id
        build.qc_at = datetime.now(timezone.utc)

        if data.qc_status.upper() in ["PASS", "PASSED", "APPROVED"]:
            build.status = BuildStatus.COMPLETED.value
            # Update work order
            work_order = await self.get_work_order(build.work_order_id)
            if work_order:
                work_order.quantity_completed += 1
                work_order.quantity_remaining -= 1
        else:
            build.status = BuildStatus.FAILED.value
            work_order = await self.get_work_order(build.work_order_id)
            if work_order:
                work_order.quantity_failed += 1
                work_order.quantity_remaining -= 1

        await self.db.commit()
        await self.db.refresh(build)
        return build

    # =========================================================================
    # DASHBOARD & ANALYTICS
    # =========================================================================

    async def get_dashboard(
        self,
        warehouse_id: uuid.UUID,
        from_date: Optional[date] = None,
        to_date: Optional[date] = None
    ) -> KitDashboard:
        """Get kitting dashboard statistics."""
        if not from_date:
            from_date = date.today()
        if not to_date:
            to_date = date.today()

        # Kit counts
        total_kits = await self.db.scalar(
            select(func.count(KitDefinition.id)).where(
                and_(
                    KitDefinition.tenant_id == self.tenant_id,
                    KitDefinition.warehouse_id == warehouse_id
                )
            )
        ) or 0

        active_kits = await self.db.scalar(
            select(func.count(KitDefinition.id)).where(
                and_(
                    KitDefinition.tenant_id == self.tenant_id,
                    KitDefinition.warehouse_id == warehouse_id,
                    KitDefinition.status == KitStatus.ACTIVE.value
                )
            )
        ) or 0

        # Station counts
        total_stations = await self.db.scalar(
            select(func.count(AssemblyStation.id)).where(
                and_(
                    AssemblyStation.tenant_id == self.tenant_id,
                    AssemblyStation.warehouse_id == warehouse_id,
                    AssemblyStation.is_active == True
                )
            )
        ) or 0

        available_stations = await self.db.scalar(
            select(func.count(AssemblyStation.id)).where(
                and_(
                    AssemblyStation.tenant_id == self.tenant_id,
                    AssemblyStation.warehouse_id == warehouse_id,
                    AssemblyStation.status == StationStatus.AVAILABLE.value,
                    AssemblyStation.is_active == True
                )
            )
        ) or 0

        occupied_stations = await self.db.scalar(
            select(func.count(AssemblyStation.id)).where(
                and_(
                    AssemblyStation.tenant_id == self.tenant_id,
                    AssemblyStation.warehouse_id == warehouse_id,
                    AssemblyStation.status == StationStatus.OCCUPIED.value,
                    AssemblyStation.is_active == True
                )
            )
        ) or 0

        # Work order stats
        pending_work_orders = await self.db.scalar(
            select(func.count(KitWorkOrder.id)).where(
                and_(
                    KitWorkOrder.tenant_id == self.tenant_id,
                    KitWorkOrder.warehouse_id == warehouse_id,
                    KitWorkOrder.status.in_([
                        WorkOrderStatus.DRAFT.value,
                        WorkOrderStatus.PENDING.value,
                        WorkOrderStatus.RELEASED.value
                    ])
                )
            )
        ) or 0

        in_progress_work_orders = await self.db.scalar(
            select(func.count(KitWorkOrder.id)).where(
                and_(
                    KitWorkOrder.tenant_id == self.tenant_id,
                    KitWorkOrder.warehouse_id == warehouse_id,
                    KitWorkOrder.status == WorkOrderStatus.IN_PROGRESS.value
                )
            )
        ) or 0

        completed_today = await self.db.scalar(
            select(func.count(KitWorkOrder.id)).where(
                and_(
                    KitWorkOrder.tenant_id == self.tenant_id,
                    KitWorkOrder.warehouse_id == warehouse_id,
                    KitWorkOrder.status == WorkOrderStatus.COMPLETED.value,
                    func.date(KitWorkOrder.completed_at) == date.today()
                )
            )
        ) or 0

        quantity_built_today = await self.db.scalar(
            select(func.count(KitBuildRecord.id)).where(
                and_(
                    KitBuildRecord.tenant_id == self.tenant_id,
                    KitBuildRecord.status == BuildStatus.COMPLETED.value,
                    func.date(KitBuildRecord.completed_at) == date.today()
                )
            )
        ) or 0

        # Performance
        avg_build_time = await self.db.scalar(
            select(func.avg(KitBuildRecord.build_time_minutes)).where(
                and_(
                    KitBuildRecord.tenant_id == self.tenant_id,
                    KitBuildRecord.status == BuildStatus.COMPLETED.value,
                    func.date(KitBuildRecord.completed_at) >= from_date,
                    func.date(KitBuildRecord.completed_at) <= to_date
                )
            )
        )

        # Work orders with shortage
        work_orders_with_shortage = await self.db.scalar(
            select(func.count(KitWorkOrder.id)).where(
                and_(
                    KitWorkOrder.tenant_id == self.tenant_id,
                    KitWorkOrder.warehouse_id == warehouse_id,
                    KitWorkOrder.components_available == False,
                    KitWorkOrder.status.notin_([
                        WorkOrderStatus.COMPLETED.value,
                        WorkOrderStatus.CANCELLED.value
                    ])
                )
            )
        ) or 0

        # Recent work orders
        recent_wo_query = select(KitWorkOrder).where(
            and_(
                KitWorkOrder.tenant_id == self.tenant_id,
                KitWorkOrder.warehouse_id == warehouse_id
            )
        ).order_by(KitWorkOrder.created_at.desc()).limit(5)
        recent_wo_result = await self.db.execute(recent_wo_query)
        recent_work_orders = list(recent_wo_result.scalars().all())

        # Recent builds
        recent_builds_query = select(KitBuildRecord).where(
            KitBuildRecord.tenant_id == self.tenant_id
        ).order_by(KitBuildRecord.created_at.desc()).limit(10)
        recent_builds_result = await self.db.execute(recent_builds_query)
        recent_builds = list(recent_builds_result.scalars().all())

        return KitDashboard(
            total_kits=total_kits,
            active_kits=active_kits,
            total_stations=total_stations,
            available_stations=available_stations,
            occupied_stations=occupied_stations,
            pending_work_orders=pending_work_orders,
            in_progress_work_orders=in_progress_work_orders,
            completed_today=completed_today,
            quantity_built_today=quantity_built_today,
            avg_build_time_minutes=Decimal(str(avg_build_time)) if avg_build_time else None,
            builds_per_hour=Decimal(str(60 / float(avg_build_time))) if avg_build_time and avg_build_time > 0 else None,
            work_orders_with_shortage=work_orders_with_shortage,
            recent_work_orders=recent_work_orders,
            recent_builds=recent_builds
        )
