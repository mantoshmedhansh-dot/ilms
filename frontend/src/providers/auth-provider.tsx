'use client';

import { createContext, useContext, useEffect, useState, useCallback, ReactNode } from 'react';
import { useRouter } from 'next/navigation';
import { User, UserPermissions, LoginRequest } from '@/types';
import { authApi } from '@/lib/api';
import { getAccessToken, getTenantId, getRedirectSubdomain } from '@/lib/api/client';

interface AuthContextType {
  user: User | null;
  permissions: UserPermissions | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  login: (credentials: LoginRequest) => Promise<void>;
  logout: () => Promise<void>;
  refreshUser: () => Promise<void>;
  hasPermission: (code: string) => boolean;
  hasAnyPermission: (codes: string[]) => boolean;
  hasAllPermissions: (codes: string[]) => boolean;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [permissions, setPermissions] = useState<UserPermissions | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const router = useRouter();

  const isAuthenticated = !!user;

  const fetchUserAndPermissions = useCallback(async () => {
    try {
      const token = getAccessToken();
      const tenantId = getTenantId();
      const tenantSubdomain = getRedirectSubdomain();

      console.log('[Auth] Starting auth check', {
        hasToken: !!token,
        hasTenantId: !!tenantId,
        tenantSubdomain,
      });

      if (!token) {
        console.log('[Auth] No token found, skipping user fetch');
        setIsLoading(false);
        return;
      }

      // Check if tenant_id is set (required for API calls)
      if (!tenantId) {
        console.warn('[Auth] No tenant_id in localStorage - API calls will fail');
        // If we have a token but no tenant_id, the tenant context was lost
        // This can happen if localStorage was partially cleared
        // Clear tokens and let the user re-login through tenant path
        console.warn('[Auth] Clearing tokens due to missing tenant context');
        setIsLoading(false);
        return;
      }

      console.log('[Auth] Fetching user and permissions from API...');

      // Fetch user and permissions in parallel to reduce load time
      let userData;
      try {
        const [userResult, permissionsResult] = await Promise.allSettled([
          authApi.getCurrentUser(),
          authApi.getUserPermissions(),
        ]);

        if (userResult.status === 'rejected') {
          const errorDetails = userResult.reason instanceof Error ? userResult.reason.message : String(userResult.reason);
          console.error('[Auth] Failed to fetch user:', errorDetails);
          setUser(null);
          setPermissions(null);
          setIsLoading(false);
          return;
        }

        userData = userResult.value;
        console.log('[Auth] User fetched successfully:', userData.email);
        setUser(userData);

        if (permissionsResult.status === 'fulfilled') {
          console.log('[Auth] Permissions fetched successfully');
          setPermissions(permissionsResult.value);
        } else {
          console.warn('[Auth] Failed to fetch permissions, using defaults:', permissionsResult.reason);
          const isSuperAdmin = userData.roles?.some((r: { code: string }) => r.code === 'SUPER_ADMIN') ?? false;
          setPermissions({
            is_super_admin: isSuperAdmin,
            roles: userData.roles,
            permissions_by_module: {},
            total_permissions: 0,
            permissions: {},
          });
        }
      } catch (unexpectedError) {
        console.error('[Auth] Unexpected error during fetch:', unexpectedError);
        setUser(null);
        setPermissions(null);
        setIsLoading(false);
        return;
      }

      console.log('[Auth] Auth check complete - user authenticated');
    } catch (error) {
      console.error('[Auth] Unexpected error:', error);
      setUser(null);
      setPermissions(null);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchUserAndPermissions();
  }, [fetchUserAndPermissions]);

  const login = async (credentials: LoginRequest) => {
    setIsLoading(true);
    try {
      await authApi.login(credentials);
      await fetchUserAndPermissions();
      router.push('/dashboard');
    } finally {
      setIsLoading(false);
    }
  };

  const logout = async () => {
    setIsLoading(true);
    try {
      await authApi.logout();
    } finally {
      setUser(null);
      setPermissions(null);
      setIsLoading(false);
      // Redirect to tenant-specific login if tenant is known
      const subdomain = typeof window !== 'undefined' ? getRedirectSubdomain() : null;
      if (subdomain) {
        router.push(`/t/${subdomain}/login`);
      } else {
        router.push('/login');
      }
    }
  };

  const refreshUser = async () => {
    await fetchUserAndPermissions();
  };

  const hasPermission = useCallback(
    (code: string): boolean => {
      if (!permissions) return false;
      if (permissions.is_super_admin) return true;
      return permissions.permissions[code] === true;
    },
    [permissions]
  );

  const hasAnyPermission = useCallback(
    (codes: string[]): boolean => {
      return codes.some((code) => hasPermission(code));
    },
    [hasPermission]
  );

  const hasAllPermissions = useCallback(
    (codes: string[]): boolean => {
      return codes.every((code) => hasPermission(code));
    },
    [hasPermission]
  );

  return (
    <AuthContext.Provider
      value={{
        user,
        permissions,
        isLoading,
        isAuthenticated,
        login,
        logout,
        refreshUser,
        hasPermission,
        hasAnyPermission,
        hasAllPermissions,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}
