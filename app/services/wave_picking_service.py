"""
Wave Picking and Task Interleaving Service.

Implements enterprise-grade wave management and task interleaving:
- Wave creation with multiple strategies (carrier cutoff, zone, priority)
- Intelligent task interleaving to minimize travel time
- Pick route optimization
- Slot optimization analysis
"""
import uuid
import math
from datetime import datetime, timezone, time, date, timedelta
from decimal import Decimal
from typing import Optional, List, Dict, Any, Tuple
import logging

from sqlalchemy import select, func, and_, or_, update, case
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.wms_advanced import (
    PickWave, WavePicklist, WarehouseTask, SlotScore, CrossDock, WorkerLocation,
    WaveType, WaveStatus, TaskType, TaskStatus, TaskPriority, SlotClass
)
from app.models.picklist import Picklist, PicklistItem, PicklistStatus, PicklistType
from app.models.order import Order, OrderStatus
from app.models.warehouse import Warehouse
from app.models.wms import WarehouseZone, WarehouseBin
from app.models.inventory import InventorySummary
from app.schemas.wms_advanced import (
    WaveCreate, WaveUpdate, WaveReleaseRequest, WaveReleaseResponse,
    TaskCreate, TaskCompleteRequest, NextTaskRequest, NextTaskResponse,
    SlotOptimizationRequest, SlotOptimizationResult, TaskResponse
)

logger = logging.getLogger(__name__)


class WavePickingService:
    """
    Advanced wave picking service with optimization.
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    # ========================================================================
    # WAVE MANAGEMENT
    # ========================================================================

    async def create_wave(
        self,
        data: WaveCreate,
        tenant_id: uuid.UUID,
        created_by: Optional[uuid.UUID] = None
    ) -> PickWave:
        """
        Create a new picking wave.

        If auto_select_orders is True, automatically selects eligible orders
        based on wave configuration (carrier cutoff, priority, zone, etc.).
        """
        # Generate wave number
        wave_number = await self._generate_wave_number(tenant_id)

        # Create wave
        wave = PickWave(
            tenant_id=tenant_id,
            wave_number=wave_number,
            name=data.name,
            warehouse_id=data.warehouse_id,
            wave_type=data.wave_type.value,
            status=WaveStatus.DRAFT.value,
            carrier_id=data.carrier_id,
            cutoff_time=data.cutoff_time,
            cutoff_date=data.cutoff_date or date.today(),
            zone_ids={"ids": [str(z) for z in data.zone_ids]} if data.zone_ids else None,
            channel_ids={"ids": [str(c) for c in data.channel_ids]} if data.channel_ids else None,
            customer_types={"types": data.customer_types} if data.customer_types else None,
            min_priority=data.min_priority,
            max_priority=data.max_priority,
            optimize_route=data.optimize_route,
            group_by_zone=data.group_by_zone,
            max_picks_per_trip=data.max_picks_per_trip,
            max_weight_per_trip=data.max_weight_per_trip,
            created_by=created_by,
        )
        self.db.add(wave)
        await self.db.flush()

        # Select orders for wave
        if data.auto_select_orders:
            orders = await self._select_orders_for_wave(wave, data)
        elif data.order_ids:
            orders = await self._get_orders_by_ids(data.order_ids)
        else:
            orders = []

        # Create picklists from orders
        if orders:
            await self._create_wave_picklists(wave, orders)

        # Update wave metrics
        await self._update_wave_metrics(wave)

        # Auto-release if requested
        if data.auto_release and wave.total_orders > 0:
            await self.release_wave(wave.id, WaveReleaseRequest())

        await self.db.commit()
        await self.db.refresh(wave)

        logger.info(
            f"Created wave {wave_number} with {wave.total_orders} orders, "
            f"{wave.total_picklists} picklists"
        )

        return wave

    async def get_wave(self, wave_id: uuid.UUID) -> Optional[PickWave]:
        """Get wave by ID with relationships."""
        stmt = (
            select(PickWave)
            .options(
                selectinload(PickWave.picklists).selectinload(WavePicklist.picklist),
                selectinload(PickWave.warehouse),
                selectinload(PickWave.carrier),
            )
            .where(PickWave.id == wave_id)
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_waves(
        self,
        tenant_id: Optional[uuid.UUID] = None,
        warehouse_id: Optional[uuid.UUID] = None,
        status: Optional[str] = None,
        wave_type: Optional[str] = None,
        page: int = 1,
        size: int = 20,
    ) -> Tuple[List[PickWave], int]:
        """Get waves with filters and pagination."""
        query = select(PickWave)

        if tenant_id:
            query = query.where(PickWave.tenant_id == tenant_id)
        if warehouse_id:
            query = query.where(PickWave.warehouse_id == warehouse_id)
        if status:
            query = query.where(PickWave.status == status)
        if wave_type:
            query = query.where(PickWave.wave_type == wave_type)

        # Count
        count_query = select(func.count()).select_from(query.subquery())
        total = (await self.db.execute(count_query)).scalar() or 0

        # Paginate
        query = (
            query
            .order_by(PickWave.created_at.desc())
            .offset((page - 1) * size)
            .limit(size)
        )
        result = await self.db.execute(query)
        waves = list(result.scalars().all())

        return waves, total

    async def release_wave(
        self,
        wave_id: uuid.UUID,
        request: WaveReleaseRequest,
        released_by: Optional[uuid.UUID] = None
    ) -> WaveReleaseResponse:
        """
        Release wave to warehouse floor.

        Creates tasks for each picklist item and optionally assigns pickers.
        """
        wave = await self.get_wave(wave_id)
        if not wave:
            raise ValueError("Wave not found")

        if wave.status not in [WaveStatus.DRAFT.value, WaveStatus.PLANNED.value]:
            raise ValueError(f"Cannot release wave in status: {wave.status}")

        # Create tasks for all picklist items
        tasks_created = 0
        for wave_picklist in wave.picklists:
            picklist = wave_picklist.picklist
            if picklist:
                tasks_created += await self._create_tasks_for_picklist(
                    wave, picklist, wave_picklist.sequence
                )

        # Assign pickers if provided
        pickers_assigned = 0
        if request.assign_pickers:
            pickers_assigned = await self._assign_pickers_to_wave(
                wave, request.assign_pickers
            )
            wave.assigned_pickers = {"ids": [str(p) for p in request.assign_pickers]}

        # Update wave status
        wave.status = WaveStatus.RELEASED.value
        wave.released_at = datetime.now(timezone.utc)
        wave.released_by = released_by

        # Update picklist statuses
        for wave_picklist in wave.picklists:
            if wave_picklist.picklist:
                wave_picklist.picklist.status = PicklistStatus.PENDING.value

        await self.db.commit()

        logger.info(
            f"Released wave {wave.wave_number}: {tasks_created} tasks, "
            f"{pickers_assigned} pickers assigned"
        )

        return WaveReleaseResponse(
            wave_id=wave.id,
            wave_number=wave.wave_number,
            status=wave.status,
            picklists_created=wave.total_picklists,
            tasks_created=tasks_created,
            pickers_assigned=pickers_assigned,
            released_at=wave.released_at,
        )

    async def complete_wave(self, wave_id: uuid.UUID) -> PickWave:
        """Mark wave as completed."""
        wave = await self.get_wave(wave_id)
        if not wave:
            raise ValueError("Wave not found")

        wave.status = WaveStatus.COMPLETED.value
        wave.completed_at = datetime.now(timezone.utc)

        await self.db.commit()
        return wave

    async def cancel_wave(
        self,
        wave_id: uuid.UUID,
        reason: str
    ) -> PickWave:
        """Cancel a wave."""
        wave = await self.get_wave(wave_id)
        if not wave:
            raise ValueError("Wave not found")

        if wave.status == WaveStatus.COMPLETED.value:
            raise ValueError("Cannot cancel completed wave")

        wave.status = WaveStatus.CANCELLED.value
        wave.cancelled_at = datetime.now(timezone.utc)
        wave.cancellation_reason = reason

        # Cancel associated tasks
        await self.db.execute(
            update(WarehouseTask)
            .where(
                and_(
                    WarehouseTask.wave_id == wave_id,
                    WarehouseTask.status.in_([
                        TaskStatus.PENDING.value,
                        TaskStatus.ASSIGNED.value
                    ])
                )
            )
            .values(status=TaskStatus.CANCELLED.value)
        )

        await self.db.commit()
        return wave

    # ========================================================================
    # TASK INTERLEAVING
    # ========================================================================

    async def get_next_task(
        self,
        request: NextTaskRequest,
        tenant_id: uuid.UUID
    ) -> NextTaskResponse:
        """
        Get the optimal next task for a worker using task interleaving.

        Considers:
        - Task priority and SLA
        - Worker's current location
        - Travel distance minimization
        - Task type preferences
        """
        # Get worker's current location
        worker_loc = await self._get_worker_location(request.worker_id, tenant_id)

        # Build task query
        query = (
            select(WarehouseTask)
            .where(
                and_(
                    WarehouseTask.tenant_id == tenant_id,
                    WarehouseTask.status == TaskStatus.PENDING.value,
                    or_(
                        WarehouseTask.assigned_to.is_(None),
                        WarehouseTask.assigned_to == request.worker_id
                    )
                )
            )
        )

        # Filter by task types if specified
        if request.task_types:
            query = query.where(
                WarehouseTask.task_type.in_([t.value for t in request.task_types])
            )

        # Filter by equipment if specified
        if request.equipment_type:
            query = query.where(
                or_(
                    WarehouseTask.equipment_type.is_(None),
                    WarehouseTask.equipment_type == request.equipment_type
                )
            )

        # Get pending tasks
        result = await self.db.execute(query.limit(100))
        pending_tasks = list(result.scalars().all())

        if not pending_tasks:
            return NextTaskResponse(
                task=None,
                reason="No pending tasks available"
            )

        # Score tasks based on priority and travel distance
        scored_tasks = []
        for task in pending_tasks:
            score = await self._calculate_task_score(
                task, worker_loc, request.current_zone_id, request.current_bin_code
            )
            scored_tasks.append((task, score))

        # Sort by score (higher = better)
        scored_tasks.sort(key=lambda x: x[1], reverse=True)

        # Get best task
        best_task, best_score = scored_tasks[0]

        # Assign task to worker
        best_task.assigned_to = request.worker_id
        best_task.assigned_at = datetime.now(timezone.utc)
        best_task.status = TaskStatus.ASSIGNED.value

        # Update worker location
        if worker_loc:
            worker_loc.current_task_id = best_task.id
            worker_loc.last_scan_at = datetime.now(timezone.utc)

        await self.db.commit()
        await self.db.refresh(best_task)

        # Get alternatives
        alternatives = [
            TaskResponse.model_validate(t) for t, s in scored_tasks[1:4]
        ]

        # Estimate travel
        travel_distance = await self._estimate_travel_distance(
            request.current_bin_code, best_task.source_bin_code
        )

        return NextTaskResponse(
            task=TaskResponse.model_validate(best_task),
            travel_distance_meters=travel_distance,
            estimated_travel_time_seconds=travel_distance // 2 if travel_distance else None,
            reason=self._get_task_selection_reason(best_task, best_score),
            alternative_tasks=alternatives if alternatives else None,
        )

    async def start_task(
        self,
        task_id: uuid.UUID,
        worker_id: uuid.UUID,
        equipment_type: Optional[str] = None,
        equipment_id: Optional[str] = None
    ) -> WarehouseTask:
        """Start working on a task."""
        task = await self._get_task(task_id)
        if not task:
            raise ValueError("Task not found")

        if task.assigned_to and task.assigned_to != worker_id:
            raise ValueError("Task assigned to different worker")

        task.status = TaskStatus.IN_PROGRESS.value
        task.started_at = datetime.now(timezone.utc)
        task.assigned_to = worker_id
        task.assigned_at = task.assigned_at or datetime.now(timezone.utc)

        if equipment_type:
            task.equipment_type = equipment_type
            task.equipment_id = equipment_id

        # Update wave status if first task started
        if task.wave_id:
            wave = await self.get_wave(task.wave_id)
            if wave and wave.status == WaveStatus.RELEASED.value:
                wave.status = WaveStatus.IN_PROGRESS.value
                wave.started_at = datetime.now(timezone.utc)

        await self.db.commit()
        await self.db.refresh(task)
        return task

    async def complete_task(
        self,
        task_id: uuid.UUID,
        worker_id: uuid.UUID,
        data: TaskCompleteRequest
    ) -> WarehouseTask:
        """Complete a task."""
        task = await self._get_task(task_id)
        if not task:
            raise ValueError("Task not found")

        if task.assigned_to != worker_id:
            raise ValueError("Task not assigned to this worker")

        now = datetime.now(timezone.utc)

        task.status = TaskStatus.COMPLETED.value
        task.completed_at = now
        task.quantity_completed = data.quantity_completed
        task.quantity_exception = data.quantity_exception

        if data.exception_reason:
            task.exception_reason = data.exception_reason

        if data.destination_bin_id:
            task.destination_bin_id = data.destination_bin_id

        if data.notes:
            task.notes = data.notes

        # Calculate performance metrics
        if task.started_at:
            task.total_time_seconds = int((now - task.started_at).total_seconds())
            if task.assigned_at and task.started_at > task.assigned_at:
                task.travel_time_seconds = int((task.started_at - task.assigned_at).total_seconds())
                task.execution_time_seconds = task.total_time_seconds - task.travel_time_seconds

        # Update picklist if this is a pick task
        if task.task_type == TaskType.PICK.value and task.picklist_item_id:
            await self._update_picklist_item(task, data)

        # Update wave metrics
        if task.wave_id:
            await self._check_wave_completion(task.wave_id)

        # Update worker stats
        await self._update_worker_stats(worker_id, task)

        await self.db.commit()
        await self.db.refresh(task)

        logger.info(
            f"Task {task.task_number} completed by worker {worker_id}: "
            f"{data.quantity_completed}/{task.quantity_required}"
        )

        return task

    async def pause_task(self, task_id: uuid.UUID, reason: str) -> WarehouseTask:
        """Pause a task."""
        task = await self._get_task(task_id)
        if not task:
            raise ValueError("Task not found")

        task.status = TaskStatus.PAUSED.value
        task.paused_at = datetime.now(timezone.utc)
        task.notes = (task.notes or "") + f"\nPaused: {reason}"

        await self.db.commit()
        return task

    # ========================================================================
    # SLOT OPTIMIZATION
    # ========================================================================

    async def run_slot_optimization(
        self,
        request: SlotOptimizationRequest,
        tenant_id: uuid.UUID
    ) -> SlotOptimizationResult:
        """
        Run slot optimization analysis.

        Analyzes pick frequency and recommends optimal bin placements.
        """
        analysis_start = date.today() - timedelta(days=request.analysis_days)
        analysis_end = date.today()

        # Get pick history
        pick_data = await self._get_pick_history(
            tenant_id,
            request.warehouse_id,
            analysis_start,
            analysis_end
        )

        # Calculate velocity scores
        total_picks = sum(p['picks'] for p in pick_data)

        # ABC classification thresholds
        thresholds = request.abc_thresholds or {"A": 0.8, "B": 0.95}

        # Sort by picks descending
        pick_data.sort(key=lambda x: x['picks'], reverse=True)

        # Classify products
        cumulative = 0
        results = []

        for item in pick_data:
            if item['picks'] < request.min_picks_threshold:
                velocity_class = SlotClass.D.value
            else:
                cumulative += item['picks']
                pct = cumulative / total_picks if total_picks > 0 else 0

                if pct <= thresholds["A"]:
                    velocity_class = SlotClass.A.value
                elif pct <= thresholds["B"]:
                    velocity_class = SlotClass.B.value
                else:
                    velocity_class = SlotClass.C.value

            # Calculate scores
            velocity_score = Decimal(str(min(100, (item['picks'] / max(1, total_picks / len(pick_data))) * 100)))

            # Update or create slot score
            slot_score = await self._update_slot_score(
                tenant_id,
                item['product_id'],
                item.get('variant_id'),
                item['sku'],
                request.warehouse_id,
                velocity_class,
                item['picks'],
                item['quantity'],
                velocity_score,
                analysis_start,
                analysis_end
            )
            results.append(slot_score)

        # Count by class
        class_counts = {
            SlotClass.A.value: 0,
            SlotClass.B.value: 0,
            SlotClass.C.value: 0,
            SlotClass.D.value: 0
        }
        for r in results:
            class_counts[r.velocity_class] = class_counts.get(r.velocity_class, 0) + 1

        # Find products needing relocation
        relocation_needed = [r for r in results if r.needs_relocation]

        await self.db.commit()

        return SlotOptimizationResult(
            warehouse_id=request.warehouse_id,
            analysis_period_days=request.analysis_days,
            total_products_analyzed=len(results),
            products_needing_relocation=len(relocation_needed),
            class_a_count=class_counts[SlotClass.A.value],
            class_b_count=class_counts[SlotClass.B.value],
            class_c_count=class_counts[SlotClass.C.value],
            class_d_count=class_counts[SlotClass.D.value],
            high_priority_relocations=[],  # TODO: Add relocation details
            estimated_pick_time_reduction_percent=0.0,  # TODO: Calculate
            analyzed_at=datetime.now(timezone.utc)
        )

    # ========================================================================
    # PRIVATE HELPER METHODS
    # ========================================================================

    async def _generate_wave_number(self, tenant_id: uuid.UUID) -> str:
        """Generate unique wave number."""
        today = date.today().strftime("%Y%m%d")
        prefix = f"WV-{today}-"

        # Get max sequence for today
        result = await self.db.execute(
            select(func.count())
            .select_from(PickWave)
            .where(
                and_(
                    PickWave.tenant_id == tenant_id,
                    PickWave.wave_number.like(f"{prefix}%")
                )
            )
        )
        count = result.scalar() or 0

        return f"{prefix}{count + 1:03d}"

    async def _select_orders_for_wave(
        self,
        wave: PickWave,
        config: WaveCreate
    ) -> List[Order]:
        """Select eligible orders based on wave configuration."""
        query = (
            select(Order)
            .where(
                and_(
                    Order.status == OrderStatus.CONFIRMED.value,
                    Order.warehouse_id == wave.warehouse_id,
                )
            )
        )

        # Filter by carrier
        if wave.carrier_id:
            # Orders assigned to this carrier
            pass  # TODO: Add carrier filter

        # Filter by priority
        if wave.min_priority:
            query = query.where(Order.priority >= wave.min_priority)
        if wave.max_priority:
            query = query.where(Order.priority <= wave.max_priority)

        # Limit to reasonable batch size
        query = query.limit(500)

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def _get_orders_by_ids(self, order_ids: List[uuid.UUID]) -> List[Order]:
        """Get orders by IDs."""
        result = await self.db.execute(
            select(Order).where(Order.id.in_(order_ids))
        )
        return list(result.scalars().all())

    async def _create_wave_picklists(
        self,
        wave: PickWave,
        orders: List[Order]
    ) -> None:
        """Create picklists for wave orders."""
        sequence = 1
        for order in orders:
            # Create or get picklist for order
            picklist = await self._get_or_create_picklist(order, wave.warehouse_id, wave.tenant_id)

            # Link to wave
            wave_picklist = WavePicklist(
                wave_id=wave.id,
                picklist_id=picklist.id,
                sequence=sequence,
            )
            self.db.add(wave_picklist)
            sequence += 1

        wave.total_orders = len(orders)

    async def _get_or_create_picklist(
        self,
        order: Order,
        warehouse_id: uuid.UUID,
        tenant_id: uuid.UUID
    ) -> Picklist:
        """Get existing or create new picklist for order."""
        # Check for existing picklist
        result = await self.db.execute(
            select(Picklist)
            .join(PicklistItem)
            .where(PicklistItem.order_id == order.id)
            .limit(1)
        )
        existing = result.scalar_one_or_none()

        if existing:
            return existing

        # Create new picklist
        picklist_number = f"PL-{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"

        picklist = Picklist(
            picklist_number=picklist_number,
            warehouse_id=warehouse_id,
            status=PicklistStatus.PENDING.value,
            picklist_type=PicklistType.SINGLE_ORDER.value,
            total_orders=1,
        )
        self.db.add(picklist)
        await self.db.flush()

        # Add items
        # TODO: Create picklist items from order items

        return picklist

    async def _update_wave_metrics(self, wave: PickWave) -> None:
        """Update wave aggregate metrics."""
        # Count picklists
        result = await self.db.execute(
            select(func.count())
            .select_from(WavePicklist)
            .where(WavePicklist.wave_id == wave.id)
        )
        wave.total_picklists = result.scalar() or 0

        # Count items and quantities
        # TODO: Calculate from picklist items

    async def _create_tasks_for_picklist(
        self,
        wave: PickWave,
        picklist: Picklist,
        sequence: int
    ) -> int:
        """Create pick tasks for picklist items."""
        tasks_created = 0

        # Get picklist items
        result = await self.db.execute(
            select(PicklistItem).where(PicklistItem.picklist_id == picklist.id)
        )
        items = list(result.scalars().all())

        for item in items:
            task_number = f"TK-{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"

            task = WarehouseTask(
                tenant_id=wave.tenant_id,
                task_number=task_number,
                task_type=TaskType.PICK.value,
                status=TaskStatus.PENDING.value,
                priority=TaskPriority.NORMAL.value,
                warehouse_id=wave.warehouse_id,
                source_bin_id=item.bin_id,
                source_bin_code=item.bin_location,
                product_id=item.product_id,
                variant_id=item.variant_id,
                sku=item.sku,
                product_name=item.product_name,
                quantity_required=item.quantity_required,
                wave_id=wave.id,
                picklist_id=picklist.id,
                picklist_item_id=item.id,
            )
            self.db.add(task)
            tasks_created += 1

        return tasks_created

    async def _assign_pickers_to_wave(
        self,
        wave: PickWave,
        picker_ids: List[uuid.UUID]
    ) -> int:
        """Assign pickers to wave tasks."""
        # Get pending tasks
        result = await self.db.execute(
            select(WarehouseTask)
            .where(
                and_(
                    WarehouseTask.wave_id == wave.id,
                    WarehouseTask.status == TaskStatus.PENDING.value,
                    WarehouseTask.assigned_to.is_(None)
                )
            )
            .order_by(WarehouseTask.created_at)
        )
        tasks = list(result.scalars().all())

        # Round-robin assignment
        assigned = 0
        for i, task in enumerate(tasks):
            picker_idx = i % len(picker_ids)
            task.assigned_to = picker_ids[picker_idx]
            task.assigned_at = datetime.now(timezone.utc)
            task.status = TaskStatus.ASSIGNED.value
            assigned += 1

        return assigned

    async def _get_task(self, task_id: uuid.UUID) -> Optional[WarehouseTask]:
        """Get task by ID."""
        result = await self.db.execute(
            select(WarehouseTask).where(WarehouseTask.id == task_id)
        )
        return result.scalar_one_or_none()

    async def _get_worker_location(
        self,
        user_id: uuid.UUID,
        tenant_id: uuid.UUID
    ) -> Optional[WorkerLocation]:
        """Get worker's current location."""
        result = await self.db.execute(
            select(WorkerLocation)
            .where(
                and_(
                    WorkerLocation.user_id == user_id,
                    WorkerLocation.tenant_id == tenant_id
                )
            )
        )
        return result.scalar_one_or_none()

    async def _calculate_task_score(
        self,
        task: WarehouseTask,
        worker_loc: Optional[WorkerLocation],
        current_zone_id: Optional[uuid.UUID],
        current_bin_code: Optional[str]
    ) -> float:
        """
        Calculate task score for interleaving.

        Higher score = higher priority for selection.
        """
        score = 0.0

        # Priority weight (40%)
        priority_scores = {
            TaskPriority.URGENT.value: 100,
            TaskPriority.HIGH.value: 75,
            TaskPriority.NORMAL.value: 50,
            TaskPriority.LOW.value: 25,
        }
        score += priority_scores.get(task.priority, 50) * 0.4

        # SLA weight (30%)
        if task.due_at:
            time_until_due = (task.due_at - datetime.now(timezone.utc)).total_seconds()
            if time_until_due < 0:
                score += 100 * 0.3  # Overdue = highest urgency
            elif time_until_due < 3600:  # Within 1 hour
                score += 80 * 0.3
            elif time_until_due < 7200:  # Within 2 hours
                score += 60 * 0.3
            else:
                score += 40 * 0.3
        else:
            score += 40 * 0.3  # No deadline

        # Proximity weight (30%)
        if current_zone_id and task.zone_id:
            if current_zone_id == task.zone_id:
                score += 100 * 0.3  # Same zone
            else:
                score += 30 * 0.3  # Different zone
        elif current_bin_code and task.source_bin_code:
            distance = self._calculate_bin_distance(current_bin_code, task.source_bin_code)
            proximity_score = max(0, 100 - distance)
            score += proximity_score * 0.3
        else:
            score += 50 * 0.3  # Unknown location

        return score

    def _calculate_bin_distance(self, bin1: str, bin2: str) -> int:
        """
        Estimate distance between two bins based on location codes.

        Assumes bin codes like "A1-B2-C3" where:
        - First part is aisle
        - Second part is rack
        - Third part is shelf
        """
        try:
            parts1 = bin1.split("-")
            parts2 = bin2.split("-")

            if len(parts1) < 2 or len(parts2) < 2:
                return 50  # Default distance

            # Extract aisle numbers
            aisle1 = ord(parts1[0][0].upper()) - ord('A')
            aisle2 = ord(parts2[0][0].upper()) - ord('A')

            # Extract rack numbers
            rack1 = int(parts1[1][1:]) if len(parts1[1]) > 1 else 0
            rack2 = int(parts2[1][1:]) if len(parts2[1]) > 1 else 0

            # Simple Manhattan distance
            distance = abs(aisle1 - aisle2) * 10 + abs(rack1 - rack2) * 2

            return distance
        except Exception:
            return 50  # Default on parse error

    async def _estimate_travel_distance(
        self,
        from_bin: Optional[str],
        to_bin: Optional[str]
    ) -> Optional[int]:
        """Estimate travel distance in meters."""
        if not from_bin or not to_bin:
            return None

        # Convert bin distance to meters (rough estimate)
        bin_distance = self._calculate_bin_distance(from_bin, to_bin)
        return bin_distance * 3  # Assume 3 meters per "unit"

    def _get_task_selection_reason(self, task: WarehouseTask, score: float) -> str:
        """Get human-readable reason for task selection."""
        reasons = []

        if task.priority == TaskPriority.URGENT.value:
            reasons.append("Urgent priority")
        elif task.priority == TaskPriority.HIGH.value:
            reasons.append("High priority")

        if task.due_at:
            time_until = (task.due_at - datetime.now(timezone.utc)).total_seconds()
            if time_until < 0:
                reasons.append("Overdue")
            elif time_until < 3600:
                reasons.append("Due within 1 hour")

        if not reasons:
            reasons.append("Optimized for minimal travel")

        return ", ".join(reasons)

    async def _update_picklist_item(
        self,
        task: WarehouseTask,
        data: TaskCompleteRequest
    ) -> None:
        """Update picklist item after pick task completion."""
        # TODO: Update PicklistItem with picked quantities

    async def _check_wave_completion(self, wave_id: uuid.UUID) -> None:
        """Check if wave is complete and update status."""
        # Count pending/in-progress tasks
        result = await self.db.execute(
            select(func.count())
            .select_from(WarehouseTask)
            .where(
                and_(
                    WarehouseTask.wave_id == wave_id,
                    WarehouseTask.status.in_([
                        TaskStatus.PENDING.value,
                        TaskStatus.ASSIGNED.value,
                        TaskStatus.IN_PROGRESS.value
                    ])
                )
            )
        )
        pending = result.scalar() or 0

        if pending == 0:
            wave = await self.get_wave(wave_id)
            if wave:
                wave.status = WaveStatus.COMPLETED.value
                wave.completed_at = datetime.now(timezone.utc)

    async def _update_worker_stats(
        self,
        worker_id: uuid.UUID,
        task: WarehouseTask
    ) -> None:
        """Update worker performance stats."""
        # Get or create worker location
        result = await self.db.execute(
            select(WorkerLocation)
            .where(WorkerLocation.user_id == worker_id)
        )
        worker_loc = result.scalar_one_or_none()

        if worker_loc:
            worker_loc.tasks_completed_today += 1
            worker_loc.items_picked_today += task.quantity_completed
            worker_loc.current_task_id = None
            worker_loc.current_bin_code = task.source_bin_code

    async def _get_pick_history(
        self,
        tenant_id: uuid.UUID,
        warehouse_id: uuid.UUID,
        start_date: date,
        end_date: date
    ) -> List[Dict[str, Any]]:
        """Get pick history for slot optimization."""
        # Query completed pick tasks
        result = await self.db.execute(
            select(
                WarehouseTask.product_id,
                WarehouseTask.variant_id,
                WarehouseTask.sku,
                func.count().label('picks'),
                func.sum(WarehouseTask.quantity_completed).label('quantity')
            )
            .where(
                and_(
                    WarehouseTask.tenant_id == tenant_id,
                    WarehouseTask.warehouse_id == warehouse_id,
                    WarehouseTask.task_type == TaskType.PICK.value,
                    WarehouseTask.status == TaskStatus.COMPLETED.value,
                    WarehouseTask.completed_at >= datetime.combine(start_date, time.min),
                    WarehouseTask.completed_at <= datetime.combine(end_date, time.max)
                )
            )
            .group_by(
                WarehouseTask.product_id,
                WarehouseTask.variant_id,
                WarehouseTask.sku
            )
        )

        return [
            {
                'product_id': row.product_id,
                'variant_id': row.variant_id,
                'sku': row.sku,
                'picks': row.picks,
                'quantity': row.quantity or 0
            }
            for row in result.all()
        ]

    async def _update_slot_score(
        self,
        tenant_id: uuid.UUID,
        product_id: uuid.UUID,
        variant_id: Optional[uuid.UUID],
        sku: str,
        warehouse_id: uuid.UUID,
        velocity_class: str,
        picks: int,
        quantity: int,
        velocity_score: Decimal,
        analysis_start: date,
        analysis_end: date
    ) -> SlotScore:
        """Update or create slot score for product."""
        # Check for existing
        query = select(SlotScore).where(
            and_(
                SlotScore.tenant_id == tenant_id,
                SlotScore.product_id == product_id,
                SlotScore.warehouse_id == warehouse_id
            )
        )
        if variant_id:
            query = query.where(SlotScore.variant_id == variant_id)

        result = await self.db.execute(query)
        slot_score = result.scalar_one_or_none()

        if slot_score:
            slot_score.velocity_class = velocity_class
            slot_score.pick_frequency = picks
            slot_score.pick_quantity = quantity
            slot_score.velocity_score = velocity_score
            slot_score.total_score = velocity_score
            slot_score.analysis_start = analysis_start
            slot_score.analysis_end = analysis_end
            slot_score.last_analyzed_at = datetime.now(timezone.utc)
        else:
            slot_score = SlotScore(
                tenant_id=tenant_id,
                product_id=product_id,
                variant_id=variant_id,
                sku=sku,
                warehouse_id=warehouse_id,
                velocity_class=velocity_class,
                pick_frequency=picks,
                pick_quantity=quantity,
                velocity_score=velocity_score,
                total_score=velocity_score,
                analysis_start=analysis_start,
                analysis_end=analysis_end,
                last_analyzed_at=datetime.now(timezone.utc)
            )
            self.db.add(slot_score)

        return slot_score
