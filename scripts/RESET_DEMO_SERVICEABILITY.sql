-- ============================================================================
-- RESET DEMO SERVICEABILITY - Remove demo pincode data
-- Run in Supabase SQL Editor
-- ============================================================================

-- Remove all demo serviceability records
DELETE FROM warehouse_serviceability
WHERE pincode IN (
    -- Delhi NCR
    '110001', '110002', '110003', '110004', '110005',
    '201301', '201302',  -- Noida
    '122001', '122002',  -- Gurgaon
    -- Metro cities
    '400001', '400002', '400003',  -- Mumbai
    '560001', '560002',  -- Bangalore
    '600001', '600002',  -- Chennai
    '500001', '500002',  -- Hyderabad
    '700001',  -- Kolkata
    -- Regional cities
    '302001',  -- Jaipur
    '226001',  -- Lucknow
    '380001',  -- Ahmedabad
    '411001',  -- Pune
    '160001',  -- Chandigarh
    -- National reach
    '800001',  -- Patna
    '751001',  -- Bhubaneswar
    '452001',  -- Indore
    '682001',  -- Kochi
    '781001'   -- Guwahati
);

-- Verify
SELECT 'Demo serviceability reset complete' as status;
SELECT COUNT(*) as remaining_records FROM warehouse_serviceability WHERE is_active = true;
