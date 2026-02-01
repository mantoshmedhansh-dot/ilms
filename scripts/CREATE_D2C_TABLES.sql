-- ============================================================================
-- CREATE D2C TABLES - Missing tables for D2C storefront
-- Run in Supabase SQL Editor
-- Created: 2026-01-19
-- ============================================================================

-- Check if tables exist first
SELECT table_name FROM information_schema.tables
WHERE table_schema = 'public'
AND table_name IN ('customer_otps', 'abandoned_carts', 'wishlist_items');

-- ============================================================================
-- 1. CUSTOMER OTP TABLE (for D2C login)
-- ============================================================================
CREATE TABLE IF NOT EXISTS customer_otps (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    phone VARCHAR(20) NOT NULL,
    otp_hash VARCHAR(255) NOT NULL,
    purpose VARCHAR(50) NOT NULL DEFAULT 'LOGIN',
    is_verified BOOLEAN NOT NULL DEFAULT FALSE,
    attempts INTEGER NOT NULL DEFAULT 0,
    max_attempts INTEGER NOT NULL DEFAULT 3,
    expires_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    verified_at TIMESTAMPTZ
);

-- Index for fast phone lookups
CREATE INDEX IF NOT EXISTS ix_customer_otps_phone ON customer_otps (phone);
CREATE INDEX IF NOT EXISTS ix_customer_otps_phone_purpose ON customer_otps (phone, purpose);

-- ============================================================================
-- 2. ABANDONED CARTS TABLE (for cart recovery)
-- ============================================================================
CREATE TABLE IF NOT EXISTS abandoned_carts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id VARCHAR(100) NOT NULL,
    customer_id UUID REFERENCES customers(id) ON DELETE SET NULL,
    customer_email VARCHAR(255),
    customer_phone VARCHAR(20),
    customer_name VARCHAR(200),

    -- Cart data
    items JSONB NOT NULL DEFAULT '[]',
    subtotal NUMERIC(18,2) DEFAULT 0,
    discount_amount NUMERIC(18,2) DEFAULT 0,
    coupon_code VARCHAR(50),
    total_amount NUMERIC(18,2) DEFAULT 0,

    -- Checkout progress
    checkout_step VARCHAR(50) DEFAULT 'CART',
    shipping_address JSONB,
    payment_method VARCHAR(50),

    -- Recovery tracking
    recovery_email_sent BOOLEAN DEFAULT FALSE,
    recovery_email_sent_at TIMESTAMPTZ,
    recovery_token VARCHAR(100),

    -- Conversion tracking
    is_converted BOOLEAN DEFAULT FALSE,
    converted_order_id UUID REFERENCES orders(id) ON DELETE SET NULL,
    converted_at TIMESTAMPTZ,

    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_activity_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Indexes
CREATE INDEX IF NOT EXISTS ix_abandoned_carts_session_id ON abandoned_carts (session_id);
CREATE INDEX IF NOT EXISTS ix_abandoned_carts_customer_id ON abandoned_carts (customer_id);
CREATE INDEX IF NOT EXISTS ix_abandoned_carts_customer_email ON abandoned_carts (customer_email);
CREATE INDEX IF NOT EXISTS ix_abandoned_carts_recovery_token ON abandoned_carts (recovery_token);
CREATE INDEX IF NOT EXISTS ix_abandoned_carts_is_converted ON abandoned_carts (is_converted);

-- ============================================================================
-- 3. WISHLIST ITEMS TABLE
-- ============================================================================
CREATE TABLE IF NOT EXISTS wishlist_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    customer_id UUID NOT NULL REFERENCES customers(id) ON DELETE CASCADE,
    product_id UUID NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    variant_id UUID REFERENCES product_variants(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- Unique constraint: one product per customer
    CONSTRAINT uq_wishlist_customer_product UNIQUE (customer_id, product_id)
);

-- Indexes
CREATE INDEX IF NOT EXISTS ix_wishlist_items_customer_id ON wishlist_items (customer_id);
CREATE INDEX IF NOT EXISTS ix_wishlist_items_product_id ON wishlist_items (product_id);

-- ============================================================================
-- 4. WAREHOUSE SERVICEABILITY INDEX (Performance fix)
-- ============================================================================
CREATE INDEX IF NOT EXISTS ix_warehouse_serviceability_pincode
ON warehouse_serviceability (pincode);

CREATE INDEX IF NOT EXISTS ix_warehouse_serviceability_pincode_active
ON warehouse_serviceability (pincode, is_serviceable, is_active);

-- ============================================================================
-- 5. VERIFY TABLES CREATED
-- ============================================================================
SELECT 'Tables created successfully' as status;

SELECT table_name,
       (SELECT COUNT(*) FROM information_schema.columns WHERE table_name = t.table_name) as column_count
FROM information_schema.tables t
WHERE table_schema = 'public'
AND table_name IN ('customer_otps', 'abandoned_carts', 'wishlist_items', 'warehouse_serviceability')
ORDER BY table_name;
