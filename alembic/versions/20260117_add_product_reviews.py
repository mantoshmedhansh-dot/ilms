"""Add product reviews tables

Revision ID: 20260117_reviews
Revises:
Create Date: 2026-01-17

Adds tables for product reviews:
- product_reviews: Customer reviews and ratings
- review_helpful: Helpful vote tracking
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy import text


# revision identifiers, used by Alembic.
revision = '20260117_reviews'
down_revision = None  # Will be filled automatically
branch_labels = None
depends_on = None


def table_exists(table_name: str) -> bool:
    """Check if a table exists."""
    conn = op.get_bind()
    result = conn.execute(text(f"""
        SELECT EXISTS (
            SELECT 1 FROM information_schema.tables
            WHERE table_name = '{table_name}'
        )
    """))
    return result.scalar()


def upgrade() -> None:
    """Create product reviews tables."""

    # Create product_reviews table
    if not table_exists('product_reviews'):
        op.create_table(
            'product_reviews',
            sa.Column('id', UUID(as_uuid=True), primary_key=True),
            sa.Column('product_id', UUID(as_uuid=True), sa.ForeignKey('products.id', ondelete='CASCADE'), nullable=False),
            sa.Column('customer_id', UUID(as_uuid=True), sa.ForeignKey('customers.id', ondelete='CASCADE'), nullable=False),
            sa.Column('order_id', UUID(as_uuid=True), sa.ForeignKey('orders.id', ondelete='SET NULL'), nullable=True),
            sa.Column('rating', sa.Integer, nullable=False),
            sa.Column('title', sa.String(200), nullable=True),
            sa.Column('review_text', sa.Text, nullable=True),
            sa.Column('is_verified_purchase', sa.Boolean, nullable=False, server_default='false'),
            sa.Column('is_approved', sa.Boolean, nullable=False, server_default='true'),
            sa.Column('is_featured', sa.Boolean, nullable=False, server_default='false'),
            sa.Column('helpful_count', sa.Integer, nullable=False, server_default='0'),
            sa.Column('not_helpful_count', sa.Integer, nullable=False, server_default='0'),
            sa.Column('images', JSONB, nullable=True),
            sa.Column('admin_response', sa.Text, nullable=True),
            sa.Column('admin_response_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')),
            sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')),
            sa.CheckConstraint('rating >= 1 AND rating <= 5', name='check_rating_range'),
        )

        # Create indexes
        op.create_index('ix_product_reviews_product_id', 'product_reviews', ['product_id'])
        op.create_index('ix_product_reviews_customer_id', 'product_reviews', ['customer_id'])
        op.create_index('ix_product_reviews_rating', 'product_reviews', ['rating'])

        # Unique constraint: one review per customer per product
        op.create_unique_constraint(
            'uq_product_reviews_customer_product',
            'product_reviews',
            ['customer_id', 'product_id']
        )

    # Create review_helpful table
    if not table_exists('review_helpful'):
        op.create_table(
            'review_helpful',
            sa.Column('id', UUID(as_uuid=True), primary_key=True),
            sa.Column('review_id', UUID(as_uuid=True), sa.ForeignKey('product_reviews.id', ondelete='CASCADE'), nullable=False),
            sa.Column('customer_id', UUID(as_uuid=True), sa.ForeignKey('customers.id', ondelete='CASCADE'), nullable=False),
            sa.Column('is_helpful', sa.Boolean, nullable=False),
            sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')),
        )

        # Unique constraint: one vote per customer per review
        op.create_unique_constraint(
            'uq_review_helpful_customer_review',
            'review_helpful',
            ['customer_id', 'review_id']
        )


def downgrade() -> None:
    """Drop product reviews tables."""

    if table_exists('review_helpful'):
        op.drop_table('review_helpful')

    if table_exists('product_reviews'):
        op.drop_table('product_reviews')
