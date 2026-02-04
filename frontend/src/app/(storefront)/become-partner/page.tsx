'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import { partnerAuthApi } from '@/lib/storefront/partner-api';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Checkbox } from '@/components/ui/checkbox';
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import { Alert, AlertDescription } from '@/components/ui/alert';
import {
  Loader2,
  User,
  Phone,
  Mail,
  MapPin,
  Gift,
  CheckCircle,
  ArrowRight,
  Wallet,
  Share2,
  TrendingUp,
  BadgeCheck,
  IndianRupee,
  Users,
  Clock,
  Headphones,
} from 'lucide-react';
import { Badge } from '@/components/ui/badge';

// Icon mapping for dynamic icons from CMS
const iconMap: Record<string, React.ElementType> = {
  Wallet,
  Share2,
  TrendingUp,
};

// Default content (used as fallback if CMS settings not configured)
const defaultContent = {
  hero_title: 'Become an ILMS.AI Partner',
  hero_subtitle: 'Join India\'s fastest-growing water purifier partner network. Zero investment required, unlimited earning potential with 10-15% commission on every sale!',
  benefit_1_title: 'High Commission',
  benefit_1_description: 'Earn 10-15% commission on every successful sale. No caps, no limits!',
  benefit_1_icon: 'Wallet',
  benefit_2_title: 'Easy to Share',
  benefit_2_description: 'Share product links via WhatsApp, social media, or personal network',
  benefit_2_icon: 'Share2',
  benefit_3_title: 'Grow Your Earnings',
  benefit_3_description: 'Unlock higher commission tiers as you grow. Top partners earn ₹1 Lakh+/month',
  benefit_3_icon: 'TrendingUp',
  form_title: 'Partner Registration',
  form_subtitle: 'Join 5,000+ active partners earning with ILMS.AI',
  success_title: 'Welcome to ILMS.AI Partner Network!',
  success_message: 'Your partner application has been approved. You can now login with your mobile number and start earning!',
};

// Additional benefits to display
const additionalBenefits = [
  'Weekly commission payouts directly to your bank',
  'Dedicated partner support team',
  'Marketing materials & product training',
  'Real-time sales tracking dashboard',
  'Special partner-exclusive deals',
  'No inventory or logistics hassle',
];

interface PageContent {
  hero_title: string;
  hero_subtitle: string;
  benefit_1_title: string;
  benefit_1_description: string;
  benefit_1_icon: string;
  benefit_2_title: string;
  benefit_2_description: string;
  benefit_2_icon: string;
  benefit_3_title: string;
  benefit_3_description: string;
  benefit_3_icon: string;
  form_title: string;
  form_subtitle: string;
  success_title: string;
  success_message: string;
}

export default function BecomePartnerPage() {
  const [content, setContent] = useState<PageContent>(defaultContent);
  const [contentLoading, setContentLoading] = useState(true);

  const [formData, setFormData] = useState({
    full_name: '',
    mobile: '',
    email: '',
    city: '',
    pincode: '',
    referral_code: '',
  });
  const [acceptTerms, setAcceptTerms] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

  // Fetch CMS content on mount (using public storefront endpoint)
  useEffect(() => {
    const fetchContent = async () => {
      try {
        // Use the public storefront settings endpoint (no auth required)
        const response = await fetch(
          `${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/api/v1/storefront/settings?group=partner_page`
        );

        if (response.ok) {
          // Response is a flat key-value object: {partner_page_hero_title: "...", ...}
          const data = await response.json();

          if (Object.keys(data).length > 0) {
            const newContent = { ...defaultContent };
            Object.entries(data).forEach(([settingKey, settingValue]) => {
              const key = settingKey.replace('partner_page_', '') as keyof PageContent;
              if (key in defaultContent && settingValue) {
                newContent[key] = settingValue as string;
              }
            });
            setContent(newContent);
          }
        }
      } catch (err) {
        // Use default content on error
        console.log('Using default content');
      } finally {
        setContentLoading(false);
      }
    };

    fetchContent();
  }, []);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target;
    setFormData((prev) => ({ ...prev, [name]: value }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!acceptTerms) {
      setError('Please accept the terms and conditions');
      return;
    }

    setError(null);
    setIsSubmitting(true);

    try {
      // Format mobile number
      const formattedMobile = formData.mobile.startsWith('+91')
        ? formData.mobile
        : formData.mobile.startsWith('91')
        ? '+' + formData.mobile
        : '+91' + formData.mobile.replace(/\D/g, '');

      const response = await partnerAuthApi.register({
        full_name: formData.full_name,
        phone: formattedMobile,
        email: formData.email || undefined,
        city: formData.city || undefined,
        pincode: formData.pincode || undefined,
        referred_by_code: formData.referral_code || undefined,
      });

      // API returns partner object on success, check for id to confirm
      if (response && (response.id || response.partner_id)) {
        setSuccess(true);
      } else if (response && response.success === false) {
        setError(response.message || 'Registration failed');
      } else {
        // Assume success if we got a response without explicit failure
        setSuccess(true);
      }
    } catch (err: unknown) {
      const errorMessage =
        err instanceof Error
          ? (err as { response?: { data?: { detail?: string } } }).response?.data?.detail ||
            err.message
          : 'Registration failed. Please try again.';
      setError(errorMessage);
    } finally {
      setIsSubmitting(false);
    }
  };

  // Build benefits array from content
  const benefits = [
    {
      icon: iconMap[content.benefit_1_icon] || Wallet,
      title: content.benefit_1_title,
      description: content.benefit_1_description,
      href: '#registration',
    },
    {
      icon: iconMap[content.benefit_2_icon] || Share2,
      title: content.benefit_2_title,
      description: content.benefit_2_description,
      href: '/partner/products',
    },
    {
      icon: iconMap[content.benefit_3_icon] || TrendingUp,
      title: content.benefit_3_title,
      description: content.benefit_3_description,
      href: '/partner',
    },
  ];

  if (success) {
    return (
      <div className="min-h-[60vh] flex items-center justify-center py-12 px-4">
        <Card className="w-full max-w-md text-center">
          <CardContent className="pt-8">
            <div className="mx-auto w-16 h-16 bg-green-100 rounded-full flex items-center justify-center mb-4">
              <CheckCircle className="h-8 w-8 text-green-600" />
            </div>
            <h2 className="text-2xl font-bold mb-2">{content.success_title}</h2>
            <p className="text-muted-foreground mb-6">
              {content.success_message}
            </p>
            <Button asChild className="w-full">
              <Link href="/partner/login">
                Login to Partner Portal
                <ArrowRight className="ml-2 h-4 w-4" />
              </Link>
            </Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="min-h-[60vh] py-12 px-4">
      <div className="max-w-5xl mx-auto">
        {/* Header */}
        <div className="text-center mb-8">
          <Badge className="mb-4 bg-primary/10 text-primary hover:bg-primary/10">
            <Users className="h-3 w-3 mr-1" />
            Partner Program
          </Badge>
          <h1 className="text-3xl md:text-4xl font-bold mb-4">
            {contentLoading ? (
              <span className="animate-pulse bg-muted rounded h-10 w-96 inline-block" />
            ) : (
              content.hero_title
            )}
          </h1>
          <p className="text-lg text-muted-foreground max-w-2xl mx-auto mb-6">
            {contentLoading ? (
              <span className="animate-pulse bg-muted rounded h-6 w-full inline-block" />
            ) : (
              content.hero_subtitle
            )}
          </p>

          {/* Quick Stats */}
          <div className="flex flex-wrap justify-center gap-6 mt-6">
            <div className="flex items-center gap-2 text-sm">
              <div className="w-8 h-8 rounded-full bg-green-100 flex items-center justify-center">
                <IndianRupee className="h-4 w-4 text-green-600" />
              </div>
              <div className="text-left">
                <p className="font-semibold text-green-600">₹50 Lakh+</p>
                <p className="text-xs text-muted-foreground">Paid to Partners</p>
              </div>
            </div>
            <div className="flex items-center gap-2 text-sm">
              <div className="w-8 h-8 rounded-full bg-blue-100 flex items-center justify-center">
                <Users className="h-4 w-4 text-blue-600" />
              </div>
              <div className="text-left">
                <p className="font-semibold text-blue-600">5,000+</p>
                <p className="text-xs text-muted-foreground">Active Partners</p>
              </div>
            </div>
            <div className="flex items-center gap-2 text-sm">
              <div className="w-8 h-8 rounded-full bg-orange-100 flex items-center justify-center">
                <TrendingUp className="h-4 w-4 text-orange-600" />
              </div>
              <div className="text-left">
                <p className="font-semibold text-orange-600">15%</p>
                <p className="text-xs text-muted-foreground">Max Commission</p>
              </div>
            </div>
          </div>
        </div>

        {/* Main Benefits */}
        <div className="grid md:grid-cols-3 gap-6 mb-8">
          {benefits.map((benefit) => (
            <Link key={benefit.title} href={benefit.href}>
              <Card className="text-center h-full cursor-pointer hover:shadow-lg hover:border-primary/50 transition-all duration-200">
                <CardContent className="pt-6">
                  <div className="mx-auto w-12 h-12 bg-primary/10 rounded-full flex items-center justify-center mb-4">
                    <benefit.icon className="h-6 w-6 text-primary" />
                  </div>
                  <h3 className="font-semibold mb-2">{benefit.title}</h3>
                  <p className="text-sm text-muted-foreground">{benefit.description}</p>
                </CardContent>
              </Card>
            </Link>
          ))}
        </div>

        {/* Additional Benefits */}
        <Card className="mb-8 bg-gradient-to-r from-primary/5 to-secondary/5">
          <CardContent className="py-6">
            <h3 className="font-semibold text-center mb-4">Why Partners Love ILMS.AI</h3>
            <div className="grid sm:grid-cols-2 md:grid-cols-3 gap-3">
              {additionalBenefits.map((benefit, index) => (
                <div key={index} className="flex items-center gap-2 text-sm">
                  <CheckCircle className="h-4 w-4 text-green-500 shrink-0" />
                  <span>{benefit}</span>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        {/* Registration Form */}
        <Card id="registration" className="max-w-md mx-auto scroll-mt-20">
          <CardHeader>
            <CardTitle>{content.form_title}</CardTitle>
            <CardDescription>{content.form_subtitle}</CardDescription>
          </CardHeader>

          <form onSubmit={handleSubmit}>
            <CardContent className="space-y-4">
              {error && (
                <Alert variant="destructive">
                  <AlertDescription>{error}</AlertDescription>
                </Alert>
              )}

              <div className="space-y-2">
                <Label htmlFor="full_name">Full Name *</Label>
                <div className="relative">
                  <User className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                  <Input
                    id="full_name"
                    name="full_name"
                    placeholder="Enter your full name"
                    value={formData.full_name}
                    onChange={handleChange}
                    className="pl-10"
                    required
                    disabled={isSubmitting}
                  />
                </div>
              </div>

              <div className="space-y-2">
                <Label htmlFor="mobile">Mobile Number *</Label>
                <div className="relative">
                  <Phone className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                  <Input
                    id="mobile"
                    name="mobile"
                    type="tel"
                    placeholder="10-digit mobile number"
                    value={formData.mobile}
                    onChange={handleChange}
                    className="pl-10"
                    required
                    pattern="[0-9+]{10,13}"
                    disabled={isSubmitting}
                  />
                </div>
              </div>

              <div className="space-y-2">
                <Label htmlFor="email">Email (Optional)</Label>
                <div className="relative">
                  <Mail className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                  <Input
                    id="email"
                    name="email"
                    type="email"
                    placeholder="your@email.com"
                    value={formData.email}
                    onChange={handleChange}
                    className="pl-10"
                    disabled={isSubmitting}
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="city">City</Label>
                  <div className="relative">
                    <MapPin className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                    <Input
                      id="city"
                      name="city"
                      placeholder="Your city"
                      value={formData.city}
                      onChange={handleChange}
                      className="pl-10"
                      disabled={isSubmitting}
                    />
                  </div>
                </div>

                <div className="space-y-2">
                  <Label htmlFor="pincode">Pincode</Label>
                  <Input
                    id="pincode"
                    name="pincode"
                    placeholder="123456"
                    value={formData.pincode}
                    onChange={handleChange}
                    pattern="[0-9]{6}"
                    maxLength={6}
                    disabled={isSubmitting}
                  />
                </div>
              </div>

              <div className="space-y-2">
                <Label htmlFor="referral_code">Referral Code (Optional)</Label>
                <div className="relative">
                  <Gift className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                  <Input
                    id="referral_code"
                    name="referral_code"
                    placeholder="If referred by someone"
                    value={formData.referral_code}
                    onChange={handleChange}
                    className="pl-10"
                    disabled={isSubmitting}
                  />
                </div>
              </div>

              <div className="flex items-start space-x-2">
                <Checkbox
                  id="terms"
                  checked={acceptTerms}
                  onCheckedChange={(checked) => setAcceptTerms(checked as boolean)}
                  disabled={isSubmitting}
                />
                <Label htmlFor="terms" className="text-sm font-normal leading-none">
                  I agree to the{' '}
                  <Link href="/terms" className="text-primary hover:underline">
                    Terms of Service
                  </Link>{' '}
                  and{' '}
                  <Link href="/privacy" className="text-primary hover:underline">
                    Privacy Policy
                  </Link>
                </Label>
              </div>
            </CardContent>

            <CardFooter className="flex flex-col gap-4">
              <Button type="submit" className="w-full" disabled={isSubmitting}>
                {isSubmitting ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    Registering...
                  </>
                ) : (
                  <>
                    Register as Partner
                    <ArrowRight className="ml-2 h-4 w-4" />
                  </>
                )}
              </Button>

              <p className="text-sm text-center text-muted-foreground">
                Already a partner?{' '}
                <Link href="/partner/login" className="text-primary hover:underline">
                  Login here
                </Link>
              </p>
            </CardFooter>
          </form>
        </Card>

        {/* How It Works */}
        <Card className="mt-8">
          <CardHeader>
            <CardTitle className="text-center">How Partner Program Works</CardTitle>
            <CardDescription className="text-center">
              Start earning in 3 simple steps
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid md:grid-cols-3 gap-6">
              <div className="text-center">
                <div className="w-12 h-12 rounded-full bg-primary text-primary-foreground flex items-center justify-center mx-auto mb-3 text-lg font-bold">
                  1
                </div>
                <h4 className="font-semibold mb-1">Register Free</h4>
                <p className="text-sm text-muted-foreground">
                  Fill the form above. Get approved instantly and access your partner dashboard.
                </p>
              </div>
              <div className="text-center">
                <div className="w-12 h-12 rounded-full bg-primary text-primary-foreground flex items-center justify-center mx-auto mb-3 text-lg font-bold">
                  2
                </div>
                <h4 className="font-semibold mb-1">Share Products</h4>
                <p className="text-sm text-muted-foreground">
                  Get unique referral links. Share with your network via WhatsApp, social media, or in-person.
                </p>
              </div>
              <div className="text-center">
                <div className="w-12 h-12 rounded-full bg-primary text-primary-foreground flex items-center justify-center mx-auto mb-3 text-lg font-bold">
                  3
                </div>
                <h4 className="font-semibold mb-1">Earn Commission</h4>
                <p className="text-sm text-muted-foreground">
                  When someone buys using your link, earn 10-15% commission. Weekly payouts to your bank.
                </p>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Commission Tiers */}
        <Card className="mt-8">
          <CardHeader>
            <CardTitle className="text-center">Commission Tiers</CardTitle>
            <CardDescription className="text-center">
              Sell more, earn more! Unlock higher tiers as you grow
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid sm:grid-cols-3 gap-4">
              <Card className="border-2">
                <CardContent className="pt-6 text-center">
                  <Badge variant="secondary" className="mb-3">Bronze</Badge>
                  <p className="text-3xl font-bold text-primary mb-1">10%</p>
                  <p className="text-sm text-muted-foreground mb-3">Commission</p>
                  <p className="text-xs text-muted-foreground">0-5 sales/month</p>
                </CardContent>
              </Card>
              <Card className="border-2 border-primary">
                <CardContent className="pt-6 text-center">
                  <Badge className="mb-3 bg-primary">Silver</Badge>
                  <p className="text-3xl font-bold text-primary mb-1">12%</p>
                  <p className="text-sm text-muted-foreground mb-3">Commission</p>
                  <p className="text-xs text-muted-foreground">6-15 sales/month</p>
                </CardContent>
              </Card>
              <Card className="border-2 border-secondary">
                <CardContent className="pt-6 text-center">
                  <Badge className="mb-3 bg-secondary text-secondary-foreground">Gold</Badge>
                  <p className="text-3xl font-bold text-secondary mb-1">15%</p>
                  <p className="text-sm text-muted-foreground mb-3">Commission</p>
                  <p className="text-xs text-muted-foreground">16+ sales/month</p>
                </CardContent>
              </Card>
            </div>
          </CardContent>
        </Card>

        {/* Support Info */}
        <Card className="mt-8 bg-muted/50">
          <CardContent className="py-6">
            <div className="flex flex-col md:flex-row items-center gap-4 text-center md:text-left">
              <div className="p-3 bg-primary/10 rounded-full">
                <Headphones className="h-6 w-6 text-primary" />
              </div>
              <div className="flex-1">
                <h3 className="font-semibold">Partner Support Available</h3>
                <p className="text-sm text-muted-foreground">
                  Have questions? Our partner support team is here to help you succeed.
                </p>
              </div>
              <div className="flex gap-2">
                <Button variant="outline" asChild>
                  <a
                    href="https://wa.me/919311939076?text=Hi, I have a question about the partner program"
                    target="_blank"
                    rel="noopener noreferrer"
                  >
                    WhatsApp Support
                  </a>
                </Button>
                <Button variant="outline" asChild>
                  <a href="mailto:partners@ilms.ai">
                    Email Us
                  </a>
                </Button>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
