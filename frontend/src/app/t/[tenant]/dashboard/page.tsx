'use client';

import { useEffect } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { getAccessToken } from '@/lib/api/client';

export default function TenantDashboardRedirect() {
  const params = useParams();
  const router = useRouter();
  const tenant = params.tenant as string;

  useEffect(() => {
    const token = getAccessToken();
    if (!token) {
      // Not logged in, redirect to login
      router.push(`/t/${tenant}/login`);
    } else {
      // Redirect to main dashboard
      router.push('/dashboard');
    }
  }, [tenant, router]);

  return (
    <div className="min-h-screen flex items-center justify-center">
      <p className="text-muted-foreground">Redirecting to dashboard...</p>
    </div>
  );
}
