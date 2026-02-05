"""
Labor Management Service - Phase 4: Workforce Optimization.

Business logic for warehouse labor management.
"""
import uuid
from datetime import datetime, timezone, timedelta, date, time
from decimal import Decimal
from typing import Optional, List, Dict, Any, Tuple

from sqlalchemy import select, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from fastapi import HTTPException, status

from app.models.labor import (
    WarehouseWorker, WorkShift, LaborStandard,
    ProductivityMetric, WarehouseLeaveRequest, ShiftTemplate
)
from app.schemas.labor import (
    WorkerCreate, WorkerUpdate,
    ShiftCreate, ShiftUpdate, ClockInRequest, ClockOutRequest, BulkShiftCreate,
    ShiftTemplateCreate, LaborStandardCreate,
    LeaveRequestCreate, LeaveRequestUpdate,
    WorkerDashboardStats, LaborDashboardStats
)


class LaborService:
    """Service for labor management operations."""

    def __init__(self, db: AsyncSession, tenant_id: uuid.UUID):
        self.db = db
        self.tenant_id = tenant_id

    # =========================================================================
    # WORKER MANAGEMENT
    # =========================================================================

    async def create_worker(
        self,
        data: WorkerCreate,
        created_by: Optional[uuid.UUID] = None
    ) -> WarehouseWorker:
        """Create a new warehouse worker."""
        # Check for duplicate employee code
        existing = await self.db.execute(
            select(WarehouseWorker).where(
                WarehouseWorker.tenant_id == self.tenant_id,
                WarehouseWorker.employee_code == data.employee_code
            )
        )
        if existing.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Employee code {data.employee_code} already exists"
            )

        # Prepare certifications as dict
        certifications = None
        if data.certifications:
            certifications = {
                c.name: {
                    "issuer": c.issuer,
                    "issue_date": str(c.issue_date),
                    "expiry_date": str(c.expiry_date) if c.expiry_date else None,
                    "certificate_number": c.certificate_number
                }
                for c in data.certifications
            }

        worker = WarehouseWorker(
            tenant_id=self.tenant_id,
            employee_code=data.employee_code,
            first_name=data.first_name,
            last_name=data.last_name,
            email=data.email,
            phone=data.phone,
            worker_type=data.worker_type.value,
            hire_date=data.hire_date,
            primary_warehouse_id=data.primary_warehouse_id,
            primary_zone_id=data.primary_zone_id,
            supervisor_id=data.supervisor_id,
            user_id=data.user_id,
            skills=data.skills,
            certifications=certifications,
            equipment_certified=data.equipment_certified,
            preferred_shift=data.preferred_shift.value if data.preferred_shift else None,
            max_hours_per_week=data.max_hours_per_week,
            can_work_overtime=data.can_work_overtime,
            can_work_weekends=data.can_work_weekends,
            hourly_rate=data.hourly_rate,
            overtime_multiplier=data.overtime_multiplier,
            annual_leave_balance=data.annual_leave_balance,
            sick_leave_balance=data.sick_leave_balance,
            casual_leave_balance=data.casual_leave_balance,
            notes=data.notes,
            status="ACTIVE"
        )

        self.db.add(worker)
        await self.db.flush()
        await self.db.refresh(worker)
        return worker

    async def get_worker(self, worker_id: uuid.UUID) -> WarehouseWorker:
        """Get worker by ID."""
        result = await self.db.execute(
            select(WarehouseWorker)
            .options(selectinload(WarehouseWorker.supervisor))
            .where(
                WarehouseWorker.id == worker_id,
                WarehouseWorker.tenant_id == self.tenant_id
            )
        )
        worker = result.scalar_one_or_none()
        if not worker:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Worker not found"
            )
        return worker

    async def get_workers(
        self,
        skip: int = 0,
        limit: int = 20,
        warehouse_id: Optional[uuid.UUID] = None,
        status: Optional[str] = None,
        worker_type: Optional[str] = None,
        supervisor_id: Optional[uuid.UUID] = None,
        search: Optional[str] = None
    ) -> Tuple[List[WarehouseWorker], int]:
        """Get paginated list of workers."""
        query = select(WarehouseWorker).where(
            WarehouseWorker.tenant_id == self.tenant_id
        )

        if warehouse_id:
            query = query.where(WarehouseWorker.primary_warehouse_id == warehouse_id)
        if status:
            query = query.where(WarehouseWorker.status == status)
        if worker_type:
            query = query.where(WarehouseWorker.worker_type == worker_type)
        if supervisor_id:
            query = query.where(WarehouseWorker.supervisor_id == supervisor_id)
        if search:
            query = query.where(
                or_(
                    WarehouseWorker.first_name.ilike(f"%{search}%"),
                    WarehouseWorker.last_name.ilike(f"%{search}%"),
                    WarehouseWorker.employee_code.ilike(f"%{search}%")
                )
            )

        # Count
        count_query = select(func.count()).select_from(query.subquery())
        total = (await self.db.execute(count_query)).scalar() or 0

        # Fetch
        query = query.order_by(WarehouseWorker.first_name).offset(skip).limit(limit)
        result = await self.db.execute(query)

        return result.scalars().all(), total

    async def update_worker(
        self,
        worker_id: uuid.UUID,
        data: WorkerUpdate
    ) -> WarehouseWorker:
        """Update worker profile."""
        worker = await self.get_worker(worker_id)

        update_data = data.model_dump(exclude_unset=True)

        # Handle enum conversions
        if "worker_type" in update_data and update_data["worker_type"]:
            update_data["worker_type"] = update_data["worker_type"].value
        if "status" in update_data and update_data["status"]:
            update_data["status"] = update_data["status"].value
        if "preferred_shift" in update_data and update_data["preferred_shift"]:
            update_data["preferred_shift"] = update_data["preferred_shift"].value

        for field, value in update_data.items():
            setattr(worker, field, value)

        await self.db.flush()
        await self.db.refresh(worker)
        return worker

    async def terminate_worker(
        self,
        worker_id: uuid.UUID,
        termination_date: date,
        reason: Optional[str] = None
    ) -> WarehouseWorker:
        """Terminate a worker."""
        worker = await self.get_worker(worker_id)

        worker.status = "TERMINATED"
        worker.termination_date = termination_date
        if reason:
            worker.notes = f"{worker.notes or ''}\nTermination: {reason}"

        await self.db.flush()
        await self.db.refresh(worker)
        return worker

    # =========================================================================
    # SHIFT MANAGEMENT
    # =========================================================================

    async def create_shift(
        self,
        data: ShiftCreate,
        created_by: Optional[uuid.UUID] = None
    ) -> WorkShift:
        """Create a work shift."""
        # Check for existing shift on same date
        existing = await self.db.execute(
            select(WorkShift).where(
                WorkShift.tenant_id == self.tenant_id,
                WorkShift.worker_id == data.worker_id,
                WorkShift.shift_date == data.shift_date,
                WorkShift.status != "CANCELLED"
            )
        )
        if existing.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Worker already has a shift scheduled for this date"
            )

        shift = WorkShift(
            tenant_id=self.tenant_id,
            worker_id=data.worker_id,
            warehouse_id=data.warehouse_id,
            shift_date=data.shift_date,
            shift_type=data.shift_type.value,
            scheduled_start=data.scheduled_start,
            scheduled_end=data.scheduled_end,
            scheduled_break_minutes=data.scheduled_break_minutes,
            assigned_zone_id=data.assigned_zone_id,
            assigned_function=data.assigned_function,
            supervisor_id=data.supervisor_id,
            is_overtime=data.is_overtime,
            notes=data.notes,
            status="SCHEDULED"
        )

        self.db.add(shift)
        await self.db.flush()
        await self.db.refresh(shift)
        return shift

    async def create_bulk_shifts(
        self,
        data: BulkShiftCreate,
        created_by: Optional[uuid.UUID] = None
    ) -> List[WorkShift]:
        """Create shifts for multiple workers."""
        shifts = []
        for worker_id in data.worker_ids:
            # Check for existing shift
            existing = await self.db.execute(
                select(WorkShift).where(
                    WorkShift.tenant_id == self.tenant_id,
                    WorkShift.worker_id == worker_id,
                    WorkShift.shift_date == data.shift_date,
                    WorkShift.status != "CANCELLED"
                )
            )
            if existing.scalar_one_or_none():
                continue  # Skip if already scheduled

            shift = WorkShift(
                tenant_id=self.tenant_id,
                worker_id=worker_id,
                warehouse_id=data.warehouse_id,
                shift_date=data.shift_date,
                shift_type=data.shift_type.value,
                scheduled_start=data.scheduled_start,
                scheduled_end=data.scheduled_end,
                scheduled_break_minutes=data.scheduled_break_minutes,
                assigned_function=data.assigned_function,
                status="SCHEDULED"
            )
            self.db.add(shift)
            shifts.append(shift)

        await self.db.flush()
        for shift in shifts:
            await self.db.refresh(shift)

        return shifts

    async def get_shift(self, shift_id: uuid.UUID) -> WorkShift:
        """Get shift by ID."""
        result = await self.db.execute(
            select(WorkShift)
            .options(selectinload(WorkShift.worker))
            .where(
                WorkShift.id == shift_id,
                WorkShift.tenant_id == self.tenant_id
            )
        )
        shift = result.scalar_one_or_none()
        if not shift:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Shift not found"
            )
        return shift

    async def get_shifts(
        self,
        skip: int = 0,
        limit: int = 20,
        worker_id: Optional[uuid.UUID] = None,
        warehouse_id: Optional[uuid.UUID] = None,
        shift_date: Optional[date] = None,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
        status: Optional[str] = None
    ) -> Tuple[List[WorkShift], int]:
        """Get paginated list of shifts."""
        query = select(WorkShift).where(
            WorkShift.tenant_id == self.tenant_id
        )

        if worker_id:
            query = query.where(WorkShift.worker_id == worker_id)
        if warehouse_id:
            query = query.where(WorkShift.warehouse_id == warehouse_id)
        if shift_date:
            query = query.where(WorkShift.shift_date == shift_date)
        if date_from:
            query = query.where(WorkShift.shift_date >= date_from)
        if date_to:
            query = query.where(WorkShift.shift_date <= date_to)
        if status:
            query = query.where(WorkShift.status == status)

        # Count
        count_query = select(func.count()).select_from(query.subquery())
        total = (await self.db.execute(count_query)).scalar() or 0

        # Fetch
        query = query.order_by(WorkShift.shift_date.desc(), WorkShift.scheduled_start)
        query = query.offset(skip).limit(limit)
        result = await self.db.execute(query)

        return result.scalars().all(), total

    async def clock_in(
        self,
        shift_id: uuid.UUID,
        data: ClockInRequest
    ) -> WorkShift:
        """Clock in for a shift."""
        shift = await self.get_shift(shift_id)

        if shift.status not in ["SCHEDULED"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot clock in for shift in {shift.status} status"
            )

        now = datetime.now(timezone.utc)
        shift.actual_start = now
        shift.status = "IN_PROGRESS"

        if data.notes:
            shift.notes = f"{shift.notes or ''}\nClock in: {data.notes}"

        await self.db.flush()
        await self.db.refresh(shift)
        return shift

    async def clock_out(
        self,
        shift_id: uuid.UUID,
        data: ClockOutRequest
    ) -> WorkShift:
        """Clock out from a shift."""
        shift = await self.get_shift(shift_id)

        if shift.status != "IN_PROGRESS":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot clock out for shift in {shift.status} status"
            )

        now = datetime.now(timezone.utc)
        shift.actual_end = now
        shift.actual_break_minutes = data.break_minutes
        shift.status = "COMPLETED"

        # Calculate overtime if applicable
        if shift.actual_hours and shift.scheduled_hours:
            extra_hours = shift.actual_hours - shift.scheduled_hours
            if extra_hours > 0.25:  # More than 15 minutes extra
                shift.overtime_hours = Decimal(str(round(extra_hours, 2)))

        if data.notes:
            shift.notes = f"{shift.notes or ''}\nClock out: {data.notes}"

        await self.db.flush()
        await self.db.refresh(shift)
        return shift

    async def mark_no_show(
        self,
        shift_id: uuid.UUID,
        reason: Optional[str] = None
    ) -> WorkShift:
        """Mark shift as no-show."""
        shift = await self.get_shift(shift_id)

        if shift.status != "SCHEDULED":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot mark no-show for shift in {shift.status} status"
            )

        shift.status = "NO_SHOW"
        shift.no_show_reason = reason

        # Update worker's absence count
        worker = await self.get_worker(shift.worker_id)
        worker.absence_count_ytd += 1

        await self.db.flush()
        await self.db.refresh(shift)
        return shift

    async def cancel_shift(
        self,
        shift_id: uuid.UUID,
        reason: Optional[str] = None
    ) -> WorkShift:
        """Cancel a shift."""
        shift = await self.get_shift(shift_id)

        if shift.status not in ["SCHEDULED"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot cancel shift in {shift.status} status"
            )

        shift.status = "CANCELLED"
        if reason:
            shift.notes = f"{shift.notes or ''}\nCancelled: {reason}"

        await self.db.flush()
        await self.db.refresh(shift)
        return shift

    # =========================================================================
    # SHIFT TEMPLATES
    # =========================================================================

    async def create_shift_template(
        self,
        data: ShiftTemplateCreate
    ) -> ShiftTemplate:
        """Create a shift template."""
        template = ShiftTemplate(
            tenant_id=self.tenant_id,
            name=data.name,
            shift_type=data.shift_type.value,
            warehouse_id=data.warehouse_id,
            start_time=data.start_time,
            end_time=data.end_time,
            break_duration_minutes=data.break_duration_minutes,
            days_of_week=data.days_of_week,
            min_workers=data.min_workers,
            max_workers=data.max_workers,
            ideal_workers=data.ideal_workers,
            notes=data.notes
        )

        self.db.add(template)
        await self.db.flush()
        await self.db.refresh(template)
        return template

    async def get_shift_templates(
        self,
        warehouse_id: Optional[uuid.UUID] = None
    ) -> List[ShiftTemplate]:
        """Get shift templates."""
        query = select(ShiftTemplate).where(
            ShiftTemplate.tenant_id == self.tenant_id,
            ShiftTemplate.is_active == True
        )

        if warehouse_id:
            query = query.where(ShiftTemplate.warehouse_id == warehouse_id)

        result = await self.db.execute(query.order_by(ShiftTemplate.name))
        return result.scalars().all()

    # =========================================================================
    # LABOR STANDARDS
    # =========================================================================

    async def create_labor_standard(
        self,
        data: LaborStandardCreate,
        created_by: Optional[uuid.UUID] = None
    ) -> LaborStandard:
        """Create a labor standard."""
        standard = LaborStandard(
            tenant_id=self.tenant_id,
            warehouse_id=data.warehouse_id,
            function=data.function,
            zone_id=data.zone_id,
            units_per_hour=data.units_per_hour,
            lines_per_hour=data.lines_per_hour,
            orders_per_hour=data.orders_per_hour,
            travel_time_per_pick=data.travel_time_per_pick,
            pick_time_per_unit=data.pick_time_per_unit,
            setup_time=data.setup_time,
            threshold_minimum=data.threshold_minimum,
            threshold_target=data.threshold_target,
            threshold_excellent=data.threshold_excellent,
            effective_from=data.effective_from,
            effective_to=data.effective_to,
            notes=data.notes,
            created_by=created_by
        )

        self.db.add(standard)
        await self.db.flush()
        await self.db.refresh(standard)
        return standard

    async def get_labor_standards(
        self,
        warehouse_id: Optional[uuid.UUID] = None,
        function: Optional[str] = None,
        active_only: bool = True
    ) -> List[LaborStandard]:
        """Get labor standards."""
        query = select(LaborStandard).where(
            LaborStandard.tenant_id == self.tenant_id
        )

        if warehouse_id:
            query = query.where(LaborStandard.warehouse_id == warehouse_id)
        if function:
            query = query.where(LaborStandard.function == function)
        if active_only:
            query = query.where(LaborStandard.is_active == True)

        result = await self.db.execute(query.order_by(LaborStandard.function))
        return result.scalars().all()

    # =========================================================================
    # LEAVE MANAGEMENT
    # =========================================================================

    async def create_leave_request(
        self,
        data: LeaveRequestCreate
    ) -> WarehouseLeaveRequest:
        """Create a leave request."""
        # Calculate days
        days = (data.end_date - data.start_date).days + 1

        # Check leave balance
        worker = await self.get_worker(data.worker_id)
        leave_type = data.leave_type.value

        if leave_type == "ANNUAL" and worker.annual_leave_balance < days:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Insufficient annual leave balance"
            )
        elif leave_type == "SICK" and worker.sick_leave_balance < days:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Insufficient sick leave balance"
            )
        elif leave_type == "CASUAL" and worker.casual_leave_balance < days:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Insufficient casual leave balance"
            )

        leave_request = WarehouseLeaveRequest(
            tenant_id=self.tenant_id,
            worker_id=data.worker_id,
            leave_type=leave_type,
            start_date=data.start_date,
            end_date=data.end_date,
            days_requested=Decimal(str(days)),
            reason=data.reason,
            status="PENDING"
        )

        self.db.add(leave_request)
        await self.db.flush()
        await self.db.refresh(leave_request)
        return leave_request

    async def get_leave_request(self, request_id: uuid.UUID) -> WarehouseLeaveRequest:
        """Get leave request by ID."""
        result = await self.db.execute(
            select(WarehouseLeaveRequest)
            .options(selectinload(WarehouseLeaveRequest.worker))
            .where(
                WarehouseLeaveRequest.id == request_id,
                WarehouseLeaveRequest.tenant_id == self.tenant_id
            )
        )
        leave_req = result.scalar_one_or_none()
        if not leave_req:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Leave request not found"
            )
        return leave_req

    async def get_leave_requests(
        self,
        skip: int = 0,
        limit: int = 20,
        worker_id: Optional[uuid.UUID] = None,
        status: Optional[str] = None
    ) -> Tuple[List[WarehouseLeaveRequest], int]:
        """Get paginated leave requests."""
        query = select(WarehouseLeaveRequest).where(
            WarehouseLeaveRequest.tenant_id == self.tenant_id
        )

        if worker_id:
            query = query.where(WarehouseLeaveRequest.worker_id == worker_id)
        if status:
            query = query.where(WarehouseLeaveRequest.status == status)

        # Count
        count_query = select(func.count()).select_from(query.subquery())
        total = (await self.db.execute(count_query)).scalar() or 0

        # Fetch
        query = query.order_by(WarehouseLeaveRequest.created_at.desc())
        query = query.offset(skip).limit(limit)
        result = await self.db.execute(query)

        return result.scalars().all(), total

    async def approve_leave_request(
        self,
        request_id: uuid.UUID,
        approver_id: uuid.UUID
    ) -> WarehouseLeaveRequest:
        """Approve a leave request."""
        leave_req = await self.get_leave_request(request_id)

        if leave_req.status != "PENDING":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot approve request in {leave_req.status} status"
            )

        leave_req.status = "APPROVED"
        leave_req.approved_by = approver_id
        leave_req.approved_at = datetime.now(timezone.utc)

        # Deduct leave balance
        worker = await self.get_worker(leave_req.worker_id)
        days = leave_req.days_requested

        if leave_req.leave_type == "ANNUAL":
            worker.annual_leave_balance -= days
        elif leave_req.leave_type == "SICK":
            worker.sick_leave_balance -= days
        elif leave_req.leave_type == "CASUAL":
            worker.casual_leave_balance -= days

        await self.db.flush()
        await self.db.refresh(leave_req)
        return leave_req

    async def reject_leave_request(
        self,
        request_id: uuid.UUID,
        reason: str,
        rejector_id: uuid.UUID
    ) -> WarehouseLeaveRequest:
        """Reject a leave request."""
        leave_req = await self.get_leave_request(request_id)

        if leave_req.status != "PENDING":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot reject request in {leave_req.status} status"
            )

        leave_req.status = "REJECTED"
        leave_req.rejection_reason = reason
        leave_req.approved_by = rejector_id
        leave_req.approved_at = datetime.now(timezone.utc)

        await self.db.flush()
        await self.db.refresh(leave_req)
        return leave_req

    # =========================================================================
    # PRODUCTIVITY METRICS
    # =========================================================================

    async def get_productivity_metrics(
        self,
        skip: int = 0,
        limit: int = 20,
        worker_id: Optional[uuid.UUID] = None,
        warehouse_id: Optional[uuid.UUID] = None,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
        function: Optional[str] = None
    ) -> Tuple[List[ProductivityMetric], int]:
        """Get paginated productivity metrics."""
        query = select(ProductivityMetric).where(
            ProductivityMetric.tenant_id == self.tenant_id
        )

        if worker_id:
            query = query.where(ProductivityMetric.worker_id == worker_id)
        if warehouse_id:
            query = query.where(ProductivityMetric.warehouse_id == warehouse_id)
        if date_from:
            query = query.where(ProductivityMetric.metric_date >= date_from)
        if date_to:
            query = query.where(ProductivityMetric.metric_date <= date_to)
        if function:
            query = query.where(ProductivityMetric.function == function)

        # Count
        count_query = select(func.count()).select_from(query.subquery())
        total = (await self.db.execute(count_query)).scalar() or 0

        # Fetch
        query = query.order_by(ProductivityMetric.metric_date.desc())
        query = query.offset(skip).limit(limit)
        result = await self.db.execute(query)

        return result.scalars().all(), total

    async def calculate_daily_productivity(
        self,
        worker_id: uuid.UUID,
        metric_date: date
    ) -> Optional[ProductivityMetric]:
        """Calculate daily productivity for a worker."""
        # Get completed shift for the day
        shift_result = await self.db.execute(
            select(WorkShift).where(
                WorkShift.tenant_id == self.tenant_id,
                WorkShift.worker_id == worker_id,
                WorkShift.shift_date == metric_date,
                WorkShift.status == "COMPLETED"
            )
        )
        shift = shift_result.scalar_one_or_none()

        if not shift or not shift.actual_hours:
            return None

        # Get worker for hourly rate
        worker = await self.get_worker(worker_id)

        # Get labor standard
        standard_result = await self.db.execute(
            select(LaborStandard).where(
                LaborStandard.tenant_id == self.tenant_id,
                LaborStandard.warehouse_id == shift.warehouse_id,
                LaborStandard.function == (shift.assigned_function or "PICKING"),
                LaborStandard.is_active == True
            )
        )
        standard = standard_result.scalar_one_or_none()

        # Calculate metrics
        hours_worked = Decimal(str(shift.actual_hours))
        productive_hours = Decimal(str((shift.productive_minutes or 0) / 60))
        idle_hours = Decimal(str((shift.idle_minutes or 0) / 60))

        units_processed = shift.units_processed
        units_per_hour = Decimal(str(units_processed / float(hours_worked))) if hours_worked > 0 else Decimal("0")

        standard_uph = standard.units_per_hour if standard else Decimal("100")
        performance_pct = (units_per_hour / standard_uph * 100) if standard_uph > 0 else Decimal("0")

        accuracy = Decimal("100")
        if units_processed > 0:
            accuracy = Decimal(str(((units_processed - shift.errors_count) / units_processed) * 100))

        labor_cost = hours_worked * worker.hourly_rate
        if shift.overtime_hours > 0:
            labor_cost += shift.overtime_hours * worker.hourly_rate * worker.overtime_multiplier

        cost_per_unit = labor_cost / units_processed if units_processed > 0 else Decimal("0")

        # Create or update metric
        existing_result = await self.db.execute(
            select(ProductivityMetric).where(
                ProductivityMetric.tenant_id == self.tenant_id,
                ProductivityMetric.worker_id == worker_id,
                ProductivityMetric.metric_date == metric_date,
                ProductivityMetric.function == (shift.assigned_function or "PICKING")
            )
        )
        metric = existing_result.scalar_one_or_none()

        if not metric:
            metric = ProductivityMetric(
                tenant_id=self.tenant_id,
                worker_id=worker_id,
                warehouse_id=shift.warehouse_id,
                metric_date=metric_date,
                function=shift.assigned_function or "PICKING"
            )
            self.db.add(metric)

        metric.hours_worked = hours_worked
        metric.productive_hours = productive_hours
        metric.idle_hours = idle_hours
        metric.units_processed = units_processed
        metric.tasks_completed = shift.tasks_completed
        metric.units_per_hour = units_per_hour
        metric.standard_units_per_hour = standard_uph
        metric.performance_percentage = performance_pct
        metric.errors_count = shift.errors_count
        metric.accuracy_rate = accuracy
        metric.labor_cost = labor_cost
        metric.cost_per_unit = cost_per_unit

        await self.db.flush()
        await self.db.refresh(metric)
        return metric

    # =========================================================================
    # STATISTICS
    # =========================================================================

    async def get_labor_dashboard_stats(
        self,
        warehouse_id: Optional[uuid.UUID] = None
    ) -> LaborDashboardStats:
        """Get labor management dashboard statistics."""
        today = date.today()

        # Base filter
        worker_filter = [WarehouseWorker.tenant_id == self.tenant_id]
        if warehouse_id:
            worker_filter.append(WarehouseWorker.primary_warehouse_id == warehouse_id)

        shift_filter = [
            WorkShift.tenant_id == self.tenant_id,
            WorkShift.shift_date == today
        ]
        if warehouse_id:
            shift_filter.append(WorkShift.warehouse_id == warehouse_id)

        # Worker counts
        total_workers = await self.db.execute(
            select(func.count()).where(
                *worker_filter,
                WarehouseWorker.status != "TERMINATED"
            )
        )
        active_workers = await self.db.execute(
            select(func.count()).where(
                *worker_filter,
                WarehouseWorker.status == "ACTIVE"
            )
        )
        on_leave = await self.db.execute(
            select(func.count()).where(
                *worker_filter,
                WarehouseWorker.status == "ON_LEAVE"
            )
        )

        # Shift counts
        shifts_scheduled = await self.db.execute(
            select(func.count()).where(*shift_filter)
        )
        shifts_in_progress = await self.db.execute(
            select(func.count()).where(
                *shift_filter,
                WorkShift.status == "IN_PROGRESS"
            )
        )
        shifts_completed = await self.db.execute(
            select(func.count()).where(
                *shift_filter,
                WorkShift.status == "COMPLETED"
            )
        )
        no_shows = await self.db.execute(
            select(func.count()).where(
                *shift_filter,
                WorkShift.status == "NO_SHOW"
            )
        )

        # Productivity today
        units_result = await self.db.execute(
            select(func.coalesce(func.sum(WorkShift.units_processed), 0)).where(
                *shift_filter,
                WorkShift.status.in_(["IN_PROGRESS", "COMPLETED"])
            )
        )
        total_units = units_result.scalar() or 0

        workers_working = (shifts_in_progress.scalar() or 0) + (shifts_completed.scalar() or 0)
        avg_units_per_worker = Decimal(str(total_units / workers_working)) if workers_working > 0 else Decimal("0")

        # Overtime
        overtime_result = await self.db.execute(
            select(func.coalesce(func.sum(WorkShift.overtime_hours), 0)).where(
                *shift_filter
            )
        )
        workers_overtime = await self.db.execute(
            select(func.count()).where(
                *shift_filter,
                WorkShift.overtime_hours > 0
            )
        )

        # Leave requests
        pending_leave = await self.db.execute(
            select(func.count()).where(
                WarehouseLeaveRequest.tenant_id == self.tenant_id,
                WarehouseLeaveRequest.status == "PENDING"
            )
        )
        approved_leave_today = await self.db.execute(
            select(func.count()).where(
                WarehouseLeaveRequest.tenant_id == self.tenant_id,
                WarehouseLeaveRequest.status == "APPROVED",
                WarehouseLeaveRequest.start_date <= today,
                WarehouseLeaveRequest.end_date >= today
            )
        )

        return LaborDashboardStats(
            total_workers=total_workers.scalar() or 0,
            active_workers=active_workers.scalar() or 0,
            workers_on_leave=on_leave.scalar() or 0,
            workers_clocked_in=shifts_in_progress.scalar() or 0,
            shifts_scheduled_today=shifts_scheduled.scalar() or 0,
            shifts_in_progress=shifts_in_progress.scalar() or 0,
            shifts_completed_today=shifts_completed.scalar() or 0,
            no_shows_today=no_shows.scalar() or 0,
            avg_performance_percentage=Decimal("0"),  # Would need metric aggregation
            total_units_today=total_units,
            avg_units_per_worker=avg_units_per_worker,
            overtime_hours_today=overtime_result.scalar() or Decimal("0"),
            workers_on_overtime=workers_overtime.scalar() or 0,
            estimated_labor_cost_today=Decimal("0"),  # Would need hourly rate calculation
            pending_leave_requests=pending_leave.scalar() or 0,
            workers_on_approved_leave=approved_leave_today.scalar() or 0
        )
