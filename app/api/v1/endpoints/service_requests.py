"""Service Request API endpoints."""
from typing import Optional
import uuid
from math import ceil
from datetime import datetime, date

from fastapi import APIRouter, HTTPException, status, Query, Depends

from app.api.deps import DB, CurrentUser, require_permissions
from app.models.service_request import ServiceType, ServicePriority, ServiceStatus, ServiceSource
from app.schemas.service import (
    ServiceRequestCreate,
    ServiceRequestUpdate,
    ServiceStatusUpdate,
    TechnicianAssignment,
    ServiceCompletion,
    ServiceFeedback,
    ServiceRequestResponse,
    ServiceRequestDetail,
    ServiceRequestListResponse,
    ServiceStatusHistoryResponse,
    ServiceStats,
)
from app.schemas.customer import CustomerBrief
from app.services.service_request_service import ServiceRequestService
from app.core.module_decorators import require_module

router = APIRouter(tags=["Service Requests"])


def _build_service_response(sr) -> ServiceRequestResponse:
    """Build service request response."""
    return ServiceRequestResponse(
        id=sr.id,
        ticket_number=sr.ticket_number,
        service_type=sr.service_type,
        source=sr.source,
        priority=sr.priority,
        status=sr.status,
        customer=CustomerBrief(
            id=sr.customer.id,
            customer_code=sr.customer.customer_code,
            full_name=sr.customer.full_name,
            phone=sr.customer.phone,
            email=sr.customer.email,
        ),
        product_id=sr.product_id,
        serial_number=sr.serial_number,
        title=sr.title,
        description=sr.description,
        service_pincode=sr.service_pincode,
        service_city=sr.service_city,
        technician_id=sr.technician_id,
        scheduled_date=sr.scheduled_date,
        scheduled_time_slot=sr.scheduled_time_slot,
        is_sla_breached=sr.is_sla_breached,
        customer_rating=sr.customer_rating,
        total_charges=sr.total_charges,
        created_at=sr.created_at,
        updated_at=sr.updated_at,
    )


@router.get(
    "",
    response_model=ServiceRequestListResponse,
    dependencies=[Depends(require_permissions("service:view"))]
)
async def list_service_requests(
    db: DB,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    customer_id: Optional[uuid.UUID] = Query(None),
    technician_id: Optional[uuid.UUID] = Query(None),
    status: Optional[ServiceStatus] = Query(None),
    service_type: Optional[ServiceType] = Query(None),
    priority: Optional[ServicePriority] = Query(None),
    region_id: Optional[uuid.UUID] = Query(None),
    pincode: Optional[str] = Query(None),
    date_from: Optional[datetime] = Query(None),
    date_to: Optional[datetime] = Query(None),
    search: Optional[str] = Query(None),
):
    """
    Get paginated list of service requests.
    Requires: service:view permission
    """
    service = ServiceRequestService(db)
    skip = (page - 1) * size

    requests, total = await service.get_service_requests(
        customer_id=customer_id,
        technician_id=technician_id,
        status=status,
        service_type=service_type,
        priority=priority,
        region_id=region_id,
        pincode=pincode,
        date_from=date_from,
        date_to=date_to,
        search=search,
        skip=skip,
        limit=size,
    )

    return ServiceRequestListResponse(
        items=[_build_service_response(r) for r in requests],
        total=total,
        page=page,
        size=size,
        pages=ceil(total / size) if total > 0 else 1,
    )


@router.get(
    "/stats",
    response_model=ServiceStats,
    dependencies=[Depends(require_permissions("service:view"))]
)
async def get_service_stats(
    db: DB,
    region_id: Optional[uuid.UUID] = Query(None),
    technician_id: Optional[uuid.UUID] = Query(None),
):
    """Get service statistics."""
    service = ServiceRequestService(db)
    stats = await service.get_service_stats(
        region_id=region_id,
        technician_id=technician_id,
    )
    return ServiceStats(**stats)


@router.get(
    "/{request_id}",
    response_model=ServiceRequestDetail,
    dependencies=[Depends(require_permissions("service:view"))]
)
async def get_service_request(
    request_id: uuid.UUID,
    db: DB,
):
    """Get service request by ID."""
    service = ServiceRequestService(db)
    sr = await service.get_service_request_by_id(request_id, include_history=True)

    if not sr:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Service request not found"
        )

    response = ServiceRequestDetail(
        **_build_service_response(sr).model_dump(),
        customer_address_id=sr.customer_address_id,
        order_id=sr.order_id,
        installation_id=sr.installation_id,
        amc_id=sr.amc_id,
        symptoms=sr.symptoms,
        customer_reported_issue=sr.customer_reported_issue,
        service_address=sr.service_address,
        preferred_date=sr.preferred_date,
        preferred_time_slot=sr.preferred_time_slot,
        assigned_at=sr.assigned_at,
        started_at=sr.started_at,
        completed_at=sr.completed_at,
        closed_at=sr.closed_at,
        resolution_type=sr.resolution_type,
        resolution_notes=sr.resolution_notes,
        root_cause=sr.root_cause,
        action_taken=sr.action_taken,
        parts_used=sr.parts_used,
        total_parts_cost=sr.total_parts_cost,
        labor_charges=sr.labor_charges,
        service_charges=sr.service_charges,
        travel_charges=sr.travel_charges,
        is_chargeable=sr.is_chargeable,
        payment_status=sr.payment_status,
        payment_collected=sr.payment_collected,
        customer_feedback=sr.customer_feedback,
        images_before=sr.images_before,
        images_after=sr.images_after,
        internal_notes=sr.internal_notes,
        escalation_level=sr.escalation_level,
        product_name=sr.product.name if sr.product else None,
        technician_name=sr.technician.full_name if sr.technician else None,
    )
    return response


@router.get(
    "/ticket/{ticket_number}",
    response_model=ServiceRequestDetail,
    dependencies=[Depends(require_permissions("service:view"))]
)
async def get_service_request_by_ticket(
    ticket_number: str,
    db: DB,
):
    """Get service request by ticket number."""
    service = ServiceRequestService(db)
    sr = await service.get_service_request_by_ticket(ticket_number)

    if not sr:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Service request not found"
        )

    return await get_service_request(sr.id, db)


@router.post(
    "",
    response_model=ServiceRequestDetail,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permissions("service:create"))]
)
async def create_service_request(
    data: ServiceRequestCreate,
    db: DB,
    current_user: CurrentUser,
):
    """
    Create a new service request.
    Requires: service:create permission
    """
    service = ServiceRequestService(db)

    try:
        sr = await service.create_service_request(
            data.model_dump(),
            created_by=current_user.id,
        )
        return await get_service_request(sr.id, db)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.put(
    "/{request_id}",
    response_model=ServiceRequestDetail,
    dependencies=[Depends(require_permissions("service:update"))]
)
async def update_service_request(
    request_id: uuid.UUID,
    data: ServiceRequestUpdate,
    db: DB,
    current_user: CurrentUser,
):
    """
    Update a service request.
    Requires: service:update permission
    """
    service = ServiceRequestService(db)

    sr = await service.update_service_request(
        request_id,
        data.model_dump(exclude_unset=True),
    )

    if not sr:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Service request not found"
        )

    return await get_service_request(sr.id, db)


@router.put(
    "/{request_id}/status",
    response_model=ServiceRequestDetail,
    dependencies=[Depends(require_permissions("service:update"))]
)
async def update_service_status(
    request_id: uuid.UUID,
    data: ServiceStatusUpdate,
    db: DB,
    current_user: CurrentUser,
):
    """
    Update service request status.
    Requires: service:update permission
    """
    service = ServiceRequestService(db)

    sr = await service.update_status(
        request_id,
        data.status,
        changed_by=current_user.id,
        notes=data.notes,
    )

    if not sr:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Service request not found"
        )

    return await get_service_request(sr.id, db)


@router.post(
    "/{request_id}/assign",
    response_model=ServiceRequestDetail,
    dependencies=[Depends(require_permissions("service:assign"))]
)
async def assign_technician(
    request_id: uuid.UUID,
    data: TechnicianAssignment,
    db: DB,
    current_user: CurrentUser,
):
    """
    Assign a technician to service request.
    Requires: service:assign permission
    """
    service = ServiceRequestService(db)

    try:
        sr = await service.assign_technician(
            request_id,
            technician_id=data.technician_id,
            assigned_by=current_user.id,
            scheduled_date=data.scheduled_date,
            scheduled_time_slot=data.scheduled_time_slot,
            notes=data.notes,
        )

        if not sr:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Service request not found"
            )

        return await get_service_request(sr.id, db)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post(
    "/{request_id}/complete",
    response_model=ServiceRequestDetail,
    dependencies=[Depends(require_permissions("service:update"))]
)
async def complete_service(
    request_id: uuid.UUID,
    data: ServiceCompletion,
    db: DB,
    current_user: CurrentUser,
):
    """
    Complete a service request.
    Requires: service:update permission
    """
    service = ServiceRequestService(db)

    sr = await service.complete_service(
        request_id,
        data.model_dump(),
        completed_by=current_user.id,
    )

    if not sr:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Service request not found"
        )

    return await get_service_request(sr.id, db)


@router.post(
    "/{request_id}/feedback",
    response_model=ServiceRequestDetail,
)
@require_module("crm_service")
async def add_feedback(
    request_id: uuid.UUID,
    data: ServiceFeedback,
    db: DB,
):
    """Add customer feedback (no auth required)."""
    service = ServiceRequestService(db)

    sr = await service.add_feedback(
        request_id,
        rating=data.rating,
        feedback=data.feedback,
    )

    if not sr:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Service request not found"
        )

    return await get_service_request(sr.id, db)


@router.get(
    "/{request_id}/history",
    response_model=list[ServiceStatusHistoryResponse],
    dependencies=[Depends(require_permissions("service:view"))]
)
async def get_status_history(
    request_id: uuid.UUID,
    db: DB,
):
    """Get service request status history."""
    service = ServiceRequestService(db)
    sr = await service.get_service_request_by_id(request_id, include_history=True)

    if not sr:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Service request not found"
        )

    return [ServiceStatusHistoryResponse.model_validate(h) for h in sr.status_history]


# ==================== AUTO ASSIGNMENT ENDPOINTS ====================


@router.post(
    "/{request_id}/auto-assign",
    response_model=ServiceRequestDetail,
    dependencies=[Depends(require_permissions("service:assign"))]
)
async def auto_assign_technician(
    request_id: uuid.UUID,
    db: DB,
    current_user: CurrentUser,
):
    """
    Auto-assign the best available technician to a service request.

    Selection criteria:
    - Technician services the request's pincode
    - Technician is ACTIVE and available
    - Lowest current workload (current_month_jobs)
    - Highest rating (average_rating)
    - Higher skill level preferred

    Requires: service:assign permission
    """
    service = ServiceRequestService(db)

    try:
        sr = await service.auto_assign_technician(
            request_id=request_id,
            assigned_by=current_user.id,
        )

        if not sr:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No available technician found for this service area"
            )

        return await get_service_request(sr.id, db)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post(
    "/bulk-auto-assign",
    dependencies=[Depends(require_permissions("service:assign"))]
)
async def bulk_auto_assign_technicians(
    db: DB,
    current_user: CurrentUser,
    region_id: Optional[uuid.UUID] = Query(None),
    limit: int = Query(50, ge=1, le=100),
):
    """
    Auto-assign technicians to multiple pending service requests.

    Processes pending requests without technicians, prioritizing by SLA breach time.

    Requires: service:assign permission

    Returns:
    - assigned: Number of successfully assigned requests
    - failed: Number of requests where no technician was found
    - skipped: Number of skipped requests
    """
    service = ServiceRequestService(db)

    stats = await service.bulk_auto_assign(
        assigned_by=current_user.id,
        region_id=region_id,
        limit=limit,
    )

    return {
        "message": f"Auto-assignment completed",
        "assigned": stats["assigned"],
        "failed": stats["failed"],
        "skipped": stats["skipped"],
    }
