-- ============================================================================
-- CONSOLIDATE PERMISSIONS - Merge UPPERCASE legacy permissions into lowercase
-- Run in Supabase SQL Editor
-- Created: 2026-01-19
-- ============================================================================

-- ============================================================================
-- ANALYSIS: Two permission formats exist
-- ============================================================================
-- Format 1 (NEW/CORRECT): module:action (e.g., dashboard:view, hr:create)
-- Format 2 (LEGACY):      MODULE_ACTION (e.g., DASHBOARD_VIEW, HR_CREATE)
--
-- Strategy:
-- 1. Move role_permissions from UPPERCASE to lowercase equivalent
-- 2. Delete UPPERCASE permissions (they're duplicates)
-- 3. Keep only the standardized lowercase:colon format
-- ============================================================================

-- ============================================================================
-- STEP 1: DIAGNOSTIC - See what we're dealing with
-- ============================================================================

SELECT 'Permission format analysis' as diagnosis;
SELECT
    CASE
        WHEN code ~ '^[A-Z_]+$' THEN 'UPPERCASE_UNDERSCORE'
        WHEN code ~ '^[a-z_]+:[a-z_]+$' THEN 'lowercase_colon'
        ELSE 'OTHER'
    END as format,
    COUNT(*) as count
FROM permissions
GROUP BY 1
ORDER BY count DESC;

-- Show duplicate actions (same module + action but different code formats)
SELECT 'Duplicate permissions (same module+action)' as diagnosis;
SELECT
    p1.code as uppercase_code,
    p2.code as lowercase_code,
    p1.action,
    m.code as module
FROM permissions p1
JOIN permissions p2 ON
    LOWER(REPLACE(SPLIT_PART(p1.code, '_', 1), '_', '')) = SPLIT_PART(p2.code, ':', 1)
    AND p1.action = p2.action
    AND p1.id != p2.id
JOIN modules m ON p2.module_id = m.id
WHERE p1.code ~ '^[A-Z_]+$'
  AND p2.code ~ '^[a-z_]+:[a-z_]+$'
ORDER BY m.code, p1.action;

-- ============================================================================
-- STEP 2: CREATE MAPPING TABLE
-- ============================================================================

-- Create temporary mapping of UPPERCASE -> lowercase permission IDs
CREATE TEMP TABLE permission_mapping AS
WITH uppercase_perms AS (
    SELECT id, code, action, module_id,
           LOWER(SPLIT_PART(code, '_', 1)) as module_prefix
    FROM permissions
    WHERE code ~ '^[A-Z_]+$'
),
lowercase_perms AS (
    SELECT id, code, action, module_id,
           SPLIT_PART(code, ':', 1) as module_prefix
    FROM permissions
    WHERE code ~ '^[a-z_]+:[a-z_]+$'
)
SELECT
    u.id as old_permission_id,
    u.code as old_code,
    l.id as new_permission_id,
    l.code as new_code
FROM uppercase_perms u
JOIN lowercase_perms l ON
    -- Match module prefix (accounting -> accounting, dashboard -> dashboard)
    (u.module_prefix = l.module_prefix OR
     u.module_prefix = REPLACE(l.module_prefix, '_', ''))
    AND u.action = l.action;

-- Show what will be migrated
SELECT 'Permissions to migrate' as info;
SELECT * FROM permission_mapping ORDER BY old_code;

-- ============================================================================
-- STEP 3: MIGRATE ROLE_PERMISSIONS
-- ============================================================================

-- Move role assignments from UPPERCASE permissions to lowercase equivalents
UPDATE role_permissions rp
SET permission_id = pm.new_permission_id
FROM permission_mapping pm
WHERE rp.permission_id = pm.old_permission_id
  AND NOT EXISTS (
      -- Don't create duplicate if role already has the lowercase permission
      SELECT 1 FROM role_permissions rp2
      WHERE rp2.role_id = rp.role_id
        AND rp2.permission_id = pm.new_permission_id
  );

-- Delete role_permissions that would now be duplicates
DELETE FROM role_permissions rp
WHERE EXISTS (
    SELECT 1 FROM permission_mapping pm
    WHERE rp.permission_id = pm.old_permission_id
);

-- ============================================================================
-- STEP 4: DELETE UPPERCASE PERMISSIONS
-- ============================================================================

-- Delete the UPPERCASE permissions (they're now consolidated)
DELETE FROM permissions
WHERE code ~ '^[A-Z_]+$';

-- ============================================================================
-- STEP 5: RENAME/STANDARDIZE REMAINING EDGE CASES
-- ============================================================================

-- Handle any remaining non-standard permission codes
-- Update 'products:read' to 'products:view' for consistency
UPDATE permissions SET code = 'products:view', action = 'view', name = 'View Products'
WHERE code = 'products:read';

-- ============================================================================
-- STEP 6: ADD MISSING PERMISSIONS FROM seed_rbac.py
-- ============================================================================

-- These are permissions defined in seed_rbac.py but may be missing

-- crm:delete and crm:export (seed_rbac.py has 5 crm permissions)
INSERT INTO permissions (id, code, name, description, action, module_id, is_active, created_at, updated_at)
SELECT gen_random_uuid(), 'crm:delete', 'Delete Customers', 'Remove customers', 'delete', m.id, true, NOW(), NOW()
FROM modules m WHERE m.code = 'crm'
ON CONFLICT (code) DO NOTHING;

INSERT INTO permissions (id, code, name, description, action, module_id, is_active, created_at, updated_at)
SELECT gen_random_uuid(), 'crm:export', 'Export Customers', 'Export customer data', 'export', m.id, true, NOW(), NOW()
FROM modules m WHERE m.code = 'crm'
ON CONFLICT (code) DO NOTHING;

-- vendors:delete and vendors:approve
INSERT INTO permissions (id, code, name, description, action, module_id, is_active, created_at, updated_at)
SELECT gen_random_uuid(), 'vendors:delete', 'Delete Vendors', 'Remove vendors', 'delete', m.id, true, NOW(), NOW()
FROM modules m WHERE m.code = 'vendors'
ON CONFLICT (code) DO NOTHING;

INSERT INTO permissions (id, code, name, description, action, module_id, is_active, created_at, updated_at)
SELECT gen_random_uuid(), 'vendors:approve', 'Approve Vendors', 'Approve vendor onboarding', 'approve', m.id, true, NOW(), NOW()
FROM modules m WHERE m.code = 'vendors'
ON CONFLICT (code) DO NOTHING;

-- orders:approve and orders:export
INSERT INTO permissions (id, code, name, description, action, module_id, is_active, created_at, updated_at)
SELECT gen_random_uuid(), 'orders:approve', 'Approve Orders', 'Approve order processing', 'approve', m.id, true, NOW(), NOW()
FROM modules m WHERE m.code = 'orders'
ON CONFLICT (code) DO NOTHING;

INSERT INTO permissions (id, code, name, description, action, module_id, is_active, created_at, updated_at)
SELECT gen_random_uuid(), 'orders:export', 'Export Orders', 'Export order data', 'export', m.id, true, NOW(), NOW()
FROM modules m WHERE m.code = 'orders'
ON CONFLICT (code) DO NOTHING;

-- inventory:transfer, inventory:adjust, inventory:export, inventory:delete
INSERT INTO permissions (id, code, name, description, action, module_id, is_active, created_at, updated_at)
SELECT gen_random_uuid(), 'inventory:transfer', 'Transfer Inventory', 'Transfer between warehouses', 'transfer', m.id, true, NOW(), NOW()
FROM modules m WHERE m.code = 'inventory'
ON CONFLICT (code) DO NOTHING;

INSERT INTO permissions (id, code, name, description, action, module_id, is_active, created_at, updated_at)
SELECT gen_random_uuid(), 'inventory:adjust', 'Adjust Inventory', 'Make inventory adjustments', 'adjust', m.id, true, NOW(), NOW()
FROM modules m WHERE m.code = 'inventory'
ON CONFLICT (code) DO NOTHING;

INSERT INTO permissions (id, code, name, description, action, module_id, is_active, created_at, updated_at)
SELECT gen_random_uuid(), 'inventory:export', 'Export Inventory', 'Export inventory data', 'export', m.id, true, NOW(), NOW()
FROM modules m WHERE m.code = 'inventory'
ON CONFLICT (code) DO NOTHING;

INSERT INTO permissions (id, code, name, description, action, module_id, is_active, created_at, updated_at)
SELECT gen_random_uuid(), 'inventory:delete', 'Delete Inventory', 'Delete inventory entries', 'delete', m.id, true, NOW(), NOW()
FROM modules m WHERE m.code = 'inventory'
ON CONFLICT (code) DO NOTHING;

-- products:import, products:export
INSERT INTO permissions (id, code, name, description, action, module_id, is_active, created_at, updated_at)
SELECT gen_random_uuid(), 'products:import', 'Import Products', 'Bulk import products', 'import', m.id, true, NOW(), NOW()
FROM modules m WHERE m.code = 'products'
ON CONFLICT (code) DO NOTHING;

INSERT INTO permissions (id, code, name, description, action, module_id, is_active, created_at, updated_at)
SELECT gen_random_uuid(), 'products:export', 'Export Products', 'Export product data', 'export', m.id, true, NOW(), NOW()
FROM modules m WHERE m.code = 'products'
ON CONFLICT (code) DO NOTHING;

-- service:assign, service:close, service:escalate
INSERT INTO permissions (id, code, name, description, action, module_id, is_active, created_at, updated_at)
SELECT gen_random_uuid(), 'service:assign', 'Assign Service Requests', 'Assign to technicians', 'assign', m.id, true, NOW(), NOW()
FROM modules m WHERE m.code = 'service'
ON CONFLICT (code) DO NOTHING;

INSERT INTO permissions (id, code, name, description, action, module_id, is_active, created_at, updated_at)
SELECT gen_random_uuid(), 'service:close', 'Close Service Requests', 'Close service tickets', 'close', m.id, true, NOW(), NOW()
FROM modules m WHERE m.code = 'service'
ON CONFLICT (code) DO NOTHING;

INSERT INTO permissions (id, code, name, description, action, module_id, is_active, created_at, updated_at)
SELECT gen_random_uuid(), 'service:escalate', 'Escalate Service Requests', 'Escalate issues', 'escalate', m.id, true, NOW(), NOW()
FROM modules m WHERE m.code = 'service'
ON CONFLICT (code) DO NOTHING;

INSERT INTO permissions (id, code, name, description, action, module_id, is_active, created_at, updated_at)
SELECT gen_random_uuid(), 'service:delete', 'Delete Service Requests', 'Delete service tickets', 'delete', m.id, true, NOW(), NOW()
FROM modules m WHERE m.code = 'service'
ON CONFLICT (code) DO NOTHING;

-- procurement:receive
INSERT INTO permissions (id, code, name, description, action, module_id, is_active, created_at, updated_at)
SELECT gen_random_uuid(), 'procurement:receive', 'Receive Goods', 'Mark goods as received', 'receive', m.id, true, NOW(), NOW()
FROM modules m WHERE m.code = 'procurement'
ON CONFLICT (code) DO NOTHING;

INSERT INTO permissions (id, code, name, description, action, module_id, is_active, created_at, updated_at)
SELECT gen_random_uuid(), 'procurement:delete', 'Delete Purchase Orders', 'Delete POs', 'delete', m.id, true, NOW(), NOW()
FROM modules m WHERE m.code = 'procurement'
ON CONFLICT (code) DO NOTHING;

-- finance:approve, finance:reconcile, finance:export
INSERT INTO permissions (id, code, name, description, action, module_id, is_active, created_at, updated_at)
SELECT gen_random_uuid(), 'finance:approve', 'Approve Payments', 'Approve payments', 'approve', m.id, true, NOW(), NOW()
FROM modules m WHERE m.code = 'finance'
ON CONFLICT (code) DO NOTHING;

INSERT INTO permissions (id, code, name, description, action, module_id, is_active, created_at, updated_at)
SELECT gen_random_uuid(), 'finance:reconcile', 'Reconcile Accounts', 'Perform reconciliation', 'reconcile', m.id, true, NOW(), NOW()
FROM modules m WHERE m.code = 'finance'
ON CONFLICT (code) DO NOTHING;

INSERT INTO permissions (id, code, name, description, action, module_id, is_active, created_at, updated_at)
SELECT gen_random_uuid(), 'finance:export', 'Export Financial Data', 'Export reports', 'export', m.id, true, NOW(), NOW()
FROM modules m WHERE m.code = 'finance'
ON CONFLICT (code) DO NOTHING;

INSERT INTO permissions (id, code, name, description, action, module_id, is_active, created_at, updated_at)
SELECT gen_random_uuid(), 'finance:delete', 'Delete Transactions', 'Delete financial records', 'delete', m.id, true, NOW(), NOW()
FROM modules m WHERE m.code = 'finance'
ON CONFLICT (code) DO NOTHING;

-- hr:approve (hr already has many, just add missing)
INSERT INTO permissions (id, code, name, description, action, module_id, is_active, created_at, updated_at)
SELECT gen_random_uuid(), 'hr:approve', 'Approve HR Requests', 'Approve leave/requests', 'approve', m.id, true, NOW(), NOW()
FROM modules m WHERE m.code = 'hr'
ON CONFLICT (code) DO NOTHING;

-- reports:schedule
INSERT INTO permissions (id, code, name, description, action, module_id, is_active, created_at, updated_at)
SELECT gen_random_uuid(), 'reports:schedule', 'Schedule Reports', 'Schedule automated reports', 'schedule', m.id, true, NOW(), NOW()
FROM modules m WHERE m.code = 'reports'
ON CONFLICT (code) DO NOTHING;

INSERT INTO permissions (id, code, name, description, action, module_id, is_active, created_at, updated_at)
SELECT gen_random_uuid(), 'reports:create', 'Create Reports', 'Create custom reports', 'create', m.id, true, NOW(), NOW()
FROM modules m WHERE m.code = 'reports'
ON CONFLICT (code) DO NOTHING;

INSERT INTO permissions (id, code, name, description, action, module_id, is_active, created_at, updated_at)
SELECT gen_random_uuid(), 'reports:update', 'Update Reports', 'Modify report settings', 'update', m.id, true, NOW(), NOW()
FROM modules m WHERE m.code = 'reports'
ON CONFLICT (code) DO NOTHING;

INSERT INTO permissions (id, code, name, description, action, module_id, is_active, created_at, updated_at)
SELECT gen_random_uuid(), 'reports:delete', 'Delete Reports', 'Delete saved reports', 'delete', m.id, true, NOW(), NOW()
FROM modules m WHERE m.code = 'reports'
ON CONFLICT (code) DO NOTHING;

-- access_control:assign
INSERT INTO permissions (id, code, name, description, action, module_id, is_active, created_at, updated_at)
SELECT gen_random_uuid(), 'access_control:assign', 'Assign Roles', 'Assign roles to users', 'assign', m.id, true, NOW(), NOW()
FROM modules m WHERE m.code = 'access_control'
ON CONFLICT (code) DO NOTHING;

-- settings:create, settings:delete
INSERT INTO permissions (id, code, name, description, action, module_id, is_active, created_at, updated_at)
SELECT gen_random_uuid(), 'settings:create', 'Create Settings', 'Add new settings', 'create', m.id, true, NOW(), NOW()
FROM modules m WHERE m.code = 'settings'
ON CONFLICT (code) DO NOTHING;

INSERT INTO permissions (id, code, name, description, action, module_id, is_active, created_at, updated_at)
SELECT gen_random_uuid(), 'settings:delete', 'Delete Settings', 'Remove settings', 'delete', m.id, true, NOW(), NOW()
FROM modules m WHERE m.code = 'settings'
ON CONFLICT (code) DO NOTHING;

-- dashboard:create, dashboard:update, dashboard:delete (for dashboard widgets)
INSERT INTO permissions (id, code, name, description, action, module_id, is_active, created_at, updated_at)
SELECT gen_random_uuid(), 'dashboard:create', 'Create Dashboard Widgets', 'Add dashboard widgets', 'create', m.id, true, NOW(), NOW()
FROM modules m WHERE m.code = 'dashboard'
ON CONFLICT (code) DO NOTHING;

INSERT INTO permissions (id, code, name, description, action, module_id, is_active, created_at, updated_at)
SELECT gen_random_uuid(), 'dashboard:update', 'Update Dashboard', 'Modify dashboard layout', 'update', m.id, true, NOW(), NOW()
FROM modules m WHERE m.code = 'dashboard'
ON CONFLICT (code) DO NOTHING;

INSERT INTO permissions (id, code, name, description, action, module_id, is_active, created_at, updated_at)
SELECT gen_random_uuid(), 'dashboard:delete', 'Delete Dashboard Widgets', 'Remove dashboard widgets', 'delete', m.id, true, NOW(), NOW()
FROM modules m WHERE m.code = 'dashboard'
ON CONFLICT (code) DO NOTHING;

-- Drop the temp table
DROP TABLE IF EXISTS permission_mapping;

-- ============================================================================
-- STEP 7: VERIFICATION
-- ============================================================================

SELECT 'VERIFICATION AFTER CONSOLIDATION' as status;

-- Check no UPPERCASE permissions remain
SELECT 'UPPERCASE permissions (should be 0)' as check_name, COUNT(*) as count
FROM permissions WHERE code ~ '^[A-Z_]+$';

-- Permission format summary
SELECT 'Permission format summary' as check_name;
SELECT
    CASE
        WHEN code ~ '^[a-z_]+:[a-z_]+$' THEN 'lowercase:colon (correct)'
        ELSE 'other format'
    END as format,
    COUNT(*) as count
FROM permissions
GROUP BY 1;

-- Final module permission counts
SELECT 'Module permission counts (final)' as status;
SELECT
    m.code as module_code,
    m.name as module_name,
    (SELECT COUNT(*) FROM permissions p WHERE p.module_id = m.id) as permission_count
FROM modules m
ORDER BY m.code;

-- Total counts
SELECT 'Total counts' as summary,
    (SELECT COUNT(*) FROM modules) as modules,
    (SELECT COUNT(*) FROM permissions) as permissions,
    (SELECT COUNT(*) FROM roles) as roles,
    (SELECT COUNT(*) FROM role_permissions) as role_permission_assignments;
