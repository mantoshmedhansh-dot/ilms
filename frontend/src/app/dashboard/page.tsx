'use client';

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { formatDistanceToNow, format, subDays } from 'date-fns';
import Link from 'next/link';
import {
  ShoppingCart,
  Package,
  Users,
  DollarSign,
  TrendingUp,
  TrendingDown,
  Wrench,
  Truck,
  Building2,
  Briefcase,
  AlertTriangle,
  AlertCircle,
  CheckCircle,
  Clock,
  ArrowRight,
  BarChart3,
  X,
  Info,
  CreditCard,
} from 'lucide-react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { dashboardApi, notificationsApi, fixedAssetsApi, hrApi } from '@/lib/api';
import {
  LineChart,
  Line,
  BarChart,
  Bar,
  PieChart,
  Pie,
  Cell,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from 'recharts';

interface ActivityItem {
  type: string;
  color: string;
  title: string;
  description: string;
  timestamp: string;
}

interface TopProduct {
  id: string;
  name: string;
  sku: string;
  sales: number;
}

interface StatCardProps {
  title: string;
  value: string | number;
  change?: number;
  icon: React.ReactNode;
  isLoading?: boolean;
  href?: string;
}

const COLORS = ['#3B82F6', '#10B981', '#F59E0B', '#EF4444', '#8B5CF6', '#EC4899'];

const announcementTypeColors: Record<string, string> = {
  INFO: 'bg-blue-50 border-blue-200 text-blue-800',
  WARNING: 'bg-yellow-50 border-yellow-200 text-yellow-800',
  SUCCESS: 'bg-green-50 border-green-200 text-green-800',
  ERROR: 'bg-red-50 border-red-200 text-red-800',
};

const announcementTypeIcons: Record<string, typeof Info> = {
  INFO: Info,
  WARNING: AlertTriangle,
  SUCCESS: CheckCircle,
  ERROR: AlertCircle,
};

function StatCard({ title, value, change, icon, isLoading, href }: StatCardProps) {
  if (isLoading) {
    return (
      <Card>
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <Skeleton className="h-4 w-24" />
          <Skeleton className="h-4 w-4" />
        </CardHeader>
        <CardContent>
          <Skeleton className="h-8 w-32 mb-2" />
          <Skeleton className="h-4 w-20" />
        </CardContent>
      </Card>
    );
  }

  const content = (
    <Card className={href ? 'hover:shadow-md transition-shadow cursor-pointer' : ''}>
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <CardTitle className="text-sm font-medium text-muted-foreground">{title}</CardTitle>
        <div className="text-muted-foreground">{icon}</div>
      </CardHeader>
      <CardContent>
        <div className="text-2xl font-bold">{value}</div>
        {change !== undefined && (
          <p className="flex items-center text-xs text-muted-foreground mt-1">
            {change >= 0 ? (
              <TrendingUp className="mr-1 h-3 w-3 text-green-500" />
            ) : (
              <TrendingDown className="mr-1 h-3 w-3 text-red-500" />
            )}
            <span className={change >= 0 ? 'text-green-500' : 'text-red-500'}>
              {change >= 0 ? '+' : ''}{change}%
            </span>
            <span className="ml-1">from last month</span>
          </p>
        )}
      </CardContent>
    </Card>
  );

  if (href) {
    return <Link href={href}>{content}</Link>;
  }

  return content;
}

export default function DashboardPage() {
  const queryClient = useQueryClient();

  const { data: stats, isLoading } = useQuery({
    queryKey: ['dashboard-stats'],
    queryFn: dashboardApi.getStats,
  });

  const { data: recentActivity, isLoading: activityLoading } = useQuery({
    queryKey: ['recent-activity'],
    queryFn: () => dashboardApi.getRecentActivity(5),
  });

  const { data: topProducts, isLoading: productsLoading } = useQuery({
    queryKey: ['top-selling-products'],
    queryFn: () => dashboardApi.getTopSellingProducts(4),
  });

  // Additional data for enhanced dashboard
  const { data: announcements } = useQuery({
    queryKey: ['dashboard-announcements'],
    queryFn: async () => {
      try {
        const result = await notificationsApi.getActiveAnnouncements();
        return result.announcements || [];
      } catch {
        return [];
      }
    },
  });

  const { data: hrDashboard } = useQuery({
    queryKey: ['hr-dashboard'],
    queryFn: async () => {
      try {
        return await hrApi.getDashboard();
      } catch {
        return null;
      }
    },
  });

  const { data: fixedAssetsDashboard } = useQuery({
    queryKey: ['fixed-assets-dashboard-mini'],
    queryFn: async () => {
      try {
        return await fixedAssetsApi.getDashboard();
      } catch {
        return null;
      }
    },
  });

  // Fetch real chart data from API
  const { data: salesTrend } = useQuery({
    queryKey: ['dashboard-sales-trend'],
    queryFn: async () => {
      try {
        const result = await dashboardApi.getSalesTrend();
        return result;
      } catch {
        return [];
      }
    },
  });

  const { data: orderStatusDistribution } = useQuery({
    queryKey: ['dashboard-order-status'],
    queryFn: async () => {
      try {
        const result = await dashboardApi.getOrderStatusDistribution();
        return result;
      } catch {
        return [];
      }
    },
  });

  const { data: categorySales } = useQuery({
    queryKey: ['dashboard-category-sales'],
    queryFn: async () => {
      try {
        const result = await dashboardApi.getCategorySales();
        return result;
      } catch {
        return [];
      }
    },
  });

  const dismissAnnouncementMutation = useMutation({
    mutationFn: notificationsApi.dismissAnnouncement,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['dashboard-announcements'] });
    },
  });

  const defaultStats = {
    total_orders: stats?.total_orders ?? 0,
    total_revenue: stats?.total_revenue ?? 0,
    total_customers: stats?.total_customers ?? 0,
    total_products: stats?.total_products ?? 0,
    pending_orders: stats?.pending_orders ?? 0,
    pending_service_requests: stats?.pending_service_requests ?? 0,
    low_stock_items: stats?.low_stock_items ?? 0,
    shipments_in_transit: stats?.shipments_in_transit ?? 0,
    orders_change: stats?.orders_change ?? 0,
    revenue_change: stats?.revenue_change ?? 0,
    customers_change: stats?.customers_change ?? 0,
  };

  const formatCurrency = (value: number) => {
    return new Intl.NumberFormat('en-IN', {
      style: 'currency',
      currency: 'INR',
      maximumFractionDigits: 0,
    }).format(value);
  };

  // Chart data from API (with fallback empty arrays if API fails)
  const statusColors: Record<string, string> = {
    DELIVERED: '#10B981',
    SHIPPED: '#3B82F6',
    PROCESSING: '#F59E0B',
    PENDING: '#EF4444',
    CANCELLED: '#6B7280',
    RETURNED: '#8B5CF6',
  };

  const revenueData = salesTrend || [];

  const orderStatusData = (orderStatusDistribution || []).map((item: { status: string; count: number; percentage: number }) => ({
    name: item.status?.replace(/_/g, ' ') || 'Unknown',
    value: item.percentage || 0,
    color: statusColors[item.status] || '#6B7280',
  }));

  const categoryData = (categorySales || []).map((item: { category: string; total_sales: number }) => ({
    name: item.category || 'Unknown',
    sales: item.total_sales || 0,
  }));

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Dashboard</h1>
        <p className="text-muted-foreground">
          Welcome to your ERP Control Panel. Here&apos;s an overview of your business.
        </p>
      </div>

      {/* Active Announcements */}
      {announcements && announcements.length > 0 && (
        <div className="space-y-2">
          {announcements.slice(0, 2).map((announcement) => {
            const Icon = announcementTypeIcons[announcement.announcement_type] || Info;
            const colorClass = announcementTypeColors[announcement.announcement_type] || announcementTypeColors.INFO;
            return (
              <div
                key={announcement.id}
                className={`flex items-center justify-between p-3 rounded-lg border ${colorClass}`}
              >
                <div className="flex items-center gap-3">
                  <Icon className="h-5 w-5" />
                  <div>
                    <span className="font-medium">{announcement.title}</span>
                    <span className="mx-2">-</span>
                    <span>{announcement.message}</span>
                  </div>
                </div>
                {announcement.is_dismissible && (
                  <Button
                    variant="ghost"
                    size="icon"
                    className="h-6 w-6"
                    onClick={() => dismissAnnouncementMutation.mutate(announcement.id)}
                  >
                    <X className="h-4 w-4" />
                  </Button>
                )}
              </div>
            );
          })}
        </div>
      )}

      {/* Main Stats */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <StatCard
          title="Total Revenue"
          value={formatCurrency(defaultStats.total_revenue)}
          change={defaultStats.revenue_change}
          icon={<DollarSign className="h-4 w-4" />}
          isLoading={isLoading}
          href="/dashboard/reports/profit-loss"
        />
        <StatCard
          title="Total Orders"
          value={defaultStats.total_orders.toLocaleString()}
          change={defaultStats.orders_change}
          icon={<ShoppingCart className="h-4 w-4" />}
          isLoading={isLoading}
          href="/dashboard/orders"
        />
        <StatCard
          title="Total Customers"
          value={defaultStats.total_customers.toLocaleString()}
          change={defaultStats.customers_change}
          icon={<Users className="h-4 w-4" />}
          isLoading={isLoading}
          href="/dashboard/crm/customers"
        />
        <StatCard
          title="Products"
          value={defaultStats.total_products.toLocaleString()}
          icon={<Package className="h-4 w-4" />}
          isLoading={isLoading}
          href="/dashboard/catalog"
        />
      </div>

      {/* Charts Row */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        {/* Revenue Trend Chart */}
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle className="text-lg">Revenue Trend</CardTitle>
            <CardDescription>Last 7 days revenue and orders</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="h-[250px]">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={revenueData}>
                  <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
                  <XAxis dataKey="date" className="text-xs" />
                  <YAxis yAxisId="left" className="text-xs" tickFormatter={(v) => `${(v / 1000).toFixed(0)}k`} />
                  <YAxis yAxisId="right" orientation="right" className="text-xs" />
                  <Tooltip
                    contentStyle={{ backgroundColor: 'hsl(var(--background))', border: '1px solid hsl(var(--border))' }}
                    formatter={(value, name) => [
                      name === 'Revenue' ? formatCurrency(value as number) : value,
                      name
                    ]}
                  />
                  <Legend />
                  <Line
                    yAxisId="left"
                    type="monotone"
                    dataKey="revenue"
                    stroke="#3B82F6"
                    strokeWidth={2}
                    dot={{ fill: '#3B82F6' }}
                    name="Revenue"
                  />
                  <Line
                    yAxisId="right"
                    type="monotone"
                    dataKey="orders"
                    stroke="#10B981"
                    strokeWidth={2}
                    dot={{ fill: '#10B981' }}
                    name="Orders"
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </CardContent>
        </Card>

        {/* Order Status Pie Chart */}
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">Order Status</CardTitle>
            <CardDescription>Distribution by status</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="h-[250px]">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={orderStatusData}
                    cx="50%"
                    cy="50%"
                    innerRadius={50}
                    outerRadius={80}
                    paddingAngle={2}
                    dataKey="value"
                  >
                    {orderStatusData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={entry.color} />
                    ))}
                  </Pie>
                  <Tooltip
                    contentStyle={{ backgroundColor: 'hsl(var(--background))', border: '1px solid hsl(var(--border))' }}
                    formatter={(value) => [`${value}%`, 'Percentage']}
                  />
                  <Legend />
                </PieChart>
              </ResponsiveContainer>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Action Required */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <Link href="/dashboard/orders?status=PENDING">
          <Card className="border-orange-200 dark:border-orange-800 hover:shadow-md transition-shadow cursor-pointer">
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Pending Orders</CardTitle>
              <ShoppingCart className="h-4 w-4 text-orange-500" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-orange-600">
                {isLoading ? <Skeleton className="h-8 w-16" /> : defaultStats.pending_orders}
              </div>
              <p className="text-xs text-muted-foreground">Requires attention</p>
            </CardContent>
          </Card>
        </Link>

        <Link href="/dashboard/service/requests?status=PENDING">
          <Card className="border-blue-200 dark:border-blue-800 hover:shadow-md transition-shadow cursor-pointer">
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Service Requests</CardTitle>
              <Wrench className="h-4 w-4 text-blue-500" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-blue-600">
                {isLoading ? <Skeleton className="h-8 w-16" /> : defaultStats.pending_service_requests}
              </div>
              <p className="text-xs text-muted-foreground">Pending assignment</p>
            </CardContent>
          </Card>
        </Link>

        <Link href="/dashboard/inventory?low_stock=true">
          <Card className="border-red-200 dark:border-red-800 hover:shadow-md transition-shadow cursor-pointer">
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Low Stock Items</CardTitle>
              <Package className="h-4 w-4 text-red-500" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-red-600">
                {isLoading ? <Skeleton className="h-8 w-16" /> : defaultStats.low_stock_items}
              </div>
              <p className="text-xs text-muted-foreground">Below reorder level</p>
            </CardContent>
          </Card>
        </Link>

        <Link href="/dashboard/logistics/shipments?status=IN_TRANSIT">
          <Card className="border-green-200 dark:border-green-800 hover:shadow-md transition-shadow cursor-pointer">
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">In Transit</CardTitle>
              <Truck className="h-4 w-4 text-green-500" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-green-600">
                {isLoading ? <Skeleton className="h-8 w-16" /> : defaultStats.shipments_in_transit}
              </div>
              <p className="text-xs text-muted-foreground">Shipments on the way</p>
            </CardContent>
          </Card>
        </Link>
      </div>

      {/* Category Sales & HR/Assets Summary */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        {/* Category Sales Bar Chart */}
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">Sales by Category</CardTitle>
            <CardDescription>Top performing categories</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="h-[200px]">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={categoryData} layout="vertical">
                  <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
                  <XAxis type="number" className="text-xs" tickFormatter={(v) => `${(v / 1000).toFixed(0)}k`} />
                  <YAxis type="category" dataKey="name" className="text-xs" width={100} />
                  <Tooltip
                    contentStyle={{ backgroundColor: 'hsl(var(--background))', border: '1px solid hsl(var(--border))' }}
                    formatter={(value) => [formatCurrency(value as number), 'Sales']}
                  />
                  <Bar dataKey="sales" fill="#3B82F6" radius={[0, 4, 4, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </CardContent>
        </Card>

        {/* HR Summary */}
        <Card>
          <CardHeader className="flex flex-row items-center justify-between">
            <div>
              <CardTitle className="text-lg">HR Overview</CardTitle>
              <CardDescription>Employee & attendance summary</CardDescription>
            </div>
            <Link href="/dashboard/hr">
              <Button variant="ghost" size="sm">
                <ArrowRight className="h-4 w-4" />
              </Button>
            </Link>
          </CardHeader>
          <CardContent className="space-y-4">
            {hrDashboard ? (
              <>
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <Briefcase className="h-4 w-4 text-muted-foreground" />
                    <span className="text-sm">Active Employees</span>
                  </div>
                  <span className="font-semibold">{hrDashboard.active_employees || 0}</span>
                </div>
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <Clock className="h-4 w-4 text-muted-foreground" />
                    <span className="text-sm">Present Today</span>
                  </div>
                  <span className="font-semibold text-green-600">{hrDashboard.present_today || 0}</span>
                </div>
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <AlertTriangle className="h-4 w-4 text-orange-500" />
                    <span className="text-sm">Pending Leaves</span>
                  </div>
                  <Badge variant="secondary">{hrDashboard.pending_leave_requests || 0}</Badge>
                </div>
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <CreditCard className="h-4 w-4 text-muted-foreground" />
                    <span className="text-sm">Pending Payroll</span>
                  </div>
                  <Badge variant="secondary">{hrDashboard.pending_payroll_approval || 0}</Badge>
                </div>
              </>
            ) : (
              <div className="text-center py-4 text-muted-foreground">
                <Briefcase className="h-8 w-8 mx-auto mb-2 opacity-50" />
                <p className="text-sm">HR module not configured</p>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Fixed Assets Summary */}
        <Card>
          <CardHeader className="flex flex-row items-center justify-between">
            <div>
              <CardTitle className="text-lg">Fixed Assets</CardTitle>
              <CardDescription>Asset value summary</CardDescription>
            </div>
            <Link href="/dashboard/finance/fixed-assets">
              <Button variant="ghost" size="sm">
                <ArrowRight className="h-4 w-4" />
              </Button>
            </Link>
          </CardHeader>
          <CardContent className="space-y-4">
            {fixedAssetsDashboard ? (
              <>
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <Building2 className="h-4 w-4 text-muted-foreground" />
                    <span className="text-sm">Total Assets</span>
                  </div>
                  <span className="font-semibold">{fixedAssetsDashboard.total_assets || 0}</span>
                </div>
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <DollarSign className="h-4 w-4 text-muted-foreground" />
                    <span className="text-sm">Book Value</span>
                  </div>
                  <span className="font-semibold">
                    {formatCurrency(fixedAssetsDashboard.total_current_book_value || 0)}
                  </span>
                </div>
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <Wrench className="h-4 w-4 text-orange-500" />
                    <span className="text-sm">Under Maintenance</span>
                  </div>
                  <Badge variant="secondary">{fixedAssetsDashboard.under_maintenance || 0}</Badge>
                </div>
                <div className="space-y-1">
                  <div className="flex items-center justify-between text-xs">
                    <span className="text-muted-foreground">Depreciation Progress</span>
                    <span>
                      {fixedAssetsDashboard.total_capitalized_value
                        ? Math.round(
                            (fixedAssetsDashboard.total_accumulated_depreciation /
                              fixedAssetsDashboard.total_capitalized_value) *
                              100
                          )
                        : 0}
                      %
                    </span>
                  </div>
                  <Progress
                    value={
                      fixedAssetsDashboard.total_capitalized_value
                        ? (fixedAssetsDashboard.total_accumulated_depreciation /
                            fixedAssetsDashboard.total_capitalized_value) *
                          100
                        : 0
                    }
                    className="h-2"
                  />
                </div>
              </>
            ) : (
              <div className="text-center py-4 text-muted-foreground">
                <Building2 className="h-8 w-8 mx-auto mb-2 opacity-50" />
                <p className="text-sm">No assets registered</p>
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Activity, Products & Quick Actions */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">Recent Activity</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {activityLoading ? (
                <>
                  {[1, 2, 3, 4].map((i) => (
                    <div key={i} className="flex items-center gap-4">
                      <Skeleton className="h-2 w-2 rounded-full" />
                      <div className="flex-1">
                        <Skeleton className="h-4 w-48 mb-1" />
                        <Skeleton className="h-3 w-24" />
                      </div>
                    </div>
                  ))}
                </>
              ) : recentActivity && recentActivity.length > 0 ? (
                recentActivity.map((activity: ActivityItem, i: number) => (
                  <div key={i} className="flex items-center gap-4">
                    <div
                      className={`h-2 w-2 rounded-full ${
                        activity.color === 'green'
                          ? 'bg-green-500'
                          : activity.color === 'blue'
                          ? 'bg-blue-500'
                          : activity.color === 'orange'
                          ? 'bg-orange-500'
                          : 'bg-gray-500'
                      }`}
                    />
                    <div className="flex-1">
                      <p className="text-sm font-medium">{activity.title}</p>
                      <p className="text-xs text-muted-foreground">
                        {formatDistanceToNow(new Date(activity.timestamp), { addSuffix: true })}
                      </p>
                    </div>
                  </div>
                ))
              ) : (
                <p className="text-sm text-muted-foreground text-center py-4">No recent activity</p>
              )}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-lg">Top Selling Products</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {productsLoading ? (
                <>
                  {[1, 2, 3, 4].map((i) => (
                    <div key={i} className="flex items-center justify-between">
                      <div className="flex items-center gap-3">
                        <Skeleton className="h-6 w-6 rounded-full" />
                        <Skeleton className="h-4 w-32" />
                      </div>
                      <Skeleton className="h-4 w-16" />
                    </div>
                  ))}
                </>
              ) : topProducts && topProducts.length > 0 ? (
                topProducts.map((product: TopProduct, i: number) => (
                  <div key={product.id} className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <span
                        className={`flex h-6 w-6 items-center justify-center rounded-full text-xs font-medium ${
                          i === 0
                            ? 'bg-yellow-100 text-yellow-800'
                            : i === 1
                            ? 'bg-gray-100 text-gray-800'
                            : i === 2
                            ? 'bg-orange-100 text-orange-800'
                            : 'bg-muted text-muted-foreground'
                        }`}
                      >
                        {i + 1}
                      </span>
                      <span className="text-sm font-medium truncate max-w-[150px]">{product.name}</span>
                    </div>
                    <Badge variant="secondary">{product.sales} units</Badge>
                  </div>
                ))
              ) : (
                <p className="text-sm text-muted-foreground text-center py-4">No sales data yet</p>
              )}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-lg">Quick Actions</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-2 gap-3">
              {[
                { label: 'New Order', href: '/dashboard/orders/new', icon: ShoppingCart },
                { label: 'Add Product', href: '/dashboard/catalog/new', icon: Package },
                { label: 'Create PO', href: '/dashboard/procurement/purchase-orders?create=true', icon: DollarSign },
                { label: 'Service Req', href: '/dashboard/service/requests/new', icon: Wrench },
                { label: 'New Employee', href: '/dashboard/hr/employees/new', icon: Users },
                { label: 'Add Asset', href: '/dashboard/finance/fixed-assets', icon: Building2 },
              ].map((action, i) => {
                const Icon = action.icon;
                return (
                  <Link
                    key={i}
                    href={action.href}
                    className="flex items-center justify-center gap-2 rounded-lg border p-3 text-sm font-medium transition-colors hover:bg-accent"
                  >
                    <Icon className="h-4 w-4" />
                    {action.label}
                  </Link>
                );
              })}
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
