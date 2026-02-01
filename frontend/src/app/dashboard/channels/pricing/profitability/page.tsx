'use client';

import { useState, useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import Link from 'next/link';
import {
  TrendingUp,
  TrendingDown,
  DollarSign,
  ArrowUpRight,
  ArrowDownRight,
  BarChart3,
  Package,
  Percent,
  ShoppingCart,
  ArrowLeft,
  ExternalLink,
  Loader2
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { PageHeader } from '@/components/common';
import apiClient from '@/lib/api/client';
import { formatCurrency } from '@/lib/utils';

interface ChannelMetrics {
  channel_id: string;
  channel_name: string;
  channel_type: string;
  period: {
    start_date: string;
    end_date: string;
  };
  revenue: {
    gross_revenue: number;
    discounts: number;
    net_revenue: number;
    order_count: number;
  };
  cost_of_goods_sold: number;
  gross_profit: number;
  gross_margin_percent: number;
  operating_expenses: {
    channel_fees: number;
    shipping_costs: number;
    payment_processing: number;
    total: number;
  };
  operating_income: number;
  operating_margin_percent: number;
  net_income: number;
  net_margin_percent: number;
}

interface PnLResponse {
  report_type: string;
  period: {
    start_date: string;
    end_date: string;
  };
  channels: ChannelMetrics[];
  totals: {
    net_revenue: number;
    cost_of_goods_sold: number;
    gross_profit: number;
    gross_margin_percent: number;
    operating_income: number;
    net_income: number;
    net_margin_percent: number;
  };
}

const channelReportsApi = {
  getPnL: async (params?: { year?: number; month?: number }): Promise<PnLResponse> => {
    try {
      const { data } = await apiClient.get('/channel-reports/pnl', { params });
      return data;
    } catch {
      return {
        report_type: 'Channel P&L',
        period: { start_date: '', end_date: '' },
        channels: [],
        totals: {
          net_revenue: 0,
          cost_of_goods_sold: 0,
          gross_profit: 0,
          gross_margin_percent: 0,
          operating_income: 0,
          net_income: 0,
          net_margin_percent: 0,
        },
      };
    }
  },
};

function getMarginStatus(margin: number): { label: string; color: string; bgColor: string } {
  if (margin >= 20) {
    return { label: 'Healthy', color: 'text-green-700', bgColor: 'bg-green-100' };
  } else if (margin >= 10) {
    return { label: 'Moderate', color: 'text-yellow-700', bgColor: 'bg-yellow-100' };
  } else if (margin >= 0) {
    return { label: 'Low', color: 'text-orange-700', bgColor: 'bg-orange-100' };
  }
  return { label: 'Loss', color: 'text-red-700', bgColor: 'bg-red-100' };
}

function getChannelTypeColor(type: string): string {
  switch (type?.toUpperCase()) {
    case 'D2C': return 'bg-blue-100 text-blue-800';
    case 'B2B': return 'bg-purple-100 text-purple-800';
    case 'MARKETPLACE': return 'bg-green-100 text-green-800';
    case 'OFFLINE': return 'bg-gray-100 text-gray-800';
    default: return 'bg-gray-100 text-gray-800';
  }
}

export default function ChannelProfitabilityPage() {
  const currentDate = new Date();
  const [year, setYear] = useState<number>(currentDate.getFullYear());
  const [month, setMonth] = useState<number>(currentDate.getMonth() + 1);

  const { data, isLoading, error } = useQuery({
    queryKey: ['channel-profitability', year, month],
    queryFn: () => channelReportsApi.getPnL({ year, month }),
  });

  // Calculate summary metrics
  const summary = useMemo(() => {
    if (!data?.channels || data.channels.length === 0) {
      return {
        totalRevenue: 0,
        totalProfit: 0,
        avgMargin: 0,
        totalOrders: 0,
        bestChannel: null as ChannelMetrics | null,
        worstChannel: null as ChannelMetrics | null,
      };
    }

    const channels = data.channels;
    const totalRevenue = channels.reduce((sum, c) => sum + c.revenue.net_revenue, 0);
    const totalProfit = channels.reduce((sum, c) => sum + c.net_income, 0);
    const totalOrders = channels.reduce((sum, c) => sum + c.revenue.order_count, 0);
    const avgMargin = totalRevenue > 0 ? (totalProfit / totalRevenue) * 100 : 0;

    // Find best and worst channels by net margin
    const sortedByMargin = [...channels].sort((a, b) => b.net_margin_percent - a.net_margin_percent);
    const bestChannel = sortedByMargin[0] || null;
    const worstChannel = sortedByMargin[sortedByMargin.length - 1] || null;

    return { totalRevenue, totalProfit, avgMargin, totalOrders, bestChannel, worstChannel };
  }, [data]);

  // Generate month options
  const months = [
    { value: 1, label: 'January' },
    { value: 2, label: 'February' },
    { value: 3, label: 'March' },
    { value: 4, label: 'April' },
    { value: 5, label: 'May' },
    { value: 6, label: 'June' },
    { value: 7, label: 'July' },
    { value: 8, label: 'August' },
    { value: 9, label: 'September' },
    { value: 10, label: 'October' },
    { value: 11, label: 'November' },
    { value: 12, label: 'December' },
  ];

  const years = [2024, 2025, 2026].filter(y => y <= currentDate.getFullYear() + 1);

  return (
    <div className="space-y-6">
      <PageHeader
        title="Channel Profitability"
        description="Analyze profitability and margins across all sales channels"
        actions={
          <div className="flex gap-2">
            <Link href="/dashboard/channels/pricing">
              <Button variant="outline">
                <ArrowLeft className="mr-2 h-4 w-4" />
                Back to Pricing
              </Button>
            </Link>
            <Link href="/dashboard/reports/channel-pl">
              <Button variant="outline">
                <ExternalLink className="mr-2 h-4 w-4" />
                Detailed P&L Report
              </Button>
            </Link>
          </div>
        }
      />

      {/* Period Selector */}
      <div className="flex gap-4 items-center">
        <div className="space-y-1">
          <label className="text-xs text-muted-foreground">Month</label>
          <Select value={month.toString()} onValueChange={(v) => setMonth(parseInt(v))}>
            <SelectTrigger className="w-[150px]">
              <SelectValue placeholder="Select month" />
            </SelectTrigger>
            <SelectContent>
              {months.map((m) => (
                <SelectItem key={m.value} value={m.value.toString()}>
                  {m.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        <div className="space-y-1">
          <label className="text-xs text-muted-foreground">Year</label>
          <Select value={year.toString()} onValueChange={(v) => setYear(parseInt(v))}>
            <SelectTrigger className="w-[100px]">
              <SelectValue placeholder="Year" />
            </SelectTrigger>
            <SelectContent>
              {years.map((y) => (
                <SelectItem key={y} value={y.toString()}>
                  {y}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        {data?.period && (
          <div className="text-sm text-muted-foreground self-end pb-2">
            Period: {data.period.start_date} to {data.period.end_date}
          </div>
        )}
      </div>

      {isLoading ? (
        <div className="flex items-center justify-center py-12">
          <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
        </div>
      ) : error ? (
        <Card>
          <CardContent className="flex flex-col items-center justify-center py-12">
            <BarChart3 className="h-12 w-12 text-muted-foreground mb-4" />
            <p className="text-lg font-medium">Error Loading Data</p>
            <p className="text-sm text-muted-foreground">Please try again later</p>
          </CardContent>
        </Card>
      ) : (
        <>
          {/* Summary Stats Cards */}
          <div className="grid gap-4 md:grid-cols-4">
            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">Total Revenue</CardTitle>
                <DollarSign className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">{formatCurrency(summary.totalRevenue)}</div>
                <p className="text-xs text-muted-foreground">
                  Net revenue across all channels
                </p>
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">Total Profit</CardTitle>
                {summary.totalProfit >= 0 ? (
                  <TrendingUp className="h-4 w-4 text-green-600" />
                ) : (
                  <TrendingDown className="h-4 w-4 text-red-600" />
                )}
              </CardHeader>
              <CardContent>
                <div className={`text-2xl font-bold ${summary.totalProfit >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                  {formatCurrency(summary.totalProfit)}
                </div>
                <p className="text-xs text-muted-foreground">
                  Net income after all costs
                </p>
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">Avg Net Margin</CardTitle>
                <Percent className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <div className={`text-2xl font-bold ${
                  summary.avgMargin >= 15 ? 'text-green-600' :
                  summary.avgMargin >= 5 ? 'text-yellow-600' : 'text-red-600'
                }`}>
                  {summary.avgMargin.toFixed(1)}%
                </div>
                <p className="text-xs text-muted-foreground">
                  Weighted average margin
                </p>
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">Total Orders</CardTitle>
                <ShoppingCart className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">{summary.totalOrders.toLocaleString()}</div>
                <p className="text-xs text-muted-foreground">
                  Across all channels
                </p>
              </CardContent>
            </Card>
          </div>

          {/* Best & Worst Performers */}
          {(summary.bestChannel || summary.worstChannel) && (
            <div className="grid gap-4 md:grid-cols-2">
              {summary.bestChannel && (
                <Card className="border-l-4 border-l-green-500">
                  <CardHeader>
                    <CardTitle className="text-base flex items-center gap-2">
                      <ArrowUpRight className="h-5 w-5 text-green-600" />
                      Best Performer
                    </CardTitle>
                    <CardDescription>Highest net margin this period</CardDescription>
                  </CardHeader>
                  <CardContent>
                    <div className="flex items-center justify-between">
                      <div>
                        <p className="font-semibold text-lg">{summary.bestChannel.channel_name}</p>
                        <Badge className={getChannelTypeColor(summary.bestChannel.channel_type)}>
                          {summary.bestChannel.channel_type}
                        </Badge>
                      </div>
                      <div className="text-right">
                        <p className="text-2xl font-bold text-green-600">
                          {summary.bestChannel.net_margin_percent.toFixed(1)}%
                        </p>
                        <p className="text-sm text-muted-foreground">
                          {formatCurrency(summary.bestChannel.net_income)} profit
                        </p>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              )}
              {summary.worstChannel && summary.worstChannel.channel_id !== summary.bestChannel?.channel_id && (
                <Card className="border-l-4 border-l-orange-500">
                  <CardHeader>
                    <CardTitle className="text-base flex items-center gap-2">
                      <ArrowDownRight className="h-5 w-5 text-orange-600" />
                      Needs Attention
                    </CardTitle>
                    <CardDescription>Lowest net margin this period</CardDescription>
                  </CardHeader>
                  <CardContent>
                    <div className="flex items-center justify-between">
                      <div>
                        <p className="font-semibold text-lg">{summary.worstChannel.channel_name}</p>
                        <Badge className={getChannelTypeColor(summary.worstChannel.channel_type)}>
                          {summary.worstChannel.channel_type}
                        </Badge>
                      </div>
                      <div className="text-right">
                        <p className={`text-2xl font-bold ${
                          summary.worstChannel.net_margin_percent >= 0 ? 'text-orange-600' : 'text-red-600'
                        }`}>
                          {summary.worstChannel.net_margin_percent.toFixed(1)}%
                        </p>
                        <p className="text-sm text-muted-foreground">
                          {formatCurrency(summary.worstChannel.net_income)} profit
                        </p>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              )}
            </div>
          )}

          {/* Channel Profitability Table */}
          <Card>
            <CardHeader>
              <CardTitle>Channel Profitability Comparison</CardTitle>
              <CardDescription>
                Detailed breakdown of revenue, costs, and margins by channel
              </CardDescription>
            </CardHeader>
            <CardContent>
              {data?.channels && data.channels.length > 0 ? (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Channel</TableHead>
                      <TableHead className="text-right">Orders</TableHead>
                      <TableHead className="text-right">Revenue</TableHead>
                      <TableHead className="text-right">COGS</TableHead>
                      <TableHead className="text-right">Gross Margin</TableHead>
                      <TableHead className="text-right">Expenses</TableHead>
                      <TableHead className="text-right">Net Profit</TableHead>
                      <TableHead className="text-right">Net Margin</TableHead>
                      <TableHead>Status</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {data.channels.map((channel) => {
                      const marginStatus = getMarginStatus(channel.net_margin_percent);
                      return (
                        <TableRow key={channel.channel_id}>
                          <TableCell>
                            <div>
                              <p className="font-medium">{channel.channel_name}</p>
                              <Badge variant="secondary" className={`text-xs ${getChannelTypeColor(channel.channel_type)}`}>
                                {channel.channel_type}
                              </Badge>
                            </div>
                          </TableCell>
                          <TableCell className="text-right">
                            {channel.revenue.order_count.toLocaleString()}
                          </TableCell>
                          <TableCell className="text-right font-mono">
                            {formatCurrency(channel.revenue.net_revenue)}
                          </TableCell>
                          <TableCell className="text-right font-mono text-red-600">
                            ({formatCurrency(channel.cost_of_goods_sold)})
                          </TableCell>
                          <TableCell className="text-right">
                            <div className="flex items-center justify-end gap-2">
                              <span className={`font-medium ${
                                channel.gross_margin_percent >= 30 ? 'text-green-600' :
                                channel.gross_margin_percent >= 15 ? 'text-yellow-600' : 'text-red-600'
                              }`}>
                                {channel.gross_margin_percent.toFixed(1)}%
                              </span>
                            </div>
                          </TableCell>
                          <TableCell className="text-right font-mono text-red-600">
                            ({formatCurrency(channel.operating_expenses.total)})
                          </TableCell>
                          <TableCell className={`text-right font-mono font-semibold ${
                            channel.net_income >= 0 ? 'text-green-600' : 'text-red-600'
                          }`}>
                            {formatCurrency(channel.net_income)}
                          </TableCell>
                          <TableCell className="text-right">
                            <span className={`font-semibold ${
                              channel.net_margin_percent >= 15 ? 'text-green-600' :
                              channel.net_margin_percent >= 5 ? 'text-yellow-600' : 'text-red-600'
                            }`}>
                              {channel.net_margin_percent.toFixed(1)}%
                            </span>
                          </TableCell>
                          <TableCell>
                            <Badge className={`${marginStatus.bgColor} ${marginStatus.color}`}>
                              {marginStatus.label}
                            </Badge>
                          </TableCell>
                        </TableRow>
                      );
                    })}
                    {/* Totals Row */}
                    <TableRow className="bg-muted/50 font-bold">
                      <TableCell>
                        <span className="font-bold">TOTAL</span>
                      </TableCell>
                      <TableCell className="text-right">
                        {summary.totalOrders.toLocaleString()}
                      </TableCell>
                      <TableCell className="text-right font-mono">
                        {formatCurrency(data.totals.net_revenue)}
                      </TableCell>
                      <TableCell className="text-right font-mono text-red-600">
                        ({formatCurrency(data.totals.cost_of_goods_sold)})
                      </TableCell>
                      <TableCell className="text-right">
                        <span className="font-medium">
                          {data.totals.gross_margin_percent.toFixed(1)}%
                        </span>
                      </TableCell>
                      <TableCell className="text-right font-mono text-red-600">
                        ({formatCurrency(data.totals.operating_income - data.totals.net_income + data.totals.gross_profit - data.totals.net_revenue + data.totals.cost_of_goods_sold)})
                      </TableCell>
                      <TableCell className={`text-right font-mono ${
                        data.totals.net_income >= 0 ? 'text-green-600' : 'text-red-600'
                      }`}>
                        {formatCurrency(data.totals.net_income)}
                      </TableCell>
                      <TableCell className="text-right">
                        <span className={data.totals.net_margin_percent >= 10 ? 'text-green-600' : 'text-red-600'}>
                          {data.totals.net_margin_percent.toFixed(1)}%
                        </span>
                      </TableCell>
                      <TableCell></TableCell>
                    </TableRow>
                  </TableBody>
                </Table>
              ) : (
                <div className="flex flex-col items-center justify-center py-12">
                  <Package className="h-12 w-12 text-muted-foreground mb-4" />
                  <p className="text-lg font-medium">No Data Available</p>
                  <p className="text-sm text-muted-foreground">
                    No channel profitability data for the selected period
                  </p>
                </div>
              )}
            </CardContent>
          </Card>

          {/* Expense Breakdown */}
          {data?.channels && data.channels.length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle>Operating Expense Breakdown</CardTitle>
                <CardDescription>
                  Channel-wise breakdown of operating costs
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-6">
                  {data.channels.map((channel) => {
                    const total = channel.operating_expenses.total;
                    const feesPct = total > 0 ? (channel.operating_expenses.channel_fees / total) * 100 : 0;
                    const shippingPct = total > 0 ? (channel.operating_expenses.shipping_costs / total) * 100 : 0;
                    const paymentPct = total > 0 ? (channel.operating_expenses.payment_processing / total) * 100 : 0;

                    return (
                      <div key={channel.channel_id} className="space-y-2">
                        <div className="flex items-center justify-between">
                          <div className="flex items-center gap-2">
                            <span className="font-medium">{channel.channel_name}</span>
                            <Badge variant="outline" className="text-xs">
                              {formatCurrency(total)} total
                            </Badge>
                          </div>
                        </div>
                        <div className="grid grid-cols-3 gap-4 text-sm">
                          <div>
                            <div className="flex justify-between mb-1">
                              <span className="text-muted-foreground">Channel Fees</span>
                              <span>{formatCurrency(channel.operating_expenses.channel_fees)}</span>
                            </div>
                            <Progress value={feesPct} className="h-2" />
                          </div>
                          <div>
                            <div className="flex justify-between mb-1">
                              <span className="text-muted-foreground">Shipping</span>
                              <span>{formatCurrency(channel.operating_expenses.shipping_costs)}</span>
                            </div>
                            <Progress value={shippingPct} className="h-2" />
                          </div>
                          <div>
                            <div className="flex justify-between mb-1">
                              <span className="text-muted-foreground">Payment Fees</span>
                              <span>{formatCurrency(channel.operating_expenses.payment_processing)}</span>
                            </div>
                            <Progress value={paymentPct} className="h-2" />
                          </div>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </CardContent>
            </Card>
          )}
        </>
      )}
    </div>
  );
}
