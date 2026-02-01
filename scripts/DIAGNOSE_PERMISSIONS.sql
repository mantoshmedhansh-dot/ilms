-- ============================================================================
-- DIAGNOSE PERMISSIONS - Run each section separately to understand the state
-- ============================================================================

-- 1. Check for permissions with NULL module_id
SELECT 'Permissions with NULL module_id' as issue;
SELECT id, code, name, action, module_id
FROM permissions
WHERE module_id IS NULL;

-- 2. Check for permissions with NULL action
SELECT 'Permissions with NULL action' as issue;
SELECT id, code, name, action, module_id
FROM permissions
WHERE action IS NULL;

-- 3. Check permissions by code prefix (to see if they exist but aren't linked)
SELECT 'Permissions by code prefix' as info;
SELECT
    SPLIT_PART(code, ':', 1) as module_prefix,
    COUNT(*) as count,
    ARRAY_AGG(code) as permission_codes
FROM permissions
GROUP BY SPLIT_PART(code, ':', 1)
ORDER BY module_prefix;

-- 4. Check which permission codes SHOULD exist (based on module codes)
SELECT 'Expected vs Actual permissions' as info;
SELECT
    m.code as module_code,
    m.name as module_name,
    (SELECT COUNT(*) FROM permissions p WHERE p.module_id = m.id) as actual_perms,
    (SELECT COUNT(*) FROM permissions p WHERE SPLIT_PART(p.code, ':', 1) = m.code) as matching_prefix_perms
FROM modules m
ORDER BY m.code;

-- 5. Find orphan permissions (code prefix doesn't match any module)
SELECT 'Orphan permissions (prefix doesnt match any module)' as issue;
SELECT p.id, p.code, p.name, p.module_id,
    SPLIT_PART(p.code, ':', 1) as code_prefix
FROM permissions p
WHERE NOT EXISTS (
    SELECT 1 FROM modules m WHERE m.code = SPLIT_PART(p.code, ':', 1)
);

-- 6. Total counts
SELECT 'Summary counts' as info;
SELECT
    (SELECT COUNT(*) FROM modules) as total_modules,
    (SELECT COUNT(*) FROM permissions) as total_permissions,
    (SELECT COUNT(*) FROM permissions WHERE module_id IS NULL) as null_module_perms,
    (SELECT COUNT(*) FROM permissions WHERE action IS NULL) as null_action_perms;
