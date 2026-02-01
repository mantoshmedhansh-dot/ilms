from typing import Optional
import uuid
import json
from math import ceil

from fastapi import APIRouter, HTTPException, status, Query, Depends

from app.api.deps import DB, CurrentUser, Permissions, require_permissions
from app.services.cache_service import get_cache
from app.models.product import ProductStatus
from app.schemas.product import (
    ProductCreate,
    ProductUpdate,
    ProductResponse,
    ProductDetailResponse,
    ProductListResponse,
    ProductImageCreate,
    ProductImageResponse,
    ProductVariantCreate,
    ProductVariantUpdate,
    ProductVariantResponse,
    CategoryBrief,
    BrandBrief,
)
from app.services.product_service import ProductService
from app.services.costing_service import CostingService
from app.services.product_orchestration_service import ProductOrchestrationService
from app.schemas.product_cost import (

    ProductCostResponse,
    ProductCostBriefResponse,
    CostHistoryResponse,
    CostHistoryEntry,
    ProductCostSummary,
    WeightedAverageCostRequest,
    WeightedAverageCostResponse,
)
from app.core.module_decorators import require_module


router = APIRouter(tags=["Products"])


# ==================== PRODUCT CRUD ====================

@router.get("", response_model=ProductListResponse)
@require_module("oms_fulfillment")
async def list_products(
    db: DB,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    category_id: Optional[uuid.UUID] = Query(None, description="Filter by category"),
    brand_id: Optional[uuid.UUID] = Query(None, description="Filter by brand"),
    status: Optional[ProductStatus] = Query(None, description="Filter by status"),
    search: Optional[str] = Query(None, description="Search in name, SKU, description"),
    is_featured: Optional[bool] = Query(None, description="Filter featured products"),
    is_active: Optional[bool] = Query(True, description="Filter active products"),
    min_price: Optional[float] = Query(None, ge=0, description="Minimum price"),
    max_price: Optional[float] = Query(None, ge=0, description="Maximum price"),
    sort_by: str = Query("created_at", description="Sort field"),
    sort_order: str = Query("desc", regex="^(asc|desc)$"),
):
    """
    Get paginated list of products with filters.
    Public endpoint for catalog browsing.
    """
    service = ProductService(db)
    skip = (page - 1) * size

    products, total = await service.get_products(
        category_id=category_id,
        brand_id=brand_id,
        status=status,
        search=search,
        is_featured=is_featured,
        is_active=is_active,
        min_price=min_price,
        max_price=max_price,
        skip=skip,
        limit=size,
        sort_by=sort_by,
        sort_order=sort_order,
    )

    items = []
    for p in products:
        items.append(ProductResponse(
            id=p.id,
            name=p.name,
            slug=p.slug,
            sku=p.sku,
            model_number=p.model_number,
            # Master Product File fields
            fg_code=p.fg_code,
            model_code=p.model_code,
            item_type=p.item_type,
            short_description=p.short_description,
            description=p.description,
            features=p.features,
            category=CategoryBrief.model_validate(p.category) if p.category else None,
            brand=BrandBrief.model_validate(p.brand) if p.brand else None,
            mrp=p.mrp,
            selling_price=p.selling_price,
            dealer_price=p.dealer_price,
            discount_percentage=p.discount_percentage,
            hsn_code=p.hsn_code,
            gst_rate=p.gst_rate,
            warranty_months=p.warranty_months,
            extended_warranty_available=p.extended_warranty_available,
            warranty_terms=p.warranty_terms,
            # Physical attributes - weight and dimensions
            dead_weight_kg=p.dead_weight_kg,
            length_cm=p.length_cm,
            width_cm=p.width_cm,
            height_cm=p.height_cm,
            # Computed weight fields from Master Product File
            volumetric_weight_kg=p.volumetric_weight_kg,
            chargeable_weight_kg=p.chargeable_weight_kg,
            status=p.status,
            is_active=p.is_active,
            is_featured=p.is_featured,
            is_bestseller=p.is_bestseller,
            is_new_arrival=p.is_new_arrival,
            sort_order=p.sort_order,
            meta_title=p.meta_title,
            meta_description=p.meta_description,
            meta_keywords=p.meta_keywords,
            images=[{
                "id": img.id,
                "image_url": img.image_url,
                "thumbnail_url": img.thumbnail_url,
                "alt_text": img.alt_text,
                "is_primary": img.is_primary,
                "sort_order": img.sort_order,
            } for img in p.images],
            created_at=p.created_at,
            updated_at=p.updated_at,
            published_at=p.published_at,
        ))

    return ProductListResponse(
        items=items,
        total=total,
        page=page,
        size=size,
        pages=ceil(total / size) if total > 0 else 1,
    )


@router.get("/stats", dependencies=[Depends(require_permissions("products:view"))])
async def get_product_stats(db: DB):
    """
    Get product statistics.
    Requires: products:view permission
    """
    service = ProductService(db)
    return await service.get_product_stats()


@router.get("/top-selling", dependencies=[Depends(require_permissions("products:view"))])
async def get_top_selling_products(
    db: DB,
    limit: int = Query(5, ge=1, le=20),
):
    """
    Get top selling products for dashboard.
    Requires: products:view permission
    """
    service = ProductService(db)
    products = await service.get_top_selling_products(limit=limit)
    return {"items": products}


# ==================== PRODUCT COST ENDPOINTS (Static Routes First) ====================

@router.get(
    "/costs/summary",
    response_model=ProductCostSummary,
    dependencies=[Depends(require_permissions("products:view"))]
)
async def get_inventory_valuation_summary(
    db: DB,
    current_user: CurrentUser,
    warehouse_id: Optional[uuid.UUID] = Query(None, description="Filter by warehouse"),
):
    """
    Get inventory valuation summary.

    Shows total inventory value, average stock value per product,
    and counts by valuation method.

    Requires: products:view permission
    """
    costing_service = CostingService(db)
    summary = await costing_service.get_inventory_valuation_summary(warehouse_id=warehouse_id)

    return ProductCostSummary(
        total_products=summary["total_products"],
        total_inventory_value=summary["total_inventory_value"],
        average_stock_value_per_product=summary["average_stock_value_per_product"],
        products_with_cost=summary["products_with_cost"],
        products_without_cost=summary["products_without_cost"],
        weighted_avg_count=summary["weighted_avg_count"],
        fifo_count=summary["fifo_count"],
        specific_id_count=summary["specific_id_count"],
    )


@router.post(
    "/costs/initialize",
    dependencies=[Depends(require_permissions("products:update"))]
)
async def initialize_product_costs(
    db: DB,
    current_user: CurrentUser,
):
    """
    Initialize ProductCost records for all products without one.

    Uses product's static cost_price as initial average_cost.
    Run this once after migration to populate initial cost records.

    Requires: products:update permission
    """
    costing_service = CostingService(db)
    result = await costing_service.initialize_costs_from_products()
    return result


# ==================== PRODUCT DETAIL ENDPOINTS ====================

@router.get("/{product_id}", response_model=ProductDetailResponse)
@require_module("oms_fulfillment")
async def get_product(
    product_id: uuid.UUID,
    db: DB,
):
    """Get a product by ID with all details."""
    service = ProductService(db)
    product = await service.get_product_by_id(product_id, include_all=True)

    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found"
        )

    return _build_product_detail_response(product)


@router.get("/sku/{sku}", response_model=ProductResponse)
@require_module("oms_fulfillment")
async def get_product_by_sku(
    sku: str,
    db: DB,
):
    """Get a product by SKU."""
    service = ProductService(db)
    product = await service.get_product_by_sku(sku)

    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found"
        )

    return _build_product_response(product)


@router.get("/slug/{slug}", response_model=ProductDetailResponse)
@require_module("oms_fulfillment")
async def get_product_by_slug(
    slug: str,
    db: DB,
):
    """Get a product by slug with all details."""
    service = ProductService(db)
    product = await service.get_product_by_slug(slug)

    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found"
        )

    return _build_product_detail_response(product)


@router.post(
    "",
    response_model=ProductDetailResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permissions("products:create"))]
)
async def create_product(
    data: ProductCreate,
    db: DB,
    current_user: CurrentUser,
):
    """
    Create a new product.
    Requires: products:create permission
    """
    service = ProductService(db)

    # Check SKU uniqueness
    existing = await service.get_product_by_sku(data.sku)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Product with SKU '{data.sku}' already exists"
        )

    # Check slug uniqueness
    existing_slug = await service.get_product_by_slug(data.slug)
    if existing_slug:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Product with slug '{data.slug}' already exists"
        )

    # Validate category exists
    category = await service.get_category_by_id(data.category_id)
    if not category:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Category not found"
        )

    # Validate brand exists
    brand = await service.get_brand_by_id(data.brand_id)
    if not brand:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Brand not found"
        )

    product = await service.create_product(data)

    # ORCHESTRATION: Auto-setup serialization (model_code, serial sequence)
    orchestration = ProductOrchestrationService(db)
    orchestration_result = await orchestration.on_product_created(product)

    # Commit orchestration changes
    await db.commit()

    # Invalidate product caches
    cache = get_cache()
    await cache.invalidate_products()

    # Re-fetch with all relationships loaded (refresh strips relationships)
    final_product = await service.get_product_by_id(product.id, include_all=True)
    return _build_product_detail_response(final_product)


@router.put(
    "/{product_id}",
    response_model=ProductDetailResponse,
    dependencies=[Depends(require_permissions("products:update"))]
)
async def update_product(
    product_id: uuid.UUID,
    data: ProductUpdate,
    db: DB,
    current_user: CurrentUser,
):
    """
    Update a product.
    Requires: products:update permission
    """
    service = ProductService(db)

    product = await service.get_product_by_id(product_id)
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found"
        )

    # Track old model_code for orchestration
    old_model_code = product.model_code

    # Validate category if changing
    if data.category_id:
        category = await service.get_category_by_id(data.category_id)
        if not category:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Category not found"
            )

    # Validate brand if changing
    if data.brand_id:
        brand = await service.get_brand_by_id(data.brand_id)
        if not brand:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Brand not found"
            )

    updated = await service.update_product(product_id, data)

    # ORCHESTRATION: Update serialization if model_code changed
    orchestration = ProductOrchestrationService(db)
    await orchestration.on_product_updated(updated, old_model_code)

    # Commit orchestration changes
    await db.commit()

    # Invalidate product caches
    cache = get_cache()
    await cache.invalidate_products()

    # Re-fetch with all relationships loaded (refresh strips relationships)
    final_product = await service.get_product_by_id(product_id, include_all=True)
    return _build_product_detail_response(final_product)


@router.delete(
    "/{product_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_permissions("products:delete"))]
)
async def delete_product(
    product_id: uuid.UUID,
    db: DB,
    current_user: CurrentUser,
):
    """
    Delete (deactivate) a product.
    Requires: products:delete permission
    """
    service = ProductService(db)

    success = await service.delete_product(product_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found"
        )

    # Invalidate product caches
    cache = get_cache()
    await cache.invalidate_products()


# ==================== PRODUCT IMAGES ====================

@router.post(
    "/{product_id}/images",
    response_model=ProductImageResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permissions("products:update"))]
)
async def add_product_image(
    product_id: uuid.UUID,
    data: ProductImageCreate,
    db: DB,
    current_user: CurrentUser,
):
    """Add an image to a product."""
    service = ProductService(db)

    product = await service.get_product_by_id(product_id)
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found"
        )

    image = await service.add_product_image(product_id, data)
    return ProductImageResponse.model_validate(image)


@router.delete(
    "/{product_id}/images/{image_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_permissions("products:update"))]
)
async def delete_product_image(
    product_id: uuid.UUID,
    image_id: uuid.UUID,
    db: DB,
    current_user: CurrentUser,
):
    """Delete a product image."""
    service = ProductService(db)

    success = await service.delete_product_image(image_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Image not found"
        )


@router.put(
    "/{product_id}/images/{image_id}/primary",
    dependencies=[Depends(require_permissions("products:update"))]
)
async def set_primary_image(
    product_id: uuid.UUID,
    image_id: uuid.UUID,
    db: DB,
    current_user: CurrentUser,
):
    """Set an image as primary."""
    service = ProductService(db)

    await service.set_primary_image(product_id, image_id)
    return {"message": "Primary image updated"}


# ==================== PRODUCT VARIANTS ====================

@router.post(
    "/{product_id}/variants",
    response_model=ProductVariantResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permissions("products:update"))]
)
async def add_product_variant(
    product_id: uuid.UUID,
    data: ProductVariantCreate,
    db: DB,
    current_user: CurrentUser,
):
    """Add a variant to a product."""
    service = ProductService(db)

    product = await service.get_product_by_id(product_id)
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found"
        )

    variant = await service.add_product_variant(product_id, data)
    return ProductVariantResponse.model_validate(variant)


@router.put(
    "/{product_id}/variants/{variant_id}",
    response_model=ProductVariantResponse,
    dependencies=[Depends(require_permissions("products:update"))]
)
async def update_product_variant(
    product_id: uuid.UUID,
    variant_id: uuid.UUID,
    data: ProductVariantUpdate,
    db: DB,
    current_user: CurrentUser,
):
    """Update a product variant."""
    service = ProductService(db)

    variant = await service.update_product_variant(variant_id, data)
    if not variant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Variant not found"
        )

    return ProductVariantResponse.model_validate(variant)


@router.delete(
    "/{product_id}/variants/{variant_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_permissions("products:update"))]
)
async def delete_product_variant(
    product_id: uuid.UUID,
    variant_id: uuid.UUID,
    db: DB,
    current_user: CurrentUser,
):
    """Delete a product variant."""
    service = ProductService(db)

    success = await service.delete_product_variant(variant_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Variant not found"
        )


# ==================== HELPER FUNCTIONS ====================

def _build_product_response(p) -> ProductResponse:
    """Build ProductResponse from Product model."""
    return ProductResponse(
        id=p.id,
        name=p.name,
        slug=p.slug,
        sku=p.sku,
        model_number=p.model_number,
        # Master Product File fields
        fg_code=p.fg_code,
        model_code=p.model_code,
        item_type=p.item_type,
        short_description=p.short_description,
        description=p.description,
        features=p.features,
        category=CategoryBrief.model_validate(p.category) if p.category else None,
        brand=BrandBrief.model_validate(p.brand) if p.brand else None,
        mrp=p.mrp,
        selling_price=p.selling_price,
        dealer_price=p.dealer_price,
        discount_percentage=p.discount_percentage,
        hsn_code=p.hsn_code,
        gst_rate=p.gst_rate,
        warranty_months=p.warranty_months,
        extended_warranty_available=p.extended_warranty_available,
        warranty_terms=p.warranty_terms,
        # Weight fields
        dead_weight_kg=p.dead_weight_kg,
        length_cm=p.length_cm,
        width_cm=p.width_cm,
        height_cm=p.height_cm,
        volumetric_weight_kg=p.volumetric_weight_kg,
        chargeable_weight_kg=p.chargeable_weight_kg,
        status=p.status,
        is_active=p.is_active,
        is_featured=p.is_featured,
        is_bestseller=p.is_bestseller,
        is_new_arrival=p.is_new_arrival,
        sort_order=p.sort_order,
        meta_title=p.meta_title,
        meta_description=p.meta_description,
        meta_keywords=p.meta_keywords,
        images=[ProductImageResponse.model_validate(img) for img in p.images],
        created_at=p.created_at,
        updated_at=p.updated_at,
        published_at=p.published_at,
    )


def _build_product_detail_response(p) -> ProductDetailResponse:
    """Build ProductDetailResponse from Product model."""
    return ProductDetailResponse(
        id=p.id,
        name=p.name,
        slug=p.slug,
        sku=p.sku,
        model_number=p.model_number,
        # Master Product File fields
        fg_code=p.fg_code,
        model_code=p.model_code,
        item_type=p.item_type,
        short_description=p.short_description,
        description=p.description,
        features=p.features,
        category=CategoryBrief.model_validate(p.category) if p.category else None,
        brand=BrandBrief.model_validate(p.brand) if p.brand else None,
        mrp=p.mrp,
        selling_price=p.selling_price,
        dealer_price=p.dealer_price,
        discount_percentage=p.discount_percentage,
        hsn_code=p.hsn_code,
        gst_rate=p.gst_rate,
        warranty_months=p.warranty_months,
        extended_warranty_available=p.extended_warranty_available,
        warranty_terms=p.warranty_terms,
        # Weight fields
        dead_weight_kg=p.dead_weight_kg,
        length_cm=p.length_cm,
        width_cm=p.width_cm,
        height_cm=p.height_cm,
        volumetric_weight_kg=p.volumetric_weight_kg,
        chargeable_weight_kg=p.chargeable_weight_kg,
        status=p.status,
        is_active=p.is_active,
        is_featured=p.is_featured,
        is_bestseller=p.is_bestseller,
        is_new_arrival=p.is_new_arrival,
        sort_order=p.sort_order,
        meta_title=p.meta_title,
        meta_description=p.meta_description,
        meta_keywords=p.meta_keywords,
        images=[ProductImageResponse.model_validate(img) for img in p.images],
        specifications=[{
            "id": spec.id,
            "group_name": spec.group_name,
            "key": spec.key,
            "value": spec.value,
            "sort_order": spec.sort_order,
        } for spec in p.specifications],
        variants=[ProductVariantResponse.model_validate(v) for v in p.variants],
        documents=[{
            "id": doc.id,
            "title": doc.title,
            "document_type": doc.document_type,
            "file_url": doc.file_url,
            "file_size_bytes": doc.file_size_bytes,
            "mime_type": doc.mime_type,
            "sort_order": doc.sort_order,
            "created_at": doc.created_at,
        } for doc in p.documents],
        # Handle extra_data being stored as JSON string in some records
        extra_data=json.loads(p.extra_data) if isinstance(p.extra_data, str) else p.extra_data,
        created_at=p.created_at,
        updated_at=p.updated_at,
        published_at=p.published_at,
    )


# ==================== PRODUCT COSTING (COGS) ====================

@router.get(
    "/{product_id}/cost",
    response_model=ProductCostResponse,
    dependencies=[Depends(require_permissions("products:view"))]
)
async def get_product_cost(
    product_id: uuid.UUID,
    db: DB,
    current_user: CurrentUser,
    variant_id: Optional[uuid.UUID] = Query(None, description="Filter by variant"),
    warehouse_id: Optional[uuid.UUID] = Query(None, description="Filter by warehouse"),
):
    """
    Get current COGS (Cost of Goods Sold) for a product.

    The cost is auto-calculated using Weighted Average Cost method
    from GRN receipts (Purchase Orders).

    Requires: products:view permission
    """
    costing_service = CostingService(db)

    product_cost = await costing_service.get_product_cost(
        product_id=product_id,
        variant_id=variant_id,
        warehouse_id=warehouse_id,
    )

    if not product_cost:
        # Try to create one with initial zero cost
        product_cost = await costing_service.get_or_create_product_cost(
            product_id=product_id,
            variant_id=variant_id,
            warehouse_id=warehouse_id,
        )

    return ProductCostResponse(
        id=product_cost.id,
        product_id=product_cost.product_id,
        variant_id=product_cost.variant_id,
        warehouse_id=product_cost.warehouse_id,
        valuation_method=product_cost.valuation_method,
        average_cost=product_cost.average_cost,
        last_purchase_cost=product_cost.last_purchase_cost,
        standard_cost=product_cost.standard_cost,
        quantity_on_hand=product_cost.quantity_on_hand,
        total_value=product_cost.total_value,
        last_grn_id=product_cost.last_grn_id,
        last_calculated_at=product_cost.last_calculated_at,
        cost_variance=product_cost.cost_variance,
        cost_variance_percentage=product_cost.cost_variance_percentage,
        created_at=product_cost.created_at,
        updated_at=product_cost.updated_at,
    )


@router.get(
    "/{product_id}/cost-history",
    dependencies=[Depends(require_permissions("products:view"))]
)
async def get_product_cost_history(
    product_id: uuid.UUID,
    db: DB,
    current_user: CurrentUser,
    variant_id: Optional[uuid.UUID] = Query(None),
    warehouse_id: Optional[uuid.UUID] = Query(None),
    limit: int = Query(100, ge=1, le=500),
):
    """
    Get cost history for a product (GRN receipt history).

    Shows all cost movements from GRN acceptances,
    including running average after each receipt.

    Requires: products:view permission
    """
    costing_service = CostingService(db)

    history = await costing_service.get_cost_history(
        product_id=product_id,
        variant_id=variant_id,
        warehouse_id=warehouse_id,
        limit=limit,
    )

    return history


@router.post(
    "/{product_id}/cost/calculate-preview",
    response_model=WeightedAverageCostResponse,
    dependencies=[Depends(require_permissions("products:update"))]
)
async def preview_cost_calculation(
    product_id: uuid.UUID,
    data: WeightedAverageCostRequest,
    db: DB,
    current_user: CurrentUser,
):
    """
    Preview weighted average cost calculation without updating.

    Use this to see what the new average cost would be
    if a GRN with given quantity and price is accepted.

    Formula:
    New Avg = (Current Stock Value + New Purchase Value) / (Current Qty + New Qty)

    Requires: products:update permission
    """
    costing_service = CostingService(db)

    result = await costing_service.calculate_weighted_average(
        product_id=product_id,
        new_qty=data.new_quantity,
        new_unit_cost=data.new_unit_cost,
        variant_id=data.variant_id,
        warehouse_id=data.warehouse_id,
    )

    return WeightedAverageCostResponse(**result)


@router.put(
    "/{product_id}/cost/standard-cost",
    dependencies=[Depends(require_permissions("products:update"))]
)
async def set_standard_cost(
    product_id: uuid.UUID,
    standard_cost: float,
    db: DB,
    current_user: CurrentUser,
    variant_id: Optional[uuid.UUID] = Query(None),
    warehouse_id: Optional[uuid.UUID] = Query(None),
):
    """
    Set standard (budgeted) cost for variance analysis.

    The standard cost is compared against the actual average cost
    to show cost variance in reports.

    Requires: products:update permission
    """
    from decimal import Decimal

    costing_service = CostingService(db)

    product_cost = await costing_service.get_or_create_product_cost(
        product_id=product_id,
        variant_id=variant_id,
        warehouse_id=warehouse_id,
    )

    product_cost.standard_cost = Decimal(str(standard_cost))
    await db.commit()

    return {
        "message": "Standard cost updated",
        "product_id": str(product_id),
        "standard_cost": float(product_cost.standard_cost),
        "average_cost": float(product_cost.average_cost),
        "variance": float(product_cost.cost_variance) if product_cost.cost_variance else None,
        "variance_percentage": product_cost.cost_variance_percentage,
    }
