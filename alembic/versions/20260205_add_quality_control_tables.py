"""Add Quality Control tables - Phase 7: Inspection & Quality Management

Revision ID: 20260205_qc
Revises: 20260205_yard_mgmt
Create Date: 2026-02-05

Tables created:
- qc_configurations: Quality standards and parameters
- qc_inspections: Inspection records
- qc_defects: Defect recording
- qc_hold_areas: Quarantine/hold management
- qc_samplings: Sample-based inspection
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '20260205_qc'
down_revision = '20260205_yard_mgmt'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # =========================================================================
    # QC_CONFIGURATIONS - Quality Standards
    # =========================================================================
    op.create_table(
        'qc_configurations',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False, index=True),

        sa.Column('config_code', sa.String(30), nullable=False, index=True),
        sa.Column('config_name', sa.String(100), nullable=False),
        sa.Column('description', sa.Text, nullable=True),

        sa.Column('warehouse_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('warehouses.id', ondelete='CASCADE'), nullable=True, index=True),
        sa.Column('product_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('products.id', ondelete='CASCADE'), nullable=True, index=True),
        sa.Column('category_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('categories.id', ondelete='CASCADE'), nullable=True),
        sa.Column('vendor_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('vendors.id', ondelete='CASCADE'), nullable=True),

        sa.Column('inspection_type', sa.String(30), default='RECEIVING', nullable=False),
        sa.Column('sampling_plan', sa.String(30), default='FULL', nullable=False),
        sa.Column('sample_size_percent', sa.Numeric(5, 2), nullable=True),
        sa.Column('sample_size_quantity', sa.Integer, nullable=True),
        sa.Column('aql_level', sa.Numeric(4, 2), nullable=True),

        sa.Column('max_defect_percent', sa.Numeric(5, 2), default=0),
        sa.Column('max_critical_defects', sa.Integer, default=0),
        sa.Column('max_major_defects', sa.Integer, default=0),
        sa.Column('max_minor_defects', sa.Integer, nullable=True),

        sa.Column('checkpoints', postgresql.JSONB, nullable=True),
        sa.Column('measurements', postgresql.JSONB, nullable=True),

        sa.Column('auto_release_on_pass', sa.Boolean, default=True),
        sa.Column('auto_hold_on_fail', sa.Boolean, default=True),
        sa.Column('require_supervisor_approval', sa.Boolean, default=False),
        sa.Column('is_receiving_required', sa.Boolean, default=True),
        sa.Column('is_shipping_required', sa.Boolean, default=False),

        sa.Column('is_active', sa.Boolean, default=True),
        sa.Column('notes', sa.Text, nullable=True),

        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_unique_constraint('uq_qc_config_code', 'qc_configurations',
                                ['tenant_id', 'config_code'])
    op.create_index('ix_qc_configurations_product', 'qc_configurations', ['product_id'])

    # =========================================================================
    # QC_INSPECTIONS - Inspection Records
    # =========================================================================
    op.create_table(
        'qc_inspections',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False, index=True),

        sa.Column('inspection_number', sa.String(30), nullable=False, unique=True, index=True),
        sa.Column('inspection_type', sa.String(30), nullable=False),
        sa.Column('status', sa.String(30), default='PENDING', nullable=False, index=True),

        sa.Column('warehouse_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('warehouses.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('zone_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('warehouse_zones.id', ondelete='SET NULL'), nullable=True),
        sa.Column('config_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('qc_configurations.id', ondelete='SET NULL'), nullable=True),

        sa.Column('grn_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('goods_receipt_notes.id', ondelete='SET NULL'), nullable=True, index=True),
        sa.Column('shipment_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('order_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('return_order_id', postgresql.UUID(as_uuid=True), nullable=True),

        sa.Column('product_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('products.id', ondelete='RESTRICT'), nullable=False, index=True),
        sa.Column('sku', sa.String(100), nullable=False),
        sa.Column('product_name', sa.String(255), nullable=False),
        sa.Column('vendor_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('vendors.id', ondelete='SET NULL'), nullable=True),

        sa.Column('total_quantity', sa.Integer, nullable=False),
        sa.Column('sample_quantity', sa.Integer, nullable=False),
        sa.Column('passed_quantity', sa.Integer, default=0),
        sa.Column('failed_quantity', sa.Integer, default=0),
        sa.Column('pending_quantity', sa.Integer, default=0),

        sa.Column('lot_number', sa.String(50), nullable=True),
        sa.Column('batch_number', sa.String(50), nullable=True),
        sa.Column('manufacture_date', sa.Date, nullable=True),
        sa.Column('expiry_date', sa.Date, nullable=True),

        sa.Column('inspection_date', sa.Date, nullable=False, index=True),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('inspector_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),

        sa.Column('defect_count', sa.Integer, default=0),
        sa.Column('critical_defects', sa.Integer, default=0),
        sa.Column('major_defects', sa.Integer, default=0),
        sa.Column('minor_defects', sa.Integer, default=0),
        sa.Column('defect_rate', sa.Numeric(5, 2), nullable=True),

        sa.Column('checkpoint_results', postgresql.JSONB, nullable=True),
        sa.Column('measurement_results', postgresql.JSONB, nullable=True),

        sa.Column('disposition', sa.String(30), nullable=True),
        sa.Column('disposition_notes', sa.Text, nullable=True),
        sa.Column('disposition_by', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('disposition_at', sa.DateTime(timezone=True), nullable=True),

        sa.Column('requires_approval', sa.Boolean, default=False),
        sa.Column('approved_by', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('approved_at', sa.DateTime(timezone=True), nullable=True),

        sa.Column('photos', postgresql.JSONB, nullable=True),
        sa.Column('documents', postgresql.JSONB, nullable=True),
        sa.Column('notes', sa.Text, nullable=True),

        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_index('ix_qc_inspections_date', 'qc_inspections', ['inspection_date'])
    op.create_index('ix_qc_inspections_status', 'qc_inspections', ['status'])

    # =========================================================================
    # QC_DEFECTS - Defect Records
    # =========================================================================
    op.create_table(
        'qc_defects',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False, index=True),

        sa.Column('inspection_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('qc_inspections.id', ondelete='CASCADE'), nullable=False, index=True),

        sa.Column('defect_code', sa.String(30), nullable=False, index=True),
        sa.Column('defect_name', sa.String(100), nullable=False),
        sa.Column('category', sa.String(30), nullable=False),
        sa.Column('severity', sa.String(30), nullable=False, index=True),
        sa.Column('description', sa.Text, nullable=True),

        sa.Column('defect_quantity', sa.Integer, default=1),
        sa.Column('defect_location', sa.String(100), nullable=True),
        sa.Column('serial_numbers', postgresql.JSONB, nullable=True),
        sa.Column('root_cause', sa.String(200), nullable=True),
        sa.Column('is_vendor_related', sa.Boolean, default=False),

        sa.Column('photos', postgresql.JSONB, nullable=True),

        sa.Column('recorded_by', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('recorded_at', sa.DateTime(timezone=True), server_default=sa.func.now()),

        sa.Column('notes', sa.Text, nullable=True),
    )

    op.create_index('ix_qc_defects_inspection', 'qc_defects', ['inspection_id'])
    op.create_index('ix_qc_defects_severity', 'qc_defects', ['severity'])

    # =========================================================================
    # QC_HOLD_AREAS - Quarantine/Hold
    # =========================================================================
    op.create_table(
        'qc_hold_areas',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False, index=True),

        sa.Column('hold_number', sa.String(30), nullable=False, unique=True, index=True),
        sa.Column('status', sa.String(30), default='ACTIVE', nullable=False, index=True),

        sa.Column('warehouse_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('warehouses.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('hold_bin_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('warehouse_bins.id', ondelete='SET NULL'), nullable=True),

        sa.Column('hold_reason', sa.String(30), nullable=False),
        sa.Column('reason_detail', sa.Text, nullable=True),

        sa.Column('inspection_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('qc_inspections.id', ondelete='SET NULL'), nullable=True),
        sa.Column('grn_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('return_order_id', postgresql.UUID(as_uuid=True), nullable=True),

        sa.Column('product_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('products.id', ondelete='RESTRICT'), nullable=False, index=True),
        sa.Column('sku', sa.String(100), nullable=False),

        sa.Column('hold_quantity', sa.Integer, nullable=False),
        sa.Column('released_quantity', sa.Integer, default=0),
        sa.Column('scrapped_quantity', sa.Integer, default=0),
        sa.Column('returned_quantity', sa.Integer, default=0),
        sa.Column('remaining_quantity', sa.Integer, nullable=False),

        sa.Column('lot_number', sa.String(50), nullable=True),
        sa.Column('serial_numbers', postgresql.JSONB, nullable=True),
        sa.Column('vendor_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('vendors.id', ondelete='SET NULL'), nullable=True),

        sa.Column('hold_date', sa.Date, nullable=False),
        sa.Column('target_resolution_date', sa.Date, nullable=True),
        sa.Column('resolved_date', sa.Date, nullable=True),

        sa.Column('created_by', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('resolved_by', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),

        sa.Column('resolution_action', sa.String(30), nullable=True),
        sa.Column('resolution_notes', sa.Text, nullable=True),
        sa.Column('notes', sa.Text, nullable=True),

        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_index('ix_qc_hold_areas_status', 'qc_hold_areas', ['status'])
    op.create_index('ix_qc_hold_areas_product', 'qc_hold_areas', ['product_id'])

    # =========================================================================
    # QC_SAMPLINGS - Sample Records
    # =========================================================================
    op.create_table(
        'qc_samplings',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False, index=True),

        sa.Column('inspection_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('qc_inspections.id', ondelete='CASCADE'), nullable=False, index=True),

        sa.Column('sample_number', sa.Integer, nullable=False),
        sa.Column('sample_quantity', sa.Integer, nullable=False),
        sa.Column('passed_quantity', sa.Integer, default=0),
        sa.Column('failed_quantity', sa.Integer, default=0),

        sa.Column('serial_numbers', postgresql.JSONB, nullable=True),
        sa.Column('lpn', sa.String(50), nullable=True),

        sa.Column('checkpoint_results', postgresql.JSONB, nullable=True),
        sa.Column('measurements', postgresql.JSONB, nullable=True),

        sa.Column('result', sa.String(20), nullable=False),
        sa.Column('defect_count', sa.Integer, default=0),

        sa.Column('inspected_by', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('inspected_at', sa.DateTime(timezone=True), server_default=sa.func.now()),

        sa.Column('photos', postgresql.JSONB, nullable=True),
        sa.Column('notes', sa.Text, nullable=True),
    )

    op.create_index('ix_qc_samplings_inspection', 'qc_samplings', ['inspection_id'])


def downgrade() -> None:
    op.drop_table('qc_samplings')
    op.drop_table('qc_hold_areas')
    op.drop_table('qc_defects')
    op.drop_table('qc_inspections')
    op.drop_table('qc_configurations')
