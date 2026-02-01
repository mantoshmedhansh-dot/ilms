-- STRUCTURAL FIX: Permissions table - Enforce NOT NULL constraints
-- Run this in Supabase SQL Editor AFTER running fix_permissions_null_values.sql
-- Created: 2026-01-19

-- ==================== STEP 1: Verify no NULL values remain ====================
-- MUST return 0 rows before proceeding

SELECT id, name, code, action, module_id
FROM permissions
WHERE action IS NULL OR module_id IS NULL;

-- If any rows returned, run fix_permissions_null_values.sql first!

-- ==================== STEP 2: Add NOT NULL constraints ====================
-- This makes the fix STRUCTURAL - prevents future NULL values

-- Fix action column
ALTER TABLE permissions
ALTER COLUMN action SET NOT NULL;

-- Fix module_id column
ALTER TABLE permissions
ALTER COLUMN module_id SET NOT NULL;

-- ==================== STEP 3: Verify constraints are in place ====================

SELECT
    column_name,
    is_nullable,
    data_type
FROM information_schema.columns
WHERE table_name = 'permissions'
  AND column_name IN ('action', 'module_id');

-- Should show:
-- action     | NO  | character varying
-- module_id  | NO  | uuid

-- ==================== DONE ====================
-- Now the database will reject any INSERT/UPDATE with NULL action or module_id
-- This is the STRUCTURAL fix that prevents the issue from recurring
