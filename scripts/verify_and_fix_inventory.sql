-- Script to verify and fix inventory_summary for D2C allocation
-- Run this on Supabase SQL Editor

-- Step 1: Check current inventory and warehouse mapping
SELECT
    inv.id as inventory_id,
    inv.warehouse_id,
    w.code as warehouse_code,
    w.name as warehouse_name,
    inv.product_id,
    p.sku,
    p.name as product_name,
    inv.total_quantity,
    inv.available_quantity,
    inv.reserved_quantity,
    inv.allocated_quantity
FROM inventory_summary inv
LEFT JOIN warehouses w ON inv.warehouse_id = w.id
LEFT JOIN products p ON inv.product_id = p.id
WHERE p.sku = 'WPRAOPT001'  -- Aquapurite Optima
ORDER BY w.code;

-- Step 2: Get the Delhi warehouse ID
SELECT id, code, name, city, is_active, can_fulfill_orders
FROM warehouses
WHERE code = 'WH-DEL-001';
-- Expected: c0f09920-b71a-497b-ba03-c54be4bca7e1

-- Step 3: Get the Aquapurite Optima product ID
SELECT id, sku, name, is_active
FROM products
WHERE sku = 'WPRAOPT001';
-- Expected: 2976506e-edc9-4ab2-b35d-b1c1681e4f53

-- Step 4: Check if inventory exists for the CORRECT warehouse + product combination
SELECT
    inv.*,
    w.code as warehouse_code,
    p.sku
FROM inventory_summary inv
JOIN warehouses w ON inv.warehouse_id = w.id
JOIN products p ON inv.product_id = p.id
WHERE w.code = 'WH-DEL-001'
  AND p.sku = 'WPRAOPT001';

-- Step 5: If no record found in Step 4, INSERT the correct record
-- ONLY RUN THIS IF Step 4 returns 0 rows

-- First, check if there's any inventory for this product in ANY warehouse:
SELECT
    w.code,
    w.name,
    inv.warehouse_id,
    inv.product_id,
    inv.available_quantity
FROM inventory_summary inv
JOIN warehouses w ON inv.warehouse_id = w.id
JOIN products p ON inv.product_id = p.id
WHERE p.sku = 'WPRAOPT001';

-- If inventory exists in wrong warehouse, you can either:
-- A) Update the warehouse_id to Delhi warehouse
-- B) Insert a new record for Delhi warehouse

-- Option A: Update existing record to Delhi warehouse (if only one record exists)
/*
UPDATE inventory_summary
SET warehouse_id = 'c0f09920-b71a-497b-ba03-c54be4bca7e1'  -- Delhi warehouse UUID
WHERE product_id = '2976506e-edc9-4ab2-b35d-b1c1681e4f53'  -- Aquapurite Optima product UUID
  AND warehouse_id != 'c0f09920-b71a-497b-ba03-c54be4bca7e1';  -- Not already Delhi
*/

-- Option B: Insert new record for Delhi warehouse
/*
INSERT INTO inventory_summary (
    id, warehouse_id, product_id,
    total_quantity, available_quantity, reserved_quantity, allocated_quantity
)
SELECT
    gen_random_uuid(),
    'c0f09920-b71a-497b-ba03-c54be4bca7e1',  -- Delhi warehouse UUID
    '2976506e-edc9-4ab2-b35d-b1c1681e4f53',  -- Aquapurite Optima product UUID
    100,  -- total_quantity
    100,  -- available_quantity
    0,    -- reserved_quantity
    0     -- allocated_quantity
WHERE NOT EXISTS (
    SELECT 1 FROM inventory_summary
    WHERE warehouse_id = 'c0f09920-b71a-497b-ba03-c54be4bca7e1'
      AND product_id = '2976506e-edc9-4ab2-b35d-b1c1681e4f53'
);
*/
