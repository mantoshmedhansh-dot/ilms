'use client';

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  LineChart,
  Plus,
  RefreshCw,
  Filter,
  Eye,
  CheckCircle,
  Clock,
  AlertCircle,
  Brain,
  BarChart3,
  Trophy,
  Zap,
  Radio,
  ArrowUp,
  ArrowDown,
  Signal,
  ShieldAlert,
  Sparkles,
  XCircle,
  Scan,
} from 'lucide-react';
import {
  LineChart as RechartsLineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
  BarChart,
  Bar,
  Cell,
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  Radar,
} from 'recharts';

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { snopApi } from '@/lib/api';
import { toast } from 'sonner';
import { apiClient } from '@/lib/api/client';

const statusColors: Record<string, string> = {
  DRAFT: 'bg-gray-100 text-gray-800',
  PENDING_REVIEW: 'bg-yellow-100 text-yellow-800',
  UNDER_REVIEW: 'bg-blue-100 text-blue-800',
  APPROVED: 'bg-green-100 text-green-800',
  REJECTED: 'bg-red-100 text-red-800',
};

const algorithmColors: Record<string, string> = {
  prophet: '#8B5CF6',
  xgboost: '#F59E0B',
  arima: '#3B82F6',
  holt_winters: '#10B981',
  ensemble: '#EC4899',
};

const algorithmLabels: Record<string, string> = {
  prophet: 'Prophet',
  xgboost: 'XGBoost',
  arima: 'SARIMAX',
  holt_winters: 'Holt-Winters',
  ensemble: 'Ensemble',
  PROPHET: 'Prophet',
  XGBOOST: 'XGBoost',
  ARIMA: 'SARIMAX',
  HOLT_WINTERS: 'Holt-Winters',
  ENSEMBLE: 'Auto-ML',
};

const classColors: Record<string, string> = {
  A: 'bg-green-100 text-green-800 border-green-300',
  B: 'bg-yellow-100 text-yellow-800 border-yellow-300',
  C: 'bg-gray-100 text-gray-800 border-gray-300',
  X: 'bg-blue-100 text-blue-800 border-blue-300',
  Y: 'bg-orange-100 text-orange-800 border-orange-300',
  Z: 'bg-red-100 text-red-800 border-red-300',
};

const signalTypeLabels: Record<string, string> = {
  POS_SPIKE: 'POS Spike',
  POS_DROP: 'POS Drop',
  STOCKOUT_ALERT: 'Stockout Alert',
  PROMOTION_LAUNCH: 'Promotion Launch',
  PROMOTION_END: 'Promotion End',
  WEATHER_EVENT: 'Weather Event',
  FESTIVAL_SEASON: 'Festival Season',
  COMPETITOR_PRICE: 'Competitor Price',
  MARKET_TREND: 'Market Trend',
  NEW_CHANNEL: 'New Channel',
  RETURNS_SPIKE: 'Returns Spike',
  SOCIAL_BUZZ: 'Social Buzz',
};

const signalTypeColors: Record<string, string> = {
  POS_SPIKE: 'bg-green-100 text-green-800',
  POS_DROP: 'bg-red-100 text-red-800',
  STOCKOUT_ALERT: 'bg-red-100 text-red-800',
  PROMOTION_LAUNCH: 'bg-purple-100 text-purple-800',
  PROMOTION_END: 'bg-gray-100 text-gray-800',
  WEATHER_EVENT: 'bg-sky-100 text-sky-800',
  FESTIVAL_SEASON: 'bg-amber-100 text-amber-800',
  COMPETITOR_PRICE: 'bg-orange-100 text-orange-800',
  MARKET_TREND: 'bg-blue-100 text-blue-800',
  NEW_CHANNEL: 'bg-indigo-100 text-indigo-800',
  RETURNS_SPIKE: 'bg-rose-100 text-rose-800',
  SOCIAL_BUZZ: 'bg-pink-100 text-pink-800',
};

const signalTypeOptions = [
  'POS_SPIKE', 'POS_DROP', 'STOCKOUT_ALERT', 'PROMOTION_LAUNCH', 'PROMOTION_END',
  'WEATHER_EVENT', 'FESTIVAL_SEASON', 'COMPETITOR_PRICE', 'MARKET_TREND',
  'NEW_CHANNEL', 'RETURNS_SPIKE', 'SOCIAL_BUZZ',
];

export default function DemandForecastsPage() {
  const queryClient = useQueryClient();
  const [granularity, setGranularity] = useState<string>('');
  const [level, setLevel] = useState<string>('');
  const [warehouseId, setWarehouseId] = useState<string>('');
  const [selectedForecast, setSelectedForecast] = useState<any>(null);
  const [activeTab, setActiveTab] = useState<string>('forecasts');

  // Warehouse list for filter dropdown
  const { data: geoData } = useQuery({
    queryKey: ['geo-hierarchy'],
    queryFn: async () => {
      try {
        const { data } = await apiClient.get('/channel-reports/geo-hierarchy');
        return data;
      } catch {
        return { regions: [] };
      }
    },
    staleTime: 5 * 60 * 1000,
  });

  // Flatten warehouses from geo hierarchy for dropdown
  const allWarehouses = (geoData?.regions || []).flatMap((r: any) => [
    ...(r.warehouses || []),
    ...(r.clusters || []).flatMap((c: any) => c.warehouses || []),
  ]);

  const { data: forecasts, isLoading, refetch, isFetching } = useQuery({
    queryKey: ['snop-forecasts', granularity, level, warehouseId],
    queryFn: () => snopApi.getForecasts({
      ...(granularity ? { granularity } : {}),
      ...(level ? { level } : {}),
      ...(warehouseId ? { warehouse_id: warehouseId } : {}),
    }),
    staleTime: 5 * 60 * 1000,
    gcTime: 10 * 60 * 1000,
  });

  // Model comparison query - always fetch (prefetch for Model Arena tab)
  const { data: modelComparison, isLoading: isComparing } = useQuery({
    queryKey: ['snop-model-comparison', granularity],
    queryFn: async () => {
      try {
        const res = await apiClient.post(`/snop/forecast/compare-models?granularity=${granularity || 'WEEKLY'}&lookback_days=365&forecast_horizon_days=30`);
        return res.data;
      } catch { return null; }
    },
    staleTime: 5 * 60 * 1000,
    gcTime: 10 * 60 * 1000,
  });

  // Demand classification query
  const { data: classification, isLoading: isClassifying } = useQuery({
    queryKey: ['snop-classification', granularity],
    queryFn: async () => {
      try {
        const res = await apiClient.get(`/snop/demand-classification?granularity=${granularity || 'WEEKLY'}`);
        return res.data;
      } catch { return null; }
    },
    enabled: activeTab === 'classification',
    staleTime: 5 * 60 * 1000,
    gcTime: 10 * 60 * 1000,
  });

  // Demand signals query
  const { data: signalsData, isLoading: isLoadingSignals, refetch: refetchSignals } = useQuery({
    queryKey: ['snop-demand-signals'],
    queryFn: async () => {
      const res = await apiClient.get('/snop/demand-signals?limit=100');
      return res.data;
    },
    enabled: activeTab === 'sensing',
    staleTime: 5 * 60 * 1000,
    gcTime: 10 * 60 * 1000,
  });

  // Demand sensing analysis
  const { data: sensingAnalysis, isLoading: isAnalyzing, refetch: refetchAnalysis } = useQuery({
    queryKey: ['snop-sensing-analysis'],
    queryFn: async () => {
      const res = await apiClient.post('/snop/demand-signals/analyze?horizon_days=30');
      return res.data;
    },
    enabled: activeTab === 'sensing',
    staleTime: 5 * 60 * 1000,
    gcTime: 10 * 60 * 1000,
  });

  // Create signal state
  const [showCreateSignal, setShowCreateSignal] = useState(false);
  const [newSignal, setNewSignal] = useState({
    signal_name: '',
    signal_type: 'PROMOTION_LAUNCH',
    impact_direction: 'UP',
    impact_pct: 10,
    signal_strength: 0.7,
    confidence: 0.8,
    effective_start: new Date().toISOString().split('T')[0],
    effective_end: new Date(Date.now() + 14 * 86400000).toISOString().split('T')[0],
    decay_rate: 0.1,
    applies_to_all: true,
    source: 'MANUAL',
    notes: '',
  });

  const createSignalMutation = useMutation({
    mutationFn: async () => {
      const res = await apiClient.post('/snop/demand-signals', newSignal);
      return res.data;
    },
    onSuccess: () => {
      toast.success('Demand signal created');
      setShowCreateSignal(false);
      queryClient.invalidateQueries({ queryKey: ['snop-demand-signals'] });
      queryClient.invalidateQueries({ queryKey: ['snop-sensing-analysis'] });
    },
    onError: () => {
      toast.error('Failed to create signal');
    },
  });

  const detectPosMutation = useMutation({
    mutationFn: async () => {
      const res = await apiClient.post('/snop/demand-signals/detect-pos?lookback_days=7');
      return res.data;
    },
    onSuccess: (data) => {
      toast.success(`Detected ${data.signals?.length || 0} POS signals`);
      queryClient.invalidateQueries({ queryKey: ['snop-demand-signals'] });
      queryClient.invalidateQueries({ queryKey: ['snop-sensing-analysis'] });
    },
    onError: () => {
      toast.error('Failed to detect POS signals');
    },
  });

  const dismissSignalMutation = useMutation({
    mutationFn: async (signalId: string) => {
      const res = await apiClient.post(`/snop/demand-signals/${signalId}/dismiss`);
      return res.data;
    },
    onSuccess: () => {
      toast.success('Signal dismissed');
      queryClient.invalidateQueries({ queryKey: ['snop-demand-signals'] });
      queryClient.invalidateQueries({ queryKey: ['snop-sensing-analysis'] });
    },
    onError: () => {
      toast.error('Failed to dismiss signal');
    },
  });

  const generateMutation = useMutation({
    mutationFn: () => snopApi.generateForecast({
      granularity,
      level,
      horizon_periods: 12,
    }),
    onSuccess: () => {
      toast.success('ML-powered forecast generation started');
      queryClient.invalidateQueries({ queryKey: ['snop-forecasts'] });
    },
    onError: () => {
      toast.error('Failed to generate forecast');
    },
  });

  if (isLoading) {
    return (
      <div className="space-y-6 p-6">
        <Skeleton className="h-8 w-64" />
        <div className="grid gap-4 md:grid-cols-3">
          {[...Array(3)].map((_, i) => <Skeleton key={i} className="h-24" />)}
        </div>
        <Skeleton className="h-96" />
      </div>
    );
  }

  // Build model comparison chart data
  const modelChartData = modelComparison?.model_comparison
    ? Object.entries(modelComparison.model_comparison).map(([name, data]: [string, any]) => ({
        name: algorithmLabels[name] || name,
        mape: data.mape,
        accuracy: data.accuracy ?? Math.max(0, 100 - data.mape),
        weight: (data.weight * 100),
        fill: algorithmColors[name] || '#6B7280',
      }))
    : [];

  // Detect insufficient data: all models at ~0% accuracy (MAPE >= 99)
  const hasInsufficientData = modelChartData.length > 0 &&
    modelChartData.every((m) => m.mape >= 99);
  const hasEmptyChartData = modelChartData.length > 0 &&
    modelChartData.every((m) => m.accuracy < 1);

  return (
    <div className="space-y-6 p-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-blue-100 rounded-lg">
            <Brain className="h-6 w-6 text-blue-600" />
          </div>
          <div>
            <h1 className="text-2xl font-bold tracking-tight">AI Demand Forecasting</h1>
            <p className="text-muted-foreground">
              ML-powered predictions using Prophet, XGBoost, SARIMAX & auto-model selection
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Button onClick={() => refetch()} disabled={isFetching} variant="outline" size="sm">
            <RefreshCw className={`h-4 w-4 mr-2 ${isFetching ? 'animate-spin' : ''}`} />
            Refresh
          </Button>
          <Button onClick={() => generateMutation.mutate()} disabled={generateMutation.isPending}>
            <Zap className="h-4 w-4 mr-2" />
            Generate ML Forecast
          </Button>
        </div>
      </div>

      {/* Filters */}
      <Card>
        <CardContent className="p-4">
          <div className="flex items-center gap-4">
            <Filter className="h-4 w-4 text-muted-foreground" />
            <Select value={granularity} onValueChange={(v) => setGranularity(v === 'ALL' ? '' : v)}>
              <SelectTrigger className="w-40">
                <SelectValue placeholder="Granularity" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="ALL">All</SelectItem>
                <SelectItem value="DAILY">Daily</SelectItem>
                <SelectItem value="WEEKLY">Weekly</SelectItem>
                <SelectItem value="MONTHLY">Monthly</SelectItem>
                <SelectItem value="QUARTERLY">Quarterly</SelectItem>
              </SelectContent>
            </Select>
            <Select value={level} onValueChange={(v) => setLevel(v === 'ALL' ? '' : v)}>
              <SelectTrigger className="w-40">
                <SelectValue placeholder="Level" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="ALL">All Levels</SelectItem>
                <SelectItem value="SKU">By SKU</SelectItem>
                <SelectItem value="CATEGORY">By Category</SelectItem>
                <SelectItem value="REGION">By Region</SelectItem>
                <SelectItem value="CHANNEL">By Channel</SelectItem>
                <SelectItem value="COMPANY">Company-wide</SelectItem>
              </SelectContent>
            </Select>
            <Select value={warehouseId || 'ALL'} onValueChange={(v) => setWarehouseId(v === 'ALL' ? '' : v)}>
              <SelectTrigger className="w-48">
                <SelectValue placeholder="All Warehouses" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="ALL">All Warehouses</SelectItem>
                {allWarehouses.map((w: any) => (
                  <SelectItem key={w.id} value={w.id}>{w.name}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </CardContent>
      </Card>

      {/* Main Tabs */}
      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList>
          <TabsTrigger value="forecasts">
            <LineChart className="h-4 w-4 mr-1.5" />
            Forecasts
          </TabsTrigger>
          <TabsTrigger value="models">
            <Trophy className="h-4 w-4 mr-1.5" />
            Model Arena
          </TabsTrigger>
          <TabsTrigger value="classification">
            <BarChart3 className="h-4 w-4 mr-1.5" />
            ABC-XYZ Classification
          </TabsTrigger>
          <TabsTrigger value="sensing">
            <Radio className="h-4 w-4 mr-1.5" />
            Demand Sensing
          </TabsTrigger>
        </TabsList>

        {/* Forecasts Tab */}
        <TabsContent value="forecasts" className="space-y-4">
          {/* Summary Cards */}
          <div className="grid gap-4 md:grid-cols-4">
            <Card>
              <CardContent className="p-4">
                <div className="flex items-center gap-2">
                  <Clock className="h-4 w-4 text-yellow-600" />
                  <span className="text-sm text-muted-foreground">Pending Review</span>
                </div>
                <p className="text-2xl font-bold mt-2">
                  {forecasts?.items?.filter((f: any) => f.status === 'PENDING_REVIEW').length ?? 0}
                </p>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="p-4">
                <div className="flex items-center gap-2">
                  <CheckCircle className="h-4 w-4 text-green-600" />
                  <span className="text-sm text-muted-foreground">Approved</span>
                </div>
                <p className="text-2xl font-bold mt-2">
                  {forecasts?.items?.filter((f: any) => f.status === 'APPROVED').length ?? 0}
                </p>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="p-4">
                <div className="flex items-center gap-2">
                  <AlertCircle className="h-4 w-4 text-blue-600" />
                  <span className="text-sm text-muted-foreground">Avg Accuracy</span>
                </div>
                <p className="text-2xl font-bold mt-2">
                  {Number(forecasts?.avg_accuracy || 85).toFixed(1)}%
                </p>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="p-4">
                <div className="flex items-center gap-2">
                  <Brain className="h-4 w-4 text-purple-600" />
                  <span className="text-sm text-muted-foreground">Total Forecasts</span>
                </div>
                <p className="text-2xl font-bold mt-2">{forecasts?.total || 0}</p>
              </CardContent>
            </Card>
          </div>

          {/* Forecasts Table */}
          <Card>
            <CardHeader>
              <CardTitle>Forecasts</CardTitle>
              <CardDescription>ML-powered demand forecasts with accuracy metrics</CardDescription>
            </CardHeader>
            <CardContent>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Product/Category</TableHead>
                    <TableHead>Level</TableHead>
                    <TableHead>Granularity</TableHead>
                    <TableHead>Algorithm</TableHead>
                    <TableHead>Accuracy</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead>Created</TableHead>
                    <TableHead></TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {forecasts?.items?.length > 0 ? (
                    forecasts.items.map((forecast: any) => (
                      <TableRow key={forecast.id}>
                        <TableCell className="font-medium">
                          {forecast.product_name || forecast.category_name || 'All Products'}
                        </TableCell>
                        <TableCell>
                          <Badge variant="outline">{forecast.level}</Badge>
                        </TableCell>
                        <TableCell>{forecast.granularity}</TableCell>
                        <TableCell>
                          <Badge
                            variant="outline"
                            className="font-mono text-xs"
                            style={{
                              borderColor: algorithmColors[forecast.algorithm?.toLowerCase()] || '#6B7280',
                              color: algorithmColors[forecast.algorithm?.toLowerCase()] || '#6B7280',
                            }}
                          >
                            {algorithmLabels[forecast.algorithm] || forecast.algorithm}
                          </Badge>
                        </TableCell>
                        <TableCell>
                          <span className={Number(forecast.accuracy) >= 80 ? 'text-green-600 font-semibold' : Number(forecast.accuracy) >= 60 ? 'text-amber-600' : 'text-red-600'}>
                            {forecast.accuracy != null ? Number(forecast.accuracy).toFixed(1) : '-'}%
                          </span>
                        </TableCell>
                        <TableCell>
                          <Badge className={statusColors[forecast.status] || ''}>
                            {forecast.status}
                          </Badge>
                        </TableCell>
                        <TableCell className="text-muted-foreground">
                          {new Date(forecast.created_at).toLocaleDateString()}
                        </TableCell>
                        <TableCell>
                          <Dialog>
                            <DialogTrigger asChild>
                              <Button
                                variant="ghost"
                                size="sm"
                                onClick={() => setSelectedForecast(forecast)}
                              >
                                <Eye className="h-4 w-4" />
                              </Button>
                            </DialogTrigger>
                            <DialogContent className="max-w-4xl">
                              <DialogHeader>
                                <DialogTitle>Forecast Details</DialogTitle>
                                <DialogDescription>
                                  {forecast.product_name || forecast.category_name} - {forecast.granularity} forecast
                                </DialogDescription>
                              </DialogHeader>
                              <div className="h-80">
                                <ResponsiveContainer width="100%" height="100%">
                                  <RechartsLineChart data={forecast.forecast_data || []}>
                                    <CartesianGrid strokeDasharray="3 3" />
                                    <XAxis dataKey="period" />
                                    <YAxis />
                                    <Tooltip />
                                    <Legend />
                                    <Line
                                      type="monotone"
                                      dataKey="predicted_value"
                                      stroke="#3B82F6"
                                      strokeWidth={2}
                                      name="Predicted"
                                    />
                                    <Line
                                      type="monotone"
                                      dataKey="upper_bound"
                                      stroke="#93C5FD"
                                      strokeDasharray="3 3"
                                      name="Upper Bound"
                                    />
                                    <Line
                                      type="monotone"
                                      dataKey="lower_bound"
                                      stroke="#93C5FD"
                                      strokeDasharray="3 3"
                                      name="Lower Bound"
                                    />
                                  </RechartsLineChart>
                                </ResponsiveContainer>
                              </div>
                            </DialogContent>
                          </Dialog>
                        </TableCell>
                      </TableRow>
                    ))
                  ) : (
                    <TableRow>
                      <TableCell colSpan={8} className="text-center py-8 text-muted-foreground">
                        No forecasts found. Click &quot;Generate ML Forecast&quot; to create one.
                      </TableCell>
                    </TableRow>
                  )}
                </TableBody>
              </Table>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Model Arena Tab */}
        <TabsContent value="models" className="space-y-4">
          {isComparing ? (
            <div className="grid gap-4 md:grid-cols-2">
              {[...Array(4)].map((_, i) => <Skeleton key={i} className="h-48" />)}
            </div>
          ) : modelComparison ? (
            <>
              {/* Insufficient Data Warning */}
              {hasInsufficientData && (
                <Card className="border-2 border-amber-200 bg-amber-50/50">
                  <CardContent className="p-6">
                    <div className="flex items-center gap-4">
                      <div className="p-3 bg-amber-100 rounded-full">
                        <AlertCircle className="h-8 w-8 text-amber-600" />
                      </div>
                      <div>
                        <p className="text-base font-semibold text-amber-800">
                          Insufficient Historical Data
                        </p>
                        <p className="text-sm text-amber-700 mt-1">
                          Not enough delivered order data for accurate model training. All models are showing ~0% accuracy.
                          Generate more orders or adjust the lookback period to improve results.
                        </p>
                        {modelComparison.data_points != null && (
                          <p className="text-xs text-amber-600 mt-1">
                            Data points available: {modelComparison.data_points}
                          </p>
                        )}
                      </div>
                    </div>
                  </CardContent>
                </Card>
              )}

              {/* Winning Model Banner */}
              <Card className="border-2 border-green-200 bg-green-50/50">
                <CardContent className="p-6">
                  <div className="flex items-center gap-4">
                    <div className="p-3 bg-green-100 rounded-full">
                      <Trophy className="h-8 w-8 text-green-600" />
                    </div>
                    <div>
                      <p className="text-sm text-green-600 font-medium">Best Model (Auto-Selected)</p>
                      <p className="text-2xl font-bold text-green-800">
                        {algorithmLabels[modelComparison.winning_model] || modelComparison.winning_model}
                      </p>
                      <p className="text-sm text-green-700">
                        MAPE: {modelComparison.winning_mape?.toFixed(1)}% | Accuracy: {(100 - (modelComparison.winning_mape || 0)).toFixed(1)}%
                      </p>
                    </div>
                    {modelComparison.ml_libraries && (
                      <div className="ml-auto flex flex-wrap gap-1.5">
                        {Object.entries(modelComparison.ml_libraries).map(([lib, avail]) => (
                          <Badge
                            key={lib}
                            variant="outline"
                            className={avail ? 'border-green-400 text-green-700 bg-green-50' : 'border-gray-300 text-gray-500'}
                          >
                            {lib} {avail ? '✓' : '✗'}
                          </Badge>
                        ))}
                      </div>
                    )}
                  </div>
                </CardContent>
              </Card>

              {/* Model Accuracy Comparison */}
              <div className="grid gap-4 md:grid-cols-2">
                <Card>
                  <CardHeader>
                    <CardTitle className="text-base">Model Accuracy (Lower MAPE = Better)</CardTitle>
                  </CardHeader>
                  <CardContent>
                    {hasEmptyChartData ? (
                      <div className="h-64 flex items-center justify-center text-muted-foreground text-sm">
                        No meaningful accuracy data to display. Models need more historical data to train.
                      </div>
                    ) : (
                      <div className="h-64">
                        <ResponsiveContainer width="100%" height="100%">
                          <BarChart data={modelChartData} layout="vertical">
                            <CartesianGrid strokeDasharray="3 3" />
                            <XAxis type="number" domain={[0, 100]} unit="%" />
                            <YAxis type="category" dataKey="name" width={100} />
                            <Tooltip
                              formatter={(value) => [`${Number(value).toFixed(1)}%`, 'Accuracy']}
                            />
                            <Bar dataKey="accuracy" radius={[0, 4, 4, 0]}>
                              {modelChartData.map((entry, index) => (
                                <Cell key={`cell-${index}`} fill={entry.fill} />
                              ))}
                            </Bar>
                          </BarChart>
                        </ResponsiveContainer>
                      </div>
                    )}
                  </CardContent>
                </Card>

                <Card>
                  <CardHeader>
                    <CardTitle className="text-base">Ensemble Weights</CardTitle>
                    <CardDescription>How much each model contributes to the ensemble</CardDescription>
                  </CardHeader>
                  <CardContent>
                    <div className="h-64">
                      <ResponsiveContainer width="100%" height="100%">
                        <RadarChart data={modelChartData}>
                          <PolarGrid />
                          <PolarAngleAxis dataKey="name" />
                          <PolarRadiusAxis angle={30} domain={[0, 50]} />
                          <Radar
                            name="Weight %"
                            dataKey="weight"
                            stroke="#8B5CF6"
                            fill="#8B5CF6"
                            fillOpacity={0.3}
                          />
                        </RadarChart>
                      </ResponsiveContainer>
                    </div>
                  </CardContent>
                </Card>
              </div>

              {/* Demand Classification */}
              {modelComparison.demand_classification && (
                <Card>
                  <CardHeader>
                    <CardTitle className="text-base">Demand Pattern Classification</CardTitle>
                    <CardDescription>
                      ABC-XYZ analysis determines the best algorithm for each product
                    </CardDescription>
                  </CardHeader>
                  <CardContent>
                    <div className="flex items-center gap-4">
                      <div className="flex gap-2">
                        <Badge className={classColors[modelComparison.demand_classification.abc_class] || ''}>
                          {modelComparison.demand_classification.abc_class} Class
                        </Badge>
                        <Badge className={classColors[modelComparison.demand_classification.xyz_class] || ''}>
                          {modelComparison.demand_classification.xyz_class} Variability
                        </Badge>
                      </div>
                      <span className="text-sm text-muted-foreground">
                        CV: {modelComparison.demand_classification.cv?.toFixed(3)} |
                        Combined: <strong>{modelComparison.demand_classification.combined_class}</strong> |
                        Recommended: <strong>{algorithmLabels[modelComparison.demand_classification.recommended_algorithm] || modelComparison.demand_classification.recommended_algorithm}</strong>
                      </span>
                    </div>
                  </CardContent>
                </Card>
              )}

              {/* Model Detail Cards */}
              <div className="grid gap-3 md:grid-cols-4">
                {modelChartData.map((model) => (
                  <Card key={model.name} className="relative overflow-hidden">
                    <div
                      className="absolute top-0 left-0 w-full h-1"
                      style={{ backgroundColor: hasInsufficientData ? '#D97706' : model.fill }}
                    />
                    <CardContent className="p-4 pt-5">
                      <p className="text-sm font-medium" style={{ color: model.fill }}>
                        {model.name}
                      </p>
                      <p className="text-2xl font-bold mt-1">
                        {hasInsufficientData ? (
                          <span className="text-amber-600">N/A</span>
                        ) : (
                          <>{model.accuracy.toFixed(1)}%</>
                        )}
                      </p>
                      <p className="text-xs text-muted-foreground">
                        MAPE: {model.mape.toFixed(1)}% | Weight: {model.weight.toFixed(1)}%
                      </p>
                    </CardContent>
                  </Card>
                ))}
              </div>
            </>
          ) : (
            <Card>
              <CardContent className="p-8 text-center text-muted-foreground">
                No model comparison data available. Generate a forecast first.
              </CardContent>
            </Card>
          )}
        </TabsContent>

        {/* ABC-XYZ Classification Tab */}
        <TabsContent value="classification" className="space-y-4">
          {isClassifying ? (
            <Skeleton className="h-96" />
          ) : classification ? (
            <>
              {/* Summary */}
              <div className="grid gap-4 md:grid-cols-6">
                {['A', 'B', 'C'].map((cls) => (
                  <Card key={cls}>
                    <CardContent className="p-4 text-center">
                      <Badge className={classColors[cls] + ' text-lg px-3 py-1'}>
                        {cls}
                      </Badge>
                      <p className="text-2xl font-bold mt-2">
                        {classification.summary?.[cls] || 0}
                      </p>
                      <p className="text-xs text-muted-foreground">
                        {cls === 'A' ? 'High Value' : cls === 'B' ? 'Medium' : 'Low Value'}
                      </p>
                    </CardContent>
                  </Card>
                ))}
                {['X', 'Y', 'Z'].map((cls) => (
                  <Card key={cls}>
                    <CardContent className="p-4 text-center">
                      <Badge className={classColors[cls] + ' text-lg px-3 py-1'}>
                        {cls}
                      </Badge>
                      <p className="text-2xl font-bold mt-2">
                        {classification.summary?.[cls] || 0}
                      </p>
                      <p className="text-xs text-muted-foreground">
                        {cls === 'X' ? 'Stable' : cls === 'Y' ? 'Variable' : 'Erratic'}
                      </p>
                    </CardContent>
                  </Card>
                ))}
              </div>

              {/* Classification Table */}
              <Card>
                <CardHeader>
                  <CardTitle>Product Classification</CardTitle>
                  <CardDescription>
                    {classification.total_products} products classified. Each gets the best-fit algorithm automatically.
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>Product</TableHead>
                        <TableHead>ABC</TableHead>
                        <TableHead>XYZ</TableHead>
                        <TableHead>Class</TableHead>
                        <TableHead>CV</TableHead>
                        <TableHead>Mean Demand</TableHead>
                        <TableHead>Recommended Algorithm</TableHead>
                        <TableHead>Data Points</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {classification.classifications?.slice(0, 50).map((item: any) => (
                        <TableRow key={item.product_id}>
                          <TableCell className="font-medium">{item.product_name}</TableCell>
                          <TableCell>
                            <Badge className={classColors[item.abc_class]}>{item.abc_class}</Badge>
                          </TableCell>
                          <TableCell>
                            <Badge className={classColors[item.xyz_class]}>{item.xyz_class}</Badge>
                          </TableCell>
                          <TableCell>
                            <span className="font-mono font-semibold">{item.combined_class}</span>
                          </TableCell>
                          <TableCell className="font-mono text-sm">
                            {item.cv?.toFixed(3)}
                          </TableCell>
                          <TableCell className="font-mono text-sm">
                            {item.mean_demand?.toFixed(1)}
                          </TableCell>
                          <TableCell>
                            <Badge
                              variant="outline"
                              style={{
                                borderColor: algorithmColors[item.recommended_algorithm?.toLowerCase()] || '#6B7280',
                                color: algorithmColors[item.recommended_algorithm?.toLowerCase()] || '#6B7280',
                              }}
                            >
                              {algorithmLabels[item.recommended_algorithm] || item.recommended_algorithm}
                            </Badge>
                          </TableCell>
                          <TableCell className="text-muted-foreground">{item.data_points}</TableCell>
                        </TableRow>
                      ))}
                      {(!classification.classifications || classification.classifications.length === 0) && (
                        <TableRow>
                          <TableCell colSpan={8} className="text-center py-8 text-muted-foreground">
                            No products found with demand data.
                          </TableCell>
                        </TableRow>
                      )}
                    </TableBody>
                  </Table>
                </CardContent>
              </Card>
            </>
          ) : (
            <Card>
              <CardContent className="p-8 text-center text-muted-foreground">
                No classification data available.
              </CardContent>
            </Card>
          )}
        </TabsContent>

        {/* Demand Sensing Tab */}
        <TabsContent value="sensing" className="space-y-4">
          {isLoadingSignals || isAnalyzing ? (
            <div className="grid gap-4 md:grid-cols-2">
              {[...Array(4)].map((_, i) => <Skeleton key={i} className="h-40" />)}
            </div>
          ) : (
            <>
              {/* Sensing Overview Cards */}
              <div className="grid gap-4 md:grid-cols-4">
                <Card>
                  <CardContent className="p-4">
                    <div className="flex items-center gap-2">
                      <Signal className="h-4 w-4 text-green-600" />
                      <span className="text-sm text-muted-foreground">Active Signals</span>
                    </div>
                    <p className="text-2xl font-bold mt-2">
                      {sensingAnalysis?.active_signals_count || 0}
                    </p>
                  </CardContent>
                </Card>
                <Card>
                  <CardContent className="p-4">
                    <div className="flex items-center gap-2">
                      {(sensingAnalysis?.net_forecast_adjustment_pct || 0) >= 0 ? (
                        <ArrowUp className="h-4 w-4 text-green-600" />
                      ) : (
                        <ArrowDown className="h-4 w-4 text-red-600" />
                      )}
                      <span className="text-sm text-muted-foreground">Net Forecast Adj.</span>
                    </div>
                    <p className={`text-2xl font-bold mt-2 ${
                      (sensingAnalysis?.net_forecast_adjustment_pct || 0) >= 0 ? 'text-green-600' : 'text-red-600'
                    }`}>
                      {(sensingAnalysis?.net_forecast_adjustment_pct || 0) >= 0 ? '+' : ''}
                      {sensingAnalysis?.net_forecast_adjustment_pct?.toFixed(1) || '0.0'}%
                    </p>
                  </CardContent>
                </Card>
                <Card>
                  <CardContent className="p-4">
                    <div className="flex items-center gap-2">
                      <Sparkles className="h-4 w-4 text-purple-600" />
                      <span className="text-sm text-muted-foreground">Confidence</span>
                    </div>
                    <p className="text-2xl font-bold mt-2">
                      {((sensingAnalysis?.weighted_confidence || 0) * 100).toFixed(0)}%
                    </p>
                  </CardContent>
                </Card>
                <Card>
                  <CardContent className="p-4">
                    <div className="flex items-center gap-2">
                      <Radio className="h-4 w-4 text-blue-600" />
                      <span className="text-sm text-muted-foreground">Total Signals</span>
                    </div>
                    <p className="text-2xl font-bold mt-2">
                      {sensingAnalysis?.total_signals_count || signalsData?.total || 0}
                    </p>
                  </CardContent>
                </Card>
              </div>

              {/* Actions Row */}
              <div className="flex items-center gap-2">
                <Button
                  onClick={() => setShowCreateSignal(true)}
                  size="sm"
                >
                  <Plus className="h-4 w-4 mr-2" />
                  Create Signal
                </Button>
                <Button
                  onClick={() => detectPosMutation.mutate()}
                  disabled={detectPosMutation.isPending}
                  variant="outline"
                  size="sm"
                >
                  <Scan className="h-4 w-4 mr-2" />
                  {detectPosMutation.isPending ? 'Scanning...' : 'Auto-Detect POS Signals'}
                </Button>
                <Button
                  onClick={() => { refetchSignals(); refetchAnalysis(); }}
                  variant="outline"
                  size="sm"
                >
                  <RefreshCw className="h-4 w-4 mr-2" />
                  Refresh
                </Button>
              </div>

              {/* Create Signal Dialog */}
              <Dialog open={showCreateSignal} onOpenChange={setShowCreateSignal}>
                <DialogContent className="max-w-lg">
                  <DialogHeader>
                    <DialogTitle>Create Demand Signal</DialogTitle>
                    <DialogDescription>
                      Add a manual demand signal (promotion, weather event, market trend, etc.)
                    </DialogDescription>
                  </DialogHeader>
                  <div className="space-y-4">
                    <div>
                      <Label>Signal Name</Label>
                      <Input
                        value={newSignal.signal_name}
                        onChange={(e) => setNewSignal({ ...newSignal, signal_name: e.target.value })}
                        placeholder="e.g., Diwali Sale 2026"
                      />
                    </div>
                    <div className="grid grid-cols-2 gap-3">
                      <div>
                        <Label>Signal Type</Label>
                        <Select
                          value={newSignal.signal_type}
                          onValueChange={(v) => setNewSignal({ ...newSignal, signal_type: v })}
                        >
                          <SelectTrigger>
                            <SelectValue />
                          </SelectTrigger>
                          <SelectContent>
                            {signalTypeOptions.map((t) => (
                              <SelectItem key={t} value={t}>
                                {signalTypeLabels[t] || t}
                              </SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                      </div>
                      <div>
                        <Label>Direction</Label>
                        <Select
                          value={newSignal.impact_direction}
                          onValueChange={(v) => setNewSignal({ ...newSignal, impact_direction: v })}
                        >
                          <SelectTrigger>
                            <SelectValue />
                          </SelectTrigger>
                          <SelectContent>
                            <SelectItem value="UP">Demand UP</SelectItem>
                            <SelectItem value="DOWN">Demand DOWN</SelectItem>
                          </SelectContent>
                        </Select>
                      </div>
                    </div>
                    <div className="grid grid-cols-3 gap-3">
                      <div>
                        <Label>Impact %</Label>
                        <Input
                          type="number"
                          value={newSignal.impact_pct}
                          onChange={(e) => setNewSignal({ ...newSignal, impact_pct: Number(e.target.value) })}
                        />
                      </div>
                      <div>
                        <Label>Strength (0-1)</Label>
                        <Input
                          type="number"
                          step="0.1"
                          min="0"
                          max="1"
                          value={newSignal.signal_strength}
                          onChange={(e) => setNewSignal({ ...newSignal, signal_strength: Number(e.target.value) })}
                        />
                      </div>
                      <div>
                        <Label>Confidence</Label>
                        <Input
                          type="number"
                          step="0.1"
                          min="0"
                          max="1"
                          value={newSignal.confidence}
                          onChange={(e) => setNewSignal({ ...newSignal, confidence: Number(e.target.value) })}
                        />
                      </div>
                    </div>
                    <div className="grid grid-cols-2 gap-3">
                      <div>
                        <Label>Start Date</Label>
                        <Input
                          type="date"
                          value={newSignal.effective_start}
                          onChange={(e) => setNewSignal({ ...newSignal, effective_start: e.target.value })}
                        />
                      </div>
                      <div>
                        <Label>End Date</Label>
                        <Input
                          type="date"
                          value={newSignal.effective_end}
                          onChange={(e) => setNewSignal({ ...newSignal, effective_end: e.target.value })}
                        />
                      </div>
                    </div>
                    <div>
                      <Label>Notes (optional)</Label>
                      <Input
                        value={newSignal.notes}
                        onChange={(e) => setNewSignal({ ...newSignal, notes: e.target.value })}
                        placeholder="Additional context..."
                      />
                    </div>
                    <Button
                      onClick={() => createSignalMutation.mutate()}
                      disabled={createSignalMutation.isPending || !newSignal.signal_name}
                      className="w-full"
                    >
                      {createSignalMutation.isPending ? 'Creating...' : 'Create Signal'}
                    </Button>
                  </div>
                </DialogContent>
              </Dialog>

              {/* Recommendations */}
              {sensingAnalysis?.recommendations && sensingAnalysis.recommendations.length > 0 && (
                <Card className="border-blue-200 bg-blue-50/30">
                  <CardHeader className="pb-2">
                    <CardTitle className="text-base flex items-center gap-2">
                      <Sparkles className="h-4 w-4 text-blue-600" />
                      AI Recommendations
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <ul className="space-y-2">
                      {sensingAnalysis.recommendations.map((rec: string, i: number) => (
                        <li key={i} className="text-sm flex items-start gap-2">
                          <span className="text-blue-500 mt-0.5">&#8226;</span>
                          {rec}
                        </li>
                      ))}
                    </ul>
                  </CardContent>
                </Card>
              )}

              {/* Impact by Signal Type */}
              {sensingAnalysis?.impact_by_type && Object.keys(sensingAnalysis.impact_by_type).length > 0 && (
                <Card>
                  <CardHeader>
                    <CardTitle className="text-base">Impact by Signal Type</CardTitle>
                    <CardDescription>Weighted impact contribution from each signal category</CardDescription>
                  </CardHeader>
                  <CardContent>
                    <div className="h-56">
                      <ResponsiveContainer width="100%" height="100%">
                        <BarChart
                          data={Object.entries(sensingAnalysis.impact_by_type).map(([type, impact]) => ({
                            type: signalTypeLabels[type] || type.replace('EXT_', ''),
                            impact: Number(impact),
                            fill: Number(impact) >= 0 ? '#22C55E' : '#EF4444',
                          }))}
                          layout="vertical"
                        >
                          <CartesianGrid strokeDasharray="3 3" />
                          <XAxis type="number" unit="%" />
                          <YAxis type="category" dataKey="type" width={130} />
                          <Tooltip formatter={(value) => [`${Number(value).toFixed(1)}%`, 'Impact']} />
                          <Bar dataKey="impact" radius={[0, 4, 4, 0]}>
                            {Object.entries(sensingAnalysis.impact_by_type).map(([type, impact], index) => (
                              <Cell key={index} fill={Number(impact) >= 0 ? '#22C55E' : '#EF4444'} />
                            ))}
                          </Bar>
                        </BarChart>
                      </ResponsiveContainer>
                    </div>
                  </CardContent>
                </Card>
              )}

              {/* Active Signals Feed */}
              <Card>
                <CardHeader>
                  <CardTitle className="text-base">Signal Feed</CardTitle>
                  <CardDescription>
                    {signalsData?.total || 0} total signals | Showing active and recent signals
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>Signal</TableHead>
                        <TableHead>Type</TableHead>
                        <TableHead>Direction</TableHead>
                        <TableHead>Impact</TableHead>
                        <TableHead>Strength</TableHead>
                        <TableHead>Active</TableHead>
                        <TableHead>Remaining</TableHead>
                        <TableHead>Source</TableHead>
                        <TableHead>Status</TableHead>
                        <TableHead></TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {signalsData?.signals?.length > 0 ? (
                        signalsData.signals.map((signal: any) => (
                          <TableRow key={signal.id}>
                            <TableCell className="font-medium max-w-[180px] truncate">
                              {signal.name}
                            </TableCell>
                            <TableCell>
                              <Badge className={signalTypeColors[signal.type] || 'bg-gray-100 text-gray-800'}>
                                {signalTypeLabels[signal.type] || signal.type}
                              </Badge>
                            </TableCell>
                            <TableCell>
                              {signal.impact_direction === 'UP' ? (
                                <ArrowUp className="h-4 w-4 text-green-600" />
                              ) : (
                                <ArrowDown className="h-4 w-4 text-red-600" />
                              )}
                            </TableCell>
                            <TableCell>
                              <span className={signal.impact_direction === 'UP' ? 'text-green-600 font-semibold' : 'text-red-600 font-semibold'}>
                                {signal.impact_direction === 'UP' ? '+' : '-'}{signal.impact_pct?.toFixed(1)}%
                              </span>
                            </TableCell>
                            <TableCell>
                              <div className="flex items-center gap-1.5">
                                <div className="w-16 h-2 bg-gray-200 rounded-full overflow-hidden">
                                  <div
                                    className="h-full bg-blue-500 rounded-full"
                                    style={{ width: `${(signal.current_strength || 0) * 100}%` }}
                                  />
                                </div>
                                <span className="text-xs text-muted-foreground">
                                  {((signal.current_strength || 0) * 100).toFixed(0)}%
                                </span>
                              </div>
                            </TableCell>
                            <TableCell className="text-muted-foreground text-sm">
                              {signal.days_active}d
                            </TableCell>
                            <TableCell className="text-muted-foreground text-sm">
                              {signal.days_remaining}d
                            </TableCell>
                            <TableCell>
                              <Badge variant="outline" className="text-xs">
                                {signal.source}
                              </Badge>
                            </TableCell>
                            <TableCell>
                              <Badge className={
                                signal.status === 'ACTIVE' ? 'bg-green-100 text-green-800' :
                                signal.status === 'APPLIED' ? 'bg-blue-100 text-blue-800' :
                                signal.status === 'EXPIRED' ? 'bg-gray-100 text-gray-600' :
                                signal.status === 'DISMISSED' ? 'bg-red-100 text-red-600' :
                                'bg-yellow-100 text-yellow-800'
                              }>
                                {signal.status}
                              </Badge>
                            </TableCell>
                            <TableCell>
                              {signal.status === 'ACTIVE' && (
                                <Button
                                  variant="ghost"
                                  size="sm"
                                  onClick={() => dismissSignalMutation.mutate(signal.id)}
                                  title="Dismiss signal"
                                >
                                  <XCircle className="h-4 w-4 text-muted-foreground" />
                                </Button>
                              )}
                            </TableCell>
                          </TableRow>
                        ))
                      ) : (
                        <TableRow>
                          <TableCell colSpan={10} className="text-center py-8 text-muted-foreground">
                            No demand signals yet. Create one manually or use Auto-Detect to scan POS data.
                          </TableCell>
                        </TableRow>
                      )}
                    </TableBody>
                  </Table>
                </CardContent>
              </Card>
            </>
          )}
        </TabsContent>
      </Tabs>
    </div>
  );
}
