"""Add wishlist table

Revision ID: add_wishlist_001
Revises: add_abandoned_cart_001
Create Date: 2026-01-18

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'add_wishlist_001'
down_revision: Union[str, None] = 'add_abandoned_cart_001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create wishlist_items table
    op.create_table(
        'wishlist_items',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('customer_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('product_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('variant_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('price_when_added', sa.Float(), nullable=True),
        sa.Column('notes', sa.String(500), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['customer_id'], ['customers.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['product_id'], ['products.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['variant_id'], ['product_variants.id'], ondelete='SET NULL'),
        sa.UniqueConstraint('customer_id', 'product_id', name='uq_wishlist_customer_product'),
    )

    # Create indexes
    op.create_index('ix_wishlist_customer_id', 'wishlist_items', ['customer_id'])
    op.create_index('ix_wishlist_product_id', 'wishlist_items', ['product_id'])


def downgrade() -> None:
    # Drop indexes
    op.drop_index('ix_wishlist_product_id', table_name='wishlist_items')
    op.drop_index('ix_wishlist_customer_id', table_name='wishlist_items')

    # Drop table
    op.drop_table('wishlist_items')
