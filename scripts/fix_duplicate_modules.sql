-- Fix Duplicate Modules (uppercase vs lowercase)
-- Run this in Supabase SQL Editor
-- Created: 2026-01-19

-- ==================== STEP 1: View duplicates ====================
SELECT id, name, code, is_active, created_at
FROM modules
WHERE LOWER(code) IN (
    SELECT LOWER(code) FROM modules GROUP BY LOWER(code) HAVING COUNT(*) > 1
)
ORDER BY LOWER(code), code;

-- ==================== STEP 2: Update permissions to use lowercase modules ====================
-- For each duplicate, move permissions from UPPERCASE module to lowercase module

-- Update permissions pointing to UPPERCASE modules to point to lowercase versions
UPDATE permissions p
SET module_id = lower_m.id
FROM modules upper_m, modules lower_m
WHERE p.module_id = upper_m.id
  AND upper_m.code = UPPER(upper_m.code)  -- This is an uppercase module
  AND lower_m.code = LOWER(upper_m.code)  -- Find matching lowercase module
  AND upper_m.code != lower_m.code;        -- They're different records

-- ==================== STEP 3: Delete uppercase duplicate modules ====================
-- Only delete modules that have a lowercase counterpart

DELETE FROM modules
WHERE code = UPPER(code)  -- This is uppercase
  AND code != LOWER(code) -- Not already lowercase
  AND LOWER(code) IN (    -- Has a lowercase counterpart
    SELECT code FROM modules WHERE code = LOWER(code)
  );

-- ==================== STEP 4: Verify - should show no duplicates ====================
SELECT LOWER(code) as module_code, COUNT(*) as count
FROM modules
GROUP BY LOWER(code)
HAVING COUNT(*) > 1;

-- ==================== STEP 5: Check remaining modules ====================
SELECT id, name, code, is_active, sort_order
FROM modules
ORDER BY sort_order, name;

-- ==================== STEP 6: STRUCTURAL FIX - Add unique constraint ====================
-- This prevents future duplicates (case-insensitive)

-- Create a unique index on lowercase code
CREATE UNIQUE INDEX IF NOT EXISTS idx_modules_code_lower_unique
ON modules (LOWER(code));

-- ==================== STEP 7: Verify constraint exists ====================
SELECT indexname, indexdef
FROM pg_indexes
WHERE tablename = 'modules' AND indexname LIKE '%code%';

-- ==================== DONE ====================
-- Now the database will reject any INSERT/UPDATE that creates duplicate codes
-- Example: If 'products' exists, trying to insert 'PRODUCTS' will fail
