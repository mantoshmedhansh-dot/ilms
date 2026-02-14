'use client';

import { useEffect, useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { Loader2 } from 'lucide-react';
import { setActiveSubdomain, setTenantContext } from '@/lib/api/client';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

interface TenantInfo {
  tenant_id: string;
  subdomain: string;
  name: string;
  status: string;
}

export default function TenantLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const params = useParams();
  const router = useRouter();
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const tenant = params.tenant as string;

  useEffect(() => {
    async function resolveTenant() {
      if (!tenant) {
        setError('No tenant specified');
        setIsLoading(false);
        return;
      }

      try {
        // Set active subdomain for this tab immediately
        setActiveSubdomain(tenant);

        const response = await fetch(
          `${API_BASE_URL}/api/v1/onboarding/tenant-lookup?subdomain=${tenant}`
        );

        if (response.ok) {
          const data: TenantInfo = await response.json();

          // Store scoped + generic tenant context
          setTenantContext(data.tenant_id, data.subdomain);
          localStorage.setItem(`tenant_name:${data.subdomain}`, data.name);
          localStorage.setItem('tenant_name', data.name);

          // Migrate: if generic tokens exist for this subdomain, copy to scoped keys
          const existingSubdomain = localStorage.getItem('tenant_subdomain');
          const existingToken = localStorage.getItem('access_token');
          if (existingSubdomain === data.subdomain && existingToken) {
            if (!localStorage.getItem(`access_token:${data.subdomain}`)) {
              localStorage.setItem(`access_token:${data.subdomain}`, existingToken);
            }
            const existingRefresh = localStorage.getItem('refresh_token');
            if (existingRefresh && !localStorage.getItem(`refresh_token:${data.subdomain}`)) {
              localStorage.setItem(`refresh_token:${data.subdomain}`, existingRefresh);
            }
          }

          setIsLoading(false);
        } else {
          const errorData = await response.json();
          setError(errorData.detail || 'Tenant not found');
          setIsLoading(false);
        }
      } catch (err) {
        console.error('Failed to resolve tenant:', err);
        setError('Failed to connect to server');
        setIsLoading(false);
      }
    }

    resolveTenant();
  }, [tenant]);

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-muted/50">
        <div className="text-center">
          <Loader2 className="h-8 w-8 animate-spin mx-auto mb-4" />
          <p className="text-muted-foreground">Loading tenant...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-muted/50">
        <div className="text-center max-w-md mx-auto p-6">
          <h1 className="text-2xl font-bold text-destructive mb-2">
            Tenant Not Found
          </h1>
          <p className="text-muted-foreground mb-4">{error}</p>
          <p className="text-sm text-muted-foreground">
            The organization &quot;{tenant}&quot; does not exist or is inactive.
          </p>
          <button
            onClick={() => router.push('/')}
            className="mt-4 px-4 py-2 bg-primary text-primary-foreground rounded-md hover:bg-primary/90"
          >
            Go to Homepage
          </button>
        </div>
      </div>
    );
  }

  return <>{children}</>;
}
