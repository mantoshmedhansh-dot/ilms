'use client';

import {
  createContext,
  useContext,
  useEffect,
  useState,
  ReactNode,
  useCallback,
} from 'react';
import { usePathname, useRouter } from 'next/navigation';
import {
  getTenantFromPath,
  getStoredTenantId,
  getStoredTenantSubdomain,
  setTenantContext,
  clearTenantContext,
  buildTenantUrl,
} from '@/lib/tenant';

interface TenantInfo {
  subdomain: string;
  tenantId: string;
  name?: string;
}

interface TenantContextType {
  tenant: TenantInfo | null;
  isLoading: boolean;
  error: string | null;
  setTenant: (subdomain: string, tenantId: string, name?: string) => void;
  clearTenant: () => void;
  getTenantUrl: (path: string) => string;
}

const TenantContext = createContext<TenantContextType | undefined>(undefined);

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export function TenantProvider({ children }: { children: ReactNode }) {
  const [tenant, setTenantState] = useState<TenantInfo | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const pathname = usePathname();
  const router = useRouter();

  // Resolve tenant from URL or localStorage
  const resolveTenant = useCallback(async () => {
    setIsLoading(true);
    setError(null);

    try {
      // First try to get tenant from URL path
      const subdomainFromPath = getTenantFromPath(pathname);

      if (subdomainFromPath) {
        // Lookup tenant ID from subdomain
        const response = await fetch(
          `${API_BASE_URL}/api/v1/onboarding/tenant-lookup?subdomain=${subdomainFromPath}`
        );

        if (response.ok) {
          const data = await response.json();
          const tenantInfo: TenantInfo = {
            subdomain: subdomainFromPath,
            tenantId: data.tenant_id,
            name: data.name,
          };
          setTenantState(tenantInfo);
          setTenantContext(subdomainFromPath, data.tenant_id);
          return;
        } else {
          setError('Tenant not found');
          setTenantState(null);
          return;
        }
      }

      // Fallback to localStorage
      const storedSubdomain = getStoredTenantSubdomain();
      const storedTenantId = getStoredTenantId();

      if (storedSubdomain && storedTenantId) {
        setTenantState({
          subdomain: storedSubdomain,
          tenantId: storedTenantId,
        });
      } else {
        setTenantState(null);
      }
    } catch (err) {
      console.error('Failed to resolve tenant:', err);
      setError('Failed to resolve tenant');
      setTenantState(null);
    } finally {
      setIsLoading(false);
    }
  }, [pathname]);

  useEffect(() => {
    resolveTenant();
  }, [resolveTenant]);

  const setTenant = useCallback(
    (subdomain: string, tenantId: string, name?: string) => {
      const tenantInfo: TenantInfo = { subdomain, tenantId, name };
      setTenantState(tenantInfo);
      setTenantContext(subdomain, tenantId);
    },
    []
  );

  const clearTenant = useCallback(() => {
    setTenantState(null);
    clearTenantContext();
    router.push('/');
  }, [router]);

  const getTenantUrl = useCallback(
    (path: string): string => {
      if (tenant?.subdomain) {
        return buildTenantUrl(tenant.subdomain, path);
      }
      return path;
    },
    [tenant]
  );

  return (
    <TenantContext.Provider
      value={{
        tenant,
        isLoading,
        error,
        setTenant,
        clearTenant,
        getTenantUrl,
      }}
    >
      {children}
    </TenantContext.Provider>
  );
}

export function useTenant() {
  const context = useContext(TenantContext);
  if (context === undefined) {
    throw new Error('useTenant must be used within a TenantProvider');
  }
  return context;
}
