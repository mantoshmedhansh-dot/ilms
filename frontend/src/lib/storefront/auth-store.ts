import { create } from 'zustand';
import { persist } from 'zustand/middleware';

export interface CustomerProfile {
  id: string;
  phone: string;
  email?: string;
  first_name: string;
  last_name?: string;
  is_verified: boolean;
}

export interface CustomerAddress {
  id: string;
  address_type: string;
  contact_name?: string;
  contact_phone?: string;
  address_line1: string;
  address_line2?: string;
  landmark?: string;
  city: string;
  state: string;
  pincode: string;
  country: string;
  is_default: boolean;
}

interface AuthState {
  // Auth state
  isAuthenticated: boolean;
  isLoading: boolean;
  accessToken: string | null;
  refreshToken: string | null;
  customer: CustomerProfile | null;

  // Actions
  login: (accessToken: string, refreshToken: string, customer: CustomerProfile) => void;
  logout: () => void;
  updateProfile: (profile: Partial<CustomerProfile>) => void;
  setTokens: (accessToken: string, refreshToken?: string) => void;
  setLoading: (loading: boolean) => void;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      isAuthenticated: false,
      isLoading: true, // Initially loading until hydration completes
      accessToken: null,
      refreshToken: null,
      customer: null,

      login: (accessToken, refreshToken, customer) =>
        set({
          isAuthenticated: true,
          isLoading: false,
          accessToken,
          refreshToken,
          customer,
        }),

      logout: () =>
        set({
          isAuthenticated: false,
          isLoading: false,
          accessToken: null,
          refreshToken: null,
          customer: null,
        }),

      updateProfile: (profile) =>
        set((state) => ({
          customer: state.customer ? { ...state.customer, ...profile } : null,
        })),

      setTokens: (accessToken, refreshToken) =>
        set((state) => ({
          accessToken,
          refreshToken: refreshToken || state.refreshToken,
        })),

      setLoading: (loading) => set({ isLoading: loading }),
    }),
    {
      name: 'd2c-auth-storage',
      partialize: (state) => ({
        isAuthenticated: state.isAuthenticated,
        accessToken: state.accessToken,
        refreshToken: state.refreshToken,
        customer: state.customer,
      }),
      onRehydrateStorage: () => (state) => {
        // Set isLoading to false after hydration completes
        if (state) {
          state.setLoading(false);
        }
      },
    }
  )
);

// Selector hooks for convenience
export const useIsAuthenticated = () => useAuthStore((state) => state.isAuthenticated);
export const useCustomer = () => useAuthStore((state) => state.customer);
export const useAccessToken = () => useAuthStore((state) => state.accessToken);
