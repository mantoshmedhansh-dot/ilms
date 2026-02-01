-- ============================================================================
-- Production Schema Fix Script
-- This script adds missing columns and fixes type mismatches
-- Production (Supabase) is SOURCE OF TRUTH - but must match CLAUDE.md standards
-- Standards: TIMESTAMPTZ, JSONB, VARCHAR for status, UUID for IDs (mostly)
-- ============================================================================

-- ============================================================================
-- PART 1: Add missing columns to ORDERS table (critical for order flow)
-- ============================================================================

ALTER TABLE orders
  ADD COLUMN IF NOT EXISTS awb_code VARCHAR(100),
  ADD COLUMN IF NOT EXISTS courier_id UUID,
  ADD COLUMN IF NOT EXISTS courier_name VARCHAR(255),
  ADD COLUMN IF NOT EXISTS estimated_delivery TIMESTAMPTZ,
  ADD COLUMN IF NOT EXISTS last_tracking_activity VARCHAR(500),
  ADD COLUMN IF NOT EXISTS last_tracking_location VARCHAR(255),
  ADD COLUMN IF NOT EXISTS last_tracking_update TIMESTAMPTZ,
  ADD COLUMN IF NOT EXISTS paid_at TIMESTAMPTZ,
  ADD COLUMN IF NOT EXISTS razorpay_order_id VARCHAR(100),
  ADD COLUMN IF NOT EXISTS razorpay_payment_id VARCHAR(100),
  ADD COLUMN IF NOT EXISTS shiprocket_order_id VARCHAR(100),
  ADD COLUMN IF NOT EXISTS shiprocket_shipment_id VARCHAR(100),
  ADD COLUMN IF NOT EXISTS tracking_status VARCHAR(100),
  ADD COLUMN IF NOT EXISTS tracking_status_id INTEGER,
  ADD COLUMN IF NOT EXISTS weight_kg NUMERIC(10,3);

-- ============================================================================
-- PART 2: Add missing columns to SHIPMENTS table
-- ============================================================================

ALTER TABLE shipments
  ADD COLUMN IF NOT EXISTS payment_mode VARCHAR(50);

-- ============================================================================
-- PART 3: Add missing columns to SHIPMENT_TRACKING table
-- ============================================================================

ALTER TABLE shipment_tracking
  ADD COLUMN IF NOT EXISTS status VARCHAR(50);

-- ============================================================================
-- PART 4: Add missing columns to EMPLOYEES table
-- ============================================================================

ALTER TABLE employees
  ADD COLUMN IF NOT EXISTS first_name VARCHAR(100),
  ADD COLUMN IF NOT EXISTS last_name VARCHAR(100);

-- ============================================================================
-- PART 5: Add missing columns to PERMISSIONS table
-- ============================================================================

ALTER TABLE permissions
  ADD COLUMN IF NOT EXISTS resource VARCHAR(100);

-- ============================================================================
-- PART 6: Add missing columns to USER_ROLES table
-- ============================================================================

ALTER TABLE user_roles
  ADD COLUMN IF NOT EXISTS is_primary BOOLEAN DEFAULT false;

-- ============================================================================
-- PART 7: Add missing columns to USERS table (full_name computed from first+last)
-- ============================================================================

ALTER TABLE users
  ADD COLUMN IF NOT EXISTS full_name VARCHAR(255);

-- ============================================================================
-- PART 8: Add missing columns to PRODUCTS table
-- ============================================================================

ALTER TABLE products
  ADD COLUMN IF NOT EXISTS weight_kg NUMERIC(10,3);

-- ============================================================================
-- PART 9: Add missing columns to LEAVE_BALANCES table
-- ============================================================================

ALTER TABLE leave_balances
  ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ DEFAULT NOW(),
  ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ DEFAULT NOW(),
  ADD COLUMN IF NOT EXISTS leave_type VARCHAR(50);

-- ============================================================================
-- PART 10: Add missing columns to TAX_INVOICES table
-- ============================================================================

ALTER TABLE tax_invoices
  ADD COLUMN IF NOT EXISTS shipment_id UUID,
  ADD COLUMN IF NOT EXISTS generation_trigger VARCHAR(50);

-- ============================================================================
-- PART 11: Add missing columns to other tables for order flow
-- ============================================================================

-- allocation_rules
ALTER TABLE allocation_rules
  ADD COLUMN IF NOT EXISTS channel_code VARCHAR(50);

-- campaign_automations
ALTER TABLE campaign_automations
  ADD COLUMN IF NOT EXISTS campaign_type VARCHAR(50);

-- campaign_templates
ALTER TABLE campaign_templates
  ADD COLUMN IF NOT EXISTS campaign_type VARCHAR(50);

-- cms_pages
ALTER TABLE cms_pages
  ADD COLUMN IF NOT EXISTS featured_image_url VARCHAR(500);

-- dealer_tier_pricing
ALTER TABLE dealer_tier_pricing
  ADD COLUMN IF NOT EXISTS tier VARCHAR(50);

-- escalation_history
ALTER TABLE escalation_history
  ADD COLUMN IF NOT EXISTS from_level INTEGER,
  ADD COLUMN IF NOT EXISTS to_level INTEGER,
  ADD COLUMN IF NOT EXISTS from_status VARCHAR(50),
  ADD COLUMN IF NOT EXISTS to_status VARCHAR(50);

-- escalation_matrix
ALTER TABLE escalation_matrix
  ADD COLUMN IF NOT EXISTS level INTEGER;

-- escalations
ALTER TABLE escalations
  ADD COLUMN IF NOT EXISTS current_level INTEGER;

-- lead_activities
ALTER TABLE lead_activities
  ADD COLUMN IF NOT EXISTS old_status VARCHAR(50),
  ADD COLUMN IF NOT EXISTS new_status VARCHAR(50);

-- lead_assignment_rules
ALTER TABLE lead_assignment_rules
  ADD COLUMN IF NOT EXISTS source VARCHAR(100);

-- notification_templates
ALTER TABLE notification_templates
  ADD COLUMN IF NOT EXISTS notification_type VARCHAR(50);

-- product_documents
ALTER TABLE product_documents
  ADD COLUMN IF NOT EXISTS document_type VARCHAR(50);

-- unsubscribe_list
ALTER TABLE unsubscribe_list
  ADD COLUMN IF NOT EXISTS channel VARCHAR(50);

-- ============================================================================
-- VERIFICATION QUERIES
-- ============================================================================

SELECT 'orders columns' as table_name, COUNT(*) as column_count FROM information_schema.columns WHERE table_name = 'orders';
SELECT 'shipments columns' as table_name, COUNT(*) as column_count FROM information_schema.columns WHERE table_name = 'shipments';
SELECT 'employees columns' as table_name, COUNT(*) as column_count FROM information_schema.columns WHERE table_name = 'employees';
SELECT 'users columns' as table_name, COUNT(*) as column_count FROM information_schema.columns WHERE table_name = 'users';

-- Check if critical columns exist
SELECT
  'orders.razorpay_order_id' as column_check,
  EXISTS(SELECT 1 FROM information_schema.columns WHERE table_name = 'orders' AND column_name = 'razorpay_order_id') as exists;

SELECT
  'shipments.payment_mode' as column_check,
  EXISTS(SELECT 1 FROM information_schema.columns WHERE table_name = 'shipments' AND column_name = 'payment_mode') as exists;

SELECT
  'users.full_name' as column_check,
  EXISTS(SELECT 1 FROM information_schema.columns WHERE table_name = 'users' AND column_name = 'full_name') as exists;
