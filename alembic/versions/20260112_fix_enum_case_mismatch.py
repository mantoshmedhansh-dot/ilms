"""Fix enum value case mismatch - convert lowercase to UPPERCASE

Revision ID: fix_enum_case_mismatch
Revises: convert_string36_to_uuid
Create Date: 2026-01-12

This migration converts lowercase enum values to UPPERCASE in the database
to match frontend expectations and maintain consistency.

Affected tables and columns:
- service_requests: service_type, priority, status, source
- warehouses: warehouse_type
- stock_items: status
- stock_movements: movement_type
- po_delivery_schedules: status
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'fix_enum_case_mismatch'
down_revision: Union[str, None] = 'convert_string36_to_uuid'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Convert lowercase enum values to UPPERCASE."""

    # ==================== service_requests table ====================

    # service_type column
    op.execute("""
        UPDATE service_requests SET service_type = UPPER(service_type)
        WHERE service_type IS NOT NULL AND service_type != UPPER(service_type)
    """)

    # priority column
    op.execute("""
        UPDATE service_requests SET priority = UPPER(priority)
        WHERE priority IS NOT NULL AND priority != UPPER(priority)
    """)

    # status column
    op.execute("""
        UPDATE service_requests SET status = UPPER(status)
        WHERE status IS NOT NULL AND status != UPPER(status)
    """)

    # source column
    op.execute("""
        UPDATE service_requests SET source = UPPER(source)
        WHERE source IS NOT NULL AND source != UPPER(source)
    """)

    # ==================== warehouses table ====================

    # warehouse_type column
    op.execute("""
        UPDATE warehouses SET warehouse_type = UPPER(warehouse_type)
        WHERE warehouse_type IS NOT NULL AND warehouse_type != UPPER(warehouse_type)
    """)

    # ==================== stock_items table ====================

    # status column
    op.execute("""
        UPDATE stock_items SET status = UPPER(status)
        WHERE status IS NOT NULL AND status != UPPER(status)
    """)

    # ==================== stock_movements table ====================

    # movement_type column
    op.execute("""
        UPDATE stock_movements SET movement_type = UPPER(movement_type)
        WHERE movement_type IS NOT NULL AND movement_type != UPPER(movement_type)
    """)

    # ==================== po_delivery_schedules table ====================

    # status column
    op.execute("""
        UPDATE po_delivery_schedules SET status = UPPER(status)
        WHERE status IS NOT NULL AND status != UPPER(status)
    """)


def downgrade() -> None:
    """Revert UPPERCASE enum values back to lowercase."""

    # ==================== service_requests table ====================

    op.execute("""
        UPDATE service_requests SET service_type = LOWER(service_type)
        WHERE service_type IS NOT NULL
    """)

    op.execute("""
        UPDATE service_requests SET priority = LOWER(priority)
        WHERE priority IS NOT NULL
    """)

    op.execute("""
        UPDATE service_requests SET status = LOWER(status)
        WHERE status IS NOT NULL
    """)

    op.execute("""
        UPDATE service_requests SET source = LOWER(source)
        WHERE source IS NOT NULL
    """)

    # ==================== warehouses table ====================

    op.execute("""
        UPDATE warehouses SET warehouse_type = LOWER(warehouse_type)
        WHERE warehouse_type IS NOT NULL
    """)

    # ==================== stock_items table ====================

    op.execute("""
        UPDATE stock_items SET status = LOWER(status)
        WHERE status IS NOT NULL
    """)

    # ==================== stock_movements table ====================

    op.execute("""
        UPDATE stock_movements SET movement_type = LOWER(movement_type)
        WHERE movement_type IS NOT NULL
    """)

    # ==================== po_delivery_schedules table ====================

    op.execute("""
        UPDATE po_delivery_schedules SET status = LOWER(status)
        WHERE status IS NOT NULL
    """)
