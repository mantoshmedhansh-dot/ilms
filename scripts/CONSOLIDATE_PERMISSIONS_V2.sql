-- ============================================================================
-- CONSOLIDATE PERMISSIONS V2 - Fixed duplicate handling
-- Run in Supabase SQL Editor
-- Created: 2026-01-19
-- ============================================================================

-- ============================================================================
-- STEP 1: Handle products:read -> products:view (migrate, don't rename)
-- ============================================================================

-- Move role_permissions from products:read to products:view
UPDATE role_permissions rp
SET permission_id = (SELECT id FROM permissions WHERE code = 'products:view')
WHERE permission_id = (SELECT id FROM permissions WHERE code = 'products:read')
  AND EXISTS (SELECT 1 FROM permissions WHERE code = 'products:view')
  AND NOT EXISTS (
      SELECT 1 FROM role_permissions rp2
      WHERE rp2.role_id = rp.role_id
        AND rp2.permission_id = (SELECT id FROM permissions WHERE code = 'products:view')
  );

-- Delete products:read (it's now redundant)
DELETE FROM role_permissions WHERE permission_id = (SELECT id FROM permissions WHERE code = 'products:read');
DELETE FROM permissions WHERE code = 'products:read';

-- ============================================================================
-- STEP 2: CREATE MAPPING for UPPERCASE -> lowercase
-- ============================================================================

CREATE TEMP TABLE IF NOT EXISTS permission_mapping AS
SELECT
    up.id as old_permission_id,
    up.code as old_code,
    lp.id as new_permission_id,
    lp.code as new_code
FROM permissions up
JOIN permissions lp ON
    up.action = lp.action
    AND up.code ~ '^[A-Z_]+$'
    AND lp.code ~ '^[a-z_]+:[a-z_]+$'
    AND up.module_id = lp.module_id;

-- Show mapping
SELECT 'Permission mapping (UPPERCASE -> lowercase)' as info;
SELECT * FROM permission_mapping ORDER BY old_code;

-- ============================================================================
-- STEP 3: MIGRATE ROLE_PERMISSIONS from UPPERCASE to lowercase
-- ============================================================================

-- Update role_permissions to point to lowercase permission
UPDATE role_permissions rp
SET permission_id = pm.new_permission_id
FROM permission_mapping pm
WHERE rp.permission_id = pm.old_permission_id
  AND NOT EXISTS (
      SELECT 1 FROM role_permissions rp2
      WHERE rp2.role_id = rp.role_id
        AND rp2.permission_id = pm.new_permission_id
  );

-- Delete role_permissions still pointing to UPPERCASE (they're duplicates now)
DELETE FROM role_permissions rp
WHERE EXISTS (
    SELECT 1 FROM permission_mapping pm
    WHERE rp.permission_id = pm.old_permission_id
);

-- ============================================================================
-- STEP 4: DELETE UPPERCASE PERMISSIONS
-- ============================================================================

DELETE FROM permissions WHERE code ~ '^[A-Z_]+$';

-- Drop temp table
DROP TABLE IF EXISTS permission_mapping;

-- ============================================================================
-- STEP 5: ADD MISSING PERMISSIONS (using ON CONFLICT DO NOTHING)
-- ============================================================================

-- crm:delete and crm:export
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

INSERT INTO permissions (id, code, name, description, action, module_id, is_active, created_at, updated_at)
SELECT gen_random_uuid(), 'orders:delete', 'Delete Orders', 'Delete orders', 'delete', m.id, true, NOW(), NOW()
FROM modules m WHERE m.code = 'orders'
ON CONFLICT (code) DO NOTHING;

-- inventory:transfer, adjust, export, delete
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

-- products:import, export
INSERT INTO permissions (id, code, name, description, action, module_id, is_active, created_at, updated_at)
SELECT gen_random_uuid(), 'products:import', 'Import Products', 'Bulk import products', 'import', m.id, true, NOW(), NOW()
FROM modules m WHERE m.code = 'products'
ON CONFLICT (code) DO NOTHING;

INSERT INTO permissions (id, code, name, description, action, module_id, is_active, created_at, updated_at)
SELECT gen_random_uuid(), 'products:export', 'Export Products', 'Export product data', 'export', m.id, true, NOW(), NOW()
FROM modules m WHERE m.code = 'products'
ON CONFLICT (code) DO NOTHING;

-- service:assign, close, escalate, delete
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

-- procurement:receive, delete
INSERT INTO permissions (id, code, name, description, action, module_id, is_active, created_at, updated_at)
SELECT gen_random_uuid(), 'procurement:receive', 'Receive Goods', 'Mark goods as received', 'receive', m.id, true, NOW(), NOW()
FROM modules m WHERE m.code = 'procurement'
ON CONFLICT (code) DO NOTHING;

INSERT INTO permissions (id, code, name, description, action, module_id, is_active, created_at, updated_at)
SELECT gen_random_uuid(), 'procurement:delete', 'Delete Purchase Orders', 'Delete POs', 'delete', m.id, true, NOW(), NOW()
FROM modules m WHERE m.code = 'procurement'
ON CONFLICT (code) DO NOTHING;

-- finance:approve, reconcile, export, delete
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

-- hr:approve
INSERT INTO permissions (id, code, name, description, action, module_id, is_active, created_at, updated_at)
SELECT gen_random_uuid(), 'hr:approve', 'Approve HR Requests', 'Approve leave/requests', 'approve', m.id, true, NOW(), NOW()
FROM modules m WHERE m.code = 'hr'
ON CONFLICT (code) DO NOTHING;

-- reports:schedule, create, update, delete
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

-- settings:create, delete
INSERT INTO permissions (id, code, name, description, action, module_id, is_active, created_at, updated_at)
SELECT gen_random_uuid(), 'settings:create', 'Create Settings', 'Add new settings', 'create', m.id, true, NOW(), NOW()
FROM modules m WHERE m.code = 'settings'
ON CONFLICT (code) DO NOTHING;

INSERT INTO permissions (id, code, name, description, action, module_id, is_active, created_at, updated_at)
SELECT gen_random_uuid(), 'settings:delete', 'Delete Settings', 'Remove settings', 'delete', m.id, true, NOW(), NOW()
FROM modules m WHERE m.code = 'settings'
ON CONFLICT (code) DO NOTHING;

-- dashboard:create, update, delete
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

-- ============================================================================
-- STEP 6: VERIFICATION
-- ============================================================================

SELECT 'VERIFICATION AFTER CONSOLIDATION' as status;

-- Check no UPPERCASE permissions remain
SELECT 'UPPERCASE permissions remaining (should be 0)' as check_name, COUNT(*) as count
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
