"""Add goods issue tracking to shipments and shipment link to invoices.

SAP S/4HANA-aligned Order-to-Invoice flow:
- Add goods_issue_at, goods_issue_by, goods_issue_reference to shipments
- Add shipment_id, generation_trigger to tax_invoices

Revision ID: 2026012201
Revises: 20260121_link_bank_accounts_to_ledger
Create Date: 2026-01-22

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic
revision = '2026012201'
down_revision = '20260121_bank_ledger'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add goods issue tracking fields to shipments table
    op.add_column(
        'shipments',
        sa.Column(
            'goods_issue_at',
            sa.DateTime(timezone=True),
            nullable=True,
            comment='Timestamp when goods issue was posted (manifest confirmed)'
        )
    )
    op.add_column(
        'shipments',
        sa.Column(
            'goods_issue_by',
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey('users.id', ondelete='SET NULL'),
            nullable=True,
            comment='User who posted the goods issue'
        )
    )
    op.add_column(
        'shipments',
        sa.Column(
            'goods_issue_reference',
            sa.String(50),
            nullable=True,
            comment='Reference number (manifest number)'
        )
    )

    # Add index for goods_issue_at for efficient querying
    op.create_index(
        'ix_shipments_goods_issue_at',
        'shipments',
        ['goods_issue_at'],
        unique=False
    )

    # Add shipment_id and generation_trigger to tax_invoices table
    op.add_column(
        'tax_invoices',
        sa.Column(
            'shipment_id',
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey('shipments.id', ondelete='SET NULL'),
            nullable=True,
            comment='Shipment that triggered this invoice (for goods issue)'
        )
    )
    op.add_column(
        'tax_invoices',
        sa.Column(
            'generation_trigger',
            sa.String(50),
            nullable=True,
            comment='MANUAL, GOODS_ISSUE, ORDER_CONFIRMATION, etc.'
        )
    )

    # Add index for shipment_id
    op.create_index(
        'ix_tax_invoices_shipment_id',
        'tax_invoices',
        ['shipment_id'],
        unique=False
    )

    # Add index for generation_trigger for analytics queries
    op.create_index(
        'ix_tax_invoices_generation_trigger',
        'tax_invoices',
        ['generation_trigger'],
        unique=False
    )


def downgrade() -> None:
    # Remove indexes first
    op.drop_index('ix_tax_invoices_generation_trigger', table_name='tax_invoices')
    op.drop_index('ix_tax_invoices_shipment_id', table_name='tax_invoices')
    op.drop_index('ix_shipments_goods_issue_at', table_name='shipments')

    # Remove columns from tax_invoices
    op.drop_column('tax_invoices', 'generation_trigger')
    op.drop_column('tax_invoices', 'shipment_id')

    # Remove columns from shipments
    op.drop_column('shipments', 'goods_issue_reference')
    op.drop_column('shipments', 'goods_issue_by')
    op.drop_column('shipments', 'goods_issue_at')
