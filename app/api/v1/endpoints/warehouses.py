"""Warehouse API endpoints."""
from typing import Optional
import uuid
from math import ceil

from fastapi import APIRouter, HTTPException, status, Query, Depends

from app.api.deps import DB, CurrentUser, require_permissions
from app.models.warehouse import WarehouseType
from app.schemas.warehouse import (
    WarehouseCreate,
    WarehouseUpdate,
    WarehouseResponse,
    WarehouseBrief,
    WarehouseListResponse,
)
from app.services.inventory_service import InventoryService


router = APIRouter(tags=["Warehouses"])


@router.get(
    "",
    response_model=WarehouseListResponse,
    dependencies=[Depends(require_permissions("inventory:view"))]
)
async def list_warehouses(
    db: DB,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    warehouse_type: Optional[WarehouseType] = Query(None),
    region_id: Optional[uuid.UUID] = Query(None),
    is_active: bool = Query(True),
    search: Optional[str] = Query(None),
):
    """
    Get paginated list of warehouses.
    Requires: inventory:view permission
    """
    service = InventoryService(db)
    skip = (page - 1) * size

    warehouses, total = await service.get_warehouses(
        warehouse_type=warehouse_type,
        region_id=region_id,
        is_active=is_active,
        search=search,
        skip=skip,
        limit=size,
    )

    return WarehouseListResponse(
        items=[WarehouseResponse.model_validate(w) for w in warehouses],
        total=total,
        page=page,
        size=size,
        pages=ceil(total / size) if total > 0 else 1,
    )


@router.get(
    "/dropdown",
    response_model=list[WarehouseBrief],
    dependencies=[Depends(require_permissions("inventory:view"))]
)
async def get_warehouses_dropdown(
    db: DB,
    warehouse_type: Optional[WarehouseType] = Query(None),
    is_active: bool = Query(True),
):
    """Get warehouses for dropdown selection."""
    service = InventoryService(db)
    warehouses, _ = await service.get_warehouses(
        warehouse_type=warehouse_type,
        is_active=is_active,
        limit=100,
    )
    return [WarehouseBrief.model_validate(w) for w in warehouses]


@router.get(
    "/{warehouse_id}",
    response_model=WarehouseResponse,
    dependencies=[Depends(require_permissions("inventory:view"))]
)
async def get_warehouse(
    warehouse_id: uuid.UUID,
    db: DB,
):
    """Get warehouse by ID."""
    service = InventoryService(db)
    warehouse = await service.get_warehouse_by_id(warehouse_id)

    if not warehouse:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Warehouse not found"
        )

    return WarehouseResponse.model_validate(warehouse)


@router.post(
    "",
    response_model=WarehouseResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permissions("inventory:create"))]
)
async def create_warehouse(
    data: WarehouseCreate,
    db: DB,
    current_user: CurrentUser,
):
    """
    Create a new warehouse.
    Requires: inventory:create permission
    """
    service = InventoryService(db)

    # Check for duplicate code if provided
    if data.code:
        existing = await service.get_warehouse_by_code(data.code)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Warehouse with this code already exists"
            )

    warehouse = await service.create_warehouse(data.model_dump())
    return WarehouseResponse.model_validate(warehouse)


@router.put(
    "/{warehouse_id}",
    response_model=WarehouseResponse,
    dependencies=[Depends(require_permissions("inventory:update"))]
)
async def update_warehouse(
    warehouse_id: uuid.UUID,
    data: WarehouseUpdate,
    db: DB,
    current_user: CurrentUser,
):
    """
    Update a warehouse.
    Requires: inventory:update permission
    """
    service = InventoryService(db)

    warehouse = await service.update_warehouse(
        warehouse_id,
        data.model_dump(exclude_unset=True)
    )

    if not warehouse:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Warehouse not found"
        )

    return WarehouseResponse.model_validate(warehouse)


@router.delete(
    "/{warehouse_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_permissions("inventory:delete"))]
)
async def deactivate_warehouse(
    warehouse_id: uuid.UUID,
    db: DB,
    current_user: CurrentUser,
):
    """
    Deactivate a warehouse (soft delete).
    Requires: inventory:delete permission
    """
    service = InventoryService(db)

    warehouse = await service.get_warehouse_by_id(warehouse_id)
    if not warehouse:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Warehouse not found"
        )

    await service.update_warehouse(warehouse_id, {"is_active": False})
