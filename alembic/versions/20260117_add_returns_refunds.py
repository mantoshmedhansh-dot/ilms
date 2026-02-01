"""Add return_orders, return_items, return_status_history, and refunds tables

Revision ID: 20260117_add_returns_refunds
Revises:
Create Date: 2026-01-17
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB


# revision identifiers, used by Alembic.
revision = '20260117_add_returns_refunds'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create return_orders table
    op.create_table(
        'return_orders',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('rma_number', sa.String(50), unique=True, nullable=False, index=True,
                  comment='Return Merchandise Authorization number'),
        sa.Column('order_id', UUID(as_uuid=True), sa.ForeignKey('orders.id'), nullable=False, index=True),
        sa.Column('customer_id', UUID(as_uuid=True), sa.ForeignKey('customers.id'), nullable=True, index=True),
        sa.Column('return_type', sa.String(50), nullable=False, default='RETURN',
                  comment='RETURN, EXCHANGE, REPLACEMENT'),
        sa.Column('return_reason', sa.String(100), nullable=False,
                  comment='DAMAGED, DEFECTIVE, WRONG_ITEM, NOT_AS_DESCRIBED, CHANGED_MIND, SIZE_FIT_ISSUE, QUALITY_ISSUE, OTHER'),
        sa.Column('return_reason_details', sa.Text, nullable=True),
        sa.Column('status', sa.String(50), nullable=False, default='INITIATED', index=True,
                  comment='INITIATED, AUTHORIZED, PICKUP_SCHEDULED, PICKED_UP, IN_TRANSIT, RECEIVED, UNDER_INSPECTION, APPROVED, REJECTED, REFUND_INITIATED, REFUND_PROCESSED, CLOSED, CANCELLED'),

        # Dates
        sa.Column('requested_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('authorized_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('pickup_scheduled_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('picked_up_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('received_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('inspected_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('closed_at', sa.DateTime(timezone=True), nullable=True),

        # Return Shipping
        sa.Column('return_shipment_id', UUID(as_uuid=True), sa.ForeignKey('shipments.id'), nullable=True),
        sa.Column('return_tracking_number', sa.String(100), nullable=True),
        sa.Column('return_courier', sa.String(100), nullable=True),
        sa.Column('pickup_address', JSONB, nullable=True),

        # Inspection
        sa.Column('inspection_notes', sa.Text, nullable=True),
        sa.Column('inspection_images', JSONB, nullable=True),
        sa.Column('inspected_by', UUID(as_uuid=True), nullable=True),
        sa.Column('rejection_reason', sa.Text, nullable=True),

        # Resolution
        sa.Column('resolution_type', sa.String(50), nullable=True,
                  comment='FULL_REFUND, PARTIAL_REFUND, STORE_CREDIT, REPLACEMENT, EXCHANGE'),
        sa.Column('resolution_notes', sa.Text, nullable=True),

        # Amounts
        sa.Column('total_return_amount', sa.Numeric(18, 2), nullable=False, default=0),
        sa.Column('restocking_fee', sa.Numeric(18, 2), nullable=False, default=0),
        sa.Column('shipping_deduction', sa.Numeric(18, 2), nullable=False, default=0),
        sa.Column('net_refund_amount', sa.Numeric(18, 2), nullable=False, default=0),

        # Store Credit
        sa.Column('store_credit_amount', sa.Numeric(18, 2), nullable=False, default=0),
        sa.Column('store_credit_code', sa.String(50), nullable=True),

        # Replacement
        sa.Column('replacement_order_id', UUID(as_uuid=True), nullable=True),

        # Communication
        sa.Column('customer_notified_at', sa.DateTime(timezone=True), nullable=True),

        # Timestamps
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    # Create return_items table
    op.create_table(
        'return_items',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('return_order_id', UUID(as_uuid=True), sa.ForeignKey('return_orders.id'), nullable=False, index=True),
        sa.Column('order_item_id', UUID(as_uuid=True), sa.ForeignKey('order_items.id'), nullable=False),
        sa.Column('product_id', UUID(as_uuid=True), nullable=False),
        sa.Column('product_name', sa.String(500), nullable=False),
        sa.Column('sku', sa.String(100), nullable=False),
        sa.Column('quantity_ordered', sa.Integer, nullable=False),
        sa.Column('quantity_returned', sa.Integer, nullable=False),
        sa.Column('condition', sa.String(50), nullable=False, default='UNOPENED',
                  comment='UNOPENED, OPENED_UNUSED, USED, DAMAGED, DEFECTIVE'),
        sa.Column('condition_notes', sa.Text, nullable=True),
        sa.Column('inspection_result', sa.String(50), nullable=True,
                  comment='ACCEPTED, REJECTED, PARTIAL'),
        sa.Column('inspection_notes', sa.Text, nullable=True),
        sa.Column('accepted_quantity', sa.Integer, nullable=True),
        sa.Column('unit_price', sa.Numeric(18, 2), nullable=False),
        sa.Column('total_amount', sa.Numeric(18, 2), nullable=False),
        sa.Column('refund_amount', sa.Numeric(18, 2), nullable=False, default=0),
        sa.Column('serial_number', sa.String(100), nullable=True),
        sa.Column('customer_images', JSONB, nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    # Create return_status_history table
    op.create_table(
        'return_status_history',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('return_order_id', UUID(as_uuid=True), sa.ForeignKey('return_orders.id'), nullable=False, index=True),
        sa.Column('from_status', sa.String(50), nullable=True),
        sa.Column('to_status', sa.String(50), nullable=False),
        sa.Column('notes', sa.Text, nullable=True),
        sa.Column('changed_by', UUID(as_uuid=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    # Create refunds table
    op.create_table(
        'refunds',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('refund_number', sa.String(50), unique=True, nullable=False, index=True),
        sa.Column('order_id', UUID(as_uuid=True), sa.ForeignKey('orders.id'), nullable=False, index=True),
        sa.Column('return_order_id', UUID(as_uuid=True), sa.ForeignKey('return_orders.id'), nullable=True, index=True),
        sa.Column('customer_id', UUID(as_uuid=True), sa.ForeignKey('customers.id'), nullable=True, index=True),
        sa.Column('refund_type', sa.String(50), nullable=False,
                  comment='FULL, PARTIAL, CANCELLATION, RETURN'),
        sa.Column('refund_method', sa.String(50), nullable=False,
                  comment='ORIGINAL_PAYMENT, BANK_TRANSFER, STORE_CREDIT, WALLET'),

        # Amounts
        sa.Column('order_amount', sa.Numeric(18, 2), nullable=False),
        sa.Column('refund_amount', sa.Numeric(18, 2), nullable=False),
        sa.Column('processing_fee', sa.Numeric(18, 2), nullable=False, default=0),
        sa.Column('net_refund', sa.Numeric(18, 2), nullable=False),
        sa.Column('tax_refund', sa.Numeric(18, 2), nullable=False, default=0),

        # Status
        sa.Column('status', sa.String(50), nullable=False, default='PENDING', index=True,
                  comment='PENDING, PROCESSING, COMPLETED, FAILED, CANCELLED'),

        # Payment Gateway
        sa.Column('original_payment_id', sa.String(100), nullable=True),
        sa.Column('refund_transaction_id', sa.String(100), nullable=True),
        sa.Column('gateway_response', JSONB, nullable=True),

        # Bank Details
        sa.Column('bank_account_number', sa.String(50), nullable=True),
        sa.Column('bank_ifsc', sa.String(20), nullable=True),
        sa.Column('bank_account_name', sa.String(200), nullable=True),

        # Reason
        sa.Column('reason', sa.String(200), nullable=False),
        sa.Column('notes', sa.Text, nullable=True),

        # Dates
        sa.Column('initiated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('processed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('failed_at', sa.DateTime(timezone=True), nullable=True),

        # Failure
        sa.Column('failure_reason', sa.Text, nullable=True),
        sa.Column('retry_count', sa.Integer, nullable=False, default=0),

        # Accounting
        sa.Column('accounting_entry_id', UUID(as_uuid=True), nullable=True),

        # Users
        sa.Column('initiated_by', UUID(as_uuid=True), nullable=True),
        sa.Column('approved_by', UUID(as_uuid=True), nullable=True),

        # Timestamps
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table('refunds')
    op.drop_table('return_status_history')
    op.drop_table('return_items')
    op.drop_table('return_orders')
