"""Pydantic schemas for CMS (D2C Content Management)."""
from datetime import datetime
from typing import Optional, List
from uuid import UUID
from pydantic import BaseModel, Field, ConfigDict, field_validator

from app.schemas.base import BaseResponseSchema
from enum import Enum


# ==================== Enums ====================

class CMSPageStatus(str, Enum):
    DRAFT = "DRAFT"
    PUBLISHED = "PUBLISHED"
    ARCHIVED = "ARCHIVED"


class CMSAnnouncementType(str, Enum):
    INFO = "INFO"
    WARNING = "WARNING"
    PROMO = "PROMO"
    SUCCESS = "SUCCESS"


class CMSMegaMenuItemType(str, Enum):
    """Type of mega menu item"""
    CATEGORY = "CATEGORY"       # Links to ERP category with subcategories
    CUSTOM_LINK = "CUSTOM_LINK" # Custom URL link


# ==================== Banner Schemas ====================

class CMSBannerBase(BaseModel):
    """Base schema for CMS Banner."""
    title: str = Field(..., min_length=1, max_length=200)
    subtitle: Optional[str] = Field(None, max_length=500)
    image_url: str = Field(..., max_length=500)
    thumbnail_url: Optional[str] = Field(None, max_length=500)
    mobile_image_url: Optional[str] = Field(None, max_length=500)
    cta_text: Optional[str] = Field(None, max_length=100)
    cta_link: Optional[str] = Field(None, max_length=500)
    text_position: str = Field("left", pattern="^(left|center|right)$")
    text_color: str = Field("white", pattern="^(white|dark)$")
    sort_order: int = Field(0, ge=0)
    is_active: bool = True
    starts_at: Optional[datetime] = None
    ends_at: Optional[datetime] = None


class CMSBannerCreate(CMSBannerBase):
    """Schema for creating a banner."""
    pass


class CMSBannerUpdate(BaseModel):
    """Schema for updating a banner."""
    title: Optional[str] = Field(None, max_length=200)
    subtitle: Optional[str] = Field(None, max_length=500)
    image_url: Optional[str] = Field(None, max_length=500)
    thumbnail_url: Optional[str] = Field(None, max_length=500)
    mobile_image_url: Optional[str] = Field(None, max_length=500)
    cta_text: Optional[str] = Field(None, max_length=100)
    cta_link: Optional[str] = Field(None, max_length=500)
    text_position: Optional[str] = Field(None, pattern="^(left|center|right)$")
    text_color: Optional[str] = Field(None, pattern="^(white|dark)$")
    sort_order: Optional[int] = Field(None, ge=0)
    is_active: Optional[bool] = None
    starts_at: Optional[datetime] = None
    ends_at: Optional[datetime] = None


class CMSBannerResponse(BaseResponseSchema):
    """Response schema for banner."""
    id: UUID
    created_at: datetime
    updated_at: datetime
    created_by: Optional[UUID] = None


class CMSBannerBrief(BaseResponseSchema):
    """Brief banner info for lists."""
    id: UUID
    title: str
    image_url: str
    thumbnail_url: Optional[str] = None
    is_active: bool
    sort_order: int


# ==================== USP Schemas ====================

class CMSUspBase(BaseModel):
    """Base schema for CMS USP."""
    title: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=300)
    icon: str = Field(..., min_length=1, max_length=50, description="Lucide icon name")
    icon_color: Optional[str] = Field(None, max_length=50)
    link_url: Optional[str] = Field(None, max_length=500)
    link_text: Optional[str] = Field(None, max_length=100)
    sort_order: int = Field(0, ge=0)
    is_active: bool = True


class CMSUspCreate(CMSUspBase):
    """Schema for creating a USP."""
    pass


class CMSUspUpdate(BaseModel):
    """Schema for updating a USP."""
    title: Optional[str] = Field(None, max_length=100)
    description: Optional[str] = Field(None, max_length=300)
    icon: Optional[str] = Field(None, max_length=50)
    icon_color: Optional[str] = Field(None, max_length=50)
    link_url: Optional[str] = Field(None, max_length=500)
    link_text: Optional[str] = Field(None, max_length=100)
    sort_order: Optional[int] = Field(None, ge=0)
    is_active: Optional[bool] = None


class CMSUspResponse(BaseResponseSchema):
    """Response schema for USP."""
    id: UUID
    created_at: datetime
    updated_at: datetime
    created_by: Optional[UUID] = None


# ==================== Testimonial Schemas ====================

class CMSTestimonialBase(BaseModel):
    """Base schema for CMS Testimonial."""
    customer_name: str = Field(..., min_length=1, max_length=100)
    customer_location: Optional[str] = Field(None, max_length=100)
    customer_avatar_url: Optional[str] = Field(None, max_length=500)
    customer_designation: Optional[str] = Field(None, max_length=100)
    rating: int = Field(..., ge=1, le=5)
    content: str = Field(..., min_length=10, max_length=2000)
    title: Optional[str] = Field(None, max_length=200)
    product_name: Optional[str] = Field(None, max_length=200)
    product_id: Optional[UUID] = None
    sort_order: int = Field(0, ge=0)
    is_featured: bool = False
    is_active: bool = True


class CMSTestimonialCreate(CMSTestimonialBase):
    """Schema for creating a testimonial."""
    pass


class CMSTestimonialUpdate(BaseModel):
    """Schema for updating a testimonial."""
    customer_name: Optional[str] = Field(None, max_length=100)
    customer_location: Optional[str] = Field(None, max_length=100)
    customer_avatar_url: Optional[str] = Field(None, max_length=500)
    customer_designation: Optional[str] = Field(None, max_length=100)
    rating: Optional[int] = Field(None, ge=1, le=5)
    content: Optional[str] = Field(None, max_length=2000)
    title: Optional[str] = Field(None, max_length=200)
    product_name: Optional[str] = Field(None, max_length=200)
    product_id: Optional[UUID] = None
    sort_order: Optional[int] = Field(None, ge=0)
    is_featured: Optional[bool] = None
    is_active: Optional[bool] = None


class CMSTestimonialResponse(BaseResponseSchema):
    """Response schema for testimonial."""
    id: UUID
    created_at: datetime
    updated_at: datetime
    created_by: Optional[UUID] = None


# ==================== Announcement Schemas ====================

class CMSAnnouncementBase(BaseModel):
    """Base schema for CMS Announcement."""
    text: str = Field(..., min_length=1, max_length=500)
    link_url: Optional[str] = Field(None, max_length=500)
    link_text: Optional[str] = Field(None, max_length=100)
    announcement_type: CMSAnnouncementType = CMSAnnouncementType.INFO
    background_color: Optional[str] = Field(None, max_length=50)
    text_color: Optional[str] = Field(None, max_length=50)
    starts_at: Optional[datetime] = None
    ends_at: Optional[datetime] = None
    sort_order: int = Field(0, ge=0)
    is_dismissible: bool = True
    is_active: bool = True


class CMSAnnouncementCreate(CMSAnnouncementBase):
    """Schema for creating an announcement."""
    pass


class CMSAnnouncementUpdate(BaseModel):
    """Schema for updating an announcement."""
    text: Optional[str] = Field(None, max_length=500)
    link_url: Optional[str] = Field(None, max_length=500)
    link_text: Optional[str] = Field(None, max_length=100)
    announcement_type: Optional[CMSAnnouncementType] = None
    background_color: Optional[str] = Field(None, max_length=50)
    text_color: Optional[str] = Field(None, max_length=50)
    starts_at: Optional[datetime] = None
    ends_at: Optional[datetime] = None
    sort_order: Optional[int] = Field(None, ge=0)
    is_dismissible: Optional[bool] = None
    is_active: Optional[bool] = None


class CMSAnnouncementResponse(BaseResponseSchema):
    """Response schema for announcement."""
    id: UUID
    created_at: datetime
    updated_at: datetime
    created_by: Optional[UUID] = None


# ==================== Page Schemas ====================

class CMSPageBase(BaseModel):
    """Base schema for CMS Page."""
    title: str = Field(..., min_length=1, max_length=200)
    slug: str = Field(..., min_length=1, max_length=200, pattern="^[a-z0-9-]+$")
    content: Optional[str] = None
    excerpt: Optional[str] = Field(None, max_length=500)
    meta_title: Optional[str] = Field(None, max_length=200)
    meta_description: Optional[str] = Field(None, max_length=500)
    meta_keywords: Optional[str] = Field(None, max_length=500)
    og_image_url: Optional[str] = Field(None, max_length=500)
    canonical_url: Optional[str] = Field(None, max_length=500)
    status: CMSPageStatus = CMSPageStatus.DRAFT
    template: str = Field("default", pattern="^(default|full-width|landing)$")
    show_in_footer: bool = False
    show_in_header: bool = False
    sort_order: int = Field(0, ge=0)


class CMSPageCreate(CMSPageBase):
    """Schema for creating a page."""
    pass


class CMSPageUpdate(BaseModel):
    """Schema for updating a page."""
    title: Optional[str] = Field(None, max_length=200)
    slug: Optional[str] = Field(None, max_length=200, pattern="^[a-z0-9-]+$")
    content: Optional[str] = None
    excerpt: Optional[str] = Field(None, max_length=500)
    meta_title: Optional[str] = Field(None, max_length=200)
    meta_description: Optional[str] = Field(None, max_length=500)
    meta_keywords: Optional[str] = Field(None, max_length=500)
    og_image_url: Optional[str] = Field(None, max_length=500)
    canonical_url: Optional[str] = Field(None, max_length=500)
    status: Optional[CMSPageStatus] = None
    template: Optional[str] = Field(None, pattern="^(default|full-width|landing)$")
    show_in_footer: Optional[bool] = None
    show_in_header: Optional[bool] = None
    sort_order: Optional[int] = Field(None, ge=0)


class CMSPageVersionResponse(BaseResponseSchema):
    """Response schema for page version."""
    id: UUID
    page_id: UUID
    version_number: int
    title: str
    content: Optional[str] = None
    meta_title: Optional[str] = None
    meta_description: Optional[str] = None
    change_summary: Optional[str] = None
    created_at: datetime
    created_by: Optional[UUID] = None


class CMSPageResponse(BaseResponseSchema):
    """Response schema for page."""
    id: UUID
    published_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    created_by: Optional[UUID] = None
    updated_by: Optional[UUID] = None
    versions: List[CMSPageVersionResponse] = []


class CMSPageBrief(BaseResponseSchema):
    """Brief page info for lists."""
    id: UUID
    title: str
    slug: str
    status: str
    published_at: Optional[datetime] = None
    updated_at: datetime


# ==================== SEO Schemas ====================

class CMSSeoBase(BaseModel):
    """Base schema for CMS SEO settings."""
    url_path: str = Field(..., min_length=1, max_length=500)
    meta_title: Optional[str] = Field(None, max_length=200)
    meta_description: Optional[str] = Field(None, max_length=500)
    meta_keywords: Optional[str] = Field(None, max_length=500)
    og_title: Optional[str] = Field(None, max_length=200)
    og_description: Optional[str] = Field(None, max_length=500)
    og_image_url: Optional[str] = Field(None, max_length=500)
    og_type: str = Field("website", max_length=50)
    canonical_url: Optional[str] = Field(None, max_length=500)
    robots_index: bool = True
    robots_follow: bool = True
    structured_data: Optional[dict] = None


class CMSSeoCreate(CMSSeoBase):
    """Schema for creating SEO settings."""
    pass


class CMSSeoUpdate(BaseModel):
    """Schema for updating SEO settings."""
    url_path: Optional[str] = Field(None, max_length=500)
    meta_title: Optional[str] = Field(None, max_length=200)
    meta_description: Optional[str] = Field(None, max_length=500)
    meta_keywords: Optional[str] = Field(None, max_length=500)
    og_title: Optional[str] = Field(None, max_length=200)
    og_description: Optional[str] = Field(None, max_length=500)
    og_image_url: Optional[str] = Field(None, max_length=500)
    og_type: Optional[str] = Field(None, max_length=50)
    canonical_url: Optional[str] = Field(None, max_length=500)
    robots_index: Optional[bool] = None
    robots_follow: Optional[bool] = None
    structured_data: Optional[dict] = None


class CMSSeoResponse(BaseResponseSchema):
    """Response schema for SEO settings."""
    id: UUID
    created_at: datetime
    updated_at: datetime
    created_by: Optional[UUID] = None


# ==================== List/Pagination Schemas ====================

class CMSBannerListResponse(BaseModel):
    """Response for listing banners."""
    items: List[CMSBannerResponse]
    total: int


class CMSUspListResponse(BaseModel):
    """Response for listing USPs."""
    items: List[CMSUspResponse]
    total: int


class CMSTestimonialListResponse(BaseModel):
    """Response for listing testimonials."""
    items: List[CMSTestimonialResponse]
    total: int


class CMSAnnouncementListResponse(BaseModel):
    """Response for listing announcements."""
    items: List[CMSAnnouncementResponse]
    total: int


class CMSPageListResponse(BaseModel):
    """Response for listing pages."""
    items: List[CMSPageBrief]
    total: int


class CMSSeoListResponse(BaseModel):
    """Response for listing SEO settings."""
    items: List[CMSSeoResponse]
    total: int


# ==================== Reorder Schema ====================

class CMSReorderRequest(BaseModel):
    """Request to reorder items."""
    ids: List[UUID] = Field(..., min_length=1, description="List of IDs in desired order")


# ==================== Storefront Schemas (Public) ====================

class StorefrontBannerResponse(BaseModel):
    """Public banner response for storefront."""
    id: str
    title: str
    subtitle: Optional[str] = None
    image_url: str
    mobile_image_url: Optional[str] = None
    cta_text: Optional[str] = None
    cta_link: Optional[str] = None
    text_position: str
    text_color: str


class StorefrontUspResponse(BaseModel):
    """Public USP response for storefront."""
    id: str
    title: str
    description: Optional[str] = None
    icon: str
    icon_color: Optional[str] = None
    link_url: Optional[str] = None
    link_text: Optional[str] = None


class StorefrontTestimonialResponse(BaseModel):
    """Public testimonial response for storefront."""
    id: str
    customer_name: str
    customer_location: Optional[str] = None
    customer_avatar_url: Optional[str] = None
    customer_designation: Optional[str] = None
    rating: int
    content: str
    title: Optional[str] = None
    product_name: Optional[str] = None


class StorefrontAnnouncementResponse(BaseModel):
    """Public announcement response for storefront."""
    id: str
    text: str
    link_url: Optional[str] = None
    link_text: Optional[str] = None
    announcement_type: str
    background_color: Optional[str] = None
    text_color: Optional[str] = None
    is_dismissible: bool


class StorefrontPageResponse(BaseModel):
    """Public page response for storefront."""
    id: str
    title: str
    slug: str
    content: Optional[str] = None
    excerpt: Optional[str] = None
    meta_title: Optional[str] = None
    meta_description: Optional[str] = None
    og_image_url: Optional[str] = None
    template: str
    published_at: Optional[datetime] = None


# ==================== Site Settings Schemas ====================

class CMSSiteSettingBase(BaseModel):
    """Base schema for site settings."""
    setting_key: str = Field(..., min_length=1, max_length=100)
    setting_value: Optional[str] = None
    setting_type: str = Field("text", max_length=50)
    setting_group: str = Field("general", max_length=50)
    label: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = None
    sort_order: int = 0


class CMSSiteSettingCreate(CMSSiteSettingBase):
    """Schema for creating site setting."""
    pass


class CMSSiteSettingUpdate(BaseModel):
    """Schema for updating site setting."""
    setting_value: Optional[str] = None
    setting_type: Optional[str] = Field(None, max_length=50)
    label: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = None
    sort_order: Optional[int] = None


class CMSSiteSettingResponse(BaseResponseSchema):
    """Response schema for site setting."""
    id: UUID
    created_at: datetime
    updated_at: datetime


class CMSSiteSettingListResponse(BaseModel):
    """Response for listing site settings."""
    items: List[CMSSiteSettingResponse]
    total: int


class CMSSiteSettingBulkUpdate(BaseModel):
    """Schema for bulk updating site settings."""
    settings: dict[str, str] = Field(..., description="Key-value pairs of settings to update")


# ==================== Menu Item Schemas ====================

class CMSMenuItemBase(BaseModel):
    """Base schema for menu items."""
    menu_location: str = Field(..., max_length=50)
    title: str = Field(..., min_length=1, max_length=255)
    url: str = Field(..., min_length=1, max_length=500)
    icon: Optional[str] = Field(None, max_length=100)
    target: str = Field("_self", max_length=20)
    parent_id: Optional[UUID] = None
    sort_order: int = 0
    is_active: bool = True
    show_on_mobile: bool = True
    css_class: Optional[str] = Field(None, max_length=100)


class CMSMenuItemCreate(CMSMenuItemBase):
    """Schema for creating menu item."""
    pass


class CMSMenuItemUpdate(BaseModel):
    """Schema for updating menu item."""
    menu_location: Optional[str] = Field(None, max_length=50)
    title: Optional[str] = Field(None, max_length=255)
    url: Optional[str] = Field(None, max_length=500)
    icon: Optional[str] = Field(None, max_length=100)
    target: Optional[str] = Field(None, max_length=20)
    parent_id: Optional[UUID] = None
    sort_order: Optional[int] = None
    is_active: Optional[bool] = None
    show_on_mobile: Optional[bool] = None
    css_class: Optional[str] = Field(None, max_length=100)


class CMSMenuItemResponse(BaseResponseSchema):
    """Response schema for menu item."""
    id: UUID
    created_at: datetime
    updated_at: datetime


class CMSMenuItemListResponse(BaseModel):
    """Response for listing menu items."""
    items: List[CMSMenuItemResponse]
    total: int


# ==================== Feature Bar Schemas ====================

class CMSFeatureBarBase(BaseModel):
    """Base schema for feature bar items."""
    icon: str = Field(..., min_length=1, max_length=100)
    title: str = Field(..., min_length=1, max_length=255)
    subtitle: Optional[str] = Field(None, max_length=255)
    sort_order: int = 0
    is_active: bool = True


class CMSFeatureBarCreate(CMSFeatureBarBase):
    """Schema for creating feature bar item."""
    pass


class CMSFeatureBarUpdate(BaseModel):
    """Schema for updating feature bar item."""
    icon: Optional[str] = Field(None, max_length=100)
    title: Optional[str] = Field(None, max_length=255)
    subtitle: Optional[str] = Field(None, max_length=255)
    sort_order: Optional[int] = None
    is_active: Optional[bool] = None


class CMSFeatureBarResponse(BaseResponseSchema):
    """Response schema for feature bar item."""
    id: UUID
    created_at: datetime
    updated_at: datetime


class CMSFeatureBarListResponse(BaseModel):
    """Response for listing feature bar items."""
    items: List[CMSFeatureBarResponse]
    total: int


# ==================== Mega Menu Item Schemas ====================

class CMSMegaMenuItemBase(BaseModel):
    """Base schema for mega menu items."""
    title: str = Field(..., min_length=1, max_length=100)
    icon: Optional[str] = Field(None, max_length=50, description="Lucide icon name")
    image_url: Optional[str] = Field(None, max_length=500)
    menu_type: CMSMegaMenuItemType = CMSMegaMenuItemType.CATEGORY
    category_id: Optional[UUID] = Field(None, description="ERP category ID (for CATEGORY type)")
    url: Optional[str] = Field(None, max_length=500, description="Custom URL (for CUSTOM_LINK type)")
    target: str = Field("_self", pattern="^(_self|_blank)$")
    show_subcategories: bool = Field(True, description="Whether to show subcategories in dropdown")
    subcategory_ids: Optional[List[UUID]] = Field(None, description="Specific subcategory IDs to show (null = all)")
    sort_order: int = Field(0, ge=0)
    is_active: bool = True
    is_highlighted: bool = Field(False, description="Show highlight badge (e.g., 'New')")
    highlight_text: Optional[str] = Field(None, max_length=20, description="Text for highlight badge")


class CMSMegaMenuItemCreate(CMSMegaMenuItemBase):
    """Schema for creating a mega menu item."""
    pass


class CMSMegaMenuItemUpdate(BaseModel):
    """Schema for updating a mega menu item."""
    title: Optional[str] = Field(None, max_length=100)
    icon: Optional[str] = Field(None, max_length=50)
    image_url: Optional[str] = Field(None, max_length=500)
    menu_type: Optional[CMSMegaMenuItemType] = None
    category_id: Optional[UUID] = None
    url: Optional[str] = Field(None, max_length=500)
    target: Optional[str] = Field(None, pattern="^(_self|_blank)$")
    show_subcategories: Optional[bool] = None
    subcategory_ids: Optional[List[UUID]] = None
    sort_order: Optional[int] = Field(None, ge=0)
    is_active: Optional[bool] = None
    is_highlighted: Optional[bool] = None
    highlight_text: Optional[str] = Field(None, max_length=20)


class CMSMegaMenuItemResponse(BaseResponseSchema):
    """Response schema for mega menu item."""
    id: UUID
    company_id: Optional[UUID] = None
    created_at: datetime
    updated_at: datetime
    created_by: Optional[UUID] = None
    # Include category details if linked
    category_name: Optional[str] = None
    category_slug: Optional[str] = None


class CMSMegaMenuItemListResponse(BaseModel):
    """Response for listing mega menu items."""
    items: List[CMSMegaMenuItemResponse]
    total: int


# ==================== Storefront Mega Menu Response ====================

class StorefrontSubcategoryResponse(BaseModel):
    """Subcategory info for storefront mega menu."""
    id: str
    name: str
    slug: str
    image_url: Optional[str] = None
    product_count: int = 0


class StorefrontMegaMenuItemResponse(BaseModel):
    """Public mega menu item response for storefront."""
    id: str
    title: str
    icon: Optional[str] = None
    image_url: Optional[str] = None
    menu_type: str
    url: Optional[str] = None
    target: str = "_self"
    is_highlighted: bool = False
    highlight_text: Optional[str] = None
    # For CATEGORY type - resolved category data
    category_slug: Optional[str] = None
    subcategories: List[StorefrontSubcategoryResponse] = []


# ==================== Storefront Settings Response ====================

class StorefrontSettingsResponse(BaseModel):
    """Public settings response for storefront."""
    social: dict[str, str] = {}
    contact: dict[str, str] = {}
    footer: dict[str, str] = {}
    newsletter: dict[str, str] = {}


class StorefrontMenuItemResponse(BaseModel):
    """Public menu item response for storefront."""
    id: str
    menu_location: str
    title: str
    url: str
    icon: Optional[str] = None
    target: str = "_self"
    children: List["StorefrontMenuItemResponse"] = []


class StorefrontFeatureBarResponse(BaseModel):
    """Public feature bar response for storefront."""
    id: str
    icon: str
    title: str
    subtitle: Optional[str] = None


# ==================== FAQ Category Schemas ====================

class CMSFaqCategoryBase(BaseModel):
    """Base schema for FAQ Category."""
    name: str = Field(..., min_length=1, max_length=100)
    slug: str = Field(..., min_length=1, max_length=100, pattern=r"^[a-z0-9-]+$")
    description: Optional[str] = Field(None, max_length=500)
    icon: str = Field("HelpCircle", min_length=1, max_length=50, description="Lucide icon name")
    icon_color: Optional[str] = Field(None, max_length=50)
    sort_order: int = Field(0, ge=0)
    is_active: bool = True


class CMSFaqCategoryCreate(CMSFaqCategoryBase):
    """Schema for creating a FAQ category."""
    pass


class CMSFaqCategoryUpdate(BaseModel):
    """Schema for updating a FAQ category."""
    name: Optional[str] = Field(None, max_length=100)
    slug: Optional[str] = Field(None, max_length=100, pattern=r"^[a-z0-9-]+$")
    description: Optional[str] = Field(None, max_length=500)
    icon: Optional[str] = Field(None, max_length=50)
    icon_color: Optional[str] = Field(None, max_length=50)
    sort_order: Optional[int] = Field(None, ge=0)
    is_active: Optional[bool] = None


class CMSFaqCategoryResponse(BaseResponseSchema):
    """Response schema for FAQ category."""
    id: UUID
    name: str
    slug: str
    description: Optional[str] = None
    icon: str
    icon_color: Optional[str] = None
    sort_order: int
    is_active: bool
    created_at: datetime
    updated_at: datetime
    created_by: Optional[UUID] = None
    items_count: int = 0  # Computed field for number of items


class CMSFaqCategoryBrief(BaseModel):
    """Brief FAQ category info for lists."""
    id: UUID
    name: str
    slug: str
    icon: str
    is_active: bool
    sort_order: int
    items_count: int = 0

    model_config = ConfigDict(from_attributes=True)


class CMSFaqCategoryListResponse(BaseModel):
    """Paginated list of FAQ categories."""
    items: List[CMSFaqCategoryResponse]
    total: int


# ==================== FAQ Item Schemas ====================

class CMSFaqItemBase(BaseModel):
    """Base schema for FAQ Item."""
    category_id: UUID
    question: str = Field(..., min_length=1, max_length=500)
    answer: str = Field(..., min_length=1)
    keywords: List[str] = Field(default_factory=list, description="Search keywords")
    sort_order: int = Field(0, ge=0)
    is_featured: bool = False
    is_active: bool = True


class CMSFaqItemCreate(CMSFaqItemBase):
    """Schema for creating a FAQ item."""
    pass


class CMSFaqItemUpdate(BaseModel):
    """Schema for updating a FAQ item."""
    category_id: Optional[UUID] = None
    question: Optional[str] = Field(None, max_length=500)
    answer: Optional[str] = None
    keywords: Optional[List[str]] = None
    sort_order: Optional[int] = Field(None, ge=0)
    is_featured: Optional[bool] = None
    is_active: Optional[bool] = None


class CMSFaqItemResponse(BaseResponseSchema):
    """Response schema for FAQ item."""
    id: UUID
    category_id: UUID
    question: str
    answer: str
    keywords: List[str] = []
    sort_order: int
    is_featured: bool
    is_active: bool
    view_count: int = 0
    helpful_count: int = 0
    created_at: datetime
    updated_at: datetime
    created_by: Optional[UUID] = None


class CMSFaqItemBrief(BaseModel):
    """Brief FAQ item info for lists."""
    id: UUID
    question: str
    is_featured: bool
    is_active: bool
    sort_order: int

    model_config = ConfigDict(from_attributes=True)


class CMSFaqItemListResponse(BaseModel):
    """Paginated list of FAQ items."""
    items: List[CMSFaqItemResponse]
    total: int


# ==================== Storefront FAQ Schemas ====================

class StorefrontFaqItemResponse(BaseModel):
    """Public FAQ item for storefront."""
    id: str
    question: str
    answer: str
    keywords: List[str] = []

    model_config = ConfigDict(from_attributes=True)


class StorefrontFaqCategoryResponse(BaseModel):
    """Public FAQ category with items for storefront."""
    id: str
    name: str
    slug: str
    icon: str
    icon_color: Optional[str] = None
    items: List[StorefrontFaqItemResponse] = []

    model_config = ConfigDict(from_attributes=True)


class StorefrontFaqResponse(BaseModel):
    """Complete FAQ response for storefront."""
    categories: List[StorefrontFaqCategoryResponse] = []
    total_items: int = 0


# ==================== Video Guide Schemas ====================

class VideoGuideCategoryEnum(str, Enum):
    INSTALLATION = "INSTALLATION"
    MAINTENANCE = "MAINTENANCE"
    TROUBLESHOOTING = "TROUBLESHOOTING"
    PRODUCT_TOUR = "PRODUCT_TOUR"
    HOW_TO = "HOW_TO"
    TIPS = "TIPS"


class VideoGuideVideoTypeEnum(str, Enum):
    YOUTUBE = "YOUTUBE"
    VIMEO = "VIMEO"
    DIRECT = "DIRECT"


class CMSVideoGuideBase(BaseModel):
    """Base schema for Video Guide."""
    title: str = Field(..., min_length=1, max_length=255)
    slug: str = Field(..., min_length=1, max_length=255, pattern=r"^[a-z0-9-]+$")
    description: Optional[str] = Field(None)
    thumbnail_url: str = Field(..., max_length=500)
    video_url: str = Field(..., max_length=500)
    video_type: str = Field("YOUTUBE", pattern=r"^(YOUTUBE|VIMEO|DIRECT)$")
    video_id: Optional[str] = Field(None, max_length=50, description="YouTube/Vimeo video ID")
    duration_seconds: Optional[int] = Field(None, ge=0)
    category: str = Field("HOW_TO", description="INSTALLATION, MAINTENANCE, TROUBLESHOOTING, PRODUCT_TOUR, HOW_TO, TIPS")
    tags: Optional[List[str]] = Field(default_factory=list)
    product_id: Optional[UUID] = None
    product_category_id: Optional[UUID] = None
    sort_order: int = Field(0, ge=0)
    is_featured: bool = False
    is_active: bool = True


class CMSVideoGuideCreate(CMSVideoGuideBase):
    """Schema for creating a video guide."""
    pass


class CMSVideoGuideUpdate(BaseModel):
    """Schema for updating a video guide."""
    title: Optional[str] = Field(None, max_length=255)
    slug: Optional[str] = Field(None, max_length=255, pattern=r"^[a-z0-9-]+$")
    description: Optional[str] = None
    thumbnail_url: Optional[str] = Field(None, max_length=500)
    video_url: Optional[str] = Field(None, max_length=500)
    video_type: Optional[str] = Field(None, pattern=r"^(YOUTUBE|VIMEO|DIRECT)$")
    video_id: Optional[str] = Field(None, max_length=50)
    duration_seconds: Optional[int] = Field(None, ge=0)
    category: Optional[str] = None
    tags: Optional[List[str]] = None
    product_id: Optional[UUID] = None
    product_category_id: Optional[UUID] = None
    sort_order: Optional[int] = Field(None, ge=0)
    is_featured: Optional[bool] = None
    is_active: Optional[bool] = None


class CMSVideoGuideResponse(BaseResponseSchema):
    """Response schema for video guide."""
    id: UUID
    title: str
    slug: str
    description: Optional[str] = None
    thumbnail_url: str
    video_url: str
    video_type: str
    video_id: Optional[str] = None
    duration_seconds: Optional[int] = None
    category: str
    tags: Optional[List[str]] = []
    product_id: Optional[UUID] = None
    product_category_id: Optional[UUID] = None
    sort_order: int
    is_featured: bool
    is_active: bool
    view_count: int = 0
    like_count: int = 0
    created_at: datetime
    updated_at: datetime
    created_by: Optional[UUID] = None


class CMSVideoGuideBrief(BaseModel):
    """Brief video guide info for lists."""
    id: UUID
    title: str
    slug: str
    thumbnail_url: str
    category: str
    is_featured: bool
    is_active: bool
    sort_order: int
    view_count: int = 0

    model_config = ConfigDict(from_attributes=True)


class CMSVideoGuideListResponse(BaseModel):
    """Paginated list of video guides."""
    items: List[CMSVideoGuideResponse]
    total: int
