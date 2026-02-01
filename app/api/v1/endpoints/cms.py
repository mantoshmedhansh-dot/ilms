"""CMS Admin API endpoints for D2C content management.

Provides CRUD operations for:
- Banners
- USPs (Features)
- Testimonials
- Announcements
- Static Pages (with version history)
- SEO Settings

All endpoints require authentication and CMS permissions.
"""
from datetime import datetime, timezone
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, Depends
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload

from app.api.deps import DB, CurrentUser, require_permissions
from app.services.cache_service import get_cache
from app.models.cms import (
    CMSBanner,
    CMSUsp,
    CMSTestimonial,
    CMSAnnouncement,
    CMSPage,
    CMSPageVersion,
    CMSSeo,
    CMSSiteSetting,
    CMSMenuItem,
    CMSFeatureBar,
    CMSMegaMenuItem,
    CMSFaqCategory,
    CMSFaqItem,
    VideoGuide,
)
from app.models import Category
from app.core.module_decorators import require_module
from app.schemas.cms import (
    # Banner schemas
    CMSBannerCreate,
    CMSBannerUpdate,
    CMSBannerResponse,
    CMSBannerListResponse,
    # USP schemas
    CMSUspCreate,
    CMSUspUpdate,
    CMSUspResponse,
    CMSUspListResponse,
    # Testimonial schemas
    CMSTestimonialCreate,
    CMSTestimonialUpdate,
    CMSTestimonialResponse,
    CMSTestimonialListResponse,
    # Announcement schemas
    CMSAnnouncementCreate,
    CMSAnnouncementUpdate,
    CMSAnnouncementResponse,
    CMSAnnouncementListResponse,
    # Page schemas
    CMSPageCreate,
    CMSPageUpdate,
    CMSPageResponse,
    CMSPageListResponse,
    CMSPageVersionResponse,
    # SEO schemas
    CMSSeoCreate,
    CMSSeoUpdate,
    CMSSeoResponse,
    CMSSeoListResponse,
    # Site Settings schemas
    CMSSiteSettingCreate,
    CMSSiteSettingUpdate,
    CMSSiteSettingResponse,
    CMSSiteSettingListResponse,
    CMSSiteSettingBulkUpdate,
    # Menu Item schemas
    CMSMenuItemCreate,
    CMSMenuItemUpdate,
    CMSMenuItemResponse,
    CMSMenuItemListResponse,
    # Feature Bar schemas
    CMSFeatureBarCreate,
    CMSFeatureBarUpdate,
    CMSFeatureBarResponse,
    CMSFeatureBarListResponse,
    # Mega Menu schemas
    CMSMegaMenuItemCreate,
    CMSMegaMenuItemUpdate,
    CMSMegaMenuItemResponse,
    CMSMegaMenuItemListResponse,
    # FAQ Category schemas
    CMSFaqCategoryCreate,
    CMSFaqCategoryUpdate,
    CMSFaqCategoryResponse,
    CMSFaqCategoryListResponse,
    # FAQ Item schemas
    CMSFaqItemCreate,
    CMSFaqItemUpdate,
    CMSFaqItemResponse,
    CMSFaqItemListResponse,
    # Video Guide schemas
    CMSVideoGuideCreate,
    CMSVideoGuideUpdate,
    CMSVideoGuideResponse,
    CMSVideoGuideListResponse,
    # Common schemas
    CMSReorderRequest,
)

router = APIRouter()


# ==================== Banner Endpoints ====================

@router.get("/banners", response_model=CMSBannerListResponse)
@require_module("d2c_storefront")
async def list_banners(
    db: DB,
    current_user: CurrentUser,
    is_active: Optional[bool] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    _: bool = Depends(require_permissions(["CMS_VIEW"])),
):
    """List all banners (admin view - includes inactive)."""
    query = select(CMSBanner).order_by(CMSBanner.sort_order.asc(), CMSBanner.created_at.desc())

    if is_active is not None:
        query = query.where(CMSBanner.is_active == is_active)

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # Fetch items
    query = query.offset(skip).limit(limit)
    result = await db.execute(query)
    banners = result.scalars().all()

    return CMSBannerListResponse(
        items=[CMSBannerResponse.model_validate(b) for b in banners],
        total=total
    )


@router.post("/banners", response_model=CMSBannerResponse, status_code=201)
@require_module("d2c_storefront")
async def create_banner(
    data: CMSBannerCreate,
    db: DB,
    current_user: CurrentUser,
    _: bool = Depends(require_permissions(["CMS_CREATE"])),
):
    """Create a new banner."""
    banner = CMSBanner(
        **data.model_dump(),
        created_by=current_user.id,
    )
    db.add(banner)
    await db.commit()
    await db.refresh(banner)
    return CMSBannerResponse.model_validate(banner)


@router.get("/banners/{banner_id}", response_model=CMSBannerResponse)
@require_module("d2c_storefront")
async def get_banner(
    banner_id: UUID,
    db: DB,
    current_user: CurrentUser,
    _: bool = Depends(require_permissions(["CMS_VIEW"])),
):
    """Get a single banner by ID."""
    result = await db.execute(
        select(CMSBanner).where(CMSBanner.id == banner_id)
    )
    banner = result.scalar_one_or_none()
    if not banner:
        raise HTTPException(status_code=404, detail="Banner not found")
    return CMSBannerResponse.model_validate(banner)


@router.put("/banners/{banner_id}", response_model=CMSBannerResponse)
@require_module("d2c_storefront")
async def update_banner(
    banner_id: UUID,
    data: CMSBannerUpdate,
    db: DB,
    current_user: CurrentUser,
    _: bool = Depends(require_permissions(["CMS_EDIT"])),
):
    """Update a banner."""
    result = await db.execute(
        select(CMSBanner).where(CMSBanner.id == banner_id)
    )
    banner = result.scalar_one_or_none()
    if not banner:
        raise HTTPException(status_code=404, detail="Banner not found")

    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(banner, key, value)

    await db.commit()
    await db.refresh(banner)
    return CMSBannerResponse.model_validate(banner)


@router.delete("/banners/{banner_id}", status_code=204)
@require_module("d2c_storefront")
async def delete_banner(
    banner_id: UUID,
    db: DB,
    current_user: CurrentUser,
    _: bool = Depends(require_permissions(["CMS_DELETE"])),
):
    """Delete a banner."""
    result = await db.execute(
        select(CMSBanner).where(CMSBanner.id == banner_id)
    )
    banner = result.scalar_one_or_none()
    if not banner:
        raise HTTPException(status_code=404, detail="Banner not found")

    await db.delete(banner)
    await db.commit()


@router.put("/banners/reorder", response_model=List[CMSBannerResponse])
@require_module("d2c_storefront")
async def reorder_banners(
    data: CMSReorderRequest,
    db: DB,
    current_user: CurrentUser,
    _: bool = Depends(require_permissions(["CMS_EDIT"])),
):
    """Reorder banners by providing list of IDs in desired order."""
    banners = []
    for idx, banner_id in enumerate(data.ids):
        result = await db.execute(
            select(CMSBanner).where(CMSBanner.id == banner_id)
        )
        banner = result.scalar_one_or_none()
        if banner:
            banner.sort_order = idx
            banners.append(banner)

    await db.commit()
    for banner in banners:
        await db.refresh(banner)

    return [CMSBannerResponse.model_validate(b) for b in banners]


# ==================== USP Endpoints ====================

@router.get("/usps", response_model=CMSUspListResponse)
@require_module("d2c_storefront")
async def list_usps(
    db: DB,
    current_user: CurrentUser,
    is_active: Optional[bool] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    _: bool = Depends(require_permissions(["CMS_VIEW"])),
):
    """List all USPs."""
    query = select(CMSUsp).order_by(CMSUsp.sort_order.asc())

    if is_active is not None:
        query = query.where(CMSUsp.is_active == is_active)

    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    query = query.offset(skip).limit(limit)
    result = await db.execute(query)
    usps = result.scalars().all()

    return CMSUspListResponse(
        items=[CMSUspResponse.model_validate(u) for u in usps],
        total=total
    )


@router.post("/usps", response_model=CMSUspResponse, status_code=201)
@require_module("d2c_storefront")
async def create_usp(
    data: CMSUspCreate,
    db: DB,
    current_user: CurrentUser,
    _: bool = Depends(require_permissions(["CMS_CREATE"])),
):
    """Create a new USP."""
    usp = CMSUsp(
        **data.model_dump(),
        created_by=current_user.id,
    )
    db.add(usp)
    await db.commit()
    await db.refresh(usp)
    return CMSUspResponse.model_validate(usp)


@router.get("/usps/{usp_id}", response_model=CMSUspResponse)
@require_module("d2c_storefront")
async def get_usp(
    usp_id: UUID,
    db: DB,
    current_user: CurrentUser,
    _: bool = Depends(require_permissions(["CMS_VIEW"])),
):
    """Get a single USP by ID."""
    result = await db.execute(
        select(CMSUsp).where(CMSUsp.id == usp_id)
    )
    usp = result.scalar_one_or_none()
    if not usp:
        raise HTTPException(status_code=404, detail="USP not found")
    return CMSUspResponse.model_validate(usp)


@router.put("/usps/{usp_id}", response_model=CMSUspResponse)
@require_module("d2c_storefront")
async def update_usp(
    usp_id: UUID,
    data: CMSUspUpdate,
    db: DB,
    current_user: CurrentUser,
    _: bool = Depends(require_permissions(["CMS_EDIT"])),
):
    """Update a USP."""
    result = await db.execute(
        select(CMSUsp).where(CMSUsp.id == usp_id)
    )
    usp = result.scalar_one_or_none()
    if not usp:
        raise HTTPException(status_code=404, detail="USP not found")

    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(usp, key, value)

    await db.commit()
    await db.refresh(usp)
    return CMSUspResponse.model_validate(usp)


@router.delete("/usps/{usp_id}", status_code=204)
@require_module("d2c_storefront")
async def delete_usp(
    usp_id: UUID,
    db: DB,
    current_user: CurrentUser,
    _: bool = Depends(require_permissions(["CMS_DELETE"])),
):
    """Delete a USP."""
    result = await db.execute(
        select(CMSUsp).where(CMSUsp.id == usp_id)
    )
    usp = result.scalar_one_or_none()
    if not usp:
        raise HTTPException(status_code=404, detail="USP not found")

    await db.delete(usp)
    await db.commit()


@router.put("/usps/reorder", response_model=List[CMSUspResponse])
@require_module("d2c_storefront")
async def reorder_usps(
    data: CMSReorderRequest,
    db: DB,
    current_user: CurrentUser,
    _: bool = Depends(require_permissions(["CMS_EDIT"])),
):
    """Reorder USPs."""
    usps = []
    for idx, usp_id in enumerate(data.ids):
        result = await db.execute(
            select(CMSUsp).where(CMSUsp.id == usp_id)
        )
        usp = result.scalar_one_or_none()
        if usp:
            usp.sort_order = idx
            usps.append(usp)

    await db.commit()
    for usp in usps:
        await db.refresh(usp)

    return [CMSUspResponse.model_validate(u) for u in usps]


# ==================== Testimonial Endpoints ====================

@router.get("/testimonials", response_model=CMSTestimonialListResponse)
@require_module("d2c_storefront")
async def list_testimonials(
    db: DB,
    current_user: CurrentUser,
    is_active: Optional[bool] = None,
    is_featured: Optional[bool] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    _: bool = Depends(require_permissions(["CMS_VIEW"])),
):
    """List all testimonials."""
    query = select(CMSTestimonial).order_by(
        CMSTestimonial.is_featured.desc(),
        CMSTestimonial.sort_order.asc()
    )

    if is_active is not None:
        query = query.where(CMSTestimonial.is_active == is_active)
    if is_featured is not None:
        query = query.where(CMSTestimonial.is_featured == is_featured)

    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    query = query.offset(skip).limit(limit)
    result = await db.execute(query)
    testimonials = result.scalars().all()

    return CMSTestimonialListResponse(
        items=[CMSTestimonialResponse.model_validate(t) for t in testimonials],
        total=total
    )


@router.post("/testimonials", response_model=CMSTestimonialResponse, status_code=201)
@require_module("d2c_storefront")
async def create_testimonial(
    data: CMSTestimonialCreate,
    db: DB,
    current_user: CurrentUser,
    _: bool = Depends(require_permissions(["CMS_CREATE"])),
):
    """Create a new testimonial."""
    testimonial = CMSTestimonial(
        **data.model_dump(),
        created_by=current_user.id,
    )
    db.add(testimonial)
    await db.commit()
    await db.refresh(testimonial)
    return CMSTestimonialResponse.model_validate(testimonial)


@router.get("/testimonials/{testimonial_id}", response_model=CMSTestimonialResponse)
@require_module("d2c_storefront")
async def get_testimonial(
    testimonial_id: UUID,
    db: DB,
    current_user: CurrentUser,
    _: bool = Depends(require_permissions(["CMS_VIEW"])),
):
    """Get a single testimonial by ID."""
    result = await db.execute(
        select(CMSTestimonial).where(CMSTestimonial.id == testimonial_id)
    )
    testimonial = result.scalar_one_or_none()
    if not testimonial:
        raise HTTPException(status_code=404, detail="Testimonial not found")
    return CMSTestimonialResponse.model_validate(testimonial)


@router.put("/testimonials/{testimonial_id}", response_model=CMSTestimonialResponse)
@require_module("d2c_storefront")
async def update_testimonial(
    testimonial_id: UUID,
    data: CMSTestimonialUpdate,
    db: DB,
    current_user: CurrentUser,
    _: bool = Depends(require_permissions(["CMS_EDIT"])),
):
    """Update a testimonial."""
    result = await db.execute(
        select(CMSTestimonial).where(CMSTestimonial.id == testimonial_id)
    )
    testimonial = result.scalar_one_or_none()
    if not testimonial:
        raise HTTPException(status_code=404, detail="Testimonial not found")

    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(testimonial, key, value)

    await db.commit()
    await db.refresh(testimonial)
    return CMSTestimonialResponse.model_validate(testimonial)


@router.delete("/testimonials/{testimonial_id}", status_code=204)
@require_module("d2c_storefront")
async def delete_testimonial(
    testimonial_id: UUID,
    db: DB,
    current_user: CurrentUser,
    _: bool = Depends(require_permissions(["CMS_DELETE"])),
):
    """Delete a testimonial."""
    result = await db.execute(
        select(CMSTestimonial).where(CMSTestimonial.id == testimonial_id)
    )
    testimonial = result.scalar_one_or_none()
    if not testimonial:
        raise HTTPException(status_code=404, detail="Testimonial not found")

    await db.delete(testimonial)
    await db.commit()


# ==================== Announcement Endpoints ====================

@router.get("/announcements", response_model=CMSAnnouncementListResponse)
@require_module("d2c_storefront")
async def list_announcements(
    db: DB,
    current_user: CurrentUser,
    is_active: Optional[bool] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    _: bool = Depends(require_permissions(["CMS_VIEW"])),
):
    """List all announcements."""
    query = select(CMSAnnouncement).order_by(CMSAnnouncement.sort_order.asc())

    if is_active is not None:
        query = query.where(CMSAnnouncement.is_active == is_active)

    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    query = query.offset(skip).limit(limit)
    result = await db.execute(query)
    announcements = result.scalars().all()

    return CMSAnnouncementListResponse(
        items=[CMSAnnouncementResponse.model_validate(a) for a in announcements],
        total=total
    )


@router.post("/announcements", response_model=CMSAnnouncementResponse, status_code=201)
@require_module("d2c_storefront")
async def create_announcement(
    data: CMSAnnouncementCreate,
    db: DB,
    current_user: CurrentUser,
    _: bool = Depends(require_permissions(["CMS_CREATE"])),
):
    """Create a new announcement."""
    announcement = CMSAnnouncement(
        **data.model_dump(),
        created_by=current_user.id,
    )
    db.add(announcement)
    await db.commit()
    await db.refresh(announcement)
    return CMSAnnouncementResponse.model_validate(announcement)


@router.get("/announcements/{announcement_id}", response_model=CMSAnnouncementResponse)
@require_module("d2c_storefront")
async def get_announcement(
    announcement_id: UUID,
    db: DB,
    current_user: CurrentUser,
    _: bool = Depends(require_permissions(["CMS_VIEW"])),
):
    """Get a single announcement by ID."""
    result = await db.execute(
        select(CMSAnnouncement).where(CMSAnnouncement.id == announcement_id)
    )
    announcement = result.scalar_one_or_none()
    if not announcement:
        raise HTTPException(status_code=404, detail="Announcement not found")
    return CMSAnnouncementResponse.model_validate(announcement)


@router.put("/announcements/{announcement_id}", response_model=CMSAnnouncementResponse)
@require_module("d2c_storefront")
async def update_announcement(
    announcement_id: UUID,
    data: CMSAnnouncementUpdate,
    db: DB,
    current_user: CurrentUser,
    _: bool = Depends(require_permissions(["CMS_EDIT"])),
):
    """Update an announcement."""
    result = await db.execute(
        select(CMSAnnouncement).where(CMSAnnouncement.id == announcement_id)
    )
    announcement = result.scalar_one_or_none()
    if not announcement:
        raise HTTPException(status_code=404, detail="Announcement not found")

    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        if key == 'announcement_type' and value is not None:
            setattr(announcement, key, value.value if hasattr(value, 'value') else value)
        else:
            setattr(announcement, key, value)

    await db.commit()
    await db.refresh(announcement)
    return CMSAnnouncementResponse.model_validate(announcement)


@router.delete("/announcements/{announcement_id}", status_code=204)
@require_module("d2c_storefront")
async def delete_announcement(
    announcement_id: UUID,
    db: DB,
    current_user: CurrentUser,
    _: bool = Depends(require_permissions(["CMS_DELETE"])),
):
    """Delete an announcement."""
    result = await db.execute(
        select(CMSAnnouncement).where(CMSAnnouncement.id == announcement_id)
    )
    announcement = result.scalar_one_or_none()
    if not announcement:
        raise HTTPException(status_code=404, detail="Announcement not found")

    await db.delete(announcement)
    await db.commit()


# ==================== Page Endpoints ====================

@router.get("/pages", response_model=CMSPageListResponse)
@require_module("d2c_storefront")
async def list_pages(
    db: DB,
    current_user: CurrentUser,
    status: Optional[str] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    _: bool = Depends(require_permissions(["CMS_VIEW"])),
):
    """List all pages."""
    query = select(CMSPage).order_by(CMSPage.sort_order.asc(), CMSPage.created_at.desc())

    if status:
        query = query.where(CMSPage.status == status)

    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    query = query.offset(skip).limit(limit)
    result = await db.execute(query)
    pages = result.scalars().all()

    return CMSPageListResponse(
        items=[
            {
                "id": p.id,
                "title": p.title,
                "slug": p.slug,
                "status": p.status,
                "published_at": p.published_at,
                "updated_at": p.updated_at,
            }
            for p in pages
        ],
        total=total
    )


@router.post("/pages", response_model=CMSPageResponse, status_code=201)
@require_module("d2c_storefront")
async def create_page(
    data: CMSPageCreate,
    db: DB,
    current_user: CurrentUser,
    _: bool = Depends(require_permissions(["CMS_CREATE"])),
):
    """Create a new page."""
    # Check for duplicate slug
    existing = await db.execute(
        select(CMSPage).where(CMSPage.slug == data.slug)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Page with this slug already exists")

    page = CMSPage(
        **data.model_dump(),
        created_by=current_user.id,
    )
    db.add(page)
    await db.commit()
    await db.refresh(page)

    # Create initial version
    version = CMSPageVersion(
        page_id=page.id,
        version_number=1,
        title=page.title,
        content=page.content,
        meta_title=page.meta_title,
        meta_description=page.meta_description,
        change_summary="Initial version",
        created_by=current_user.id,
    )
    db.add(version)
    await db.commit()

    # Reload with versions
    result = await db.execute(
        select(CMSPage)
        .options(selectinload(CMSPage.versions))
        .where(CMSPage.id == page.id)
    )
    page = result.scalar_one()

    return CMSPageResponse.model_validate(page)


@router.get("/pages/{page_id}", response_model=CMSPageResponse)
@require_module("d2c_storefront")
async def get_page(
    page_id: UUID,
    db: DB,
    current_user: CurrentUser,
    _: bool = Depends(require_permissions(["CMS_VIEW"])),
):
    """Get a single page by ID with version history."""
    result = await db.execute(
        select(CMSPage)
        .options(selectinload(CMSPage.versions))
        .where(CMSPage.id == page_id)
    )
    page = result.scalar_one_or_none()
    if not page:
        raise HTTPException(status_code=404, detail="Page not found")
    return CMSPageResponse.model_validate(page)


@router.put("/pages/{page_id}", response_model=CMSPageResponse)
@require_module("d2c_storefront")
async def update_page(
    page_id: UUID,
    data: CMSPageUpdate,
    db: DB,
    current_user: CurrentUser,
    _: bool = Depends(require_permissions(["CMS_EDIT"])),
):
    """Update a page (creates new version)."""
    result = await db.execute(
        select(CMSPage)
        .options(selectinload(CMSPage.versions))
        .where(CMSPage.id == page_id)
    )
    page = result.scalar_one_or_none()
    if not page:
        raise HTTPException(status_code=404, detail="Page not found")

    # Check for duplicate slug if slug is being updated
    if data.slug and data.slug != page.slug:
        existing = await db.execute(
            select(CMSPage).where(CMSPage.slug == data.slug, CMSPage.id != page_id)
        )
        if existing.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="Page with this slug already exists")

    update_data = data.model_dump(exclude_unset=True)

    # Create new version before update
    max_version = max([v.version_number for v in page.versions], default=0)
    version = CMSPageVersion(
        page_id=page.id,
        version_number=max_version + 1,
        title=update_data.get('title', page.title),
        content=update_data.get('content', page.content),
        meta_title=update_data.get('meta_title', page.meta_title),
        meta_description=update_data.get('meta_description', page.meta_description),
        change_summary=f"Updated by user",
        created_by=current_user.id,
    )
    db.add(version)

    # Apply updates
    for key, value in update_data.items():
        if key == 'status' and value is not None:
            setattr(page, key, value.value if hasattr(value, 'value') else value)
        else:
            setattr(page, key, value)

    page.updated_by = current_user.id

    # Store old slug for cache invalidation if slug is changing
    old_slug = page.slug if data.slug and data.slug != page.slug else None

    await db.commit()

    # Invalidate cache for this page (so D2C storefront gets fresh content)
    cache = get_cache()
    await cache.delete(f"cms:page:{page.slug}")
    if old_slug:
        await cache.delete(f"cms:page:{old_slug}")
    # Also invalidate footer pages cache in case this page is in footer
    await cache.delete("cms:pages:footer")

    # Reload with versions
    result = await db.execute(
        select(CMSPage)
        .options(selectinload(CMSPage.versions))
        .where(CMSPage.id == page_id)
    )
    page = result.scalar_one()

    return CMSPageResponse.model_validate(page)


@router.delete("/pages/{page_id}", status_code=204)
@require_module("d2c_storefront")
async def delete_page(
    page_id: UUID,
    db: DB,
    current_user: CurrentUser,
    _: bool = Depends(require_permissions(["CMS_DELETE"])),
):
    """Delete a page and all its versions."""
    result = await db.execute(
        select(CMSPage).where(CMSPage.id == page_id)
    )
    page = result.scalar_one_or_none()
    if not page:
        raise HTTPException(status_code=404, detail="Page not found")

    # Store slug for cache invalidation before deletion
    page_slug = page.slug

    await db.delete(page)
    await db.commit()

    # Invalidate cache
    cache = get_cache()
    await cache.delete(f"cms:page:{page_slug}")
    await cache.delete("cms:pages:footer")


@router.post("/pages/{page_id}/publish", response_model=CMSPageResponse)
@require_module("d2c_storefront")
async def publish_page(
    page_id: UUID,
    db: DB,
    current_user: CurrentUser,
    _: bool = Depends(require_permissions(["CMS_PUBLISH"])),
):
    """Publish a draft page."""
    result = await db.execute(
        select(CMSPage)
        .options(selectinload(CMSPage.versions))
        .where(CMSPage.id == page_id)
    )
    page = result.scalar_one_or_none()
    if not page:
        raise HTTPException(status_code=404, detail="Page not found")

    page.status = "PUBLISHED"
    page.published_at = datetime.now(timezone.utc)
    page.updated_by = current_user.id

    await db.commit()
    await db.refresh(page)

    # Invalidate cache so the page appears on storefront immediately
    cache = get_cache()
    await cache.delete(f"cms:page:{page.slug}")
    await cache.delete("cms:pages:footer")

    return CMSPageResponse.model_validate(page)


@router.get("/pages/{page_id}/versions", response_model=List[CMSPageVersionResponse])
@require_module("d2c_storefront")
async def get_page_versions(
    page_id: UUID,
    db: DB,
    current_user: CurrentUser,
    _: bool = Depends(require_permissions(["CMS_VIEW"])),
):
    """Get version history for a page."""
    result = await db.execute(
        select(CMSPageVersion)
        .where(CMSPageVersion.page_id == page_id)
        .order_by(CMSPageVersion.version_number.desc())
    )
    versions = result.scalars().all()
    return [CMSPageVersionResponse.model_validate(v) for v in versions]


@router.post("/pages/{page_id}/revert/{version_number}", response_model=CMSPageResponse)
@require_module("d2c_storefront")
async def revert_page_to_version(
    page_id: UUID,
    version_number: int,
    db: DB,
    current_user: CurrentUser,
    _: bool = Depends(require_permissions(["CMS_EDIT"])),
):
    """Revert a page to a specific version."""
    # Get page
    result = await db.execute(
        select(CMSPage)
        .options(selectinload(CMSPage.versions))
        .where(CMSPage.id == page_id)
    )
    page = result.scalar_one_or_none()
    if not page:
        raise HTTPException(status_code=404, detail="Page not found")

    # Find version
    version_result = await db.execute(
        select(CMSPageVersion)
        .where(
            CMSPageVersion.page_id == page_id,
            CMSPageVersion.version_number == version_number
        )
    )
    version = version_result.scalar_one_or_none()
    if not version:
        raise HTTPException(status_code=404, detail="Version not found")

    # Create new version from old content
    max_version = max([v.version_number for v in page.versions], default=0)
    new_version = CMSPageVersion(
        page_id=page.id,
        version_number=max_version + 1,
        title=version.title,
        content=version.content,
        meta_title=version.meta_title,
        meta_description=version.meta_description,
        change_summary=f"Reverted to version {version_number}",
        created_by=current_user.id,
    )
    db.add(new_version)

    # Update page with old version content
    page.title = version.title
    page.content = version.content
    page.meta_title = version.meta_title
    page.meta_description = version.meta_description
    page.updated_by = current_user.id

    await db.commit()

    # Reload
    result = await db.execute(
        select(CMSPage)
        .options(selectinload(CMSPage.versions))
        .where(CMSPage.id == page_id)
    )
    page = result.scalar_one()

    return CMSPageResponse.model_validate(page)


# ==================== SEO Endpoints ====================

@router.get("/seo", response_model=CMSSeoListResponse)
@require_module("d2c_storefront")
async def list_seo_settings(
    db: DB,
    current_user: CurrentUser,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    _: bool = Depends(require_permissions(["CMS_VIEW"])),
):
    """List all SEO settings."""
    query = select(CMSSeo).order_by(CMSSeo.url_path.asc())

    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    query = query.offset(skip).limit(limit)
    result = await db.execute(query)
    seo_settings = result.scalars().all()

    return CMSSeoListResponse(
        items=[CMSSeoResponse.model_validate(s) for s in seo_settings],
        total=total
    )


@router.post("/seo", response_model=CMSSeoResponse, status_code=201)
@require_module("d2c_storefront")
async def create_seo_settings(
    data: CMSSeoCreate,
    db: DB,
    current_user: CurrentUser,
    _: bool = Depends(require_permissions(["CMS_CREATE"])),
):
    """Create SEO settings for a URL path."""
    # Check for duplicate
    existing = await db.execute(
        select(CMSSeo).where(CMSSeo.url_path == data.url_path)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="SEO settings for this URL already exist")

    seo = CMSSeo(
        **data.model_dump(),
        created_by=current_user.id,
    )
    db.add(seo)
    await db.commit()
    await db.refresh(seo)
    return CMSSeoResponse.model_validate(seo)


@router.get("/seo/{seo_id}", response_model=CMSSeoResponse)
@require_module("d2c_storefront")
async def get_seo_settings(
    seo_id: UUID,
    db: DB,
    current_user: CurrentUser,
    _: bool = Depends(require_permissions(["CMS_VIEW"])),
):
    """Get SEO settings by ID."""
    result = await db.execute(
        select(CMSSeo).where(CMSSeo.id == seo_id)
    )
    seo = result.scalar_one_or_none()
    if not seo:
        raise HTTPException(status_code=404, detail="SEO settings not found")
    return CMSSeoResponse.model_validate(seo)


@router.put("/seo/{seo_id}", response_model=CMSSeoResponse)
@require_module("d2c_storefront")
async def update_seo_settings(
    seo_id: UUID,
    data: CMSSeoUpdate,
    db: DB,
    current_user: CurrentUser,
    _: bool = Depends(require_permissions(["CMS_EDIT"])),
):
    """Update SEO settings."""
    result = await db.execute(
        select(CMSSeo).where(CMSSeo.id == seo_id)
    )
    seo = result.scalar_one_or_none()
    if not seo:
        raise HTTPException(status_code=404, detail="SEO settings not found")

    # Check for duplicate URL path
    if data.url_path and data.url_path != seo.url_path:
        existing = await db.execute(
            select(CMSSeo).where(CMSSeo.url_path == data.url_path, CMSSeo.id != seo_id)
        )
        if existing.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="SEO settings for this URL already exist")

    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(seo, key, value)

    await db.commit()
    await db.refresh(seo)
    return CMSSeoResponse.model_validate(seo)


@router.delete("/seo/{seo_id}", status_code=204)
@require_module("d2c_storefront")
async def delete_seo_settings(
    seo_id: UUID,
    db: DB,
    current_user: CurrentUser,
    _: bool = Depends(require_permissions(["CMS_DELETE"])),
):
    """Delete SEO settings."""
    result = await db.execute(
        select(CMSSeo).where(CMSSeo.id == seo_id)
    )
    seo = result.scalar_one_or_none()
    if not seo:
        raise HTTPException(status_code=404, detail="SEO settings not found")

    await db.delete(seo)
    await db.commit()


# ==================== Site Settings Endpoints ====================

@router.get("/settings", response_model=CMSSiteSettingListResponse)
@require_module("d2c_storefront")
async def list_site_settings(
    db: DB,
    current_user: CurrentUser,
    group: Optional[str] = None,
    _: bool = Depends(require_permissions(["CMS_VIEW"])),
):
    """List all site settings, optionally filtered by group."""
    query = select(CMSSiteSetting).order_by(CMSSiteSetting.setting_group, CMSSiteSetting.sort_order)

    if group:
        query = query.where(CMSSiteSetting.setting_group == group)

    result = await db.execute(query)
    settings = result.scalars().all()

    return CMSSiteSettingListResponse(
        items=[CMSSiteSettingResponse.model_validate(s) for s in settings],
        total=len(settings)
    )


@router.get("/settings/{setting_key}", response_model=CMSSiteSettingResponse)
@require_module("d2c_storefront")
async def get_site_setting(
    setting_key: str,
    db: DB,
    current_user: CurrentUser,
    _: bool = Depends(require_permissions(["CMS_VIEW"])),
):
    """Get a single site setting by key."""
    result = await db.execute(
        select(CMSSiteSetting).where(CMSSiteSetting.setting_key == setting_key)
    )
    setting = result.scalar_one_or_none()
    if not setting:
        raise HTTPException(status_code=404, detail="Setting not found")
    return CMSSiteSettingResponse.model_validate(setting)


@router.post("/settings", response_model=CMSSiteSettingResponse, status_code=201)
@require_module("d2c_storefront")
async def create_site_setting(
    data: CMSSiteSettingCreate,
    db: DB,
    current_user: CurrentUser,
    _: bool = Depends(require_permissions(["CMS_CREATE"])),
):
    """Create a new site setting."""
    existing = await db.execute(
        select(CMSSiteSetting).where(CMSSiteSetting.setting_key == data.setting_key)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Setting with this key already exists")

    setting = CMSSiteSetting(**data.model_dump())
    db.add(setting)
    await db.commit()
    await db.refresh(setting)
    return CMSSiteSettingResponse.model_validate(setting)


@router.put("/settings/{setting_key}", response_model=CMSSiteSettingResponse)
@require_module("d2c_storefront")
async def update_site_setting(
    setting_key: str,
    data: CMSSiteSettingUpdate,
    db: DB,
    current_user: CurrentUser,
    _: bool = Depends(require_permissions(["CMS_EDIT"])),
):
    """Update a site setting."""
    result = await db.execute(
        select(CMSSiteSetting).where(CMSSiteSetting.setting_key == setting_key)
    )
    setting = result.scalar_one_or_none()
    if not setting:
        raise HTTPException(status_code=404, detail="Setting not found")

    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(setting, key, value)

    await db.commit()
    await db.refresh(setting)
    return CMSSiteSettingResponse.model_validate(setting)


@router.put("/settings-bulk", response_model=CMSSiteSettingListResponse)
@require_module("d2c_storefront")
async def bulk_update_site_settings(
    data: CMSSiteSettingBulkUpdate,
    db: DB,
    current_user: CurrentUser,
    _: bool = Depends(require_permissions(["CMS_EDIT"])),
):
    """Bulk update site settings by key-value pairs. Creates settings if they don't exist."""
    updated = []
    for key, value in data.settings.items():
        result = await db.execute(
            select(CMSSiteSetting).where(CMSSiteSetting.setting_key == key)
        )
        setting = result.scalar_one_or_none()
        if setting:
            # Update existing setting
            setting.setting_value = value
            updated.append(setting)
        else:
            # Create new setting if it doesn't exist
            # Determine setting type and group from key
            setting_type = "url" if "url" in key.lower() or "link" in key.lower() else "text"

            # Determine setting_group from key prefix
            if key.startswith("partner_page_"):
                setting_group = "partner_page"
            elif any(s in key.lower() for s in ["facebook", "twitter", "instagram", "youtube", "linkedin"]):
                setting_group = "social"
            elif "phone" in key.lower() or "email" in key.lower() or "address" in key.lower():
                setting_group = "contact"
            elif "footer" in key.lower() or "copyright" in key.lower():
                setting_group = "footer"
            elif "newsletter" in key.lower():
                setting_group = "newsletter"
            else:
                setting_group = "general"

            new_setting = CMSSiteSetting(
                setting_key=key,
                setting_value=value,
                setting_type=setting_type,
                setting_group=setting_group,
                label=key.replace("_", " ").title(),
                sort_order=0,
            )
            db.add(new_setting)
            updated.append(new_setting)

    await db.commit()

    # Refresh all updated settings
    for setting in updated:
        await db.refresh(setting)

    # Invalidate settings cache
    cache = get_cache()
    await cache.delete("storefront:settings")

    return CMSSiteSettingListResponse(
        items=[CMSSiteSettingResponse.model_validate(s) for s in updated],
        total=len(updated)
    )


@router.delete("/settings/{setting_key}", status_code=204)
@require_module("d2c_storefront")
async def delete_site_setting(
    setting_key: str,
    db: DB,
    current_user: CurrentUser,
    _: bool = Depends(require_permissions(["CMS_DELETE"])),
):
    """Delete a site setting."""
    result = await db.execute(
        select(CMSSiteSetting).where(CMSSiteSetting.setting_key == setting_key)
    )
    setting = result.scalar_one_or_none()
    if not setting:
        raise HTTPException(status_code=404, detail="Setting not found")

    await db.delete(setting)
    await db.commit()


# ==================== Menu Item Endpoints ====================

@router.get("/menu-items", response_model=CMSMenuItemListResponse)
@require_module("d2c_storefront")
async def list_menu_items(
    db: DB,
    current_user: CurrentUser,
    location: Optional[str] = None,
    _: bool = Depends(require_permissions(["CMS_VIEW"])),
):
    """List all menu items, optionally filtered by location."""
    query = select(CMSMenuItem).order_by(CMSMenuItem.menu_location, CMSMenuItem.sort_order)

    if location:
        query = query.where(CMSMenuItem.menu_location == location)

    result = await db.execute(query)
    items = result.scalars().all()

    return CMSMenuItemListResponse(
        items=[CMSMenuItemResponse.model_validate(i) for i in items],
        total=len(items)
    )


@router.get("/menu-items/{item_id}", response_model=CMSMenuItemResponse)
@require_module("d2c_storefront")
async def get_menu_item(
    item_id: UUID,
    db: DB,
    current_user: CurrentUser,
    _: bool = Depends(require_permissions(["CMS_VIEW"])),
):
    """Get a single menu item by ID."""
    result = await db.execute(
        select(CMSMenuItem).where(CMSMenuItem.id == item_id)
    )
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Menu item not found")
    return CMSMenuItemResponse.model_validate(item)


@router.post("/menu-items", response_model=CMSMenuItemResponse, status_code=201)
@require_module("d2c_storefront")
async def create_menu_item(
    data: CMSMenuItemCreate,
    db: DB,
    current_user: CurrentUser,
    _: bool = Depends(require_permissions(["CMS_CREATE"])),
):
    """Create a new menu item."""
    item = CMSMenuItem(**data.model_dump())
    db.add(item)
    await db.commit()
    await db.refresh(item)

    # Invalidate menu cache so D2C storefront gets fresh data
    cache = get_cache()
    await cache.delete("cms:menu:all")
    await cache.delete(f"cms:menu:{item.menu_location}")

    return CMSMenuItemResponse.model_validate(item)


@router.put("/menu-items/{item_id}", response_model=CMSMenuItemResponse)
@require_module("d2c_storefront")
async def update_menu_item(
    item_id: UUID,
    data: CMSMenuItemUpdate,
    db: DB,
    current_user: CurrentUser,
    _: bool = Depends(require_permissions(["CMS_EDIT"])),
):
    """Update a menu item."""
    result = await db.execute(
        select(CMSMenuItem).where(CMSMenuItem.id == item_id)
    )
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Menu item not found")

    # Store old location for cache invalidation
    old_location = item.menu_location

    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(item, key, value)

    await db.commit()
    await db.refresh(item)

    # Invalidate menu cache so D2C storefront gets fresh data
    cache = get_cache()
    await cache.delete("cms:menu:all")
    await cache.delete(f"cms:menu:{item.menu_location}")
    if old_location != item.menu_location:
        await cache.delete(f"cms:menu:{old_location}")

    return CMSMenuItemResponse.model_validate(item)


@router.delete("/menu-items/{item_id}", status_code=204)
@require_module("d2c_storefront")
async def delete_menu_item(
    item_id: UUID,
    db: DB,
    current_user: CurrentUser,
    _: bool = Depends(require_permissions(["CMS_DELETE"])),
):
    """Delete a menu item."""
    result = await db.execute(
        select(CMSMenuItem).where(CMSMenuItem.id == item_id)
    )
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Menu item not found")

    # Store location for cache invalidation
    menu_location = item.menu_location

    await db.delete(item)
    await db.commit()

    # Invalidate menu cache so D2C storefront gets fresh data
    cache = get_cache()
    await cache.delete("cms:menu:all")
    await cache.delete(f"cms:menu:{menu_location}")


@router.put("/menu-items/reorder", status_code=200)
@require_module("d2c_storefront")
async def reorder_menu_items(
    data: CMSReorderRequest,
    db: DB,
    current_user: CurrentUser,
    _: bool = Depends(require_permissions(["CMS_EDIT"])),
):
    """Reorder menu items."""
    locations_affected = set()
    for idx, item_id in enumerate(data.ids):
        result = await db.execute(
            select(CMSMenuItem).where(CMSMenuItem.id == item_id)
        )
        item = result.scalar_one_or_none()
        if item:
            item.sort_order = idx
            locations_affected.add(item.menu_location)

    await db.commit()

    # Invalidate menu cache so D2C storefront gets fresh data
    cache = get_cache()
    await cache.delete("cms:menu:all")
    for location in locations_affected:
        await cache.delete(f"cms:menu:{location}")

    return {"success": True, "message": "Menu items reordered"}


# ==================== Feature Bar Endpoints ====================

@router.get("/feature-bars", response_model=CMSFeatureBarListResponse)
@require_module("d2c_storefront")
async def list_feature_bars(
    db: DB,
    current_user: CurrentUser,
    is_active: Optional[bool] = None,
    _: bool = Depends(require_permissions(["CMS_VIEW"])),
):
    """List all feature bar items."""
    query = select(CMSFeatureBar).order_by(CMSFeatureBar.sort_order)

    if is_active is not None:
        query = query.where(CMSFeatureBar.is_active == is_active)

    result = await db.execute(query)
    items = result.scalars().all()

    return CMSFeatureBarListResponse(
        items=[CMSFeatureBarResponse.model_validate(i) for i in items],
        total=len(items)
    )


@router.get("/feature-bars/{item_id}", response_model=CMSFeatureBarResponse)
@require_module("d2c_storefront")
async def get_feature_bar(
    item_id: UUID,
    db: DB,
    current_user: CurrentUser,
    _: bool = Depends(require_permissions(["CMS_VIEW"])),
):
    """Get a single feature bar item by ID."""
    result = await db.execute(
        select(CMSFeatureBar).where(CMSFeatureBar.id == item_id)
    )
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Feature bar item not found")
    return CMSFeatureBarResponse.model_validate(item)


@router.post("/feature-bars", response_model=CMSFeatureBarResponse, status_code=201)
@require_module("d2c_storefront")
async def create_feature_bar(
    data: CMSFeatureBarCreate,
    db: DB,
    current_user: CurrentUser,
    _: bool = Depends(require_permissions(["CMS_CREATE"])),
):
    """Create a new feature bar item."""
    item = CMSFeatureBar(**data.model_dump())
    db.add(item)
    await db.commit()
    await db.refresh(item)
    return CMSFeatureBarResponse.model_validate(item)


@router.put("/feature-bars/{item_id}", response_model=CMSFeatureBarResponse)
@require_module("d2c_storefront")
async def update_feature_bar(
    item_id: UUID,
    data: CMSFeatureBarUpdate,
    db: DB,
    current_user: CurrentUser,
    _: bool = Depends(require_permissions(["CMS_EDIT"])),
):
    """Update a feature bar item."""
    result = await db.execute(
        select(CMSFeatureBar).where(CMSFeatureBar.id == item_id)
    )
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Feature bar item not found")

    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(item, key, value)

    await db.commit()
    await db.refresh(item)
    return CMSFeatureBarResponse.model_validate(item)


@router.delete("/feature-bars/{item_id}", status_code=204)
@require_module("d2c_storefront")
async def delete_feature_bar(
    item_id: UUID,
    db: DB,
    current_user: CurrentUser,
    _: bool = Depends(require_permissions(["CMS_DELETE"])),
):
    """Delete a feature bar item."""
    result = await db.execute(
        select(CMSFeatureBar).where(CMSFeatureBar.id == item_id)
    )
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Feature bar item not found")

    await db.delete(item)
    await db.commit()


@router.put("/feature-bars/reorder", status_code=200)
@require_module("d2c_storefront")
async def reorder_feature_bars(
    data: CMSReorderRequest,
    db: DB,
    current_user: CurrentUser,
    _: bool = Depends(require_permissions(["CMS_EDIT"])),
):
    """Reorder feature bar items."""
    for idx, item_id in enumerate(data.ids):
        result = await db.execute(
            select(CMSFeatureBar).where(CMSFeatureBar.id == item_id)
        )
        item = result.scalar_one_or_none()
        if item:
            item.sort_order = idx

    await db.commit()
    return {"success": True, "message": "Feature bars reordered"}


# ==================== Mega Menu Item Endpoints ====================

@router.get("/mega-menu-items", response_model=CMSMegaMenuItemListResponse)
@require_module("d2c_storefront")
async def list_mega_menu_items(
    db: DB,
    current_user: CurrentUser,
    is_active: Optional[bool] = None,
    _: bool = Depends(require_permissions(["CMS_VIEW"])),
):
    """List all mega menu items for D2C navigation management."""
    query = select(CMSMegaMenuItem).order_by(CMSMegaMenuItem.sort_order)

    if is_active is not None:
        query = query.where(CMSMegaMenuItem.is_active == is_active)

    result = await db.execute(query)
    items = result.scalars().all()

    # Enrich with category names
    response_items = []
    for item in items:
        item_dict = {
            "id": item.id,
            "title": item.title,
            "icon": item.icon,
            "image_url": item.image_url,
            "menu_type": item.menu_type,
            "category_id": item.category_id,
            "url": item.url,
            "target": item.target,
            "show_subcategories": item.show_subcategories,
            "subcategory_ids": item.subcategory_ids,
            "sort_order": item.sort_order,
            "is_active": item.is_active,
            "is_highlighted": item.is_highlighted,
            "highlight_text": item.highlight_text,
            "company_id": item.company_id,
            "created_at": item.created_at,
            "updated_at": item.updated_at,
            "created_by": item.created_by,
            "category_name": None,
            "category_slug": None,
        }

        # Get category details if linked
        if item.category_id:
            cat_result = await db.execute(
                select(Category).where(Category.id == item.category_id)
            )
            category = cat_result.scalar_one_or_none()
            if category:
                item_dict["category_name"] = category.name
                item_dict["category_slug"] = category.slug

        response_items.append(CMSMegaMenuItemResponse(**item_dict))

    return CMSMegaMenuItemListResponse(
        items=response_items,
        total=len(items)
    )


@router.get("/mega-menu-items/{item_id}", response_model=CMSMegaMenuItemResponse)
@require_module("d2c_storefront")
async def get_mega_menu_item(
    item_id: UUID,
    db: DB,
    current_user: CurrentUser,
    _: bool = Depends(require_permissions(["CMS_VIEW"])),
):
    """Get a single mega menu item by ID."""
    result = await db.execute(
        select(CMSMegaMenuItem).where(CMSMegaMenuItem.id == item_id)
    )
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Mega menu item not found")

    # Get category details if linked
    category_name = None
    category_slug = None
    if item.category_id:
        cat_result = await db.execute(
            select(Category).where(Category.id == item.category_id)
        )
        category = cat_result.scalar_one_or_none()
        if category:
            category_name = category.name
            category_slug = category.slug

    return CMSMegaMenuItemResponse(
        id=item.id,
        title=item.title,
        icon=item.icon,
        image_url=item.image_url,
        menu_type=item.menu_type,
        category_id=item.category_id,
        url=item.url,
        target=item.target,
        show_subcategories=item.show_subcategories,
        subcategory_ids=item.subcategory_ids,
        sort_order=item.sort_order,
        is_active=item.is_active,
        is_highlighted=item.is_highlighted,
        highlight_text=item.highlight_text,
        company_id=item.company_id,
        created_at=item.created_at,
        updated_at=item.updated_at,
        created_by=item.created_by,
        category_name=category_name,
        category_slug=category_slug,
    )


@router.post("/mega-menu-items", response_model=CMSMegaMenuItemResponse, status_code=201)
@require_module("d2c_storefront")
async def create_mega_menu_item(
    data: CMSMegaMenuItemCreate,
    db: DB,
    current_user: CurrentUser,
    _: bool = Depends(require_permissions(["CMS_CREATE"])),
):
    """Create a new mega menu item for D2C navigation."""
    # Validate category exists if menu_type is CATEGORY
    category_name = None
    category_slug = None
    # Handle both enum and string for menu_type
    menu_type_str = data.menu_type.value if hasattr(data.menu_type, 'value') else data.menu_type
    if menu_type_str == "CATEGORY" and data.category_id:
        cat_result = await db.execute(
            select(Category).where(Category.id == data.category_id)
        )
        category = cat_result.scalar_one_or_none()
        if not category:
            raise HTTPException(status_code=400, detail="Category not found")
        category_name = category.name
        category_slug = category.slug

    # Convert subcategory_ids list to JSON format for storage
    item_data = data.model_dump()
    if item_data.get("subcategory_ids"):
        item_data["subcategory_ids"] = {"ids": [str(uid) for uid in item_data["subcategory_ids"]]}
    item_data["menu_type"] = item_data["menu_type"].value if hasattr(item_data["menu_type"], "value") else item_data["menu_type"]

    item = CMSMegaMenuItem(
        **item_data,
        created_by=current_user.id,
    )
    db.add(item)
    await db.commit()
    await db.refresh(item)

    # Invalidate mega menu cache
    cache = get_cache()
    await cache.delete("storefront:mega-menu")

    return CMSMegaMenuItemResponse(
        id=item.id,
        title=item.title,
        icon=item.icon,
        image_url=item.image_url,
        menu_type=item.menu_type,
        category_id=item.category_id,
        url=item.url,
        target=item.target,
        show_subcategories=item.show_subcategories,
        subcategory_ids=data.subcategory_ids,
        sort_order=item.sort_order,
        is_active=item.is_active,
        is_highlighted=item.is_highlighted,
        highlight_text=item.highlight_text,
        company_id=item.company_id,
        created_at=item.created_at,
        updated_at=item.updated_at,
        created_by=item.created_by,
        category_name=category_name,
        category_slug=category_slug,
    )


@router.put("/mega-menu-items/{item_id}", response_model=CMSMegaMenuItemResponse)
@require_module("d2c_storefront")
async def update_mega_menu_item(
    item_id: UUID,
    data: CMSMegaMenuItemUpdate,
    db: DB,
    current_user: CurrentUser,
    _: bool = Depends(require_permissions(["CMS_EDIT"])),
):
    """Update a mega menu item."""
    result = await db.execute(
        select(CMSMegaMenuItem).where(CMSMegaMenuItem.id == item_id)
    )
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Mega menu item not found")

    update_data = data.model_dump(exclude_unset=True)

    # Validate category if updating to CATEGORY type
    if update_data.get("menu_type") == "CATEGORY" or (item.menu_type == "CATEGORY" and update_data.get("category_id")):
        cat_id = update_data.get("category_id", item.category_id)
        if cat_id:
            cat_result = await db.execute(
                select(Category).where(Category.id == cat_id)
            )
            if not cat_result.scalar_one_or_none():
                raise HTTPException(status_code=400, detail="Category not found")

    # Convert subcategory_ids list to JSON format
    if "subcategory_ids" in update_data and update_data["subcategory_ids"]:
        update_data["subcategory_ids"] = {"ids": [str(uid) for uid in update_data["subcategory_ids"]]}

    # Convert enum to string if needed
    if "menu_type" in update_data and update_data["menu_type"]:
        update_data["menu_type"] = update_data["menu_type"].value if hasattr(update_data["menu_type"], "value") else update_data["menu_type"]

    for key, value in update_data.items():
        setattr(item, key, value)

    await db.commit()
    await db.refresh(item)

    # Invalidate mega menu cache
    cache = get_cache()
    await cache.delete("storefront:mega-menu")

    # Get category details
    category_name = None
    category_slug = None
    if item.category_id:
        cat_result = await db.execute(
            select(Category).where(Category.id == item.category_id)
        )
        category = cat_result.scalar_one_or_none()
        if category:
            category_name = category.name
            category_slug = category.slug

    # Convert stored subcategory_ids back to list
    subcategory_ids = None
    if item.subcategory_ids and isinstance(item.subcategory_ids, dict):
        subcategory_ids = item.subcategory_ids.get("ids", [])

    return CMSMegaMenuItemResponse(
        id=item.id,
        title=item.title,
        icon=item.icon,
        image_url=item.image_url,
        menu_type=item.menu_type,
        category_id=item.category_id,
        url=item.url,
        target=item.target,
        show_subcategories=item.show_subcategories,
        subcategory_ids=subcategory_ids,
        sort_order=item.sort_order,
        is_active=item.is_active,
        is_highlighted=item.is_highlighted,
        highlight_text=item.highlight_text,
        company_id=item.company_id,
        created_at=item.created_at,
        updated_at=item.updated_at,
        created_by=item.created_by,
        category_name=category_name,
        category_slug=category_slug,
    )


@router.delete("/mega-menu-items/{item_id}", status_code=204)
@require_module("d2c_storefront")
async def delete_mega_menu_item(
    item_id: UUID,
    db: DB,
    current_user: CurrentUser,
    _: bool = Depends(require_permissions(["CMS_DELETE"])),
):
    """Delete a mega menu item."""
    result = await db.execute(
        select(CMSMegaMenuItem).where(CMSMegaMenuItem.id == item_id)
    )
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Mega menu item not found")

    await db.delete(item)
    await db.commit()

    # Invalidate mega menu cache
    cache = get_cache()
    await cache.delete("storefront:mega-menu")


@router.put("/mega-menu-items/reorder", status_code=200)
@require_module("d2c_storefront")
async def reorder_mega_menu_items(
    data: CMSReorderRequest,
    db: DB,
    current_user: CurrentUser,
    _: bool = Depends(require_permissions(["CMS_EDIT"])),
):
    """Reorder mega menu items."""
    for idx, item_id in enumerate(data.ids):
        result = await db.execute(
            select(CMSMegaMenuItem).where(CMSMegaMenuItem.id == item_id)
        )
        item = result.scalar_one_or_none()
        if item:
            item.sort_order = idx

    await db.commit()

    # Invalidate mega menu cache
    cache = get_cache()
    await cache.delete("storefront:mega-menu")

    return {"success": True, "message": "Mega menu items reordered"}


# ==================== FAQ Category Endpoints ====================

@router.get("/faq-categories", response_model=CMSFaqCategoryListResponse)
@require_module("d2c_storefront")
async def list_faq_categories(
    db: DB,
    current_user: CurrentUser,
    is_active: Optional[bool] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    _: bool = Depends(require_permissions(["CMS_VIEW"])),
):
    """List all FAQ categories (admin view - includes inactive)."""
    query = select(CMSFaqCategory).order_by(CMSFaqCategory.sort_order.asc())

    if is_active is not None:
        query = query.where(CMSFaqCategory.is_active == is_active)

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # Fetch items with item counts
    query = query.offset(skip).limit(limit)
    result = await db.execute(query)
    categories = result.scalars().all()

    # Get item counts for each category
    response_items = []
    for cat in categories:
        item_count_result = await db.execute(
            select(func.count()).where(CMSFaqItem.category_id == cat.id)
        )
        items_count = item_count_result.scalar() or 0
        cat_data = CMSFaqCategoryResponse.model_validate(cat)
        cat_data.items_count = items_count
        response_items.append(cat_data)

    return CMSFaqCategoryListResponse(items=response_items, total=total)


@router.post("/faq-categories", response_model=CMSFaqCategoryResponse, status_code=201)
@require_module("d2c_storefront")
async def create_faq_category(
    data: CMSFaqCategoryCreate,
    db: DB,
    current_user: CurrentUser,
    _: bool = Depends(require_permissions(["CMS_CREATE"])),
):
    """Create a new FAQ category."""
    # Check for duplicate slug
    existing = await db.execute(
        select(CMSFaqCategory).where(CMSFaqCategory.slug == data.slug)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="A category with this slug already exists")

    category = CMSFaqCategory(
        **data.model_dump(),
        created_by=current_user.id,
    )
    db.add(category)
    await db.commit()
    await db.refresh(category)

    # Invalidate FAQ cache
    cache = get_cache()
    await cache.delete("storefront:faq")

    response = CMSFaqCategoryResponse.model_validate(category)
    response.items_count = 0
    return response


@router.get("/faq-categories/{category_id}", response_model=CMSFaqCategoryResponse)
@require_module("d2c_storefront")
async def get_faq_category(
    category_id: UUID,
    db: DB,
    current_user: CurrentUser,
    _: bool = Depends(require_permissions(["CMS_VIEW"])),
):
    """Get a specific FAQ category by ID."""
    result = await db.execute(
        select(CMSFaqCategory).where(CMSFaqCategory.id == category_id)
    )
    category = result.scalar_one_or_none()
    if not category:
        raise HTTPException(status_code=404, detail="FAQ category not found")

    # Get items count
    item_count_result = await db.execute(
        select(func.count()).where(CMSFaqItem.category_id == category.id)
    )
    items_count = item_count_result.scalar() or 0

    response = CMSFaqCategoryResponse.model_validate(category)
    response.items_count = items_count
    return response


@router.put("/faq-categories/{category_id}", response_model=CMSFaqCategoryResponse)
@require_module("d2c_storefront")
async def update_faq_category(
    category_id: UUID,
    data: CMSFaqCategoryUpdate,
    db: DB,
    current_user: CurrentUser,
    _: bool = Depends(require_permissions(["CMS_EDIT"])),
):
    """Update a FAQ category."""
    result = await db.execute(
        select(CMSFaqCategory).where(CMSFaqCategory.id == category_id)
    )
    category = result.scalar_one_or_none()
    if not category:
        raise HTTPException(status_code=404, detail="FAQ category not found")

    # Check for duplicate slug if slug is being changed
    if data.slug and data.slug != category.slug:
        existing = await db.execute(
            select(CMSFaqCategory).where(
                CMSFaqCategory.slug == data.slug,
                CMSFaqCategory.id != category_id
            )
        )
        if existing.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="A category with this slug already exists")

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(category, field, value)

    await db.commit()
    await db.refresh(category)

    # Invalidate FAQ cache
    cache = get_cache()
    await cache.delete("storefront:faq")

    # Get items count
    item_count_result = await db.execute(
        select(func.count()).where(CMSFaqItem.category_id == category.id)
    )
    items_count = item_count_result.scalar() or 0

    response = CMSFaqCategoryResponse.model_validate(category)
    response.items_count = items_count
    return response


@router.delete("/faq-categories/{category_id}", status_code=204)
@require_module("d2c_storefront")
async def delete_faq_category(
    category_id: UUID,
    db: DB,
    current_user: CurrentUser,
    _: bool = Depends(require_permissions(["CMS_DELETE"])),
):
    """Delete a FAQ category and all its items."""
    result = await db.execute(
        select(CMSFaqCategory).where(CMSFaqCategory.id == category_id)
    )
    category = result.scalar_one_or_none()
    if not category:
        raise HTTPException(status_code=404, detail="FAQ category not found")

    await db.delete(category)
    await db.commit()

    # Invalidate FAQ cache
    cache = get_cache()
    await cache.delete("storefront:faq")


@router.put("/faq-categories/reorder", status_code=200)
@require_module("d2c_storefront")
async def reorder_faq_categories(
    data: CMSReorderRequest,
    db: DB,
    current_user: CurrentUser,
    _: bool = Depends(require_permissions(["CMS_EDIT"])),
):
    """Reorder FAQ categories."""
    for idx, category_id in enumerate(data.ids):
        result = await db.execute(
            select(CMSFaqCategory).where(CMSFaqCategory.id == category_id)
        )
        category = result.scalar_one_or_none()
        if category:
            category.sort_order = idx

    await db.commit()

    # Invalidate FAQ cache
    cache = get_cache()
    await cache.delete("storefront:faq")

    return {"success": True, "message": "FAQ categories reordered"}


# ==================== FAQ Item Endpoints ====================

@router.get("/faq-items", response_model=CMSFaqItemListResponse)
@require_module("d2c_storefront")
async def list_faq_items(
    db: DB,
    current_user: CurrentUser,
    category_id: Optional[UUID] = None,
    is_active: Optional[bool] = None,
    is_featured: Optional[bool] = None,
    search: Optional[str] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    _: bool = Depends(require_permissions(["CMS_VIEW"])),
):
    """List all FAQ items (admin view - includes inactive)."""
    query = select(CMSFaqItem).order_by(CMSFaqItem.sort_order.asc(), CMSFaqItem.created_at.desc())

    if category_id:
        query = query.where(CMSFaqItem.category_id == category_id)
    if is_active is not None:
        query = query.where(CMSFaqItem.is_active == is_active)
    if is_featured is not None:
        query = query.where(CMSFaqItem.is_featured == is_featured)
    if search:
        search_filter = f"%{search}%"
        query = query.where(
            CMSFaqItem.question.ilike(search_filter) |
            CMSFaqItem.answer.ilike(search_filter)
        )

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # Fetch items
    query = query.offset(skip).limit(limit)
    result = await db.execute(query)
    items = result.scalars().all()

    return CMSFaqItemListResponse(
        items=[CMSFaqItemResponse.model_validate(item) for item in items],
        total=total
    )


@router.post("/faq-items", response_model=CMSFaqItemResponse, status_code=201)
@require_module("d2c_storefront")
async def create_faq_item(
    data: CMSFaqItemCreate,
    db: DB,
    current_user: CurrentUser,
    _: bool = Depends(require_permissions(["CMS_CREATE"])),
):
    """Create a new FAQ item."""
    # Verify category exists
    cat_result = await db.execute(
        select(CMSFaqCategory).where(CMSFaqCategory.id == data.category_id)
    )
    if not cat_result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="FAQ category not found")

    item = CMSFaqItem(
        **data.model_dump(),
        created_by=current_user.id,
    )
    db.add(item)
    await db.commit()
    await db.refresh(item)

    # Invalidate FAQ cache
    cache = get_cache()
    await cache.delete("storefront:faq")

    return CMSFaqItemResponse.model_validate(item)


@router.get("/faq-items/{item_id}", response_model=CMSFaqItemResponse)
@require_module("d2c_storefront")
async def get_faq_item(
    item_id: UUID,
    db: DB,
    current_user: CurrentUser,
    _: bool = Depends(require_permissions(["CMS_VIEW"])),
):
    """Get a specific FAQ item by ID."""
    result = await db.execute(
        select(CMSFaqItem).where(CMSFaqItem.id == item_id)
    )
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="FAQ item not found")

    return CMSFaqItemResponse.model_validate(item)


@router.put("/faq-items/{item_id}", response_model=CMSFaqItemResponse)
@require_module("d2c_storefront")
async def update_faq_item(
    item_id: UUID,
    data: CMSFaqItemUpdate,
    db: DB,
    current_user: CurrentUser,
    _: bool = Depends(require_permissions(["CMS_EDIT"])),
):
    """Update a FAQ item."""
    result = await db.execute(
        select(CMSFaqItem).where(CMSFaqItem.id == item_id)
    )
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="FAQ item not found")

    # Verify new category exists if changing
    if data.category_id and data.category_id != item.category_id:
        cat_result = await db.execute(
            select(CMSFaqCategory).where(CMSFaqCategory.id == data.category_id)
        )
        if not cat_result.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="FAQ category not found")

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(item, field, value)

    await db.commit()
    await db.refresh(item)

    # Invalidate FAQ cache
    cache = get_cache()
    await cache.delete("storefront:faq")

    return CMSFaqItemResponse.model_validate(item)


@router.delete("/faq-items/{item_id}", status_code=204)
@require_module("d2c_storefront")
async def delete_faq_item(
    item_id: UUID,
    db: DB,
    current_user: CurrentUser,
    _: bool = Depends(require_permissions(["CMS_DELETE"])),
):
    """Delete a FAQ item."""
    result = await db.execute(
        select(CMSFaqItem).where(CMSFaqItem.id == item_id)
    )
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="FAQ item not found")

    await db.delete(item)
    await db.commit()

    # Invalidate FAQ cache
    cache = get_cache()
    await cache.delete("storefront:faq")


@router.put("/faq-items/reorder", status_code=200)
@require_module("d2c_storefront")
async def reorder_faq_items(
    data: CMSReorderRequest,
    db: DB,
    current_user: CurrentUser,
    _: bool = Depends(require_permissions(["CMS_EDIT"])),
):
    """Reorder FAQ items."""
    for idx, item_id in enumerate(data.ids):
        result = await db.execute(
            select(CMSFaqItem).where(CMSFaqItem.id == item_id)
        )
        item = result.scalar_one_or_none()
        if item:
            item.sort_order = idx

    await db.commit()

    # Invalidate FAQ cache
    cache = get_cache()
    await cache.delete("storefront:faq")

    return {"success": True, "message": "FAQ items reordered"}


# ==================== Video Guide Endpoints ====================

@router.get("/video-guides", response_model=CMSVideoGuideListResponse)
@require_module("d2c_storefront")
async def list_video_guides(
    db: DB,
    current_user: CurrentUser,
    category: Optional[str] = None,
    is_active: Optional[bool] = None,
    is_featured: Optional[bool] = None,
    search: Optional[str] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    _: bool = Depends(require_permissions(["CMS_VIEW"])),
):
    """List all video guides (admin view - includes inactive)."""
    query = select(VideoGuide).order_by(VideoGuide.sort_order.asc(), VideoGuide.created_at.desc())

    if category:
        query = query.where(VideoGuide.category == category.upper())
    if is_active is not None:
        query = query.where(VideoGuide.is_active == is_active)
    if is_featured is not None:
        query = query.where(VideoGuide.is_featured == is_featured)
    if search:
        search_filter = f"%{search}%"
        query = query.where(
            VideoGuide.title.ilike(search_filter) |
            VideoGuide.description.ilike(search_filter)
        )

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # Fetch items
    query = query.offset(skip).limit(limit)
    result = await db.execute(query)
    guides = result.scalars().all()

    return CMSVideoGuideListResponse(
        items=[CMSVideoGuideResponse.model_validate(guide) for guide in guides],
        total=total,
    )


@router.post("/video-guides", response_model=CMSVideoGuideResponse, status_code=201)
@require_module("d2c_storefront")
async def create_video_guide(
    data: CMSVideoGuideCreate,
    db: DB,
    current_user: CurrentUser,
    _: bool = Depends(require_permissions(["CMS_CREATE"])),
):
    """Create a new video guide."""
    # Check for duplicate slug
    existing = await db.execute(
        select(VideoGuide).where(VideoGuide.slug == data.slug)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="A video guide with this slug already exists")

    guide = VideoGuide(
        **data.model_dump(),
        created_by=current_user.id,
    )
    db.add(guide)
    await db.commit()
    await db.refresh(guide)

    # Invalidate video guides cache
    cache = get_cache()
    await cache.delete_pattern("guides:*")

    return CMSVideoGuideResponse.model_validate(guide)


@router.get("/video-guides/{guide_id}", response_model=CMSVideoGuideResponse)
@require_module("d2c_storefront")
async def get_video_guide(
    guide_id: UUID,
    db: DB,
    current_user: CurrentUser,
    _: bool = Depends(require_permissions(["CMS_VIEW"])),
):
    """Get a specific video guide by ID."""
    result = await db.execute(
        select(VideoGuide).where(VideoGuide.id == guide_id)
    )
    guide = result.scalar_one_or_none()
    if not guide:
        raise HTTPException(status_code=404, detail="Video guide not found")

    return CMSVideoGuideResponse.model_validate(guide)


@router.put("/video-guides/{guide_id}", response_model=CMSVideoGuideResponse)
@require_module("d2c_storefront")
async def update_video_guide(
    guide_id: UUID,
    data: CMSVideoGuideUpdate,
    db: DB,
    current_user: CurrentUser,
    _: bool = Depends(require_permissions(["CMS_EDIT"])),
):
    """Update a video guide."""
    result = await db.execute(
        select(VideoGuide).where(VideoGuide.id == guide_id)
    )
    guide = result.scalar_one_or_none()
    if not guide:
        raise HTTPException(status_code=404, detail="Video guide not found")

    # Check for duplicate slug if slug is being changed
    if data.slug and data.slug != guide.slug:
        existing = await db.execute(
            select(VideoGuide).where(
                VideoGuide.slug == data.slug,
                VideoGuide.id != guide_id
            )
        )
        if existing.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="A video guide with this slug already exists")

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(guide, field, value)

    await db.commit()
    await db.refresh(guide)

    # Invalidate video guides cache
    cache = get_cache()
    await cache.delete_pattern("guides:*")

    return CMSVideoGuideResponse.model_validate(guide)


@router.delete("/video-guides/{guide_id}", status_code=204)
@require_module("d2c_storefront")
async def delete_video_guide(
    guide_id: UUID,
    db: DB,
    current_user: CurrentUser,
    _: bool = Depends(require_permissions(["CMS_DELETE"])),
):
    """Delete a video guide."""
    result = await db.execute(
        select(VideoGuide).where(VideoGuide.id == guide_id)
    )
    guide = result.scalar_one_or_none()
    if not guide:
        raise HTTPException(status_code=404, detail="Video guide not found")

    await db.delete(guide)
    await db.commit()

    # Invalidate video guides cache
    cache = get_cache()
    await cache.delete_pattern("guides:*")


@router.put("/video-guides/reorder", status_code=200)
@require_module("d2c_storefront")
async def reorder_video_guides(
    data: CMSReorderRequest,
    db: DB,
    current_user: CurrentUser,
    _: bool = Depends(require_permissions(["CMS_EDIT"])),
):
    """Reorder video guides."""
    for idx, guide_id in enumerate(data.ids):
        result = await db.execute(
            select(VideoGuide).where(VideoGuide.id == guide_id)
        )
        guide = result.scalar_one_or_none()
        if guide:
            guide.sort_order = idx

    await db.commit()

    # Invalidate video guides cache
    cache = get_cache()
    await cache.delete_pattern("guides:*")

    return {"success": True, "message": "Video guides reordered"}
