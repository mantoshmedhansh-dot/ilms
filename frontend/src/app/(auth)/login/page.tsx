'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { Loader2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';

export default function LoginPage() {
  const router = useRouter();
  const [isChecking, setIsChecking] = useState(true);
  const [tenantSubdomain, setTenantSubdomain] = useState('');

  // Check for stored tenant on mount - redirect if found
  useEffect(() => {
    const storedSubdomain = localStorage.getItem('tenant_subdomain');
    if (storedSubdomain) {
      // Redirect to tenant-specific login immediately
      router.replace(`/t/${storedSubdomain}/login`);
    } else {
      // No tenant stored, show tenant input
      setIsChecking(false);
    }
  }, [router]);

  const handleTenantSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (tenantSubdomain.trim()) {
      router.push(`/t/${tenantSubdomain.trim().toLowerCase()}/login`);
    }
  };

  // Show loading while checking for stored tenant
  if (isChecking) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-muted/50">
        <div className="text-center">
          <Loader2 className="h-8 w-8 animate-spin mx-auto mb-4" />
          <p className="text-muted-foreground">Loading...</p>
        </div>
      </div>
    );
  }

  // Only show tenant selector - never email/password form
  return (
    <div className="min-h-screen flex items-center justify-center bg-muted/50 p-4">
      <Card className="w-full max-w-md">
        <CardHeader className="space-y-1 text-center">
          <div className="flex justify-center mb-4">
            <span className="font-bold text-4xl bg-gradient-to-r from-primary to-secondary bg-clip-text text-transparent">
              Fretron
            </span>
          </div>
          <CardTitle className="text-2xl font-bold">Welcome to Fretron</CardTitle>
          <CardDescription>
            Enter your organization ID to continue
          </CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleTenantSubmit} className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="tenant">Organization ID</Label>
              <Input
                id="tenant"
                type="text"
                placeholder="e.g., mantosh"
                value={tenantSubdomain}
                onChange={(e) => setTenantSubdomain(e.target.value)}
                autoFocus
              />
              <p className="text-xs text-muted-foreground">
                This is the subdomain provided during registration
              </p>
            </div>
            <Button type="submit" className="w-full" disabled={!tenantSubdomain.trim()}>
              Continue
            </Button>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
