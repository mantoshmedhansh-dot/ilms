"""Add customer_ledger table for AR tracking

Revision ID: 20260123_add_customer_ledger
Revises:
Create Date: 2026-01-23

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision: str = '20260123_add_customer_ledger'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create customer_ledger table
    op.create_table(
        'customer_ledger',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('customer_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('transaction_type', sa.String(50), nullable=False,
                  comment='OPENING_BALANCE, INVOICE, PAYMENT, CREDIT_NOTE, DEBIT_NOTE, ADVANCE, ADJUSTMENT, REFUND, WRITE_OFF'),
        sa.Column('transaction_date', sa.Date(), nullable=False),
        sa.Column('due_date', sa.Date(), nullable=True, comment='Due date for payment (for invoices)'),
        sa.Column('reference_type', sa.String(50), nullable=False,
                  comment='INVOICE, PAYMENT_RECEIPT, CREDIT_NOTE, DEBIT_NOTE, ORDER, MANUAL'),
        sa.Column('reference_number', sa.String(50), nullable=False, comment='Invoice/Receipt/Order number'),
        sa.Column('reference_id', postgresql.UUID(as_uuid=True), nullable=True, comment='UUID of the source document'),
        sa.Column('order_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('debit_amount', sa.Numeric(14, 2), nullable=False, server_default='0',
                  comment='Increases outstanding (invoices, debit notes)'),
        sa.Column('credit_amount', sa.Numeric(14, 2), nullable=False, server_default='0',
                  comment='Decreases outstanding (payments, credit notes)'),
        sa.Column('balance', sa.Numeric(14, 2), nullable=False, server_default='0',
                  comment='Running balance after this transaction'),
        sa.Column('tax_amount', sa.Numeric(12, 2), nullable=False, server_default='0',
                  comment='Tax portion of the amount'),
        sa.Column('is_settled', sa.Boolean(), nullable=False, server_default='false',
                  comment='True if invoice is fully paid'),
        sa.Column('settled_date', sa.Date(), nullable=True, comment='Date when fully settled'),
        sa.Column('settled_against_id', postgresql.UUID(as_uuid=True), nullable=True,
                  comment='Reference to payment/credit that settled this'),
        sa.Column('description', sa.String(500), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('channel_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['customer_id'], ['customers.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['order_id'], ['orders.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['channel_id'], ['sales_channels.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ondelete='SET NULL'),
    )

    # Create indexes
    op.create_index('ix_customer_ledger_customer_id', 'customer_ledger', ['customer_id'])
    op.create_index('ix_customer_ledger_date', 'customer_ledger', ['customer_id', 'transaction_date'])
    op.create_index('ix_customer_ledger_due_date', 'customer_ledger', ['due_date'])
    op.create_index('ix_customer_ledger_order_id', 'customer_ledger', ['order_id'])


def downgrade() -> None:
    op.drop_index('ix_customer_ledger_order_id', table_name='customer_ledger')
    op.drop_index('ix_customer_ledger_due_date', table_name='customer_ledger')
    op.drop_index('ix_customer_ledger_date', table_name='customer_ledger')
    op.drop_index('ix_customer_ledger_customer_id', table_name='customer_ledger')
    op.drop_table('customer_ledger')
