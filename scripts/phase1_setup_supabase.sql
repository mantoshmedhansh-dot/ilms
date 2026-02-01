-- ============================================================================
-- PHASE 1: Multi-Tenant Schema Setup for Supabase
-- ============================================================================
-- Run this in Supabase SQL Editor to create multi-tenant infrastructure
-- Date: 2026-02-01
-- ============================================================================

-- ====================
-- 1. CREATE TENANTS TABLE
-- ====================
CREATE TABLE IF NOT EXISTS public.tenants (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    subdomain VARCHAR(100) UNIQUE NOT NULL,
    database_schema VARCHAR(100) NOT NULL,
    status VARCHAR(20) DEFAULT 'active' NOT NULL,
    plan_id UUID,
    trial_ends_at TIMESTAMPTZ,
    onboarded_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    settings JSONB DEFAULT '{}' NOT NULL,
    tenant_metadata JSONB DEFAULT '{}' NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT NOW() NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_tenants_subdomain ON public.tenants(subdomain);
CREATE INDEX IF NOT EXISTS idx_tenants_status ON public.tenants(status);

-- ====================
-- 2. CREATE MODULES TABLE
-- ====================
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
    is_base_module BOOLEAN DEFAULT false NOT NULL,
    dependencies JSONB DEFAULT '[]' NOT NULL,
    sections JSONB DEFAULT '[]' NOT NULL,
    database_tables JSONB DEFAULT '[]' NOT NULL,
    api_endpoints JSONB DEFAULT '[]' NOT NULL,
    frontend_routes JSONB DEFAULT '[]' NOT NULL,
    features JSONB DEFAULT '[]' NOT NULL,
    is_active BOOLEAN DEFAULT true NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT NOW() NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_modules_code ON public.modules(code);
CREATE INDEX IF NOT EXISTS idx_modules_category ON public.modules(category);

-- ====================
-- 3. CREATE PLANS TABLE
-- ====================
CREATE TABLE IF NOT EXISTS public.plans (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(100) NOT NULL,
    slug VARCHAR(50) UNIQUE NOT NULL,
    type VARCHAR(20) NOT NULL,
    billing_cycle VARCHAR(20),
    price_inr NUMERIC(10, 2),
    original_price_inr NUMERIC(10, 2),
    discount_percent INTEGER DEFAULT 0 NOT NULL,
    included_modules JSONB DEFAULT '[]' NOT NULL,
    max_users INTEGER,
    max_transactions_monthly INTEGER,
    features JSONB DEFAULT '[]' NOT NULL,
    is_active BOOLEAN DEFAULT true NOT NULL,
    is_popular BOOLEAN DEFAULT false NOT NULL,
    display_order INTEGER,
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT NOW() NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_plans_slug ON public.plans(slug);
CREATE INDEX IF NOT EXISTS idx_plans_type ON public.plans(type);

-- ====================
-- 4. CREATE TENANT_SUBSCRIPTIONS TABLE
-- ====================
CREATE TABLE IF NOT EXISTS public.tenant_subscriptions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES public.tenants(id) ON DELETE CASCADE,
    module_id UUID NOT NULL REFERENCES public.modules(id) ON DELETE CASCADE,
    plan_id UUID REFERENCES public.plans(id) ON DELETE SET NULL,
    status VARCHAR(20) DEFAULT 'active' NOT NULL,
    subscription_type VARCHAR(20),
    billing_cycle VARCHAR(20),
    price_paid NUMERIC(10, 2),
    starts_at TIMESTAMPTZ NOT NULL,
    expires_at TIMESTAMPTZ,
    is_trial BOOLEAN DEFAULT false NOT NULL,
    trial_ends_at TIMESTAMPTZ,
    auto_renew BOOLEAN DEFAULT true NOT NULL,
    settings JSONB DEFAULT '{}' NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT NOW() NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_tenant_subscriptions_tenant ON public.tenant_subscriptions(tenant_id);
CREATE INDEX IF NOT EXISTS idx_tenant_subscriptions_module ON public.tenant_subscriptions(module_id);
CREATE INDEX IF NOT EXISTS idx_tenant_subscriptions_status ON public.tenant_subscriptions(status);

-- ====================
-- 5. CREATE FEATURE_FLAGS TABLE
-- ====================
CREATE TABLE IF NOT EXISTS public.feature_flags (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES public.tenants(id) ON DELETE CASCADE,
    module_code VARCHAR(50) NOT NULL,
    feature_key VARCHAR(100) NOT NULL,
    is_enabled BOOLEAN DEFAULT false NOT NULL,
    config JSONB DEFAULT '{}' NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT NOW() NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_feature_flags_tenant ON public.feature_flags(tenant_id);
CREATE INDEX IF NOT EXISTS idx_feature_flags_module ON public.feature_flags(module_code);

-- ====================
-- 6. CREATE BILLING_HISTORY TABLE
-- ====================
CREATE TABLE IF NOT EXISTS public.billing_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES public.tenants(id) ON DELETE CASCADE,
    invoice_number VARCHAR(50) UNIQUE NOT NULL,
    billing_period_start TIMESTAMPTZ NOT NULL,
    billing_period_end TIMESTAMPTZ NOT NULL,
    amount NUMERIC(10, 2) NOT NULL,
    tax_amount NUMERIC(10, 2) DEFAULT 0 NOT NULL,
    total_amount NUMERIC(10, 2) NOT NULL,
    status VARCHAR(20) DEFAULT 'pending' NOT NULL,
    payment_method VARCHAR(50),
    payment_transaction_id VARCHAR(255),
    invoice_data JSONB DEFAULT '{}' NOT NULL,
    paid_at TIMESTAMPTZ,
    due_date TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT NOW() NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_billing_history_tenant ON public.billing_history(tenant_id);
CREATE INDEX IF NOT EXISTS idx_billing_history_status ON public.billing_history(status);
CREATE INDEX IF NOT EXISTS idx_billing_history_invoice ON public.billing_history(invoice_number);

-- ====================
-- 7. CREATE USAGE_METRICS TABLE
-- ====================
CREATE TABLE IF NOT EXISTS public.usage_metrics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES public.tenants(id) ON DELETE CASCADE,
    module_code VARCHAR(50),
    metric_type VARCHAR(50),
    metric_value NUMERIC(15, 2),
    recorded_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    metric_metadata JSONB DEFAULT '{}' NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_usage_metrics_tenant ON public.usage_metrics(tenant_id);
CREATE INDEX IF NOT EXISTS idx_usage_metrics_recorded ON public.usage_metrics(recorded_at);

-- ====================
-- 8. ADD FOREIGN KEY CONSTRAINT TO TENANTS
-- ====================
ALTER TABLE public.tenants
ADD CONSTRAINT fk_tenants_plan
FOREIGN KEY (plan_id) REFERENCES public.plans(id) ON DELETE SET NULL;

-- ============================================================================
-- SEED DATA: Modules and Plans
-- ============================================================================

-- ====================
-- SEED: 10 MODULES
-- ====================
INSERT INTO public.modules (code, name, description, category, icon, color, display_order, price_monthly, price_yearly, is_base_module, dependencies, sections, database_tables, api_endpoints, frontend_routes, features)
VALUES
-- Module 1: OMS, WMS & Fulfillment
('oms_fulfillment', 'OMS, WMS & Fulfillment', 'Complete order management, warehouse operations, inventory tracking, and shipping', 'core', '📦', 'blue', 1, 12999, 139990, false, '[]'::jsonb,
'[3, 8, 9, 10]'::jsonb,
'["orders", "order_items", "inventory", "stock_items", "warehouse_zones", "pick_lists", "pack_lists", "shipments", "manifests", "inventory_movements", "stock_adjustments", "stock_transfers", "inventory_reservations", "delivery_schedules"]'::jsonb,
'["orders", "inventory", "warehouses", "shipments", "manifests", "stock_adjustments", "stock_transfers"]'::jsonb,
'["/dashboard/orders", "/dashboard/inventory", "/dashboard/logistics"]'::jsonb,
'["Multi-warehouse management", "Order orchestration", "Pick-pack-ship workflow", "Real-time stock tracking", "Barcode scanning", "Batch picking", "Zone-based operations"]'::jsonb),

-- Module 2: Procurement (P2P)
('procurement', 'Procurement (P2P)', 'Purchase-to-pay: Vendors, POs, GRN, 3-way matching, and vendor payments', 'operations', '🛒', 'purple', 2, 6999, 75990, false, '[]'::jsonb,
'[14, 15, 16]'::jsonb,
'["vendors", "vendor_ledgers", "purchase_orders", "po_items", "grn", "grn_items", "vendor_invoices", "vendor_payments", "vendor_proformas"]'::jsonb,
'["vendors", "purchase", "grn", "vendor_invoices"]'::jsonb,
'["/dashboard/procurement"]'::jsonb,
'["Vendor management", "Purchase requisitions", "PO approvals", "GRN with quality check", "3-way matching", "Payment terms", "Vendor ratings"]'::jsonb),

-- Module 3: Finance & Accounting
('finance', 'Finance & Accounting', 'Complete accounting: GL, AR/AP, banking, tax compliance, and financial reporting', 'finance', '💰', 'green', 3, 9999, 107990, false, '[]'::jsonb,
'[17, 18, 19, 20]'::jsonb,
'["gl_accounts", "journal_entries", "journal_entry_lines", "accounting_periods", "billing", "banking_transactions", "payment_reconciliation", "tds_entries", "gst_returns", "e_way_bills", "e_invoices", "auto_journal_rules"]'::jsonb,
'["accounting", "billing", "banking", "tds", "gst", "e_way_bills", "e_invoices", "auto_journal"]'::jsonb,
'["/dashboard/finance"]'::jsonb,
'["Chart of accounts", "Double-entry bookkeeping", "AR/AP management", "Bank reconciliation", "GST compliance", "TDS calculation", "E-invoicing", "Financial reports"]'::jsonb),

-- Module 4: CRM & Service Management
('crm_service', 'CRM & Service Management', 'Lead management, call center, service requests, AMC, and warranty tracking', 'customer', '🎯', 'indigo', 4, 6999, 75990, false, '[]'::jsonb,
'[11, 12]'::jsonb,
'["customers", "customer_addresses", "leads", "lead_activities", "call_center_logs", "service_requests", "installations", "amc_contracts", "technicians", "service_history"]'::jsonb,
'["customers", "leads", "call_center", "service_requests", "technicians", "amc", "installations"]'::jsonb,
'["/dashboard/crm", "/dashboard/service"]'::jsonb,
'["Lead scoring", "Call center CRM", "Service ticketing", "Technician dispatch", "AMC management", "Installation tracking", "Warranty claims"]'::jsonb),

-- Module 5: Multi-Channel Sales & Distribution
('sales_distribution', 'Multi-Channel Sales & Distribution', 'Channel management, marketplace integrations, pricing, and distribution', 'sales', '🏪', 'orange', 5, 7999, 86390, false, '[]'::jsonb,
'[5, 6, 7, 13]'::jsonb,
'["channels", "channel_inventory", "channel_pricing", "channel_orders", "marketplaces", "channel_reports", "franchisees", "partners", "distributor_orders"]'::jsonb,
'["channels", "marketplaces", "channel_reports", "partners"]'::jsonb,
'["/dashboard/channels", "/dashboard/partners"]'::jsonb,
'["Multi-channel inventory", "Dynamic pricing", "Marketplace integration", "Franchise management", "Distributor portal", "Channel analytics"]'::jsonb),

-- Module 6: HRMS
('hrms', 'HRMS', 'Employee management, attendance, payroll, and leave management', 'hr', '👥', 'pink', 6, 4999, 53990, false, '[]'::jsonb,
'[21]'::jsonb,
'["employees", "attendance", "payroll", "leave_applications", "employee_documents", "performance_reviews"]'::jsonb,
'["hr"]'::jsonb,
'["/dashboard/hr"]'::jsonb,
'["Employee onboarding", "Attendance tracking", "Payroll processing", "Leave management", "Performance reviews", "Document management"]'::jsonb),

-- Module 7: D2C E-Commerce Storefront
('d2c_storefront', 'D2C E-Commerce Storefront', 'Customer-facing online store with cart, checkout, and order tracking', 'ecommerce', '🛍️', 'teal', 7, 3999, 43190, false, '["oms_fulfillment"]'::jsonb,
'[1, 2]'::jsonb,
'["cms_pages", "cms_banners", "product_reviews", "wishlists", "cart_items", "storefront_orders"]'::jsonb,
'["cms", "storefront"]'::jsonb,
'["/products", "/cart", "/checkout", "/account", "/track"]'::jsonb,
'["Product catalog", "Shopping cart", "Payment gateway", "Order tracking", "Customer reviews", "CMS for content"]'::jsonb),

-- Module 8: Supply Chain & AI Insights
('scm_ai', 'Supply Chain & AI Insights', 'Demand forecasting, S&OP, inventory optimization, and AI-powered analytics', 'analytics', '🤖', 'cyan', 8, 8999, 97190, false, '["oms_fulfillment", "procurement"]'::jsonb,
'[22]'::jsonb,
'["demand_forecasts", "snop_plans", "inventory_targets", "replenishment_suggestions", "ai_insights"]'::jsonb,
'["snop", "insights", "ai"]'::jsonb,
'["/dashboard/snop", "/dashboard/insights"]'::jsonb,
'["Demand forecasting", "S&OP planning", "Inventory optimization", "AI insights", "Predictive analytics", "What-if scenarios"]'::jsonb),

-- Module 9: Marketing & Promotions
('marketing', 'Marketing & Promotions', 'Campaigns, promotions, discounts, and customer engagement', 'marketing', '📢', 'rose', 9, 3999, 43190, false, '["crm_service"]'::jsonb,
'[]'::jsonb,
'["campaigns", "promotions", "discount_rules", "customer_segments", "email_templates"]'::jsonb,
'["campaigns", "promotions"]'::jsonb,
'["/dashboard/marketing"]'::jsonb,
'["Campaign management", "Promotion rules", "Customer segmentation", "Email marketing", "Discount coupons", "Loyalty programs"]'::jsonb),

-- Module 10: System Administration
('system_admin', 'System Administration', 'User management, roles, permissions, and system configuration', 'admin', '⚙️', 'gray', 10, 2999, 32390, true, '[]'::jsonb,
'[4]'::jsonb,
'["users", "roles", "permissions", "role_permissions", "access_control", "audit_logs", "system_settings"]'::jsonb,
'["auth", "users", "roles", "permissions", "access_control"]'::jsonb,
'["/dashboard/settings"]'::jsonb,
'["User management", "Role-based access", "Permission control", "Audit logging", "System settings", "Security"]'::jsonb)

ON CONFLICT (code) DO NOTHING;

-- ====================
-- SEED: 4 PRICING PLANS
-- ====================
INSERT INTO public.plans (name, slug, type, billing_cycle, price_inr, original_price_inr, discount_percent, included_modules, max_users, max_transactions_monthly, features, is_active, is_popular, display_order)
VALUES
-- Starter Plan
('Starter', 'starter', 'bundle', 'monthly', 19999, 23997, 17,
'["system_admin", "oms_fulfillment", "d2c_storefront"]'::jsonb,
5, 1000,
'["Basic order management", "Single warehouse", "D2C storefront", "Up to 5 users", "1,000 orders/month", "Email support"]'::jsonb,
true, false, 1),

-- Growth Plan
('Growth', 'growth', 'bundle', 'monthly', 39999, 49996, 20,
'["system_admin", "oms_fulfillment", "procurement", "crm_service", "sales_distribution", "d2c_storefront"]'::jsonb,
20, 5000,
'["Multi-warehouse support", "Procurement module", "CRM & service", "Multi-channel sales", "Up to 20 users", "5,000 orders/month", "Priority support"]'::jsonb,
true, true, 2),

-- Professional Plan
('Professional', 'professional', 'bundle', 'monthly', 59999, 79993, 25,
'["system_admin", "oms_fulfillment", "procurement", "finance", "crm_service", "sales_distribution", "hrms", "d2c_storefront", "marketing"]'::jsonb,
50, 15000,
'["Full ERP suite", "Finance & accounting", "HRMS", "Marketing automation", "Up to 50 users", "15,000 orders/month", "24/7 support", "Custom integrations"]'::jsonb,
true, false, 3),

-- Enterprise Plan
('Enterprise', 'enterprise', 'bundle', 'monthly', 79999, 109990, 27,
'["system_admin", "oms_fulfillment", "procurement", "finance", "crm_service", "sales_distribution", "hrms", "d2c_storefront", "scm_ai", "marketing"]'::jsonb,
NULL, NULL,
'["Complete platform", "AI & analytics", "Unlimited users", "Unlimited orders", "Dedicated account manager", "Custom development", "SLA guarantee", "Advanced security"]'::jsonb,
true, false, 4)

ON CONFLICT (slug) DO NOTHING;

-- ============================================================================
-- VERIFICATION QUERIES
-- ============================================================================

-- Check tables created
-- \dt public.*;

-- Check modules
-- SELECT code, name, price_monthly FROM public.modules ORDER BY display_order;

-- Check plans
-- SELECT slug, name, price_inr FROM public.plans ORDER BY display_order;

-- ============================================================================
-- SUCCESS!
-- ============================================================================
-- Phase 1 multi-tenant schema is now ready in Supabase
-- Next: Test tenant middleware and module access control
-- ============================================================================
