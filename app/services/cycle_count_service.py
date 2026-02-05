"""
Cycle Counting Service - Phase 11: Cycle Counting & Physical Inventory.

Business logic for cycle counting operations.
"""
from datetime import datetime, date, timedelta
from decimal import Decimal
from typing import Optional, List, Tuple, Dict, Any
from uuid import UUID, uuid4

from sqlalchemy import select, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.cycle_count import (
    CycleCountPlan, CountSchedule, CountSession, CountTask, CountDetail,
    InventoryVariance, ABCClassification,
    CountType, CountFrequency, CountMethod, CountPlanStatus,
    CountTaskStatus, VarianceStatus, VarianceReason, ABCClass, ApprovalLevel
)
from app.models.inventory import InventorySummary
from app.models.wms import WarehouseBin, WarehouseZone
from app.models.product import Product
from app.schemas.cycle_count import (
    CycleCountPlanCreate, CycleCountPlanUpdate,
    CountSessionCreate, CountSessionUpdate,
    CountTaskCreate, CountTaskCount, CountTaskRecount, CountTaskApprove,
    CountDetailCreate,
    VarianceInvestigate, VarianceApprove, VarianceWriteOff,
    ABCClassificationCreate, ABCClassificationUpdate, ABCRecalculate,
    GenerateCountTasks
)


class CycleCountService:
    """Service for cycle counting operations."""

    def __init__(self, db: AsyncSession, tenant_id: UUID):
        self.db = db
        self.tenant_id = tenant_id

    # ========================================================================
    # CYCLE COUNT PLANS
    # ========================================================================

    async def create_plan(
        self,
        data: CycleCountPlanCreate,
        created_by: UUID
    ) -> CycleCountPlan:
        """Create a new cycle count plan."""
        plan = CycleCountPlan(
            tenant_id=self.tenant_id,
            warehouse_id=data.warehouse_id,
            plan_name=data.plan_name,
            plan_code=data.plan_code,
            description=data.description,
            count_type=data.count_type,
            frequency=data.frequency,
            start_date=data.start_date,
            end_date=data.end_date,
            count_a_frequency=data.count_a_frequency,
            count_b_frequency=data.count_b_frequency,
            count_c_frequency=data.count_c_frequency,
            zone_ids=data.zone_ids,
            category_ids=data.category_ids,
            product_ids=data.product_ids,
            bin_ids=data.bin_ids,
            abc_classes=data.abc_classes,
            sample_percentage=data.sample_percentage,
            min_items_per_count=data.min_items_per_count,
            max_items_per_count=data.max_items_per_count,
            count_method=data.count_method,
            blind_count=data.blind_count,
            require_recount_on_variance=data.require_recount_on_variance,
            recount_threshold_percent=data.recount_threshold_percent,
            recount_threshold_value=data.recount_threshold_value,
            auto_approve_threshold_percent=data.auto_approve_threshold_percent,
            auto_approve_threshold_value=data.auto_approve_threshold_value,
            supervisor_threshold_percent=data.supervisor_threshold_percent,
            manager_threshold_percent=data.manager_threshold_percent,
            director_threshold_value=data.director_threshold_value,
            notes=data.notes,
            status=CountPlanStatus.DRAFT,
            next_count_date=data.start_date,
            created_by=created_by
        )

        self.db.add(plan)
        await self.db.commit()
        await self.db.refresh(plan)
        return plan

    async def get_plan(self, plan_id: UUID) -> Optional[CycleCountPlan]:
        """Get a cycle count plan by ID."""
        result = await self.db.execute(
            select(CycleCountPlan).where(
                CycleCountPlan.id == plan_id,
                CycleCountPlan.tenant_id == self.tenant_id
            )
        )
        return result.scalar_one_or_none()

    async def list_plans(
        self,
        warehouse_id: Optional[UUID] = None,
        status: Optional[CountPlanStatus] = None,
        count_type: Optional[CountType] = None,
        skip: int = 0,
        limit: int = 100
    ) -> Tuple[List[CycleCountPlan], int]:
        """List cycle count plans with filters."""
        query = select(CycleCountPlan).where(
            CycleCountPlan.tenant_id == self.tenant_id
        )

        if warehouse_id:
            query = query.where(CycleCountPlan.warehouse_id == warehouse_id)
        if status:
            query = query.where(CycleCountPlan.status == status)
        if count_type:
            query = query.where(CycleCountPlan.count_type == count_type)

        # Count
        count_query = select(func.count()).select_from(query.subquery())
        total = await self.db.scalar(count_query)

        # Paginate
        query = query.order_by(CycleCountPlan.created_at.desc())
        query = query.offset(skip).limit(limit)

        result = await self.db.execute(query)
        plans = result.scalars().all()

        return list(plans), total or 0

    async def update_plan(
        self,
        plan_id: UUID,
        data: CycleCountPlanUpdate
    ) -> Optional[CycleCountPlan]:
        """Update a cycle count plan."""
        plan = await self.get_plan(plan_id)
        if not plan:
            return None

        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(plan, field, value)

        await self.db.commit()
        await self.db.refresh(plan)
        return plan

    async def activate_plan(self, plan_id: UUID) -> Optional[CycleCountPlan]:
        """Activate a cycle count plan."""
        plan = await self.get_plan(plan_id)
        if not plan or plan.status not in [CountPlanStatus.DRAFT, CountPlanStatus.PAUSED]:
            return None

        plan.status = CountPlanStatus.ACTIVE
        await self.db.commit()
        await self.db.refresh(plan)
        return plan

    async def pause_plan(self, plan_id: UUID) -> Optional[CycleCountPlan]:
        """Pause a cycle count plan."""
        plan = await self.get_plan(plan_id)
        if not plan or plan.status != CountPlanStatus.ACTIVE:
            return None

        plan.status = CountPlanStatus.PAUSED
        await self.db.commit()
        await self.db.refresh(plan)
        return plan

    # ========================================================================
    # COUNT SESSIONS
    # ========================================================================

    async def create_session(
        self,
        data: CountSessionCreate,
        created_by: UUID
    ) -> CountSession:
        """Create a new count session."""
        # Generate session number
        today = date.today()
        count_result = await self.db.execute(
            select(func.count()).select_from(CountSession).where(
                CountSession.tenant_id == self.tenant_id,
                func.date(CountSession.created_at) == today
            )
        )
        count = count_result.scalar() or 0
        session_number = f"CS-{today.strftime('%Y%m%d')}-{count + 1:04d}"

        session = CountSession(
            tenant_id=self.tenant_id,
            warehouse_id=data.warehouse_id,
            plan_id=data.plan_id,
            session_number=session_number,
            session_name=data.session_name,
            count_type=data.count_type,
            count_method=data.count_method,
            blind_count=data.blind_count,
            count_date=data.count_date,
            zone_ids=data.zone_ids,
            bin_ids=data.bin_ids,
            category_ids=data.category_ids,
            notes=data.notes,
            status=CountTaskStatus.PENDING,
            created_by=created_by
        )

        self.db.add(session)
        await self.db.commit()
        await self.db.refresh(session)
        return session

    async def get_session(self, session_id: UUID) -> Optional[CountSession]:
        """Get a count session by ID."""
        result = await self.db.execute(
            select(CountSession).where(
                CountSession.id == session_id,
                CountSession.tenant_id == self.tenant_id
            ).options(selectinload(CountSession.tasks))
        )
        return result.scalar_one_or_none()

    async def list_sessions(
        self,
        warehouse_id: Optional[UUID] = None,
        plan_id: Optional[UUID] = None,
        status: Optional[CountTaskStatus] = None,
        from_date: Optional[date] = None,
        to_date: Optional[date] = None,
        skip: int = 0,
        limit: int = 100
    ) -> Tuple[List[CountSession], int]:
        """List count sessions with filters."""
        query = select(CountSession).where(
            CountSession.tenant_id == self.tenant_id
        )

        if warehouse_id:
            query = query.where(CountSession.warehouse_id == warehouse_id)
        if plan_id:
            query = query.where(CountSession.plan_id == plan_id)
        if status:
            query = query.where(CountSession.status == status)
        if from_date:
            query = query.where(CountSession.count_date >= from_date)
        if to_date:
            query = query.where(CountSession.count_date <= to_date)

        # Count
        count_query = select(func.count()).select_from(query.subquery())
        total = await self.db.scalar(count_query)

        # Paginate
        query = query.order_by(CountSession.count_date.desc())
        query = query.offset(skip).limit(limit)

        result = await self.db.execute(query)
        sessions = result.scalars().all()

        return list(sessions), total or 0

    async def start_session(self, session_id: UUID) -> Optional[CountSession]:
        """Start a count session."""
        session = await self.get_session(session_id)
        if not session or session.status != CountTaskStatus.PENDING:
            return None

        session.status = CountTaskStatus.IN_PROGRESS
        session.started_at = datetime.utcnow()
        await self.db.commit()
        await self.db.refresh(session)
        return session

    async def complete_session(
        self,
        session_id: UUID,
        approved_by: UUID,
        notes: Optional[str] = None
    ) -> Optional[CountSession]:
        """Complete a count session."""
        session = await self.get_session(session_id)
        if not session:
            return None

        # Check all tasks are completed
        pending_tasks = await self.db.execute(
            select(func.count()).select_from(CountTask).where(
                CountTask.session_id == session_id,
                CountTask.tenant_id == self.tenant_id,
                CountTask.status.not_in([
                    CountTaskStatus.COMPLETED,
                    CountTaskStatus.APPROVED,
                    CountTaskStatus.CANCELLED
                ])
            )
        )
        if pending_tasks.scalar() > 0:
            return None

        session.status = CountTaskStatus.COMPLETED
        session.completed_at = datetime.utcnow()
        session.approved_by = approved_by
        session.approved_at = datetime.utcnow()
        session.approval_notes = notes

        # Calculate final metrics
        await self._calculate_session_metrics(session)

        await self.db.commit()
        await self.db.refresh(session)
        return session

    async def _calculate_session_metrics(self, session: CountSession):
        """Calculate session-level metrics."""
        # Get task statistics
        tasks_result = await self.db.execute(
            select(
                func.count().label('total'),
                func.sum(func.cast(CountTask.has_variance, Integer)).label('with_variance'),
                func.sum(CountTask.variance_qty).label('variance_qty'),
                func.sum(CountTask.variance_value).label('variance_value')
            ).where(
                CountTask.session_id == session.id,
                CountTask.tenant_id == self.tenant_id
            )
        )
        stats = tasks_result.one()

        session.total_items = stats.total or 0
        session.items_with_variance = stats.with_variance or 0
        session.total_variance_qty = abs(stats.variance_qty or Decimal("0"))
        session.total_variance_value = abs(stats.variance_value or Decimal("0"))

        # Calculate accuracy
        if session.total_items > 0:
            accurate_count = session.total_items - session.items_with_variance
            session.accuracy_rate = (Decimal(accurate_count) / Decimal(session.total_items)) * 100

    # ========================================================================
    # COUNT TASKS
    # ========================================================================

    async def create_task(self, data: CountTaskCreate) -> CountTask:
        """Create a new count task."""
        # Get session
        session = await self.get_session(data.session_id)
        if not session:
            raise ValueError("Session not found")

        # Generate task number
        task_count = await self.db.execute(
            select(func.count()).select_from(CountTask).where(
                CountTask.session_id == data.session_id,
                CountTask.tenant_id == self.tenant_id
            )
        )
        count = task_count.scalar() or 0
        task_number = f"{session.session_number}-T{count + 1:04d}"

        task = CountTask(
            tenant_id=self.tenant_id,
            session_id=data.session_id,
            warehouse_id=session.warehouse_id,
            task_number=task_number,
            sequence=count + 1,
            zone_id=data.zone_id,
            bin_id=data.bin_id,
            location_code=data.location_code,
            product_id=data.product_id,
            variant_id=data.variant_id,
            lot_number=data.lot_number,
            serial_number=data.serial_number,
            expected_qty=data.expected_qty,
            expected_uom=data.expected_uom,
            expected_value=data.expected_value,
            assigned_to=data.assigned_to,
            assigned_at=datetime.utcnow() if data.assigned_to else None,
            notes=data.notes,
            status=CountTaskStatus.PENDING
        )

        self.db.add(task)

        # Update session totals
        session.total_tasks += 1
        session.total_items += 1

        await self.db.commit()
        await self.db.refresh(task)
        return task

    async def get_task(self, task_id: UUID) -> Optional[CountTask]:
        """Get a count task by ID."""
        result = await self.db.execute(
            select(CountTask).where(
                CountTask.id == task_id,
                CountTask.tenant_id == self.tenant_id
            ).options(selectinload(CountTask.count_details))
        )
        return result.scalar_one_or_none()

    async def list_tasks(
        self,
        session_id: Optional[UUID] = None,
        assigned_to: Optional[UUID] = None,
        status: Optional[CountTaskStatus] = None,
        has_variance: Optional[bool] = None,
        skip: int = 0,
        limit: int = 100
    ) -> Tuple[List[CountTask], int]:
        """List count tasks with filters."""
        query = select(CountTask).where(CountTask.tenant_id == self.tenant_id)

        if session_id:
            query = query.where(CountTask.session_id == session_id)
        if assigned_to:
            query = query.where(CountTask.assigned_to == assigned_to)
        if status:
            query = query.where(CountTask.status == status)
        if has_variance is not None:
            query = query.where(CountTask.has_variance == has_variance)

        # Count
        count_query = select(func.count()).select_from(query.subquery())
        total = await self.db.scalar(count_query)

        # Paginate
        query = query.order_by(CountTask.sequence)
        query = query.offset(skip).limit(limit)

        result = await self.db.execute(query)
        tasks = result.scalars().all()

        return list(tasks), total or 0

    async def assign_task(
        self,
        task_id: UUID,
        assigned_to: UUID
    ) -> Optional[CountTask]:
        """Assign a task to a user."""
        task = await self.get_task(task_id)
        if not task:
            return None

        task.assigned_to = assigned_to
        task.assigned_at = datetime.utcnow()
        task.status = CountTaskStatus.ASSIGNED

        await self.db.commit()
        await self.db.refresh(task)
        return task

    async def record_count(
        self,
        task_id: UUID,
        data: CountTaskCount,
        counted_by: UUID
    ) -> Optional[CountTask]:
        """Record a count for a task."""
        task = await self.get_task(task_id)
        if not task:
            return None

        # Record first count
        task.first_count_qty = data.counted_qty
        task.first_count_by = counted_by
        task.first_count_at = datetime.utcnow()
        task.first_count_method = data.count_method.value
        task.status = CountTaskStatus.COUNTING

        # Calculate variance
        variance_qty = data.counted_qty - task.expected_qty
        variance_percent = Decimal("0")
        if task.expected_qty > 0:
            variance_percent = (variance_qty / task.expected_qty) * 100

        task.variance_qty = variance_qty
        task.variance_percent = variance_percent

        # Get session for recount threshold
        session = await self.get_session(task.session_id)
        plan = None
        if session and session.plan_id:
            plan = await self.get_plan(session.plan_id)

        # Check if recount required
        recount_threshold_percent = Decimal("5.0")
        recount_threshold_value = Decimal("100.0")
        if plan:
            recount_threshold_percent = plan.recount_threshold_percent
            recount_threshold_value = plan.recount_threshold_value

        # Determine if recount needed
        if abs(variance_percent) > recount_threshold_percent or abs(task.variance_qty) > recount_threshold_value:
            task.recount_required = True
            task.status = CountTaskStatus.RECOUNTING
        else:
            # Finalize count
            task.final_count_qty = data.counted_qty
            task.has_variance = variance_qty != 0
            task.status = CountTaskStatus.PENDING_REVIEW if task.has_variance else CountTaskStatus.COMPLETED

        if data.notes:
            task.notes = data.notes
        if data.photos:
            task.photos = data.photos

        # Create variance record if needed
        if task.has_variance and not task.recount_required:
            await self._create_variance(task, counted_by)

        await self.db.commit()
        await self.db.refresh(task)
        return task

    async def record_recount(
        self,
        task_id: UUID,
        data: CountTaskRecount,
        recounted_by: UUID
    ) -> Optional[CountTask]:
        """Record a recount for a task."""
        task = await self.get_task(task_id)
        if not task or not task.recount_required:
            return None

        task.recount_qty = data.recount_qty
        task.recount_by = recounted_by
        task.recount_at = datetime.utcnow()

        # Use recount as final count
        task.final_count_qty = data.recount_qty

        # Recalculate variance
        variance_qty = data.recount_qty - task.expected_qty
        task.variance_qty = variance_qty
        task.has_variance = variance_qty != 0

        if task.expected_qty > 0:
            task.variance_percent = (variance_qty / task.expected_qty) * 100

        task.status = CountTaskStatus.PENDING_REVIEW if task.has_variance else CountTaskStatus.COMPLETED

        if data.notes:
            task.notes = (task.notes or "") + f"\nRecount: {data.notes}"

        # Create variance record if needed
        if task.has_variance:
            await self._create_variance(task, recounted_by)

        await self.db.commit()
        await self.db.refresh(task)
        return task

    async def approve_task(
        self,
        task_id: UUID,
        data: CountTaskApprove,
        approved_by: UUID
    ) -> Optional[CountTask]:
        """Approve or reject a count task."""
        task = await self.get_task(task_id)
        if not task or task.status != CountTaskStatus.PENDING_REVIEW:
            return None

        if data.approved:
            task.status = CountTaskStatus.APPROVED
            task.approved_by = approved_by
            task.approved_at = datetime.utcnow()
        else:
            task.status = CountTaskStatus.REJECTED
            task.rejection_reason = data.notes

        await self.db.commit()
        await self.db.refresh(task)
        return task

    async def _create_variance(self, task: CountTask, created_by: UUID):
        """Create a variance record from a count task."""
        # Generate variance number
        today = date.today()
        var_count = await self.db.execute(
            select(func.count()).select_from(InventoryVariance).where(
                InventoryVariance.tenant_id == self.tenant_id,
                func.date(InventoryVariance.created_at) == today
            )
        )
        count = var_count.scalar() or 0
        variance_number = f"VAR-{today.strftime('%Y%m%d')}-{count + 1:04d}"

        # Determine approval level
        approval_level = ApprovalLevel.AUTO
        session = await self.get_session(task.session_id)
        plan = None
        if session and session.plan_id:
            plan = await self.get_plan(session.plan_id)

        if plan:
            variance_percent = abs(task.variance_percent)
            variance_value = abs(task.variance_qty * (task.expected_value / task.expected_qty if task.expected_qty > 0 else Decimal("0")))

            if variance_value >= plan.director_threshold_value:
                approval_level = ApprovalLevel.DIRECTOR
            elif variance_percent >= plan.manager_threshold_percent:
                approval_level = ApprovalLevel.MANAGER
            elif variance_percent >= plan.supervisor_threshold_percent:
                approval_level = ApprovalLevel.SUPERVISOR
            elif variance_percent <= plan.auto_approve_threshold_percent and variance_value <= plan.auto_approve_threshold_value:
                approval_level = ApprovalLevel.AUTO

        variance = InventoryVariance(
            tenant_id=self.tenant_id,
            warehouse_id=task.warehouse_id,
            session_id=task.session_id,
            task_id=task.id,
            variance_number=variance_number,
            variance_date=date.today(),
            zone_id=task.zone_id,
            bin_id=task.bin_id,
            location_code=task.location_code,
            product_id=task.product_id,
            variant_id=task.variant_id,
            lot_number=task.lot_number,
            system_qty=task.expected_qty,
            counted_qty=task.final_count_qty,
            variance_qty=task.variance_qty,
            uom=task.expected_uom,
            unit_cost=task.expected_value / task.expected_qty if task.expected_qty > 0 else Decimal("0"),
            variance_value=task.variance_qty * (task.expected_value / task.expected_qty if task.expected_qty > 0 else Decimal("0")),
            variance_percent=task.variance_percent,
            is_positive=task.variance_qty > 0,
            is_negative=task.variance_qty < 0,
            approval_level=approval_level,
            status=VarianceStatus.ADJUSTED if approval_level == ApprovalLevel.AUTO else VarianceStatus.PENDING
        )

        self.db.add(variance)

    # ========================================================================
    # GENERATE TASKS FROM PLAN
    # ========================================================================

    async def generate_tasks_from_plan(
        self,
        data: GenerateCountTasks,
        created_by: UUID
    ) -> CountSession:
        """Generate count tasks from a plan."""
        plan = await self.get_plan(data.plan_id)
        if not plan:
            raise ValueError("Plan not found")

        # Create session
        session_data = CountSessionCreate(
            warehouse_id=plan.warehouse_id,
            plan_id=plan.id,
            session_name=f"{plan.plan_name} - {data.count_date}",
            count_type=plan.count_type,
            count_method=plan.count_method,
            blind_count=plan.blind_count,
            count_date=data.count_date,
            zone_ids=plan.zone_ids,
            bin_ids=plan.bin_ids,
            category_ids=plan.category_ids
        )
        session = await self.create_session(session_data, created_by)

        # Get items to count based on plan criteria
        items_query = select(
            InventorySummary.warehouse_id,
            InventorySummary.product_id,
            InventorySummary.available_quantity,
            Product.base_price
        ).join(
            Product, InventorySummary.product_id == Product.id
        ).where(
            InventorySummary.tenant_id == self.tenant_id,
            InventorySummary.warehouse_id == plan.warehouse_id
        )

        # Apply category filter
        if plan.category_ids:
            items_query = items_query.where(
                Product.category_id.in_(plan.category_ids)
            )

        # Apply product filter
        if plan.product_ids:
            items_query = items_query.where(
                InventorySummary.product_id.in_(plan.product_ids)
            )

        # Limit items
        max_items = data.max_tasks or plan.max_items_per_count
        items_query = items_query.limit(max_items)

        items_result = await self.db.execute(items_query)
        items = items_result.all()

        # Create tasks for each item
        for item in items:
            # Get a bin for this product (simplified - in real impl would check bin inventory)
            bin_result = await self.db.execute(
                select(WarehouseBin).where(
                    WarehouseBin.tenant_id == self.tenant_id,
                    WarehouseBin.warehouse_id == plan.warehouse_id,
                    WarehouseBin.is_active == True
                ).limit(1)
            )
            bin_row = bin_result.scalar_one_or_none()

            task_data = CountTaskCreate(
                session_id=session.id,
                zone_id=bin_row.zone_id if bin_row else None,
                bin_id=bin_row.id if bin_row else None,
                location_code=bin_row.bin_code if bin_row else "UNKNOWN",
                product_id=item.product_id,
                expected_qty=item.available_quantity or Decimal("0"),
                expected_uom="EACH",
                expected_value=(item.available_quantity or Decimal("0")) * (item.base_price or Decimal("0")),
                assigned_to=data.assigned_to
            )
            await self.create_task(task_data)

        # Update plan statistics
        plan.last_count_date = data.count_date
        plan.total_counts_completed += 1

        # Calculate next count date
        if plan.frequency == CountFrequency.DAILY:
            plan.next_count_date = data.count_date + timedelta(days=1)
        elif plan.frequency == CountFrequency.WEEKLY:
            plan.next_count_date = data.count_date + timedelta(weeks=1)
        elif plan.frequency == CountFrequency.BIWEEKLY:
            plan.next_count_date = data.count_date + timedelta(weeks=2)
        elif plan.frequency == CountFrequency.MONTHLY:
            plan.next_count_date = data.count_date + timedelta(days=30)
        elif plan.frequency == CountFrequency.QUARTERLY:
            plan.next_count_date = data.count_date + timedelta(days=90)
        elif plan.frequency == CountFrequency.ANNUALLY:
            plan.next_count_date = data.count_date + timedelta(days=365)

        await self.db.commit()
        await self.db.refresh(session)
        return session

    # ========================================================================
    # VARIANCES
    # ========================================================================

    async def get_variance(self, variance_id: UUID) -> Optional[InventoryVariance]:
        """Get a variance by ID."""
        result = await self.db.execute(
            select(InventoryVariance).where(
                InventoryVariance.id == variance_id,
                InventoryVariance.tenant_id == self.tenant_id
            )
        )
        return result.scalar_one_or_none()

    async def list_variances(
        self,
        warehouse_id: Optional[UUID] = None,
        session_id: Optional[UUID] = None,
        status: Optional[VarianceStatus] = None,
        product_id: Optional[UUID] = None,
        from_date: Optional[date] = None,
        to_date: Optional[date] = None,
        skip: int = 0,
        limit: int = 100
    ) -> Tuple[List[InventoryVariance], int]:
        """List variances with filters."""
        query = select(InventoryVariance).where(
            InventoryVariance.tenant_id == self.tenant_id
        )

        if warehouse_id:
            query = query.where(InventoryVariance.warehouse_id == warehouse_id)
        if session_id:
            query = query.where(InventoryVariance.session_id == session_id)
        if status:
            query = query.where(InventoryVariance.status == status)
        if product_id:
            query = query.where(InventoryVariance.product_id == product_id)
        if from_date:
            query = query.where(InventoryVariance.variance_date >= from_date)
        if to_date:
            query = query.where(InventoryVariance.variance_date <= to_date)

        # Count
        count_query = select(func.count()).select_from(query.subquery())
        total = await self.db.scalar(count_query)

        # Paginate
        query = query.order_by(InventoryVariance.created_at.desc())
        query = query.offset(skip).limit(limit)

        result = await self.db.execute(query)
        variances = result.scalars().all()

        return list(variances), total or 0

    async def investigate_variance(
        self,
        variance_id: UUID,
        data: VarianceInvestigate,
        investigated_by: UUID
    ) -> Optional[InventoryVariance]:
        """Record investigation details for a variance."""
        variance = await self.get_variance(variance_id)
        if not variance:
            return None

        variance.variance_reason = data.variance_reason
        variance.root_cause = data.root_cause
        variance.corrective_action = data.corrective_action
        variance.investigation_notes = data.investigation_notes
        variance.evidence_photos = data.evidence_photos
        variance.investigated_by = investigated_by
        variance.status = VarianceStatus.ROOT_CAUSE_IDENTIFIED

        await self.db.commit()
        await self.db.refresh(variance)
        return variance

    async def approve_variance(
        self,
        variance_id: UUID,
        data: VarianceApprove,
        approved_by: UUID
    ) -> Optional[InventoryVariance]:
        """Approve variance for adjustment."""
        variance = await self.get_variance(variance_id)
        if not variance:
            return None

        if data.approved:
            variance.status = VarianceStatus.ADJUSTMENT_PENDING
            variance.approved_by = approved_by
            variance.approved_at = datetime.utcnow()
        else:
            variance.status = VarianceStatus.PENDING
            variance.notes = (variance.notes or "") + f"\nRejected: {data.notes}"

        await self.db.commit()
        await self.db.refresh(variance)
        return variance

    async def write_off_variance(
        self,
        variance_id: UUID,
        data: VarianceWriteOff,
        written_off_by: UUID
    ) -> Optional[InventoryVariance]:
        """Write off a variance."""
        variance = await self.get_variance(variance_id)
        if not variance:
            return None

        variance.written_off = True
        variance.write_off_gl_account = data.write_off_gl_account
        variance.write_off_amount = abs(variance.variance_value)
        variance.status = VarianceStatus.WRITTEN_OFF
        variance.adjusted_by = written_off_by
        variance.adjusted_at = datetime.utcnow()
        if data.notes:
            variance.notes = (variance.notes or "") + f"\nWrite-off: {data.notes}"

        await self.db.commit()
        await self.db.refresh(variance)
        return variance

    # ========================================================================
    # ABC CLASSIFICATION
    # ========================================================================

    async def recalculate_abc(
        self,
        data: ABCRecalculate
    ) -> int:
        """Recalculate ABC classification for all products in a warehouse."""
        # Get product values/velocity
        if data.classification_method in ["value", "both"]:
            # Get annual value (simplified - would use actual sales data)
            products_result = await self.db.execute(
                select(
                    InventorySummary.product_id,
                    (InventorySummary.available_quantity * Product.base_price).label('annual_value')
                ).join(
                    Product, InventorySummary.product_id == Product.id
                ).where(
                    InventorySummary.tenant_id == self.tenant_id,
                    InventorySummary.warehouse_id == data.warehouse_id
                ).order_by(
                    (InventorySummary.available_quantity * Product.base_price).desc()
                )
            )
            products = products_result.all()
        else:
            products = []

        if not products:
            return 0

        # Calculate total and cumulative percentages
        total_value = sum(p.annual_value or Decimal("0") for p in products)
        if total_value == 0:
            return 0

        # Clear existing classifications
        await self.db.execute(
            select(ABCClassification).where(
                ABCClassification.tenant_id == self.tenant_id,
                ABCClassification.warehouse_id == data.warehouse_id
            )
        )

        # Assign classes
        cumulative = Decimal("0")
        count = 0
        for product in products:
            cumulative += (product.annual_value or Decimal("0"))
            cumulative_percent = (cumulative / total_value) * 100

            if cumulative_percent <= data.a_threshold_percent:
                abc_class = ABCClass.A
                frequency = CountFrequency.WEEKLY
            elif cumulative_percent <= data.b_threshold_percent:
                abc_class = ABCClass.B
                frequency = CountFrequency.MONTHLY
            else:
                abc_class = ABCClass.C
                frequency = CountFrequency.QUARTERLY

            # Create or update classification
            existing = await self.db.execute(
                select(ABCClassification).where(
                    ABCClassification.tenant_id == self.tenant_id,
                    ABCClassification.warehouse_id == data.warehouse_id,
                    ABCClassification.product_id == product.product_id
                )
            )
            classification = existing.scalar_one_or_none()

            if classification:
                classification.abc_class = abc_class
                classification.annual_value = product.annual_value or Decimal("0")
                classification.cumulative_value_percent = cumulative_percent
                classification.count_frequency = frequency
                classification.calculated_at = datetime.utcnow()
            else:
                classification = ABCClassification(
                    tenant_id=self.tenant_id,
                    warehouse_id=data.warehouse_id,
                    product_id=product.product_id,
                    abc_class=abc_class,
                    classification_method=data.classification_method,
                    annual_value=product.annual_value or Decimal("0"),
                    cumulative_value_percent=cumulative_percent,
                    count_frequency=frequency
                )
                self.db.add(classification)

            count += 1

        await self.db.commit()
        return count

    # ========================================================================
    # DASHBOARD
    # ========================================================================

    async def get_dashboard(
        self,
        warehouse_id: Optional[UUID] = None,
        from_date: Optional[date] = None,
        to_date: Optional[date] = None
    ) -> Dict[str, Any]:
        """Get cycle counting dashboard statistics."""
        if not from_date:
            from_date = date.today().replace(day=1)
        if not to_date:
            to_date = date.today()

        # Plan stats
        plans_result = await self.db.execute(
            select(
                func.count().filter(CycleCountPlan.status == CountPlanStatus.ACTIVE).label('active'),
                func.count().label('total')
            ).where(
                CycleCountPlan.tenant_id == self.tenant_id,
                CycleCountPlan.warehouse_id == warehouse_id if warehouse_id else True
            )
        )
        plan_stats = plans_result.one()

        # Session stats
        today = date.today()
        week_start = today - timedelta(days=today.weekday())
        month_start = today.replace(day=1)

        sessions_result = await self.db.execute(
            select(
                func.count().filter(CountSession.count_date == today).label('today'),
                func.count().filter(CountSession.count_date >= week_start).label('this_week'),
                func.count().filter(CountSession.count_date >= month_start).label('this_month')
            ).where(
                CountSession.tenant_id == self.tenant_id,
                CountSession.warehouse_id == warehouse_id if warehouse_id else True
            )
        )
        session_stats = sessions_result.one()

        # Task stats
        tasks_result = await self.db.execute(
            select(
                func.count().filter(CountTask.status == CountTaskStatus.PENDING).label('pending'),
                func.count().filter(CountTask.status == CountTaskStatus.IN_PROGRESS).label('in_progress'),
                func.count().filter(
                    and_(
                        CountTask.status == CountTaskStatus.COMPLETED,
                        func.date(CountTask.updated_at) == today
                    )
                ).label('completed_today')
            ).where(CountTask.tenant_id == self.tenant_id)
        )
        task_stats = tasks_result.one()

        # Variance stats
        variance_result = await self.db.execute(
            select(
                func.count().filter(
                    InventoryVariance.status.in_([VarianceStatus.PENDING, VarianceStatus.INVESTIGATING])
                ).label('open'),
                func.count().filter(
                    InventoryVariance.status == VarianceStatus.ADJUSTMENT_PENDING
                ).label('pending_approval'),
                func.coalesce(
                    func.sum(
                        func.abs(InventoryVariance.variance_value)
                    ).filter(
                        InventoryVariance.variance_date >= month_start
                    ),
                    0
                ).label('variance_value_mtd')
            ).where(
                InventoryVariance.tenant_id == self.tenant_id,
                InventoryVariance.warehouse_id == warehouse_id if warehouse_id else True
            )
        )
        var_stats = variance_result.one()

        # Recent sessions
        recent_sessions, _ = await self.list_sessions(
            warehouse_id=warehouse_id,
            skip=0,
            limit=5
        )

        # Recent variances
        recent_variances, _ = await self.list_variances(
            warehouse_id=warehouse_id,
            skip=0,
            limit=5
        )

        return {
            "active_plans": plan_stats.active or 0,
            "total_plans": plan_stats.total or 0,
            "sessions_today": session_stats.today or 0,
            "sessions_this_week": session_stats.this_week or 0,
            "sessions_this_month": session_stats.this_month or 0,
            "pending_tasks": task_stats.pending or 0,
            "in_progress_tasks": task_stats.in_progress or 0,
            "completed_tasks_today": task_stats.completed_today or 0,
            "open_variances": var_stats.open or 0,
            "pending_approval_variances": var_stats.pending_approval or 0,
            "total_variance_value_mtd": var_stats.variance_value_mtd or Decimal("0"),
            "overall_accuracy_rate": None,  # Would calculate from historical data
            "accuracy_by_zone": [],
            "accuracy_by_abc_class": {},
            "items_counted_mtd": 0,
            "items_due_for_count": 0,
            "overdue_items": 0,
            "recent_sessions": recent_sessions,
            "recent_variances": recent_variances
        }
