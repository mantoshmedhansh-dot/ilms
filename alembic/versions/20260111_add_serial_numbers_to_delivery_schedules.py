"""Add serial_number_start and serial_number_end to po_delivery_schedules

Revision ID: add_serial_numbers
Revises: 20260106_100101_f18dbdd90985_add_channel_id_to_journal_entries_and_
Create Date: 2026-01-11

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'add_serial_numbers'
down_revision: Union[str, None] = 'f18dbdd90985'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add serial number range columns to po_delivery_schedules table."""
    op.add_column(
        'po_delivery_schedules',
        sa.Column(
            'serial_number_start',
            sa.Integer(),
            nullable=True,
            comment='Starting serial number for this lot (e.g., 101)'
        )
    )
    op.add_column(
        'po_delivery_schedules',
        sa.Column(
            'serial_number_end',
            sa.Integer(),
            nullable=True,
            comment='Ending serial number for this lot (e.g., 200)'
        )
    )


def downgrade() -> None:
    """Remove serial number range columns from po_delivery_schedules table."""
    op.drop_column('po_delivery_schedules', 'serial_number_end')
    op.drop_column('po_delivery_schedules', 'serial_number_start')
