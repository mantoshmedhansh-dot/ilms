'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { ArrowLeft, Loader2, Save, User, Phone, Check } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { toast } from 'sonner';
import { useAuthStore, useIsAuthenticated, useCustomer } from '@/lib/storefront/auth-store';
import { authApi } from '@/lib/storefront/api';

export default function ProfilePage() {
  const router = useRouter();
  const isAuthenticated = useIsAuthenticated();
  const customer = useCustomer();
  const updateProfile = useAuthStore((state) => state.updateProfile);

  const [loading, setLoading] = useState(false);
  const [formData, setFormData] = useState({
    first_name: '',
    last_name: '',
    email: '',
  });
  const [errors, setErrors] = useState<Record<string, string>>({});

  // Phone change state
  const [showPhoneChange, setShowPhoneChange] = useState(false);
  const [phoneChangeStep, setPhoneChangeStep] = useState<'phone' | 'otp'>('phone');
  const [newPhone, setNewPhone] = useState('');
  const [otp, setOtp] = useState('');
  const [phoneLoading, setPhoneLoading] = useState(false);
  const [resendTimer, setResendTimer] = useState(0);

  useEffect(() => {
    if (!isAuthenticated) {
      router.replace('/account/login');
      return;
    }

    if (customer) {
      setFormData({
        first_name: customer.first_name || '',
        last_name: customer.last_name || '',
        email: customer.email || '',
      });
    }
  }, [isAuthenticated, customer, router]);

  const validateForm = () => {
    const newErrors: Record<string, string> = {};

    if (!formData.first_name.trim()) {
      newErrors.first_name = 'First name is required';
    }

    if (formData.email && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(formData.email)) {
      newErrors.email = 'Enter a valid email address';
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!validateForm()) return;

    setLoading(true);
    try {
      const updatedProfile = await authApi.updateProfile({
        first_name: formData.first_name,
        last_name: formData.last_name || undefined,
        email: formData.email || undefined,
      });

      updateProfile(updatedProfile);
      toast.success('Profile updated successfully');
      router.push('/account');
    } catch (error: any) {
      toast.error(error.response?.data?.detail || 'Failed to update profile');
    } finally {
      setLoading(false);
    }
  };

  // Phone change handlers
  const handleRequestPhoneChange = async () => {
    if (!newPhone || newPhone.length !== 10) {
      toast.error('Please enter a valid 10-digit phone number');
      return;
    }

    if (newPhone === customer?.phone) {
      toast.error('New phone number must be different from current');
      return;
    }

    setPhoneLoading(true);
    try {
      const response = await authApi.requestPhoneChange(newPhone);
      if (response.success) {
        setPhoneChangeStep('otp');
        setResendTimer(response.resend_in_seconds || 30);
        toast.success('OTP sent to new phone number');
      } else {
        toast.error(response.message || 'Failed to send OTP');
      }
    } catch (error: any) {
      toast.error(error.response?.data?.detail || 'Failed to send OTP');
    } finally {
      setPhoneLoading(false);
    }
  };

  const handleVerifyPhoneChange = async () => {
    if (!otp || otp.length !== 6) {
      toast.error('Please enter a valid 6-digit OTP');
      return;
    }

    setPhoneLoading(true);
    try {
      const updatedProfile = await authApi.verifyPhoneChange(newPhone, otp);
      updateProfile(updatedProfile);
      toast.success('Phone number updated successfully');
      setShowPhoneChange(false);
      setPhoneChangeStep('phone');
      setNewPhone('');
      setOtp('');
    } catch (error: any) {
      toast.error(error.response?.data?.detail || 'Invalid OTP');
    } finally {
      setPhoneLoading(false);
    }
  };

  const handleClosePhoneDialog = () => {
    setShowPhoneChange(false);
    setPhoneChangeStep('phone');
    setNewPhone('');
    setOtp('');
  };

  // Resend timer countdown
  useEffect(() => {
    if (resendTimer > 0) {
      const timer = setTimeout(() => setResendTimer(resendTimer - 1), 1000);
      return () => clearTimeout(timer);
    }
  }, [resendTimer]);

  if (!isAuthenticated || !customer) {
    return (
      <div className="min-h-[60vh] flex items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
      </div>
    );
  }

  return (
    <div className="container mx-auto px-4 py-8 max-w-lg">
      <Link
        href="/account"
        className="inline-flex items-center text-sm text-muted-foreground hover:text-primary mb-6"
      >
        <ArrowLeft className="h-4 w-4 mr-1" />
        Back to Account
      </Link>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <User className="h-5 w-5" />
            Edit Profile
          </CardTitle>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="grid gap-4 sm:grid-cols-2">
              <div className="space-y-2">
                <Label htmlFor="first_name">First Name *</Label>
                <Input
                  id="first_name"
                  value={formData.first_name}
                  onChange={(e) => {
                    setFormData({ ...formData, first_name: e.target.value });
                    setErrors({ ...errors, first_name: '' });
                  }}
                  className={errors.first_name ? 'border-red-500' : ''}
                />
                {errors.first_name && (
                  <p className="text-sm text-red-500">{errors.first_name}</p>
                )}
              </div>

              <div className="space-y-2">
                <Label htmlFor="last_name">Last Name</Label>
                <Input
                  id="last_name"
                  value={formData.last_name}
                  onChange={(e) =>
                    setFormData({ ...formData, last_name: e.target.value })
                  }
                />
              </div>
            </div>

            <div className="space-y-2">
              <Label htmlFor="phone">Phone Number</Label>
              <div className="flex gap-2">
                <Input
                  id="phone"
                  value={`+91 ${customer.phone}`}
                  disabled
                  className="bg-muted flex-1"
                />
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={() => setShowPhoneChange(true)}
                >
                  <Phone className="h-4 w-4 mr-1" />
                  Change
                </Button>
              </div>
            </div>

            <div className="space-y-2">
              <Label htmlFor="email">Email Address</Label>
              <Input
                id="email"
                type="email"
                value={formData.email}
                onChange={(e) => {
                  setFormData({ ...formData, email: e.target.value });
                  setErrors({ ...errors, email: '' });
                }}
                placeholder="your@email.com"
                className={errors.email ? 'border-red-500' : ''}
              />
              {errors.email && (
                <p className="text-sm text-red-500">{errors.email}</p>
              )}
            </div>

            <div className="flex gap-4 pt-4">
              <Button type="submit" disabled={loading} className="flex-1">
                {loading ? (
                  <>
                    <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                    Saving...
                  </>
                ) : (
                  <>
                    <Save className="h-4 w-4 mr-2" />
                    Save Changes
                  </>
                )}
              </Button>
              <Button
                type="button"
                variant="outline"
                onClick={() => router.push('/account')}
              >
                Cancel
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>

      {/* Phone Change Dialog */}
      <Dialog open={showPhoneChange} onOpenChange={handleClosePhoneDialog}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>Change Phone Number</DialogTitle>
            <DialogDescription>
              {phoneChangeStep === 'phone'
                ? 'Enter your new phone number. We will send an OTP to verify.'
                : `Enter the 6-digit OTP sent to +91 ${newPhone}`}
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4 py-4">
            {phoneChangeStep === 'phone' ? (
              <>
                <div className="space-y-2">
                  <Label htmlFor="new_phone">New Phone Number</Label>
                  <div className="flex gap-2">
                    <span className="flex items-center px-3 bg-muted rounded-l-md border border-r-0 text-sm text-muted-foreground">
                      +91
                    </span>
                    <Input
                      id="new_phone"
                      value={newPhone}
                      onChange={(e) => setNewPhone(e.target.value.replace(/\D/g, '').slice(0, 10))}
                      placeholder="Enter 10-digit number"
                      className="rounded-l-none"
                      maxLength={10}
                    />
                  </div>
                </div>
                <Button
                  onClick={handleRequestPhoneChange}
                  disabled={phoneLoading || newPhone.length !== 10}
                  className="w-full"
                >
                  {phoneLoading ? (
                    <>
                      <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                      Sending OTP...
                    </>
                  ) : (
                    'Send OTP'
                  )}
                </Button>
              </>
            ) : (
              <>
                <div className="space-y-2">
                  <Label htmlFor="otp">Enter OTP</Label>
                  <Input
                    id="otp"
                    value={otp}
                    onChange={(e) => setOtp(e.target.value.replace(/\D/g, '').slice(0, 6))}
                    placeholder="Enter 6-digit OTP"
                    maxLength={6}
                    className="text-center text-lg tracking-widest"
                  />
                </div>
                <Button
                  onClick={handleVerifyPhoneChange}
                  disabled={phoneLoading || otp.length !== 6}
                  className="w-full"
                >
                  {phoneLoading ? (
                    <>
                      <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                      Verifying...
                    </>
                  ) : (
                    <>
                      <Check className="h-4 w-4 mr-2" />
                      Verify & Update
                    </>
                  )}
                </Button>
                <div className="text-center">
                  {resendTimer > 0 ? (
                    <p className="text-sm text-muted-foreground">
                      Resend OTP in {resendTimer}s
                    </p>
                  ) : (
                    <Button
                      variant="link"
                      size="sm"
                      onClick={handleRequestPhoneChange}
                      disabled={phoneLoading}
                    >
                      Resend OTP
                    </Button>
                  )}
                </div>
                <Button
                  variant="outline"
                  onClick={() => {
                    setPhoneChangeStep('phone');
                    setOtp('');
                  }}
                  className="w-full"
                >
                  Change Number
                </Button>
              </>
            )}
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
