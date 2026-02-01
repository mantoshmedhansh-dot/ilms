"""Transporter/Carrier API endpoints."""
from typing import Optional
import uuid
from math import ceil

from fastapi import APIRouter, HTTPException, status, Query, Depends
from sqlalchemy import select, func, and_, or_
from sqlalchemy.orm import selectinload

from app.api.deps import DB, CurrentUser, require_permissions
from app.models.transporter import Transporter, TransporterType, TransporterServiceability
from app.schemas.transporter import (
    TransporterCreate,
    TransporterUpdate,
    TransporterResponse,
    TransporterBrief,
    TransporterListResponse,
    ServiceabilityCreate,
    ServiceabilityResponse,
    ServiceabilityCheckRequest,
    ServiceabilityCheckResponse,
    TransporterServiceabilityOption,
    AWBGenerateRequest,
    AWBGenerateResponse,
)


router = APIRouter()


# ==================== TRANSPORTER CRUD ====================

@router.get(
    "",
    response_model=TransporterListResponse,
    dependencies=[Depends(require_permissions("logistics:view"))]
)
async def list_transporters(
    db: DB,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    transporter_type: Optional[TransporterType] = Query(None),
    is_active: bool = Query(True),
    search: Optional[str] = Query(None),
):
    """
    Get paginated list of transporters.
    Requires: logistics:view permission
    """
    query = select(Transporter).where(Transporter.is_active == is_active)
    count_query = select(func.count(Transporter.id)).where(Transporter.is_active == is_active)

    if transporter_type:
        query = query.where(Transporter.transporter_type == transporter_type)
        count_query = count_query.where(Transporter.transporter_type == transporter_type)

    if search:
        search_filter = or_(
            Transporter.code.ilike(f"%{search}%"),
            Transporter.name.ilike(f"%{search}%"),
        )
        query = query.where(search_filter)
        count_query = count_query.where(search_filter)

    # Get total count
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # Get paginated results
    offset = (page - 1) * size
    query = query.order_by(Transporter.priority.asc(), Transporter.name.asc())
    query = query.offset(offset).limit(size)

    result = await db.execute(query)
    transporters = result.scalars().all()

    return TransporterListResponse(
        items=[TransporterResponse.model_validate(t) for t in transporters],
        total=total,
        page=page,
        size=size,
        pages=ceil(total / size) if total > 0 else 1,
    )


@router.get(
    "/dropdown",
    response_model=list[TransporterBrief],
    dependencies=[Depends(require_permissions("logistics:view"))]
)
async def get_transporters_dropdown(
    db: DB,
    transporter_type: Optional[TransporterType] = Query(None),
    is_active: bool = Query(True),
):
    """Get transporters for dropdown selection."""
    query = select(Transporter).where(Transporter.is_active == is_active)

    if transporter_type:
        query = query.where(Transporter.transporter_type == transporter_type)

    query = query.order_by(Transporter.priority.asc(), Transporter.name.asc())
    query = query.limit(100)

    result = await db.execute(query)
    transporters = result.scalars().all()

    return [TransporterBrief.model_validate(t) for t in transporters]


@router.get(
    "/{transporter_id}",
    response_model=TransporterResponse,
    dependencies=[Depends(require_permissions("logistics:view"))]
)
async def get_transporter(
    transporter_id: uuid.UUID,
    db: DB,
):
    """Get transporter by ID."""
    query = select(Transporter).where(Transporter.id == transporter_id)
    result = await db.execute(query)
    transporter = result.scalar_one_or_none()

    if not transporter:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Transporter not found"
        )

    return TransporterResponse.model_validate(transporter)


@router.post(
    "",
    response_model=TransporterResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permissions("logistics:create"))]
)
async def create_transporter(
    data: TransporterCreate,
    db: DB,
    current_user: CurrentUser,
):
    """
    Create a new transporter.
    Requires: logistics:create permission
    """
    # Check for duplicate code
    existing_query = select(Transporter).where(Transporter.code == data.code.upper())
    existing_result = await db.execute(existing_query)
    if existing_result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Transporter with this code already exists"
        )

    transporter_data = data.model_dump()
    transporter_data["code"] = data.code.upper()
    transporter = Transporter(**transporter_data)

    db.add(transporter)
    await db.commit()
    await db.refresh(transporter)

    return TransporterResponse.model_validate(transporter)


@router.put(
    "/{transporter_id}",
    response_model=TransporterResponse,
    dependencies=[Depends(require_permissions("logistics:update"))]
)
async def update_transporter(
    transporter_id: uuid.UUID,
    data: TransporterUpdate,
    db: DB,
    current_user: CurrentUser,
):
    """
    Update a transporter.
    Requires: logistics:update permission
    """
    query = select(Transporter).where(Transporter.id == transporter_id)
    result = await db.execute(query)
    transporter = result.scalar_one_or_none()

    if not transporter:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Transporter not found"
        )

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(transporter, field, value)

    await db.commit()
    await db.refresh(transporter)

    return TransporterResponse.model_validate(transporter)


@router.delete(
    "/{transporter_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_permissions("logistics:delete"))]
)
async def deactivate_transporter(
    transporter_id: uuid.UUID,
    db: DB,
    current_user: CurrentUser,
):
    """
    Deactivate a transporter (soft delete).
    Requires: logistics:delete permission
    """
    query = select(Transporter).where(Transporter.id == transporter_id)
    result = await db.execute(query)
    transporter = result.scalar_one_or_none()

    if not transporter:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Transporter not found"
        )

    transporter.is_active = False
    await db.commit()


# ==================== SERVICEABILITY ====================

@router.post(
    "/check-serviceability",
    response_model=ServiceabilityCheckResponse,
    dependencies=[Depends(require_permissions("logistics:view"))]
)
async def check_serviceability(
    data: ServiceabilityCheckRequest,
    db: DB,
):
    """
    Check which transporters can service a pincode route.
    """
    query = (
        select(TransporterServiceability)
        .join(Transporter)
        .where(
            and_(
                TransporterServiceability.origin_pincode == data.from_pincode,
                TransporterServiceability.destination_pincode == data.to_pincode,
                TransporterServiceability.is_serviceable == True,
                Transporter.is_active == True,
            )
        )
        .options(selectinload(TransporterServiceability.transporter))
    )

    # Filter by payment mode
    if data.payment_mode == "COD":
        query = query.where(TransporterServiceability.cod_available == True)
    elif data.payment_mode == "PREPAID":
        query = query.where(TransporterServiceability.prepaid_available == True)

    # Filter by weight
    if data.weight_kg:
        query = query.where(
            or_(
                Transporter.max_weight_kg.is_(None),
                Transporter.max_weight_kg >= data.weight_kg
            )
        )
        query = query.where(Transporter.min_weight_kg <= data.weight_kg)

    result = await db.execute(query)
    serviceabilities = result.scalars().all()

    available = []
    for s in serviceabilities:
        available.append(TransporterServiceabilityOption(
            transporter=TransporterBrief.model_validate(s.transporter),
            estimated_days=s.estimated_days,
            cod_available=s.cod_available,
            prepaid_available=s.prepaid_available,
            rate=s.rate,
            cod_charge=s.cod_charge,
        ))

    return ServiceabilityCheckResponse(
        is_serviceable=len(available) > 0,
        available_transporters=available,
    )


@router.post(
    "/{transporter_id}/serviceability",
    response_model=ServiceabilityResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permissions("logistics:create"))]
)
async def add_serviceability(
    transporter_id: uuid.UUID,
    data: ServiceabilityCreate,
    db: DB,
    current_user: CurrentUser,
):
    """Add serviceability mapping for a transporter."""
    # Verify transporter exists
    transporter_query = select(Transporter).where(Transporter.id == transporter_id)
    transporter_result = await db.execute(transporter_query)
    if not transporter_result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Transporter not found"
        )

    # Check for duplicate
    existing_query = select(TransporterServiceability).where(
        and_(
            TransporterServiceability.transporter_id == transporter_id,
            TransporterServiceability.origin_pincode == data.origin_pincode,
            TransporterServiceability.destination_pincode == data.destination_pincode,
        )
    )
    existing_result = await db.execute(existing_query)
    if existing_result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Serviceability mapping already exists"
        )

    serviceability = TransporterServiceability(
        transporter_id=transporter_id,
        **data.model_dump(exclude={"transporter_id"}),
    )

    db.add(serviceability)
    await db.commit()
    await db.refresh(serviceability)

    return ServiceabilityResponse.model_validate(serviceability)


@router.get(
    "/{transporter_id}/serviceability",
    response_model=list[ServiceabilityResponse],
    dependencies=[Depends(require_permissions("logistics:view"))]
)
async def get_serviceability(
    transporter_id: uuid.UUID,
    db: DB,
    origin_pincode: Optional[str] = Query(None),
    destination_pincode: Optional[str] = Query(None),
    limit: int = Query(100, le=500),
):
    """Get serviceability mappings for a transporter."""
    query = select(TransporterServiceability).where(
        TransporterServiceability.transporter_id == transporter_id
    )

    if origin_pincode:
        query = query.where(TransporterServiceability.origin_pincode == origin_pincode)
    if destination_pincode:
        query = query.where(TransporterServiceability.destination_pincode == destination_pincode)

    query = query.limit(limit)

    result = await db.execute(query)
    serviceabilities = result.scalars().all()

    return [ServiceabilityResponse.model_validate(s) for s in serviceabilities]


@router.delete(
    "/{transporter_id}/serviceability/{serviceability_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_permissions("logistics:delete"))]
)
async def delete_serviceability(
    transporter_id: uuid.UUID,
    serviceability_id: uuid.UUID,
    db: DB,
    current_user: CurrentUser,
):
    """Delete a serviceability mapping."""
    query = select(TransporterServiceability).where(
        and_(
            TransporterServiceability.id == serviceability_id,
            TransporterServiceability.transporter_id == transporter_id,
        )
    )
    result = await db.execute(query)
    serviceability = result.scalar_one_or_none()

    if not serviceability:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Serviceability mapping not found"
        )

    await db.delete(serviceability)
    await db.commit()


# ==================== AWB GENERATION ====================

@router.post(
    "/{transporter_id}/generate-awb",
    response_model=AWBGenerateResponse,
    dependencies=[Depends(require_permissions("logistics:create"))]
)
async def generate_awb(
    transporter_id: uuid.UUID,
    db: DB,
    current_user: CurrentUser,
):
    """
    Generate AWB (Air Waybill) number for a transporter.
    Uses the transporter's prefix and sequence.
    """
    query = select(Transporter).where(Transporter.id == transporter_id)
    result = await db.execute(query)
    transporter = result.scalar_one_or_none()

    if not transporter:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Transporter not found"
        )

    # Generate AWB number
    prefix = transporter.awb_prefix or transporter.code[:3].upper()
    sequence = transporter.awb_sequence_current
    awb_number = f"{prefix}{sequence:010d}"

    # Increment sequence
    transporter.awb_sequence_current = sequence + 1
    await db.commit()

    # Generate tracking URL
    tracking_url = transporter.get_tracking_url(awb_number)

    return AWBGenerateResponse(
        awb_number=awb_number,
        transporter_id=transporter.id,
        transporter_code=transporter.code,
        tracking_url=tracking_url,
    )
