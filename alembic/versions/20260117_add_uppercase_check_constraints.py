"""Add CHECK constraints to enforce UPPERCASE enum-like values.

This migration adds CHECK constraints to all enum-like VARCHAR columns
to enforce that values are stored in UPPERCASE. This prevents case
sensitivity issues between database, backend, and frontend.

The constraints ensure:
- All status, type, and enum-like fields are stored as UPPERCASE
- Case-insensitive input is normalized at application layer
- Database provides final validation

Revision ID: add_uppercase_check_constraints
Revises: fix_purchase_enum_to_varchar
Create Date: 2026-01-17
"""
from alembic import op
import sqlalchemy as sa


revision = 'add_uppercase_check_constraints'
down_revision = 'fix_purchase_enum_to_varchar'
branch_labels = None
depends_on = None


# Define all columns that need UPPERCASE CHECK constraints
# Format: (table_name, column_name)
UPPERCASE_COLUMNS = [
    # Roles
    ('roles', 'level'),

    # Orders
    ('orders', 'status'),
    ('orders', 'payment_status'),
    ('orders', 'payment_method'),
    ('orders', 'source'),

    # Companies
    ('companies', 'company_type'),
    ('companies', 'gst_registration_type'),

    # Dealers
    ('dealers', 'type'),
    ('dealers', 'status'),
    ('dealers', 'tier'),
    ('dealers', 'credit_status'),

    # Vendors
    ('vendors', 'vendor_type'),
    ('vendors', 'status'),

    # Shipments
    ('shipments', 'status'),
    ('shipments', 'packaging_type'),
    ('shipments', 'payment_mode'),

    # Purchase Orders
    ('purchase_orders', 'status'),

    # Service Requests
    ('service_requests', 'status'),

    # Installations
    ('installations', 'status'),

    # Leads
    ('leads', 'status'),

    # Picklists
    ('picklists', 'status'),
    ('picklists', 'picklist_type'),

    # GRN (Goods Receipt Notes)
    ('goods_receipt_notes', 'status'),

    # Invoices
    ('invoices', 'status'),
    ('invoices', 'invoice_type'),

    # Payments
    ('payments', 'status'),
    ('payments', 'payment_method'),

    # Returns
    ('returns', 'status'),
    ('returns', 'return_type'),

    # Inventory
    ('inventory_transactions', 'transaction_type'),

    # Users
    ('users', 'status'),

    # Employees
    ('employees', 'employment_status'),
    ('employees', 'employment_type'),

    # Leave Requests
    ('leave_requests', 'status'),
    ('leave_requests', 'leave_type'),

    # Approvals
    ('approval_workflows', 'status'),
    ('approval_requests', 'status'),
]


def constraint_name(table_name: str, column_name: str) -> str:
    """Generate consistent CHECK constraint name."""
    return f"chk_{table_name}_{column_name}_uppercase"


def table_exists(conn, table_name: str) -> bool:
    """Check if a table exists."""
    result = conn.execute(sa.text("""
        SELECT EXISTS (
            SELECT 1 FROM information_schema.tables
            WHERE table_name = :table_name
            AND table_schema = 'public'
        )
    """), {"table_name": table_name})
    return result.scalar()


def column_exists(conn, table_name: str, column_name: str) -> bool:
    """Check if a column exists in a table."""
    result = conn.execute(sa.text("""
        SELECT EXISTS (
            SELECT 1 FROM information_schema.columns
            WHERE table_name = :table_name
            AND column_name = :column_name
            AND table_schema = 'public'
        )
    """), {"table_name": table_name, "column_name": column_name})
    return result.scalar()


def constraint_exists(conn, constraint_name: str) -> bool:
    """Check if a constraint already exists."""
    result = conn.execute(sa.text("""
        SELECT EXISTS (
            SELECT 1 FROM information_schema.table_constraints
            WHERE constraint_name = :constraint_name
            AND table_schema = 'public'
        )
    """), {"constraint_name": constraint_name})
    return result.scalar()


def add_uppercase_constraint(conn, table_name: str, column_name: str):
    """Add CHECK constraint to enforce UPPERCASE values."""
    cname = constraint_name(table_name, column_name)

    # Skip if table doesn't exist
    if not table_exists(conn, table_name):
        print(f"  Skipping {table_name}.{column_name} - table does not exist")
        return

    # Skip if column doesn't exist
    if not column_exists(conn, table_name, column_name):
        print(f"  Skipping {table_name}.{column_name} - column does not exist")
        return

    # Skip if constraint already exists
    if constraint_exists(conn, cname):
        print(f"  Skipping {table_name}.{column_name} - constraint already exists")
        return

    # First, update any existing non-UPPERCASE values to UPPERCASE
    update_sql = sa.text(f"""
        UPDATE {table_name}
        SET {column_name} = UPPER({column_name})
        WHERE {column_name} IS NOT NULL
        AND {column_name} != UPPER({column_name})
    """)
    result = conn.execute(update_sql)
    if result.rowcount > 0:
        print(f"  Updated {result.rowcount} rows in {table_name}.{column_name} to UPPERCASE")

    # Add the CHECK constraint
    add_constraint_sql = sa.text(f"""
        ALTER TABLE {table_name}
        ADD CONSTRAINT {cname}
        CHECK ({column_name} IS NULL OR {column_name} = UPPER({column_name}))
    """)
    conn.execute(add_constraint_sql)
    print(f"  Added CHECK constraint {cname}")


def drop_uppercase_constraint(conn, table_name: str, column_name: str):
    """Drop the UPPERCASE CHECK constraint."""
    cname = constraint_name(table_name, column_name)

    # Skip if constraint doesn't exist
    if not constraint_exists(conn, cname):
        print(f"  Skipping {cname} - constraint does not exist")
        return

    drop_sql = sa.text(f"""
        ALTER TABLE {table_name}
        DROP CONSTRAINT IF EXISTS {cname}
    """)
    conn.execute(drop_sql)
    print(f"  Dropped CHECK constraint {cname}")


def upgrade():
    """Add UPPERCASE CHECK constraints to all enum-like columns."""
    print("Adding UPPERCASE CHECK constraints...")

    conn = op.get_bind()

    for table_name, column_name in UPPERCASE_COLUMNS:
        add_uppercase_constraint(conn, table_name, column_name)

    print("Done adding CHECK constraints")


def downgrade():
    """Remove all UPPERCASE CHECK constraints."""
    print("Removing UPPERCASE CHECK constraints...")

    conn = op.get_bind()

    for table_name, column_name in UPPERCASE_COLUMNS:
        drop_uppercase_constraint(conn, table_name, column_name)

    print("Done removing CHECK constraints")
