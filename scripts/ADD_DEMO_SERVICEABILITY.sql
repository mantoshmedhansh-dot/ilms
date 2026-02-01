-- ============================================================================
-- ADD DEMO SERVICEABILITY - Pincode delivery serviceability for D2C testing
-- Run in Supabase SQL Editor
-- Created: 2026-01-19
-- ============================================================================

-- STEP 1: Verify warehouse exists
SELECT id, code, name FROM warehouses WHERE is_active = true LIMIT 1;

-- STEP 2: Add serviceability for Delhi NCR pincodes (LOCAL zone - 1-2 days)
INSERT INTO warehouse_serviceability (id, warehouse_id, pincode, is_serviceable, cod_available, prepaid_available, estimated_days, priority, shipping_cost, city, state, zone, is_active, created_at, updated_at)
SELECT gen_random_uuid(), w.id, '110001', true, true, true, 1, 10, 0, 'New Delhi', 'Delhi', 'LOCAL', true, NOW(), NOW()
FROM warehouses w WHERE w.is_active = true LIMIT 1
ON CONFLICT (warehouse_id, pincode) DO UPDATE SET estimated_days = 1, shipping_cost = 0, is_active = true, updated_at = NOW();

INSERT INTO warehouse_serviceability (id, warehouse_id, pincode, is_serviceable, cod_available, prepaid_available, estimated_days, priority, shipping_cost, city, state, zone, is_active, created_at, updated_at)
SELECT gen_random_uuid(), w.id, '110002', true, true, true, 1, 10, 0, 'New Delhi', 'Delhi', 'LOCAL', true, NOW(), NOW()
FROM warehouses w WHERE w.is_active = true LIMIT 1
ON CONFLICT (warehouse_id, pincode) DO UPDATE SET estimated_days = 1, shipping_cost = 0, is_active = true, updated_at = NOW();

INSERT INTO warehouse_serviceability (id, warehouse_id, pincode, is_serviceable, cod_available, prepaid_available, estimated_days, priority, shipping_cost, city, state, zone, is_active, created_at, updated_at)
SELECT gen_random_uuid(), w.id, '110003', true, true, true, 1, 10, 0, 'New Delhi', 'Delhi', 'LOCAL', true, NOW(), NOW()
FROM warehouses w WHERE w.is_active = true LIMIT 1
ON CONFLICT (warehouse_id, pincode) DO UPDATE SET estimated_days = 1, shipping_cost = 0, is_active = true, updated_at = NOW();

INSERT INTO warehouse_serviceability (id, warehouse_id, pincode, is_serviceable, cod_available, prepaid_available, estimated_days, priority, shipping_cost, city, state, zone, is_active, created_at, updated_at)
SELECT gen_random_uuid(), w.id, '110004', true, true, true, 1, 10, 0, 'New Delhi', 'Delhi', 'LOCAL', true, NOW(), NOW()
FROM warehouses w WHERE w.is_active = true LIMIT 1
ON CONFLICT (warehouse_id, pincode) DO UPDATE SET estimated_days = 1, shipping_cost = 0, is_active = true, updated_at = NOW();

INSERT INTO warehouse_serviceability (id, warehouse_id, pincode, is_serviceable, cod_available, prepaid_available, estimated_days, priority, shipping_cost, city, state, zone, is_active, created_at, updated_at)
SELECT gen_random_uuid(), w.id, '110005', true, true, true, 1, 10, 0, 'New Delhi', 'Delhi', 'LOCAL', true, NOW(), NOW()
FROM warehouses w WHERE w.is_active = true LIMIT 1
ON CONFLICT (warehouse_id, pincode) DO UPDATE SET estimated_days = 1, shipping_cost = 0, is_active = true, updated_at = NOW();

-- Noida pincodes
INSERT INTO warehouse_serviceability (id, warehouse_id, pincode, is_serviceable, cod_available, prepaid_available, estimated_days, priority, shipping_cost, city, state, zone, is_active, created_at, updated_at)
SELECT gen_random_uuid(), w.id, '201301', true, true, true, 1, 10, 0, 'Noida', 'Uttar Pradesh', 'LOCAL', true, NOW(), NOW()
FROM warehouses w WHERE w.is_active = true LIMIT 1
ON CONFLICT (warehouse_id, pincode) DO UPDATE SET estimated_days = 1, shipping_cost = 0, is_active = true, updated_at = NOW();

INSERT INTO warehouse_serviceability (id, warehouse_id, pincode, is_serviceable, cod_available, prepaid_available, estimated_days, priority, shipping_cost, city, state, zone, is_active, created_at, updated_at)
SELECT gen_random_uuid(), w.id, '201302', true, true, true, 1, 10, 0, 'Noida', 'Uttar Pradesh', 'LOCAL', true, NOW(), NOW()
FROM warehouses w WHERE w.is_active = true LIMIT 1
ON CONFLICT (warehouse_id, pincode) DO UPDATE SET estimated_days = 1, shipping_cost = 0, is_active = true, updated_at = NOW();

-- Gurgaon pincodes
INSERT INTO warehouse_serviceability (id, warehouse_id, pincode, is_serviceable, cod_available, prepaid_available, estimated_days, priority, shipping_cost, city, state, zone, is_active, created_at, updated_at)
SELECT gen_random_uuid(), w.id, '122001', true, true, true, 1, 10, 0, 'Gurgaon', 'Haryana', 'LOCAL', true, NOW(), NOW()
FROM warehouses w WHERE w.is_active = true LIMIT 1
ON CONFLICT (warehouse_id, pincode) DO UPDATE SET estimated_days = 1, shipping_cost = 0, is_active = true, updated_at = NOW();

INSERT INTO warehouse_serviceability (id, warehouse_id, pincode, is_serviceable, cod_available, prepaid_available, estimated_days, priority, shipping_cost, city, state, zone, is_active, created_at, updated_at)
SELECT gen_random_uuid(), w.id, '122002', true, true, true, 1, 10, 0, 'Gurgaon', 'Haryana', 'LOCAL', true, NOW(), NOW()
FROM warehouses w WHERE w.is_active = true LIMIT 1
ON CONFLICT (warehouse_id, pincode) DO UPDATE SET estimated_days = 1, shipping_cost = 0, is_active = true, updated_at = NOW();

-- STEP 3: Add serviceability for METRO cities (2-3 days delivery)

-- Mumbai pincodes
INSERT INTO warehouse_serviceability (id, warehouse_id, pincode, is_serviceable, cod_available, prepaid_available, estimated_days, priority, shipping_cost, city, state, zone, is_active, created_at, updated_at)
SELECT gen_random_uuid(), w.id, '400001', true, true, true, 2, 20, 50, 'Mumbai', 'Maharashtra', 'METRO', true, NOW(), NOW()
FROM warehouses w WHERE w.is_active = true LIMIT 1
ON CONFLICT (warehouse_id, pincode) DO UPDATE SET estimated_days = 2, shipping_cost = 50, is_active = true, updated_at = NOW();

INSERT INTO warehouse_serviceability (id, warehouse_id, pincode, is_serviceable, cod_available, prepaid_available, estimated_days, priority, shipping_cost, city, state, zone, is_active, created_at, updated_at)
SELECT gen_random_uuid(), w.id, '400002', true, true, true, 2, 20, 50, 'Mumbai', 'Maharashtra', 'METRO', true, NOW(), NOW()
FROM warehouses w WHERE w.is_active = true LIMIT 1
ON CONFLICT (warehouse_id, pincode) DO UPDATE SET estimated_days = 2, shipping_cost = 50, is_active = true, updated_at = NOW();

INSERT INTO warehouse_serviceability (id, warehouse_id, pincode, is_serviceable, cod_available, prepaid_available, estimated_days, priority, shipping_cost, city, state, zone, is_active, created_at, updated_at)
SELECT gen_random_uuid(), w.id, '400003', true, true, true, 2, 20, 50, 'Mumbai', 'Maharashtra', 'METRO', true, NOW(), NOW()
FROM warehouses w WHERE w.is_active = true LIMIT 1
ON CONFLICT (warehouse_id, pincode) DO UPDATE SET estimated_days = 2, shipping_cost = 50, is_active = true, updated_at = NOW();

-- Bangalore pincodes
INSERT INTO warehouse_serviceability (id, warehouse_id, pincode, is_serviceable, cod_available, prepaid_available, estimated_days, priority, shipping_cost, city, state, zone, is_active, created_at, updated_at)
SELECT gen_random_uuid(), w.id, '560001', true, true, true, 2, 20, 50, 'Bangalore', 'Karnataka', 'METRO', true, NOW(), NOW()
FROM warehouses w WHERE w.is_active = true LIMIT 1
ON CONFLICT (warehouse_id, pincode) DO UPDATE SET estimated_days = 2, shipping_cost = 50, is_active = true, updated_at = NOW();

INSERT INTO warehouse_serviceability (id, warehouse_id, pincode, is_serviceable, cod_available, prepaid_available, estimated_days, priority, shipping_cost, city, state, zone, is_active, created_at, updated_at)
SELECT gen_random_uuid(), w.id, '560002', true, true, true, 2, 20, 50, 'Bangalore', 'Karnataka', 'METRO', true, NOW(), NOW()
FROM warehouses w WHERE w.is_active = true LIMIT 1
ON CONFLICT (warehouse_id, pincode) DO UPDATE SET estimated_days = 2, shipping_cost = 50, is_active = true, updated_at = NOW();

-- Chennai pincodes
INSERT INTO warehouse_serviceability (id, warehouse_id, pincode, is_serviceable, cod_available, prepaid_available, estimated_days, priority, shipping_cost, city, state, zone, is_active, created_at, updated_at)
SELECT gen_random_uuid(), w.id, '600001', true, true, true, 3, 20, 50, 'Chennai', 'Tamil Nadu', 'METRO', true, NOW(), NOW()
FROM warehouses w WHERE w.is_active = true LIMIT 1
ON CONFLICT (warehouse_id, pincode) DO UPDATE SET estimated_days = 3, shipping_cost = 50, is_active = true, updated_at = NOW();

INSERT INTO warehouse_serviceability (id, warehouse_id, pincode, is_serviceable, cod_available, prepaid_available, estimated_days, priority, shipping_cost, city, state, zone, is_active, created_at, updated_at)
SELECT gen_random_uuid(), w.id, '600002', true, true, true, 3, 20, 50, 'Chennai', 'Tamil Nadu', 'METRO', true, NOW(), NOW()
FROM warehouses w WHERE w.is_active = true LIMIT 1
ON CONFLICT (warehouse_id, pincode) DO UPDATE SET estimated_days = 3, shipping_cost = 50, is_active = true, updated_at = NOW();

-- Hyderabad pincodes
INSERT INTO warehouse_serviceability (id, warehouse_id, pincode, is_serviceable, cod_available, prepaid_available, estimated_days, priority, shipping_cost, city, state, zone, is_active, created_at, updated_at)
SELECT gen_random_uuid(), w.id, '500001', true, true, true, 3, 20, 50, 'Hyderabad', 'Telangana', 'METRO', true, NOW(), NOW()
FROM warehouses w WHERE w.is_active = true LIMIT 1
ON CONFLICT (warehouse_id, pincode) DO UPDATE SET estimated_days = 3, shipping_cost = 50, is_active = true, updated_at = NOW();

INSERT INTO warehouse_serviceability (id, warehouse_id, pincode, is_serviceable, cod_available, prepaid_available, estimated_days, priority, shipping_cost, city, state, zone, is_active, created_at, updated_at)
SELECT gen_random_uuid(), w.id, '500002', true, true, true, 3, 20, 50, 'Hyderabad', 'Telangana', 'METRO', true, NOW(), NOW()
FROM warehouses w WHERE w.is_active = true LIMIT 1
ON CONFLICT (warehouse_id, pincode) DO UPDATE SET estimated_days = 3, shipping_cost = 50, is_active = true, updated_at = NOW();

-- Kolkata pincodes
INSERT INTO warehouse_serviceability (id, warehouse_id, pincode, is_serviceable, cod_available, prepaid_available, estimated_days, priority, shipping_cost, city, state, zone, is_active, created_at, updated_at)
SELECT gen_random_uuid(), w.id, '700001', true, true, true, 3, 20, 50, 'Kolkata', 'West Bengal', 'METRO', true, NOW(), NOW()
FROM warehouses w WHERE w.is_active = true LIMIT 1
ON CONFLICT (warehouse_id, pincode) DO UPDATE SET estimated_days = 3, shipping_cost = 50, is_active = true, updated_at = NOW();

-- STEP 4: Add REGIONAL cities (3-5 days delivery)

-- Jaipur
INSERT INTO warehouse_serviceability (id, warehouse_id, pincode, is_serviceable, cod_available, prepaid_available, estimated_days, priority, shipping_cost, city, state, zone, is_active, created_at, updated_at)
SELECT gen_random_uuid(), w.id, '302001', true, true, true, 3, 30, 75, 'Jaipur', 'Rajasthan', 'REGIONAL', true, NOW(), NOW()
FROM warehouses w WHERE w.is_active = true LIMIT 1
ON CONFLICT (warehouse_id, pincode) DO UPDATE SET estimated_days = 3, shipping_cost = 75, is_active = true, updated_at = NOW();

-- Lucknow
INSERT INTO warehouse_serviceability (id, warehouse_id, pincode, is_serviceable, cod_available, prepaid_available, estimated_days, priority, shipping_cost, city, state, zone, is_active, created_at, updated_at)
SELECT gen_random_uuid(), w.id, '226001', true, true, true, 3, 30, 75, 'Lucknow', 'Uttar Pradesh', 'REGIONAL', true, NOW(), NOW()
FROM warehouses w WHERE w.is_active = true LIMIT 1
ON CONFLICT (warehouse_id, pincode) DO UPDATE SET estimated_days = 3, shipping_cost = 75, is_active = true, updated_at = NOW();

-- Ahmedabad
INSERT INTO warehouse_serviceability (id, warehouse_id, pincode, is_serviceable, cod_available, prepaid_available, estimated_days, priority, shipping_cost, city, state, zone, is_active, created_at, updated_at)
SELECT gen_random_uuid(), w.id, '380001', true, true, true, 3, 30, 75, 'Ahmedabad', 'Gujarat', 'REGIONAL', true, NOW(), NOW()
FROM warehouses w WHERE w.is_active = true LIMIT 1
ON CONFLICT (warehouse_id, pincode) DO UPDATE SET estimated_days = 3, shipping_cost = 75, is_active = true, updated_at = NOW();

-- Pune
INSERT INTO warehouse_serviceability (id, warehouse_id, pincode, is_serviceable, cod_available, prepaid_available, estimated_days, priority, shipping_cost, city, state, zone, is_active, created_at, updated_at)
SELECT gen_random_uuid(), w.id, '411001', true, true, true, 3, 30, 50, 'Pune', 'Maharashtra', 'REGIONAL', true, NOW(), NOW()
FROM warehouses w WHERE w.is_active = true LIMIT 1
ON CONFLICT (warehouse_id, pincode) DO UPDATE SET estimated_days = 3, shipping_cost = 50, is_active = true, updated_at = NOW();

-- Chandigarh
INSERT INTO warehouse_serviceability (id, warehouse_id, pincode, is_serviceable, cod_available, prepaid_available, estimated_days, priority, shipping_cost, city, state, zone, is_active, created_at, updated_at)
SELECT gen_random_uuid(), w.id, '160001', true, true, true, 2, 30, 50, 'Chandigarh', 'Chandigarh', 'REGIONAL', true, NOW(), NOW()
FROM warehouses w WHERE w.is_active = true LIMIT 1
ON CONFLICT (warehouse_id, pincode) DO UPDATE SET estimated_days = 2, shipping_cost = 50, is_active = true, updated_at = NOW();

-- STEP 5: Add NATIONAL reach (5-7 days delivery) - sample remote pincodes

-- Patna
INSERT INTO warehouse_serviceability (id, warehouse_id, pincode, is_serviceable, cod_available, prepaid_available, estimated_days, priority, shipping_cost, city, state, zone, is_active, created_at, updated_at)
SELECT gen_random_uuid(), w.id, '800001', true, true, true, 5, 40, 100, 'Patna', 'Bihar', 'NATIONAL', true, NOW(), NOW()
FROM warehouses w WHERE w.is_active = true LIMIT 1
ON CONFLICT (warehouse_id, pincode) DO UPDATE SET estimated_days = 5, shipping_cost = 100, is_active = true, updated_at = NOW();

-- Bhubaneswar
INSERT INTO warehouse_serviceability (id, warehouse_id, pincode, is_serviceable, cod_available, prepaid_available, estimated_days, priority, shipping_cost, city, state, zone, is_active, created_at, updated_at)
SELECT gen_random_uuid(), w.id, '751001', true, true, true, 5, 40, 100, 'Bhubaneswar', 'Odisha', 'NATIONAL', true, NOW(), NOW()
FROM warehouses w WHERE w.is_active = true LIMIT 1
ON CONFLICT (warehouse_id, pincode) DO UPDATE SET estimated_days = 5, shipping_cost = 100, is_active = true, updated_at = NOW();

-- Indore
INSERT INTO warehouse_serviceability (id, warehouse_id, pincode, is_serviceable, cod_available, prepaid_available, estimated_days, priority, shipping_cost, city, state, zone, is_active, created_at, updated_at)
SELECT gen_random_uuid(), w.id, '452001', true, true, true, 4, 40, 75, 'Indore', 'Madhya Pradesh', 'NATIONAL', true, NOW(), NOW()
FROM warehouses w WHERE w.is_active = true LIMIT 1
ON CONFLICT (warehouse_id, pincode) DO UPDATE SET estimated_days = 4, shipping_cost = 75, is_active = true, updated_at = NOW();

-- Kochi
INSERT INTO warehouse_serviceability (id, warehouse_id, pincode, is_serviceable, cod_available, prepaid_available, estimated_days, priority, shipping_cost, city, state, zone, is_active, created_at, updated_at)
SELECT gen_random_uuid(), w.id, '682001', true, true, true, 5, 40, 100, 'Kochi', 'Kerala', 'NATIONAL', true, NOW(), NOW()
FROM warehouses w WHERE w.is_active = true LIMIT 1
ON CONFLICT (warehouse_id, pincode) DO UPDATE SET estimated_days = 5, shipping_cost = 100, is_active = true, updated_at = NOW();

-- Guwahati
INSERT INTO warehouse_serviceability (id, warehouse_id, pincode, is_serviceable, cod_available, prepaid_available, estimated_days, priority, shipping_cost, city, state, zone, is_active, created_at, updated_at)
SELECT gen_random_uuid(), w.id, '781001', true, false, true, 7, 50, 150, 'Guwahati', 'Assam', 'NATIONAL', true, NOW(), NOW()
FROM warehouses w WHERE w.is_active = true LIMIT 1
ON CONFLICT (warehouse_id, pincode) DO UPDATE SET estimated_days = 7, shipping_cost = 150, cod_available = false, is_active = true, updated_at = NOW();

-- STEP 6: Verify
SELECT 'Demo serviceability added' as status;
SELECT pincode, city, state, zone, estimated_days, shipping_cost, cod_available, prepaid_available
FROM warehouse_serviceability
WHERE is_active = true
ORDER BY zone, estimated_days, pincode;
