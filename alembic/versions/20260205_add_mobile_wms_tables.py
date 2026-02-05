"""Add Mobile WMS tables - Phase 5: RF Scanner & Mobile Operations

Revision ID: 20260205_mobile_wms
Revises: 20260205_labor
Create Date: 2026-02-05

Tables created:
- mobile_devices: RF scanner and mobile device registration
- mobile_scan_logs: Barcode scan logging for audit
- mobile_task_queues: Worker-specific task queues
- pick_confirmations: Mobile pick confirmations with validation
- offline_sync_queue: Offline data synchronization
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '20260205_mobile_wms'
down_revision = '20260205_labor'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # =========================================================================
    # MOBILE_DEVICES - RF Scanner & Mobile Device Registration
    # =========================================================================
    op.create_table(
        'mobile_devices',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False, index=True),

        # Device Identification
        sa.Column('device_code', sa.String(50), nullable=False, index=True),
        sa.Column('device_name', sa.String(100), nullable=False),
        sa.Column('device_type', sa.String(30), default='RF_SCANNER', nullable=False),
        sa.Column('status', sa.String(30), default='ACTIVE', nullable=False, index=True),

        # Hardware Info
        sa.Column('manufacturer', sa.String(100), nullable=True),
        sa.Column('model', sa.String(100), nullable=True),
        sa.Column('serial_number', sa.String(100), nullable=True),
        sa.Column('imei', sa.String(50), nullable=True),
        sa.Column('mac_address', sa.String(50), nullable=True),

        # Software Info
        sa.Column('os_version', sa.String(50), nullable=True),
        sa.Column('app_version', sa.String(50), nullable=True),
        sa.Column('firmware_version', sa.String(50), nullable=True),

        # Assignment
        sa.Column('warehouse_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('warehouses.id', ondelete='SET NULL'), nullable=True, index=True),
        sa.Column('assigned_to', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('assigned_at', sa.DateTime(timezone=True), nullable=True),

        # Configuration
        sa.Column('config', postgresql.JSONB, nullable=True),
        sa.Column('scan_settings', postgresql.JSONB, nullable=True),

        # Battery
        sa.Column('battery_level', sa.Integer, nullable=True),
        sa.Column('last_battery_update', sa.DateTime(timezone=True), nullable=True),

        # Connectivity
        sa.Column('is_online', sa.Boolean, default=False),
        sa.Column('last_heartbeat', sa.DateTime(timezone=True), nullable=True),
        sa.Column('ip_address', sa.String(50), nullable=True),

        # Usage Stats
        sa.Column('total_scans', sa.Integer, default=0),
        sa.Column('scans_today', sa.Integer, default=0),
        sa.Column('last_scan_at', sa.DateTime(timezone=True), nullable=True),

        # Maintenance
        sa.Column('last_maintenance_date', sa.Date, nullable=True),
        sa.Column('next_maintenance_date', sa.Date, nullable=True),
        sa.Column('maintenance_notes', sa.Text, nullable=True),

        # Notes
        sa.Column('notes', sa.Text, nullable=True),

        # Timestamps
        sa.Column('registered_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_unique_constraint('uq_device_code', 'mobile_devices',
                                ['tenant_id', 'device_code'])
    op.create_index('ix_mobile_devices_status', 'mobile_devices', ['status'])

    # =========================================================================
    # MOBILE_SCAN_LOGS - Barcode Scan Logging
    # =========================================================================
    op.create_table(
        'mobile_scan_logs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False, index=True),

        # Device
        sa.Column('device_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('mobile_devices.id', ondelete='CASCADE'), nullable=False, index=True),

        # User
        sa.Column('user_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True, index=True),

        # Scan Details
        sa.Column('barcode', sa.String(255), nullable=False, index=True),
        sa.Column('scan_type', sa.String(30), nullable=False),
        sa.Column('scan_result', sa.String(30), default='VALID', nullable=False),

        # Context
        sa.Column('warehouse_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('warehouses.id', ondelete='SET NULL'), nullable=True),
        sa.Column('zone_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('warehouse_zones.id', ondelete='SET NULL'), nullable=True),
        sa.Column('bin_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('warehouse_bins.id', ondelete='SET NULL'), nullable=True),

        # Referenced Entities
        sa.Column('task_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('picklist_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('product_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('products.id', ondelete='SET NULL'), nullable=True),

        # Expected vs Actual
        sa.Column('expected_value', sa.String(255), nullable=True),
        sa.Column('is_match', sa.Boolean, nullable=True),

        # Location
        sa.Column('gps_latitude', sa.Numeric(10, 7), nullable=True),
        sa.Column('gps_longitude', sa.Numeric(10, 7), nullable=True),

        # Error Details
        sa.Column('error_message', sa.Text, nullable=True),

        # Offline Handling
        sa.Column('is_offline_scan', sa.Boolean, default=False),
        sa.Column('offline_created_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('sync_status', sa.String(30), default='SYNCED', nullable=False),
        sa.Column('synced_at', sa.DateTime(timezone=True), nullable=True),

        # Timestamp
        sa.Column('scanned_at', sa.DateTime(timezone=True), server_default=sa.func.now(), index=True),
    )

    op.create_index('ix_mobile_scan_logs_timestamp', 'mobile_scan_logs', ['scanned_at'])
    op.create_index('ix_mobile_scan_logs_device', 'mobile_scan_logs', ['device_id', 'scanned_at'])
    op.create_index('ix_mobile_scan_logs_barcode', 'mobile_scan_logs', ['barcode'])

    # =========================================================================
    # MOBILE_TASK_QUEUES - Worker-Specific Task Queues
    # =========================================================================
    op.create_table(
        'mobile_task_queues',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False, index=True),

        # Worker
        sa.Column('worker_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True),

        # Device
        sa.Column('device_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('mobile_devices.id', ondelete='SET NULL'), nullable=True),

        # Warehouse
        sa.Column('warehouse_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('warehouses.id', ondelete='CASCADE'), nullable=False, index=True),

        # Task Reference
        sa.Column('task_id', postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column('task_type', sa.String(30), nullable=False),

        # Priority and Order
        sa.Column('priority', sa.Integer, default=50, index=True),
        sa.Column('sequence', sa.Integer, default=0),

        # Status
        sa.Column('status', sa.String(30), default='QUEUED', nullable=False, index=True),

        # Task Details (denormalized for mobile efficiency)
        sa.Column('task_summary', postgresql.JSONB, nullable=True),

        # Location
        sa.Column('source_bin_code', sa.String(100), nullable=True),
        sa.Column('destination_bin_code', sa.String(100), nullable=True),

        # Product (for pick tasks)
        sa.Column('sku', sa.String(100), nullable=True),
        sa.Column('product_name', sa.String(255), nullable=True),
        sa.Column('quantity_required', sa.Integer, default=0),
        sa.Column('quantity_completed', sa.Integer, default=0),

        # Timing
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('skipped_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('skip_reason', sa.String(200), nullable=True),

        # Offline Handling
        sa.Column('is_offline_task', sa.Boolean, default=False),
        sa.Column('sync_status', sa.String(30), default='SYNCED', nullable=False),

        # Timestamps
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_index('ix_mobile_task_queue_worker', 'mobile_task_queues', ['worker_id', 'status'])
    op.create_index('ix_mobile_task_queue_priority', 'mobile_task_queues', ['priority', 'created_at'])

    # =========================================================================
    # PICK_CONFIRMATIONS - Mobile Pick Confirmations
    # =========================================================================
    op.create_table(
        'pick_confirmations',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False, index=True),

        # Task Reference
        sa.Column('task_id', postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column('picklist_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('picklist_item_id', postgresql.UUID(as_uuid=True), nullable=True),

        # Device and User
        sa.Column('device_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('mobile_devices.id', ondelete='SET NULL'), nullable=True, index=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True, index=True),

        # Location
        sa.Column('warehouse_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('warehouses.id', ondelete='CASCADE'), nullable=False),
        sa.Column('bin_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('warehouse_bins.id', ondelete='SET NULL'), nullable=True),
        sa.Column('bin_code', sa.String(100), nullable=True),

        # Product
        sa.Column('product_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('products.id', ondelete='SET NULL'), nullable=True),
        sa.Column('sku', sa.String(100), nullable=False),

        # Quantities
        sa.Column('quantity_required', sa.Integer, nullable=False),
        sa.Column('quantity_confirmed', sa.Integer, nullable=False),
        sa.Column('quantity_short', sa.Integer, default=0),

        # Status
        sa.Column('status', sa.String(30), default='CONFIRMED', nullable=False),
        sa.Column('short_reason', sa.String(200), nullable=True),

        # Barcode Validation
        sa.Column('bin_barcode_scanned', sa.String(255), nullable=True),
        sa.Column('bin_scan_valid', sa.Boolean, default=True),
        sa.Column('product_barcode_scanned', sa.String(255), nullable=True),
        sa.Column('product_scan_valid', sa.Boolean, default=True),

        # Serial Numbers (if applicable)
        sa.Column('serial_numbers', postgresql.JSONB, nullable=True),
        sa.Column('lot_numbers', postgresql.JSONB, nullable=True),

        # Substitution
        sa.Column('is_substitution', sa.Boolean, default=False),
        sa.Column('original_sku', sa.String(100), nullable=True),
        sa.Column('substitution_reason', sa.String(200), nullable=True),

        # Offline Handling
        sa.Column('is_offline_confirmation', sa.Boolean, default=False),
        sa.Column('offline_created_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('sync_status', sa.String(30), default='SYNCED', nullable=False),

        # Notes
        sa.Column('notes', sa.Text, nullable=True),

        # Timestamps
        sa.Column('confirmed_at', sa.DateTime(timezone=True), server_default=sa.func.now(), index=True),
    )

    op.create_index('ix_pick_confirmations_task', 'pick_confirmations', ['task_id'])
    op.create_index('ix_pick_confirmations_time', 'pick_confirmations', ['confirmed_at'])

    # =========================================================================
    # OFFLINE_SYNC_QUEUE - Offline Data Synchronization
    # =========================================================================
    op.create_table(
        'offline_sync_queue',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False, index=True),

        # Device
        sa.Column('device_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('mobile_devices.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),

        # Sync Item
        sa.Column('entity_type', sa.String(50), nullable=False),
        sa.Column('entity_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('operation', sa.String(20), nullable=False),

        # Payload
        sa.Column('payload', postgresql.JSONB, nullable=False),

        # Status
        sa.Column('status', sa.String(30), default='PENDING', nullable=False, index=True),
        sa.Column('retry_count', sa.Integer, default=0),
        sa.Column('max_retries', sa.Integer, default=3),
        sa.Column('last_error', sa.Text, nullable=True),

        # Timestamps
        sa.Column('offline_created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('synced_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('failed_at', sa.DateTime(timezone=True), nullable=True),
    )

    op.create_index('ix_offline_sync_device', 'offline_sync_queue', ['device_id', 'status'])
    op.create_index('ix_offline_sync_created', 'offline_sync_queue', ['created_at'])


def downgrade() -> None:
    # Drop tables in reverse order
    op.drop_table('offline_sync_queue')
    op.drop_table('pick_confirmations')
    op.drop_table('mobile_task_queues')
    op.drop_table('mobile_scan_logs')
    op.drop_table('mobile_devices')
