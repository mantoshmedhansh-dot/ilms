-- ============================================================================
-- FIX MODULES V2 - Handles existing unique index
-- Run this in Supabase SQL Editor
-- ============================================================================

-- ============================================================================
-- STEP 1: See current state
-- ============================================================================

SELECT code, name,
    (SELECT COUNT(*) FROM permissions p WHERE p.module_id = m.id) as perm_count
FROM modules m
ORDER BY code;

-- ============================================================================
-- STEP 2: Move permissions from UPPERCASE to lowercase (where lowercase exists)
-- ============================================================================

-- ACCOUNTING -> accounting (if accounting exists)
UPDATE permissions SET module_id = (SELECT id FROM modules WHERE code = 'accounting' LIMIT 1)
WHERE module_id = (SELECT id FROM modules WHERE code = 'ACCOUNTING' LIMIT 1)
  AND EXISTS (SELECT 1 FROM modules WHERE code = 'accounting');

-- BILLING -> billing
UPDATE permissions SET module_id = (SELECT id FROM modules WHERE code = 'billing' LIMIT 1)
WHERE module_id = (SELECT id FROM modules WHERE code = 'BILLING' LIMIT 1)
  AND EXISTS (SELECT 1 FROM modules WHERE code = 'billing');

-- CUSTOMERS -> customers
UPDATE permissions SET module_id = (SELECT id FROM modules WHERE code = 'customers' LIMIT 1)
WHERE module_id = (SELECT id FROM modules WHERE code = 'CUSTOMERS' LIMIT 1)
  AND EXISTS (SELECT 1 FROM modules WHERE code = 'customers');

-- GRN -> grn
UPDATE permissions SET module_id = (SELECT id FROM modules WHERE code = 'grn' LIMIT 1)
WHERE module_id = (SELECT id FROM modules WHERE code = 'GRN' LIMIT 1)
  AND EXISTS (SELECT 1 FROM modules WHERE code = 'grn');

-- PURCHASE -> purchase
UPDATE permissions SET module_id = (SELECT id FROM modules WHERE code = 'purchase' LIMIT 1)
WHERE module_id = (SELECT id FROM modules WHERE code = 'PURCHASE' LIMIT 1)
  AND EXISTS (SELECT 1 FROM modules WHERE code = 'purchase');

-- ROLE_MGMT -> role_mgmt
UPDATE permissions SET module_id = (SELECT id FROM modules WHERE code = 'role_mgmt' LIMIT 1)
WHERE module_id = (SELECT id FROM modules WHERE code = 'ROLE_MGMT' LIMIT 1)
  AND EXISTS (SELECT 1 FROM modules WHERE code = 'role_mgmt');

-- USER_MGMT -> user_mgmt
UPDATE permissions SET module_id = (SELECT id FROM modules WHERE code = 'user_mgmt' LIMIT 1)
WHERE module_id = (SELECT id FROM modules WHERE code = 'USER_MGMT' LIMIT 1)
  AND EXISTS (SELECT 1 FROM modules WHERE code = 'user_mgmt');

-- ============================================================================
-- STEP 3: For UPPERCASE modules without lowercase equivalent, rename them
-- ============================================================================

-- Rename ACCOUNTING to accounting (if no lowercase exists)
UPDATE modules SET code = 'accounting', name = 'Accounting'
WHERE code = 'ACCOUNTING'
  AND NOT EXISTS (SELECT 1 FROM modules WHERE code = 'accounting');

-- Rename BILLING to billing
UPDATE modules SET code = 'billing', name = 'Billing'
WHERE code = 'BILLING'
  AND NOT EXISTS (SELECT 1 FROM modules WHERE code = 'billing');

-- Rename CUSTOMERS to customers
UPDATE modules SET code = 'customers', name = 'Customers'
WHERE code = 'CUSTOMERS'
  AND NOT EXISTS (SELECT 1 FROM modules WHERE code = 'customers');

-- Rename GRN to grn
UPDATE modules SET code = 'grn', name = 'GRN'
WHERE code = 'GRN'
  AND NOT EXISTS (SELECT 1 FROM modules WHERE code = 'grn');

-- Rename PURCHASE to purchase
UPDATE modules SET code = 'purchase', name = 'Purchase'
WHERE code = 'PURCHASE'
  AND NOT EXISTS (SELECT 1 FROM modules WHERE code = 'purchase');

-- Rename ROLE_MGMT to role_mgmt
UPDATE modules SET code = 'role_mgmt', name = 'Role Management'
WHERE code = 'ROLE_MGMT'
  AND NOT EXISTS (SELECT 1 FROM modules WHERE code = 'role_mgmt');

-- Rename USER_MGMT to user_mgmt
UPDATE modules SET code = 'user_mgmt', name = 'User Management'
WHERE code = 'USER_MGMT'
  AND NOT EXISTS (SELECT 1 FROM modules WHERE code = 'user_mgmt');

-- ============================================================================
-- STEP 4: Delete UPPERCASE modules that now have 0 permissions
-- ============================================================================

DELETE FROM modules
WHERE code IN ('ACCOUNTING', 'BILLING', 'CUSTOMERS', 'GRN', 'PURCHASE', 'ROLE_MGMT', 'USER_MGMT')
  AND NOT EXISTS (SELECT 1 FROM permissions WHERE module_id = modules.id);

-- ============================================================================
-- STEP 5: Fix NULL module_id in permissions
-- ============================================================================

UPDATE permissions p
SET module_id = m.id
FROM modules m
WHERE p.module_id IS NULL
  AND p.code LIKE '%:%'
  AND m.code = LOWER(SPLIT_PART(p.code, ':', 1));

-- ============================================================================
-- STEP 6: Fix NULL action in permissions
-- ============================================================================

UPDATE permissions
SET action = SPLIT_PART(code, ':', 2)
WHERE action IS NULL AND code LIKE '%:%';

-- ============================================================================
-- STEP 7: Add NOT NULL constraints (if no NULLs remain)
-- ============================================================================

DO $$
DECLARE
    null_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO null_count FROM permissions WHERE action IS NULL OR module_id IS NULL;
    IF null_count = 0 THEN
        BEGIN
            ALTER TABLE permissions ALTER COLUMN action SET NOT NULL;
        EXCEPTION WHEN others THEN
            RAISE NOTICE 'action NOT NULL constraint may already exist';
        END;
        BEGIN
            ALTER TABLE permissions ALTER COLUMN module_id SET NOT NULL;
        EXCEPTION WHEN others THEN
            RAISE NOTICE 'module_id NOT NULL constraint may already exist';
        END;
    ELSE
        RAISE NOTICE 'Warning: % permissions still have NULL values', null_count;
    END IF;
END $$;

-- ============================================================================
-- VERIFICATION
-- ============================================================================

SELECT 'UPPERCASE modules' as check_type, COUNT(*) as count
FROM modules WHERE code ~ '^[A-Z_]+$'
UNION ALL
SELECT 'NULL module_id permissions', COUNT(*) FROM permissions WHERE module_id IS NULL
UNION ALL
SELECT 'NULL action permissions', COUNT(*) FROM permissions WHERE action IS NULL
UNION ALL
SELECT 'Total modules', COUNT(*) FROM modules
UNION ALL
SELECT 'Total permissions', COUNT(*) FROM permissions;

-- Final module list
SELECT code, name,
    (SELECT COUNT(*) FROM permissions p WHERE p.module_id = m.id) as permission_count
FROM modules m
ORDER BY code;
