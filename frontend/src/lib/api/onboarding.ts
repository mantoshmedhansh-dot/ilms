import { apiClient } from './client';

export interface SubdomainCheckRequest {
  subdomain: string;
}

export interface SubdomainCheckResponse {
  available: boolean;
  message: string;
  subdomain: string;
}

export interface Module {
  code: string;
  name: string;
  description: string;
  category: string;
  icon: string;
  price_monthly: number;
  price_yearly: number;
  features: string[];
  limits: Record<string, any>;
  is_base_module: boolean;
  is_enabled: boolean;
  sort_order: number;
}

export interface ModulesListResponse {
  modules: Module[];
  total: number;
}

export interface TenantRegistrationRequest {
  subdomain: string;
  company_name: string;
  admin_email: string;
  admin_phone: string;
  admin_password: string;
  admin_first_name: string;
  admin_last_name: string;
  selected_modules: string[];
  billing_cycle: 'monthly' | 'annual';
}

export interface TenantRegistrationResponse {
  tenant: {
    id: string;
    subdomain: string;
    company_name: string;
    schema_name: string;
    is_active: boolean;
    created_at: string;
  };
  admin: {
    id: string;
    email: string;
    first_name: string;
    last_name: string;
  };
  subscriptions: Array<{
    module_code: string;
    module_name: string;
    tier: string;
    status: string;
  }>;
  access_token: string;
  refresh_token: string;
  token_type: string;
}

export const onboardingApi = {
  checkSubdomain: async (request: SubdomainCheckRequest): Promise<SubdomainCheckResponse> => {
    const { data } = await apiClient.post<SubdomainCheckResponse>('/onboarding/check-subdomain', request);
    return data;
  },

  listModules: async (): Promise<ModulesListResponse> => {
    const { data } = await apiClient.get<ModulesListResponse>('/onboarding/modules');
    return data;
  },

  register: async (request: TenantRegistrationRequest): Promise<TenantRegistrationResponse> => {
    const { data } = await apiClient.post<TenantRegistrationResponse>('/onboarding/register', request);
    return data;
  },
};
