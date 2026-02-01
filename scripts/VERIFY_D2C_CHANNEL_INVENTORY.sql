-- ============================================================================
-- VERIFY D2C CHANNEL & INVENTORY SETUP
-- Run in Supabase SQL Editor to check production state
-- Created: 2026-01-20
-- ============================================================================

-- ============================================================================
-- 1. CHECK IF SALES_CHANNELS TABLE EXISTS AND HAS D2C
-- ============================================================================
SELECT '=== SALES CHANNELS ===' as section;

SELECT
    id,
    code,
    name,
    channel_type,
    status,
    is_active,
    created_at
FROM sales_channels
WHERE code = 'D2C' OR channel_type = 'D2C' OR channel_type = 'D2C_WEBSITE'
ORDER BY code;

-- Count all active channels
SELECT '=== ALL ACTIVE CHANNELS ===' as section;
SELECT code, name, channel_type, status FROM sales_channels WHERE status = 'ACTIVE' OR is_active = true;

-- ============================================================================
-- 2. CHECK CHANNEL_INVENTORY TABLE
-- ============================================================================
SELECT '=== CHANNEL_INVENTORY TABLE STATUS ===' as section;

-- Check if table exists and has data
SELECT
    COUNT(*) as total_records,
    COUNT(DISTINCT channel_id) as unique_channels,
    COUNT(DISTINCT warehouse_id) as unique_warehouses,
    COUNT(DISTINCT product_id) as unique_products,
    SUM(allocated_quantity) as total_allocated,
    SUM(reserved_quantity) as total_reserved
FROM channel_inventory;

-- Sample channel inventory records
SELECT '=== SAMPLE CHANNEL_INVENTORY RECORDS ===' as section;
SELECT
    ci.id,
    sc.code as channel_code,
    sc.name as channel_name,
    w.code as warehouse_code,
    p.sku as product_sku,
    p.name as product_name,
    ci.allocated_quantity,
    ci.buffer_quantity,
    ci.reserved_quantity,
    ci.marketplace_quantity,
    ci.is_active,
    ci.created_at
FROM channel_inventory ci
LEFT JOIN sales_channels sc ON ci.channel_id = sc.id
LEFT JOIN warehouses w ON ci.warehouse_id = w.id
LEFT JOIN products p ON ci.product_id = p.id
LIMIT 10;

-- ============================================================================
-- 3. CHECK PRODUCT_CHANNEL_SETTINGS TABLE
-- ============================================================================
SELECT '=== PRODUCT_CHANNEL_SETTINGS TABLE STATUS ===' as section;

-- Check if table exists
SELECT EXISTS (
    SELECT FROM information_schema.tables
    WHERE table_schema = 'public'
    AND table_name = 'product_channel_settings'
) as table_exists;

-- If exists, show count and sample
SELECT
    COUNT(*) as total_settings,
    COUNT(DISTINCT product_id) as unique_products,
    COUNT(DISTINCT channel_id) as unique_channels
FROM product_channel_settings;

-- ============================================================================
-- 4. CHECK INVENTORY_SUMMARY FOR COMPARISON
-- ============================================================================
SELECT '=== INVENTORY_SUMMARY COMPARISON ===' as section;

SELECT
    p.sku,
    p.name,
    w.code as warehouse_code,
    invs.total_quantity,
    invs.available_quantity,
    invs.reserved_quantity,
    COALESCE(ci.allocated_quantity, 0) as d2c_allocated,
    COALESCE(ci.reserved_quantity, 0) as d2c_reserved
FROM inventory_summary invs
JOIN products p ON invs.product_id = p.id
JOIN warehouses w ON invs.warehouse_id = w.id
LEFT JOIN sales_channels sc ON sc.code = 'D2C'
LEFT JOIN channel_inventory ci ON ci.product_id = invs.product_id
    AND ci.warehouse_id = invs.warehouse_id
    AND ci.channel_id = sc.id
WHERE invs.available_quantity > 0
ORDER BY p.sku
LIMIT 20;

-- ============================================================================
-- 5. CHECK ALLOCATION_RULES FOR D2C
-- ============================================================================
SELECT '=== D2C ALLOCATION RULES ===' as section;

SELECT
    id,
    name,
    channel_code,
    allocation_type,
    priority,
    is_active,
    created_at
FROM allocation_rules
WHERE channel_code IN ('D2C', 'ALL')
AND is_active = true
ORDER BY priority;

-- ============================================================================
-- 6. SUMMARY & RECOMMENDATIONS
-- ============================================================================
SELECT '=== SUMMARY ===' as section;

WITH status_check AS (
    SELECT
        (SELECT COUNT(*) FROM sales_channels WHERE code = 'D2C' OR channel_type LIKE '%D2C%') as d2c_channel_exists,
        (SELECT COUNT(*) FROM channel_inventory) as channel_inventory_count,
        (SELECT COUNT(*) FROM allocation_rules WHERE channel_code = 'D2C' AND is_active = true) as d2c_rules_count,
        (SELECT COUNT(*) FROM inventory_summary WHERE available_quantity > 0) as products_with_stock
)
SELECT
    CASE WHEN d2c_channel_exists > 0 THEN '✅ D2C Channel exists' ELSE '❌ D2C Channel MISSING' END as d2c_channel_status,
    CASE WHEN channel_inventory_count > 0 THEN '✅ ChannelInventory has data' ELSE '❌ ChannelInventory is EMPTY' END as channel_inventory_status,
    CASE WHEN d2c_rules_count > 0 THEN '✅ D2C allocation rules exist' ELSE '❌ D2C allocation rules MISSING' END as allocation_rules_status,
    products_with_stock || ' products have stock in InventorySummary' as inventory_status
FROM status_check;

-- ============================================================================
-- IF D2C CHANNEL IS MISSING, RUN THIS TO CREATE IT:
-- ============================================================================
/*
INSERT INTO sales_channels (
    id, code, name, description, channel_type, status,
    allow_cod, allow_prepaid, min_order_value, max_order_value,
    default_payment_terms, is_active, created_at, updated_at
)
SELECT
    gen_random_uuid(),
    'D2C',
    'D2C Website',
    'Direct to Consumer website orders',
    'D2C_WEBSITE',
    'ACTIVE',
    true,  -- allow_cod
    true,  -- allow_prepaid
    0,     -- min_order_value
    500000, -- max_order_value
    'PREPAID',
    true,
    NOW(),
    NOW()
WHERE NOT EXISTS (SELECT 1 FROM sales_channels WHERE code = 'D2C');
*/

-- ============================================================================
-- IF CHANNEL_INVENTORY IS EMPTY, RUN THIS TO ALLOCATE INVENTORY TO D2C:
-- ============================================================================
/*
-- This allocates 100% of current InventorySummary to D2C channel
INSERT INTO channel_inventory (
    id, channel_id, warehouse_id, product_id, variant_id,
    allocated_quantity, buffer_quantity, reserved_quantity,
    marketplace_quantity, last_synced_at, is_active, created_at, updated_at
)
SELECT
    gen_random_uuid(),
    (SELECT id FROM sales_channels WHERE code = 'D2C' LIMIT 1),
    invs.warehouse_id,
    invs.product_id,
    invs.variant_id,
    invs.available_quantity,  -- Allocate all available to D2C
    5,  -- Buffer (safety stock)
    0,  -- Reserved
    0,  -- Marketplace quantity
    NULL,
    true,
    NOW(),
    NOW()
FROM inventory_summary invs
WHERE invs.available_quantity > 0
AND NOT EXISTS (
    SELECT 1 FROM channel_inventory ci
    WHERE ci.product_id = invs.product_id
    AND ci.warehouse_id = invs.warehouse_id
    AND ci.channel_id = (SELECT id FROM sales_channels WHERE code = 'D2C' LIMIT 1)
);
*/
