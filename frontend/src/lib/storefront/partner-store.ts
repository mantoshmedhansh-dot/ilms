import { create } from 'zustand';
import { persist } from 'zustand/middleware';

export interface PartnerProfile {
  id: string;
  partner_code: string;
  full_name: string;
  phone: string;
  email?: string;
  status: string;
  kyc_status: string;
  referral_code: string;
  tier_code: string;
}

export interface PartnerDashboardStats {
  total_referrals: number;
  successful_conversions: number;
  total_earnings: number;
  pending_earnings: number;
  paid_earnings: number;
  current_tier: string;
  next_tier?: string;
  tier_progress: number;
  this_month_orders: number;
  this_month_earnings: number;
}

export interface PartnerCommission {
  id: string;
  order_number: string;
  order_date: string;
  customer_name: string;
  order_amount: number;
  commission_rate: number;
  commission_amount: number;
  tds_amount: number;
  net_amount: number;
  status: string;
}

export interface PartnerPayout {
  id: string;
  payout_number: string;
  amount: number;
  tds_deducted: number;
  net_amount: number;
  status: string;
  payment_mode: string;
  payment_reference?: string;
  requested_at: string;
  processed_at?: string;
}

interface PartnerState {
  // Auth state
  isAuthenticated: boolean;
  isLoading: boolean;
  accessToken: string | null;
  refreshToken: string | null;
  partner: PartnerProfile | null;

  // Dashboard state
  dashboardStats: PartnerDashboardStats | null;
  commissions: PartnerCommission[];
  payouts: PartnerPayout[];

  // Actions
  login: (accessToken: string, refreshToken: string, partner: PartnerProfile) => void;
  logout: () => void;
  updateProfile: (profile: Partial<PartnerProfile>) => void;
  setTokens: (accessToken: string, refreshToken?: string) => void;
  setLoading: (loading: boolean) => void;
  setDashboardStats: (stats: PartnerDashboardStats) => void;
  setCommissions: (commissions: PartnerCommission[]) => void;
  setPayouts: (payouts: PartnerPayout[]) => void;
}

export const usePartnerStore = create<PartnerState>()(
  persist(
    (set) => ({
      isAuthenticated: false,
      isLoading: true,
      accessToken: null,
      refreshToken: null,
      partner: null,
      dashboardStats: null,
      commissions: [],
      payouts: [],

      login: (accessToken, refreshToken, partner) =>
        set({
          isAuthenticated: true,
          isLoading: false,
          accessToken,
          refreshToken,
          partner,
        }),

      logout: () =>
        set({
          isAuthenticated: false,
          isLoading: false,
          accessToken: null,
          refreshToken: null,
          partner: null,
          dashboardStats: null,
          commissions: [],
          payouts: [],
        }),

      updateProfile: (profile) =>
        set((state) => ({
          partner: state.partner ? { ...state.partner, ...profile } : null,
        })),

      setTokens: (accessToken, refreshToken) =>
        set((state) => ({
          accessToken,
          refreshToken: refreshToken || state.refreshToken,
        })),

      setLoading: (loading) => set({ isLoading: loading }),

      setDashboardStats: (stats) => set({ dashboardStats: stats }),

      setCommissions: (commissions) => set({ commissions }),

      setPayouts: (payouts) => set({ payouts }),
    }),
    {
      name: 'partner-auth-storage',
      partialize: (state) => ({
        isAuthenticated: state.isAuthenticated,
        accessToken: state.accessToken,
        refreshToken: state.refreshToken,
        partner: state.partner,
      }),
      onRehydrateStorage: () => (state) => {
        if (state) {
          state.setLoading(false);
        }
      },
    }
  )
);

// Selector hooks for convenience
export const usePartnerIsAuthenticated = () => usePartnerStore((state) => state.isAuthenticated);
export const usePartner = () => usePartnerStore((state) => state.partner);
export const usePartnerAccessToken = () => usePartnerStore((state) => state.accessToken);
export const usePartnerDashboardStats = () => usePartnerStore((state) => state.dashboardStats);
