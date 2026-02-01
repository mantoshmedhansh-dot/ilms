"""Convert remaining ENUM columns to VARCHAR (Phase 2) to match production schema.

This migration covers tables from Phases 2-6 of the model conversion.
Uses column existence checks to avoid errors on missing columns.

Revision ID: convert_enum_to_varchar_phase2
Revises: convert_enum_to_varchar
Create Date: 2026-01-16

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'convert_enum_to_varchar_phase2'
down_revision = 'convert_enum_to_varchar'
branch_labels = None
depends_on = None


def column_exists(conn, table_name, column_name):
    """Check if a column exists in a table."""
    result = conn.execute(sa.text(f"""
        SELECT EXISTS (
            SELECT 1 FROM information_schema.columns
            WHERE table_name = '{table_name}'
            AND column_name = '{column_name}'
        )
    """))
    return result.scalar()


def table_exists(conn, table_name):
    """Check if a table exists."""
    result = conn.execute(sa.text(f"""
        SELECT EXISTS (
            SELECT 1 FROM information_schema.tables
            WHERE table_name = '{table_name}'
        )
    """))
    return result.scalar()


def get_column_type(conn, table_name, column_name):
    """Get the current data type of a column."""
    result = conn.execute(sa.text(f"""
        SELECT data_type FROM information_schema.columns
        WHERE table_name = '{table_name}'
        AND column_name = '{column_name}'
    """))
    row = result.fetchone()
    return row[0] if row else None


def upgrade() -> None:
    """
    Convert remaining ENUM columns to VARCHAR.
    Also convert JSON to JSONB and TIMESTAMP to TIMESTAMPTZ.
    """
    conn = op.get_bind()

    # ========== ENUM to VARCHAR conversions ==========
    enum_columns = [
        # product.py
        ('products', 'product_type', 50),
        ('products', 'status', 50),
        ('products', 'warranty_type', 50),

        # customer.py
        ('customers', 'customer_type', 50),
        ('customers', 'status', 50),
        ('customer_addresses', 'address_type', 50),

        # lead.py
        ('leads', 'status', 50),
        ('leads', 'source', 50),
        ('leads', 'priority', 50),
        ('lead_activities', 'activity_type', 50),
        ('lead_activities', 'status', 50),

        # shipment.py
        ('shipments', 'status', 50),
        ('shipments', 'carrier_type', 50),

        # inventory.py
        ('stock_items', 'status', 50),
        ('stock_items', 'condition', 50),
        ('stock_movements', 'movement_type', 50),
        ('stock_movements', 'reason', 50),

        # service_request.py
        ('service_requests', 'request_type', 50),
        ('service_requests', 'status', 50),
        ('service_requests', 'priority', 50),
        ('service_requests', 'source', 50),

        # installation.py
        ('installations', 'status', 50),
        ('installations', 'installation_type', 50),

        # amc.py
        ('amc_contracts', 'contract_type', 50),
        ('amc_contracts', 'status', 50),
        ('amc_plans', 'plan_type', 50),

        # purchase.py
        ('purchase_orders', 'status', 50),
        ('purchase_orders', 'po_type', 50),
        ('purchase_order_items', 'item_status', 50),
        ('goods_receipt_notes', 'status', 50),

        # manifest.py
        ('manifests', 'status', 50),
        ('manifests', 'manifest_type', 50),
        ('manifest_items', 'scan_status', 50),

        # picklist.py
        ('picklists', 'status', 50),
        ('picklist_items', 'status', 50),

        # transporter.py
        ('transporters', 'transporter_type', 50),
        ('transporters', 'status', 50),

        # approval.py
        ('approval_requests', 'status', 50),

        # hr.py
        ('employees', 'employment_type', 50),
        ('employees', 'status', 50),
        ('employees', 'gender', 20),
        ('leave_requests', 'leave_type', 50),
        ('leave_requests', 'status', 50),

        # campaign.py
        ('campaigns', 'campaign_type', 50),
        ('campaigns', 'status', 50),
        ('campaigns', 'channel', 50),

        # channel.py
        ('sales_channels', 'channel_type', 50),
        ('sales_channels', 'status', 50),

        # escalation.py
        ('escalations', 'escalation_level', 20),
        ('escalations', 'status', 50),

        # promotion.py
        ('promotions', 'promotion_type', 50),
        ('promotions', 'status', 50),

        # region.py
        ('regions', 'region_type', 50),
        ('regions', 'status', 50),

        # snop.py
        ('demand_forecasts', 'forecast_level', 50),
        ('demand_forecasts', 'granularity', 50),
        ('demand_forecasts', 'algorithm', 50),
        ('demand_forecasts', 'status', 50),
        ('supply_plans', 'status', 50),
        ('snop_scenarios', 'status', 50),
        ('external_factors', 'factor_type', 50),

        # stock_adjustment.py
        ('stock_adjustments', 'adjustment_type', 50),
        ('stock_adjustments', 'status', 50),
        ('inventory_audits', 'status', 50),

        # company.py
        ('companies', 'company_type', 50),
        ('companies', 'gst_registration_type', 50),

        # dealer.py
        ('dealers', 'dealer_type', 50),
        ('dealers', 'status', 50),
        ('dealers', 'tier', 50),
        ('dealers', 'credit_status', 50),
        ('dealer_credit_ledger', 'transaction_type', 50),
        ('dealer_schemes', 'scheme_type', 50),

        # rate_card.py
        ('d2c_rate_cards', 'service_type', 50),
        ('d2c_surcharges', 'surcharge_type', 50),
        ('d2c_surcharges', 'calculation_type', 50),
        ('b2b_rate_cards', 'service_type', 50),
        ('b2b_rate_cards', 'transport_mode', 50),
        ('b2b_rate_cards', 'rate_type', 50),
        ('ftl_rate_cards', 'rate_type', 50),
        ('ftl_vehicle_types', 'vehicle_category', 50),

        # tds.py
        ('tds_deductions', 'section', 20),
        ('tds_deductions', 'status', 50),

        # serviceability.py
        ('warehouse_serviceability', 'channel', 50),
        ('allocation_rules', 'allocation_type', 50),

        # notifications.py
        ('notifications', 'notification_type', 50),
        ('notifications', 'priority', 20),
        ('notification_templates', 'default_priority', 20),

        # franchisee.py
        ('franchisees', 'franchisee_type', 50),
        ('franchisees', 'status', 50),
        ('franchisees', 'tier', 50),
        ('franchisee_contracts', 'status', 50),
        ('franchisee_territories', 'status', 50),
        ('franchisee_trainings', 'training_type', 50),
        ('franchisee_trainings', 'status', 50),
        ('franchisee_support_tickets', 'category', 50),
        ('franchisee_support_tickets', 'priority', 50),
        ('franchisee_support_tickets', 'status', 50),
        ('franchisee_audits', 'audit_type', 50),
        ('franchisee_audits', 'status', 50),
        ('franchisee_audits', 'result', 50),

        # serialization.py
        ('po_serials', 'status', 50),
        ('po_serials', 'item_type', 10),
        ('serial_sequences', 'item_type', 10),
        ('product_serial_sequences', 'item_type', 10),
        ('model_code_references', 'item_type', 10),
    ]

    print("Converting ENUM columns to VARCHAR...")
    for table, column, length in enum_columns:
        if not table_exists(conn, table):
            print(f"  Skipping {table}.{column}: table does not exist")
            continue
        if not column_exists(conn, table, column):
            print(f"  Skipping {table}.{column}: column does not exist")
            continue

        col_type = get_column_type(conn, table, column)
        if col_type and 'character' in col_type:
            print(f"  Skipping {table}.{column}: already VARCHAR")
            continue

        try:
            op.execute(f"""
                ALTER TABLE {table}
                ALTER COLUMN {column} TYPE VARCHAR({length})
                USING {column}::text
            """)
            print(f"  Converted {table}.{column} to VARCHAR({length})")
        except Exception as e:
            print(f"  Error on {table}.{column}: {e}")

    # ========== JSON to JSONB conversions ==========
    json_columns = [
        # customer.py
        ('customers', 'preferences'),

        # lead.py
        ('leads', 'custom_fields'),
        ('leads', 'utm_params'),

        # shipment.py
        ('shipments', 'tracking_details'),
        ('shipment_tracking', 'tracking_data'),

        # service_request.py
        ('service_requests', 'symptoms'),
        ('service_requests', 'diagnostic_data'),

        # installation.py
        ('installations', 'site_survey_data'),
        ('installations', 'photos'),

        # amc.py
        ('amc_contracts', 'covered_services'),

        # purchase.py
        ('purchase_orders', 'delivery_schedule'),

        # manifest.py
        ('manifests', 'route_details'),
        ('manifest_items', 'dimensions'),

        # transporter.py
        ('transporters', 'documents'),

        # hr.py
        ('employees', 'documents'),
        ('employees', 'bank_details'),
        ('employees', 'current_address'),
        ('employees', 'permanent_address'),

        # campaign.py
        ('campaigns', 'target_criteria'),
        ('campaigns', 'content'),

        # channel.py
        ('channel_pricing', 'price_rules'),

        # escalation.py
        ('escalations', 'context_data'),

        # promotion.py
        ('promotions', 'applicable_products'),
        ('promotions', 'applicable_categories'),
        ('promotions', 'rules'),

        # region.py
        ('regions', 'geo_boundary'),

        # snop.py
        ('demand_forecasts', 'forecast_data'),
        ('demand_forecasts', 'model_parameters'),
        ('demand_forecasts', 'external_factors'),
        ('supply_plans', 'schedule_data'),
        ('snop_scenarios', 'assumptions'),
        ('snop_scenarios', 'results'),
        ('external_factors', 'calculation_details'),
        ('snop_meetings', 'participants'),
        ('snop_meetings', 'forecasts_reviewed'),
        ('snop_meetings', 'decisions'),
        ('snop_meetings', 'action_items'),
        ('snop_meetings', 'metadata'),

        # audit_log.py
        ('audit_logs', 'old_values'),
        ('audit_logs', 'new_values'),

        # company.py
        ('companies', 'extra_data'),

        # dealer.py
        ('dealers', 'assigned_pincodes'),
        ('dealers', 'existing_brands'),
        ('dealer_targets', 'applicable_products'),
        ('dealer_targets', 'applicable_categories'),
        ('dealer_schemes', 'rules'),
        ('dealer_schemes', 'applicable_dealer_types'),
        ('dealer_schemes', 'applicable_tiers'),
        ('dealer_schemes', 'applicable_regions'),
        ('dealer_schemes', 'applicable_products'),
        ('dealer_schemes', 'applicable_categories'),

        # notifications.py
        ('notifications', 'extra_data'),
        ('notification_preferences', 'type_preferences'),
        ('notification_templates', 'default_channels'),
        ('notification_templates', 'target_roles'),
        ('notification_templates', 'target_departments'),
        ('announcements', 'channels'),
        ('announcements', 'delivered_at'),

        # franchisee.py
        ('franchisees', 'documents'),
        ('franchisee_territories', 'pincodes'),
        ('franchisee_territories', 'cities'),
        ('franchisee_territories', 'districts'),
        ('franchisee_territories', 'states'),
        ('franchisee_territories', 'geo_boundary'),
        ('franchisee_serviceability', 'service_types'),
        ('franchisee_trainings', 'objectives'),
        ('franchisee_trainings', 'attachments'),
        ('franchisee_support_tickets', 'attachments'),
        ('franchisee_audits', 'checklist'),
        ('franchisee_audits', 'observations'),
        ('franchisee_audits', 'non_conformities'),
        ('franchisee_audits', 'corrective_actions'),
        ('franchisee_audits', 'evidence_urls'),
    ]

    print("\nConverting JSON columns to JSONB...")
    for table, column in json_columns:
        if not table_exists(conn, table):
            print(f"  Skipping {table}.{column}: table does not exist")
            continue
        if not column_exists(conn, table, column):
            print(f"  Skipping {table}.{column}: column does not exist")
            continue

        col_type = get_column_type(conn, table, column)
        if col_type == 'jsonb':
            print(f"  Skipping {table}.{column}: already JSONB")
            continue

        try:
            op.execute(f"""
                ALTER TABLE {table}
                ALTER COLUMN {column} TYPE JSONB
                USING {column}::jsonb
            """)
            print(f"  Converted {table}.{column} to JSONB")
        except Exception as e:
            print(f"  Error on {table}.{column}: {e}")

    # ========== TIMESTAMP to TIMESTAMPTZ conversions ==========
    timestamp_tables = [
        'products', 'product_variants', 'customers', 'customer_addresses',
        'leads', 'lead_activities', 'shipments', 'shipment_tracking',
        'stock_items', 'stock_movements', 'service_requests',
        'installations', 'amc_contracts', 'amc_plans',
        'purchase_orders', 'purchase_order_items', 'goods_receipt_notes',
        'manifests', 'manifest_items', 'picklists', 'picklist_items',
        'transporters', 'approval_requests', 'employees', 'leave_requests',
        'leave_balances', 'campaigns', 'sales_channels', 'channel_pricing',
        'escalations', 'promotions', 'regions',
        'demand_forecasts', 'forecast_adjustments', 'supply_plans',
        'snop_scenarios', 'external_factors', 'inventory_optimizations',
        'snop_meetings', 'stock_adjustments', 'stock_adjustment_items',
        'inventory_audits', 'audit_logs', 'companies', 'company_bank_accounts',
        'dealers', 'dealer_pricing', 'dealer_tier_pricing',
        'dealer_credit_ledger', 'dealer_targets', 'dealer_schemes',
        'dealer_scheme_applications', 'd2c_rate_cards', 'd2c_weight_slabs',
        'd2c_surcharges', 'zone_mappings', 'b2b_rate_cards', 'b2b_rate_slabs',
        'b2b_additional_charges', 'ftl_rate_cards', 'ftl_lane_rates',
        'ftl_additional_charges', 'ftl_vehicle_types', 'carrier_performance',
        'tds_deductions', 'tds_rates', 'form_16a_certificates',
        'warehouse_serviceability', 'allocation_rules', 'allocation_logs',
        'notifications', 'notification_preferences', 'notification_templates',
        'announcements', 'announcement_dismissals',
        'franchisees', 'franchisee_contracts', 'franchisee_territories',
        'franchisee_serviceability', 'franchisee_performance',
        'franchisee_trainings', 'franchisee_support_tickets',
        'franchisee_support_comments', 'franchisee_audits',
        'serial_sequences', 'product_serial_sequences', 'po_serials',
        'model_code_references', 'supplier_codes',
        'categories', 'brands', 'modules', 'permissions',
        'role_permissions', 'users', 'user_roles',
    ]

    print("\nConverting TIMESTAMP to TIMESTAMPTZ...")
    for table in timestamp_tables:
        if not table_exists(conn, table):
            print(f"  Skipping table {table}: does not exist")
            continue

        try:
            result = conn.execute(sa.text(f"""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name = '{table}'
                AND data_type = 'timestamp without time zone'
            """))
            columns = [row[0] for row in result]

            if not columns:
                continue

            for column in columns:
                try:
                    op.execute(f"""
                        ALTER TABLE {table}
                        ALTER COLUMN {column} TYPE TIMESTAMP WITH TIME ZONE
                        USING {column} AT TIME ZONE 'UTC'
                    """)
                    print(f"  Converted {table}.{column} to TIMESTAMPTZ")
                except Exception as e:
                    print(f"  Error on {table}.{column}: {e}")
        except Exception as e:
            print(f"  Error checking table {table}: {e}")

    # ========== Drop old ENUM types ==========
    enum_types = [
        'producttype', 'productstatus', 'warrantytype',
        'customertype', 'customerstatus', 'addresstype',
        'leadstatus', 'leadsource', 'leadpriority', 'activitytype', 'activitystatus',
        'shipmentstatus', 'carriertype',
        'stockstatus', 'stockcondition', 'movementtype', 'movementreason',
        'servicerequesttype', 'servicerequeststatus', 'servicerequestpriority', 'servicerequestsource',
        'installationstatus', 'installationtype',
        'contracttype', 'contractstatus', 'plantype',
        'postatus', 'potype', 'poitemstatus', 'grnstatus',
        'manifeststatus', 'manifesttype', 'scanstatus',
        'pickliststatus', 'picklistitemstatus',
        'transportertype', 'transporterstatus',
        'requeststatus',
        'employmenttype', 'employeestatus', 'gender', 'leavetype', 'leavestatus',
        'campaigntype', 'campaignstatus', 'campaignchannel',
        'channeltype', 'channelstatus',
        'escalationlevel', 'escalationstatus',
        'promotiontype', 'promotionstatus',
        'regiontype', 'regionstatus',
        'forecastlevel', 'forecastgranularity', 'forecastalgorithm', 'forecaststatus',
        'supplyplanstatus', 'scenariostatus', 'factortype',
        'adjustmenttype', 'adjustmentstatus', 'auditstatus',
        'companytype', 'gstregistrationtype',
        'dealertype', 'dealerstatus', 'dealertier', 'creditstatus', 'transactiontype', 'schemetype',
        'd2cservicetype', 'surchargetype', 'calculationtype',
        'b2bservicetype', 'transportmode', 'b2bratetype', 'ftlratetype', 'vehiclecategory',
        'tdssection', 'tdsdeductionstatus',
        'channelcode', 'allocationtype',
        'notificationtype', 'notificationpriority', 'defaultpriority',
        'franchiseetype', 'franchiseestatus', 'franchiseetier',
        'territorystatus', 'trainingtype', 'trainingstatus',
        'supportticketcategory', 'supportticketpriority', 'supportticketstatus',
        'audittype', 'auditresult',
        'serialstatus', 'itemtype',
    ]

    print("\nDropping old ENUM types...")
    for enum_type in enum_types:
        try:
            op.execute(f"DROP TYPE IF EXISTS {enum_type} CASCADE")
            print(f"  Dropped ENUM type: {enum_type}")
        except Exception as e:
            print(f"  Error dropping {enum_type}: {e}")


def downgrade() -> None:
    """
    Note: Downgrade is not recommended as production uses VARCHAR.
    """
    pass
