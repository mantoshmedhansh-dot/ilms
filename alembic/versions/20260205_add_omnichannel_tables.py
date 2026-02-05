"""Add Omnichannel tables - Phase 3: BOPIS/BORIS & Ship-from-Store

Revision ID: 20260205_omnichannel
Revises: 20260205_wms_adv
Create Date: 2026-02-05

Tables created:
- store_locations: Physical retail store locations
- bopis_orders: Buy Online, Pick up In Store orders
- ship_from_store_orders: Ship-from-store fulfillment
- store_inventory_reservations: Store inventory reservations
- store_returns: In-store returns (BORIS)
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '20260205_omnichannel'
down_revision = '20260205_wms_adv'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # =========================================================================
    # STORE_LOCATIONS - Physical Retail Stores
    # =========================================================================
    op.create_table(
        'store_locations',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False, index=True),

        # Identification
        sa.Column('store_code', sa.String(30), nullable=False, index=True),
        sa.Column('name', sa.String(200), nullable=False),
        sa.Column('store_type', sa.String(30), default='STANDARD', nullable=False),
        sa.Column('status', sa.String(30), default='ACTIVE', nullable=False, index=True),

        # Link to warehouse
        sa.Column('warehouse_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('warehouses.id', ondelete='SET NULL'), nullable=True),

        # Contact
        sa.Column('phone', sa.String(20), nullable=True),
        sa.Column('email', sa.String(100), nullable=True),
        sa.Column('manager_name', sa.String(100), nullable=True),
        sa.Column('manager_phone', sa.String(20), nullable=True),

        # Address
        sa.Column('address_line1', sa.String(255), nullable=False),
        sa.Column('address_line2', sa.String(255), nullable=True),
        sa.Column('city', sa.String(100), nullable=False, index=True),
        sa.Column('state', sa.String(100), nullable=False),
        sa.Column('pincode', sa.String(10), nullable=False, index=True),
        sa.Column('country', sa.String(50), default='India', nullable=False),

        # Geo
        sa.Column('latitude', sa.Numeric(10, 7), nullable=True),
        sa.Column('longitude', sa.Numeric(10, 7), nullable=True),

        # Hours
        sa.Column('operating_hours', postgresql.JSONB, nullable=True),
        sa.Column('holiday_schedule', postgresql.JSONB, nullable=True),

        # Capabilities
        sa.Column('bopis_enabled', sa.Boolean, default=False),
        sa.Column('ship_from_store_enabled', sa.Boolean, default=False),
        sa.Column('boris_enabled', sa.Boolean, default=False),
        sa.Column('endless_aisle_enabled', sa.Boolean, default=False),

        # Pickup Options
        sa.Column('curbside_pickup', sa.Boolean, default=False),
        sa.Column('locker_pickup', sa.Boolean, default=False),
        sa.Column('drive_thru', sa.Boolean, default=False),

        # BOPIS Settings
        sa.Column('bopis_prep_time_minutes', sa.Integer, default=120),
        sa.Column('bopis_pickup_window_hours', sa.Integer, default=72),
        sa.Column('bopis_max_items', sa.Integer, nullable=True),

        # SFS Settings
        sa.Column('sfs_max_orders_per_day', sa.Integer, nullable=True),
        sa.Column('sfs_priority', sa.Integer, default=50),
        sa.Column('sfs_serviceable_pincodes', postgresql.JSONB, nullable=True),

        # Performance
        sa.Column('avg_bopis_prep_time_minutes', sa.Integer, nullable=True),
        sa.Column('bopis_completion_rate', sa.Numeric(5, 2), nullable=True),
        sa.Column('sfs_completion_rate', sa.Numeric(5, 2), nullable=True),
        sa.Column('customer_rating', sa.Numeric(3, 2), nullable=True),

        # Timestamps
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_index('ix_store_locations_geo', 'store_locations', ['latitude', 'longitude'])
    op.create_index('ix_store_locations_pincode', 'store_locations', ['pincode'])
    op.create_unique_constraint('uq_store_code', 'store_locations', ['tenant_id', 'store_code'])

    # =========================================================================
    # BOPIS_ORDERS - Buy Online, Pick up In Store
    # =========================================================================
    op.create_table(
        'bopis_orders',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False, index=True),

        # References
        sa.Column('order_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('orders.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('store_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('store_locations.id', ondelete='RESTRICT'), nullable=False, index=True),
        sa.Column('customer_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('customers.id', ondelete='RESTRICT'), nullable=False, index=True),

        # Status
        sa.Column('status', sa.String(30), default='PENDING', nullable=False, index=True),

        # Pickup Details
        sa.Column('pickup_code', sa.String(20), nullable=False, unique=True, index=True),
        sa.Column('pickup_location_type', sa.String(30), default='IN_STORE', nullable=False),
        sa.Column('pickup_instructions', sa.Text, nullable=True),

        # Timing
        sa.Column('estimated_ready_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('actual_ready_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('pickup_deadline', sa.DateTime(timezone=True), nullable=True),
        sa.Column('picked_up_at', sa.DateTime(timezone=True), nullable=True),

        # Notifications
        sa.Column('ready_notification_sent', sa.Boolean, default=False),
        sa.Column('ready_notification_sent_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('reminder_sent', sa.Boolean, default=False),
        sa.Column('reminder_sent_at', sa.DateTime(timezone=True), nullable=True),

        # Items
        sa.Column('items', postgresql.JSONB, nullable=True),
        sa.Column('total_items', sa.Integer, default=0),
        sa.Column('picked_items', sa.Integer, default=0),

        # Pickup Person
        sa.Column('picked_up_by_name', sa.String(100), nullable=True),
        sa.Column('picked_up_by_phone', sa.String(20), nullable=True),
        sa.Column('id_verification_type', sa.String(50), nullable=True),
        sa.Column('id_verification_number', sa.String(50), nullable=True),

        # Staff
        sa.Column('assigned_to', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('picked_by', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('handed_over_by', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),

        # Storage
        sa.Column('storage_location', sa.String(50), nullable=True),

        # Cancellation
        sa.Column('cancelled_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('cancellation_reason', sa.Text, nullable=True),
        sa.Column('cancelled_by', postgresql.UUID(as_uuid=True), nullable=True),

        # Timestamps
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), index=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('notes', sa.Text, nullable=True),
    )

    op.create_index('ix_bopis_orders_store_status', 'bopis_orders', ['store_id', 'status'])
    op.create_index('ix_bopis_orders_pickup_code', 'bopis_orders', ['pickup_code'])

    # =========================================================================
    # SHIP_FROM_STORE_ORDERS - Ship-from-Store Fulfillment
    # =========================================================================
    op.create_table(
        'ship_from_store_orders',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False, index=True),

        # References
        sa.Column('order_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('orders.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('store_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('store_locations.id', ondelete='RESTRICT'), nullable=False, index=True),

        # Status
        sa.Column('status', sa.String(30), default='PENDING', nullable=False, index=True),
        sa.Column('sfs_number', sa.String(30), nullable=False, unique=True, index=True),

        # Items
        sa.Column('items', postgresql.JSONB, nullable=True),
        sa.Column('total_items', sa.Integer, default=0),
        sa.Column('picked_items', sa.Integer, default=0),
        sa.Column('packed_items', sa.Integer, default=0),

        # Shipping
        sa.Column('shipping_address', postgresql.JSONB, nullable=True),
        sa.Column('carrier_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('tracking_number', sa.String(100), nullable=True),
        sa.Column('shipment_id', postgresql.UUID(as_uuid=True), nullable=True),

        # Staff
        sa.Column('accepted_by', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('picked_by', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('packed_by', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('shipped_by', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),

        # Rejection
        sa.Column('rejection_reason', sa.Text, nullable=True),
        sa.Column('rejected_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('rejected_at', sa.DateTime(timezone=True), nullable=True),

        # Timing
        sa.Column('accepted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('picking_started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('packed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('shipped_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('delivered_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('sla_deadline', sa.DateTime(timezone=True), nullable=True),

        # Timestamps
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), index=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('notes', sa.Text, nullable=True),
    )

    op.create_index('ix_sfs_orders_store_status', 'ship_from_store_orders', ['store_id', 'status'])

    # =========================================================================
    # STORE_INVENTORY_RESERVATIONS - Store Inventory Reservations
    # =========================================================================
    op.create_table(
        'store_inventory_reservations',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False, index=True),

        # Store and Product
        sa.Column('store_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('store_locations.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('product_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('products.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('variant_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('sku', sa.String(100), nullable=True),

        # Quantity
        sa.Column('quantity_reserved', sa.Integer, default=0),
        sa.Column('quantity_fulfilled', sa.Integer, default=0),
        sa.Column('quantity_released', sa.Integer, default=0),

        # Type
        sa.Column('reservation_type', sa.String(30), nullable=False),

        # References
        sa.Column('order_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('orders.id', ondelete='SET NULL'), nullable=True),
        sa.Column('bopis_order_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('bopis_orders.id', ondelete='SET NULL'), nullable=True),
        sa.Column('sfs_order_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('ship_from_store_orders.id', ondelete='SET NULL'), nullable=True),

        # Status
        sa.Column('is_active', sa.Boolean, default=True),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),

        # Timestamps
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('fulfilled_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('released_at', sa.DateTime(timezone=True), nullable=True),
    )

    op.create_index('ix_store_reservations_product', 'store_inventory_reservations', ['store_id', 'product_id'])

    # =========================================================================
    # STORE_RETURNS - In-store Returns (BORIS)
    # =========================================================================
    op.create_table(
        'store_returns',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False, index=True),

        # Return Number
        sa.Column('return_number', sa.String(30), nullable=False, unique=True, index=True),

        # References
        sa.Column('order_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('orders.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('store_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('store_locations.id', ondelete='RESTRICT'), nullable=False, index=True),
        sa.Column('customer_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('customers.id', ondelete='RESTRICT'), nullable=False, index=True),

        # Original Order
        sa.Column('original_channel', sa.String(50), nullable=True),

        # Status
        sa.Column('status', sa.String(30), default='INITIATED', nullable=False, index=True),

        # Items
        sa.Column('items', postgresql.JSONB, nullable=True),
        sa.Column('total_items', sa.Integer, default=0),
        sa.Column('inspected_items', sa.Integer, default=0),
        sa.Column('approved_items', sa.Integer, default=0),
        sa.Column('rejected_items', sa.Integer, default=0),

        # Reason
        sa.Column('return_reason', sa.String(100), nullable=True),
        sa.Column('return_comments', sa.Text, nullable=True),

        # Refund
        sa.Column('refund_amount', sa.Numeric(12, 2), default=0),
        sa.Column('refund_method', sa.String(50), nullable=True),
        sa.Column('refund_transaction_id', sa.String(100), nullable=True),
        sa.Column('refunded_at', sa.DateTime(timezone=True), nullable=True),

        # Inspection
        sa.Column('inspection_notes', sa.Text, nullable=True),
        sa.Column('item_condition', sa.String(50), nullable=True),

        # Staff
        sa.Column('received_by', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('inspected_by', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('approved_by', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),

        # Restocking
        sa.Column('restock_decision', sa.String(30), nullable=True),
        sa.Column('restocked_at', sa.DateTime(timezone=True), nullable=True),

        # Scheduling
        sa.Column('scheduled_date', sa.Date, nullable=True),
        sa.Column('scheduled_time_slot', sa.String(50), nullable=True),

        # Timestamps
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), index=True),
        sa.Column('received_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('inspected_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('notes', sa.Text, nullable=True),
    )

    op.create_index('ix_store_returns_status', 'store_returns', ['store_id', 'status'])


def downgrade() -> None:
    # Drop tables in reverse order
    op.drop_table('store_returns')
    op.drop_table('store_inventory_reservations')
    op.drop_table('ship_from_store_orders')
    op.drop_table('bopis_orders')
    op.drop_table('store_locations')
