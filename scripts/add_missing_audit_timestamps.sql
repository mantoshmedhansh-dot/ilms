-- ============================================================================
-- Add Missing Audit Timestamps to Tables
-- Run this script on Supabase production database
-- ============================================================================

-- amc_contracts - missing created_at, updated_at
ALTER TABLE amc_contracts
ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ DEFAULT NOW(),
ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ DEFAULT NOW();

-- amc_plans - missing created_at, updated_at
ALTER TABLE amc_plans
ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ DEFAULT NOW(),
ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ DEFAULT NOW();

-- affiliate_referrals - missing updated_at
ALTER TABLE affiliate_referrals
ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ DEFAULT NOW();

-- customer_referrals - missing created_at, updated_at
ALTER TABLE customer_referrals
ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ DEFAULT NOW(),
ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ DEFAULT NOW();

-- leave_balances - missing created_at, updated_at (mentioned in CLAUDE.md)
ALTER TABLE leave_balances
ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ DEFAULT NOW(),
ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ DEFAULT NOW();

-- Add trigger function for auto-updating updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create triggers for tables with updated_at
DO $$
DECLARE
    tbl_name TEXT;
    tbl_names TEXT[] := ARRAY['amc_contracts', 'amc_plans', 'affiliate_referrals', 'customer_referrals', 'leave_balances'];
BEGIN
    FOREACH tbl_name IN ARRAY tbl_names
    LOOP
        EXECUTE format('
            DROP TRIGGER IF EXISTS update_%s_updated_at ON %s;
            CREATE TRIGGER update_%s_updated_at
                BEFORE UPDATE ON %s
                FOR EACH ROW
                EXECUTE FUNCTION update_updated_at_column();
        ', tbl_name, tbl_name, tbl_name, tbl_name);
    END LOOP;
END $$;

-- Verify the changes
SELECT
    table_name,
    column_name,
    data_type
FROM information_schema.columns
WHERE table_name IN ('amc_contracts', 'amc_plans', 'affiliate_referrals', 'customer_referrals', 'leave_balances')
AND column_name IN ('created_at', 'updated_at')
ORDER BY table_name, column_name;
