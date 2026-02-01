-- ============================================================================
-- FINAL FIX FOR MODULES - Based on actual production data
-- Run this in Supabase SQL Editor
-- Created: 2026-01-19
-- ============================================================================

-- ============================================================================
-- STEP 1: Create lowercase versions of uppercase-only modules
-- ============================================================================

-- These UPPERCASE modules exist but have no lowercase equivalent
INSERT INTO modules (id, name, code, description, icon, sort_order, is_active, created_at, updated_at)
VALUES
    (gen_random_uuid(), 'Accounting', 'accounting', 'General accounting functions', 'calculate', 30, true, NOW(), NOW()),
    (gen_random_uuid(), 'Billing', 'billing', 'Billing and invoicing', 'receipt', 31, true, NOW(), NOW()),
    (gen_random_uuid(), 'Customers', 'customers', 'Customer management', 'people', 32, true, NOW(), NOW()),
    (gen_random_uuid(), 'GRN', 'grn', 'Goods Receipt Notes', 'inventory_2', 33, true, NOW(), NOW()),
    (gen_random_uuid(), 'Purchase', 'purchase', 'Purchase management', 'shopping_cart', 34, true, NOW(), NOW()),
    (gen_random_uuid(), 'Role Management', 'role_mgmt', 'Role management', 'admin_panel_settings', 35, true, NOW(), NOW()),
    (gen_random_uuid(), 'User Management', 'user_mgmt', 'User management', 'manage_accounts', 36, true, NOW(), NOW())
ON CONFLICT (code) DO NOTHING;

-- ============================================================================
-- STEP 2: Move permissions from UPPERCASE modules to lowercase
-- ============================================================================

-- ACCOUNTING -> accounting
UPDATE permissions SET module_id = (SELECT id FROM modules WHERE code = 'accounting')
WHERE module_id = (SELECT id FROM modules WHERE code = 'ACCOUNTING');

-- BILLING -> billing
UPDATE permissions SET module_id = (SELECT id FROM modules WHERE code = 'billing')
WHERE module_id = (SELECT id FROM modules WHERE code = 'BILLING');

-- CUSTOMERS -> customers
UPDATE permissions SET module_id = (SELECT id FROM modules WHERE code = 'customers')
WHERE module_id = (SELECT id FROM modules WHERE code = 'CUSTOMERS');

-- GRN -> grn
UPDATE permissions SET module_id = (SELECT id FROM modules WHERE code = 'grn')
WHERE module_id = (SELECT id FROM modules WHERE code = 'GRN');

-- PURCHASE -> purchase
UPDATE permissions SET module_id = (SELECT id FROM modules WHERE code = 'purchase')
WHERE module_id = (SELECT id FROM modules WHERE code = 'PURCHASE');

-- ROLE_MGMT -> role_mgmt
UPDATE permissions SET module_id = (SELECT id FROM modules WHERE code = 'role_mgmt')
WHERE module_id = (SELECT id FROM modules WHERE code = 'ROLE_MGMT');

-- USER_MGMT -> user_mgmt
UPDATE permissions SET module_id = (SELECT id FROM modules WHERE code = 'user_mgmt')
WHERE module_id = (SELECT id FROM modules WHERE code = 'USER_MGMT');

-- ============================================================================
-- STEP 3: Delete UPPERCASE modules (now empty)
-- ============================================================================

DELETE FROM modules WHERE code = 'ACCOUNTING';
DELETE FROM modules WHERE code = 'BILLING';
DELETE FROM modules WHERE code = 'CUSTOMERS';
DELETE FROM modules WHERE code = 'GRN';
DELETE FROM modules WHERE code = 'PURCHASE';
DELETE FROM modules WHERE code = 'ROLE_MGMT';
DELETE FROM modules WHERE code = 'USER_MGMT';

-- ============================================================================
-- STEP 4: Fix permissions with NULL module_id
-- ============================================================================

-- Update module_id based on permission code prefix
UPDATE permissions p
SET module_id = m.id
FROM modules m
WHERE p.module_id IS NULL
  AND p.code LIKE '%:%'
  AND m.code = LOWER(SPLIT_PART(p.code, ':', 1));

-- ============================================================================
-- STEP 5: Fix permissions with NULL action
-- ============================================================================

UPDATE permissions
SET action = SPLIT_PART(code, ':', 2)
WHERE action IS NULL AND code LIKE '%:%';

-- ============================================================================
-- STEP 6: Add unique index (case-insensitive) - STRUCTURAL
-- ============================================================================

DROP INDEX IF EXISTS idx_modules_code_lower_unique;
CREATE UNIQUE INDEX idx_modules_code_lower_unique ON modules (LOWER(code));

-- ============================================================================
-- STEP 7: Add NOT NULL constraints if no NULLs remain
-- ============================================================================

DO $$
DECLARE
    null_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO null_count FROM permissions WHERE action IS NULL OR module_id IS NULL;
    IF null_count = 0 THEN
        EXECUTE 'ALTER TABLE permissions ALTER COLUMN action SET NOT NULL';
        EXECUTE 'ALTER TABLE permissions ALTER COLUMN module_id SET NOT NULL';
        RAISE NOTICE 'NOT NULL constraints added successfully';
    ELSE
        RAISE NOTICE 'Warning: % permissions still have NULL values', null_count;
    END IF;
END $$;

-- ============================================================================
-- VERIFICATION
-- ============================================================================

-- Check for uppercase modules (should be 0)
SELECT 'Uppercase modules remaining' as check_name, COUNT(*) as count
FROM modules WHERE code ~ '^[A-Z_]+$'
UNION ALL
-- Check for NULL permissions
SELECT 'Permissions with NULL module_id', COUNT(*) FROM permissions WHERE module_id IS NULL
UNION ALL
SELECT 'Permissions with NULL action', COUNT(*) FROM permissions WHERE action IS NULL
UNION ALL
-- Totals
SELECT 'Total modules', COUNT(*) FROM modules
UNION ALL
SELECT 'Total permissions', COUNT(*) FROM permissions;

-- Show final module list
SELECT code, name,
    (SELECT COUNT(*) FROM permissions p WHERE p.module_id = m.id) as permission_count
FROM modules m
ORDER BY code;
