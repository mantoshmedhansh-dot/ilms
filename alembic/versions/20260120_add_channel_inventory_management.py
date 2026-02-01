"""Add channel inventory management tables and fields

Revision ID: 20260120_channel_inv
Revises: ee15987e65dd
Create Date: 2026-01-20

This migration adds:
1. product_channel_settings table for per-product channel allocation settings
2. allocated_channel_id field to stock_items table for channel tracking
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '20260120_channel_inv'
down_revision: Union[str, None] = 'ee15987e65dd'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create product_channel_settings table
    op.create_table(
        'product_channel_settings',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('product_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('products.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('channel_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('sales_channels.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('warehouse_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('warehouses.id', ondelete='CASCADE'), nullable=False, index=True),
        # Allocation defaults
        sa.Column('default_allocation_percentage', sa.Integer(), nullable=True, comment='Default % of GRN to allocate to this channel'),
        sa.Column('default_allocation_qty', sa.Integer(), default=0, nullable=False, comment='Default fixed qty to allocate on GRN'),
        # Auto-replenish settings
        sa.Column('safety_stock', sa.Integer(), default=0, nullable=False, comment='Target level to maintain'),
        sa.Column('reorder_point', sa.Integer(), default=0, nullable=False, comment='Trigger replenishment when below this'),
        sa.Column('max_allocation', sa.Integer(), nullable=True, comment='Never exceed this allocation'),
        # Flags
        sa.Column('auto_replenish_enabled', sa.Boolean(), default=True, nullable=False),
        sa.Column('replenish_from_shared_pool', sa.Boolean(), default=True, nullable=False),
        # Sync settings
        sa.Column('sync_enabled', sa.Boolean(), default=True, nullable=False),
        sa.Column('sync_buffer_percentage', sa.Integer(), nullable=True, comment='Additional buffer % when syncing'),
        # Status
        sa.Column('is_active', sa.Boolean(), default=True, nullable=False),
        # Timestamps
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),
        # Unique constraint
        sa.UniqueConstraint('product_id', 'channel_id', 'warehouse_id', name='uq_product_channel_warehouse_settings'),
    )

    # 2. Add allocated_channel_id to stock_items table
    op.add_column(
        'stock_items',
        sa.Column(
            'allocated_channel_id',
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey('sales_channels.id', ondelete='SET NULL'),
            nullable=True,
            comment='Channel this stock item is allocated to'
        )
    )

    # 3. Create index for faster lookups
    op.create_index(
        'ix_stock_items_allocated_channel_id',
        'stock_items',
        ['allocated_channel_id']
    )

    # 4. Add safety_stock and reorder_point to channel_inventory if not exists
    # Check if columns exist first to make migration idempotent
    connection = op.get_bind()
    inspector = sa.inspect(connection)
    columns = [col['name'] for col in inspector.get_columns('channel_inventory')]

    if 'safety_stock' not in columns:
        op.add_column(
            'channel_inventory',
            sa.Column('safety_stock', sa.Integer(), default=0, nullable=True, comment='Target level for auto-replenish')
        )

    if 'reorder_point' not in columns:
        op.add_column(
            'channel_inventory',
            sa.Column('reorder_point', sa.Integer(), default=0, nullable=True, comment='Trigger auto-replenish below this')
        )

    if 'auto_replenish_enabled' not in columns:
        op.add_column(
            'channel_inventory',
            sa.Column('auto_replenish_enabled', sa.Boolean(), default=True, nullable=True)
        )


def downgrade() -> None:
    # Remove index
    op.drop_index('ix_stock_items_allocated_channel_id', table_name='stock_items')

    # Remove column from stock_items
    op.drop_column('stock_items', 'allocated_channel_id')

    # Remove columns from channel_inventory
    connection = op.get_bind()
    inspector = sa.inspect(connection)
    columns = [col['name'] for col in inspector.get_columns('channel_inventory')]

    if 'safety_stock' in columns:
        op.drop_column('channel_inventory', 'safety_stock')
    if 'reorder_point' in columns:
        op.drop_column('channel_inventory', 'reorder_point')
    if 'auto_replenish_enabled' in columns:
        op.drop_column('channel_inventory', 'auto_replenish_enabled')

    # Drop product_channel_settings table
    op.drop_table('product_channel_settings')
