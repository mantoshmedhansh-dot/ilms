"""Add Labor Management tables - Phase 4: Workforce Optimization

Revision ID: 20260205_labor
Revises: 20260205_omnichannel
Create Date: 2026-02-05

Tables created:
- warehouse_workers: Worker profiles with skills and certifications
- work_shifts: Shift scheduling and time tracking
- labor_standards: Engineered labor standards
- productivity_metrics: Daily productivity rollups
- leave_requests: Worker leave management
- shift_templates: Reusable shift templates
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '20260205_labor'
down_revision = '20260205_omnichannel'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # =========================================================================
    # WAREHOUSE_WORKERS - Worker Profiles
    # =========================================================================
    op.create_table(
        'warehouse_workers',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False, index=True),

        # Link to user
        sa.Column('user_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True, index=True),

        # Employee Info
        sa.Column('employee_code', sa.String(30), nullable=False, index=True),
        sa.Column('first_name', sa.String(100), nullable=False),
        sa.Column('last_name', sa.String(100), nullable=False),
        sa.Column('email', sa.String(100), nullable=True),
        sa.Column('phone', sa.String(20), nullable=True),

        # Employment
        sa.Column('worker_type', sa.String(30), default='FULL_TIME', nullable=False),
        sa.Column('status', sa.String(30), default='ACTIVE', nullable=False, index=True),
        sa.Column('hire_date', sa.Date, nullable=False),
        sa.Column('termination_date', sa.Date, nullable=True),

        # Assignment
        sa.Column('primary_warehouse_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('warehouses.id', ondelete='RESTRICT'), nullable=False, index=True),
        sa.Column('primary_zone_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('warehouse_zones.id', ondelete='SET NULL'), nullable=True),
        sa.Column('supervisor_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('warehouse_workers.id', ondelete='SET NULL'), nullable=True),

        # Skills
        sa.Column('skills', postgresql.JSONB, nullable=True),
        sa.Column('certifications', postgresql.JSONB, nullable=True),
        sa.Column('equipment_certified', postgresql.JSONB, nullable=True),

        # Preferences
        sa.Column('preferred_shift', sa.String(30), nullable=True),
        sa.Column('max_hours_per_week', sa.Integer, default=40),
        sa.Column('can_work_overtime', sa.Boolean, default=True),
        sa.Column('can_work_weekends', sa.Boolean, default=True),

        # Pay
        sa.Column('hourly_rate', sa.Numeric(10, 2), default=0),
        sa.Column('overtime_multiplier', sa.Numeric(3, 2), default=1.5),

        # Performance
        sa.Column('avg_picks_per_hour', sa.Numeric(10, 2), nullable=True),
        sa.Column('avg_units_per_hour', sa.Numeric(10, 2), nullable=True),
        sa.Column('accuracy_rate', sa.Numeric(5, 2), nullable=True),
        sa.Column('productivity_score', sa.Numeric(5, 2), nullable=True),

        # Attendance
        sa.Column('attendance_rate', sa.Numeric(5, 2), nullable=True),
        sa.Column('tardiness_count_ytd', sa.Integer, default=0),
        sa.Column('absence_count_ytd', sa.Integer, default=0),

        # Leave Balances
        sa.Column('annual_leave_balance', sa.Numeric(5, 2), default=0),
        sa.Column('sick_leave_balance', sa.Numeric(5, 2), default=0),
        sa.Column('casual_leave_balance', sa.Numeric(5, 2), default=0),

        # Notes
        sa.Column('notes', sa.Text, nullable=True),

        # Timestamps
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_unique_constraint('uq_worker_employee_code', 'warehouse_workers',
                                ['tenant_id', 'employee_code'])
    op.create_index('ix_warehouse_workers_status', 'warehouse_workers', ['status'])

    # =========================================================================
    # SHIFT_TEMPLATES - Reusable Shift Templates
    # =========================================================================
    op.create_table(
        'shift_templates',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False, index=True),

        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('shift_type', sa.String(30), nullable=False),

        sa.Column('warehouse_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('warehouses.id', ondelete='CASCADE'), nullable=False, index=True),

        sa.Column('start_time', sa.Time, nullable=False),
        sa.Column('end_time', sa.Time, nullable=False),
        sa.Column('break_duration_minutes', sa.Integer, default=30),

        sa.Column('days_of_week', postgresql.JSONB, nullable=False),

        sa.Column('min_workers', sa.Integer, default=1),
        sa.Column('max_workers', sa.Integer, default=10),
        sa.Column('ideal_workers', sa.Integer, default=5),

        sa.Column('is_active', sa.Boolean, default=True),
        sa.Column('notes', sa.Text, nullable=True),

        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # =========================================================================
    # WORK_SHIFTS - Shift Scheduling
    # =========================================================================
    op.create_table(
        'work_shifts',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False, index=True),

        # Worker
        sa.Column('worker_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('warehouse_workers.id', ondelete='CASCADE'), nullable=False, index=True),

        # Warehouse
        sa.Column('warehouse_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('warehouses.id', ondelete='CASCADE'), nullable=False, index=True),

        # Shift Details
        sa.Column('shift_date', sa.Date, nullable=False, index=True),
        sa.Column('shift_type', sa.String(30), nullable=False),
        sa.Column('status', sa.String(30), default='SCHEDULED', nullable=False),

        # Scheduled Time
        sa.Column('scheduled_start', sa.Time, nullable=False),
        sa.Column('scheduled_end', sa.Time, nullable=False),
        sa.Column('scheduled_break_minutes', sa.Integer, default=30),

        # Actual Time
        sa.Column('actual_start', sa.DateTime(timezone=True), nullable=True),
        sa.Column('actual_end', sa.DateTime(timezone=True), nullable=True),
        sa.Column('actual_break_minutes', sa.Integer, nullable=True),

        # Assignment
        sa.Column('assigned_zone_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('warehouse_zones.id', ondelete='SET NULL'), nullable=True),
        sa.Column('assigned_function', sa.String(50), nullable=True),
        sa.Column('supervisor_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('warehouse_workers.id', ondelete='SET NULL'), nullable=True),

        # Performance
        sa.Column('tasks_completed', sa.Integer, default=0),
        sa.Column('units_processed', sa.Integer, default=0),
        sa.Column('errors_count', sa.Integer, default=0),

        # Time Breakdown
        sa.Column('productive_minutes', sa.Integer, nullable=True),
        sa.Column('idle_minutes', sa.Integer, nullable=True),
        sa.Column('travel_minutes', sa.Integer, nullable=True),

        # Overtime
        sa.Column('is_overtime', sa.Boolean, default=False),
        sa.Column('overtime_hours', sa.Numeric(4, 2), default=0),
        sa.Column('overtime_approved_by', postgresql.UUID(as_uuid=True), nullable=True),

        # Notes
        sa.Column('notes', sa.Text, nullable=True),
        sa.Column('no_show_reason', sa.Text, nullable=True),

        # Timestamps
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_index('ix_work_shifts_date', 'work_shifts', ['shift_date'])
    op.create_index('ix_work_shifts_worker', 'work_shifts', ['worker_id', 'shift_date'])

    # =========================================================================
    # LABOR_STANDARDS - Engineered Labor Standards
    # =========================================================================
    op.create_table(
        'labor_standards',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False, index=True),

        sa.Column('warehouse_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('warehouses.id', ondelete='CASCADE'), nullable=False, index=True),

        sa.Column('function', sa.String(50), nullable=False),
        sa.Column('zone_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('warehouse_zones.id', ondelete='SET NULL'), nullable=True),

        # Rates
        sa.Column('units_per_hour', sa.Numeric(10, 2), nullable=False),
        sa.Column('lines_per_hour', sa.Numeric(10, 2), nullable=True),
        sa.Column('orders_per_hour', sa.Numeric(10, 2), nullable=True),

        # Time Components
        sa.Column('travel_time_per_pick', sa.Integer, default=15),
        sa.Column('pick_time_per_unit', sa.Integer, default=5),
        sa.Column('setup_time', sa.Integer, default=60),

        # Thresholds
        sa.Column('threshold_minimum', sa.Numeric(5, 2), default=70),
        sa.Column('threshold_target', sa.Numeric(5, 2), default=100),
        sa.Column('threshold_excellent', sa.Numeric(5, 2), default=120),

        # Effective Period
        sa.Column('effective_from', sa.Date, nullable=False),
        sa.Column('effective_to', sa.Date, nullable=True),
        sa.Column('is_active', sa.Boolean, default=True),

        sa.Column('notes', sa.Text, nullable=True),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=True),

        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_unique_constraint('uq_labor_standard', 'labor_standards',
                                ['tenant_id', 'warehouse_id', 'function', 'zone_id'])

    # =========================================================================
    # PRODUCTIVITY_METRICS - Daily Productivity Rollups
    # =========================================================================
    op.create_table(
        'productivity_metrics',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False, index=True),

        sa.Column('worker_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('warehouse_workers.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('warehouse_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('warehouses.id', ondelete='CASCADE'), nullable=False, index=True),

        sa.Column('metric_date', sa.Date, nullable=False, index=True),
        sa.Column('function', sa.String(50), nullable=False),

        # Time
        sa.Column('hours_worked', sa.Numeric(5, 2), default=0),
        sa.Column('productive_hours', sa.Numeric(5, 2), default=0),
        sa.Column('idle_hours', sa.Numeric(5, 2), default=0),

        # Volume
        sa.Column('units_processed', sa.Integer, default=0),
        sa.Column('lines_processed', sa.Integer, default=0),
        sa.Column('orders_processed', sa.Integer, default=0),
        sa.Column('tasks_completed', sa.Integer, default=0),

        # Rates
        sa.Column('units_per_hour', sa.Numeric(10, 2), default=0),
        sa.Column('lines_per_hour', sa.Numeric(10, 2), default=0),

        # Performance
        sa.Column('standard_units_per_hour', sa.Numeric(10, 2), default=0),
        sa.Column('performance_percentage', sa.Numeric(6, 2), default=0),

        # Quality
        sa.Column('errors_count', sa.Integer, default=0),
        sa.Column('accuracy_rate', sa.Numeric(5, 2), default=100),

        # Cost
        sa.Column('labor_cost', sa.Numeric(12, 2), default=0),
        sa.Column('cost_per_unit', sa.Numeric(10, 4), default=0),

        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_unique_constraint('uq_productivity_metric', 'productivity_metrics',
                                ['tenant_id', 'worker_id', 'metric_date', 'function'])
    op.create_index('ix_productivity_metrics_date', 'productivity_metrics', ['metric_date'])

    # =========================================================================
    # LEAVE_REQUESTS - Worker Leave Management
    # =========================================================================
    op.create_table(
        'warehouse_leave_requests',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False, index=True),

        sa.Column('worker_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('warehouse_workers.id', ondelete='CASCADE'), nullable=False, index=True),

        sa.Column('leave_type', sa.String(30), nullable=False),
        sa.Column('status', sa.String(30), default='PENDING', nullable=False),

        sa.Column('start_date', sa.Date, nullable=False),
        sa.Column('end_date', sa.Date, nullable=False),
        sa.Column('days_requested', sa.Numeric(4, 1), nullable=False),

        sa.Column('reason', sa.Text, nullable=True),

        sa.Column('approved_by', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('warehouse_workers.id', ondelete='SET NULL'), nullable=True),
        sa.Column('approved_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('rejection_reason', sa.Text, nullable=True),

        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_index('ix_warehouse_leave_requests_worker', 'warehouse_leave_requests', ['worker_id', 'start_date'])


def downgrade() -> None:
    # Drop tables in reverse order
    op.drop_table('warehouse_leave_requests')
    op.drop_table('productivity_metrics')
    op.drop_table('labor_standards')
    op.drop_table('work_shifts')
    op.drop_table('shift_templates')
    op.drop_table('warehouse_workers')
