'use client';

import { useState, useEffect, useMemo } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Boxes,
  RefreshCw,
  AlertTriangle,
  CheckCircle,
  TrendingDown,
  Calculator,
  Package,
  ArrowRight,
  ChevronRight,
  MapPin,
  Activity,
  BarChart3,
  LineChart as LineChartIcon,
  Target,
} from 'lucide-react';
import {
  BarChart,
  Bar,
  LineChart,
  Line,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from 'recharts';

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
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
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { snopApi } from '@/lib/api';
import apiClient from '@/lib/api/client';
import { toast } from 'sonner';

// ==================== Types ====================

interface GeoWarehouse { id: string; name: string; code: string; }
interface GeoCluster { id: string; name: string; code: string; type: string; warehouses: GeoWarehouse[]; }
interface GeoRegion { id: string; name: string; code: string; type: string; clusters: GeoCluster[]; warehouses: GeoWarehouse[]; }
interface GeoHierarchy { regions: GeoRegion[]; }

interface KPIs {
  total_skus: number;
  stockout_count: number;
  overstock_count: number;
  healthy_count: number;
  avg_days_of_supply: number;
  avg_fill_rate: number;
  forecast_accuracy_mape: number | null;
  forecast_accuracy_wmape: number | null;
  forecast_bias: number | null;
  demand_supply_gap_pct: number;
  total_exceptions: number;
  health_status: 'GREEN' | 'AMBER' | 'RED';
}

interface GeoChild {
  id: string;
  name: string;
  code: string | null;
  type: string;
  kpis: KPIs;
}

interface NetworkHealthResponse {
  level: string;
  level_name: string;
  kpis: KPIs;
  children: GeoChild[];
  breadcrumb: { level: string; name: string; id: string | null; code?: string }[];
}

// ==================== Helpers ====================

function formatNumber(value: number | string | null | undefined): string {
  const num = Number(value) || 0;
  if (num >= 100000) return `${(num / 100000).toFixed(1)}L`;
  if (num >= 1000) return `${(num / 1000).toFixed(1)}K`;
  return num.toFixed(0);
}

const healthColor = (status: string) => {
  if (status === 'RED') return 'text-red-600 bg-red-50 border-red-200';
  if (status === 'AMBER') return 'text-amber-600 bg-amber-50 border-amber-200';
  return 'text-green-600 bg-green-50 border-green-200';
};

const healthDot = (status: string) => {
  if (status === 'RED') return 'bg-red-500';
  if (status === 'AMBER') return 'bg-amber-500';
  return 'bg-green-500';
};

const statusBadge = (s: string) => {
  if (s === 'CRITICAL') return <Badge variant="destructive">Critical</Badge>;
  if (s === 'REORDER') return <Badge className="bg-amber-100 text-amber-800 border-amber-200">Reorder</Badge>;
  if (s === 'OVERSTOCK') return <Badge className="bg-purple-100 text-purple-800 border-purple-200">Overstock</Badge>;
  return <Badge variant="outline">Optimal</Badge>;
};

const getGeoHierarchy = async (): Promise<GeoHierarchy> => {
  try {
    const { data } = await apiClient.get('/channel-reports/geo-hierarchy');
    return data;
  } catch {
    return { regions: [] };
  }
};

// ==================== Component ====================

export default function InventoryOptimizationPage() {
  const queryClient = useQueryClient();
  const [activeTab, setActiveTab] = useState('overview');

  // Geographic drill-down state
  const [regionFilter, setRegionFilter] = useState<string>('all');
  const [clusterFilter, setClusterFilter] = useState<string>('all');
  const [warehouseFilter, setWarehouseFilter] = useState<string>('all');

  // Cascading resets
  useEffect(() => { setClusterFilter('all'); setWarehouseFilter('all'); }, [regionFilter]);
  useEffect(() => { setWarehouseFilter('all'); }, [clusterFilter]);

  // Date range for forecast accuracy (last 6 months)
  const dateRange = useMemo(() => {
    const end = new Date();
    const start = new Date();
    start.setMonth(start.getMonth() - 6);
    return {
      start_date: start.toISOString().split('T')[0],
      end_date: end.toISOString().split('T')[0],
    };
  }, []);

  // Geo hierarchy
  const { data: geoData } = useQuery({
    queryKey: ['geo-hierarchy'],
    queryFn: getGeoHierarchy,
    staleTime: 5 * 60 * 1000,
  });

  // Compute filter params
  const geoParams = useMemo(() => {
    const p: Record<string, string> = {};
    if (regionFilter !== 'all') p.region_id = regionFilter;
    if (clusterFilter !== 'all') p.cluster_id = clusterFilter;
    if (warehouseFilter !== 'all') p.warehouse_id = warehouseFilter;
    return p;
  }, [regionFilter, clusterFilter, warehouseFilter]);

  // Network health query
  const { data: networkHealth, isLoading: isLoadingHealth, refetch, isFetching } = useQuery({
    queryKey: ['inventory-network-health', geoParams],
    queryFn: () => snopApi.getNetworkHealth(geoParams),
  });

  // Warehouse detail (only when a warehouse is selected)
  const { data: warehouseDetail, isLoading: isLoadingDetail } = useQuery({
    queryKey: ['warehouse-detail', warehouseFilter],
    queryFn: () => snopApi.getWarehouseDetail(warehouseFilter),
    enabled: warehouseFilter !== 'all',
  });

  // Forecast accuracy geo
  const { data: forecastAccuracy, isLoading: isLoadingAccuracy } = useQuery({
    queryKey: ['forecast-accuracy-geo', dateRange, geoParams],
    queryFn: () => snopApi.getForecastAccuracyGeo({ ...dateRange, ...geoParams }),
    enabled: activeTab === 'forecast-accuracy',
  });

  // Availability vs forecast (warehouse level only)
  const { data: availForecast, isLoading: isLoadingAvail } = useQuery({
    queryKey: ['availability-vs-forecast', warehouseFilter],
    queryFn: () => snopApi.getAvailabilityVsForecast({ warehouse_id: warehouseFilter }),
    enabled: activeTab === 'avail-vs-forecast' && warehouseFilter !== 'all',
  });

  // Run optimization mutation
  const runOptimization = useMutation({
    mutationFn: () => snopApi.runOptimization(),
    onSuccess: () => {
      toast.success('Optimization completed');
      queryClient.invalidateQueries({ queryKey: ['inventory-network-health'] });
      queryClient.invalidateQueries({ queryKey: ['warehouse-detail'] });
    },
    onError: () => toast.error('Optimization failed'),
  });

  // Filtered geo options
  const selectedRegion = geoData?.regions.find((r: GeoRegion) => r.id === regionFilter);
  const clusters = selectedRegion?.clusters || [];
  const selectedCluster = clusters.find((c: GeoCluster) => c.id === clusterFilter);
  const warehouses = selectedCluster?.warehouses || selectedRegion?.warehouses || [];

  const kpis: KPIs = networkHealth?.kpis || {
    total_skus: 0, stockout_count: 0, overstock_count: 0, healthy_count: 0,
    avg_days_of_supply: 0, avg_fill_rate: 0, forecast_accuracy_mape: null,
    forecast_accuracy_wmape: null, forecast_bias: null, demand_supply_gap_pct: 0,
    total_exceptions: 0, health_status: 'GREEN',
  };

  const children: GeoChild[] = networkHealth?.children || [];
  const breadcrumb = networkHealth?.breadcrumb || [];

  // Child card click handler
  const handleChildClick = (child: GeoChild) => {
    if (child.type === 'REGION') setRegionFilter(child.id);
    else if (child.type === 'CLUSTER') setClusterFilter(child.id);
    else if (child.type === 'WAREHOUSE') setWarehouseFilter(child.id);
  };

  // Breadcrumb click handler
  const handleBreadcrumbClick = (bc: { level: string; id: string | null }) => {
    if (bc.level === 'ENTERPRISE') {
      setRegionFilter('all');
    } else if (bc.level === 'REGION') {
      setRegionFilter(bc.id || 'all');
      setClusterFilter('all');
      setWarehouseFilter('all');
    } else if (bc.level === 'CLUSTER') {
      setClusterFilter(bc.id || 'all');
      setWarehouseFilter('all');
    }
  };

  if (isLoadingHealth && !networkHealth) {
    return (
      <div className="space-y-6 p-6">
        <Skeleton className="h-8 w-64" />
        <div className="grid gap-4 md:grid-cols-3">
          {[...Array(3)].map((_, i) => <Skeleton key={i} className="h-12" />)}
        </div>
        <div className="grid gap-4 md:grid-cols-6">
          {[...Array(6)].map((_, i) => <Skeleton key={i} className="h-24" />)}
        </div>
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
            <Boxes className="h-6 w-6 text-amber-600" />
          </div>
          <div>
            <h1 className="text-2xl font-bold tracking-tight">Inventory Network Health</h1>
            <p className="text-muted-foreground">
              Stepping-ladder drill-down: Enterprise &rarr; Region &rarr; Cluster &rarr; Warehouse &rarr; SKU
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Button onClick={() => refetch()} disabled={isFetching} variant="outline" size="sm">
            <RefreshCw className={`h-4 w-4 mr-2 ${isFetching ? 'animate-spin' : ''}`} />
            Refresh
          </Button>
          <Button onClick={() => runOptimization.mutate()} disabled={runOptimization.isPending}>
            <Calculator className="h-4 w-4 mr-2" />
            {runOptimization.isPending ? 'Optimizing...' : 'Run Optimization'}
          </Button>
        </div>
      </div>

      {/* Geo Filters */}
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
                {geoData?.regions.map((r: GeoRegion) => (
                  <SelectItem key={r.id} value={r.id}>{r.name}</SelectItem>
                ))}
              </SelectContent>
            </Select>

            <Select value={clusterFilter} onValueChange={setClusterFilter} disabled={regionFilter === 'all'}>
              <SelectTrigger className="w-[200px]">
                <SelectValue placeholder="All Clusters" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Clusters</SelectItem>
                {clusters.map((c: GeoCluster) => (
                  <SelectItem key={c.id} value={c.id}>{c.name}</SelectItem>
                ))}
              </SelectContent>
            </Select>

            <Select value={warehouseFilter} onValueChange={setWarehouseFilter} disabled={regionFilter === 'all'}>
              <SelectTrigger className="w-[200px]">
                <SelectValue placeholder="All Warehouses" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Warehouses</SelectItem>
                {warehouses.map((w: GeoWarehouse) => (
                  <SelectItem key={w.id} value={w.id}>{w.name}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {/* Breadcrumb */}
          {breadcrumb.length > 1 && (
            <div className="flex items-center gap-1 mt-3 text-sm text-muted-foreground">
              {breadcrumb.map((bc: { level: string; name: string; id: string | null }, i: number) => (
                <span key={i} className="flex items-center gap-1">
                  {i > 0 && <ChevronRight className="h-3 w-3" />}
                  <button
                    onClick={() => handleBreadcrumbClick(bc)}
                    className={`hover:underline ${i === breadcrumb.length - 1 ? 'font-medium text-foreground' : ''}`}
                  >
                    {bc.name}
                  </button>
                </span>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {/* KPI Summary Cards */}
      <div className="grid gap-4 md:grid-cols-6">
        <Card className={`border ${healthColor(kpis.health_status)}`}>
          <CardContent className="p-4">
            <div className="flex items-center gap-2">
              <AlertTriangle className="h-4 w-4 text-red-600" />
              <span className="text-sm text-muted-foreground">Stockouts</span>
            </div>
            <p className="text-2xl font-bold mt-1 text-red-600">{kpis.stockout_count}</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center gap-2">
              <Package className="h-4 w-4 text-purple-600" />
              <span className="text-sm text-muted-foreground">Overstock</span>
            </div>
            <p className="text-2xl font-bold mt-1 text-purple-600">{kpis.overstock_count}</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center gap-2">
              <CheckCircle className="h-4 w-4 text-green-600" />
              <span className="text-sm text-muted-foreground">Healthy</span>
            </div>
            <p className="text-2xl font-bold mt-1 text-green-600">{kpis.healthy_count}</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center gap-2">
              <Target className="h-4 w-4 text-blue-600" />
              <span className="text-sm text-muted-foreground">MAPE</span>
            </div>
            <p className="text-2xl font-bold mt-1">
              {kpis.forecast_accuracy_mape != null ? `${kpis.forecast_accuracy_mape}%` : 'N/A'}
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center gap-2">
              <Activity className="h-4 w-4 text-emerald-600" />
              <span className="text-sm text-muted-foreground">Fill Rate</span>
            </div>
            <p className="text-2xl font-bold mt-1">{kpis.avg_fill_rate}%</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center gap-2">
              <TrendingDown className="h-4 w-4 text-amber-600" />
              <span className="text-sm text-muted-foreground">Days of Supply</span>
            </div>
            <p className="text-2xl font-bold mt-1">{kpis.avg_days_of_supply}d</p>
          </CardContent>
        </Card>
      </div>

      {/* Tabs */}
      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList>
          <TabsTrigger value="overview" className="flex items-center gap-1.5">
            <Boxes className="h-4 w-4" /> Overview
          </TabsTrigger>
          <TabsTrigger value="forecast-accuracy" className="flex items-center gap-1.5">
            <BarChart3 className="h-4 w-4" /> Forecast Accuracy
          </TabsTrigger>
          <TabsTrigger
            value="avail-vs-forecast"
            className="flex items-center gap-1.5"
            disabled={warehouseFilter === 'all'}
          >
            <LineChartIcon className="h-4 w-4" /> Avail vs Forecast
          </TabsTrigger>
        </TabsList>

        {/* ==================== Overview Tab ==================== */}
        <TabsContent value="overview" className="space-y-4">
          {/* Children cards (clickable drill-down) */}
          {children.length > 0 && (
            <div className="grid gap-4 md:grid-cols-3 lg:grid-cols-4">
              {children.map((child) => (
                <Card
                  key={child.id}
                  className="cursor-pointer hover:shadow-md transition-shadow border"
                  onClick={() => handleChildClick(child)}
                >
                  <CardContent className="p-4">
                    <div className="flex items-center justify-between mb-3">
                      <h3 className="font-semibold truncate">{child.name}</h3>
                      <div className={`w-3 h-3 rounded-full ${healthDot(child.kpis.health_status)}`} />
                    </div>
                    <div className="space-y-1.5 text-sm">
                      <div className="flex justify-between">
                        <span className="text-muted-foreground">Stockouts</span>
                        <span className={child.kpis.stockout_count > 0 ? 'text-red-600 font-semibold' : ''}>
                          {child.kpis.stockout_count}
                        </span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-muted-foreground">Overstock</span>
                        <span className={child.kpis.overstock_count > 0 ? 'text-purple-600 font-semibold' : ''}>
                          {child.kpis.overstock_count}
                        </span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-muted-foreground">MAPE</span>
                        <span>{child.kpis.forecast_accuracy_mape != null ? `${child.kpis.forecast_accuracy_mape}%` : 'N/A'}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-muted-foreground">DoS</span>
                        <span>{child.kpis.avg_days_of_supply}d</span>
                      </div>
                    </div>
                    <div className="mt-3 flex items-center text-xs text-blue-600">
                      Drill down <ArrowRight className="h-3 w-3 ml-1" />
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          )}

          {/* Warehouse-level: SKU detail table */}
          {warehouseFilter !== 'all' && (
            <Card>
              <CardHeader>
                <CardTitle className="text-base">
                  SKU Details — {warehouseDetail?.warehouse?.name || 'Warehouse'}
                </CardTitle>
                <CardDescription>
                  Per-product inventory health with recommended actions
                </CardDescription>
              </CardHeader>
              <CardContent>
                {isLoadingDetail ? (
                  <div className="space-y-2">
                    {[...Array(5)].map((_, i) => <Skeleton key={i} className="h-10" />)}
                  </div>
                ) : (
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>Product</TableHead>
                        <TableHead className="text-right">Stock</TableHead>
                        <TableHead className="text-right">Safety</TableHead>
                        <TableHead className="text-right">ROP</TableHead>
                        <TableHead className="text-right">DoS</TableHead>
                        <TableHead className="text-right">Accuracy</TableHead>
                        <TableHead>Status</TableHead>
                        <TableHead>Action</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {warehouseDetail?.sku_details?.length > 0 ? (
                        warehouseDetail.sku_details.map((sku: any) => (
                          <TableRow key={sku.product_id}>
                            <TableCell>
                              <div>
                                <p className="font-medium">{sku.product_name}</p>
                                {sku.sku && <p className="text-xs text-muted-foreground">{sku.sku}</p>}
                              </div>
                            </TableCell>
                            <TableCell className="text-right font-mono">
                              {sku.current_stock?.toLocaleString()}
                            </TableCell>
                            <TableCell className="text-right font-mono">
                              {sku.safety_stock?.toLocaleString()}
                            </TableCell>
                            <TableCell className="text-right font-mono">
                              {sku.reorder_point?.toLocaleString()}
                            </TableCell>
                            <TableCell className="text-right font-mono">
                              {sku.days_of_supply}d
                            </TableCell>
                            <TableCell className="text-right">
                              {sku.forecast_accuracy_mape != null
                                ? <span className={sku.forecast_accuracy_mape > 30 ? 'text-red-600' : sku.forecast_accuracy_mape > 20 ? 'text-amber-600' : 'text-green-600'}>
                                    {(100 - sku.forecast_accuracy_mape).toFixed(0)}%
                                  </span>
                                : 'N/A'
                              }
                            </TableCell>
                            <TableCell>{statusBadge(sku.status)}</TableCell>
                            <TableCell>
                              {sku.recommended_action && (
                                <span className="text-xs text-muted-foreground">{sku.recommended_action}</span>
                              )}
                            </TableCell>
                          </TableRow>
                        ))
                      ) : (
                        <TableRow>
                          <TableCell colSpan={8} className="text-center py-8 text-muted-foreground">
                            <Package className="h-12 w-12 mx-auto mb-4 opacity-50" />
                            <p>No optimization data for this warehouse</p>
                            <p className="text-sm">Run optimization to generate recommendations</p>
                          </TableCell>
                        </TableRow>
                      )}
                    </TableBody>
                  </Table>
                )}
              </CardContent>
            </Card>
          )}

          {/* Empty state for no children and no warehouse selected */}
          {children.length === 0 && warehouseFilter === 'all' && kpis.total_skus === 0 && (
            <Card>
              <CardContent className="p-8 text-center text-muted-foreground">
                <Package className="h-12 w-12 mx-auto mb-4 opacity-50" />
                <p>No inventory optimization data available</p>
                <p className="text-sm mt-1">Run optimization to calculate inventory parameters</p>
              </CardContent>
            </Card>
          )}
        </TabsContent>

        {/* ==================== Forecast Accuracy Tab ==================== */}
        <TabsContent value="forecast-accuracy" className="space-y-4">
          {isLoadingAccuracy ? (
            <div className="grid gap-4 md:grid-cols-2">
              {[...Array(4)].map((_, i) => <Skeleton key={i} className="h-48" />)}
            </div>
          ) : forecastAccuracy ? (
            <>
              {/* Overall metrics */}
              <div className="grid gap-4 md:grid-cols-4">
                <Card>
                  <CardContent className="p-4">
                    <p className="text-sm text-muted-foreground">MAPE</p>
                    <p className="text-2xl font-bold">
                      {forecastAccuracy.overall?.mape != null ? `${forecastAccuracy.overall.mape}%` : 'N/A'}
                    </p>
                  </CardContent>
                </Card>
                <Card>
                  <CardContent className="p-4">
                    <p className="text-sm text-muted-foreground">WMAPE</p>
                    <p className="text-2xl font-bold">
                      {forecastAccuracy.overall?.wmape != null ? `${forecastAccuracy.overall.wmape}%` : 'N/A'}
                    </p>
                  </CardContent>
                </Card>
                <Card>
                  <CardContent className="p-4">
                    <p className="text-sm text-muted-foreground">Bias</p>
                    <p className="text-2xl font-bold">
                      {forecastAccuracy.overall?.bias != null ? forecastAccuracy.overall.bias.toFixed(2) : 'N/A'}
                    </p>
                  </CardContent>
                </Card>
                <Card>
                  <CardContent className="p-4">
                    <p className="text-sm text-muted-foreground">Forecasts</p>
                    <p className="text-2xl font-bold">{forecastAccuracy.overall?.forecast_count || 0}</p>
                  </CardContent>
                </Card>
              </div>

              {/* Children accuracy comparison chart */}
              {forecastAccuracy.children_accuracy?.length > 0 && (
                <Card>
                  <CardHeader>
                    <CardTitle className="text-base">Accuracy by {networkHealth?.level === 'ENTERPRISE' ? 'Region' : networkHealth?.level === 'REGION' ? 'Cluster' : 'Warehouse'}</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="h-64">
                      <ResponsiveContainer width="100%" height="100%">
                        <BarChart data={forecastAccuracy.children_accuracy}>
                          <CartesianGrid strokeDasharray="3 3" />
                          <XAxis dataKey="name" />
                          <YAxis unit="%" />
                          <Tooltip formatter={(value) => [`${value}%`, 'MAPE']} />
                          <Bar dataKey="mape" fill="#3B82F6" radius={[4, 4, 0, 0]} name="MAPE %" />
                        </BarChart>
                      </ResponsiveContainer>
                    </div>
                  </CardContent>
                </Card>
              )}

              {/* Monthly trend chart */}
              {forecastAccuracy.trend?.length > 0 && (
                <Card>
                  <CardHeader>
                    <CardTitle className="text-base">Monthly Accuracy Trend</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="h-64">
                      <ResponsiveContainer width="100%" height="100%">
                        <AreaChart data={forecastAccuracy.trend.map((t: any) => ({
                          ...t,
                          month: t.month ? new Date(t.month).toLocaleDateString('en-US', { month: 'short', year: '2-digit' }) : '',
                          accuracy: t.mape != null ? Math.max(0, 100 - t.mape) : null,
                        }))}>
                          <CartesianGrid strokeDasharray="3 3" />
                          <XAxis dataKey="month" />
                          <YAxis unit="%" domain={[0, 100]} />
                          <Tooltip formatter={(value) => [`${Number(value || 0).toFixed(1)}%`, 'Accuracy']} />
                          <Area type="monotone" dataKey="accuracy" stroke="#10B981" fill="#10B98133" name="Accuracy %" />
                        </AreaChart>
                      </ResponsiveContainer>
                    </div>
                  </CardContent>
                </Card>
              )}

              {/* Worst SKUs table */}
              {forecastAccuracy.by_sku?.length > 0 && (
                <Card>
                  <CardHeader>
                    <CardTitle className="text-base">Top 20 Worst Forecast Accuracy SKUs</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <Table>
                      <TableHeader>
                        <TableRow>
                          <TableHead>Product</TableHead>
                          <TableHead>SKU</TableHead>
                          <TableHead className="text-right">MAPE %</TableHead>
                          <TableHead className="text-right">Bias</TableHead>
                          <TableHead className="text-right">Forecasts</TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {forecastAccuracy.by_sku.map((s: any) => (
                          <TableRow key={s.product_id}>
                            <TableCell className="font-medium">{s.product_name}</TableCell>
                            <TableCell className="text-muted-foreground">{s.sku || '-'}</TableCell>
                            <TableCell className="text-right">
                              <span className={s.mape > 30 ? 'text-red-600 font-semibold' : s.mape > 20 ? 'text-amber-600' : 'text-green-600'}>
                                {s.mape?.toFixed(1)}%
                              </span>
                            </TableCell>
                            <TableCell className="text-right">{s.bias?.toFixed(2) || 'N/A'}</TableCell>
                            <TableCell className="text-right">{s.count}</TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  </CardContent>
                </Card>
              )}

              {/* Algorithm breakdown */}
              {forecastAccuracy.by_algorithm && Object.keys(forecastAccuracy.by_algorithm).length > 0 && (
                <Card>
                  <CardHeader>
                    <CardTitle className="text-base">Accuracy by Algorithm</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="grid gap-3 md:grid-cols-3 lg:grid-cols-4">
                      {Object.entries(forecastAccuracy.by_algorithm).map(([algo, data]: [string, any]) => (
                        <div key={algo} className="p-3 rounded-lg bg-muted/50">
                          <p className="text-sm font-medium">{algo}</p>
                          <p className="text-lg font-bold">{data.mape != null ? `${data.mape}%` : 'N/A'}</p>
                          <p className="text-xs text-muted-foreground">{data.count} forecasts</p>
                        </div>
                      ))}
                    </div>
                  </CardContent>
                </Card>
              )}
            </>
          ) : (
            <Card>
              <CardContent className="p-8 text-center text-muted-foreground">
                No forecast accuracy data available for the selected period.
              </CardContent>
            </Card>
          )}
        </TabsContent>

        {/* ==================== Availability vs Forecast Tab ==================== */}
        <TabsContent value="avail-vs-forecast" className="space-y-4">
          {warehouseFilter === 'all' ? (
            <Card>
              <CardContent className="p-8 text-center text-muted-foreground">
                <MapPin className="h-12 w-12 mx-auto mb-4 opacity-50" />
                <p>Select a specific warehouse to view availability vs forecast comparison</p>
              </CardContent>
            </Card>
          ) : isLoadingAvail ? (
            <div className="space-y-4">
              <Skeleton className="h-24" />
              <Skeleton className="h-80" />
            </div>
          ) : availForecast ? (
            <>
              {/* Summary */}
              <div className="grid gap-4 md:grid-cols-4">
                <Card>
                  <CardContent className="p-4">
                    <p className="text-sm text-muted-foreground">Starting Stock</p>
                    <p className="text-2xl font-bold">{formatNumber(availForecast.summary?.total_available_start)}</p>
                  </CardContent>
                </Card>
                <Card>
                  <CardContent className="p-4">
                    <p className="text-sm text-muted-foreground">Total Forecast</p>
                    <p className="text-2xl font-bold">{formatNumber(availForecast.summary?.total_forecast)}</p>
                  </CardContent>
                </Card>
                <Card>
                  <CardContent className="p-4">
                    <p className="text-sm text-muted-foreground">Net Gap</p>
                    <p className={`text-2xl font-bold ${(availForecast.summary?.net_gap || 0) < 0 ? 'text-red-600' : 'text-green-600'}`}>
                      {formatNumber(availForecast.summary?.net_gap)}
                    </p>
                  </CardContent>
                </Card>
                <Card>
                  <CardContent className="p-4">
                    <p className="text-sm text-muted-foreground">Stockout Days</p>
                    <p className={`text-2xl font-bold ${(availForecast.summary?.stockout_days || 0) > 0 ? 'text-red-600' : 'text-green-600'}`}>
                      {availForecast.summary?.stockout_days || 0}
                    </p>
                  </CardContent>
                </Card>
              </div>

              {/* Time-series chart */}
              {availForecast.comparison?.length > 0 && (
                <Card>
                  <CardHeader>
                    <CardTitle className="text-base">
                      Available vs Forecasted — {availForecast.warehouse_name}
                    </CardTitle>
                    <CardDescription>
                      {availForecast.summary?.horizon_days}-day horizon
                    </CardDescription>
                  </CardHeader>
                  <CardContent>
                    <div className="h-80">
                      <ResponsiveContainer width="100%" height="100%">
                        <LineChart data={availForecast.comparison.map((c: any) => ({
                          ...c,
                          date: new Date(c.date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' }),
                        }))}>
                          <CartesianGrid strokeDasharray="3 3" />
                          <XAxis dataKey="date" interval="preserveStartEnd" />
                          <YAxis />
                          <Tooltip />
                          <Legend />
                          <Line type="monotone" dataKey="available_qty" stroke="#10B981" strokeWidth={2} dot={false} name="Available" />
                          <Line type="monotone" dataKey="forecasted_qty" stroke="#3B82F6" strokeWidth={2} strokeDasharray="5 5" dot={false} name="Forecasted" />
                        </LineChart>
                      </ResponsiveContainer>
                    </div>
                  </CardContent>
                </Card>
              )}
            </>
          ) : (
            <Card>
              <CardContent className="p-8 text-center text-muted-foreground">
                No forecast data available for this warehouse.
              </CardContent>
            </Card>
          )}
        </TabsContent>
      </Tabs>
    </div>
  );
}
