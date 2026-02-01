#!/usr/bin/env python3
"""
Script to fix community_partners schema in production database.
Run this script to add missing columns and tables.
"""
import asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

# Production database URL
DATABASE_URL = "postgresql+psycopg://postgres:Aquapurite2026@db.aavjhutqzwusgdwrczds.supabase.co:6543/postgres"

# SQL statements to fix the schema
SQL_STATEMENTS = [
    # 1. Create partner_tiers table if not exists
    """
    CREATE TABLE IF NOT EXISTS partner_tiers (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        code VARCHAR(20) UNIQUE NOT NULL,
        name VARCHAR(50) NOT NULL,
        description TEXT,
        badge_color VARCHAR(20),
        badge_icon_url VARCHAR(500),
        level INTEGER DEFAULT 1,
        min_monthly_sales INTEGER DEFAULT 0,
        max_monthly_sales INTEGER,
        min_monthly_value NUMERIC(12, 2) DEFAULT 0.00,
        commission_percentage NUMERIC(5, 2) NOT NULL,
        bonus_percentage NUMERIC(5, 2) DEFAULT 0.00,
        milestone_bonus NUMERIC(10, 2) DEFAULT 0.00,
        referral_bonus NUMERIC(10, 2) DEFAULT 0.00,
        benefits JSONB,
        is_active BOOLEAN DEFAULT TRUE,
        is_default BOOLEAN DEFAULT FALSE,
        created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
        updated_at TIMESTAMPTZ DEFAULT NOW() NOT NULL
    )
    """,

    # 2. Add missing columns to community_partners
    "ALTER TABLE community_partners ADD COLUMN IF NOT EXISTS pan_document_url VARCHAR(500)",
    "ALTER TABLE community_partners ADD COLUMN IF NOT EXISTS aadhaar_front_url VARCHAR(500)",
    "ALTER TABLE community_partners ADD COLUMN IF NOT EXISTS aadhaar_back_url VARCHAR(500)",
    "ALTER TABLE community_partners ADD COLUMN IF NOT EXISTS bank_branch VARCHAR(200)",
    "ALTER TABLE community_partners ADD COLUMN IF NOT EXISTS bank_account_holder_name VARCHAR(200)",
    "ALTER TABLE community_partners ADD COLUMN IF NOT EXISTS upi_id VARCHAR(100)",
    "ALTER TABLE community_partners ADD COLUMN IF NOT EXISTS upi_verified BOOLEAN DEFAULT FALSE",
    "ALTER TABLE community_partners ADD COLUMN IF NOT EXISTS total_sales_count INTEGER DEFAULT 0",
    "ALTER TABLE community_partners ADD COLUMN IF NOT EXISTS total_sales_value NUMERIC(15, 2) DEFAULT 0.00",
    "ALTER TABLE community_partners ADD COLUMN IF NOT EXISTS total_commission_earned NUMERIC(12, 2) DEFAULT 0.00",
    "ALTER TABLE community_partners ADD COLUMN IF NOT EXISTS total_commission_paid NUMERIC(12, 2) DEFAULT 0.00",
    "ALTER TABLE community_partners ADD COLUMN IF NOT EXISTS current_month_sales INTEGER DEFAULT 0",
    "ALTER TABLE community_partners ADD COLUMN IF NOT EXISTS current_month_value NUMERIC(12, 2) DEFAULT 0.00",
    "ALTER TABLE community_partners ADD COLUMN IF NOT EXISTS wallet_balance NUMERIC(12, 2) DEFAULT 0.00",
    "ALTER TABLE community_partners ADD COLUMN IF NOT EXISTS training_completed BOOLEAN DEFAULT FALSE",
    "ALTER TABLE community_partners ADD COLUMN IF NOT EXISTS training_completed_at TIMESTAMPTZ",
    "ALTER TABLE community_partners ADD COLUMN IF NOT EXISTS certification_level VARCHAR(50)",
    "ALTER TABLE community_partners ADD COLUMN IF NOT EXISTS app_version VARCHAR(20)",
    "ALTER TABLE community_partners ADD COLUMN IF NOT EXISTS device_type VARCHAR(20)",
    "ALTER TABLE community_partners ADD COLUMN IF NOT EXISTS fcm_token VARCHAR(500)",
    "ALTER TABLE community_partners ADD COLUMN IF NOT EXISTS last_login_at TIMESTAMPTZ",
    "ALTER TABLE community_partners ADD COLUMN IF NOT EXISTS kyc_verified_by UUID",
    "ALTER TABLE community_partners ADD COLUMN IF NOT EXISTS kyc_verified_at TIMESTAMPTZ",
    "ALTER TABLE community_partners ADD COLUMN IF NOT EXISTS kyc_rejection_reason TEXT",
    "ALTER TABLE community_partners ADD COLUMN IF NOT EXISTS extra_data JSONB",
    "ALTER TABLE community_partners ADD COLUMN IF NOT EXISTS notes TEXT",
    "ALTER TABLE community_partners ADD COLUMN IF NOT EXISTS registered_at TIMESTAMPTZ DEFAULT NOW()",
    "ALTER TABLE community_partners ADD COLUMN IF NOT EXISTS activated_at TIMESTAMPTZ",
    "ALTER TABLE community_partners ADD COLUMN IF NOT EXISTS tier_id UUID",

    # 3. Create partner_commissions table
    """
    CREATE TABLE IF NOT EXISTS partner_commissions (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        partner_id UUID NOT NULL REFERENCES community_partners(id) ON DELETE CASCADE,
        order_id UUID NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
        order_number VARCHAR(50) NOT NULL,
        order_date TIMESTAMPTZ NOT NULL,
        order_amount NUMERIC(12, 2) NOT NULL,
        order_items_count INTEGER DEFAULT 1,
        commission_rate NUMERIC(5, 2) NOT NULL,
        commission_amount NUMERIC(10, 2) NOT NULL,
        bonus_amount NUMERIC(10, 2) DEFAULT 0.00,
        total_earnings NUMERIC(10, 2) NOT NULL,
        tds_rate NUMERIC(5, 2) DEFAULT 0.00,
        tds_amount NUMERIC(10, 2) DEFAULT 0.00,
        net_earnings NUMERIC(10, 2) NOT NULL,
        tier_id UUID,
        tier_code VARCHAR(20),
        status VARCHAR(50) DEFAULT 'PENDING' NOT NULL,
        payout_id UUID,
        approved_at TIMESTAMPTZ,
        paid_at TIMESTAMPTZ,
        cancelled_at TIMESTAMPTZ,
        cancellation_reason TEXT,
        created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
        updated_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
        UNIQUE(partner_id, order_id)
    )
    """,

    # 4. Create partner_payouts table
    """
    CREATE TABLE IF NOT EXISTS partner_payouts (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        payout_number VARCHAR(50) UNIQUE NOT NULL,
        partner_id UUID NOT NULL REFERENCES community_partners(id) ON DELETE CASCADE,
        gross_amount NUMERIC(12, 2) NOT NULL,
        tds_amount NUMERIC(10, 2) DEFAULT 0.00,
        other_deductions NUMERIC(10, 2) DEFAULT 0.00,
        net_amount NUMERIC(12, 2) NOT NULL,
        payout_method VARCHAR(50) NOT NULL,
        bank_account_number VARCHAR(20),
        bank_ifsc VARCHAR(11),
        bank_name VARCHAR(100),
        upi_id VARCHAR(100),
        status VARCHAR(50) DEFAULT 'PENDING' NOT NULL,
        payment_gateway VARCHAR(50),
        gateway_transaction_id VARCHAR(100),
        gateway_response JSONB,
        initiated_at TIMESTAMPTZ,
        processed_at TIMESTAMPTZ,
        failed_at TIMESTAMPTZ,
        failure_reason TEXT,
        retry_count INTEGER DEFAULT 0,
        initiated_by UUID,
        notes TEXT,
        created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
        updated_at TIMESTAMPTZ DEFAULT NOW() NOT NULL
    )
    """,

    # 5. Create partner_referrals table
    """
    CREATE TABLE IF NOT EXISTS partner_referrals (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        referrer_id UUID NOT NULL REFERENCES community_partners(id) ON DELETE CASCADE,
        referred_id UUID NOT NULL REFERENCES community_partners(id) ON DELETE CASCADE,
        referral_code VARCHAR(20) NOT NULL,
        status VARCHAR(50) DEFAULT 'PENDING',
        referred_activated BOOLEAN DEFAULT FALSE,
        referred_first_sale BOOLEAN DEFAULT FALSE,
        referred_qualified BOOLEAN DEFAULT FALSE,
        qualification_date TIMESTAMPTZ,
        bonus_amount NUMERIC(10, 2) DEFAULT 0.00,
        bonus_paid BOOLEAN DEFAULT FALSE,
        bonus_paid_at TIMESTAMPTZ,
        payout_id UUID,
        referred_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
        created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
        updated_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
        UNIQUE(referrer_id, referred_id)
    )
    """,

    # 6. Create partner_training table
    """
    CREATE TABLE IF NOT EXISTS partner_training (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        partner_id UUID NOT NULL REFERENCES community_partners(id) ON DELETE CASCADE,
        module_code VARCHAR(50) NOT NULL,
        module_name VARCHAR(200) NOT NULL,
        module_type VARCHAR(50) DEFAULT 'VIDEO',
        status VARCHAR(50) DEFAULT 'NOT_STARTED',
        progress_percentage INTEGER DEFAULT 0,
        quiz_score INTEGER,
        quiz_passed BOOLEAN DEFAULT FALSE,
        attempts INTEGER DEFAULT 0,
        certificate_issued BOOLEAN DEFAULT FALSE,
        certificate_url VARCHAR(500),
        certificate_number VARCHAR(50),
        started_at TIMESTAMPTZ,
        completed_at TIMESTAMPTZ,
        expires_at TIMESTAMPTZ,
        created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
        updated_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
        UNIQUE(partner_id, module_code)
    )
    """,

    # 7. Create partner_orders table
    """
    CREATE TABLE IF NOT EXISTS partner_orders (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        partner_id UUID NOT NULL REFERENCES community_partners(id) ON DELETE CASCADE,
        order_id UUID NOT NULL REFERENCES orders(id) ON DELETE CASCADE UNIQUE,
        attribution_source VARCHAR(50) DEFAULT 'PARTNER_LINK',
        partner_code_used VARCHAR(20),
        referral_link VARCHAR(500),
        commission_id UUID,
        attributed_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
        created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL
    )
    """,

    # 8. Create indexes
    "CREATE INDEX IF NOT EXISTS ix_community_partners_referral_code ON community_partners(referral_code)",
    "CREATE INDEX IF NOT EXISTS ix_community_partners_phone ON community_partners(phone)",
    "CREATE INDEX IF NOT EXISTS ix_community_partners_status ON community_partners(status)",
    "CREATE INDEX IF NOT EXISTS ix_partner_commissions_status ON partner_commissions(status)",
    "CREATE INDEX IF NOT EXISTS ix_partner_commissions_created ON partner_commissions(created_at)",
    "CREATE INDEX IF NOT EXISTS ix_partner_payouts_status ON partner_payouts(status)",
    "CREATE INDEX IF NOT EXISTS ix_partner_payouts_created ON partner_payouts(created_at)",

    # 9. Insert default partner tiers
    """
    INSERT INTO partner_tiers (code, name, description, level, min_monthly_sales, min_monthly_value, commission_percentage, bonus_percentage, referral_bonus, is_active, is_default)
    VALUES
        ('BRONZE', 'Bronze Partner', 'Entry level partner tier', 1, 0, 0.00, 10.00, 0.00, 100.00, TRUE, TRUE),
        ('SILVER', 'Silver Partner', 'Mid-level partner tier with better rates', 2, 5, 50000.00, 12.00, 1.00, 150.00, TRUE, FALSE),
        ('GOLD', 'Gold Partner', 'High-performing partner tier', 3, 15, 150000.00, 14.00, 2.00, 200.00, TRUE, FALSE),
        ('PLATINUM', 'Platinum Partner', 'Top-tier partner with maximum benefits', 4, 30, 300000.00, 15.00, 3.00, 300.00, TRUE, FALSE)
    ON CONFLICT (code) DO NOTHING
    """,
]


async def run_fix():
    """Run the schema fix."""
    print("Connecting to production database...")
    engine = create_async_engine(DATABASE_URL, echo=False)

    async_session = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )

    async with async_session() as session:
        for i, sql in enumerate(SQL_STATEMENTS, 1):
            try:
                print(f"Executing statement {i}/{len(SQL_STATEMENTS)}...")
                await session.execute(text(sql))
                await session.commit()
                print(f"  ✓ Statement {i} executed successfully")
            except Exception as e:
                print(f"  ✗ Statement {i} failed: {str(e)[:100]}")
                await session.rollback()

    # Verify
    async with async_session() as session:
        print("\nVerifying community_partners columns...")
        result = await session.execute(text("""
            SELECT column_name FROM information_schema.columns
            WHERE table_name = 'community_partners'
            ORDER BY ordinal_position
        """))
        columns = [row[0] for row in result.fetchall()]
        print(f"  Found {len(columns)} columns: {', '.join(columns[:10])}...")

        print("\nVerifying partner_tiers...")
        result = await session.execute(text("SELECT code, commission_percentage FROM partner_tiers"))
        tiers = result.fetchall()
        print(f"  Found {len(tiers)} tiers: {', '.join([t[0] for t in tiers])}")

    await engine.dispose()
    print("\n✅ Schema fix completed!")


if __name__ == "__main__":
    asyncio.run(run_fix())
