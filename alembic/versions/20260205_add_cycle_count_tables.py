"""Add cycle count tables

Revision ID: 20260205_cycle_count
Revises: 20260205_billing
Create Date: 2026-02-05

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '20260205_cycle_count'
down_revision: Union[str, None] = '20260205_billing'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Cycle Count Plans
    op.create_table(
        'cycle_count_plans',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('tenants.id'), nullable=False),
        sa.Column('warehouse_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('warehouses.id'), nullable=False),
        sa.Column('plan_name', sa.String(200), nullable=False),
        sa.Column('plan_code', sa.String(50), nullable=False),
        sa.Column('description', sa.Text),
        sa.Column('count_type', sa.String(30), nullable=False, default='cycle_count'),
        sa.Column('frequency', sa.String(20), nullable=False, default='weekly'),
        sa.Column('start_date', sa.Date, nullable=False),
        sa.Column('end_date', sa.Date),
        sa.Column('next_count_date', sa.Date),
        sa.Column('count_a_frequency', sa.String(20)),
        sa.Column('count_b_frequency', sa.String(20)),
        sa.Column('count_c_frequency', sa.String(20)),
        sa.Column('zone_ids', postgresql.JSONB),
        sa.Column('category_ids', postgresql.JSONB),
        sa.Column('product_ids', postgresql.JSONB),
        sa.Column('bin_ids', postgresql.JSONB),
        sa.Column('abc_classes', postgresql.JSONB),
        sa.Column('sample_percentage', sa.Numeric(5, 2)),
        sa.Column('min_items_per_count', sa.Integer, default=10),
        sa.Column('max_items_per_count', sa.Integer, default=100),
        sa.Column('count_method', sa.String(20), nullable=False, default='rf_scanner'),
        sa.Column('blind_count', sa.Boolean, default=False),
        sa.Column('require_recount_on_variance', sa.Boolean, default=True),
        sa.Column('recount_threshold_percent', sa.Numeric(5, 2), default=5.0),
        sa.Column('recount_threshold_value', sa.Numeric(15, 2), default=100.0),
        sa.Column('auto_approve_threshold_percent', sa.Numeric(5, 2), default=1.0),
        sa.Column('auto_approve_threshold_value', sa.Numeric(15, 2), default=50.0),
        sa.Column('supervisor_threshold_percent', sa.Numeric(5, 2), default=5.0),
        sa.Column('manager_threshold_percent', sa.Numeric(5, 2), default=10.0),
        sa.Column('director_threshold_value', sa.Numeric(15, 2), default=10000.0),
        sa.Column('status', sa.String(20), nullable=False, default='draft'),
        sa.Column('total_counts_completed', sa.Integer, default=0),
        sa.Column('total_items_counted', sa.Integer, default=0),
        sa.Column('total_variances_found', sa.Integer, default=0),
        sa.Column('accuracy_rate', sa.Numeric(5, 2)),
        sa.Column('last_count_date', sa.Date),
        sa.Column('notes', sa.Text),
        sa.Column('created_by', postgresql.UUID(as_uuid=True)),
        sa.Column('created_at', sa.DateTime, default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, default=sa.func.now(), onupdate=sa.func.now()),
        schema='public'
    )
    op.create_index('idx_ccp_tenant_warehouse', 'cycle_count_plans', ['tenant_id', 'warehouse_id'], schema='public')
    op.create_index('idx_ccp_status', 'cycle_count_plans', ['tenant_id', 'status'], schema='public')

    # Count Sessions
    op.create_table(
        'count_sessions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('tenants.id'), nullable=False),
        sa.Column('warehouse_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('warehouses.id'), nullable=False),
        sa.Column('plan_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('cycle_count_plans.id')),
        sa.Column('session_number', sa.String(50), nullable=False),
        sa.Column('session_name', sa.String(200), nullable=False),
        sa.Column('count_type', sa.String(30), nullable=False, default='cycle_count'),
        sa.Column('count_method', sa.String(20), nullable=False, default='rf_scanner'),
        sa.Column('blind_count', sa.Boolean, default=False),
        sa.Column('count_date', sa.Date, nullable=False),
        sa.Column('started_at', sa.DateTime),
        sa.Column('completed_at', sa.DateTime),
        sa.Column('zone_ids', postgresql.JSONB),
        sa.Column('bin_ids', postgresql.JSONB),
        sa.Column('category_ids', postgresql.JSONB),
        sa.Column('total_tasks', sa.Integer, default=0),
        sa.Column('completed_tasks', sa.Integer, default=0),
        sa.Column('total_items', sa.Integer, default=0),
        sa.Column('items_counted', sa.Integer, default=0),
        sa.Column('items_with_variance', sa.Integer, default=0),
        sa.Column('total_variance_qty', sa.Numeric(15, 3), default=0),
        sa.Column('total_variance_value', sa.Numeric(15, 2), default=0),
        sa.Column('positive_variance_qty', sa.Numeric(15, 3), default=0),
        sa.Column('negative_variance_qty', sa.Numeric(15, 3), default=0),
        sa.Column('accuracy_rate', sa.Numeric(5, 2)),
        sa.Column('first_count_accuracy', sa.Numeric(5, 2)),
        sa.Column('status', sa.String(20), nullable=False, default='pending'),
        sa.Column('approved_by', postgresql.UUID(as_uuid=True)),
        sa.Column('approved_at', sa.DateTime),
        sa.Column('approval_notes', sa.Text),
        sa.Column('notes', sa.Text),
        sa.Column('created_by', postgresql.UUID(as_uuid=True)),
        sa.Column('created_at', sa.DateTime, default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, default=sa.func.now(), onupdate=sa.func.now()),
        schema='public'
    )
    op.create_index('idx_csess_tenant_warehouse', 'count_sessions', ['tenant_id', 'warehouse_id'], schema='public')
    op.create_index('idx_csess_status', 'count_sessions', ['tenant_id', 'status'], schema='public')
    op.create_index('idx_csess_date', 'count_sessions', ['tenant_id', 'count_date'], schema='public')

    # Count Schedules
    op.create_table(
        'count_schedules',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('tenants.id'), nullable=False),
        sa.Column('plan_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('cycle_count_plans.id'), nullable=False),
        sa.Column('warehouse_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('warehouses.id'), nullable=False),
        sa.Column('scheduled_date', sa.Date, nullable=False),
        sa.Column('scheduled_time', sa.String(10)),
        sa.Column('assigned_to', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id')),
        sa.Column('team_ids', postgresql.JSONB),
        sa.Column('zone_ids', postgresql.JSONB),
        sa.Column('bin_ids', postgresql.JSONB),
        sa.Column('product_ids', postgresql.JSONB),
        sa.Column('estimated_item_count', sa.Integer, default=0),
        sa.Column('status', sa.String(20), default='pending'),
        sa.Column('session_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('count_sessions.id')),
        sa.Column('notes', sa.Text),
        sa.Column('created_at', sa.DateTime, default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, default=sa.func.now(), onupdate=sa.func.now()),
        schema='public'
    )
    op.create_index('idx_cs_tenant_plan', 'count_schedules', ['tenant_id', 'plan_id'], schema='public')
    op.create_index('idx_cs_date', 'count_schedules', ['tenant_id', 'scheduled_date'], schema='public')

    # Count Tasks
    op.create_table(
        'count_tasks',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('tenants.id'), nullable=False),
        sa.Column('session_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('count_sessions.id'), nullable=False),
        sa.Column('warehouse_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('warehouses.id'), nullable=False),
        sa.Column('task_number', sa.String(50), nullable=False),
        sa.Column('sequence', sa.Integer, default=0),
        sa.Column('zone_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('warehouse_zones.id')),
        sa.Column('bin_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('warehouse_bins.id')),
        sa.Column('location_code', sa.String(50), nullable=False),
        sa.Column('product_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('products.id')),
        sa.Column('variant_id', postgresql.UUID(as_uuid=True)),
        sa.Column('lot_number', sa.String(50)),
        sa.Column('serial_number', sa.String(100)),
        sa.Column('expected_qty', sa.Numeric(15, 3), default=0),
        sa.Column('expected_uom', sa.String(20), default='EACH'),
        sa.Column('expected_value', sa.Numeric(15, 2), default=0),
        sa.Column('first_count_qty', sa.Numeric(15, 3)),
        sa.Column('first_count_by', postgresql.UUID(as_uuid=True)),
        sa.Column('first_count_at', sa.DateTime),
        sa.Column('first_count_method', sa.String(20)),
        sa.Column('recount_required', sa.Boolean, default=False),
        sa.Column('recount_qty', sa.Numeric(15, 3)),
        sa.Column('recount_by', postgresql.UUID(as_uuid=True)),
        sa.Column('recount_at', sa.DateTime),
        sa.Column('final_count_qty', sa.Numeric(15, 3)),
        sa.Column('final_count_value', sa.Numeric(15, 2)),
        sa.Column('variance_qty', sa.Numeric(15, 3), default=0),
        sa.Column('variance_value', sa.Numeric(15, 2), default=0),
        sa.Column('variance_percent', sa.Numeric(8, 4), default=0),
        sa.Column('has_variance', sa.Boolean, default=False),
        sa.Column('assigned_to', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id')),
        sa.Column('assigned_at', sa.DateTime),
        sa.Column('status', sa.String(20), nullable=False, default='pending'),
        sa.Column('approval_level', sa.String(20)),
        sa.Column('approved_by', postgresql.UUID(as_uuid=True)),
        sa.Column('approved_at', sa.DateTime),
        sa.Column('rejection_reason', sa.Text),
        sa.Column('notes', sa.Text),
        sa.Column('photos', postgresql.JSONB),
        sa.Column('created_at', sa.DateTime, default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, default=sa.func.now(), onupdate=sa.func.now()),
        schema='public'
    )
    op.create_index('idx_ct_tenant_session', 'count_tasks', ['tenant_id', 'session_id'], schema='public')
    op.create_index('idx_ct_status', 'count_tasks', ['tenant_id', 'status'], schema='public')
    op.create_index('idx_ct_assignee', 'count_tasks', ['tenant_id', 'assigned_to'], schema='public')
    op.create_index('idx_ct_bin', 'count_tasks', ['tenant_id', 'bin_id'], schema='public')

    # Count Details
    op.create_table(
        'count_details',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('tenants.id'), nullable=False),
        sa.Column('task_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('count_tasks.id'), nullable=False),
        sa.Column('count_sequence', sa.Integer, nullable=False),
        sa.Column('is_recount', sa.Boolean, default=False),
        sa.Column('product_id', postgresql.UUID(as_uuid=True)),
        sa.Column('barcode_scanned', sa.String(100)),
        sa.Column('lot_number', sa.String(50)),
        sa.Column('serial_number', sa.String(100)),
        sa.Column('expiry_date', sa.Date),
        sa.Column('quantity', sa.Numeric(15, 3), nullable=False),
        sa.Column('uom', sa.String(20), default='EACH'),
        sa.Column('count_method', sa.String(20), nullable=False, default='rf_scanner'),
        sa.Column('device_id', sa.String(50)),
        sa.Column('counted_by', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('counted_at', sa.DateTime, default=sa.func.now()),
        sa.Column('found_in_bin', sa.String(50)),
        sa.Column('notes', sa.Text),
        sa.Column('created_at', sa.DateTime, default=sa.func.now()),
        schema='public'
    )
    op.create_index('idx_cd_tenant_task', 'count_details', ['tenant_id', 'task_id'], schema='public')

    # Inventory Variances
    op.create_table(
        'inventory_variances',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('tenants.id'), nullable=False),
        sa.Column('warehouse_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('warehouses.id'), nullable=False),
        sa.Column('session_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('count_sessions.id'), nullable=False),
        sa.Column('task_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('count_tasks.id'), nullable=False),
        sa.Column('variance_number', sa.String(50), nullable=False),
        sa.Column('variance_date', sa.Date, nullable=False),
        sa.Column('zone_id', postgresql.UUID(as_uuid=True)),
        sa.Column('bin_id', postgresql.UUID(as_uuid=True)),
        sa.Column('location_code', sa.String(50), nullable=False),
        sa.Column('product_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('products.id'), nullable=False),
        sa.Column('variant_id', postgresql.UUID(as_uuid=True)),
        sa.Column('lot_number', sa.String(50)),
        sa.Column('system_qty', sa.Numeric(15, 3), nullable=False),
        sa.Column('counted_qty', sa.Numeric(15, 3), nullable=False),
        sa.Column('variance_qty', sa.Numeric(15, 3), nullable=False),
        sa.Column('uom', sa.String(20), default='EACH'),
        sa.Column('unit_cost', sa.Numeric(15, 4), default=0),
        sa.Column('variance_value', sa.Numeric(15, 2), nullable=False),
        sa.Column('variance_percent', sa.Numeric(8, 4), nullable=False),
        sa.Column('abc_class', sa.String(1)),
        sa.Column('is_positive', sa.Boolean, default=False),
        sa.Column('is_negative', sa.Boolean, default=True),
        sa.Column('status', sa.String(30), nullable=False, default='pending'),
        sa.Column('variance_reason', sa.String(30)),
        sa.Column('root_cause', sa.Text),
        sa.Column('corrective_action', sa.Text),
        sa.Column('approval_level', sa.String(20), nullable=False, default='supervisor'),
        sa.Column('approved_by', postgresql.UUID(as_uuid=True)),
        sa.Column('approved_at', sa.DateTime),
        sa.Column('adjustment_id', postgresql.UUID(as_uuid=True)),
        sa.Column('adjusted_by', postgresql.UUID(as_uuid=True)),
        sa.Column('adjusted_at', sa.DateTime),
        sa.Column('written_off', sa.Boolean, default=False),
        sa.Column('write_off_gl_account', sa.String(50)),
        sa.Column('write_off_amount', sa.Numeric(15, 2), default=0),
        sa.Column('investigated_by', postgresql.UUID(as_uuid=True)),
        sa.Column('investigation_notes', sa.Text),
        sa.Column('evidence_photos', postgresql.JSONB),
        sa.Column('notes', sa.Text),
        sa.Column('created_at', sa.DateTime, default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, default=sa.func.now(), onupdate=sa.func.now()),
        schema='public'
    )
    op.create_index('idx_iv_tenant_session', 'inventory_variances', ['tenant_id', 'session_id'], schema='public')
    op.create_index('idx_iv_status', 'inventory_variances', ['tenant_id', 'status'], schema='public')
    op.create_index('idx_iv_product', 'inventory_variances', ['tenant_id', 'product_id'], schema='public')

    # ABC Classifications
    op.create_table(
        'abc_classifications',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('tenants.id'), nullable=False),
        sa.Column('warehouse_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('warehouses.id'), nullable=False),
        sa.Column('product_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('products.id'), nullable=False),
        sa.Column('abc_class', sa.String(1), nullable=False),
        sa.Column('classification_method', sa.String(30), default='value'),
        sa.Column('annual_value', sa.Numeric(15, 2), default=0),
        sa.Column('annual_velocity', sa.Integer, default=0),
        sa.Column('cumulative_value_percent', sa.Numeric(5, 2), default=0),
        sa.Column('cumulative_velocity_percent', sa.Numeric(5, 2), default=0),
        sa.Column('count_frequency', sa.String(20)),
        sa.Column('last_count_date', sa.Date),
        sa.Column('next_count_date', sa.Date),
        sa.Column('times_counted_ytd', sa.Integer, default=0),
        sa.Column('accuracy_rate', sa.Numeric(5, 2)),
        sa.Column('variance_history', postgresql.JSONB),
        sa.Column('calculated_at', sa.DateTime, default=sa.func.now()),
        sa.Column('created_at', sa.DateTime, default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, default=sa.func.now(), onupdate=sa.func.now()),
        schema='public'
    )
    op.create_unique_constraint('uq_abc_product', 'abc_classifications', ['tenant_id', 'warehouse_id', 'product_id'], schema='public')
    op.create_index('idx_abc_tenant_warehouse', 'abc_classifications', ['tenant_id', 'warehouse_id'], schema='public')
    op.create_index('idx_abc_class', 'abc_classifications', ['tenant_id', 'abc_class'], schema='public')


def downgrade() -> None:
    op.drop_table('abc_classifications', schema='public')
    op.drop_table('inventory_variances', schema='public')
    op.drop_table('count_details', schema='public')
    op.drop_table('count_tasks', schema='public')
    op.drop_table('count_schedules', schema='public')
    op.drop_table('count_sessions', schema='public')
    op.drop_table('cycle_count_plans', schema='public')
