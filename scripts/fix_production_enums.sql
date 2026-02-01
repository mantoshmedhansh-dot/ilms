-- =====================================================
-- PRODUCTION FIX: Convert ENUM columns to VARCHAR
-- Run this in Supabase SQL Editor
-- =====================================================

-- 1. First, check what ENUM types exist
SELECT t.typname as enum_name
FROM pg_type t
JOIN pg_catalog.pg_namespace n ON n.oid = t.typnamespace
WHERE n.nspname = 'public' AND t.typtype = 'e'
ORDER BY t.typname;

-- 2. Convert purchase_orders.status from ENUM to VARCHAR
ALTER TABLE purchase_orders
ALTER COLUMN status TYPE VARCHAR(50)
USING status::text;

-- 3. Convert other purchase-related ENUM columns
ALTER TABLE purchase_orders
ALTER COLUMN po_type TYPE VARCHAR(50)
USING po_type::text;

ALTER TABLE purchase_order_items
ALTER COLUMN item_status TYPE VARCHAR(50)
USING item_status::text;

ALTER TABLE goods_receipt_notes
ALTER COLUMN status TYPE VARCHAR(50)
USING status::text;

ALTER TABLE purchase_requisitions
ALTER COLUMN status TYPE VARCHAR(50)
USING status::text;

-- 4. Convert vendor-related ENUM columns
ALTER TABLE vendors
ALTER COLUMN vendor_type TYPE VARCHAR(50)
USING vendor_type::text;

ALTER TABLE vendors
ALTER COLUMN status TYPE VARCHAR(50)
USING status::text;

ALTER TABLE vendors
ALTER COLUMN grade TYPE VARCHAR(10)
USING grade::text;

ALTER TABLE vendors
ALTER COLUMN payment_terms TYPE VARCHAR(50)
USING payment_terms::text;

-- 5. Convert other critical ENUM columns
ALTER TABLE orders
ALTER COLUMN status TYPE VARCHAR(50)
USING status::text;

ALTER TABLE orders
ALTER COLUMN source TYPE VARCHAR(50)
USING source::text;

ALTER TABLE orders
ALTER COLUMN payment_method TYPE VARCHAR(50)
USING payment_method::text;

ALTER TABLE orders
ALTER COLUMN payment_status TYPE VARCHAR(50)
USING payment_status::text;

-- 6. Convert delivery schedule status
ALTER TABLE po_delivery_schedules
ALTER COLUMN status TYPE VARCHAR(50)
USING status::text;

-- 7. Drop old ENUM types (after all conversions)
DROP TYPE IF EXISTS postatus CASCADE;
DROP TYPE IF EXISTS potype CASCADE;
DROP TYPE IF EXISTS poitemstatus CASCADE;
DROP TYPE IF EXISTS grnstatus CASCADE;
DROP TYPE IF EXISTS requisitionstatus CASCADE;
DROP TYPE IF EXISTS vendortype CASCADE;
DROP TYPE IF EXISTS vendorstatus CASCADE;
DROP TYPE IF EXISTS vendorgrade CASCADE;
DROP TYPE IF EXISTS paymentterms CASCADE;
DROP TYPE IF EXISTS orderstatus CASCADE;
DROP TYPE IF EXISTS ordersource CASCADE;
DROP TYPE IF EXISTS paymentmethod CASCADE;
DROP TYPE IF EXISTS paymentstatus CASCADE;
DROP TYPE IF EXISTS deliverylotstatus CASCADE;

-- 8. Verify the changes
SELECT table_name, column_name, data_type, udt_name
FROM information_schema.columns
WHERE table_name IN ('purchase_orders', 'purchase_order_items', 'goods_receipt_notes', 'orders', 'vendors', 'po_delivery_schedules')
  AND column_name IN ('status', 'po_type', 'item_status', 'vendor_type', 'grade', 'payment_terms', 'source', 'payment_method', 'payment_status')
ORDER BY table_name, column_name;
