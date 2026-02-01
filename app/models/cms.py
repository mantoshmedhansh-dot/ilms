"""
CMS Models for D2C Storefront Content Management

Content types:
- CMSBanner: Hero banners with images, CTAs, scheduling
- CMSUsp: USPs/Features with icons
- CMSTestimonial: Customer testimonials
- CMSAnnouncement: Announcement bar messages
- CMSPage: Static pages with rich text content
- CMSPageVersion: Version history for pages
- CMSSeo: SEO settings per page
- CMSFaqCategory: FAQ categories for organization
- CMSFaqItem: FAQ questions and answers
"""

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import TYPE_CHECKING, Optional, List

from sqlalchemy import String, Boolean, DateTime, ForeignKey, Integer, Text, CheckConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB

from app.database import Base

if TYPE_CHECKING:
    from app.models.user import User


# ==================== Enums (stored as VARCHAR in DB) ====================

class CMSPageStatus(str, Enum):
    """Page publish status"""
    DRAFT = "DRAFT"
    PUBLISHED = "PUBLISHED"
    ARCHIVED = "ARCHIVED"


class CMSAnnouncementType(str, Enum):
    """Announcement bar type/style"""
    INFO = "INFO"
    WARNING = "WARNING"
    PROMO = "PROMO"
    SUCCESS = "SUCCESS"


# ==================== CMS Banner Model ====================

class CMSBanner(Base):
    """
    Hero banner for D2C storefront homepage.
    Supports scheduling, multiple banners with sort order.
    """
    __tablename__ = "cms_banners"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )

    # Content
    title: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
        comment="Banner headline"
    )
    subtitle: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
        comment="Banner subheadline/description"
    )
    image_url: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
        comment="Full-size banner image URL"
    )
    thumbnail_url: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
        comment="Thumbnail image for admin preview"
    )
    mobile_image_url: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
        comment="Mobile-optimized image URL"
    )

    # CTA (Call to Action)
    cta_text: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        comment="Button text e.g., 'Shop Now'"
    )
    cta_link: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
        comment="Button link URL"
    )

    # Positioning
    text_position: Mapped[str] = mapped_column(
        String(20),
        default="left",
        nullable=False,
        comment="Text alignment: left, center, right"
    )
    text_color: Mapped[str] = mapped_column(
        String(20),
        default="white",
        nullable=False,
        comment="Text color: white, dark"
    )

    # Display settings
    sort_order: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        comment="Display order (lower = first)"
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False
    )

    # Scheduling
    starts_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Start showing banner at this time"
    )
    ends_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Stop showing banner after this time"
    )

    # Audit
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False
    )
    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )

    # Relationships
    creator: Mapped[Optional["User"]] = relationship("User", foreign_keys=[created_by])

    def __repr__(self) -> str:
        return f"<CMSBanner(title='{self.title}', active={self.is_active})>"


# ==================== CMS USP Model ====================

class CMSUsp(Base):
    """
    USPs (Unique Selling Points) / Features for homepage.
    E.g., "Free Installation", "2 Year Warranty", etc.
    """
    __tablename__ = "cms_usps"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )

    # Content
    title: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="USP headline"
    )
    description: Mapped[Optional[str]] = mapped_column(
        String(300),
        nullable=True,
        comment="Short description"
    )
    icon: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="Lucide icon name e.g., 'truck', 'shield-check'"
    )
    icon_color: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        comment="Icon color class e.g., 'text-blue-500'"
    )

    # Link (optional)
    link_url: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True
    )
    link_text: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True
    )

    # Display
    sort_order: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False
    )

    # Audit
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False
    )
    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )

    def __repr__(self) -> str:
        return f"<CMSUsp(title='{self.title}', icon='{self.icon}')>"


# ==================== CMS Testimonial Model ====================

class CMSTestimonial(Base):
    """
    Customer testimonials for homepage.
    """
    __tablename__ = "cms_testimonials"
    __table_args__ = (
        CheckConstraint('rating >= 1 AND rating <= 5', name='check_testimonial_rating'),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )

    # Customer info
    customer_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False
    )
    customer_location: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        comment="City/State"
    )
    customer_avatar_url: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True
    )
    customer_designation: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        comment="Job title or role (optional)"
    )

    # Review content
    rating: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Rating from 1-5 stars"
    )
    content: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="Testimonial text"
    )
    title: Mapped[Optional[str]] = mapped_column(
        String(200),
        nullable=True,
        comment="Review title/headline"
    )

    # Product reference (optional)
    product_name: Mapped[Optional[str]] = mapped_column(
        String(200),
        nullable=True,
        comment="Product being reviewed"
    )
    product_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("products.id", ondelete="SET NULL"),
        nullable=True
    )

    # Display
    sort_order: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False
    )
    is_featured: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        comment="Featured testimonials shown first"
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False
    )

    # Audit
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False
    )
    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )

    def __repr__(self) -> str:
        return f"<CMSTestimonial(customer='{self.customer_name}', rating={self.rating})>"


# ==================== CMS Announcement Model ====================

class CMSAnnouncement(Base):
    """
    Announcement bar messages for storefront header.
    E.g., "Free shipping on orders above ₹999!"
    """
    __tablename__ = "cms_announcements"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )

    # Content
    text: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
        comment="Announcement message"
    )
    link_url: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
        comment="Link when clicked"
    )
    link_text: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        comment="Link text e.g., 'Learn More'"
    )

    # Style
    announcement_type: Mapped[str] = mapped_column(
        String(20),
        default="INFO",
        nullable=False,
        comment="INFO, WARNING, PROMO, SUCCESS"
    )
    background_color: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        comment="Custom background color"
    )
    text_color: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        comment="Custom text color"
    )

    # Scheduling
    starts_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )
    ends_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )

    # Display
    sort_order: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False
    )
    is_dismissible: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        comment="Can user close this announcement"
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False
    )

    # Audit
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False
    )
    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )

    def __repr__(self) -> str:
        return f"<CMSAnnouncement(text='{self.text[:50]}...', type={self.announcement_type})>"


# ==================== CMS Page Model ====================

class CMSPage(Base):
    """
    Static pages with rich text content.
    E.g., About Us, Privacy Policy, Terms & Conditions.
    """
    __tablename__ = "cms_pages"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )

    # Identification
    title: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
        comment="Page title"
    )
    slug: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
        unique=True,
        index=True,
        comment="URL slug e.g., 'about-us'"
    )

    # Content
    content: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Rich text HTML content"
    )
    excerpt: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
        comment="Short summary for listings"
    )

    # SEO
    meta_title: Mapped[Optional[str]] = mapped_column(
        String(200),
        nullable=True,
        comment="SEO meta title"
    )
    meta_description: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
        comment="SEO meta description"
    )
    meta_keywords: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
        comment="SEO keywords (comma-separated)"
    )
    og_image_url: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
        comment="Open Graph image URL"
    )
    canonical_url: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
        comment="Canonical URL if different"
    )

    # Status
    status: Mapped[str] = mapped_column(
        String(20),
        default="DRAFT",
        nullable=False,
        comment="DRAFT, PUBLISHED, ARCHIVED"
    )
    published_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="When page was published"
    )

    # Template
    template: Mapped[str] = mapped_column(
        String(50),
        default="default",
        nullable=False,
        comment="Page template: default, full-width, landing"
    )

    # Navigation
    show_in_footer: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False
    )
    show_in_header: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False
    )
    sort_order: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False
    )

    # Audit
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False
    )
    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )
    updated_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )

    # Relationships
    versions: Mapped[List["CMSPageVersion"]] = relationship(
        "CMSPageVersion",
        back_populates="page",
        cascade="all, delete-orphan",
        order_by="CMSPageVersion.version_number.desc()"
    )
    creator: Mapped[Optional["User"]] = relationship("User", foreign_keys=[created_by])
    updater: Mapped[Optional["User"]] = relationship("User", foreign_keys=[updated_by])

    def __repr__(self) -> str:
        return f"<CMSPage(title='{self.title}', slug='{self.slug}', status={self.status})>"


# ==================== CMS Page Version Model ====================

class CMSPageVersion(Base):
    """
    Version history for CMS pages.
    Created automatically when a page is updated.
    """
    __tablename__ = "cms_page_versions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )

    # Page reference
    page_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cms_pages.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    version_number: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Sequential version number"
    )

    # Snapshot of content at this version
    title: Mapped[str] = mapped_column(
        String(200),
        nullable=False
    )
    content: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True
    )
    meta_title: Mapped[Optional[str]] = mapped_column(
        String(200),
        nullable=True
    )
    meta_description: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True
    )

    # Change metadata
    change_summary: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
        comment="Description of changes in this version"
    )

    # Audit
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )
    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )

    # Relationships
    page: Mapped["CMSPage"] = relationship("CMSPage", back_populates="versions")
    creator: Mapped[Optional["User"]] = relationship("User", foreign_keys=[created_by])

    def __repr__(self) -> str:
        return f"<CMSPageVersion(page_id={self.page_id}, version={self.version_number})>"


# ==================== CMS SEO Settings Model ====================

class CMSSeo(Base):
    """
    SEO settings for specific routes/pages.
    Allows overriding default SEO for any URL path.
    """
    __tablename__ = "cms_seo"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )

    # URL/Route
    url_path: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
        unique=True,
        index=True,
        comment="URL path e.g., '/', '/products', '/products/aqua-ro'"
    )

    # SEO fields
    meta_title: Mapped[Optional[str]] = mapped_column(
        String(200),
        nullable=True
    )
    meta_description: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True
    )
    meta_keywords: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True
    )
    og_title: Mapped[Optional[str]] = mapped_column(
        String(200),
        nullable=True
    )
    og_description: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True
    )
    og_image_url: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True
    )
    og_type: Mapped[str] = mapped_column(
        String(50),
        default="website",
        nullable=False
    )
    canonical_url: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True
    )

    # Robots
    robots_index: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        comment="Allow search engine indexing"
    )
    robots_follow: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        comment="Allow following links"
    )

    # Structured data (JSON-LD)
    structured_data: Mapped[Optional[dict]] = mapped_column(
        JSONB,
        nullable=True,
        comment="JSON-LD structured data"
    )

    # Audit
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False
    )
    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )

    def __repr__(self) -> str:
        return f"<CMSSeo(url_path='{self.url_path}')>"


# ==================== CMS Site Settings Model ====================

class CMSSiteSetting(Base):
    """
    Key-value store for site-wide settings.
    E.g., social links, contact overrides, footer text.
    """
    __tablename__ = "cms_site_settings"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )

    setting_key: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        unique=True,
        index=True,
        comment="Unique key e.g., 'social_facebook'"
    )
    setting_value: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Setting value"
    )
    setting_type: Mapped[str] = mapped_column(
        String(50),
        default="text",
        nullable=False,
        comment="text, textarea, url, boolean, number"
    )
    setting_group: Mapped[str] = mapped_column(
        String(50),
        default="general",
        nullable=False,
        comment="Group: social, contact, footer, newsletter"
    )
    label: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        comment="Human-readable label"
    )
    description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Help text for admin"
    )
    sort_order: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    def __repr__(self) -> str:
        return f"<CMSSiteSetting(key='{self.setting_key}', group='{self.setting_group}')>"


# ==================== CMS Menu Item Model ====================

class CMSMenuItem(Base):
    """
    Navigation menu items for header and footer.
    Supports hierarchical menus with parent-child relationships.
    """
    __tablename__ = "cms_menu_items"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )

    menu_location: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
        comment="header, footer_quick, footer_service"
    )
    title: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Menu item text"
    )
    url: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
        comment="Link URL"
    )
    icon: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        comment="Lucide icon name"
    )
    target: Mapped[str] = mapped_column(
        String(20),
        default="_self",
        nullable=False,
        comment="_self or _blank"
    )
    parent_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cms_menu_items.id", ondelete="CASCADE"),
        nullable=True,
        comment="Parent menu item for dropdowns"
    )
    sort_order: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False
    )
    show_on_mobile: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False
    )
    css_class: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        comment="Custom CSS class"
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    # Self-referential relationship for hierarchical menus
    children: Mapped[List["CMSMenuItem"]] = relationship(
        "CMSMenuItem",
        back_populates="parent",
        cascade="all, delete-orphan"
    )
    parent: Mapped[Optional["CMSMenuItem"]] = relationship(
        "CMSMenuItem",
        back_populates="children",
        remote_side=[id]
    )

    def __repr__(self) -> str:
        return f"<CMSMenuItem(title='{self.title}', location='{self.menu_location}')>"


# ==================== CMS Feature Bar Model ====================

class CMSFeatureBar(Base):
    """
    Feature bar items shown above footer.
    E.g., Free Shipping, Secure Payment, 24/7 Support.
    """
    __tablename__ = "cms_feature_bars"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )

    icon: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="Lucide icon name"
    )
    title: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Feature title"
    )
    subtitle: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        comment="Feature description"
    )
    sort_order: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    def __repr__(self) -> str:
        return f"<CMSFeatureBar(title='{self.title}', icon='{self.icon}')>"


# ==================== CMS Mega Menu Item Model ====================

class CMSMegaMenuItemType(str, Enum):
    """Type of mega menu item"""
    CATEGORY = "CATEGORY"       # Links to ERP category with subcategories
    CUSTOM_LINK = "CUSTOM_LINK" # Custom URL link


class CMSMegaMenuItem(Base):
    """
    Mega menu items for D2C storefront navigation.
    Allows admin to control which categories appear in the mega menu,
    select specific subcategories, and add custom links.

    Similar to Eureka Forbes / Atomberg navigation structure.
    """
    __tablename__ = "cms_mega_menu_items"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )

    # Display
    title: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="Display title (can override category name)"
    )
    icon: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        comment="Lucide icon name for the menu item"
    )
    image_url: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
        comment="Optional image for the menu item"
    )

    # Type and linking
    menu_type: Mapped[str] = mapped_column(
        String(20),
        default="CATEGORY",
        nullable=False,
        comment="CATEGORY or CUSTOM_LINK"
    )

    # For CATEGORY type: link to ERP category
    category_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("categories.id", ondelete="CASCADE"),
        nullable=True,
        comment="ERP category ID (for CATEGORY type)"
    )

    # For CUSTOM_LINK type: custom URL
    url: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
        comment="Custom URL (for CUSTOM_LINK type)"
    )
    target: Mapped[str] = mapped_column(
        String(20),
        default="_self",
        nullable=False,
        comment="Link target: _self or _blank"
    )

    # Subcategory control (for CATEGORY type)
    show_subcategories: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        comment="Whether to show subcategories in dropdown"
    )
    subcategory_ids: Mapped[Optional[dict]] = mapped_column(
        JSONB,
        nullable=True,
        comment="Specific subcategory IDs to show (null = all active subcategories)"
    )

    # Display settings
    sort_order: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False
    )
    is_highlighted: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        comment="Highlight this item (e.g., 'New' badge)"
    )
    highlight_text: Mapped[Optional[str]] = mapped_column(
        String(20),
        nullable=True,
        comment="Text for highlight badge e.g., 'New', 'Sale'"
    )

    # Multi-tenant
    company_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=True
    )

    # Audit
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False
    )
    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )

    # Relationships
    category = relationship("Category", foreign_keys=[category_id])

    def __repr__(self) -> str:
        return f"<CMSMegaMenuItem(title='{self.title}', type={self.menu_type})>"


# ==================== Demo Booking Model ====================

class DemoBookingStatus(str, Enum):
    """Demo booking status"""
    PENDING = "PENDING"
    CONFIRMED = "CONFIRMED"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"
    NO_SHOW = "NO_SHOW"


class DemoBooking(Base):
    """
    Demo booking requests from customers on the D2C storefront.
    Allows customers to book video call or phone call demos for products.
    """
    __tablename__ = "demo_bookings"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )

    # Customer info (may or may not be registered)
    customer_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("customers.id", ondelete="SET NULL"),
        nullable=True,
        comment="Linked customer if logged in"
    )
    customer_name: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
        comment="Customer's name"
    )
    phone: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        index=True,
        comment="Customer's phone number"
    )
    email: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        comment="Customer's email"
    )
    address: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
        comment="Customer's address"
    )
    pincode: Mapped[Optional[str]] = mapped_column(
        String(10),
        nullable=True,
        comment="Customer's pincode"
    )

    # Product info
    product_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("products.id", ondelete="SET NULL"),
        nullable=True,
        comment="Product for which demo is requested"
    )
    product_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Product name at booking time"
    )

    # Demo details
    demo_type: Mapped[str] = mapped_column(
        String(20),
        default="VIDEO",
        nullable=False,
        comment="VIDEO or PHONE"
    )
    preferred_date: Mapped[Optional[str]] = mapped_column(
        String(20),
        nullable=True,
        comment="Preferred date (YYYY-MM-DD)"
    )
    preferred_time: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        comment="Preferred time slot"
    )
    notes: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Customer's questions or notes"
    )

    # Status
    status: Mapped[str] = mapped_column(
        String(20),
        default="PENDING",
        nullable=False,
        comment="PENDING, CONFIRMED, COMPLETED, CANCELLED, NO_SHOW"
    )
    booking_number: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        unique=True,
        index=True,
        comment="Unique booking reference number"
    )

    # Assignment
    assigned_to: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        comment="Sales rep assigned to this demo"
    )
    confirmed_date: Mapped[Optional[str]] = mapped_column(
        String(20),
        nullable=True,
        comment="Confirmed date for the demo"
    )
    confirmed_time: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        comment="Confirmed time slot"
    )

    # Outcome
    outcome: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        comment="CONVERTED, NOT_INTERESTED, FOLLOW_UP, etc."
    )
    outcome_notes: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Notes from the demo session"
    )

    # Source tracking
    source: Mapped[str] = mapped_column(
        String(50),
        default="WEBSITE",
        nullable=False,
        comment="WEBSITE, MOBILE_APP, WHATSAPP, etc."
    )
    utm_source: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True
    )
    utm_medium: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True
    )
    utm_campaign: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True
    )

    # Audit
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    # Relationships
    customer = relationship("Customer", foreign_keys=[customer_id])
    product = relationship("Product", foreign_keys=[product_id])
    assignee = relationship("User", foreign_keys=[assigned_to])

    def __repr__(self) -> str:
        return f"<DemoBooking(id={self.id}, customer='{self.customer_name}', product='{self.product_name}', status={self.status})>"


# ==================== Video Guide Model ====================

class VideoGuideCategory(str, Enum):
    """Video guide categories"""
    INSTALLATION = "INSTALLATION"
    MAINTENANCE = "MAINTENANCE"
    TROUBLESHOOTING = "TROUBLESHOOTING"
    PRODUCT_TOUR = "PRODUCT_TOUR"
    HOW_TO = "HOW_TO"
    TIPS = "TIPS"


class VideoGuide(Base):
    """
    Video guides for D2C storefront.
    Educational content like installation guides, maintenance tips, troubleshooting, etc.
    """
    __tablename__ = "video_guides"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )

    # Content
    title: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Video title"
    )
    slug: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        unique=True,
        index=True,
        comment="URL slug"
    )
    description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Video description"
    )
    thumbnail_url: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
        comment="Thumbnail image URL"
    )

    # Video source
    video_url: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
        comment="Video URL (YouTube, Vimeo, or direct)"
    )
    video_type: Mapped[str] = mapped_column(
        String(20),
        default="YOUTUBE",
        nullable=False,
        comment="YOUTUBE, VIMEO, DIRECT"
    )
    video_id: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        comment="YouTube/Vimeo video ID"
    )
    duration_seconds: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        comment="Video duration in seconds"
    )

    # Categorization
    category: Mapped[str] = mapped_column(
        String(50),
        default="HOW_TO",
        nullable=False,
        comment="INSTALLATION, MAINTENANCE, TROUBLESHOOTING, PRODUCT_TOUR, HOW_TO, TIPS"
    )
    tags: Mapped[Optional[dict]] = mapped_column(
        JSONB,
        nullable=True,
        comment="Tags as JSON array"
    )

    # Product association
    product_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("products.id", ondelete="SET NULL"),
        nullable=True,
        comment="Associated product (null = general guide)"
    )
    product_category_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("categories.id", ondelete="SET NULL"),
        nullable=True,
        comment="Associated product category"
    )

    # Display
    sort_order: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False
    )
    is_featured: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False
    )

    # Stats
    view_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False
    )
    like_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False
    )

    # Audit
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False
    )
    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )

    # Relationships
    product = relationship("Product", foreign_keys=[product_id])
    product_category = relationship("Category", foreign_keys=[product_category_id])
    creator: Mapped[Optional["User"]] = relationship("User", foreign_keys=[created_by])

    def __repr__(self) -> str:
        return f"<VideoGuide(title='{self.title}', category={self.category})>"


# ==================== FAQ Category Model ====================

class CMSFaqCategory(Base):
    """
    FAQ categories for organizing FAQ items by topic.
    E.g., "Orders & Shopping", "Shipping & Delivery", "Payment & EMI"
    """
    __tablename__ = "cms_faq_categories"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )

    # Content
    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="Category display name"
    )
    slug: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        unique=True,
        comment="URL-friendly identifier"
    )
    description: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
        comment="Category description"
    )
    icon: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="HelpCircle",
        comment="Lucide icon name"
    )
    icon_color: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        comment="Optional icon color"
    )

    # Display
    sort_order: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False
    )

    # Audit
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False
    )
    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )

    # Relationships
    items: Mapped[List["CMSFaqItem"]] = relationship(
        "CMSFaqItem",
        back_populates="category",
        cascade="all, delete-orphan",
        order_by="CMSFaqItem.sort_order"
    )
    creator: Mapped[Optional["User"]] = relationship("User", foreign_keys=[created_by])

    def __repr__(self) -> str:
        return f"<CMSFaqCategory(name='{self.name}', slug='{self.slug}')>"


# ==================== FAQ Item Model ====================

class CMSFaqItem(Base):
    """
    Individual FAQ question and answer.
    Belongs to a FAQ category for organization.
    """
    __tablename__ = "cms_faq_items"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )

    # Category relationship
    category_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cms_faq_categories.id", ondelete="CASCADE"),
        nullable=False
    )

    # Content
    question: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
        comment="FAQ question"
    )
    answer: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="FAQ answer (supports rich text)"
    )
    keywords: Mapped[Optional[dict]] = mapped_column(
        JSONB,
        default=list,
        nullable=True,
        comment="Search keywords as JSON array"
    )

    # Display
    sort_order: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False
    )
    is_featured: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        comment="Show in featured/popular section"
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False
    )

    # Stats
    view_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False
    )
    helpful_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        comment="Users who found this helpful"
    )

    # Audit
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False
    )
    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )

    # Relationships
    category: Mapped["CMSFaqCategory"] = relationship(
        "CMSFaqCategory",
        back_populates="items"
    )
    creator: Mapped[Optional["User"]] = relationship("User", foreign_keys=[created_by])

    def __repr__(self) -> str:
        return f"<CMSFaqItem(question='{self.question[:50]}...')>"
