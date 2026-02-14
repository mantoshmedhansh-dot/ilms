'use client';

import { createContext, useContext, useEffect, useState, useCallback, ReactNode } from 'react';
import { useRouter } from 'next/navigation';
import { getPlatformAccessToken, clearPlatformTokens } from '@/lib/api/platform-client';
import { platformAdminApi } from '@/lib/api/platform-admin';
import type { PlatformUser } from '@/types/platform';

interface PlatformAuthContextType {
  user: PlatformUser | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
}

const PlatformAuthContext = createContext<PlatformAuthContextType | undefined>(undefined);

export function PlatformAuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<PlatformUser | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const router = useRouter();

  const isAuthenticated = !!user;

  const checkAuth = useCallback(async () => {
    try {
      const token = getPlatformAccessToken();
      if (!token) {
        setIsLoading(false);
        return;
      }

      // Token exists — restore user from localStorage
      const email = localStorage.getItem('platform_user_email') || 'admin';
      const firstName = localStorage.getItem('platform_user_first_name') || 'Platform';
      const lastName = localStorage.getItem('platform_user_last_name') || 'Admin';

      setUser({ email, first_name: firstName, last_name: lastName });
    } catch {
      setUser(null);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    checkAuth();
  }, [checkAuth]);

  const login = async (email: string, password: string) => {
    setIsLoading(true);
    try {
      const data = await platformAdminApi.login(email, password);

      // Store user info for session restoration
      const firstName = data.first_name || data.tenant_subdomain || 'Platform';
      const lastName = data.last_name || 'Admin';
      localStorage.setItem('platform_user_email', email);
      localStorage.setItem('platform_user_first_name', firstName);
      localStorage.setItem('platform_user_last_name', lastName);

      setUser({ email, first_name: firstName, last_name: lastName });
      setIsLoading(false);

      router.push('/platform/dashboard');
    } catch (error) {
      setIsLoading(false);
      throw error;
    }
  };

  const logout = () => {
    clearPlatformTokens();
    localStorage.removeItem('platform_user_email');
    localStorage.removeItem('platform_user_first_name');
    localStorage.removeItem('platform_user_last_name');
    setUser(null);
    router.push('/platform/login');
  };

  return (
    <PlatformAuthContext.Provider
      value={{ user, isLoading, isAuthenticated, login, logout }}
    >
      {children}
    </PlatformAuthContext.Provider>
  );
}

export function usePlatformAuth() {
  const context = useContext(PlatformAuthContext);
  if (context === undefined) {
    throw new Error('usePlatformAuth must be used within a PlatformAuthProvider');
  }
  return context;
}
