"""Add DMS (Distribution Management System) module and activate for finaltest tenant

Revision ID: 20260218_dms
Revises: 20260217_add_warehouse_pnl_columns
Create Date: 2026-02-18
"""
from alembic import op
from sqlalchemy.sql import text

# revision identifiers
revision = '20260218_dms'
down_revision = '20260217_add_warehouse_pnl_columns'
branch_labels = None
depends_on = None


def upgrade():
    """Insert DMS module and activate subscription for finaltest tenant."""
    conn = op.get_bind()

    # Insert DMS module
    conn.execute(text("""
        INSERT INTO public.modules (
            code, name, description, category, icon, color,
            display_order, price_monthly, price_yearly,
            is_base_module, dependencies, sections
        )
        VALUES (
            'dms',
            'Distribution Management (DMS)',
            'Distributor management system: DMS dashboard, B2B orders, dealer pricing, credit management, schemes, and distributor performance analytics',
            'commerce',
            '🚛',
            'indigo',
            11,
            8999,
            97190,
            false,
            '["oms_fulfillment"]'::jsonb,
            '[]'::jsonb
        )
        ON CONFLICT (code) DO NOTHING
    """))

    # Activate DMS for the finaltest tenant (admin@finaltest.com)
    # Find the tenant and module, then create subscription
    conn.execute(text("""
        INSERT INTO public.tenant_subscriptions (
            tenant_id, module_id, status, subscription_type,
            billing_cycle, price_paid, starts_at, is_trial, auto_renew
        )
        SELECT
            t.id AS tenant_id,
            m.id AS module_id,
            'active',
            'module',
            'monthly',
            8999,
            NOW(),
            false,
            true
        FROM public.tenants t
        CROSS JOIN public.modules m
        WHERE m.code = 'dms'
        AND EXISTS (
            SELECT 1 FROM public.users u
            WHERE u.tenant_id = t.id AND u.email = 'admin@finaltest.com'
        )
        ON CONFLICT DO NOTHING
    """))

    # Also add DMS module to Professional and Enterprise plans
    conn.execute(text("""
        UPDATE public.plans
        SET included_modules = included_modules || '"dms"'::jsonb
        WHERE slug IN ('professional', 'enterprise')
        AND NOT included_modules ? 'dms'
    """))


def downgrade():
    """Remove DMS module and related subscriptions."""
    conn = op.get_bind()

    # Remove DMS subscriptions
    conn.execute(text("""
        DELETE FROM public.tenant_subscriptions
        WHERE module_id IN (SELECT id FROM public.modules WHERE code = 'dms')
    """))

    # Remove DMS from plans
    conn.execute(text("""
        UPDATE public.plans
        SET included_modules = included_modules - 'dms'
        WHERE included_modules ? 'dms'
    """))

    # Remove DMS module
    conn.execute(text("""
        DELETE FROM public.modules WHERE code = 'dms'
    """))
