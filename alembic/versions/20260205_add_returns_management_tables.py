"""Add Returns Management tables - Phase 9: Reverse Logistics & Return Processing

Revision ID: 20260205_returns
Revises: 20260205_kitting
Create Date: 2026-02-05

Tables created:
- return_authorizations: RMA/Return authorization
- return_authorization_items: RMA line items
- return_receipts: Return receipt records
- return_receipt_items: Receipt line items
- return_inspections: Inspection and grading
- refurbishment_orders: Refurbishment/repair tracking
- disposition_records: Final disposition decisions
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '20260205_returns'
down_revision = '20260205_kitting'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # =========================================================================
    # RETURN_AUTHORIZATIONS - RMA
    # =========================================================================
    op.create_table(
        'return_authorizations',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False, index=True),

        # RMA Identity
        sa.Column('rma_number', sa.String(30), nullable=False, unique=True, index=True),
        sa.Column('return_type', sa.String(30), nullable=False, index=True),
        sa.Column('status', sa.String(30), default='PENDING', nullable=False, index=True),

        # Source Reference
        sa.Column('order_id', postgresql.UUID(as_uuid=True), nullable=True, index=True),
        sa.Column('order_number', sa.String(50), nullable=True),
        sa.Column('invoice_number', sa.String(50), nullable=True),

        # Customer/Dealer
        sa.Column('customer_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('customers.id', ondelete='SET NULL'), nullable=True, index=True),
        sa.Column('customer_name', sa.String(200), nullable=True),
        sa.Column('customer_email', sa.String(200), nullable=True),
        sa.Column('customer_phone', sa.String(20), nullable=True),

        # Destination Warehouse
        sa.Column('warehouse_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('warehouses.id', ondelete='CASCADE'), nullable=False, index=True),

        # Return Details
        sa.Column('return_reason', sa.String(50), nullable=False),
        sa.Column('reason_detail', sa.Text, nullable=True),

        # Quantities
        sa.Column('total_items', sa.Integer, default=0),
        sa.Column('approved_items', sa.Integer, default=0),
        sa.Column('received_items', sa.Integer, default=0),

        # Values
        sa.Column('original_order_value', sa.Numeric(12, 2), default=0),
        sa.Column('return_value', sa.Numeric(12, 2), default=0),

        # Refund
        sa.Column('refund_type', sa.String(30), nullable=True),
        sa.Column('refund_amount', sa.Numeric(12, 2), default=0),
        sa.Column('refund_status', sa.String(30), nullable=True),

        # Shipping
        sa.Column('return_shipping_method', sa.String(50), nullable=True),
        sa.Column('return_tracking_number', sa.String(100), nullable=True),
        sa.Column('shipping_paid_by', sa.String(30), nullable=True),
        sa.Column('shipping_cost', sa.Numeric(10, 2), default=0),

        # Pickup
        sa.Column('pickup_required', sa.Boolean, default=False),
        sa.Column('pickup_address', postgresql.JSONB, nullable=True),
        sa.Column('pickup_scheduled_date', sa.Date, nullable=True),
        sa.Column('pickup_completed_date', sa.Date, nullable=True),

        # Dates
        sa.Column('request_date', sa.Date, nullable=False, index=True),
        sa.Column('approval_date', sa.Date, nullable=True),
        sa.Column('expiry_date', sa.Date, nullable=True),

        # Approval
        sa.Column('approved_by', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('rejection_reason', sa.String(500), nullable=True),

        # Photos/Evidence
        sa.Column('photos', postgresql.JSONB, nullable=True),
        sa.Column('documents', postgresql.JSONB, nullable=True),

        sa.Column('notes', sa.Text, nullable=True),
        sa.Column('internal_notes', sa.Text, nullable=True),

        # Audit
        sa.Column('created_by', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),

        # Timestamps
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_index('ix_return_authorizations_status', 'return_authorizations', ['status'])
    op.create_index('ix_return_authorizations_type', 'return_authorizations', ['return_type'])

    # =========================================================================
    # RETURN_AUTHORIZATION_ITEMS - RMA Line Items
    # =========================================================================
    op.create_table(
        'return_authorization_items',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False, index=True),

        # RMA Reference
        sa.Column('rma_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('return_authorizations.id', ondelete='CASCADE'), nullable=False, index=True),

        # Product
        sa.Column('product_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('products.id', ondelete='RESTRICT'), nullable=False, index=True),
        sa.Column('sku', sa.String(100), nullable=False),
        sa.Column('product_name', sa.String(255), nullable=False),

        # Quantities
        sa.Column('ordered_quantity', sa.Integer, nullable=False),
        sa.Column('requested_quantity', sa.Integer, nullable=False),
        sa.Column('approved_quantity', sa.Integer, default=0),
        sa.Column('received_quantity', sa.Integer, default=0),

        # Values
        sa.Column('unit_price', sa.Numeric(12, 2), nullable=False),
        sa.Column('total_value', sa.Numeric(12, 2), nullable=False),
        sa.Column('refund_amount', sa.Numeric(12, 2), default=0),

        # Return Details
        sa.Column('return_reason', sa.String(50), nullable=False),
        sa.Column('reason_detail', sa.Text, nullable=True),

        # Item Identity
        sa.Column('serial_numbers', postgresql.JSONB, nullable=True),
        sa.Column('lot_number', sa.String(50), nullable=True),

        # Status
        sa.Column('status', sa.String(30), default='PENDING', nullable=False),

        # Evidence
        sa.Column('photos', postgresql.JSONB, nullable=True),

        sa.Column('notes', sa.Text, nullable=True),

        # Timestamps
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # =========================================================================
    # RETURN_RECEIPTS - Return Receipt Records
    # =========================================================================
    op.create_table(
        'return_receipts',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False, index=True),

        # Receipt Identity
        sa.Column('receipt_number', sa.String(30), nullable=False, unique=True, index=True),
        sa.Column('status', sa.String(30), default='PENDING', nullable=False, index=True),

        # RMA Reference
        sa.Column('rma_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('return_authorizations.id', ondelete='CASCADE'), nullable=False, index=True),

        # Warehouse
        sa.Column('warehouse_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('warehouses.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('receiving_zone_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('warehouse_zones.id', ondelete='SET NULL'), nullable=True),
        sa.Column('receiving_bin_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('warehouse_bins.id', ondelete='SET NULL'), nullable=True),

        # Shipping
        sa.Column('carrier', sa.String(100), nullable=True),
        sa.Column('tracking_number', sa.String(100), nullable=True),

        # Dates
        sa.Column('expected_date', sa.Date, nullable=True),
        sa.Column('receipt_date', sa.Date, nullable=False, index=True),

        # Quantities
        sa.Column('expected_quantity', sa.Integer, nullable=False),
        sa.Column('received_quantity', sa.Integer, default=0),
        sa.Column('damaged_quantity', sa.Integer, default=0),
        sa.Column('missing_quantity', sa.Integer, default=0),

        # Package Condition
        sa.Column('package_condition', sa.String(30), nullable=True),
        sa.Column('condition_notes', sa.Text, nullable=True),
        sa.Column('package_photos', postgresql.JSONB, nullable=True),

        # Receiver
        sa.Column('received_by', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),

        sa.Column('notes', sa.Text, nullable=True),

        # Timestamps
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_index('ix_return_receipts_status', 'return_receipts', ['status'])

    # =========================================================================
    # RETURN_RECEIPT_ITEMS - Receipt Line Items
    # =========================================================================
    op.create_table(
        'return_receipt_items',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False, index=True),

        # Receipt Reference
        sa.Column('receipt_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('return_receipts.id', ondelete='CASCADE'), nullable=False, index=True),

        # RMA Item Reference
        sa.Column('rma_item_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('return_authorization_items.id', ondelete='CASCADE'), nullable=False),

        # Product
        sa.Column('product_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('products.id', ondelete='RESTRICT'), nullable=False, index=True),
        sa.Column('sku', sa.String(100), nullable=False),

        # Quantities
        sa.Column('expected_quantity', sa.Integer, nullable=False),
        sa.Column('received_quantity', sa.Integer, default=0),
        sa.Column('damaged_quantity', sa.Integer, default=0),

        # Item Identity
        sa.Column('serial_numbers', postgresql.JSONB, nullable=True),
        sa.Column('lot_number', sa.String(50), nullable=True),

        # Condition
        sa.Column('initial_condition', sa.String(30), nullable=True),
        sa.Column('condition_notes', sa.Text, nullable=True),

        # Location
        sa.Column('put_away_bin_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('warehouse_bins.id', ondelete='SET NULL'), nullable=True),

        # Inspection Status
        sa.Column('needs_inspection', sa.Boolean, default=True),
        sa.Column('inspection_id', postgresql.UUID(as_uuid=True), nullable=True),

        sa.Column('notes', sa.Text, nullable=True),

        # Timestamps
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # =========================================================================
    # RETURN_INSPECTIONS - Inspection and Grading
    # =========================================================================
    op.create_table(
        'return_inspections',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False, index=True),

        # Inspection Identity
        sa.Column('inspection_number', sa.String(30), nullable=False, unique=True, index=True),
        sa.Column('status', sa.String(30), default='PENDING', nullable=False, index=True),

        # References
        sa.Column('receipt_item_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('return_receipt_items.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('rma_id', postgresql.UUID(as_uuid=True), nullable=False),

        # Warehouse
        sa.Column('warehouse_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('warehouses.id', ondelete='CASCADE'), nullable=False, index=True),

        # Product
        sa.Column('product_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('products.id', ondelete='RESTRICT'), nullable=False, index=True),
        sa.Column('sku', sa.String(100), nullable=False),
        sa.Column('product_name', sa.String(255), nullable=False),

        # Item Identity
        sa.Column('serial_number', sa.String(100), nullable=True),
        sa.Column('lot_number', sa.String(50), nullable=True),

        # Inspection
        sa.Column('inspection_date', sa.Date, nullable=False, index=True),
        sa.Column('inspector_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),

        # Grade
        sa.Column('grade', sa.String(20), nullable=True, index=True),

        # Checklist Results
        sa.Column('checklist_results', postgresql.JSONB, nullable=True),

        # Defects Found
        sa.Column('defects_found', postgresql.JSONB, nullable=True),
        sa.Column('defect_count', sa.Integer, default=0),

        # Customer Claim Verification
        sa.Column('claim_verified', sa.Boolean, nullable=True),
        sa.Column('claim_notes', sa.Text, nullable=True),

        # Functional Testing
        sa.Column('functional_test_passed', sa.Boolean, nullable=True),
        sa.Column('test_results', postgresql.JSONB, nullable=True),

        # Cosmetic Assessment
        sa.Column('cosmetic_condition', sa.String(30), nullable=True),
        sa.Column('cosmetic_notes', sa.Text, nullable=True),

        # Packaging
        sa.Column('original_packaging', sa.Boolean, default=False),
        sa.Column('packaging_condition', sa.String(30), nullable=True),
        sa.Column('accessories_complete', sa.Boolean, default=True),
        sa.Column('missing_accessories', postgresql.JSONB, nullable=True),

        # Photos/Evidence
        sa.Column('photos', postgresql.JSONB, nullable=True),

        # Disposition Recommendation
        sa.Column('recommended_disposition', sa.String(30), nullable=True),
        sa.Column('disposition_notes', sa.Text, nullable=True),

        # Actual Disposition
        sa.Column('final_disposition', sa.String(30), nullable=True),
        sa.Column('disposition_by', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('disposition_at', sa.DateTime(timezone=True), nullable=True),

        # Refund Impact
        sa.Column('refund_eligible', sa.Boolean, default=True),
        sa.Column('refund_deduction', sa.Numeric(10, 2), default=0),
        sa.Column('refund_notes', sa.Text, nullable=True),

        sa.Column('notes', sa.Text, nullable=True),

        # Timestamps
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_index('ix_return_inspections_status', 'return_inspections', ['status'])
    op.create_index('ix_return_inspections_grade', 'return_inspections', ['grade'])

    # =========================================================================
    # REFURBISHMENT_ORDERS - Refurbishment/Repair Tracking
    # =========================================================================
    op.create_table(
        'refurbishment_orders',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False, index=True),

        # Order Identity
        sa.Column('order_number', sa.String(30), nullable=False, unique=True, index=True),
        sa.Column('status', sa.String(30), default='PENDING', nullable=False, index=True),

        # Reference
        sa.Column('inspection_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('return_inspections.id', ondelete='CASCADE'), nullable=False, index=True),

        # Warehouse
        sa.Column('warehouse_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('warehouses.id', ondelete='CASCADE'), nullable=False, index=True),

        # Product
        sa.Column('product_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('products.id', ondelete='RESTRICT'), nullable=False, index=True),
        sa.Column('sku', sa.String(100), nullable=False),
        sa.Column('serial_number', sa.String(100), nullable=True),

        # Refurbishment Type
        sa.Column('refurbishment_type', sa.String(30), nullable=False),

        # Work Required
        sa.Column('work_description', sa.Text, nullable=False),
        sa.Column('work_items', postgresql.JSONB, nullable=True),

        # Parts Required
        sa.Column('parts_required', postgresql.JSONB, nullable=True),
        sa.Column('parts_cost', sa.Numeric(10, 2), default=0),

        # Labor
        sa.Column('estimated_labor_hours', sa.Numeric(6, 2), nullable=True),
        sa.Column('actual_labor_hours', sa.Numeric(6, 2), nullable=True),
        sa.Column('labor_cost', sa.Numeric(10, 2), default=0),

        # Total Cost
        sa.Column('total_cost', sa.Numeric(10, 2), default=0),

        # Assignment
        sa.Column('assigned_to', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('assigned_at', sa.DateTime(timezone=True), nullable=True),

        # Vendor (if external)
        sa.Column('vendor_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('vendors.id', ondelete='SET NULL'), nullable=True),

        # Dates
        sa.Column('created_date', sa.Date, nullable=False),
        sa.Column('due_date', sa.Date, nullable=True),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),

        # Result
        sa.Column('result_grade', sa.String(20), nullable=True),
        sa.Column('result_notes', sa.Text, nullable=True),

        # Destination
        sa.Column('destination_bin_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('warehouse_bins.id', ondelete='SET NULL'), nullable=True),

        # QC
        sa.Column('qc_required', sa.Boolean, default=True),
        sa.Column('qc_passed', sa.Boolean, nullable=True),
        sa.Column('qc_by', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('qc_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('qc_notes', sa.Text, nullable=True),

        # Photos
        sa.Column('before_photos', postgresql.JSONB, nullable=True),
        sa.Column('after_photos', postgresql.JSONB, nullable=True),

        sa.Column('notes', sa.Text, nullable=True),

        # Audit
        sa.Column('created_by', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),

        # Timestamps
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_index('ix_refurbishment_orders_status', 'refurbishment_orders', ['status'])

    # =========================================================================
    # DISPOSITION_RECORDS - Final Disposition Decisions
    # =========================================================================
    op.create_table(
        'disposition_records',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False, index=True),

        # Record Identity
        sa.Column('disposition_number', sa.String(30), nullable=False, unique=True, index=True),

        # Reference
        sa.Column('inspection_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('return_inspections.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('refurbishment_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('refurbishment_orders.id', ondelete='SET NULL'), nullable=True),

        # Warehouse
        sa.Column('warehouse_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('warehouses.id', ondelete='CASCADE'), nullable=False, index=True),

        # Product
        sa.Column('product_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('products.id', ondelete='RESTRICT'), nullable=False, index=True),
        sa.Column('sku', sa.String(100), nullable=False),
        sa.Column('serial_number', sa.String(100), nullable=True),
        sa.Column('lot_number', sa.String(50), nullable=True),

        # Quantity
        sa.Column('quantity', sa.Integer, default=1, nullable=False),

        # Disposition
        sa.Column('disposition_action', sa.String(30), nullable=False, index=True),
        sa.Column('disposition_date', sa.Date, nullable=False, index=True),

        # Grade at Disposition
        sa.Column('grade', sa.String(20), nullable=True),

        # Value
        sa.Column('original_value', sa.Numeric(12, 2), default=0),
        sa.Column('recovered_value', sa.Numeric(12, 2), default=0),
        sa.Column('loss_value', sa.Numeric(12, 2), default=0),

        # Destination Details
        sa.Column('destination_bin_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('warehouse_bins.id', ondelete='SET NULL'), nullable=True),

        # For RETURN_TO_VENDOR
        sa.Column('vendor_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('vendors.id', ondelete='SET NULL'), nullable=True),
        sa.Column('vendor_rma_number', sa.String(50), nullable=True),
        sa.Column('vendor_credit_amount', sa.Numeric(10, 2), default=0),

        # For DONATE
        sa.Column('donation_recipient', sa.String(200), nullable=True),
        sa.Column('donation_reference', sa.String(50), nullable=True),

        # For SCRAP/DESTROY
        sa.Column('destruction_method', sa.String(100), nullable=True),
        sa.Column('destruction_certificate', sa.String(200), nullable=True),
        sa.Column('environmental_compliance', sa.Boolean, default=True),

        # Approval
        sa.Column('requires_approval', sa.Boolean, default=False),
        sa.Column('approved_by', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('approved_at', sa.DateTime(timezone=True), nullable=True),

        # Execution
        sa.Column('executed_by', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('executed_at', sa.DateTime(timezone=True), nullable=True),

        # Photos/Evidence
        sa.Column('photos', postgresql.JSONB, nullable=True),

        sa.Column('reason', sa.String(200), nullable=False),
        sa.Column('notes', sa.Text, nullable=True),

        # Audit
        sa.Column('created_by', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),

        # Timestamps
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_index('ix_disposition_records_action', 'disposition_records', ['disposition_action'])


def downgrade() -> None:
    op.drop_table('disposition_records')
    op.drop_table('refurbishment_orders')
    op.drop_table('return_inspections')
    op.drop_table('return_receipt_items')
    op.drop_table('return_receipts')
    op.drop_table('return_authorization_items')
    op.drop_table('return_authorizations')
