'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import {
  Gift,
  Users,
  Share2,
  Copy,
  CheckCircle,
  IndianRupee,
  Clock,
  ChevronRight,
  Loader2,
  MessageCircle,
  Mail,
  Facebook,
  Twitter,
  Star,
  Sparkles,
  Wallet,
  MapPin,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Separator } from '@/components/ui/separator';
import { toast } from 'sonner';
import { useIsAuthenticated, useCustomer } from '@/lib/storefront/auth-store';
import { formatCurrency } from '@/lib/utils';
import { referralApi, ReferralStats } from '@/lib/storefront/api';

const referralBenefits = [
  {
    icon: Gift,
    title: 'You Earn ₹500',
    description: 'Cash reward for every successful referral that completes a purchase',
  },
  {
    icon: Users,
    title: 'Friend Saves 5%',
    description: 'Your friend enjoys 5% instant discount on their first water purifier',
  },
  {
    icon: IndianRupee,
    title: 'Unlimited Rewards',
    description: 'No limits! Refer as many friends as you want and earn unlimited cash',
  },
];

const howItWorks = [
  {
    step: 1,
    title: 'Get Your Code',
    description: 'Login to get your unique referral code. Share it via WhatsApp, SMS, or social media.',
  },
  {
    step: 2,
    title: 'Friend Shops & Saves',
    description: 'Your friend applies your code at checkout and gets 5% off their order instantly.',
  },
  {
    step: 3,
    title: 'You Get Paid',
    description: 'Once their order is delivered, ₹500 is credited to your account. Withdraw anytime!',
  },
];

// Success stories (testimonials)
const successStories = [
  {
    name: 'Rajesh K.',
    location: 'Delhi',
    referrals: 12,
    earned: '₹6,000',
    quote: 'I shared with my office colleagues. Everyone was looking for good water purifiers!',
  },
  {
    name: 'Priya M.',
    location: 'Mumbai',
    referrals: 8,
    earned: '₹4,000',
    quote: 'My society WhatsApp group was the perfect place to share. Easy money!',
  },
  {
    name: 'Amit S.',
    location: 'Bangalore',
    referrals: 23,
    earned: '₹11,500',
    quote: 'Great products sell themselves. I just shared the link!',
  },
];

export default function ReferralPage() {
  const router = useRouter();
  const isAuthenticated = useIsAuthenticated();
  const customer = useCustomer();
  const [stats, setStats] = useState<ReferralStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    if (!isAuthenticated) {
      // Allow viewing the page but show limited content
      setLoading(false);
      return;
    }

    // Fetch referral stats from API
    const fetchStats = async () => {
      try {
        const data = await referralApi.getMyReferralStats();
        setStats(data);
      } catch (error) {
        console.error('Failed to load referral data:', error);
        // Generate fallback referral code if API fails
        const code = customer
          ? `${customer.first_name?.toUpperCase().slice(0, 4) || 'AQUA'}${customer.phone?.slice(-4) || '2024'}`
          : 'AQUA2024';
        setStats({
          referral_code: code,
          total_referrals: 0,
          successful_referrals: 0,
          pending_referrals: 0,
          total_earnings: 0,
          pending_earnings: 0,
          referrals: [],
        });
      } finally {
        setLoading(false);
      }
    };

    fetchStats();
  }, [isAuthenticated, customer]);

  const copyCode = async () => {
    if (!stats) return;
    try {
      await navigator.clipboard.writeText(stats.referral_code);
      setCopied(true);
      toast.success('Referral code copied!');
      setTimeout(() => setCopied(false), 2000);
    } catch (error) {
      toast.error('Failed to copy code');
    }
  };

  const shareVia = (platform: string) => {
    if (!stats) return;

    const message = `Hey! Use my referral code ${stats.referral_code} to get 5% off on your first water purifier from ILMS.AI. Shop now at https://www.ilms.ai?ref=${stats.referral_code}`;
    const encodedMessage = encodeURIComponent(message);

    let url = '';
    switch (platform) {
      case 'whatsapp':
        url = `https://wa.me/?text=${encodedMessage}`;
        break;
      case 'facebook':
        url = `https://www.facebook.com/sharer/sharer.php?u=https://www.ilms.ai?ref=${stats.referral_code}&quote=${encodedMessage}`;
        break;
      case 'twitter':
        url = `https://twitter.com/intent/tweet?text=${encodedMessage}`;
        break;
      case 'email':
        url = `mailto:?subject=Get 5% off on ILMS.AI Water Purifiers&body=${encodedMessage}`;
        break;
    }

    if (url) {
      window.open(url, '_blank');
    }
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'completed':
        return <Badge className="bg-green-100 text-green-800">Completed</Badge>;
      case 'pending':
        return <Badge className="bg-yellow-100 text-yellow-800">Pending</Badge>;
      case 'expired':
        return <Badge className="bg-red-100 text-red-800">Expired</Badge>;
      default:
        return null;
    }
  };

  return (
    <div className="container mx-auto px-4 py-8 max-w-4xl">
      {/* Hero Section */}
      <div className="text-center mb-8">
        <div className="inline-flex items-center gap-2 bg-primary/10 text-primary px-4 py-2 rounded-full text-sm font-medium mb-4">
          <Gift className="h-4 w-4" />
          Refer & Earn
        </div>
        <h1 className="text-3xl md:text-4xl font-bold mb-4">
          Share Pure Water, Earn <span className="text-primary">₹500</span> Cash
        </h1>
        <p className="text-muted-foreground max-w-2xl mx-auto mb-6">
          Love your ILMS.AI water purifier? Share it with friends and family! They get 5% off their first purchase, and you earn ₹500 for every successful referral.
        </p>

        {/* Quick Stats */}
        <div className="inline-flex flex-wrap justify-center gap-4 bg-muted/50 rounded-lg px-6 py-3">
          <div className="flex items-center gap-2 text-sm">
            <Sparkles className="h-4 w-4 text-yellow-500" />
            <span><strong>₹5 Lakh+</strong> paid to customers</span>
          </div>
          <div className="w-px h-4 bg-border hidden sm:block" />
          <div className="flex items-center gap-2 text-sm">
            <Users className="h-4 w-4 text-primary" />
            <span><strong>10,000+</strong> referrals completed</span>
          </div>
        </div>
      </div>

      {/* Benefits */}
      <div className="grid md:grid-cols-3 gap-4 mb-8">
        {referralBenefits.map((benefit, index) => {
          const Icon = benefit.icon;
          return (
            <Card key={index}>
              <CardContent className="pt-6 text-center">
                <div className="w-12 h-12 rounded-full bg-primary/10 flex items-center justify-center mx-auto mb-3">
                  <Icon className="h-6 w-6 text-primary" />
                </div>
                <h3 className="font-semibold mb-1">{benefit.title}</h3>
                <p className="text-sm text-muted-foreground">{benefit.description}</p>
              </CardContent>
            </Card>
          );
        })}
      </div>

      {/* Referral Code Section */}
      {isAuthenticated && stats ? (
        <Card className="mb-8">
          <CardHeader>
            <CardTitle>Your Referral Code</CardTitle>
            <CardDescription>Share this code with friends to earn rewards</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="flex flex-col sm:flex-row gap-4 items-center">
              <div className="flex-1 w-full">
                <div className="flex">
                  <Input
                    value={stats.referral_code}
                    readOnly
                    className="text-lg font-mono font-bold text-center sm:text-left rounded-r-none"
                  />
                  <Button
                    variant="secondary"
                    className="rounded-l-none"
                    onClick={copyCode}
                  >
                    {copied ? (
                      <CheckCircle className="h-4 w-4" />
                    ) : (
                      <Copy className="h-4 w-4" />
                    )}
                  </Button>
                </div>
              </div>
              <Separator orientation="vertical" className="h-10 hidden sm:block" />
              <div className="flex gap-2">
                <Button
                  size="icon"
                  variant="outline"
                  className="bg-green-50 hover:bg-green-100 border-green-200"
                  onClick={() => shareVia('whatsapp')}
                  title="Share on WhatsApp"
                >
                  <MessageCircle className="h-4 w-4 text-green-600" />
                </Button>
                <Button
                  size="icon"
                  variant="outline"
                  className="bg-blue-50 hover:bg-blue-100 border-blue-200"
                  onClick={() => shareVia('facebook')}
                  title="Share on Facebook"
                >
                  <Facebook className="h-4 w-4 text-blue-600" />
                </Button>
                <Button
                  size="icon"
                  variant="outline"
                  className="bg-sky-50 hover:bg-sky-100 border-sky-200"
                  onClick={() => shareVia('twitter')}
                  title="Share on Twitter"
                >
                  <Twitter className="h-4 w-4 text-sky-500" />
                </Button>
                <Button
                  size="icon"
                  variant="outline"
                  onClick={() => shareVia('email')}
                  title="Share via Email"
                >
                  <Mail className="h-4 w-4" />
                </Button>
              </div>
            </div>

            {/* Stats */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mt-6 pt-6 border-t">
              <div className="text-center">
                <p className="text-2xl font-bold text-primary">{stats.total_referrals}</p>
                <p className="text-sm text-muted-foreground">Total Referrals</p>
              </div>
              <div className="text-center">
                <p className="text-2xl font-bold text-green-600">{stats.successful_referrals}</p>
                <p className="text-sm text-muted-foreground">Successful</p>
              </div>
              <div className="text-center">
                <p className="text-2xl font-bold text-yellow-600">{stats.pending_referrals}</p>
                <p className="text-sm text-muted-foreground">Pending</p>
              </div>
              <div className="text-center">
                <p className="text-2xl font-bold">{formatCurrency(stats.total_earnings)}</p>
                <p className="text-sm text-muted-foreground">Total Earned</p>
              </div>
            </div>
          </CardContent>
        </Card>
      ) : (
        <Card className="mb-8">
          <CardContent className="py-8 text-center">
            <Gift className="h-12 w-12 mx-auto text-primary mb-4" />
            <h3 className="text-lg font-semibold mb-2">Login to Get Your Referral Code</h3>
            <p className="text-muted-foreground mb-4">
              Create an account or login to start referring friends and earning rewards.
            </p>
            <Link href="/account/login?redirect=/referral">
              <Button>
                Login / Sign Up
                <ChevronRight className="h-4 w-4 ml-2" />
              </Button>
            </Link>
          </CardContent>
        </Card>
      )}

      {/* How It Works */}
      <Card className="mb-8">
        <CardHeader>
          <CardTitle>How It Works</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid md:grid-cols-3 gap-6">
            {howItWorks.map((item) => (
              <div key={item.step} className="relative">
                <div className="flex items-center gap-4 mb-2">
                  <div className="w-10 h-10 rounded-full bg-primary text-primary-foreground flex items-center justify-center font-bold">
                    {item.step}
                  </div>
                  <h4 className="font-semibold">{item.title}</h4>
                </div>
                <p className="text-sm text-muted-foreground ml-14">{item.description}</p>
                {item.step < 3 && (
                  <ChevronRight className="hidden md:block absolute top-3 -right-3 h-6 w-6 text-muted-foreground/50" />
                )}
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Referral History */}
      {isAuthenticated && stats && stats.referrals.length > 0 && (
        <Card className="mb-8">
          <CardHeader>
            <CardTitle>Referral History</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {stats.referrals.map((referral) => (
                <div
                  key={referral.id}
                  className="flex items-center justify-between py-3 border-b last:border-0"
                >
                  <div>
                    <p className="font-medium">{referral.referee_name}</p>
                    <p className="text-sm text-muted-foreground">
                      {new Date(referral.created_at).toLocaleDateString('en-IN', {
                        day: 'numeric',
                        month: 'short',
                        year: 'numeric',
                      })}
                    </p>
                  </div>
                  <div className="text-right">
                    {getStatusBadge(referral.status)}
                    {referral.reward_amount && (
                      <p className="text-sm font-medium text-green-600 mt-1">
                        +{formatCurrency(referral.reward_amount)}
                      </p>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Success Stories */}
      <Card className="mb-8">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Star className="h-5 w-5 text-yellow-500" />
            Success Stories
          </CardTitle>
          <CardDescription>
            See how other customers are earning with referrals
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid md:grid-cols-3 gap-4">
            {successStories.map((story, index) => (
              <Card key={index} className="bg-muted/30">
                <CardContent className="pt-4">
                  <div className="flex items-center gap-3 mb-3">
                    <div className="w-10 h-10 rounded-full bg-primary/10 flex items-center justify-center font-semibold text-primary">
                      {story.name.charAt(0)}
                    </div>
                    <div>
                      <p className="font-medium text-sm">{story.name}</p>
                      <p className="text-xs text-muted-foreground flex items-center gap-1">
                        <MapPin className="h-3 w-3" />
                        {story.location}
                      </p>
                    </div>
                  </div>
                  <p className="text-sm italic text-muted-foreground mb-3">&ldquo;{story.quote}&rdquo;</p>
                  <div className="flex justify-between text-sm pt-2 border-t">
                    <span className="text-muted-foreground">{story.referrals} referrals</span>
                    <span className="font-semibold text-green-600">{story.earned} earned</span>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* FAQ Section */}
      <Card className="mb-8">
        <CardHeader>
          <CardTitle className="text-base">Frequently Asked Questions</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div>
            <p className="font-medium text-sm mb-1">How do I get my referral code?</p>
            <p className="text-sm text-muted-foreground">
              Login to your account and your unique referral code will be displayed above. You can share it directly from there.
            </p>
          </div>
          <div>
            <p className="font-medium text-sm mb-1">When do I receive my reward?</p>
            <p className="text-sm text-muted-foreground">
              Your ₹500 reward is credited within 24 hours after your friend&apos;s order is successfully delivered.
            </p>
          </div>
          <div>
            <p className="font-medium text-sm mb-1">How can I use my rewards?</p>
            <p className="text-sm text-muted-foreground">
              Rewards can be used for your next purchase, or withdrawn to your bank account once you have ₹1,000 or more.
            </p>
          </div>
          <div>
            <p className="font-medium text-sm mb-1">Is there a limit on referrals?</p>
            <p className="text-sm text-muted-foreground">
              No limits! Refer as many friends as you want and earn ₹500 for each successful referral.
            </p>
          </div>
        </CardContent>
      </Card>

      {/* Terms */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Terms & Conditions</CardTitle>
        </CardHeader>
        <CardContent>
          <ul className="text-sm text-muted-foreground space-y-2">
            <li className="flex items-start gap-2">
              <CheckCircle className="h-4 w-4 text-green-500 mt-0.5 shrink-0" />
              <span>Referral reward of ₹500 is credited after the referred order is successfully delivered.</span>
            </li>
            <li className="flex items-start gap-2">
              <CheckCircle className="h-4 w-4 text-green-500 mt-0.5 shrink-0" />
              <span>The referred friend must be a new customer making their first purchase on ILMS.AI.</span>
            </li>
            <li className="flex items-start gap-2">
              <CheckCircle className="h-4 w-4 text-green-500 mt-0.5 shrink-0" />
              <span>Minimum order value of ₹10,000 is required for the referral reward to be valid.</span>
            </li>
            <li className="flex items-start gap-2">
              <CheckCircle className="h-4 w-4 text-green-500 mt-0.5 shrink-0" />
              <span>Rewards can be used on your next purchase or withdrawn to bank (minimum ₹1,000 for withdrawal).</span>
            </li>
            <li className="flex items-start gap-2">
              <CheckCircle className="h-4 w-4 text-green-500 mt-0.5 shrink-0" />
              <span>Self-referrals or fraudulent referrals will result in forfeiture of rewards and potential account suspension.</span>
            </li>
            <li className="flex items-start gap-2">
              <CheckCircle className="h-4 w-4 text-green-500 mt-0.5 shrink-0" />
              <span>ILMS.AI reserves the right to modify or terminate this program at any time with prior notice.</span>
            </li>
          </ul>
        </CardContent>
      </Card>

      {/* CTA for Non-Customers */}
      {!isAuthenticated && (
        <Card className="mt-8 bg-gradient-to-r from-primary/10 to-secondary/10 border-primary/20">
          <CardContent className="py-6 text-center">
            <h3 className="text-lg font-semibold mb-2">Not a Customer Yet?</h3>
            <p className="text-muted-foreground mb-4">
              Buy an ILMS.AI water purifier today and start referring your friends to earn rewards!
            </p>
            <Button asChild>
              <Link href="/products">
                Shop Water Purifiers
                <ChevronRight className="h-4 w-4 ml-2" />
              </Link>
            </Button>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
