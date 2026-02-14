'use client';

import { useState, useEffect, useRef } from 'react';
import { usePathname } from 'next/navigation';
import { Loader2 } from 'lucide-react';
import { cn } from '@/lib/utils';
import { PlatformAuthProvider, usePlatformAuth } from '@/providers/platform-auth-provider';
import { PlatformSidebar } from '@/components/platform/platform-sidebar';
import { PlatformHeader } from '@/components/platform/platform-header';

function PlatformLayoutInner({ children }: { children: React.ReactNode }) {
  const [isCollapsed, setIsCollapsed] = useState(false);
  const { isAuthenticated, isLoading } = usePlatformAuth();
  const pathname = usePathname();
  const hasRedirected = useRef(false);

  const isLoginPage = pathname === '/platform/login';

  useEffect(() => {
    if (hasRedirected.current) return;
    if (isLoading) return;
    if (isLoginPage) return;

    if (!isAuthenticated) {
      hasRedirected.current = true;
      window.location.href = '/platform/login';
    }
  }, [isAuthenticated, isLoading, isLoginPage]);

  // Login page renders without sidebar/header
  if (isLoginPage) {
    return <>{children}</>;
  }

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
    <div className="min-h-screen bg-muted/30">
      <PlatformSidebar isCollapsed={isCollapsed} onToggle={() => setIsCollapsed(!isCollapsed)} />
      <div
        className={cn(
          'transition-all duration-300',
          isCollapsed ? 'pl-16' : 'pl-64'
        )}
      >
        <PlatformHeader />
        <main className="p-6">{children}</main>
      </div>
    </div>
  );
}

export default function PlatformLayout({ children }: { children: React.ReactNode }) {
  return (
    <PlatformAuthProvider>
      <PlatformLayoutInner>{children}</PlatformLayoutInner>
    </PlatformAuthProvider>
  );
}
