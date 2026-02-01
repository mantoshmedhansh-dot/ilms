"""Add product_costs table for COGS auto-calculation

Revision ID: 20260119_product_costs
Revises:
Create Date: 2026-01-19

Adds table for product cost tracking using Weighted Average Cost method.
This enables automatic COGS calculation from GRN receipts (Purchase Orders).
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy import text


# revision identifiers, used by Alembic.
revision = '20260119_product_costs'
down_revision = None  # Will be filled automatically
branch_labels = None
depends_on = None


def table_exists(table_name: str) -> bool:
    """Check if a table exists."""
    conn = op.get_bind()
    result = conn.execute(text(f"""
        SELECT EXISTS (
            SELECT 1 FROM information_schema.tables
            WHERE table_name = '{table_name}'
        )
    """))
    return result.scalar()


def upgrade() -> None:
    """Create product_costs table."""

    if not table_exists('product_costs'):
        op.create_table(
            'product_costs',
            # Primary Key
            sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),

            # Product Reference
            sa.Column('product_id', UUID(as_uuid=True), sa.ForeignKey('products.id', ondelete='CASCADE'), nullable=False),
            sa.Column('variant_id', UUID(as_uuid=True), sa.ForeignKey('product_variants.id', ondelete='CASCADE'), nullable=True),

            # Warehouse (NULL = company-wide aggregate)
            sa.Column('warehouse_id', UUID(as_uuid=True), sa.ForeignKey('warehouses.id', ondelete='SET NULL'), nullable=True),

            # Valuation Method: WEIGHTED_AVG, FIFO, SPECIFIC_ID
            sa.Column('valuation_method', sa.String(20), nullable=False, server_default='WEIGHTED_AVG'),

            # Cost Fields - Auto-calculated from GRN
            sa.Column('average_cost', sa.Numeric(12, 2), nullable=False, server_default='0'),
            sa.Column('last_purchase_cost', sa.Numeric(12, 2), nullable=True),
            sa.Column('standard_cost', sa.Numeric(12, 2), nullable=True),

            # Inventory Position
            sa.Column('quantity_on_hand', sa.Integer, nullable=False, server_default='0'),
            sa.Column('total_value', sa.Numeric(14, 2), nullable=False, server_default='0'),

            # Tracking
            sa.Column('last_grn_id', UUID(as_uuid=True), sa.ForeignKey('goods_receipt_notes.id', ondelete='SET NULL'), nullable=True),
            sa.Column('last_calculated_at', sa.DateTime(timezone=True), nullable=True),

            # Cost History (JSONB array of cost movements)
            # Format: [{"date": "ISO", "quantity": int, "unit_cost": float, "grn_id": uuid, "running_average": float}]
            sa.Column('cost_history', JSONB, nullable=True, server_default='[]'),

            # Timestamps
            sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')),
            sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')),
        )

        # Create indexes for fast lookups
        op.create_index('idx_product_costs_product', 'product_costs', ['product_id'])
        op.create_index('idx_product_costs_warehouse', 'product_costs', ['warehouse_id'])
        op.create_index('idx_product_costs_variant', 'product_costs', ['variant_id'])

        # Unique constraint: one cost record per product+variant+warehouse
        op.create_unique_constraint(
            'uq_product_cost',
            'product_costs',
            ['product_id', 'variant_id', 'warehouse_id']
        )

        print("Created product_costs table successfully")

    else:
        print("Table product_costs already exists, skipping")


def downgrade() -> None:
    """Drop product_costs table."""

    if table_exists('product_costs'):
        op.drop_table('product_costs')
        print("Dropped product_costs table")
