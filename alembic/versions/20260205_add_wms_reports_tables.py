"""Add WMS reports tables

Revision ID: 20260205_wms_reports
Revises: 20260205_cycle_count
Create Date: 2026-02-05

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '20260205_wms_reports'
down_revision: Union[str, None] = '20260205_cycle_count'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Report Definitions
    op.create_table(
        'report_definitions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('tenants.id'), nullable=False),
        sa.Column('report_code', sa.String(50), nullable=False),
        sa.Column('report_name', sa.String(200), nullable=False),
        sa.Column('description', sa.Text),
        sa.Column('category', sa.String(30), nullable=False, default='operations'),
        sa.Column('report_type', sa.String(20), nullable=False, default='summary'),
        sa.Column('data_source', sa.String(100), nullable=False),
        sa.Column('base_query', sa.Text),
        sa.Column('filters', postgresql.JSONB),
        sa.Column('parameters', postgresql.JSONB),
        sa.Column('group_by', postgresql.JSONB),
        sa.Column('order_by', postgresql.JSONB),
        sa.Column('columns', postgresql.JSONB, nullable=False),
        sa.Column('calculated_fields', postgresql.JSONB),
        sa.Column('aggregations', postgresql.JSONB),
        sa.Column('default_format', sa.String(10), nullable=False, default='excel'),
        sa.Column('available_formats', postgresql.JSONB, default=['pdf', 'excel', 'csv']),
        sa.Column('page_size', sa.String(10), default='A4'),
        sa.Column('orientation', sa.String(10), default='portrait'),
        sa.Column('header_template', sa.Text),
        sa.Column('footer_template', sa.Text),
        sa.Column('include_charts', sa.Boolean, default=False),
        sa.Column('chart_config', postgresql.JSONB),
        sa.Column('is_public', sa.Boolean, default=False),
        sa.Column('roles', postgresql.JSONB),
        sa.Column('warehouse_ids', postgresql.JSONB),
        sa.Column('is_active', sa.Boolean, default=True),
        sa.Column('is_system', sa.Boolean, default=False),
        sa.Column('created_by', postgresql.UUID(as_uuid=True)),
        sa.Column('created_at', sa.DateTime, default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, default=sa.func.now(), onupdate=sa.func.now()),
        schema='public'
    )
    op.create_index('idx_rd_tenant_category', 'report_definitions', ['tenant_id', 'category'], schema='public')
    op.create_index('idx_rd_active', 'report_definitions', ['tenant_id', 'is_active'], schema='public')

    # Report Schedules
    op.create_table(
        'report_schedules',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('tenants.id'), nullable=False),
        sa.Column('report_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('report_definitions.id'), nullable=False),
        sa.Column('schedule_name', sa.String(200), nullable=False),
        sa.Column('frequency', sa.String(20), nullable=False, default='daily'),
        sa.Column('cron_expression', sa.String(100)),
        sa.Column('run_time', sa.String(10), default='06:00'),
        sa.Column('day_of_week', sa.Integer),
        sa.Column('day_of_month', sa.Integer),
        sa.Column('timezone', sa.String(50), default='Asia/Kolkata'),
        sa.Column('parameters', postgresql.JSONB),
        sa.Column('output_format', sa.String(10), nullable=False, default='excel'),
        sa.Column('date_range', sa.String(30), default='yesterday'),
        sa.Column('email_to', postgresql.JSONB),
        sa.Column('email_cc', postgresql.JSONB),
        sa.Column('email_subject', sa.String(200)),
        sa.Column('email_body', sa.Text),
        sa.Column('upload_to_sftp', sa.Boolean, default=False),
        sa.Column('sftp_config', postgresql.JSONB),
        sa.Column('webhook_url', sa.String(500)),
        sa.Column('is_active', sa.Boolean, default=True),
        sa.Column('last_run_at', sa.DateTime),
        sa.Column('last_run_status', sa.String(20)),
        sa.Column('next_run_at', sa.DateTime),
        sa.Column('consecutive_failures', sa.Integer, default=0),
        sa.Column('created_by', postgresql.UUID(as_uuid=True)),
        sa.Column('created_at', sa.DateTime, default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, default=sa.func.now(), onupdate=sa.func.now()),
        schema='public'
    )
    op.create_index('idx_rs_tenant_report', 'report_schedules', ['tenant_id', 'report_id'], schema='public')
    op.create_index('idx_rs_next_run', 'report_schedules', ['tenant_id', 'next_run_at'], schema='public')

    # Report Executions
    op.create_table(
        'report_executions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('tenants.id'), nullable=False),
        sa.Column('report_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('report_definitions.id'), nullable=False),
        sa.Column('schedule_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('report_schedules.id')),
        sa.Column('execution_number', sa.String(50), nullable=False),
        sa.Column('output_format', sa.String(10), nullable=False),
        sa.Column('parameters', postgresql.JSONB),
        sa.Column('date_range_start', sa.Date),
        sa.Column('date_range_end', sa.Date),
        sa.Column('started_at', sa.DateTime, default=sa.func.now()),
        sa.Column('completed_at', sa.DateTime),
        sa.Column('duration_seconds', sa.Integer),
        sa.Column('status', sa.String(20), nullable=False, default='pending'),
        sa.Column('row_count', sa.Integer, default=0),
        sa.Column('file_size_bytes', sa.Integer, default=0),
        sa.Column('file_url', sa.String(500)),
        sa.Column('file_name', sa.String(200)),
        sa.Column('emailed_to', postgresql.JSONB),
        sa.Column('emailed_at', sa.DateTime),
        sa.Column('email_status', sa.String(20)),
        sa.Column('error_message', sa.Text),
        sa.Column('error_details', postgresql.JSONB),
        sa.Column('triggered_by', sa.String(20), default='manual'),
        sa.Column('run_by', postgresql.UUID(as_uuid=True)),
        sa.Column('created_at', sa.DateTime, default=sa.func.now()),
        schema='public'
    )
    op.create_index('idx_re_tenant_report', 'report_executions', ['tenant_id', 'report_id'], schema='public')
    op.create_index('idx_re_status', 'report_executions', ['tenant_id', 'status'], schema='public')
    op.create_index('idx_re_date', 'report_executions', ['tenant_id', 'started_at'], schema='public')

    # KPI Definitions
    op.create_table(
        'kpi_definitions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('tenants.id'), nullable=False),
        sa.Column('warehouse_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('warehouses.id')),
        sa.Column('kpi_code', sa.String(50), nullable=False),
        sa.Column('kpi_name', sa.String(200), nullable=False),
        sa.Column('description', sa.Text),
        sa.Column('category', sa.String(30), nullable=False, default='fulfillment'),
        sa.Column('data_source', sa.String(100), nullable=False),
        sa.Column('calculation_formula', sa.Text, nullable=False),
        sa.Column('aggregation_type', sa.String(20), default='sum'),
        sa.Column('unit', sa.String(20), default='count'),
        sa.Column('decimal_places', sa.Integer, default=2),
        sa.Column('target_value', sa.Numeric(15, 4)),
        sa.Column('warning_threshold', sa.Numeric(15, 4)),
        sa.Column('critical_threshold', sa.Numeric(15, 4)),
        sa.Column('higher_is_better', sa.Boolean, default=True),
        sa.Column('industry_benchmark', sa.Numeric(15, 4)),
        sa.Column('internal_benchmark', sa.Numeric(15, 4)),
        sa.Column('display_order', sa.Integer, default=0),
        sa.Column('show_on_dashboard', sa.Boolean, default=True),
        sa.Column('chart_type', sa.String(20)),
        sa.Column('is_active', sa.Boolean, default=True),
        sa.Column('is_system', sa.Boolean, default=False),
        sa.Column('created_by', postgresql.UUID(as_uuid=True)),
        sa.Column('created_at', sa.DateTime, default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, default=sa.func.now(), onupdate=sa.func.now()),
        schema='public'
    )
    op.create_index('idx_kpi_tenant_category', 'kpi_definitions', ['tenant_id', 'category'], schema='public')
    op.create_index('idx_kpi_active', 'kpi_definitions', ['tenant_id', 'is_active'], schema='public')

    # KPI Snapshots
    op.create_table(
        'kpi_snapshots',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('tenants.id'), nullable=False),
        sa.Column('kpi_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('kpi_definitions.id'), nullable=False),
        sa.Column('warehouse_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('warehouses.id')),
        sa.Column('snapshot_date', sa.Date, nullable=False),
        sa.Column('period_type', sa.String(20), nullable=False, default='daily'),
        sa.Column('current_value', sa.Numeric(15, 4), nullable=False),
        sa.Column('previous_value', sa.Numeric(15, 4)),
        sa.Column('target_value', sa.Numeric(15, 4)),
        sa.Column('change_value', sa.Numeric(15, 4), default=0),
        sa.Column('change_percent', sa.Numeric(8, 4), default=0),
        sa.Column('trend_direction', sa.String(10), nullable=False, default='stable'),
        sa.Column('is_on_target', sa.Boolean, default=True),
        sa.Column('is_warning', sa.Boolean, default=False),
        sa.Column('is_critical', sa.Boolean, default=False),
        sa.Column('data_points', sa.Integer, default=0),
        sa.Column('breakdown', postgresql.JSONB),
        sa.Column('created_at', sa.DateTime, default=sa.func.now()),
        schema='public'
    )
    op.create_index('idx_kpis_tenant_kpi', 'kpi_snapshots', ['tenant_id', 'kpi_id'], schema='public')
    op.create_index('idx_kpis_date', 'kpi_snapshots', ['tenant_id', 'snapshot_date'], schema='public')
    op.create_unique_constraint('uq_kpi_snapshot', 'kpi_snapshots',
                               ['tenant_id', 'kpi_id', 'warehouse_id', 'snapshot_date', 'period_type'],
                               schema='public')

    # Inventory Snapshots
    op.create_table(
        'inventory_snapshots',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('tenants.id'), nullable=False),
        sa.Column('warehouse_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('warehouses.id'), nullable=False),
        sa.Column('product_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('products.id'), nullable=False),
        sa.Column('snapshot_date', sa.Date, nullable=False),
        sa.Column('on_hand_qty', sa.Numeric(15, 3), default=0),
        sa.Column('available_qty', sa.Numeric(15, 3), default=0),
        sa.Column('reserved_qty', sa.Numeric(15, 3), default=0),
        sa.Column('in_transit_qty', sa.Numeric(15, 3), default=0),
        sa.Column('backorder_qty', sa.Numeric(15, 3), default=0),
        sa.Column('unit_cost', sa.Numeric(15, 4), default=0),
        sa.Column('total_value', sa.Numeric(15, 2), default=0),
        sa.Column('received_qty', sa.Numeric(15, 3), default=0),
        sa.Column('shipped_qty', sa.Numeric(15, 3), default=0),
        sa.Column('adjusted_qty', sa.Numeric(15, 3), default=0),
        sa.Column('returned_qty', sa.Numeric(15, 3), default=0),
        sa.Column('days_of_supply', sa.Integer),
        sa.Column('turn_rate', sa.Numeric(8, 4)),
        sa.Column('abc_class', sa.String(1)),
        sa.Column('created_at', sa.DateTime, default=sa.func.now()),
        schema='public'
    )
    op.create_index('idx_invs_tenant_date', 'inventory_snapshots', ['tenant_id', 'snapshot_date'], schema='public')
    op.create_index('idx_invs_warehouse', 'inventory_snapshots', ['tenant_id', 'warehouse_id', 'snapshot_date'], schema='public')
    op.create_unique_constraint('uq_inventory_snapshot', 'inventory_snapshots',
                               ['tenant_id', 'warehouse_id', 'product_id', 'snapshot_date'],
                               schema='public')

    # Operations Snapshots
    op.create_table(
        'operations_snapshots',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('tenants.id'), nullable=False),
        sa.Column('warehouse_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('warehouses.id'), nullable=False),
        sa.Column('snapshot_date', sa.Date, nullable=False),
        # Receiving
        sa.Column('receipts_count', sa.Integer, default=0),
        sa.Column('units_received', sa.Integer, default=0),
        sa.Column('receiving_accuracy', sa.Numeric(5, 2)),
        sa.Column('avg_putaway_time_mins', sa.Numeric(8, 2)),
        # Picking
        sa.Column('orders_picked', sa.Integer, default=0),
        sa.Column('lines_picked', sa.Integer, default=0),
        sa.Column('units_picked', sa.Integer, default=0),
        sa.Column('picks_per_hour', sa.Numeric(8, 2)),
        sa.Column('picking_accuracy', sa.Numeric(5, 2)),
        # Packing
        sa.Column('orders_packed', sa.Integer, default=0),
        sa.Column('packages_created', sa.Integer, default=0),
        sa.Column('packing_accuracy', sa.Numeric(5, 2)),
        # Shipping
        sa.Column('shipments_created', sa.Integer, default=0),
        sa.Column('units_shipped', sa.Integer, default=0),
        sa.Column('on_time_shipment_rate', sa.Numeric(5, 2)),
        sa.Column('same_day_ship_rate', sa.Numeric(5, 2)),
        # Returns
        sa.Column('returns_received', sa.Integer, default=0),
        sa.Column('returns_processed', sa.Integer, default=0),
        sa.Column('return_rate', sa.Numeric(5, 2)),
        # Quality
        sa.Column('qc_passed', sa.Integer, default=0),
        sa.Column('qc_failed', sa.Integer, default=0),
        sa.Column('defect_rate', sa.Numeric(5, 2)),
        # Labor
        sa.Column('total_labor_hours', sa.Numeric(10, 2), default=0),
        sa.Column('productive_hours', sa.Numeric(10, 2), default=0),
        sa.Column('labor_utilization', sa.Numeric(5, 2)),
        # Capacity
        sa.Column('storage_utilization', sa.Numeric(5, 2)),
        sa.Column('dock_utilization', sa.Numeric(5, 2)),
        # Costs
        sa.Column('cost_per_order', sa.Numeric(10, 2)),
        sa.Column('cost_per_line', sa.Numeric(10, 2)),
        sa.Column('cost_per_unit', sa.Numeric(10, 4)),
        sa.Column('created_at', sa.DateTime, default=sa.func.now()),
        schema='public'
    )
    op.create_index('idx_ops_tenant_date', 'operations_snapshots', ['tenant_id', 'snapshot_date'], schema='public')
    op.create_index('idx_ops_warehouse', 'operations_snapshots', ['tenant_id', 'warehouse_id', 'snapshot_date'], schema='public')
    op.create_unique_constraint('uq_operations_snapshot', 'operations_snapshots',
                               ['tenant_id', 'warehouse_id', 'snapshot_date'],
                               schema='public')

    # Dashboard Widgets
    op.create_table(
        'dashboard_widgets',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('tenants.id'), nullable=False),
        sa.Column('dashboard_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('widget_type', sa.String(30), nullable=False),
        sa.Column('title', sa.String(200), nullable=False),
        sa.Column('data_source', sa.String(100), nullable=False),
        sa.Column('kpi_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('kpi_definitions.id')),
        sa.Column('report_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('report_definitions.id')),
        sa.Column('query', sa.Text),
        sa.Column('parameters', postgresql.JSONB),
        sa.Column('position_x', sa.Integer, default=0),
        sa.Column('position_y', sa.Integer, default=0),
        sa.Column('width', sa.Integer, default=4),
        sa.Column('height', sa.Integer, default=2),
        sa.Column('chart_type', sa.String(30)),
        sa.Column('chart_config', postgresql.JSONB),
        sa.Column('color_scheme', sa.String(30)),
        sa.Column('refresh_interval_seconds', sa.Integer, default=300),
        sa.Column('last_refreshed_at', sa.DateTime),
        sa.Column('is_visible', sa.Boolean, default=True),
        sa.Column('created_at', sa.DateTime, default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, default=sa.func.now(), onupdate=sa.func.now()),
        schema='public'
    )
    op.create_index('idx_dw_tenant_dashboard', 'dashboard_widgets', ['tenant_id', 'dashboard_id'], schema='public')

    # Alert Rules
    op.create_table(
        'alert_rules',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('tenants.id'), nullable=False),
        sa.Column('warehouse_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('warehouses.id')),
        sa.Column('rule_name', sa.String(200), nullable=False),
        sa.Column('description', sa.Text),
        sa.Column('category', sa.String(30), nullable=False),
        sa.Column('kpi_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('kpi_definitions.id')),
        sa.Column('metric', sa.String(100), nullable=False),
        sa.Column('condition', sa.String(20), nullable=False),
        sa.Column('threshold_value', sa.Numeric(15, 4), nullable=False),
        sa.Column('evaluation_window_minutes', sa.Integer, default=60),
        sa.Column('severity', sa.String(20), nullable=False, default='warning'),
        sa.Column('notification_channels', postgresql.JSONB, default=['email']),
        sa.Column('notify_users', postgresql.JSONB),
        sa.Column('notify_emails', postgresql.JSONB),
        sa.Column('cooldown_minutes', sa.Integer, default=60),
        sa.Column('max_alerts_per_day', sa.Integer, default=10),
        sa.Column('last_triggered_at', sa.DateTime),
        sa.Column('triggered_count_today', sa.Integer, default=0),
        sa.Column('is_active', sa.Boolean, default=True),
        sa.Column('created_by', postgresql.UUID(as_uuid=True)),
        sa.Column('created_at', sa.DateTime, default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, default=sa.func.now(), onupdate=sa.func.now()),
        schema='public'
    )
    op.create_index('idx_ar_tenant_active', 'alert_rules', ['tenant_id', 'is_active'], schema='public')


def downgrade() -> None:
    op.drop_table('alert_rules', schema='public')
    op.drop_table('dashboard_widgets', schema='public')
    op.drop_table('operations_snapshots', schema='public')
    op.drop_table('inventory_snapshots', schema='public')
    op.drop_table('kpi_snapshots', schema='public')
    op.drop_table('kpi_definitions', schema='public')
    op.drop_table('report_executions', schema='public')
    op.drop_table('report_schedules', schema='public')
    op.drop_table('report_definitions', schema='public')
