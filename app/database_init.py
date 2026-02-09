"""
Database initialization for multi-tenant architecture.

This module handles initialization of the PUBLIC schema only.
Tenant schemas are created dynamically during tenant onboarding (Phase 3B).
"""

from sqlalchemy import text
from app.database import async_session_factory, Base
import logging

logger = logging.getLogger(__name__)


async def init_public_schema():
    """
    Initialize PUBLIC schema tables only.

    Creates tables for:
    - Tenants management (tenants, modules, plans, subscriptions)
    - Platform-level data (billing, usage metrics, feature flags)

    Tenant-specific tables are NOT created here - they are created
    dynamically when a tenant is onboarded (see TenantSchemaService).
    """
    from app.models.tenant import (
        Tenant, ErpModule, Plan, TenantSubscription,
        FeatureFlag, BillingHistory, UsageMetric
    )

    logger.info("Initializing PUBLIC schema tables...")

    try:
        async with async_session_factory() as session:
            # Check if tables already exist
            result = await session.execute(text("""
                SELECT COUNT(*)
                FROM information_schema.tables
                WHERE table_schema = 'public'
                AND table_name IN ('tenants', 'modules', 'plans')
            """))
            existing_tables = result.scalar()

            if existing_tables >= 3:
                logger.info(f"PUBLIC schema tables already exist ({existing_tables} found). Skipping creation.")
                return

            # Create tables using SQLAlchemy metadata
            # Filter to only public schema tables
            from sqlalchemy import MetaData

            # Get all tables from Base.metadata
            public_tables = [
                table for table in Base.metadata.tables.values()
                if table.schema == 'public' or table.schema is None
            ]

            if not public_tables:
                logger.warning("No public schema tables found in metadata")
                return

            # For multi-tenant, we create public tables only
            # Tenant tables are created per-tenant during onboarding
            logger.info(f"Creating {len(public_tables)} PUBLIC schema tables...")

            # Use raw SQL to create tables (safer for production)
            await session.execute(text("""
                CREATE TABLE IF NOT EXISTS public.plans (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    name VARCHAR(100) NOT NULL,
                    slug VARCHAR(50) UNIQUE NOT NULL,
                    type VARCHAR(20) NOT NULL,
                    billing_cycle VARCHAR(20),
                    price_inr NUMERIC(10, 2),
                    original_price_inr NUMERIC(10, 2),
                    discount_percent INTEGER DEFAULT 0,
                    included_modules JSONB DEFAULT '[]'::jsonb,
                    max_users INTEGER,
                    max_transactions_monthly INTEGER,
                    features JSONB DEFAULT '[]'::jsonb,
                    is_active BOOLEAN DEFAULT TRUE,
                    is_popular BOOLEAN DEFAULT FALSE,
                    display_order INTEGER,
                    created_at TIMESTAMPTZ DEFAULT NOW(),
                    updated_at TIMESTAMPTZ DEFAULT NOW()
                )
            """))

            await session.execute(text("""
                CREATE TABLE IF NOT EXISTS public.modules (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    code VARCHAR(50) UNIQUE NOT NULL,
                    name VARCHAR(100) NOT NULL,
                    description TEXT,
                    category VARCHAR(50),
                    icon VARCHAR(50),
                    color VARCHAR(20),
                    display_order INTEGER,
                    price_monthly NUMERIC(10, 2),
                    price_yearly NUMERIC(10, 2),
                    is_base_module BOOLEAN DEFAULT FALSE,
                    dependencies JSONB DEFAULT '[]'::jsonb,
                    sections JSONB DEFAULT '[]'::jsonb,
                    database_tables JSONB DEFAULT '[]'::jsonb,
                    api_endpoints JSONB DEFAULT '[]'::jsonb,
                    frontend_routes JSONB DEFAULT '[]'::jsonb,
                    features JSONB DEFAULT '[]'::jsonb,
                    is_active BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMPTZ DEFAULT NOW(),
                    updated_at TIMESTAMPTZ DEFAULT NOW()
                )
            """))

            await session.execute(text("""
                CREATE TABLE IF NOT EXISTS public.tenants (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    name VARCHAR(255) NOT NULL,
                    subdomain VARCHAR(100) UNIQUE NOT NULL,
                    database_schema VARCHAR(100) NOT NULL,
                    status VARCHAR(20) DEFAULT 'active',
                    plan_id UUID REFERENCES public.plans(id) ON DELETE SET NULL,
                    trial_ends_at TIMESTAMPTZ,
                    onboarded_at TIMESTAMPTZ DEFAULT NOW(),
                    settings JSONB DEFAULT '{}'::jsonb,
                    tenant_metadata JSONB DEFAULT '{}'::jsonb,
                    created_at TIMESTAMPTZ DEFAULT NOW(),
                    updated_at TIMESTAMPTZ DEFAULT NOW()
                )
            """))

            await session.execute(text("""
                CREATE TABLE IF NOT EXISTS public.tenant_subscriptions (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    tenant_id UUID REFERENCES public.tenants(id) ON DELETE CASCADE,
                    module_id UUID REFERENCES public.modules(id) ON DELETE CASCADE,
                    plan_id UUID REFERENCES public.plans(id) ON DELETE SET NULL,
                    status VARCHAR(20) DEFAULT 'active',
                    subscription_type VARCHAR(20),
                    billing_cycle VARCHAR(20),
                    price_paid NUMERIC(10, 2),
                    starts_at TIMESTAMPTZ NOT NULL,
                    expires_at TIMESTAMPTZ,
                    is_trial BOOLEAN DEFAULT FALSE,
                    trial_ends_at TIMESTAMPTZ,
                    auto_renew BOOLEAN DEFAULT TRUE,
                    settings JSONB DEFAULT '{}'::jsonb,
                    created_at TIMESTAMPTZ DEFAULT NOW(),
                    updated_at TIMESTAMPTZ DEFAULT NOW()
                )
            """))

            await session.execute(text("""
                CREATE TABLE IF NOT EXISTS public.feature_flags (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    tenant_id UUID REFERENCES public.tenants(id) ON DELETE CASCADE,
                    module_code VARCHAR(50) NOT NULL,
                    feature_key VARCHAR(100) NOT NULL,
                    is_enabled BOOLEAN DEFAULT FALSE,
                    config JSONB DEFAULT '{}'::jsonb,
                    created_at TIMESTAMPTZ DEFAULT NOW(),
                    updated_at TIMESTAMPTZ DEFAULT NOW()
                )
            """))

            await session.execute(text("""
                CREATE TABLE IF NOT EXISTS public.billing_history (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    tenant_id UUID REFERENCES public.tenants(id) ON DELETE CASCADE,
                    invoice_number VARCHAR(50) UNIQUE NOT NULL,
                    billing_period_start TIMESTAMPTZ NOT NULL,
                    billing_period_end TIMESTAMPTZ NOT NULL,
                    amount NUMERIC(10, 2) NOT NULL,
                    tax_amount NUMERIC(10, 2) DEFAULT 0,
                    total_amount NUMERIC(10, 2) NOT NULL,
                    status VARCHAR(20) DEFAULT 'pending',
                    payment_method VARCHAR(50),
                    payment_transaction_id VARCHAR(255),
                    invoice_data JSONB DEFAULT '{}'::jsonb,
                    paid_at TIMESTAMPTZ,
                    due_date TIMESTAMPTZ,
                    created_at TIMESTAMPTZ DEFAULT NOW(),
                    updated_at TIMESTAMPTZ DEFAULT NOW()
                )
            """))

            await session.execute(text("""
                CREATE TABLE IF NOT EXISTS public.usage_metrics (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    tenant_id UUID REFERENCES public.tenants(id) ON DELETE CASCADE,
                    module_code VARCHAR(50),
                    metric_type VARCHAR(50),
                    metric_value NUMERIC(15, 2),
                    recorded_at TIMESTAMPTZ DEFAULT NOW(),
                    metric_metadata JSONB DEFAULT '{}'::jsonb
                )
            """))

            # Create indexes
            await session.execute(text("CREATE INDEX IF NOT EXISTS idx_tenants_subdomain ON public.tenants(subdomain)"))
            await session.execute(text("CREATE INDEX IF NOT EXISTS idx_modules_code ON public.modules(code)"))
            await session.execute(text("CREATE INDEX IF NOT EXISTS idx_tenant_subs_tenant ON public.tenant_subscriptions(tenant_id)"))
            await session.execute(text("CREATE INDEX IF NOT EXISTS idx_tenant_subs_status ON public.tenant_subscriptions(status)"))

            await session.commit()
            logger.info("PUBLIC schema tables created successfully")

    except Exception as e:
        logger.error(f"Failed to initialize PUBLIC schema: {e}")
        raise


async def seed_default_modules():
    """
    Seed default ERP modules if they don't exist.

    This runs once at startup to ensure modules are available for tenant onboarding.
    """
    logger.info("Checking for default modules...")

    from app.models.tenant import ErpModule
    from sqlalchemy import select
    import uuid

    try:
        async with async_session_factory() as session:
            # Check if modules already exist
            result = await session.execute(select(ErpModule))
            existing_modules = result.scalars().all()

            if len(existing_modules) > 0:
                logger.info(f"Modules already exist ({len(existing_modules)} found). Skipping seed.")
                return

            logger.info("Seeding default ERP modules...")

            # ILMS.AI 6-Module Structure (Phase 4)
            # Restructured from 10 modules to 6 for simpler pricing and UX
            default_modules = [
                {
                    "code": "core",
                    "name": "Core Platform",
                    "description": "User management, roles, permissions, audit logs, system administration",
                    "category": "core",
                    "price_monthly": 4999.00,
                    "is_base_module": True,
                    "display_order": 1
                },
                {
                    "code": "oms_wms",
                    "name": "OMS & WMS",
                    "description": "Order management, warehouse operations, fulfillment, procurement, inventory, logistics",
                    "category": "operations",
                    "price_monthly": 19999.00,
                    "display_order": 2
                },
                {
                    "code": "finance",
                    "name": "Finance & Compliance",
                    "description": "GL, invoicing, banking, GST compliance, tax filing, financial reports",
                    "category": "finance",
                    "price_monthly": 9999.00,
                    "display_order": 3
                },
                {
                    "code": "sales_cx",
                    "name": "Sales & Customer Experience",
                    "description": "CRM, service management, D2C storefront, marketing, campaigns, customer support",
                    "category": "sales",
                    "price_monthly": 12999.00,
                    "display_order": 4
                },
                {
                    "code": "ai_insights",
                    "name": "AI Insights",
                    "description": "Demand forecasting, S&OP, AI analytics, reorder suggestions, churn analysis",
                    "category": "analytics",
                    "price_monthly": 9999.00,
                    "display_order": 5
                },
                {
                    "code": "hrms",
                    "name": "HRMS",
                    "description": "Employee management, attendance, payroll, leave management, performance",
                    "category": "hr",
                    "price_monthly": 6999.00,
                    "display_order": 6
                }
            ]

            for module_data in default_modules:
                module = ErpModule(
                    id=uuid.uuid4(),
                    code=module_data["code"],
                    name=module_data["name"],
                    description=module_data["description"],
                    category=module_data["category"],
                    price_monthly=module_data["price_monthly"],
                    price_yearly=module_data["price_monthly"] * 12 * 0.8,  # 20% yearly discount
                    is_base_module=module_data.get("is_base_module", False),
                    display_order=module_data["display_order"],
                    is_active=True
                )
                session.add(module)

            await session.commit()
            logger.info(f"Seeded {len(default_modules)} default modules")

    except Exception as e:
        logger.error(f"Failed to seed modules: {e}")
        raise


async def startup_initialization():
    """
    Main startup initialization for multi-tenant SaaS.

    Steps:
    1. Initialize PUBLIC schema tables
    2. Seed default modules
    3. Log completion

    Note: Tenant-specific initialization happens during onboarding (Phase 3B)
    """
    logger.info("=== Multi-Tenant SaaS Startup Initialization ===")

    try:
        # Step 1: Initialize public schema
        await init_public_schema()

        # Step 2: Seed default modules
        await seed_default_modules()

        logger.info("=== Startup initialization complete ===")
        logger.info("Tenant schemas will be created during onboarding")

    except Exception as e:
        logger.error(f"Startup initialization failed: {e}")
        # Don't raise - allow server to start even if initialization fails
        logger.warning("Server will start but platform may not be fully initialized")
