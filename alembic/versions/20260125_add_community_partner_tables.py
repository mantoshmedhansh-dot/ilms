"""Add Community Partner tables for Meesho-style sales channel

Revision ID: community_partner_001
Revises:
Create Date: 2026-01-25

Tables created:
- partner_tiers: Commission tier configuration (Bronze, Silver, Gold, Platinum)
- community_partners: Main partner registration with KYC
- partner_commissions: Per-sale commission tracking
- partner_payouts: Payout batch records
- partner_referrals: Referral tracking
- partner_training: Training/certification completion
- partner_orders: Order-to-partner attribution
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB


# revision identifiers, used by Alembic.
revision = 'community_partner_001'
down_revision = '20260123_add_customer_ledger'
branch_labels = None
depends_on = None


def upgrade():
    # Check if tables already exist (for idempotent migrations)
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    existing_tables = inspector.get_table_names()

    # 1. Partner Tiers Table
    if 'partner_tiers' not in existing_tables:
        op.create_table(
            'partner_tiers',
            sa.Column('id', UUID(as_uuid=True), primary_key=True),
            sa.Column('name', sa.String(50), nullable=False),
            sa.Column('code', sa.String(20), nullable=False, unique=True),
            sa.Column('min_orders', sa.Integer(), default=0),
            sa.Column('min_revenue', sa.Numeric(18, 2), default=0),
            sa.Column('commission_rate', sa.Numeric(5, 2), nullable=False),
            sa.Column('bonus_rate', sa.Numeric(5, 2), default=0),
            sa.Column('benefits', JSONB, nullable=True),
            sa.Column('is_active', sa.Boolean(), default=True),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()')),
            sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()')),
        )
        print("Created table: partner_tiers")

    # 2. Community Partners Table
    if 'community_partners' not in existing_tables:
        op.create_table(
            'community_partners',
            sa.Column('id', UUID(as_uuid=True), primary_key=True),
            sa.Column('partner_code', sa.String(20), nullable=False, unique=True),
            sa.Column('full_name', sa.String(200), nullable=False),
            sa.Column('phone', sa.String(20), nullable=False, unique=True),
            sa.Column('email', sa.String(255), nullable=True),
            sa.Column('whatsapp_number', sa.String(20), nullable=True),

            # Address
            sa.Column('address_line1', sa.String(500), nullable=True),
            sa.Column('address_line2', sa.String(500), nullable=True),
            sa.Column('city', sa.String(100), nullable=True),
            sa.Column('state', sa.String(100), nullable=True),
            sa.Column('pincode', sa.String(10), nullable=True),

            # Profile
            sa.Column('profile_photo_url', sa.String(500), nullable=True),
            sa.Column('date_of_birth', sa.Date(), nullable=True),
            sa.Column('gender', sa.String(20), nullable=True),
            sa.Column('language_preference', sa.String(10), default='hi'),

            # Status
            sa.Column('status', sa.String(50), default='PENDING_KYC'),
            sa.Column('tier_id', UUID(as_uuid=True), sa.ForeignKey('partner_tiers.id'), nullable=True),

            # KYC Documents
            sa.Column('aadhaar_number', sa.String(12), nullable=True),
            sa.Column('aadhaar_front_url', sa.String(500), nullable=True),
            sa.Column('aadhaar_back_url', sa.String(500), nullable=True),
            sa.Column('pan_number', sa.String(10), nullable=True),
            sa.Column('pan_card_url', sa.String(500), nullable=True),
            sa.Column('selfie_url', sa.String(500), nullable=True),

            # KYC Status
            sa.Column('kyc_status', sa.String(50), default='NOT_STARTED'),
            sa.Column('kyc_submitted_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('kyc_verified_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('kyc_verified_by', UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=True),
            sa.Column('kyc_rejection_reason', sa.Text(), nullable=True),

            # Bank Details
            sa.Column('bank_account_number', sa.String(20), nullable=True),
            sa.Column('bank_ifsc', sa.String(11), nullable=True),
            sa.Column('bank_account_name', sa.String(200), nullable=True),
            sa.Column('bank_name', sa.String(200), nullable=True),
            sa.Column('cancelled_cheque_url', sa.String(500), nullable=True),

            # Referral
            sa.Column('referred_by', UUID(as_uuid=True), nullable=True),  # Self-referential
            sa.Column('referral_code', sa.String(20), nullable=True, unique=True),

            # Performance Metrics (Denormalized for quick access)
            sa.Column('total_orders', sa.Integer(), default=0),
            sa.Column('total_sales', sa.Numeric(18, 2), default=0),
            sa.Column('total_commission_earned', sa.Numeric(18, 2), default=0),
            sa.Column('total_commission_paid', sa.Numeric(18, 2), default=0),
            sa.Column('average_rating', sa.Numeric(3, 2), nullable=True),

            # Timestamps
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()')),
            sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()')),
            sa.Column('activated_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('last_active_at', sa.DateTime(timezone=True), nullable=True),

            # Metadata
            sa.Column('metadata', JSONB, nullable=True),
        )
        # Create indexes
        op.create_index('ix_community_partners_phone', 'community_partners', ['phone'])
        op.create_index('ix_community_partners_status', 'community_partners', ['status'])
        op.create_index('ix_community_partners_kyc_status', 'community_partners', ['kyc_status'])
        op.create_index('ix_community_partners_state', 'community_partners', ['state'])
        op.create_index('ix_community_partners_referral_code', 'community_partners', ['referral_code'])
        print("Created table: community_partners")

    # 3. Partner Commissions Table
    if 'partner_commissions' not in existing_tables:
        op.create_table(
            'partner_commissions',
            sa.Column('id', UUID(as_uuid=True), primary_key=True),
            sa.Column('partner_id', UUID(as_uuid=True), sa.ForeignKey('community_partners.id'), nullable=False),
            sa.Column('order_id', UUID(as_uuid=True), sa.ForeignKey('orders.id'), nullable=False),
            sa.Column('order_amount', sa.Numeric(18, 2), nullable=False),
            sa.Column('commission_rate', sa.Numeric(5, 2), nullable=False),
            sa.Column('commission_amount', sa.Numeric(18, 2), nullable=False),
            sa.Column('bonus_amount', sa.Numeric(18, 2), default=0),
            sa.Column('tds_rate', sa.Numeric(5, 2), default=0),
            sa.Column('tds_amount', sa.Numeric(18, 2), default=0),
            sa.Column('net_amount', sa.Numeric(18, 2), nullable=False),
            sa.Column('status', sa.String(50), default='PENDING'),
            sa.Column('payout_id', UUID(as_uuid=True), nullable=True),  # Will reference partner_payouts
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()')),
            sa.Column('approved_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('paid_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('notes', sa.Text(), nullable=True),
        )
        op.create_index('ix_partner_commissions_partner_id', 'partner_commissions', ['partner_id'])
        op.create_index('ix_partner_commissions_status', 'partner_commissions', ['status'])
        print("Created table: partner_commissions")

    # 4. Partner Payouts Table
    if 'partner_payouts' not in existing_tables:
        op.create_table(
            'partner_payouts',
            sa.Column('id', UUID(as_uuid=True), primary_key=True),
            sa.Column('partner_id', UUID(as_uuid=True), sa.ForeignKey('community_partners.id'), nullable=False),
            sa.Column('payout_number', sa.String(50), nullable=False, unique=True),
            sa.Column('gross_amount', sa.Numeric(18, 2), nullable=False),
            sa.Column('tds_amount', sa.Numeric(18, 2), default=0),
            sa.Column('net_amount', sa.Numeric(18, 2), nullable=False),
            sa.Column('status', sa.String(50), default='PENDING'),
            sa.Column('payout_method', sa.String(50), default='BANK_TRANSFER'),
            sa.Column('payout_details', JSONB, nullable=True),
            sa.Column('payout_reference', sa.String(100), nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()')),
            sa.Column('processed_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('failure_reason', sa.Text(), nullable=True),
        )
        op.create_index('ix_partner_payouts_partner_id', 'partner_payouts', ['partner_id'])
        op.create_index('ix_partner_payouts_status', 'partner_payouts', ['status'])
        print("Created table: partner_payouts")

    # Add FK from commissions to payouts (after payouts table exists)
    if 'partner_commissions' in existing_tables or 'partner_commissions' not in existing_tables:
        try:
            op.create_foreign_key(
                'fk_partner_commissions_payout_id',
                'partner_commissions',
                'partner_payouts',
                ['payout_id'],
                ['id']
            )
        except Exception:
            pass  # FK might already exist

    # 5. Partner Referrals Table
    if 'partner_referrals' not in existing_tables:
        op.create_table(
            'partner_referrals',
            sa.Column('id', UUID(as_uuid=True), primary_key=True),
            sa.Column('referrer_id', UUID(as_uuid=True), sa.ForeignKey('community_partners.id'), nullable=False),
            sa.Column('referred_id', UUID(as_uuid=True), sa.ForeignKey('community_partners.id'), nullable=False),
            sa.Column('referral_code', sa.String(20), nullable=False),
            sa.Column('referral_bonus', sa.Numeric(18, 2), default=0),
            sa.Column('is_qualified', sa.Boolean(), default=False),
            sa.Column('qualified_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('qualification_order_id', UUID(as_uuid=True), nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()')),
        )
        op.create_index('ix_partner_referrals_referrer_id', 'partner_referrals', ['referrer_id'])
        print("Created table: partner_referrals")

    # 6. Partner Training Table
    if 'partner_training' not in existing_tables:
        op.create_table(
            'partner_training',
            sa.Column('id', UUID(as_uuid=True), primary_key=True),
            sa.Column('partner_id', UUID(as_uuid=True), sa.ForeignKey('community_partners.id'), nullable=False),
            sa.Column('training_name', sa.String(200), nullable=False),
            sa.Column('training_type', sa.String(50), nullable=False),
            sa.Column('description', sa.Text(), nullable=True),
            sa.Column('video_url', sa.String(500), nullable=True),
            sa.Column('document_url', sa.String(500), nullable=True),
            sa.Column('is_mandatory', sa.Boolean(), default=False),
            sa.Column('passing_score', sa.Integer(), nullable=True),
            sa.Column('is_completed', sa.Boolean(), default=False),
            sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('score', sa.Integer(), nullable=True),
            sa.Column('certificate_url', sa.String(500), nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()')),
        )
        op.create_index('ix_partner_training_partner_id', 'partner_training', ['partner_id'])
        print("Created table: partner_training")

    # 7. Partner Orders Table (Order Attribution)
    if 'partner_orders' not in existing_tables:
        op.create_table(
            'partner_orders',
            sa.Column('id', UUID(as_uuid=True), primary_key=True),
            sa.Column('partner_id', UUID(as_uuid=True), sa.ForeignKey('community_partners.id'), nullable=False),
            sa.Column('order_id', UUID(as_uuid=True), sa.ForeignKey('orders.id'), nullable=False, unique=True),
            sa.Column('customer_id', UUID(as_uuid=True), sa.ForeignKey('customers.id'), nullable=True),
            sa.Column('order_amount', sa.Numeric(18, 2), nullable=False),
            sa.Column('commission_id', UUID(as_uuid=True), sa.ForeignKey('partner_commissions.id'), nullable=True),
            sa.Column('attribution_source', sa.String(50), default='DIRECT'),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()')),
        )
        op.create_index('ix_partner_orders_partner_id', 'partner_orders', ['partner_id'])
        op.create_index('ix_partner_orders_order_id', 'partner_orders', ['order_id'])
        print("Created table: partner_orders")

    # Self-referential FK for community_partners.referred_by
    try:
        op.create_foreign_key(
            'fk_community_partners_referred_by',
            'community_partners',
            'community_partners',
            ['referred_by'],
            ['id']
        )
    except Exception:
        pass  # FK might already exist

    # Seed default partner tiers
    conn = op.get_bind()
    result = conn.execute(sa.text("SELECT COUNT(*) FROM partner_tiers"))
    count = result.scalar()
    if count == 0:
        conn.execute(sa.text("""
            INSERT INTO partner_tiers (id, name, code, min_orders, min_revenue, commission_rate, bonus_rate, benefits, is_active)
            VALUES
                (gen_random_uuid(), 'Bronze', 'BRONZE', 0, 0, 10.00, 0, '{"badge": "bronze", "support": "email"}', true),
                (gen_random_uuid(), 'Silver', 'SILVER', 10, 50000, 12.00, 1.00, '{"badge": "silver", "support": "chat"}', true),
                (gen_random_uuid(), 'Gold', 'GOLD', 25, 150000, 15.00, 2.00, '{"badge": "gold", "support": "priority", "early_payout": true}', true),
                (gen_random_uuid(), 'Platinum', 'PLATINUM', 50, 500000, 18.00, 3.00, '{"badge": "platinum", "support": "dedicated", "early_payout": true, "exclusive_products": true}', true)
        """))
        print("Seeded default partner tiers: Bronze, Silver, Gold, Platinum")


def downgrade():
    # Drop tables in reverse order of dependencies
    op.drop_table('partner_orders')
    op.drop_table('partner_training')
    op.drop_table('partner_referrals')
    op.drop_table('partner_commissions')
    op.drop_table('partner_payouts')
    op.drop_table('community_partners')
    op.drop_table('partner_tiers')
