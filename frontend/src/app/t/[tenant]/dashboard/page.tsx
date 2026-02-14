'use client';

import { useEffect, useState } from 'react';
import { useParams } from 'next/navigation';
import { Loader2 } from 'lucide-react';
import { getAccessToken, getTenantId } from '@/lib/api/client';

export default function TenantDashboardRedirect() {
  const params = useParams();
  const tenant = params.tenant as string;
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    // sessionStorage.active_subdomain is already set by the tenant layout
    const token = getAccessToken();
    const tenantId = getTenantId();

    if (!token) {
      // Not logged in, redirect to login using full page reload
      window.location.href = `/t/${tenant}/login`;
      return;
    }

    if (!tenantId) {
      // Tenant context lost, redirect to tenant login to restore it
      console.warn('[TenantDashboard] No tenant_id, redirecting to login');
      window.location.href = `/t/${tenant}/login`;
      return;
    }

    // Use full page reload to ensure clean auth state
    // sessionStorage.active_subdomain persists across same-tab navigations
    window.location.href = '/dashboard';
  }, [tenant]);

  if (error) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <p className="text-destructive mb-2">{error}</p>
          <button
            onClick={() => window.location.href = `/t/${tenant}/login`}
            className="text-primary hover:underline"
          >
            Go to Login
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex items-center justify-center">
      <div className="text-center">
        <Loader2 className="h-8 w-8 animate-spin mx-auto mb-4" />
        <p className="text-muted-foreground">Redirecting to dashboard...</p>
      </div>
    </div>
  );
}
