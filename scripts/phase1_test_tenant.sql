-- ============================================================================
-- PHASE 1: Create Test Tenant and Verify Setup
-- ============================================================================
-- Run this AFTER phase1_setup_supabase.sql
-- Date: 2026-02-01
-- ============================================================================

-- ====================
-- VERIFICATION: Check Tables Exist
-- ====================
SELECT
    'Tables Created' as status,
    COUNT(*) as table_count
FROM information_schema.tables
WHERE table_schema = 'public'
AND table_name IN (
    'tenants', 'modules', 'plans', 'tenant_subscriptions',
    'feature_flags', 'billing_history', 'usage_metrics'
);
-- Expected: table_count = 7

-- ====================
-- VERIFICATION: Check Modules Seeded
-- ====================
SELECT
    'Modules Seeded' as status,
    code,
    name,
    price_monthly
FROM public.modules
ORDER BY display_order;
-- Expected: 10 rows

-- ====================
-- VERIFICATION: Check Plans Seeded
-- ====================
SELECT
    'Plans Seeded' as status,
    slug,
    name,
    price_inr,
    ARRAY_LENGTH(included_modules, 1) as module_count
FROM public.plans
ORDER BY display_order;
-- Expected: 4 rows

-- ====================
-- CREATE TEST TENANT
-- ====================

-- Insert test tenant
INSERT INTO public.tenants (
    name,
    subdomain,
    database_schema,
    status,
    plan_id
)
VALUES (
    'Test Company',
    'testcompany',
    'tenant_testcompany',
    'active',
    (SELECT id FROM public.plans WHERE slug = 'starter')
)
ON CONFLICT (subdomain) DO UPDATE
SET
    name = EXCLUDED.name,
    updated_at = NOW()
RETURNING id, name, subdomain, database_schema;

-- ====================
-- CREATE TEST TENANT SUBSCRIPTIONS
-- ====================

-- Get test tenant ID
DO $$
DECLARE
    v_tenant_id UUID;
BEGIN
    -- Get tenant ID
    SELECT id INTO v_tenant_id
    FROM public.tenants
    WHERE subdomain = 'testcompany';

    -- Delete existing subscriptions for clean slate
    DELETE FROM public.tenant_subscriptions
    WHERE tenant_id = v_tenant_id;

    -- Add subscriptions for Starter plan modules
    -- (system_admin, oms_fulfillment, d2c_storefront)
    INSERT INTO public.tenant_subscriptions (
        tenant_id,
        module_id,
        status,
        starts_at
    )
    SELECT
        v_tenant_id,
        m.id,
        'active',
        NOW()
    FROM public.modules m
    WHERE m.code IN ('system_admin', 'oms_fulfillment', 'd2c_storefront');

    RAISE NOTICE 'Test tenant subscriptions created for tenant_id: %', v_tenant_id;
END $$;

-- ====================
-- VERIFICATION: Check Test Tenant
-- ====================

-- Get tenant details
SELECT
    'Test Tenant Created' as status,
    t.id,
    t.name,
    t.subdomain,
    t.database_schema,
    p.name as plan_name
FROM public.tenants t
LEFT JOIN public.plans p ON t.plan_id = p.id
WHERE t.subdomain = 'testcompany';

-- Get tenant subscriptions
SELECT
    'Tenant Subscriptions' as status,
    t.name as tenant_name,
    m.code as module_code,
    m.name as module_name,
    ts.status,
    ts.starts_at
FROM public.tenant_subscriptions ts
JOIN public.tenants t ON ts.tenant_id = t.id
JOIN public.modules m ON ts.module_id = m.id
WHERE t.subdomain = 'testcompany'
ORDER BY m.display_order;

-- Expected: 3 subscriptions (system_admin, oms_fulfillment, d2c_storefront)

-- ====================
-- TEST QUERIES
-- ====================

-- Get enabled modules for test tenant
SELECT
    m.code,
    m.name
FROM public.modules m
JOIN public.tenant_subscriptions ts ON ts.module_id = m.id
JOIN public.tenants t ON ts.tenant_id = t.id
WHERE t.subdomain = 'testcompany'
AND ts.status = 'active'
ORDER BY m.display_order;

-- Check if tenant has access to specific module (should return true)
SELECT EXISTS (
    SELECT 1
    FROM public.tenant_subscriptions ts
    JOIN public.tenants t ON ts.tenant_id = t.id
    JOIN public.modules m ON ts.module_id = m.id
    WHERE t.subdomain = 'testcompany'
    AND m.code = 'oms_fulfillment'
    AND ts.status = 'active'
) as has_oms_access;
-- Expected: true

-- Check if tenant has access to module they don't have (should return false)
SELECT EXISTS (
    SELECT 1
    FROM public.tenant_subscriptions ts
    JOIN public.tenants t ON ts.tenant_id = t.id
    JOIN public.modules m ON ts.module_id = m.id
    WHERE t.subdomain = 'testcompany'
    AND m.code = 'finance'
    AND ts.status = 'active'
) as has_finance_access;
-- Expected: false

-- ====================
-- GET TEST TENANT ID FOR API TESTING
-- ====================
SELECT
    '=== COPY THIS TENANT ID FOR API TESTING ===' as note,
    id as tenant_id
FROM public.tenants
WHERE subdomain = 'testcompany';

-- ============================================================================
-- SUCCESS!
-- ============================================================================
-- Test tenant "Test Company" created with subdomain: testcompany
-- Enabled modules: system_admin, oms_fulfillment, d2c_storefront
-- Use the tenant_id above in X-Tenant-ID header for API testing
-- ============================================================================
