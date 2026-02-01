# IMPLEMENTATION PLAN
## ilms.ai - Modular Multi-Tenant ERP System

**Version:** 1.0
**Date:** 2026-01-31
**Status:** APPROVED - Ready for Implementation

---

## EXECUTIVE SUMMARY

**Objective:** Transform the current monolithic ERP into a modular, multi-tenant SaaS platform with 10 independent modules that customers can subscribe to individually or in bundles.

**Timeline:** 14 weeks (3.5 months)

**Approach:** Schema-per-tenant multi-tenancy with module-based access control

**Technology Stack:**
- Backend: FastAPI + SQLAlchemy + PostgreSQL
- Frontend: Next.js 14 + TypeScript + Tailwind CSS
- Database: PostgreSQL (Supabase) with schema-per-tenant

---

## FINAL MODULE STRUCTURE

### 10 Independent Modules:

1. **OMS, WMS & FULFILLMENT** - ₹12,999/month
   - Sections: Orders (3) + Inventory (8) + WMS (9) + Logistics (10)

2. **PROCUREMENT (P2P)** - ₹6,999/month
   - Sections: Procurement (7)

3. **FINANCE & ACCOUNTING** - ₹9,999/month
   - Sections: Finance (12) + Billing (13) + Reports (14)

4. **CRM & SERVICE MANAGEMENT** - ₹6,999/month
   - Sections: CRM (16) + Service (15)

5. **MULTI-CHANNEL SALES & DISTRIBUTION** - ₹7,999/month
   - Sections: Channels (4) + Distribution (5) + Partners (6)

6. **HRMS** - ₹4,999/month
   - Sections: HR (18)

7. **D2C E-COMMERCE STOREFRONT** - ₹3,999/month
   - Sections: D2C Storefront + Catalog (19) + CMS (20)

8. **SUPPLY CHAIN & AI INSIGHTS** - ₹8,999/month
   - Sections: Intelligence (2) + Planning/S&OP (11)

9. **MARKETING & PROMOTIONS** - ₹3,999/month
   - Sections: Marketing (17)

10. **SYSTEM ADMINISTRATION** - ₹2,999/month (Base Module)
    - Sections: Dashboard (1) + Access Control (21) + Administration (22)

---

## PHASE 1: FOUNDATION (WEEKS 1-2)

### Goal: Build multi-tenant infrastructure and module configuration system

---

### 1.1 DATABASE SCHEMA DESIGN

#### A. Create Public Schema (Shared Tenant Data)

**New Tables in `public` schema:**

```sql
-- ====================
-- TENANTS TABLE
-- ====================
CREATE TABLE public.tenants (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    subdomain VARCHAR(100) UNIQUE NOT NULL,  -- customer.ilms.ai
    database_schema VARCHAR(100) NOT NULL,    -- tenant_customer
    status VARCHAR(20) DEFAULT 'active',      -- active, suspended, trial, deleted
    plan_id UUID REFERENCES public.plans(id),
    trial_ends_at TIMESTAMPTZ,
    onboarded_at TIMESTAMPTZ DEFAULT NOW(),
    settings JSONB DEFAULT '{}',              -- tenant-specific config
    metadata JSONB DEFAULT '{}',              -- additional data
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_tenants_subdomain ON public.tenants(subdomain);
CREATE INDEX idx_tenants_status ON public.tenants(status);

-- ====================
-- MODULES TABLE
-- ====================
CREATE TABLE public.modules (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    code VARCHAR(50) UNIQUE NOT NULL,         -- 'oms_fulfillment', 'finance', 'crm_service'
    name VARCHAR(100) NOT NULL,               -- 'OMS, WMS & Fulfillment'
    description TEXT,
    category VARCHAR(50),                      -- 'core', 'operations', 'finance', 'commerce', 'people', 'advanced'
    icon VARCHAR(50),                          -- Icon name for UI
    color VARCHAR(20),                         -- Color code for UI
    display_order INT,
    price_monthly NUMERIC(10,2),
    price_yearly NUMERIC(10,2),
    is_base_module BOOLEAN DEFAULT false,     -- true for System Administration
    dependencies JSONB DEFAULT '[]',           -- ['inventory', 'oms']
    sections JSONB DEFAULT '[]',               -- Dashboard section numbers [3, 8, 9, 10]
    database_tables JSONB DEFAULT '[]',        -- List of tables needed
    api_endpoints JSONB DEFAULT '[]',          -- List of API routes
    frontend_routes JSONB DEFAULT '[]',        -- List of frontend pages
    features JSONB DEFAULT '[]',               -- List of features
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_modules_code ON public.modules(code);
CREATE INDEX idx_modules_category ON public.modules(category);

-- ====================
-- PLANS TABLE
-- ====================
CREATE TABLE public.plans (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(100) NOT NULL,               -- 'Starter', 'Growth', 'Professional', 'Enterprise'
    slug VARCHAR(50) UNIQUE NOT NULL,         -- 'starter', 'growth', 'professional', 'enterprise'
    type VARCHAR(20) NOT NULL,                -- 'bundle', 'custom'
    billing_cycle VARCHAR(20),                -- 'monthly', 'yearly'
    price_inr NUMERIC(10,2),
    original_price_inr NUMERIC(10,2),         -- For showing discount
    discount_percent INT DEFAULT 0,
    included_modules JSONB DEFAULT '[]',      -- ['oms_fulfillment', 'finance', 'crm_service']
    max_users INT,
    max_transactions_monthly INT,
    features JSONB DEFAULT '[]',              -- Additional features
    is_active BOOLEAN DEFAULT true,
    is_popular BOOLEAN DEFAULT false,         -- For highlighting in pricing page
    display_order INT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_plans_slug ON public.plans(slug);
CREATE INDEX idx_plans_type ON public.plans(type);

-- ====================
-- TENANT SUBSCRIPTIONS TABLE
-- ====================
CREATE TABLE public.tenant_subscriptions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID REFERENCES public.tenants(id) ON DELETE CASCADE,
    module_id UUID REFERENCES public.modules(id),
    plan_id UUID REFERENCES public.plans(id),
    status VARCHAR(20) DEFAULT 'active',      -- active, trial, expired, suspended, cancelled
    subscription_type VARCHAR(20),            -- 'plan', 'module', 'custom'
    billing_cycle VARCHAR(20),                -- 'monthly', 'yearly'
    price_paid NUMERIC(10,2),
    starts_at TIMESTAMPTZ NOT NULL,
    expires_at TIMESTAMPTZ,
    is_trial BOOLEAN DEFAULT false,
    trial_ends_at TIMESTAMPTZ,
    auto_renew BOOLEAN DEFAULT true,
    settings JSONB DEFAULT '{}',              -- module-specific config
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(tenant_id, module_id)
);

CREATE INDEX idx_tenant_subs_tenant ON public.tenant_subscriptions(tenant_id);
CREATE INDEX idx_tenant_subs_module ON public.tenant_subscriptions(module_id);
CREATE INDEX idx_tenant_subs_status ON public.tenant_subscriptions(status);

-- ====================
-- FEATURE FLAGS TABLE
-- ====================
CREATE TABLE public.feature_flags (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID REFERENCES public.tenants(id) ON DELETE CASCADE,
    module_code VARCHAR(50) NOT NULL,
    feature_key VARCHAR(100) NOT NULL,        -- 'multi_currency', 'ml_reconciliation', 'advanced_reporting'
    is_enabled BOOLEAN DEFAULT false,
    config JSONB DEFAULT '{}',                -- feature-specific configuration
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(tenant_id, module_code, feature_key)
);

CREATE INDEX idx_feature_flags_tenant ON public.feature_flags(tenant_id);
CREATE INDEX idx_feature_flags_module ON public.feature_flags(module_code);

-- ====================
-- BILLING HISTORY TABLE
-- ====================
CREATE TABLE public.billing_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID REFERENCES public.tenants(id) ON DELETE CASCADE,
    invoice_number VARCHAR(50) UNIQUE NOT NULL,
    billing_period_start TIMESTAMPTZ NOT NULL,
    billing_period_end TIMESTAMPTZ NOT NULL,
    amount NUMERIC(10,2) NOT NULL,
    tax_amount NUMERIC(10,2) DEFAULT 0,
    total_amount NUMERIC(10,2) NOT NULL,
    status VARCHAR(20) DEFAULT 'pending',     -- pending, paid, failed, cancelled
    payment_method VARCHAR(50),               -- razorpay, bank_transfer, etc.
    payment_transaction_id VARCHAR(255),
    invoice_data JSONB DEFAULT '{}',          -- Full invoice breakdown
    paid_at TIMESTAMPTZ,
    due_date TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_billing_tenant ON public.billing_history(tenant_id);
CREATE INDEX idx_billing_status ON public.billing_history(status);
CREATE INDEX idx_billing_invoice ON public.billing_history(invoice_number);

-- ====================
-- USAGE METRICS TABLE (for analytics)
-- ====================
CREATE TABLE public.usage_metrics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID REFERENCES public.tenants(id) ON DELETE CASCADE,
    module_code VARCHAR(50),
    metric_type VARCHAR(50),                  -- 'api_calls', 'storage_gb', 'orders', 'users'
    metric_value NUMERIC(15,2),
    recorded_at TIMESTAMPTZ DEFAULT NOW(),
    metadata JSONB DEFAULT '{}'
);

CREATE INDEX idx_usage_tenant ON public.usage_metrics(tenant_id);
CREATE INDEX idx_usage_module ON public.usage_metrics(module_code);
CREATE INDEX idx_usage_recorded ON public.usage_metrics(recorded_at);
```

---

#### B. Seed Module Data

```sql
-- Insert all 10 modules
INSERT INTO public.modules (code, name, description, category, icon, color, display_order, price_monthly, price_yearly, is_base_module, dependencies, sections) VALUES

-- Module 1: OMS, WMS & Fulfillment
('oms_fulfillment', 'OMS, WMS & Fulfillment', 'Complete order management, warehouse operations, inventory tracking, and shipping', 'core', '📦', 'blue', 1, 12999, 139990, false, '[]', '[3, 8, 9, 10]'),

-- Module 2: Procurement
('procurement', 'Procurement (P2P)', 'Purchase-to-pay workflow: requisitions, purchase orders, GRN, vendor invoices, and payments', 'operations', '🛒', 'blue', 2, 6999, 75990, false, '[]', '[7]'),

-- Module 3: Finance & Accounting
('finance', 'Finance & Accounting', 'Complete accounting, GST compliance, invoicing, financial reporting, and bank reconciliation', 'finance', '💰', 'green', 3, 9999, 107990, false, '[]', '[12, 13, 14]'),

-- Module 4: CRM & Service
('crm_service', 'CRM & Service Management', 'Customer relationship management, leads, call center, service requests, AMC, and warranty', 'people', '👥', 'orange', 4, 6999, 75990, false, '[]', '[16, 15]'),

-- Module 5: Multi-Channel Sales & Distribution
('sales_distribution', 'Multi-Channel Sales & Distribution', 'Multi-channel selling (D2C, B2B, Marketplaces), dealer network, franchisees, and community partners', 'commerce', '🌐', 'purple', 5, 7999, 86390, false, '["oms_fulfillment"]', '[4, 5, 6]'),

-- Module 6: HRMS
('hrms', 'HRMS', 'Human resource management: employees, attendance, leave, payroll, and performance', 'people', '👔', 'teal', 6, 4999, 53990, false, '[]', '[18]'),

-- Module 7: D2C E-Commerce Storefront
('d2c_storefront', 'D2C E-Commerce Storefront', 'Customer-facing e-commerce website, product catalog, CMS, shopping cart, and checkout', 'commerce', '🛍️', 'purple', 7, 3999, 43190, false, '["oms_fulfillment"]', '[19, 20]'),

-- Module 8: Supply Chain & AI Insights
('scm_ai', 'Supply Chain & AI Insights', 'AI-powered demand forecasting, S&OP planning, reorder suggestions, and inventory optimization', 'advanced', '🤖', 'darkblue', 8, 8999, 97190, false, '["oms_fulfillment"]', '[2, 11]'),

-- Module 9: Marketing & Promotions
('marketing', 'Marketing & Promotions', 'Marketing campaigns, promotions, coupons, and affiliate programs', 'marketing', '📢', 'pink', 9, 3999, 43190, false, '[]', '[17]'),

-- Module 10: System Administration (Base Module)
('system_admin', 'System Administration', 'Core system functions: dashboard, user management, roles, permissions, and audit logs', 'core', '⚙️', 'gray', 10, 2999, 32390, true, '[]', '[1, 21, 22]');
```

```sql
-- Insert pricing plans
INSERT INTO public.plans (name, slug, type, billing_cycle, price_inr, original_price_inr, discount_percent, included_modules, max_users, max_transactions_monthly, is_popular, display_order) VALUES

-- Starter Bundle
('Starter', 'starter', 'bundle', 'monthly', 19999, 19999, 0,
 '["system_admin", "oms_fulfillment", "d2c_storefront"]',
 5, 1000, false, 1),

-- Growth Bundle (15% discount)
('Growth', 'growth', 'bundle', 'monthly', 39999, 46995, 15,
 '["system_admin", "oms_fulfillment", "d2c_storefront", "procurement", "finance", "crm_service"]',
 20, 5000, true, 2),

-- Professional Bundle (10% discount)
('Professional', 'professional', 'bundle', 'monthly', 59999, 66994, 10,
 '["system_admin", "oms_fulfillment", "d2c_storefront", "procurement", "finance", "crm_service", "sales_distribution", "scm_ai", "marketing"]',
 50, 20000, false, 3),

-- Enterprise Bundle
('Enterprise', 'enterprise', 'bundle', 'monthly', 79999, 67989, 0,
 '["system_admin", "oms_fulfillment", "d2c_storefront", "procurement", "finance", "crm_service", "sales_distribution", "scm_ai", "marketing", "hrms"]',
 NULL, NULL, false, 4);
```

---

### 1.2 BACKEND ARCHITECTURE CHANGES

#### A. Create Tenant Middleware

**File:** `app/middleware/tenant.py`

```python
from fastapi import Request, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_public_session
from app.models.tenant import Tenant
import logging

logger = logging.getLogger(__name__)

async def get_tenant_from_request(request: Request) -> Tenant:
    """
    Extract tenant from request (subdomain, header, or JWT token)
    """
    # Option 1: Extract from subdomain
    host = request.headers.get("host", "")
    if "." in host:
        subdomain = host.split(".")[0]
        # Check if it's a valid subdomain (not www, api, etc.)
        if subdomain not in ["www", "api", "admin"]:
            tenant = await get_tenant_by_subdomain(subdomain)
            if tenant:
                return tenant

    # Option 2: Extract from custom header (for API calls)
    tenant_id = request.headers.get("X-Tenant-ID")
    if tenant_id:
        tenant = await get_tenant_by_id(tenant_id)
        if tenant:
            return tenant

    # Option 3: Extract from JWT token (if user is logged in)
    if hasattr(request.state, "user") and request.state.user:
        tenant_id = request.state.user.get("tenant_id")
        if tenant_id:
            tenant = await get_tenant_by_id(tenant_id)
            if tenant:
                return tenant

    # No tenant found
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Tenant not found. Please check your subdomain or login credentials."
    )

async def get_tenant_by_subdomain(subdomain: str) -> Tenant:
    """Get tenant by subdomain"""
    async with get_public_session() as session:
        result = await session.execute(
            select(Tenant).where(Tenant.subdomain == subdomain, Tenant.status == 'active')
        )
        return result.scalar_one_or_none()

async def get_tenant_by_id(tenant_id: str) -> Tenant:
    """Get tenant by ID"""
    async with get_public_session() as session:
        result = await session.execute(
            select(Tenant).where(Tenant.id == tenant_id, Tenant.status == 'active')
        )
        return result.scalar_one_or_none()

async def tenant_middleware(request: Request, call_next):
    """
    Middleware to inject tenant context into request
    """
    # Skip tenant check for public routes
    public_routes = ["/health", "/docs", "/openapi.json", "/api/auth/login"]
    if request.url.path in public_routes:
        return await call_next(request)

    try:
        # Get tenant from request
        tenant = await get_tenant_from_request(request)

        # Inject tenant into request state
        request.state.tenant = tenant
        request.state.tenant_id = str(tenant.id)
        request.state.schema = tenant.database_schema

        logger.info(f"Request for tenant: {tenant.name} ({tenant.subdomain})")

        # Continue with request
        response = await call_next(request)
        return response

    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Tenant middleware error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error processing tenant context"
        )
```

---

#### B. Module Access Control Decorator

**File:** `app/core/module_decorators.py`

```python
from functools import wraps
from fastapi import HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_public_session
from app.models.tenant import TenantSubscription
from sqlalchemy import select, and_
import logging

logger = logging.getLogger(__name__)

def require_module(module_code: str):
    """
    Decorator to check if tenant has access to a specific module

    Usage:
    @router.get("/api/wms/zones")
    @require_module("oms_fulfillment")
    async def get_zones(request: Request):
        ...
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(request: Request, *args, **kwargs):
            # Get tenant from request state
            if not hasattr(request.state, "tenant"):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Tenant context not found"
                )

            tenant = request.state.tenant

            # Check if module is enabled for this tenant
            has_access = await check_module_access(tenant.id, module_code)

            if not has_access:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Module '{module_code}' is not enabled for your account. Please upgrade your subscription."
                )

            # Module access granted, proceed with request
            return await func(request, *args, **kwargs)

        return wrapper
    return decorator

async def check_module_access(tenant_id: str, module_code: str) -> bool:
    """
    Check if tenant has active subscription to a module
    """
    async with get_public_session() as session:
        # Check if tenant has active subscription for this module
        result = await session.execute(
            select(TenantSubscription)
            .join(Module)
            .where(
                and_(
                    TenantSubscription.tenant_id == tenant_id,
                    Module.code == module_code,
                    TenantSubscription.status == 'active'
                )
            )
        )
        subscription = result.scalar_one_or_none()

        # Check if subscription is valid
        if subscription:
            # Check if subscription has expired
            if subscription.expires_at and subscription.expires_at < datetime.now(timezone.utc):
                return False
            return True

        return False

async def get_tenant_enabled_modules(tenant_id: str) -> list[str]:
    """
    Get list of module codes enabled for a tenant
    """
    async with get_public_session() as session:
        result = await session.execute(
            select(Module.code)
            .join(TenantSubscription)
            .where(
                and_(
                    TenantSubscription.tenant_id == tenant_id,
                    TenantSubscription.status == 'active'
                )
            )
        )
        modules = result.scalars().all()
        return list(modules)
```

---

#### C. Dynamic Schema Routing

**File:** `app/db/session.py` (Update)

```python
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import sessionmaker
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

# Engine for public schema (tenant management)
public_engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DB_ECHO,
    pool_pre_ping=True,
    pool_size=20,
    max_overflow=40
)

PublicSessionLocal = async_sessionmaker(
    public_engine,
    class_=AsyncSession,
    expire_on_commit=False
)

async def get_public_session() -> AsyncSession:
    """Get session for public schema (tenant management)"""
    async with PublicSessionLocal() as session:
        yield session

async def get_tenant_session(schema: str) -> AsyncSession:
    """
    Get session for tenant-specific schema

    Args:
        schema: Tenant database schema name (e.g., 'tenant_customer1')

    Returns:
        AsyncSession configured for tenant schema
    """
    # Create engine for tenant schema
    tenant_engine = create_async_engine(
        settings.DATABASE_URL,
        echo=settings.DB_ECHO,
        pool_pre_ping=True,
        connect_args={"options": f"-c search_path={schema}"}
    )

    TenantSessionLocal = async_sessionmaker(
        tenant_engine,
        class_=AsyncSession,
        expire_on_commit=False
    )

    async with TenantSessionLocal() as session:
        # Verify schema is set correctly
        result = await session.execute(text("SELECT current_schema()"))
        current_schema = result.scalar()
        logger.info(f"Connected to schema: {current_schema}")

        yield session

async def get_db(request: Request):
    """
    Dependency to get database session for current tenant

    Usage in FastAPI routes:
    @router.get("/api/products")
    async def get_products(db: AsyncSession = Depends(get_db)):
        ...
    """
    # Get tenant schema from request state
    if not hasattr(request.state, "schema"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tenant schema not found in request"
        )

    schema = request.state.schema

    # Get session for tenant schema
    async for session in get_tenant_session(schema):
        yield session
```

---

#### D. Update API Endpoints with Module Decorators

**Example: `app/api/v1/endpoints/wms.py`**

```python
from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.core.module_decorators import require_module
from app.schemas.wms import ZoneCreate, ZoneResponse
from app.services import wms_service

router = APIRouter()

@router.get("/zones")
@require_module("oms_fulfillment")  # Check if tenant has OMS module
async def get_zones(
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Get all warehouse zones"""
    tenant_id = request.state.tenant_id
    zones = await wms_service.get_zones(db, tenant_id)
    return zones

@router.post("/zones")
@require_module("oms_fulfillment")
async def create_zone(
    request: Request,
    zone_data: ZoneCreate,
    db: AsyncSession = Depends(get_db)
):
    """Create a new warehouse zone"""
    tenant_id = request.state.tenant_id
    zone = await wms_service.create_zone(db, tenant_id, zone_data)
    return zone
```

**Repeat for ALL 78 API endpoint files** - add `@require_module()` decorator with appropriate module code.

---

### 1.3 FRONTEND ARCHITECTURE CHANGES

#### A. Module Configuration Hook

**File:** `frontend/src/hooks/useModules.ts`

```typescript
import { useEffect, useState } from 'react';
import { apiClient } from '@/lib/api-client';

export interface Module {
  code: string;
  name: string;
  description: string;
  icon: string;
  color: string;
  isEnabled: boolean;
  sections: number[];
  routes: string[];
}

export function useModules() {
  const [modules, setModules] = useState<Module[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function fetchModules() {
      try {
        const response = await apiClient.get('/api/tenant/modules');
        setModules(response.data.modules);
      } catch (err) {
        setError('Failed to load modules');
        console.error(err);
      } finally {
        setLoading(false);
      }
    }

    fetchModules();
  }, []);

  const isModuleEnabled = (moduleCode: string): boolean => {
    const module = modules.find(m => m.code === moduleCode);
    return module?.isEnabled || false;
  };

  const isSectionEnabled = (sectionNumber: number): boolean => {
    return modules.some(m => m.isEnabled && m.sections.includes(sectionNumber));
  };

  return {
    modules,
    loading,
    error,
    isModuleEnabled,
    isSectionEnabled
  };
}
```

---

#### B. Dynamic Sidebar Navigation

**File:** `frontend/src/components/DashboardSidebar.tsx`

```typescript
'use client';

import { useModules } from '@/hooks/useModules';
import Link from 'next/link';
import { usePathname } from 'next/navigation';

interface NavItem {
  name: string;
  href: string;
  icon: string;
  section: number;
  moduleCode: string;
}

const allNavItems: NavItem[] = [
  { name: 'Dashboard', href: '/dashboard', icon: '📊', section: 1, moduleCode: 'system_admin' },

  // Module 1: OMS, WMS & Fulfillment
  { name: 'Orders', href: '/dashboard/orders', icon: '📦', section: 3, moduleCode: 'oms_fulfillment' },
  { name: 'Inventory', href: '/dashboard/inventory', icon: '📦', section: 8, moduleCode: 'oms_fulfillment' },
  { name: 'Warehouse', href: '/dashboard/wms', icon: '🏭', section: 9, moduleCode: 'oms_fulfillment' },
  { name: 'Logistics', href: '/dashboard/logistics', icon: '🚚', section: 10, moduleCode: 'oms_fulfillment' },

  // Module 2: Procurement
  { name: 'Procurement', href: '/dashboard/procurement', icon: '🛒', section: 7, moduleCode: 'procurement' },

  // Module 3: Finance
  { name: 'Finance', href: '/dashboard/finance', icon: '💰', section: 12, moduleCode: 'finance' },
  { name: 'Billing', href: '/dashboard/billing', icon: '🧾', section: 13, moduleCode: 'finance' },
  { name: 'Reports', href: '/dashboard/reports', icon: '📊', section: 14, moduleCode: 'finance' },

  // Module 4: CRM & Service
  { name: 'CRM', href: '/dashboard/crm', icon: '👥', section: 16, moduleCode: 'crm_service' },
  { name: 'Service', href: '/dashboard/service', icon: '🔧', section: 15, moduleCode: 'crm_service' },

  // Module 5: Sales & Distribution
  { name: 'Channels', href: '/dashboard/channels', icon: '🌐', section: 4, moduleCode: 'sales_distribution' },
  { name: 'Distribution', href: '/dashboard/distribution', icon: '🤝', section: 5, moduleCode: 'sales_distribution' },
  { name: 'Partners', href: '/dashboard/partners', icon: '👥', section: 6, moduleCode: 'sales_distribution' },

  // Module 6: HRMS
  { name: 'HR', href: '/dashboard/hr', icon: '👔', section: 18, moduleCode: 'hrms' },

  // Module 7: D2C Storefront
  { name: 'Catalog', href: '/dashboard/catalog', icon: '📦', section: 19, moduleCode: 'd2c_storefront' },
  { name: 'CMS', href: '/dashboard/cms', icon: '📝', section: 20, moduleCode: 'd2c_storefront' },

  // Module 8: SCM & AI
  { name: 'Insights', href: '/dashboard/insights', icon: '🤖', section: 2, moduleCode: 'scm_ai' },
  { name: 'Planning', href: '/dashboard/snop', icon: '📈', section: 11, moduleCode: 'scm_ai' },

  // Module 9: Marketing
  { name: 'Marketing', href: '/dashboard/marketing', icon: '📢', section: 17, moduleCode: 'marketing' },

  // Module 10: System Admin
  { name: 'Access Control', href: '/dashboard/access-control', icon: '🔐', section: 21, moduleCode: 'system_admin' },
  { name: 'Settings', href: '/dashboard/settings', icon: '⚙️', section: 22, moduleCode: 'system_admin' },
];

export function DashboardSidebar() {
  const { modules, loading, isSectionEnabled } = useModules();
  const pathname = usePathname();

  if (loading) {
    return <div>Loading...</div>;
  }

  // Filter nav items based on enabled modules
  const enabledNavItems = allNavItems.filter(item => isSectionEnabled(item.section));

  return (
    <aside className="w-64 bg-gray-900 text-white min-h-screen">
      <div className="p-4">
        <h1 className="text-2xl font-bold">ilms.ai</h1>
      </div>

      <nav className="mt-8">
        {enabledNavItems.map((item) => (
          <Link
            key={item.href}
            href={item.href}
            className={`
              flex items-center px-4 py-3 hover:bg-gray-800
              ${pathname === item.href ? 'bg-gray-800 border-l-4 border-blue-500' : ''}
            `}
          >
            <span className="mr-3">{item.icon}</span>
            <span>{item.name}</span>
          </Link>
        ))}
      </nav>

      {/* Upgrade CTA if modules are disabled */}
      <div className="mt-8 p-4">
        <div className="bg-blue-900 rounded-lg p-4">
          <p className="text-sm mb-2">Want more features?</p>
          <button className="bg-blue-600 hover:bg-blue-700 px-4 py-2 rounded text-sm w-full">
            Upgrade Plan
          </button>
        </div>
      </div>
    </aside>
  );
}
```

---

#### C. Feature Gate Component

**File:** `frontend/src/components/FeatureGate.tsx`

```typescript
'use client';

import { useModules } from '@/hooks/useModules';
import { ReactNode } from 'react';

interface FeatureGateProps {
  moduleCode: string;
  children: ReactNode;
  fallback?: ReactNode;
}

export function FeatureGate({ moduleCode, children, fallback }: FeatureGateProps) {
  const { isModuleEnabled, loading } = useModules();

  if (loading) {
    return null;
  }

  if (!isModuleEnabled(moduleCode)) {
    return fallback ? <>{fallback}</> : null;
  }

  return <>{children}</>;
}

// Usage example:
// <FeatureGate moduleCode="scm_ai">
//   <AdvancedForecastingChart />
// </FeatureGate>
```

---

### 1.4 TENANT ONBOARDING API

**File:** `app/api/v1/endpoints/tenant_management.py`

```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_public_session
from app.schemas.tenant import TenantCreate, TenantResponse
from app.services.tenant_service import create_new_tenant
from app.models.tenant import Tenant, TenantSubscription, Plan
from sqlalchemy import select

router = APIRouter()

@router.post("/tenants", response_model=TenantResponse)
async def create_tenant(
    tenant_data: TenantCreate,
    db: AsyncSession = Depends(get_public_session)
):
    """
    Create a new tenant with selected plan

    Steps:
    1. Create tenant record
    2. Create database schema for tenant
    3. Copy template tables to tenant schema
    4. Create subscriptions based on plan
    5. Return tenant details
    """
    try:
        tenant = await create_new_tenant(db, tenant_data)
        return tenant
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/tenant/modules")
async def get_tenant_modules(
    request: Request,
    db: AsyncSession = Depends(get_public_session)
):
    """
    Get enabled modules for current tenant
    """
    tenant_id = request.state.tenant_id

    # Get all active subscriptions
    result = await db.execute(
        select(Module)
        .join(TenantSubscription)
        .where(
            TenantSubscription.tenant_id == tenant_id,
            TenantSubscription.status == 'active'
        )
    )
    modules = result.scalars().all()

    return {
        "modules": [
            {
                "code": m.code,
                "name": m.name,
                "description": m.description,
                "icon": m.icon,
                "color": m.color,
                "sections": m.sections,
                "isEnabled": True
            }
            for m in modules
        ]
    }
```

---

## DELIVERABLES FOR PHASE 1:

✅ Multi-tenant database schema (public schema with tenant management tables)
✅ Tenant middleware for request routing
✅ Module access control decorators
✅ Dynamic schema routing
✅ Frontend module configuration hook
✅ Dynamic sidebar navigation
✅ Feature gate component
✅ Tenant onboarding API
✅ Module seed data

**Timeline:** 2 weeks
**Developers Needed:** 2 backend + 1 frontend

---

## PHASE 2: MODULE SEPARATION (WEEKS 3-6)

[Content continues in next message due to length...]

---

---

## PHASE 2: MODULE SEPARATION & API DECORATION (WEEKS 3-6)

### Goal: Add module access control to all 78 backend endpoints

---

### 2.1 MODULE TO API ENDPOINT MAPPING

Create comprehensive mapping document showing which endpoints belong to which modules:

| Module Code | Backend APIs (add `@require_module()` decorator) |
|-------------|--------------------------------------------------|
| **oms_fulfillment** | orders.py, returns.py, picklists.py, inventory.py, stock_adjustments.py, transfers.py, warehouses.py, wms.py, shipments.py, manifests.py, transporters.py, rate_cards.py, serviceability.py, shipping.py, order_tracking.py, serialization.py |
| **procurement** | vendors.py, purchase.py, grn.py, vendor_proformas.py, vendor_invoices.py, vendor_payments.py, sales_returns.py, approvals.py |
| **finance** | accounting.py, banking.py, auto_journal.py, gst_filing.py, tds.py, fixed_assets.py, billing.py, payments.py, reports.py, channel_reports.py |
| **crm_service** | customers.py, leads.py, call_center.py, escalations.py, service_requests.py, technicians.py, installations.py, amc.py |
| **sales_distribution** | channels.py, marketplaces.py, channel_reports.py, dealers.py, franchisees.py, partners.py, commissions.py |
| **hrms** | hr.py |
| **d2c_storefront** | storefront.py, d2c_auth.py, portal.py, products.py, categories.py, brands.py, reviews.py, questions.py, abandoned_cart.py, coupons.py, cms.py |
| **scm_ai** | ai.py, insights.py, snop.py |
| **marketing** | campaigns.py, promotions.py |
| **system_admin** | auth.py, users.py, roles.py, permissions.py, access_control.py, audit_logs.py, notifications.py, company.py, credentials.py, dashboard_charts.py |

---

### 2.2 AUTOMATED ENDPOINT DECORATION SCRIPT

Create script to add `@require_module()` decorators to all endpoints:

**File:** `scripts/add_module_decorators.py`

```python
import os
import re

# Mapping of files to module codes
MODULE_MAPPING = {
    # OMS, WMS & Fulfillment
    'orders.py': 'oms_fulfillment',
    'returns.py': 'oms_fulfillment',
    'picklists.py': 'oms_fulfillment',
    'inventory.py': 'oms_fulfillment',
    'stock_adjustments.py': 'oms_fulfillment',
    'transfers.py': 'oms_fulfillment',
    'warehouses.py': 'oms_fulfillment',
    'wms.py': 'oms_fulfillment',
    'shipments.py': 'oms_fulfillment',
    'manifests.py': 'oms_fulfillment',
    'transporters.py': 'oms_fulfillment',
    'rate_cards.py': 'oms_fulfillment',
    'serviceability.py': 'oms_fulfillment',
    'shipping.py': 'oms_fulfillment',
    'order_tracking.py': 'oms_fulfillment',
    'serialization.py': 'oms_fulfillment',

    # Procurement
    'vendors.py': 'procurement',
    'purchase.py': 'procurement',
    'grn.py': 'procurement',
    'vendor_proformas.py': 'procurement',
    'vendor_invoices.py': 'procurement',
    'vendor_payments.py': 'procurement',
    'sales_returns.py': 'procurement',
    'approvals.py': 'procurement',

    # Finance & Accounting
    'accounting.py': 'finance',
    'banking.py': 'finance',
    'auto_journal.py': 'finance',
    'gst_filing.py': 'finance',
    'tds.py': 'finance',
    'fixed_assets.py': 'finance',
    'billing.py': 'finance',
    'payments.py': 'finance',
    'reports.py': 'finance',
    'channel_reports.py': 'finance',

    # CRM & Service
    'customers.py': 'crm_service',
    'leads.py': 'crm_service',
    'call_center.py': 'crm_service',
    'escalations.py': 'crm_service',
    'service_requests.py': 'crm_service',
    'technicians.py': 'crm_service',
    'installations.py': 'crm_service',
    'amc.py': 'crm_service',

    # Sales & Distribution
    'channels.py': 'sales_distribution',
    'marketplaces.py': 'sales_distribution',
    'dealers.py': 'sales_distribution',
    'franchisees.py': 'sales_distribution',
    'partners.py': 'sales_distribution',
    'commissions.py': 'sales_distribution',

    # HRMS
    'hr.py': 'hrms',

    # D2C Storefront
    'storefront.py': 'd2c_storefront',
    'd2c_auth.py': 'd2c_storefront',
    'portal.py': 'd2c_storefront',
    'products.py': 'd2c_storefront',
    'categories.py': 'd2c_storefront',
    'brands.py': 'd2c_storefront',
    'reviews.py': 'd2c_storefront',
    'questions.py': 'd2c_storefront',
    'abandoned_cart.py': 'd2c_storefront',
    'coupons.py': 'd2c_storefront',
    'cms.py': 'd2c_storefront',

    # SCM & AI
    'ai.py': 'scm_ai',
    'insights.py': 'scm_ai',
    'snop.py': 'scm_ai',

    # Marketing
    'campaigns.py': 'marketing',
    'promotions.py': 'marketing',

    # System Admin
    'auth.py': 'system_admin',
    'users.py': 'system_admin',
    'roles.py': 'system_admin',
    'permissions.py': 'system_admin',
    'access_control.py': 'system_admin',
    'audit_logs.py': 'system_admin',
    'notifications.py': 'system_admin',
    'company.py': 'system_admin',
    'credentials.py': 'system_admin',
    'dashboard_charts.py': 'system_admin',
}

def add_decorator_to_endpoints(file_path, module_code):
    """Add @require_module decorator to all route handlers in file"""
    with open(file_path, 'r') as f:
        content = f.read()

    # Check if decorator is already imported
    if 'from app.core.module_decorators import require_module' not in content:
        # Add import after existing imports
        import_line = 'from app.core.module_decorators import require_module\n'
        # Find last import statement
        import_pattern = r'(from .+ import .+\n)'
        matches = list(re.finditer(import_pattern, content))
        if matches:
            last_import_pos = matches[-1].end()
            content = content[:last_import_pos] + import_line + content[last_import_pos:]

    # Add decorator to all route handlers
    # Pattern to match @router.get/post/put/delete/patch
    route_pattern = r'(@router\.(get|post|put|delete|patch)\([^\)]+\))\n(async )?def '

    def add_decorator(match):
        decorator = match.group(1)
        async_keyword = match.group(3) or ''
        # Check if @require_module is already present
        if f'@require_module("{module_code}")' in decorator:
            return match.group(0)  # Already has decorator
        return f'{decorator}\n@require_module("{module_code}")\n{async_keyword}def '

    content = re.sub(route_pattern, add_decorator, content)

    with open(file_path, 'w') as f:
        f.write(content)

    print(f'✓ Updated {file_path}')

def main():
    endpoints_dir = 'app/api/v1/endpoints'

    for filename, module_code in MODULE_MAPPING.items():
        file_path = os.path.join(endpoints_dir, filename)
        if os.path.exists(file_path):
            add_decorator_to_endpoints(file_path, module_code)
        else:
            print(f'⚠ File not found: {file_path}')

    print('\n✅ Module decorators added to all endpoint files!')

if __name__ == '__main__':
    main()
```

Run the script:
```bash
cd "/Users/mantosh/Desktop/ilms.ai"
python scripts/add_module_decorators.py
```

---

### 2.3 UPDATE ALL 78 ENDPOINT FILES

After running the script, manually verify each file to ensure decorators are correct.

**Example:** `app/api/v1/endpoints/orders.py`

```python
from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.core.module_decorators import require_module  # ← Added
from app.schemas.order import OrderCreate, OrderResponse
from app.services import order_service

router = APIRouter()

@router.get("/orders")
@require_module("oms_fulfillment")  # ← Added
async def get_orders(
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Get all orders"""
    tenant_id = request.state.tenant_id
    orders = await order_service.get_orders(db, tenant_id)
    return orders

@router.post("/orders")
@require_module("oms_fulfillment")  # ← Added
async def create_order(
    request: Request,
    order_data: OrderCreate,
    db: AsyncSession = Depends(get_db)
):
    """Create a new order"""
    tenant_id = request.state.tenant_id
    order = await order_service.create_order(db, tenant_id, order_data)
    return order

# ... all other endpoints get the decorator
```

**Repeat for ALL 78 endpoint files.**

---

### 2.4 MODULE DEPENDENCY VALIDATION

Create service to validate module dependencies before enabling:

**File:** `app/services/module_service.py`

```python
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from app.models.tenant import Module, TenantSubscription
from app.core.exceptions import ModuleDependencyError

class ModuleService:
    @staticmethod
    async def validate_dependencies(
        db: AsyncSession,
        tenant_id: UUID,
        module_code: str
    ) -> bool:
        """
        Check if all required dependencies are enabled for tenant
        """
        # Get module
        result = await db.execute(
            select(Module).where(Module.code == module_code)
        )
        module = result.scalar_one_or_none()

        if not module:
            raise ValueError(f"Module {module_code} not found")

        # Get dependencies
        dependencies = module.dependencies or []

        if not dependencies:
            return True  # No dependencies

        # Check if all dependencies are enabled
        for dep_code in dependencies:
            result = await db.execute(
                select(TenantSubscription)
                .join(Module)
                .where(
                    and_(
                        TenantSubscription.tenant_id == tenant_id,
                        Module.code == dep_code,
                        TenantSubscription.status == 'active'
                    )
                )
            )
            if not result.scalar_one_or_none():
                raise ModuleDependencyError(
                    f"Module '{module_code}' requires '{dep_code}' to be enabled"
                )

        return True

    @staticmethod
    async def enable_module(
        db: AsyncSession,
        tenant_id: UUID,
        module_code: str
    ):
        """Enable a module for a tenant (with dependency check)"""
        # Validate dependencies first
        await ModuleService.validate_dependencies(db, tenant_id, module_code)

        # Get module
        result = await db.execute(
            select(Module).where(Module.code == module_code)
        )
        module = result.scalar_one()

        # Create subscription
        subscription = TenantSubscription(
            tenant_id=tenant_id,
            module_id=module.id,
            status='active',
            starts_at=datetime.now(timezone.utc)
        )
        db.add(subscription)
        await db.commit()

        return subscription
```

---

## DELIVERABLES FOR PHASE 2:

✅ All 78 endpoint files updated with `@require_module()` decorators
✅ Module dependency validation service
✅ Automated script for adding decorators
✅ Module enable/disable API endpoints
✅ Testing of access control on all endpoints

**Timeline:** 4 weeks
**Developers Needed:** 3 backend developers (parallel work on endpoint files)

---

## PHASE 3: FRONTEND MODULARIZATION (WEEKS 7-10)

### Goal: Dynamic frontend based on enabled modules

---

### 3.1 TENANT SETTINGS PAGE

Create UI for tenants to manage their subscriptions:

**File:** `frontend/src/app/dashboard/settings/subscriptions/page.tsx`

```typescript
'use client';

import { useState, useEffect } from 'react';
import { Card, CardHeader, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { apiClient } from '@/lib/api-client';

interface Module {
  code: string;
  name: string;
  description: string;
  icon: string;
  category: string;
  priceMonthly: number;
  isEnabled: boolean;
  isBase: boolean;
}

export default function SubscriptionsPage() {
  const [modules, setModules] = useState<Module[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function fetchModules() {
      try {
        const response = await apiClient.get('/api/tenant/available-modules');
        setModules(response.data.modules);
      } catch (error) {
        console.error('Failed to load modules:', error);
      } finally {
        setLoading(false);
      }
    }
    fetchModules();
  }, []);

  const handleToggleModule = async (moduleCode: string) => {
    try {
      await apiClient.post(`/api/tenant/modules/${moduleCode}/toggle`);
      // Refresh modules
      window.location.reload();
    } catch (error) {
      alert('Failed to toggle module');
    }
  };

  const groupedModules = modules.reduce((acc, module) => {
    if (!acc[module.category]) acc[module.category] = [];
    acc[module.category].push(module);
    return acc;
  }, {} as Record<string, Module[]>);

  return (
    <div className="p-6">
      <h1 className="text-3xl font-bold mb-6">Your Subscriptions</h1>

      {Object.entries(groupedModules).map(([category, categoryModules]) => (
        <div key={category} className="mb-8">
          <h2 className="text-xl font-semibold mb-4 capitalize">{category}</h2>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {categoryModules.map((module) => (
              <Card key={module.code} className={module.isEnabled ? 'border-blue-500' : ''}>
                <CardHeader>
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <span className="text-2xl">{module.icon}</span>
                      <h3 className="font-semibold">{module.name}</h3>
                    </div>
                    {module.isEnabled && (
                      <Badge variant="success">Active</Badge>
                    )}
                  </div>
                </CardHeader>

                <CardContent>
                  <p className="text-sm text-gray-600 mb-4">{module.description}</p>

                  <div className="flex items-center justify-between">
                    <span className="text-lg font-bold">
                      ₹{module.priceMonthly.toLocaleString()}/month
                    </span>

                    {!module.isBase && (
                      <Button
                        onClick={() => handleToggleModule(module.code)}
                        variant={module.isEnabled ? 'outline' : 'default'}
                      >
                        {module.isEnabled ? 'Disable' : 'Enable'}
                      </Button>
                    )}
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}
```

---

### 3.2 UPDATE NAVIGATION CONFIGURATION

Update navigation to check module access:

**File:** `frontend/src/config/navigation.ts`

```typescript
export interface NavItem {
  title: string;
  href?: string;
  icon?: any;
  children?: NavItem[];
  moduleCode?: string;  // ← Added
  section?: number;     // ← Added
}

export const navigation: NavItem[] = [
  {
    title: 'Dashboard',
    href: '/dashboard',
    icon: LayoutDashboard,
    moduleCode: 'system_admin',
    section: 1,
  },
  {
    title: 'Sales & Orders',
    icon: ShoppingCart,
    moduleCode: 'oms_fulfillment',
    children: [
      { title: 'Orders', href: '/dashboard/orders', section: 3 },
      { title: 'Inventory', href: '/dashboard/inventory', section: 8 },
      { title: 'Warehouse', href: '/dashboard/wms', section: 9 },
      { title: 'Logistics', href: '/dashboard/logistics', section: 10 },
    ],
  },
  {
    title: 'Procurement',
    icon: Package,
    moduleCode: 'procurement',
    children: [
      { title: 'Vendors', href: '/dashboard/procurement/vendors', section: 7 },
      { title: 'Purchase Orders', href: '/dashboard/procurement/purchase-orders', section: 7 },
      { title: 'GRN', href: '/dashboard/procurement/grn', section: 7 },
    ],
  },
  {
    title: 'Finance',
    icon: DollarSign,
    moduleCode: 'finance',
    children: [
      { title: 'Accounting', href: '/dashboard/finance/chart-of-accounts', section: 12 },
      { title: 'Invoices', href: '/dashboard/billing/invoices', section: 13 },
      { title: 'Reports', href: '/dashboard/reports/profit-loss', section: 14 },
    ],
  },
  {
    title: 'CRM & Service',
    icon: Users,
    moduleCode: 'crm_service',
    children: [
      { title: 'Customers', href: '/dashboard/crm/customers', section: 16 },
      { title: 'Leads', href: '/dashboard/crm/leads', section: 16 },
      { title: 'Service', href: '/dashboard/service/requests', section: 15 },
    ],
  },
  {
    title: 'Channels',
    icon: Globe,
    moduleCode: 'sales_distribution',
    children: [
      { title: 'Channels', href: '/dashboard/channels', section: 4 },
      { title: 'Dealers', href: '/dashboard/distribution/dealers', section: 5 },
      { title: 'Partners', href: '/dashboard/partners/list', section: 6 },
    ],
  },
  {
    title: 'HR',
    icon: Briefcase,
    moduleCode: 'hrms',
    children: [
      { title: 'Employees', href: '/dashboard/hr/employees', section: 18 },
      { title: 'Payroll', href: '/dashboard/hr/payroll', section: 18 },
    ],
  },
  {
    title: 'E-Commerce',
    icon: ShoppingBag,
    moduleCode: 'd2c_storefront',
    children: [
      { title: 'Products', href: '/dashboard/catalog', section: 19 },
      { title: 'CMS', href: '/dashboard/cms', section: 20 },
    ],
  },
  {
    title: 'Analytics',
    icon: TrendingUp,
    moduleCode: 'scm_ai',
    children: [
      { title: 'Insights', href: '/dashboard/insights', section: 2 },
      { title: 'Planning', href: '/dashboard/snop/forecasts', section: 11 },
    ],
  },
  {
    title: 'Marketing',
    icon: Megaphone,
    moduleCode: 'marketing',
    children: [
      { title: 'Campaigns', href: '/dashboard/marketing/campaigns', section: 17 },
      { title: 'Promotions', href: '/dashboard/marketing/promotions', section: 17 },
    ],
  },
  {
    title: 'Settings',
    icon: Settings,
    moduleCode: 'system_admin',
    children: [
      { title: 'Access Control', href: '/dashboard/access-control/users', section: 21 },
      { title: 'Subscriptions', href: '/dashboard/settings/subscriptions', section: 22 },
    ],
  },
];
```

---

### 3.3 PROTECTED ROUTE COMPONENT

Create component to protect routes based on module access:

**File:** `frontend/src/components/ProtectedRoute.tsx`

```typescript
'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { useModules } from '@/hooks/useModules';

interface ProtectedRouteProps {
  moduleCode: string;
  children: React.ReactNode;
}

export function ProtectedRoute({ moduleCode, children }: ProtectedRouteProps) {
  const router = useRouter();
  const { isModuleEnabled, loading } = useModules();
  const [hasAccess, setHasAccess] = useState(false);

  useEffect(() => {
    if (!loading) {
      const enabled = isModuleEnabled(moduleCode);
      setHasAccess(enabled);

      if (!enabled) {
        // Redirect to upgrade page
        router.push('/dashboard/settings/subscriptions?upgrade=' + moduleCode);
      }
    }
  }, [loading, moduleCode, isModuleEnabled, router]);

  if (loading) {
    return <div className="flex items-center justify-center min-h-screen">Loading...</div>;
  }

  if (!hasAccess) {
    return (
      <div className="flex flex-col items-center justify-center min-h-screen">
        <h1 className="text-2xl font-bold mb-4">Module Not Enabled</h1>
        <p className="text-gray-600 mb-6">This module is not included in your current subscription.</p>
        <button
          onClick={() => router.push('/dashboard/settings/subscriptions')}
          className="bg-blue-600 text-white px-6 py-2 rounded hover:bg-blue-700"
        >
          Upgrade Now
        </button>
      </div>
    );
  }

  return <>{children}</>;
}

// Usage in page:
// export default function WMSPage() {
//   return (
//     <ProtectedRoute moduleCode="oms_fulfillment">
//       <WMSContent />
//     </ProtectedRoute>
//   );
// }
```

---

## DELIVERABLES FOR PHASE 3:

✅ Subscription management UI
✅ Dynamic navigation based on modules
✅ Protected route component
✅ Feature gate component
✅ Module upgrade prompts
✅ All dashboard pages wrapped with module protection

**Timeline:** 4 weeks
**Developers Needed:** 2 frontend developers

---

## PHASE 4: DATA MIGRATION & TESTING (WEEKS 11-12)

### Goal: Migrate existing data to multi-tenant structure and test all modules

---

### 4.1 CREATE TENANT SCHEMA TEMPLATE

**Migration:** `alembic/versions/001_create_template_schema.py`

```python
"""Create template schema with all tables"""

from alembic import op
import sqlalchemy as sa

def upgrade():
    # Create template schema
    op.execute('CREATE SCHEMA IF NOT EXISTS template_tenant')

    # Copy ALL existing tables to template schema
    # (This becomes the blueprint for new tenants)

    # Example for orders table:
    op.execute('''
        CREATE TABLE template_tenant.orders AS
        SELECT * FROM public.orders WHERE 1=0
    ''')

    # Repeat for ALL 200+ tables
    # (Use a script to generate these CREATE TABLE statements)

def downgrade():
    op.execute('DROP SCHEMA IF EXISTS template_tenant CASCADE')
```

---

### 4.2 MIGRATE AQUAPURITE DATA

Create first tenant for existing Aquapurite data:

```sql
-- Create tenant record
INSERT INTO public.tenants (
    id, name, subdomain, database_schema, status, plan_id
) VALUES (
    gen_random_uuid(),
    'Aquapurite',
    'aquapurite',
    'tenant_aquapurite',
    'active',
    (SELECT id FROM public.plans WHERE slug = 'enterprise')
);

-- Create schema for Aquapurite
CREATE SCHEMA tenant_aquapurite;

-- Copy all tables from template
-- (Use pg_dump and pg_restore or script)

-- Migrate existing data from public schema to tenant schema
INSERT INTO tenant_aquapurite.products SELECT * FROM public.products;
INSERT INTO tenant_aquapurite.orders SELECT * FROM public.orders;
-- ... for all tables

-- Create subscriptions for all modules (Enterprise plan)
INSERT INTO public.tenant_subscriptions (tenant_id, module_id, status, starts_at)
SELECT
    (SELECT id FROM public.tenants WHERE subdomain = 'aquapurite'),
    m.id,
    'active',
    NOW()
FROM public.modules m;
```

---

### 4.3 TESTING CHECKLIST

Create comprehensive test plan:

#### A. Module Access Testing

| Test Case | Expected Result |
|-----------|-----------------|
| Access order page without OMS module | Redirect to upgrade page |
| Access order API without OMS module | HTTP 403 error |
| Enable OMS module | Order page becomes accessible |
| Disable OMS module | Order page becomes inaccessible |
| Access finance with only OMS enabled | Redirect to upgrade page |

#### B. Multi-Tenant Testing

| Test Case | Expected Result |
|-----------|-----------------|
| Create tenant A with Starter plan | Only Starter modules accessible |
| Create tenant B with Enterprise plan | All modules accessible |
| Tenant A tries to access Tenant B data | HTTP 404 (data isolation) |
| Switch between tenants (different subdomains) | Correct data displayed |

#### C. Dependency Testing

| Test Case | Expected Result |
|-----------|-----------------|
| Enable Sales & Distribution without OMS | Error: Dependency missing |
| Enable OMS, then Sales & Distribution | Success |
| Disable OMS while Sales & Distribution active | Error: Module in use |

#### D. Performance Testing

| Test Case | Metric |
|-----------|--------|
| API response time with module check | < 100ms overhead |
| Module list loading time | < 200ms |
| Navigation rendering with 10 modules | < 50ms |
| Database query with schema routing | < 150ms |

---

### 4.4 DEMO TENANT CREATION

Create demo tenants for each bundle:

```bash
# Create Starter bundle tenant
curl -X POST https://ilms-api.onrender.com/api/tenants \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Demo Starter Company",
    "subdomain": "demo-starter",
    "plan_slug": "starter",
    "admin_email": "admin@demo-starter.com"
  }'

# Create Growth bundle tenant
curl -X POST https://ilms-api.onrender.com/api/tenants \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Demo Growth Company",
    "subdomain": "demo-growth",
    "plan_slug": "growth",
    "admin_email": "admin@demo-growth.com"
  }'
```

---

## DELIVERABLES FOR PHASE 4:

✅ Template schema with all tables
✅ Aquapurite data migrated to tenant schema
✅ 4 demo tenants created (one per bundle)
✅ Comprehensive test suite executed
✅ Performance benchmarks documented
✅ All tests passing

**Timeline:** 2 weeks
**Developers Needed:** 2 backend + 1 QA

---

## PHASE 5: BILLING & LAUNCH (WEEKS 13-14)

### Goal: Implement subscription billing and prepare for launch

---

### 5.1 RAZORPAY SUBSCRIPTIONS INTEGRATION

**File:** `app/services/billing_service.py`

```python
import razorpay
from app.core.config import settings

razorpay_client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))

class BillingService:
    @staticmethod
    async def create_subscription(tenant_id: UUID, plan_id: UUID):
        """Create Razorpay subscription for tenant"""
        plan = await get_plan(plan_id)

        # Create Razorpay subscription
        subscription = razorpay_client.subscription.create({
            "plan_id": plan.razorpay_plan_id,
            "customer_notify": 1,
            "total_count": 12,  # 12 months
            "notes": {
                "tenant_id": str(tenant_id),
                "plan_id": str(plan_id)
            }
        })

        # Store subscription ID
        await save_subscription_id(tenant_id, subscription['id'])

        return subscription

    @staticmethod
    async def handle_payment_webhook(payload):
        """Handle Razorpay webhook for payment events"""
        event = payload['event']

        if event == 'subscription.charged':
            # Payment successful
            subscription_id = payload['payload']['subscription']['entity']['id']
            await mark_subscription_paid(subscription_id)

        elif event == 'subscription.cancelled':
            # Subscription cancelled
            subscription_id = payload['payload']['subscription']['entity']['id']
            await suspend_tenant_subscription(subscription_id)
```

---

### 5.2 SUBSCRIPTION LIFECYCLE MANAGEMENT

```python
class SubscriptionLifecycleService:
    @staticmethod
    async def check_expiring_subscriptions():
        """Check for subscriptions expiring in 7 days and send reminders"""
        expiring = await get_expiring_subscriptions(days=7)

        for subscription in expiring:
            await send_renewal_reminder(subscription.tenant_id)

    @staticmethod
    async def suspend_expired_subscriptions():
        """Suspend subscriptions that have expired"""
        expired = await get_expired_subscriptions()

        for subscription in expired:
            subscription.status = 'expired'
            await db.commit()

            # Send notification
            await notify_subscription_expired(subscription.tenant_id)

    @staticmethod
    async def auto_renew_subscriptions():
        """Auto-renew subscriptions with auto_renew=true"""
        to_renew = await get_auto_renew_subscriptions()

        for subscription in to_renew:
            if subscription.expires_at <= datetime.now(timezone.utc):
                await BillingService.charge_renewal(subscription.id)
```

Run this as a daily cron job.

---

### 5.3 CUSTOMER PORTAL

Create self-service portal for subscription management:

**File:** `frontend/src/app/dashboard/settings/billing/page.tsx`

```typescript
export default function BillingPage() {
  const [currentPlan, setCurrentPlan] = useState(null);
  const [billingHistory, setBillingHistory] = useState([]);

  return (
    <div className="p-6">
      <h1 className="text-3xl font-bold mb-6">Billing & Subscription</h1>

      {/* Current Plan */}
      <Card className="mb-6">
        <CardHeader>
          <h2 className="text-xl font-semibold">Current Plan</h2>
        </CardHeader>
        <CardContent>
          <div className="flex items-center justify-between">
            <div>
              <p className="text-2xl font-bold">{currentPlan?.name}</p>
              <p className="text-gray-600">₹{currentPlan?.price}/month</p>
              <p className="text-sm text-gray-500">
                Renews on {currentPlan?.renewsOn}
              </p>
            </div>
            <Button>Upgrade Plan</Button>
          </div>
        </CardContent>
      </Card>

      {/* Billing History */}
      <Card>
        <CardHeader>
          <h2 className="text-xl font-semibold">Billing History</h2>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Invoice Date</TableHead>
                <TableHead>Description</TableHead>
                <TableHead>Amount</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {billingHistory.map((invoice) => (
                <TableRow key={invoice.id}>
                  <TableCell>{invoice.date}</TableCell>
                  <TableCell>{invoice.description}</TableCell>
                  <TableCell>₹{invoice.amount}</TableCell>
                  <TableCell>
                    <Badge variant={invoice.status === 'paid' ? 'success' : 'warning'}>
                      {invoice.status}
                    </Badge>
                  </TableCell>
                  <TableCell>
                    <Button variant="ghost" size="sm">Download</Button>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  );
}
```

---

### 5.4 LAUNCH CHECKLIST

#### Pre-Launch Tasks

- [ ] All 10 modules tested individually
- [ ] All 4 pricing bundles tested
- [ ] Multi-tenant data isolation verified
- [ ] Performance benchmarks met
- [ ] Security audit completed
- [ ] Razorpay integration tested
- [ ] Webhook handlers tested
- [ ] Email notifications configured
- [ ] Documentation completed
- [ ] Training materials prepared

#### Launch Day Tasks

- [ ] Deploy to production
- [ ] Migrate Aquapurite to tenant schema
- [ ] Create marketing website
- [ ] Announce launch
- [ ] Monitor error logs
- [ ] Monitor performance metrics
- [ ] Support team ready

#### Post-Launch Tasks (Week 1)

- [ ] Onboard first 5 customers
- [ ] Collect feedback
- [ ] Fix critical bugs
- [ ] Optimize performance
- [ ] Update documentation

---

## DELIVERABLES FOR PHASE 5:

✅ Razorpay subscription integration
✅ Billing webhook handlers
✅ Customer billing portal
✅ Subscription lifecycle management
✅ Invoice generation
✅ Launch checklist completed
✅ Platform launched to production

**Timeline:** 2 weeks
**Developers Needed:** 1 backend + 1 frontend + 1 DevOps

---

## TOTAL PROJECT TIMELINE

| Phase | Duration | Developers | Deliverables |
|-------|----------|------------|--------------|
| **Phase 1: Foundation** | 2 weeks | 2 BE + 1 FE | Multi-tenant infrastructure |
| **Phase 2: API Decoration** | 4 weeks | 3 BE | Module access control on all endpoints |
| **Phase 3: Frontend Modularization** | 4 weeks | 2 FE | Dynamic UI based on modules |
| **Phase 4: Migration & Testing** | 2 weeks | 2 BE + 1 QA | Data migration, testing |
| **Phase 5: Billing & Launch** | 2 weeks | 1 BE + 1 FE + 1 DevOps | Billing, launch |
| **TOTAL** | **14 weeks** | **3-4 developers** | **Modular multi-tenant SaaS ERP** |

---

## BUDGET ESTIMATION

### Development Costs (14 weeks)

| Resource | Rate | Hours | Cost |
|----------|------|-------|------|
| Senior Backend Developer | ₹2000/hr | 560 hrs (2 devs × 14 weeks × 40 hrs) | ₹11,20,000 |
| Frontend Developer | ₹1500/hr | 280 hrs (1 dev × 14 weeks × 40 hrs) | ₹4,20,000 |
| QA Engineer | ₹1000/hr | 80 hrs (1 dev × 2 weeks × 40 hrs) | ₹80,000 |
| DevOps Engineer | ₹2000/hr | 80 hrs (1 dev × 2 weeks × 40 hrs) | ₹1,60,000 |
| **TOTAL DEVELOPMENT** | | | **₹17,80,000** |

### Infrastructure Costs (Monthly)

| Service | Cost/Month |
|---------|------------|
| Supabase (Pro Plan) | ₹2,000 |
| Vercel (Pro Plan) | ₹1,500 |
| Render (Pro Plan) | ₹2,500 |
| Razorpay Transaction Fees (2%) | Variable |
| **TOTAL INFRASTRUCTURE** | **₹6,000/month** |

---

## RISK MITIGATION

| Risk | Impact | Mitigation |
|------|--------|------------|
| **Performance degradation with multi-tenancy** | High | Use connection pooling, schema caching, indexed queries |
| **Data migration issues** | High | Extensive testing, rollback plan, backup strategy |
| **Module dependency conflicts** | Medium | Thorough dependency validation, clear error messages |
| **Billing integration failures** | High | Extensive webhook testing, manual fallback process |
| **Existing customers disruption** | High | Migrate Aquapurite first, test thoroughly, gradual rollout |

---

## SUCCESS METRICS

### Technical Metrics

- API response time: < 200ms (with module check)
- Module enable/disable: < 2 seconds
- Tenant onboarding: < 5 minutes
- Database query performance: < 100ms overhead
- System uptime: > 99.9%

### Business Metrics

- First paying customer: Within 2 weeks of launch
- 10 paying customers: Within 3 months
- MRR: ₹5,00,000 by Month 6
- Customer churn rate: < 10% annually
- Module adoption rate: Average 5 modules per customer

---

## POST-LAUNCH ROADMAP

### Month 1-3: Optimization
- Performance tuning based on real usage
- Fix critical bugs
- UI/UX improvements based on feedback

### Month 4-6: Feature Enhancements
- Add more granular permissions within modules
- Custom module configurations per tenant
- Advanced analytics dashboard

### Month 7-12: Expansion
- White-label option for resellers
- API marketplace for third-party integrations
- Mobile app for key modules
- International expansion (multi-currency, multi-language)

---

## CONCLUSION

This implementation plan transforms ilms.ai from a monolithic ERP into a **modular, multi-tenant SaaS platform** that can compete with UniCommerce while offering superior features.

**Key Advantages:**
1. ✅ More comprehensive than competitors (built-in finance, HRMS, D2C)
2. ✅ Flexible pricing (customers buy only what they need)
3. ✅ Scalable architecture (schema-per-tenant)
4. ✅ Market-validated module structure
5. ✅ Clear implementation roadmap (14 weeks)

**Ready to start Phase 1!** 🚀

---

**Document Status:** APPROVED FOR IMPLEMENTATION
**Next Step:** Begin Phase 1 - Foundation (Weeks 1-2)
**Point of Contact:** Development Team Lead
**Last Updated:** 2026-01-31
