"""Add document_sequences table for atomic number generation.

Revision ID: add_document_sequences
Revises: 20260116_convert_enum_to_varchar_phase2
Create Date: 2026-01-16

Industry Best Practice Document Numbering:
- Financial year based (April-March)
- Continuous within FY (no daily reset)
- Format: {PREFIX}/{COMPANY_CODE}/{FY}/{SEQUENCE}
- Example: PR/APL/25-26/00001
"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


# revision identifiers, used by Alembic.
revision: str = 'add_document_sequences'
down_revision: Union[str, None] = 'convert_enum_to_varchar_phase2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create document_sequences table."""

    # Check if table already exists
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    if 'document_sequences' in inspector.get_table_names():
        print("document_sequences table already exists, skipping...")
        return

    # Create document_sequences table
    op.create_table(
        'document_sequences',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('document_type', sa.String(10), nullable=False),
        sa.Column('document_name', sa.String(100), nullable=False),
        sa.Column('company_code', sa.String(10), nullable=False, server_default='APL'),
        sa.Column('financial_year', sa.String(10), nullable=False),
        sa.Column('current_number', sa.Integer, nullable=False, server_default='0'),
        sa.Column('padding_length', sa.Integer, nullable=False, server_default='5'),
        sa.Column('separator', sa.String(5), nullable=False, server_default='/'),
        sa.Column('is_active', sa.Boolean, nullable=False, server_default='true'),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')),
        sa.UniqueConstraint('document_type', 'financial_year', name='uq_document_type_fy'),
    )

    # Create index on document_type for faster lookups
    op.create_index('ix_document_sequences_document_type', 'document_sequences', ['document_type'])

    print("Created document_sequences table")

    # Initialize sequences from existing data
    _initialize_sequences(conn)


def _initialize_sequences(conn) -> None:
    """Initialize sequences from existing PRs, POs, GRNs, SRNs."""

    # Get current financial year
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc)
    year = now.year
    month = now.month

    if month >= 4:  # April onwards
        fy_start = year
        fy_end = year + 1
    else:  # Jan-Mar
        fy_start = year - 1
        fy_end = year

    fy = f"{fy_start % 100:02d}-{fy_end % 100:02d}"

    document_types = [
        ('PR', 'Purchase Requisition'),
        ('PO', 'Purchase Order'),
        ('GRN', 'Goods Receipt Note'),
        ('SRN', 'Sales Return Note'),
        ('ST', 'Stock Transfer'),
        ('SA', 'Stock Adjustment'),
        ('MF', 'Manifest'),
        ('PL', 'Picklist'),
    ]

    # Initialize all document types for current FY
    for doc_type, doc_name in document_types:
        # Check if sequence already exists
        result = conn.execute(
            sa.text("""
                SELECT current_number FROM document_sequences
                WHERE document_type = :doc_type AND financial_year = :fy
            """),
            {'doc_type': doc_type, 'fy': fy}
        ).fetchone()

        if result:
            print(f"  {doc_type} sequence already exists with current_number={result[0]}")
            continue

        # Get max number from existing records
        max_num = 0

        if doc_type == 'PR':
            # Check for both old format (PR-YYYYMMDD-XXXX) and new format (PR/APL/YY-YY/XXXXX)
            result = conn.execute(
                sa.text("""
                    SELECT requisition_number FROM purchase_requisitions
                    WHERE requisition_number LIKE :new_pattern
                    ORDER BY requisition_number DESC LIMIT 1
                """),
                {'new_pattern': f'PR/APL/{fy}/%'}
            ).fetchone()

            if result:
                try:
                    max_num = int(result[0].split('/')[-1])
                except (ValueError, IndexError):
                    pass

        elif doc_type == 'PO':
            result = conn.execute(
                sa.text("""
                    SELECT po_number FROM purchase_orders
                    WHERE po_number LIKE :pattern
                    ORDER BY po_number DESC LIMIT 1
                """),
                {'pattern': f'PO/APL/{fy}/%'}
            ).fetchone()

            if result:
                try:
                    max_num = int(result[0].split('/')[-1])
                except (ValueError, IndexError):
                    pass

        elif doc_type == 'GRN':
            result = conn.execute(
                sa.text("""
                    SELECT grn_number FROM goods_receipt_notes
                    WHERE grn_number LIKE :pattern
                    ORDER BY grn_number DESC LIMIT 1
                """),
                {'pattern': f'GRN/APL/{fy}/%'}
            ).fetchone()

            if result:
                try:
                    max_num = int(result[0].split('/')[-1])
                except (ValueError, IndexError):
                    pass

        elif doc_type == 'SRN':
            result = conn.execute(
                sa.text("""
                    SELECT srn_number FROM sales_return_notes
                    WHERE srn_number LIKE :pattern
                    ORDER BY srn_number DESC LIMIT 1
                """),
                {'pattern': f'SRN/APL/{fy}/%'}
            ).fetchone()

            if result:
                try:
                    max_num = int(result[0].split('/')[-1])
                except (ValueError, IndexError):
                    pass

        # Insert sequence record
        conn.execute(
            sa.text("""
                INSERT INTO document_sequences
                (id, document_type, document_name, company_code, financial_year,
                 current_number, padding_length, separator, is_active)
                VALUES
                (gen_random_uuid(), :doc_type, :doc_name, 'APL', :fy,
                 :max_num, 5, '/', true)
            """),
            {
                'doc_type': doc_type,
                'doc_name': doc_name,
                'fy': fy,
                'max_num': max_num
            }
        )
        print(f"  Initialized {doc_type} sequence: current_number={max_num}")

    conn.commit()
    print(f"Initialized document sequences for FY {fy}")


def downgrade() -> None:
    """Drop document_sequences table."""
    op.drop_index('ix_document_sequences_document_type', table_name='document_sequences')
    op.drop_table('document_sequences')
