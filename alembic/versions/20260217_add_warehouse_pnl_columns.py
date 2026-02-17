"""Add warehouse P&L columns: warehouse_id on cost_centers, cost_center_id on employees, unit_cost on order_items.

Revision ID: warehouse_pnl_001
Revises: supply_plan_po_001
Create Date: 2026-02-17

Additive migration - nullable columns only, zero downtime.
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


# revision identifiers, used by Alembic.
revision = 'warehouse_pnl_001'
down_revision = 'supply_plan_po_001'
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    table_names = inspector.get_table_names()

    # 1. Add warehouse_id to cost_centers
    if 'cost_centers' in table_names:
        existing = [c['name'] for c in inspector.get_columns('cost_centers')]
        if 'warehouse_id' not in existing:
            op.add_column(
                'cost_centers',
                sa.Column(
                    'warehouse_id',
                    UUID(as_uuid=True),
                    sa.ForeignKey('warehouses.id', ondelete='SET NULL'),
                    nullable=True,
                    comment='Links LOCATION cost centres to warehouses for P&L attribution'
                )
            )

    # 2. Add cost_center_id to employees
    if 'employees' in table_names:
        existing = [c['name'] for c in inspector.get_columns('employees')]
        if 'cost_center_id' not in existing:
            op.add_column(
                'employees',
                sa.Column(
                    'cost_center_id',
                    UUID(as_uuid=True),
                    sa.ForeignKey('cost_centers.id', ondelete='SET NULL'),
                    nullable=True,
                    comment='Cost centre for manpower cost attribution to warehouse P&L'
                )
            )

    # 3. Add unit_cost to order_items
    if 'order_items' in table_names:
        existing = [c['name'] for c in inspector.get_columns('order_items')]
        if 'unit_cost' not in existing:
            op.add_column(
                'order_items',
                sa.Column(
                    'unit_cost',
                    sa.Numeric(12, 2),
                    nullable=True,
                    server_default='0',
                    comment='Cost price for COGS calculation'
                )
            )


def downgrade():
    op.drop_column('order_items', 'unit_cost')
    op.drop_column('employees', 'cost_center_id')
    op.drop_column('cost_centers', 'warehouse_id')
