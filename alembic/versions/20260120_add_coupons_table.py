"""Add coupons and coupon_usage tables for D2C storefront

Revision ID: 20260120_coupons
Revises: 20260120_channel_inv
Create Date: 2026-01-20

This migration adds:
1. coupons table for promo codes
2. coupon_usage table for tracking coupon usage
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '20260120_coupons'
down_revision: Union[str, None] = '20260120_channel_inv'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Check if table already exists
    connection = op.get_bind()
    inspector = sa.inspect(connection)
    existing_tables = inspector.get_table_names()

    if 'coupons' not in existing_tables:
        # Create coupons table
        op.create_table(
            'coupons',
            sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
            # Coupon Code
            sa.Column('code', sa.String(50), unique=True, nullable=False, index=True,
                      comment='Unique coupon code (case-insensitive)'),
            # Display Info
            sa.Column('name', sa.String(200), nullable=False,
                      comment='Display name for the coupon'),
            sa.Column('description', sa.Text(), nullable=True,
                      comment='Description shown to customers'),
            # Discount Type & Value
            sa.Column('discount_type', sa.String(50), nullable=False, default='PERCENTAGE',
                      comment='PERCENTAGE, FIXED_AMOUNT, FREE_SHIPPING'),
            sa.Column('discount_value', sa.Numeric(10, 2), nullable=False, default=0,
                      comment='Discount value (percentage or amount)'),
            sa.Column('max_discount_amount', sa.Numeric(10, 2), nullable=True,
                      comment='Cap on discount for PERCENTAGE type'),
            # Minimum Requirements
            sa.Column('minimum_order_amount', sa.Numeric(10, 2), nullable=True,
                      comment='Minimum cart value to apply coupon'),
            sa.Column('minimum_items', sa.Integer(), nullable=True,
                      comment='Minimum number of items in cart'),
            # Usage Limits
            sa.Column('usage_limit', sa.Integer(), nullable=True,
                      comment='Total times this coupon can be used'),
            sa.Column('usage_limit_per_customer', sa.Integer(), nullable=False, default=1,
                      comment='Times each customer can use this coupon'),
            sa.Column('used_count', sa.Integer(), nullable=False, default=0,
                      comment='Number of times coupon has been used'),
            # Validity Period
            sa.Column('valid_from', sa.DateTime(timezone=True), nullable=False,
                      server_default=sa.func.now()),
            sa.Column('valid_until', sa.DateTime(timezone=True), nullable=True,
                      comment='Expiry date (null = never expires)'),
            # Restrictions (stored as JSONB)
            sa.Column('applicable_products', postgresql.JSONB(), nullable=True,
                      comment='List of product IDs this coupon applies to'),
            sa.Column('applicable_categories', postgresql.JSONB(), nullable=True,
                      comment='List of category IDs this coupon applies to'),
            sa.Column('excluded_products', postgresql.JSONB(), nullable=True,
                      comment='List of product IDs excluded from this coupon'),
            # Customer Restrictions
            sa.Column('first_order_only', sa.Boolean(), nullable=False, default=False,
                      comment='Only for first-time customers'),
            sa.Column('specific_customers', postgresql.JSONB(), nullable=True,
                      comment='List of customer IDs who can use this coupon'),
            # Status
            sa.Column('is_active', sa.Boolean(), nullable=False, default=True),
            # Timestamps
            sa.Column('created_at', sa.DateTime(timezone=True), nullable=False,
                      server_default=sa.func.now()),
            sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False,
                      server_default=sa.func.now(), onupdate=sa.func.now()),
        )

    if 'coupon_usage' not in existing_tables:
        # Create coupon_usage table
        op.create_table(
            'coupon_usage',
            sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column('coupon_id', postgresql.UUID(as_uuid=True), nullable=False, index=True),
            sa.Column('customer_id', postgresql.UUID(as_uuid=True), nullable=False, index=True),
            sa.Column('order_id', postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column('discount_amount', sa.Numeric(10, 2), nullable=False,
                      comment='Actual discount applied'),
            sa.Column('created_at', sa.DateTime(timezone=True), nullable=False,
                      server_default=sa.func.now()),
            # Foreign keys
            sa.ForeignKeyConstraint(['coupon_id'], ['coupons.id'], ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['customer_id'], ['customers.id'], ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['order_id'], ['orders.id'], ondelete='CASCADE'),
        )


def downgrade() -> None:
    op.drop_table('coupon_usage')
    op.drop_table('coupons')
