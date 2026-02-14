// Platform Admin Dashboard Types
// Matches actual backend responses from /api/v1/admin/ endpoints

export interface TenantListItem {
  id: string;
  name: string;
  subdomain: string;
  status: string;
  plan_name: string | null;
  total_subscriptions: number;
  monthly_cost: number;
  onboarded_at: string;
  last_active: string | null;
}

export interface TenantListResponse {
  tenants: TenantListItem[];
  total: number;
  active: number;
  pending: number;
  suspended: number;
}

export interface TenantSubscription {
  module_code: string;
  module_name: string;
  status: string;
  price_paid: number;
  starts_at: string;
  billing_cycle: string;
}

export interface TenantDetailResponse {
  id: string;
  name: string;
  subdomain: string;
  database_schema: string;
  status: string;
  plan_id: string | null;
  plan_name: string | null;
  onboarded_at: string;
  trial_ends_at: string | null;
  settings: Record<string, unknown>;
  tenant_metadata: Record<string, unknown>;
  subscriptions: TenantSubscription[];
  total_monthly_cost: number;
  total_users: number;
  storage_used_mb: number | null;
  api_calls_monthly: number | null;
}

export interface PlatformStatistics {
  total_tenants: number;
  active_tenants: number;
  pending_tenants: number;
  suspended_tenants: number;
  total_revenue_monthly: number;
  total_revenue_yearly: number;
  total_users: number;
  avg_modules_per_tenant: number;
  most_popular_modules: ModulePopularity[];
  growth_rate: number | null;
}

export interface ModulePopularity {
  code: string;
  name: string;
  subscriptions: number;
}

export interface BillingHistoryResponse {
  invoices: BillingHistoryItem[];
  total: number;
  total_revenue: number;
  pending_amount: number;
}

export interface BillingHistoryItem {
  id: string;
  tenant_id: string;
  tenant_name: string;
  invoice_number: string;
  amount: number;
  currency: string;
  status: string;
  billing_period_start: string;
  billing_period_end: string;
  created_at: string;
  paid_at: string | null;
}

export interface TenantUsersResponse {
  tenant_id: string;
  schema: string;
  user_count: number;
  users: TenantUser[];
}

export interface TenantUser {
  id: string;
  email: string;
  first_name: string;
  last_name: string;
  is_active: boolean;
  is_verified: boolean;
  created_at: string;
}

export interface PlatformUser {
  email: string;
  first_name: string;
  last_name: string;
}
