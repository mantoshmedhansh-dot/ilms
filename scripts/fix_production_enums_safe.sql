-- =====================================================
-- PRODUCTION FIX: Convert ENUM columns to VARCHAR
-- Run this STEP BY STEP in Supabase SQL Editor
-- https://supabase.com/dashboard/project/lgkoenbijrcmhewthwks/sql
-- =====================================================

-- STEP 1: Check current ENUM types
-- Copy and run this first to see what ENUMs exist
SELECT t.typname as enum_name
FROM pg_type t
JOIN pg_catalog.pg_namespace n ON n.oid = t.typnamespace
WHERE n.nspname = 'public' AND t.typtype = 'e'
ORDER BY t.typname;

-- =====================================================
-- STEP 2: Convert purchase_orders.status (THE CRITICAL ONE)
-- This is causing the PO approval error
-- =====================================================
DO $$
BEGIN
    -- Check if column is ENUM type
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'purchase_orders'
        AND column_name = 'status'
        AND udt_name = 'postatus'
    ) THEN
        ALTER TABLE purchase_orders
        ALTER COLUMN status TYPE VARCHAR(50)
        USING status::text;
        RAISE NOTICE 'Converted purchase_orders.status to VARCHAR';
    ELSE
        RAISE NOTICE 'purchase_orders.status is already VARCHAR or does not exist';
    END IF;
END $$;

-- =====================================================
-- STEP 3: Convert po_delivery_schedules.status
-- =====================================================
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'po_delivery_schedules'
        AND column_name = 'status'
        AND udt_name NOT LIKE '%character%'
        AND udt_name NOT LIKE 'varchar%'
    ) THEN
        ALTER TABLE po_delivery_schedules
        ALTER COLUMN status TYPE VARCHAR(50)
        USING status::text;
        RAISE NOTICE 'Converted po_delivery_schedules.status to VARCHAR';
    ELSE
        RAISE NOTICE 'po_delivery_schedules.status is already VARCHAR or does not exist';
    END IF;
END $$;

-- =====================================================
-- STEP 4: Convert other purchase-related columns
-- =====================================================
DO $$
BEGIN
    -- purchase_orders.po_type
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'purchase_orders'
        AND column_name = 'po_type'
        AND data_type = 'USER-DEFINED'
    ) THEN
        ALTER TABLE purchase_orders ALTER COLUMN po_type TYPE VARCHAR(50) USING po_type::text;
        RAISE NOTICE 'Converted purchase_orders.po_type';
    END IF;

    -- purchase_order_items.item_status
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'purchase_order_items'
        AND column_name = 'item_status'
        AND data_type = 'USER-DEFINED'
    ) THEN
        ALTER TABLE purchase_order_items ALTER COLUMN item_status TYPE VARCHAR(50) USING item_status::text;
        RAISE NOTICE 'Converted purchase_order_items.item_status';
    END IF;

    -- goods_receipt_notes.status
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'goods_receipt_notes'
        AND column_name = 'status'
        AND data_type = 'USER-DEFINED'
    ) THEN
        ALTER TABLE goods_receipt_notes ALTER COLUMN status TYPE VARCHAR(50) USING status::text;
        RAISE NOTICE 'Converted goods_receipt_notes.status';
    END IF;

    -- purchase_requisitions.status
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'purchase_requisitions'
        AND column_name = 'status'
        AND data_type = 'USER-DEFINED'
    ) THEN
        ALTER TABLE purchase_requisitions ALTER COLUMN status TYPE VARCHAR(50) USING status::text;
        RAISE NOTICE 'Converted purchase_requisitions.status';
    END IF;
END $$;

-- =====================================================
-- STEP 5: Convert vendor-related columns
-- =====================================================
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'vendors' AND column_name = 'vendor_type' AND data_type = 'USER-DEFINED') THEN
        ALTER TABLE vendors ALTER COLUMN vendor_type TYPE VARCHAR(50) USING vendor_type::text;
        RAISE NOTICE 'Converted vendors.vendor_type';
    END IF;

    IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'vendors' AND column_name = 'status' AND data_type = 'USER-DEFINED') THEN
        ALTER TABLE vendors ALTER COLUMN status TYPE VARCHAR(50) USING status::text;
        RAISE NOTICE 'Converted vendors.status';
    END IF;

    IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'vendors' AND column_name = 'grade' AND data_type = 'USER-DEFINED') THEN
        ALTER TABLE vendors ALTER COLUMN grade TYPE VARCHAR(10) USING grade::text;
        RAISE NOTICE 'Converted vendors.grade';
    END IF;

    IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'vendors' AND column_name = 'payment_terms' AND data_type = 'USER-DEFINED') THEN
        ALTER TABLE vendors ALTER COLUMN payment_terms TYPE VARCHAR(50) USING payment_terms::text;
        RAISE NOTICE 'Converted vendors.payment_terms';
    END IF;

    IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'vendor_ledger' AND column_name = 'transaction_type' AND data_type = 'USER-DEFINED') THEN
        ALTER TABLE vendor_ledger ALTER COLUMN transaction_type TYPE VARCHAR(50) USING transaction_type::text;
        RAISE NOTICE 'Converted vendor_ledger.transaction_type';
    END IF;
END $$;

-- =====================================================
-- STEP 6: Drop old ENUM types (OPTIONAL - run after verification)
-- =====================================================
-- Only run these after confirming the columns are converted:
-- DROP TYPE IF EXISTS postatus CASCADE;
-- DROP TYPE IF EXISTS potype CASCADE;
-- DROP TYPE IF EXISTS poitemstatus CASCADE;
-- DROP TYPE IF EXISTS grnstatus CASCADE;
-- DROP TYPE IF EXISTS requisitionstatus CASCADE;
-- DROP TYPE IF EXISTS deliverylotstatus CASCADE;
-- DROP TYPE IF EXISTS vendortype CASCADE;
-- DROP TYPE IF EXISTS vendorstatus CASCADE;
-- DROP TYPE IF EXISTS vendorgrade CASCADE;

-- =====================================================
-- STEP 7: Verify the changes
-- =====================================================
SELECT table_name, column_name, data_type, udt_name
FROM information_schema.columns
WHERE table_name IN ('purchase_orders', 'purchase_order_items', 'goods_receipt_notes',
                     'purchase_requisitions', 'po_delivery_schedules', 'vendors', 'vendor_ledger')
  AND column_name IN ('status', 'po_type', 'item_status', 'vendor_type', 'grade', 'payment_terms', 'transaction_type')
ORDER BY table_name, column_name;
