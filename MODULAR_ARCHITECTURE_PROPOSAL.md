# Modular ERP Architecture Proposal
## ilms.ai - Module-Based ERP System

**Date:** 2026-01-31
**Purpose:** Restructure the ERP system to enable individual module licensing and customer-specific feature enablement

---

## 1. EXECUTIVE SUMMARY

Transform the current monolithic ERP into a **modular, multi-tenant SaaS platform** where customers can subscribe to individual modules based on their business needs.

**Key Objectives:**
- Enable independent module licensing (pay-per-module)
- Support multi-tenant architecture (one system, multiple customers)
- Allow dynamic feature enablement per customer/tenant
- Maintain data isolation and security
- Support both bundled and à la carte pricing models

---

## 2. PROPOSED MODULE STRUCTURE

Based on the current codebase analysis, here are the **14 core modules** that can be independently sold:

### Module 1: D2C Storefront (E-commerce)
**Target Customers:** Companies wanting online B2C sales
**Core Features:**
- Product catalog and browsing
- Shopping cart and checkout
- Customer accounts and order history
- Payment gateway integration (Razorpay)
- Order tracking
- Product reviews and Q&A
- SEO and content management
- Abandoned cart recovery
- Partner/affiliate portal

**Database Tables:** products, categories, brands, customers, orders, order_items, abandoned_carts, product_reviews, cms_*, payments

**Backend APIs:** `/api/storefront/*`, `/api/products/*`, `/api/orders/*`, `/api/customers/*`, `/api/cms/*`

**Frontend Pages:** All storefront pages (39 pages)

---

### Module 2: Order Management System (OMS)
**Target Customers:** All customers managing orders
**Core Features:**
- Multi-channel order creation and management
- Order status tracking and workflow
- Order allocation rules engine
- Payment processing and tracking
- Invoice generation
- Returns and refund management
- Order analytics and reports

**Database Tables:** orders, order_items, order_status_history, payments, invoices, returns, return_items, allocation_rules, allocation_logs

**Backend APIs:** `/api/orders/*`, `/api/returns/*`, `/api/allocations/*`, `/api/billing/*`

**Frontend Pages:** Sales → Orders, Sales → Returns, Sales → Allocations

**Dependencies:** Requires Inventory module for stock allocation

---

### Module 3: Inventory Management
**Target Customers:** Companies managing stock across multiple locations
**Core Features:**
- Real-time stock tracking
- Multi-location inventory
- Stock movements and transfers
- Stock adjustments and audits
- Reorder point management
- Stock aging and valuation reports
- Serialization and barcode tracking

**Database Tables:** stock_items, inventory_summary, stock_movements, stock_transfers, stock_adjustments, warehouses, serialization_sequences

**Backend APIs:** `/api/inventory/*`, `/api/stock-adjustments/*`, `/api/transfers/*`, `/api/serialization/*`

**Frontend Pages:** Inventory → Stock Summary, Stock Movements, Transfers, Adjustments

**Dependencies:** Standalone (core module)

---

### Module 4: Warehouse Management System (WMS)
**Target Customers:** Companies with complex warehouse operations
**Core Features:**
- Zone, rack, and bin management
- Putaway rule engine
- Picklist generation
- Bin allocation and enquiry
- Cycle counting
- Warehouse performance analytics
- Multi-warehouse orchestration

**Database Tables:** warehouses, warehouse_zones, warehouse_bins, picklists, picklist_items, putaway_rules, warehouse_serviceability

**Backend APIs:** `/api/wms/*`, `/api/warehouses/*`, `/api/picklists/*`, `/api/zones/*`

**Frontend Pages:** Warehouse → Zones, Bins, Putaway Rules, Picklists

**Dependencies:** Requires Inventory module

---

### Module 5: Procurement (Purchase-to-Pay)
**Target Customers:** Companies managing supplier relationships and purchases
**Core Features:**
- Vendor management
- Purchase requisition workflow
- Purchase order creation and tracking
- Multi-level approval workflows
- Goods Receipt Note (GRN) processing
- 3-way matching (PO-GRN-Invoice)
- Vendor invoice processing
- Vendor payments and ledger
- Sales returns to vendors
- Proforma/quotation management

**Database Tables:** vendors, vendor_contacts, vendor_ledgers, purchase_requisitions, purchase_orders, goods_receipt_notes, grn_items, vendor_invoices, vendor_proformas, sales_return_notes, approval_requests

**Backend APIs:** `/api/vendors/*`, `/api/purchase/*`, `/api/grn/*`, `/api/vendor-invoices/*`, `/api/approvals/*`

**Frontend Pages:** Procurement → Purchase Requisitions, POs, GRN, Vendor Invoices, Vendors

**Dependencies:** Requires Inventory module

---

### Module 6: Finance & Accounting
**Target Customers:** Companies needing financial management
**Core Features:**
- Chart of accounts
- General ledger and journal entries
- Accounts Payable (AP)
- Accounts Receivable (AR)
- Bank reconciliation with ML matching
- Financial reporting (P&L, Balance Sheet, Trial Balance)
- Cost center management
- GST compliance (GSTR-1, GSTR-3B, GSTR-2A, ITC)
- TDS management and Form 16A
- E-invoicing and E-way bill
- Fixed asset management
- Multi-currency support

**Database Tables:** chart_of_accounts, general_ledgers, journal_entries, journal_entry_lines, financial_periods, cost_centers, bank_reconciliation, banking_transactions, tds_deductions, tax_invoices, e_way_bills

**Backend APIs:** `/api/accounting/*`, `/api/banking/*`, `/api/gst-filing/*`, `/api/tds/*`, `/api/fixed-assets/*`

**Frontend Pages:** Finance → all 15 sub-sections

**Dependencies:** Can work with OMS, Procurement; can be standalone

---

### Module 7: Logistics & Shipping
**Target Customers:** Companies managing shipments and deliveries
**Core Features:**
- Shipment creation and tracking
- Multi-carrier management
- Manifest generation
- Rate card management (D2C, B2B, FTL)
- Pincode serviceability matrix
- Order allocation rules
- Shipping label generation
- AWB tracking
- SLA monitoring and dashboard
- Shiprocket integration

**Database Tables:** shipments, shipment_tracking, manifests, manifest_items, transporters, transporter_serviceability, rate_cards, allocation_rules, allocation_logs

**Backend APIs:** `/api/shipments/*`, `/api/manifests/*`, `/api/transporters/*`, `/api/rate-cards/*`, `/api/shipping/*`

**Frontend Pages:** Logistics → Shipments, Manifests, Carriers, Rate Cards, Serviceability

**Dependencies:** Requires OMS module

---

### Module 8: Service Management (After-Sales)
**Target Customers:** Companies providing after-sales service and support
**Core Features:**
- Service request management
- Technician scheduling and assignment
- Installation tracking
- Warranty management
- AMC (Annual Maintenance Contract)
- Parts request tracking
- Customer satisfaction surveys
- Service SLA tracking

**Database Tables:** service_requests, technicians, installations, amc_contracts, amc_plans, warranty_claims

**Backend APIs:** `/api/service-requests/*`, `/api/technicians/*`, `/api/installations/*`, `/api/amc/*`

**Frontend Pages:** Service → Service Requests, Technicians, Installations, AMC, Warranties

**Dependencies:** Requires OMS module for order linkage

---

### Module 9: Customer Relationship Management (CRM)
**Target Customers:** Companies managing customer relationships and sales pipeline
**Core Features:**
- Customer 360-degree view
- Lead management and scoring
- Call center integration
- Escalation management
- Campaign management
- Customer segmentation
- Activity tracking
- Churn risk analysis
- Callback scheduling

**Database Tables:** customers, customer_addresses, leads, lead_activities, calls, call_dispositions, escalations, escalation_histories, campaigns, campaign_recipients

**Backend APIs:** `/api/customers/*`, `/api/leads/*`, `/api/call-center/*`, `/api/escalations/*`, `/api/campaigns/*`

**Frontend Pages:** CRM → Customers, Leads, Call Center, Escalations, Campaigns

**Dependencies:** Standalone (can integrate with OMS)

---

### Module 10: Human Resource Management System (HRMS)
**Target Customers:** Companies managing employees and payroll
**Core Features:**
- Employee master data
- Department and organizational structure
- Attendance management
- Leave management
- Payroll processing
- Salary structures
- Payslip generation
- Performance reviews
- HR reports

**Database Tables:** employees, departments, salary_structures, attendance, leave_balances, leave_requests, payroll, payslips

**Backend APIs:** `/api/hr/*`, `/api/employees/*`, `/api/attendance/*`, `/api/payroll/*`

**Frontend Pages:** HR → Employees, Attendance, Leave, Payroll, Reports

**Dependencies:** Standalone; can integrate with Finance for accounting

---

### Module 11: Multi-Channel Commerce
**Target Customers:** Companies selling through multiple channels (B2B, B2C, Marketplaces)
**Core Features:**
- Sales channel management
- Channel-specific pricing
- Channel inventory sync
- Marketplace integrations (Amazon, Flipkart)
- Channel commission tracking
- Channel P&L reporting
- Automated order sync

**Database Tables:** sales_channels, channel_pricing, channel_inventory, channel_orders, channel_commissions, commissions_plans, commissions_transactions

**Backend APIs:** `/api/channels/*`, `/api/marketplaces/*`, `/api/channel-reports/*`, `/api/commissions/*`

**Frontend Pages:** Sales → Channels, Marketplace Integration, Channel Reports

**Dependencies:** Requires OMS and Inventory modules

---

### Module 12: Distribution Management
**Target Customers:** Companies managing dealer/franchisee networks
**Core Features:**
- Dealer management
- Dealer pricing and tiers
- Dealer credit management
- Franchisee network
- Franchisee contracts and territories
- Dealer schemes and incentives
- Target tracking
- Community partner portal (Meesho-style)
- Partner KYC and commission

**Database Tables:** dealers, dealer_pricing, dealer_tier_pricing, dealer_credit_ledgers, dealer_targets, dealer_schemes, franchisees, franchisee_contracts, franchisee_territories, community_partners, partner_commissions

**Backend APIs:** `/api/dealers/*`, `/api/franchisees/*`, `/api/partners/*`, `/api/commissions/*`

**Frontend Pages:** Sales → Dealers, Franchisees, Community Partners

**Dependencies:** Requires OMS module

---

### Module 13: Analytics & AI
**Target Customers:** Companies wanting advanced insights and forecasting
**Core Features:**
- Demand forecasting (ML-based)
- Sales & Operations Planning (S&OP)
- Scenario planning
- Reorder point suggestions
- Slow-moving stock detection
- Churn risk analysis
- Bank reconciliation with ML matching
- Custom reports and dashboards
- Predictive analytics

**Database Tables:** demand_forecasts, forecast_adjustments, supply_plans, snop_scenarios, external_factors, inventory_optimizations

**Backend APIs:** `/api/ai/*`, `/api/insights/*`, `/api/snop/*`, `/api/forecasting/*`

**Frontend Pages:** Intelligence → AI Hub, Forecasting, S&OP, Insights

**Dependencies:** Requires Inventory and OMS modules for data

---

### Module 14: Content Management System (CMS)
**Target Customers:** Companies managing website content
**Core Features:**
- Homepage banner management
- Page builder with versioning
- SEO configuration
- Navigation and mega menu
- Testimonials and reviews
- FAQ management
- Announcement bars
- Video guides
- Demo booking forms

**Database Tables:** cms_banners, cms_pages, cms_page_versions, cms_seo, cms_announcements, cms_testimonials, cms_features, demo_bookings, video_guides

**Backend APIs:** `/api/cms/*`

**Frontend Pages:** Content → All CMS sections (11 sub-sections)

**Dependencies:** Typically used with D2C Storefront

---

## 3. TECHNICAL ARCHITECTURE

### A. Multi-Tenant Database Strategy

**Option 1: Schema-per-Tenant (Recommended for SaaS)**
```
Database: ilms_erp
├── Schema: public (shared)
│   ├── tenants (company/organization master)
│   ├── tenant_subscriptions (module subscriptions)
│   ├── modules (module definitions)
│   ├── users (global users)
│   └── plans (pricing plans)
├── Schema: tenant_001 (Customer 1)
│   ├── All module tables
│   └── Tenant-specific data
├── Schema: tenant_002 (Customer 2)
│   ├── Only subscribed module tables
│   └── Tenant-specific data
```

**Benefits:**
- Strong data isolation
- Easy backup/restore per tenant
- Performance isolation
- Schema-level security
- Can create tables only for subscribed modules

**Option 2: Row-Level Security (RLS) with Single Schema**
```
Database: ilms_erp
├── All tables have tenant_id column
├── PostgreSQL RLS policies enforce isolation
└── Indexed on tenant_id for performance
```

**Benefits:**
- Simpler deployment
- Shared database resources
- Easier cross-tenant analytics
- Lower maintenance overhead

**Recommendation:** Start with **Option 1 (Schema-per-Tenant)** for better isolation and scalability.

---

### B. Module Configuration Schema

**New Tables in Public Schema:**

#### 1. `tenants` (Company/Organization Master)
```sql
CREATE TABLE public.tenants (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    subdomain VARCHAR(100) UNIQUE NOT NULL, -- customer.ilms.ai
    database_schema VARCHAR(100) NOT NULL,   -- tenant_001
    status VARCHAR(20) DEFAULT 'active',     -- active, suspended, deleted
    onboarded_at TIMESTAMPTZ DEFAULT NOW(),
    settings JSONB,                          -- tenant-specific config
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

#### 2. `modules` (Module Definitions)
```sql
CREATE TABLE public.modules (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    code VARCHAR(50) UNIQUE NOT NULL,        -- 'oms', 'wms', 'finance'
    name VARCHAR(100) NOT NULL,              -- 'Order Management'
    description TEXT,
    category VARCHAR(50),                     -- 'core', 'addon', 'premium'
    dependencies JSONB,                       -- ['inventory', 'oms']
    database_tables JSONB,                    -- List of tables needed
    api_endpoints JSONB,                      -- List of API routes
    frontend_routes JSONB,                    -- List of frontend pages
    is_active BOOLEAN DEFAULT true,
    display_order INT
);
```

#### 3. `plans` (Pricing Plans)
```sql
CREATE TABLE public.plans (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(100) NOT NULL,              -- 'Starter', 'Professional', 'Enterprise'
    type VARCHAR(20) NOT NULL,               -- 'bundle', 'module', 'custom'
    billing_cycle VARCHAR(20),               -- 'monthly', 'yearly'
    price_inr NUMERIC(10,2),
    included_modules JSONB,                   -- ['oms', 'inventory', 'crm']
    max_users INT,
    max_transactions INT,
    is_active BOOLEAN DEFAULT true
);
```

#### 4. `tenant_subscriptions` (Module Subscriptions)
```sql
CREATE TABLE public.tenant_subscriptions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID REFERENCES public.tenants(id),
    module_id UUID REFERENCES public.modules(id),
    plan_id UUID REFERENCES public.plans(id),
    status VARCHAR(20) DEFAULT 'active',     -- active, trial, expired, suspended
    starts_at TIMESTAMPTZ NOT NULL,
    expires_at TIMESTAMPTZ,
    is_trial BOOLEAN DEFAULT false,
    trial_ends_at TIMESTAMPTZ,
    settings JSONB,                          -- module-specific config
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(tenant_id, module_id)
);
```

#### 5. `feature_flags` (Granular Feature Control)
```sql
CREATE TABLE public.feature_flags (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID REFERENCES public.tenants(id),
    module_code VARCHAR(50) NOT NULL,
    feature_key VARCHAR(100) NOT NULL,       -- 'multi_currency', 'ml_reconciliation'
    is_enabled BOOLEAN DEFAULT false,
    config JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(tenant_id, module_code, feature_key)
);
```

---

### C. Backend Architecture Changes

#### 1. Tenant Context Middleware
```python
# app/middleware/tenant.py
from fastapi import Request, HTTPException
from app.db.tenant_manager import get_tenant_by_subdomain

async def tenant_middleware(request: Request, call_next):
    """Extract tenant from subdomain or header"""
    host = request.headers.get("host", "")
    subdomain = host.split(".")[0] if "." in host else None

    # Alternative: JWT token contains tenant_id
    tenant_id = request.state.user.get("tenant_id") if hasattr(request.state, "user") else None

    tenant = await get_tenant_by_subdomain(subdomain) or await get_tenant_by_id(tenant_id)

    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    request.state.tenant = tenant
    request.state.schema = tenant.database_schema

    response = await call_next(request)
    return response
```

#### 2. Dynamic Schema Routing
```python
# app/db/session.py
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

def get_tenant_session(schema: str) -> Session:
    """Create session with tenant-specific schema"""
    engine = create_engine(DATABASE_URL)
    connection = engine.connect()
    connection.execute(f"SET search_path TO {schema}")
    return Session(bind=connection)
```

#### 3. Module Access Control Decorator
```python
# app/core/decorators.py
from functools import wraps
from fastapi import HTTPException, Request

def require_module(module_code: str):
    """Check if tenant has access to module"""
    def decorator(func):
        @wraps(func)
        async def wrapper(request: Request, *args, **kwargs):
            tenant = request.state.tenant

            # Check subscription
            subscription = await check_tenant_subscription(tenant.id, module_code)

            if not subscription or subscription.status != 'active':
                raise HTTPException(
                    status_code=403,
                    detail=f"Module '{module_code}' not enabled for your account"
                )

            return await func(request, *args, **kwargs)
        return wrapper
    return decorator

# Usage:
@router.post("/api/wms/zones")
@require_module("wms")
async def create_zone(request: Request, zone_data: ZoneCreate):
    ...
```

#### 4. Conditional API Route Registration
```python
# app/main.py
from app.core.config import settings
from app.api.router_factory import register_module_routes

app = FastAPI()

# Register routes based on enabled modules
for module in settings.ENABLED_MODULES:
    register_module_routes(app, module)

# Example: router_factory.py
def register_module_routes(app: FastAPI, module_code: str):
    if module_code == "oms":
        from app.api.endpoints import orders, returns
        app.include_router(orders.router, prefix="/api/orders", tags=["Orders"])
        app.include_router(returns.router, prefix="/api/returns", tags=["Returns"])
    elif module_code == "wms":
        from app.api.endpoints import wms, picklists
        app.include_router(wms.router, prefix="/api/wms", tags=["WMS"])
        app.include_router(picklists.router, prefix="/api/picklists", tags=["Picklists"])
    # ... etc
```

---

### D. Frontend Architecture Changes

#### 1. Module-Based Routing
```typescript
// frontend/lib/moduleConfig.ts
export interface Module {
  code: string;
  name: string;
  icon: string;
  routes: Route[];
  isEnabled: boolean;
}

export const getEnabledModules = async (): Promise<Module[]> => {
  const response = await fetch('/api/tenant/modules');
  const data = await response.json();
  return data.modules;
};

// frontend/app/dashboard/layout.tsx
import { getEnabledModules } from '@/lib/moduleConfig';

export default async function DashboardLayout({ children }) {
  const enabledModules = await getEnabledModules();

  return (
    <div className="flex">
      <Sidebar modules={enabledModules} />
      <main>{children}</main>
    </div>
  );
}
```

#### 2. Dynamic Navigation Menu
```typescript
// frontend/components/Sidebar.tsx
import { Module } from '@/lib/moduleConfig';

export function Sidebar({ modules }: { modules: Module[] }) {
  return (
    <nav>
      {modules.map(module => (
        <div key={module.code}>
          <h3>{module.name}</h3>
          <ul>
            {module.routes.map(route => (
              <li key={route.path}>
                <Link href={route.path}>{route.label}</Link>
              </li>
            ))}
          </ul>
        </div>
      ))}
    </nav>
  );
}
```

#### 3. Feature Flag Component
```typescript
// frontend/components/FeatureGate.tsx
import { useFeatureFlag } from '@/hooks/useFeatureFlag';

export function FeatureGate({
  module,
  feature,
  children
}: {
  module: string;
  feature: string;
  children: React.ReactNode
}) {
  const isEnabled = useFeatureFlag(module, feature);

  if (!isEnabled) return null;

  return <>{children}</>;
}

// Usage:
<FeatureGate module="finance" feature="multi_currency">
  <CurrencySelector />
</FeatureGate>
```

---

## 4. MODULE DEPENDENCY MANAGEMENT

### Dependency Graph
```
D2C Storefront → OMS → Inventory
                 ↓
             Logistics → Inventory

WMS → Inventory

Procurement → Inventory
          ↓
      Finance (AP)

OMS → Finance (AR)
    → Service Management
    → CRM

Multi-Channel → OMS → Inventory

Distribution → OMS

Analytics → OMS, Inventory

HRMS → Finance (Payroll accounting)
```

### Dependency Resolution Logic
```python
# app/services/module_manager.py
def get_required_modules(module_code: str) -> List[str]:
    """Get all dependencies for a module"""
    dependencies = {
        "d2c": ["oms", "inventory", "cms"],
        "oms": ["inventory"],
        "wms": ["inventory"],
        "logistics": ["oms", "inventory"],
        "procurement": ["inventory"],
        "multi_channel": ["oms", "inventory"],
        "distribution": ["oms"],
        "service": ["oms"],
        "analytics": ["oms", "inventory"],
    }
    return dependencies.get(module_code, [])

def validate_module_subscription(tenant_id: UUID, module_code: str) -> bool:
    """Check if all dependencies are met"""
    required = get_required_modules(module_code)
    active_modules = get_tenant_active_modules(tenant_id)

    return all(dep in active_modules for dep in required)
```

---

## 5. PRICING MODELS

### A. Bundled Plans
**Starter Plan** - ₹9,999/month
- OMS + Inventory + CRM + Finance (Basic)
- Up to 5 users
- 1000 orders/month

**Professional Plan** - ₹24,999/month
- Everything in Starter
- WMS + Procurement + Logistics + Service
- Up to 20 users
- 5000 orders/month

**Enterprise Plan** - Custom pricing
- All modules
- Unlimited users
- Unlimited transactions
- Dedicated support

### B. À la Carte Pricing
- **Core Modules** (Required for most operations)
  - Inventory: ₹2,999/month
  - OMS: ₹3,999/month

- **Operations Modules**
  - WMS: ₹4,999/month
  - Procurement: ₹4,999/month
  - Logistics: ₹3,999/month

- **Financial Modules**
  - Finance & Accounting: ₹6,999/month
  - Multi-Channel Commerce: ₹5,999/month

- **Customer Modules**
  - CRM: ₹3,999/month
  - Service Management: ₹3,999/month
  - D2C Storefront: ₹4,999/month

- **Advanced Modules**
  - Analytics & AI: ₹7,999/month
  - Distribution Management: ₹5,999/month
  - HRMS: ₹4,999/month
  - CMS: ₹1,999/month

### C. Usage-Based Pricing (Optional)
- Per order: ₹2-5
- Per transaction: ₹1-3
- Per user: ₹499/month
- Storage: ₹99/GB/month

---

## 6. IMPLEMENTATION PHASES

### Phase 1: Foundation (Weeks 1-2)
1. Create multi-tenant schema in public database
2. Implement tenant context middleware
3. Add module configuration tables
4. Create tenant onboarding flow
5. Build subscription management admin panel

**Deliverables:**
- Tenant management system
- Module subscription tracking
- Basic access control

---

### Phase 2: Module Separation (Weeks 3-6)
1. Refactor backend APIs with `@require_module` decorators
2. Organize routes by module
3. Create module-specific database migration scripts
4. Implement dynamic route registration
5. Add module dependency validation

**Deliverables:**
- Modular API structure
- Module access control working
- Dependency resolution

---

### Phase 3: Frontend Modularization (Weeks 7-9)
1. Implement dynamic navigation based on enabled modules
2. Create FeatureGate component for feature flags
3. Build tenant settings UI for module management
4. Add subscription status indicators
5. Create module marketplace/store

**Deliverables:**
- Dynamic dashboard navigation
- Module enable/disable functionality
- Tenant self-service portal

---

### Phase 4: Data Migration & Testing (Weeks 10-11)
1. Migrate Aquapurite data to tenant_001 schema
2. Create demo tenants with different module combinations
3. End-to-end testing of all modules
4. Performance testing with multiple tenants
5. Security audit

**Deliverables:**
- Migration scripts
- Test coverage for all modules
- Performance benchmarks

---

### Phase 5: Billing & Launch (Weeks 12-13)
1. Integrate payment gateway (Razorpay Subscriptions)
2. Implement automated subscription renewal
3. Add invoice generation
4. Create customer portal for subscription management
5. Documentation and onboarding materials

**Deliverables:**
- Billing system
- Customer portal
- Launch-ready platform

---

## 7. DATABASE MIGRATION STRATEGY

### Step 1: Create Tenant Schema Template
```sql
-- Create template schema with all tables
CREATE SCHEMA template_tenant;

-- Copy all existing tables to template
-- (This becomes the blueprint for new tenants)

-- Function to create new tenant
CREATE OR REPLACE FUNCTION create_tenant_schema(tenant_schema_name TEXT)
RETURNS VOID AS $$
BEGIN
    -- Clone template schema
    EXECUTE format('CREATE SCHEMA %I', tenant_schema_name);

    -- Copy all tables from template
    -- (This can be automated with pg_dump/restore)
END;
$$ LANGUAGE plpgsql;
```

### Step 2: Migrate Current Data
```sql
-- Create first tenant for Aquapurite
SELECT create_tenant_schema('tenant_aquapurite');

-- Migrate existing data
INSERT INTO tenant_aquapurite.*
SELECT * FROM public.*;

-- Update foreign keys to use tenant schema
```

### Step 3: Module-Specific Table Creation
```python
# When tenant subscribes to a module
async def enable_module_for_tenant(tenant_id: UUID, module_code: str):
    tenant = await get_tenant(tenant_id)
    module = await get_module(module_code)

    # Create tables for this module
    for table_sql in module.database_tables:
        await execute_sql(tenant.database_schema, table_sql)

    # Mark subscription as active
    await create_subscription(tenant_id, module.id, status='active')
```

---

## 8. SECURITY CONSIDERATIONS

### A. Data Isolation
- ✅ Schema-level separation prevents cross-tenant data access
- ✅ Row-level security as fallback
- ✅ Encrypted credentials per tenant

### B. API Security
- ✅ JWT tokens include tenant_id
- ✅ All API calls validate tenant context
- ✅ Module access checked on every endpoint

### C. Database Security
- ✅ Connection pooling per schema
- ✅ Read-only replicas for reporting
- ✅ Automated backups per tenant schema

### D. Audit Logging
- ✅ Track all module access attempts
- ✅ Log subscription changes
- ✅ Monitor API usage per tenant

---

## 9. MONITORING & ANALYTICS

### Tenant-Level Metrics
- Module usage statistics
- API call volume per module
- Storage usage per tenant
- Transaction counts
- User activity

### Business Metrics
- MRR (Monthly Recurring Revenue) per module
- Churn rate per module
- Most popular module combinations
- Upgrade/downgrade patterns
- Trial conversion rates

---

## 10. ADMIN SUPER PANEL

Create an admin dashboard for managing the entire SaaS platform:

### Features:
1. **Tenant Management**
   - Create/edit/delete tenants
   - View tenant details and usage
   - Manage subscriptions

2. **Module Management**
   - Enable/disable modules globally
   - Update module definitions
   - Manage dependencies

3. **Billing Management**
   - View revenue reports
   - Manage pricing plans
   - Handle subscription issues

4. **System Health**
   - Monitor API performance
   - Database connection pools
   - Error logs and alerts

5. **Usage Analytics**
   - Tenant activity dashboards
   - Module adoption rates
   - Feature usage heatmaps

---

## 11. BENEFITS OF THIS ARCHITECTURE

### For Your Business:
✅ **Flexible Pricing** - Sell modules independently or bundled
✅ **Scalable Revenue** - Upsell modules to existing customers
✅ **Faster Sales Cycles** - Customers buy only what they need
✅ **Competitive Advantage** - Pay-per-module model is attractive
✅ **Resource Efficiency** - Tenants share infrastructure

### For Customers:
✅ **Lower Entry Cost** - Start small, scale up
✅ **No Feature Bloat** - Only pay for what they use
✅ **Faster Onboarding** - Less complexity initially
✅ **Easy Upgrades** - Add modules as business grows
✅ **Data Security** - Tenant isolation ensures privacy

---

## 12. EXAMPLE CUSTOMER SCENARIOS

### Scenario 1: Small Manufacturer
**Needs:** Inventory + Procurement + Finance (Basic)
**Monthly Cost:** ₹9,999
**Modules Enabled:** Inventory, Procurement, Finance (without GST filing)

### Scenario 2: D2C Brand
**Needs:** D2C Storefront + OMS + Inventory + Logistics + CRM
**Monthly Cost:** ₹19,995
**Modules Enabled:** D2C, OMS, Inventory, Logistics, CRM

### Scenario 3: Distributor
**Needs:** OMS + Inventory + WMS + Distribution + Logistics
**Monthly Cost:** ₹22,995
**Modules Enabled:** OMS, Inventory, WMS, Distribution, Logistics

### Scenario 4: Enterprise with All Modules
**Needs:** Everything
**Monthly Cost:** Custom (₹50,000+)
**Modules Enabled:** All 14 modules

---

## 13. MIGRATION CHECKLIST

- [ ] Create multi-tenant schema structure
- [ ] Implement tenant context middleware
- [ ] Add module configuration tables
- [ ] Refactor backend with module decorators
- [ ] Update database models with schema routing
- [ ] Create dynamic route registration
- [ ] Build frontend module configuration
- [ ] Implement dynamic navigation
- [ ] Create FeatureGate components
- [ ] Migrate existing Aquapurite data to tenant schema
- [ ] Build tenant onboarding flow
- [ ] Create admin super panel
- [ ] Integrate billing system
- [ ] Add subscription management
- [ ] Set up automated backups per tenant
- [ ] Performance testing with multiple tenants
- [ ] Security audit
- [ ] Documentation
- [ ] Launch!

---

## 14. NEXT STEPS

1. **Review and Approve** this architecture proposal
2. **Prioritize Modules** - Which modules are most important for first customers?
3. **Set Timeline** - Confirm implementation phases
4. **Allocate Resources** - Development team assignments
5. **Create Detailed Technical Specs** - Deep dive into each module
6. **Begin Phase 1** - Foundation and multi-tenant setup

---

## 15. QUESTIONS FOR DISCUSSION

1. Do you want schema-per-tenant or RLS approach?
2. Should we support self-service tenant onboarding or sales-assisted only?
3. What should the trial period be? (14 days, 30 days?)
4. Should modules have tiered features (Basic, Pro, Enterprise within each module)?
5. Do you want to white-label the platform for resellers?
6. Should we support API access for customers to build custom integrations?
7. What's the minimum viable module set for launch?

---

**Prepared by:** Claude (AI Assistant)
**For:** ilms.ai ERP Modularization Project
**Status:** Awaiting Approval
