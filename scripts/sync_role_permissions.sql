-- =====================================================
-- SYNC ROLE PERMISSIONS - Run in Supabase SQL Editor
-- =====================================================
-- This script assigns permissions to roles based on their level/department.
-- Safe to run multiple times (uses ON CONFLICT DO NOTHING).
-- =====================================================

-- First, let's see what we have
DO $$
DECLARE
    role_count INT;
    perm_count INT;
    rp_count INT;
BEGIN
    SELECT COUNT(*) INTO role_count FROM roles WHERE is_active = true;
    SELECT COUNT(*) INTO perm_count FROM permissions WHERE is_active = true;
    SELECT COUNT(*) INTO rp_count FROM role_permissions;

    RAISE NOTICE 'Current state: % roles, % permissions, % role_permissions', role_count, perm_count, rp_count;
END $$;

-- =====================================================
-- SUPER_ADMIN: Gets ALL permissions
-- =====================================================
INSERT INTO role_permissions (id, role_id, permission_id, created_at)
SELECT
    gen_random_uuid(),
    r.id,
    p.id,
    NOW()
FROM roles r
CROSS JOIN permissions p
WHERE UPPER(r.code) = 'SUPER_ADMIN'
  AND r.is_active = true
  AND p.is_active = true
ON CONFLICT (role_id, permission_id) DO NOTHING;

-- =====================================================
-- DIRECTOR: Strategic oversight - view access + approvals
-- =====================================================
INSERT INTO role_permissions (id, role_id, permission_id, created_at)
SELECT
    gen_random_uuid(),
    r.id,
    p.id,
    NOW()
FROM roles r
CROSS JOIN permissions p
WHERE UPPER(r.code) = 'DIRECTOR'
  AND r.is_active = true
  AND p.is_active = true
  AND (
    -- View access to everything
    LOWER(p.code) LIKE '%view%'
    OR LOWER(p.code) LIKE '%export%'
    -- Approval rights
    OR LOWER(p.code) LIKE '%approve%'
    -- Escalation
    OR LOWER(p.code) LIKE '%escalate%'
    -- Track
    OR LOWER(p.code) LIKE '%track%'
    -- Publish
    OR LOWER(p.code) LIKE '%publish%'
    -- Schedule
    OR LOWER(p.code) LIKE '%schedule%'
  )
ON CONFLICT (role_id, permission_id) DO NOTHING;

-- =====================================================
-- SALES_HEAD: Full sales access
-- =====================================================
INSERT INTO role_permissions (id, role_id, permission_id, created_at)
SELECT
    gen_random_uuid(),
    r.id,
    p.id,
    NOW()
FROM roles r
CROSS JOIN permissions p
WHERE UPPER(r.code) = 'SALES_HEAD'
  AND r.is_active = true
  AND p.is_active = true
  AND (
    -- Dashboard
    LOWER(p.code) LIKE '%dashboard%'
    -- Products (view, export)
    OR (LOWER(p.code) LIKE '%product%' AND (LOWER(p.code) LIKE '%view%' OR LOWER(p.code) LIKE '%export%'))
    -- Orders (full access)
    OR LOWER(p.code) LIKE '%order%'
    -- CRM/Customers (full access)
    OR LOWER(p.code) LIKE '%crm%'
    OR LOWER(p.code) LIKE '%customer%'
    -- Reports
    OR (LOWER(p.code) LIKE '%report%' AND (LOWER(p.code) LIKE '%view%' OR LOWER(p.code) LIKE '%export%'))
    -- Notifications (view)
    OR (LOWER(p.code) LIKE '%notification%' AND LOWER(p.code) LIKE '%view%')
  )
ON CONFLICT (role_id, permission_id) DO NOTHING;

-- =====================================================
-- SERVICE_HEAD: Full service access
-- =====================================================
INSERT INTO role_permissions (id, role_id, permission_id, created_at)
SELECT
    gen_random_uuid(),
    r.id,
    p.id,
    NOW()
FROM roles r
CROSS JOIN permissions p
WHERE UPPER(r.code) = 'SERVICE_HEAD'
  AND r.is_active = true
  AND p.is_active = true
  AND (
    -- Dashboard
    LOWER(p.code) LIKE '%dashboard%'
    -- Products (view)
    OR (LOWER(p.code) LIKE '%product%' AND LOWER(p.code) LIKE '%view%')
    -- Service (full access)
    OR LOWER(p.code) LIKE '%service%'
    -- Complaints (full access)
    OR LOWER(p.code) LIKE '%complaint%'
    -- CRM/Customers (view, update)
    OR (LOWER(p.code) LIKE '%crm%' AND (LOWER(p.code) LIKE '%view%' OR LOWER(p.code) LIKE '%update%'))
    OR (LOWER(p.code) LIKE '%customer%' AND (LOWER(p.code) LIKE '%view%' OR LOWER(p.code) LIKE '%update%'))
    -- Inventory (view)
    OR (LOWER(p.code) LIKE '%inventory%' AND LOWER(p.code) LIKE '%view%')
    -- Reports
    OR (LOWER(p.code) LIKE '%report%' AND (LOWER(p.code) LIKE '%view%' OR LOWER(p.code) LIKE '%export%'))
    -- Notifications (view)
    OR (LOWER(p.code) LIKE '%notification%' AND LOWER(p.code) LIKE '%view%')
  )
ON CONFLICT (role_id, permission_id) DO NOTHING;

-- =====================================================
-- ACCOUNTS_HEAD: Day-to-day accounting operations
-- =====================================================
INSERT INTO role_permissions (id, role_id, permission_id, created_at)
SELECT
    gen_random_uuid(),
    r.id,
    p.id,
    NOW()
FROM roles r
CROSS JOIN permissions p
WHERE UPPER(r.code) = 'ACCOUNTS_HEAD'
  AND r.is_active = true
  AND p.is_active = true
  AND (
    -- Dashboard
    LOWER(p.code) LIKE '%dashboard%'
    -- Products (view)
    OR (LOWER(p.code) LIKE '%product%' AND LOWER(p.code) LIKE '%view%')
    -- Orders (view, export)
    OR (LOWER(p.code) LIKE '%order%' AND (LOWER(p.code) LIKE '%view%' OR LOWER(p.code) LIKE '%export%'))
    -- Inventory (view, adjust, export)
    OR (LOWER(p.code) LIKE '%inventory%' AND (LOWER(p.code) LIKE '%view%' OR LOWER(p.code) LIKE '%adjust%' OR LOWER(p.code) LIKE '%export%'))
    -- CRM/Customers (view, export)
    OR (LOWER(p.code) LIKE '%crm%' AND (LOWER(p.code) LIKE '%view%' OR LOWER(p.code) LIKE '%export%'))
    OR (LOWER(p.code) LIKE '%customer%' AND (LOWER(p.code) LIKE '%view%' OR LOWER(p.code) LIKE '%export%'))
    -- Vendors (view, create, update)
    OR (LOWER(p.code) LIKE '%vendor%' AND (LOWER(p.code) LIKE '%view%' OR LOWER(p.code) LIKE '%create%' OR LOWER(p.code) LIKE '%update%'))
    -- Procurement/Purchase (view, receive)
    OR (LOWER(p.code) LIKE '%procurement%' AND (LOWER(p.code) LIKE '%view%' OR LOWER(p.code) LIKE '%receive%'))
    OR (LOWER(p.code) LIKE '%purchase%' AND (LOWER(p.code) LIKE '%view%' OR LOWER(p.code) LIKE '%receive%'))
    -- GRN (view, create, update)
    OR (LOWER(p.code) LIKE '%grn%' AND (LOWER(p.code) LIKE '%view%' OR LOWER(p.code) LIKE '%create%' OR LOWER(p.code) LIKE '%update%'))
    -- Finance (view, create, update, reconcile, export)
    OR (LOWER(p.code) LIKE '%finance%' AND NOT LOWER(p.code) LIKE '%approve%' AND NOT LOWER(p.code) LIKE '%delete%')
    -- Accounting (view, create, update)
    OR (LOWER(p.code) LIKE '%accounting%' AND (LOWER(p.code) LIKE '%view%' OR LOWER(p.code) LIKE '%create%' OR LOWER(p.code) LIKE '%update%'))
    -- Billing (view, create, update)
    OR (LOWER(p.code) LIKE '%billing%' AND (LOWER(p.code) LIKE '%view%' OR LOWER(p.code) LIKE '%create%' OR LOWER(p.code) LIKE '%update%'))
    -- Reports (view, export)
    OR (LOWER(p.code) LIKE '%report%' AND (LOWER(p.code) LIKE '%view%' OR LOWER(p.code) LIKE '%export%'))
    -- Notifications (view)
    OR (LOWER(p.code) LIKE '%notification%' AND LOWER(p.code) LIKE '%view%')
    -- Service (view)
    OR (LOWER(p.code) LIKE '%service%' AND LOWER(p.code) LIKE '%view%')
  )
ON CONFLICT (role_id, permission_id) DO NOTHING;

-- =====================================================
-- FINANCE_HEAD: Strategic finance oversight + approvals
-- =====================================================
INSERT INTO role_permissions (id, role_id, permission_id, created_at)
SELECT
    gen_random_uuid(),
    r.id,
    p.id,
    NOW()
FROM roles r
CROSS JOIN permissions p
WHERE UPPER(r.code) = 'FINANCE_HEAD'
  AND r.is_active = true
  AND p.is_active = true
  AND (
    -- Dashboard
    LOWER(p.code) LIKE '%dashboard%'
    -- Products (view, export)
    OR (LOWER(p.code) LIKE '%product%' AND (LOWER(p.code) LIKE '%view%' OR LOWER(p.code) LIKE '%export%'))
    -- Orders (full access)
    OR LOWER(p.code) LIKE '%order%'
    -- Inventory (view, adjust, export)
    OR (LOWER(p.code) LIKE '%inventory%' AND (LOWER(p.code) LIKE '%view%' OR LOWER(p.code) LIKE '%adjust%' OR LOWER(p.code) LIKE '%export%'))
    -- Service (view)
    OR (LOWER(p.code) LIKE '%service%' AND LOWER(p.code) LIKE '%view%')
    -- CRM/Customers (view, export)
    OR (LOWER(p.code) LIKE '%crm%' AND (LOWER(p.code) LIKE '%view%' OR LOWER(p.code) LIKE '%export%'))
    OR (LOWER(p.code) LIKE '%customer%' AND (LOWER(p.code) LIKE '%view%' OR LOWER(p.code) LIKE '%export%'))
    -- Vendors (full access)
    OR LOWER(p.code) LIKE '%vendor%'
    -- Logistics (view, track)
    OR (LOWER(p.code) LIKE '%logistics%' AND (LOWER(p.code) LIKE '%view%' OR LOWER(p.code) LIKE '%track%'))
    -- Procurement/Purchase (full access)
    OR LOWER(p.code) LIKE '%procurement%'
    OR LOWER(p.code) LIKE '%purchase%'
    -- GRN (full access)
    OR LOWER(p.code) LIKE '%grn%'
    -- Finance (full access)
    OR LOWER(p.code) LIKE '%finance%'
    -- Accounting (full access)
    OR LOWER(p.code) LIKE '%accounting%'
    -- Billing (full access)
    OR LOWER(p.code) LIKE '%billing%'
    -- HR (view)
    OR (LOWER(p.code) LIKE '%hr%' AND LOWER(p.code) LIKE '%view%')
    -- Payroll (view, process, approve)
    OR LOWER(p.code) LIKE '%payroll%'
    -- Marketing (view)
    OR (LOWER(p.code) LIKE '%marketing%' AND LOWER(p.code) LIKE '%view%')
    -- Reports (full access)
    OR LOWER(p.code) LIKE '%report%'
    -- Notifications (view, create)
    OR (LOWER(p.code) LIKE '%notification%' AND (LOWER(p.code) LIKE '%view%' OR LOWER(p.code) LIKE '%create%'))
    -- Settings (view)
    OR (LOWER(p.code) LIKE '%setting%' AND LOWER(p.code) LIKE '%view%')
    -- Access Control (view)
    OR (LOWER(p.code) LIKE '%access%' AND LOWER(p.code) LIKE '%view%')
  )
ON CONFLICT (role_id, permission_id) DO NOTHING;

-- =====================================================
-- OPERATIONS_HEAD: Inventory + Logistics + Procurement
-- =====================================================
INSERT INTO role_permissions (id, role_id, permission_id, created_at)
SELECT
    gen_random_uuid(),
    r.id,
    p.id,
    NOW()
FROM roles r
CROSS JOIN permissions p
WHERE UPPER(r.code) = 'OPERATIONS_HEAD'
  AND r.is_active = true
  AND p.is_active = true
  AND (
    -- Dashboard
    LOWER(p.code) LIKE '%dashboard%'
    -- Products (view, update)
    OR (LOWER(p.code) LIKE '%product%' AND (LOWER(p.code) LIKE '%view%' OR LOWER(p.code) LIKE '%update%'))
    -- Orders (view, update)
    OR (LOWER(p.code) LIKE '%order%' AND (LOWER(p.code) LIKE '%view%' OR LOWER(p.code) LIKE '%update%'))
    -- Inventory (full access)
    OR LOWER(p.code) LIKE '%inventory%'
    -- Logistics (full access)
    OR LOWER(p.code) LIKE '%logistics%'
    -- Procurement/Purchase (view, create, update, receive)
    OR (LOWER(p.code) LIKE '%procurement%' AND NOT LOWER(p.code) LIKE '%approve%')
    OR (LOWER(p.code) LIKE '%purchase%' AND NOT LOWER(p.code) LIKE '%approve%')
    -- GRN (view, create, update)
    OR (LOWER(p.code) LIKE '%grn%' AND (LOWER(p.code) LIKE '%view%' OR LOWER(p.code) LIKE '%create%' OR LOWER(p.code) LIKE '%update%'))
    -- Vendors (view, create, update)
    OR (LOWER(p.code) LIKE '%vendor%' AND (LOWER(p.code) LIKE '%view%' OR LOWER(p.code) LIKE '%create%' OR LOWER(p.code) LIKE '%update%'))
    -- Reports (view, export)
    OR (LOWER(p.code) LIKE '%report%' AND (LOWER(p.code) LIKE '%view%' OR LOWER(p.code) LIKE '%export%'))
    -- Notifications (view)
    OR (LOWER(p.code) LIKE '%notification%' AND LOWER(p.code) LIKE '%view%')
  )
ON CONFLICT (role_id, permission_id) DO NOTHING;

-- =====================================================
-- REGIONAL_MANAGER: Limited territory access
-- =====================================================
INSERT INTO role_permissions (id, role_id, permission_id, created_at)
SELECT
    gen_random_uuid(),
    r.id,
    p.id,
    NOW()
FROM roles r
CROSS JOIN permissions p
WHERE UPPER(r.code) = 'REGIONAL_MANAGER'
  AND r.is_active = true
  AND p.is_active = true
  AND (
    LOWER(p.code) LIKE '%dashboard%view%'
    OR (LOWER(p.code) LIKE '%product%' AND LOWER(p.code) LIKE '%view%')
    OR (LOWER(p.code) LIKE '%order%' AND (LOWER(p.code) LIKE '%view%' OR LOWER(p.code) LIKE '%create%' OR LOWER(p.code) LIKE '%update%' OR LOWER(p.code) LIKE '%export%'))
    OR (LOWER(p.code) LIKE '%crm%' AND (LOWER(p.code) LIKE '%view%' OR LOWER(p.code) LIKE '%create%' OR LOWER(p.code) LIKE '%update%'))
    OR (LOWER(p.code) LIKE '%customer%' AND (LOWER(p.code) LIKE '%view%' OR LOWER(p.code) LIKE '%create%' OR LOWER(p.code) LIKE '%update%'))
    OR (LOWER(p.code) LIKE '%complaint%' AND (LOWER(p.code) LIKE '%view%' OR LOWER(p.code) LIKE '%update%'))
    OR (LOWER(p.code) LIKE '%report%' AND (LOWER(p.code) LIKE '%view%' OR LOWER(p.code) LIKE '%export%'))
    OR (LOWER(p.code) LIKE '%notification%' AND LOWER(p.code) LIKE '%view%')
  )
ON CONFLICT (role_id, permission_id) DO NOTHING;

-- =====================================================
-- WAREHOUSE_MANAGER: Inventory control
-- =====================================================
INSERT INTO role_permissions (id, role_id, permission_id, created_at)
SELECT
    gen_random_uuid(),
    r.id,
    p.id,
    NOW()
FROM roles r
CROSS JOIN permissions p
WHERE UPPER(r.code) = 'WAREHOUSE_MANAGER'
  AND r.is_active = true
  AND p.is_active = true
  AND (
    LOWER(p.code) LIKE '%dashboard%view%'
    OR (LOWER(p.code) LIKE '%product%' AND LOWER(p.code) LIKE '%view%')
    OR LOWER(p.code) LIKE '%inventory%'
    OR (LOWER(p.code) LIKE '%logistics%' AND (LOWER(p.code) LIKE '%view%' OR LOWER(p.code) LIKE '%create%' OR LOWER(p.code) LIKE '%assign%'))
    OR (LOWER(p.code) LIKE '%procurement%' AND (LOWER(p.code) LIKE '%view%' OR LOWER(p.code) LIKE '%receive%'))
    OR (LOWER(p.code) LIKE '%purchase%' AND (LOWER(p.code) LIKE '%view%' OR LOWER(p.code) LIKE '%receive%'))
    OR (LOWER(p.code) LIKE '%grn%' AND (LOWER(p.code) LIKE '%view%' OR LOWER(p.code) LIKE '%create%' OR LOWER(p.code) LIKE '%update%'))
    OR (LOWER(p.code) LIKE '%report%' AND LOWER(p.code) LIKE '%view%')
    OR (LOWER(p.code) LIKE '%notification%' AND LOWER(p.code) LIKE '%view%')
  )
ON CONFLICT (role_id, permission_id) DO NOTHING;

-- =====================================================
-- SERVICE_MANAGER: Service center operations
-- =====================================================
INSERT INTO role_permissions (id, role_id, permission_id, created_at)
SELECT
    gen_random_uuid(),
    r.id,
    p.id,
    NOW()
FROM roles r
CROSS JOIN permissions p
WHERE UPPER(r.code) = 'SERVICE_MANAGER'
  AND r.is_active = true
  AND p.is_active = true
  AND (
    LOWER(p.code) LIKE '%dashboard%view%'
    OR (LOWER(p.code) LIKE '%product%' AND LOWER(p.code) LIKE '%view%')
    OR (LOWER(p.code) LIKE '%service%' AND NOT LOWER(p.code) LIKE '%escalate%')
    OR (LOWER(p.code) LIKE '%complaint%' AND NOT LOWER(p.code) LIKE '%escalate%')
    OR (LOWER(p.code) LIKE '%crm%' AND (LOWER(p.code) LIKE '%view%' OR LOWER(p.code) LIKE '%update%'))
    OR (LOWER(p.code) LIKE '%customer%' AND (LOWER(p.code) LIKE '%view%' OR LOWER(p.code) LIKE '%update%'))
    OR (LOWER(p.code) LIKE '%inventory%' AND LOWER(p.code) LIKE '%view%')
    OR (LOWER(p.code) LIKE '%report%' AND LOWER(p.code) LIKE '%view%')
    OR (LOWER(p.code) LIKE '%notification%' AND LOWER(p.code) LIKE '%view%')
  )
ON CONFLICT (role_id, permission_id) DO NOTHING;

-- =====================================================
-- MARKETING_MANAGER: Marketing campaigns
-- =====================================================
INSERT INTO role_permissions (id, role_id, permission_id, created_at)
SELECT
    gen_random_uuid(),
    r.id,
    p.id,
    NOW()
FROM roles r
CROSS JOIN permissions p
WHERE UPPER(r.code) = 'MARKETING_MANAGER'
  AND r.is_active = true
  AND p.is_active = true
  AND (
    LOWER(p.code) LIKE '%dashboard%view%'
    OR (LOWER(p.code) LIKE '%product%' AND LOWER(p.code) LIKE '%view%')
    OR LOWER(p.code) LIKE '%marketing%'
    OR (LOWER(p.code) LIKE '%crm%' AND (LOWER(p.code) LIKE '%view%' OR LOWER(p.code) LIKE '%export%'))
    OR (LOWER(p.code) LIKE '%customer%' AND (LOWER(p.code) LIKE '%view%' OR LOWER(p.code) LIKE '%export%'))
    OR (LOWER(p.code) LIKE '%report%' AND (LOWER(p.code) LIKE '%view%' OR LOWER(p.code) LIKE '%export%'))
    OR LOWER(p.code) LIKE '%notification%'
  )
ON CONFLICT (role_id, permission_id) DO NOTHING;

-- =====================================================
-- CUSTOMER_SERVICE_EXECUTIVE
-- =====================================================
INSERT INTO role_permissions (id, role_id, permission_id, created_at)
SELECT
    gen_random_uuid(),
    r.id,
    p.id,
    NOW()
FROM roles r
CROSS JOIN permissions p
WHERE UPPER(r.code) = 'CUSTOMER_SERVICE_EXECUTIVE'
  AND r.is_active = true
  AND p.is_active = true
  AND (
    LOWER(p.code) LIKE '%dashboard%view%'
    OR (LOWER(p.code) LIKE '%product%' AND LOWER(p.code) LIKE '%view%')
    OR (LOWER(p.code) LIKE '%service%' AND (LOWER(p.code) LIKE '%view%' OR LOWER(p.code) LIKE '%create%' OR LOWER(p.code) LIKE '%update%'))
    OR (LOWER(p.code) LIKE '%complaint%' AND (LOWER(p.code) LIKE '%view%' OR LOWER(p.code) LIKE '%create%' OR LOWER(p.code) LIKE '%update%'))
    OR (LOWER(p.code) LIKE '%crm%' AND (LOWER(p.code) LIKE '%view%' OR LOWER(p.code) LIKE '%create%' OR LOWER(p.code) LIKE '%update%'))
    OR (LOWER(p.code) LIKE '%customer%' AND (LOWER(p.code) LIKE '%view%' OR LOWER(p.code) LIKE '%create%' OR LOWER(p.code) LIKE '%update%'))
    OR (LOWER(p.code) LIKE '%order%' AND LOWER(p.code) LIKE '%view%')
    OR (LOWER(p.code) LIKE '%notification%' AND LOWER(p.code) LIKE '%view%')
  )
ON CONFLICT (role_id, permission_id) DO NOTHING;

-- =====================================================
-- SALES_EXECUTIVE
-- =====================================================
INSERT INTO role_permissions (id, role_id, permission_id, created_at)
SELECT
    gen_random_uuid(),
    r.id,
    p.id,
    NOW()
FROM roles r
CROSS JOIN permissions p
WHERE UPPER(r.code) = 'SALES_EXECUTIVE'
  AND r.is_active = true
  AND p.is_active = true
  AND (
    LOWER(p.code) LIKE '%dashboard%view%'
    OR (LOWER(p.code) LIKE '%product%' AND LOWER(p.code) LIKE '%view%')
    OR (LOWER(p.code) LIKE '%order%' AND (LOWER(p.code) LIKE '%view%' OR LOWER(p.code) LIKE '%create%'))
    OR (LOWER(p.code) LIKE '%crm%' AND (LOWER(p.code) LIKE '%view%' OR LOWER(p.code) LIKE '%create%' OR LOWER(p.code) LIKE '%update%'))
    OR (LOWER(p.code) LIKE '%customer%' AND (LOWER(p.code) LIKE '%view%' OR LOWER(p.code) LIKE '%create%' OR LOWER(p.code) LIKE '%update%'))
    OR (LOWER(p.code) LIKE '%inventory%' AND LOWER(p.code) LIKE '%view%')
    OR (LOWER(p.code) LIKE '%notification%' AND LOWER(p.code) LIKE '%view%')
  )
ON CONFLICT (role_id, permission_id) DO NOTHING;

-- =====================================================
-- ACCOUNTS_EXECUTIVE
-- =====================================================
INSERT INTO role_permissions (id, role_id, permission_id, created_at)
SELECT
    gen_random_uuid(),
    r.id,
    p.id,
    NOW()
FROM roles r
CROSS JOIN permissions p
WHERE UPPER(r.code) = 'ACCOUNTS_EXECUTIVE'
  AND r.is_active = true
  AND p.is_active = true
  AND (
    LOWER(p.code) LIKE '%dashboard%view%'
    OR (LOWER(p.code) LIKE '%order%' AND LOWER(p.code) LIKE '%view%')
    OR (LOWER(p.code) LIKE '%finance%' AND (LOWER(p.code) LIKE '%view%' OR LOWER(p.code) LIKE '%create%' OR LOWER(p.code) LIKE '%update%'))
    OR (LOWER(p.code) LIKE '%accounting%' AND (LOWER(p.code) LIKE '%view%' OR LOWER(p.code) LIKE '%create%' OR LOWER(p.code) LIKE '%update%'))
    OR (LOWER(p.code) LIKE '%billing%' AND (LOWER(p.code) LIKE '%view%' OR LOWER(p.code) LIKE '%create%' OR LOWER(p.code) LIKE '%update%'))
    OR (LOWER(p.code) LIKE '%vendor%' AND LOWER(p.code) LIKE '%view%')
    OR (LOWER(p.code) LIKE '%procurement%' AND LOWER(p.code) LIKE '%view%')
    OR (LOWER(p.code) LIKE '%purchase%' AND LOWER(p.code) LIKE '%view%')
    OR (LOWER(p.code) LIKE '%notification%' AND LOWER(p.code) LIKE '%view%')
  )
ON CONFLICT (role_id, permission_id) DO NOTHING;

-- =====================================================
-- TECHNICIAN_SUPERVISOR
-- =====================================================
INSERT INTO role_permissions (id, role_id, permission_id, created_at)
SELECT
    gen_random_uuid(),
    r.id,
    p.id,
    NOW()
FROM roles r
CROSS JOIN permissions p
WHERE UPPER(r.code) = 'TECHNICIAN_SUPERVISOR'
  AND r.is_active = true
  AND p.is_active = true
  AND (
    LOWER(p.code) LIKE '%dashboard%view%'
    OR (LOWER(p.code) LIKE '%product%' AND LOWER(p.code) LIKE '%view%')
    OR (LOWER(p.code) LIKE '%service%' AND (LOWER(p.code) LIKE '%view%' OR LOWER(p.code) LIKE '%update%' OR LOWER(p.code) LIKE '%close%'))
    OR (LOWER(p.code) LIKE '%complaint%' AND (LOWER(p.code) LIKE '%view%' OR LOWER(p.code) LIKE '%update%'))
    OR (LOWER(p.code) LIKE '%inventory%' AND LOWER(p.code) LIKE '%view%')
    OR (LOWER(p.code) LIKE '%logistics%' AND (LOWER(p.code) LIKE '%view%' OR LOWER(p.code) LIKE '%track%'))
    OR (LOWER(p.code) LIKE '%notification%' AND LOWER(p.code) LIKE '%view%')
  )
ON CONFLICT (role_id, permission_id) DO NOTHING;

-- =====================================================
-- SYSTEM: System role (same as SUPER_ADMIN - all permissions)
-- =====================================================
INSERT INTO role_permissions (id, role_id, permission_id, created_at)
SELECT
    gen_random_uuid(),
    r.id,
    p.id,
    NOW()
FROM roles r
CROSS JOIN permissions p
WHERE UPPER(r.code) = 'SYSTEM'
  AND r.is_active = true
  AND p.is_active = true
ON CONFLICT (role_id, permission_id) DO NOTHING;

-- =====================================================
-- MANAGER: Generic manager role (combined permissions)
-- =====================================================
INSERT INTO role_permissions (id, role_id, permission_id, created_at)
SELECT
    gen_random_uuid(),
    r.id,
    p.id,
    NOW()
FROM roles r
CROSS JOIN permissions p
WHERE UPPER(r.code) = 'MANAGER'
  AND r.is_active = true
  AND p.is_active = true
  AND (
    -- Dashboard
    LOWER(p.code) LIKE '%dashboard%'
    -- Products (view)
    OR (LOWER(p.code) LIKE '%product%' AND LOWER(p.code) LIKE '%view%')
    -- Orders (view, create, update, export)
    OR (LOWER(p.code) LIKE '%order%' AND (LOWER(p.code) LIKE '%view%' OR LOWER(p.code) LIKE '%create%' OR LOWER(p.code) LIKE '%update%' OR LOWER(p.code) LIKE '%export%'))
    -- Inventory (view, create, update, transfer, adjust)
    OR LOWER(p.code) LIKE '%inventory%'
    -- Service (view, create, update, assign, close)
    OR (LOWER(p.code) LIKE '%service%' AND NOT LOWER(p.code) LIKE '%escalate%')
    -- Complaints (view, update, assign, resolve)
    OR (LOWER(p.code) LIKE '%complaint%' AND NOT LOWER(p.code) LIKE '%escalate%')
    -- CRM/Customers (view, create, update)
    OR (LOWER(p.code) LIKE '%crm%' AND (LOWER(p.code) LIKE '%view%' OR LOWER(p.code) LIKE '%create%' OR LOWER(p.code) LIKE '%update%'))
    OR (LOWER(p.code) LIKE '%customer%' AND (LOWER(p.code) LIKE '%view%' OR LOWER(p.code) LIKE '%create%' OR LOWER(p.code) LIKE '%update%'))
    -- Logistics (view, create, assign)
    OR (LOWER(p.code) LIKE '%logistics%' AND (LOWER(p.code) LIKE '%view%' OR LOWER(p.code) LIKE '%create%' OR LOWER(p.code) LIKE '%assign%'))
    -- Procurement/Purchase (view, receive)
    OR (LOWER(p.code) LIKE '%procurement%' AND (LOWER(p.code) LIKE '%view%' OR LOWER(p.code) LIKE '%receive%'))
    OR (LOWER(p.code) LIKE '%purchase%' AND (LOWER(p.code) LIKE '%view%' OR LOWER(p.code) LIKE '%receive%'))
    -- GRN (view, create, update)
    OR (LOWER(p.code) LIKE '%grn%' AND (LOWER(p.code) LIKE '%view%' OR LOWER(p.code) LIKE '%create%' OR LOWER(p.code) LIKE '%update%'))
    -- Reports (view, export)
    OR (LOWER(p.code) LIKE '%report%' AND (LOWER(p.code) LIKE '%view%' OR LOWER(p.code) LIKE '%export%'))
    -- Notifications (view)
    OR (LOWER(p.code) LIKE '%notification%' AND LOWER(p.code) LIKE '%view%')
    -- Marketing (view, create, update)
    OR (LOWER(p.code) LIKE '%marketing%' AND (LOWER(p.code) LIKE '%view%' OR LOWER(p.code) LIKE '%create%' OR LOWER(p.code) LIKE '%update%'))
  )
ON CONFLICT (role_id, permission_id) DO NOTHING;

-- =====================================================
-- FINAL REPORT: Show permission counts per role
-- =====================================================
SELECT
    r.code as role_code,
    r.name as role_name,
    r.level,
    COUNT(rp.id) as permission_count
FROM roles r
LEFT JOIN role_permissions rp ON r.id = rp.role_id
WHERE r.is_active = true
GROUP BY r.id, r.code, r.name, r.level
ORDER BY
    CASE r.level
        WHEN 'SUPER_ADMIN' THEN 0
        WHEN 'DIRECTOR' THEN 1
        WHEN 'HEAD' THEN 2
        WHEN 'MANAGER' THEN 3
        WHEN 'EXECUTIVE' THEN 4
        ELSE 5
    END,
    r.name;
