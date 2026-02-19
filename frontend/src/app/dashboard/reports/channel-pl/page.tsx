'use client';

import { useState, useEffect, useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import {
  Download, TrendingUp, TrendingDown, DollarSign,
  MinusCircle, PlusCircle, BarChart3, MapPin, ChevronRight,
  Users, Warehouse as WarehouseIcon
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
import { PageHeader } from '@/components/common';
import apiClient from '@/lib/api/client';
import { formatCurrency } from '@/lib/utils';

// ==================== Types ====================

interface GeoWarehouse {
  id: string;
  name: string;
  code: string;
}

interface GeoCluster {
  id: string;
  name: string;
  code: string;
  type: string;
  warehouses: GeoWarehouse[];
}

interface GeoRegion {
  id: string;
  name: string;
  code: string;
  type: string;
  clusters: GeoCluster[];
  warehouses: GeoWarehouse[];
}

interface GeoHierarchy {
  regions: GeoRegion[];
}

interface ManpowerDepartment {
  department: string;
  headcount: number;
  cost: number;
}

interface ManpowerDetail {
  total_manpower_cost: number;
  headcount: number;
  avg_monthly_ctc: number;
  by_department: ManpowerDepartment[];
}

interface ChannelPnlRevenue {
  gross_revenue: number;
  discounts: number;
  net_revenue: number;
  order_count: number;
}

interface ChannelPnlCogs {
  product_cost: number;
  gross_profit: number;
  gross_margin_pct: number;
}

interface ChannelPnlOpex {
  channel_commission: number;
  shipping_cost: number;
  payment_processing: number;
  warehouse_storage: number;
  warehouse_handling: number;
  warehouse_vas: number;
  manpower_cost: number;
  total_opex: number;
}

interface ChannelPnl {
  channel_id: string;
  channel_name: string;
  channel_type: string;
  period: { start_date: string; end_date: string };
  geo_filter: Record<string, string> | null;
  revenue: ChannelPnlRevenue;
  cogs: ChannelPnlCogs;
  opex: ChannelPnlOpex;
  ebitda: number;
  ebitda_margin_pct: number;
  manpower_detail?: ManpowerDetail;
}

interface PnlResponse {
  report_type: string;
  period: { start_date: string; end_date: string };
  geo_filter: Record<string, string> | null;
  channels: ChannelPnl[];
  totals: {
    net_revenue: number;
    cost_of_goods_sold: number;
    gross_profit: number;
    gross_margin_pct: number;
    total_opex: number;
    ebitda: number;
    ebitda_margin_pct: number;
  };
}

// ==================== API ====================

const reportsApi = {
  getGeoHierarchy: async (): Promise<GeoHierarchy> => {
    try {
      const { data } = await apiClient.get('/channel-reports/geo-hierarchy');
      return data;
    } catch {
      return { regions: [] };
    }
  },
  getChannelPL: async (params: Record<string, string | boolean | undefined>): Promise<PnlResponse> => {
    try {
      const cleanParams: Record<string, string | boolean> = {};
      Object.entries(params).forEach(([k, v]) => {
        if (v !== undefined && v !== '' && v !== 'all') cleanParams[k] = v;
      });
      const { data } = await apiClient.get('/channel-reports/pnl', { params: cleanParams });
      return data;
    } catch {
      return {
        report_type: 'Channel P&L',
        period: { start_date: '', end_date: '' },
        geo_filter: null,
        channels: [],
        totals: {
          net_revenue: 0, cost_of_goods_sold: 0, gross_profit: 0,
          gross_margin_pct: 0, total_opex: 0, ebitda: 0, ebitda_margin_pct: 0,
        },
      };
    }
  },
};

// ==================== Component ====================

export default function ChannelPLPage() {
  const [period, setPeriod] = useState<string>('this_month');
  const [channelFilter, setChannelFilter] = useState<string>('all');

  // Geographic drill-down state
  const [regionFilter, setRegionFilter] = useState<string>('all');
  const [clusterFilter, setClusterFilter] = useState<string>('all');
  const [warehouseFilter, setWarehouseFilter] = useState<string>('all');

  // Cost toggles
  const [includeManpower, setIncludeManpower] = useState(false);
  const [includeWarehouseCosts, setIncludeWarehouseCosts] = useState(false);

  // Expandable sections
  const [expandedSections, setExpandedSections] = useState<Record<string, boolean>>({
    revenue: true,
    cogs: true,
    opex: true,
    warehouse_ops: false,
    manpower: false,
  });

  // Geo hierarchy data
  const { data: geoData } = useQuery({
    queryKey: ['geo-hierarchy'],
    queryFn: reportsApi.getGeoHierarchy,
    staleTime: 5 * 60 * 1000,
  });

  // Cascading filter: reset downstream when upstream changes
  useEffect(() => { setClusterFilter('all'); setWarehouseFilter('all'); }, [regionFilter]);
  useEffect(() => { setWarehouseFilter('all'); }, [clusterFilter]);

  // Auto-enable cost toggles when warehouse is selected
  useEffect(() => {
    if (warehouseFilter !== 'all') {
      setIncludeManpower(true);
      setIncludeWarehouseCosts(true);
    }
  }, [warehouseFilter]);

  // Derive date params from period selection
  const dateParams = useMemo(() => {
    const now = new Date();
    const y = now.getFullYear();
    const m = now.getMonth() + 1;
    switch (period) {
      case 'this_month': return { year: String(y), month: String(m) };
      case 'last_month': {
        const lm = m === 1 ? 12 : m - 1;
        const ly = m === 1 ? y - 1 : y;
        return { year: String(ly), month: String(lm) };
      }
      case 'this_quarter': {
        const qStart = new Date(y, Math.floor((m - 1) / 3) * 3, 1);
        return {
          start_date: qStart.toISOString().split('T')[0],
          end_date: now.toISOString().split('T')[0],
        };
      }
      case 'last_quarter': {
        const cqStart = Math.floor((m - 1) / 3) * 3;
        const lqEnd = new Date(y, cqStart, 0);
        const lqStart = new Date(lqEnd.getFullYear(), lqEnd.getMonth() - 2, 1);
        return {
          start_date: lqStart.toISOString().split('T')[0],
          end_date: lqEnd.toISOString().split('T')[0],
        };
      }
      case 'this_year': return {
        start_date: `${y}-01-01`,
        end_date: now.toISOString().split('T')[0],
      };
      case 'last_year': return {
        start_date: `${y - 1}-01-01`,
        end_date: `${y - 1}-12-31`,
      };
      default: return { year: String(y), month: String(m) };
    }
  }, [period]);

  // P&L query
  const { data, isLoading } = useQuery({
    queryKey: [
      'channel-pl', period, channelFilter,
      regionFilter, clusterFilter, warehouseFilter,
      includeManpower, includeWarehouseCosts,
    ],
    queryFn: () => reportsApi.getChannelPL({
      ...dateParams,
      channel_id: channelFilter !== 'all' ? channelFilter : undefined,
      region_id: regionFilter !== 'all' ? regionFilter : undefined,
      cluster_id: clusterFilter !== 'all' ? clusterFilter : undefined,
      warehouse_id: warehouseFilter !== 'all' ? warehouseFilter : undefined,
      include_manpower: includeManpower,
      include_warehouse_costs: includeWarehouseCosts,
    }),
  });

  // Filtered cluster/warehouse options
  const selectedRegion = geoData?.regions.find(r => r.id === regionFilter);
  const clusters = selectedRegion?.clusters || [];
  const selectedCluster = clusters.find(c => c.id === clusterFilter);
  const warehouses = selectedCluster?.warehouses || selectedRegion?.warehouses || [];

  const toggleSection = (section: string) => {
    setExpandedSections(prev => ({ ...prev, [section]: !prev[section] }));
  };

  // Breadcrumb path
  const breadcrumbs: { label: string; onClick: () => void }[] = [
    { label: 'All Regions', onClick: () => { setRegionFilter('all'); } },
  ];
  if (selectedRegion) {
    breadcrumbs.push({
      label: selectedRegion.name,
      onClick: () => { setClusterFilter('all'); setWarehouseFilter('all'); },
    });
  }
  if (selectedCluster) {
    breadcrumbs.push({
      label: selectedCluster.name,
      onClick: () => { setWarehouseFilter('all'); },
    });
  }
  const selectedWarehouse = warehouses.find(w => w.id === warehouseFilter);
  if (selectedWarehouse) {
    breadcrumbs.push({ label: selectedWarehouse.name, onClick: () => {} });
  }

  const hasGeoFilter = regionFilter !== 'all' || clusterFilter !== 'all' || warehouseFilter !== 'all';

  return (
    <div className="space-y-6">
      <PageHeader
        title="Channel-wise P&L"
        description="Profit & Loss statement by sales channel with geographic drill-down"
        actions={
          <Button variant="outline">
            <Download className="mr-2 h-4 w-4" />
            Export
          </Button>
        }
      />

      {/* Filters Row 1: Period & Channel */}
      <div className="flex flex-wrap gap-4">
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
            <SelectItem value="all">All Channels</SelectItem>
            {data?.channels.map(ch => (
              <SelectItem key={ch.channel_id} value={ch.channel_id}>
                {ch.channel_name}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      {/* Filters Row 2: Geographic Drill-Down */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-base flex items-center gap-2">
            <MapPin className="h-4 w-4" />
            Geographic Drill-Down
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex flex-wrap gap-4">
            <Select value={regionFilter} onValueChange={setRegionFilter}>
              <SelectTrigger className="w-[200px]">
                <SelectValue placeholder="All Regions" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Regions</SelectItem>
                {geoData?.regions.map(r => (
                  <SelectItem key={r.id} value={r.id}>{r.name}</SelectItem>
                ))}
              </SelectContent>
            </Select>

            <Select
              value={clusterFilter}
              onValueChange={setClusterFilter}
              disabled={regionFilter === 'all'}
            >
              <SelectTrigger className="w-[200px]">
                <SelectValue placeholder="All Clusters" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Clusters</SelectItem>
                {clusters.map(c => (
                  <SelectItem key={c.id} value={c.id}>{c.name}</SelectItem>
                ))}
              </SelectContent>
            </Select>

            <Select
              value={warehouseFilter}
              onValueChange={setWarehouseFilter}
              disabled={regionFilter === 'all'}
            >
              <SelectTrigger className="w-[200px]">
                <SelectValue placeholder="All Warehouses" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Warehouses</SelectItem>
                {warehouses.map(w => (
                  <SelectItem key={w.id} value={w.id}>{w.name}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {/* Breadcrumb */}
          {hasGeoFilter && (
            <div className="flex items-center gap-1 mt-3 text-sm text-muted-foreground">
              {breadcrumbs.map((bc, i) => (
                <span key={i} className="flex items-center gap-1">
                  {i > 0 && <ChevronRight className="h-3 w-3" />}
                  <button
                    onClick={bc.onClick}
                    className={`hover:underline ${i === breadcrumbs.length - 1 ? 'font-medium text-foreground' : ''}`}
                  >
                    {bc.label}
                  </button>
                </span>
              ))}
            </div>
          )}

          {/* Cost Toggles */}
          {hasGeoFilter && (
            <div className="flex gap-4 mt-3">
              <label className="flex items-center gap-2 text-sm cursor-pointer">
                <input
                  type="checkbox"
                  checked={includeManpower}
                  onChange={e => setIncludeManpower(e.target.checked)}
                  className="rounded border-gray-300"
                />
                <Users className="h-4 w-4" /> Include Manpower Costs
              </label>
              <label className="flex items-center gap-2 text-sm cursor-pointer">
                <input
                  type="checkbox"
                  checked={includeWarehouseCosts}
                  onChange={e => setIncludeWarehouseCosts(e.target.checked)}
                  className="rounded border-gray-300"
                />
                <WarehouseIcon className="h-4 w-4" /> Include Warehouse Costs
              </label>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Summary Cards */}
      <div className="grid gap-4 md:grid-cols-5">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Net Revenue</CardTitle>
            <DollarSign className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-green-600">
              {formatCurrency(data?.totals.net_revenue || 0)}
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">COGS</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-red-600">
              ({formatCurrency(data?.totals.cost_of_goods_sold || 0)})
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Gross Profit</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{formatCurrency(data?.totals.gross_profit || 0)}</div>
            <p className="text-xs text-muted-foreground">
              {data?.totals.gross_margin_pct || 0}% margin
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total OpEx</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-red-600">
              ({formatCurrency(data?.totals.total_opex || 0)})
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">EBITDA</CardTitle>
            <TrendingUp className="h-4 w-4 text-green-600" />
          </CardHeader>
          <CardContent>
            <div className={`text-2xl font-bold ${(data?.totals.ebitda || 0) >= 0 ? 'text-green-600' : 'text-red-600'}`}>
              {formatCurrency(data?.totals.ebitda || 0)}
            </div>
            <p className="text-xs text-muted-foreground">
              {data?.totals.ebitda_margin_pct || 0}% margin
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Channel Comparison Cards */}
      {channelFilter === 'all' && data?.channels && data.channels.length > 1 && (
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
                        <span className="text-sm text-muted-foreground">Revenue</span>
                        <span className="font-mono">{formatCurrency(channel.revenue.net_revenue)}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-sm text-muted-foreground">Gross Margin</span>
                        <span className={`font-medium ${channel.cogs.gross_margin_pct >= 30 ? 'text-green-600' : 'text-orange-600'}`}>
                          {(channel.cogs.gross_margin_pct ?? 0).toFixed(1)}%
                        </span>
                      </div>
                      <div className="flex justify-between border-t pt-2">
                        <span className="text-sm text-muted-foreground">EBITDA</span>
                        <span className={`font-mono font-bold ${channel.ebitda >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                          {formatCurrency(channel.ebitda)}
                        </span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-sm text-muted-foreground">EBITDA Margin</span>
                        <span className={`font-medium ${channel.ebitda_margin_pct >= 10 ? 'text-green-600' : 'text-orange-600'}`}>
                          {(channel.ebitda_margin_pct ?? 0).toFixed(1)}%
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
          ) : data?.channels && data.channels.length > 0 ? (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="w-[45%]">Line Item</TableHead>
                  <TableHead className="text-right">Amount</TableHead>
                  <TableHead className="text-right">% of Revenue</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {/* We show totals if multiple channels, or single channel data */}
                {(() => {
                  const d = channelFilter !== 'all' && data.channels[0]
                    ? data.channels[0]
                    : null;
                  const rev = d ? d.revenue : {
                    gross_revenue: data.totals.net_revenue,
                    discounts: 0,
                    net_revenue: data.totals.net_revenue,
                    order_count: data.channels.reduce((s, c) => s + c.revenue.order_count, 0),
                  };
                  const cogs = d ? d.cogs : {
                    product_cost: data.totals.cost_of_goods_sold,
                    gross_profit: data.totals.gross_profit,
                    gross_margin_pct: data.totals.gross_margin_pct,
                  };
                  const opex = d ? d.opex : {
                    channel_commission: data.channels.reduce((s, c) => s + c.opex.channel_commission, 0),
                    shipping_cost: data.channels.reduce((s, c) => s + c.opex.shipping_cost, 0),
                    payment_processing: data.channels.reduce((s, c) => s + c.opex.payment_processing, 0),
                    warehouse_storage: data.channels.reduce((s, c) => s + c.opex.warehouse_storage, 0),
                    warehouse_handling: data.channels.reduce((s, c) => s + c.opex.warehouse_handling, 0),
                    warehouse_vas: data.channels.reduce((s, c) => s + c.opex.warehouse_vas, 0),
                    manpower_cost: data.channels.reduce((s, c) => s + c.opex.manpower_cost, 0),
                    total_opex: data.totals.total_opex,
                  };
                  const ebitda = d ? d.ebitda : data.totals.ebitda;
                  const ebitda_margin = d ? d.ebitda_margin_pct : data.totals.ebitda_margin_pct;
                  const netRev = rev.net_revenue || 1;
                  const pct = (val: number) => netRev > 0 ? ((val / netRev) * 100).toFixed(1) + '%' : '-';
                  const manpower = d?.manpower_detail;

                  return (
                    <>
                      {/* Revenue Section */}
                      <TableRow
                        className="cursor-pointer hover:bg-muted/50 font-semibold"
                        onClick={() => toggleSection('revenue')}
                      >
                        <TableCell className="flex items-center gap-2">
                          {expandedSections.revenue ? <MinusCircle className="h-4 w-4" /> : <PlusCircle className="h-4 w-4" />}
                          Revenue
                        </TableCell>
                        <TableCell className="text-right font-mono text-green-600">
                          {formatCurrency(rev.net_revenue)}
                        </TableCell>
                        <TableCell className="text-right">100%</TableCell>
                      </TableRow>
                      {expandedSections.revenue && (
                        <>
                          <TableRow>
                            <TableCell className="pl-8">Gross Revenue</TableCell>
                            <TableCell className="text-right font-mono">{formatCurrency(rev.gross_revenue)}</TableCell>
                            <TableCell className="text-right text-muted-foreground">{pct(rev.gross_revenue)}</TableCell>
                          </TableRow>
                          <TableRow>
                            <TableCell className="pl-8">Less: Discounts</TableCell>
                            <TableCell className="text-right font-mono text-red-600">({formatCurrency(rev.discounts)})</TableCell>
                            <TableCell className="text-right text-muted-foreground">{pct(rev.discounts)}</TableCell>
                          </TableRow>
                          <TableRow>
                            <TableCell className="pl-8 text-muted-foreground">Orders</TableCell>
                            <TableCell className="text-right font-mono">{rev.order_count}</TableCell>
                            <TableCell className="text-right">-</TableCell>
                          </TableRow>
                        </>
                      )}

                      {/* COGS Section */}
                      <TableRow
                        className="cursor-pointer hover:bg-muted/50 font-semibold"
                        onClick={() => toggleSection('cogs')}
                      >
                        <TableCell className="flex items-center gap-2">
                          {expandedSections.cogs ? <MinusCircle className="h-4 w-4" /> : <PlusCircle className="h-4 w-4" />}
                          Cost of Goods Sold
                        </TableCell>
                        <TableCell className="text-right font-mono text-red-600">
                          ({formatCurrency(cogs.product_cost)})
                        </TableCell>
                        <TableCell className="text-right text-muted-foreground">{pct(cogs.product_cost)}</TableCell>
                      </TableRow>
                      {expandedSections.cogs && (
                        <TableRow>
                          <TableCell className="pl-8">Product Cost</TableCell>
                          <TableCell className="text-right font-mono text-red-600">({formatCurrency(cogs.product_cost)})</TableCell>
                          <TableCell className="text-right text-muted-foreground">{pct(cogs.product_cost)}</TableCell>
                        </TableRow>
                      )}

                      {/* Gross Profit */}
                      <TableRow className="bg-muted font-bold">
                        <TableCell>Gross Profit</TableCell>
                        <TableCell className="text-right font-mono">{formatCurrency(cogs.gross_profit)}</TableCell>
                        <TableCell className="text-right">
                          <span className="text-green-600">{(cogs.gross_margin_pct ?? 0).toFixed(1)}%</span>
                        </TableCell>
                      </TableRow>

                      {/* OpEx Section */}
                      <TableRow
                        className="cursor-pointer hover:bg-muted/50 font-semibold"
                        onClick={() => toggleSection('opex')}
                      >
                        <TableCell className="flex items-center gap-2">
                          {expandedSections.opex ? <MinusCircle className="h-4 w-4" /> : <PlusCircle className="h-4 w-4" />}
                          Operating Expenses
                        </TableCell>
                        <TableCell className="text-right font-mono text-red-600">
                          ({formatCurrency(opex.total_opex)})
                        </TableCell>
                        <TableCell className="text-right text-muted-foreground">{pct(opex.total_opex)}</TableCell>
                      </TableRow>
                      {expandedSections.opex && (
                        <>
                          <TableRow>
                            <TableCell className="pl-8">Channel Commission</TableCell>
                            <TableCell className="text-right font-mono text-red-600">({formatCurrency(opex.channel_commission)})</TableCell>
                            <TableCell className="text-right text-muted-foreground">{pct(opex.channel_commission)}</TableCell>
                          </TableRow>
                          <TableRow>
                            <TableCell className="pl-8">Shipping Cost</TableCell>
                            <TableCell className="text-right font-mono text-red-600">({formatCurrency(opex.shipping_cost)})</TableCell>
                            <TableCell className="text-right text-muted-foreground">{pct(opex.shipping_cost)}</TableCell>
                          </TableRow>
                          <TableRow>
                            <TableCell className="pl-8">Payment Processing</TableCell>
                            <TableCell className="text-right font-mono text-red-600">({formatCurrency(opex.payment_processing)})</TableCell>
                            <TableCell className="text-right text-muted-foreground">{pct(opex.payment_processing)}</TableCell>
                          </TableRow>

                          {/* Warehouse Operations Sub-section */}
                          {(opex.warehouse_storage > 0 || opex.warehouse_handling > 0 || opex.warehouse_vas > 0 || includeWarehouseCosts) && (
                            <>
                              <TableRow
                                className="cursor-pointer hover:bg-muted/30"
                                onClick={() => toggleSection('warehouse_ops')}
                              >
                                <TableCell className="pl-8 flex items-center gap-2 font-medium">
                                  {expandedSections.warehouse_ops ? <MinusCircle className="h-3 w-3" /> : <PlusCircle className="h-3 w-3" />}
                                  <WarehouseIcon className="h-3 w-3" /> Warehouse Operations
                                </TableCell>
                                <TableCell className="text-right font-mono text-red-600">
                                  ({formatCurrency(opex.warehouse_storage + opex.warehouse_handling + opex.warehouse_vas)})
                                </TableCell>
                                <TableCell className="text-right text-muted-foreground">
                                  {pct(opex.warehouse_storage + opex.warehouse_handling + opex.warehouse_vas)}
                                </TableCell>
                              </TableRow>
                              {expandedSections.warehouse_ops && (
                                <>
                                  <TableRow>
                                    <TableCell className="pl-12">Storage</TableCell>
                                    <TableCell className="text-right font-mono text-red-600">({formatCurrency(opex.warehouse_storage)})</TableCell>
                                    <TableCell className="text-right text-muted-foreground">{pct(opex.warehouse_storage)}</TableCell>
                                  </TableRow>
                                  <TableRow>
                                    <TableCell className="pl-12">Handling</TableCell>
                                    <TableCell className="text-right font-mono text-red-600">({formatCurrency(opex.warehouse_handling)})</TableCell>
                                    <TableCell className="text-right text-muted-foreground">{pct(opex.warehouse_handling)}</TableCell>
                                  </TableRow>
                                  <TableRow>
                                    <TableCell className="pl-12">Value Added Services</TableCell>
                                    <TableCell className="text-right font-mono text-red-600">({formatCurrency(opex.warehouse_vas)})</TableCell>
                                    <TableCell className="text-right text-muted-foreground">{pct(opex.warehouse_vas)}</TableCell>
                                  </TableRow>
                                </>
                              )}
                            </>
                          )}

                          {/* Manpower Cost Sub-section */}
                          {(opex.manpower_cost > 0 || includeManpower) && (
                            <>
                              <TableRow
                                className="cursor-pointer hover:bg-muted/30"
                                onClick={() => toggleSection('manpower')}
                              >
                                <TableCell className="pl-8 flex items-center gap-2 font-medium">
                                  {expandedSections.manpower ? <MinusCircle className="h-3 w-3" /> : <PlusCircle className="h-3 w-3" />}
                                  <Users className="h-3 w-3" /> Manpower Cost
                                  {manpower && manpower.headcount > 0 && (
                                    <Badge variant="secondary" className="ml-2 text-xs">
                                      {manpower.headcount} employees
                                    </Badge>
                                  )}
                                </TableCell>
                                <TableCell className="text-right font-mono text-red-600">
                                  ({formatCurrency(opex.manpower_cost)})
                                </TableCell>
                                <TableCell className="text-right text-muted-foreground">{pct(opex.manpower_cost)}</TableCell>
                              </TableRow>
                              {expandedSections.manpower && manpower && manpower.by_department.length > 0 && (
                                <>
                                  {manpower.by_department.map((dept, i) => (
                                    <TableRow key={i}>
                                      <TableCell className="pl-12">
                                        {dept.department}
                                        <span className="text-muted-foreground ml-2 text-xs">({dept.headcount} people)</span>
                                      </TableCell>
                                      <TableCell className="text-right font-mono text-red-600">({formatCurrency(dept.cost)})</TableCell>
                                      <TableCell className="text-right text-muted-foreground">{pct(dept.cost)}</TableCell>
                                    </TableRow>
                                  ))}
                                  <TableRow>
                                    <TableCell className="pl-12 text-muted-foreground">Avg Monthly CTC</TableCell>
                                    <TableCell className="text-right font-mono text-muted-foreground">{formatCurrency(manpower.avg_monthly_ctc)}</TableCell>
                                    <TableCell className="text-right">-</TableCell>
                                  </TableRow>
                                </>
                              )}
                              {expandedSections.manpower && (!manpower || manpower.by_department.length === 0) && (
                                <TableRow>
                                  <TableCell className="pl-12 text-muted-foreground" colSpan={3}>
                                    No payroll data available for this warehouse/period
                                  </TableCell>
                                </TableRow>
                              )}
                            </>
                          )}
                        </>
                      )}

                      {/* EBITDA */}
                      <TableRow className="bg-primary/10 font-bold text-lg">
                        <TableCell>EBITDA</TableCell>
                        <TableCell className={`text-right font-mono ${ebitda >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                          {formatCurrency(ebitda)}
                        </TableCell>
                        <TableCell className="text-right">
                          <span className={(ebitda_margin ?? 0) >= 0 ? 'text-green-600' : 'text-red-600'}>
                            {(ebitda_margin ?? 0).toFixed(1)}%
                          </span>
                        </TableCell>
                      </TableRow>
                    </>
                  );
                })()}
              </TableBody>
            </Table>
          ) : (
            <div className="text-center py-12 text-muted-foreground">
              <BarChart3 className="h-12 w-12 mx-auto mb-4 opacity-50" />
              <p>No data available for the selected filters</p>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
