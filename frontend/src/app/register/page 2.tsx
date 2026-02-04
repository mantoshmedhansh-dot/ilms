'use client';

import { useState, useEffect } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { useRouter } from 'next/navigation';
import { Loader2, Check, X, Building2, User, Mail, Phone, Lock, CreditCard } from 'lucide-react';
import { toast } from 'sonner';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Checkbox } from '@/components/ui/checkbox';
import { RadioGroup, RadioGroupItem } from '@/components/ui/radio-group';
import { Progress } from '@/components/ui/progress';
import { onboardingApi } from '@/lib/api';

const registerSchema = z.object({
  subdomain: z.string()
    .min(3, 'Subdomain must be at least 3 characters')
    .max(20, 'Subdomain must be less than 20 characters')
    .regex(/^[a-z0-9-]+$/, 'Only lowercase letters, numbers, and hyphens allowed'),
  company_name: z.string().min(2, 'Company name is required'),
  admin_email: z.string().email('Please enter a valid email'),
  admin_phone: z.string().min(10, 'Please enter a valid phone number'),
  admin_password: z.string().min(8, 'Password must be at least 8 characters'),
  admin_first_name: z.string().min(1, 'First name is required'),
  admin_last_name: z.string().min(1, 'Last name is required'),
  selected_modules: z.array(z.string()).min(1, 'Please select at least one module'),
  billing_cycle: z.enum(['monthly', 'annual']),
});

type RegisterForm = z.infer<typeof registerSchema>;

interface Module {
  code: string;
  name: string;
  description: string;
  price_monthly: number;
  price_yearly: number;
  is_base_module: boolean;
}

export default function RegisterPage() {
  const router = useRouter();
  const [isLoading, setIsLoading] = useState(false);
  const [registrationProgress, setRegistrationProgress] = useState(0);
  const [isRegistering, setIsRegistering] = useState(false);
  const [subdomainAvailable, setSubdomainAvailable] = useState<boolean | null>(null);
  const [checkingSubdomain, setCheckingSubdomain] = useState(false);
  const [modules, setModules] = useState<Module[]>([]);
  const [loadingModules, setLoadingModules] = useState(true);

  const {
    register,
    handleSubmit,
    watch,
    setValue,
    formState: { errors },
  } = useForm<RegisterForm>({
    resolver: zodResolver(registerSchema),
    defaultValues: {
      subdomain: '',
      company_name: '',
      admin_email: '',
      admin_phone: '',
      admin_password: '',
      admin_first_name: '',
      admin_last_name: '',
      selected_modules: ['system_admin'],
      billing_cycle: 'monthly',
    },
  });

  const selectedModules = watch('selected_modules');
  const billingCycle = watch('billing_cycle');
  const subdomain = watch('subdomain');

  // Fetch available modules
  useEffect(() => {
    onboardingApi.listModules()
      .then(data => {
        setModules(data.modules || []);
        setLoadingModules(false);
      })
      .catch(() => {
        toast.error('Failed to load modules');
        setLoadingModules(false);
      });
  }, []);

  // Check subdomain availability with debounce
  useEffect(() => {
    const timer = setTimeout(() => {
      if (subdomain && subdomain.length >= 3) {
        setCheckingSubdomain(true);
        onboardingApi.checkSubdomain({ subdomain })
          .then(data => {
            setSubdomainAvailable(data.available);
            setCheckingSubdomain(false);
          })
          .catch(() => {
            setCheckingSubdomain(false);
          });
      } else {
        setSubdomainAvailable(null);
      }
    }, 500);

    return () => clearTimeout(timer);
  }, [subdomain]);

  // Calculate total cost
  const calculateTotal = () => {
    const selectedModuleObjects = modules.filter(m => selectedModules.includes(m.code));
    const total = selectedModuleObjects.reduce((sum, m) => {
      return sum + (billingCycle === 'monthly' ? m.price_monthly : m.price_yearly);
    }, 0);
    return total;
  };

  const onSubmit = async (data: RegisterForm) => {
    if (subdomainAvailable === false) {
      toast.error('Please choose an available subdomain');
      return;
    }

    setIsLoading(true);
    setIsRegistering(true);
    setRegistrationProgress(0);

    try {
      // Simulate progress updates
      const progressInterval = setInterval(() => {
        setRegistrationProgress(prev => {
          if (prev >= 90) return prev;
          return prev + 10;
        });
      }, 2000);

      const result = await onboardingApi.register(data);

      clearInterval(progressInterval);
      setRegistrationProgress(100);

      // Store tokens
      if (result.access_token) {
        localStorage.setItem('access_token', result.access_token);
      }
      if (result.refresh_token) {
        localStorage.setItem('refresh_token', result.refresh_token);
      }
      if (result.tenant?.id) {
        localStorage.setItem('tenant_id', result.tenant.id);
      }

      toast.success('Registration successful! Welcome to ILMS.AI');

      // Redirect to dashboard
      setTimeout(() => {
        router.push('/dashboard');
      }, 1500);

    } catch (error) {
      setRegistrationProgress(0);
      toast.error(error instanceof Error ? error.message : 'Registration failed');
    } finally {
      setIsLoading(false);
      setIsRegistering(false);
    }
  };

  const toggleModule = (moduleCode: string) => {
    const current = selectedModules || [];
    if (moduleCode === 'system_admin') return; // Cannot deselect base module

    if (current.includes(moduleCode)) {
      setValue('selected_modules', current.filter(c => c !== moduleCode));
    } else {
      setValue('selected_modules', [...current, moduleCode]);
    }
  };

  if (isRegistering) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-muted/50 p-4">
        <Card className="w-full max-w-md">
          <CardHeader className="text-center">
            <CardTitle>Creating Your Tenant</CardTitle>
            <CardDescription>
              This may take 3-5 minutes. Please do not close this window.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <Progress value={registrationProgress} className="w-full" />
            <div className="text-center space-y-2">
              <Loader2 className="h-8 w-8 animate-spin mx-auto text-primary" />
              <p className="text-sm text-muted-foreground">
                {registrationProgress < 30 && 'Creating tenant schema...'}
                {registrationProgress >= 30 && registrationProgress < 60 && 'Setting up database tables...'}
                {registrationProgress >= 60 && registrationProgress < 90 && 'Configuring modules...'}
                {registrationProgress >= 90 && 'Finalizing setup...'}
              </p>
              <p className="text-xs text-muted-foreground">
                {registrationProgress}% complete
              </p>
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-muted/50 p-4 py-12">
      <div className="max-w-4xl mx-auto space-y-6">
        <div className="text-center space-y-2">
          <h1 className="text-3xl font-bold">Welcome to ILMS.AI</h1>
          <p className="text-muted-foreground">Create your multi-tenant ERP account</p>
        </div>

        <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
          {/* Subdomain Selection */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Building2 className="h-5 w-5" />
                Choose Your Subdomain
              </CardTitle>
              <CardDescription>
                This will be your unique identifier. Choose carefully.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="subdomain">Subdomain</Label>
                <div className="flex gap-2 items-center">
                  <Input
                    id="subdomain"
                    placeholder="mycompany"
                    {...register('subdomain')}
                    disabled={isLoading}
                    className="flex-1"
                  />
                  <span className="text-sm text-muted-foreground">.ilms.ai</span>
                  {checkingSubdomain && <Loader2 className="h-4 w-4 animate-spin" />}
                  {!checkingSubdomain && subdomainAvailable === true && (
                    <Check className="h-5 w-5 text-green-500" />
                  )}
                  {!checkingSubdomain && subdomainAvailable === false && (
                    <X className="h-5 w-5 text-red-500" />
                  )}
                </div>
                {errors.subdomain && (
                  <p className="text-sm text-destructive">{errors.subdomain.message}</p>
                )}
                {subdomainAvailable === false && (
                  <p className="text-sm text-destructive">This subdomain is already taken</p>
                )}
                {subdomainAvailable === true && (
                  <p className="text-sm text-green-600">This subdomain is available!</p>
                )}
              </div>

              <div className="space-y-2">
                <Label htmlFor="company_name">Company Name</Label>
                <Input
                  id="company_name"
                  placeholder="Acme Corporation"
                  {...register('company_name')}
                  disabled={isLoading}
                />
                {errors.company_name && (
                  <p className="text-sm text-destructive">{errors.company_name.message}</p>
                )}
              </div>
            </CardContent>
          </Card>

          {/* Admin User Details */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <User className="h-5 w-5" />
                Admin Account Details
              </CardTitle>
              <CardDescription>
                This will be the primary administrator account
              </CardDescription>
            </CardHeader>
            <CardContent className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="admin_first_name">First Name</Label>
                <Input
                  id="admin_first_name"
                  {...register('admin_first_name')}
                  disabled={isLoading}
                />
                {errors.admin_first_name && (
                  <p className="text-sm text-destructive">{errors.admin_first_name.message}</p>
                )}
              </div>

              <div className="space-y-2">
                <Label htmlFor="admin_last_name">Last Name</Label>
                <Input
                  id="admin_last_name"
                  {...register('admin_last_name')}
                  disabled={isLoading}
                />
                {errors.admin_last_name && (
                  <p className="text-sm text-destructive">{errors.admin_last_name.message}</p>
                )}
              </div>

              <div className="space-y-2">
                <Label htmlFor="admin_email">
                  <Mail className="h-4 w-4 inline mr-1" />
                  Email
                </Label>
                <Input
                  id="admin_email"
                  type="email"
                  {...register('admin_email')}
                  disabled={isLoading}
                />
                {errors.admin_email && (
                  <p className="text-sm text-destructive">{errors.admin_email.message}</p>
                )}
              </div>

              <div className="space-y-2">
                <Label htmlFor="admin_phone">
                  <Phone className="h-4 w-4 inline mr-1" />
                  Phone
                </Label>
                <Input
                  id="admin_phone"
                  placeholder="+919876543210"
                  {...register('admin_phone')}
                  disabled={isLoading}
                />
                {errors.admin_phone && (
                  <p className="text-sm text-destructive">{errors.admin_phone.message}</p>
                )}
              </div>

              <div className="space-y-2 col-span-2">
                <Label htmlFor="admin_password">
                  <Lock className="h-4 w-4 inline mr-1" />
                  Password
                </Label>
                <Input
                  id="admin_password"
                  type="password"
                  {...register('admin_password')}
                  disabled={isLoading}
                />
                {errors.admin_password && (
                  <p className="text-sm text-destructive">{errors.admin_password.message}</p>
                )}
              </div>
            </CardContent>
          </Card>

          {/* Module Selection */}
          <Card>
            <CardHeader>
              <CardTitle>Select Modules</CardTitle>
              <CardDescription>
                Choose the modules you need. You can upgrade or downgrade later.
              </CardDescription>
            </CardHeader>
            <CardContent>
              {loadingModules ? (
                <div className="flex justify-center py-8">
                  <Loader2 className="h-6 w-6 animate-spin" />
                </div>
              ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {modules.map(module => (
                    <div
                      key={module.code}
                      className={`border rounded-lg p-4 cursor-pointer transition-colors ${
                        selectedModules.includes(module.code)
                          ? 'border-primary bg-primary/5'
                          : 'border-muted hover:border-primary/50'
                      } ${module.is_base_module ? 'opacity-50 cursor-not-allowed' : ''}`}
                      onClick={() => !module.is_base_module && toggleModule(module.code)}
                    >
                      <div className="flex items-start gap-3">
                        <Checkbox
                          checked={selectedModules.includes(module.code)}
                          disabled={module.is_base_module}
                          className="mt-1"
                        />
                        <div className="flex-1">
                          <div className="font-medium">{module.name}</div>
                          <div className="text-sm text-muted-foreground">{module.description}</div>
                          <div className="text-sm font-medium mt-2">
                            ${billingCycle === 'monthly' ? module.price_monthly : module.price_yearly}
                            /{billingCycle === 'monthly' ? 'mo' : 'yr'}
                          </div>
                          {module.is_base_module && (
                            <div className="text-xs text-muted-foreground mt-1">Base module (included)</div>
                          )}
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
              {errors.selected_modules && (
                <p className="text-sm text-destructive mt-2">{errors.selected_modules.message}</p>
              )}
            </CardContent>
          </Card>

          {/* Billing Cycle */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <CreditCard className="h-5 w-5" />
                Billing Cycle
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <RadioGroup
                value={billingCycle}
                onValueChange={(value) => setValue('billing_cycle', value as 'monthly' | 'annual')}
              >
                <div className="flex items-center space-x-2 border rounded-lg p-4">
                  <RadioGroupItem value="monthly" id="monthly" />
                  <Label htmlFor="monthly" className="flex-1 cursor-pointer">
                    <div className="font-medium">Monthly</div>
                    <div className="text-sm text-muted-foreground">Pay monthly, cancel anytime</div>
                  </Label>
                  <div className="font-medium">${calculateTotal()}/mo</div>
                </div>
                <div className="flex items-center space-x-2 border rounded-lg p-4">
                  <RadioGroupItem value="annual" id="annual" />
                  <Label htmlFor="annual" className="flex-1 cursor-pointer">
                    <div className="font-medium">Annual</div>
                    <div className="text-sm text-muted-foreground">Save 20% with annual billing</div>
                  </Label>
                  <div className="font-medium">${calculateTotal()}/yr</div>
                </div>
              </RadioGroup>

              <div className="border-t pt-4">
                <div className="flex justify-between text-lg font-bold">
                  <span>Total:</span>
                  <span>${calculateTotal()}/{billingCycle === 'monthly' ? 'month' : 'year'}</span>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Submit */}
          <Button type="submit" className="w-full" size="lg" disabled={isLoading || subdomainAvailable === false}>
            {isLoading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
            Create My Tenant
          </Button>

          <p className="text-center text-sm text-muted-foreground">
            Already have an account?{' '}
            <Button variant="link" className="p-0" asChild>
              <a href="/login">Sign in</a>
            </Button>
          </p>
        </form>
      </div>
    </div>
  );
}
