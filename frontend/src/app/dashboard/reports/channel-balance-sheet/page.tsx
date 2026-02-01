'use client';

import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Download, MinusCircle, PlusCircle, Building2, Wallet, Scale } from 'lucide-react';
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

interface BSLineItem {
  account_code: string;
  account_name: string;
  amount: number;
  previous_amount: number;
  is_header: boolean;
  indent_level: number;
}

interface ChannelBalanceSheet {
  channel_id: string;
  channel_name: string;
  channel_type: string;
  assets: {
    current_assets: BSLineItem[];
    non_current_assets: BSLineItem[];
    total_assets: number;
  };
  liabilities: {
    current_liabilities: BSLineItem[];
    non_current_liabilities: BSLineItem[];
    total_liabilities: number;
  };
  equity: {
    items: BSLineItem[];
    total_equity: number;
  };
  previous_total_assets: number;
  previous_total_liabilities: number;
  previous_total_equity: number;
}

interface ConsolidatedBS {
  as_of_date: string;
  total_assets: number;
  total_liabilities: number;
  total_equity: number;
  channels: ChannelBalanceSheet[];
}

const reportsApi = {
  getChannelBalanceSheet: async (params?: { as_of_date?: string; channel_id?: string }): Promise<ConsolidatedBS> => {
    try {
      const { data } = await apiClient.get('/reports/channel-balance-sheet', { params });
      return data;
    } catch {
      return {
        as_of_date: new Date().toISOString(),
        total_assets: 0,
        total_liabilities: 0,
        total_equity: 0,
        channels: []
      };
    }
  },
};

export default function ChannelBalanceSheetPage() {
  const [asOfDate, setAsOfDate] = useState<string>('today');
  const [channelFilter, setChannelFilter] = useState<string>('all');
  const [expandedSections, setExpandedSections] = useState<Record<string, boolean>>({
    current_assets: true,
    non_current_assets: false,
    current_liabilities: true,
    non_current_liabilities: false,
    equity: true,
  });

  const { data, isLoading } = useQuery({
    queryKey: ['channel-balance-sheet', asOfDate, channelFilter],
    queryFn: () => reportsApi.getChannelBalanceSheet({
      as_of_date: asOfDate === 'today' ? undefined : asOfDate,
      channel_id: channelFilter !== 'all' ? channelFilter : undefined
    }),
  });

  const toggleSection = (section: string) => {
    setExpandedSections(prev => ({ ...prev, [section]: !prev[section] }));
  };

  const renderBSSection = (title: string, items: BSLineItem[], sectionKey: string) => {
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
          <TableCell className="text-right font-mono">{formatCurrency(total)}</TableCell>
          <TableCell className="text-right text-muted-foreground">-</TableCell>
        </TableRow>
        {isExpanded && items.map((item, idx) => (
          <TableRow key={idx} className={item.is_header ? 'bg-muted/30' : ''}>
            <TableCell className={`pl-${4 + (item.indent_level * 4)} ${item.is_header ? 'font-medium' : ''}`}>
              {item.account_name}
            </TableCell>
            <TableCell className="text-right font-mono">
              {item.is_header ? '' : formatCurrency(item.amount)}
            </TableCell>
            <TableCell className="text-right font-mono text-muted-foreground">
              {item.is_header ? '' : formatCurrency(item.previous_amount)}
            </TableCell>
          </TableRow>
        ))}
      </>
    );
  };

  const selectedChannel = channelFilter !== 'all' && data?.channels?.[0];

  return (
    <div className="space-y-6">
      <PageHeader
        title="Channel-wise Balance Sheet"
        description="Financial position by sales channel"
        actions={
          <Button variant="outline">
            <Download className="mr-2 h-4 w-4" />
            Export
          </Button>
        }
      />

      {/* Filters */}
      <div className="flex gap-4">
        <Select value={asOfDate} onValueChange={setAsOfDate}>
          <SelectTrigger className="w-[180px]">
            <SelectValue placeholder="As of date" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="today">As of Today</SelectItem>
            <SelectItem value="month_end">Month End</SelectItem>
            <SelectItem value="quarter_end">Quarter End</SelectItem>
            <SelectItem value="year_end">Year End</SelectItem>
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
      <div className="grid gap-4 md:grid-cols-3">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Assets</CardTitle>
            <Building2 className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-blue-600">{formatCurrency(data?.total_assets || 0)}</div>
            <p className="text-xs text-muted-foreground">What the business owns</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Liabilities</CardTitle>
            <Wallet className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-red-600">{formatCurrency(data?.total_liabilities || 0)}</div>
            <p className="text-xs text-muted-foreground">What the business owes</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Equity</CardTitle>
            <Scale className="h-4 w-4 text-green-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-green-600">{formatCurrency(data?.total_equity || 0)}</div>
            <p className="text-xs text-muted-foreground">Owner&apos;s stake</p>
          </CardContent>
        </Card>
      </div>

      {/* Accounting Equation Check */}
      <Card className="border-l-4 border-l-primary">
        <CardContent className="py-4">
          <div className="flex items-center justify-center gap-4 text-lg font-mono">
            <span className="text-blue-600">{formatCurrency(data?.total_assets || 0)}</span>
            <span>=</span>
            <span className="text-red-600">{formatCurrency(data?.total_liabilities || 0)}</span>
            <span>+</span>
            <span className="text-green-600">{formatCurrency(data?.total_equity || 0)}</span>
          </div>
          <div className="flex items-center justify-center gap-4 text-sm text-muted-foreground">
            <span>Assets</span>
            <span>=</span>
            <span>Liabilities</span>
            <span>+</span>
            <span>Equity</span>
          </div>
        </CardContent>
      </Card>

      {/* Channel Comparison */}
      {channelFilter === 'all' && data?.channels && data.channels.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Channel Financial Position</CardTitle>
            <CardDescription>Compare financial health across channels</CardDescription>
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
                        <span className="text-sm text-muted-foreground">Assets</span>
                        <span className="font-mono text-blue-600">{formatCurrency(channel.assets.total_assets)}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-sm text-muted-foreground">Liabilities</span>
                        <span className="font-mono text-red-600">{formatCurrency(channel.liabilities.total_liabilities)}</span>
                      </div>
                      <div className="flex justify-between border-t pt-2">
                        <span className="text-sm font-medium">Equity</span>
                        <span className={`font-mono font-bold ${channel.equity.total_equity >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                          {formatCurrency(channel.equity.total_equity)}
                        </span>
                      </div>
                      <div className="flex justify-between text-xs">
                        <span className="text-muted-foreground">Debt-to-Equity</span>
                        <span className={channel.equity.total_equity > 0 && channel.liabilities.total_liabilities / channel.equity.total_equity < 1 ? 'text-green-600' : 'text-orange-600'}>
                          {channel.equity.total_equity > 0
                            ? (channel.liabilities.total_liabilities / channel.equity.total_equity).toFixed(2)
                            : 'N/A'}
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

      {/* Detailed Balance Sheet */}
      <Card>
        <CardHeader>
          <CardTitle>Detailed Balance Sheet</CardTitle>
          <CardDescription>As of {data?.as_of_date ? new Date(data.as_of_date).toLocaleDateString('en-IN', { dateStyle: 'long' }) : 'Today'}</CardDescription>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="flex items-center justify-center py-12">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" />
            </div>
          ) : selectedChannel ? (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="w-[50%]">Account</TableHead>
                  <TableHead className="text-right">Current Period</TableHead>
                  <TableHead className="text-right">Previous Period</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {/* ASSETS */}
                <TableRow className="bg-blue-50 font-bold text-blue-900">
                  <TableCell colSpan={3}>ASSETS</TableCell>
                </TableRow>
                {renderBSSection('Current Assets', selectedChannel.assets.current_assets, 'current_assets')}
                {renderBSSection('Non-Current Assets', selectedChannel.assets.non_current_assets, 'non_current_assets')}
                <TableRow className="bg-blue-100 font-bold">
                  <TableCell>TOTAL ASSETS</TableCell>
                  <TableCell className="text-right font-mono text-blue-600">
                    {formatCurrency(selectedChannel.assets.total_assets)}
                  </TableCell>
                  <TableCell className="text-right font-mono text-muted-foreground">
                    {formatCurrency(selectedChannel.previous_total_assets)}
                  </TableCell>
                </TableRow>

                {/* LIABILITIES */}
                <TableRow className="bg-red-50 font-bold text-red-900">
                  <TableCell colSpan={3}>LIABILITIES</TableCell>
                </TableRow>
                {renderBSSection('Current Liabilities', selectedChannel.liabilities.current_liabilities, 'current_liabilities')}
                {renderBSSection('Non-Current Liabilities', selectedChannel.liabilities.non_current_liabilities, 'non_current_liabilities')}
                <TableRow className="bg-red-100 font-bold">
                  <TableCell>TOTAL LIABILITIES</TableCell>
                  <TableCell className="text-right font-mono text-red-600">
                    {formatCurrency(selectedChannel.liabilities.total_liabilities)}
                  </TableCell>
                  <TableCell className="text-right font-mono text-muted-foreground">
                    {formatCurrency(selectedChannel.previous_total_liabilities)}
                  </TableCell>
                </TableRow>

                {/* EQUITY */}
                <TableRow className="bg-green-50 font-bold text-green-900">
                  <TableCell colSpan={3}>EQUITY</TableCell>
                </TableRow>
                {renderBSSection('Equity', selectedChannel.equity.items, 'equity')}
                <TableRow className="bg-green-100 font-bold">
                  <TableCell>TOTAL EQUITY</TableCell>
                  <TableCell className="text-right font-mono text-green-600">
                    {formatCurrency(selectedChannel.equity.total_equity)}
                  </TableCell>
                  <TableCell className="text-right font-mono text-muted-foreground">
                    {formatCurrency(selectedChannel.previous_total_equity)}
                  </TableCell>
                </TableRow>

                {/* TOTAL LIABILITIES + EQUITY */}
                <TableRow className="bg-primary/10 font-bold text-lg">
                  <TableCell>TOTAL LIABILITIES + EQUITY</TableCell>
                  <TableCell className="text-right font-mono">
                    {formatCurrency(selectedChannel.liabilities.total_liabilities + selectedChannel.equity.total_equity)}
                  </TableCell>
                  <TableCell className="text-right font-mono text-muted-foreground">
                    {formatCurrency(selectedChannel.previous_total_liabilities + selectedChannel.previous_total_equity)}
                  </TableCell>
                </TableRow>
              </TableBody>
            </Table>
          ) : (
            <div className="text-center py-12 text-muted-foreground">
              <Scale className="h-12 w-12 mx-auto mb-4 opacity-50" />
              <p>Select a specific channel to view detailed Balance Sheet</p>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
