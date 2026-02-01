"""Link company bank accounts to chart of accounts

Revision ID: 20260121_bank_ledger
Revises: 20260121_cms
Create Date: 2026-01-21 12:45:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '20260121_bank_ledger'
down_revision: Union[str, None] = '20260121_cms'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add ledger_account_id column to company_bank_accounts
    op.add_column(
        'company_bank_accounts',
        sa.Column(
            'ledger_account_id',
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey('chart_of_accounts.id', ondelete='SET NULL'),
            nullable=True,
            comment='Linked ledger account for journal entries'
        )
    )
    op.create_index(
        'ix_company_bank_accounts_ledger_account_id',
        'company_bank_accounts',
        ['ledger_account_id']
    )


def downgrade() -> None:
    op.drop_index('ix_company_bank_accounts_ledger_account_id', table_name='company_bank_accounts')
    op.drop_column('company_bank_accounts', 'ledger_account_id')
