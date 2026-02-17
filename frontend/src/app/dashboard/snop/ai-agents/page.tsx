'use client';

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Bot,
  RefreshCw,
  Shield,
  ShoppingCart,
  BarChart3,
  AlertTriangle,
  AlertCircle,
  CheckCircle,
  Clock,
  Zap,
  Play,
  Activity,
  Package,
  TrendingUp,
  TrendingDown,
  Info,
} from 'lucide-react';

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Progress } from '@/components/ui/progress';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { apiClient } from '@/lib/api/client';
import { toast } from 'sonner';

const severityConfig: Record<string, { color: string; icon: any; bg: string }> = {
  CRITICAL: { color: 'text-red-600', icon: AlertTriangle, bg: 'bg-red-100 dark:bg-red-900/30' },
  HIGH: { color: 'text-orange-600', icon: AlertCircle, bg: 'bg-orange-100 dark:bg-orange-900/30' },
  MEDIUM: { color: 'text-yellow-600', icon: Clock, bg: 'bg-yellow-100 dark:bg-yellow-900/30' },
  LOW: { color: 'text-blue-600', icon: Info, bg: 'bg-blue-100 dark:bg-blue-900/30' },
  INFO: { color: 'text-gray-500', icon: Info, bg: 'bg-gray-100 dark:bg-gray-800/30' },
};

const categoryLabels: Record<string, string> = {
  STOCKOUT_RISK: 'Stockout Risk',
  OVERSTOCK: 'Overstock',
  DEMAND_SPIKE: 'Demand Spike',
  DEMAND_DROP: 'Demand Drop',
  SUPPLY_GAP: 'Supply Gap',
  FORECAST_BIAS: 'Forecast Bias',
  REORDER_NEEDED: 'Reorder Needed',
  CAPACITY_BREACH: 'Capacity Breach',
  LEAD_TIME_RISK: 'Lead Time Risk',
};

export default function AIAgentsPage() {
  const [activeTab, setActiveTab] = useState('alerts');
  const queryClient = useQueryClient();

  // ---- Queries ----
  const { data: alertCenter, isLoading, refetch, isFetching } = useQuery({
    queryKey: ['snop-alert-center'],
    queryFn: async () => {
      const res = await apiClient.get('/snop/agents/alert-center');
      return res.data;
    },
  });

  const { data: agentStatus } = useQuery({
    queryKey: ['snop-agent-status'],
    queryFn: async () => {
      const res = await apiClient.get('/snop/agents/status');
      return res.data;
    },
    enabled: activeTab === 'agents',
  });

  // ---- Individual agent mutations ----
  const runExceptions = useMutation({
    mutationFn: async () => {
      const res = await apiClient.post('/snop/agents/run-exceptions');
      return res.data;
    },
    onSuccess: (data) => {
      toast.success(`Exception agent found ${data.total_alerts ?? 0} alerts`);
      queryClient.invalidateQueries({ queryKey: ['snop-alert-center'] });
    },
    onError: (err: any) => {
      toast.error(err?.response?.data?.detail || 'Failed to run Exception Detection agent');
    },
  });

  const runReorder = useMutation({
    mutationFn: async () => {
      const res = await apiClient.post('/snop/agents/run-reorder');
      return res.data;
    },
    onSuccess: (data) => {
      toast.success(`Reorder agent generated ${data.total_suggestions ?? 0} suggestions`);
    },
    onError: (err: any) => {
      toast.error(err?.response?.data?.detail || 'Failed to run Reorder agent');
    },
  });

  const runBias = useMutation({
    mutationFn: async () => {
      const res = await apiClient.post('/snop/agents/run-bias');
      return res.data;
    },
    onSuccess: (data) => {
      toast.success(`Bias agent found ${data.total_findings ?? 0} findings`);
    },
    onError: (err: any) => {
      toast.error(err?.response?.data?.detail || 'Failed to run Forecast Bias agent');
    },
  });

  if (isLoading) {
    return (
      <div className="space-y-6 p-6">
        <Skeleton className="h-8 w-64" />
        <div className="grid gap-4 md:grid-cols-5">
          {[...Array(5)].map((_, i) => <Skeleton key={i} className="h-24" />)}
        </div>
        <Skeleton className="h-96" />
      </div>
    );
  }

  const summary = alertCenter?.summary || {};
  const alerts = alertCenter?.alerts || [];
  const reorderData = runReorder.data;
  const biasData = runBias.data;

  return (
    <div className="space-y-6 p-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-indigo-100 rounded-lg dark:bg-indigo-900/30">
            <Bot className="h-6 w-6 text-indigo-600" />
          </div>
          <div>
            <h1 className="text-2xl font-bold tracking-tight">AI Command Center</h1>
            <p className="text-muted-foreground">
              Autonomous planning agents monitoring your supply chain 24/7
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Button onClick={() => refetch()} disabled={isFetching} variant="outline" size="sm">
            <RefreshCw className={`h-4 w-4 mr-2 ${isFetching ? 'animate-spin' : ''}`} />
            Refresh All
          </Button>
        </div>
      </div>

      {/* Severity Summary Cards */}
      <div className="grid gap-4 md:grid-cols-5">
        {[
          { label: 'Critical', key: 'CRITICAL', icon: AlertTriangle, color: 'text-red-600', bg: 'bg-red-50 dark:bg-red-900/20' },
          { label: 'High', key: 'HIGH', icon: AlertCircle, color: 'text-orange-600', bg: 'bg-orange-50 dark:bg-orange-900/20' },
          { label: 'Medium', key: 'MEDIUM', icon: Clock, color: 'text-yellow-600', bg: 'bg-yellow-50 dark:bg-yellow-900/20' },
          { label: 'Low', key: 'LOW', icon: Info, color: 'text-blue-600', bg: 'bg-blue-50 dark:bg-blue-900/20' },
          { label: 'Total Alerts', key: 'total', icon: Zap, color: 'text-indigo-600', bg: 'bg-indigo-50 dark:bg-indigo-900/20' },
        ].map((item) => (
          <Card key={item.key} className={item.bg}>
            <CardContent className="p-4">
              <div className="flex items-center gap-2">
                <item.icon className={`h-4 w-4 ${item.color}`} />
                <span className="text-sm text-muted-foreground">{item.label}</span>
              </div>
              <p className="text-2xl font-bold mt-2">
                {item.key === 'total' ? summary.total_alerts || 0 : summary.by_severity?.[item.key] || 0}
              </p>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Tabs */}
      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList>
          <TabsTrigger value="alerts" className="gap-1">
            <AlertTriangle className="h-4 w-4" /> Alert Center
          </TabsTrigger>
          <TabsTrigger value="agents" className="gap-1">
            <Bot className="h-4 w-4" /> Agent Status
          </TabsTrigger>
          <TabsTrigger value="reorder" className="gap-1">
            <ShoppingCart className="h-4 w-4" /> Reorder Agent
          </TabsTrigger>
          <TabsTrigger value="bias" className="gap-1">
            <BarChart3 className="h-4 w-4" /> Forecast Bias
          </TabsTrigger>
        </TabsList>

        {/* ======= TAB: Alert Center ======= */}
        <TabsContent value="alerts">
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <div>
                  <CardTitle>Prioritized Alerts</CardTitle>
                  <CardDescription>
                    {summary.total_alerts || 0} alerts from {Object.keys(summary.by_agent || {}).length} agents
                  </CardDescription>
                </div>
                <Badge variant="outline" className="text-xs">
                  Last updated: {alertCenter?.generated_at ? new Date(alertCenter.generated_at).toLocaleTimeString() : 'N/A'}
                </Badge>
              </div>
            </CardHeader>
            <CardContent>
              {alerts.length > 0 ? (
                <div className="space-y-3">
                  {alerts.map((alert: any) => {
                    const sevConfig = severityConfig[alert.severity] || severityConfig.INFO;
                    const SevIcon = sevConfig.icon;

                    return (
                      <div
                        key={alert.id}
                        className={`flex items-start gap-4 p-4 rounded-lg border ${sevConfig.bg}`}
                      >
                        <div className={`mt-0.5 ${sevConfig.color}`}>
                          <SevIcon className="h-5 w-5" />
                        </div>
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2 flex-wrap">
                            <h4 className="font-semibold text-sm">{alert.title}</h4>
                            <Badge variant="outline" className="text-xs">
                              {categoryLabels[alert.category] || alert.category}
                            </Badge>
                            <Badge
                              className={`text-xs ${
                                alert.severity === 'CRITICAL' ? 'bg-red-600 text-white' :
                                alert.severity === 'HIGH' ? 'bg-orange-600 text-white' :
                                alert.severity === 'MEDIUM' ? 'bg-yellow-600 text-white' :
                                'bg-gray-600 text-white'
                              }`}
                            >
                              {alert.severity}
                            </Badge>
                          </div>
                          <p className="text-sm text-muted-foreground mt-1">{alert.message}</p>
                          {alert.recommended_action && (
                            <p className="text-xs mt-2 text-primary font-medium">
                              Recommended: {alert.recommended_action}
                            </p>
                          )}
                        </div>
                        <div className="text-xs text-muted-foreground whitespace-nowrap">
                          {alert.agent_source?.replace(/_/g, ' ')}
                        </div>
                      </div>
                    );
                  })}
                </div>
              ) : (
                <div className="text-center py-12 text-muted-foreground">
                  <CheckCircle className="h-16 w-16 mx-auto mb-4 text-green-500 opacity-50" />
                  <h3 className="text-lg font-semibold">All Clear</h3>
                  <p>No active alerts — your supply chain is operating within normal parameters</p>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* ======= TAB: Agent Status ======= */}
        <TabsContent value="agents">
          <div className="grid gap-4 md:grid-cols-3">
            {(agentStatus?.agents || []).map((agent: any) => (
              <Card key={agent.id}>
                <CardHeader>
                  <div className="flex items-center justify-between">
                    <CardTitle className="text-base flex items-center gap-2">
                      {agent.id === 'exception_detection' && <Shield className="h-5 w-5 text-red-600" />}
                      {agent.id === 'reorder' && <ShoppingCart className="h-5 w-5 text-blue-600" />}
                      {agent.id === 'forecast_bias' && <BarChart3 className="h-5 w-5 text-purple-600" />}
                      {agent.name}
                    </CardTitle>
                    <Badge variant={agent.status === 'ready' ? 'default' : 'secondary'}>
                      {agent.status === 'ready' ? 'Ready' : 'No Data'}
                    </Badge>
                  </div>
                  <CardDescription>{agent.description}</CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="space-y-3">
                    <div className="text-sm">
                      <span className="text-muted-foreground">Data Sources: </span>
                      <span>{agent.data_sources}</span>
                    </div>
                    <div>
                      <p className="text-xs font-medium text-muted-foreground mb-1">Capabilities:</p>
                      <div className="flex flex-wrap gap-1">
                        {(agent.capabilities || []).map((cap: string, i: number) => (
                          <Badge key={i} variant="outline" className="text-xs">
                            {cap}
                          </Badge>
                        ))}
                      </div>
                    </div>
                    <Button
                      size="sm"
                      variant="outline"
                      className="w-full mt-2"
                      onClick={() => {
                        if (agent.id === 'exception_detection') runExceptions.mutate();
                        else if (agent.id === 'reorder') runReorder.mutate();
                        else if (agent.id === 'forecast_bias') runBias.mutate();
                      }}
                      disabled={
                        agent.status !== 'ready' ||
                        runExceptions.isPending || runReorder.isPending || runBias.isPending
                      }
                    >
                      <Play className="h-3 w-3 mr-1" /> Run Agent
                    </Button>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        </TabsContent>

        {/* ======= TAB: Reorder Agent ======= */}
        <TabsContent value="reorder">
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-lg font-semibold">Purchase Order Suggestions</h3>
                <p className="text-sm text-muted-foreground">
                  Auto-generated based on inventory position and demand forecast
                </p>
              </div>
              <Button
                onClick={() => runReorder.mutate()}
                disabled={runReorder.isPending}
                size="sm"
              >
                <Play className={`h-4 w-4 mr-2 ${runReorder.isPending ? 'animate-spin' : ''}`} />
                Run Reorder Agent
              </Button>
            </div>

            {reorderData ? (
              <>
                {/* Reorder Summary */}
                <div className="grid gap-4 md:grid-cols-4">
                  <Card>
                    <CardContent className="p-4">
                      <span className="text-sm text-muted-foreground">Total Suggestions</span>
                      <p className="text-2xl font-bold">{reorderData.total_suggestions}</p>
                    </CardContent>
                  </Card>
                  <Card className="bg-red-50 dark:bg-red-900/20">
                    <CardContent className="p-4">
                      <span className="text-sm text-red-600">Emergency</span>
                      <p className="text-2xl font-bold text-red-600">{reorderData.by_urgency?.EMERGENCY || 0}</p>
                    </CardContent>
                  </Card>
                  <Card className="bg-orange-50 dark:bg-orange-900/20">
                    <CardContent className="p-4">
                      <span className="text-sm text-orange-600">Urgent</span>
                      <p className="text-2xl font-bold text-orange-600">{reorderData.by_urgency?.URGENT || 0}</p>
                    </CardContent>
                  </Card>
                  <Card>
                    <CardContent className="p-4">
                      <span className="text-sm text-muted-foreground">Est. Total Cost</span>
                      <p className="text-2xl font-bold">INR {(reorderData.total_estimated_cost / 100000).toFixed(2)} L</p>
                    </CardContent>
                  </Card>
                </div>

                {/* Reorder Table */}
                <Card>
                  <CardContent className="pt-6">
                    <Table>
                      <TableHeader>
                        <TableRow>
                          <TableHead>Product</TableHead>
                          <TableHead>Urgency</TableHead>
                          <TableHead className="text-right">Current Stock</TableHead>
                          <TableHead className="text-right">Reorder Point</TableHead>
                          <TableHead className="text-right">Order Qty</TableHead>
                          <TableHead className="text-right">Days Supply</TableHead>
                          <TableHead>Est. Delivery</TableHead>
                          <TableHead className="text-right">Est. Cost</TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {(reorderData.suggestions || []).map((s: any) => (
                          <TableRow key={s.id}>
                            <TableCell className="font-mono text-sm">{s.product_id?.slice(0, 8)}</TableCell>
                            <TableCell>
                              <Badge className={
                                s.urgency === 'EMERGENCY' ? 'bg-red-600 text-white' :
                                s.urgency === 'URGENT' ? 'bg-orange-600 text-white' :
                                'bg-blue-600 text-white'
                              }>
                                {s.urgency}
                              </Badge>
                            </TableCell>
                            <TableCell className="text-right">{s.current_stock}</TableCell>
                            <TableCell className="text-right">{s.reorder_point}</TableCell>
                            <TableCell className="text-right font-semibold text-primary">{s.suggested_order_qty}</TableCell>
                            <TableCell className="text-right">
                              <span className={s.days_of_supply_remaining < 3 ? 'text-red-600 font-bold' : ''}>
                                {s.days_of_supply_remaining} days
                              </span>
                            </TableCell>
                            <TableCell>{s.expected_delivery_date}</TableCell>
                            <TableCell className="text-right">INR {(s.estimated_cost / 1000).toFixed(1)}K</TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  </CardContent>
                </Card>
              </>
            ) : (
              <Card>
                <CardContent className="p-12 text-center">
                  <ShoppingCart className="h-16 w-16 mx-auto mb-4 text-muted-foreground opacity-50" />
                  <h3 className="text-lg font-semibold">No Reorder Data</h3>
                  <p className="text-muted-foreground mt-1">Click &quot;Run Reorder Agent&quot; to generate purchase order suggestions</p>
                </CardContent>
              </Card>
            )}
          </div>
        </TabsContent>

        {/* ======= TAB: Forecast Bias ======= */}
        <TabsContent value="bias">
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-lg font-semibold">Forecast Bias Analysis</h3>
                <p className="text-sm text-muted-foreground">
                  Detect systematic errors and algorithm performance issues
                </p>
              </div>
              <Button
                onClick={() => runBias.mutate()}
                disabled={runBias.isPending}
                size="sm"
              >
                <Play className={`h-4 w-4 mr-2 ${runBias.isPending ? 'animate-spin' : ''}`} />
                Run Bias Agent
              </Button>
            </div>

            {biasData ? (
              <>
                {/* Bias Summary */}
                <div className="grid gap-4 md:grid-cols-4">
                  <Card>
                    <CardContent className="p-4">
                      <span className="text-sm text-muted-foreground">Forecasts Analyzed</span>
                      <p className="text-2xl font-bold">{biasData.overall_stats?.total_forecasts_analyzed || 0}</p>
                    </CardContent>
                  </Card>
                  <Card>
                    <CardContent className="p-4">
                      <span className="text-sm text-muted-foreground">Overall Bias</span>
                      <p className={`text-2xl font-bold ${biasData.overall_stats?.overall_avg_bias > 0 ? 'text-blue-600' : 'text-orange-600'}`}>
                        {biasData.overall_stats?.overall_avg_bias > 0 ? '+' : ''}
                        {biasData.overall_stats?.overall_avg_bias?.toFixed(1)}%
                      </p>
                      <p className="text-xs text-muted-foreground capitalize">
                        {biasData.overall_stats?.overall_direction}
                      </p>
                    </CardContent>
                  </Card>
                  <Card className="bg-green-50 dark:bg-green-900/20">
                    <CardContent className="p-4">
                      <span className="text-sm text-green-600">Best Algorithm</span>
                      <p className="text-xl font-bold text-green-600">{biasData.overall_stats?.best_algorithm || '-'}</p>
                    </CardContent>
                  </Card>
                  <Card className="bg-red-50 dark:bg-red-900/20">
                    <CardContent className="p-4">
                      <span className="text-sm text-red-600">Worst Algorithm</span>
                      <p className="text-xl font-bold text-red-600">{biasData.overall_stats?.worst_algorithm || '-'}</p>
                    </CardContent>
                  </Card>
                </div>

                {/* Algorithm MAPE Comparison */}
                {biasData.overall_stats?.algorithm_mape && (
                  <Card>
                    <CardHeader>
                      <CardTitle className="text-base">Algorithm Accuracy (MAPE)</CardTitle>
                      <CardDescription>Lower is better</CardDescription>
                    </CardHeader>
                    <CardContent>
                      <div className="space-y-3">
                        {Object.entries(biasData.overall_stats.algorithm_mape).map(([algo, mape]: [string, any]) => (
                          <div key={algo} className="space-y-1">
                            <div className="flex justify-between text-sm">
                              <span className="font-medium">{algo}</span>
                              <span className={mape > 30 ? 'text-red-600 font-bold' : mape > 15 ? 'text-yellow-600' : 'text-green-600'}>
                                {mape.toFixed(1)}% MAPE
                              </span>
                            </div>
                            <Progress value={Math.max(0, 100 - mape)} className="h-2" />
                          </div>
                        ))}
                      </div>
                    </CardContent>
                  </Card>
                )}

                {/* Findings */}
                {biasData.findings?.length > 0 && (
                  <Card>
                    <CardHeader>
                      <CardTitle className="text-base">Findings & Recommendations</CardTitle>
                    </CardHeader>
                    <CardContent>
                      <div className="space-y-3">
                        {biasData.findings.map((f: any) => {
                          const cfg = severityConfig[f.severity] || severityConfig.INFO;
                          const Icon = cfg.icon;
                          return (
                            <div key={f.id} className={`p-4 rounded-lg border ${cfg.bg}`}>
                              <div className="flex items-start gap-3">
                                <Icon className={`h-5 w-5 mt-0.5 ${cfg.color}`} />
                                <div>
                                  <p className="font-medium text-sm">{f.message}</p>
                                  <p className="text-xs text-primary mt-1 font-medium">
                                    {f.recommendation}
                                  </p>
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
            ) : (
              <Card>
                <CardContent className="p-12 text-center">
                  <BarChart3 className="h-16 w-16 mx-auto mb-4 text-muted-foreground opacity-50" />
                  <h3 className="text-lg font-semibold">No Bias Analysis</h3>
                  <p className="text-muted-foreground mt-1">Click &quot;Run Bias Agent&quot; to analyze forecast accuracy</p>
                </CardContent>
              </Card>
            )}
          </div>
        </TabsContent>
      </Tabs>
    </div>
  );
}
