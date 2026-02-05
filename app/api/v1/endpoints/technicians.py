"""Technician API endpoints."""
from typing import Optional
import uuid
from math import ceil

from fastapi import APIRouter, HTTPException, status, Query, Depends
from sqlalchemy import select, func, and_, or_
from sqlalchemy.orm import joinedload

from app.api.deps import DB, CurrentUser, require_permissions
from app.models.technician import Technician, TechnicianStatus, TechnicianType, SkillLevel
from app.schemas.technician import (
    TechnicianCreate,
    TechnicianUpdate,
    TechnicianResponse,
    TechnicianDetail,
    TechnicianBrief,
    TechnicianListResponse,
    TechnicianLocationUpdate,
)
from datetime import datetime, timezone


router = APIRouter(tags=["Technicians"])


async def _generate_employee_code(db) -> str:
    """Generate unique employee code."""
    query = select(func.count()).select_from(Technician)
    count = await db.scalar(query)
    return f"TECH-{(count or 0) + 1:04d}"


@router.get(
    "",
    response_model=TechnicianListResponse,
    dependencies=[Depends(require_permissions("service:view"))]
)
async def list_technicians(
    db: DB,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    status: Optional[TechnicianStatus] = Query(None),
    technician_type: Optional[TechnicianType] = Query(None),
    skill_level: Optional[SkillLevel] = Query(None),
    region_id: Optional[uuid.UUID] = Query(None),
    is_available: Optional[bool] = Query(None),
    search: Optional[str] = Query(None),
):
    """
    Get paginated list of technicians.
    Requires: service:view permission
    """
    query = select(Technician)

    conditions = []
    if status:
        conditions.append(Technician.status == status)
    if technician_type:
        conditions.append(Technician.technician_type == technician_type)
    if skill_level:
        conditions.append(Technician.skill_level == skill_level)
    if region_id:
        conditions.append(Technician.region_id == region_id)
    if is_available is not None:
        conditions.append(Technician.is_available == is_available)
    if search:
        conditions.append(
            or_(
                Technician.first_name.ilike(f"%{search}%"),
                Technician.last_name.ilike(f"%{search}%"),
                Technician.phone.ilike(f"%{search}%"),
                Technician.employee_code.ilike(f"%{search}%"),
            )
        )

    if conditions:
        query = query.where(and_(*conditions))

    # Count
    count_query = select(func.count()).select_from(query.subquery())
    total = await db.scalar(count_query)

    # Paginate
    skip = (page - 1) * size
    query = query.order_by(Technician.employee_code).offset(skip).limit(size)
    result = await db.execute(query)
    technicians = result.scalars().all()

    return TechnicianListResponse(
        items=[TechnicianResponse.model_validate(t) for t in technicians],
        total=total,
        page=page,
        size=size,
        pages=ceil(total / size) if total > 0 else 1,
    )


@router.get(
    "/dropdown",
    response_model=list[TechnicianBrief],
    dependencies=[Depends(require_permissions("service:view"))]
)
async def get_technicians_dropdown(
    db: DB,
    region_id: Optional[uuid.UUID] = Query(None),
    pincode: Optional[str] = Query(None),
    is_available: bool = Query(True),
):
    """Get available technicians for dropdown."""
    query = select(Technician).where(
        and_(
            Technician.status == TechnicianStatus.ACTIVE,
            Technician.is_available == is_available,
        )
    )

    if region_id:
        query = query.where(Technician.region_id == region_id)

    query = query.order_by(Technician.average_rating.desc()).limit(50)
    result = await db.execute(query)
    technicians = result.scalars().all()

    # Filter by serviceable pincode if provided
    if pincode:
        technicians = [
            t for t in technicians
            if not t.service_pincodes or pincode in t.service_pincodes
        ]

    return [TechnicianBrief.model_validate(t) for t in technicians]


@router.get(
    "/{technician_id}",
    response_model=TechnicianDetail,
    dependencies=[Depends(require_permissions("service:view"))]
)
async def get_technician(
    technician_id: uuid.UUID,
    db: DB,
):
    """Get technician by ID."""
    query = select(Technician).where(Technician.id == technician_id)
    result = await db.execute(query)
    technician = result.scalar_one_or_none()

    if not technician:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Technician not found"
        )

    return TechnicianDetail.model_validate(technician)


@router.post(
    "",
    response_model=TechnicianDetail,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permissions("service:create"))]
)
async def create_technician(
    data: TechnicianCreate,
    db: DB,
    current_user: CurrentUser,
):
    """
    Create a new technician.
    Requires: service:create permission
    """
    # Check for duplicate phone
    existing_query = select(Technician).where(Technician.phone == data.phone)
    existing = await db.execute(existing_query)
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Technician with this phone number already exists"
        )

    # Generate employee code
    employee_code = await _generate_employee_code(db)

    technician = Technician(
        employee_code=employee_code,
        **data.model_dump(),
    )
    db.add(technician)
    await db.commit()
    await db.refresh(technician)

    return TechnicianDetail.model_validate(technician)


@router.put(
    "/{technician_id}",
    response_model=TechnicianDetail,
    dependencies=[Depends(require_permissions("service:update"))]
)
async def update_technician(
    technician_id: uuid.UUID,
    data: TechnicianUpdate,
    db: DB,
    current_user: CurrentUser,
):
    """
    Update a technician.
    Requires: service:update permission
    """
    query = select(Technician).where(Technician.id == technician_id)
    result = await db.execute(query)
    technician = result.scalar_one_or_none()

    if not technician:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Technician not found"
        )

    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        if hasattr(technician, key):
            setattr(technician, key, value)

    await db.commit()
    await db.refresh(technician)
    return TechnicianDetail.model_validate(technician)


@router.put(
    "/{technician_id}/location",
    response_model=TechnicianBrief,
    dependencies=[Depends(require_permissions("service:update"))]
)
async def update_technician_location(
    technician_id: uuid.UUID,
    data: TechnicianLocationUpdate,
    db: DB,
):
    """Update technician's current location."""
    query = select(Technician).where(Technician.id == technician_id)
    result = await db.execute(query)
    technician = result.scalar_one_or_none()

    if not technician:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Technician not found"
        )

    technician.current_location_lat = data.latitude
    technician.current_location_lng = data.longitude
    technician.location_updated_at = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(technician)
    return TechnicianBrief.model_validate(technician)


@router.put(
    "/{technician_id}/availability",
    response_model=TechnicianBrief,
    dependencies=[Depends(require_permissions("service:update"))]
)
async def toggle_availability(
    technician_id: uuid.UUID,
    is_available: bool,
    db: DB,
):
    """Toggle technician availability."""
    query = select(Technician).where(Technician.id == technician_id)
    result = await db.execute(query)
    technician = result.scalar_one_or_none()

    if not technician:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Technician not found"
        )

    technician.is_available = is_available
    await db.commit()
    await db.refresh(technician)
    return TechnicianBrief.model_validate(technician)


@router.delete(
    "/{technician_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_permissions("service:delete"))]
)
async def deactivate_technician(
    technician_id: uuid.UUID,
    db: DB,
    current_user: CurrentUser,
):
    """
    Deactivate a technician.
    Requires: service:delete permission
    """
    query = select(Technician).where(Technician.id == technician_id)
    result = await db.execute(query)
    technician = result.scalar_one_or_none()

    if not technician:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Technician not found"
        )

    technician.status = TechnicianStatus.INACTIVE.value
    technician.is_available = False
    await db.commit()


# ==================== PERFORMANCE DASHBOARD ENDPOINTS ====================

from app.models.technician import TechnicianJobHistory
from app.models.service_request import ServiceRequest


@router.get(
    "/performance/dashboard",
    dependencies=[Depends(require_permissions("service:view"))]
)
async def get_performance_dashboard(
    db: DB,
    region_id: Optional[uuid.UUID] = Query(None),
    date_from: Optional[datetime] = Query(None),
    date_to: Optional[datetime] = Query(None),
):
    """
    Get technician performance dashboard overview.

    Returns:
    - Total technicians and their status breakdown
    - Top performers by jobs completed
    - Average metrics (rating, jobs per technician)
    - SLA performance

    Requires: service:view permission
    """
    # Base conditions
    conditions = [Technician.status == "ACTIVE"]
    if region_id:
        conditions.append(Technician.region_id == region_id)

    # Total technicians
    total_query = select(func.count()).select_from(Technician).where(and_(*conditions))
    total_technicians = await db.scalar(total_query) or 0

    # Available technicians
    available_query = select(func.count()).select_from(Technician).where(
        and_(*conditions, Technician.is_available == True)
    )
    available_technicians = await db.scalar(available_query) or 0

    # Status breakdown
    status_query = select(
        Technician.status,
        func.count().label('count')
    ).group_by(Technician.status)
    if region_id:
        status_query = status_query.where(Technician.region_id == region_id)
    status_result = await db.execute(status_query)
    status_breakdown = {row.status: row.count for row in status_result.all()}

    # Top performers (by jobs completed this month)
    top_query = select(Technician).where(
        and_(*conditions)
    ).order_by(
        Technician.current_month_jobs.desc()
    ).limit(10)
    top_result = await db.execute(top_query)
    top_performers = top_result.scalars().all()

    # Average metrics
    avg_query = select(
        func.avg(Technician.average_rating).label('avg_rating'),
        func.avg(Technician.current_month_jobs).label('avg_jobs'),
        func.avg(Technician.total_jobs_completed).label('avg_total_jobs'),
    ).where(and_(*conditions))
    avg_result = await db.execute(avg_query)
    avg_row = avg_result.one()

    # Skill level distribution
    skill_query = select(
        Technician.skill_level,
        func.count().label('count')
    ).where(and_(*conditions)).group_by(Technician.skill_level)
    skill_result = await db.execute(skill_query)
    skill_distribution = {row.skill_level or "UNKNOWN": row.count for row in skill_result.all()}

    # Jobs completed today
    today = datetime.now(timezone.utc).date()
    jobs_today_query = select(func.count()).select_from(TechnicianJobHistory).where(
        func.date(TechnicianJobHistory.completed_at) == today
    )
    jobs_today = await db.scalar(jobs_today_query) or 0

    return {
        "overview": {
            "total_technicians": total_technicians,
            "available_technicians": available_technicians,
            "busy_technicians": total_technicians - available_technicians,
            "jobs_completed_today": jobs_today,
        },
        "status_breakdown": status_breakdown,
        "skill_distribution": skill_distribution,
        "averages": {
            "average_rating": round(float(avg_row.avg_rating or 0), 2),
            "average_monthly_jobs": round(float(avg_row.avg_jobs or 0), 1),
            "average_total_jobs": round(float(avg_row.avg_total_jobs or 0), 1),
        },
        "top_performers": [
            {
                "id": str(t.id),
                "employee_code": t.employee_code,
                "name": t.full_name,
                "current_month_jobs": t.current_month_jobs,
                "total_jobs": t.total_jobs_completed,
                "average_rating": round(t.average_rating, 2) if t.average_rating else 0,
                "skill_level": t.skill_level,
            }
            for t in top_performers
        ],
    }


@router.get(
    "/performance/rankings",
    dependencies=[Depends(require_permissions("service:view"))]
)
async def get_technician_rankings(
    db: DB,
    rank_by: str = Query("jobs", pattern="^(jobs|rating|efficiency)$"),
    period: str = Query("month", pattern="^(week|month|quarter|year)$"),
    region_id: Optional[uuid.UUID] = Query(None),
    limit: int = Query(20, ge=1, le=100),
):
    """
    Get technician rankings by different criteria.

    Ranking options:
    - jobs: Most jobs completed
    - rating: Highest average rating
    - efficiency: Best SLA compliance

    Requires: service:view permission
    """
    conditions = [Technician.status == "ACTIVE"]
    if region_id:
        conditions.append(Technician.region_id == region_id)

    # Build order by based on ranking criteria
    if rank_by == "jobs":
        order_by = Technician.current_month_jobs.desc()
    elif rank_by == "rating":
        order_by = Technician.average_rating.desc()
    else:  # efficiency - use rating as proxy for now
        order_by = Technician.average_rating.desc()

    query = select(Technician).where(
        and_(*conditions)
    ).order_by(order_by).limit(limit)

    result = await db.execute(query)
    technicians = result.scalars().all()

    rankings = []
    for rank, t in enumerate(technicians, 1):
        rankings.append({
            "rank": rank,
            "id": str(t.id),
            "employee_code": t.employee_code,
            "name": t.full_name,
            "phone": t.phone,
            "current_month_jobs": t.current_month_jobs,
            "total_jobs": t.total_jobs_completed,
            "average_rating": round(t.average_rating, 2) if t.average_rating else 0,
            "total_ratings": t.total_ratings,
            "skill_level": t.skill_level,
            "is_available": t.is_available,
        })

    return {
        "rank_by": rank_by,
        "period": period,
        "total_technicians": len(rankings),
        "rankings": rankings,
    }


@router.get(
    "/{technician_id}/performance",
    dependencies=[Depends(require_permissions("service:view"))]
)
async def get_technician_performance(
    technician_id: uuid.UUID,
    db: DB,
    date_from: Optional[datetime] = Query(None),
    date_to: Optional[datetime] = Query(None),
):
    """
    Get detailed performance metrics for a specific technician.

    Returns:
    - Job history with completion times
    - Rating trends
    - SLA compliance stats
    - Monthly performance breakdown

    Requires: service:view permission
    """
    # Get technician
    tech_result = await db.execute(
        select(Technician).where(Technician.id == technician_id)
    )
    technician = tech_result.scalar_one_or_none()

    if not technician:
        raise HTTPException(status_code=404, detail="Technician not found")

    # Job history conditions
    job_conditions = [TechnicianJobHistory.technician_id == technician_id]
    if date_from:
        job_conditions.append(TechnicianJobHistory.assigned_at >= date_from)
    if date_to:
        job_conditions.append(TechnicianJobHistory.assigned_at <= date_to)

    # Get job history stats
    job_stats_query = select(
        func.count().label('total_jobs'),
        func.count().filter(TechnicianJobHistory.status == "COMPLETED").label('completed_jobs'),
        func.avg(TechnicianJobHistory.time_taken_minutes).label('avg_time_minutes'),
        func.avg(TechnicianJobHistory.customer_rating).label('avg_job_rating'),
    ).where(and_(*job_conditions))
    job_stats = await db.execute(job_stats_query)
    stats_row = job_stats.one()

    # Get recent jobs
    recent_jobs_query = select(TechnicianJobHistory).options(
        joinedload(TechnicianJobHistory.service_request)
    ).where(
        TechnicianJobHistory.technician_id == technician_id
    ).order_by(
        TechnicianJobHistory.assigned_at.desc()
    ).limit(20)
    recent_result = await db.execute(recent_jobs_query)
    recent_jobs = recent_result.scalars().unique().all()

    # Rating distribution
    rating_dist_query = select(
        TechnicianJobHistory.customer_rating,
        func.count().label('count')
    ).where(
        and_(
            TechnicianJobHistory.technician_id == technician_id,
            TechnicianJobHistory.customer_rating.isnot(None)
        )
    ).group_by(TechnicianJobHistory.customer_rating)
    rating_dist_result = await db.execute(rating_dist_query)
    rating_distribution = {row.customer_rating: row.count for row in rating_dist_result.all()}

    return {
        "technician": {
            "id": str(technician.id),
            "employee_code": technician.employee_code,
            "name": technician.full_name,
            "phone": technician.phone,
            "skill_level": technician.skill_level,
            "is_available": technician.is_available,
            "status": technician.status,
        },
        "performance_summary": {
            "total_jobs": technician.total_jobs_completed,
            "current_month_jobs": technician.current_month_jobs,
            "average_rating": round(technician.average_rating, 2) if technician.average_rating else 0,
            "total_ratings": technician.total_ratings,
        },
        "period_stats": {
            "total_assigned": stats_row.total_jobs or 0,
            "completed": stats_row.completed_jobs or 0,
            "completion_rate": round((stats_row.completed_jobs or 0) / max(stats_row.total_jobs, 1) * 100, 1),
            "avg_time_minutes": round(float(stats_row.avg_time_minutes or 0), 0),
            "avg_job_rating": round(float(stats_row.avg_job_rating or 0), 2),
        },
        "rating_distribution": rating_distribution,
        "recent_jobs": [
            {
                "id": str(job.id),
                "service_request_id": str(job.service_request_id),
                "ticket_number": job.service_request.ticket_number if job.service_request else None,
                "assigned_at": job.assigned_at.isoformat() if job.assigned_at else None,
                "completed_at": job.completed_at.isoformat() if job.completed_at else None,
                "time_taken_minutes": job.time_taken_minutes,
                "status": job.status,
                "customer_rating": job.customer_rating,
            }
            for job in recent_jobs
        ],
    }
