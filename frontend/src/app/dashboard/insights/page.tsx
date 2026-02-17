'use client';

import { useQuery } from '@tanstack/react-query';
import {
  Brain,
  TrendingUp,
  TrendingDown,
  Minus,
  Package,
  Users,
  AlertTriangle,
  ArrowRight,
  RefreshCw,
  ShoppingCart,
  Boxes,
  UserX,
  DollarSign,
} from 'lucide-react';
import Link from 'next/link';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
  BarChart,
  Bar,
  Legend,
} from 'recharts';

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Skeleton } from '@/components/ui/skeleton';
import { insightsApi } from '@/lib/api';

const SEGMENT_COLORS = [
  '#22C55E', // Champions - Green
  '#3B82F6', // Loyal - Blue
  '#8B5CF6', // Potential - Purple
  '#06B6D4', // New - Cyan
  '#F59E0B', // At Risk - Amber
  '#6B7280', // Hibernating - Gray
  '#EF4444', // Lost - Red
];

function formatCurrency(value: number): string {
  if (value >= 10000000) {
    return `${(value / 10000000).toFixed(1)}Cr`;
  }
  if (value >= 100000) {
    return `${(value / 100000).toFixed(1)}L`;
  }
  if (value >= 1000) {
    return `${(value / 1000).toFixed(1)}K`;
  }
  return value.toFixed(0);
}

function TrendIndicator({ trend }: { trend: string }) {
  const isUp = trend.includes('UP');
  const isDown = trend.includes('DOWN');

  if (isUp) {
    return (
      <div className="flex items-center text-green-600">
        <TrendingUp className="h-4 w-4 mr-1" />
        <span className="text-sm font-medium">{trend}</span>
      </div>
    );
  }
  if (isDown) {
    return (
      <div className="flex items-center text-red-600">
        <TrendingDown className="h-4 w-4 mr-1" />
        <span className="text-sm font-medium">{trend}</span>
      </div>
    );
  }
  return (
    <div className="flex items-center text-gray-600">
      <Minus className="h-4 w-4 mr-1" />
      <span className="text-sm font-medium">Stable</span>
    </div>
  );
}

export default function InsightsPage() {
  const { data: dashboard, isLoading, refetch, isFetching } = useQuery({
    queryKey: ['insights-dashboard'],
    queryFn: insightsApi.getDashboard,
    staleTime: 5 * 60 * 1000, // 5 minutes
  });

  const { data: topPerformers } = useQuery({
    queryKey: ['insights-top-performers'],
    queryFn: () => insightsApi.getTopPerformers({ period_days: 30, limit: 5 }),
  });

  const { data: salesTrends } = useQuery({
    queryKey: ['insights-sales-trends'],
    queryFn: () => insightsApi.getSalesTrends({ lookback_days: 30 }),
  });

  if (isLoading) {
    return (
      <div className="space-y-6 p-6">
        <div className="flex items-center justify-between">
          <Skeleton className="h-8 w-48" />
          <Skeleton className="h-10 w-24" />
        </div>
        <div className="grid gap-4 md:grid-cols-4">
          {[...Array(4)].map((_, i) => (
            <Skeleton key={i} className="h-32" />
          ))}
        </div>
        <div className="grid gap-4 md:grid-cols-2">
          <Skeleton className="h-80" />
          <Skeleton className="h-80" />
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6 p-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-purple-100 rounded-lg">
            <Brain className="h-6 w-6 text-purple-600" />
          </div>
          <div>
            <h1 className="text-2xl font-bold tracking-tight">AI Insights</h1>
            <p className="text-muted-foreground">
              Predictive analytics and smart recommendations
            </p>
          </div>
        </div>
        <Button onClick={() => refetch()} disabled={isFetching} variant="outline">
          <RefreshCw className={`h-4 w-4 mr-2 ${isFetching ? 'animate-spin' : ''}`} />
          Refresh
        </Button>
      </div>

      {/* KPI Cards */}
      <div className="grid gap-4 md:grid-cols-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Revenue Trend</CardTitle>
            <DollarSign className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {formatCurrency(dashboard?.predicted_monthly_revenue || 0)}
            </div>
            <TrendIndicator trend={dashboard?.revenue_trend || 'STABLE'} />
            <p className="text-xs text-muted-foreground mt-1">
              Predicted this month
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Order Forecast</CardTitle>
            <ShoppingCart className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {dashboard?.predicted_monthly_orders || 0}
            </div>
            <p className="text-sm text-muted-foreground">
              {dashboard?.order_trend}
            </p>
          </CardContent>
        </Card>

        <Card className={dashboard?.high_churn_risk ? 'border-amber-200 bg-amber-50' : ''}>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Churn Risk</CardTitle>
            <UserX className="h-4 w-4 text-amber-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-amber-600">
              {dashboard?.high_churn_risk || 0}
            </div>
            <p className="text-sm text-muted-foreground">
              Customers need attention
            </p>
            {dashboard?.high_churn_risk ? (
              <Link href="/dashboard/insights/churn-risk">
                <Button variant="link" className="p-0 h-auto text-xs text-amber-600">
                  View details <ArrowRight className="h-3 w-3 ml-1" />
                </Button>
              </Link>
            ) : null}
          </CardContent>
        </Card>

        <Card className={dashboard?.critical_stockouts ? 'border-red-200 bg-red-50' : ''}>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Stockout Alerts</CardTitle>
            <Boxes className="h-4 w-4 text-red-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-red-600">
              {dashboard?.critical_stockouts || 0}
            </div>
            <p className="text-sm text-muted-foreground">
              {dashboard?.reorder_needed || 0} need reorder
            </p>
            {dashboard?.reorder_needed ? (
              <Link href="/dashboard/insights/reorder">
                <Button variant="link" className="p-0 h-auto text-xs text-red-600">
                  View all <ArrowRight className="h-3 w-3 ml-1" />
                </Button>
              </Link>
            ) : null}
          </CardContent>
        </Card>
      </div>

      {/* Actionable Insights */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <AlertTriangle className="h-5 w-5 text-indigo-500" />
            Actionable Insights
          </CardTitle>
          <CardDescription>
            Key findings that need your attention
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            <div className="flex items-center justify-between p-3 bg-blue-50 rounded-lg">
              <div className="flex items-center gap-3">
                <TrendingUp className="h-5 w-5 text-blue-600" />
                <span className="text-sm">{dashboard?.top_insight_sales}</span>
              </div>
            </div>
            <div className="flex items-center justify-between p-3 bg-amber-50 rounded-lg">
              <div className="flex items-center gap-3">
                <Package className="h-5 w-5 text-amber-600" />
                <span className="text-sm">{dashboard?.top_insight_inventory}</span>
              </div>
              <Link href="/dashboard/insights/reorder">
                <Button variant="ghost" size="sm">
                  View <ArrowRight className="h-4 w-4 ml-1" />
                </Button>
              </Link>
            </div>
            <div className="flex items-center justify-between p-3 bg-purple-50 rounded-lg">
              <div className="flex items-center gap-3">
                <Users className="h-5 w-5 text-purple-600" />
                <span className="text-sm">{dashboard?.top_insight_customers}</span>
              </div>
              <Link href="/dashboard/insights/churn-risk">
                <Button variant="ghost" size="sm">
                  View <ArrowRight className="h-4 w-4 ml-1" />
                </Button>
              </Link>
            </div>
            {dashboard?.slow_moving_value ? (
              <div className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                <div className="flex items-center gap-3">
                  <Boxes className="h-5 w-5 text-gray-600" />
                  <span className="text-sm">
                    {formatCurrency(dashboard.slow_moving_value)} in slow-moving inventory needs action
                  </span>
                </div>
                <Link href="/dashboard/insights/slow-moving">
                  <Button variant="ghost" size="sm">
                    View <ArrowRight className="h-4 w-4 ml-1" />
                  </Button>
                </Link>
              </div>
            ) : null}
          </div>
        </CardContent>
      </Card>

      {/* Charts Row */}
      <div className="grid gap-4 md:grid-cols-2">
        {/* Revenue Forecast Chart */}
        <Card>
          <CardHeader>
            <CardTitle>Revenue Forecast (14 Days)</CardTitle>
            <CardDescription>Predicted daily revenue with confidence interval</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="h-[300px]">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={dashboard?.revenue_forecast_chart || []}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis
                    dataKey="date"
                    tickFormatter={(value) => new Date(value).toLocaleDateString('en-IN', { day: 'numeric', month: 'short' })}
                    fontSize={12}
                  />
                  <YAxis
                    tickFormatter={(value) => formatCurrency(value)}
                    fontSize={12}
                  />
                  <Tooltip
                    formatter={(value) => [formatCurrency(value as number), 'Revenue']}
                    labelFormatter={(label) => new Date(label).toLocaleDateString('en-IN', { weekday: 'short', day: 'numeric', month: 'short' })}
                  />
                  <Line
                    type="monotone"
                    dataKey="predicted_value"
                    stroke="#3B82F6"
                    strokeWidth={2}
                    dot={false}
                  />
                  <Line
                    type="monotone"
                    dataKey="upper_bound"
                    stroke="#93C5FD"
                    strokeWidth={1}
                    strokeDasharray="3 3"
                    dot={false}
                  />
                  <Line
                    type="monotone"
                    dataKey="lower_bound"
                    stroke="#93C5FD"
                    strokeWidth={1}
                    strokeDasharray="3 3"
                    dot={false}
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </CardContent>
        </Card>

        {/* Customer Segments Chart */}
        <Card>
          <CardHeader>
            <CardTitle>Customer Segments</CardTitle>
            <CardDescription>RFM-based customer segmentation</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="h-[300px]">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={(dashboard?.customer_segments_chart || []) as Array<{ name: string; value: number }>}
                    cx="50%"
                    cy="50%"
                    innerRadius={60}
                    outerRadius={100}
                    paddingAngle={2}
                    dataKey="value"
                    nameKey="name"
                    label={({ name, percent }: { name?: string; percent?: number }) => `${name || ''} ${((percent || 0) * 100).toFixed(0)}%`}
                    labelLine={false}
                  >
                    {(dashboard?.customer_segments_chart || []).map((_, index) => (
                      <Cell key={`cell-${index}`} fill={SEGMENT_COLORS[index % SEGMENT_COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip
                    formatter={(value) => [value, 'Customers']}
                  />
                </PieChart>
              </ResponsiveContainer>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Tabs for detailed insights */}
      <Tabs defaultValue="sales" className="space-y-4">
        <TabsList>
          <TabsTrigger value="sales">Sales Insights</TabsTrigger>
          <TabsTrigger value="inventory">Inventory Insights</TabsTrigger>
          <TabsTrigger value="customers">Customer Insights</TabsTrigger>
        </TabsList>

        <TabsContent value="sales" className="space-y-4">
          <div className="grid gap-4 md:grid-cols-2">
            {/* Top Products */}
            <Card>
              <CardHeader>
                <CardTitle>Top Selling Products</CardTitle>
                <CardDescription>Last 30 days by revenue</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  {topPerformers?.top_products?.slice(0, 5).map((product, index) => (
                    <div key={product.id} className="flex items-center justify-between">
                      <div className="flex items-center gap-3">
                        <span className="text-sm font-medium text-muted-foreground w-6">
                          #{index + 1}
                        </span>
                        <div>
                          <p className="font-medium text-sm">{product.name}</p>
                          <p className="text-xs text-muted-foreground">{product.sku}</p>
                        </div>
                      </div>
                      <div className="text-right">
                        <p className="font-medium">{formatCurrency(product.revenue)}</p>
                        <p className="text-xs text-muted-foreground">{product.quantity} units</p>
                      </div>
                    </div>
                  ))}
                  {!topPerformers?.top_products?.length && (
                    <p className="text-sm text-muted-foreground text-center py-4">
                      No sales data available
                    </p>
                  )}
                </div>
              </CardContent>
            </Card>

            {/* Sales Pattern */}
            <Card>
              <CardHeader>
                <CardTitle>Weekly Sales Pattern</CardTitle>
                <CardDescription>Best performing days</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  <div className="grid grid-cols-7 gap-2">
                    {['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'].map((day) => {
                      const value = salesTrends?.weekly_pattern?.[
                        day === 'Sun' ? 'Sunday' :
                        day === 'Mon' ? 'Monday' :
                        day === 'Tue' ? 'Tuesday' :
                        day === 'Wed' ? 'Wednesday' :
                        day === 'Thu' ? 'Thursday' :
                        day === 'Fri' ? 'Friday' : 'Saturday'
                      ] || 1;
                      const intensity = Math.min(1, Math.max(0.2, value));

                      return (
                        <div key={day} className="text-center">
                          <div
                            className="h-12 rounded-md flex items-center justify-center"
                            style={{ backgroundColor: `rgba(59, 130, 246, ${intensity})` }}
                          >
                            <span className="text-xs font-medium text-white">
                              {(value * 100).toFixed(0)}%
                            </span>
                          </div>
                          <span className="text-xs text-muted-foreground">{day}</span>
                        </div>
                      );
                    })}
                  </div>
                  <div className="pt-4 border-t">
                    <div className="flex justify-between text-sm">
                      <span className="text-muted-foreground">Peak Hours:</span>
                      <span className="font-medium">
                        {salesTrends?.peak_hours?.map(h => `${h}:00`).join(', ') || 'N/A'}
                      </span>
                    </div>
                    <div className="flex justify-between text-sm mt-2">
                      <span className="text-muted-foreground">Monthly Growth:</span>
                      <span className={`font-medium ${(salesTrends?.monthly_growth || 0) >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                        {salesTrends?.monthly_growth?.toFixed(1) || 0}%
                      </span>
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* Top Channels */}
            <Card className="md:col-span-2">
              <CardHeader>
                <CardTitle>Channel Performance</CardTitle>
                <CardDescription>Revenue by sales channel</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="h-[200px]">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={topPerformers?.top_channels || []} layout="vertical">
                      <CartesianGrid strokeDasharray="3 3" />
                      <XAxis type="number" tickFormatter={(value) => formatCurrency(value)} />
                      <YAxis type="category" dataKey="channel" width={100} />
                      <Tooltip
                        formatter={(value) => [formatCurrency(value as number), 'Revenue']}
                      />
                      <Bar dataKey="revenue" fill="#3B82F6" radius={[0, 4, 4, 0]} />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        <TabsContent value="inventory" className="space-y-4">
          <div className="grid gap-4 md:grid-cols-2">
            {/* Stockout Timeline */}
            <Card>
              <CardHeader>
                <CardTitle>Stockout Timeline</CardTitle>
                <CardDescription>Products running low on stock</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  {dashboard?.stockout_timeline?.map((item, index) => (
                    <div key={index} className="flex items-center justify-between p-2 rounded-lg bg-muted/50">
                      <span className="text-sm font-medium truncate max-w-[200px]">
                        {item.product}
                      </span>
                      <Badge variant={item.days <= 3 ? 'destructive' : item.days <= 7 ? 'secondary' : 'outline'}>
                        {item.days} days
                      </Badge>
                    </div>
                  ))}
                  {!dashboard?.stockout_timeline?.length && (
                    <p className="text-sm text-muted-foreground text-center py-4">
                      No stockout risks detected
                    </p>
                  )}
                </div>
                <div className="mt-4">
                  <Link href="/dashboard/insights/reorder">
                    <Button variant="outline" className="w-full">
                      View All Reorder Recommendations
                      <ArrowRight className="h-4 w-4 ml-2" />
                    </Button>
                  </Link>
                </div>
              </CardContent>
            </Card>

            {/* Slow Moving Summary */}
            <Card>
              <CardHeader>
                <CardTitle>Slow Moving Inventory</CardTitle>
                <CardDescription>Items needing attention</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="text-center py-8">
                  <div className="text-4xl font-bold text-amber-600">
                    {formatCurrency(dashboard?.slow_moving_value || 0)}
                  </div>
                  <p className="text-sm text-muted-foreground mt-2">
                    Total value of slow-moving stock
                  </p>
                </div>
                <div className="mt-4">
                  <Link href="/dashboard/insights/slow-moving">
                    <Button variant="outline" className="w-full">
                      View Slow Moving Items
                      <ArrowRight className="h-4 w-4 ml-2" />
                    </Button>
                  </Link>
                </div>
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        <TabsContent value="customers" className="space-y-4">
          <div className="grid gap-4 md:grid-cols-2">
            {/* Churn Risk Summary */}
            <Card>
              <CardHeader>
                <CardTitle>Churn Risk Summary</CardTitle>
                <CardDescription>Customers at risk of leaving</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="text-center py-8">
                  <div className="text-4xl font-bold text-amber-600">
                    {dashboard?.high_churn_risk || 0}
                  </div>
                  <p className="text-sm text-muted-foreground mt-2">
                    High-value customers need attention
                  </p>
                </div>
                <div className="mt-4">
                  <Link href="/dashboard/insights/churn-risk">
                    <Button variant="outline" className="w-full">
                      View At-Risk Customers
                      <ArrowRight className="h-4 w-4 ml-2" />
                    </Button>
                  </Link>
                </div>
              </CardContent>
            </Card>

            {/* Segment Breakdown */}
            <Card>
              <CardHeader>
                <CardTitle>Customer Segment Legend</CardTitle>
                <CardDescription>Understanding your customer base</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-2">
                  {[
                    { name: 'Champions', color: SEGMENT_COLORS[0], desc: 'Best customers' },
                    { name: 'Loyal', color: SEGMENT_COLORS[1], desc: 'Frequent buyers' },
                    { name: 'Potential', color: SEGMENT_COLORS[2], desc: 'Growing customers' },
                    { name: 'New', color: SEGMENT_COLORS[3], desc: 'First-time buyers' },
                    { name: 'At Risk', color: SEGMENT_COLORS[4], desc: 'Declining activity' },
                    { name: 'Hibernating', color: SEGMENT_COLORS[5], desc: 'Long inactive' },
                    { name: 'Lost', color: SEGMENT_COLORS[6], desc: 'Very long inactive' },
                  ].map((segment) => (
                    <div key={segment.name} className="flex items-center gap-3">
                      <div
                        className="w-3 h-3 rounded-full"
                        style={{ backgroundColor: segment.color }}
                      />
                      <span className="text-sm font-medium">{segment.name}</span>
                      <span className="text-xs text-muted-foreground">- {segment.desc}</span>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          </div>
        </TabsContent>
      </Tabs>
    </div>
  );
}
