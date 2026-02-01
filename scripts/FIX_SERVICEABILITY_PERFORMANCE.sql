-- ============================================================================
-- FIX SERVICEABILITY PERFORMANCE - Add missing pincode index
-- Run in Supabase SQL Editor
-- Created: 2026-01-19
--
-- ISSUE: Pincode lookups do full table scan (200-500ms)
-- FIX: Add index on pincode column for instant lookups (<5ms)
-- ============================================================================

-- STEP 1: Check current indexes
SELECT indexname, indexdef
FROM pg_indexes
WHERE tablename = 'warehouse_serviceability';

-- STEP 2: Add pincode index (if not exists)
CREATE INDEX IF NOT EXISTS ix_warehouse_serviceability_pincode
ON warehouse_serviceability (pincode);

-- STEP 3: Add composite index for common query pattern
-- This covers: WHERE pincode = ? AND is_serviceable = true AND is_active = true
CREATE INDEX IF NOT EXISTS ix_warehouse_serviceability_pincode_active
ON warehouse_serviceability (pincode, is_serviceable, is_active);

-- STEP 4: Analyze table to update query planner statistics
ANALYZE warehouse_serviceability;

-- STEP 5: Verify indexes were created
SELECT indexname, indexdef
FROM pg_indexes
WHERE tablename = 'warehouse_serviceability';

-- STEP 6: Test query performance (should show Index Scan, not Seq Scan)
EXPLAIN ANALYZE
SELECT * FROM warehouse_serviceability
WHERE pincode = '110001'
  AND is_serviceable = true
  AND is_active = true;

SELECT 'Serviceability performance fix complete' as status;
