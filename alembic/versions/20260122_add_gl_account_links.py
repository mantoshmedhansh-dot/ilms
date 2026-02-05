"""Add GL account links to vendors and customers for finance integration.

This migration links Vendors and Customers to Chart of Accounts entries,
enabling proper double-entry accounting when transactions occur.

Vendor -> Accounts Payable (Creditors) ledger account
Customer -> Accounts Receivable (Debtors) ledger account

Revision ID: 20260122_gl_links
Revises: 2026012201
Create Date: 2026-01-22

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '20260122_gl_links'
down_revision: Union[str, None] = '2026012201'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add GL account link to vendors table
    op.add_column(
        'vendors',
        sa.Column(
            'gl_account_id',
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey('chart_of_accounts.id', ondelete='SET NULL'),
            nullable=True,
            comment='Linked GL account for Accounts Payable (Creditors)'
        )
    )
    op.create_index('ix_vendors_gl_account_id', 'vendors', ['gl_account_id'])

    # Add GL account link to customers table
    op.add_column(
        'customers',
        sa.Column(
            'gl_account_id',
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey('chart_of_accounts.id', ondelete='SET NULL'),
            nullable=True,
            comment='Linked GL account for Accounts Receivable (Debtors)'
        )
    )
    op.create_index('ix_customers_gl_account_id', 'customers', ['gl_account_id'])


def downgrade() -> None:
    # Drop indexes first
    op.drop_index('ix_customers_gl_account_id', table_name='customers')
    op.drop_index('ix_vendors_gl_account_id', table_name='vendors')

    # Drop columns
    op.drop_column('customers', 'gl_account_id')
    op.drop_column('vendors', 'gl_account_id')
