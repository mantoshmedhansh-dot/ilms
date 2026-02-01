-- ============================================================================
-- COMPLETE PERMISSIONS FIX - Diagnoses and fixes all permission issues
-- Run in Supabase SQL Editor
-- Created: 2026-01-19
-- ============================================================================

-- ============================================================================
-- STEP 1: DIAGNOSE - Run these queries first to understand the current state
-- ============================================================================

-- 1a. Check permissions with NULL module_id
SELECT 'Orphaned permissions (NULL module_id)' as diagnosis;
SELECT id, code, name, action, module_id
FROM permissions
WHERE module_id IS NULL
ORDER BY code;

-- 1b. Check permissions grouped by code prefix
SELECT 'Permissions by module prefix' as diagnosis;
SELECT
    SPLIT_PART(code, ':', 1) as module_prefix,
    COUNT(*) as permission_count,
    SUM(CASE WHEN module_id IS NULL THEN 1 ELSE 0 END) as null_module_count
FROM permissions
GROUP BY SPLIT_PART(code, ':', 1)
ORDER BY module_prefix;

-- 1c. Check modules vs permissions count
SELECT 'Module permission counts' as diagnosis;
SELECT
    m.code as module_code,
    m.name as module_name,
    m.id as module_id,
    (SELECT COUNT(*) FROM permissions p WHERE p.module_id = m.id) as linked_permissions,
    (SELECT COUNT(*) FROM permissions p WHERE SPLIT_PART(p.code, ':', 1) = m.code) as matching_prefix_permissions
FROM modules m
ORDER BY m.code;

-- ============================================================================
-- STEP 2: FIX ORPHANED PERMISSIONS - Link permissions to their modules
-- ============================================================================

-- 2a. Link permissions to modules based on code prefix
UPDATE permissions p
SET module_id = m.id
FROM modules m
WHERE p.module_id IS NULL
  AND p.code LIKE '%:%'
  AND m.code = SPLIT_PART(p.code, ':', 1);

-- 2b. Fix NULL action field
UPDATE permissions
SET action = SPLIT_PART(code, ':', 2)
WHERE action IS NULL AND code LIKE '%:%';

-- ============================================================================
-- STEP 3: CREATE MISSING PERMISSIONS - These match seed_rbac.py EXACTLY
-- ============================================================================

-- Insert all permissions that should exist but don't
-- This uses ON CONFLICT to skip existing permissions

-- complaints (6 permissions)
INSERT INTO permissions (id, code, name, description, action, module_id, is_active, created_at, updated_at)
SELECT gen_random_uuid(), 'complaints:view', 'View Complaints', 'View complaint tickets', 'view', m.id, true, NOW(), NOW()
FROM modules m WHERE m.code = 'complaints'
ON CONFLICT (code) DO NOTHING;

INSERT INTO permissions (id, code, name, description, action, module_id, is_active, created_at, updated_at)
SELECT gen_random_uuid(), 'complaints:create', 'Create Complaints', 'Log new complaints', 'create', m.id, true, NOW(), NOW()
FROM modules m WHERE m.code = 'complaints'
ON CONFLICT (code) DO NOTHING;

INSERT INTO permissions (id, code, name, description, action, module_id, is_active, created_at, updated_at)
SELECT gen_random_uuid(), 'complaints:update', 'Update Complaints', 'Modify complaint details', 'update', m.id, true, NOW(), NOW()
FROM modules m WHERE m.code = 'complaints'
ON CONFLICT (code) DO NOTHING;

INSERT INTO permissions (id, code, name, description, action, module_id, is_active, created_at, updated_at)
SELECT gen_random_uuid(), 'complaints:assign', 'Assign Complaints', 'Assign to agents', 'assign', m.id, true, NOW(), NOW()
FROM modules m WHERE m.code = 'complaints'
ON CONFLICT (code) DO NOTHING;

INSERT INTO permissions (id, code, name, description, action, module_id, is_active, created_at, updated_at)
SELECT gen_random_uuid(), 'complaints:resolve', 'Resolve Complaints', 'Mark as resolved', 'resolve', m.id, true, NOW(), NOW()
FROM modules m WHERE m.code = 'complaints'
ON CONFLICT (code) DO NOTHING;

INSERT INTO permissions (id, code, name, description, action, module_id, is_active, created_at, updated_at)
SELECT gen_random_uuid(), 'complaints:escalate', 'Escalate Complaints', 'Escalate to higher level', 'escalate', m.id, true, NOW(), NOW()
FROM modules m WHERE m.code = 'complaints'
ON CONFLICT (code) DO NOTHING;

-- logistics (5 permissions)
INSERT INTO permissions (id, code, name, description, action, module_id, is_active, created_at, updated_at)
SELECT gen_random_uuid(), 'logistics:view', 'View Logistics', 'View shipments', 'view', m.id, true, NOW(), NOW()
FROM modules m WHERE m.code = 'logistics'
ON CONFLICT (code) DO NOTHING;

INSERT INTO permissions (id, code, name, description, action, module_id, is_active, created_at, updated_at)
SELECT gen_random_uuid(), 'logistics:create', 'Create Shipments', 'Create shipments', 'create', m.id, true, NOW(), NOW()
FROM modules m WHERE m.code = 'logistics'
ON CONFLICT (code) DO NOTHING;

INSERT INTO permissions (id, code, name, description, action, module_id, is_active, created_at, updated_at)
SELECT gen_random_uuid(), 'logistics:update', 'Update Shipments', 'Modify shipment details', 'update', m.id, true, NOW(), NOW()
FROM modules m WHERE m.code = 'logistics'
ON CONFLICT (code) DO NOTHING;

INSERT INTO permissions (id, code, name, description, action, module_id, is_active, created_at, updated_at)
SELECT gen_random_uuid(), 'logistics:assign', 'Assign Deliveries', 'Assign to delivery agents', 'assign', m.id, true, NOW(), NOW()
FROM modules m WHERE m.code = 'logistics'
ON CONFLICT (code) DO NOTHING;

INSERT INTO permissions (id, code, name, description, action, module_id, is_active, created_at, updated_at)
SELECT gen_random_uuid(), 'logistics:track', 'Track Shipments', 'Track delivery status', 'track', m.id, true, NOW(), NOW()
FROM modules m WHERE m.code = 'logistics'
ON CONFLICT (code) DO NOTHING;

-- marketing (5 permissions)
INSERT INTO permissions (id, code, name, description, action, module_id, is_active, created_at, updated_at)
SELECT gen_random_uuid(), 'marketing:view', 'View Marketing', 'View campaigns', 'view', m.id, true, NOW(), NOW()
FROM modules m WHERE m.code = 'marketing'
ON CONFLICT (code) DO NOTHING;

INSERT INTO permissions (id, code, name, description, action, module_id, is_active, created_at, updated_at)
SELECT gen_random_uuid(), 'marketing:create', 'Create Campaigns', 'Create marketing campaigns', 'create', m.id, true, NOW(), NOW()
FROM modules m WHERE m.code = 'marketing'
ON CONFLICT (code) DO NOTHING;

INSERT INTO permissions (id, code, name, description, action, module_id, is_active, created_at, updated_at)
SELECT gen_random_uuid(), 'marketing:update', 'Update Campaigns', 'Modify campaigns', 'update', m.id, true, NOW(), NOW()
FROM modules m WHERE m.code = 'marketing'
ON CONFLICT (code) DO NOTHING;

INSERT INTO permissions (id, code, name, description, action, module_id, is_active, created_at, updated_at)
SELECT gen_random_uuid(), 'marketing:delete', 'Delete Campaigns', 'Remove campaigns', 'delete', m.id, true, NOW(), NOW()
FROM modules m WHERE m.code = 'marketing'
ON CONFLICT (code) DO NOTHING;

INSERT INTO permissions (id, code, name, description, action, module_id, is_active, created_at, updated_at)
SELECT gen_random_uuid(), 'marketing:publish', 'Publish Campaigns', 'Publish/activate campaigns', 'publish', m.id, true, NOW(), NOW()
FROM modules m WHERE m.code = 'marketing'
ON CONFLICT (code) DO NOTHING;

-- notifications (3 permissions)
INSERT INTO permissions (id, code, name, description, action, module_id, is_active, created_at, updated_at)
SELECT gen_random_uuid(), 'notifications:view', 'View Notifications', 'View notifications', 'view', m.id, true, NOW(), NOW()
FROM modules m WHERE m.code = 'notifications'
ON CONFLICT (code) DO NOTHING;

INSERT INTO permissions (id, code, name, description, action, module_id, is_active, created_at, updated_at)
SELECT gen_random_uuid(), 'notifications:create', 'Create Notifications', 'Create system notifications', 'create', m.id, true, NOW(), NOW()
FROM modules m WHERE m.code = 'notifications'
ON CONFLICT (code) DO NOTHING;

INSERT INTO permissions (id, code, name, description, action, module_id, is_active, created_at, updated_at)
SELECT gen_random_uuid(), 'notifications:send', 'Send Notifications', 'Send notifications to users', 'send', m.id, true, NOW(), NOW()
FROM modules m WHERE m.code = 'notifications'
ON CONFLICT (code) DO NOTHING;

-- accounts - Chart of Accounts (4 permissions)
INSERT INTO permissions (id, code, name, description, action, module_id, is_active, created_at, updated_at)
SELECT gen_random_uuid(), 'accounts:view', 'View Chart of Accounts', 'View ledger accounts', 'view', m.id, true, NOW(), NOW()
FROM modules m WHERE m.code = 'accounts'
ON CONFLICT (code) DO NOTHING;

INSERT INTO permissions (id, code, name, description, action, module_id, is_active, created_at, updated_at)
SELECT gen_random_uuid(), 'accounts:create', 'Create Accounts', 'Create new ledger accounts', 'create', m.id, true, NOW(), NOW()
FROM modules m WHERE m.code = 'accounts'
ON CONFLICT (code) DO NOTHING;

INSERT INTO permissions (id, code, name, description, action, module_id, is_active, created_at, updated_at)
SELECT gen_random_uuid(), 'accounts:update', 'Update Accounts', 'Modify ledger accounts', 'update', m.id, true, NOW(), NOW()
FROM modules m WHERE m.code = 'accounts'
ON CONFLICT (code) DO NOTHING;

INSERT INTO permissions (id, code, name, description, action, module_id, is_active, created_at, updated_at)
SELECT gen_random_uuid(), 'accounts:delete', 'Delete Accounts', 'Delete ledger accounts', 'delete', m.id, true, NOW(), NOW()
FROM modules m WHERE m.code = 'accounts'
ON CONFLICT (code) DO NOTHING;

-- journals - Journal Entries (4 permissions)
INSERT INTO permissions (id, code, name, description, action, module_id, is_active, created_at, updated_at)
SELECT gen_random_uuid(), 'journals:view', 'View Journal Entries', 'View journal entries', 'view', m.id, true, NOW(), NOW()
FROM modules m WHERE m.code = 'journals'
ON CONFLICT (code) DO NOTHING;

INSERT INTO permissions (id, code, name, description, action, module_id, is_active, created_at, updated_at)
SELECT gen_random_uuid(), 'journals:create', 'Create Journal Entries', 'Create journal entries', 'create', m.id, true, NOW(), NOW()
FROM modules m WHERE m.code = 'journals'
ON CONFLICT (code) DO NOTHING;

INSERT INTO permissions (id, code, name, description, action, module_id, is_active, created_at, updated_at)
SELECT gen_random_uuid(), 'journals:approve', 'Approve Journal Entries', 'Approve/post journal entries', 'approve', m.id, true, NOW(), NOW()
FROM modules m WHERE m.code = 'journals'
ON CONFLICT (code) DO NOTHING;

INSERT INTO permissions (id, code, name, description, action, module_id, is_active, created_at, updated_at)
SELECT gen_random_uuid(), 'journals:reverse', 'Reverse Journal Entries', 'Reverse posted entries', 'reverse', m.id, true, NOW(), NOW()
FROM modules m WHERE m.code = 'journals'
ON CONFLICT (code) DO NOTHING;

-- assets - Fixed Assets (4 permissions)
INSERT INTO permissions (id, code, name, description, action, module_id, is_active, created_at, updated_at)
SELECT gen_random_uuid(), 'assets:view', 'View Fixed Assets', 'View asset register', 'view', m.id, true, NOW(), NOW()
FROM modules m WHERE m.code = 'assets'
ON CONFLICT (code) DO NOTHING;

INSERT INTO permissions (id, code, name, description, action, module_id, is_active, created_at, updated_at)
SELECT gen_random_uuid(), 'assets:create', 'Create Fixed Assets', 'Add new assets', 'create', m.id, true, NOW(), NOW()
FROM modules m WHERE m.code = 'assets'
ON CONFLICT (code) DO NOTHING;

INSERT INTO permissions (id, code, name, description, action, module_id, is_active, created_at, updated_at)
SELECT gen_random_uuid(), 'assets:update', 'Update Fixed Assets', 'Modify asset details', 'update', m.id, true, NOW(), NOW()
FROM modules m WHERE m.code = 'assets'
ON CONFLICT (code) DO NOTHING;

INSERT INTO permissions (id, code, name, description, action, module_id, is_active, created_at, updated_at)
SELECT gen_random_uuid(), 'assets:depreciate', 'Run Depreciation', 'Calculate depreciation', 'depreciate', m.id, true, NOW(), NOW()
FROM modules m WHERE m.code = 'assets'
ON CONFLICT (code) DO NOTHING;

-- bank_recon - Bank Reconciliation (3 permissions)
INSERT INTO permissions (id, code, name, description, action, module_id, is_active, created_at, updated_at)
SELECT gen_random_uuid(), 'bank_recon:view', 'View Bank Reconciliation', 'View bank statements', 'view', m.id, true, NOW(), NOW()
FROM modules m WHERE m.code = 'bank_recon'
ON CONFLICT (code) DO NOTHING;

INSERT INTO permissions (id, code, name, description, action, module_id, is_active, created_at, updated_at)
SELECT gen_random_uuid(), 'bank_recon:reconcile', 'Perform Reconciliation', 'Match bank transactions', 'reconcile', m.id, true, NOW(), NOW()
FROM modules m WHERE m.code = 'bank_recon'
ON CONFLICT (code) DO NOTHING;

INSERT INTO permissions (id, code, name, description, action, module_id, is_active, created_at, updated_at)
SELECT gen_random_uuid(), 'bank_recon:import', 'Import Bank Statements', 'Import bank files', 'import', m.id, true, NOW(), NOW()
FROM modules m WHERE m.code = 'bank_recon'
ON CONFLICT (code) DO NOTHING;

-- cost_centers (3 permissions)
INSERT INTO permissions (id, code, name, description, action, module_id, is_active, created_at, updated_at)
SELECT gen_random_uuid(), 'cost_centers:view', 'View Cost Centers', 'View cost centers', 'view', m.id, true, NOW(), NOW()
FROM modules m WHERE m.code = 'cost_centers'
ON CONFLICT (code) DO NOTHING;

INSERT INTO permissions (id, code, name, description, action, module_id, is_active, created_at, updated_at)
SELECT gen_random_uuid(), 'cost_centers:create', 'Create Cost Centers', 'Create cost centers', 'create', m.id, true, NOW(), NOW()
FROM modules m WHERE m.code = 'cost_centers'
ON CONFLICT (code) DO NOTHING;

INSERT INTO permissions (id, code, name, description, action, module_id, is_active, created_at, updated_at)
SELECT gen_random_uuid(), 'cost_centers:update', 'Update Cost Centers', 'Modify cost centers', 'update', m.id, true, NOW(), NOW()
FROM modules m WHERE m.code = 'cost_centers'
ON CONFLICT (code) DO NOTHING;

-- periods - Financial Periods (3 permissions)
INSERT INTO permissions (id, code, name, description, action, module_id, is_active, created_at, updated_at)
SELECT gen_random_uuid(), 'periods:view', 'View Financial Periods', 'View accounting periods', 'view', m.id, true, NOW(), NOW()
FROM modules m WHERE m.code = 'periods'
ON CONFLICT (code) DO NOTHING;

INSERT INTO permissions (id, code, name, description, action, module_id, is_active, created_at, updated_at)
SELECT gen_random_uuid(), 'periods:create', 'Create Periods', 'Create new periods', 'create', m.id, true, NOW(), NOW()
FROM modules m WHERE m.code = 'periods'
ON CONFLICT (code) DO NOTHING;

INSERT INTO permissions (id, code, name, description, action, module_id, is_active, created_at, updated_at)
SELECT gen_random_uuid(), 'periods:close', 'Close Periods', 'Close accounting periods', 'close', m.id, true, NOW(), NOW()
FROM modules m WHERE m.code = 'periods'
ON CONFLICT (code) DO NOTHING;

-- gst - GST Returns (4 permissions)
INSERT INTO permissions (id, code, name, description, action, module_id, is_active, created_at, updated_at)
SELECT gen_random_uuid(), 'gst:view', 'View GST Returns', 'View GSTR-1/2A/3B', 'view', m.id, true, NOW(), NOW()
FROM modules m WHERE m.code = 'gst'
ON CONFLICT (code) DO NOTHING;

INSERT INTO permissions (id, code, name, description, action, module_id, is_active, created_at, updated_at)
SELECT gen_random_uuid(), 'gst:generate', 'Generate GST Returns', 'Generate GST reports', 'generate', m.id, true, NOW(), NOW()
FROM modules m WHERE m.code = 'gst'
ON CONFLICT (code) DO NOTHING;

INSERT INTO permissions (id, code, name, description, action, module_id, is_active, created_at, updated_at)
SELECT gen_random_uuid(), 'gst:file', 'File GST Returns', 'Submit GST returns', 'file', m.id, true, NOW(), NOW()
FROM modules m WHERE m.code = 'gst'
ON CONFLICT (code) DO NOTHING;

INSERT INTO permissions (id, code, name, description, action, module_id, is_active, created_at, updated_at)
SELECT gen_random_uuid(), 'gst:export', 'Export GST Data', 'Export GST files', 'export', m.id, true, NOW(), NOW()
FROM modules m WHERE m.code = 'gst'
ON CONFLICT (code) DO NOTHING;

-- tds - TDS (3 permissions)
INSERT INTO permissions (id, code, name, description, action, module_id, is_active, created_at, updated_at)
SELECT gen_random_uuid(), 'tds:view', 'View TDS', 'View TDS reports', 'view', m.id, true, NOW(), NOW()
FROM modules m WHERE m.code = 'tds'
ON CONFLICT (code) DO NOTHING;

INSERT INTO permissions (id, code, name, description, action, module_id, is_active, created_at, updated_at)
SELECT gen_random_uuid(), 'tds:create', 'Create TDS Entries', 'Record TDS deductions', 'create', m.id, true, NOW(), NOW()
FROM modules m WHERE m.code = 'tds'
ON CONFLICT (code) DO NOTHING;

INSERT INTO permissions (id, code, name, description, action, module_id, is_active, created_at, updated_at)
SELECT gen_random_uuid(), 'tds:file', 'File TDS Returns', 'Submit TDS returns', 'file', m.id, true, NOW(), NOW()
FROM modules m WHERE m.code = 'tds'
ON CONFLICT (code) DO NOTHING;

-- ============================================================================
-- STEP 4: ENSURE ALL EXISTING PERMISSIONS HAVE CORRECT MODULE REFERENCE
-- ============================================================================

-- This is a safety net - re-link any permissions that might still be orphaned
UPDATE permissions p
SET module_id = m.id
FROM modules m
WHERE p.module_id IS NULL
  AND p.code LIKE '%:%'
  AND m.code = SPLIT_PART(p.code, ':', 1);

-- ============================================================================
-- STEP 5: ADD DATABASE CONSTRAINTS (Structural Fix)
-- ============================================================================

-- Add NOT NULL constraints if no NULLs remain
DO $$
DECLARE
    null_module_count INTEGER;
    null_action_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO null_module_count FROM permissions WHERE module_id IS NULL;
    SELECT COUNT(*) INTO null_action_count FROM permissions WHERE action IS NULL;

    IF null_module_count > 0 THEN
        RAISE NOTICE 'WARNING: % permissions still have NULL module_id', null_module_count;
    ELSE
        BEGIN
            ALTER TABLE permissions ALTER COLUMN module_id SET NOT NULL;
            RAISE NOTICE 'SUCCESS: Added NOT NULL constraint to module_id';
        EXCEPTION WHEN others THEN
            RAISE NOTICE 'module_id NOT NULL constraint may already exist';
        END;
    END IF;

    IF null_action_count > 0 THEN
        RAISE NOTICE 'WARNING: % permissions still have NULL action', null_action_count;
    ELSE
        BEGIN
            ALTER TABLE permissions ALTER COLUMN action SET NOT NULL;
            RAISE NOTICE 'SUCCESS: Added NOT NULL constraint to action';
        EXCEPTION WHEN others THEN
            RAISE NOTICE 'action NOT NULL constraint may already exist';
        END;
    END IF;
END $$;

-- ============================================================================
-- STEP 6: VERIFICATION - Run after completing all steps
-- ============================================================================

-- Final summary
SELECT 'VERIFICATION SUMMARY' as status;

SELECT 'Total counts' as check_name,
    (SELECT COUNT(*) FROM modules) as modules,
    (SELECT COUNT(*) FROM permissions) as permissions,
    (SELECT COUNT(*) FROM permissions WHERE module_id IS NULL) as null_module_perms,
    (SELECT COUNT(*) FROM permissions WHERE action IS NULL) as null_action_perms;

-- Final module permission counts
SELECT 'Module permission counts (final)' as status;
SELECT
    m.code as module_code,
    m.name as module_name,
    (SELECT COUNT(*) FROM permissions p WHERE p.module_id = m.id) as permission_count
FROM modules m
ORDER BY m.code;

-- List modules that still have 0 permissions (should be empty)
SELECT 'Modules with 0 permissions (should be none)' as warning;
SELECT m.code, m.name
FROM modules m
WHERE NOT EXISTS (SELECT 1 FROM permissions p WHERE p.module_id = m.id);

-- Show all permissions for verification
SELECT 'All permissions by module' as status;
SELECT
    m.code as module,
    p.code as permission_code,
    p.action,
    p.name
FROM permissions p
JOIN modules m ON p.module_id = m.id
ORDER BY m.code, p.action;
