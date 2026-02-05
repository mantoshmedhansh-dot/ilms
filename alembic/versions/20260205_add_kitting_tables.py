"""Add Kitting & Assembly tables - Phase 8: Kit Management & Assembly Operations

Revision ID: 20260205_kitting
Revises: 20260205_qc
Create Date: 2026-02-05

Tables created:
- kit_definitions: Kit/bundle product definitions
- kit_components: Components that make up a kit
- assembly_stations: Assembly workstation management
- kit_work_orders: Work orders for kit assembly/disassembly
- kit_build_records: Individual kit build tracking
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '20260205_kitting'
down_revision = '20260205_qc'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # =========================================================================
    # KIT_DEFINITIONS - Kit/Bundle Product Definitions
    # =========================================================================
    op.create_table(
        'kit_definitions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False, index=True),

        # Kit Identity
        sa.Column('kit_sku', sa.String(100), nullable=False, index=True),
        sa.Column('kit_name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('kit_type', sa.String(30), default='STANDARD', nullable=False),
        sa.Column('status', sa.String(30), default='DRAFT', nullable=False, index=True),

        # Link to kit product
        sa.Column('product_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('products.id', ondelete='SET NULL'), nullable=True, index=True),

        # Warehouse
        sa.Column('warehouse_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('warehouses.id', ondelete='SET NULL'), nullable=True, index=True),

        # Assembly Info
        sa.Column('assembly_time_minutes', sa.Integer, default=10),
        sa.Column('labor_cost', sa.Numeric(10, 2), default=0),
        sa.Column('packaging_cost', sa.Numeric(10, 2), default=0),

        # Assembly Instructions
        sa.Column('instructions', sa.Text, nullable=True),
        sa.Column('instruction_images', postgresql.JSONB, nullable=True),
        sa.Column('instruction_video_url', sa.String(500), nullable=True),

        # Packaging
        sa.Column('packaging_type', sa.String(50), nullable=True),
        sa.Column('package_weight', sa.Numeric(10, 3), nullable=True),
        sa.Column('package_length', sa.Numeric(10, 2), nullable=True),
        sa.Column('package_width', sa.Numeric(10, 2), nullable=True),
        sa.Column('package_height', sa.Numeric(10, 2), nullable=True),

        # QC Requirements
        sa.Column('requires_qc', sa.Boolean, default=False),
        sa.Column('qc_checklist', postgresql.JSONB, nullable=True),

        # Validity
        sa.Column('effective_from', sa.Date, nullable=True),
        sa.Column('effective_to', sa.Date, nullable=True),

        # Stats
        sa.Column('total_builds', sa.Integer, default=0),
        sa.Column('avg_build_time_minutes', sa.Numeric(8, 2), nullable=True),

        sa.Column('notes', sa.Text, nullable=True),

        # Timestamps
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('created_by', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
    )

    op.create_unique_constraint('uq_kit_sku', 'kit_definitions', ['tenant_id', 'kit_sku'])
    op.create_index('ix_kit_definitions_status', 'kit_definitions', ['status'])

    # =========================================================================
    # KIT_COMPONENTS - Components that make up a kit
    # =========================================================================
    op.create_table(
        'kit_components',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False, index=True),

        # Kit Reference
        sa.Column('kit_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('kit_definitions.id', ondelete='CASCADE'), nullable=False, index=True),

        # Component Product
        sa.Column('product_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('products.id', ondelete='RESTRICT'), nullable=False, index=True),
        sa.Column('sku', sa.String(100), nullable=False),
        sa.Column('product_name', sa.String(255), nullable=False),

        # Quantity
        sa.Column('quantity', sa.Integer, default=1, nullable=False),
        sa.Column('uom', sa.String(20), default='EACH', nullable=False),

        # Component Type
        sa.Column('component_type', sa.String(30), default='REQUIRED', nullable=False),

        # Substitution
        sa.Column('substitute_group', sa.String(50), nullable=True),
        sa.Column('substitute_priority', sa.Integer, default=1),

        # Sequence
        sa.Column('sequence', sa.Integer, default=0),

        # Cost
        sa.Column('component_cost', sa.Numeric(12, 2), default=0),

        # Special Handling
        sa.Column('special_instructions', sa.Text, nullable=True),
        sa.Column('requires_serial', sa.Boolean, default=False),

        sa.Column('is_active', sa.Boolean, default=True),

        # Timestamps
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_index('ix_kit_components_kit', 'kit_components', ['kit_id'])
    op.create_index('ix_kit_components_product', 'kit_components', ['product_id'])

    # =========================================================================
    # ASSEMBLY_STATIONS - Assembly Workstations
    # =========================================================================
    op.create_table(
        'assembly_stations',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False, index=True),

        sa.Column('warehouse_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('warehouses.id', ondelete='CASCADE'), nullable=False, index=True),

        # Station Identity
        sa.Column('station_code', sa.String(30), nullable=False, index=True),
        sa.Column('station_name', sa.String(100), nullable=False),
        sa.Column('status', sa.String(30), default='AVAILABLE', nullable=False, index=True),

        # Location
        sa.Column('zone_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('warehouse_zones.id', ondelete='SET NULL'), nullable=True),

        # Equipment
        sa.Column('equipment', postgresql.JSONB, nullable=True),
        sa.Column('tools_required', postgresql.JSONB, nullable=True),

        # Capacity
        sa.Column('max_concurrent_builds', sa.Integer, default=1),
        sa.Column('current_builds', sa.Integer, default=0),

        # Assignment
        sa.Column('assigned_worker_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('assigned_at', sa.DateTime(timezone=True), nullable=True),

        # Current Work Order
        sa.Column('current_work_order_id', postgresql.UUID(as_uuid=True), nullable=True),

        # Stats
        sa.Column('total_builds_today', sa.Integer, default=0),
        sa.Column('avg_build_time_today', sa.Numeric(8, 2), nullable=True),

        sa.Column('is_active', sa.Boolean, default=True),
        sa.Column('notes', sa.Text, nullable=True),

        # Timestamps
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_unique_constraint('uq_station_code', 'assembly_stations',
                                ['tenant_id', 'warehouse_id', 'station_code'])

    # =========================================================================
    # KIT_WORK_ORDERS - Work Orders for Kit Assembly/Disassembly
    # =========================================================================
    op.create_table(
        'kit_work_orders',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False, index=True),

        # Work Order Identity
        sa.Column('work_order_number', sa.String(30), nullable=False, unique=True, index=True),
        sa.Column('work_order_type', sa.String(30), default='ASSEMBLY', nullable=False),
        sa.Column('status', sa.String(30), default='DRAFT', nullable=False, index=True),
        sa.Column('priority', sa.String(20), default='NORMAL', nullable=False),

        # Kit Reference
        sa.Column('kit_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('kit_definitions.id', ondelete='RESTRICT'), nullable=False, index=True),

        # Warehouse
        sa.Column('warehouse_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('warehouses.id', ondelete='CASCADE'), nullable=False, index=True),

        # Station
        sa.Column('station_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('assembly_stations.id', ondelete='SET NULL'), nullable=True),

        # Quantities
        sa.Column('quantity_ordered', sa.Integer, nullable=False),
        sa.Column('quantity_completed', sa.Integer, default=0),
        sa.Column('quantity_failed', sa.Integer, default=0),
        sa.Column('quantity_remaining', sa.Integer, nullable=False),

        # Scheduling
        sa.Column('scheduled_date', sa.Date, nullable=False, index=True),
        sa.Column('due_date', sa.Date, nullable=True),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),

        # Source Reference
        sa.Column('order_id', postgresql.UUID(as_uuid=True), nullable=True),

        # Assignment
        sa.Column('assigned_to', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),

        # Component Availability
        sa.Column('components_available', sa.Boolean, default=False),
        sa.Column('component_shortage', postgresql.JSONB, nullable=True),

        # Destination
        sa.Column('destination_bin_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('warehouse_bins.id', ondelete='SET NULL'), nullable=True),

        # Time Tracking
        sa.Column('estimated_hours', sa.Numeric(6, 2), nullable=True),
        sa.Column('actual_hours', sa.Numeric(6, 2), nullable=True),

        # Cost
        sa.Column('estimated_cost', sa.Numeric(12, 2), default=0),
        sa.Column('actual_cost', sa.Numeric(12, 2), default=0),

        sa.Column('notes', sa.Text, nullable=True),
        sa.Column('cancellation_reason', sa.String(200), nullable=True),

        # Audit
        sa.Column('created_by', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),

        # Timestamps
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_index('ix_kit_work_orders_status', 'kit_work_orders', ['status'])
    op.create_index('ix_kit_work_orders_date', 'kit_work_orders', ['scheduled_date'])

    # =========================================================================
    # KIT_BUILD_RECORDS - Individual Kit Build Tracking
    # =========================================================================
    op.create_table(
        'kit_build_records',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False, index=True),

        # Work Order Reference
        sa.Column('work_order_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('kit_work_orders.id', ondelete='CASCADE'), nullable=False, index=True),

        # Build Identity
        sa.Column('build_number', sa.Integer, nullable=False),
        sa.Column('status', sa.String(30), default='PENDING', nullable=False, index=True),

        # Kit Info (denormalized)
        sa.Column('kit_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('kit_sku', sa.String(100), nullable=False),

        # Serial/LPN
        sa.Column('serial_number', sa.String(100), nullable=True, unique=True),
        sa.Column('lpn', sa.String(50), nullable=True),

        # Components Used
        sa.Column('components_used', postgresql.JSONB, nullable=True),

        # Station
        sa.Column('station_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('assembly_stations.id', ondelete='SET NULL'), nullable=True),

        # Builder
        sa.Column('built_by', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),

        # Timing
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('build_time_minutes', sa.Integer, nullable=True),

        # QC
        sa.Column('qc_status', sa.String(30), nullable=True),
        sa.Column('qc_by', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('qc_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('qc_notes', sa.Text, nullable=True),

        # Destination
        sa.Column('destination_bin_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('warehouse_bins.id', ondelete='SET NULL'), nullable=True),

        # Failure
        sa.Column('failure_reason', sa.String(200), nullable=True),

        sa.Column('notes', sa.Text, nullable=True),

        # Timestamps
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_index('ix_kit_build_records_work_order', 'kit_build_records', ['work_order_id'])
    op.create_index('ix_kit_build_records_status', 'kit_build_records', ['status'])


def downgrade() -> None:
    op.drop_table('kit_build_records')
    op.drop_table('kit_work_orders')
    op.drop_table('assembly_stations')
    op.drop_table('kit_components')
    op.drop_table('kit_definitions')
