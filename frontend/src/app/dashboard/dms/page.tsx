'use client';

import { useQuery } from '@tanstack/react-query';
import {
  Users,
  UserCheck,
  ShoppingCart,
  IndianRupee,
  Wallet,
  AlertCircle,
  RefreshCw,
  Truck,
  TrendingUp,
  ArrowRight,
  UserPlus,
} from 'lucide-react';
import Link from 'next/link';
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
  Legend,
} from 'recharts';

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import { Progress } from '@/components/ui/progress';
import { dmsApi } from '@/lib/api';
import { DMSDashboardResponse } from '@/types';

const REGION_COLORS = ['#6366f1', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#06b6d4', '#ec4899', '#84cc16'];

function formatCurrency(value: number | string | null | undefined): string {
  const num = Number(value) || 0;
  if (num >= 10000000) return `\u20B9${(num / 10000000).toFixed(1)}Cr`;
  if (num >= 100000) return `\u20B9${(num / 100000).toFixed(1)}L`;
  if (num >= 1000) return `\u20B9${(num / 1000).toFixed(1)}K`;
  return `\u20B9${num.toFixed(0)}`;
}

function formatNumber(value: number | string | null | undefined): string {
  const num = Number(value) || 0;
  if (num >= 100000) return `${(num / 100000).toFixed(1)}L`;
  if (num >= 1000) return `${(num / 1000).toFixed(1)}K`;
  return num.toFixed(0);
}

function getStatusColor(status: string): string {
  const colors: Record<string, string> = {
    NEW: 'bg-blue-100 text-blue-800',
    CONFIRMED: 'bg-indigo-100 text-indigo-800',
    SHIPPED: 'bg-purple-100 text-purple-800',
    DELIVERED: 'bg-green-100 text-green-800',
    CANCELLED: 'bg-red-100 text-red-800',
    PENDING_PAYMENT: 'bg-yellow-100 text-yellow-800',
  };
  return colors[status] || 'bg-gray-100 text-gray-800';
}

export default function DMSDashboardPage() {
  const { data, isLoading, refetch, isFetching } = useQuery<DMSDashboardResponse>({
    queryKey: ['dms-dashboard'],
    queryFn: () => dmsApi.getDashboard(),
    staleTime: 5 * 60 * 1000,
  });

  if (isLoading) {
    return (
      <div className="space-y-6 p-6">
        <Skeleton className="h-10 w-80" />
        <div className="grid gap-4 md:grid-cols-3 lg:grid-cols-6">
          {[...Array(6)].map((_, i) => <Skeleton key={i} className="h-28" />)}
        </div>
        <div className="grid gap-4 md:grid-cols-2">
          <Skeleton className="h-80" />
          <Skeleton className="h-80" />
        </div>
        <div className="grid gap-4 md:grid-cols-2">
          <Skeleton className="h-72" />
          <Skeleton className="h-72" />
        </div>
      </div>
    );
  }

  const summary = data?.summary;
  const monthlyTrend = data?.monthly_trend || [];
  const byRegion = data?.by_region || [];
  const topPerformers = data?.top_performers || [];
  const creditAlerts = data?.credit_alerts || [];
  const recentOrders = data?.recent_orders || [];

  return (
    <div className="space-y-6 p-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-indigo-100 rounded-lg">
            <Truck className="h-6 w-6 text-indigo-600" />
          </div>
          <div>
            <h1 className="text-2xl font-bold tracking-tight">Distribution Management</h1>
            <p className="text-muted-foreground">
              Monitor distributor performance, orders, and credit health
            </p>
          </div>
        </div>
        <div className="flex gap-2">
          <Link href="/dashboard/distribution/dealers">
            <Button variant="outline">
              <UserPlus className="h-4 w-4 mr-2" />
              Add Distributor
            </Button>
          </Link>
          <Button onClick={() => refetch()} disabled={isFetching} variant="outline" size="icon">
            <RefreshCw className={`h-4 w-4 ${isFetching ? 'animate-spin' : ''}`} />
          </Button>
        </div>
      </div>

      {/* KPI Summary Row */}
      <div className="grid gap-4 md:grid-cols-3 lg:grid-cols-6">
        <Card className="hover:shadow-md transition-shadow border-l-4 border-l-indigo-500">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-xs font-medium text-muted-foreground">Total Distributors</CardTitle>
            <div className="p-1.5 bg-indigo-50 rounded-md">
              <Users className="h-3.5 w-3.5 text-indigo-600" />
            </div>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold tabular-nums">{summary?.total_distributors || 0}</div>
            <p className="text-xs text-muted-foreground mt-1">
              {summary?.pending_approval || 0} pending approval
            </p>
          </CardContent>
        </Card>

        <Card className="hover:shadow-md transition-shadow border-l-4 border-l-emerald-500">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-xs font-medium text-muted-foreground">Active Distributors</CardTitle>
            <div className="p-1.5 bg-emerald-50 rounded-md">
              <UserCheck className="h-3.5 w-3.5 text-emerald-600" />
            </div>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold tabular-nums text-emerald-600">
              {summary?.active_distributors || 0}
            </div>
            <p className="text-xs text-muted-foreground mt-1">
              {summary?.total_distributors ? Math.round((summary.active_distributors / summary.total_distributors) * 100) : 0}% of total
            </p>
          </CardContent>
        </Card>

        <Card className="hover:shadow-md transition-shadow border-l-4 border-l-blue-500">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-xs font-medium text-muted-foreground">Orders MTD</CardTitle>
            <div className="p-1.5 bg-blue-50 rounded-md">
              <ShoppingCart className="h-3.5 w-3.5 text-blue-600" />
            </div>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold tabular-nums">{summary?.total_orders_mtd || 0}</div>
            <p className="text-xs text-muted-foreground mt-1">
              Avg: {formatCurrency(summary?.avg_order_value)}
            </p>
          </CardContent>
        </Card>

        <Card className="hover:shadow-md transition-shadow border-l-4 border-l-violet-500">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-xs font-medium text-muted-foreground">Revenue MTD</CardTitle>
            <div className="p-1.5 bg-violet-50 rounded-md">
              <IndianRupee className="h-3.5 w-3.5 text-violet-600" />
            </div>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold tabular-nums">{formatCurrency(summary?.revenue_mtd)}</div>
            <p className="text-xs text-muted-foreground mt-1">This month</p>
          </CardContent>
        </Card>

        <Card className="hover:shadow-md transition-shadow border-l-4 border-l-teal-500">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-xs font-medium text-muted-foreground">Collection MTD</CardTitle>
            <div className="p-1.5 bg-teal-50 rounded-md">
              <Wallet className="h-3.5 w-3.5 text-teal-600" />
            </div>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold tabular-nums">{formatCurrency(summary?.collection_mtd)}</div>
            <p className="text-xs text-muted-foreground mt-1">Payments received</p>
          </CardContent>
        </Card>

        <Card className="hover:shadow-md transition-shadow border-l-4 border-l-amber-500">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-xs font-medium text-muted-foreground">Outstanding</CardTitle>
            <div className="p-1.5 bg-amber-50 rounded-md">
              <AlertCircle className="h-3.5 w-3.5 text-amber-600" />
            </div>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold tabular-nums text-amber-600">
              {formatCurrency(summary?.total_outstanding)}
            </div>
            <p className="text-xs text-red-500 mt-1">
              Overdue: {formatCurrency(summary?.total_overdue)}
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Charts Row */}
      <div className="grid gap-4 md:grid-cols-2">
        {/* Monthly Trend */}
        <Card>
          <CardHeader>
            <CardTitle className="text-base flex items-center gap-2">
              <TrendingUp className="h-4 w-4 text-indigo-500" />
              Monthly Trend
            </CardTitle>
            <CardDescription>Revenue & Collection over last 12 months</CardDescription>
          </CardHeader>
          <CardContent>
            {monthlyTrend.length > 0 ? (
              <ResponsiveContainer width="100%" height={280}>
                <AreaChart data={monthlyTrend}>
                  <defs>
                    <linearGradient id="colorRevenue" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#6366f1" stopOpacity={0.3} />
                      <stop offset="95%" stopColor="#6366f1" stopOpacity={0} />
                    </linearGradient>
                    <linearGradient id="colorCollection" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#10b981" stopOpacity={0.3} />
                      <stop offset="95%" stopColor="#10b981" stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
                  <XAxis dataKey="month" tick={{ fontSize: 11 }} />
                  <YAxis tick={{ fontSize: 11 }} tickFormatter={(v) => formatCurrency(v)} />
                  <Tooltip
                    formatter={(value) => formatCurrency(value as number)}
                    labelStyle={{ fontWeight: 600 }}
                  />
                  <Area type="monotone" dataKey="revenue" stroke="#6366f1" fill="url(#colorRevenue)" name="Revenue" />
                  <Area type="monotone" dataKey="collection" stroke="#10b981" fill="url(#colorCollection)" name="Collection" />
                </AreaChart>
              </ResponsiveContainer>
            ) : (
              <div className="h-[280px] flex items-center justify-center text-muted-foreground text-sm">
                No trend data available yet
              </div>
            )}
          </CardContent>
        </Card>

        {/* Region Distribution */}
        <Card>
          <CardHeader>
            <CardTitle className="text-base flex items-center gap-2">
              <Users className="h-4 w-4 text-indigo-500" />
              Distributors by Region
            </CardTitle>
            <CardDescription>Geographic distribution of your network</CardDescription>
          </CardHeader>
          <CardContent>
            {byRegion.length > 0 ? (
              <ResponsiveContainer width="100%" height={280}>
                <PieChart>
                  <Pie
                    data={byRegion}
                    cx="50%"
                    cy="50%"
                    innerRadius={60}
                    outerRadius={100}
                    dataKey="count"
                    nameKey="region"
                    label={({ name, value }) => `${name} (${value})`}
                    labelLine={false}
                  >
                    {byRegion.map((_, index) => (
                      <Cell key={index} fill={REGION_COLORS[index % REGION_COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip formatter={(value) => value} />
                  <Legend />
                </PieChart>
              </ResponsiveContainer>
            ) : (
              <div className="h-[280px] flex items-center justify-center text-muted-foreground text-sm">
                No region data available yet
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Tables Row */}
      <div className="grid gap-4 md:grid-cols-2">
        {/* Top 10 Performers */}
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle className="text-base">Top 10 Performers</CardTitle>
              <Link href="/dashboard/distribution/dealers">
                <Button variant="ghost" size="sm" className="text-xs">
                  View All <ArrowRight className="h-3 w-3 ml-1" />
                </Button>
              </Link>
            </div>
            <CardDescription>By revenue this financial year</CardDescription>
          </CardHeader>
          <CardContent>
            {topPerformers.length > 0 ? (
              <div className="space-y-3">
                {topPerformers.map((performer, index) => (
                  <div key={performer.dealer_id} className="flex items-center gap-3">
                    <span className="text-xs font-bold text-muted-foreground w-5 text-right">
                      {index + 1}
                    </span>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center justify-between mb-1">
                        <span className="text-sm font-medium truncate">{performer.name}</span>
                        <span className="text-xs text-muted-foreground ml-2">{formatCurrency(performer.revenue)}</span>
                      </div>
                      <div className="flex items-center gap-2">
                        <Progress value={Math.min(performer.achievement_pct, 100)} className="h-1.5 flex-1" />
                        <span className="text-xs tabular-nums text-muted-foreground w-10 text-right">
                          {performer.achievement_pct.toFixed(0)}%
                        </span>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-sm text-muted-foreground text-center py-8">No performance data yet</p>
            )}
          </CardContent>
        </Card>

        {/* Credit Alerts */}
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle className="text-base flex items-center gap-2">
                Credit Alerts
                {creditAlerts.length > 0 && (
                  <Badge variant="destructive" className="text-[10px] px-1.5">{creditAlerts.length}</Badge>
                )}
              </CardTitle>
            </div>
            <CardDescription>Dealers with &gt;80% credit utilization</CardDescription>
          </CardHeader>
          <CardContent>
            {creditAlerts.length > 0 ? (
              <div className="space-y-3">
                {creditAlerts.slice(0, 8).map((alert) => (
                  <div key={alert.dealer_id} className="flex items-center justify-between">
                    <div className="min-w-0 flex-1">
                      <p className="text-sm font-medium truncate">{alert.name}</p>
                      <p className="text-xs text-muted-foreground">
                        {alert.dealer_code} &middot; Limit: {formatCurrency(alert.credit_limit)}
                      </p>
                    </div>
                    <div className="text-right ml-3">
                      <p className="text-sm font-semibold tabular-nums">
                        {formatCurrency(alert.outstanding)}
                      </p>
                      <Badge
                        variant="outline"
                        className={`text-[10px] ${
                          alert.utilization_pct > 95 ? 'border-red-300 text-red-600 bg-red-50'
                            : alert.utilization_pct > 90 ? 'border-orange-300 text-orange-600 bg-orange-50'
                            : 'border-amber-300 text-amber-600 bg-amber-50'
                        }`}
                      >
                        {alert.utilization_pct.toFixed(0)}%
                      </Badge>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-sm text-muted-foreground text-center py-8">No credit alerts - all healthy!</p>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Recent B2B Orders */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle className="text-base">Recent B2B Orders</CardTitle>
            <Link href="/dashboard/dms/orders">
              <Button variant="ghost" size="sm" className="text-xs">
                View All Orders <ArrowRight className="h-3 w-3 ml-1" />
              </Button>
            </Link>
          </div>
          <CardDescription>Last 10 distributor orders</CardDescription>
        </CardHeader>
        <CardContent>
          {recentOrders.length > 0 ? (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b text-left">
                    <th className="pb-2 font-medium text-muted-foreground">Order #</th>
                    <th className="pb-2 font-medium text-muted-foreground">Dealer</th>
                    <th className="pb-2 font-medium text-muted-foreground text-right">Amount</th>
                    <th className="pb-2 font-medium text-muted-foreground text-center">Status</th>
                    <th className="pb-2 font-medium text-muted-foreground text-right">Date</th>
                  </tr>
                </thead>
                <tbody>
                  {recentOrders.map((order) => (
                    <tr key={order.order_id} className="border-b last:border-0 hover:bg-muted/50">
                      <td className="py-2.5 font-mono text-xs">{order.order_number}</td>
                      <td className="py-2.5">{order.dealer_name}</td>
                      <td className="py-2.5 text-right tabular-nums font-medium">{formatCurrency(order.amount)}</td>
                      <td className="py-2.5 text-center">
                        <Badge variant="outline" className={`text-[10px] ${getStatusColor(order.status)}`}>
                          {order.status}
                        </Badge>
                      </td>
                      <td className="py-2.5 text-right text-muted-foreground text-xs">{order.date}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <p className="text-sm text-muted-foreground text-center py-8">No B2B orders yet</p>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
