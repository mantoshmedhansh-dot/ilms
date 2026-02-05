'use client';

import { useEffect, useState } from 'react';
import { useParams } from 'next/navigation';
import { Loader2 } from 'lucide-react';
import { getAccessToken } from '@/lib/api/client';

export default function TenantDashboardRedirect() {
  const params = useParams();
  const tenant = params.tenant as string;
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const token = getAccessToken();
    const tenantId = localStorage.getItem('tenant_id');

    if (!token) {
      // Not logged in, redirect to login using full page reload
      window.location.href = `/t/${tenant}/login`;
      return;
    }

    if (!tenantId) {
      // Tenant context lost, redirect to tenant login to restore it
      console.warn('[TenantDashboard] No tenant_id in localStorage, redirecting to login');
      window.location.href = `/t/${tenant}/login`;
      return;
    }

    // Use full page reload to ensure clean auth state
    // This avoids React state timing issues with client-side navigation
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
