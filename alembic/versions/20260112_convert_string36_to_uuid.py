"""Convert String(36) columns to UUID type for franchisee_audits table

Revision ID: convert_string36_to_uuid
Revises: add_serial_numbers
Create Date: 2026-01-12

This migration converts VARCHAR(36) columns to native PostgreSQL UUID type
for better storage efficiency and type safety.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'convert_string36_to_uuid'
down_revision: Union[str, None] = 'add_serial_numbers'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Convert VARCHAR(36) columns to UUID type in franchisee_audits table."""

    # franchisee_audits table - convert id, franchisee_id, auditor_id
    # Using USING clause to cast existing VARCHAR data to UUID

    op.execute("""
        ALTER TABLE franchisee_audits
        ALTER COLUMN id TYPE UUID USING id::uuid
    """)

    op.execute("""
        ALTER TABLE franchisee_audits
        ALTER COLUMN franchisee_id TYPE UUID USING franchisee_id::uuid
    """)

    op.execute("""
        ALTER TABLE franchisee_audits
        ALTER COLUMN auditor_id TYPE UUID USING auditor_id::uuid
    """)


def downgrade() -> None:
    """Revert UUID columns back to VARCHAR(36) in franchisee_audits table."""

    op.execute("""
        ALTER TABLE franchisee_audits
        ALTER COLUMN id TYPE VARCHAR(36) USING id::text
    """)

    op.execute("""
        ALTER TABLE franchisee_audits
        ALTER COLUMN franchisee_id TYPE VARCHAR(36) USING franchisee_id::text
    """)

    op.execute("""
        ALTER TABLE franchisee_audits
        ALTER COLUMN auditor_id TYPE VARCHAR(36) USING auditor_id::text
    """)
