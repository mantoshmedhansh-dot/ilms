"""Create multi-tenant schema

Revision ID: 001_multitenant
Revises:
Create Date: 2026-01-31
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

# revision identifiers
revision = '001_multitenant'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    """Create multi-tenant management tables in public schema"""

    # ====================
    # TENANTS TABLE
    # ====================
    op.create_table(
        'tenants',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('subdomain', sa.String(100), unique=True, nullable=False),
        sa.Column('database_schema', sa.String(100), nullable=False),
        sa.Column('status', sa.String(20), server_default='active', nullable=False),
        sa.Column('plan_id', UUID(as_uuid=True), nullable=True),
        sa.Column('trial_ends_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('onboarded_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.Column('settings', JSONB, server_default='{}', nullable=False),
        sa.Column('metadata', JSONB, server_default='{}', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        schema='public'
    )

    op.create_index('idx_tenants_subdomain', 'tenants', ['subdomain'], schema='public')
    op.create_index('idx_tenants_status', 'tenants', ['status'], schema='public')

    # ====================
    # MODULES TABLE
    # ====================
    op.create_table(
        'modules',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('code', sa.String(50), unique=True, nullable=False),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('category', sa.String(50), nullable=True),
        sa.Column('icon', sa.String(50), nullable=True),
        sa.Column('color', sa.String(20), nullable=True),
        sa.Column('display_order', sa.Integer, nullable=True),
        sa.Column('price_monthly', sa.Numeric(10, 2), nullable=True),
        sa.Column('price_yearly', sa.Numeric(10, 2), nullable=True),
        sa.Column('is_base_module', sa.Boolean, server_default='false', nullable=False),
        sa.Column('dependencies', JSONB, server_default='[]', nullable=False),
        sa.Column('sections', JSONB, server_default='[]', nullable=False),
        sa.Column('database_tables', JSONB, server_default='[]', nullable=False),
        sa.Column('api_endpoints', JSONB, server_default='[]', nullable=False),
        sa.Column('frontend_routes', JSONB, server_default='[]', nullable=False),
        sa.Column('features', JSONB, server_default='[]', nullable=False),
        sa.Column('is_active', sa.Boolean, server_default='true', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        schema='public'
    )

    op.create_index('idx_modules_code', 'modules', ['code'], schema='public')
    op.create_index('idx_modules_category', 'modules', ['category'], schema='public')

    # ====================
    # PLANS TABLE
    # ====================
    op.create_table(
        'plans',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('slug', sa.String(50), unique=True, nullable=False),
        sa.Column('type', sa.String(20), nullable=False),
        sa.Column('billing_cycle', sa.String(20), nullable=True),
        sa.Column('price_inr', sa.Numeric(10, 2), nullable=True),
        sa.Column('original_price_inr', sa.Numeric(10, 2), nullable=True),
        sa.Column('discount_percent', sa.Integer, server_default='0', nullable=False),
        sa.Column('included_modules', JSONB, server_default='[]', nullable=False),
        sa.Column('max_users', sa.Integer, nullable=True),
        sa.Column('max_transactions_monthly', sa.Integer, nullable=True),
        sa.Column('features', JSONB, server_default='[]', nullable=False),
        sa.Column('is_active', sa.Boolean, server_default='true', nullable=False),
        sa.Column('is_popular', sa.Boolean, server_default='false', nullable=False),
        sa.Column('display_order', sa.Integer, nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        schema='public'
    )

    op.create_index('idx_plans_slug', 'plans', ['slug'], schema='public')
    op.create_index('idx_plans_type', 'plans', ['type'], schema='public')

    # ====================
    # TENANT SUBSCRIPTIONS TABLE
    # ====================
    op.create_table(
        'tenant_subscriptions',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('tenant_id', UUID(as_uuid=True), nullable=False),
        sa.Column('module_id', UUID(as_uuid=True), nullable=False),
        sa.Column('plan_id', UUID(as_uuid=True), nullable=True),
        sa.Column('status', sa.String(20), server_default='active', nullable=False),
        sa.Column('subscription_type', sa.String(20), nullable=True),
        sa.Column('billing_cycle', sa.String(20), nullable=True),
        sa.Column('price_paid', sa.Numeric(10, 2), nullable=True),
        sa.Column('starts_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('is_trial', sa.Boolean, server_default='false', nullable=False),
        sa.Column('trial_ends_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('auto_renew', sa.Boolean, server_default='true', nullable=False),
        sa.Column('settings', JSONB, server_default='{}', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.ForeignKeyConstraint(['tenant_id'], ['public.tenants.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['module_id'], ['public.modules.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['plan_id'], ['public.plans.id'], ondelete='SET NULL'),
        sa.UniqueConstraint('tenant_id', 'module_id', name='uq_tenant_module'),
        schema='public'
    )

    op.create_index('idx_tenant_subs_tenant', 'tenant_subscriptions', ['tenant_id'], schema='public')
    op.create_index('idx_tenant_subs_module', 'tenant_subscriptions', ['module_id'], schema='public')
    op.create_index('idx_tenant_subs_status', 'tenant_subscriptions', ['status'], schema='public')

    # ====================
    # FEATURE FLAGS TABLE
    # ====================
    op.create_table(
        'feature_flags',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('tenant_id', UUID(as_uuid=True), nullable=False),
        sa.Column('module_code', sa.String(50), nullable=False),
        sa.Column('feature_key', sa.String(100), nullable=False),
        sa.Column('is_enabled', sa.Boolean, server_default='false', nullable=False),
        sa.Column('config', JSONB, server_default='{}', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.ForeignKeyConstraint(['tenant_id'], ['public.tenants.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('tenant_id', 'module_code', 'feature_key', name='uq_tenant_module_feature'),
        schema='public'
    )

    op.create_index('idx_feature_flags_tenant', 'feature_flags', ['tenant_id'], schema='public')
    op.create_index('idx_feature_flags_module', 'feature_flags', ['module_code'], schema='public')

    # ====================
    # BILLING HISTORY TABLE
    # ====================
    op.create_table(
        'billing_history',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('tenant_id', UUID(as_uuid=True), nullable=False),
        sa.Column('invoice_number', sa.String(50), unique=True, nullable=False),
        sa.Column('billing_period_start', sa.DateTime(timezone=True), nullable=False),
        sa.Column('billing_period_end', sa.DateTime(timezone=True), nullable=False),
        sa.Column('amount', sa.Numeric(10, 2), nullable=False),
        sa.Column('tax_amount', sa.Numeric(10, 2), server_default='0', nullable=False),
        sa.Column('total_amount', sa.Numeric(10, 2), nullable=False),
        sa.Column('status', sa.String(20), server_default='pending', nullable=False),
        sa.Column('payment_method', sa.String(50), nullable=True),
        sa.Column('payment_transaction_id', sa.String(255), nullable=True),
        sa.Column('invoice_data', JSONB, server_default='{}', nullable=False),
        sa.Column('paid_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('due_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.ForeignKeyConstraint(['tenant_id'], ['public.tenants.id'], ondelete='CASCADE'),
        schema='public'
    )

    op.create_index('idx_billing_tenant', 'billing_history', ['tenant_id'], schema='public')
    op.create_index('idx_billing_status', 'billing_history', ['status'], schema='public')
    op.create_index('idx_billing_invoice', 'billing_history', ['invoice_number'], schema='public')

    # ====================
    # USAGE METRICS TABLE
    # ====================
    op.create_table(
        'usage_metrics',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('tenant_id', UUID(as_uuid=True), nullable=False),
        sa.Column('module_code', sa.String(50), nullable=True),
        sa.Column('metric_type', sa.String(50), nullable=True),
        sa.Column('metric_value', sa.Numeric(15, 2), nullable=True),
        sa.Column('recorded_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.Column('metadata', JSONB, server_default='{}', nullable=False),
        sa.ForeignKeyConstraint(['tenant_id'], ['public.tenants.id'], ondelete='CASCADE'),
        schema='public'
    )

    op.create_index('idx_usage_tenant', 'usage_metrics', ['tenant_id'], schema='public')
    op.create_index('idx_usage_module', 'usage_metrics', ['module_code'], schema='public')
    op.create_index('idx_usage_recorded', 'usage_metrics', ['recorded_at'], schema='public')

    # Add foreign key constraint to tenants.plan_id (after plans table is created)
    op.create_foreign_key(
        'fk_tenants_plan_id',
        'tenants', 'plans',
        ['plan_id'], ['id'],
        source_schema='public',
        referent_schema='public',
        ondelete='SET NULL'
    )


def downgrade():
    """Drop all multi-tenant tables"""
    op.drop_table('usage_metrics', schema='public')
    op.drop_table('billing_history', schema='public')
    op.drop_table('feature_flags', schema='public')
    op.drop_table('tenant_subscriptions', schema='public')
    op.drop_table('plans', schema='public')
    op.drop_table('modules', schema='public')
    op.drop_table('tenants', schema='public')
