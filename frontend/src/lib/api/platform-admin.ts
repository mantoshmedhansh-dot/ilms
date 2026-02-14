import axios from 'axios';
import platformApiClient, { setPlatformTokens } from './platform-client';
import type {
  TenantListResponse,
  TenantDetailResponse,
  PlatformStatistics,
  BillingHistoryResponse,
  TenantUsersResponse,
} from '@/types/platform';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export const platformAdminApi = {
  // --- Auth ---
  login: async (email: string, password: string) => {
    // Step 1: Resolve "mantosh" tenant ID for login
    const lookupRes = await axios.get(
      `${API_BASE_URL}/api/v1/onboarding/tenant-lookup?subdomain=mantosh`
    );
    const tenantId = lookupRes.data.tenant_id;

    // Step 2: Login with tenant header
    const { data } = await axios.post(
      `${API_BASE_URL}/api/v1/auth/login`,
      { email, password },
      { headers: { 'X-Tenant-ID': tenantId, 'Content-Type': 'application/json' } }
    );

    setPlatformTokens(data.access_token, data.refresh_token);
    localStorage.setItem('platform_tenant_id', tenantId);

    return data;
  },

  // --- Statistics ---
  getStatistics: async (): Promise<PlatformStatistics> => {
    const { data } = await platformApiClient.get<PlatformStatistics>('/admin/statistics');
    return data;
  },

  // --- Tenants ---
  listTenants: async (params?: {
    page?: number;
    size?: number;
    status?: string;
    search?: string;
  }): Promise<TenantListResponse> => {
    const { data } = await platformApiClient.get<TenantListResponse>('/admin/tenants', { params });
    return data;
  },

  getTenantDetails: async (tenantId: string): Promise<TenantDetailResponse> => {
    const { data } = await platformApiClient.get<TenantDetailResponse>(`/admin/tenants/${tenantId}`);
    return data;
  },

  updateTenantStatus: async (
    tenantId: string,
    status: string,
    reason?: string
  ): Promise<{ success: boolean }> => {
    const { data } = await platformApiClient.put(`/admin/tenants/${tenantId}/status`, {
      status,
      reason,
    });
    return data;
  },

  // --- Users ---
  getTenantUsers: async (tenantId: string): Promise<TenantUsersResponse> => {
    const { data } = await platformApiClient.get<TenantUsersResponse>(
      `/admin/tenants/${tenantId}/users`
    );
    return data;
  },

  resetAdminPassword: async (
    tenantId: string,
    newPassword: string
  ): Promise<{ success: boolean }> => {
    const { data } = await platformApiClient.post(`/admin/tenants/${tenantId}/reset-password`, {
      new_password: newPassword,
    });
    return data;
  },

  // --- Billing ---
  getBillingHistory: async (params?: {
    tenant_id?: string;
    page?: number;
    size?: number;
  }): Promise<BillingHistoryResponse> => {
    const { data } = await platformApiClient.get<BillingHistoryResponse>('/admin/billing', {
      params,
    });
    return data;
  },
};
