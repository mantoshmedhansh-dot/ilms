"""Add Yard Management tables - Phase 6: Dock Scheduling & Yard Operations

Revision ID: 20260205_yard_mgmt
Revises: 20260205_mobile_wms
Create Date: 2026-02-05

Tables created:
- yard_locations: Yard parking, staging, dock locations
- dock_doors: Dock door configuration and scheduling
- dock_appointments: Carrier appointment scheduling
- yard_moves: Trailer/vehicle movement tracking
- gate_transactions: Gate in/out logging
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '20260205_yard_mgmt'
down_revision = '20260205_mobile_wms'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # =========================================================================
    # YARD_LOCATIONS - Parking, Staging, Dock Areas
    # =========================================================================
    op.create_table(
        'yard_locations',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False, index=True),

        sa.Column('warehouse_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('warehouses.id', ondelete='CASCADE'), nullable=False, index=True),

        # Location Identity
        sa.Column('location_code', sa.String(30), nullable=False, index=True),
        sa.Column('location_name', sa.String(100), nullable=False),
        sa.Column('location_type', sa.String(30), nullable=False, index=True),
        sa.Column('status', sa.String(30), default='AVAILABLE', nullable=False, index=True),

        # Physical Properties
        sa.Column('zone', sa.String(30), nullable=True),
        sa.Column('row', sa.String(10), nullable=True),
        sa.Column('column', sa.String(10), nullable=True),
        sa.Column('level', sa.Integer, nullable=True),

        # Capacity
        sa.Column('max_length_feet', sa.Numeric(6, 1), nullable=True),
        sa.Column('max_width_feet', sa.Numeric(6, 1), nullable=True),
        sa.Column('max_height_feet', sa.Numeric(6, 1), nullable=True),
        sa.Column('max_weight_lbs', sa.Numeric(10, 2), nullable=True),

        # Current Occupancy
        sa.Column('current_vehicle_id', sa.String(50), nullable=True),
        sa.Column('current_vehicle_type', sa.String(30), nullable=True),
        sa.Column('occupied_since', sa.DateTime(timezone=True), nullable=True),

        # GPS Coordinates
        sa.Column('latitude', sa.Numeric(10, 7), nullable=True),
        sa.Column('longitude', sa.Numeric(10, 7), nullable=True),

        # Capabilities
        sa.Column('has_power', sa.Boolean, default=False),
        sa.Column('has_refrigeration', sa.Boolean, default=False),
        sa.Column('has_fuel', sa.Boolean, default=False),
        sa.Column('is_hazmat_approved', sa.Boolean, default=False),

        # Configuration
        sa.Column('is_active', sa.Boolean, default=True),
        sa.Column('sequence', sa.Integer, default=0),
        sa.Column('notes', sa.Text, nullable=True),

        # Timestamps
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_unique_constraint('uq_yard_location_code', 'yard_locations',
                                ['tenant_id', 'warehouse_id', 'location_code'])
    op.create_index('ix_yard_locations_status', 'yard_locations', ['status'])

    # =========================================================================
    # DOCK_DOORS - Dock Door Configuration
    # =========================================================================
    op.create_table(
        'dock_doors',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False, index=True),

        sa.Column('warehouse_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('warehouses.id', ondelete='CASCADE'), nullable=False, index=True),

        sa.Column('yard_location_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('yard_locations.id', ondelete='CASCADE'), nullable=False),

        # Door Identity
        sa.Column('door_number', sa.String(20), nullable=False, index=True),
        sa.Column('door_name', sa.String(100), nullable=False),
        sa.Column('door_type', sa.String(30), default='DUAL', nullable=False),
        sa.Column('status', sa.String(30), default='AVAILABLE', nullable=False, index=True),

        # Physical Properties
        sa.Column('door_height_feet', sa.Numeric(5, 1), nullable=True),
        sa.Column('door_width_feet', sa.Numeric(5, 1), nullable=True),
        sa.Column('dock_height_inches', sa.Integer, nullable=True),

        # Equipment
        sa.Column('has_leveler', sa.Boolean, default=True),
        sa.Column('has_shelter', sa.Boolean, default=True),
        sa.Column('has_restraint', sa.Boolean, default=False),
        sa.Column('has_lights', sa.Boolean, default=True),
        sa.Column('leveler_capacity_lbs', sa.Integer, nullable=True),

        # Linked Zone
        sa.Column('linked_zone_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('warehouse_zones.id', ondelete='SET NULL'), nullable=True),

        # Scheduling
        sa.Column('default_appointment_duration_mins', sa.Integer, default=60),
        sa.Column('max_appointments_per_hour', sa.Integer, default=1),

        # Operating Hours
        sa.Column('operating_start_time', sa.Time, nullable=True),
        sa.Column('operating_end_time', sa.Time, nullable=True),
        sa.Column('operating_days', postgresql.JSONB, nullable=True),

        # Current Assignment
        sa.Column('current_appointment_id', postgresql.UUID(as_uuid=True), nullable=True),

        # Preferences
        sa.Column('preferred_carriers', postgresql.JSONB, nullable=True),
        sa.Column('blocked_carriers', postgresql.JSONB, nullable=True),

        sa.Column('is_active', sa.Boolean, default=True),
        sa.Column('notes', sa.Text, nullable=True),

        # Timestamps
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_unique_constraint('uq_dock_door_number', 'dock_doors',
                                ['tenant_id', 'warehouse_id', 'door_number'])

    # =========================================================================
    # DOCK_APPOINTMENTS - Carrier Appointments
    # =========================================================================
    op.create_table(
        'dock_appointments',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False, index=True),

        sa.Column('warehouse_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('warehouses.id', ondelete='CASCADE'), nullable=False, index=True),

        # Appointment Identity
        sa.Column('appointment_number', sa.String(30), nullable=False, unique=True, index=True),
        sa.Column('appointment_type', sa.String(30), nullable=False),
        sa.Column('status', sa.String(30), default='SCHEDULED', nullable=False, index=True),

        # Scheduling
        sa.Column('appointment_date', sa.Date, nullable=False, index=True),
        sa.Column('scheduled_arrival', sa.Time, nullable=False),
        sa.Column('scheduled_departure', sa.Time, nullable=True),
        sa.Column('duration_minutes', sa.Integer, default=60),

        # Assigned Dock
        sa.Column('dock_door_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('dock_doors.id', ondelete='SET NULL'), nullable=True, index=True),

        # Carrier Info
        sa.Column('transporter_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('transporters.id', ondelete='SET NULL'), nullable=True, index=True),
        sa.Column('carrier_name', sa.String(100), nullable=False),
        sa.Column('carrier_code', sa.String(30), nullable=True),

        # Vehicle/Driver
        sa.Column('driver_name', sa.String(100), nullable=True),
        sa.Column('driver_phone', sa.String(20), nullable=True),
        sa.Column('vehicle_number', sa.String(50), nullable=True),
        sa.Column('trailer_number', sa.String(50), nullable=True),
        sa.Column('vehicle_type', sa.String(30), nullable=True),

        # Shipment Reference
        sa.Column('reference_numbers', postgresql.JSONB, nullable=True),
        sa.Column('shipment_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('purchase_order_id', postgresql.UUID(as_uuid=True), nullable=True),

        # Load Details
        sa.Column('expected_pallets', sa.Integer, nullable=True),
        sa.Column('expected_cases', sa.Integer, nullable=True),
        sa.Column('expected_units', sa.Integer, nullable=True),
        sa.Column('expected_weight_lbs', sa.Numeric(12, 2), nullable=True),

        # Actual Times
        sa.Column('actual_arrival', sa.DateTime(timezone=True), nullable=True),
        sa.Column('check_in_time', sa.DateTime(timezone=True), nullable=True),
        sa.Column('dock_time', sa.DateTime(timezone=True), nullable=True),
        sa.Column('load_start_time', sa.DateTime(timezone=True), nullable=True),
        sa.Column('load_end_time', sa.DateTime(timezone=True), nullable=True),
        sa.Column('departure_time', sa.DateTime(timezone=True), nullable=True),

        # Performance Metrics
        sa.Column('wait_time_minutes', sa.Integer, nullable=True),
        sa.Column('dock_time_minutes', sa.Integer, nullable=True),
        sa.Column('turnaround_time_minutes', sa.Integer, nullable=True),

        # Status Tracking
        sa.Column('is_late', sa.Boolean, default=False),
        sa.Column('late_reason', sa.String(200), nullable=True),
        sa.Column('no_show_reason', sa.String(200), nullable=True),
        sa.Column('cancellation_reason', sa.String(200), nullable=True),

        # Special Instructions
        sa.Column('special_instructions', sa.Text, nullable=True),
        sa.Column('handling_instructions', sa.Text, nullable=True),

        # Audit
        sa.Column('created_by', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('checked_in_by', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),

        sa.Column('notes', sa.Text, nullable=True),

        # Timestamps
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_index('ix_dock_appointments_date', 'dock_appointments', ['appointment_date'])
    op.create_index('ix_dock_appointments_status', 'dock_appointments', ['status'])

    # =========================================================================
    # YARD_MOVES - Trailer/Vehicle Movement
    # =========================================================================
    op.create_table(
        'yard_moves',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False, index=True),

        sa.Column('warehouse_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('warehouses.id', ondelete='CASCADE'), nullable=False, index=True),

        # Move Identity
        sa.Column('move_number', sa.String(30), nullable=False, unique=True, index=True),
        sa.Column('move_type', sa.String(30), nullable=False),
        sa.Column('status', sa.String(30), default='REQUESTED', nullable=False, index=True),
        sa.Column('priority', sa.Integer, default=50),

        # Locations
        sa.Column('from_location_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('yard_locations.id', ondelete='RESTRICT'), nullable=False),
        sa.Column('to_location_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('yard_locations.id', ondelete='RESTRICT'), nullable=False),

        # Vehicle
        sa.Column('vehicle_id', sa.String(50), nullable=False),
        sa.Column('vehicle_type', sa.String(30), nullable=False),

        # Related Appointment
        sa.Column('appointment_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('dock_appointments.id', ondelete='SET NULL'), nullable=True),

        # Assignment
        sa.Column('assigned_to', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('assigned_at', sa.DateTime(timezone=True), nullable=True),

        # Timing
        sa.Column('requested_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('estimated_duration_mins', sa.Integer, default=15),
        sa.Column('actual_duration_mins', sa.Integer, nullable=True),

        # Cancellation
        sa.Column('cancelled_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('cancellation_reason', sa.String(200), nullable=True),

        sa.Column('notes', sa.Text, nullable=True),

        # Timestamps
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_index('ix_yard_moves_status', 'yard_moves', ['status'])
    op.create_index('ix_yard_moves_created', 'yard_moves', ['created_at'])

    # =========================================================================
    # GATE_TRANSACTIONS - Gate In/Out Log
    # =========================================================================
    op.create_table(
        'gate_transactions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False, index=True),

        sa.Column('warehouse_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('warehouses.id', ondelete='CASCADE'), nullable=False, index=True),

        # Transaction Identity
        sa.Column('transaction_number', sa.String(30), nullable=False, unique=True, index=True),
        sa.Column('transaction_type', sa.String(20), nullable=False),

        # Gate Info
        sa.Column('gate_location_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('yard_locations.id', ondelete='SET NULL'), nullable=True),
        sa.Column('gate_name', sa.String(50), nullable=True),

        # Vehicle Info
        sa.Column('vehicle_number', sa.String(50), nullable=False, index=True),
        sa.Column('trailer_number', sa.String(50), nullable=True),
        sa.Column('vehicle_type', sa.String(30), nullable=False),

        # Driver Info
        sa.Column('driver_name', sa.String(100), nullable=True),
        sa.Column('driver_license', sa.String(50), nullable=True),
        sa.Column('driver_phone', sa.String(20), nullable=True),

        # Carrier Info
        sa.Column('carrier_name', sa.String(100), nullable=True),
        sa.Column('transporter_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('transporters.id', ondelete='SET NULL'), nullable=True),

        # Related Appointment
        sa.Column('appointment_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('dock_appointments.id', ondelete='SET NULL'), nullable=True),

        # Assigned Location (on entry)
        sa.Column('assigned_location_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('yard_locations.id', ondelete='SET NULL'), nullable=True),

        # Seal Info
        sa.Column('seal_number', sa.String(50), nullable=True),
        sa.Column('seal_intact', sa.Boolean, nullable=True),
        sa.Column('new_seal_number', sa.String(50), nullable=True),

        # Load Info
        sa.Column('is_loaded', sa.Boolean, nullable=True),
        sa.Column('load_description', sa.String(200), nullable=True),

        # Timing
        sa.Column('transaction_time', sa.DateTime(timezone=True), server_default=sa.func.now(), index=True),

        # Matching Entry (for exit transactions)
        sa.Column('entry_transaction_id', postgresql.UUID(as_uuid=True), nullable=True),

        # Security
        sa.Column('processed_by', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('id_verified', sa.Boolean, default=False),
        sa.Column('inspection_notes', sa.Text, nullable=True),

        # Photo Evidence
        sa.Column('photos', postgresql.JSONB, nullable=True),

        sa.Column('notes', sa.Text, nullable=True),

        # Timestamps
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_index('ix_gate_transactions_time', 'gate_transactions', ['transaction_time'])
    op.create_index('ix_gate_transactions_vehicle', 'gate_transactions', ['vehicle_number'])


def downgrade() -> None:
    # Drop tables in reverse order
    op.drop_table('gate_transactions')
    op.drop_table('yard_moves')
    op.drop_table('dock_appointments')
    op.drop_table('dock_doors')
    op.drop_table('yard_locations')
