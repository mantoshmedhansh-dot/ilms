'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { usePartnerStore, PartnerDashboardStats } from '@/lib/storefront/partner-store';
import { partnerApi } from '@/lib/storefront/partner-api';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Progress } from '@/components/ui/progress';
import { Badge } from '@/components/ui/badge';
import {
  ArrowRight,
  TrendingUp,
  Wallet,
  Package,
  Users,
  IndianRupee,
  Share2,
  Copy,
  Check,
} from 'lucide-react';
import { formatCurrency } from '@/lib/utils';

export default function PartnerDashboardPage() {
  const { partner, dashboardStats, setDashboardStats } = usePartnerStore();
  const [isLoading, setIsLoading] = useState(true);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    const fetchDashboard = async () => {
      try {
        const stats = await partnerApi.getDashboardStats();
        setDashboardStats(stats);
      } catch (error) {
        console.error('Failed to fetch dashboard:', error);
      } finally {
        setIsLoading(false);
      }
    };

    fetchDashboard();
  }, [setDashboardStats]);

  const copyReferralCode = () => {
    if (partner?.referral_code) {
      navigator.clipboard.writeText(partner.referral_code);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  if (isLoading) {
    return (
      <div className="space-y-6 animate-pulse">
        <div className="h-32 bg-gray-200 rounded-lg" />
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
          {[1, 2, 3, 4].map((i) => (
            <div key={i} className="h-28 bg-gray-200 rounded-lg" />
          ))}
        </div>
      </div>
    );
  }

  const stats: PartnerDashboardStats = dashboardStats || {
    total_referrals: 0,
    successful_conversions: 0,
    total_earnings: 0,
    pending_earnings: 0,
    paid_earnings: 0,
    current_tier: 'BRONZE',
    tier_progress: 0,
    this_month_orders: 0,
    this_month_earnings: 0,
  };

  return (
    <div className="space-y-6">
      {/* Welcome Card */}
      <Card className="bg-gradient-to-r from-primary/10 to-primary/5">
        <CardContent className="pt-6">
          <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
            <div>
              <h1 className="text-2xl font-bold">
                Welcome back, {partner?.full_name?.split(' ')[0]}!
              </h1>
              <p className="text-muted-foreground mt-1">
                Your referral code:{' '}
                <span className="font-mono font-semibold text-primary">
                  {partner?.referral_code}
                </span>
                <button
                  onClick={copyReferralCode}
                  className="ml-2 inline-flex items-center text-primary hover:text-primary/80"
                >
                  {copied ? (
                    <Check className="h-4 w-4" />
                  ) : (
                    <Copy className="h-4 w-4" />
                  )}
                </button>
              </p>
            </div>
            <div className="flex gap-2">
              <Button asChild>
                <Link href="/partner/products">
                  <Share2 className="mr-2 h-4 w-4" />
                  Share Products
                </Link>
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Stats Grid */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Earnings</CardTitle>
            <Wallet className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {formatCurrency(stats.total_earnings)}
            </div>
            <p className="text-xs text-muted-foreground">
              {formatCurrency(stats.pending_earnings)} pending
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">This Month</CardTitle>
            <TrendingUp className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {formatCurrency(stats.this_month_earnings)}
            </div>
            <p className="text-xs text-muted-foreground">
              {stats.this_month_orders} orders
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Referrals</CardTitle>
            <Users className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{stats.total_referrals}</div>
            <p className="text-xs text-muted-foreground">
              {stats.successful_conversions} converted
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Paid Out</CardTitle>
            <IndianRupee className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {formatCurrency(stats.paid_earnings)}
            </div>
            <p className="text-xs text-muted-foreground">Total received</p>
          </CardContent>
        </Card>
      </div>

      {/* Tier Progress & Quick Actions */}
      <div className="grid gap-6 md:grid-cols-2">
        {/* Tier Progress */}
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle>Partner Tier</CardTitle>
              <Badge variant="outline" className="text-lg font-semibold">
                {stats.current_tier}
              </Badge>
            </div>
            <CardDescription>
              {stats.next_tier
                ? `Progress towards ${stats.next_tier}`
                : 'You have reached the highest tier!'}
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              <Progress value={stats.tier_progress} className="h-3" />
              <p className="text-sm text-muted-foreground">
                {stats.tier_progress}% complete
              </p>
            </div>
            <div className="mt-4 p-4 bg-muted rounded-lg">
              <h4 className="font-medium mb-2">Tier Benefits</h4>
              <ul className="text-sm text-muted-foreground space-y-1">
                <li>
                  {stats.current_tier === 'BRONZE' && '10% commission on all sales'}
                  {stats.current_tier === 'SILVER' && '12% commission on all sales'}
                  {stats.current_tier === 'GOLD' && '14% commission on all sales'}
                  {stats.current_tier === 'PLATINUM' && '15% commission on all sales'}
                </li>
                <li>Priority support</li>
                {(stats.current_tier === 'GOLD' || stats.current_tier === 'PLATINUM') && (
                  <li>Exclusive product access</li>
                )}
                {stats.current_tier === 'PLATINUM' && <li>Dedicated account manager</li>}
              </ul>
            </div>
          </CardContent>
        </Card>

        {/* Quick Actions */}
        <Card>
          <CardHeader>
            <CardTitle>Quick Actions</CardTitle>
            <CardDescription>Common tasks to boost your earnings</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <Link
              href="/partner/products"
              className="flex items-center justify-between p-4 rounded-lg border hover:bg-muted transition-colors"
            >
              <div className="flex items-center gap-3">
                <div className="p-2 bg-primary/10 rounded-lg">
                  <Package className="h-5 w-5 text-primary" />
                </div>
                <div>
                  <p className="font-medium">Share Products</p>
                  <p className="text-sm text-muted-foreground">
                    Generate referral links
                  </p>
                </div>
              </div>
              <ArrowRight className="h-5 w-5 text-muted-foreground" />
            </Link>

            <Link
              href="/partner/earnings"
              className="flex items-center justify-between p-4 rounded-lg border hover:bg-muted transition-colors"
            >
              <div className="flex items-center gap-3">
                <div className="p-2 bg-green-100 rounded-lg">
                  <Wallet className="h-5 w-5 text-green-600" />
                </div>
                <div>
                  <p className="font-medium">View Earnings</p>
                  <p className="text-sm text-muted-foreground">
                    Track your commissions
                  </p>
                </div>
              </div>
              <ArrowRight className="h-5 w-5 text-muted-foreground" />
            </Link>

            <Link
              href="/partner/payouts"
              className="flex items-center justify-between p-4 rounded-lg border hover:bg-muted transition-colors"
            >
              <div className="flex items-center gap-3">
                <div className="p-2 bg-blue-100 rounded-lg">
                  <IndianRupee className="h-5 w-5 text-blue-600" />
                </div>
                <div>
                  <p className="font-medium">Request Payout</p>
                  <p className="text-sm text-muted-foreground">
                    Withdraw your earnings
                  </p>
                </div>
              </div>
              <ArrowRight className="h-5 w-5 text-muted-foreground" />
            </Link>
          </CardContent>
        </Card>
      </div>

      {/* KYC Alert if not verified */}
      {partner?.kyc_status !== 'VERIFIED' && (
        <Card className="border-yellow-200 bg-yellow-50">
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="font-medium text-yellow-800">Complete Your KYC</h3>
                <p className="text-sm text-yellow-700">
                  Submit your documents to start receiving payouts
                </p>
              </div>
              <Button asChild variant="outline" className="border-yellow-300">
                <Link href="/partner/kyc">Complete KYC</Link>
              </Button>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
