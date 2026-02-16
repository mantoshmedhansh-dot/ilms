"""Add supply_plan_id FK to purchase_orders table.

Revision ID: supply_plan_po_001
Revises: customer_credit_001
Create Date: 2026-02-16

Additive migration - nullable FK column, zero downtime.
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


# revision identifiers, used by Alembic.
revision = 'supply_plan_po_001'
down_revision = 'customer_credit_001'
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()
    inspector = sa.inspect(conn)

    if 'purchase_orders' in inspector.get_table_names():
        existing_columns = [c['name'] for c in inspector.get_columns('purchase_orders')]

        if 'supply_plan_id' not in existing_columns:
            op.add_column(
                'purchase_orders',
                sa.Column(
                    'supply_plan_id',
                    UUID(as_uuid=True),
                    sa.ForeignKey('supply_plans.id', ondelete='SET NULL'),
                    nullable=True,
                    comment='S&OP supply plan that triggered this PO'
                )
            )


def downgrade():
    op.drop_column('purchase_orders', 'supply_plan_id')
