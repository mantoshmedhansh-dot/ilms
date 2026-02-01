-- ============================================================================
-- ADD DEFAULT D2C ALLOCATION RULE
-- Run in Supabase SQL Editor
-- Created: 2026-01-19
-- ============================================================================

-- First, check if we have a warehouse
SELECT id, code, name, is_active, can_fulfill_orders
FROM warehouses
WHERE is_active = true
LIMIT 5;

-- Check existing allocation rules
SELECT id, name, channel_code, allocation_type, priority, is_active
FROM allocation_rules
ORDER BY priority;

-- ============================================================================
-- CREATE DEFAULT D2C ALLOCATION RULE
-- ============================================================================
-- This rule will use NEAREST allocation (by warehouse priority)
-- for all D2C orders with any payment mode

INSERT INTO allocation_rules (
    id,
    name,
    description,
    channel_code,
    allocation_type,
    priority,
    priority_factors,
    allow_split,
    max_splits,
    is_active,
    created_at,
    updated_at
)
SELECT
    gen_random_uuid(),
    'D2C Default - Nearest Warehouse',
    'Default allocation rule for D2C website orders. Allocates to nearest serviceable warehouse by priority.',
    'D2C',
    'NEAREST',
    10,
    'PROXIMITY,INVENTORY',
    false,
    1,
    true,
    NOW(),
    NOW()
WHERE NOT EXISTS (
    SELECT 1 FROM allocation_rules
    WHERE channel_code = 'D2C' AND is_active = true
);

-- Also create an ALL channel fallback rule (lowest priority)
INSERT INTO allocation_rules (
    id,
    name,
    description,
    channel_code,
    allocation_type,
    priority,
    priority_factors,
    allow_split,
    max_splits,
    is_active,
    created_at,
    updated_at
)
SELECT
    gen_random_uuid(),
    'Fallback - Nearest Warehouse',
    'Fallback allocation rule for all channels. Used when no channel-specific rule matches.',
    'ALL',
    'NEAREST',
    999,
    'PROXIMITY,INVENTORY',
    false,
    1,
    true,
    NOW(),
    NOW()
WHERE NOT EXISTS (
    SELECT 1 FROM allocation_rules
    WHERE channel_code = 'ALL' AND is_active = true
);

-- Verify rules created
SELECT id, name, channel_code, allocation_type, priority, is_active
FROM allocation_rules
WHERE is_active = true
ORDER BY priority;

-- ============================================================================
-- VERIFY WAREHOUSE SERVICEABILITY FOR DEMO PINCODE
-- ============================================================================
SELECT
    ws.pincode,
    w.code as warehouse_code,
    w.name as warehouse_name,
    ws.is_serviceable,
    ws.cod_available,
    ws.estimated_days,
    ws.priority
FROM warehouse_serviceability ws
JOIN warehouses w ON ws.warehouse_id = w.id
WHERE ws.pincode = '110001'
AND ws.is_serviceable = true
AND ws.is_active = true
ORDER BY ws.priority;
