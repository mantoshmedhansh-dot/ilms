import axios, { AxiosInstance } from 'axios';
import {
  usePartnerStore,
  PartnerProfile,
  PartnerDashboardStats,
  PartnerCommission,
  PartnerPayout,
} from './partner-store';
import { StorefrontProduct, PaginatedResponse } from '@/types/storefront';

// Create axios instance for partner API
const partnerClient: AxiosInstance = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000',
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Add auth token to requests
partnerClient.interceptors.request.use((config) => {
  const token = usePartnerStore.getState().accessToken;
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Handle token refresh on 401
partnerClient.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;

    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;

      const refreshToken = usePartnerStore.getState().refreshToken;
      if (refreshToken) {
        try {
          const { data } = await axios.post(
            `${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/api/v1/partners/auth/refresh`,
            { refresh_token: refreshToken }
          );

          usePartnerStore.getState().setTokens(data.access_token);
          originalRequest.headers.Authorization = `Bearer ${data.access_token}`;
          return partnerClient(originalRequest);
        } catch (refreshError) {
          usePartnerStore.getState().logout();
          if (typeof window !== 'undefined') {
            window.location.href = '/partner/login';
          }
          return Promise.reject(refreshError);
        }
      }

      usePartnerStore.getState().logout();
      if (typeof window !== 'undefined') {
        window.location.href = '/partner/login';
      }
    }

    return Promise.reject(error);
  }
);

// API paths
const PARTNERS_PATH = '/api/v1/partners';

// Authentication API
export interface SendOTPRequest {
  phone: string;
}

export interface VerifyOTPRequest {
  phone: string;
  otp: string;
}

export interface PartnerRegistrationRequest {
  full_name: string;
  phone: string;
  email?: string;
  city?: string;
  pincode?: string;
  referred_by_code?: string; // Code of the referring partner
}

export interface AuthResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
  partner: PartnerProfile;
}

export const partnerAuthApi = {
  // Direct login without OTP (temporary - for demo/testing)
  loginDirect: async (phone: string): Promise<AuthResponse> => {
    const { data } = await partnerClient.post(`${PARTNERS_PATH}/auth/login-direct`, { phone });
    return data;
  },

  // Send OTP for login (disabled temporarily)
  sendOTP: async (phone: string): Promise<{ success: boolean; message: string; cooldown_seconds?: number }> => {
    const { data } = await partnerClient.post(`${PARTNERS_PATH}/auth/send-otp`, { phone });
    return data;
  },

  // Verify OTP and get tokens (disabled temporarily)
  verifyOTP: async (phone: string, otp: string): Promise<AuthResponse> => {
    const { data } = await partnerClient.post(`${PARTNERS_PATH}/auth/verify-otp`, { phone, otp });
    return data;
  },

  // Register new partner
  // API returns CommunityPartnerResponse on success, or throws error
  register: async (request: PartnerRegistrationRequest): Promise<{ id?: string; partner_id?: string; success?: boolean; message?: string }> => {
    const { data } = await partnerClient.post(`${PARTNERS_PATH}/register`, request);
    return data;
  },

  // Refresh access token
  refreshToken: async (refreshToken: string): Promise<{ access_token: string; token_type: string; expires_in: number }> => {
    const { data } = await partnerClient.post(`${PARTNERS_PATH}/auth/refresh`, { refresh_token: refreshToken });
    return data;
  },
};

// Partner Portal API (authenticated)
export const partnerApi = {
  // Get current partner profile
  getProfile: async (): Promise<PartnerProfile> => {
    const { data } = await partnerClient.get(`${PARTNERS_PATH}/me`);
    return data;
  },

  // Update partner profile
  updateProfile: async (updates: Partial<PartnerProfile>): Promise<PartnerProfile> => {
    const { data } = await partnerClient.patch(`${PARTNERS_PATH}/me`, updates);
    return data;
  },

  // Get dashboard stats
  getDashboardStats: async (): Promise<PartnerDashboardStats> => {
    const { data } = await partnerClient.get(`${PARTNERS_PATH}/me/dashboard`);
    return data;
  },

  // Get products for sharing
  getProducts: async (page = 1, size = 20): Promise<PaginatedResponse<StorefrontProduct>> => {
    const { data } = await partnerClient.get(`${PARTNERS_PATH}/me/products`, {
      params: { page, size },
    });
    return data;
  },

  // Get commission history
  getCommissions: async (
    status?: string,
    page = 1,
    size = 20
  ): Promise<PaginatedResponse<PartnerCommission>> => {
    const params: Record<string, string | number> = { page, size };
    if (status) params.status = status;

    const { data } = await partnerClient.get(`${PARTNERS_PATH}/me/commissions`, { params });
    return data;
  },

  // Get payout history
  getPayouts: async (page = 1, size = 20): Promise<PaginatedResponse<PartnerPayout>> => {
    const { data } = await partnerClient.get(`${PARTNERS_PATH}/me/payouts`, {
      params: { page, size },
    });
    return data;
  },

  // Request payout
  requestPayout: async (amount: number): Promise<{ success: boolean; message: string; payout_id?: string }> => {
    const { data } = await partnerClient.post(`${PARTNERS_PATH}/me/payouts/request`, { amount });
    return data;
  },

  // Generate referral link for a product
  getReferralLink: async (productSlug: string): Promise<{ referral_link: string; partner_code: string }> => {
    const { data } = await partnerClient.get(`${PARTNERS_PATH}/me/referral-link/${productSlug}`);
    return data;
  },
};

// KYC API
export interface KYCDocumentUpload {
  document_type: 'AADHAAR' | 'PAN' | 'BANK_PROOF';
  document_number?: string;
  document_url: string;
}

export interface BankDetails {
  account_holder_name: string;
  account_number: string;
  ifsc_code: string;
  bank_name: string;
}

export const partnerKYCApi = {
  // Get KYC status
  getKYCStatus: async (): Promise<{
    kyc_status: string;
    documents: { type: string; status: string; uploaded_at?: string }[];
    bank_details?: BankDetails;
  }> => {
    const { data } = await partnerClient.get(`${PARTNERS_PATH}/me/kyc`);
    return data;
  },

  // Upload KYC document
  uploadDocument: async (document: KYCDocumentUpload): Promise<{ success: boolean; message: string }> => {
    const { data } = await partnerClient.post(`${PARTNERS_PATH}/me/kyc/documents`, document);
    return data;
  },

  // Update bank details
  updateBankDetails: async (bankDetails: BankDetails): Promise<{ success: boolean; message: string }> => {
    const { data } = await partnerClient.post(`${PARTNERS_PATH}/me/kyc/bank-details`, bankDetails);
    return data;
  },
};

// Helper function to generate share URLs
export const generateShareUrl = (productSlug: string, partnerCode: string): string => {
  const baseUrl = typeof window !== 'undefined' ? window.location.origin : 'https://www.ilms.ai';
  return `${baseUrl}/products/${productSlug}?ref=${partnerCode}`;
};

// Helper function to generate WhatsApp share link
export const generateWhatsAppShareLink = (productSlug: string, productName: string, partnerCode: string): string => {
  const shareUrl = generateShareUrl(productSlug, partnerCode);
  const message = encodeURIComponent(
    `Check out this amazing product: ${productName}\n\n${shareUrl}`
  );
  return `https://wa.me/?text=${message}`;
};

export default partnerClient;
