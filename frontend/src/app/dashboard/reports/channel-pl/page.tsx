'use client';

import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Download, TrendingUp, TrendingDown, DollarSign, MinusCircle, PlusCircle, BarChart3 } from 'lucide-react';
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
import { PageHeader } from '@/components/common';
import apiClient from '@/lib/api/client';
import { formatCurrency } from '@/lib/utils';

interface PLLineItem {
  account_code: string;
  account_name: string;
  amount: number;
  previous_amount: number;
  change_percent: number;
  is_header: boolean;
  indent_level: number;
}

interface ChannelPL {
  channel_id: string;
  channel_name: string;
  channel_type: string;
  revenue: PLLineItem[];
  cost_of_goods_sold: PLLineItem[];
  gross_profit: number;
  gross_margin_percent: number;
  operating_expenses: PLLineItem[];
  operating_income: number;
  other_income_expense: PLLineItem[];
  net_income: number;
  net_margin_percent: number;
  previous_gross_profit: number;
  previous_net_income: number;
}

interface ConsolidatedPL {
  total_revenue: number;
  total_cogs: number;
  total_gross_profit: number;
  total_operating_expenses: number;
  total_net_income: number;
  channels: ChannelPL[];
}

const reportsApi = {
  getChannelPL: async (params?: { period?: string; channel_id?: string }): Promise<ConsolidatedPL> => {
    try {
      const { data } = await apiClient.get('/reports/channel-pl', { params });
      return data;
    } catch {
      return {
        total_revenue: 0,
        total_cogs: 0,
        total_gross_profit: 0,
        total_operating_expenses: 0,
        total_net_income: 0,
        channels: []
      };
    }
  },
};

export default function ChannelPLPage() {
  const [period, setPeriod] = useState<string>('this_month');
  const [channelFilter, setChannelFilter] = useState<string>('all');
  const [expandedSections, setExpandedSections] = useState<Record<string, boolean>>({
    revenue: true,
    cogs: true,
    opex: false,
    other: false,
  });

  const { data, isLoading } = useQuery({
    queryKey: ['channel-pl', period, channelFilter],
    queryFn: () => reportsApi.getChannelPL({ period, channel_id: channelFilter !== 'all' ? channelFilter : undefined }),
  });

  const toggleSection = (section: string) => {
    setExpandedSections(prev => ({ ...prev, [section]: !prev[section] }));
  };

  const renderPLSection = (title: string, items: PLLineItem[], sectionKey: string, isExpense: boolean = false) => {
    const isExpanded = expandedSections[sectionKey];
    const total = items.reduce((sum, item) => !item.is_header ? sum + item.amount : sum, 0);

    return (
      <>
        <TableRow
          className="cursor-pointer hover:bg-muted/50 font-semibold"
          onClick={() => toggleSection(sectionKey)}
        >
          <TableCell className="flex items-center gap-2">
            {isExpanded ? <MinusCircle className="h-4 w-4" /> : <PlusCircle className="h-4 w-4" />}
            {title}
          </TableCell>
          <TableCell className={`text-right font-mono ${isExpense ? 'text-red-600' : 'text-green-600'}`}>
            {isExpense ? `(${formatCurrency(Math.abs(total))})` : formatCurrency(total)}
          </TableCell>
          <TableCell className="text-right text-muted-foreground">-</TableCell>
          <TableCell className="text-right">-</TableCell>
        </TableRow>
        {isExpanded && items.map((item, idx) => (
          <TableRow key={idx} className={item.is_header ? 'bg-muted/30' : ''}>
            <TableCell className={`pl-${4 + (item.indent_level * 4)} ${item.is_header ? 'font-medium' : ''}`}>
              {item.account_name}
            </TableCell>
            <TableCell className={`text-right font-mono ${isExpense && item.amount > 0 ? 'text-red-600' : ''}`}>
              {item.is_header ? '' : formatCurrency(item.amount)}
            </TableCell>
            <TableCell className="text-right font-mono text-muted-foreground">
              {item.is_header ? '' : formatCurrency(item.previous_amount)}
            </TableCell>
            <TableCell className="text-right">
              {!item.is_header && item.change_percent !== 0 && (
                <span className={`flex items-center justify-end gap-1 ${
                  item.change_percent > 0 ? 'text-green-600' : 'text-red-600'
                }`}>
                  {item.change_percent > 0 ? (
                    <TrendingUp className="h-3 w-3" />
                  ) : (
                    <TrendingDown className="h-3 w-3" />
                  )}
                  {Math.abs(item.change_percent).toFixed(1)}%
                </span>
              )}
            </TableCell>
          </TableRow>
        ))}
      </>
    );
  };

  return (
    <div className="space-y-6">
      <PageHeader
        title="Channel-wise P&L"
        description="Profit & Loss statement by sales channel"
        actions={
          <Button variant="outline">
            <Download className="mr-2 h-4 w-4" />
            Export
          </Button>
        }
      />

      {/* Filters */}
      <div className="flex gap-4">
        <Select value={period} onValueChange={setPeriod}>
          <SelectTrigger className="w-[180px]">
            <SelectValue placeholder="Select period" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="this_month">This Month</SelectItem>
            <SelectItem value="last_month">Last Month</SelectItem>
            <SelectItem value="this_quarter">This Quarter</SelectItem>
            <SelectItem value="last_quarter">Last Quarter</SelectItem>
            <SelectItem value="this_year">This Year</SelectItem>
            <SelectItem value="last_year">Last Year</SelectItem>
          </SelectContent>
        </Select>
        <Select value={channelFilter} onValueChange={setChannelFilter}>
          <SelectTrigger className="w-[200px]">
            <SelectValue placeholder="All Channels" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Channels (Consolidated)</SelectItem>
            <SelectItem value="d2c">D2C Website</SelectItem>
            <SelectItem value="amazon">Amazon</SelectItem>
            <SelectItem value="flipkart">Flipkart</SelectItem>
            <SelectItem value="b2b">B2B / GTMT</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {/* Summary Cards */}
      <div className="grid gap-4 md:grid-cols-5">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Revenue</CardTitle>
            <DollarSign className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-green-600">{formatCurrency(data?.total_revenue || 0)}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Cost of Goods</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-red-600">({formatCurrency(data?.total_cogs || 0)})</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Gross Profit</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{formatCurrency(data?.total_gross_profit || 0)}</div>
            <p className="text-xs text-muted-foreground">
              {data?.total_revenue ? ((data.total_gross_profit / data.total_revenue) * 100).toFixed(1) : 0}% margin
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Operating Expenses</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-red-600">({formatCurrency(data?.total_operating_expenses || 0)})</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Net Income</CardTitle>
            <TrendingUp className="h-4 w-4 text-green-600" />
          </CardHeader>
          <CardContent>
            <div className={`text-2xl font-bold ${(data?.total_net_income || 0) >= 0 ? 'text-green-600' : 'text-red-600'}`}>
              {formatCurrency(data?.total_net_income || 0)}
            </div>
            <p className="text-xs text-muted-foreground">
              {data?.total_revenue ? ((data.total_net_income / data.total_revenue) * 100).toFixed(1) : 0}% margin
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Channel Comparison */}
      {channelFilter === 'all' && data?.channels && data.channels.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Channel Comparison</CardTitle>
            <CardDescription>Compare profitability across channels</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
              {data.channels.map((channel) => (
                <Card key={channel.channel_id} className="border-l-4 border-l-primary">
                  <CardHeader className="pb-2">
                    <CardTitle className="text-base">{channel.channel_name}</CardTitle>
                    <CardDescription>{channel.channel_type}</CardDescription>
                  </CardHeader>
                  <CardContent>
                    <div className="space-y-2">
                      <div className="flex justify-between">
                        <span className="text-sm text-muted-foreground">Gross Profit</span>
                        <span className="font-mono">{formatCurrency(channel.gross_profit)}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-sm text-muted-foreground">Gross Margin</span>
                        <span className={`font-medium ${channel.gross_margin_percent >= 30 ? 'text-green-600' : 'text-orange-600'}`}>
                          {channel.gross_margin_percent.toFixed(1)}%
                        </span>
                      </div>
                      <div className="flex justify-between border-t pt-2">
                        <span className="text-sm text-muted-foreground">Net Income</span>
                        <span className={`font-mono font-bold ${channel.net_income >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                          {formatCurrency(channel.net_income)}
                        </span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-sm text-muted-foreground">Net Margin</span>
                        <span className={`font-medium ${channel.net_margin_percent >= 15 ? 'text-green-600' : 'text-orange-600'}`}>
                          {channel.net_margin_percent.toFixed(1)}%
                        </span>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Detailed P&L Table */}
      <Card>
        <CardHeader>
          <CardTitle>Detailed P&L Statement</CardTitle>
          <CardDescription>Click on sections to expand/collapse</CardDescription>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="flex items-center justify-center py-12">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" />
            </div>
          ) : channelFilter !== 'all' && data?.channels?.[0] ? (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="w-[40%]">Account</TableHead>
                  <TableHead className="text-right">Current Period</TableHead>
                  <TableHead className="text-right">Previous Period</TableHead>
                  <TableHead className="text-right">Change</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {renderPLSection('Revenue', data.channels[0].revenue, 'revenue')}
                {renderPLSection('Cost of Goods Sold', data.channels[0].cost_of_goods_sold, 'cogs', true)}

                <TableRow className="bg-muted font-bold">
                  <TableCell>Gross Profit</TableCell>
                  <TableCell className="text-right font-mono">{formatCurrency(data.channels[0].gross_profit)}</TableCell>
                  <TableCell className="text-right font-mono text-muted-foreground">
                    {formatCurrency(data.channels[0].previous_gross_profit)}
                  </TableCell>
                  <TableCell className="text-right">
                    <span className="text-green-600">{data.channels[0].gross_margin_percent.toFixed(1)}% margin</span>
                  </TableCell>
                </TableRow>

                {renderPLSection('Operating Expenses', data.channels[0].operating_expenses, 'opex', true)}

                <TableRow className="bg-muted font-bold">
                  <TableCell>Operating Income</TableCell>
                  <TableCell className="text-right font-mono">{formatCurrency(data.channels[0].operating_income)}</TableCell>
                  <TableCell className="text-right font-mono text-muted-foreground">-</TableCell>
                  <TableCell></TableCell>
                </TableRow>

                {data.channels[0].other_income_expense.length > 0 &&
                  renderPLSection('Other Income/Expense', data.channels[0].other_income_expense, 'other')}

                <TableRow className="bg-primary/10 font-bold text-lg">
                  <TableCell>Net Income</TableCell>
                  <TableCell className={`text-right font-mono ${data.channels[0].net_income >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                    {formatCurrency(data.channels[0].net_income)}
                  </TableCell>
                  <TableCell className="text-right font-mono text-muted-foreground">
                    {formatCurrency(data.channels[0].previous_net_income)}
                  </TableCell>
                  <TableCell className="text-right">
                    <span className={data.channels[0].net_margin_percent >= 0 ? 'text-green-600' : 'text-red-600'}>
                      {data.channels[0].net_margin_percent.toFixed(1)}% margin
                    </span>
                  </TableCell>
                </TableRow>
              </TableBody>
            </Table>
          ) : (
            <div className="text-center py-12 text-muted-foreground">
              <BarChart3 className="h-12 w-12 mx-auto mb-4 opacity-50" />
              <p>Select a specific channel to view detailed P&L</p>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
