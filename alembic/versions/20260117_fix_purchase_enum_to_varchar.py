"""Fix purchase_orders ENUM to VARCHAR - Production Fix.

This migration converts remaining ENUM columns to VARCHAR in production.
The purchase_orders.status column is still using PostgreSQL ENUM type
'postatus' in production, causing PO approval to fail.

Revision ID: fix_purchase_enum_to_varchar
Revises: convert_enum_to_varchar_phase2
Create Date: 2026-01-17
"""
from alembic import op
import sqlalchemy as sa


revision = 'fix_purchase_enum_to_varchar'
down_revision = 'convert_enum_to_varchar_phase2'
branch_labels = None
depends_on = None


def get_column_type(conn, table_name, column_name):
    """Get the udt_name (underlying type) of a column."""
    result = conn.execute(sa.text(f"""
        SELECT udt_name, data_type
        FROM information_schema.columns
        WHERE table_name = :table_name
        AND column_name = :column_name
    """), {"table_name": table_name, "column_name": column_name})
    row = result.fetchone()
    return (row[0], row[1]) if row else (None, None)


def table_exists(conn, table_name):
    """Check if a table exists."""
    result = conn.execute(sa.text("""
        SELECT EXISTS (
            SELECT 1 FROM information_schema.tables
            WHERE table_name = :table_name
        )
    """), {"table_name": table_name})
    return result.scalar()


def convert_column_if_enum(conn, table_name, column_name, varchar_length=50):
    """Convert a column from ENUM to VARCHAR if it's currently an ENUM."""
    if not table_exists(conn, table_name):
        print(f"  Table {table_name} does not exist, skipping")
        return

    udt_name, data_type = get_column_type(conn, table_name, column_name)

    if udt_name is None:
        print(f"  Column {table_name}.{column_name} does not exist, skipping")
        return

    # Check if it's already VARCHAR
    if 'character' in str(data_type) or 'varchar' in str(udt_name).lower():
        print(f"  {table_name}.{column_name} is already VARCHAR, skipping")
        return

    # It's an ENUM - convert it
    try:
        conn.execute(sa.text(f"""
            ALTER TABLE {table_name}
            ALTER COLUMN {column_name} TYPE VARCHAR({varchar_length})
            USING {column_name}::text
        """))
        conn.commit()
        print(f"  Converted {table_name}.{column_name} from {udt_name} to VARCHAR({varchar_length})")
    except Exception as e:
        print(f"  Error converting {table_name}.{column_name}: {e}")
        conn.rollback()


def upgrade() -> None:
    """Convert remaining ENUM columns to VARCHAR."""
    conn = op.get_bind()

    print("\n" + "="*60)
    print("FIXING ENUM TO VARCHAR - PRODUCTION")
    print("="*60 + "\n")

    # Critical: purchase_orders columns
    print("Converting purchase_orders columns...")
    convert_column_if_enum(conn, 'purchase_orders', 'status', 50)
    convert_column_if_enum(conn, 'purchase_orders', 'po_type', 50)

    # Critical: po_delivery_schedules
    print("\nConverting po_delivery_schedules columns...")
    convert_column_if_enum(conn, 'po_delivery_schedules', 'status', 50)

    # purchase_order_items
    print("\nConverting purchase_order_items columns...")
    convert_column_if_enum(conn, 'purchase_order_items', 'item_status', 50)

    # goods_receipt_notes
    print("\nConverting goods_receipt_notes columns...")
    convert_column_if_enum(conn, 'goods_receipt_notes', 'status', 50)

    # purchase_requisitions
    print("\nConverting purchase_requisitions columns...")
    convert_column_if_enum(conn, 'purchase_requisitions', 'status', 50)

    # vendor tables
    print("\nConverting vendor columns...")
    convert_column_if_enum(conn, 'vendors', 'vendor_type', 50)
    convert_column_if_enum(conn, 'vendors', 'status', 50)
    convert_column_if_enum(conn, 'vendors', 'grade', 10)
    convert_column_if_enum(conn, 'vendors', 'payment_terms', 50)
    convert_column_if_enum(conn, 'vendor_ledger', 'transaction_type', 50)

    # vendor_invoices
    print("\nConverting vendor_invoices columns...")
    convert_column_if_enum(conn, 'vendor_invoices', 'status', 50)

    # vendor_proforma_invoices
    print("\nConverting vendor_proforma_invoices columns...")
    convert_column_if_enum(conn, 'vendor_proforma_invoices', 'status', 50)

    # sales_return_notes
    print("\nConverting sales_return_notes columns...")
    convert_column_if_enum(conn, 'sales_return_notes', 'status', 50)
    convert_column_if_enum(conn, 'sales_return_notes', 'return_reason', 50)
    convert_column_if_enum(conn, 'sales_return_notes', 'resolution_type', 50)
    convert_column_if_enum(conn, 'sales_return_notes', 'pickup_status', 50)

    # srn_items
    print("\nConverting srn_items columns...")
    convert_column_if_enum(conn, 'srn_items', 'item_condition', 50)
    convert_column_if_enum(conn, 'srn_items', 'qc_result', 50)
    convert_column_if_enum(conn, 'srn_items', 'restock_decision', 50)

    # orders
    print("\nConverting orders columns...")
    convert_column_if_enum(conn, 'orders', 'status', 50)
    convert_column_if_enum(conn, 'orders', 'source', 50)
    convert_column_if_enum(conn, 'orders', 'payment_method', 50)
    convert_column_if_enum(conn, 'orders', 'payment_status', 50)

    # billing tables
    print("\nConverting billing columns...")
    convert_column_if_enum(conn, 'tax_invoices', 'invoice_type', 50)
    convert_column_if_enum(conn, 'tax_invoices', 'status', 50)
    convert_column_if_enum(conn, 'credit_debit_notes', 'document_type', 50)
    convert_column_if_enum(conn, 'credit_debit_notes', 'reason', 50)
    convert_column_if_enum(conn, 'credit_debit_notes', 'status', 50)
    convert_column_if_enum(conn, 'eway_bills', 'status', 50)
    convert_column_if_enum(conn, 'payment_receipts', 'payment_mode', 50)

    # accounting tables
    print("\nConverting accounting columns...")
    convert_column_if_enum(conn, 'chart_of_accounts', 'account_type', 50)
    convert_column_if_enum(conn, 'chart_of_accounts', 'account_sub_type', 50)
    convert_column_if_enum(conn, 'financial_periods', 'status', 50)
    convert_column_if_enum(conn, 'journal_entries', 'status', 50)

    # shipments
    print("\nConverting shipment columns...")
    convert_column_if_enum(conn, 'shipments', 'status', 50)
    convert_column_if_enum(conn, 'shipments', 'carrier_type', 50)

    # inventory
    print("\nConverting inventory columns...")
    convert_column_if_enum(conn, 'stock_items', 'status', 50)
    convert_column_if_enum(conn, 'stock_items', 'condition', 50)
    convert_column_if_enum(conn, 'stock_movements', 'movement_type', 50)
    convert_column_if_enum(conn, 'stock_movements', 'reason', 50)

    # service
    print("\nConverting service columns...")
    convert_column_if_enum(conn, 'service_requests', 'request_type', 50)
    convert_column_if_enum(conn, 'service_requests', 'status', 50)
    convert_column_if_enum(conn, 'service_requests', 'priority', 50)
    convert_column_if_enum(conn, 'service_requests', 'source', 50)

    # technicians
    print("\nConverting technician columns...")
    convert_column_if_enum(conn, 'technicians', 'technician_type', 50)
    convert_column_if_enum(conn, 'technicians', 'status', 50)
    convert_column_if_enum(conn, 'technicians', 'skill_level', 50)

    # installations
    print("\nConverting installation columns...")
    convert_column_if_enum(conn, 'installations', 'status', 50)
    convert_column_if_enum(conn, 'installations', 'installation_type', 50)

    # warranty
    print("\nConverting warranty columns...")
    convert_column_if_enum(conn, 'warranty_claims', 'status', 50)
    convert_column_if_enum(conn, 'warranty_claims', 'claim_type', 50)

    # amc
    print("\nConverting AMC columns...")
    convert_column_if_enum(conn, 'amc_contracts', 'contract_type', 50)
    convert_column_if_enum(conn, 'amc_contracts', 'status', 50)

    # products
    print("\nConverting product columns...")
    convert_column_if_enum(conn, 'products', 'product_type', 50)
    convert_column_if_enum(conn, 'products', 'status', 50)
    convert_column_if_enum(conn, 'products', 'warranty_type', 50)

    # customers
    print("\nConverting customer columns...")
    convert_column_if_enum(conn, 'customers', 'customer_type', 50)
    convert_column_if_enum(conn, 'customers', 'status', 50)

    # leads
    print("\nConverting lead columns...")
    convert_column_if_enum(conn, 'leads', 'status', 50)
    convert_column_if_enum(conn, 'leads', 'source', 50)
    convert_column_if_enum(conn, 'leads', 'priority', 50)

    # HR
    print("\nConverting HR columns...")
    convert_column_if_enum(conn, 'employees', 'employment_type', 50)
    convert_column_if_enum(conn, 'employees', 'status', 50)
    convert_column_if_enum(conn, 'employees', 'gender', 20)
    convert_column_if_enum(conn, 'leave_requests', 'leave_type', 50)
    convert_column_if_enum(conn, 'leave_requests', 'status', 50)

    # Approval
    print("\nConverting approval columns...")
    convert_column_if_enum(conn, 'approval_requests', 'status', 50)

    # Serialization
    print("\nConverting serialization columns...")
    convert_column_if_enum(conn, 'po_serials', 'status', 50)
    convert_column_if_enum(conn, 'po_serials', 'item_type', 10)

    # Drop old ENUM types
    print("\nDropping old ENUM types...")
    enum_types = [
        'postatus', 'potype', 'poitemstatus', 'grnstatus', 'requisitionstatus',
        'deliverylotstatus', 'vendortype', 'vendorstatus', 'vendorgrade',
        'vendorinvoicestatus', 'proformastatus',
        'srnstatus', 'returnreason', 'resolutiontype', 'pickupstatus',
        'itemcondition', 'qcresult', 'restockdecision',
        'orderstatus', 'ordersource', 'paymentmethod', 'paymentstatus',
        'invoicetype', 'invoicestatus', 'documenttype', 'notereason',
        'ewaybillstatus', 'paymentmode',
        'accounttype', 'accountsubtype', 'periodstatus', 'entrystatus',
        'shipmentstatus', 'carriertype',
        'stockstatus', 'stockcondition', 'movementtype', 'movementreason',
        'servicerequesttype', 'servicerequeststatus', 'servicerequestpriority',
        'techniciantype', 'technicianstatus', 'skilllevel',
        'installationstatus', 'installationtype',
        'warrantyclaimstatus', 'warrantyclaimtype',
        'contracttype', 'contractstatus',
        'producttype', 'productstatus', 'warrantytype',
        'customertype', 'customerstatus',
        'leadstatus', 'leadsource', 'leadpriority',
        'employmenttype', 'employeestatus', 'gender', 'leavetype', 'leavestatus',
        'requeststatus', 'serialstatus', 'itemtype',
    ]

    for enum_type in enum_types:
        try:
            conn.execute(sa.text(f"DROP TYPE IF EXISTS {enum_type} CASCADE"))
            conn.commit()
        except Exception:
            conn.rollback()

    print("\n" + "="*60)
    print("ENUM TO VARCHAR CONVERSION COMPLETE")
    print("="*60 + "\n")


def downgrade() -> None:
    """No downgrade - production uses VARCHAR."""
    pass
