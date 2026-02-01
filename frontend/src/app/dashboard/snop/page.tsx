'use client';

import { useQuery } from '@tanstack/react-query';
import {
  Target,
  LineChart,
  GitBranch,
  Boxes,
  TrendingUp,
  TrendingDown,
  AlertTriangle,
  ArrowRight,
  RefreshCw,
  Calendar,
  Package,
  Truck,
} from 'lucide-react';
import Link from 'next/link';

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import { snopApi } from '@/lib/api';

function formatNumber(value: number): string {
  if (value >= 10000000) return `${(value / 10000000).toFixed(1)}Cr`;
  if (value >= 100000) return `${(value / 100000).toFixed(1)}L`;
  if (value >= 1000) return `${(value / 1000).toFixed(1)}K`;
  return value.toFixed(0);
}

export default function SNOPDashboardPage() {
  const { data: dashboard, isLoading, refetch, isFetching } = useQuery({
    queryKey: ['snop-dashboard'],
    queryFn: () => snopApi.getDashboard(),
    staleTime: 5 * 60 * 1000,
  });

  const { data: gapAnalysis } = useQuery({
    queryKey: ['snop-gap-analysis'],
    queryFn: () => snopApi.getDemandSupplyGap(),
  });

  if (isLoading) {
    return (
      <div className="space-y-6 p-6">
        <Skeleton className="h-8 w-64" />
        <div className="grid gap-4 md:grid-cols-4">
          {[...Array(4)].map((_, i) => <Skeleton key={i} className="h-32" />)}
        </div>
        <div className="grid gap-4 md:grid-cols-2">
          <Skeleton className="h-64" />
          <Skeleton className="h-64" />
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6 p-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-blue-100 rounded-lg">
            <Target className="h-6 w-6 text-blue-600" />
          </div>
          <div>
            <h1 className="text-2xl font-bold tracking-tight">S&OP Dashboard</h1>
            <p className="text-muted-foreground">
              Sales & Operations Planning - Demand Forecasting & Supply Planning
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
            <CardTitle className="text-sm font-medium">Forecast Accuracy</CardTitle>
            <LineChart className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-green-600">
              {dashboard?.forecast_accuracy?.toFixed(1) || 85}%
            </div>
            <p className="text-xs text-muted-foreground">
              MAPE: {dashboard?.mape?.toFixed(1) || 15}%
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Active Forecasts</CardTitle>
            <TrendingUp className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {dashboard?.active_forecasts || 0}
            </div>
            <p className="text-xs text-muted-foreground">
              {dashboard?.pending_review || 0} pending review
            </p>
            <Link href="/dashboard/snop/forecasts">
              <Button variant="link" className="p-0 h-auto text-xs">
                View forecasts <ArrowRight className="h-3 w-3 ml-1" />
              </Button>
            </Link>
          </CardContent>
        </Card>

        <Card className={gapAnalysis?.total_gap_units > 0 ? 'border-amber-200 bg-amber-50' : ''}>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Supply Gap</CardTitle>
            <AlertTriangle className="h-4 w-4 text-amber-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-amber-600">
              {formatNumber(gapAnalysis?.total_gap_units || 0)}
            </div>
            <p className="text-xs text-muted-foreground">
              Units short for next 30 days
            </p>
            <Link href="/dashboard/snop/supply-plans">
              <Button variant="link" className="p-0 h-auto text-xs text-amber-600">
                Plan supply <ArrowRight className="h-3 w-3 ml-1" />
              </Button>
            </Link>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Inventory Health</CardTitle>
            <Boxes className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {dashboard?.inventory_health_score?.toFixed(0) || 78}%
            </div>
            <p className="text-xs text-muted-foreground">
              {dashboard?.items_below_safety || 0} below safety stock
            </p>
            <Link href="/dashboard/snop/inventory-optimization">
              <Button variant="link" className="p-0 h-auto text-xs">
                Optimize <ArrowRight className="h-3 w-3 ml-1" />
              </Button>
            </Link>
          </CardContent>
        </Card>
      </div>

      {/* Quick Actions */}
      <div className="grid gap-4 md:grid-cols-4">
        <Link href="/dashboard/snop/forecasts">
          <Card className="hover:shadow-md transition-shadow cursor-pointer">
            <CardContent className="p-6">
              <div className="flex items-center gap-4">
                <div className="p-3 bg-blue-100 rounded-lg">
                  <LineChart className="h-6 w-6 text-blue-600" />
                </div>
                <div>
                  <h3 className="font-semibold">Demand Forecasting</h3>
                  <p className="text-sm text-muted-foreground">AI-powered predictions</p>
                </div>
              </div>
            </CardContent>
          </Card>
        </Link>

        <Link href="/dashboard/snop/supply-plans">
          <Card className="hover:shadow-md transition-shadow cursor-pointer">
            <CardContent className="p-6">
              <div className="flex items-center gap-4">
                <div className="p-3 bg-green-100 rounded-lg">
                  <GitBranch className="h-6 w-6 text-green-600" />
                </div>
                <div>
                  <h3 className="font-semibold">Supply Planning</h3>
                  <p className="text-sm text-muted-foreground">Production & procurement</p>
                </div>
              </div>
            </CardContent>
          </Card>
        </Link>

        <Link href="/dashboard/snop/scenarios">
          <Card className="hover:shadow-md transition-shadow cursor-pointer">
            <CardContent className="p-6">
              <div className="flex items-center gap-4">
                <div className="p-3 bg-purple-100 rounded-lg">
                  <Target className="h-6 w-6 text-purple-600" />
                </div>
                <div>
                  <h3 className="font-semibold">Scenario Analysis</h3>
                  <p className="text-sm text-muted-foreground">What-if simulations</p>
                </div>
              </div>
            </CardContent>
          </Card>
        </Link>

        <Link href="/dashboard/snop/inventory-optimization">
          <Card className="hover:shadow-md transition-shadow cursor-pointer">
            <CardContent className="p-6">
              <div className="flex items-center gap-4">
                <div className="p-3 bg-amber-100 rounded-lg">
                  <Boxes className="h-6 w-6 text-amber-600" />
                </div>
                <div>
                  <h3 className="font-semibold">Inventory Optimization</h3>
                  <p className="text-sm text-muted-foreground">Safety stock & EOQ</p>
                </div>
              </div>
            </CardContent>
          </Card>
        </Link>
      </div>

      {/* Demand-Supply Gap */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <AlertTriangle className="h-5 w-5 text-amber-500" />
            Demand-Supply Gap Analysis
          </CardTitle>
          <CardDescription>
            Products with supply shortfall in the next 30 days
          </CardDescription>
        </CardHeader>
        <CardContent>
          {gapAnalysis?.gaps?.length > 0 ? (
            <div className="space-y-3">
              {gapAnalysis.gaps.slice(0, 5).map((gap: any, index: number) => (
                <div key={index} className="flex items-center justify-between p-3 bg-muted/50 rounded-lg">
                  <div className="flex items-center gap-3">
                    <Package className="h-5 w-5 text-muted-foreground" />
                    <div>
                      <p className="font-medium">{gap.product_name}</p>
                      <p className="text-xs text-muted-foreground">{gap.sku}</p>
                    </div>
                  </div>
                  <div className="flex items-center gap-4">
                    <div className="text-right">
                      <p className="text-sm">Demand: {formatNumber(gap.forecast_demand)}</p>
                      <p className="text-sm">Supply: {formatNumber(gap.available_supply)}</p>
                    </div>
                    <Badge variant="destructive">
                      Gap: {formatNumber(gap.gap_units)}
                    </Badge>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="text-center py-8 text-muted-foreground">
              <Truck className="h-12 w-12 mx-auto mb-4 opacity-50" />
              <p>No significant supply gaps detected</p>
              <p className="text-sm">Your supply chain is well-balanced</p>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Recent Activity */}
      <div className="grid gap-4 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Recent Forecasts</CardTitle>
            <CardDescription>Latest demand forecasts generated</CardDescription>
          </CardHeader>
          <CardContent>
            {dashboard?.recent_forecasts?.length > 0 ? (
              <div className="space-y-3">
                {dashboard.recent_forecasts.slice(0, 5).map((forecast: any, index: number) => (
                  <div key={index} className="flex items-center justify-between">
                    <div>
                      <p className="font-medium text-sm">{forecast.product_name || forecast.category_name}</p>
                      <p className="text-xs text-muted-foreground">
                        {forecast.granularity} | {forecast.level}
                      </p>
                    </div>
                    <Badge variant={
                      forecast.status === 'APPROVED' ? 'default' :
                      forecast.status === 'PENDING_REVIEW' ? 'secondary' :
                      'outline'
                    }>
                      {forecast.status}
                    </Badge>
                  </div>
                ))}
              </div>
            ) : (
              <div className="text-center py-8 text-muted-foreground">
                <LineChart className="h-12 w-12 mx-auto mb-4 opacity-50" />
                <p>No forecasts yet</p>
                <Link href="/dashboard/snop/forecasts">
                  <Button variant="outline" className="mt-4">
                    Generate Forecast
                  </Button>
                </Link>
              </div>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Upcoming S&OP Meetings</CardTitle>
            <CardDescription>Scheduled consensus planning sessions</CardDescription>
          </CardHeader>
          <CardContent>
            {dashboard?.upcoming_meetings?.length > 0 ? (
              <div className="space-y-3">
                {dashboard.upcoming_meetings.map((meeting: any, index: number) => (
                  <div key={index} className="flex items-center justify-between p-3 bg-muted/50 rounded-lg">
                    <div className="flex items-center gap-3">
                      <Calendar className="h-5 w-5 text-blue-600" />
                      <div>
                        <p className="font-medium">{meeting.title}</p>
                        <p className="text-xs text-muted-foreground">
                          {new Date(meeting.scheduled_date).toLocaleDateString()}
                        </p>
                      </div>
                    </div>
                    <Badge variant="outline">{meeting.status}</Badge>
                  </div>
                ))}
              </div>
            ) : (
              <div className="text-center py-8 text-muted-foreground">
                <Calendar className="h-12 w-12 mx-auto mb-4 opacity-50" />
                <p>No upcoming meetings</p>
                <p className="text-sm">Schedule your next S&OP review</p>
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
