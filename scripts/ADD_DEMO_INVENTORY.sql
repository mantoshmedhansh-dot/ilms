-- ============================================================================
-- ADD DEMO INVENTORY - For D2C Storefront Testing
-- Run in Supabase SQL Editor
-- Created: 2026-01-19
-- ============================================================================

-- STEP 1: Check existing warehouses
SELECT id, code, name FROM warehouses WHERE is_active = true LIMIT 1;

-- STEP 2: Create warehouse if none exists
INSERT INTO warehouses (id, code, name, warehouse_type, address_line1, city, state, pincode, country, is_active, is_default, can_fulfill_orders)
SELECT
    gen_random_uuid(), 'MAIN-WH', 'Main Warehouse', 'MAIN', '123 Industrial Area', 'Delhi', 'Delhi', '110001', 'India', true, true, true
WHERE NOT EXISTS (SELECT 1 FROM warehouses WHERE is_active = true);

-- STEP 3: Add inventory for flagship water purifiers
INSERT INTO inventory_summary (id, warehouse_id, product_id, total_quantity, available_quantity, reserved_quantity, allocated_quantity, damaged_quantity, in_transit_quantity, reorder_level, minimum_stock, maximum_stock)
SELECT gen_random_uuid(), w.id, p.id, 25, 25, 0, 0, 0, 0, 3, 2, 50
FROM products p, warehouses w WHERE p.slug = 'aquapurite-i-elitz' AND w.is_active = true LIMIT 1
ON CONFLICT (warehouse_id, product_id, variant_id) DO UPDATE SET total_quantity = 25, available_quantity = 25;

INSERT INTO inventory_summary (id, warehouse_id, product_id, total_quantity, available_quantity, reserved_quantity, allocated_quantity, damaged_quantity, in_transit_quantity, reorder_level, minimum_stock, maximum_stock)
SELECT gen_random_uuid(), w.id, p.id, 30, 30, 0, 0, 0, 0, 5, 2, 60
FROM products p, warehouses w WHERE p.slug = 'aquapurite-i-premiuo' AND w.is_active = true LIMIT 1
ON CONFLICT (warehouse_id, product_id, variant_id) DO UPDATE SET total_quantity = 30, available_quantity = 30;

INSERT INTO inventory_summary (id, warehouse_id, product_id, total_quantity, available_quantity, reserved_quantity, allocated_quantity, damaged_quantity, in_transit_quantity, reorder_level, minimum_stock, maximum_stock)
SELECT gen_random_uuid(), w.id, p.id, 40, 40, 0, 0, 0, 0, 5, 3, 80
FROM products p, warehouses w WHERE p.slug = 'aquapurite-blitz' AND w.is_active = true LIMIT 1
ON CONFLICT (warehouse_id, product_id, variant_id) DO UPDATE SET total_quantity = 40, available_quantity = 40;

INSERT INTO inventory_summary (id, warehouse_id, product_id, total_quantity, available_quantity, reserved_quantity, allocated_quantity, damaged_quantity, in_transit_quantity, reorder_level, minimum_stock, maximum_stock)
SELECT gen_random_uuid(), w.id, p.id, 50, 50, 0, 0, 0, 0, 5, 3, 100
FROM products p, warehouses w WHERE p.slug = 'aquapurite-optima' AND w.is_active = true LIMIT 1
ON CONFLICT (warehouse_id, product_id, variant_id) DO UPDATE SET total_quantity = 50, available_quantity = 50;

INSERT INTO inventory_summary (id, warehouse_id, product_id, total_quantity, available_quantity, reserved_quantity, allocated_quantity, damaged_quantity, in_transit_quantity, reorder_level, minimum_stock, maximum_stock)
SELECT gen_random_uuid(), w.id, p.id, 45, 45, 0, 0, 0, 0, 5, 3, 90
FROM products p, warehouses w WHERE p.slug = 'aquapurite-neura' AND w.is_active = true LIMIT 1
ON CONFLICT (warehouse_id, product_id, variant_id) DO UPDATE SET total_quantity = 45, available_quantity = 45;

INSERT INTO inventory_summary (id, warehouse_id, product_id, total_quantity, available_quantity, reserved_quantity, allocated_quantity, damaged_quantity, in_transit_quantity, reorder_level, minimum_stock, maximum_stock)
SELECT gen_random_uuid(), w.id, p.id, 60, 60, 0, 0, 0, 0, 8, 5, 120
FROM products p, warehouses w WHERE p.slug = 'aquapurite-premiuo-uv' AND w.is_active = true LIMIT 1
ON CONFLICT (warehouse_id, product_id, variant_id) DO UPDATE SET total_quantity = 60, available_quantity = 60;

-- STEP 4: Add inventory for filters/accessories
INSERT INTO inventory_summary (id, warehouse_id, product_id, total_quantity, available_quantity, reserved_quantity, allocated_quantity, damaged_quantity, in_transit_quantity, reorder_level, minimum_stock, maximum_stock)
SELECT gen_random_uuid(), w.id, p.id, 200, 200, 0, 0, 0, 0, 20, 10, 500
FROM products p, warehouses w WHERE p.slug = 'pre-carbon-block-regular-10-economical' AND w.is_active = true LIMIT 1
ON CONFLICT (warehouse_id, product_id, variant_id) DO UPDATE SET total_quantity = 200, available_quantity = 200;

INSERT INTO inventory_summary (id, warehouse_id, product_id, total_quantity, available_quantity, reserved_quantity, allocated_quantity, damaged_quantity, in_transit_quantity, reorder_level, minimum_stock, maximum_stock)
SELECT gen_random_uuid(), w.id, p.id, 200, 200, 0, 0, 0, 0, 20, 10, 500
FROM products p, warehouses w WHERE p.slug = 'alkaline-mineral-block-economical' AND w.is_active = true LIMIT 1
ON CONFLICT (warehouse_id, product_id, variant_id) DO UPDATE SET total_quantity = 200, available_quantity = 200;

INSERT INTO inventory_summary (id, warehouse_id, product_id, total_quantity, available_quantity, reserved_quantity, allocated_quantity, damaged_quantity, in_transit_quantity, reorder_level, minimum_stock, maximum_stock)
SELECT gen_random_uuid(), w.id, p.id, 200, 200, 0, 0, 0, 0, 20, 10, 500
FROM products p, warehouses w WHERE p.slug = 'post-carbon-copper-economical' AND w.is_active = true LIMIT 1
ON CONFLICT (warehouse_id, product_id, variant_id) DO UPDATE SET total_quantity = 200, available_quantity = 200;

INSERT INTO inventory_summary (id, warehouse_id, product_id, total_quantity, available_quantity, reserved_quantity, allocated_quantity, damaged_quantity, in_transit_quantity, reorder_level, minimum_stock, maximum_stock)
SELECT gen_random_uuid(), w.id, p.id, 150, 150, 0, 0, 0, 0, 15, 10, 300
FROM products p, warehouses w WHERE p.slug = 'ro-membrane-regular-80gpd-economical' AND w.is_active = true LIMIT 1
ON CONFLICT (warehouse_id, product_id, variant_id) DO UPDATE SET total_quantity = 150, available_quantity = 150;

-- STEP 5: Mark products as featured/bestseller
UPDATE products SET is_featured = true, is_bestseller = true WHERE slug IN ('aquapurite-i-elitz', 'aquapurite-blitz');
UPDATE products SET is_bestseller = true WHERE slug IN ('aquapurite-optima', 'aquapurite-neura', 'aquapurite-premiuo-uv');
UPDATE products SET is_new_arrival = true WHERE slug IN ('aquapurite-i-premiuo', 'aquapurite-i-elitz');
UPDATE products SET is_featured = true WHERE slug IN ('ro-membrane-regular-80gpd-economical', 'alkaline-mineral-block-economical');

-- STEP 6: Verify
SELECT 'Demo inventory added' as status;
SELECT p.name, p.mrp, COALESCE(inv.available_quantity, 0) as stock, p.is_featured, p.is_bestseller
FROM products p
LEFT JOIN inventory_summary inv ON p.id = inv.product_id
WHERE p.slug IN ('aquapurite-i-elitz', 'aquapurite-blitz', 'aquapurite-optima', 'aquapurite-neura', 'aquapurite-premiuo-uv')
ORDER BY p.mrp DESC;
