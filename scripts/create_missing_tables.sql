-- ============================================================
-- SQL Migration: Create 38 Missing Tables in Supabase Production
-- Generated: 2026-01-28
-- ============================================================
-- Run this script against Supabase production to create missing tables.
-- Tables are grouped by functionality.
-- ============================================================

-- ==============================================
-- 1. PRODUCT REVIEWS & Q&A (6 tables)
-- ==============================================

-- Product Reviews
CREATE TABLE IF NOT EXISTS product_reviews (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    product_id UUID NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    customer_id UUID NOT NULL REFERENCES customers(id) ON DELETE CASCADE,
    order_id UUID REFERENCES orders(id) ON DELETE SET NULL,
    rating INTEGER NOT NULL CHECK (rating >= 1 AND rating <= 5),
    title VARCHAR(200),
    review_text TEXT,
    is_verified_purchase BOOLEAN NOT NULL DEFAULT FALSE,
    is_approved BOOLEAN NOT NULL DEFAULT TRUE,
    is_featured BOOLEAN NOT NULL DEFAULT FALSE,
    helpful_count INTEGER NOT NULL DEFAULT 0,
    not_helpful_count INTEGER NOT NULL DEFAULT 0,
    images JSONB DEFAULT '[]',
    admin_response TEXT,
    admin_response_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_product_reviews_product_id ON product_reviews(product_id);
CREATE INDEX IF NOT EXISTS ix_product_reviews_customer_id ON product_reviews(customer_id);

-- Review Helpful Votes
CREATE TABLE IF NOT EXISTS review_helpful (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    review_id UUID NOT NULL REFERENCES product_reviews(id) ON DELETE CASCADE,
    customer_id UUID NOT NULL REFERENCES customers(id) ON DELETE CASCADE,
    is_helpful BOOLEAN NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Product Questions
CREATE TABLE IF NOT EXISTS product_questions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    product_id UUID NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    customer_id UUID NOT NULL REFERENCES customers(id) ON DELETE CASCADE,
    question_text TEXT NOT NULL,
    asked_by VARCHAR(100) NOT NULL,
    is_approved BOOLEAN NOT NULL DEFAULT TRUE,
    helpful_count INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_product_questions_product_id ON product_questions(product_id);
CREATE INDEX IF NOT EXISTS ix_product_questions_customer_id ON product_questions(customer_id);

-- Product Answers
CREATE TABLE IF NOT EXISTS product_answers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    question_id UUID NOT NULL REFERENCES product_questions(id) ON DELETE CASCADE,
    customer_id UUID REFERENCES customers(id) ON DELETE SET NULL,
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    answer_text TEXT NOT NULL,
    answered_by VARCHAR(100) NOT NULL,
    is_seller_answer BOOLEAN NOT NULL DEFAULT FALSE,
    is_verified_buyer BOOLEAN NOT NULL DEFAULT FALSE,
    is_approved BOOLEAN NOT NULL DEFAULT TRUE,
    helpful_count INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_product_answers_question_id ON product_answers(question_id);

-- Question Helpful Votes
CREATE TABLE IF NOT EXISTS question_helpful (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    question_id UUID NOT NULL REFERENCES product_questions(id) ON DELETE CASCADE,
    customer_id UUID NOT NULL REFERENCES customers(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_question_helpful_question_id ON question_helpful(question_id);
CREATE INDEX IF NOT EXISTS ix_question_helpful_customer_id ON question_helpful(customer_id);

-- Answer Helpful Votes
CREATE TABLE IF NOT EXISTS answer_helpful (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    answer_id UUID NOT NULL REFERENCES product_answers(id) ON DELETE CASCADE,
    customer_id UUID NOT NULL REFERENCES customers(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_answer_helpful_answer_id ON answer_helpful(answer_id);
CREATE INDEX IF NOT EXISTS ix_answer_helpful_customer_id ON answer_helpful(customer_id);


-- ==============================================
-- 2. D2C RATE CARDS (3 tables)
-- ==============================================

-- D2C Rate Cards
CREATE TABLE IF NOT EXISTS d2c_rate_cards (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    transporter_id UUID NOT NULL REFERENCES transporters(id) ON DELETE CASCADE,
    code VARCHAR(50) NOT NULL,
    name VARCHAR(200) NOT NULL,
    description TEXT,
    service_type VARCHAR(50) NOT NULL DEFAULT 'STANDARD',
    zone_type VARCHAR(20) DEFAULT 'DISTANCE',
    effective_from DATE NOT NULL,
    effective_to DATE,
    is_active BOOLEAN DEFAULT TRUE,
    is_default BOOLEAN DEFAULT FALSE,
    created_by UUID REFERENCES users(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_d2c_rate_card UNIQUE (transporter_id, code, effective_from)
);
CREATE INDEX IF NOT EXISTS ix_d2c_rate_cards_transporter_id ON d2c_rate_cards(transporter_id);
CREATE INDEX IF NOT EXISTS ix_d2c_rate_cards_code ON d2c_rate_cards(code);

-- D2C Weight Slabs
CREATE TABLE IF NOT EXISTS d2c_weight_slabs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    rate_card_id UUID NOT NULL REFERENCES d2c_rate_cards(id) ON DELETE CASCADE,
    zone VARCHAR(20) NOT NULL,
    min_weight_kg NUMERIC(10,3) NOT NULL DEFAULT 0,
    max_weight_kg NUMERIC(10,3) NOT NULL,
    base_rate NUMERIC(10,2) NOT NULL,
    additional_rate_per_kg NUMERIC(10,2) DEFAULT 0,
    additional_weight_unit_kg NUMERIC(10,3) DEFAULT 0.5,
    cod_available BOOLEAN DEFAULT TRUE,
    prepaid_available BOOLEAN DEFAULT TRUE,
    estimated_days_min INTEGER,
    estimated_days_max INTEGER,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_d2c_weight_slab UNIQUE (rate_card_id, zone, min_weight_kg)
);
CREATE INDEX IF NOT EXISTS idx_d2c_weight_slab_lookup ON d2c_weight_slabs(rate_card_id, zone, min_weight_kg);

-- D2C Surcharges
CREATE TABLE IF NOT EXISTS d2c_surcharges (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    rate_card_id UUID NOT NULL REFERENCES d2c_rate_cards(id) ON DELETE CASCADE,
    surcharge_type VARCHAR(50) NOT NULL,
    calculation_type VARCHAR(50) NOT NULL DEFAULT 'PERCENTAGE',
    value NUMERIC(10,4) NOT NULL,
    min_amount NUMERIC(10,2),
    max_amount NUMERIC(10,2),
    applies_to_cod BOOLEAN DEFAULT TRUE,
    applies_to_prepaid BOOLEAN DEFAULT TRUE,
    zone VARCHAR(20),
    is_active BOOLEAN DEFAULT TRUE,
    effective_from DATE,
    effective_to DATE,
    CONSTRAINT uq_d2c_surcharge UNIQUE (rate_card_id, surcharge_type, zone)
);
CREATE INDEX IF NOT EXISTS ix_d2c_surcharges_rate_card_id ON d2c_surcharges(rate_card_id);


-- ==============================================
-- 3. B2B RATE CARDS (3 tables)
-- ==============================================

-- B2B Rate Cards
CREATE TABLE IF NOT EXISTS b2b_rate_cards (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    transporter_id UUID NOT NULL REFERENCES transporters(id) ON DELETE CASCADE,
    code VARCHAR(50) NOT NULL,
    name VARCHAR(200) NOT NULL,
    description TEXT,
    service_type VARCHAR(50) NOT NULL DEFAULT 'LTL',
    transport_mode VARCHAR(50) NOT NULL DEFAULT 'SURFACE',
    min_chargeable_weight_kg NUMERIC(10,2) DEFAULT 25,
    min_invoice_value NUMERIC(12,2),
    effective_from DATE NOT NULL,
    effective_to DATE,
    is_active BOOLEAN DEFAULT TRUE,
    created_by UUID REFERENCES users(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_b2b_rate_cards_transporter_id ON b2b_rate_cards(transporter_id);
CREATE INDEX IF NOT EXISTS ix_b2b_rate_cards_code ON b2b_rate_cards(code);

-- B2B Rate Slabs
CREATE TABLE IF NOT EXISTS b2b_rate_slabs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    rate_card_id UUID NOT NULL REFERENCES b2b_rate_cards(id) ON DELETE CASCADE,
    origin_city VARCHAR(100),
    origin_state VARCHAR(100),
    destination_city VARCHAR(100),
    destination_state VARCHAR(100),
    zone VARCHAR(20),
    min_weight_kg NUMERIC(10,2) NOT NULL DEFAULT 0,
    max_weight_kg NUMERIC(10,2),
    rate_type VARCHAR(50) NOT NULL DEFAULT 'PER_KG',
    rate NUMERIC(10,2) NOT NULL,
    min_charge NUMERIC(10,2),
    transit_days_min INTEGER,
    transit_days_max INTEGER,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_b2b_rate_slabs_rate_card_id ON b2b_rate_slabs(rate_card_id);

-- B2B Additional Charges
CREATE TABLE IF NOT EXISTS b2b_additional_charges (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    rate_card_id UUID NOT NULL REFERENCES b2b_rate_cards(id) ON DELETE CASCADE,
    charge_type VARCHAR(50) NOT NULL,
    calculation_type VARCHAR(50) NOT NULL DEFAULT 'FIXED',
    value NUMERIC(10,4) NOT NULL,
    per_unit VARCHAR(20),
    is_active BOOLEAN DEFAULT TRUE
);
CREATE INDEX IF NOT EXISTS ix_b2b_additional_charges_rate_card_id ON b2b_additional_charges(rate_card_id);


-- ==============================================
-- 4. FTL RATE CARDS (4 tables)
-- ==============================================

-- FTL Rate Cards
CREATE TABLE IF NOT EXISTS ftl_rate_cards (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    transporter_id UUID REFERENCES transporters(id) ON DELETE SET NULL,
    code VARCHAR(50) NOT NULL,
    name VARCHAR(200) NOT NULL,
    description TEXT,
    rate_type VARCHAR(50) NOT NULL DEFAULT 'CONTRACT',
    payment_terms VARCHAR(100),
    effective_from DATE NOT NULL,
    effective_to DATE,
    is_active BOOLEAN DEFAULT TRUE,
    created_by UUID REFERENCES users(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_ftl_rate_cards_transporter_id ON ftl_rate_cards(transporter_id);
CREATE INDEX IF NOT EXISTS ix_ftl_rate_cards_code ON ftl_rate_cards(code);

-- FTL Lane Rates
CREATE TABLE IF NOT EXISTS ftl_lane_rates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    rate_card_id UUID NOT NULL REFERENCES ftl_rate_cards(id) ON DELETE CASCADE,
    origin_city VARCHAR(100) NOT NULL,
    origin_state VARCHAR(100) NOT NULL,
    origin_pincode VARCHAR(10),
    destination_city VARCHAR(100) NOT NULL,
    destination_state VARCHAR(100) NOT NULL,
    destination_pincode VARCHAR(10),
    distance_km INTEGER,
    vehicle_type VARCHAR(50) NOT NULL,
    vehicle_capacity_tons NUMERIC(10,2),
    vehicle_capacity_cft INTEGER,
    rate_per_trip NUMERIC(12,2) NOT NULL,
    rate_per_km NUMERIC(10,2),
    min_running_km INTEGER,
    extra_km_rate NUMERIC(10,2),
    transit_hours INTEGER,
    loading_points_included INTEGER DEFAULT 1,
    unloading_points_included INTEGER DEFAULT 1,
    extra_point_charge NUMERIC(10,2),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_ftl_lane_rate UNIQUE (rate_card_id, origin_city, destination_city, vehicle_type)
);
CREATE INDEX IF NOT EXISTS idx_ftl_lane_lookup ON ftl_lane_rates(rate_card_id, origin_city, destination_city);
CREATE INDEX IF NOT EXISTS ix_ftl_lane_rates_origin_city ON ftl_lane_rates(origin_city);
CREATE INDEX IF NOT EXISTS ix_ftl_lane_rates_destination_city ON ftl_lane_rates(destination_city);

-- FTL Additional Charges
CREATE TABLE IF NOT EXISTS ftl_additional_charges (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    rate_card_id UUID NOT NULL REFERENCES ftl_rate_cards(id) ON DELETE CASCADE,
    charge_type VARCHAR(50) NOT NULL,
    calculation_type VARCHAR(50) NOT NULL DEFAULT 'FIXED',
    value NUMERIC(10,4) NOT NULL,
    per_unit VARCHAR(20),
    free_hours INTEGER,
    is_active BOOLEAN DEFAULT TRUE
);
CREATE INDEX IF NOT EXISTS ix_ftl_additional_charges_rate_card_id ON ftl_additional_charges(rate_card_id);

-- FTL Vehicle Types
CREATE TABLE IF NOT EXISTS ftl_vehicle_types (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    code VARCHAR(30) NOT NULL UNIQUE,
    name VARCHAR(100) NOT NULL,
    length_ft NUMERIC(6,2),
    width_ft NUMERIC(6,2),
    height_ft NUMERIC(6,2),
    capacity_tons NUMERIC(10,2),
    capacity_cft INTEGER,
    category VARCHAR(50),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);


-- ==============================================
-- 5. ZONE MAPPINGS & CARRIER PERFORMANCE (2 tables)
-- ==============================================

-- Zone Mappings
CREATE TABLE IF NOT EXISTS zone_mappings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    origin_pincode VARCHAR(10),
    origin_city VARCHAR(100),
    origin_state VARCHAR(100),
    destination_pincode VARCHAR(10),
    destination_city VARCHAR(100),
    destination_state VARCHAR(100),
    zone VARCHAR(20) NOT NULL,
    distance_km INTEGER,
    is_oda BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_zone_mapping UNIQUE (origin_pincode, destination_pincode)
);
CREATE INDEX IF NOT EXISTS idx_zone_mapping_dest ON zone_mappings(destination_pincode);
CREATE INDEX IF NOT EXISTS idx_zone_mapping_origin ON zone_mappings(origin_pincode);

-- Carrier Performance
CREATE TABLE IF NOT EXISTS carrier_performance (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    transporter_id UUID NOT NULL REFERENCES transporters(id) ON DELETE CASCADE,
    period_start DATE NOT NULL,
    period_end DATE NOT NULL,
    zone VARCHAR(20),
    origin_city VARCHAR(100),
    destination_city VARCHAR(100),
    total_shipments INTEGER DEFAULT 0,
    total_weight_kg NUMERIC(14,2) DEFAULT 0,
    total_revenue NUMERIC(14,2) DEFAULT 0,
    on_time_delivery_count INTEGER DEFAULT 0,
    on_time_pickup_count INTEGER DEFAULT 0,
    total_delivered INTEGER DEFAULT 0,
    rto_count INTEGER DEFAULT 0,
    damage_count INTEGER DEFAULT 0,
    lost_count INTEGER DEFAULT 0,
    ndr_count INTEGER DEFAULT 0,
    delivery_score NUMERIC(5,2),
    pickup_score NUMERIC(5,2),
    rto_score NUMERIC(5,2),
    damage_score NUMERIC(5,2),
    overall_score NUMERIC(5,2),
    score_trend VARCHAR(10),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_carrier_performance UNIQUE (transporter_id, period_start, zone)
);
CREATE INDEX IF NOT EXISTS ix_carrier_performance_transporter_id ON carrier_performance(transporter_id);


-- ==============================================
-- 6. RETURNS & REFUNDS (4 tables)
-- ==============================================

-- Return Orders
CREATE TABLE IF NOT EXISTS return_orders (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    rma_number VARCHAR(50) NOT NULL UNIQUE,
    order_id UUID NOT NULL REFERENCES orders(id),
    customer_id UUID REFERENCES customers(id),
    return_type VARCHAR(50) NOT NULL DEFAULT 'RETURN',
    return_reason VARCHAR(100) NOT NULL,
    return_reason_details TEXT,
    status VARCHAR(50) NOT NULL DEFAULT 'INITIATED',
    requested_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    authorized_at TIMESTAMPTZ,
    pickup_scheduled_at TIMESTAMPTZ,
    picked_up_at TIMESTAMPTZ,
    received_at TIMESTAMPTZ,
    inspected_at TIMESTAMPTZ,
    closed_at TIMESTAMPTZ,
    return_shipment_id UUID REFERENCES shipments(id),
    return_tracking_number VARCHAR(100),
    return_courier VARCHAR(100),
    pickup_address JSONB,
    inspection_notes TEXT,
    inspection_images JSONB,
    inspected_by UUID,
    rejection_reason TEXT,
    resolution_type VARCHAR(50),
    resolution_notes TEXT,
    total_return_amount NUMERIC(18,2) NOT NULL DEFAULT 0,
    restocking_fee NUMERIC(18,2) NOT NULL DEFAULT 0,
    shipping_deduction NUMERIC(18,2) NOT NULL DEFAULT 0,
    net_refund_amount NUMERIC(18,2) NOT NULL DEFAULT 0,
    store_credit_amount NUMERIC(18,2) NOT NULL DEFAULT 0,
    store_credit_code VARCHAR(50),
    replacement_order_id UUID,
    customer_notified_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_return_orders_rma_number ON return_orders(rma_number);
CREATE INDEX IF NOT EXISTS ix_return_orders_order_id ON return_orders(order_id);
CREATE INDEX IF NOT EXISTS ix_return_orders_customer_id ON return_orders(customer_id);
CREATE INDEX IF NOT EXISTS ix_return_orders_status ON return_orders(status);

-- Return Items
CREATE TABLE IF NOT EXISTS return_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    return_order_id UUID NOT NULL REFERENCES return_orders(id),
    order_item_id UUID NOT NULL REFERENCES order_items(id),
    product_id UUID NOT NULL,
    product_name VARCHAR(500) NOT NULL,
    sku VARCHAR(100) NOT NULL,
    quantity_ordered INTEGER NOT NULL,
    quantity_returned INTEGER NOT NULL,
    condition VARCHAR(50) NOT NULL DEFAULT 'UNOPENED',
    condition_notes TEXT,
    inspection_result VARCHAR(50),
    inspection_notes TEXT,
    accepted_quantity INTEGER,
    unit_price NUMERIC(18,2) NOT NULL,
    total_amount NUMERIC(18,2) NOT NULL,
    refund_amount NUMERIC(18,2) NOT NULL DEFAULT 0,
    serial_number VARCHAR(100),
    customer_images JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_return_items_return_order_id ON return_items(return_order_id);

-- Return Status History
CREATE TABLE IF NOT EXISTS return_status_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    return_order_id UUID NOT NULL REFERENCES return_orders(id),
    from_status VARCHAR(50),
    to_status VARCHAR(50) NOT NULL,
    notes TEXT,
    changed_by UUID,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_return_status_history_return_order_id ON return_status_history(return_order_id);

-- Refunds
CREATE TABLE IF NOT EXISTS refunds (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    refund_number VARCHAR(50) NOT NULL UNIQUE,
    order_id UUID NOT NULL REFERENCES orders(id),
    return_order_id UUID REFERENCES return_orders(id),
    customer_id UUID REFERENCES customers(id),
    refund_type VARCHAR(50) NOT NULL,
    refund_method VARCHAR(50) NOT NULL,
    order_amount NUMERIC(18,2) NOT NULL,
    refund_amount NUMERIC(18,2) NOT NULL,
    processing_fee NUMERIC(18,2) NOT NULL DEFAULT 0,
    net_refund NUMERIC(18,2) NOT NULL,
    tax_refund NUMERIC(18,2) NOT NULL DEFAULT 0,
    status VARCHAR(50) NOT NULL DEFAULT 'PENDING',
    original_payment_id VARCHAR(100),
    refund_transaction_id VARCHAR(100),
    gateway_response JSONB,
    bank_account_number VARCHAR(50),
    bank_ifsc VARCHAR(20),
    bank_account_name VARCHAR(200),
    reason VARCHAR(200) NOT NULL,
    notes TEXT,
    initiated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    processed_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    failed_at TIMESTAMPTZ,
    failure_reason TEXT,
    retry_count INTEGER NOT NULL DEFAULT 0,
    accounting_entry_id UUID,
    initiated_by UUID,
    approved_by UUID,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_refunds_refund_number ON refunds(refund_number);
CREATE INDEX IF NOT EXISTS ix_refunds_order_id ON refunds(order_id);
CREATE INDEX IF NOT EXISTS ix_refunds_return_order_id ON refunds(return_order_id);
CREATE INDEX IF NOT EXISTS ix_refunds_customer_id ON refunds(customer_id);
CREATE INDEX IF NOT EXISTS ix_refunds_status ON refunds(status);


-- ==============================================
-- 7. SNOP - DEMAND FORECASTING (6 tables)
-- ==============================================

-- Demand Forecasts
CREATE TABLE IF NOT EXISTS demand_forecasts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    forecast_code VARCHAR(50) NOT NULL UNIQUE,
    forecast_name VARCHAR(200) NOT NULL,
    forecast_level VARCHAR(50) DEFAULT 'SKU',
    granularity VARCHAR(50) DEFAULT 'WEEKLY',
    product_id UUID REFERENCES products(id),
    category_id UUID REFERENCES categories(id),
    warehouse_id UUID REFERENCES warehouses(id),
    region_id UUID REFERENCES regions(id),
    channel VARCHAR(50),
    forecast_start_date DATE NOT NULL,
    forecast_end_date DATE NOT NULL,
    forecast_horizon_days INTEGER DEFAULT 90,
    forecast_data JSONB NOT NULL DEFAULT '[]',
    total_forecasted_qty NUMERIC(15,2) DEFAULT 0,
    avg_daily_demand NUMERIC(15,4) DEFAULT 0,
    peak_demand NUMERIC(15,2) DEFAULT 0,
    algorithm_used VARCHAR(50) DEFAULT 'ENSEMBLE',
    model_parameters JSONB,
    mape FLOAT,
    mae FLOAT,
    rmse FLOAT,
    forecast_bias FLOAT,
    confidence_level FLOAT DEFAULT 0.95,
    external_factors_json JSONB,
    status VARCHAR(50) DEFAULT 'DRAFT',
    created_by_id UUID REFERENCES users(id),
    reviewed_by_id UUID REFERENCES users(id),
    approved_by_id UUID REFERENCES users(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    submitted_at TIMESTAMPTZ,
    reviewed_at TIMESTAMPTZ,
    approved_at TIMESTAMPTZ,
    version INTEGER DEFAULT 1,
    parent_forecast_id UUID REFERENCES demand_forecasts(id),
    is_active BOOLEAN DEFAULT TRUE,
    notes TEXT
);
CREATE INDEX IF NOT EXISTS ix_demand_forecasts_product_date ON demand_forecasts(product_id, forecast_start_date);
CREATE INDEX IF NOT EXISTS ix_demand_forecasts_category_date ON demand_forecasts(category_id, forecast_start_date);
CREATE INDEX IF NOT EXISTS ix_demand_forecasts_status ON demand_forecasts(status);
CREATE INDEX IF NOT EXISTS ix_demand_forecasts_level_granularity ON demand_forecasts(forecast_level, granularity);

-- Forecast Adjustments
CREATE TABLE IF NOT EXISTS forecast_adjustments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    forecast_id UUID NOT NULL REFERENCES demand_forecasts(id),
    adjustment_date DATE NOT NULL,
    original_qty NUMERIC(15,2) NOT NULL,
    adjusted_qty NUMERIC(15,2) NOT NULL,
    adjustment_pct FLOAT NOT NULL,
    adjustment_reason VARCHAR(100) NOT NULL,
    justification TEXT,
    status VARCHAR(50) DEFAULT 'PENDING_REVIEW',
    adjusted_by_id UUID NOT NULL REFERENCES users(id),
    approved_by_id UUID REFERENCES users(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    approved_at TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS ix_forecast_adjustments_forecast_id ON forecast_adjustments(forecast_id);

-- Supply Plans
CREATE TABLE IF NOT EXISTS supply_plans (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    plan_code VARCHAR(50) NOT NULL UNIQUE,
    plan_name VARCHAR(200) NOT NULL,
    forecast_id UUID REFERENCES demand_forecasts(id),
    plan_start_date DATE NOT NULL,
    plan_end_date DATE NOT NULL,
    product_id UUID REFERENCES products(id),
    warehouse_id UUID REFERENCES warehouses(id),
    planned_production_qty NUMERIC(15,2) DEFAULT 0,
    planned_procurement_qty NUMERIC(15,2) DEFAULT 0,
    production_capacity NUMERIC(15,2) DEFAULT 0,
    capacity_utilization_pct FLOAT DEFAULT 0.0,
    vendor_id UUID REFERENCES vendors(id),
    lead_time_days INTEGER DEFAULT 0,
    schedule_data JSONB NOT NULL DEFAULT '[]',
    status VARCHAR(50) DEFAULT 'DRAFT',
    created_by_id UUID REFERENCES users(id),
    approved_by_id UUID REFERENCES users(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    approved_at TIMESTAMPTZ,
    is_active BOOLEAN DEFAULT TRUE,
    notes TEXT
);
CREATE INDEX IF NOT EXISTS ix_supply_plans_forecast_id ON supply_plans(forecast_id);

-- SNOP Scenarios
CREATE TABLE IF NOT EXISTS snop_scenarios (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    scenario_code VARCHAR(50) NOT NULL UNIQUE,
    scenario_name VARCHAR(200) NOT NULL,
    description TEXT,
    base_scenario_id UUID REFERENCES snop_scenarios(id),
    demand_multiplier FLOAT DEFAULT 1.0,
    supply_constraint_pct FLOAT DEFAULT 100.0,
    lead_time_multiplier FLOAT DEFAULT 1.0,
    price_change_pct FLOAT DEFAULT 0.0,
    assumptions JSONB NOT NULL DEFAULT '{}',
    simulation_start_date DATE NOT NULL,
    simulation_end_date DATE NOT NULL,
    results JSONB,
    projected_revenue NUMERIC(18,2),
    projected_margin NUMERIC(18,2),
    stockout_probability FLOAT,
    service_level_pct FLOAT,
    status VARCHAR(50) DEFAULT 'DRAFT',
    created_by_id UUID REFERENCES users(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMPTZ,
    is_active BOOLEAN DEFAULT TRUE
);

-- External Factors
CREATE TABLE IF NOT EXISTS external_factors (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    factor_code VARCHAR(50) NOT NULL UNIQUE,
    factor_name VARCHAR(200) NOT NULL,
    factor_type VARCHAR(50) NOT NULL,
    product_id UUID REFERENCES products(id),
    category_id UUID REFERENCES categories(id),
    region_id UUID REFERENCES regions(id),
    applies_to_all BOOLEAN DEFAULT FALSE,
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    impact_multiplier FLOAT DEFAULT 1.0,
    impact_absolute NUMERIC(15,2),
    metadata_json JSONB,
    is_active BOOLEAN DEFAULT TRUE,
    created_by_id UUID REFERENCES users(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_external_factors_type_dates ON external_factors(factor_type, start_date, end_date);
CREATE INDEX IF NOT EXISTS ix_external_factors_product ON external_factors(product_id);

-- Inventory Optimizations
CREATE TABLE IF NOT EXISTS inventory_optimizations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    product_id UUID NOT NULL REFERENCES products(id),
    warehouse_id UUID NOT NULL REFERENCES warehouses(id),
    recommended_safety_stock NUMERIC(15,2) NOT NULL,
    recommended_reorder_point NUMERIC(15,2) NOT NULL,
    recommended_order_qty NUMERIC(15,2) NOT NULL,
    current_safety_stock NUMERIC(15,2) DEFAULT 0,
    current_reorder_point NUMERIC(15,2) DEFAULT 0,
    avg_daily_demand NUMERIC(15,4) NOT NULL,
    demand_std_dev NUMERIC(15,4) NOT NULL,
    lead_time_days INTEGER NOT NULL,
    lead_time_std_dev FLOAT DEFAULT 0.0,
    service_level_target FLOAT DEFAULT 0.95,
    holding_cost_pct FLOAT DEFAULT 0.25,
    ordering_cost NUMERIC(15,2) DEFAULT 100,
    stockout_cost NUMERIC(15,2),
    expected_stockout_rate FLOAT DEFAULT 0.0,
    expected_inventory_turns FLOAT DEFAULT 0.0,
    expected_holding_cost NUMERIC(15,2) DEFAULT 0,
    calculation_details JSONB,
    valid_from DATE NOT NULL,
    valid_until DATE NOT NULL,
    is_applied BOOLEAN DEFAULT FALSE,
    applied_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_inventory_opt_product_warehouse_date UNIQUE (product_id, warehouse_id, valid_from)
);
CREATE INDEX IF NOT EXISTS ix_inventory_opt_product_warehouse ON inventory_optimizations(product_id, warehouse_id);

-- SNOP Meetings
CREATE TABLE IF NOT EXISTS snop_meetings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    meeting_code VARCHAR(50) NOT NULL UNIQUE,
    meeting_title VARCHAR(200) NOT NULL,
    meeting_date TIMESTAMP NOT NULL,
    planning_period_start DATE NOT NULL,
    planning_period_end DATE NOT NULL,
    participants JSONB NOT NULL DEFAULT '[]',
    agenda TEXT,
    meeting_notes TEXT,
    forecasts_reviewed JSONB NOT NULL DEFAULT '[]',
    decisions JSONB,
    action_items JSONB,
    is_completed BOOLEAN DEFAULT FALSE,
    created_by_id UUID REFERENCES users(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);


-- ==============================================
-- 8. BANKING (2 tables)
-- ==============================================

-- Bank Accounts
CREATE TABLE IF NOT EXISTS bank_accounts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    account_name VARCHAR(200) NOT NULL,
    account_number VARCHAR(50) NOT NULL UNIQUE,
    bank_name VARCHAR(200) NOT NULL,
    branch_name VARCHAR(200),
    ifsc_code VARCHAR(20),
    swift_code VARCHAR(20),
    account_type VARCHAR(50) DEFAULT 'CURRENT',
    opening_balance NUMERIC(15,2) DEFAULT 0,
    current_balance NUMERIC(15,2) DEFAULT 0,
    ledger_account_id UUID,
    credit_limit NUMERIC(15,2),
    available_limit NUMERIC(15,2),
    last_reconciled_date DATE,
    last_reconciled_balance NUMERIC(15,2),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_by UUID REFERENCES users(id)
);

-- Bank Transactions
CREATE TABLE IF NOT EXISTS bank_transactions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    bank_account_id UUID NOT NULL REFERENCES bank_accounts(id),
    transaction_date DATE NOT NULL,
    value_date DATE,
    description TEXT NOT NULL,
    reference_number VARCHAR(100),
    cheque_number VARCHAR(20),
    transaction_type VARCHAR(50) NOT NULL,
    amount NUMERIC(15,2) NOT NULL,
    debit_amount NUMERIC(15,2) DEFAULT 0,
    credit_amount NUMERIC(15,2) DEFAULT 0,
    running_balance NUMERIC(15,2),
    is_reconciled BOOLEAN DEFAULT FALSE,
    reconciled_at TIMESTAMPTZ,
    matched_journal_entry_id UUID REFERENCES journal_entries(id),
    reconciliation_status VARCHAR(50) DEFAULT 'PENDING',
    source VARCHAR(50) DEFAULT 'IMPORT',
    import_reference VARCHAR(255),
    import_batch_id UUID,
    category VARCHAR(100),
    party_name VARCHAR(200),
    party_id UUID,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_by UUID REFERENCES users(id)
);
CREATE INDEX IF NOT EXISTS ix_bank_transactions_account_id ON bank_transactions(bank_account_id);
CREATE INDEX IF NOT EXISTS ix_bank_transactions_date ON bank_transactions(transaction_date);
CREATE INDEX IF NOT EXISTS ix_bank_transactions_reconciled ON bank_transactions(is_reconciled);


-- ==============================================
-- 9. COUPONS (2 tables)
-- ==============================================

-- Coupons
CREATE TABLE IF NOT EXISTS coupons (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    code VARCHAR(50) NOT NULL UNIQUE,
    name VARCHAR(200) NOT NULL,
    description TEXT,
    discount_type VARCHAR(50) NOT NULL DEFAULT 'PERCENTAGE',
    discount_value NUMERIC(10,2) NOT NULL DEFAULT 0,
    max_discount_amount NUMERIC(10,2),
    minimum_order_amount NUMERIC(10,2),
    minimum_items INTEGER,
    usage_limit INTEGER,
    usage_limit_per_customer INTEGER NOT NULL DEFAULT 1,
    used_count INTEGER NOT NULL DEFAULT 0,
    valid_from TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    valid_until TIMESTAMPTZ,
    applicable_products JSONB,
    applicable_categories JSONB,
    excluded_products JSONB,
    first_order_only BOOLEAN NOT NULL DEFAULT FALSE,
    specific_customers JSONB,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_coupons_code ON coupons(code);

-- Coupon Usage
CREATE TABLE IF NOT EXISTS coupon_usage (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    coupon_id UUID NOT NULL,
    customer_id UUID NOT NULL,
    order_id UUID NOT NULL,
    discount_amount NUMERIC(10,2) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_coupon_usage_coupon_id ON coupon_usage(coupon_id);
CREATE INDEX IF NOT EXISTS ix_coupon_usage_customer_id ON coupon_usage(customer_id);


-- ==============================================
-- 10. TDS (3 tables)
-- ==============================================

-- TDS Rates
CREATE TABLE IF NOT EXISTS tds_rates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id UUID NOT NULL REFERENCES companies(id),
    section VARCHAR(20) NOT NULL,
    description VARCHAR(255) NOT NULL,
    standard_rate NUMERIC(5,2) NOT NULL,
    higher_rate NUMERIC(5,2),
    threshold_amount NUMERIC(15,2) DEFAULT 0,
    effective_from DATE NOT NULL,
    effective_to DATE,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_tds_rates_company_section ON tds_rates(company_id, section);

-- TDS Deductions
CREATE TABLE IF NOT EXISTS tds_deductions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id UUID NOT NULL REFERENCES companies(id),
    deductee_id UUID,
    deductee_type VARCHAR(50) NOT NULL,
    deductee_name VARCHAR(255) NOT NULL,
    deductee_pan VARCHAR(10) NOT NULL,
    deductee_address TEXT,
    section VARCHAR(20) NOT NULL,
    deduction_date DATE NOT NULL,
    financial_year VARCHAR(9) NOT NULL,
    quarter VARCHAR(2) NOT NULL,
    gross_amount NUMERIC(15,2) NOT NULL,
    tds_rate NUMERIC(5,2) NOT NULL,
    tds_amount NUMERIC(15,2) NOT NULL,
    surcharge NUMERIC(15,2) DEFAULT 0,
    education_cess NUMERIC(15,2) DEFAULT 0,
    total_tds NUMERIC(15,2) NOT NULL,
    lower_deduction_cert_no VARCHAR(50),
    lower_deduction_rate NUMERIC(5,2),
    reference_type VARCHAR(50),
    reference_id UUID,
    reference_number VARCHAR(100),
    narration TEXT,
    status VARCHAR(50) DEFAULT 'PENDING',
    deposit_date DATE,
    challan_number VARCHAR(50),
    challan_date DATE,
    bsr_code VARCHAR(20),
    cin VARCHAR(50),
    certificate_number VARCHAR(50),
    certificate_date DATE,
    certificate_issued BOOLEAN DEFAULT FALSE,
    created_by UUID REFERENCES users(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_tds_deductions_company_fy ON tds_deductions(company_id, financial_year);
CREATE INDEX IF NOT EXISTS ix_tds_deductions_deductee_pan ON tds_deductions(deductee_pan);
CREATE INDEX IF NOT EXISTS ix_tds_deductions_status ON tds_deductions(status);
CREATE INDEX IF NOT EXISTS ix_tds_deductions_section ON tds_deductions(section);

-- Form 16A Certificates
CREATE TABLE IF NOT EXISTS form_16a_certificates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id UUID NOT NULL REFERENCES companies(id),
    certificate_number VARCHAR(50) NOT NULL,
    issue_date DATE NOT NULL,
    financial_year VARCHAR(9) NOT NULL,
    quarter VARCHAR(2) NOT NULL,
    deductee_name VARCHAR(255) NOT NULL,
    deductee_pan VARCHAR(10) NOT NULL,
    deductee_address TEXT,
    deductor_name VARCHAR(255) NOT NULL,
    deductor_tan VARCHAR(10) NOT NULL,
    deductor_pan VARCHAR(10),
    deductor_address TEXT,
    total_amount_paid NUMERIC(15,2) NOT NULL,
    total_tds_deducted NUMERIC(15,2) NOT NULL,
    total_tds_deposited NUMERIC(15,2) NOT NULL,
    is_revised BOOLEAN DEFAULT FALSE,
    original_certificate_id UUID,
    pdf_path VARCHAR(500),
    created_by UUID REFERENCES users(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_form16a_company_fy_qtr ON form_16a_certificates(company_id, financial_year, quarter);
CREATE INDEX IF NOT EXISTS ix_form16a_deductee_pan ON form_16a_certificates(deductee_pan);


-- ==============================================
-- 11. CART RECOVERY & CUSTOMER LEDGER (2 tables)
-- ==============================================

-- Cart Recovery Emails
CREATE TABLE IF NOT EXISTS cart_recovery_emails (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    cart_id UUID NOT NULL REFERENCES abandoned_carts(id) ON DELETE CASCADE,
    sequence_number INTEGER NOT NULL DEFAULT 1,
    channel VARCHAR(50) NOT NULL DEFAULT 'EMAIL',
    status VARCHAR(50) NOT NULL DEFAULT 'PENDING',
    recipient VARCHAR(255) NOT NULL,
    template_used VARCHAR(100) NOT NULL,
    subject VARCHAR(255),
    discount_code VARCHAR(50),
    discount_value NUMERIC(18,2),
    scheduled_at TIMESTAMPTZ NOT NULL,
    sent_at TIMESTAMPTZ,
    delivered_at TIMESTAMPTZ,
    opened_at TIMESTAMPTZ,
    clicked_at TIMESTAMPTZ,
    provider VARCHAR(50),
    provider_message_id VARCHAR(200),
    error_message TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_cart_recovery_emails_cart_id ON cart_recovery_emails(cart_id);

-- Customer Ledger
CREATE TABLE IF NOT EXISTS customer_ledger (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    customer_id UUID NOT NULL REFERENCES customers(id),
    transaction_type VARCHAR(50) NOT NULL,
    transaction_date DATE NOT NULL,
    due_date DATE,
    reference_type VARCHAR(50) NOT NULL,
    reference_number VARCHAR(50) NOT NULL,
    reference_id UUID,
    order_id UUID REFERENCES orders(id) ON DELETE SET NULL,
    debit_amount NUMERIC(14,2) DEFAULT 0,
    credit_amount NUMERIC(14,2) DEFAULT 0,
    balance NUMERIC(14,2) DEFAULT 0,
    tax_amount NUMERIC(12,2) DEFAULT 0,
    is_settled BOOLEAN DEFAULT FALSE,
    settled_date DATE,
    settled_against_id UUID,
    description VARCHAR(500),
    notes TEXT,
    channel_id UUID REFERENCES sales_channels(id) ON DELETE SET NULL,
    created_by UUID REFERENCES users(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_customer_ledger_customer_id ON customer_ledger(customer_id);
CREATE INDEX IF NOT EXISTS ix_customer_ledger_order_id ON customer_ledger(order_id);
CREATE INDEX IF NOT EXISTS ix_customer_ledger_transaction_date ON customer_ledger(transaction_date);


-- ==============================================
-- GRANT PERMISSIONS
-- ==============================================
-- Grant permissions to authenticated users
GRANT ALL ON ALL TABLES IN SCHEMA public TO authenticated;
GRANT ALL ON ALL SEQUENCES IN SCHEMA public TO authenticated;

-- End of Migration
