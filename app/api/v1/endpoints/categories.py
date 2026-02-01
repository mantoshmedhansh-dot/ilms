from typing import Optional
import uuid
from math import ceil

from fastapi import APIRouter, HTTPException, status, Query, Depends

from app.api.deps import DB, CurrentUser, Permissions, require_permissions
from app.services.cache_service import get_cache
from app.schemas.category import (
    CategoryCreate,
    CategoryUpdate,
    CategoryResponse,
    CategoryListResponse,
    CategoryWithChildren,
    CategoryTreeResponse,
)
from app.services.product_service import ProductService
from app.core.module_decorators import require_module

router = APIRouter(tags=["Categories"])


@router.get("", response_model=CategoryListResponse)
@require_module("oms_fulfillment")
async def list_categories(
    db: DB,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    parent_id: Optional[uuid.UUID] = Query(None, description="Filter by parent category"),
    include_inactive: bool = Query(False),
):
    """
    Get paginated list of categories.
    Public endpoint for viewing catalog.
    """
    service = ProductService(db)
    skip = (page - 1) * size

    categories, total = await service.get_categories(
        parent_id=parent_id,
        include_inactive=include_inactive,
        skip=skip,
        limit=size
    )

    return CategoryListResponse(
        items=[CategoryResponse.model_validate(c) for c in categories],
        total=total,
        page=page,
        size=size,
        pages=ceil(total / size) if total > 0 else 1,
    )


@router.get("/roots", response_model=CategoryListResponse)
@require_module("oms_fulfillment")
async def get_root_categories(db: DB):
    """
    Get only ROOT categories (parent_id IS NULL).
    Used for cascading dropdowns - first level selection.
    Public endpoint.
    """
    service = ProductService(db)
    categories, total = await service.get_categories(
        parent_id=None,  # Only root categories
        roots_only=True,  # Explicit flag for roots only
        include_inactive=False,
        skip=0,
        limit=100
    )

    return CategoryListResponse(
        items=[CategoryResponse.model_validate(c) for c in categories],
        total=total,
        page=1,
        size=100,
        pages=1,
    )


@router.get("/{parent_id}/children", response_model=CategoryListResponse)
@require_module("oms_fulfillment")
async def get_category_children(
    parent_id: uuid.UUID,
    db: DB,
):
    """
    Get children (subcategories) of a specific parent category.
    Used for cascading dropdowns - second level selection.
    Public endpoint.
    """
    service = ProductService(db)

    # Verify parent exists
    parent = await service.get_category_by_id(parent_id)
    if not parent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Parent category not found"
        )

    categories, total = await service.get_categories(
        parent_id=parent_id,
        include_inactive=False,
        skip=0,
        limit=100
    )

    return CategoryListResponse(
        items=[CategoryResponse.model_validate(c) for c in categories],
        total=total,
        page=1,
        size=100,
        pages=1,
    )


@router.get("/tree", response_model=CategoryTreeResponse)
@require_module("oms_fulfillment")
async def get_category_tree(db: DB):
    """
    Get full category hierarchy as a tree.
    Public endpoint.
    """
    service = ProductService(db)
    categories = await service.get_category_tree()

    def build_tree(cat) -> CategoryWithChildren:
        return CategoryWithChildren(
            id=cat.id,
            name=cat.name,
            slug=cat.slug,
            description=cat.description,
            parent_id=cat.parent_id,
            image_url=cat.image_url,
            icon=cat.icon,
            sort_order=cat.sort_order,
            meta_title=cat.meta_title,
            meta_description=cat.meta_description,
            is_active=cat.is_active,
            is_featured=cat.is_featured,
            created_at=cat.created_at,
            updated_at=cat.updated_at,
            children=[build_tree(child) for child in cat.children if child.is_active],
        )

    return CategoryTreeResponse(
        categories=[build_tree(c) for c in categories]
    )


@router.get("/{category_id}", response_model=CategoryResponse)
@require_module("oms_fulfillment")
async def get_category(
    category_id: uuid.UUID,
    db: DB,
):
    """Get a category by ID."""
    service = ProductService(db)
    category = await service.get_category_by_id(category_id)

    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category not found"
        )

    return CategoryResponse.model_validate(category)


@router.get("/slug/{slug}", response_model=CategoryResponse)
@require_module("oms_fulfillment")
async def get_category_by_slug(
    slug: str,
    db: DB,
):
    """Get a category by slug."""
    service = ProductService(db)
    category = await service.get_category_by_slug(slug)

    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category not found"
        )

    return CategoryResponse.model_validate(category)


@router.post(
    "",
    response_model=CategoryResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permissions("products:create"))]
)
async def create_category(
    data: CategoryCreate,
    db: DB,
    current_user: CurrentUser,
):
    """
    Create a new category.
    Requires: products:create permission
    """
    service = ProductService(db)

    # Check slug uniqueness
    existing = await service.get_category_by_slug(data.slug)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Category with slug '{data.slug}' already exists"
        )

    # Validate parent exists if provided
    if data.parent_id:
        parent = await service.get_category_by_id(data.parent_id)
        if not parent:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Parent category not found"
            )

    category = await service.create_category(data.model_dump())

    # Invalidate category caches
    cache = get_cache()
    await cache.invalidate_categories()

    return CategoryResponse.model_validate(category)


@router.put(
    "/{category_id}",
    response_model=CategoryResponse,
    dependencies=[Depends(require_permissions("products:update"))]
)
async def update_category(
    category_id: uuid.UUID,
    data: CategoryUpdate,
    db: DB,
    current_user: CurrentUser,
):
    """
    Update a category.
    Requires: products:update permission
    """
    service = ProductService(db)

    # Check if category exists
    category = await service.get_category_by_id(category_id)
    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category not found"
        )

    # Check slug uniqueness if changing
    if data.slug and data.slug != category.slug:
        existing = await service.get_category_by_slug(data.slug)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Category with slug '{data.slug}' already exists"
            )

    updated = await service.update_category(
        category_id,
        data.model_dump(exclude_unset=True)
    )

    # Invalidate category caches
    cache = get_cache()
    await cache.invalidate_categories()

    return CategoryResponse.model_validate(updated)


@router.delete(
    "/{category_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_permissions("products:delete"))]
)
async def delete_category(
    category_id: uuid.UUID,
    db: DB,
    current_user: CurrentUser,
):
    """
    Delete (deactivate) a category.
    Requires: products:delete permission
    """
    service = ProductService(db)

    category = await service.get_category_by_id(category_id)
    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category not found"
        )

    await service.update_category(category_id, {"is_active": False})

    # Invalidate category caches
    cache = get_cache()
    await cache.invalidate_categories()
