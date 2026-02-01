"""Fix enum value case mismatch - Part 2 (additional tables)

Revision ID: fix_enum_case_mismatch_part2
Revises: convert_float_to_numeric
Create Date: 2026-01-12

This migration converts lowercase enum values to UPPERCASE in additional tables.

Affected tables:
- po_serials: status
- installations: status
- amc_contracts: amc_type, status
- amc_templates: amc_type
- stock_transfers: status, transfer_type
- stock_adjustments: adjustment_type, status
- technicians: status, technician_type, skill_level
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'fix_enum_case_mismatch_part2'
down_revision: Union[str, None] = 'convert_float_to_numeric'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Convert lowercase enum values to UPPERCASE in additional tables."""

    # ==================== po_serials table ====================
    op.execute("""
        UPDATE po_serials SET status = UPPER(status)
        WHERE status IS NOT NULL AND status != UPPER(status)
    """)

    # ==================== installations table ====================
    op.execute("""
        UPDATE installations SET status = UPPER(status)
        WHERE status IS NOT NULL AND status != UPPER(status)
    """)

    # ==================== amc_contracts table ====================
    op.execute("""
        UPDATE amc_contracts SET amc_type = UPPER(amc_type)
        WHERE amc_type IS NOT NULL AND amc_type != UPPER(amc_type)
    """)
    op.execute("""
        UPDATE amc_contracts SET status = UPPER(status)
        WHERE status IS NOT NULL AND status != UPPER(status)
    """)

    # ==================== amc_templates table ====================
    op.execute("""
        UPDATE amc_templates SET amc_type = UPPER(amc_type)
        WHERE amc_type IS NOT NULL AND amc_type != UPPER(amc_type)
    """)

    # ==================== stock_transfers table ====================
    op.execute("""
        UPDATE stock_transfers SET status = UPPER(status)
        WHERE status IS NOT NULL AND status != UPPER(status)
    """)
    op.execute("""
        UPDATE stock_transfers SET transfer_type = UPPER(transfer_type)
        WHERE transfer_type IS NOT NULL AND transfer_type != UPPER(transfer_type)
    """)

    # ==================== stock_adjustments table ====================
    op.execute("""
        UPDATE stock_adjustments SET adjustment_type = UPPER(adjustment_type)
        WHERE adjustment_type IS NOT NULL AND adjustment_type != UPPER(adjustment_type)
    """)
    op.execute("""
        UPDATE stock_adjustments SET status = UPPER(status)
        WHERE status IS NOT NULL AND status != UPPER(status)
    """)

    # ==================== technicians table ====================
    op.execute("""
        UPDATE technicians SET status = UPPER(status)
        WHERE status IS NOT NULL AND status != UPPER(status)
    """)
    op.execute("""
        UPDATE technicians SET technician_type = UPPER(technician_type)
        WHERE technician_type IS NOT NULL AND technician_type != UPPER(technician_type)
    """)
    op.execute("""
        UPDATE technicians SET skill_level = UPPER(skill_level)
        WHERE skill_level IS NOT NULL AND skill_level != UPPER(skill_level)
    """)


def downgrade() -> None:
    """Revert UPPERCASE enum values back to lowercase."""

    # ==================== po_serials table ====================
    op.execute("""
        UPDATE po_serials SET status = LOWER(status)
        WHERE status IS NOT NULL
    """)

    # ==================== installations table ====================
    op.execute("""
        UPDATE installations SET status = LOWER(status)
        WHERE status IS NOT NULL
    """)

    # ==================== amc_contracts table ====================
    op.execute("""
        UPDATE amc_contracts SET amc_type = LOWER(amc_type)
        WHERE amc_type IS NOT NULL
    """)
    op.execute("""
        UPDATE amc_contracts SET status = LOWER(status)
        WHERE status IS NOT NULL
    """)

    # ==================== amc_templates table ====================
    op.execute("""
        UPDATE amc_templates SET amc_type = LOWER(amc_type)
        WHERE amc_type IS NOT NULL
    """)

    # ==================== stock_transfers table ====================
    op.execute("""
        UPDATE stock_transfers SET status = LOWER(status)
        WHERE status IS NOT NULL
    """)
    op.execute("""
        UPDATE stock_transfers SET transfer_type = LOWER(transfer_type)
        WHERE transfer_type IS NOT NULL
    """)

    # ==================== stock_adjustments table ====================
    op.execute("""
        UPDATE stock_adjustments SET adjustment_type = LOWER(adjustment_type)
        WHERE adjustment_type IS NOT NULL
    """)
    op.execute("""
        UPDATE stock_adjustments SET status = LOWER(status)
        WHERE status IS NOT NULL
    """)

    # ==================== technicians table ====================
    op.execute("""
        UPDATE technicians SET status = LOWER(status)
        WHERE status IS NOT NULL
    """)
    op.execute("""
        UPDATE technicians SET technician_type = LOWER(technician_type)
        WHERE technician_type IS NOT NULL
    """)
    op.execute("""
        UPDATE technicians SET skill_level = LOWER(skill_level)
        WHERE skill_level IS NOT NULL
    """)
