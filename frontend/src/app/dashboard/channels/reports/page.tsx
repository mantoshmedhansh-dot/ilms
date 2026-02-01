'use client';

import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { BarChart3, TrendingUp, TrendingDown, DollarSign, ShoppingCart, Package, ArrowUpRight, ArrowDownRight } from 'lucide-react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { PageHeader } from '@/components/common';
import apiClient from '@/lib/api/client';
import { formatCurrency } from '@/lib/utils';

interface ChannelReport {
  channel_id: string;
  channel_name: string;
  channel_type: string;
  total_orders: number;
  total_revenue: number;
  total_units_sold: number;
  avg_order_value: number;
  return_rate: number;
  cancellation_rate: number;
  gross_margin: number;
  net_margin: number;
  commission_paid: number;
  shipping_cost: number;
  marketing_cost: number;
  revenue_change: number;
  orders_change: number;
}

interface ChannelSummary {
  total_revenue: number;
  total_orders: number;
  total_units_sold: number;
  avg_order_value: number;
  best_performing_channel: string;
  worst_performing_channel: string;
}

const reportsApi = {
  getChannelReports: async (params?: { period?: string }) => {
    try {
      const { data } = await apiClient.get('/channels/reports', { params });
      return data;
    } catch {
      return { items: [], summary: null };
    }
  },
  getChannelSummary: async (params?: { period?: string }): Promise<ChannelSummary | null> => {
    try {
      const { data } = await apiClient.get('/channels/reports/summary', { params });
      return data;
    } catch {
      return null;
    }
  },
};

export default function ChannelReportsPage() {
  const [period, setPeriod] = useState<string>('this_month');

  const { data: reports, isLoading } = useQuery({
    queryKey: ['channel-reports', period],
    queryFn: () => reportsApi.getChannelReports({ period }),
  });

  const { data: summary } = useQuery({
    queryKey: ['channel-summary', period],
    queryFn: () => reportsApi.getChannelSummary({ period }),
  });

  const channelReports: ChannelReport[] = reports?.items || [];

  return (
    <div className="space-y-6">
      <PageHeader
        title="Channel Reports"
        description="Analyze performance across all sales channels"
        actions={
          <Select value={period} onValueChange={setPeriod}>
            <SelectTrigger className="w-[180px]">
              <SelectValue placeholder="Select period" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="today">Today</SelectItem>
              <SelectItem value="yesterday">Yesterday</SelectItem>
              <SelectItem value="this_week">This Week</SelectItem>
              <SelectItem value="last_week">Last Week</SelectItem>
              <SelectItem value="this_month">This Month</SelectItem>
              <SelectItem value="last_month">Last Month</SelectItem>
              <SelectItem value="this_quarter">This Quarter</SelectItem>
              <SelectItem value="this_year">This Year</SelectItem>
            </SelectContent>
          </Select>
        }
      />

      {/* Summary Cards */}
      <div className="grid gap-4 md:grid-cols-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Revenue</CardTitle>
            <DollarSign className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{formatCurrency(summary?.total_revenue || 0)}</div>
            <p className="text-xs text-muted-foreground">Across all channels</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Orders</CardTitle>
            <ShoppingCart className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{summary?.total_orders || 0}</div>
            <p className="text-xs text-muted-foreground">AOV: {formatCurrency(summary?.avg_order_value || 0)}</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Units Sold</CardTitle>
            <Package className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{summary?.total_units_sold || 0}</div>
            <p className="text-xs text-muted-foreground">Total units</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Best Channel</CardTitle>
            <TrendingUp className="h-4 w-4 text-green-600" />
          </CardHeader>
          <CardContent>
            <div className="text-xl font-bold text-green-600">{summary?.best_performing_channel || '-'}</div>
            <p className="text-xs text-muted-foreground">Top performer</p>
          </CardContent>
        </Card>
      </div>

      {/* Channel Performance Cards */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        {isLoading ? (
          Array.from({ length: 6 }).map((_, i) => (
            <Card key={i} className="animate-pulse">
              <CardHeader>
                <div className="h-4 w-24 bg-muted rounded" />
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  <div className="h-8 w-32 bg-muted rounded" />
                  <div className="h-4 w-full bg-muted rounded" />
                  <div className="h-4 w-3/4 bg-muted rounded" />
                </div>
              </CardContent>
            </Card>
          ))
        ) : channelReports.length === 0 ? (
          <Card className="col-span-full">
            <CardContent className="flex flex-col items-center justify-center py-12">
              <BarChart3 className="h-12 w-12 text-muted-foreground mb-4" />
              <p className="text-muted-foreground">No channel data available for the selected period</p>
            </CardContent>
          </Card>
        ) : (
          channelReports.map((channel) => (
            <Card key={channel.channel_id}>
              <CardHeader className="pb-2">
                <div className="flex items-center justify-between">
                  <CardTitle className="text-lg">{channel.channel_name}</CardTitle>
                  <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                    channel.channel_type === 'D2C' ? 'bg-green-100 text-green-800' :
                    channel.channel_type === 'MARKETPLACE' ? 'bg-purple-100 text-purple-800' :
                    'bg-gray-100 text-gray-800'
                  }`}>
                    {channel.channel_type}
                  </span>
                </div>
                <CardDescription>
                  {channel.total_orders} orders | {channel.total_units_sold} units
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  {/* Revenue */}
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-muted-foreground">Revenue</span>
                    <div className="flex items-center gap-2">
                      <span className="font-bold">{formatCurrency(channel.total_revenue)}</span>
                      <span className={`flex items-center text-xs ${
                        channel.revenue_change >= 0 ? 'text-green-600' : 'text-red-600'
                      }`}>
                        {channel.revenue_change >= 0 ? (
                          <ArrowUpRight className="h-3 w-3" />
                        ) : (
                          <ArrowDownRight className="h-3 w-3" />
                        )}
                        {Math.abs(channel.revenue_change).toFixed(1)}%
                      </span>
                    </div>
                  </div>

                  {/* AOV */}
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-muted-foreground">Avg Order Value</span>
                    <span className="font-medium">{formatCurrency(channel.avg_order_value)}</span>
                  </div>

                  {/* Margins */}
                  <div className="grid grid-cols-2 gap-4 pt-2 border-t">
                    <div>
                      <div className="text-xs text-muted-foreground">Gross Margin</div>
                      <div className={`font-medium ${channel.gross_margin >= 30 ? 'text-green-600' : 'text-orange-600'}`}>
                        {channel.gross_margin.toFixed(1)}%
                      </div>
                    </div>
                    <div>
                      <div className="text-xs text-muted-foreground">Net Margin</div>
                      <div className={`font-medium ${channel.net_margin >= 15 ? 'text-green-600' : 'text-orange-600'}`}>
                        {channel.net_margin.toFixed(1)}%
                      </div>
                    </div>
                  </div>

                  {/* Costs */}
                  <div className="grid grid-cols-3 gap-2 pt-2 border-t text-center">
                    <div>
                      <div className="text-xs text-muted-foreground">Commission</div>
                      <div className="text-sm font-medium">{formatCurrency(channel.commission_paid)}</div>
                    </div>
                    <div>
                      <div className="text-xs text-muted-foreground">Shipping</div>
                      <div className="text-sm font-medium">{formatCurrency(channel.shipping_cost)}</div>
                    </div>
                    <div>
                      <div className="text-xs text-muted-foreground">Marketing</div>
                      <div className="text-sm font-medium">{formatCurrency(channel.marketing_cost)}</div>
                    </div>
                  </div>

                  {/* Return & Cancellation Rates */}
                  <div className="flex items-center justify-between pt-2 border-t">
                    <div className="flex items-center gap-2">
                      <span className="text-xs text-muted-foreground">Returns:</span>
                      <span className={`text-xs font-medium ${channel.return_rate > 5 ? 'text-red-600' : 'text-green-600'}`}>
                        {channel.return_rate.toFixed(1)}%
                      </span>
                    </div>
                    <div className="flex items-center gap-2">
                      <span className="text-xs text-muted-foreground">Cancellations:</span>
                      <span className={`text-xs font-medium ${channel.cancellation_rate > 5 ? 'text-red-600' : 'text-green-600'}`}>
                        {channel.cancellation_rate.toFixed(1)}%
                      </span>
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>
          ))
        )}
      </div>
    </div>
  );
}
