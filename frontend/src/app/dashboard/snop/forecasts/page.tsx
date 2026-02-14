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
import { snopApi } from '@/lib/api';
import { toast } from 'sonner';
import { getAccessToken, getTenantId } from '@/lib/api/client';

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

export default function DemandForecastsPage() {
  const queryClient = useQueryClient();
  const [granularity, setGranularity] = useState<string>('MONTHLY');
  const [level, setLevel] = useState<string>('SKU');
  const [selectedForecast, setSelectedForecast] = useState<any>(null);
  const [activeTab, setActiveTab] = useState<string>('forecasts');

  const { data: forecasts, isLoading, refetch, isFetching } = useQuery({
    queryKey: ['snop-forecasts', granularity, level],
    queryFn: () => snopApi.getForecasts({ granularity, level }),
  });

  // Model comparison query
  const { data: modelComparison, isLoading: isComparing } = useQuery({
    queryKey: ['snop-model-comparison', granularity],
    queryFn: async () => {
      const res = await fetch(`/api/v1/snop/forecast/compare-models?granularity=${granularity}&lookback_days=365&forecast_horizon_days=30`, {
        headers: {
          'Authorization': `Bearer ${getAccessToken() || ''}`,
          'X-Tenant-ID': getTenantId(),
        },
      });
      if (!res.ok) return null;
      return res.json();
    },
    enabled: activeTab === 'models',
  });

  // Demand classification query
  const { data: classification, isLoading: isClassifying } = useQuery({
    queryKey: ['snop-classification', granularity],
    queryFn: async () => {
      const res = await fetch(`/api/v1/snop/demand-classification?granularity=${granularity}`, {
        headers: {
          'Authorization': `Bearer ${getAccessToken() || ''}`,
          'X-Tenant-ID': getTenantId(),
        },
      });
      if (!res.ok) return null;
      return res.json();
    },
    enabled: activeTab === 'classification',
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
        accuracy: Math.max(0, 100 - data.mape),
        weight: (data.weight * 100),
        fill: algorithmColors[name] || '#6B7280',
      }))
    : [];

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
            <Select value={granularity} onValueChange={setGranularity}>
              <SelectTrigger className="w-40">
                <SelectValue placeholder="Granularity" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="DAILY">Daily</SelectItem>
                <SelectItem value="WEEKLY">Weekly</SelectItem>
                <SelectItem value="MONTHLY">Monthly</SelectItem>
                <SelectItem value="QUARTERLY">Quarterly</SelectItem>
              </SelectContent>
            </Select>
            <Select value={level} onValueChange={setLevel}>
              <SelectTrigger className="w-40">
                <SelectValue placeholder="Level" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="SKU">By SKU</SelectItem>
                <SelectItem value="CATEGORY">By Category</SelectItem>
                <SelectItem value="REGION">By Region</SelectItem>
                <SelectItem value="CHANNEL">By Channel</SelectItem>
                <SelectItem value="COMPANY">Company-wide</SelectItem>
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
                  {forecasts?.items?.filter((f: any) => f.status === 'PENDING_REVIEW').length || 0}
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
                  {forecasts?.items?.filter((f: any) => f.status === 'APPROVED').length || 0}
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
                  {forecasts?.avg_accuracy?.toFixed(1) || 85}%
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
                          <span className={forecast.accuracy >= 80 ? 'text-green-600 font-semibold' : forecast.accuracy >= 60 ? 'text-amber-600' : 'text-red-600'}>
                            {forecast.accuracy?.toFixed(1) || '-'}%
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
                      style={{ backgroundColor: model.fill }}
                    />
                    <CardContent className="p-4 pt-5">
                      <p className="text-sm font-medium" style={{ color: model.fill }}>
                        {model.name}
                      </p>
                      <p className="text-2xl font-bold mt-1">{model.accuracy.toFixed(1)}%</p>
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
      </Tabs>
    </div>
  );
}
