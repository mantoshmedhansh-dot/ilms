'use client';

import { useState, useEffect, useRef } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import Link from 'next/link';
import { useParams } from 'next/navigation';
import { Loader2 } from 'lucide-react';
import { toast } from 'sonner';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { authApi } from '@/lib/api';
import { setTokens, getAccessToken, getTenantId } from '@/lib/api/client';
import { useAuth } from '@/providers';

const loginSchema = z.object({
  email: z.string().email('Please enter a valid email address'),
  password: z.string().min(6, 'Password must be at least 6 characters'),
});

type LoginForm = z.infer<typeof loginSchema>;

export default function TenantLoginPage() {
  const params = useParams();
  const { isAuthenticated, isLoading: authLoading } = useAuth();
  const tenant = params.tenant as string;
  const [isLoading, setIsLoading] = useState(false);
  const [tenantName, setTenantName] = useState<string>('');
  const [isCheckingAuth, setIsCheckingAuth] = useState(true);
  const hasRedirected = useRef(false);

  useEffect(() => {
    // Get tenant name from localStorage (scoped first, then generic)
    const name = localStorage.getItem(`tenant_name:${tenant}`) || localStorage.getItem('tenant_name');
    if (name) setTenantName(name);

    // Check if user is already logged in (using scoped functions)
    const token = getAccessToken();
    const tenantId = getTenantId();

    if (token && tenantId) {
      // User has valid session, redirect to dashboard
      console.log('[Login] User already has token, redirecting to dashboard');
      if (!hasRedirected.current) {
        hasRedirected.current = true;
        window.location.href = '/dashboard';
        return;
      }
    }

    setIsCheckingAuth(false);
  }, [tenant]);

  // Also check auth state from provider
  useEffect(() => {
    if (!authLoading && isAuthenticated && !hasRedirected.current) {
      console.log('[Login] User authenticated via provider, redirecting');
      hasRedirected.current = true;
      window.location.href = '/dashboard';
    }
  }, [authLoading, isAuthenticated]);

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<LoginForm>({
    resolver: zodResolver(loginSchema),
    defaultValues: {
      email: '',
      password: '',
    },
  });

  const onSubmit = async (data: LoginForm) => {
    setIsLoading(true);
    try {
      console.log('[Login] Submitting login for', data.email);
      const response = await authApi.login(data);
      console.log('[Login] Login successful', {
        hasAccessToken: !!response.access_token,
        tenantId: response.tenant_id,
        tenantSubdomain: response.tenant_subdomain,
      });
      setTokens(response.access_token, response.refresh_token);

      // Verify tokens were stored correctly
      const storedToken = getAccessToken();
      const storedTenantId = getTenantId();
      console.log('[Login] Stored tokens verified', {
        hasStoredToken: !!storedToken,
        storedTenantId,
        sessionSubdomain: sessionStorage.getItem('active_subdomain'),
      });

      toast.success('Welcome back!');
      window.location.href = '/dashboard';
    } catch (err) {
      console.error('[Login] Login failed:', err);
      toast.error('Invalid email or password');
    } finally {
      setIsLoading(false);
    }
  };

  // Show loading while checking auth
  if (isCheckingAuth || (authLoading && !isLoading)) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-muted/50">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
      </div>
    );
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-muted/50 p-4">
      <Card className="w-full max-w-md">
        <CardHeader className="space-y-1 text-center">
          <div className="flex justify-center mb-4">
            <span className="font-bold text-4xl bg-gradient-to-r from-primary to-secondary bg-clip-text text-transparent">
              Fretron
            </span>
          </div>
          <CardTitle className="text-2xl font-bold">
            {tenantName || 'Sign In'}
          </CardTitle>
          <CardDescription>
            Enter your credentials to access the control panel
          </CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="email">Email</Label>
              <Input
                id="email"
                type="email"
                placeholder="admin@example.com"
                {...register('email')}
                disabled={isLoading}
              />
              {errors.email && (
                <p className="text-sm text-destructive">{errors.email.message}</p>
              )}
            </div>
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <Label htmlFor="password">Password</Label>
                <Link
                  href={`/t/${tenant}/forgot-password`}
                  className="text-sm text-primary hover:underline"
                >
                  Forgot password?
                </Link>
              </div>
              <Input
                id="password"
                type="password"
                placeholder="••••••••"
                {...register('password')}
                disabled={isLoading}
              />
              {errors.password && (
                <p className="text-sm text-destructive">{errors.password.message}</p>
              )}
            </div>
            <Button type="submit" className="w-full" disabled={isLoading}>
              {isLoading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              Sign In
            </Button>
          </form>

          <div className="mt-4 text-center text-sm text-muted-foreground">
            Signing into <strong>{tenantName || tenant}</strong>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
