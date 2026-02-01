"""Add customer_otps table for D2C authentication

Revision ID: 20260117_customer_otps
Revises:
Create Date: 2026-01-17

Adds table for OTP storage:
- customer_otps: Stores OTPs for phone verification and login
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy import text


# revision identifiers, used by Alembic.
revision = '20260117_customer_otps'
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
    """Create customer_otps table."""

    if not table_exists('customer_otps'):
        op.create_table(
            'customer_otps',
            sa.Column('id', UUID(as_uuid=True), primary_key=True),
            sa.Column('phone', sa.String(20), nullable=False, index=True),
            sa.Column('otp_hash', sa.String(255), nullable=False),
            sa.Column(
                'purpose',
                sa.String(50),
                nullable=False,
                server_default='LOGIN',
                comment='LOGIN, REGISTER, VERIFY_PHONE, RESET'
            ),
            sa.Column('is_verified', sa.Boolean, nullable=False, server_default='false'),
            sa.Column('attempts', sa.Integer, nullable=False, server_default='0'),
            sa.Column('max_attempts', sa.Integer, nullable=False, server_default='3'),
            sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
            sa.Column(
                'created_at',
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.text('NOW()')
            ),
            sa.Column('verified_at', sa.DateTime(timezone=True), nullable=True),
        )

        # Create index for faster lookups
        op.create_index(
            'ix_customer_otps_phone_purpose',
            'customer_otps',
            ['phone', 'purpose']
        )


def downgrade() -> None:
    """Drop customer_otps table."""

    if table_exists('customer_otps'):
        op.drop_index('ix_customer_otps_phone_purpose', table_name='customer_otps')
        op.drop_table('customer_otps')
