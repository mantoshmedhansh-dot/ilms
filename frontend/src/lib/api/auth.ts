import apiClient, { setTokens, clearTokens } from './client';
import { LoginRequest, LoginResponse, User, UserPermissions, Role } from '@/types';

export const authApi = {
  login: async (credentials: LoginRequest): Promise<LoginResponse> => {
    const { data } = await apiClient.post<LoginResponse>('/auth/login', credentials);
    setTokens(data.access_token, data.refresh_token);
    // Store tenant context from login response - critical for API calls
    if (data.tenant_id) {
      localStorage.setItem('tenant_id', data.tenant_id);
    }
    if (data.tenant_subdomain) {
      localStorage.setItem('tenant_subdomain', data.tenant_subdomain);
    }
    return data;
  },

  logout: async (): Promise<void> => {
    try {
      await apiClient.post('/auth/logout');
    } finally {
      clearTokens();
    }
  },

  getCurrentUser: async (): Promise<User> => {
    const { data } = await apiClient.get<User>('/auth/me');
    return data;
  },

  getUserPermissions: async (): Promise<UserPermissions> => {
    const { data } = await apiClient.get<{
      is_super_admin?: boolean;
      roles?: Role[];
      permissions_by_module?: Record<string, string[]>;
      total_permissions?: number;
    }>('/access-control/access/user-access-summary');
    // Transform API response to expected format
    // Combine module + action to create full permission codes like "ORDERS_VIEW"
    const permissions: Record<string, boolean> = {};
    if (data.permissions_by_module) {
      Object.entries(data.permissions_by_module).forEach(([module, perms]) => {
        perms.forEach((action) => {
          // Create full permission code: MODULE_ACTION (e.g., ORDERS_VIEW)
          const fullCode = `${module.toUpperCase()}_${action.toUpperCase()}`;
          permissions[fullCode] = true;
        });
      });
    }
    return {
      is_super_admin: data.is_super_admin || false,
      roles: data.roles,
      permissions_by_module: data.permissions_by_module,
      total_permissions: data.total_permissions,
      permissions,
    };
  },

  refreshToken: async (refreshToken: string): Promise<LoginResponse> => {
    const { data } = await apiClient.post<LoginResponse>('/auth/refresh', {
      refresh_token: refreshToken,
    });
    setTokens(data.access_token, data.refresh_token);
    // Update tenant context from refresh response
    if (data.tenant_id) {
      localStorage.setItem('tenant_id', data.tenant_id);
    }
    if (data.tenant_subdomain) {
      localStorage.setItem('tenant_subdomain', data.tenant_subdomain);
    }
    return data;
  },
};
