"""Add CMS tables for D2C content management

Revision ID: 20260121_cms
Revises: fix_abandoned_carts_cols
Create Date: 2026-01-21 09:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '20260121_cms'
down_revision: Union[str, None] = 'fix_abandoned_carts_cols'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ==================== CMS Banners ====================
    op.create_table(
        'cms_banners',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('title', sa.String(200), nullable=False),
        sa.Column('subtitle', sa.String(500), nullable=True),
        sa.Column('image_url', sa.String(500), nullable=False),
        sa.Column('thumbnail_url', sa.String(500), nullable=True),
        sa.Column('mobile_image_url', sa.String(500), nullable=True),
        sa.Column('cta_text', sa.String(100), nullable=True),
        sa.Column('cta_link', sa.String(500), nullable=True),
        sa.Column('text_position', sa.String(20), server_default='left', nullable=False),
        sa.Column('text_color', sa.String(20), server_default='white', nullable=False),
        sa.Column('sort_order', sa.Integer, server_default='0', nullable=False),
        sa.Column('is_active', sa.Boolean, server_default='true', nullable=False),
        sa.Column('starts_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('ends_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
    )
    op.create_index('ix_cms_banners_is_active', 'cms_banners', ['is_active'])
    op.create_index('ix_cms_banners_sort_order', 'cms_banners', ['sort_order'])

    # ==================== CMS USPs ====================
    op.create_table(
        'cms_usps',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('title', sa.String(100), nullable=False),
        sa.Column('description', sa.String(300), nullable=True),
        sa.Column('icon', sa.String(50), nullable=False),
        sa.Column('icon_color', sa.String(50), nullable=True),
        sa.Column('link_url', sa.String(500), nullable=True),
        sa.Column('link_text', sa.String(100), nullable=True),
        sa.Column('sort_order', sa.Integer, server_default='0', nullable=False),
        sa.Column('is_active', sa.Boolean, server_default='true', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
    )
    op.create_index('ix_cms_usps_is_active', 'cms_usps', ['is_active'])
    op.create_index('ix_cms_usps_sort_order', 'cms_usps', ['sort_order'])

    # ==================== CMS Testimonials ====================
    op.create_table(
        'cms_testimonials',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('customer_name', sa.String(100), nullable=False),
        sa.Column('customer_location', sa.String(100), nullable=True),
        sa.Column('customer_avatar_url', sa.String(500), nullable=True),
        sa.Column('customer_designation', sa.String(100), nullable=True),
        sa.Column('rating', sa.Integer, nullable=False),
        sa.Column('content', sa.Text, nullable=False),
        sa.Column('title', sa.String(200), nullable=True),
        sa.Column('product_name', sa.String(200), nullable=True),
        sa.Column('product_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('products.id', ondelete='SET NULL'), nullable=True),
        sa.Column('sort_order', sa.Integer, server_default='0', nullable=False),
        sa.Column('is_featured', sa.Boolean, server_default='false', nullable=False),
        sa.Column('is_active', sa.Boolean, server_default='true', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.CheckConstraint('rating >= 1 AND rating <= 5', name='check_testimonial_rating'),
    )
    op.create_index('ix_cms_testimonials_is_active', 'cms_testimonials', ['is_active'])
    op.create_index('ix_cms_testimonials_is_featured', 'cms_testimonials', ['is_featured'])

    # ==================== CMS Announcements ====================
    op.create_table(
        'cms_announcements',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('text', sa.String(500), nullable=False),
        sa.Column('link_url', sa.String(500), nullable=True),
        sa.Column('link_text', sa.String(100), nullable=True),
        sa.Column('announcement_type', sa.String(20), server_default='INFO', nullable=False),
        sa.Column('background_color', sa.String(50), nullable=True),
        sa.Column('text_color', sa.String(50), nullable=True),
        sa.Column('starts_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('ends_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('sort_order', sa.Integer, server_default='0', nullable=False),
        sa.Column('is_dismissible', sa.Boolean, server_default='true', nullable=False),
        sa.Column('is_active', sa.Boolean, server_default='true', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
    )
    op.create_index('ix_cms_announcements_is_active', 'cms_announcements', ['is_active'])

    # ==================== CMS Pages ====================
    op.create_table(
        'cms_pages',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('title', sa.String(200), nullable=False),
        sa.Column('slug', sa.String(200), nullable=False, unique=True),
        sa.Column('content', sa.Text, nullable=True),
        sa.Column('excerpt', sa.String(500), nullable=True),
        sa.Column('meta_title', sa.String(200), nullable=True),
        sa.Column('meta_description', sa.String(500), nullable=True),
        sa.Column('meta_keywords', sa.String(500), nullable=True),
        sa.Column('og_image_url', sa.String(500), nullable=True),
        sa.Column('canonical_url', sa.String(500), nullable=True),
        sa.Column('status', sa.String(20), server_default='DRAFT', nullable=False),
        sa.Column('published_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('template', sa.String(50), server_default='default', nullable=False),
        sa.Column('show_in_footer', sa.Boolean, server_default='false', nullable=False),
        sa.Column('show_in_header', sa.Boolean, server_default='false', nullable=False),
        sa.Column('sort_order', sa.Integer, server_default='0', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('updated_by', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
    )
    op.create_index('ix_cms_pages_slug', 'cms_pages', ['slug'], unique=True)
    op.create_index('ix_cms_pages_status', 'cms_pages', ['status'])

    # ==================== CMS Page Versions ====================
    op.create_table(
        'cms_page_versions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('page_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('cms_pages.id', ondelete='CASCADE'), nullable=False),
        sa.Column('version_number', sa.Integer, nullable=False),
        sa.Column('title', sa.String(200), nullable=False),
        sa.Column('content', sa.Text, nullable=True),
        sa.Column('meta_title', sa.String(200), nullable=True),
        sa.Column('meta_description', sa.String(500), nullable=True),
        sa.Column('change_summary', sa.String(500), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
    )
    op.create_index('ix_cms_page_versions_page_id', 'cms_page_versions', ['page_id'])

    # ==================== CMS SEO Settings ====================
    op.create_table(
        'cms_seo',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('url_path', sa.String(500), nullable=False, unique=True),
        sa.Column('meta_title', sa.String(200), nullable=True),
        sa.Column('meta_description', sa.String(500), nullable=True),
        sa.Column('meta_keywords', sa.String(500), nullable=True),
        sa.Column('og_title', sa.String(200), nullable=True),
        sa.Column('og_description', sa.String(500), nullable=True),
        sa.Column('og_image_url', sa.String(500), nullable=True),
        sa.Column('og_type', sa.String(50), server_default='website', nullable=False),
        sa.Column('canonical_url', sa.String(500), nullable=True),
        sa.Column('robots_index', sa.Boolean, server_default='true', nullable=False),
        sa.Column('robots_follow', sa.Boolean, server_default='true', nullable=False),
        sa.Column('structured_data', postgresql.JSONB, nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
    )
    op.create_index('ix_cms_seo_url_path', 'cms_seo', ['url_path'], unique=True)


def downgrade() -> None:
    op.drop_table('cms_seo')
    op.drop_table('cms_page_versions')
    op.drop_table('cms_pages')
    op.drop_table('cms_announcements')
    op.drop_table('cms_testimonials')
    op.drop_table('cms_usps')
    op.drop_table('cms_banners')
