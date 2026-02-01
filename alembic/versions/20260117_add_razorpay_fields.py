"""Add Razorpay fields to orders table

Revision ID: 20260117_razorpay
Revises:
Create Date: 2026-01-17

Adds fields for Razorpay payment integration:
- razorpay_order_id: Razorpay order ID (order_xxx)
- razorpay_payment_id: Razorpay payment ID (pay_xxx)
- paid_at: Timestamp when payment was confirmed
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import text


# revision identifiers, used by Alembic.
revision = '20260117_razorpay'
down_revision = None  # Will be filled automatically
branch_labels = None
depends_on = None


def column_exists(table_name: str, column_name: str) -> bool:
    """Check if a column exists in a table."""
    conn = op.get_bind()
    result = conn.execute(text(f"""
        SELECT EXISTS (
            SELECT 1 FROM information_schema.columns
            WHERE table_name = '{table_name}' AND column_name = '{column_name}'
        )
    """))
    return result.scalar()


def upgrade() -> None:
    """Add Razorpay fields to orders table."""

    # Add razorpay_order_id if not exists
    if not column_exists('orders', 'razorpay_order_id'):
        op.add_column(
            'orders',
            sa.Column(
                'razorpay_order_id',
                sa.String(50),
                nullable=True,
                comment='Razorpay order ID (order_xxx)'
            )
        )
        op.create_index(
            'ix_orders_razorpay_order_id',
            'orders',
            ['razorpay_order_id']
        )

    # Add razorpay_payment_id if not exists
    if not column_exists('orders', 'razorpay_payment_id'):
        op.add_column(
            'orders',
            sa.Column(
                'razorpay_payment_id',
                sa.String(50),
                nullable=True,
                comment='Razorpay payment ID (pay_xxx)'
            )
        )
        op.create_index(
            'ix_orders_razorpay_payment_id',
            'orders',
            ['razorpay_payment_id']
        )

    # Add paid_at if not exists
    if not column_exists('orders', 'paid_at'):
        op.add_column(
            'orders',
            sa.Column(
                'paid_at',
                sa.DateTime(timezone=True),
                nullable=True,
                comment='Timestamp when payment was confirmed'
            )
        )


def downgrade() -> None:
    """Remove Razorpay fields from orders table."""

    # Remove indexes first
    try:
        op.drop_index('ix_orders_razorpay_order_id', table_name='orders')
    except Exception:
        pass

    try:
        op.drop_index('ix_orders_razorpay_payment_id', table_name='orders')
    except Exception:
        pass

    # Remove columns
    if column_exists('orders', 'razorpay_order_id'):
        op.drop_column('orders', 'razorpay_order_id')

    if column_exists('orders', 'razorpay_payment_id'):
        op.drop_column('orders', 'razorpay_payment_id')

    if column_exists('orders', 'paid_at'):
        op.drop_column('orders', 'paid_at')
