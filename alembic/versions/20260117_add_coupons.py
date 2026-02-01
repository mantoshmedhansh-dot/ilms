"""Add coupons and coupon_usage tables

Revision ID: 20260117_add_coupons
Revises:
Create Date: 2026-01-17
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB


# revision identifiers, used by Alembic.
revision = '20260117_add_coupons'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create coupons table
    op.create_table(
        'coupons',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('code', sa.String(50), unique=True, nullable=False, index=True,
                  comment='Unique coupon code (case-insensitive)'),
        sa.Column('name', sa.String(200), nullable=False,
                  comment='Display name for the coupon'),
        sa.Column('description', sa.Text, nullable=True,
                  comment='Description shown to customers'),
        sa.Column('discount_type', sa.String(50), nullable=False, default='PERCENTAGE',
                  comment='PERCENTAGE, FIXED_AMOUNT, FREE_SHIPPING'),
        sa.Column('discount_value', sa.Numeric(10, 2), nullable=False, default=0,
                  comment='Discount value (percentage or amount)'),
        sa.Column('max_discount_amount', sa.Numeric(10, 2), nullable=True,
                  comment='Cap on discount for PERCENTAGE type'),
        sa.Column('minimum_order_amount', sa.Numeric(10, 2), nullable=True,
                  comment='Minimum cart value to apply coupon'),
        sa.Column('minimum_items', sa.Integer, nullable=True,
                  comment='Minimum number of items in cart'),
        sa.Column('usage_limit', sa.Integer, nullable=True,
                  comment='Total times this coupon can be used'),
        sa.Column('usage_limit_per_customer', sa.Integer, nullable=False, default=1,
                  comment='Times each customer can use this coupon'),
        sa.Column('used_count', sa.Integer, nullable=False, default=0,
                  comment='Number of times coupon has been used'),
        sa.Column('valid_from', sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
        sa.Column('valid_until', sa.DateTime(timezone=True), nullable=True,
                  comment='Expiry date (null = never expires)'),
        sa.Column('applicable_products', JSONB, nullable=True,
                  comment='List of product IDs this coupon applies to'),
        sa.Column('applicable_categories', JSONB, nullable=True,
                  comment='List of category IDs this coupon applies to'),
        sa.Column('excluded_products', JSONB, nullable=True,
                  comment='List of product IDs excluded from this coupon'),
        sa.Column('first_order_only', sa.Boolean, nullable=False, default=False,
                  comment='Only for first-time customers'),
        sa.Column('specific_customers', JSONB, nullable=True,
                  comment='List of customer IDs who can use this coupon'),
        sa.Column('is_active', sa.Boolean, nullable=False, default=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
    )

    # Create coupon_usage table
    op.create_table(
        'coupon_usage',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('coupon_id', UUID(as_uuid=True), nullable=False, index=True),
        sa.Column('customer_id', UUID(as_uuid=True), nullable=False, index=True),
        sa.Column('order_id', UUID(as_uuid=True), nullable=False),
        sa.Column('discount_amount', sa.Numeric(10, 2), nullable=False,
                  comment='Actual discount applied'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table('coupon_usage')
    op.drop_table('coupons')
