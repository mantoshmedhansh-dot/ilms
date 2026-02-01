-- FIX: Add inventory to Delhi warehouse for Aquapurite Optima
-- This ensures D2C orders can be allocated to Delhi warehouse

-- The allocation service queries inventory_summary with BOTH warehouse_id AND product_id
-- If the inventory exists in a different warehouse, allocation fails even though storefront shows stock

-- Step 1: Get correct IDs (run this first to verify)
SELECT
    (SELECT id FROM warehouses WHERE code = 'WH-DEL-001') as delhi_warehouse_id,
    (SELECT id FROM products WHERE sku = 'WPRAOPT001') as aquapurite_optima_id;

-- Step 2: Check current inventory for this product (in any warehouse)
SELECT
    inv.id,
    w.code as warehouse_code,
    p.sku,
    inv.available_quantity
FROM inventory_summary inv
JOIN warehouses w ON inv.warehouse_id = w.id
JOIN products p ON inv.product_id = p.id
WHERE p.sku = 'WPRAOPT001';

-- Step 3: Insert inventory for Delhi warehouse (UPSERT - insert if not exists)
-- Run this to fix the issue:
INSERT INTO inventory_summary (
    id,
    warehouse_id,
    product_id,
    total_quantity,
    available_quantity,
    reserved_quantity,
    allocated_quantity
)
VALUES (
    gen_random_uuid(),
    (SELECT id FROM warehouses WHERE code = 'WH-DEL-001'),
    (SELECT id FROM products WHERE sku = 'WPRAOPT001'),
    100,
    100,
    0,
    0
)
ON CONFLICT (warehouse_id, product_id)
DO UPDATE SET
    available_quantity = EXCLUDED.available_quantity + inventory_summary.available_quantity,
    total_quantity = EXCLUDED.total_quantity + inventory_summary.total_quantity;

-- Step 4: Verify the inventory was added/updated
SELECT
    inv.id,
    w.code as warehouse_code,
    p.sku,
    inv.total_quantity,
    inv.available_quantity
FROM inventory_summary inv
JOIN warehouses w ON inv.warehouse_id = w.id
JOIN products p ON inv.product_id = p.id
WHERE w.code = 'WH-DEL-001' AND p.sku = 'WPRAOPT001';
