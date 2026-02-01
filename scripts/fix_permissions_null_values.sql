-- Fix Permissions with NULL action and module_id
-- Run this in Supabase SQL Editor
-- Created: 2026-01-19

-- ==================== DIAGNOSTIC: Check current state ====================
-- Run this first to see what needs fixing

SELECT
    p.id,
    p.name,
    p.code,
    p.action,
    p.module_id,
    m.name as module_name
FROM permissions p
LEFT JOIN modules m ON p.module_id = m.id
WHERE p.action IS NULL OR p.module_id IS NULL;

-- ==================== FIX 1: Update action from permission code ====================
-- Extracts action from code like "products:view" -> "view"

UPDATE permissions
SET action = SPLIT_PART(code, ':', 2)
WHERE action IS NULL
  AND code LIKE '%:%';

-- For codes without colon, set default action based on name
UPDATE permissions
SET action = CASE
    WHEN LOWER(name) LIKE '%view%' THEN 'view'
    WHEN LOWER(name) LIKE '%create%' OR LOWER(name) LIKE '%add%' THEN 'create'
    WHEN LOWER(name) LIKE '%update%' OR LOWER(name) LIKE '%edit%' OR LOWER(name) LIKE '%modify%' THEN 'update'
    WHEN LOWER(name) LIKE '%delete%' OR LOWER(name) LIKE '%remove%' THEN 'delete'
    WHEN LOWER(name) LIKE '%approve%' THEN 'approve'
    WHEN LOWER(name) LIKE '%export%' THEN 'export'
    WHEN LOWER(name) LIKE '%import%' THEN 'import'
    ELSE 'view'
END
WHERE action IS NULL;

-- ==================== FIX 2: Update module_id from permission code ====================
-- Extracts module from code like "products:view" -> module where code = "products"

-- First, let's create a mapping and update
UPDATE permissions p
SET module_id = m.id
FROM modules m
WHERE p.module_id IS NULL
  AND p.code LIKE '%:%'
  AND m.code = SPLIT_PART(p.code, ':', 1);

-- Handle special cases where permission code prefix doesn't match module code exactly
-- Map common permission prefixes to module codes

-- access_control permissions -> access_control module
UPDATE permissions p
SET module_id = m.id
FROM modules m
WHERE p.module_id IS NULL
  AND p.code LIKE 'access_control:%'
  AND m.code = 'access_control';

-- users permissions -> access_control module (users are part of access control)
UPDATE permissions p
SET module_id = m.id
FROM modules m
WHERE p.module_id IS NULL
  AND p.code LIKE 'users:%'
  AND m.code = 'access_control';

-- roles permissions -> access_control module
UPDATE permissions p
SET module_id = m.id
FROM modules m
WHERE p.module_id IS NULL
  AND p.code LIKE 'roles:%'
  AND m.code = 'access_control';

-- customers permissions -> crm module
UPDATE permissions p
SET module_id = m.id
FROM modules m
WHERE p.module_id IS NULL
  AND p.code LIKE 'customers:%'
  AND m.code = 'crm';

-- dealers permissions -> crm module
UPDATE permissions p
SET module_id = m.id
FROM modules m
WHERE p.module_id IS NULL
  AND p.code LIKE 'dealers:%'
  AND m.code = 'crm';

-- purchase permissions -> procurement module
UPDATE permissions p
SET module_id = m.id
FROM modules m
WHERE p.module_id IS NULL
  AND p.code LIKE 'purchase:%'
  AND m.code = 'procurement';

-- vendors permissions -> vendors module
UPDATE permissions p
SET module_id = m.id
FROM modules m
WHERE p.module_id IS NULL
  AND p.code LIKE 'vendors:%'
  AND m.code = 'vendors';

-- warehouses permissions -> inventory module
UPDATE permissions p
SET module_id = m.id
FROM modules m
WHERE p.module_id IS NULL
  AND p.code LIKE 'warehouses:%'
  AND m.code = 'inventory';

-- shipments permissions -> logistics module
UPDATE permissions p
SET module_id = m.id
FROM modules m
WHERE p.module_id IS NULL
  AND p.code LIKE 'shipments:%'
  AND m.code = 'logistics';

-- transporters permissions -> logistics module
UPDATE permissions p
SET module_id = m.id
FROM modules m
WHERE p.module_id IS NULL
  AND p.code LIKE 'transporters:%'
  AND m.code = 'logistics';

-- accounting permissions -> finance module
UPDATE permissions p
SET module_id = m.id
FROM modules m
WHERE p.module_id IS NULL
  AND p.code LIKE 'accounting:%'
  AND m.code = 'finance';

-- billing permissions -> finance module
UPDATE permissions p
SET module_id = m.id
FROM modules m
WHERE p.module_id IS NULL
  AND p.code LIKE 'billing:%'
  AND m.code = 'finance';

-- payments permissions -> finance module
UPDATE permissions p
SET module_id = m.id
FROM modules m
WHERE p.module_id IS NULL
  AND p.code LIKE 'payments:%'
  AND m.code = 'finance';

-- employees permissions -> hr module
UPDATE permissions p
SET module_id = m.id
FROM modules m
WHERE p.module_id IS NULL
  AND p.code LIKE 'employees:%'
  AND m.code = 'hr';

-- attendance permissions -> hr module
UPDATE permissions p
SET module_id = m.id
FROM modules m
WHERE p.module_id IS NULL
  AND p.code LIKE 'attendance:%'
  AND m.code = 'hr';

-- leave permissions -> hr module
UPDATE permissions p
SET module_id = m.id
FROM modules m
WHERE p.module_id IS NULL
  AND p.code LIKE 'leave:%'
  AND m.code = 'hr';

-- service_requests permissions -> service module
UPDATE permissions p
SET module_id = m.id
FROM modules m
WHERE p.module_id IS NULL
  AND p.code LIKE 'service_requests:%'
  AND m.code = 'service';

-- installations permissions -> service module
UPDATE permissions p
SET module_id = m.id
FROM modules m
WHERE p.module_id IS NULL
  AND p.code LIKE 'installations:%'
  AND m.code = 'service';

-- amc permissions -> service module
UPDATE permissions p
SET module_id = m.id
FROM modules m
WHERE p.module_id IS NULL
  AND p.code LIKE 'amc:%'
  AND m.code = 'service';

-- technicians permissions -> service module
UPDATE permissions p
SET module_id = m.id
FROM modules m
WHERE p.module_id IS NULL
  AND p.code LIKE 'technicians:%'
  AND m.code = 'service';

-- promotions permissions -> marketing module
UPDATE permissions p
SET module_id = m.id
FROM modules m
WHERE p.module_id IS NULL
  AND p.code LIKE 'promotions:%'
  AND m.code = 'marketing';

-- campaigns permissions -> marketing module
UPDATE permissions p
SET module_id = m.id
FROM modules m
WHERE p.module_id IS NULL
  AND p.code LIKE 'campaigns:%'
  AND m.code = 'marketing';

-- ==================== FIX 3: Create missing modules if needed ====================
-- If any permissions still have NULL module_id, we need to create their modules

-- First check what's still missing
SELECT DISTINCT SPLIT_PART(code, ':', 1) as missing_module_code
FROM permissions
WHERE module_id IS NULL AND code LIKE '%:%';

-- ==================== VERIFICATION: Check final state ====================
-- Run this to verify all permissions now have action and module_id

SELECT
    p.id,
    p.name,
    p.code,
    p.action,
    p.module_id,
    m.name as module_name,
    m.code as module_code
FROM permissions p
LEFT JOIN modules m ON p.module_id = m.id
ORDER BY m.code, p.code;

-- Count of fixed permissions
SELECT
    COUNT(*) as total_permissions,
    COUNT(action) as with_action,
    COUNT(module_id) as with_module,
    COUNT(*) - COUNT(action) as missing_action,
    COUNT(*) - COUNT(module_id) as missing_module
FROM permissions;
