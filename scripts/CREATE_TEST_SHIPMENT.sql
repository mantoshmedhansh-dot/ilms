-- ============================================================================
-- CREATE TEST SHIPMENT FOR LABEL & INVOICE DEMO
-- Run in Supabase SQL Editor
-- ============================================================================

-- Get the order ID we just created
SELECT id, order_number, status, total_amount, shipping_address
FROM orders
WHERE order_number = 'ORD-20260119-0003';

-- Get warehouse ID
SELECT id, code, name FROM warehouses WHERE code = 'WH-DEL-001';

-- ============================================================================
-- CREATE SHIPMENT
-- ============================================================================
INSERT INTO shipments (
    id,
    shipment_number,
    order_id,
    warehouse_id,
    status,
    payment_mode,

    -- Ship To Address (from order)
    ship_to_name,
    ship_to_phone,
    ship_to_address,
    ship_to_city,
    ship_to_state,
    ship_to_pincode,
    ship_to_country,

    -- Package Details
    packaging_type,
    no_of_boxes,
    weight_kg,
    length_cm,
    breadth_cm,
    height_cm,
    volumetric_weight,
    chargeable_weight,

    -- COD Details
    cod_amount,

    -- AWB (generated)
    awb_number,

    -- Timestamps
    created_at,
    updated_at
)
SELECT
    gen_random_uuid(),
    'SHP-20260119-00001',
    o.id,
    w.id,
    'PACKED',
    'COD',

    -- Ship To Address
    o.shipping_address->>'contact_name',
    o.shipping_address->>'contact_phone',
    jsonb_build_object(
        'address_line1', o.shipping_address->>'address_line1',
        'address_line2', o.shipping_address->>'address_line2',
        'landmark', o.shipping_address->>'landmark'
    ),
    o.shipping_address->>'city',
    o.shipping_address->>'state',
    o.shipping_address->>'pincode',
    o.shipping_address->>'country',

    -- Package Details
    'BOX',
    1,
    8.5,  -- Weight in KG (water purifier)
    50,   -- Length CM
    40,   -- Breadth CM
    45,   -- Height CM
    18.0, -- Volumetric weight
    18.0, -- Chargeable weight (max of actual and volumetric)

    -- COD Amount
    o.total_amount,

    -- AWB Number
    'AQ' || TO_CHAR(NOW(), 'YYYYMMDD') || LPAD(FLOOR(RANDOM() * 999999)::TEXT, 6, '0'),

    -- Timestamps
    NOW(),
    NOW()
FROM orders o
CROSS JOIN warehouses w
WHERE o.order_number = 'ORD-20260119-0003'
AND w.code = 'WH-DEL-001';

-- Update order status to PACKED
UPDATE orders
SET status = 'PACKED',
    packed_at = NOW(),
    warehouse_id = (SELECT id FROM warehouses WHERE code = 'WH-DEL-001')
WHERE order_number = 'ORD-20260119-0003';

-- ============================================================================
-- VERIFY SHIPMENT CREATED
-- ============================================================================
SELECT
    s.id as shipment_id,
    s.shipment_number,
    s.awb_number,
    s.status,
    s.payment_mode,
    s.cod_amount,
    s.weight_kg,
    s.ship_to_name,
    s.ship_to_city,
    s.ship_to_pincode,
    o.order_number
FROM shipments s
JOIN orders o ON s.order_id = o.id
WHERE o.order_number = 'ORD-20260119-0003';

-- ============================================================================
-- COPY THE SHIPMENT ID FROM ABOVE AND USE IT TO VIEW:
-- Label: https://aquapurite-erp-api.onrender.com/api/v1/shipments/{SHIPMENT_ID}/label/download
-- Invoice: https://aquapurite-erp-api.onrender.com/api/v1/shipments/{SHIPMENT_ID}/invoice/download
-- ============================================================================
