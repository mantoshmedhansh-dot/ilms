"""Add DOM (Distributed Order Management) tables

Revision ID: dom_foundation_001
Revises:
Create Date: 2026-02-05

Tables created:
- fulfillment_nodes: Unified abstraction for warehouses, stores, dealers, 3PLs
- routing_rules: Rule-based order routing configuration
- order_splits: Track order splits across multiple nodes
- orchestration_logs: Audit trail for routing decisions
- backorders: Capture demand for out-of-stock items
- preorders: Pre-order management for upcoming products
- global_inventory_views: Materialized inventory across all nodes
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB


# revision identifiers, used by Alembic.
revision = 'dom_foundation_001'
down_revision = 'community_partner_001'
branch_labels = None
depends_on = None


def upgrade():
    # Check if tables already exist (for idempotent migrations)
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    existing_tables = inspector.get_table_names()

    # 1. Fulfillment Nodes Table
    if 'fulfillment_nodes' not in existing_tables:
        op.create_table(
            'fulfillment_nodes',
            sa.Column('id', UUID(as_uuid=True), primary_key=True),
            sa.Column('tenant_id', UUID(as_uuid=True), nullable=False),

            # Basic Info
            sa.Column('code', sa.String(50), nullable=False),
            sa.Column('name', sa.String(200), nullable=False),
            sa.Column('node_type', sa.String(50), nullable=False),  # WAREHOUSE, STORE, DEALER, 3PL, DROPSHIP, VIRTUAL

            # Location
            sa.Column('address_line1', sa.String(500), nullable=True),
            sa.Column('address_line2', sa.String(500), nullable=True),
            sa.Column('city', sa.String(100), nullable=True),
            sa.Column('state', sa.String(100), nullable=True),
            sa.Column('country', sa.String(100), default='India'),
            sa.Column('pincode', sa.String(10), nullable=True),
            sa.Column('latitude', sa.Numeric(10, 7), nullable=True),
            sa.Column('longitude', sa.Numeric(10, 7), nullable=True),

            # Capacity & Priority
            sa.Column('priority', sa.Integer(), default=100),
            sa.Column('max_daily_orders', sa.Integer(), nullable=True),
            sa.Column('current_daily_orders', sa.Integer(), default=0),
            sa.Column('max_concurrent_picks', sa.Integer(), default=10),

            # Fulfillment Capabilities
            sa.Column('supports_cod', sa.Boolean(), default=True),
            sa.Column('supports_prepaid', sa.Boolean(), default=True),
            sa.Column('supports_same_day', sa.Boolean(), default=False),
            sa.Column('supports_next_day', sa.Boolean(), default=True),
            sa.Column('supports_b2b', sa.Boolean(), default=True),
            sa.Column('supports_d2c', sa.Boolean(), default=True),
            sa.Column('supports_marketplace', sa.Boolean(), default=True),
            sa.Column('supports_bopis', sa.Boolean(), default=False),  # Buy Online Pick In Store
            sa.Column('supports_ship_from_store', sa.Boolean(), default=False),

            # Cost Factors
            sa.Column('base_shipping_cost', sa.Numeric(10, 2), default=0),
            sa.Column('cost_per_km', sa.Numeric(10, 4), default=0),
            sa.Column('handling_cost_per_unit', sa.Numeric(10, 2), default=0),

            # SLA Configuration
            sa.Column('processing_time_hours', sa.Integer(), default=24),
            sa.Column('cutoff_time', sa.Time(), nullable=True),

            # Operating Hours
            sa.Column('operating_hours', JSONB, nullable=True),  # {"mon": {"start": "09:00", "end": "18:00"}, ...}

            # Status
            sa.Column('is_active', sa.Boolean(), default=True),
            sa.Column('is_accepting_orders', sa.Boolean(), default=True),

            # Reference to existing entities
            sa.Column('warehouse_id', UUID(as_uuid=True), sa.ForeignKey('warehouses.id'), nullable=True),
            sa.Column('dealer_id', UUID(as_uuid=True), sa.ForeignKey('dealers.id'), nullable=True),
            sa.Column('franchisee_id', UUID(as_uuid=True), sa.ForeignKey('franchisees.id'), nullable=True),

            # Contact
            sa.Column('contact_name', sa.String(200), nullable=True),
            sa.Column('contact_phone', sa.String(20), nullable=True),
            sa.Column('contact_email', sa.String(255), nullable=True),

            # Metadata
            sa.Column('metadata', JSONB, nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()')),
            sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()')),
            sa.Column('created_by', UUID(as_uuid=True), nullable=True),
        )
        # Create indexes
        op.create_index('ix_fulfillment_nodes_tenant_id', 'fulfillment_nodes', ['tenant_id'])
        op.create_index('ix_fulfillment_nodes_code', 'fulfillment_nodes', ['code'])
        op.create_index('ix_fulfillment_nodes_node_type', 'fulfillment_nodes', ['node_type'])
        op.create_index('ix_fulfillment_nodes_is_active', 'fulfillment_nodes', ['is_active'])
        op.create_index('ix_fulfillment_nodes_pincode', 'fulfillment_nodes', ['pincode'])
        op.create_unique_constraint('uq_fulfillment_nodes_tenant_code', 'fulfillment_nodes', ['tenant_id', 'code'])
        print("Created table: fulfillment_nodes")

    # 2. Routing Rules Table
    if 'routing_rules' not in existing_tables:
        op.create_table(
            'routing_rules',
            sa.Column('id', UUID(as_uuid=True), primary_key=True),
            sa.Column('tenant_id', UUID(as_uuid=True), nullable=False),

            # Rule Configuration
            sa.Column('name', sa.String(200), nullable=False),
            sa.Column('description', sa.Text(), nullable=True),
            sa.Column('priority', sa.Integer(), default=100),  # Lower = higher priority

            # Routing Strategy
            sa.Column('strategy', sa.String(50), nullable=False),  # NEAREST, CHEAPEST, FASTEST, PRIORITY, ROUND_ROBIN, INVENTORY_BASED, CUSTOM

            # Conditions (when this rule applies)
            sa.Column('conditions', JSONB, nullable=False),  # {"channels": [...], "pincodes": [...], "categories": [...], "min_order_value": 1000, ...}

            # Actions (what to do when matched)
            sa.Column('actions', JSONB, nullable=False),  # {"preferred_nodes": [...], "excluded_nodes": [...], "split_allowed": true, ...}

            # Node Selection Weights
            sa.Column('distance_weight', sa.Numeric(3, 2), default=0.4),
            sa.Column('cost_weight', sa.Numeric(3, 2), default=0.3),
            sa.Column('sla_weight', sa.Numeric(3, 2), default=0.2),
            sa.Column('inventory_weight', sa.Numeric(3, 2), default=0.1),

            # Status
            sa.Column('is_active', sa.Boolean(), default=True),
            sa.Column('effective_from', sa.DateTime(timezone=True), nullable=True),
            sa.Column('effective_to', sa.DateTime(timezone=True), nullable=True),

            # Metadata
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()')),
            sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()')),
            sa.Column('created_by', UUID(as_uuid=True), nullable=True),
        )
        op.create_index('ix_routing_rules_tenant_id', 'routing_rules', ['tenant_id'])
        op.create_index('ix_routing_rules_priority', 'routing_rules', ['priority'])
        op.create_index('ix_routing_rules_is_active', 'routing_rules', ['is_active'])
        print("Created table: routing_rules")

    # 3. Order Splits Table
    if 'order_splits' not in existing_tables:
        op.create_table(
            'order_splits',
            sa.Column('id', UUID(as_uuid=True), primary_key=True),
            sa.Column('tenant_id', UUID(as_uuid=True), nullable=False),

            # Order Reference
            sa.Column('parent_order_id', UUID(as_uuid=True), sa.ForeignKey('orders.id'), nullable=False),
            sa.Column('split_number', sa.Integer(), nullable=False),  # 1, 2, 3...

            # Fulfillment Node
            sa.Column('fulfillment_node_id', UUID(as_uuid=True), sa.ForeignKey('fulfillment_nodes.id'), nullable=False),

            # Split Reason
            sa.Column('split_reason', sa.String(50), nullable=False),  # INVENTORY_SPLIT, LOCATION_SPLIT, CAPACITY_SPLIT, MANUAL_SPLIT

            # Items in this split
            sa.Column('line_items', JSONB, nullable=False),  # [{"product_id": "...", "variant_id": "...", "quantity": 2}, ...]

            # Split Values
            sa.Column('subtotal', sa.Numeric(18, 2), nullable=False),
            sa.Column('shipping_cost', sa.Numeric(10, 2), default=0),
            sa.Column('handling_cost', sa.Numeric(10, 2), default=0),
            sa.Column('total', sa.Numeric(18, 2), nullable=False),

            # Status
            sa.Column('status', sa.String(50), default='PENDING'),  # PENDING, ALLOCATED, PICKING, PACKED, SHIPPED, DELIVERED, CANCELLED

            # Shipment Reference
            sa.Column('shipment_id', UUID(as_uuid=True), sa.ForeignKey('shipments.id'), nullable=True),

            # Timestamps
            sa.Column('allocated_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('picked_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('packed_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('shipped_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('delivered_at', sa.DateTime(timezone=True), nullable=True),

            # Metadata
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()')),
            sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()')),
        )
        op.create_index('ix_order_splits_tenant_id', 'order_splits', ['tenant_id'])
        op.create_index('ix_order_splits_parent_order_id', 'order_splits', ['parent_order_id'])
        op.create_index('ix_order_splits_fulfillment_node_id', 'order_splits', ['fulfillment_node_id'])
        op.create_index('ix_order_splits_status', 'order_splits', ['status'])
        op.create_unique_constraint('uq_order_splits_order_number', 'order_splits', ['parent_order_id', 'split_number'])
        print("Created table: order_splits")

    # 4. Orchestration Logs Table
    if 'orchestration_logs' not in existing_tables:
        op.create_table(
            'orchestration_logs',
            sa.Column('id', UUID(as_uuid=True), primary_key=True),
            sa.Column('tenant_id', UUID(as_uuid=True), nullable=False),

            # Order Reference
            sa.Column('order_id', UUID(as_uuid=True), sa.ForeignKey('orders.id'), nullable=False),

            # Routing Decision
            sa.Column('status', sa.String(50), nullable=False),  # ROUTED, SPLIT, BACKORDERED, MANUAL_REVIEW, FAILED
            sa.Column('routing_rule_id', UUID(as_uuid=True), sa.ForeignKey('routing_rules.id'), nullable=True),

            # Selected Nodes
            sa.Column('selected_nodes', JSONB, nullable=True),  # [{"node_id": "...", "score": 85.5, "items": [...]}, ...]

            # Decision Details
            sa.Column('decision_reason', sa.Text(), nullable=True),
            sa.Column('node_scores', JSONB, nullable=True),  # Detailed scoring for audit
            sa.Column('processing_time_ms', sa.Integer(), nullable=True),

            # Failure Info
            sa.Column('failure_reason', sa.Text(), nullable=True),
            sa.Column('retry_count', sa.Integer(), default=0),

            # Timestamps
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()')),
            sa.Column('processed_by', UUID(as_uuid=True), nullable=True),
        )
        op.create_index('ix_orchestration_logs_tenant_id', 'orchestration_logs', ['tenant_id'])
        op.create_index('ix_orchestration_logs_order_id', 'orchestration_logs', ['order_id'])
        op.create_index('ix_orchestration_logs_status', 'orchestration_logs', ['status'])
        op.create_index('ix_orchestration_logs_created_at', 'orchestration_logs', ['created_at'])
        print("Created table: orchestration_logs")

    # 5. Backorders Table
    if 'backorders' not in existing_tables:
        op.create_table(
            'backorders',
            sa.Column('id', UUID(as_uuid=True), primary_key=True),
            sa.Column('tenant_id', UUID(as_uuid=True), nullable=False),

            # Order Reference
            sa.Column('order_id', UUID(as_uuid=True), sa.ForeignKey('orders.id'), nullable=False),
            sa.Column('order_item_id', UUID(as_uuid=True), nullable=True),  # Specific line item

            # Product
            sa.Column('product_id', UUID(as_uuid=True), sa.ForeignKey('products.id'), nullable=False),
            sa.Column('variant_id', UUID(as_uuid=True), nullable=True),
            sa.Column('quantity', sa.Integer(), nullable=False),

            # Customer
            sa.Column('customer_id', UUID(as_uuid=True), sa.ForeignKey('customers.id'), nullable=True),

            # Status
            sa.Column('status', sa.String(50), default='PENDING'),  # PENDING, NOTIFIED, FULFILLED, CANCELLED, EXPIRED

            # Expected Availability
            sa.Column('expected_date', sa.Date(), nullable=True),
            sa.Column('expected_node_id', UUID(as_uuid=True), sa.ForeignKey('fulfillment_nodes.id'), nullable=True),

            # Customer Communication
            sa.Column('customer_notified', sa.Boolean(), default=False),
            sa.Column('notification_sent_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('customer_response', sa.String(50), nullable=True),  # WAIT, CANCEL, PARTIAL

            # Priority
            sa.Column('priority', sa.Integer(), default=100),

            # Timestamps
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()')),
            sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()')),
            sa.Column('fulfilled_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),

            # Notes
            sa.Column('notes', sa.Text(), nullable=True),
        )
        op.create_index('ix_backorders_tenant_id', 'backorders', ['tenant_id'])
        op.create_index('ix_backorders_order_id', 'backorders', ['order_id'])
        op.create_index('ix_backorders_product_id', 'backorders', ['product_id'])
        op.create_index('ix_backorders_status', 'backorders', ['status'])
        op.create_index('ix_backorders_expected_date', 'backorders', ['expected_date'])
        print("Created table: backorders")

    # 6. Preorders Table
    if 'preorders' not in existing_tables:
        op.create_table(
            'preorders',
            sa.Column('id', UUID(as_uuid=True), primary_key=True),
            sa.Column('tenant_id', UUID(as_uuid=True), nullable=False),

            # Product
            sa.Column('product_id', UUID(as_uuid=True), sa.ForeignKey('products.id'), nullable=False),
            sa.Column('variant_id', UUID(as_uuid=True), nullable=True),

            # Pre-order Configuration
            sa.Column('name', sa.String(200), nullable=False),
            sa.Column('description', sa.Text(), nullable=True),

            # Dates
            sa.Column('preorder_start', sa.DateTime(timezone=True), nullable=False),
            sa.Column('preorder_end', sa.DateTime(timezone=True), nullable=False),
            sa.Column('expected_ship_date', sa.Date(), nullable=False),

            # Inventory & Limits
            sa.Column('max_quantity', sa.Integer(), nullable=True),  # Total allowed pre-orders
            sa.Column('current_quantity', sa.Integer(), default=0),  # Current pre-order count
            sa.Column('max_per_customer', sa.Integer(), default=1),

            # Pricing
            sa.Column('deposit_required', sa.Boolean(), default=False),
            sa.Column('deposit_amount', sa.Numeric(10, 2), nullable=True),
            sa.Column('deposit_percentage', sa.Numeric(5, 2), nullable=True),
            sa.Column('preorder_price', sa.Numeric(18, 2), nullable=True),  # Special pre-order price

            # Fulfillment
            sa.Column('preferred_node_id', UUID(as_uuid=True), sa.ForeignKey('fulfillment_nodes.id'), nullable=True),

            # Status
            sa.Column('status', sa.String(50), default='DRAFT'),  # DRAFT, ACTIVE, SOLD_OUT, CLOSED, CANCELLED
            sa.Column('is_active', sa.Boolean(), default=True),

            # Timestamps
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()')),
            sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()')),
            sa.Column('created_by', UUID(as_uuid=True), nullable=True),
        )
        op.create_index('ix_preorders_tenant_id', 'preorders', ['tenant_id'])
        op.create_index('ix_preorders_product_id', 'preorders', ['product_id'])
        op.create_index('ix_preorders_status', 'preorders', ['status'])
        op.create_index('ix_preorders_preorder_start', 'preorders', ['preorder_start'])
        op.create_index('ix_preorders_preorder_end', 'preorders', ['preorder_end'])
        print("Created table: preorders")

    # 7. Global Inventory Views Table (Materialized View Cache)
    if 'global_inventory_views' not in existing_tables:
        op.create_table(
            'global_inventory_views',
            sa.Column('id', UUID(as_uuid=True), primary_key=True),
            sa.Column('tenant_id', UUID(as_uuid=True), nullable=False),

            # Product
            sa.Column('product_id', UUID(as_uuid=True), sa.ForeignKey('products.id'), nullable=False),
            sa.Column('variant_id', UUID(as_uuid=True), nullable=True),
            sa.Column('sku', sa.String(100), nullable=True),

            # Node
            sa.Column('node_id', UUID(as_uuid=True), sa.ForeignKey('fulfillment_nodes.id'), nullable=False),
            sa.Column('node_type', sa.String(50), nullable=True),

            # Stock Levels
            sa.Column('available_quantity', sa.Integer(), default=0),
            sa.Column('reserved_quantity', sa.Integer(), default=0),  # Allocated but not shipped
            sa.Column('on_hand_quantity', sa.Integer(), default=0),
            sa.Column('incoming_quantity', sa.Integer(), default=0),  # Expected from POs

            # ATP/ATF
            sa.Column('atp_quantity', sa.Integer(), default=0),  # Available to Promise
            sa.Column('atf_quantity', sa.Integer(), default=0),  # Available to Fulfill

            # Thresholds
            sa.Column('safety_stock', sa.Integer(), default=0),
            sa.Column('reorder_point', sa.Integer(), default=0),

            # Last Updated
            sa.Column('last_sync_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()')),
            sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()')),
        )
        op.create_index('ix_global_inventory_views_tenant_id', 'global_inventory_views', ['tenant_id'])
        op.create_index('ix_global_inventory_views_product_id', 'global_inventory_views', ['product_id'])
        op.create_index('ix_global_inventory_views_node_id', 'global_inventory_views', ['node_id'])
        op.create_index('ix_global_inventory_views_sku', 'global_inventory_views', ['sku'])
        op.create_unique_constraint('uq_global_inventory_product_node', 'global_inventory_views', ['tenant_id', 'product_id', 'variant_id', 'node_id'])
        print("Created table: global_inventory_views")


def downgrade():
    # Drop tables in reverse order of dependencies
    op.drop_table('global_inventory_views')
    op.drop_table('preorders')
    op.drop_table('backorders')
    op.drop_table('orchestration_logs')
    op.drop_table('order_splits')
    op.drop_table('routing_rules')
    op.drop_table('fulfillment_nodes')
