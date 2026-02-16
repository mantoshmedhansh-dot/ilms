"""Add credit_limit and credit_used columns to customers table.

Revision ID: customer_credit_001
Revises: training_modules_001
Create Date: 2026-02-16

Additive migration - nullable columns only, zero downtime.
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'customer_credit_001'
down_revision = 'training_modules_001'
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()
    inspector = sa.inspect(conn)

    if 'customers' in inspector.get_table_names():
        existing_columns = [c['name'] for c in inspector.get_columns('customers')]

        if 'credit_limit' not in existing_columns:
            op.add_column(
                'customers',
                sa.Column('credit_limit', sa.Numeric(14, 2), nullable=True,
                          comment='Max credit allowed. NULL = unlimited')
            )

        if 'credit_used' not in existing_columns:
            op.add_column(
                'customers',
                sa.Column('credit_used', sa.Numeric(14, 2), server_default='0',
                          nullable=False, comment='Current outstanding AR balance')
            )


def downgrade():
    op.drop_column('customers', 'credit_used')
    op.drop_column('customers', 'credit_limit')
