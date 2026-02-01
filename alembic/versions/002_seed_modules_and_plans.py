"""Seed modules and pricing plans

Revision ID: 002_seed_data
Revises: 001_multitenant
Create Date: 2026-01-31
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import text

# revision identifiers
revision = '002_seed_data'
down_revision = '001_multitenant'
branch_labels = None
depends_on = None


def upgrade():
    """Insert module definitions and pricing plans"""

    # ====================
    # INSERT MODULES
    # ====================
    conn = op.get_bind()

    # Module 1: OMS, WMS & Fulfillment
    conn.execute(text("""
        INSERT INTO public.modules (code, name, description, category, icon, color, display_order, price_monthly, price_yearly, is_base_module, dependencies, sections)
        VALUES (
            'oms_fulfillment',
            'OMS, WMS & Fulfillment',
            'Complete order management, warehouse operations, inventory tracking, and shipping',
            'core',
            '📦',
            'blue',
            1,
            12999,
            139990,
            false,
            '[]'::jsonb,
            '[3, 8, 9, 10]'::jsonb
        )
    """))

    # Module 2: Procurement
    conn.execute(text("""
        INSERT INTO public.modules (code, name, description, category, icon, color, display_order, price_monthly, price_yearly, is_base_module, dependencies, sections)
        VALUES (
            'procurement',
            'Procurement (P2P)',
            'Purchase-to-pay workflow: requisitions, purchase orders, GRN, vendor invoices, and payments',
            'operations',
            '🛒',
            'blue',
            2,
            6999,
            75990,
            false,
            '[]'::jsonb,
            '[7]'::jsonb
        )
    """))

    # Module 3: Finance & Accounting
    conn.execute(text("""
        INSERT INTO public.modules (code, name, description, category, icon, color, display_order, price_monthly, price_yearly, is_base_module, dependencies, sections)
        VALUES (
            'finance',
            'Finance & Accounting',
            'Complete accounting, GST compliance, invoicing, financial reporting, and bank reconciliation',
            'finance',
            '💰',
            'green',
            3,
            9999,
            107990,
            false,
            '[]'::jsonb,
            '[12, 13, 14]'::jsonb
        )
    """))

    # Module 4: CRM & Service
    conn.execute(text("""
        INSERT INTO public.modules (code, name, description, category, icon, color, display_order, price_monthly, price_yearly, is_base_module, dependencies, sections)
        VALUES (
            'crm_service',
            'CRM & Service Management',
            'Customer relationship management, leads, call center, service requests, AMC, and warranty',
            'people',
            '👥',
            'orange',
            4,
            6999,
            75990,
            false,
            '[]'::jsonb,
            '[16, 15]'::jsonb
        )
    """))

    # Module 5: Multi-Channel Sales & Distribution
    conn.execute(text("""
        INSERT INTO public.modules (code, name, description, category, icon, color, display_order, price_monthly, price_yearly, is_base_module, dependencies, sections)
        VALUES (
            'sales_distribution',
            'Multi-Channel Sales & Distribution',
            'Multi-channel selling (D2C, B2B, Marketplaces), dealer network, franchisees, and community partners',
            'commerce',
            '🌐',
            'purple',
            5,
            7999,
            86390,
            false,
            '["oms_fulfillment"]'::jsonb,
            '[4, 5, 6]'::jsonb
        )
    """))

    # Module 6: HRMS
    conn.execute(text("""
        INSERT INTO public.modules (code, name, description, category, icon, color, display_order, price_monthly, price_yearly, is_base_module, dependencies, sections)
        VALUES (
            'hrms',
            'HRMS',
            'Human resource management: employees, attendance, leave, payroll, and performance',
            'people',
            '👔',
            'teal',
            6,
            4999,
            53990,
            false,
            '[]'::jsonb,
            '[18]'::jsonb
        )
    """))

    # Module 7: D2C E-Commerce Storefront
    conn.execute(text("""
        INSERT INTO public.modules (code, name, description, category, icon, color, display_order, price_monthly, price_yearly, is_base_module, dependencies, sections)
        VALUES (
            'd2c_storefront',
            'D2C E-Commerce Storefront',
            'Customer-facing e-commerce website, product catalog, CMS, shopping cart, and checkout',
            'commerce',
            '🛍️',
            'purple',
            7,
            3999,
            43190,
            false,
            '["oms_fulfillment"]'::jsonb,
            '[19, 20]'::jsonb
        )
    """))

    # Module 8: Supply Chain & AI Insights
    conn.execute(text("""
        INSERT INTO public.modules (code, name, description, category, icon, color, display_order, price_monthly, price_yearly, is_base_module, dependencies, sections)
        VALUES (
            'scm_ai',
            'Supply Chain & AI Insights',
            'AI-powered demand forecasting, S&OP planning, reorder suggestions, and inventory optimization',
            'advanced',
            '🤖',
            'darkblue',
            8,
            8999,
            97190,
            false,
            '["oms_fulfillment"]'::jsonb,
            '[2, 11]'::jsonb
        )
    """))

    # Module 9: Marketing & Promotions
    conn.execute(text("""
        INSERT INTO public.modules (code, name, description, category, icon, color, display_order, price_monthly, price_yearly, is_base_module, dependencies, sections)
        VALUES (
            'marketing',
            'Marketing & Promotions',
            'Marketing campaigns, promotions, coupons, and affiliate programs',
            'marketing',
            '📢',
            'pink',
            9,
            3999,
            43190,
            false,
            '[]'::jsonb,
            '[17]'::jsonb
        )
    """))

    # Module 10: System Administration (Base Module)
    conn.execute(text("""
        INSERT INTO public.modules (code, name, description, category, icon, color, display_order, price_monthly, price_yearly, is_base_module, dependencies, sections)
        VALUES (
            'system_admin',
            'System Administration',
            'Core system functions: dashboard, user management, roles, permissions, and audit logs',
            'core',
            '⚙️',
            'gray',
            10,
            2999,
            32390,
            true,
            '[]'::jsonb,
            '[1, 21, 22]'::jsonb
        )
    """))

    # ====================
    # INSERT PLANS
    # ====================

    # Starter Bundle
    conn.execute(text("""
        INSERT INTO public.plans (name, slug, type, billing_cycle, price_inr, original_price_inr, discount_percent, included_modules, max_users, max_transactions_monthly, is_popular, display_order)
        VALUES (
            'Starter',
            'starter',
            'bundle',
            'monthly',
            19999,
            19999,
            0,
            '["system_admin", "oms_fulfillment", "d2c_storefront"]'::jsonb,
            5,
            1000,
            false,
            1
        )
    """))

    # Growth Bundle (15% discount)
    conn.execute(text("""
        INSERT INTO public.plans (name, slug, type, billing_cycle, price_inr, original_price_inr, discount_percent, included_modules, max_users, max_transactions_monthly, is_popular, display_order)
        VALUES (
            'Growth',
            'growth',
            'bundle',
            'monthly',
            39999,
            46995,
            15,
            '["system_admin", "oms_fulfillment", "d2c_storefront", "procurement", "finance", "crm_service"]'::jsonb,
            20,
            5000,
            true,
            2
        )
    """))

    # Professional Bundle (10% discount)
    conn.execute(text("""
        INSERT INTO public.plans (name, slug, type, billing_cycle, price_inr, original_price_inr, discount_percent, included_modules, max_users, max_transactions_monthly, is_popular, display_order)
        VALUES (
            'Professional',
            'professional',
            'bundle',
            'monthly',
            59999,
            66994,
            10,
            '["system_admin", "oms_fulfillment", "d2c_storefront", "procurement", "finance", "crm_service", "sales_distribution", "scm_ai", "marketing"]'::jsonb,
            50,
            20000,
            false,
            3
        )
    """))

    # Enterprise Bundle
    conn.execute(text("""
        INSERT INTO public.plans (name, slug, type, billing_cycle, price_inr, original_price_inr, discount_percent, included_modules, max_users, max_transactions_monthly, is_popular, display_order)
        VALUES (
            'Enterprise',
            'enterprise',
            'bundle',
            'monthly',
            79999,
            67989,
            0,
            '["system_admin", "oms_fulfillment", "d2c_storefront", "procurement", "finance", "crm_service", "sales_distribution", "scm_ai", "marketing", "hrms"]'::jsonb,
            NULL,
            NULL,
            false,
            4
        )
    """))


def downgrade():
    """Remove seed data"""
    conn = op.get_bind()
    conn.execute(text("DELETE FROM public.tenant_subscriptions"))
    conn.execute(text("DELETE FROM public.plans"))
    conn.execute(text("DELETE FROM public.modules"))
