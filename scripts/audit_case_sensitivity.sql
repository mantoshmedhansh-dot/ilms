-- ============================================================================
-- CASE SENSITIVITY AUDIT SCRIPT
-- ============================================================================
-- This script identifies all records where enum-like string fields
-- have non-UPPERCASE values. Run this against production database to
-- find data inconsistencies.
--
-- Usage: Run in Supabase SQL Editor or via psql
-- ============================================================================

-- ============================================================================
-- ROLES TABLE - level field
-- ============================================================================
SELECT 'roles' as table_name, 'level' as field_name, id, name, level
FROM roles
WHERE level IS NOT NULL AND level != UPPER(level);

-- ============================================================================
-- ORDERS TABLE - status, payment_status, payment_method, source
-- ============================================================================
SELECT 'orders' as table_name, 'status' as field_name, id, order_number, status
FROM orders
WHERE status IS NOT NULL AND status != UPPER(status);

SELECT 'orders' as table_name, 'payment_status' as field_name, id, order_number, payment_status
FROM orders
WHERE payment_status IS NOT NULL AND payment_status != UPPER(payment_status);

SELECT 'orders' as table_name, 'payment_method' as field_name, id, order_number, payment_method
FROM orders
WHERE payment_method IS NOT NULL AND payment_method != UPPER(payment_method);

SELECT 'orders' as table_name, 'source' as field_name, id, order_number, source
FROM orders
WHERE source IS NOT NULL AND source != UPPER(source);

-- ============================================================================
-- COMPANIES TABLE - company_type, gst_registration_type
-- ============================================================================
SELECT 'companies' as table_name, 'company_type' as field_name, id, legal_name, company_type
FROM companies
WHERE company_type IS NOT NULL AND company_type != UPPER(company_type);

SELECT 'companies' as table_name, 'gst_registration_type' as field_name, id, legal_name, gst_registration_type
FROM companies
WHERE gst_registration_type IS NOT NULL AND gst_registration_type != UPPER(gst_registration_type);

-- ============================================================================
-- DEALERS TABLE - type, status, tier, credit_status
-- ============================================================================
SELECT 'dealers' as table_name, 'type' as field_name, id, name, type
FROM dealers
WHERE type IS NOT NULL AND type != UPPER(type);

SELECT 'dealers' as table_name, 'status' as field_name, id, name, status
FROM dealers
WHERE status IS NOT NULL AND status != UPPER(status);

SELECT 'dealers' as table_name, 'tier' as field_name, id, name, tier
FROM dealers
WHERE tier IS NOT NULL AND tier != UPPER(tier);

SELECT 'dealers' as table_name, 'credit_status' as field_name, id, name, credit_status
FROM dealers
WHERE credit_status IS NOT NULL AND credit_status != UPPER(credit_status);

-- ============================================================================
-- VENDORS TABLE - vendor_type, status
-- ============================================================================
SELECT 'vendors' as table_name, 'vendor_type' as field_name, id, name, vendor_type
FROM vendors
WHERE vendor_type IS NOT NULL AND vendor_type != UPPER(vendor_type);

SELECT 'vendors' as table_name, 'status' as field_name, id, name, status
FROM vendors
WHERE status IS NOT NULL AND status != UPPER(status);

-- ============================================================================
-- SHIPMENTS TABLE - status, packaging_type, payment_mode
-- ============================================================================
SELECT 'shipments' as table_name, 'status' as field_name, id, tracking_number, status
FROM shipments
WHERE status IS NOT NULL AND status != UPPER(status);

SELECT 'shipments' as table_name, 'packaging_type' as field_name, id, tracking_number, packaging_type
FROM shipments
WHERE packaging_type IS NOT NULL AND packaging_type != UPPER(packaging_type);

SELECT 'shipments' as table_name, 'payment_mode' as field_name, id, tracking_number, payment_mode
FROM shipments
WHERE payment_mode IS NOT NULL AND payment_mode != UPPER(payment_mode);

-- ============================================================================
-- PURCHASE_ORDERS TABLE - status
-- ============================================================================
SELECT 'purchase_orders' as table_name, 'status' as field_name, id, po_number, status
FROM purchase_orders
WHERE status IS NOT NULL AND status != UPPER(status);

-- ============================================================================
-- SERVICE_REQUESTS TABLE - status
-- ============================================================================
SELECT 'service_requests' as table_name, 'status' as field_name, id, ticket_number, status
FROM service_requests
WHERE status IS NOT NULL AND status != UPPER(status);

-- ============================================================================
-- INSTALLATIONS TABLE - status
-- ============================================================================
SELECT 'installations' as table_name, 'status' as field_name, id, status
FROM installations
WHERE status IS NOT NULL AND status != UPPER(status);

-- ============================================================================
-- LEADS TABLE - status
-- ============================================================================
SELECT 'leads' as table_name, 'status' as field_name, id, status
FROM leads
WHERE status IS NOT NULL AND status != UPPER(status);

-- ============================================================================
-- PICKLISTS TABLE - status, picklist_type
-- ============================================================================
SELECT 'picklists' as table_name, 'status' as field_name, id, picklist_number, status
FROM picklists
WHERE status IS NOT NULL AND status != UPPER(status);

SELECT 'picklists' as table_name, 'picklist_type' as field_name, id, picklist_number, picklist_type
FROM picklists
WHERE picklist_type IS NOT NULL AND picklist_type != UPPER(picklist_type);

-- ============================================================================
-- SUMMARY COUNTS (Run to get quick overview)
-- ============================================================================
SELECT 'SUMMARY: Records with non-UPPERCASE values' as description;

SELECT 'roles.level' as field, COUNT(*) as count
FROM roles WHERE level IS NOT NULL AND level != UPPER(level)
UNION ALL
SELECT 'orders.status', COUNT(*) FROM orders WHERE status IS NOT NULL AND status != UPPER(status)
UNION ALL
SELECT 'orders.payment_status', COUNT(*) FROM orders WHERE payment_status IS NOT NULL AND payment_status != UPPER(payment_status)
UNION ALL
SELECT 'companies.company_type', COUNT(*) FROM companies WHERE company_type IS NOT NULL AND company_type != UPPER(company_type)
UNION ALL
SELECT 'dealers.status', COUNT(*) FROM dealers WHERE status IS NOT NULL AND status != UPPER(status)
UNION ALL
SELECT 'vendors.status', COUNT(*) FROM vendors WHERE status IS NOT NULL AND status != UPPER(status)
UNION ALL
SELECT 'shipments.status', COUNT(*) FROM shipments WHERE status IS NOT NULL AND status != UPPER(status)
UNION ALL
SELECT 'purchase_orders.status', COUNT(*) FROM purchase_orders WHERE status IS NOT NULL AND status != UPPER(status)
UNION ALL
SELECT 'service_requests.status', COUNT(*) FROM service_requests WHERE status IS NOT NULL AND status != UPPER(status);
