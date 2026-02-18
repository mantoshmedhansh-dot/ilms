'use client';

import { useState, useEffect, useRef } from 'react';
import { Loader2 } from 'lucide-react';
import { cn } from '@/lib/utils';
import { Sidebar, Header } from '@/components/layout';
import { useAuth } from '@/providers';
import { getAccessToken, getRedirectSubdomain } from '@/lib/api/client';

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const [isCollapsed, setIsCollapsed] = useState(false);
  const { isAuthenticated, isLoading, user } = useAuth();
  const hasRedirected = useRef(false);

  useEffect(() => {
    // Prevent multiple redirects
    if (hasRedirected.current) return;

    // Wait until loading is complete
    if (isLoading) return;

    // If not authenticated, redirect to login
    if (!isAuthenticated) {
      hasRedirected.current = true;

      // Check if we have tokens but auth still failed (API issue)
      const token = getAccessToken();

      console.log('[DashboardLayout] Auth failed', {
        hasToken: !!token,
        isAuthenticated,
        isLoading,
        sessionSubdomain: typeof window !== 'undefined' ? sessionStorage.getItem('active_subdomain') : null,
        redirectSubdomain: getRedirectSubdomain(),
      });

      // Use full page reload to avoid React state issues
      const subdomain = getRedirectSubdomain();
      if (subdomain) {
        window.location.href = `/t/${subdomain}/login`;
      } else {
        window.location.href = '/login';
      }
    }
  }, [isAuthenticated, isLoading]);

  if (isLoading) {
    return (
      <div className="flex h-screen items-center justify-center">
        <div className="text-center">
          <Loader2 className="h-8 w-8 animate-spin text-primary mx-auto" />
          <p className="text-sm text-muted-foreground mt-2">Loading...</p>
        </div>
      </div>
    );
  }

  if (!isAuthenticated) {
    // Show loading while redirect happens
    return (
      <div className="flex h-screen items-center justify-center">
        <div className="text-center">
          <Loader2 className="h-8 w-8 animate-spin text-primary mx-auto" />
          <p className="text-sm text-muted-foreground mt-2">Redirecting to login...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-white to-slate-100/80 dark:from-slate-950 dark:via-slate-950 dark:to-slate-900">
      <Sidebar isCollapsed={isCollapsed} onToggle={() => setIsCollapsed(!isCollapsed)} />
      <div
        className={cn(
          'transition-all duration-300',
          isCollapsed ? 'pl-16' : 'pl-72'
        )}
      >
        <Header />
        <main className="p-6">{children}</main>
      </div>
    </div>
  );
}
