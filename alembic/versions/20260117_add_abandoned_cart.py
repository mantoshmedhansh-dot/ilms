"""Add abandoned cart tables

Revision ID: add_abandoned_cart_001
Revises:
Create Date: 2026-01-17

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'add_abandoned_cart_001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create abandoned_carts table
    op.create_table(
        'abandoned_carts',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('customer_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('customers.id', ondelete='SET NULL'), nullable=True, index=True),

        # Session/Device identification
        sa.Column('session_id', sa.String(100), nullable=True, index=True),
        sa.Column('device_fingerprint', sa.String(100), nullable=True),

        # Contact info
        sa.Column('email', sa.String(255), nullable=True, index=True),
        sa.Column('phone', sa.String(20), nullable=True, index=True),
        sa.Column('customer_name', sa.String(200), nullable=True),

        # Cart contents
        sa.Column('items', postgresql.JSONB, nullable=False, default=[]),

        # Pricing
        sa.Column('subtotal', sa.Numeric(18, 2), nullable=False, default=0),
        sa.Column('tax_amount', sa.Numeric(18, 2), nullable=False, default=0),
        sa.Column('shipping_amount', sa.Numeric(18, 2), nullable=False, default=0),
        sa.Column('discount_amount', sa.Numeric(18, 2), nullable=False, default=0),
        sa.Column('total_amount', sa.Numeric(18, 2), nullable=False, default=0),

        # Coupon
        sa.Column('coupon_code', sa.String(50), nullable=True),

        # Status
        sa.Column('status', sa.String(50), nullable=False, default='ACTIVE', index=True),
        sa.Column('items_count', sa.Integer, nullable=False, default=0),

        # Checkout progress
        sa.Column('checkout_step', sa.String(50), nullable=True),
        sa.Column('shipping_address', postgresql.JSONB, nullable=True),
        sa.Column('selected_payment_method', sa.String(50), nullable=True),

        # Timestamps
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.Column('last_activity_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now(), index=True),
        sa.Column('abandoned_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('recovered_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('converted_at', sa.DateTime(timezone=True), nullable=True),

        # Conversion tracking
        sa.Column('converted_order_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('orders.id', ondelete='SET NULL'), nullable=True),

        # Analytics
        sa.Column('source', sa.String(100), nullable=True),
        sa.Column('utm_source', sa.String(100), nullable=True),
        sa.Column('utm_medium', sa.String(100), nullable=True),
        sa.Column('utm_campaign', sa.String(100), nullable=True),
        sa.Column('referrer_url', sa.Text, nullable=True),

        # Device info
        sa.Column('user_agent', sa.Text, nullable=True),
        sa.Column('ip_address', sa.String(50), nullable=True),
        sa.Column('device_type', sa.String(50), nullable=True),

        # Recovery tracking
        sa.Column('recovery_attempts', sa.Integer, nullable=False, default=0),
        sa.Column('last_recovery_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('recovery_token', sa.String(100), nullable=True, unique=True),
        sa.Column('recovery_token_expires_at', sa.DateTime(timezone=True), nullable=True),
    )

    # Create cart_recovery_emails table
    op.create_table(
        'cart_recovery_emails',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('cart_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('abandoned_carts.id', ondelete='CASCADE'), nullable=False, index=True),

        # Recovery sequence
        sa.Column('sequence_number', sa.Integer, nullable=False, default=1),

        # Channel
        sa.Column('channel', sa.String(50), nullable=False, default='EMAIL'),

        # Status
        sa.Column('status', sa.String(50), nullable=False, default='PENDING'),

        # Recipient
        sa.Column('recipient', sa.String(255), nullable=False),

        # Content
        sa.Column('template_used', sa.String(100), nullable=False),
        sa.Column('subject', sa.String(255), nullable=True),

        # Offer
        sa.Column('discount_code', sa.String(50), nullable=True),
        sa.Column('discount_value', sa.Numeric(18, 2), nullable=True),

        # Timestamps
        sa.Column('scheduled_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('sent_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('delivered_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('opened_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('clicked_at', sa.DateTime(timezone=True), nullable=True),

        # Provider info
        sa.Column('provider', sa.String(50), nullable=True),
        sa.Column('provider_message_id', sa.String(200), nullable=True),
        sa.Column('error_message', sa.Text, nullable=True),

        # Audit timestamps
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),
    )

    # Create indexes for common queries
    op.create_index('ix_abandoned_carts_status_last_activity', 'abandoned_carts', ['status', 'last_activity_at'])
    op.create_index('ix_abandoned_carts_customer_status', 'abandoned_carts', ['customer_id', 'status'])
    op.create_index('ix_cart_recovery_emails_status', 'cart_recovery_emails', ['status'])


def downgrade() -> None:
    # Drop indexes
    op.drop_index('ix_cart_recovery_emails_status', table_name='cart_recovery_emails')
    op.drop_index('ix_abandoned_carts_customer_status', table_name='abandoned_carts')
    op.drop_index('ix_abandoned_carts_status_last_activity', table_name='abandoned_carts')

    # Drop tables
    op.drop_table('cart_recovery_emails')
    op.drop_table('abandoned_carts')
