"""Add Warehouse Billing tables - Phase 10: Storage & Operations Billing

Revision ID: 20260205_billing
Revises: 20260205_returns
Create Date: 2026-02-05

Tables created:
- billing_contracts: Customer/3PL billing agreements
- billing_rate_cards: Rate definitions
- storage_charges: Storage space charges
- handling_charges: Activity-based handling fees
- vas_charges: Value-added service charges
- billing_invoices: Generated invoices
- billing_invoice_items: Invoice line items
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '20260205_billing'
down_revision = '20260205_returns'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # =========================================================================
    # BILLING_CONTRACTS - Billing Agreements
    # =========================================================================
    op.create_table(
        'billing_contracts',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False, index=True),

        sa.Column('contract_number', sa.String(30), nullable=False, index=True),
        sa.Column('contract_name', sa.String(200), nullable=False),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('status', sa.String(30), default='DRAFT', nullable=False, index=True),

        sa.Column('customer_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('customers.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('warehouse_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('warehouses.id', ondelete='SET NULL'), nullable=True, index=True),

        sa.Column('billing_type', sa.String(30), default='HYBRID', nullable=False),
        sa.Column('billing_period', sa.String(20), default='MONTHLY', nullable=False),
        sa.Column('billing_day', sa.Integer, default=1),

        sa.Column('start_date', sa.Date, nullable=False),
        sa.Column('end_date', sa.Date, nullable=True),
        sa.Column('renewal_date', sa.Date, nullable=True),
        sa.Column('auto_renew', sa.Boolean, default=False),

        sa.Column('minimum_storage_fee', sa.Numeric(12, 2), default=0),
        sa.Column('minimum_handling_fee', sa.Numeric(12, 2), default=0),
        sa.Column('minimum_monthly_fee', sa.Numeric(12, 2), default=0),

        sa.Column('payment_terms_days', sa.Integer, default=30),
        sa.Column('currency', sa.String(3), default='INR'),

        sa.Column('late_fee_percent', sa.Numeric(5, 2), default=1.5),
        sa.Column('grace_period_days', sa.Integer, default=5),

        sa.Column('volume_discounts', postgresql.JSONB, nullable=True),
        sa.Column('special_terms', sa.Text, nullable=True),
        sa.Column('notes', sa.Text, nullable=True),

        sa.Column('created_by', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('approved_by', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('approved_at', sa.DateTime(timezone=True), nullable=True),

        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_unique_constraint('uq_billing_contract_number', 'billing_contracts',
                                ['tenant_id', 'contract_number'])
    op.create_index('ix_billing_contracts_status', 'billing_contracts', ['status'])

    # =========================================================================
    # BILLING_RATE_CARDS - Rate Definitions
    # =========================================================================
    op.create_table(
        'billing_rate_cards',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False, index=True),

        sa.Column('contract_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('billing_contracts.id', ondelete='CASCADE'), nullable=False, index=True),

        sa.Column('charge_category', sa.String(30), nullable=False),
        sa.Column('charge_type', sa.String(50), nullable=False, index=True),
        sa.Column('charge_name', sa.String(100), nullable=False),
        sa.Column('description', sa.Text, nullable=True),

        sa.Column('billing_model', sa.String(30), nullable=False),
        sa.Column('uom', sa.String(20), nullable=False),

        sa.Column('base_rate', sa.Numeric(12, 4), nullable=False),
        sa.Column('min_charge', sa.Numeric(10, 2), default=0),
        sa.Column('max_charge', sa.Numeric(10, 2), nullable=True),

        sa.Column('tiered_rates', postgresql.JSONB, nullable=True),
        sa.Column('time_based_rates', postgresql.JSONB, nullable=True),

        sa.Column('effective_from', sa.Date, nullable=False),
        sa.Column('effective_to', sa.Date, nullable=True),

        sa.Column('is_active', sa.Boolean, default=True),
        sa.Column('notes', sa.Text, nullable=True),

        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_index('ix_billing_rate_cards_contract', 'billing_rate_cards', ['contract_id'])
    op.create_index('ix_billing_rate_cards_charge', 'billing_rate_cards', ['charge_type'])

    # =========================================================================
    # BILLING_INVOICES - Generated Invoices (created before charges for FK)
    # =========================================================================
    op.create_table(
        'billing_invoices',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False, index=True),

        sa.Column('invoice_number', sa.String(30), nullable=False, unique=True, index=True),
        sa.Column('status', sa.String(30), default='DRAFT', nullable=False, index=True),

        sa.Column('contract_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('billing_contracts.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('customer_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('customers.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('warehouse_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('warehouses.id', ondelete='SET NULL'), nullable=True, index=True),

        sa.Column('period_start', sa.Date, nullable=False),
        sa.Column('period_end', sa.Date, nullable=False),

        sa.Column('invoice_date', sa.Date, nullable=False, index=True),
        sa.Column('due_date', sa.Date, nullable=False),

        sa.Column('storage_amount', sa.Numeric(12, 2), default=0),
        sa.Column('handling_amount', sa.Numeric(12, 2), default=0),
        sa.Column('vas_amount', sa.Numeric(12, 2), default=0),
        sa.Column('labor_amount', sa.Numeric(12, 2), default=0),

        sa.Column('subtotal', sa.Numeric(12, 2), nullable=False),

        sa.Column('discount_amount', sa.Numeric(10, 2), default=0),
        sa.Column('discount_reason', sa.String(200), nullable=True),

        sa.Column('adjustment_amount', sa.Numeric(10, 2), default=0),
        sa.Column('adjustment_reason', sa.String(200), nullable=True),

        sa.Column('tax_amount', sa.Numeric(10, 2), default=0),
        sa.Column('tax_rate', sa.Numeric(5, 2), default=0),

        sa.Column('total_amount', sa.Numeric(12, 2), nullable=False),

        sa.Column('paid_amount', sa.Numeric(12, 2), default=0),
        sa.Column('balance_due', sa.Numeric(12, 2), nullable=False),

        sa.Column('late_fee', sa.Numeric(10, 2), default=0),
        sa.Column('currency', sa.String(3), default='INR'),

        sa.Column('summary', postgresql.JSONB, nullable=True),

        sa.Column('sent_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('sent_to', sa.String(200), nullable=True),

        sa.Column('last_payment_date', sa.Date, nullable=True),
        sa.Column('payment_reference', sa.String(100), nullable=True),

        sa.Column('notes', sa.Text, nullable=True),
        sa.Column('internal_notes', sa.Text, nullable=True),

        sa.Column('disputed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('dispute_reason', sa.Text, nullable=True),
        sa.Column('dispute_resolved_at', sa.DateTime(timezone=True), nullable=True),

        sa.Column('created_by', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('approved_by', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('approved_at', sa.DateTime(timezone=True), nullable=True),

        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_index('ix_billing_invoices_status', 'billing_invoices', ['status'])
    op.create_index('ix_billing_invoices_customer', 'billing_invoices', ['customer_id'])
    op.create_index('ix_billing_invoices_date', 'billing_invoices', ['invoice_date'])

    # =========================================================================
    # STORAGE_CHARGES - Storage Space Charges
    # =========================================================================
    op.create_table(
        'storage_charges',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False, index=True),

        sa.Column('contract_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('billing_contracts.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('customer_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('customers.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('warehouse_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('warehouses.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('rate_card_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('billing_rate_cards.id', ondelete='SET NULL'), nullable=True),

        sa.Column('charge_date', sa.Date, nullable=False, index=True),

        sa.Column('storage_type', sa.String(50), nullable=False),
        sa.Column('zone_id', postgresql.UUID(as_uuid=True), nullable=True),

        sa.Column('quantity', sa.Numeric(12, 2), nullable=False),
        sa.Column('uom', sa.String(20), nullable=False),

        sa.Column('rate', sa.Numeric(12, 4), nullable=False),
        sa.Column('amount', sa.Numeric(12, 2), nullable=False),

        sa.Column('breakdown', postgresql.JSONB, nullable=True),

        sa.Column('invoice_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('billing_invoices.id', ondelete='SET NULL'), nullable=True, index=True),
        sa.Column('is_billed', sa.Boolean, default=False),

        sa.Column('notes', sa.Text, nullable=True),

        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_index('ix_storage_charges_date', 'storage_charges', ['charge_date'])
    op.create_index('ix_storage_charges_customer', 'storage_charges', ['customer_id'])

    # =========================================================================
    # HANDLING_CHARGES - Activity-based Handling Fees
    # =========================================================================
    op.create_table(
        'handling_charges',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False, index=True),

        sa.Column('contract_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('billing_contracts.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('customer_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('customers.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('warehouse_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('warehouses.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('rate_card_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('billing_rate_cards.id', ondelete='SET NULL'), nullable=True),

        sa.Column('charge_date', sa.Date, nullable=False, index=True),

        sa.Column('charge_category', sa.String(30), nullable=False),
        sa.Column('charge_type', sa.String(50), nullable=False, index=True),
        sa.Column('charge_description', sa.String(200), nullable=False),

        sa.Column('source_type', sa.String(30), nullable=True),
        sa.Column('source_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('source_number', sa.String(50), nullable=True),

        sa.Column('quantity', sa.Numeric(12, 2), nullable=False),
        sa.Column('uom', sa.String(20), nullable=False),

        sa.Column('rate', sa.Numeric(12, 4), nullable=False),
        sa.Column('amount', sa.Numeric(12, 2), nullable=False),

        sa.Column('labor_hours', sa.Numeric(6, 2), nullable=True),
        sa.Column('labor_rate', sa.Numeric(10, 2), nullable=True),
        sa.Column('labor_amount', sa.Numeric(10, 2), default=0),

        sa.Column('invoice_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('billing_invoices.id', ondelete='SET NULL'), nullable=True, index=True),
        sa.Column('is_billed', sa.Boolean, default=False),

        sa.Column('notes', sa.Text, nullable=True),

        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_index('ix_handling_charges_date', 'handling_charges', ['charge_date'])
    op.create_index('ix_handling_charges_customer', 'handling_charges', ['customer_id'])
    op.create_index('ix_handling_charges_type', 'handling_charges', ['charge_type'])

    # =========================================================================
    # VAS_CHARGES - Value-Added Service Charges
    # =========================================================================
    op.create_table(
        'vas_charges',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False, index=True),

        sa.Column('contract_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('billing_contracts.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('customer_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('customers.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('warehouse_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('warehouses.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('rate_card_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('billing_rate_cards.id', ondelete='SET NULL'), nullable=True),

        sa.Column('charge_date', sa.Date, nullable=False, index=True),

        sa.Column('service_type', sa.String(50), nullable=False),
        sa.Column('service_name', sa.String(100), nullable=False),
        sa.Column('service_description', sa.Text, nullable=True),

        sa.Column('source_type', sa.String(30), nullable=True),
        sa.Column('source_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('source_number', sa.String(50), nullable=True),

        sa.Column('quantity', sa.Numeric(12, 2), nullable=False),
        sa.Column('uom', sa.String(20), nullable=False),

        sa.Column('rate', sa.Numeric(12, 4), nullable=False),
        sa.Column('amount', sa.Numeric(12, 2), nullable=False),

        sa.Column('materials_cost', sa.Numeric(10, 2), default=0),
        sa.Column('materials_detail', postgresql.JSONB, nullable=True),

        sa.Column('invoice_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('billing_invoices.id', ondelete='SET NULL'), nullable=True, index=True),
        sa.Column('is_billed', sa.Boolean, default=False),

        sa.Column('notes', sa.Text, nullable=True),

        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_index('ix_vas_charges_date', 'vas_charges', ['charge_date'])
    op.create_index('ix_vas_charges_customer', 'vas_charges', ['customer_id'])

    # =========================================================================
    # BILLING_INVOICE_ITEMS - Invoice Line Items
    # =========================================================================
    op.create_table(
        'billing_invoice_items',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False, index=True),

        sa.Column('invoice_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('billing_invoices.id', ondelete='CASCADE'), nullable=False, index=True),

        sa.Column('charge_category', sa.String(30), nullable=False),
        sa.Column('charge_type', sa.String(50), nullable=False),
        sa.Column('description', sa.String(500), nullable=False),

        sa.Column('quantity', sa.Numeric(12, 2), nullable=False),
        sa.Column('uom', sa.String(20), nullable=False),

        sa.Column('rate', sa.Numeric(12, 4), nullable=False),
        sa.Column('amount', sa.Numeric(12, 2), nullable=False),

        sa.Column('line_number', sa.Integer, nullable=False),

        sa.Column('notes', sa.Text, nullable=True),

        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table('billing_invoice_items')
    op.drop_table('vas_charges')
    op.drop_table('handling_charges')
    op.drop_table('storage_charges')
    op.drop_table('billing_invoices')
    op.drop_table('billing_rate_cards')
    op.drop_table('billing_contracts')
