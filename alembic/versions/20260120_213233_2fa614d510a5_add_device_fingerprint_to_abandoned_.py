"""add_device_fingerprint_to_abandoned_carts

Revision ID: 2fa614d510a5
Revises: 20260120_delhi_inv
Create Date: 2026-01-20 21:32:33.631155

Adds missing device_fingerprint column to abandoned_carts table.
This column is used for cross-session tracking of guest users.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '2fa614d510a5'
down_revision: Union[str, None] = '20260120_delhi_inv'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add device_fingerprint column to abandoned_carts table."""
    # Check if column exists before adding (safe for production)
    conn = op.get_bind()
    result = conn.execute(sa.text("""
        SELECT column_name
        FROM information_schema.columns
        WHERE table_name = 'abandoned_carts'
        AND column_name = 'device_fingerprint'
    """))

    if result.fetchone() is None:
        op.add_column(
            'abandoned_carts',
            sa.Column(
                'device_fingerprint',
                sa.String(100),
                nullable=True,
                comment='Device fingerprint for cross-session tracking'
            )
        )


def downgrade() -> None:
    """Remove device_fingerprint column from abandoned_carts table."""
    op.drop_column('abandoned_carts', 'device_fingerprint')
