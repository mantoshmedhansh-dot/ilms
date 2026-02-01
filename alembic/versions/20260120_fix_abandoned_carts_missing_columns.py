"""Fix abandoned_carts missing columns

The abandoned_carts table in production is missing some columns that were
defined in the original migration but may not have been applied correctly.

Revision ID: fix_abandoned_carts_cols
Revises: 2fa614d510a5
Create Date: 2026-01-20

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'fix_abandoned_carts_cols'
down_revision: Union[str, None] = '2fa614d510a5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add missing columns to abandoned_carts table if they don't exist."""
    conn = op.get_bind()

    # Check if abandoned_carts table exists
    result = conn.execute(sa.text("""
        SELECT EXISTS (
            SELECT FROM information_schema.tables
            WHERE table_name = 'abandoned_carts'
        )
    """))
    table_exists = result.scalar()

    if not table_exists:
        # Table doesn't exist, skip - the main migration should create it
        return

    # Get existing columns
    result = conn.execute(sa.text("""
        SELECT column_name
        FROM information_schema.columns
        WHERE table_name = 'abandoned_carts'
    """))
    existing_columns = {row[0] for row in result.fetchall()}

    # List of columns that should exist (from model definition)
    columns_to_add = [
        ('email', 'VARCHAR(255)', True),
        ('phone', 'VARCHAR(20)', True),
        ('customer_name', 'VARCHAR(200)', True),
        ('device_fingerprint', 'VARCHAR(100)', True),
    ]

    for col_name, col_type, nullable in columns_to_add:
        if col_name not in existing_columns:
            null_clause = '' if nullable else ' NOT NULL'
            op.execute(f'ALTER TABLE abandoned_carts ADD COLUMN IF NOT EXISTS {col_name} {col_type}{null_clause}')
            print(f"Added column: {col_name}")

    # Add indexes if they don't exist
    # Check for email index
    result = conn.execute(sa.text("""
        SELECT EXISTS (
            SELECT FROM pg_indexes
            WHERE tablename = 'abandoned_carts'
            AND indexname = 'ix_abandoned_carts_email'
        )
    """))
    if not result.scalar():
        op.create_index('ix_abandoned_carts_email', 'abandoned_carts', ['email'])

    # Check for phone index
    result = conn.execute(sa.text("""
        SELECT EXISTS (
            SELECT FROM pg_indexes
            WHERE tablename = 'abandoned_carts'
            AND indexname = 'ix_abandoned_carts_phone'
        )
    """))
    if not result.scalar():
        op.create_index('ix_abandoned_carts_phone', 'abandoned_carts', ['phone'])


def downgrade() -> None:
    """We don't remove columns on downgrade as they may contain data."""
    pass
