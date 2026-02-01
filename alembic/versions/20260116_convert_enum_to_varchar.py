"""Convert ENUM columns to VARCHAR to match production schema.

This migration converts PostgreSQL ENUM types to VARCHAR as per production (Supabase).
Production is the source of truth - it uses VARCHAR for status fields.

Revision ID: convert_enum_to_varchar
Revises: 20260116_add_snop_tables
Create Date: 2026-01-16

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'convert_enum_to_varchar'
down_revision = 'add_snop_tables'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """
    Convert ENUM columns to VARCHAR.

    The approach:
    1. ALTER COLUMN to VARCHAR using USING clause to convert existing enum values
    2. Drop the ENUM type after all columns are converted
    """

    # List of (table, column, varchar_length) to convert from ENUM to VARCHAR
    enum_columns = [
        # accounting.py
        ('chart_of_accounts', 'account_type', 50),
        ('chart_of_accounts', 'account_sub_type', 50),
        ('financial_periods', 'status', 50),
        ('journal_entries', 'status', 50),
        ('bank_statement_lines', 'transaction_type', 50),

        # vendor.py
        ('vendors', 'vendor_type', 50),
        ('vendors', 'status', 50),
        ('vendors', 'grade', 10),
        ('vendors', 'payment_terms', 50),
        ('vendor_ledger', 'transaction_type', 50),

        # billing.py
        ('tax_invoices', 'invoice_type', 50),
        ('tax_invoices', 'status', 50),
        ('credit_debit_notes', 'document_type', 50),
        ('credit_debit_notes', 'reason', 50),
        ('credit_debit_notes', 'status', 50),
        ('eway_bills', 'status', 50),
        ('payment_receipts', 'payment_mode', 50),

        # order.py
        ('orders', 'status', 50),
        ('orders', 'source', 50),
        ('orders', 'payment_method', 50),
        ('orders', 'payment_status', 50),
        ('order_status_history', 'from_status', 50),
        ('order_status_history', 'to_status', 50),
        ('payments', 'method', 50),
        ('payments', 'status', 50),

        # role.py
        ('roles', 'level', 50),

        # technician.py
        ('technicians', 'technician_type', 50),
        ('technicians', 'status', 50),
        ('technicians', 'skill_level', 50),

        # commission.py
        ('commission_plans', 'commission_type', 50),
        ('commission_plans', 'calculation_basis', 50),
        ('commission_earners', 'earner_type', 50),
        ('commission_transactions', 'status', 50),
        ('commission_payouts', 'status', 50),

        # warehouse.py
        ('warehouses', 'warehouse_type', 50),

        # stock_transfer.py
        ('stock_transfers', 'transfer_type', 50),
        ('stock_transfers', 'status', 50),
    ]

    for table, column, length in enum_columns:
        try:
            # Convert ENUM to VARCHAR - the USING clause ensures data is preserved
            op.execute(f"""
                ALTER TABLE {table}
                ALTER COLUMN {column} TYPE VARCHAR({length})
                USING {column}::text
            """)
            print(f"  Converted {table}.{column} to VARCHAR({length})")
        except Exception as e:
            # Column might already be VARCHAR (if table was created after model update)
            print(f"  Skipping {table}.{column}: {e}")

    # List of JSON columns to convert to JSONB
    json_columns = [
        # vendor.py
        ('vendors', 'warehouse_address'),
        ('vendors', 'product_categories'),

        # billing.py
        ('invoice_items', 'serial_numbers'),
        ('eway_bills', 'api_response'),

        # order.py
        ('orders', 'shipping_address'),
        ('orders', 'billing_address'),
        ('payments', 'gateway_response'),

        # technician.py
        ('technicians', 'specializations'),
        ('technicians', 'certifications'),
        ('technicians', 'service_pincodes'),

        # commission.py
        ('commission_plans', 'rate_slabs'),
        ('commission_plans', 'applicable_products'),
        ('commission_plans', 'applicable_categories'),
        ('commission_plans', 'excluded_products'),
        ('commission_category_rates', 'rate_slabs'),
    ]

    for table, column in json_columns:
        try:
            op.execute(f"""
                ALTER TABLE {table}
                ALTER COLUMN {column} TYPE JSONB
                USING {column}::jsonb
            """)
            print(f"  Converted {table}.{column} to JSONB")
        except Exception as e:
            print(f"  Skipping {table}.{column}: {e}")

    # List of timestamp columns to convert to TIMESTAMPTZ
    # Note: This is a data-preserving operation - existing times are treated as UTC
    timestamp_tables = [
        'chart_of_accounts',
        'financial_periods',
        'cost_centers',
        'journal_entries',
        'journal_entry_lines',
        'general_ledger',
        'tax_configurations',
        'bank_statement_lines',
        'vendors',
        'vendor_ledger',
        'vendor_contacts',
        'tax_invoices',
        'invoice_items',
        'credit_debit_notes',
        'credit_debit_note_items',
        'eway_bills',
        'payment_receipts',
        'invoice_number_sequences',
        'orders',
        'order_items',
        'order_status_history',
        'payments',
        'invoices',
        'roles',
        'technicians',
        'technician_job_history',
        'technician_leaves',
        'commission_plans',
        'commission_category_rates',
        'commission_product_rates',
        'commission_earners',
        'commission_transactions',
        'commission_payouts',
        'commission_payout_lines',
        'affiliate_referrals',
        'warehouses',
        'stock_transfers',
    ]

    # Get all timestamp columns for each table and convert
    for table in timestamp_tables:
        try:
            # This query gets all timestamp columns for the table
            result = op.get_bind().execute(sa.text(f"""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name = '{table}'
                AND data_type = 'timestamp without time zone'
            """))
            columns = [row[0] for row in result]

            for column in columns:
                try:
                    op.execute(f"""
                        ALTER TABLE {table}
                        ALTER COLUMN {column} TYPE TIMESTAMP WITH TIME ZONE
                        USING {column} AT TIME ZONE 'UTC'
                    """)
                    print(f"  Converted {table}.{column} to TIMESTAMPTZ")
                except Exception as e:
                    print(f"  Skipping {table}.{column}: {e}")
        except Exception as e:
            print(f"  Skipping table {table}: {e}")

    # Drop old ENUM types (they're no longer needed)
    enum_types = [
        'accounttype',
        'accountsubtype',
        'financialperiodstatus',
        'journalentrystatus',
        'banktransactiontype',
        'bankreconciliationstatus',
        'vendortype',
        'vendorstatus',
        'vendorgrade',
        'paymentterms',
        'vendortransactiontype',
        'invoicetype',
        'invoicestatus',
        'documenttype',
        'notereason',
        'ewaybillstatus',
        'paymentmode',
        'orderstatus',
        'paymenstatus',
        'paymentmethod',
        'ordersource',
        'rolelevel',
        'technicianstatus',
        'techniciantype',
        'skilllevel',
        'commissiontype',
        'calculationbasis',
        'commissionstatus',
        'payoutstatus',
        'warehousetype',
        'transferstatus',
        'transfertype',
    ]

    for enum_type in enum_types:
        try:
            op.execute(f"DROP TYPE IF EXISTS {enum_type} CASCADE")
            print(f"  Dropped ENUM type: {enum_type}")
        except Exception as e:
            print(f"  Skipping ENUM type {enum_type}: {e}")


def downgrade() -> None:
    """
    Note: Downgrade is not recommended as production uses VARCHAR.
    This would require recreating ENUM types and converting data back.
    """
    # We don't implement downgrade as production is VARCHAR and is source of truth
    pass
