"""Convert serialization tables VARCHAR(36) columns to native UUID type

Revision ID: convert_serialization_uuid
Revises: fix_enum_case_mismatch_part2
Create Date: 2026-01-15

This migration converts all VARCHAR(36) columns in serialization tables to
native PostgreSQL UUID type for structural consistency across the codebase.

Tables affected:
- serial_sequences
- product_serial_sequences
- po_serials
- model_code_references
- supplier_codes
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'convert_serialization_uuid'
down_revision: Union[str, None] = 'fix_enum_case_mismatch_part2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Convert VARCHAR(36) columns to UUID type in all serialization tables."""

    # Detect database dialect
    bind = op.get_bind()
    dialect = bind.dialect.name

    if dialect == 'sqlite':
        # SQLite doesn't support ALTER COLUMN TYPE, so we need to recreate tables
        upgrade_sqlite()
    else:
        # PostgreSQL supports ALTER COLUMN TYPE with USING clause
        upgrade_postgresql()


def upgrade_postgresql() -> None:
    """PostgreSQL-specific upgrade using ALTER COLUMN TYPE."""

    # ==================== serial_sequences ====================
    op.execute("""
        ALTER TABLE serial_sequences
        ALTER COLUMN id TYPE UUID USING id::uuid
    """)
    op.execute("""
        ALTER TABLE serial_sequences
        ALTER COLUMN product_id TYPE UUID USING product_id::uuid
    """)

    # ==================== product_serial_sequences ====================
    op.execute("""
        ALTER TABLE product_serial_sequences
        ALTER COLUMN id TYPE UUID USING id::uuid
    """)
    op.execute("""
        ALTER TABLE product_serial_sequences
        ALTER COLUMN product_id TYPE UUID USING product_id::uuid
    """)

    # ==================== po_serials ====================
    op.execute("""
        ALTER TABLE po_serials
        ALTER COLUMN id TYPE UUID USING id::uuid
    """)
    op.execute("""
        ALTER TABLE po_serials
        ALTER COLUMN po_id TYPE UUID USING po_id::uuid
    """)
    op.execute("""
        ALTER TABLE po_serials
        ALTER COLUMN po_item_id TYPE UUID USING po_item_id::uuid
    """)
    op.execute("""
        ALTER TABLE po_serials
        ALTER COLUMN product_id TYPE UUID USING product_id::uuid
    """)
    op.execute("""
        ALTER TABLE po_serials
        ALTER COLUMN grn_id TYPE UUID USING grn_id::uuid
    """)
    op.execute("""
        ALTER TABLE po_serials
        ALTER COLUMN grn_item_id TYPE UUID USING grn_item_id::uuid
    """)
    op.execute("""
        ALTER TABLE po_serials
        ALTER COLUMN received_by TYPE UUID USING received_by::uuid
    """)
    op.execute("""
        ALTER TABLE po_serials
        ALTER COLUMN stock_item_id TYPE UUID USING stock_item_id::uuid
    """)
    op.execute("""
        ALTER TABLE po_serials
        ALTER COLUMN order_id TYPE UUID USING order_id::uuid
    """)
    op.execute("""
        ALTER TABLE po_serials
        ALTER COLUMN order_item_id TYPE UUID USING order_item_id::uuid
    """)
    op.execute("""
        ALTER TABLE po_serials
        ALTER COLUMN customer_id TYPE UUID USING customer_id::uuid
    """)

    # ==================== model_code_references ====================
    op.execute("""
        ALTER TABLE model_code_references
        ALTER COLUMN id TYPE UUID USING id::uuid
    """)
    op.execute("""
        ALTER TABLE model_code_references
        ALTER COLUMN product_id TYPE UUID USING product_id::uuid
    """)

    # ==================== supplier_codes ====================
    op.execute("""
        ALTER TABLE supplier_codes
        ALTER COLUMN id TYPE UUID USING id::uuid
    """)
    op.execute("""
        ALTER TABLE supplier_codes
        ALTER COLUMN vendor_id TYPE UUID USING vendor_id::uuid
    """)


def upgrade_sqlite() -> None:
    """SQLite-specific upgrade by recreating tables with new column types."""

    # For SQLite, we need to use batch operations to change column types
    # This effectively recreates the table with the new schema

    # ==================== serial_sequences ====================
    with op.batch_alter_table('serial_sequences', schema=None) as batch_op:
        # SQLite stores UUIDs as text, so we just need to ensure the model matches
        # The actual data format (UUID string) remains compatible
        pass  # Column types in SQLite are flexible

    # ==================== product_serial_sequences ====================
    with op.batch_alter_table('product_serial_sequences', schema=None) as batch_op:
        pass  # Column types in SQLite are flexible

    # ==================== po_serials ====================
    with op.batch_alter_table('po_serials', schema=None) as batch_op:
        pass  # Column types in SQLite are flexible

    # ==================== model_code_references ====================
    with op.batch_alter_table('model_code_references', schema=None) as batch_op:
        pass  # Column types in SQLite are flexible

    # ==================== supplier_codes ====================
    with op.batch_alter_table('supplier_codes', schema=None) as batch_op:
        pass  # Column types in SQLite are flexible

    # Note: SQLite doesn't have a native UUID type, so it stores UUIDs as TEXT
    # The migration is effectively a no-op for SQLite since the data format
    # (UUID strings like '550e8400-e29b-41d4-a716-446655440000') is the same


def downgrade() -> None:
    """Revert UUID columns back to VARCHAR(36)."""

    bind = op.get_bind()
    dialect = bind.dialect.name

    if dialect == 'sqlite':
        downgrade_sqlite()
    else:
        downgrade_postgresql()


def downgrade_postgresql() -> None:
    """PostgreSQL-specific downgrade."""

    # ==================== serial_sequences ====================
    op.execute("""
        ALTER TABLE serial_sequences
        ALTER COLUMN id TYPE VARCHAR(36) USING id::text
    """)
    op.execute("""
        ALTER TABLE serial_sequences
        ALTER COLUMN product_id TYPE VARCHAR(36) USING product_id::text
    """)

    # ==================== product_serial_sequences ====================
    op.execute("""
        ALTER TABLE product_serial_sequences
        ALTER COLUMN id TYPE VARCHAR(36) USING id::text
    """)
    op.execute("""
        ALTER TABLE product_serial_sequences
        ALTER COLUMN product_id TYPE VARCHAR(36) USING product_id::text
    """)

    # ==================== po_serials ====================
    op.execute("""
        ALTER TABLE po_serials
        ALTER COLUMN id TYPE VARCHAR(36) USING id::text
    """)
    op.execute("""
        ALTER TABLE po_serials
        ALTER COLUMN po_id TYPE VARCHAR(36) USING po_id::text
    """)
    op.execute("""
        ALTER TABLE po_serials
        ALTER COLUMN po_item_id TYPE VARCHAR(36) USING po_item_id::text
    """)
    op.execute("""
        ALTER TABLE po_serials
        ALTER COLUMN product_id TYPE VARCHAR(36) USING product_id::text
    """)
    op.execute("""
        ALTER TABLE po_serials
        ALTER COLUMN grn_id TYPE VARCHAR(36) USING grn_id::text
    """)
    op.execute("""
        ALTER TABLE po_serials
        ALTER COLUMN grn_item_id TYPE VARCHAR(36) USING grn_item_id::text
    """)
    op.execute("""
        ALTER TABLE po_serials
        ALTER COLUMN received_by TYPE VARCHAR(36) USING received_by::text
    """)
    op.execute("""
        ALTER TABLE po_serials
        ALTER COLUMN stock_item_id TYPE VARCHAR(36) USING stock_item_id::text
    """)
    op.execute("""
        ALTER TABLE po_serials
        ALTER COLUMN order_id TYPE VARCHAR(36) USING order_id::text
    """)
    op.execute("""
        ALTER TABLE po_serials
        ALTER COLUMN order_item_id TYPE VARCHAR(36) USING order_item_id::text
    """)
    op.execute("""
        ALTER TABLE po_serials
        ALTER COLUMN customer_id TYPE VARCHAR(36) USING customer_id::text
    """)

    # ==================== model_code_references ====================
    op.execute("""
        ALTER TABLE model_code_references
        ALTER COLUMN id TYPE VARCHAR(36) USING id::text
    """)
    op.execute("""
        ALTER TABLE model_code_references
        ALTER COLUMN product_id TYPE VARCHAR(36) USING product_id::text
    """)

    # ==================== supplier_codes ====================
    op.execute("""
        ALTER TABLE supplier_codes
        ALTER COLUMN id TYPE VARCHAR(36) USING id::text
    """)
    op.execute("""
        ALTER TABLE supplier_codes
        ALTER COLUMN vendor_id TYPE VARCHAR(36) USING vendor_id::text
    """)


def downgrade_sqlite() -> None:
    """SQLite-specific downgrade - no-op since SQLite uses TEXT for both."""
    pass
