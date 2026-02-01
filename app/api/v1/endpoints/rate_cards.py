"""Rate Card API endpoints for D2C, B2B, and FTL segments."""
from typing import Optional
import uuid
from math import ceil
from datetime import date

from fastapi import APIRouter, HTTPException, status, Query, Depends

from app.api.deps import DB, CurrentUser, require_permissions
from app.services.rate_card_service import RateCardService
from app.models.rate_card import ServiceType, B2BServiceType, FTLRateType, VehicleCategory
from app.schemas.rate_card import (
    # D2C Schemas
    D2CRateCardCreate,
    D2CRateCardUpdate,
    D2CRateCardResponse,
    D2CRateCardDetailResponse,
    D2CRateCardListResponse,
    D2CWeightSlabCreate,
    D2CWeightSlabResponse,
    D2CWeightSlabBulkCreate,
    D2CSurchargeCreate,
    D2CSurchargeResponse,
    D2CSurchargeBulkCreate,
    # Zone Schemas
    ZoneMappingCreate,
    ZoneMappingResponse,
    ZoneMappingListResponse,
    ZoneLookupRequest,
    ZoneLookupResponse,
    ZoneMappingBulkCreate,
    # B2B Schemas
    B2BRateCardCreate,
    B2BRateCardUpdate,
    B2BRateCardResponse,
    B2BRateCardDetailResponse,
    B2BRateCardListResponse,
    B2BRateSlabCreate,
    B2BRateSlabResponse,
    B2BRateSlabBulkCreate,
    # FTL Schemas
    FTLRateCardCreate,
    FTLRateCardUpdate,
    FTLRateCardResponse,
    FTLRateCardDetailResponse,
    FTLRateCardListResponse,
    FTLLaneRateCreate,
    FTLLaneRateResponse,
    FTLLaneRateBulkCreate,
    FTLVehicleTypeCreate,
    FTLVehicleTypeUpdate,
    FTLVehicleTypeResponse,
    FTLVehicleTypeListResponse,
    # Performance
    CarrierPerformanceResponse,
    CarrierPerformanceListResponse,
    # Summary
    RateCardBrief,
    TransporterRateCardSummary,
    # Rate Calculation & Allocation
    RateCalculationRequestSchema,
    AllocationRequestSchema,
)


router = APIRouter()


# ============================================
# D2C RATE CARD ENDPOINTS
# ============================================

@router.get(
    "/d2c",
    response_model=D2CRateCardListResponse,
    dependencies=[Depends(require_permissions("logistics:view"))]
)
async def list_d2c_rate_cards(
    db: DB,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    transporter_id: Optional[uuid.UUID] = Query(None),
    service_type: Optional[ServiceType] = Query(None),
    is_active: Optional[bool] = Query(True),
    effective_date: Optional[date] = Query(None),
):
    """
    List D2C rate cards with filters.
    Requires: logistics:view permission
    """
    service = RateCardService(db)
    skip = (page - 1) * size

    items, total = await service.list_d2c_rate_cards(
        transporter_id=transporter_id,
        service_type=service_type,
        is_active=is_active,
        effective_date=effective_date,
        skip=skip,
        limit=size,
    )

    response_items = []
    for item in items:
        resp = D2CRateCardResponse.model_validate(item)
        if item.transporter:
            resp.transporter_name = item.transporter.name
            resp.transporter_code = item.transporter.code
        response_items.append(resp)

    return D2CRateCardListResponse(
        items=response_items,
        total=total,
        page=page,
        size=size,
        pages=ceil(total / size) if total > 0 else 1,
    )


@router.get(
    "/d2c/{rate_card_id}",
    response_model=D2CRateCardDetailResponse,
    dependencies=[Depends(require_permissions("logistics:view"))]
)
async def get_d2c_rate_card(
    rate_card_id: uuid.UUID,
    db: DB,
):
    """Get D2C rate card with weight slabs and surcharges."""
    service = RateCardService(db)
    rate_card = await service.get_d2c_rate_card(rate_card_id, include_details=True)

    if not rate_card:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Rate card not found"
        )

    response = D2CRateCardDetailResponse.model_validate(rate_card)
    if rate_card.transporter:
        response.transporter_name = rate_card.transporter.name
        response.transporter_code = rate_card.transporter.code

    return response


@router.post(
    "/d2c",
    response_model=D2CRateCardDetailResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permissions("logistics:create"))]
)
async def create_d2c_rate_card(
    data: D2CRateCardCreate,
    db: DB,
    current_user: CurrentUser,
):
    """
    Create new D2C rate card with optional weight slabs and surcharges.
    Requires: logistics:create permission
    """
    service = RateCardService(db)

    try:
        rate_card = await service.create_d2c_rate_card(
            data, created_by=current_user.id
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

    response = D2CRateCardDetailResponse.model_validate(rate_card)
    if rate_card.transporter:
        response.transporter_name = rate_card.transporter.name
        response.transporter_code = rate_card.transporter.code

    return response


@router.put(
    "/d2c/{rate_card_id}",
    response_model=D2CRateCardResponse,
    dependencies=[Depends(require_permissions("logistics:update"))]
)
async def update_d2c_rate_card(
    rate_card_id: uuid.UUID,
    data: D2CRateCardUpdate,
    db: DB,
    current_user: CurrentUser,
):
    """Update D2C rate card."""
    service = RateCardService(db)

    try:
        rate_card = await service.update_d2c_rate_card(rate_card_id, data)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )

    return D2CRateCardResponse.model_validate(rate_card)


@router.delete(
    "/d2c/{rate_card_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_permissions("logistics:delete"))]
)
async def delete_d2c_rate_card(
    rate_card_id: uuid.UUID,
    db: DB,
    current_user: CurrentUser,
    hard_delete: bool = Query(False),
):
    """Delete D2C rate card (soft delete by default)."""
    service = RateCardService(db)

    try:
        await service.delete_d2c_rate_card(rate_card_id, hard_delete=hard_delete)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )


# D2C Weight Slabs
@router.post(
    "/d2c/{rate_card_id}/slabs",
    response_model=D2CWeightSlabResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permissions("logistics:create"))]
)
async def add_d2c_weight_slab(
    rate_card_id: uuid.UUID,
    data: D2CWeightSlabCreate,
    db: DB,
    current_user: CurrentUser,
):
    """Add weight slab to D2C rate card."""
    service = RateCardService(db)

    try:
        slab = await service.add_d2c_weight_slab(rate_card_id, data)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

    return D2CWeightSlabResponse.model_validate(slab)


@router.post(
    "/d2c/{rate_card_id}/slabs/bulk",
    dependencies=[Depends(require_permissions("logistics:create"))]
)
async def bulk_add_d2c_weight_slabs(
    rate_card_id: uuid.UUID,
    data: D2CWeightSlabBulkCreate,
    db: DB,
    current_user: CurrentUser,
    replace_existing: bool = Query(False),
):
    """Bulk add weight slabs to D2C rate card."""
    service = RateCardService(db)

    try:
        count = await service.bulk_add_d2c_weight_slabs(
            rate_card_id, data.slabs, replace_existing=replace_existing
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

    return {"message": f"Added {count} weight slabs", "count": count}


@router.delete(
    "/d2c/{rate_card_id}/slabs/{slab_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_permissions("logistics:delete"))]
)
async def delete_d2c_weight_slab(
    rate_card_id: uuid.UUID,
    slab_id: uuid.UUID,
    db: DB,
    current_user: CurrentUser,
):
    """Delete weight slab from D2C rate card."""
    service = RateCardService(db)

    try:
        await service.delete_d2c_weight_slab(slab_id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )


# D2C Surcharges
@router.post(
    "/d2c/{rate_card_id}/surcharges",
    response_model=D2CSurchargeResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permissions("logistics:create"))]
)
async def add_d2c_surcharge(
    rate_card_id: uuid.UUID,
    data: D2CSurchargeCreate,
    db: DB,
    current_user: CurrentUser,
):
    """Add surcharge to D2C rate card."""
    service = RateCardService(db)

    try:
        surcharge = await service.add_d2c_surcharge(rate_card_id, data)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

    return D2CSurchargeResponse.model_validate(surcharge)


@router.post(
    "/d2c/{rate_card_id}/surcharges/bulk",
    dependencies=[Depends(require_permissions("logistics:create"))]
)
async def bulk_add_d2c_surcharges(
    rate_card_id: uuid.UUID,
    data: D2CSurchargeBulkCreate,
    db: DB,
    current_user: CurrentUser,
    replace_existing: bool = Query(False),
):
    """Bulk add surcharges to D2C rate card."""
    service = RateCardService(db)

    try:
        count = await service.bulk_add_d2c_surcharges(
            rate_card_id, data.surcharges, replace_existing=replace_existing
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

    return {"message": f"Added {count} surcharges", "count": count}


@router.delete(
    "/d2c/{rate_card_id}/surcharges/{surcharge_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_permissions("logistics:delete"))]
)
async def delete_d2c_surcharge(
    rate_card_id: uuid.UUID,
    surcharge_id: uuid.UUID,
    db: DB,
    current_user: CurrentUser,
):
    """Delete surcharge from D2C rate card."""
    service = RateCardService(db)

    try:
        await service.delete_d2c_surcharge(surcharge_id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )


# ============================================
# ZONE MAPPING ENDPOINTS
# ============================================

@router.get(
    "/zones",
    response_model=ZoneMappingListResponse,
    dependencies=[Depends(require_permissions("logistics:view"))]
)
async def list_zone_mappings(
    db: DB,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    origin_state: Optional[str] = Query(None),
    destination_state: Optional[str] = Query(None),
    zone: Optional[str] = Query(None),
):
    """List zone mappings with filters."""
    service = RateCardService(db)
    skip = (page - 1) * size

    items, total = await service.list_zone_mappings(
        origin_state=origin_state,
        destination_state=destination_state,
        zone=zone,
        skip=skip,
        limit=size,
    )

    return ZoneMappingListResponse(
        items=[ZoneMappingResponse.model_validate(item) for item in items],
        total=total,
        page=page,
        size=size,
        pages=ceil(total / size) if total > 0 else 1,
    )


@router.get(
    "/zones/lookup",
    response_model=ZoneLookupResponse,
    dependencies=[Depends(require_permissions("logistics:view"))]
)
async def lookup_zone(
    db: DB,
    origin_pincode: str = Query(..., min_length=5, max_length=10),
    destination_pincode: str = Query(..., min_length=5, max_length=10),
):
    """Lookup zone for origin-destination pair."""
    service = RateCardService(db)
    result = await service.lookup_zone(origin_pincode, destination_pincode)

    return ZoneLookupResponse(
        origin_pincode=origin_pincode,
        destination_pincode=destination_pincode,
        zone=result["zone"],
        distance_km=result.get("distance_km"),
        is_oda=result.get("is_oda", False),
        found=result["found"],
    )


@router.post(
    "/zones",
    response_model=ZoneMappingResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permissions("logistics:create"))]
)
async def create_zone_mapping(
    data: ZoneMappingCreate,
    db: DB,
    current_user: CurrentUser,
):
    """Create zone mapping."""
    service = RateCardService(db)

    try:
        mapping = await service.create_zone_mapping(data)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

    return ZoneMappingResponse.model_validate(mapping)


@router.post(
    "/zones/bulk",
    dependencies=[Depends(require_permissions("logistics:create"))]
)
async def bulk_create_zone_mappings(
    data: ZoneMappingBulkCreate,
    db: DB,
    current_user: CurrentUser,
    skip_duplicates: bool = Query(True),
):
    """Bulk create zone mappings."""
    service = RateCardService(db)

    count = await service.bulk_create_zone_mappings(
        data.mappings, skip_duplicates=skip_duplicates
    )

    return {"message": f"Created {count} zone mappings", "count": count}


@router.delete(
    "/zones/{mapping_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_permissions("logistics:delete"))]
)
async def delete_zone_mapping(
    mapping_id: uuid.UUID,
    db: DB,
    current_user: CurrentUser,
):
    """Delete zone mapping."""
    service = RateCardService(db)

    try:
        await service.delete_zone_mapping(mapping_id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )


# ============================================
# B2B RATE CARD ENDPOINTS
# ============================================

@router.get(
    "/b2b",
    response_model=B2BRateCardListResponse,
    dependencies=[Depends(require_permissions("logistics:view"))]
)
async def list_b2b_rate_cards(
    db: DB,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    transporter_id: Optional[uuid.UUID] = Query(None),
    service_type: Optional[B2BServiceType] = Query(None),
    is_active: Optional[bool] = Query(True),
):
    """List B2B rate cards with filters."""
    service = RateCardService(db)
    skip = (page - 1) * size

    items, total = await service.list_b2b_rate_cards(
        transporter_id=transporter_id,
        service_type=service_type,
        is_active=is_active,
        skip=skip,
        limit=size,
    )

    response_items = []
    for item in items:
        resp = B2BRateCardResponse.model_validate(item)
        if item.transporter:
            resp.transporter_name = item.transporter.name
            resp.transporter_code = item.transporter.code
        response_items.append(resp)

    return B2BRateCardListResponse(
        items=response_items,
        total=total,
        page=page,
        size=size,
        pages=ceil(total / size) if total > 0 else 1,
    )


@router.get(
    "/b2b/{rate_card_id}",
    response_model=B2BRateCardDetailResponse,
    dependencies=[Depends(require_permissions("logistics:view"))]
)
async def get_b2b_rate_card(
    rate_card_id: uuid.UUID,
    db: DB,
):
    """Get B2B rate card with rate slabs and additional charges."""
    service = RateCardService(db)
    rate_card = await service.get_b2b_rate_card(rate_card_id, include_details=True)

    if not rate_card:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Rate card not found"
        )

    response = B2BRateCardDetailResponse.model_validate(rate_card)
    if rate_card.transporter:
        response.transporter_name = rate_card.transporter.name
        response.transporter_code = rate_card.transporter.code

    return response


@router.post(
    "/b2b",
    response_model=B2BRateCardDetailResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permissions("logistics:create"))]
)
async def create_b2b_rate_card(
    data: B2BRateCardCreate,
    db: DB,
    current_user: CurrentUser,
):
    """Create new B2B rate card."""
    service = RateCardService(db)

    try:
        rate_card = await service.create_b2b_rate_card(
            data, created_by=current_user.id
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

    response = B2BRateCardDetailResponse.model_validate(rate_card)
    if rate_card.transporter:
        response.transporter_name = rate_card.transporter.name
        response.transporter_code = rate_card.transporter.code

    return response


@router.put(
    "/b2b/{rate_card_id}",
    response_model=B2BRateCardResponse,
    dependencies=[Depends(require_permissions("logistics:update"))]
)
async def update_b2b_rate_card(
    rate_card_id: uuid.UUID,
    data: B2BRateCardUpdate,
    db: DB,
    current_user: CurrentUser,
):
    """Update B2B rate card."""
    service = RateCardService(db)

    try:
        rate_card = await service.update_b2b_rate_card(rate_card_id, data)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )

    return B2BRateCardResponse.model_validate(rate_card)


@router.delete(
    "/b2b/{rate_card_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_permissions("logistics:delete"))]
)
async def delete_b2b_rate_card(
    rate_card_id: uuid.UUID,
    db: DB,
    current_user: CurrentUser,
    hard_delete: bool = Query(False),
):
    """Delete B2B rate card."""
    service = RateCardService(db)

    try:
        await service.delete_b2b_rate_card(rate_card_id, hard_delete=hard_delete)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )


# B2B Rate Slabs
@router.post(
    "/b2b/{rate_card_id}/slabs",
    response_model=B2BRateSlabResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permissions("logistics:create"))]
)
async def add_b2b_rate_slab(
    rate_card_id: uuid.UUID,
    data: B2BRateSlabCreate,
    db: DB,
    current_user: CurrentUser,
):
    """Add rate slab to B2B rate card."""
    service = RateCardService(db)

    try:
        slab = await service.add_b2b_rate_slab(rate_card_id, data)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

    return B2BRateSlabResponse.model_validate(slab)


@router.post(
    "/b2b/{rate_card_id}/slabs/bulk",
    dependencies=[Depends(require_permissions("logistics:create"))]
)
async def bulk_add_b2b_rate_slabs(
    rate_card_id: uuid.UUID,
    data: B2BRateSlabBulkCreate,
    db: DB,
    current_user: CurrentUser,
    replace_existing: bool = Query(False),
):
    """Bulk add rate slabs to B2B rate card."""
    service = RateCardService(db)

    try:
        count = await service.bulk_add_b2b_rate_slabs(
            rate_card_id, data.slabs, replace_existing=replace_existing
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

    return {"message": f"Added {count} rate slabs", "count": count}


@router.delete(
    "/b2b/{rate_card_id}/slabs/{slab_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_permissions("logistics:delete"))]
)
async def delete_b2b_rate_slab(
    rate_card_id: uuid.UUID,
    slab_id: uuid.UUID,
    db: DB,
    current_user: CurrentUser,
):
    """Delete rate slab from B2B rate card."""
    service = RateCardService(db)

    try:
        await service.delete_b2b_rate_slab(slab_id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )


# ============================================
# FTL RATE CARD ENDPOINTS
# ============================================

@router.get(
    "/ftl",
    response_model=FTLRateCardListResponse,
    dependencies=[Depends(require_permissions("logistics:view"))]
)
async def list_ftl_rate_cards(
    db: DB,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    transporter_id: Optional[uuid.UUID] = Query(None),
    rate_type: Optional[FTLRateType] = Query(None),
    is_active: Optional[bool] = Query(True),
):
    """List FTL rate cards with filters."""
    service = RateCardService(db)
    skip = (page - 1) * size

    items, total = await service.list_ftl_rate_cards(
        transporter_id=transporter_id,
        rate_type=rate_type,
        is_active=is_active,
        skip=skip,
        limit=size,
    )

    response_items = []
    for item in items:
        resp = FTLRateCardResponse.model_validate(item)
        if item.transporter:
            resp.transporter_name = item.transporter.name
            resp.transporter_code = item.transporter.code
        response_items.append(resp)

    return FTLRateCardListResponse(
        items=response_items,
        total=total,
        page=page,
        size=size,
        pages=ceil(total / size) if total > 0 else 1,
    )


@router.get(
    "/ftl/{rate_card_id}",
    response_model=FTLRateCardDetailResponse,
    dependencies=[Depends(require_permissions("logistics:view"))]
)
async def get_ftl_rate_card(
    rate_card_id: uuid.UUID,
    db: DB,
):
    """Get FTL rate card with lane rates and additional charges."""
    service = RateCardService(db)
    rate_card = await service.get_ftl_rate_card(rate_card_id, include_details=True)

    if not rate_card:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Rate card not found"
        )

    response = FTLRateCardDetailResponse.model_validate(rate_card)
    if rate_card.transporter:
        response.transporter_name = rate_card.transporter.name
        response.transporter_code = rate_card.transporter.code

    return response


@router.post(
    "/ftl",
    response_model=FTLRateCardDetailResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permissions("logistics:create"))]
)
async def create_ftl_rate_card(
    data: FTLRateCardCreate,
    db: DB,
    current_user: CurrentUser,
):
    """Create new FTL rate card."""
    service = RateCardService(db)

    try:
        rate_card = await service.create_ftl_rate_card(
            data, created_by=current_user.id
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

    response = FTLRateCardDetailResponse.model_validate(rate_card)
    if rate_card.transporter:
        response.transporter_name = rate_card.transporter.name
        response.transporter_code = rate_card.transporter.code

    return response


@router.put(
    "/ftl/{rate_card_id}",
    response_model=FTLRateCardResponse,
    dependencies=[Depends(require_permissions("logistics:update"))]
)
async def update_ftl_rate_card(
    rate_card_id: uuid.UUID,
    data: FTLRateCardUpdate,
    db: DB,
    current_user: CurrentUser,
):
    """Update FTL rate card."""
    service = RateCardService(db)

    try:
        rate_card = await service.update_ftl_rate_card(rate_card_id, data)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )

    return FTLRateCardResponse.model_validate(rate_card)


@router.delete(
    "/ftl/{rate_card_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_permissions("logistics:delete"))]
)
async def delete_ftl_rate_card(
    rate_card_id: uuid.UUID,
    db: DB,
    current_user: CurrentUser,
    hard_delete: bool = Query(False),
):
    """Delete FTL rate card."""
    service = RateCardService(db)

    try:
        await service.delete_ftl_rate_card(rate_card_id, hard_delete=hard_delete)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )


# FTL Lane Rates
@router.post(
    "/ftl/{rate_card_id}/lanes",
    response_model=FTLLaneRateResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permissions("logistics:create"))]
)
async def add_ftl_lane_rate(
    rate_card_id: uuid.UUID,
    data: FTLLaneRateCreate,
    db: DB,
    current_user: CurrentUser,
):
    """Add lane rate to FTL rate card."""
    service = RateCardService(db)

    try:
        lane = await service.add_ftl_lane_rate(rate_card_id, data)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

    return FTLLaneRateResponse.model_validate(lane)


@router.post(
    "/ftl/{rate_card_id}/lanes/bulk",
    dependencies=[Depends(require_permissions("logistics:create"))]
)
async def bulk_add_ftl_lane_rates(
    rate_card_id: uuid.UUID,
    data: FTLLaneRateBulkCreate,
    db: DB,
    current_user: CurrentUser,
    replace_existing: bool = Query(False),
):
    """Bulk add lane rates to FTL rate card."""
    service = RateCardService(db)

    try:
        count = await service.bulk_add_ftl_lane_rates(
            rate_card_id, data.lane_rates, replace_existing=replace_existing
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

    return {"message": f"Added {count} lane rates", "count": count}


@router.delete(
    "/ftl/{rate_card_id}/lanes/{lane_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_permissions("logistics:delete"))]
)
async def delete_ftl_lane_rate(
    rate_card_id: uuid.UUID,
    lane_id: uuid.UUID,
    db: DB,
    current_user: CurrentUser,
):
    """Delete lane rate from FTL rate card."""
    service = RateCardService(db)

    try:
        await service.delete_ftl_lane_rate(lane_id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )


@router.get(
    "/ftl/lanes/search",
    response_model=list[FTLLaneRateResponse],
    dependencies=[Depends(require_permissions("logistics:view"))]
)
async def search_ftl_lanes(
    db: DB,
    origin_city: Optional[str] = Query(None),
    destination_city: Optional[str] = Query(None),
    vehicle_type: Optional[str] = Query(None),
    rate_card_id: Optional[uuid.UUID] = Query(None),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
):
    """Search FTL lane rates across all rate cards."""
    service = RateCardService(db)
    skip = (page - 1) * size

    items, _ = await service.search_ftl_lanes(
        origin_city=origin_city,
        destination_city=destination_city,
        vehicle_type=vehicle_type,
        rate_card_id=rate_card_id,
        skip=skip,
        limit=size,
    )

    return [FTLLaneRateResponse.model_validate(lane) for lane in items]


# ============================================
# VEHICLE TYPE ENDPOINTS
# ============================================

@router.get(
    "/vehicle-types",
    response_model=FTLVehicleTypeListResponse,
    dependencies=[Depends(require_permissions("logistics:view"))]
)
async def list_vehicle_types(
    db: DB,
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=100),
    category: Optional[VehicleCategory] = Query(None),
    is_active: bool = Query(True),
):
    """List FTL vehicle types."""
    service = RateCardService(db)
    skip = (page - 1) * size

    items, total = await service.list_vehicle_types(
        category=category.value if category else None,
        is_active=is_active,
        skip=skip,
        limit=size,
    )

    return FTLVehicleTypeListResponse(
        items=[FTLVehicleTypeResponse.model_validate(v) for v in items],
        total=total,
        page=page,
        size=size,
        pages=ceil(total / size) if total > 0 else 1,
    )


@router.get(
    "/vehicle-types/{vehicle_id}",
    response_model=FTLVehicleTypeResponse,
    dependencies=[Depends(require_permissions("logistics:view"))]
)
async def get_vehicle_type(
    vehicle_id: uuid.UUID,
    db: DB,
):
    """Get vehicle type by ID."""
    service = RateCardService(db)
    vehicle = await service.get_vehicle_type(vehicle_id)

    if not vehicle:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vehicle type not found"
        )

    return FTLVehicleTypeResponse.model_validate(vehicle)


@router.post(
    "/vehicle-types",
    response_model=FTLVehicleTypeResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permissions("logistics:create"))]
)
async def create_vehicle_type(
    data: FTLVehicleTypeCreate,
    db: DB,
    current_user: CurrentUser,
):
    """Create new vehicle type."""
    service = RateCardService(db)

    try:
        vehicle = await service.create_vehicle_type(data)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

    return FTLVehicleTypeResponse.model_validate(vehicle)


@router.put(
    "/vehicle-types/{vehicle_id}",
    response_model=FTLVehicleTypeResponse,
    dependencies=[Depends(require_permissions("logistics:update"))]
)
async def update_vehicle_type(
    vehicle_id: uuid.UUID,
    data: FTLVehicleTypeUpdate,
    db: DB,
    current_user: CurrentUser,
):
    """Update vehicle type."""
    service = RateCardService(db)

    try:
        vehicle = await service.update_vehicle_type(vehicle_id, data)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )

    return FTLVehicleTypeResponse.model_validate(vehicle)


@router.delete(
    "/vehicle-types/{vehicle_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_permissions("logistics:delete"))]
)
async def delete_vehicle_type(
    vehicle_id: uuid.UUID,
    db: DB,
    current_user: CurrentUser,
):
    """Delete vehicle type (soft delete)."""
    service = RateCardService(db)

    try:
        await service.delete_vehicle_type(vehicle_id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )


# ============================================
# CARRIER PERFORMANCE ENDPOINTS
# ============================================

@router.get(
    "/carriers/performance",
    response_model=CarrierPerformanceListResponse,
    dependencies=[Depends(require_permissions("logistics:view"))]
)
async def list_carrier_performance(
    db: DB,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    transporter_id: Optional[uuid.UUID] = Query(None),
    zone: Optional[str] = Query(None),
    period_start: Optional[date] = Query(None),
):
    """List carrier performance records."""
    service = RateCardService(db)
    skip = (page - 1) * size

    items, total = await service.list_carrier_performance(
        transporter_id=transporter_id,
        zone=zone,
        period_start=period_start,
        skip=skip,
        limit=size,
    )

    response_items = []
    for item in items:
        resp = CarrierPerformanceResponse.model_validate(item)
        if item.transporter:
            resp.transporter_name = item.transporter.name
            resp.transporter_code = item.transporter.code
        response_items.append(resp)

    return CarrierPerformanceListResponse(
        items=response_items,
        total=total,
        page=page,
        size=size,
        pages=ceil(total / size) if total > 0 else 1,
    )


@router.get(
    "/carriers/{transporter_id}/performance",
    response_model=CarrierPerformanceResponse,
    dependencies=[Depends(require_permissions("logistics:view"))]
)
async def get_carrier_performance(
    transporter_id: uuid.UUID,
    db: DB,
    period_start: Optional[date] = Query(None),
    period_end: Optional[date] = Query(None),
    zone: Optional[str] = Query(None),
):
    """Get carrier performance for a specific transporter."""
    service = RateCardService(db)
    performance = await service.get_carrier_performance(
        transporter_id, period_start, period_end, zone
    )

    if not performance:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Performance data not found"
        )

    response = CarrierPerformanceResponse.model_validate(performance)
    if performance.transporter:
        response.transporter_name = performance.transporter.name
        response.transporter_code = performance.transporter.code

    return response


# ============================================
# SUMMARY ENDPOINTS
# ============================================

@router.get(
    "/summary",
    response_model=list[TransporterRateCardSummary],
    dependencies=[Depends(require_permissions("logistics:view"))]
)
async def get_rate_card_summary(
    db: DB,
    transporter_id: Optional[uuid.UUID] = Query(None),
):
    """Get summary of rate cards per transporter."""
    service = RateCardService(db)
    summary = await service.get_rate_card_summary(transporter_id)

    return [TransporterRateCardSummary(**s) for s in summary]


@router.get(
    "/dropdown",
    response_model=list[RateCardBrief],
    dependencies=[Depends(require_permissions("logistics:view"))]
)
async def get_rate_cards_dropdown(
    db: DB,
    segment: str = Query(..., pattern="^(d2c|b2b|ftl)$"),
    transporter_id: Optional[uuid.UUID] = Query(None),
    is_active: bool = Query(True),
):
    """Get rate cards for dropdown selection."""
    service = RateCardService(db)

    if segment == "d2c":
        items, _ = await service.list_d2c_rate_cards(
            transporter_id=transporter_id,
            is_active=is_active,
            limit=100,
        )
        return [
            RateCardBrief(
                id=item.id,
                code=item.code,
                name=item.name,
                service_type=item.service_type,
                is_active=item.is_active,
            )
            for item in items
        ]
    elif segment == "b2b":
        items, _ = await service.list_b2b_rate_cards(
            transporter_id=transporter_id,
            is_active=is_active,
            limit=100,
        )
        return [
            RateCardBrief(
                id=item.id,
                code=item.code,
                name=item.name,
                service_type=item.service_type,
                is_active=item.is_active,
            )
            for item in items
        ]
    else:  # ftl
        items, _ = await service.list_ftl_rate_cards(
            transporter_id=transporter_id,
            is_active=is_active,
            limit=100,
        )
        return [
            RateCardBrief(
                id=item.id,
                code=item.code,
                name=item.name,
                service_type=item.rate_type,
                is_active=item.is_active,
            )
            for item in items
        ]


# ============================================
# PRICING ENGINE ENDPOINTS
# ============================================

from app.services.pricing_engine import (
    PricingEngine,
    RateCalculationRequest,
    AllocationStrategy,
)


@router.post(
    "/calculate-rate",
    dependencies=[Depends(require_permissions("logistics:view"))]
)
async def calculate_shipping_rate(
    data: RateCalculationRequestSchema,
    db: DB,
):
    """
    Calculate shipping rates from all eligible carriers.

    Returns quotes from all active carriers for the given origin-destination
    and weight, including cost breakdown and estimated delivery time.

    The response includes:
    - Segment classification (D2C/B2B/FTL)
    - Zone determination
    - Quotes from all eligible carriers
    - Recommended carrier based on balanced scoring
    - Alternative options
    """
    engine = PricingEngine(db)

    request = RateCalculationRequest(
        origin_pincode=data.origin_pincode,
        destination_pincode=data.destination_pincode,
        weight_kg=data.weight_kg,
        length_cm=data.length_cm,
        width_cm=data.width_cm,
        height_cm=data.height_cm,
        payment_mode=data.payment_mode,
        order_value=data.order_value,
        channel=data.channel,
        declared_value=data.declared_value,
        is_fragile=data.is_fragile,
        num_packages=data.num_packages,
        service_type=data.service_type,
        transporter_ids=data.transporter_ids,
    )

    return await engine.get_quotes(request)


@router.post(
    "/compare-carriers",
    dependencies=[Depends(require_permissions("logistics:view"))]
)
async def compare_carriers(
    data: RateCalculationRequestSchema,
    db: DB,
    strategy: str = Query(
        "BALANCED",
        pattern="^(CHEAPEST_FIRST|FASTEST_FIRST|BEST_SLA|BALANCED)$"
    ),
):
    """
    Compare carriers for a shipment with different allocation strategies.

    Strategies:
    - CHEAPEST_FIRST: Sort by cost (lowest first)
    - FASTEST_FIRST: Sort by TAT (fastest first)
    - BEST_SLA: Sort by performance score (highest first)
    - BALANCED: Weighted combination of cost, TAT, and performance
    """
    engine = PricingEngine(db)

    request = RateCalculationRequest(
        origin_pincode=data.origin_pincode,
        destination_pincode=data.destination_pincode,
        weight_kg=data.weight_kg,
        length_cm=data.length_cm,
        width_cm=data.width_cm,
        height_cm=data.height_cm,
        payment_mode=data.payment_mode,
        order_value=data.order_value,
        channel=data.channel,
        declared_value=data.declared_value,
        is_fragile=data.is_fragile,
        num_packages=data.num_packages,
        service_type=data.service_type,
        transporter_ids=data.transporter_ids,
    )

    allocation_strategy = AllocationStrategy(strategy)
    return await engine.allocate(request, allocation_strategy)


@router.post(
    "/allocate",
    dependencies=[Depends(require_permissions("logistics:create"))]
)
async def allocate_carrier(
    data: AllocationRequestSchema,
    db: DB,
    current_user: CurrentUser,
):
    """
    Allocate carrier for a shipment.

    Returns the selected carrier based on the specified strategy,
    along with cost breakdown and alternative options.

    This endpoint can be used to:
    1. Get a carrier recommendation for order processing
    2. Compare options with different strategies
    3. Filter by specific transporters using transporter_ids
    """
    engine = PricingEngine(db)

    request = RateCalculationRequest(
        origin_pincode=data.origin_pincode,
        destination_pincode=data.destination_pincode,
        weight_kg=data.weight_kg,
        length_cm=data.length_cm,
        width_cm=data.width_cm,
        height_cm=data.height_cm,
        payment_mode=data.payment_mode,
        order_value=data.order_value,
        channel=data.channel,
        declared_value=data.declared_value,
        is_fragile=data.is_fragile,
        num_packages=data.num_packages,
        service_type=data.service_type,
        transporter_ids=data.transporter_ids,
    )

    allocation_strategy = AllocationStrategy(data.strategy)
    return await engine.allocate(request, allocation_strategy)
