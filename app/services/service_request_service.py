"""Service Request Service for managing service operations."""
from typing import Optional, List, Tuple
from datetime import datetime, date, timedelta, timezone
import uuid

from sqlalchemy import select, func, and_, or_, update, case
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload, joinedload

from app.models.service_request import (
    ServiceRequest, ServiceType, ServicePriority, ServiceStatus, ServiceSource,
    ServiceStatusHistory, PartsRequest,
)
from app.models.technician import Technician, TechnicianStatus, TechnicianJobHistory
from app.models.installation import Installation, InstallationStatus, WarrantyClaim
from app.models.amc import AMCContract, AMCStatus
from app.models.customer import Customer


class ServiceRequestService:
    """Service for service request operations."""

    def __init__(self, db: AsyncSession):
        self.db = db

    # ==================== SERVICE REQUEST METHODS ====================

    async def get_service_requests(
        self,
        customer_id: Optional[uuid.UUID] = None,
        technician_id: Optional[uuid.UUID] = None,
        status: Optional[ServiceStatus] = None,
        service_type: Optional[ServiceType] = None,
        priority: Optional[ServicePriority] = None,
        region_id: Optional[uuid.UUID] = None,
        pincode: Optional[str] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        search: Optional[str] = None,
        skip: int = 0,
        limit: int = 20,
    ) -> Tuple[List[ServiceRequest], int]:
        """Get paginated list of service requests."""
        query = select(ServiceRequest).options(
            joinedload(ServiceRequest.customer),
            joinedload(ServiceRequest.technician),
        )

        conditions = []
        if customer_id:
            conditions.append(ServiceRequest.customer_id == customer_id)
        if technician_id:
            conditions.append(ServiceRequest.technician_id == technician_id)
        if status:
            conditions.append(ServiceRequest.status == status)
        if service_type:
            conditions.append(ServiceRequest.service_type == service_type)
        if priority:
            conditions.append(ServiceRequest.priority == priority)
        if region_id:
            conditions.append(ServiceRequest.region_id == region_id)
        if pincode:
            conditions.append(ServiceRequest.service_pincode == pincode)
        if date_from:
            conditions.append(ServiceRequest.created_at >= date_from)
        if date_to:
            conditions.append(ServiceRequest.created_at <= date_to)
        if search:
            conditions.append(
                or_(
                    ServiceRequest.ticket_number.ilike(f"%{search}%"),
                    ServiceRequest.title.ilike(f"%{search}%"),
                    ServiceRequest.serial_number.ilike(f"%{search}%"),
                )
            )

        if conditions:
            query = query.where(and_(*conditions))

        # Count
        count_query = select(func.count()).select_from(query.subquery())
        total = await self.db.scalar(count_query)

        # Paginate
        query = query.order_by(ServiceRequest.created_at.desc()).offset(skip).limit(limit)
        result = await self.db.execute(query)

        return result.scalars().unique().all(), total

    async def get_service_request_by_id(
        self,
        request_id: uuid.UUID,
        include_history: bool = False,
    ) -> Optional[ServiceRequest]:
        """Get service request by ID."""
        query = select(ServiceRequest).options(
            joinedload(ServiceRequest.customer),
            joinedload(ServiceRequest.technician),
            joinedload(ServiceRequest.product),
        )

        if include_history:
            query = query.options(
                selectinload(ServiceRequest.status_history),
            )

        query = query.where(ServiceRequest.id == request_id)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def get_service_request_by_ticket(self, ticket_number: str) -> Optional[ServiceRequest]:
        """Get service request by ticket number."""
        query = select(ServiceRequest).options(
            joinedload(ServiceRequest.customer),
            joinedload(ServiceRequest.technician),
        ).where(ServiceRequest.ticket_number == ticket_number)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def create_service_request(
        self,
        data: dict,
        created_by: uuid.UUID,
    ) -> ServiceRequest:
        """Create a new service request."""
        # Generate ticket number
        ticket_number = await self._generate_ticket_number()

        # Calculate SLA breach time (e.g., 48 hours for normal priority)
        sla_hours = {
            ServicePriority.LOW: 72,
            ServicePriority.NORMAL: 48,
            ServicePriority.HIGH: 24,
            ServicePriority.URGENT: 12,
            ServicePriority.CRITICAL: 4,
        }
        priority = data.get("priority", ServicePriority.NORMAL)
        sla_breach_at = datetime.now(timezone.utc) + timedelta(hours=sla_hours.get(priority, 48))

        service_request = ServiceRequest(
            ticket_number=ticket_number,
            sla_breach_at=sla_breach_at,
            created_by=created_by,
            **data,
        )
        self.db.add(service_request)

        # Create initial status history
        status_history = ServiceStatusHistory(
            service_request_id=service_request.id,
            to_status=ServiceStatus.PENDING,
            changed_by=created_by,
            notes="Service request created",
        )
        self.db.add(status_history)

        await self.db.commit()
        await self.db.refresh(service_request)
        return service_request

    async def update_service_request(
        self,
        request_id: uuid.UUID,
        data: dict,
    ) -> Optional[ServiceRequest]:
        """Update a service request."""
        service_request = await self.get_service_request_by_id(request_id)
        if not service_request:
            return None

        for key, value in data.items():
            if hasattr(service_request, key):
                setattr(service_request, key, value)

        await self.db.commit()
        await self.db.refresh(service_request)
        return service_request

    async def update_status(
        self,
        request_id: uuid.UUID,
        new_status: ServiceStatus,
        changed_by: uuid.UUID,
        notes: Optional[str] = None,
    ) -> Optional[ServiceRequest]:
        """Update service request status."""
        service_request = await self.get_service_request_by_id(request_id)
        if not service_request:
            return None

        old_status = service_request.status
        service_request.status = new_status

        # Update timestamps based on status
        now = datetime.now(timezone.utc)
        if new_status == ServiceStatus.IN_PROGRESS and not service_request.started_at:
            service_request.started_at = now
        elif new_status == ServiceStatus.COMPLETED:
            service_request.completed_at = now
            # Check SLA breach
            if now > service_request.sla_breach_at:
                service_request.is_sla_breached = True
        elif new_status == ServiceStatus.CLOSED:
            service_request.closed_at = now

        # Create status history
        status_history = ServiceStatusHistory(
            service_request_id=request_id,
            from_status=old_status,
            to_status=new_status,
            changed_by=changed_by,
            notes=notes,
        )
        self.db.add(status_history)

        await self.db.commit()
        await self.db.refresh(service_request)
        return service_request

    async def assign_technician(
        self,
        request_id: uuid.UUID,
        technician_id: uuid.UUID,
        assigned_by: uuid.UUID,
        scheduled_date: Optional[date] = None,
        scheduled_time_slot: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> Optional[ServiceRequest]:
        """Assign a technician to a service request."""
        service_request = await self.get_service_request_by_id(request_id)
        if not service_request:
            return None

        # Verify technician exists and is available
        technician = await self.db.get(Technician, technician_id)
        if not technician or technician.status != TechnicianStatus.ACTIVE:
            raise ValueError("Technician not available")

        service_request.technician_id = technician_id
        service_request.assigned_at = datetime.now(timezone.utc)
        service_request.assigned_by = assigned_by

        if scheduled_date:
            service_request.scheduled_date = scheduled_date
        if scheduled_time_slot:
            service_request.scheduled_time_slot = scheduled_time_slot

        # Update status
        if service_request.status == ServiceStatus.PENDING:
            service_request.status = ServiceStatus.ASSIGNED.value

        # Create job history
        job_history = TechnicianJobHistory(
            technician_id=technician_id,
            service_request_id=request_id,
            assigned_by=assigned_by,
            status="assigned",
            notes=notes,
        )
        self.db.add(job_history)

        # Create status history
        status_history = ServiceStatusHistory(
            service_request_id=request_id,
            from_status=ServiceStatus.PENDING,
            to_status=ServiceStatus.ASSIGNED,
            changed_by=assigned_by,
            notes=f"Assigned to technician: {technician.full_name}",
        )
        self.db.add(status_history)

        await self.db.commit()
        await self.db.refresh(service_request)
        return service_request

    async def complete_service(
        self,
        request_id: uuid.UUID,
        completion_data: dict,
        completed_by: uuid.UUID,
    ) -> Optional[ServiceRequest]:
        """Complete a service request."""
        service_request = await self.get_service_request_by_id(request_id)
        if not service_request:
            return None

        # Update service request with completion data
        service_request.resolution_type = completion_data.get("resolution_type")
        service_request.resolution_notes = completion_data.get("resolution_notes")
        service_request.root_cause = completion_data.get("root_cause")
        service_request.action_taken = completion_data.get("action_taken")
        service_request.parts_used = completion_data.get("parts_used")
        service_request.labor_charges = completion_data.get("labor_charges", 0)
        service_request.service_charges = completion_data.get("service_charges", 0)
        service_request.travel_charges = completion_data.get("travel_charges", 0)
        service_request.total_charges = (
            service_request.labor_charges +
            service_request.service_charges +
            service_request.travel_charges +
            service_request.total_parts_cost
        )
        service_request.is_chargeable = completion_data.get("is_chargeable", False)
        service_request.payment_collected = completion_data.get("payment_collected", 0)
        service_request.payment_mode = completion_data.get("payment_mode")
        service_request.images_before = completion_data.get("images_before")
        service_request.images_after = completion_data.get("images_after")
        service_request.customer_signature_url = completion_data.get("customer_signature_url")
        service_request.status = ServiceStatus.COMPLETED.value
        service_request.completed_at = datetime.now(timezone.utc)

        # Update technician job history
        if service_request.technician_id:
            job_query = select(TechnicianJobHistory).where(
                and_(
                    TechnicianJobHistory.service_request_id == request_id,
                    TechnicianJobHistory.technician_id == service_request.technician_id,
                )
            ).order_by(TechnicianJobHistory.assigned_at.desc())
            job_result = await self.db.execute(job_query)
            job = job_result.scalar_one_or_none()
            if job:
                job.completed_at = datetime.now(timezone.utc)
                job.status = "COMPLETED"  # UPPERCASE per coding standards
                if job.started_at:
                    job.time_taken_minutes = int((job.completed_at - job.started_at).total_seconds() / 60)

            # Update technician stats
            technician = await self.db.get(Technician, service_request.technician_id)
            if technician:
                technician.total_jobs_completed += 1
                technician.current_month_jobs += 1
                technician.last_job_date = datetime.now(timezone.utc)
                technician.is_available = True

        # Create status history
        status_history = ServiceStatusHistory(
            service_request_id=request_id,
            from_status=ServiceStatus.IN_PROGRESS,
            to_status=ServiceStatus.COMPLETED,
            changed_by=completed_by,
            notes="Service completed",
        )
        self.db.add(status_history)

        await self.db.commit()
        await self.db.refresh(service_request)
        return service_request

    async def add_feedback(
        self,
        request_id: uuid.UUID,
        rating: int,
        feedback: Optional[str] = None,
    ) -> Optional[ServiceRequest]:
        """Add customer feedback to service request."""
        service_request = await self.get_service_request_by_id(request_id)
        if not service_request:
            return None

        service_request.customer_rating = rating
        service_request.customer_feedback = feedback
        service_request.feedback_date = datetime.now(timezone.utc)

        # Update technician rating
        if service_request.technician_id:
            technician = await self.db.get(Technician, service_request.technician_id)
            if technician:
                # Recalculate average
                total = technician.average_rating * technician.total_ratings + rating
                technician.total_ratings += 1
                technician.average_rating = total / technician.total_ratings

            # Update job history
            job_query = select(TechnicianJobHistory).where(
                and_(
                    TechnicianJobHistory.service_request_id == request_id,
                    TechnicianJobHistory.technician_id == service_request.technician_id,
                )
            ).order_by(TechnicianJobHistory.assigned_at.desc())
            job_result = await self.db.execute(job_query)
            job = job_result.scalar_one_or_none()
            if job:
                job.customer_rating = rating
                job.customer_feedback = feedback

        await self.db.commit()
        await self.db.refresh(service_request)
        return service_request

    async def get_service_stats(
        self,
        region_id: Optional[uuid.UUID] = None,
        technician_id: Optional[uuid.UUID] = None,
    ) -> dict:
        """Get service statistics."""
        base_conditions = []
        if region_id:
            base_conditions.append(ServiceRequest.region_id == region_id)
        if technician_id:
            base_conditions.append(ServiceRequest.technician_id == technician_id)

        # Total requests
        total_query = select(func.count()).select_from(ServiceRequest)
        if base_conditions:
            total_query = total_query.where(and_(*base_conditions))
        total = await self.db.scalar(total_query) or 0

        # Status counts
        pending = await self._count_by_status(ServiceStatus.PENDING, base_conditions)
        assigned = await self._count_by_status(ServiceStatus.ASSIGNED, base_conditions)
        in_progress = await self._count_by_status(ServiceStatus.IN_PROGRESS, base_conditions)

        # Completed today
        today = datetime.now(timezone.utc).date()
        completed_query = select(func.count()).select_from(ServiceRequest).where(
            and_(
                ServiceRequest.status == ServiceStatus.COMPLETED,
                func.date(ServiceRequest.completed_at) == today,
                *base_conditions,
            )
        )
        completed_today = await self.db.scalar(completed_query) or 0

        # SLA breached
        sla_query = select(func.count()).select_from(ServiceRequest).where(
            and_(
                ServiceRequest.is_sla_breached == True,
                *base_conditions,
            )
        )
        sla_breached = await self.db.scalar(sla_query) or 0

        # Average resolution time (in hours)
        avg_time_query = select(
            func.avg(func.extract('epoch', ServiceRequest.completed_at - ServiceRequest.created_at) / 3600)
        ).where(
            and_(
                ServiceRequest.completed_at.isnot(None),
                *base_conditions,
            )
        )
        avg_time = await self.db.scalar(avg_time_query) or 0

        # Average rating
        avg_rating_query = select(func.avg(ServiceRequest.customer_rating)).where(
            and_(
                ServiceRequest.customer_rating.isnot(None),
                *base_conditions,
            )
        )
        avg_rating = await self.db.scalar(avg_rating_query) or 0

        return {
            "total_requests": total,
            "pending_requests": pending,
            "assigned_requests": assigned,
            "in_progress_requests": in_progress,
            "completed_today": completed_today,
            "sla_breached": sla_breached,
            "average_resolution_time_hours": float(avg_time),
            "average_rating": float(avg_rating),
        }

    async def _count_by_status(self, status: ServiceStatus, extra_conditions: list) -> int:
        """Count requests by status."""
        query = select(func.count()).select_from(ServiceRequest).where(
            and_(
                ServiceRequest.status == status,
                *extra_conditions,
            )
        )
        return await self.db.scalar(query) or 0

    async def _generate_ticket_number(self) -> str:
        """Generate unique ticket number."""
        date_part = datetime.now(timezone.utc).strftime("%Y%m%d")
        query = select(func.count()).select_from(ServiceRequest).where(
            ServiceRequest.ticket_number.like(f"SR-{date_part}%")
        )
        count = await self.db.scalar(query)
        return f"SR-{date_part}-{(count or 0) + 1:04d}"

    # ==================== AUTO ASSIGNMENT ====================

    async def auto_assign_technician(
        self,
        request_id: uuid.UUID,
        assigned_by: uuid.UUID,
    ) -> Optional[ServiceRequest]:
        """
        Automatically assign the best available technician to a service request.

        Selection criteria (in order of priority):
        1. Technician services the request's pincode
        2. Technician is ACTIVE and available
        3. Lowest current workload (current_month_jobs)
        4. Highest rating (average_rating)
        5. Higher skill level preferred

        Returns None if no suitable technician found.
        """
        service_request = await self.get_service_request_by_id(request_id)
        if not service_request:
            return None

        # Already assigned?
        if service_request.technician_id:
            return service_request

        # Get request pincode
        request_pincode = service_request.service_pincode
        if not request_pincode:
            # Try to get from customer address
            if service_request.customer_id:
                customer = await self.db.get(Customer, service_request.customer_id)
                if customer and customer.primary_address:
                    request_pincode = customer.primary_address.get("pincode")

        if not request_pincode:
            raise ValueError("Service request has no pincode for technician matching")

        # Find available technicians who service this pincode
        # Using PostgreSQL JSONB contains operator for pincode matching
        query = select(Technician).where(
            and_(
                Technician.status == "ACTIVE",
                Technician.is_available == True,
                # Check if technician's service_pincodes contains the request pincode
                or_(
                    Technician.service_pincodes.contains([request_pincode]),
                    # Also check if they're in the same region
                    Technician.region_id == service_request.region_id
                )
            )
        ).order_by(
            # Priority: lowest workload first
            Technician.current_month_jobs.asc(),
            # Then highest rating
            Technician.average_rating.desc(),
            # Then by skill level (we want higher skill)
            func.case(
                (Technician.skill_level == "MASTER", 5),
                (Technician.skill_level == "EXPERT", 4),
                (Technician.skill_level == "SENIOR", 3),
                (Technician.skill_level == "JUNIOR", 2),
                (Technician.skill_level == "TRAINEE", 1),
                else_=0
            ).desc()
        ).limit(1)

        result = await self.db.execute(query)
        best_technician = result.scalar_one_or_none()

        if not best_technician:
            return None

        # Assign the technician
        return await self.assign_technician(
            request_id=request_id,
            technician_id=best_technician.id,
            assigned_by=assigned_by,
            notes=f"Auto-assigned based on availability and workload",
        )

    async def bulk_auto_assign(
        self,
        assigned_by: uuid.UUID,
        region_id: Optional[uuid.UUID] = None,
        limit: int = 50,
    ) -> dict:
        """
        Auto-assign technicians to multiple pending service requests.

        Returns dict with counts: assigned, failed, skipped.
        """
        # Get pending requests without technicians
        query = select(ServiceRequest).where(
            and_(
                ServiceRequest.status == ServiceStatus.PENDING,
                ServiceRequest.technician_id.is_(None),
            )
        )

        if region_id:
            query = query.where(ServiceRequest.region_id == region_id)

        query = query.order_by(
            # Prioritize by SLA breach time (most urgent first)
            ServiceRequest.sla_breach_at.asc()
        ).limit(limit)

        result = await self.db.execute(query)
        pending_requests = result.scalars().all()

        stats = {"assigned": 0, "failed": 0, "skipped": 0}

        for request in pending_requests:
            try:
                assigned = await self.auto_assign_technician(
                    request_id=request.id,
                    assigned_by=assigned_by,
                )
                if assigned and assigned.technician_id:
                    stats["assigned"] += 1
                else:
                    stats["failed"] += 1
            except Exception as e:
                stats["failed"] += 1

        return stats
