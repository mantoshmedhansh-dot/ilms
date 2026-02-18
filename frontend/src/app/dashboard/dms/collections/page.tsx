'use client';

import { useQuery } from '@tanstack/react-query';
import {
  Banknote,
  AlertCircle,
  RefreshCw,
  IndianRupee,
  Users,
  TrendingDown,
  Clock,
} from 'lucide-react';

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import { Progress } from '@/components/ui/progress';
import { dmsApi } from '@/lib/api';
import { DMSCollections } from '@/types';

function formatCurrency(value: number | string | null | undefined): string {
  const num = Number(value) || 0;
  if (num >= 10000000) return `\u20B9${(num / 10000000).toFixed(1)}Cr`;
  if (num >= 100000) return `\u20B9${(num / 100000).toFixed(1)}L`;
  if (num >= 1000) return `\u20B9${(num / 1000).toFixed(1)}K`;
  return `\u20B9${num.toFixed(0)}`;
}

function getAgingColor(label: string): {
  bg: string;
  text: string;
  bar: string;
  badge: string;
} {
  if (label.includes('0-30') || label.includes('0 - 30')) {
    return {
      bg: 'bg-green-50',
      text: 'text-green-700',
      bar: 'bg-green-500',
      badge: 'bg-green-100 text-green-800',
    };
  }
  if (label.includes('31-60') || label.includes('31 - 60')) {
    return {
      bg: 'bg-yellow-50',
      text: 'text-yellow-700',
      bar: 'bg-yellow-500',
      badge: 'bg-yellow-100 text-yellow-800',
    };
  }
  if (label.includes('61-90') || label.includes('61 - 90')) {
    return {
      bg: 'bg-orange-50',
      text: 'text-orange-700',
      bar: 'bg-orange-500',
      badge: 'bg-orange-100 text-orange-800',
    };
  }
  // 90+ or anything else
  return {
    bg: 'bg-red-50',
    text: 'text-red-700',
    bar: 'bg-red-500',
    badge: 'bg-red-100 text-red-800',
  };
}

function getUtilizationColor(pct: number): string {
  if (pct >= 90) return 'text-red-600 font-semibold';
  if (pct >= 75) return 'text-orange-600 font-semibold';
  if (pct >= 50) return 'text-yellow-600';
  return 'text-green-600';
}

export default function DMSCollectionsPage() {
  const {
    data: collections,
    isLoading,
    refetch,
    isFetching,
  } = useQuery<DMSCollections>({
    queryKey: ['dms-collections'],
    queryFn: () => dmsApi.getCollections(),
    staleTime: 2 * 60 * 1000,
  });

  const agingBuckets = collections?.aging_buckets || [];
  const overdueDealers = collections?.overdue_dealers || [];
  const totalOutstanding = collections?.total_outstanding || 0;
  const totalOverdue = collections?.total_overdue || 0;
  const collectedMTD = collections?.collection_this_month || 0;
  const overdueCount = collections?.overdue_count || 0;

  // Calculate total across all aging buckets for percentage calculation
  const agingTotal = agingBuckets.reduce((sum, b) => sum + (b.amount || 0), 0);

  if (isLoading) {
    return (
      <div className="space-y-6 p-6">
        <Skeleton className="h-10 w-72" />
        <div className="grid gap-4 md:grid-cols-4">
          {[...Array(4)].map((_, i) => (
            <Skeleton key={i} className="h-24" />
          ))}
        </div>
        <Skeleton className="h-48" />
        <Skeleton className="h-96" />
      </div>
    );
  }

  return (
    <div className="space-y-6 p-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-amber-100 rounded-lg">
            <Banknote className="h-6 w-6 text-amber-600" />
          </div>
          <div>
            <h1 className="text-2xl font-bold tracking-tight">
              Collections & Aging
            </h1>
            <p className="text-muted-foreground">
              Monitor outstanding payments, overdue accounts, and aging buckets
            </p>
          </div>
        </div>
        <Button
          onClick={() => refetch()}
          disabled={isFetching}
          variant="outline"
          size="icon"
        >
          <RefreshCw
            className={`h-4 w-4 ${isFetching ? 'animate-spin' : ''}`}
          />
        </Button>
      </div>

      {/* KPI Cards */}
      <div className="grid gap-4 md:grid-cols-4">
        <Card className="border-l-4 border-l-blue-500">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-xs font-medium text-muted-foreground">
              Total Outstanding
            </CardTitle>
            <IndianRupee className="h-4 w-4 text-blue-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold tabular-nums">
              {formatCurrency(totalOutstanding)}
            </div>
            <p className="text-xs text-muted-foreground mt-1">
              Across all dealers
            </p>
          </CardContent>
        </Card>

        <Card className="border-l-4 border-l-red-500">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-xs font-medium text-muted-foreground">
              Total Overdue
            </CardTitle>
            <AlertCircle className="h-4 w-4 text-red-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold tabular-nums text-red-600">
              {formatCurrency(totalOverdue)}
            </div>
            <p className="text-xs text-muted-foreground mt-1">
              Past due date
            </p>
          </CardContent>
        </Card>

        <Card className="border-l-4 border-l-emerald-500">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-xs font-medium text-muted-foreground">
              Collected MTD
            </CardTitle>
            <TrendingDown className="h-4 w-4 text-emerald-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold tabular-nums text-emerald-600">
              {formatCurrency(collectedMTD)}
            </div>
            <p className="text-xs text-muted-foreground mt-1">
              This month
            </p>
          </CardContent>
        </Card>

        <Card className="border-l-4 border-l-orange-500">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-xs font-medium text-muted-foreground">
              Dealers Overdue
            </CardTitle>
            <Users className="h-4 w-4 text-orange-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold tabular-nums text-orange-600">
              {overdueCount}
            </div>
            <p className="text-xs text-muted-foreground mt-1">
              Need follow-up
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Aging Buckets Visualization */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <Clock className="h-5 w-5 text-muted-foreground" />
            Aging Buckets
          </CardTitle>
        </CardHeader>
        <CardContent>
          {agingBuckets.length > 0 ? (
            <div className="space-y-5">
              {agingBuckets.map((bucket, index) => {
                const colors = getAgingColor(bucket.label);
                const percentage =
                  agingTotal > 0
                    ? Math.round((bucket.amount / agingTotal) * 100)
                    : 0;

                return (
                  <div key={index} className="space-y-2">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-3">
                        <Badge
                          variant="outline"
                          className={`text-xs ${colors.badge}`}
                        >
                          {bucket.label} days
                        </Badge>
                        <span className="text-sm font-medium">
                          {formatCurrency(bucket.amount)}
                        </span>
                      </div>
                      <div className="flex items-center gap-3">
                        <span className="text-xs text-muted-foreground">
                          {bucket.count} dealer{bucket.count !== 1 ? 's' : ''}
                        </span>
                        <span className="text-sm font-semibold tabular-nums w-12 text-right">
                          {percentage}%
                        </span>
                      </div>
                    </div>
                    <div className="relative h-3 w-full overflow-hidden rounded-full bg-muted">
                      <div
                        className={`h-full rounded-full transition-all duration-500 ${colors.bar}`}
                        style={{ width: `${percentage}%` }}
                      />
                    </div>
                  </div>
                );
              })}

              {/* Summary row */}
              <div className="flex items-center justify-between pt-3 border-t">
                <span className="text-sm font-semibold text-muted-foreground">
                  Total Aging
                </span>
                <span className="text-sm font-bold tabular-nums">
                  {formatCurrency(agingTotal)}
                </span>
              </div>
            </div>
          ) : (
            <div className="text-center py-8">
              <Clock className="h-10 w-10 text-muted-foreground/50 mx-auto mb-3" />
              <p className="text-muted-foreground">
                No aging data available
              </p>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Overdue Dealers Table */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <AlertCircle className="h-5 w-5 text-red-500" />
            Overdue Dealers
            {overdueDealers.length > 0 && (
              <Badge variant="destructive" className="ml-2 text-xs">
                {overdueDealers.length}
              </Badge>
            )}
          </CardTitle>
        </CardHeader>
        <CardContent>
          {overdueDealers.length > 0 ? (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b text-left">
                    <th className="pb-3 font-medium text-muted-foreground">
                      Dealer Name
                    </th>
                    <th className="pb-3 font-medium text-muted-foreground">
                      Dealer Code
                    </th>
                    <th className="pb-3 font-medium text-muted-foreground text-right">
                      Outstanding
                    </th>
                    <th className="pb-3 font-medium text-muted-foreground text-right">
                      Overdue
                    </th>
                    <th className="pb-3 font-medium text-muted-foreground text-right">
                      Credit Limit
                    </th>
                    <th className="pb-3 font-medium text-muted-foreground text-center">
                      Utilization %
                    </th>
                    <th className="pb-3 font-medium text-muted-foreground text-right">
                      Last Payment Date
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {overdueDealers.map((dealer) => {
                    const utilPct = Number(dealer.utilization_pct) || 0;

                    return (
                      <tr
                        key={dealer.dealer_id}
                        className="border-b last:border-0 hover:bg-muted/50"
                      >
                        <td className="py-3">
                          <span className="font-medium">
                            {dealer.dealer_name}
                          </span>
                          {dealer.days_overdue > 0 && (
                            <Badge
                              variant="outline"
                              className="ml-2 text-[10px] bg-red-50 text-red-700"
                            >
                              {dealer.days_overdue}d overdue
                            </Badge>
                          )}
                        </td>
                        <td className="py-3 font-mono text-xs text-muted-foreground">
                          {dealer.dealer_code}
                        </td>
                        <td className="py-3 text-right tabular-nums font-semibold">
                          {formatCurrency(dealer.outstanding)}
                        </td>
                        <td className="py-3 text-right tabular-nums font-semibold text-red-600">
                          {formatCurrency(dealer.overdue)}
                        </td>
                        <td className="py-3 text-right tabular-nums text-muted-foreground">
                          {formatCurrency(dealer.credit_limit)}
                        </td>
                        <td className="py-3 text-center">
                          <div className="flex items-center justify-center gap-2">
                            <Progress
                              value={Math.min(utilPct, 100)}
                              className="w-16 h-2"
                            />
                            <span
                              className={`text-xs tabular-nums ${getUtilizationColor(utilPct)}`}
                            >
                              {utilPct.toFixed(0)}%
                            </span>
                          </div>
                        </td>
                        <td className="py-3 text-right text-muted-foreground text-xs">
                          {dealer.last_payment_date
                            ? new Date(
                                dealer.last_payment_date
                              ).toLocaleDateString('en-IN')
                            : 'N/A'}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          ) : (
            <div className="text-center py-12">
              <Users className="h-12 w-12 text-muted-foreground/50 mx-auto mb-3" />
              <p className="text-muted-foreground">
                No overdue dealers found
              </p>
              <p className="text-xs text-muted-foreground mt-1">
                All dealer payments are up to date
              </p>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
