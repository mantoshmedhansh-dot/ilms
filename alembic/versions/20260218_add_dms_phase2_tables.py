"""Add DMS Phase 2 tables: dealer_claims and retailer_outlets

Revision ID: 20260218_dms_phase2
Revises: 20260218_dms
Create Date: 2026-02-18
"""
from alembic import op
from sqlalchemy.sql import text

# revision identifiers
revision = '20260218_dms_phase2'
down_revision = '20260218_dms'
branch_labels = None
depends_on = None


def upgrade():
    """Create dealer_claims and retailer_outlets tables."""
    conn = op.get_bind()

    # Create dealer_claims table
    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS public.dealer_claims (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            claim_number VARCHAR(30) NOT NULL UNIQUE,
            dealer_id UUID NOT NULL REFERENCES public.dealers(id) ON DELETE CASCADE,
            claim_type VARCHAR(50) NOT NULL,
            status VARCHAR(50) NOT NULL DEFAULT 'SUBMITTED',
            order_id UUID REFERENCES public.orders(id) ON DELETE SET NULL,
            items JSONB,
            evidence_urls JSONB,
            amount_claimed NUMERIC(14,2) NOT NULL,
            amount_approved NUMERIC(14,2) DEFAULT 0,
            resolution VARCHAR(50),
            resolution_notes TEXT,
            submitted_at TIMESTAMPTZ,
            reviewed_at TIMESTAMPTZ,
            settled_at TIMESTAMPTZ,
            assigned_to UUID REFERENCES public.users(id) ON DELETE SET NULL,
            created_by UUID,
            remarks TEXT,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """))

    # Create indexes for dealer_claims
    conn.execute(text("""
        CREATE INDEX IF NOT EXISTS ix_dealer_claims_claim_number ON public.dealer_claims(claim_number);
        CREATE INDEX IF NOT EXISTS ix_dealer_claims_dealer ON public.dealer_claims(dealer_id, status);
        CREATE INDEX IF NOT EXISTS ix_dealer_claims_status ON public.dealer_claims(status);
    """))

    # Create retailer_outlets table
    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS public.retailer_outlets (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            outlet_code VARCHAR(30) NOT NULL UNIQUE,
            dealer_id UUID NOT NULL REFERENCES public.dealers(id) ON DELETE CASCADE,
            name VARCHAR(200) NOT NULL,
            owner_name VARCHAR(200) NOT NULL,
            outlet_type VARCHAR(50) NOT NULL,
            phone VARCHAR(20) NOT NULL,
            email VARCHAR(255),
            address_line1 VARCHAR(255) NOT NULL,
            city VARCHAR(100) NOT NULL,
            state VARCHAR(100) NOT NULL,
            pincode VARCHAR(10) NOT NULL,
            latitude NUMERIC(10,7),
            longitude NUMERIC(10,7),
            beat_day VARCHAR(20),
            status VARCHAR(20) NOT NULL DEFAULT 'ACTIVE',
            last_order_date TIMESTAMPTZ,
            total_orders INTEGER NOT NULL DEFAULT 0,
            total_revenue NUMERIC(14,2) NOT NULL DEFAULT 0,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """))

    # Create indexes for retailer_outlets
    conn.execute(text("""
        CREATE INDEX IF NOT EXISTS ix_retailer_outlets_outlet_code ON public.retailer_outlets(outlet_code);
        CREATE INDEX IF NOT EXISTS ix_retailer_outlets_dealer ON public.retailer_outlets(dealer_id, status);
    """))

    # Enable RLS
    conn.execute(text("""
        ALTER TABLE public.dealer_claims ENABLE ROW LEVEL SECURITY;
        ALTER TABLE public.retailer_outlets ENABLE ROW LEVEL SECURITY;
    """))


def downgrade():
    """Drop dealer_claims and retailer_outlets tables."""
    conn = op.get_bind()
    conn.execute(text("DROP TABLE IF EXISTS public.dealer_claims CASCADE"))
    conn.execute(text("DROP TABLE IF EXISTS public.retailer_outlets CASCADE"))
