"""Add WMS Advanced tables - Phase 2: Wave Picking & Task Interleaving

Revision ID: 20260205_wms_adv
Revises: 20260205_add_dom
Create Date: 2026-02-05

Tables created:
- pick_waves: Wave picking management
- wave_picklists: Wave-picklist association
- warehouse_tasks: Generic task interleaving
- slot_scores: Bin slotting optimization
- cross_docks: Cross-docking workflows
- worker_locations: Real-time worker tracking
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '20260205_wms_adv'
down_revision = 'dom_foundation_001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # =========================================================================
    # PICK_WAVES - Wave Picking Management
    # =========================================================================
    op.create_table(
        'pick_waves',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False, index=True),

        # Identification
        sa.Column('wave_number', sa.String(30), nullable=False, index=True),
        sa.Column('name', sa.String(200), nullable=True),

        # Warehouse
        sa.Column('warehouse_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('warehouses.id', ondelete='RESTRICT'), nullable=False, index=True),

        # Wave Configuration
        sa.Column('wave_type', sa.String(50), default='CARRIER_CUTOFF', nullable=False),
        sa.Column('status', sa.String(50), default='DRAFT', nullable=False, index=True),

        # Carrier Cutoff
        sa.Column('carrier_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('transporters.id', ondelete='SET NULL'), nullable=True),
        sa.Column('cutoff_time', sa.Time, nullable=True),
        sa.Column('cutoff_date', sa.Date, nullable=True),

        # Zone Filtering
        sa.Column('zone_ids', postgresql.JSONB, nullable=True),

        # Priority Filtering
        sa.Column('min_priority', sa.Integer, nullable=True),
        sa.Column('max_priority', sa.Integer, nullable=True),

        # Channel/Customer Filtering
        sa.Column('channel_ids', postgresql.JSONB, nullable=True),
        sa.Column('customer_types', postgresql.JSONB, nullable=True),

        # Wave Metrics
        sa.Column('total_orders', sa.Integer, default=0),
        sa.Column('total_picklists', sa.Integer, default=0),
        sa.Column('total_items', sa.Integer, default=0),
        sa.Column('total_quantity', sa.Integer, default=0),
        sa.Column('completed_picklists', sa.Integer, default=0),
        sa.Column('picked_quantity', sa.Integer, default=0),

        # Optimization Settings
        sa.Column('optimize_route', sa.Boolean, default=True),
        sa.Column('group_by_zone', sa.Boolean, default=True),
        sa.Column('max_picks_per_trip', sa.Integer, nullable=True),
        sa.Column('max_weight_per_trip', sa.Numeric(10, 2), nullable=True),

        # Assignment
        sa.Column('assigned_pickers', postgresql.JSONB, nullable=True),

        # Timestamps
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False, index=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('released_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('cancelled_at', sa.DateTime(timezone=True), nullable=True),

        # Audit
        sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('released_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('notes', sa.Text, nullable=True),
        sa.Column('cancellation_reason', sa.Text, nullable=True),
    )

    # Indexes
    op.create_index('ix_pick_waves_warehouse_status', 'pick_waves', ['warehouse_id', 'status'])
    op.create_index('ix_pick_waves_cutoff_time', 'pick_waves', ['cutoff_time'])

    # Unique constraint
    op.create_unique_constraint('uq_pick_waves_tenant_number', 'pick_waves', ['tenant_id', 'wave_number'])

    # =========================================================================
    # WAVE_PICKLISTS - Wave-Picklist Association
    # =========================================================================
    op.create_table(
        'wave_picklists',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('wave_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('pick_waves.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('picklist_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('picklists.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('sequence', sa.Integer, default=0),
        sa.Column('zone_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('warehouse_zones.id', ondelete='SET NULL'), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_unique_constraint('uq_wave_picklist', 'wave_picklists', ['wave_id', 'picklist_id'])

    # =========================================================================
    # CROSS_DOCKS - Cross-Docking Workflows (create before warehouse_tasks due to FK)
    # =========================================================================
    op.create_table(
        'cross_docks',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False, index=True),

        # Identification
        sa.Column('cross_dock_number', sa.String(30), nullable=False, unique=True, index=True),
        sa.Column('cross_dock_type', sa.String(50), default='FLOW_THROUGH', nullable=False),
        sa.Column('status', sa.String(50), default='PENDING', nullable=False, index=True),

        # Warehouse
        sa.Column('warehouse_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('warehouses.id', ondelete='RESTRICT'), nullable=False, index=True),

        # Inbound Reference
        sa.Column('inbound_grn_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('inbound_po_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('inbound_dock', sa.String(50), nullable=True),
        sa.Column('expected_arrival', sa.DateTime(timezone=True), nullable=True),
        sa.Column('actual_arrival', sa.DateTime(timezone=True), nullable=True),

        # Outbound Reference
        sa.Column('outbound_order_ids', postgresql.JSONB, nullable=True),
        sa.Column('outbound_shipment_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('outbound_dock', sa.String(50), nullable=True),
        sa.Column('scheduled_departure', sa.DateTime(timezone=True), nullable=True),
        sa.Column('actual_departure', sa.DateTime(timezone=True), nullable=True),

        # Items
        sa.Column('items', postgresql.JSONB, nullable=True),
        sa.Column('total_quantity', sa.Integer, default=0),
        sa.Column('processed_quantity', sa.Integer, default=0),

        # Staging
        sa.Column('staging_bin_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('warehouse_bins.id', ondelete='SET NULL'), nullable=True),

        # Timestamps
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),

        # Audit
        sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('notes', sa.Text, nullable=True),
    )

    op.create_index('ix_cross_docks_status', 'cross_docks', ['status'])

    # =========================================================================
    # WAREHOUSE_TASKS - Generic Task Interleaving
    # =========================================================================
    op.create_table(
        'warehouse_tasks',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False, index=True),

        # Task Identification
        sa.Column('task_number', sa.String(30), nullable=False, index=True),
        sa.Column('task_type', sa.String(50), nullable=False, index=True),
        sa.Column('status', sa.String(50), default='PENDING', nullable=False, index=True),
        sa.Column('priority', sa.String(20), default='NORMAL', nullable=False, index=True),

        # Location
        sa.Column('warehouse_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('warehouses.id', ondelete='RESTRICT'), nullable=False, index=True),
        sa.Column('zone_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('warehouse_zones.id', ondelete='SET NULL'), nullable=True, index=True),

        # Source and Destination Bins
        sa.Column('source_bin_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('warehouse_bins.id', ondelete='SET NULL'), nullable=True),
        sa.Column('source_bin_code', sa.String(100), nullable=True),
        sa.Column('destination_bin_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('warehouse_bins.id', ondelete='SET NULL'), nullable=True),
        sa.Column('destination_bin_code', sa.String(100), nullable=True),

        # Product
        sa.Column('product_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('products.id', ondelete='SET NULL'), nullable=True),
        sa.Column('variant_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('sku', sa.String(100), nullable=True),
        sa.Column('product_name', sa.String(255), nullable=True),

        # Quantities
        sa.Column('quantity_required', sa.Integer, default=0),
        sa.Column('quantity_completed', sa.Integer, default=0),
        sa.Column('quantity_exception', sa.Integer, default=0),

        # Reference to parent entities
        sa.Column('wave_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('pick_waves.id', ondelete='SET NULL'), nullable=True, index=True),
        sa.Column('picklist_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('picklists.id', ondelete='SET NULL'), nullable=True),
        sa.Column('picklist_item_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('grn_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('cross_dock_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('cross_docks.id', ondelete='SET NULL'), nullable=True),

        # Assignment
        sa.Column('assigned_to', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True, index=True),
        sa.Column('assigned_at', sa.DateTime(timezone=True), nullable=True),

        # Task Interleaving
        sa.Column('suggested_next_task_id', postgresql.UUID(as_uuid=True), nullable=True),

        # Equipment
        sa.Column('equipment_type', sa.String(50), nullable=True),
        sa.Column('equipment_id', sa.String(50), nullable=True),

        # SLA
        sa.Column('due_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('sla_priority_boost', sa.Boolean, default=False),

        # Timestamps
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False, index=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('paused_at', sa.DateTime(timezone=True), nullable=True),

        # Performance Metrics
        sa.Column('travel_time_seconds', sa.Integer, nullable=True),
        sa.Column('execution_time_seconds', sa.Integer, nullable=True),
        sa.Column('total_time_seconds', sa.Integer, nullable=True),

        # Exception Handling
        sa.Column('exception_reason', sa.Text, nullable=True),
        sa.Column('exception_handled_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('exception_handled_at', sa.DateTime(timezone=True), nullable=True),

        # Notes
        sa.Column('notes', sa.Text, nullable=True),
        sa.Column('instruction', sa.Text, nullable=True),

        # Audit
        sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=True),
    )

    # Indexes
    op.create_index('ix_warehouse_tasks_status_priority', 'warehouse_tasks', ['status', 'priority'])
    op.create_index('ix_warehouse_tasks_assigned', 'warehouse_tasks', ['assigned_to', 'status'])
    op.create_index('ix_warehouse_tasks_zone', 'warehouse_tasks', ['zone_id', 'status'])
    op.create_index('ix_warehouse_tasks_type_status', 'warehouse_tasks', ['task_type', 'status'])

    # =========================================================================
    # SLOT_SCORES - Bin Slotting Optimization
    # =========================================================================
    op.create_table(
        'slot_scores',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False, index=True),

        # Product
        sa.Column('product_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('products.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('variant_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('sku', sa.String(100), nullable=False, index=True),

        # Warehouse
        sa.Column('warehouse_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('warehouses.id', ondelete='CASCADE'), nullable=False, index=True),

        # Velocity Classification (ABC)
        sa.Column('velocity_class', sa.String(1), default='C', nullable=False, index=True),
        sa.Column('pick_frequency', sa.Integer, default=0),
        sa.Column('pick_quantity', sa.Integer, default=0),

        # Scoring Factors
        sa.Column('velocity_score', sa.Numeric(10, 4), default=0),
        sa.Column('affinity_score', sa.Numeric(10, 4), default=0),
        sa.Column('ergonomic_score', sa.Numeric(10, 4), default=0),
        sa.Column('seasonality_score', sa.Numeric(10, 4), default=0),
        sa.Column('total_score', sa.Numeric(10, 4), default=0),

        # Current Slot
        sa.Column('current_bin_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('warehouse_bins.id', ondelete='SET NULL'), nullable=True),
        sa.Column('current_zone_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('warehouse_zones.id', ondelete='SET NULL'), nullable=True),

        # Recommended Slot
        sa.Column('recommended_bin_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('warehouse_bins.id', ondelete='SET NULL'), nullable=True),
        sa.Column('recommended_zone_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('warehouse_zones.id', ondelete='SET NULL'), nullable=True),
        sa.Column('relocation_priority', sa.Integer, nullable=True),
        sa.Column('relocation_reason', sa.String(200), nullable=True),

        # Analysis Period
        sa.Column('analysis_start', sa.Date, nullable=True),
        sa.Column('analysis_end', sa.Date, nullable=True),

        # Timestamps
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('last_analyzed_at', sa.DateTime(timezone=True), nullable=True),
    )

    # Unique constraint
    op.create_unique_constraint('uq_slot_score_product_warehouse', 'slot_scores',
                                ['tenant_id', 'product_id', 'warehouse_id'])
    op.create_index('ix_slot_scores_velocity', 'slot_scores', ['velocity_class', 'pick_frequency'])

    # =========================================================================
    # WORKER_LOCATIONS - Real-time Worker Tracking
    # =========================================================================
    op.create_table(
        'worker_locations',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False, index=True),

        # Worker
        sa.Column('user_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True),

        # Warehouse
        sa.Column('warehouse_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('warehouses.id', ondelete='CASCADE'), nullable=False, index=True),

        # Current Location
        sa.Column('current_zone_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('warehouse_zones.id', ondelete='SET NULL'), nullable=True),
        sa.Column('current_bin_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('warehouse_bins.id', ondelete='SET NULL'), nullable=True),
        sa.Column('current_bin_code', sa.String(100), nullable=True),

        # Current Task
        sa.Column('current_task_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('warehouse_tasks.id', ondelete='SET NULL'), nullable=True),

        # Status
        sa.Column('is_active', sa.Boolean, default=True),
        sa.Column('is_on_break', sa.Boolean, default=False),
        sa.Column('shift_start', sa.DateTime(timezone=True), nullable=True),
        sa.Column('shift_end', sa.DateTime(timezone=True), nullable=True),

        # Equipment
        sa.Column('equipment_type', sa.String(50), nullable=True),
        sa.Column('equipment_id', sa.String(50), nullable=True),

        # Performance (today)
        sa.Column('tasks_completed_today', sa.Integer, default=0),
        sa.Column('items_picked_today', sa.Integer, default=0),
        sa.Column('distance_traveled_meters', sa.Integer, default=0),

        # Timestamps
        sa.Column('last_scan_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )


def downgrade() -> None:
    # Drop tables in reverse order (respect foreign key dependencies)
    op.drop_table('worker_locations')
    op.drop_table('slot_scores')
    op.drop_table('warehouse_tasks')
    op.drop_table('wave_picklists')
    op.drop_table('cross_docks')
    op.drop_table('pick_waves')
