-- ============================================================================
-- RESET DEMO INVENTORY - Set all inventory back to zero
-- Run in Supabase SQL Editor
-- ============================================================================

-- Reset all inventory quantities to zero
UPDATE inventory_summary
SET
    total_quantity = 0,
    available_quantity = 0,
    reserved_quantity = 0,
    allocated_quantity = 0,
    damaged_quantity = 0,
    in_transit_quantity = 0;

-- Remove featured/bestseller/new_arrival flags
UPDATE products
SET
    is_featured = false,
    is_bestseller = false,
    is_new_arrival = false
WHERE slug IN (
    'aquapurite-i-elitz',
    'aquapurite-i-premiuo',
    'aquapurite-blitz',
    'aquapurite-optima',
    'aquapurite-neura',
    'aquapurite-premiuo-uv',
    'pre-carbon-block-regular-10-economical',
    'alkaline-mineral-block-economical',
    'post-carbon-copper-economical',
    'ro-membrane-regular-80gpd-economical'
);

-- Verify
SELECT 'Inventory reset complete' as status;
SELECT p.name, COALESCE(inv.available_quantity, 0) as stock
FROM products p
LEFT JOIN inventory_summary inv ON p.id = inv.product_id
WHERE p.slug IN ('aquapurite-i-elitz', 'aquapurite-blitz', 'aquapurite-optima')
ORDER BY p.mrp DESC;
