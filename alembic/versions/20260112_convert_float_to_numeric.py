"""Convert Float columns to Numeric for money fields

Revision ID: convert_float_to_numeric
Revises: fix_enum_case_mismatch
Create Date: 2026-01-12

This migration converts Float columns to Numeric(precision, scale) for money/currency fields
to avoid floating-point precision errors in financial calculations.

Affected tables and columns:
- stock_items: purchase_price, landed_cost
- service_requests: total_parts_cost, labor_charges, service_charges, travel_charges, total_charges, payment_collected
- warranty_claims: refund_amount, parts_cost, labor_cost, total_cost
- stock_adjustments: total_value_impact
- stock_adjustment_items: unit_cost, value_impact
- cycle_counts: total_variance_value
- amc_contracts: base_price, tax_amount, discount_amount, total_amount, discount_on_parts
- amc_templates: base_price, tax_rate, discount_on_parts
- stock_transfers: total_value
- stock_transfer_items: unit_cost, total_cost
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'convert_float_to_numeric'
down_revision: Union[str, None] = 'fix_enum_case_mismatch'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Convert Float columns to Numeric for better precision."""

    # ==================== stock_items ====================
    op.alter_column('stock_items', 'purchase_price',
                    type_=sa.Numeric(12, 2),
                    existing_type=sa.Float(),
                    postgresql_using='purchase_price::numeric(12,2)')
    op.alter_column('stock_items', 'landed_cost',
                    type_=sa.Numeric(12, 2),
                    existing_type=sa.Float(),
                    postgresql_using='landed_cost::numeric(12,2)')

    # ==================== service_requests ====================
    op.alter_column('service_requests', 'total_parts_cost',
                    type_=sa.Numeric(12, 2),
                    existing_type=sa.Float(),
                    postgresql_using='total_parts_cost::numeric(12,2)')
    op.alter_column('service_requests', 'labor_charges',
                    type_=sa.Numeric(12, 2),
                    existing_type=sa.Float(),
                    postgresql_using='labor_charges::numeric(12,2)')
    op.alter_column('service_requests', 'service_charges',
                    type_=sa.Numeric(12, 2),
                    existing_type=sa.Float(),
                    postgresql_using='service_charges::numeric(12,2)')
    op.alter_column('service_requests', 'travel_charges',
                    type_=sa.Numeric(12, 2),
                    existing_type=sa.Float(),
                    postgresql_using='travel_charges::numeric(12,2)')
    op.alter_column('service_requests', 'total_charges',
                    type_=sa.Numeric(12, 2),
                    existing_type=sa.Float(),
                    postgresql_using='total_charges::numeric(12,2)')
    op.alter_column('service_requests', 'payment_collected',
                    type_=sa.Numeric(12, 2),
                    existing_type=sa.Float(),
                    postgresql_using='payment_collected::numeric(12,2)')

    # ==================== warranty_claims ====================
    op.alter_column('warranty_claims', 'refund_amount',
                    type_=sa.Numeric(12, 2),
                    existing_type=sa.Float(),
                    postgresql_using='refund_amount::numeric(12,2)')
    op.alter_column('warranty_claims', 'parts_cost',
                    type_=sa.Numeric(12, 2),
                    existing_type=sa.Float(),
                    postgresql_using='parts_cost::numeric(12,2)')
    op.alter_column('warranty_claims', 'labor_cost',
                    type_=sa.Numeric(12, 2),
                    existing_type=sa.Float(),
                    postgresql_using='labor_cost::numeric(12,2)')
    op.alter_column('warranty_claims', 'total_cost',
                    type_=sa.Numeric(12, 2),
                    existing_type=sa.Float(),
                    postgresql_using='total_cost::numeric(12,2)')

    # ==================== stock_adjustments ====================
    op.alter_column('stock_adjustments', 'total_value_impact',
                    type_=sa.Numeric(14, 2),
                    existing_type=sa.Float(),
                    postgresql_using='total_value_impact::numeric(14,2)')

    # ==================== stock_adjustment_items ====================
    op.alter_column('stock_adjustment_items', 'unit_cost',
                    type_=sa.Numeric(12, 2),
                    existing_type=sa.Float(),
                    postgresql_using='unit_cost::numeric(12,2)')
    op.alter_column('stock_adjustment_items', 'value_impact',
                    type_=sa.Numeric(14, 2),
                    existing_type=sa.Float(),
                    postgresql_using='value_impact::numeric(14,2)')

    # ==================== cycle_counts ====================
    op.alter_column('cycle_counts', 'total_variance_value',
                    type_=sa.Numeric(14, 2),
                    existing_type=sa.Float(),
                    postgresql_using='total_variance_value::numeric(14,2)')

    # ==================== amc_contracts ====================
    op.alter_column('amc_contracts', 'base_price',
                    type_=sa.Numeric(12, 2),
                    existing_type=sa.Float(),
                    postgresql_using='base_price::numeric(12,2)')
    op.alter_column('amc_contracts', 'tax_amount',
                    type_=sa.Numeric(12, 2),
                    existing_type=sa.Float(),
                    postgresql_using='tax_amount::numeric(12,2)')
    op.alter_column('amc_contracts', 'discount_amount',
                    type_=sa.Numeric(12, 2),
                    existing_type=sa.Float(),
                    postgresql_using='discount_amount::numeric(12,2)')
    op.alter_column('amc_contracts', 'total_amount',
                    type_=sa.Numeric(12, 2),
                    existing_type=sa.Float(),
                    postgresql_using='total_amount::numeric(12,2)')
    op.alter_column('amc_contracts', 'discount_on_parts',
                    type_=sa.Numeric(5, 2),
                    existing_type=sa.Float(),
                    postgresql_using='discount_on_parts::numeric(5,2)')

    # ==================== amc_templates ====================
    op.alter_column('amc_templates', 'base_price',
                    type_=sa.Numeric(12, 2),
                    existing_type=sa.Float(),
                    postgresql_using='base_price::numeric(12,2)')
    op.alter_column('amc_templates', 'tax_rate',
                    type_=sa.Numeric(5, 2),
                    existing_type=sa.Float(),
                    postgresql_using='tax_rate::numeric(5,2)')
    op.alter_column('amc_templates', 'discount_on_parts',
                    type_=sa.Numeric(5, 2),
                    existing_type=sa.Float(),
                    postgresql_using='discount_on_parts::numeric(5,2)')

    # ==================== stock_transfers ====================
    op.alter_column('stock_transfers', 'total_value',
                    type_=sa.Numeric(14, 2),
                    existing_type=sa.Float(),
                    postgresql_using='total_value::numeric(14,2)')

    # ==================== stock_transfer_items ====================
    op.alter_column('stock_transfer_items', 'unit_cost',
                    type_=sa.Numeric(12, 2),
                    existing_type=sa.Float(),
                    postgresql_using='unit_cost::numeric(12,2)')
    op.alter_column('stock_transfer_items', 'total_cost',
                    type_=sa.Numeric(14, 2),
                    existing_type=sa.Float(),
                    postgresql_using='total_cost::numeric(14,2)')


def downgrade() -> None:
    """Revert Numeric columns back to Float."""

    # ==================== stock_items ====================
    op.alter_column('stock_items', 'purchase_price',
                    type_=sa.Float(),
                    existing_type=sa.Numeric(12, 2))
    op.alter_column('stock_items', 'landed_cost',
                    type_=sa.Float(),
                    existing_type=sa.Numeric(12, 2))

    # ==================== service_requests ====================
    op.alter_column('service_requests', 'total_parts_cost',
                    type_=sa.Float(),
                    existing_type=sa.Numeric(12, 2))
    op.alter_column('service_requests', 'labor_charges',
                    type_=sa.Float(),
                    existing_type=sa.Numeric(12, 2))
    op.alter_column('service_requests', 'service_charges',
                    type_=sa.Float(),
                    existing_type=sa.Numeric(12, 2))
    op.alter_column('service_requests', 'travel_charges',
                    type_=sa.Float(),
                    existing_type=sa.Numeric(12, 2))
    op.alter_column('service_requests', 'total_charges',
                    type_=sa.Float(),
                    existing_type=sa.Numeric(12, 2))
    op.alter_column('service_requests', 'payment_collected',
                    type_=sa.Float(),
                    existing_type=sa.Numeric(12, 2))

    # ==================== warranty_claims ====================
    op.alter_column('warranty_claims', 'refund_amount',
                    type_=sa.Float(),
                    existing_type=sa.Numeric(12, 2))
    op.alter_column('warranty_claims', 'parts_cost',
                    type_=sa.Float(),
                    existing_type=sa.Numeric(12, 2))
    op.alter_column('warranty_claims', 'labor_cost',
                    type_=sa.Float(),
                    existing_type=sa.Numeric(12, 2))
    op.alter_column('warranty_claims', 'total_cost',
                    type_=sa.Float(),
                    existing_type=sa.Numeric(12, 2))

    # ==================== stock_adjustments ====================
    op.alter_column('stock_adjustments', 'total_value_impact',
                    type_=sa.Float(),
                    existing_type=sa.Numeric(14, 2))

    # ==================== stock_adjustment_items ====================
    op.alter_column('stock_adjustment_items', 'unit_cost',
                    type_=sa.Float(),
                    existing_type=sa.Numeric(12, 2))
    op.alter_column('stock_adjustment_items', 'value_impact',
                    type_=sa.Float(),
                    existing_type=sa.Numeric(14, 2))

    # ==================== cycle_counts ====================
    op.alter_column('cycle_counts', 'total_variance_value',
                    type_=sa.Float(),
                    existing_type=sa.Numeric(14, 2))

    # ==================== amc_contracts ====================
    op.alter_column('amc_contracts', 'base_price',
                    type_=sa.Float(),
                    existing_type=sa.Numeric(12, 2))
    op.alter_column('amc_contracts', 'tax_amount',
                    type_=sa.Float(),
                    existing_type=sa.Numeric(12, 2))
    op.alter_column('amc_contracts', 'discount_amount',
                    type_=sa.Float(),
                    existing_type=sa.Numeric(12, 2))
    op.alter_column('amc_contracts', 'total_amount',
                    type_=sa.Float(),
                    existing_type=sa.Numeric(12, 2))
    op.alter_column('amc_contracts', 'discount_on_parts',
                    type_=sa.Float(),
                    existing_type=sa.Numeric(5, 2))

    # ==================== amc_templates ====================
    op.alter_column('amc_templates', 'base_price',
                    type_=sa.Float(),
                    existing_type=sa.Numeric(12, 2))
    op.alter_column('amc_templates', 'tax_rate',
                    type_=sa.Float(),
                    existing_type=sa.Numeric(5, 2))
    op.alter_column('amc_templates', 'discount_on_parts',
                    type_=sa.Float(),
                    existing_type=sa.Numeric(5, 2))

    # ==================== stock_transfers ====================
    op.alter_column('stock_transfers', 'total_value',
                    type_=sa.Float(),
                    existing_type=sa.Numeric(14, 2))

    # ==================== stock_transfer_items ====================
    op.alter_column('stock_transfer_items', 'unit_cost',
                    type_=sa.Float(),
                    existing_type=sa.Numeric(12, 2))
    op.alter_column('stock_transfer_items', 'total_cost',
                    type_=sa.Float(),
                    existing_type=sa.Numeric(14, 2))
