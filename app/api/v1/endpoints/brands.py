from typing import Optional
import uuid
from math import ceil

from fastapi import APIRouter, HTTPException, status, Query, Depends

from app.api.deps import DB, CurrentUser, Permissions, require_permissions
from app.services.cache_service import get_cache
from app.schemas.brand import (
    BrandCreate,
    BrandUpdate,
    BrandResponse,
    BrandListResponse,
)
from app.services.product_service import ProductService
from app.core.module_decorators import require_module

router = APIRouter(tags=["Brands"])


@router.get("", response_model=BrandListResponse)
@require_module("oms_fulfillment")
async def list_brands(
    db: DB,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    include_inactive: bool = Query(False),
):
    """
    Get paginated list of brands.
    Public endpoint for viewing catalog.
    """
    service = ProductService(db)
    skip = (page - 1) * size

    brands, total = await service.get_brands(
        include_inactive=include_inactive,
        skip=skip,
        limit=size
    )

    return BrandListResponse(
        items=[BrandResponse.model_validate(b) for b in brands],
        total=total,
        page=page,
        size=size,
        pages=ceil(total / size) if total > 0 else 1,
    )


@router.get("/{brand_id}", response_model=BrandResponse)
@require_module("oms_fulfillment")
async def get_brand(
    brand_id: uuid.UUID,
    db: DB,
):
    """Get a brand by ID."""
    service = ProductService(db)
    brand = await service.get_brand_by_id(brand_id)

    if not brand:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Brand not found"
        )

    return BrandResponse.model_validate(brand)


@router.get("/slug/{slug}", response_model=BrandResponse)
@require_module("oms_fulfillment")
async def get_brand_by_slug(
    slug: str,
    db: DB,
):
    """Get a brand by slug."""
    service = ProductService(db)
    brand = await service.get_brand_by_slug(slug)

    if not brand:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Brand not found"
        )

    return BrandResponse.model_validate(brand)


@router.post(
    "",
    response_model=BrandResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permissions("products:create"))]
)
async def create_brand(
    data: BrandCreate,
    db: DB,
    current_user: CurrentUser,
):
    """
    Create a new brand.
    Requires: products:create permission
    """
    service = ProductService(db)

    # Check slug uniqueness
    existing = await service.get_brand_by_slug(data.slug)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Brand with slug '{data.slug}' already exists"
        )

    brand = await service.create_brand(data.model_dump())

    # Invalidate brand caches
    cache = get_cache()
    await cache.invalidate_brands()

    return BrandResponse.model_validate(brand)


@router.put(
    "/{brand_id}",
    response_model=BrandResponse,
    dependencies=[Depends(require_permissions("products:update"))]
)
async def update_brand(
    brand_id: uuid.UUID,
    data: BrandUpdate,
    db: DB,
    current_user: CurrentUser,
):
    """
    Update a brand.
    Requires: products:update permission
    """
    service = ProductService(db)

    # Check if brand exists
    brand = await service.get_brand_by_id(brand_id)
    if not brand:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Brand not found"
        )

    # Check slug uniqueness if changing
    if data.slug and data.slug != brand.slug:
        existing = await service.get_brand_by_slug(data.slug)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Brand with slug '{data.slug}' already exists"
            )

    updated = await service.update_brand(
        brand_id,
        data.model_dump(exclude_unset=True)
    )

    # Invalidate brand caches
    cache = get_cache()
    await cache.invalidate_brands()

    return BrandResponse.model_validate(updated)


@router.delete(
    "/{brand_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_permissions("products:delete"))]
)
async def delete_brand(
    brand_id: uuid.UUID,
    db: DB,
    current_user: CurrentUser,
):
    """
    Delete (deactivate) a brand.
    Requires: products:delete permission
    """
    service = ProductService(db)

    brand = await service.get_brand_by_id(brand_id)
    if not brand:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Brand not found"
        )

    await service.update_brand(brand_id, {"is_active": False})

    # Invalidate brand caches
    cache = get_cache()
    await cache.invalidate_brands()
