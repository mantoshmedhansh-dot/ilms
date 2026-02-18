"""Region API endpoints — CRUD + tree + dropdown."""
from typing import Optional, List
import uuid
from math import ceil

from fastapi import APIRouter, HTTPException, status, Query, Depends
from sqlalchemy import select, func, or_

from app.api.deps import DB, CurrentUser, require_permissions
from app.models.region import Region, RegionType
from app.schemas.region import (
    RegionCreate,
    RegionUpdate,
    RegionResponse,
    RegionWithChildren,
    RegionListResponse,
    RegionTreeResponse,
)

router = APIRouter(tags=["Regions"])


# ---------- helpers ----------

def _build_tree(regions: list[Region], parent_id: uuid.UUID | None = None) -> list[dict]:
    """Recursively build a region tree from a flat list."""
    tree = []
    for r in regions:
        if r.parent_id == parent_id:
            node = {
                "id": r.id,
                "name": r.name,
                "code": r.code,
                "type": r.type,
                "description": r.description,
                "parent_id": r.parent_id,
                "is_active": r.is_active,
                "created_at": r.created_at,
                "updated_at": r.updated_at,
                "children": _build_tree(regions, r.id),
            }
            tree.append(node)
    return tree


# ---------- list ----------

@router.get(
    "",
    response_model=RegionListResponse,
    dependencies=[Depends(require_permissions("inventory:view"))],
)
async def list_regions(
    db: DB,
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=200),
    type: Optional[RegionType] = Query(None),
    parent_id: Optional[uuid.UUID] = Query(None),
    is_active: Optional[bool] = Query(None),
    search: Optional[str] = Query(None),
):
    """Paginated list of regions with optional filters."""
    stmt = select(Region)
    count_stmt = select(func.count(Region.id))

    if type is not None:
        stmt = stmt.where(Region.type == type.value)
        count_stmt = count_stmt.where(Region.type == type.value)
    if parent_id is not None:
        stmt = stmt.where(Region.parent_id == parent_id)
        count_stmt = count_stmt.where(Region.parent_id == parent_id)
    if is_active is not None:
        stmt = stmt.where(Region.is_active == is_active)
        count_stmt = count_stmt.where(Region.is_active == is_active)
    if search:
        like = f"%{search}%"
        filt = or_(Region.name.ilike(like), Region.code.ilike(like))
        stmt = stmt.where(filt)
        count_stmt = count_stmt.where(filt)

    total = (await db.execute(count_stmt)).scalar() or 0
    skip = (page - 1) * size
    stmt = stmt.order_by(Region.name).offset(skip).limit(size)
    rows = (await db.execute(stmt)).scalars().all()

    return RegionListResponse(
        items=[RegionResponse.model_validate(r) for r in rows],
        total=total,
        page=page,
        size=size,
        pages=ceil(total / size) if total > 0 else 1,
    )


# ---------- tree ----------

@router.get(
    "/tree",
    response_model=RegionTreeResponse,
    dependencies=[Depends(require_permissions("inventory:view"))],
)
async def get_region_tree(db: DB):
    """Full region tree (COUNTRY > ZONE > STATE > CITY > AREA)."""
    stmt = select(Region).where(Region.is_active == True).order_by(Region.name)
    rows = list((await db.execute(stmt)).scalars().all())
    tree = _build_tree(rows, parent_id=None)
    return RegionTreeResponse(regions=tree)


# ---------- dropdown ----------

@router.get(
    "/dropdown",
    response_model=list[dict],
    dependencies=[Depends(require_permissions("inventory:view"))],
)
async def get_regions_dropdown(
    db: DB,
    type: Optional[RegionType] = Query(None),
    parent_id: Optional[uuid.UUID] = Query(None),
):
    """Flat list for dropdown selectors — [{id, name, code, type}]."""
    stmt = select(Region).where(Region.is_active == True)
    if type is not None:
        stmt = stmt.where(Region.type == type.value)
    if parent_id is not None:
        stmt = stmt.where(Region.parent_id == parent_id)
    stmt = stmt.order_by(Region.name)
    rows = (await db.execute(stmt)).scalars().all()
    return [
        {"id": str(r.id), "name": r.name, "code": r.code, "type": r.type}
        for r in rows
    ]


# ---------- get by id ----------

@router.get(
    "/{region_id}",
    response_model=RegionWithChildren,
    dependencies=[Depends(require_permissions("inventory:view"))],
)
async def get_region(region_id: uuid.UUID, db: DB):
    """Get a single region with its children."""
    region = await db.get(Region, region_id)
    if not region:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Region not found")

    # Fetch direct children
    children_stmt = (
        select(Region)
        .where(Region.parent_id == region_id, Region.is_active == True)
        .order_by(Region.name)
    )
    children = list((await db.execute(children_stmt)).scalars().all())

    resp = RegionWithChildren.model_validate(region)
    resp.children = [RegionResponse.model_validate(c) for c in children]
    return resp


# ---------- create ----------

@router.post(
    "",
    response_model=RegionResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permissions("inventory:create"))],
)
async def create_region(data: RegionCreate, db: DB, current_user: CurrentUser):
    """Create a new region."""
    # Check unique code
    existing = (
        await db.execute(select(Region).where(Region.code == data.code))
    ).scalar_one_or_none()
    if existing:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail="Region with this code already exists",
        )

    # Validate parent exists if supplied
    if data.parent_id:
        parent = await db.get(Region, data.parent_id)
        if not parent:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST, detail="Parent region not found"
            )

    region = Region(**data.model_dump())
    db.add(region)
    await db.commit()
    await db.refresh(region)
    return RegionResponse.model_validate(region)


# ---------- update ----------

@router.put(
    "/{region_id}",
    response_model=RegionResponse,
    dependencies=[Depends(require_permissions("inventory:update"))],
)
async def update_region(
    region_id: uuid.UUID,
    data: RegionUpdate,
    db: DB,
    current_user: CurrentUser,
):
    """Update an existing region."""
    region = await db.get(Region, region_id)
    if not region:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Region not found")

    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(region, key, value)

    await db.commit()
    await db.refresh(region)
    return RegionResponse.model_validate(region)


# ---------- delete (soft) ----------

@router.delete(
    "/{region_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_permissions("inventory:delete"))],
)
async def delete_region(
    region_id: uuid.UUID,
    db: DB,
    current_user: CurrentUser,
):
    """Soft-delete a region (set is_active=False)."""
    region = await db.get(Region, region_id)
    if not region:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Region not found")
    region.is_active = False
    await db.commit()
