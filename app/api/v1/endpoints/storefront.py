"""Public Storefront API endpoints.

These endpoints are accessible without authentication for the D2C website.
Includes Redis caching for improved performance.
"""
import time
import uuid as uuid_module
from typing import Optional, List
from fastapi import APIRouter, HTTPException, Query, Response
from sqlalchemy import select, func, or_
from sqlalchemy.orm import selectinload

from app.api.deps import DB
from app.config import settings
from app.models.company import Company
from app.models.product import Product, ProductImage
from app.models.category import Category
from app.models.brand import Brand
from app.models.inventory import InventorySummary
from app.models.channel import ChannelInventory, SalesChannel
from app.services.channel_inventory_service import ChannelInventoryService
from app.schemas.storefront import (
    StorefrontProductImage,
    StorefrontProductVariant,
    StorefrontProductSpecification,
    StorefrontProductDocument,
    StorefrontProductResponse,
    StorefrontCategoryResponse,
    StorefrontBrandResponse,
    PaginatedProductsResponse,
    StorefrontCompanyInfo,
    SearchProductSuggestion,
    SearchCategorySuggestion,
    SearchBrandSuggestion,
    SearchSuggestionsResponse,
)
from app.schemas.serviceability import (
    ServiceabilityCheckRequest,
    ServiceabilityCheckResponse,
)
from app.services.cache_service import get_cache
from app.services.serviceability_service import ServiceabilityService

router = APIRouter()


# ==================== Products Endpoints ====================

@router.get("/products", response_model=PaginatedProductsResponse)
async def list_products(
    db: DB,
    response: Response,
    category_id: Optional[str] = None,
    brand_id: Optional[str] = None,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    is_featured: Optional[bool] = None,
    is_bestseller: Optional[bool] = None,
    is_new_arrival: Optional[bool] = None,
    search: Optional[str] = None,
    sort_by: str = Query(default="created_at", pattern="^(name|mrp|selling_price|created_at)$"),
    sort_order: str = Query(default="desc", pattern="^(asc|desc)$"),
    page: int = Query(default=1, ge=1),
    size: int = Query(default=12, ge=1, le=100),
):
    """
    List products for the public storefront.
    No authentication required. Results are cached for 5 minutes.
    """
    start_time = time.time()
    cache = get_cache()

    # Build cache key from query params
    cache_params = {
        "category_id": category_id,
        "brand_id": brand_id,
        "min_price": min_price,
        "max_price": max_price,
        "is_featured": is_featured,
        "is_bestseller": is_bestseller,
        "is_new_arrival": is_new_arrival,
        "search": search,
        "sort_by": sort_by,
        "sort_order": sort_order,
        "page": page,
        "size": size,
    }

    # Try to get from cache
    cached_result = await cache.get_product_list(cache_params)
    if cached_result:
        response.headers["X-Cache"] = "HIT"
        response.headers["X-Response-Time"] = f"{(time.time() - start_time) * 1000:.2f}ms"
        return PaginatedProductsResponse(**cached_result)
    query = (
        select(Product)
        .options(selectinload(Product.images))
        .options(selectinload(Product.category))
        .options(selectinload(Product.brand))
        .where(Product.is_active == True)
    )

    # Apply filters
    if category_id:
        # Convert string to UUID for proper database comparison
        try:
            category_uuid = uuid_module.UUID(category_id)
        except (ValueError, AttributeError):
            # Invalid UUID format, return empty results
            return PaginatedProductsResponse(items=[], total=0, page=page, size=size, pages=0)

        # Collect all relevant category IDs (current + children + parent chain)
        all_category_ids = [category_uuid]

        # Get child category IDs (products in subcategories should show when viewing parent)
        child_categories_query = (
            select(Category.id)
            .where(Category.parent_id == category_uuid)
            .where(Category.is_active == True)
        )
        child_categories_result = await db.execute(child_categories_query)
        child_category_ids = [row[0] for row in child_categories_result.fetchall()]
        all_category_ids.extend(child_category_ids)

        # Also get parent category IDs (products assigned to parent should show in children)
        # This handles the case where "ILMS.AI Optima" is in "Water Purifiers" (parent)
        # but user is viewing "RO+UV Water Purifiers" (child)
        current_cat_result = await db.execute(
            select(Category.parent_id).where(Category.id == category_uuid)
        )
        current_cat_row = current_cat_result.fetchone()
        if current_cat_row and current_cat_row[0]:
            # Add parent category to the filter
            all_category_ids.append(current_cat_row[0])

        query = query.where(Product.category_id.in_(all_category_ids))
    if brand_id:
        try:
            brand_uuid = uuid_module.UUID(brand_id)
            query = query.where(Product.brand_id == brand_uuid)
        except (ValueError, AttributeError):
            pass  # Invalid brand_id, skip filter
    if min_price is not None:
        query = query.where(Product.selling_price >= min_price)
    if max_price is not None:
        query = query.where(Product.selling_price <= max_price)
    if is_featured:
        query = query.where(Product.is_featured == True)
    if is_bestseller:
        query = query.where(Product.is_bestseller == True)
    if is_new_arrival:
        query = query.where(Product.is_new_arrival == True)
    if search:
        search_term = f"%{search}%"
        query = query.where(
            or_(
                Product.name.ilike(search_term),
                Product.sku.ilike(search_term),
                Product.description.ilike(search_term),
            )
        )

    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # Apply sorting
    sort_column = getattr(Product, sort_by)
    if sort_order == "desc":
        query = query.order_by(sort_column.desc())
    else:
        query = query.order_by(sort_column.asc())

    # Apply pagination
    offset = (page - 1) * size
    query = query.offset(offset).limit(size)

    result = await db.execute(query)
    products = result.scalars().all()

    # Get stock information for all products from D2C channel inventory
    product_ids = [p.id for p in products]

    # Try to get D2C channel first for channel-specific inventory
    d2c_channel_result = await db.execute(
        select(SalesChannel).where(
            or_(
                SalesChannel.code == "D2C",
                SalesChannel.channel_type == "D2C",
                SalesChannel.channel_type == "D2C_WEBSITE",
            ),
            SalesChannel.status == "ACTIVE",
        ).order_by(SalesChannel.created_at)
    )
    d2c_channel = d2c_channel_result.scalars().first()

    stock_map = {}

    if d2c_channel and getattr(settings, 'CHANNEL_INVENTORY_ENABLED', True):
        # Use channel-specific inventory (new behavior)
        # Available = allocated - buffer - reserved
        channel_stock_query = (
            select(
                ChannelInventory.product_id,
                func.sum(
                    func.greatest(
                        0,
                        func.coalesce(ChannelInventory.allocated_quantity, 0) -
                        func.coalesce(ChannelInventory.buffer_quantity, 0) -
                        func.coalesce(ChannelInventory.reserved_quantity, 0)
                    )
                ).label('total_available')
            )
            .where(
                ChannelInventory.channel_id == d2c_channel.id,
                ChannelInventory.product_id.in_(product_ids),
                ChannelInventory.is_active == True,
            )
            .group_by(ChannelInventory.product_id)
        )
        channel_result = await db.execute(channel_stock_query)
        stock_map = {row.product_id: row.total_available or 0 for row in channel_result.all()}

        # Fallback: For products NOT in channel inventory, use shared pool (InventorySummary)
        # This enables gradual migration - products without channel allocation use shared pool
        products_with_channel_inv = set(stock_map.keys())
        products_without_channel_inv = [pid for pid in product_ids if pid not in products_with_channel_inv]

        if products_without_channel_inv:
            fallback_query = (
                select(
                    InventorySummary.product_id,
                    func.sum(InventorySummary.available_quantity).label('total_available')
                )
                .where(InventorySummary.product_id.in_(products_without_channel_inv))
                .group_by(InventorySummary.product_id)
            )
            fallback_result = await db.execute(fallback_query)
            for row in fallback_result.all():
                stock_map[row.product_id] = row.total_available or 0
    else:
        # Fallback to legacy behavior (shared pool)
        stock_query = (
            select(
                InventorySummary.product_id,
                func.sum(InventorySummary.available_quantity).label('total_available')
            )
            .where(InventorySummary.product_id.in_(product_ids))
            .group_by(InventorySummary.product_id)
        )
        stock_result = await db.execute(stock_query)
        stock_map = {row.product_id: row.total_available or 0 for row in stock_result.all()}

    # Transform to response
    items = []
    for p in products:
        images = [
            StorefrontProductImage(
                id=str(img.id),
                image_url=img.image_url,
                thumbnail_url=img.thumbnail_url,
                alt_text=img.alt_text,
                is_primary=img.is_primary,
                sort_order=img.sort_order or 0,
            )
            for img in (p.images or [])
        ]
        # Get stock quantity from pre-fetched map
        stock_qty = stock_map.get(p.id, 0)
        items.append(StorefrontProductResponse(
            id=str(p.id),
            name=p.name,
            slug=p.slug,
            sku=p.sku,
            short_description=p.short_description,
            description=p.description,
            mrp=float(p.mrp) if p.mrp else 0,
            selling_price=float(p.selling_price) if p.selling_price else None,
            category_id=str(p.category_id) if p.category_id else None,
            category_name=p.category.name if p.category else None,
            brand_id=str(p.brand_id) if p.brand_id else None,
            brand_name=p.brand.name if p.brand else None,
            warranty_months=p.warranty_months or 12,
            is_featured=p.is_featured or False,
            is_bestseller=p.is_bestseller or False,
            is_new_arrival=p.is_new_arrival or False,
            images=images,
            in_stock=stock_qty > 0,
            stock_quantity=stock_qty,
        ))

    pages = (total + size - 1) // size

    result_data = PaginatedProductsResponse(
        items=items,
        total=total,
        page=page,
        size=size,
        pages=pages,
    )

    # Cache the result
    await cache.set_product_list(cache_params, result_data.model_dump())

    response.headers["X-Cache"] = "MISS"
    response.headers["X-Response-Time"] = f"{(time.time() - start_time) * 1000:.2f}ms"
    return result_data


@router.get("/products/{slug}", response_model=StorefrontProductResponse)
async def get_product_by_slug(slug: str, db: DB, response: Response):
    """
    Get a single product by slug for the public storefront.
    No authentication required. Cached for 5 minutes.
    """
    start_time = time.time()
    cache = get_cache()

    # Try to get from cache using slug as key
    cache_key = f"product:slug:{slug}"
    cached_product = await cache.get(cache_key)
    if cached_product:
        response.headers["X-Cache"] = "HIT"
        response.headers["X-Response-Time"] = f"{(time.time() - start_time) * 1000:.2f}ms"
        return StorefrontProductResponse(**cached_product)

    query = (
        select(Product)
        .options(selectinload(Product.images))
        .options(selectinload(Product.category))
        .options(selectinload(Product.brand))
        .options(selectinload(Product.variants))
        .options(selectinload(Product.specifications))
        .options(selectinload(Product.documents))
        .where(Product.slug == slug, Product.is_active == True)
    )
    result = await db.execute(query)
    product = result.scalar_one_or_none()

    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    images = [
        StorefrontProductImage(
            id=str(img.id),
            image_url=img.image_url,
            thumbnail_url=img.thumbnail_url,
            alt_text=img.alt_text,
            is_primary=img.is_primary,
            sort_order=img.sort_order or 0,
        )
        for img in (product.images or [])
    ]

    # Build variants list
    variants = [
        StorefrontProductVariant(
            id=str(v.id),
            name=v.name,
            sku=v.sku,
            attributes=v.attributes,
            mrp=float(v.mrp) if v.mrp else None,
            selling_price=float(v.selling_price) if v.selling_price else None,
            stock_quantity=v.stock_quantity,
            image_url=v.image_url,
            is_active=v.is_active,
        )
        for v in (product.variants or []) if v.is_active
    ]

    # Build specifications list
    specifications = [
        StorefrontProductSpecification(
            id=str(s.id),
            group_name=s.group_name,
            key=s.key,
            value=s.value,
            sort_order=s.sort_order or 0,
        )
        for s in (product.specifications or [])
    ]

    # Build documents list
    documents = [
        StorefrontProductDocument(
            id=str(d.id),
            title=d.title,
            document_type=d.document_type,
            file_url=d.file_url,
            file_size_bytes=d.file_size_bytes,
        )
        for d in (product.documents or [])
    ]

    # Get stock quantity for this product from D2C channel inventory
    d2c_channel_result = await db.execute(
        select(SalesChannel).where(
            or_(
                SalesChannel.code == "D2C",
                SalesChannel.channel_type == "D2C",
                SalesChannel.channel_type == "D2C_WEBSITE",
            ),
            SalesChannel.status == "ACTIVE",
        ).order_by(SalesChannel.created_at)
    )
    d2c_channel = d2c_channel_result.scalars().first()

    stock_qty = 0

    if d2c_channel and getattr(settings, 'CHANNEL_INVENTORY_ENABLED', True):
        # Use channel-specific inventory
        channel_stock_query = (
            select(
                func.sum(
                    func.greatest(
                        0,
                        func.coalesce(ChannelInventory.allocated_quantity, 0) -
                        func.coalesce(ChannelInventory.buffer_quantity, 0) -
                        func.coalesce(ChannelInventory.reserved_quantity, 0)
                    )
                ).label('total_available')
            )
            .where(
                ChannelInventory.channel_id == d2c_channel.id,
                ChannelInventory.product_id == product.id,
                ChannelInventory.is_active == True,
            )
        )
        channel_result = await db.execute(channel_stock_query)
        channel_qty = channel_result.scalar()

        if channel_qty is not None and channel_qty > 0:
            stock_qty = channel_qty
        else:
            # Fallback: Product not in channel inventory, use shared pool
            fallback_query = (
                select(func.sum(InventorySummary.available_quantity).label('total_available'))
                .where(InventorySummary.product_id == product.id)
            )
            fallback_result = await db.execute(fallback_query)
            stock_qty = fallback_result.scalar() or 0
    else:
        # Fallback to legacy behavior
        stock_query = (
            select(func.sum(InventorySummary.available_quantity).label('total_available'))
            .where(InventorySummary.product_id == product.id)
        )
        stock_result = await db.execute(stock_query)
        stock_qty = stock_result.scalar() or 0

    # Calculate discount percentage
    discount_pct = None
    if product.mrp and product.selling_price and product.mrp > 0:
        discount_pct = round(((float(product.mrp) - float(product.selling_price)) / float(product.mrp)) * 100, 1)

    result_data = StorefrontProductResponse(
        id=str(product.id),
        name=product.name,
        slug=product.slug,
        sku=product.sku,
        short_description=product.short_description,
        description=product.description,
        features=product.features,
        mrp=float(product.mrp) if product.mrp else 0,
        selling_price=float(product.selling_price) if product.selling_price else None,
        discount_percentage=discount_pct,
        gst_rate=float(product.gst_rate) if product.gst_rate else None,
        hsn_code=product.hsn_code,
        category_id=str(product.category_id) if product.category_id else None,
        category_name=product.category.name if product.category else None,
        brand_id=str(product.brand_id) if product.brand_id else None,
        brand_name=product.brand.name if product.brand else None,
        warranty_months=product.warranty_months or 12,
        warranty_type=product.warranty_terms,
        is_featured=product.is_featured or False,
        is_bestseller=product.is_bestseller or False,
        is_new_arrival=product.is_new_arrival or False,
        images=images,
        variants=variants,
        specifications=specifications,
        documents=documents,
        in_stock=stock_qty > 0,
        stock_quantity=stock_qty,
    )

    # Cache the result
    await cache.set(cache_key, result_data.model_dump(), ttl=settings.PRODUCT_CACHE_TTL)

    response.headers["X-Cache"] = "MISS"
    response.headers["X-Response-Time"] = f"{(time.time() - start_time) * 1000:.2f}ms"
    return result_data


# ==================== Categories Endpoint ====================

@router.get("/categories", response_model=List[StorefrontCategoryResponse])
async def list_categories(db: DB, response: Response):
    """
    List all active categories for the public storefront as a tree structure.
    Includes product count for each category (for mega menu).
    No authentication required. Cached for 30 minutes.
    """
    start_time = time.time()
    cache = get_cache()

    # Try to get from cache
    cache_key = "categories:all"
    cached_categories = await cache.get(cache_key)
    if cached_categories:
        response.headers["X-Cache"] = "HIT"
        response.headers["X-Response-Time"] = f"{(time.time() - start_time) * 1000:.2f}ms"
        return [StorefrontCategoryResponse(**c) for c in cached_categories]

    # Fetch categories with product count in a single query
    query = (
        select(
            Category,
            func.count(Product.id).filter(Product.is_active == True).label('product_count')
        )
        .outerjoin(Product, Product.category_id == Category.id)
        .where(Category.is_active == True)
        .group_by(Category.id)
        .order_by(Category.sort_order.asc(), Category.name.asc())
    )
    result = await db.execute(query)
    categories_with_counts = result.all()

    # Build category tree with children
    category_map = {}
    root_categories = []

    # First pass: create all category objects with product counts
    for row in categories_with_counts:
        c = row.Category
        product_count = row.product_count or 0
        cat_response = StorefrontCategoryResponse(
            id=str(c.id),
            name=c.name,
            slug=c.slug,
            description=c.description,
            image_url=c.image_url,
            icon=c.icon,
            parent_id=str(c.parent_id) if c.parent_id else None,
            is_active=c.is_active,
            is_featured=c.is_featured or False,
            product_count=product_count,
            children=[],
        )
        category_map[str(c.id)] = {"obj": cat_response, "parent_id": str(c.parent_id) if c.parent_id else None}

    # Second pass: build tree structure
    for cat_id, cat_data in category_map.items():
        if cat_data["parent_id"] and cat_data["parent_id"] in category_map:
            # Add as child to parent
            parent = category_map[cat_data["parent_id"]]["obj"]
            parent.children.append(cat_data["obj"])
        else:
            # Root category
            root_categories.append(cat_data["obj"])

    result_data = root_categories

    # Cache the result
    await cache.set(cache_key, [r.model_dump() for r in result_data], ttl=settings.CATEGORY_CACHE_TTL)

    response.headers["X-Cache"] = "MISS"
    response.headers["X-Response-Time"] = f"{(time.time() - start_time) * 1000:.2f}ms"
    return result_data


# ==================== Brands Endpoint ====================

@router.get("/brands", response_model=List[StorefrontBrandResponse])
async def list_brands(db: DB, response: Response):
    """
    List all active brands for the public storefront.
    No authentication required. Cached for 30 minutes.
    """
    start_time = time.time()
    cache = get_cache()

    # Try to get from cache
    cache_key = "brands:all"
    cached_brands = await cache.get(cache_key)
    if cached_brands:
        response.headers["X-Cache"] = "HIT"
        response.headers["X-Response-Time"] = f"{(time.time() - start_time) * 1000:.2f}ms"
        return [StorefrontBrandResponse(**b) for b in cached_brands]

    query = (
        select(Brand)
        .where(Brand.is_active == True)
        .order_by(Brand.sort_order.asc(), Brand.name.asc())
    )
    result = await db.execute(query)
    brands = result.scalars().all()

    result_data = [
        StorefrontBrandResponse(
            id=str(b.id),
            name=b.name,
            slug=b.slug,
            description=b.description,
            logo_url=b.logo_url,
            is_active=b.is_active,
        )
        for b in brands
    ]

    # Cache the result
    await cache.set(cache_key, [r.model_dump() for r in result_data], ttl=settings.CATEGORY_CACHE_TTL)

    response.headers["X-Cache"] = "MISS"
    response.headers["X-Response-Time"] = f"{(time.time() - start_time) * 1000:.2f}ms"
    return result_data


@router.get("/company", response_model=StorefrontCompanyInfo)
async def get_storefront_company(db: DB, response: Response):
    """
    Get public company info for the storefront.
    No authentication required. Cached for 1 hour.
    """
    start_time = time.time()
    cache = get_cache()

    # Try to get from cache
    cache_key = "company:info"
    cached_company = await cache.get(cache_key)
    if cached_company:
        response.headers["X-Cache"] = "HIT"
        response.headers["X-Response-Time"] = f"{(time.time() - start_time) * 1000:.2f}ms"
        return StorefrontCompanyInfo(**cached_company)

    # Get primary company or first active company
    query = (
        select(Company)
        .where(Company.is_primary == True, Company.is_active == True)
    )
    result = await db.execute(query)
    company = result.scalar_one_or_none()

    if not company:
        # Try to get any active company
        query = (
            select(Company)
            .where(Company.is_active == True)
            .order_by(Company.created_at.asc())
        )
        result = await db.execute(query)
        company = result.scalar_one_or_none()

    if not company:
        # Return default company info if none configured
        result_data = StorefrontCompanyInfo(
            name="ILMS.AI",
            trade_name="ILMS.AI",
            logo_url=None,
            email="support@ilms.ai",
            phone="1800-123-4567",
            website="https://ilms.ai",
            address="123 Industrial Area, Sector 62",
            city="Noida",
            state="Uttar Pradesh",
            pincode="201301"
        )
    else:
        result_data = StorefrontCompanyInfo(
            name=company.legal_name,
            trade_name=company.trade_name or company.legal_name,
            logo_url=company.logo_url,
            logo_small_url=company.logo_small_url,
            favicon_url=company.favicon_url,
            email=company.email,
            phone=company.phone,
            website=company.website,
            address=company.address_line1 + (f", {company.address_line2}" if company.address_line2 else ""),
            city=company.city,
            state=company.state,
            pincode=company.pincode
        )

    # Cache the result
    await cache.set(cache_key, result_data.model_dump(), ttl=settings.COMPANY_CACHE_TTL)

    response.headers["X-Cache"] = "MISS"
    response.headers["X-Response-Time"] = f"{(time.time() - start_time) * 1000:.2f}ms"
    return result_data


# ==================== Search Suggestions Endpoint ====================

@router.get("/search/suggestions", response_model=SearchSuggestionsResponse)
async def get_search_suggestions(
    db: DB,
    q: str = Query(..., min_length=2, max_length=100, description="Search query"),
    limit: int = Query(default=6, ge=1, le=10, description="Max results per category"),
):
    """
    Get search suggestions for autocomplete.
    Returns matching products, categories, and brands.
    No authentication required.
    """
    search_term = f"%{q.lower()}%"

    # Search products
    products_query = (
        select(Product)
        .options(selectinload(Product.images))
        .where(
            Product.is_active == True,
            or_(
                func.lower(Product.name).like(search_term),
                func.lower(Product.sku).like(search_term),
            )
        )
        .order_by(Product.is_bestseller.desc(), Product.name.asc())
        .limit(limit)
    )
    products_result = await db.execute(products_query)
    products = products_result.scalars().all()

    product_suggestions = []
    for p in products:
        primary_image = next(
            (img for img in (p.images or []) if img.is_primary),
            (p.images[0] if p.images else None)
        )
        product_suggestions.append(SearchProductSuggestion(
            id=str(p.id),
            name=p.name,
            slug=p.slug,
            image_url=primary_image.image_url if primary_image else None,
            price=float(p.selling_price) if p.selling_price else float(p.mrp),
            mrp=float(p.mrp) if p.mrp else 0,
        ))

    # Search categories
    categories_query = (
        select(Category, func.count(Product.id).label('product_count'))
        .outerjoin(Product, Product.category_id == Category.id)
        .where(
            Category.is_active == True,
            func.lower(Category.name).like(search_term)
        )
        .group_by(Category.id)
        .order_by(func.count(Product.id).desc())
        .limit(limit)
    )
    categories_result = await db.execute(categories_query)
    categories = categories_result.all()

    category_suggestions = [
        SearchCategorySuggestion(
            id=str(c.Category.id),
            name=c.Category.name,
            slug=c.Category.slug,
            image_url=c.Category.image_url,
            product_count=c.product_count or 0,
        )
        for c in categories
    ]

    # Search brands
    brands_query = (
        select(Brand)
        .where(
            Brand.is_active == True,
            func.lower(Brand.name).like(search_term)
        )
        .order_by(Brand.sort_order.asc(), Brand.name.asc())
        .limit(limit)
    )
    brands_result = await db.execute(brands_query)
    brands = brands_result.scalars().all()

    brand_suggestions = [
        SearchBrandSuggestion(
            id=str(b.id),
            name=b.name,
            slug=b.slug,
            logo_url=b.logo_url,
        )
        for b in brands
    ]

    return SearchSuggestionsResponse(
        products=product_suggestions,
        categories=category_suggestions,
        brands=brand_suggestions,
        query=q,
    )


# ==================== Serviceability Endpoint ====================

@router.get("/serviceability/{pincode}", response_model=ServiceabilityCheckResponse)
async def check_serviceability(
    pincode: str,
    db: DB,
    response: Response,
):
    """
    Check if a pincode is serviceable for delivery.
    No authentication required. Cached for 30 minutes.

    Returns serviceability status, COD availability, estimated delivery days,
    and available warehouse/transporter options.
    """
    start_time = time.time()
    cache = get_cache()

    # Validate pincode format (6 digits for India)
    if not pincode or len(pincode) != 6 or not pincode.isdigit():
        raise HTTPException(
            status_code=400,
            detail="Invalid pincode format. Must be 6 digits."
        )

    # Try to get from cache
    cache_key = f"serviceability:d2c:{pincode}"
    cached_result = await cache.get(cache_key)
    if cached_result:
        response.headers["X-Cache"] = "HIT"
        response.headers["X-Response-Time"] = f"{(time.time() - start_time) * 1000:.2f}ms"
        return ServiceabilityCheckResponse(**cached_result)

    # Check serviceability
    service = ServiceabilityService(db)
    request = ServiceabilityCheckRequest(
        pincode=pincode,
        channel_code="D2C"
    )

    result = await service.check_serviceability(request)

    # Cache the result (30 minutes)
    await cache.set(cache_key, result.model_dump(), ttl=1800)

    response.headers["X-Cache"] = "MISS"
    response.headers["X-Response-Time"] = f"{(time.time() - start_time) * 1000:.2f}ms"
    return result


# ==================== CMS Content Endpoints ====================

from app.models.cms import (
    CMSBanner, CMSUsp, CMSTestimonial, CMSAnnouncement, CMSPage,
    CMSSiteSetting, CMSMenuItem, CMSFeatureBar, CMSMegaMenuItem,
    CMSFaqCategory, CMSFaqItem,
)
from app.schemas.cms import (
    StorefrontBannerResponse,
    StorefrontUspResponse,
    StorefrontTestimonialResponse,
    StorefrontAnnouncementResponse,
    StorefrontPageResponse,
    StorefrontSettingsResponse,
    StorefrontMenuItemResponse,
    StorefrontFeatureBarResponse,
    StorefrontMegaMenuItemResponse,
    StorefrontSubcategoryResponse,
    StorefrontFaqResponse,
    StorefrontFaqCategoryResponse,
    StorefrontFaqItemResponse,
)


@router.get("/banners", response_model=List[StorefrontBannerResponse])
async def get_banners(db: DB, response: Response):
    """
    Get active hero banners for the storefront.
    Respects scheduling (starts_at, ends_at).
    No authentication required. Cached for 5 minutes.
    """
    start_time = time.time()
    cache = get_cache()

    cache_key = "cms:banners:active"
    cached_result = await cache.get(cache_key)
    if cached_result:
        response.headers["X-Cache"] = "HIT"
        response.headers["X-Response-Time"] = f"{(time.time() - start_time) * 1000:.2f}ms"
        return [StorefrontBannerResponse(**b) for b in cached_result]

    now = func.now()
    query = (
        select(CMSBanner)
        .where(
            CMSBanner.is_active == True,
            or_(CMSBanner.starts_at.is_(None), CMSBanner.starts_at <= now),
            or_(CMSBanner.ends_at.is_(None), CMSBanner.ends_at >= now),
        )
        .order_by(CMSBanner.sort_order.asc())
    )

    result = await db.execute(query)
    banners = result.scalars().all()

    result_data = [
        StorefrontBannerResponse(
            id=str(b.id),
            title=b.title,
            subtitle=b.subtitle,
            image_url=b.image_url,
            mobile_image_url=b.mobile_image_url,
            cta_text=b.cta_text,
            cta_link=b.cta_link,
            text_position=b.text_position,
            text_color=b.text_color,
        )
        for b in banners
    ]

    await cache.set(cache_key, [r.model_dump() for r in result_data], ttl=300)

    response.headers["X-Cache"] = "MISS"
    response.headers["X-Response-Time"] = f"{(time.time() - start_time) * 1000:.2f}ms"
    return result_data


@router.get("/usps", response_model=List[StorefrontUspResponse])
async def get_usps(db: DB, response: Response):
    """
    Get active USPs/features for the storefront.
    No authentication required. Cached for 10 minutes.
    """
    start_time = time.time()
    cache = get_cache()

    cache_key = "cms:usps:active"
    cached_result = await cache.get(cache_key)
    if cached_result:
        response.headers["X-Cache"] = "HIT"
        response.headers["X-Response-Time"] = f"{(time.time() - start_time) * 1000:.2f}ms"
        return [StorefrontUspResponse(**u) for u in cached_result]

    query = (
        select(CMSUsp)
        .where(CMSUsp.is_active == True)
        .order_by(CMSUsp.sort_order.asc())
    )

    result = await db.execute(query)
    usps = result.scalars().all()

    result_data = [
        StorefrontUspResponse(
            id=str(u.id),
            title=u.title,
            description=u.description,
            icon=u.icon,
            icon_color=u.icon_color,
            link_url=u.link_url,
            link_text=u.link_text,
        )
        for u in usps
    ]

    await cache.set(cache_key, [r.model_dump() for r in result_data], ttl=600)

    response.headers["X-Cache"] = "MISS"
    response.headers["X-Response-Time"] = f"{(time.time() - start_time) * 1000:.2f}ms"
    return result_data


@router.get("/testimonials", response_model=List[StorefrontTestimonialResponse])
async def get_testimonials(
    db: DB,
    response: Response,
    limit: int = Query(default=10, ge=1, le=50),
):
    """
    Get active testimonials for the storefront.
    Featured testimonials appear first.
    No authentication required. Cached for 10 minutes.
    """
    start_time = time.time()
    cache = get_cache()

    cache_key = f"cms:testimonials:active:{limit}"
    cached_result = await cache.get(cache_key)
    if cached_result:
        response.headers["X-Cache"] = "HIT"
        response.headers["X-Response-Time"] = f"{(time.time() - start_time) * 1000:.2f}ms"
        return [StorefrontTestimonialResponse(**t) for t in cached_result]

    query = (
        select(CMSTestimonial)
        .where(CMSTestimonial.is_active == True)
        .order_by(
            CMSTestimonial.is_featured.desc(),
            CMSTestimonial.sort_order.asc()
        )
        .limit(limit)
    )

    result = await db.execute(query)
    testimonials = result.scalars().all()

    result_data = [
        StorefrontTestimonialResponse(
            id=str(t.id),
            customer_name=t.customer_name,
            customer_location=t.customer_location,
            customer_avatar_url=t.customer_avatar_url,
            customer_designation=t.customer_designation,
            rating=t.rating,
            content=t.content,
            title=t.title,
            product_name=t.product_name,
        )
        for t in testimonials
    ]

    await cache.set(cache_key, [r.model_dump() for r in result_data], ttl=600)

    response.headers["X-Cache"] = "MISS"
    response.headers["X-Response-Time"] = f"{(time.time() - start_time) * 1000:.2f}ms"
    return result_data


@router.get("/announcements/active", response_model=Optional[StorefrontAnnouncementResponse])
async def get_active_announcement(db: DB, response: Response):
    """
    Get the current active announcement for the header bar.
    Returns the first active, scheduled announcement.
    No authentication required. Cached for 2 minutes.
    """
    start_time = time.time()
    cache = get_cache()

    cache_key = "cms:announcement:active"
    cached_result = await cache.get(cache_key)
    if cached_result:
        response.headers["X-Cache"] = "HIT"
        response.headers["X-Response-Time"] = f"{(time.time() - start_time) * 1000:.2f}ms"
        if cached_result == "none":
            return None
        return StorefrontAnnouncementResponse(**cached_result)

    now = func.now()
    query = (
        select(CMSAnnouncement)
        .where(
            CMSAnnouncement.is_active == True,
            or_(CMSAnnouncement.starts_at.is_(None), CMSAnnouncement.starts_at <= now),
            or_(CMSAnnouncement.ends_at.is_(None), CMSAnnouncement.ends_at >= now),
        )
        .order_by(CMSAnnouncement.sort_order.asc())
        .limit(1)
    )

    result = await db.execute(query)
    announcement = result.scalar_one_or_none()

    if not announcement:
        await cache.set(cache_key, "none", ttl=120)
        response.headers["X-Cache"] = "MISS"
        response.headers["X-Response-Time"] = f"{(time.time() - start_time) * 1000:.2f}ms"
        return None

    result_data = StorefrontAnnouncementResponse(
        id=str(announcement.id),
        text=announcement.text,
        link_url=announcement.link_url,
        link_text=announcement.link_text,
        announcement_type=announcement.announcement_type,
        background_color=announcement.background_color,
        text_color=announcement.text_color,
        is_dismissible=announcement.is_dismissible,
    )

    await cache.set(cache_key, result_data.model_dump(), ttl=120)

    response.headers["X-Cache"] = "MISS"
    response.headers["X-Response-Time"] = f"{(time.time() - start_time) * 1000:.2f}ms"
    return result_data


@router.get("/pages/{slug}", response_model=StorefrontPageResponse)
async def get_page_by_slug(slug: str, db: DB, response: Response):
    """
    Get a published page by slug.
    No authentication required. Cached for 5 minutes.
    """
    start_time = time.time()
    cache = get_cache()

    cache_key = f"cms:page:{slug}"
    cached_result = await cache.get(cache_key)
    if cached_result:
        response.headers["X-Cache"] = "HIT"
        response.headers["X-Response-Time"] = f"{(time.time() - start_time) * 1000:.2f}ms"
        return StorefrontPageResponse(**cached_result)

    query = (
        select(CMSPage)
        .where(
            CMSPage.slug == slug,
            CMSPage.status == "PUBLISHED",
        )
    )

    result = await db.execute(query)
    page = result.scalar_one_or_none()

    if not page:
        raise HTTPException(status_code=404, detail="Page not found")

    result_data = StorefrontPageResponse(
        id=str(page.id),
        title=page.title,
        slug=page.slug,
        content=page.content,
        excerpt=page.excerpt,
        meta_title=page.meta_title,
        meta_description=page.meta_description,
        og_image_url=page.og_image_url,
        template=page.template,
        published_at=page.published_at,
    )

    await cache.set(cache_key, result_data.model_dump(), ttl=300)

    response.headers["X-Cache"] = "MISS"
    response.headers["X-Response-Time"] = f"{(time.time() - start_time) * 1000:.2f}ms"
    return result_data


@router.get("/footer-pages", response_model=List[dict])
async def get_footer_pages(db: DB, response: Response):
    """
    Get list of published pages that should appear in the footer.
    No authentication required. Cached for 30 minutes.
    """
    start_time = time.time()
    cache = get_cache()

    cache_key = "cms:pages:footer"
    cached_result = await cache.get(cache_key)
    if cached_result:
        response.headers["X-Cache"] = "HIT"
        response.headers["X-Response-Time"] = f"{(time.time() - start_time) * 1000:.2f}ms"
        return cached_result

    query = (
        select(CMSPage)
        .where(
            CMSPage.status == "PUBLISHED",
            CMSPage.show_in_footer == True,
        )
        .order_by(CMSPage.sort_order.asc())
    )

    result = await db.execute(query)
    pages = result.scalars().all()

    result_data = [
        {"title": p.title, "slug": p.slug}
        for p in pages
    ]

    await cache.set(cache_key, result_data, ttl=1800)

    response.headers["X-Cache"] = "MISS"
    response.headers["X-Response-Time"] = f"{(time.time() - start_time) * 1000:.2f}ms"
    return result_data


@router.get("/settings", response_model=dict)
async def get_site_settings(
    db: DB,
    response: Response,
    group: Optional[str] = Query(default=None, description="Filter by setting group"),
):
    """
    Get public site settings (social media links, contact info, etc.).
    No authentication required. Cached for 30 minutes.
    """
    start_time = time.time()
    cache = get_cache()

    cache_key = f"cms:settings:{group or 'all'}"
    cached_result = await cache.get(cache_key)
    if cached_result:
        response.headers["X-Cache"] = "HIT"
        response.headers["X-Response-Time"] = f"{(time.time() - start_time) * 1000:.2f}ms"
        return cached_result

    query = select(CMSSiteSetting).order_by(CMSSiteSetting.sort_order.asc())
    if group:
        query = query.where(CMSSiteSetting.setting_group == group)

    result = await db.execute(query)
    settings = result.scalars().all()

    # Return as key-value pairs
    result_data = {s.setting_key: s.setting_value for s in settings}

    await cache.set(cache_key, result_data, ttl=1800)

    response.headers["X-Cache"] = "MISS"
    response.headers["X-Response-Time"] = f"{(time.time() - start_time) * 1000:.2f}ms"
    return result_data


@router.get("/menu-items", response_model=List[StorefrontMenuItemResponse])
async def get_menu_items(
    db: DB,
    response: Response,
    location: Optional[str] = Query(default=None, description="Filter by location (header, footer_quick, footer_service)"),
):
    """
    Get navigation menu items for header and footer.
    No authentication required. Cached for 30 minutes.
    """
    start_time = time.time()
    cache = get_cache()

    cache_key = f"cms:menu:{location or 'all'}"
    cached_result = await cache.get(cache_key)
    if cached_result:
        response.headers["X-Cache"] = "HIT"
        response.headers["X-Response-Time"] = f"{(time.time() - start_time) * 1000:.2f}ms"
        return [StorefrontMenuItemResponse(**m) for m in cached_result]

    query = (
        select(CMSMenuItem)
        .where(
            CMSMenuItem.is_active == True,
            CMSMenuItem.parent_id.is_(None),  # Only top-level items
        )
        .order_by(CMSMenuItem.sort_order.asc())
    )

    if location:
        query = query.where(CMSMenuItem.menu_location == location)

    result = await db.execute(query)
    menu_items = result.scalars().all()

    # Get all child items
    parent_ids = [str(m.id) for m in menu_items]
    children_query = (
        select(CMSMenuItem)
        .where(
            CMSMenuItem.is_active == True,
            CMSMenuItem.parent_id.in_([m.id for m in menu_items]) if menu_items else False,
        )
        .order_by(CMSMenuItem.sort_order.asc())
    )

    children_result = await db.execute(children_query)
    children = children_result.scalars().all()

    # Group children by parent
    children_map = {}
    for child in children:
        parent_id = str(child.parent_id)
        if parent_id not in children_map:
            children_map[parent_id] = []
        children_map[parent_id].append(StorefrontMenuItemResponse(
            id=str(child.id),
            menu_location=child.menu_location,
            title=child.title,
            url=child.url,
            icon=child.icon,
            target=child.target,
            children=[],
        ))

    result_data = [
        StorefrontMenuItemResponse(
            id=str(m.id),
            menu_location=m.menu_location,
            title=m.title,
            url=m.url,
            icon=m.icon,
            target=m.target,
            children=children_map.get(str(m.id), []),
        )
        for m in menu_items
    ]

    await cache.set(cache_key, [r.model_dump() for r in result_data], ttl=1800)

    response.headers["X-Cache"] = "MISS"
    response.headers["X-Response-Time"] = f"{(time.time() - start_time) * 1000:.2f}ms"
    return result_data


@router.get("/feature-bars", response_model=List[StorefrontFeatureBarResponse])
async def get_feature_bars(db: DB, response: Response):
    """
    Get feature bar items (Free Shipping, Secure Payment, etc.) for footer.
    No authentication required. Cached for 30 minutes.
    """
    start_time = time.time()
    cache = get_cache()

    cache_key = "cms:feature-bars:active"
    cached_result = await cache.get(cache_key)
    if cached_result:
        response.headers["X-Cache"] = "HIT"
        response.headers["X-Response-Time"] = f"{(time.time() - start_time) * 1000:.2f}ms"
        return [StorefrontFeatureBarResponse(**f) for f in cached_result]

    query = (
        select(CMSFeatureBar)
        .where(CMSFeatureBar.is_active == True)
        .order_by(CMSFeatureBar.sort_order.asc())
    )

    result = await db.execute(query)
    feature_bars = result.scalars().all()

    result_data = [
        StorefrontFeatureBarResponse(
            id=str(f.id),
            icon=f.icon,
            title=f.title,
            subtitle=f.subtitle,
        )
        for f in feature_bars
    ]

    await cache.set(cache_key, [r.model_dump() for r in result_data], ttl=1800)

    response.headers["X-Cache"] = "MISS"
    response.headers["X-Response-Time"] = f"{(time.time() - start_time) * 1000:.2f}ms"
    return result_data


# ==================== Composite Homepage Endpoint ====================

import asyncio
from pydantic import BaseModel


class HomepageDataResponse(BaseModel):
    """Composite response for homepage - all data in single request."""
    categories: List[StorefrontCategoryResponse]
    featured_products: List[StorefrontProductResponse]
    bestseller_products: List[StorefrontProductResponse]
    new_arrivals: List[StorefrontProductResponse]
    banners: List[StorefrontBannerResponse]
    brands: List[StorefrontBrandResponse]
    usps: List[StorefrontUspResponse]
    testimonials: List[StorefrontTestimonialResponse]


async def _get_featured_products(db, limit: int = 8):
    """Helper to get featured products with stock."""
    query = (
        select(Product)
        .options(selectinload(Product.images))
        .options(selectinload(Product.category))
        .options(selectinload(Product.brand))
        .where(Product.is_active == True, Product.is_featured == True)
        .order_by(Product.created_at.desc())
        .limit(limit)
    )
    result = await db.execute(query)
    products = result.scalars().all()

    # Batch get stock
    product_ids = [p.id for p in products]
    if product_ids:
        stock_query = (
            select(
                InventorySummary.product_id,
                func.sum(InventorySummary.available_quantity).label('total_available')
            )
            .where(InventorySummary.product_id.in_(product_ids))
            .group_by(InventorySummary.product_id)
        )
        stock_result = await db.execute(stock_query)
        stock_map = {row.product_id: row.total_available or 0 for row in stock_result.all()}
    else:
        stock_map = {}

    return [
        StorefrontProductResponse(
            id=str(p.id),
            name=p.name,
            slug=p.slug,
            sku=p.sku,
            short_description=p.short_description,
            mrp=float(p.mrp) if p.mrp else 0,
            selling_price=float(p.selling_price) if p.selling_price else None,
            category_id=str(p.category_id) if p.category_id else None,
            category_name=p.category.name if p.category else None,
            brand_id=str(p.brand_id) if p.brand_id else None,
            brand_name=p.brand.name if p.brand else None,
            is_featured=True,
            is_bestseller=p.is_bestseller or False,
            is_new_arrival=p.is_new_arrival or False,
            images=[
                StorefrontProductImage(
                    id=str(img.id),
                    image_url=img.image_url,
                    thumbnail_url=img.thumbnail_url,
                    alt_text=img.alt_text,
                    is_primary=img.is_primary,
                    sort_order=img.sort_order or 0,
                )
                for img in (p.images or [])
            ],
            in_stock=stock_map.get(p.id, 0) > 0,
            stock_quantity=stock_map.get(p.id, 0),
        )
        for p in products
    ]


async def _get_bestseller_products(db, limit: int = 8):
    """Helper to get bestseller products with stock."""
    query = (
        select(Product)
        .options(selectinload(Product.images))
        .options(selectinload(Product.category))
        .options(selectinload(Product.brand))
        .where(Product.is_active == True, Product.is_bestseller == True)
        .order_by(Product.created_at.desc())
        .limit(limit)
    )
    result = await db.execute(query)
    products = result.scalars().all()

    product_ids = [p.id for p in products]
    if product_ids:
        stock_query = (
            select(
                InventorySummary.product_id,
                func.sum(InventorySummary.available_quantity).label('total_available')
            )
            .where(InventorySummary.product_id.in_(product_ids))
            .group_by(InventorySummary.product_id)
        )
        stock_result = await db.execute(stock_query)
        stock_map = {row.product_id: row.total_available or 0 for row in stock_result.all()}
    else:
        stock_map = {}

    return [
        StorefrontProductResponse(
            id=str(p.id),
            name=p.name,
            slug=p.slug,
            sku=p.sku,
            short_description=p.short_description,
            mrp=float(p.mrp) if p.mrp else 0,
            selling_price=float(p.selling_price) if p.selling_price else None,
            category_id=str(p.category_id) if p.category_id else None,
            category_name=p.category.name if p.category else None,
            brand_id=str(p.brand_id) if p.brand_id else None,
            brand_name=p.brand.name if p.brand else None,
            is_featured=p.is_featured or False,
            is_bestseller=True,
            is_new_arrival=p.is_new_arrival or False,
            images=[
                StorefrontProductImage(
                    id=str(img.id),
                    image_url=img.image_url,
                    thumbnail_url=img.thumbnail_url,
                    alt_text=img.alt_text,
                    is_primary=img.is_primary,
                    sort_order=img.sort_order or 0,
                )
                for img in (p.images or [])
            ],
            in_stock=stock_map.get(p.id, 0) > 0,
            stock_quantity=stock_map.get(p.id, 0),
        )
        for p in products
    ]


async def _get_new_arrival_products(db, limit: int = 8):
    """Helper to get new arrival products with stock."""
    query = (
        select(Product)
        .options(selectinload(Product.images))
        .options(selectinload(Product.category))
        .options(selectinload(Product.brand))
        .where(Product.is_active == True, Product.is_new_arrival == True)
        .order_by(Product.created_at.desc())
        .limit(limit)
    )
    result = await db.execute(query)
    products = result.scalars().all()

    product_ids = [p.id for p in products]
    if product_ids:
        stock_query = (
            select(
                InventorySummary.product_id,
                func.sum(InventorySummary.available_quantity).label('total_available')
            )
            .where(InventorySummary.product_id.in_(product_ids))
            .group_by(InventorySummary.product_id)
        )
        stock_result = await db.execute(stock_query)
        stock_map = {row.product_id: row.total_available or 0 for row in stock_result.all()}
    else:
        stock_map = {}

    return [
        StorefrontProductResponse(
            id=str(p.id),
            name=p.name,
            slug=p.slug,
            sku=p.sku,
            short_description=p.short_description,
            mrp=float(p.mrp) if p.mrp else 0,
            selling_price=float(p.selling_price) if p.selling_price else None,
            category_id=str(p.category_id) if p.category_id else None,
            category_name=p.category.name if p.category else None,
            brand_id=str(p.brand_id) if p.brand_id else None,
            brand_name=p.brand.name if p.brand else None,
            is_featured=p.is_featured or False,
            is_bestseller=p.is_bestseller or False,
            is_new_arrival=True,
            images=[
                StorefrontProductImage(
                    id=str(img.id),
                    image_url=img.image_url,
                    thumbnail_url=img.thumbnail_url,
                    alt_text=img.alt_text,
                    is_primary=img.is_primary,
                    sort_order=img.sort_order or 0,
                )
                for img in (p.images or [])
            ],
            in_stock=stock_map.get(p.id, 0) > 0,
            stock_quantity=stock_map.get(p.id, 0),
        )
        for p in products
    ]


@router.get("/homepage", response_model=HomepageDataResponse)
async def get_homepage_data(db: DB, response: Response):
    """
    Get all data needed for homepage in a single API call.
    Includes: categories, featured products, bestsellers, new arrivals,
    banners, brands, USPs, and testimonials.

    This composite endpoint reduces multiple HTTP requests to just one,
    significantly improving homepage load time.

    No authentication required. Cached for 5 minutes.
    """
    start_time = time.time()
    cache = get_cache()

    # Try to get from cache
    cache_key = "storefront:homepage"
    cached_result = await cache.get(cache_key)
    if cached_result:
        response.headers["X-Cache"] = "HIT"
        response.headers["X-Response-Time"] = f"{(time.time() - start_time) * 1000:.2f}ms"
        return HomepageDataResponse(**cached_result)

    # Fetch all data in parallel using asyncio.gather
    # Categories
    async def get_categories():
        query = (
            select(
                Category,
                func.count(Product.id).filter(Product.is_active == True).label('product_count')
            )
            .outerjoin(Product, Product.category_id == Category.id)
            .where(Category.is_active == True)
            .group_by(Category.id)
            .order_by(Category.sort_order.asc(), Category.name.asc())
        )
        result = await db.execute(query)
        categories_with_counts = result.all()

        # Build tree
        category_map = {}
        root_categories = []
        for row in categories_with_counts:
            c = row.Category
            product_count = row.product_count or 0
            cat_response = StorefrontCategoryResponse(
                id=str(c.id),
                name=c.name,
                slug=c.slug,
                description=c.description,
                image_url=c.image_url,
                icon=c.icon,
                parent_id=str(c.parent_id) if c.parent_id else None,
                is_active=c.is_active,
                is_featured=c.is_featured or False,
                product_count=product_count,
                children=[],
            )
            category_map[str(c.id)] = {"obj": cat_response, "parent_id": str(c.parent_id) if c.parent_id else None}

        for cat_id, cat_data in category_map.items():
            if cat_data["parent_id"] and cat_data["parent_id"] in category_map:
                parent = category_map[cat_data["parent_id"]]["obj"]
                parent.children.append(cat_data["obj"])
            else:
                root_categories.append(cat_data["obj"])

        return root_categories

    # Brands
    async def get_brands():
        query = (
            select(Brand)
            .where(Brand.is_active == True)
            .order_by(Brand.sort_order.asc(), Brand.name.asc())
        )
        result = await db.execute(query)
        brands = result.scalars().all()
        return [
            StorefrontBrandResponse(
                id=str(b.id),
                name=b.name,
                slug=b.slug,
                description=b.description,
                logo_url=b.logo_url,
                is_active=b.is_active,
            )
            for b in brands
        ]

    # Banners
    async def get_banners():
        now = func.now()
        query = (
            select(CMSBanner)
            .where(
                CMSBanner.is_active == True,
                or_(CMSBanner.starts_at.is_(None), CMSBanner.starts_at <= now),
                or_(CMSBanner.ends_at.is_(None), CMSBanner.ends_at >= now),
            )
            .order_by(CMSBanner.sort_order.asc())
        )
        result = await db.execute(query)
        banners = result.scalars().all()
        return [
            StorefrontBannerResponse(
                id=str(b.id),
                title=b.title,
                subtitle=b.subtitle,
                image_url=b.image_url,
                mobile_image_url=b.mobile_image_url,
                cta_text=b.cta_text,
                cta_link=b.cta_link,
                text_position=b.text_position,
                text_color=b.text_color,
            )
            for b in banners
        ]

    # USPs
    async def get_usps():
        query = (
            select(CMSUsp)
            .where(CMSUsp.is_active == True)
            .order_by(CMSUsp.sort_order.asc())
        )
        result = await db.execute(query)
        usps = result.scalars().all()
        return [
            StorefrontUspResponse(
                id=str(u.id),
                title=u.title,
                description=u.description,
                icon=u.icon,
                icon_color=u.icon_color,
                link_url=u.link_url,
                link_text=u.link_text,
            )
            for u in usps
        ]

    # Testimonials
    async def get_testimonials():
        query = (
            select(CMSTestimonial)
            .where(CMSTestimonial.is_active == True)
            .order_by(CMSTestimonial.is_featured.desc(), CMSTestimonial.sort_order.asc())
            .limit(6)
        )
        result = await db.execute(query)
        testimonials = result.scalars().all()
        return [
            StorefrontTestimonialResponse(
                id=str(t.id),
                customer_name=t.customer_name,
                customer_location=t.customer_location,
                customer_avatar_url=t.customer_avatar_url,
                customer_designation=t.customer_designation,
                rating=t.rating,
                content=t.content,
                title=t.title,
                product_name=t.product_name,
            )
            for t in testimonials
        ]

    # Execute queries sequentially (SQLAlchemy async sessions don't support concurrent operations)
    # Even though sequential, this is still faster than multiple HTTP requests from frontend
    categories = await get_categories()
    featured_products = await _get_featured_products(db, limit=8)
    bestseller_products = await _get_bestseller_products(db, limit=8)
    new_arrivals = await _get_new_arrival_products(db, limit=8)
    banners = await get_banners()
    brands = await get_brands()
    usps = await get_usps()
    testimonials = await get_testimonials()

    result_data = HomepageDataResponse(
        categories=categories,
        featured_products=featured_products,
        bestseller_products=bestseller_products,
        new_arrivals=new_arrivals,
        banners=banners,
        brands=brands,
        usps=usps,
        testimonials=testimonials,
    )

    # Cache for 5 minutes
    await cache.set(cache_key, result_data.model_dump(), ttl=300)

    response.headers["X-Cache"] = "MISS"
    response.headers["X-Response-Time"] = f"{(time.time() - start_time) * 1000:.2f}ms"
    return result_data


# ==================== Mega Menu Endpoint ====================

@router.get("/mega-menu", response_model=List[StorefrontMegaMenuItemResponse])
async def get_mega_menu(db: DB, response: Response):
    """
    Get CMS-managed mega menu items for storefront navigation.
    Returns active menu items with resolved category data and subcategories.

    Unlike the categories endpoint which returns ALL categories,
    this endpoint returns only the curated navigation structure
    defined by admins in the CMS (similar to Eureka Forbes / Atomberg).

    No authentication required. Cached for 10 minutes.
    """
    start_time = time.time()
    cache = get_cache()

    cache_key = "storefront:mega-menu"
    cached_result = await cache.get(cache_key)
    if cached_result:
        response.headers["X-Cache"] = "HIT"
        response.headers["X-Response-Time"] = f"{(time.time() - start_time) * 1000:.2f}ms"
        return [StorefrontMegaMenuItemResponse(**item) for item in cached_result]

    # Fetch active mega menu items
    query = (
        select(CMSMegaMenuItem)
        .where(CMSMegaMenuItem.is_active == True)
        .order_by(CMSMegaMenuItem.sort_order.asc())
    )
    result = await db.execute(query)
    menu_items = result.scalars().all()

    # Build response with resolved category data
    response_items = []
    for item in menu_items:
        menu_response = StorefrontMegaMenuItemResponse(
            id=str(item.id),
            title=item.title,
            icon=item.icon,
            image_url=item.image_url,
            menu_type=item.menu_type,
            url=item.url,
            target=item.target,
            is_highlighted=item.is_highlighted,
            highlight_text=item.highlight_text,
            category_slug=None,
            subcategories=[],
        )

        # For CATEGORY type, resolve the category and its subcategories
        if item.menu_type == "CATEGORY" and item.category_id:
            # Get the main category
            cat_result = await db.execute(
                select(Category).where(Category.id == item.category_id)
            )
            category = cat_result.scalar_one_or_none()
            if category:
                menu_response.category_slug = category.slug

                # Determine which subcategories to show
                if item.show_subcategories:
                    if item.subcategory_ids and isinstance(item.subcategory_ids, dict):
                        # Show specific subcategories
                        specific_ids = item.subcategory_ids.get("ids", [])
                        if specific_ids:
                            # Get specific subcategories with product counts
                            subcat_query = (
                                select(
                                    Category,
                                    func.count(Product.id).filter(Product.is_active == True).label('product_count')
                                )
                                .outerjoin(Product, Product.category_id == Category.id)
                                .where(
                                    Category.id.in_(specific_ids),
                                    Category.is_active == True
                                )
                                .group_by(Category.id)
                                .order_by(Category.sort_order.asc(), Category.name.asc())
                            )
                            subcat_result = await db.execute(subcat_query)
                            subcategories = subcat_result.all()

                            menu_response.subcategories = [
                                StorefrontSubcategoryResponse(
                                    id=str(sc.Category.id),
                                    name=sc.Category.name,
                                    slug=sc.Category.slug,
                                    image_url=sc.Category.image_url,
                                    product_count=sc.product_count or 0,
                                )
                                for sc in subcategories
                            ]
                    else:
                        # Show all children of this category
                        subcat_query = (
                            select(
                                Category,
                                func.count(Product.id).filter(Product.is_active == True).label('product_count')
                            )
                            .outerjoin(Product, Product.category_id == Category.id)
                            .where(
                                Category.parent_id == item.category_id,
                                Category.is_active == True
                            )
                            .group_by(Category.id)
                            .order_by(Category.sort_order.asc(), Category.name.asc())
                        )
                        subcat_result = await db.execute(subcat_query)
                        subcategories = subcat_result.all()

                        menu_response.subcategories = [
                            StorefrontSubcategoryResponse(
                                id=str(sc.Category.id),
                                name=sc.Category.name,
                                slug=sc.Category.slug,
                                image_url=sc.Category.image_url,
                                product_count=sc.product_count or 0,
                            )
                            for sc in subcategories
                        ]

        response_items.append(menu_response)

    # Cache for 10 minutes (navigation changes infrequently)
    await cache.set(cache_key, [item.model_dump() for item in response_items], ttl=600)

    response.headers["X-Cache"] = "MISS"
    response.headers["X-Response-Time"] = f"{(time.time() - start_time) * 1000:.2f}ms"
    return response_items


# ==================== Product Comparison ====================


class ProductComparisonItem(BaseModel):
    """Product comparison item with specifications."""
    id: str
    name: str
    slug: str
    sku: str
    mrp: float
    selling_price: Optional[float]
    discount_percentage: Optional[float]
    primary_image_url: Optional[str]
    brand_name: Optional[str]
    category_name: Optional[str]
    short_description: Optional[str]
    specifications: dict  # Key-value pairs of specifications
    in_stock: bool
    warranty_months: Optional[int]
    hsn_code: Optional[str]
    weight_kg: Optional[float]


class ProductComparisonResponse(BaseModel):
    """Response for product comparison."""
    products: List[ProductComparisonItem]
    comparison_attributes: List[str]  # List of all unique specification keys for comparison


@router.get("/products/compare", response_model=ProductComparisonResponse)
async def compare_products(
    db: DB,
    response: Response,
    product_ids: str = Query(..., description="Comma-separated product IDs (max 4)"),
):
    """
    Compare multiple products side by side.

    Features:
    - Compares up to 4 products at once
    - Returns specifications in a unified format for easy comparison
    - Includes all comparison attributes found across products

    No authentication required. Not cached (dynamic comparisons).
    """
    start_time = time.time()

    # Parse product IDs
    try:
        ids = [uuid_module.UUID(pid.strip()) for pid in product_ids.split(",") if pid.strip()]
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid product ID format")

    if len(ids) < 2:
        raise HTTPException(status_code=400, detail="At least 2 products required for comparison")
    if len(ids) > 4:
        raise HTTPException(status_code=400, detail="Maximum 4 products can be compared at once")

    # Fetch products with specifications
    query = (
        select(Product)
        .options(
            selectinload(Product.images),
            selectinload(Product.category),
            selectinload(Product.brand),
        )
        .where(
            Product.id.in_(ids),
            Product.is_active == True,
        )
    )
    result = await db.execute(query)
    products = result.scalars().all()

    if len(products) < 2:
        raise HTTPException(status_code=404, detail="Not enough valid products found for comparison")

    # Get stock info
    stock_query = (
        select(
            InventorySummary.product_id,
            func.sum(InventorySummary.available_quantity).label('total_available')
        )
        .where(InventorySummary.product_id.in_([p.id for p in products]))
        .group_by(InventorySummary.product_id)
    )
    stock_result = await db.execute(stock_query)
    stock_map = {row.product_id: row.total_available or 0 for row in stock_result.all()}

    # Collect all unique specification keys
    all_spec_keys = set()
    comparison_items = []

    for p in products:
        # Parse specifications from product
        specs = {}
        if p.specifications and isinstance(p.specifications, list):
            for spec in p.specifications:
                if isinstance(spec, dict):
                    key = spec.get("name") or spec.get("key", "Unknown")
                    value = spec.get("value", "N/A")
                    specs[key] = value
                    all_spec_keys.add(key)

        # Get primary image
        primary_image = next(
            (img for img in (p.images or []) if img.is_primary),
            (p.images[0] if p.images else None)
        )

        # Calculate discount percentage
        discount_pct = None
        if p.mrp and p.selling_price and p.mrp > p.selling_price:
            discount_pct = round((float(p.mrp) - float(p.selling_price)) / float(p.mrp) * 100, 1)

        comparison_items.append(ProductComparisonItem(
            id=str(p.id),
            name=p.name,
            slug=p.slug,
            sku=p.sku,
            mrp=float(p.mrp) if p.mrp else 0,
            selling_price=float(p.selling_price) if p.selling_price else None,
            discount_percentage=discount_pct,
            primary_image_url=primary_image.image_url if primary_image else None,
            brand_name=p.brand.name if p.brand else None,
            category_name=p.category.name if p.category else None,
            short_description=p.short_description,
            specifications=specs,
            in_stock=stock_map.get(p.id, 0) > 0,
            warranty_months=p.warranty_months,
            hsn_code=p.hsn_code,
            weight_kg=float(p.weight_kg) if p.weight_kg else None,
        ))

    # Standard attributes that are always compared
    standard_attrs = ["Price", "Brand", "Category", "Warranty", "HSN Code", "Weight"]
    comparison_attrs = standard_attrs + sorted(list(all_spec_keys - set(standard_attrs)))

    response.headers["X-Response-Time"] = f"{(time.time() - start_time) * 1000:.2f}ms"

    return ProductComparisonResponse(
        products=comparison_items,
        comparison_attributes=comparison_attrs,
    )


# ==================== Cache Management ====================

@router.post("/cache/clear")
async def clear_storefront_cache(secret: str = Query(..., description="Admin secret key")):
    """
    Clear all storefront caches.
    Requires admin secret for protection.
    Use this after updating categories, products, or menu items.
    """
    # Simple protection - in production, use proper auth
    if secret != "ilms2026":
        raise HTTPException(status_code=403, detail="Invalid secret")

    cache = get_cache()

    # Clear all storefront-related caches
    cleared = 0
    cleared += await cache.delete("storefront:mega-menu")
    cleared += await cache.delete("storefront:categories")
    cleared += await cache.clear_pattern("storefront:*")
    cleared += await cache.clear_pattern("product:*")  # product:slug:*, product:id:*
    cleared += await cache.clear_pattern("products:*")  # Legacy key format
    cleared += await cache.clear_pattern("categories:*")

    return {
        "success": True,
        "message": f"Cleared {cleared} cache entries",
        "cleared_keys": [
            "storefront:mega-menu",
            "storefront:categories",
            "storefront:*",
            "product:*",
            "products:*",
            "categories:*"
        ]
    }


# ==================== Demo Booking Endpoint ====================

from app.models.cms import DemoBooking, VideoGuide
from app.models.shipment import Shipment, ShipmentTracking
from app.schemas.storefront import (
    DemoBookingRequest,
    DemoBookingResponse,
    ExchangeCalculateRequest,
    ExchangeCalculateResponse,
    VideoGuideResponse,
    VideoGuideListResponse,
    AWBTrackingResponse,
    TrackingEventResponse,
)
from app.services.document_sequence_service import DocumentSequenceService


@router.post("/demo-bookings", response_model=DemoBookingResponse)
async def create_demo_booking(
    request: DemoBookingRequest,
    db: DB,
):
    """
    Create a new demo booking request.
    Allows customers to book video call or phone call demos for products.
    No authentication required.
    """
    # Generate booking number
    doc_service = DocumentSequenceService(db)
    booking_number = await doc_service.get_next_number("DEMO", "")

    # Try to find product ID if not provided
    product_id = None
    if request.product_id:
        try:
            product_id = uuid_module.UUID(request.product_id)
        except (ValueError, AttributeError):
            pass

    # Create demo booking
    demo_booking = DemoBooking(
        customer_name=request.customer_name,
        phone=request.phone,
        email=request.email,
        address=request.address,
        pincode=request.pincode,
        product_id=product_id,
        product_name=request.product_name,
        demo_type=request.demo_type.upper() if request.demo_type else "VIDEO",
        preferred_date=request.preferred_date,
        preferred_time=request.preferred_time,
        notes=request.notes,
        status="PENDING",
        booking_number=booking_number,
        source="WEBSITE",
    )

    db.add(demo_booking)
    await db.commit()
    await db.refresh(demo_booking)

    return DemoBookingResponse(
        success=True,
        booking_id=str(demo_booking.id),
        booking_number=booking_number,
        message="Demo booking created successfully! Our team will contact you shortly to confirm.",
        estimated_callback="Within 2 hours during business hours (10 AM - 6 PM)",
    )


# ==================== Exchange Calculator Endpoint ====================

# Brand base values for exchange calculation
EXCHANGE_BRAND_VALUES = {
    "aquaguard": 2000,
    "kent": 1800,
    "pureit": 1500,
    "livpure": 1400,
    "eureka_forbes": 1800,
    "blue_star": 1600,
    "ao_smith": 1700,
    "ilms": 2000,
    "other": 1000,
}

# Age multipliers
EXCHANGE_AGE_MULTIPLIERS = {
    (0, 1): 1.0,      # 0-1 years
    (1, 2): 0.85,     # 1-2 years
    (2, 3): 0.70,     # 2-3 years
    (3, 5): 0.50,     # 3-5 years
    (5, 100): 0.30,   # 5+ years
}

# Condition multipliers
EXCHANGE_CONDITION_MULTIPLIERS = {
    "excellent": 1.0,
    "good": 0.8,
    "fair": 0.6,
    "poor": 0.4,
}


@router.post("/exchange/calculate", response_model=ExchangeCalculateResponse)
async def calculate_exchange_value(
    request: ExchangeCalculateRequest,
):
    """
    Calculate the exchange value for an old water purifier.
    No authentication required.
    """
    # Get brand base value
    brand_lower = request.brand.lower().replace(" ", "_")
    base_value = EXCHANGE_BRAND_VALUES.get(brand_lower, EXCHANGE_BRAND_VALUES["other"])

    # Get age multiplier
    age_multiplier = 0.5  # default
    for (min_age, max_age), multiplier in EXCHANGE_AGE_MULTIPLIERS.items():
        if min_age <= request.age_years < max_age:
            age_multiplier = multiplier
            break

    # Get condition multiplier
    condition_lower = request.condition.lower()
    condition_multiplier = EXCHANGE_CONDITION_MULTIPLIERS.get(
        condition_lower, EXCHANGE_CONDITION_MULTIPLIERS["fair"]
    )

    # Calculate value
    calculated_value = int(base_value * age_multiplier * condition_multiplier)

    # Apply min/max bounds
    min_value = 500
    max_value = 2000
    estimated_value = max(min_value, min(calculated_value, max_value))

    return ExchangeCalculateResponse(
        estimated_value=estimated_value,
        min_value=min_value,
        max_value=max_value,
        factors={
            "brand": request.brand,
            "brand_base_value": base_value,
            "age_years": request.age_years,
            "age_multiplier": age_multiplier,
            "condition": request.condition,
            "condition_multiplier": condition_multiplier,
            "calculated_value": calculated_value,
        },
        terms=[
            "Old purifier will be picked up at the time of new purifier installation",
            "Exchange value is subject to physical verification",
            "Exchange offer cannot be combined with other discounts",
            "Purifier must be in one piece with all major components intact",
        ],
    )


# ==================== Video Guides Endpoints ====================

@router.get("/guides", response_model=VideoGuideListResponse)
async def list_video_guides(
    db: DB,
    response: Response,
    category: Optional[str] = Query(None, description="Filter by category"),
    product_id: Optional[str] = Query(None, description="Filter by product ID"),
    is_featured: Optional[bool] = Query(None, description="Filter featured guides only"),
    search: Optional[str] = Query(None, description="Search in title and description"),
    page: int = Query(default=1, ge=1),
    size: int = Query(default=12, ge=1, le=50),
):
    """
    List video guides for the storefront.
    No authentication required. Cached for 10 minutes.
    """
    start_time = time.time()
    cache = get_cache()

    # Build cache key
    cache_params = f"guides:{category}:{product_id}:{is_featured}:{search}:{page}:{size}"
    cached_result = await cache.get(cache_params)
    if cached_result:
        response.headers["X-Cache"] = "HIT"
        response.headers["X-Response-Time"] = f"{(time.time() - start_time) * 1000:.2f}ms"
        return VideoGuideListResponse(**cached_result)

    # Build query
    query = (
        select(VideoGuide)
        .where(VideoGuide.is_active == True)
    )

    if category:
        query = query.where(VideoGuide.category == category.upper())
    if product_id:
        try:
            prod_uuid = uuid_module.UUID(product_id)
            query = query.where(VideoGuide.product_id == prod_uuid)
        except (ValueError, AttributeError):
            pass
    if is_featured is not None:
        query = query.where(VideoGuide.is_featured == is_featured)
    if search:
        search_term = f"%{search}%"
        query = query.where(
            or_(
                VideoGuide.title.ilike(search_term),
                VideoGuide.description.ilike(search_term),
            )
        )

    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # Sort and paginate
    query = query.order_by(
        VideoGuide.is_featured.desc(),
        VideoGuide.sort_order.asc(),
        VideoGuide.created_at.desc(),
    )
    offset = (page - 1) * size
    query = query.offset(offset).limit(size)

    result = await db.execute(query)
    guides = result.scalars().all()

    # Get unique categories for filters
    categories_query = select(VideoGuide.category.distinct()).where(VideoGuide.is_active == True)
    categories_result = await db.execute(categories_query)
    available_categories = [row[0] for row in categories_result.all() if row[0]]

    # Transform to response
    items = []
    for g in guides:
        items.append(VideoGuideResponse(
            id=str(g.id),
            title=g.title,
            slug=g.slug,
            description=g.description,
            thumbnail_url=g.thumbnail_url,
            video_url=g.video_url,
            video_type=g.video_type,
            video_id=g.video_id,
            duration_seconds=g.duration_seconds,
            category=g.category,
            product_name=None,  # Could fetch product name if needed
            view_count=g.view_count,
            is_featured=g.is_featured,
        ))

    pages = (total + size - 1) // size

    result_data = VideoGuideListResponse(
        items=items,
        total=total,
        page=page,
        size=size,
        pages=pages,
        categories=available_categories,
    )

    # Cache for 10 minutes
    await cache.set(cache_params, result_data.model_dump(), ttl=600)

    response.headers["X-Cache"] = "MISS"
    response.headers["X-Response-Time"] = f"{(time.time() - start_time) * 1000:.2f}ms"
    return result_data


@router.get("/guides/{slug}", response_model=VideoGuideResponse)
async def get_video_guide_by_slug(
    slug: str,
    db: DB,
    response: Response,
):
    """
    Get a single video guide by slug.
    Increments view count.
    No authentication required.
    """
    start_time = time.time()

    query = (
        select(VideoGuide)
        .where(VideoGuide.slug == slug, VideoGuide.is_active == True)
    )
    result = await db.execute(query)
    guide = result.scalar_one_or_none()

    if not guide:
        raise HTTPException(status_code=404, detail="Video guide not found")

    # Increment view count
    guide.view_count = (guide.view_count or 0) + 1
    await db.commit()

    result_data = VideoGuideResponse(
        id=str(guide.id),
        title=guide.title,
        slug=guide.slug,
        description=guide.description,
        thumbnail_url=guide.thumbnail_url,
        video_url=guide.video_url,
        video_type=guide.video_type,
        video_id=guide.video_id,
        duration_seconds=guide.duration_seconds,
        category=guide.category,
        product_name=None,
        view_count=guide.view_count,
        is_featured=guide.is_featured,
    )

    response.headers["X-Response-Time"] = f"{(time.time() - start_time) * 1000:.2f}ms"
    return result_data


# ==================== Public AWB Tracking Endpoint ====================

# Status message mapping for human-readable messages
STATUS_MESSAGES = {
    "CREATED": "Shipment created",
    "PACKED": "Order packed and ready",
    "READY_FOR_PICKUP": "Ready for courier pickup",
    "MANIFESTED": "Added to shipping manifest",
    "PICKED_UP": "Picked up by courier",
    "IN_TRANSIT": "In transit to destination",
    "REACHED_HUB": "Reached delivery hub",
    "OUT_FOR_DELIVERY": "Out for delivery",
    "DELIVERED": "Successfully delivered",
    "DELIVERY_FAILED": "Delivery attempt failed",
    "RTO_INITIATED": "Return to origin initiated",
    "RTO_IN_TRANSIT": "Returning to warehouse",
    "RTO_DELIVERED": "Returned to warehouse",
    "CANCELLED": "Shipment cancelled",
    "LOST": "Shipment lost in transit",
}


@router.get("/track/{awb}", response_model=AWBTrackingResponse)
async def track_shipment_by_awb(
    awb: str,
    db: DB,
    response: Response,
):
    """
    Track a shipment by AWB (Air Waybill) number.
    Public endpoint - no authentication required.

    Returns shipment status, tracking history, and delivery information.
    """
    start_time = time.time()

    # Find shipment by AWB number or tracking number
    query = (
        select(Shipment)
        .options(selectinload(Shipment.tracking_history))
        .options(selectinload(Shipment.transporter))
        .options(selectinload(Shipment.warehouse))
        .options(selectinload(Shipment.order))
        .where(
            or_(
                Shipment.awb_number == awb,
                Shipment.tracking_number == awb,
            )
        )
    )
    result = await db.execute(query)
    shipment = result.scalar_one_or_none()

    if not shipment:
        raise HTTPException(
            status_code=404,
            detail="Shipment not found. Please check the AWB number."
        )

    # Get transporter name
    courier_name = None
    if shipment.transporter:
        courier_name = shipment.transporter.name

    # Get origin city from warehouse
    origin_city = None
    if shipment.warehouse:
        origin_city = shipment.warehouse.city

    # Build tracking events list (most recent first)
    tracking_events = []
    if shipment.tracking_history:
        for event in sorted(shipment.tracking_history, key=lambda x: x.event_time, reverse=True):
            status_message = STATUS_MESSAGES.get(event.status, event.status.replace("_", " ").title())
            if event.remarks:
                status_message = event.remarks

            tracking_events.append(TrackingEventResponse(
                status=event.status,
                status_message=status_message,
                location=event.location or event.city,
                remarks=event.transporter_remarks,
                timestamp=event.event_time.isoformat() if event.event_time else "",
            ))

    # Get current location from latest tracking event
    current_location = None
    if tracking_events:
        current_location = tracking_events[0].location

    # Get order number if available
    order_number = None
    if shipment.order:
        order_number = shipment.order.order_number

    # Get status message
    status_message = STATUS_MESSAGES.get(shipment.status, shipment.status.replace("_", " ").title())

    # Build external tracking URL if transporter has one
    tracking_url = None
    if shipment.transporter and shipment.awb_number:
        # Common transporter tracking URL patterns
        transporter_name = shipment.transporter.name.lower() if shipment.transporter.name else ""
        if "delhivery" in transporter_name:
            tracking_url = f"https://www.delhivery.com/track/package/{shipment.awb_number}"
        elif "bluedart" in transporter_name:
            tracking_url = f"https://www.bluedart.com/tracking?tracknumbers={shipment.awb_number}"
        elif "dtdc" in transporter_name:
            tracking_url = f"https://tracking.dtdc.com/ctbs-tracking/customerInterface.tr?submitName=showCI498&cType=Consignment&cnNo={shipment.awb_number}"
        elif "fedex" in transporter_name:
            tracking_url = f"https://www.fedex.com/fedextrack/?tracknumbers={shipment.awb_number}"
        elif "ecom express" in transporter_name or "ecom" in transporter_name:
            tracking_url = f"https://ecomexpress.in/tracking/?awb_field={shipment.awb_number}"
        elif "xpressbees" in transporter_name:
            tracking_url = f"https://www.xpressbees.com/track?awb={shipment.awb_number}"
        elif "shadowfax" in transporter_name:
            tracking_url = f"https://tracker.shadowfax.in/?tracking_id={shipment.awb_number}"

    result_data = AWBTrackingResponse(
        awb_number=shipment.awb_number or awb,
        courier_name=courier_name,
        status=shipment.status,
        status_message=status_message,
        origin_city=origin_city,
        destination_city=shipment.ship_to_city,
        destination_pincode=shipment.ship_to_pincode,
        shipped_at=shipment.shipped_at.isoformat() if shipment.shipped_at else None,
        estimated_delivery=shipment.expected_delivery_date.isoformat() if shipment.expected_delivery_date else None,
        delivered_at=shipment.delivered_at.isoformat() if shipment.delivered_at else None,
        current_location=current_location,
        tracking_url=tracking_url,
        tracking_events=tracking_events,
        order_number=order_number,
        payment_mode=shipment.payment_mode or "PREPAID",
        cod_amount=shipment.cod_amount if shipment.payment_mode == "COD" else None,
    )

    response.headers["X-Response-Time"] = f"{(time.time() - start_time) * 1000:.2f}ms"
    return result_data


# ==================== FAQ Endpoint ====================

@router.get("/faq", response_model=StorefrontFaqResponse)
async def get_faq(
    db: DB,
    response: Response,
    category_slug: Optional[str] = None,
):
    """
    Get FAQ categories and items for the storefront.
    Returns all active FAQ categories with their active items.

    Optionally filter by category_slug to get items from a specific category.
    No authentication required. Cached for 10 minutes.
    """
    start_time = time.time()
    cache = get_cache()

    # Build cache key
    cache_key = f"storefront:faq:{category_slug or 'all'}"
    cached_result = await cache.get(cache_key)
    if cached_result:
        response.headers["X-Cache"] = "HIT"
        response.headers["X-Response-Time"] = f"{(time.time() - start_time) * 1000:.2f}ms"
        return StorefrontFaqResponse(**cached_result)

    # Build query for categories
    category_query = (
        select(CMSFaqCategory)
        .where(CMSFaqCategory.is_active == True)
        .order_by(CMSFaqCategory.sort_order.asc())
    )

    if category_slug:
        category_query = category_query.where(CMSFaqCategory.slug == category_slug)

    result = await db.execute(category_query)
    categories = result.scalars().all()

    # Build response with items for each category
    response_categories = []
    total_items = 0

    for cat in categories:
        # Get active items for this category
        items_query = (
            select(CMSFaqItem)
            .where(
                CMSFaqItem.category_id == cat.id,
                CMSFaqItem.is_active == True,
            )
            .order_by(CMSFaqItem.sort_order.asc())
        )
        items_result = await db.execute(items_query)
        items = items_result.scalars().all()

        # Convert keywords from JSONB to list if needed
        item_responses = []
        for item in items:
            keywords = item.keywords if isinstance(item.keywords, list) else []
            item_responses.append(StorefrontFaqItemResponse(
                id=str(item.id),
                question=item.question,
                answer=item.answer,
                keywords=keywords,
            ))

        total_items += len(item_responses)

        response_categories.append(StorefrontFaqCategoryResponse(
            id=str(cat.id),
            name=cat.name,
            slug=cat.slug,
            icon=cat.icon,
            icon_color=cat.icon_color,
            items=item_responses,
        ))

    result_data = StorefrontFaqResponse(
        categories=response_categories,
        total_items=total_items,
    )

    # Cache for 10 minutes
    await cache.set(cache_key, result_data.model_dump(), ttl=600)

    response.headers["X-Cache"] = "MISS"
    response.headers["X-Response-Time"] = f"{(time.time() - start_time) * 1000:.2f}ms"
    return result_data
