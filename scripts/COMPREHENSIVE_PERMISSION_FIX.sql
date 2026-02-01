-- ============================================================================
-- COMPREHENSIVE STRUCTURAL FIX FOR PERMISSION MODULE
-- Run this ENTIRE script in Supabase SQL Editor
-- Created: 2026-01-19
-- ============================================================================

-- ============================================================================
-- PART 1: CREATE MISSING MODULES
-- The seed_rbac.py creates permissions for modules that don't exist
-- ============================================================================

-- Finance sub-modules that are referenced in permissions but don't exist
INSERT INTO modules (id, name, code, description, icon, sort_order, is_active, created_at, updated_at)
VALUES
    (gen_random_uuid(), 'Chart of Accounts', 'accounts', 'Ledger accounts management', 'account_tree', 20, true, NOW(), NOW()),
    (gen_random_uuid(), 'Journal Entries', 'journals', 'Journal entry management', 'receipt_long', 21, true, NOW(), NOW()),
    (gen_random_uuid(), 'Fixed Assets', 'assets', 'Asset register and depreciation', 'business', 22, true, NOW(), NOW()),
    (gen_random_uuid(), 'Bank Reconciliation', 'bank_recon', 'Bank statement reconciliation', 'account_balance_wallet', 23, true, NOW(), NOW()),
    (gen_random_uuid(), 'Cost Centers', 'cost_centers', 'Cost center management', 'pie_chart', 24, true, NOW(), NOW()),
    (gen_random_uuid(), 'Financial Periods', 'periods', 'Accounting period management', 'date_range', 25, true, NOW(), NOW()),
    (gen_random_uuid(), 'GST', 'gst', 'GST returns and compliance', 'receipt', 26, true, NOW(), NOW()),
    (gen_random_uuid(), 'TDS', 'tds', 'TDS deduction and filing', 'description', 27, true, NOW(), NOW())
ON CONFLICT (code) DO NOTHING;

-- ============================================================================
-- PART 2: MERGE DUPLICATE MODULES (UPPERCASE → lowercase)
-- ============================================================================

-- Step 2a: Update permissions pointing to UPPERCASE modules to point to lowercase
UPDATE permissions p
SET module_id = lower_m.id
FROM modules upper_m, modules lower_m
WHERE p.module_id = upper_m.id
  AND upper_m.code ~ '^[A-Z_]+$'  -- Uppercase module
  AND lower_m.code = LOWER(upper_m.code)  -- Matching lowercase
  AND upper_m.id != lower_m.id;  -- Different records

-- Step 2b: Delete uppercase duplicate modules (now orphaned)
DELETE FROM modules
WHERE code ~ '^[A-Z_]+$'  -- Uppercase
  AND LOWER(code) IN (SELECT code FROM modules WHERE code = LOWER(code) AND code !~ '^[A-Z_]+$');

-- ============================================================================
-- PART 3: FIX PERMISSIONS WITH NULL module_id
-- Derive module from permission code (e.g., "products:view" → module "products")
-- ============================================================================

-- Update module_id based on permission code prefix
UPDATE permissions p
SET module_id = m.id
FROM modules m
WHERE p.module_id IS NULL
  AND p.code LIKE '%:%'
  AND m.code = SPLIT_PART(p.code, ':', 1);

-- ============================================================================
-- PART 4: FIX PERMISSIONS WITH NULL action
-- Derive action from permission code (e.g., "products:view" → action "view")
-- ============================================================================

UPDATE permissions
SET action = SPLIT_PART(code, ':', 2)
WHERE action IS NULL
  AND code LIKE '%:%';

-- For any remaining NULLs, derive from name
UPDATE permissions
SET action = CASE
    WHEN LOWER(name) LIKE '%view%' THEN 'view'
    WHEN LOWER(name) LIKE '%create%' OR LOWER(name) LIKE '%add%' THEN 'create'
    WHEN LOWER(name) LIKE '%update%' OR LOWER(name) LIKE '%edit%' THEN 'update'
    WHEN LOWER(name) LIKE '%delete%' OR LOWER(name) LIKE '%remove%' THEN 'delete'
    WHEN LOWER(name) LIKE '%approve%' THEN 'approve'
    ELSE 'view'
END
WHERE action IS NULL;

-- ============================================================================
-- PART 5: STRUCTURAL CONSTRAINTS - PREVENT FUTURE ISSUES
-- ============================================================================

-- 5a: Add unique index on LOWER(code) for modules (case-insensitive uniqueness)
DROP INDEX IF EXISTS idx_modules_code_lower_unique;
CREATE UNIQUE INDEX idx_modules_code_lower_unique ON modules (LOWER(code));

-- 5b: Add NOT NULL constraints to permissions (if not already)
-- First ensure no NULLs exist
DO $$
BEGIN
    -- Check for remaining NULLs
    IF EXISTS (SELECT 1 FROM permissions WHERE action IS NULL OR module_id IS NULL) THEN
        RAISE NOTICE 'Warning: Some permissions still have NULL action or module_id';
    ELSE
        -- Add constraints
        ALTER TABLE permissions ALTER COLUMN action SET NOT NULL;
        ALTER TABLE permissions ALTER COLUMN module_id SET NOT NULL;
        RAISE NOTICE 'NOT NULL constraints added successfully';
    END IF;
END $$;

-- ============================================================================
-- PART 6: VERIFICATION QUERIES
-- ============================================================================

-- Check for any remaining issues
SELECT 'Permissions with NULL action' as issue, COUNT(*) as count FROM permissions WHERE action IS NULL
UNION ALL
SELECT 'Permissions with NULL module_id', COUNT(*) FROM permissions WHERE module_id IS NULL
UNION ALL
SELECT 'Duplicate modules (case-insensitive)', COUNT(*) FROM (
    SELECT LOWER(code) FROM modules GROUP BY LOWER(code) HAVING COUNT(*) > 1
) x
UNION ALL
SELECT 'Total modules', COUNT(*) FROM modules
UNION ALL
SELECT 'Total permissions', COUNT(*) FROM permissions;

-- Show all modules
SELECT id, name, code, sort_order, is_active FROM modules ORDER BY sort_order, name;

-- Show permissions by module
SELECT
    m.code as module_code,
    COUNT(p.id) as permission_count
FROM modules m
LEFT JOIN permissions p ON p.module_id = m.id
GROUP BY m.code
ORDER BY m.code;

-- ============================================================================
-- DONE! If all counts show 0 for issues, the fix is complete.
-- ============================================================================
