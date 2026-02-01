-- ============================================================
-- MIGRATION PART 6: INVENTORY SUMMARY TABLE
-- Run LAST - requires warehouses and products tables
-- ============================================================

-- Create inventory_summary table (matches the model)
CREATE TABLE IF NOT EXISTS inventory_summary (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    warehouse_id UUID NOT NULL REFERENCES warehouses(id),
    product_id UUID NOT NULL REFERENCES products(id),
    variant_id UUID REFERENCES product_variants(id),

    -- Stock levels
    total_quantity INTEGER DEFAULT 0,
    available_quantity INTEGER DEFAULT 0,
    reserved_quantity INTEGER DEFAULT 0,
    allocated_quantity INTEGER DEFAULT 0,
    damaged_quantity INTEGER DEFAULT 0,
    in_transit_quantity INTEGER DEFAULT 0,

    -- Thresholds
    reorder_level INTEGER DEFAULT 10,
    minimum_stock INTEGER DEFAULT 5,
    maximum_stock INTEGER DEFAULT 1000,

    -- Valuation
    average_cost FLOAT DEFAULT 0,
    total_value FLOAT DEFAULT 0,

    -- Last activity
    last_stock_in_date TIMESTAMP,
    last_stock_out_date TIMESTAMP,
    last_audit_date TIMESTAMP,

    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),

    UNIQUE(warehouse_id, product_id, variant_id)
);

CREATE INDEX IF NOT EXISTS idx_inventory_summary_warehouse ON inventory_summary(warehouse_id);
CREATE INDEX IF NOT EXISTS idx_inventory_summary_product ON inventory_summary(product_id);

-- Create a convenience view named 'inventory' for backward compatibility
CREATE OR REPLACE VIEW inventory AS
SELECT
    product_id,
    (SELECT sku FROM products WHERE id = product_id) as sku,
    available_quantity as quantity_available,
    reserved_quantity,
    warehouse_id,
    TRUE as is_active
FROM inventory_summary;

SELECT 'Part 6: Inventory summary table created successfully!' AS result;
SELECT 'ALL MIGRATIONS COMPLETED!' AS final_result;
