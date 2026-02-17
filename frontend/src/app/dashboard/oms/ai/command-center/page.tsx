'use client';

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Bot,
  RefreshCw,
  Shield,
  BarChart3,
  AlertTriangle,
  AlertCircle,
  CheckCircle,
  Clock,
  Zap,
  Play,
  Info,
  ShoppingCart,
  Truck,
  PackageCheck,
  RotateCcw,
  MapPin,
  ListOrdered,
} from 'lucide-react';

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { apiClient } from '@/lib/api/client';

const severityConfig: Record<string, { color: string; icon: any; bg: string }> = {
  CRITICAL: { color: 'text-red-600', icon: AlertTriangle, bg: 'bg-red-100 dark:bg-red-900/30' },
  HIGH: { color: 'text-orange-600', icon: AlertCircle, bg: 'bg-orange-100 dark:bg-orange-900/30' },
  MEDIUM: { color: 'text-yellow-600', icon: Clock, bg: 'bg-yellow-100 dark:bg-yellow-900/30' },
  LOW: { color: 'text-blue-600', icon: Info, bg: 'bg-blue-100 dark:bg-blue-900/30' },
};

const agentIcons: Record<string, any> = {
  fraud_detection: Shield,
  smart_routing: MapPin,
  delivery_promise: Truck,
  order_prioritization: ListOrdered,
  returns_prediction: RotateCcw,
};

const agentColors: Record<string, string> = {
  fraud_detection: 'text-red-600',
  smart_routing: 'text-blue-600',
  delivery_promise: 'text-green-600',
  order_prioritization: 'text-purple-600',
  returns_prediction: 'text-orange-600',
};

const riskBadge = (level: string) => {
  const cls =
    level === 'CRITICAL' ? 'bg-red-600 text-white' :
    level === 'HIGH' ? 'bg-orange-600 text-white' :
    level === 'MEDIUM' ? 'bg-yellow-600 text-white' :
    'bg-gray-200 text-gray-800';
  return <Badge className={`text-xs ${cls}`}>{level}</Badge>;
};

export default function OMSAICommandCenterPage() {
  const [activeTab, setActiveTab] = useState('alerts');
  const queryClient = useQueryClient();

  const { data: dashboard, isLoading, refetch, isFetching } = useQuery({
    queryKey: ['oms-ai-dashboard'],
    queryFn: async () => {
      const res = await apiClient.get('/oms-ai/dashboard');
      return res.data;
    },
  });

  const runAgent = useMutation({
    mutationFn: async (agentName: string) => {
      const res = await apiClient.post(`/oms-ai/agents/${agentName}/run`);
      return res.data;
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['oms-ai-dashboard'] }),
  });

  const runFraud = useMutation({
    mutationFn: async () => {
      const res = await apiClient.post('/oms-ai/agents/fraud-detection/run');
      return res.data;
    },
  });

  const runQueue = useMutation({
    mutationFn: async () => {
      const res = await apiClient.post('/oms-ai/agents/order-prioritization/run');
      return res.data;
    },
  });

  const runReturns = useMutation({
    mutationFn: async () => {
      const res = await apiClient.post('/oms-ai/agents/returns-prediction/run');
      return res.data;
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

  const summary = dashboard?.summary || {};
  const recommendations = dashboard?.recommendations || [];
  const agents = dashboard?.agents || [];
  const fraudData = runFraud.data;
  const queueData = runQueue.data;
  const returnsData = runReturns.data;

  return (
    <div className="space-y-6 p-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-blue-100 rounded-lg dark:bg-blue-900/30">
            <ShoppingCart className="h-6 w-6 text-blue-600" />
          </div>
          <div>
            <h1 className="text-2xl font-bold tracking-tight">OMS AI Command Center</h1>
            <p className="text-muted-foreground">
              AI agents monitoring order management operations 24/7
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
          { label: 'Total Alerts', key: 'total', icon: Zap, color: 'text-blue-600', bg: 'bg-blue-50 dark:bg-blue-900/20' },
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
            <AlertTriangle className="h-4 w-4" /> Alerts
          </TabsTrigger>
          <TabsTrigger value="fraud" className="gap-1">
            <Shield className="h-4 w-4" /> Fraud Monitor
          </TabsTrigger>
          <TabsTrigger value="queue" className="gap-1">
            <ListOrdered className="h-4 w-4" /> Order Queue
          </TabsTrigger>
          <TabsTrigger value="returns" className="gap-1">
            <RotateCcw className="h-4 w-4" /> Returns Risk
          </TabsTrigger>
          <TabsTrigger value="agents" className="gap-1">
            <Bot className="h-4 w-4" /> Agent Status
          </TabsTrigger>
        </TabsList>

        {/* ======= TAB: Alerts ======= */}
        <TabsContent value="alerts">
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <div>
                  <CardTitle>Recommendations & Alerts</CardTitle>
                  <CardDescription>
                    {summary.total_alerts || 0} alerts from {summary.agents_ready || 0}/{summary.agents_total || 5} agents
                  </CardDescription>
                </div>
                <Badge variant="outline" className="text-xs">
                  Last updated: {dashboard?.generated_at ? new Date(dashboard.generated_at).toLocaleTimeString() : 'N/A'}
                </Badge>
              </div>
            </CardHeader>
            <CardContent>
              {recommendations.length > 0 ? (
                <div className="space-y-3">
                  {recommendations.map((rec: any, idx: number) => {
                    const sevConfig = severityConfig[rec.severity] || severityConfig.LOW;
                    const SevIcon = sevConfig.icon;
                    return (
                      <div key={idx} className={`flex items-start gap-4 p-4 rounded-lg border ${sevConfig.bg}`}>
                        <div className={`mt-0.5 ${sevConfig.color}`}>
                          <SevIcon className="h-5 w-5" />
                        </div>
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2 flex-wrap">
                            <Badge className={`text-xs ${
                              rec.severity === 'CRITICAL' ? 'bg-red-600 text-white' :
                              rec.severity === 'HIGH' ? 'bg-orange-600 text-white' :
                              rec.severity === 'MEDIUM' ? 'bg-yellow-600 text-white' :
                              'bg-gray-600 text-white'
                            }`}>
                              {rec.severity}
                            </Badge>
                            <Badge variant="outline" className="text-xs">
                              {(rec.type || '').replace(/_/g, ' ')}
                            </Badge>
                          </div>
                          <p className="text-sm text-muted-foreground mt-1">{rec.recommendation}</p>
                        </div>
                      </div>
                    );
                  })}
                </div>
              ) : (
                <div className="text-center py-12 text-muted-foreground">
                  <CheckCircle className="h-16 w-16 mx-auto mb-4 text-green-500 opacity-50" />
                  <h3 className="text-lg font-semibold">All Clear</h3>
                  <p>No active alerts - order operations are running smoothly</p>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* ======= TAB: Fraud Monitor ======= */}
        <TabsContent value="fraud">
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-lg font-semibold">Fraud Detection Monitor</h3>
                <p className="text-sm text-muted-foreground">Score recent orders for fraud risk (0-100)</p>
              </div>
              <Button onClick={() => runFraud.mutate()} disabled={runFraud.isPending} size="sm">
                <Play className={`h-4 w-4 mr-2 ${runFraud.isPending ? 'animate-spin' : ''}`} />
                Run Fraud Agent
              </Button>
            </div>

            {fraudData ? (
              <>
                <div className="grid gap-4 md:grid-cols-4">
                  <Card><CardContent className="p-4">
                    <span className="text-sm text-muted-foreground">Orders Scored</span>
                    <p className="text-2xl font-bold">{fraudData.summary?.total_orders_scored || 0}</p>
                  </CardContent></Card>
                  <Card className="bg-red-50 dark:bg-red-900/20"><CardContent className="p-4">
                    <span className="text-sm text-red-600">Critical Risk</span>
                    <p className="text-2xl font-bold text-red-600">{fraudData.summary?.by_risk_level?.CRITICAL || 0}</p>
                  </CardContent></Card>
                  <Card className="bg-orange-50 dark:bg-orange-900/20"><CardContent className="p-4">
                    <span className="text-sm text-orange-600">High Risk</span>
                    <p className="text-2xl font-bold text-orange-600">{fraudData.summary?.by_risk_level?.HIGH || 0}</p>
                  </CardContent></Card>
                  <Card><CardContent className="p-4">
                    <span className="text-sm text-muted-foreground">Avg Risk Score</span>
                    <p className="text-2xl font-bold">{fraudData.summary?.avg_risk_score || 0}/100</p>
                  </CardContent></Card>
                </div>

                {(fraudData.scored_orders || []).length > 0 && (
                  <Card>
                    <CardHeader><CardTitle className="text-base">Scored Orders</CardTitle></CardHeader>
                    <CardContent>
                      <Table>
                        <TableHeader>
                          <TableRow>
                            <TableHead>Order ID</TableHead>
                            <TableHead>Order #</TableHead>
                            <TableHead className="text-right">Risk Score</TableHead>
                            <TableHead>Risk Level</TableHead>
                            <TableHead className="text-right">Amount</TableHead>
                            <TableHead>Payment</TableHead>
                            <TableHead>Top Factor</TableHead>
                          </TableRow>
                        </TableHeader>
                        <TableBody>
                          {(fraudData.scored_orders || []).slice(0, 15).map((o: any, i: number) => (
                            <TableRow key={i}>
                              <TableCell className="font-mono text-sm">{o.order_id?.slice(0, 8)}</TableCell>
                              <TableCell>{o.order_number || '-'}</TableCell>
                              <TableCell className="text-right font-semibold">
                                <span className={o.risk_score >= 70 ? 'text-red-600' : o.risk_score >= 50 ? 'text-orange-600' : ''}>
                                  {o.risk_score}
                                </span>
                              </TableCell>
                              <TableCell>{riskBadge(o.risk_level)}</TableCell>
                              <TableCell className="text-right">{o.factors?.order_value?.toLocaleString() || '-'}</TableCell>
                              <TableCell>{o.factors?.payment_method || '-'}</TableCell>
                              <TableCell className="text-sm text-muted-foreground">
                                {(o.factors?.risk_factors || []).slice(0, 1).join(', ') || '-'}
                              </TableCell>
                            </TableRow>
                          ))}
                        </TableBody>
                      </Table>
                    </CardContent>
                  </Card>
                )}
              </>
            ) : (
              <Card><CardContent className="p-12 text-center">
                <Shield className="h-16 w-16 mx-auto mb-4 text-muted-foreground opacity-50" />
                <h3 className="text-lg font-semibold">No Fraud Data</h3>
                <p className="text-muted-foreground mt-1">Click &quot;Run Fraud Agent&quot; to score recent orders</p>
              </CardContent></Card>
            )}
          </div>
        </TabsContent>

        {/* ======= TAB: Order Queue ======= */}
        <TabsContent value="queue">
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-lg font-semibold">Order Prioritization Queue</h3>
                <p className="text-sm text-muted-foreground">Pending orders ranked by fulfillment priority</p>
              </div>
              <Button onClick={() => runQueue.mutate()} disabled={runQueue.isPending} size="sm">
                <Play className={`h-4 w-4 mr-2 ${runQueue.isPending ? 'animate-spin' : ''}`} />
                Run Prioritization Agent
              </Button>
            </div>

            {queueData ? (
              <>
                <div className="grid gap-4 md:grid-cols-4">
                  <Card><CardContent className="p-4">
                    <span className="text-sm text-muted-foreground">Pending Orders</span>
                    <p className="text-2xl font-bold">{queueData.summary?.total_pending_orders || 0}</p>
                  </CardContent></Card>
                  <Card className="bg-red-50 dark:bg-red-900/20"><CardContent className="p-4">
                    <span className="text-sm text-red-600">SLA Breach Risk</span>
                    <p className="text-2xl font-bold text-red-600">{queueData.summary?.sla_breach_risk || 0}</p>
                  </CardContent></Card>
                  <Card><CardContent className="p-4">
                    <span className="text-sm text-muted-foreground">Avg Age</span>
                    <p className="text-2xl font-bold">{(queueData.summary?.avg_age_hours || 0).toFixed(1)}h</p>
                  </CardContent></Card>
                  <Card><CardContent className="p-4">
                    <span className="text-sm text-muted-foreground">Avg Priority Score</span>
                    <p className="text-2xl font-bold">{queueData.summary?.avg_priority_score || 0}/100</p>
                  </CardContent></Card>
                </div>

                {(queueData.queue || []).length > 0 && (
                  <Card>
                    <CardHeader><CardTitle className="text-base">Priority Queue</CardTitle></CardHeader>
                    <CardContent>
                      <Table>
                        <TableHeader>
                          <TableRow>
                            <TableHead>#</TableHead>
                            <TableHead>Order #</TableHead>
                            <TableHead className="text-right">Priority Score</TableHead>
                            <TableHead>Tier</TableHead>
                            <TableHead className="text-right">Value</TableHead>
                            <TableHead>Age</TableHead>
                            <TableHead>Channel</TableHead>
                            <TableHead>Payment</TableHead>
                          </TableRow>
                        </TableHeader>
                        <TableBody>
                          {(queueData.queue || []).slice(0, 20).map((o: any, i: number) => (
                            <TableRow key={i}>
                              <TableCell className="text-muted-foreground">{i + 1}</TableCell>
                              <TableCell className="font-medium">{o.order_number}</TableCell>
                              <TableCell className="text-right font-semibold text-primary">{o.priority_score}</TableCell>
                              <TableCell>
                                <Badge variant="outline" className="text-xs">{o.customer_tier || 'N/A'}</Badge>
                              </TableCell>
                              <TableCell className="text-right">{o.order_value?.toLocaleString() || '-'}</TableCell>
                              <TableCell>{o.age_hours != null ? `${o.age_hours.toFixed(0)}h` : '-'}</TableCell>
                              <TableCell className="text-sm">{o.channel || '-'}</TableCell>
                              <TableCell className="text-sm">{o.payment_method || '-'}</TableCell>
                            </TableRow>
                          ))}
                        </TableBody>
                      </Table>
                    </CardContent>
                  </Card>
                )}
              </>
            ) : (
              <Card><CardContent className="p-12 text-center">
                <ListOrdered className="h-16 w-16 mx-auto mb-4 text-muted-foreground opacity-50" />
                <h3 className="text-lg font-semibold">No Queue Data</h3>
                <p className="text-muted-foreground mt-1">Click &quot;Run Prioritization Agent&quot; to rank pending orders</p>
              </CardContent></Card>
            )}
          </div>
        </TabsContent>

        {/* ======= TAB: Returns Risk ======= */}
        <TabsContent value="returns">
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-lg font-semibold">Returns Prediction</h3>
                <p className="text-sm text-muted-foreground">Predict return probability for recent orders</p>
              </div>
              <Button onClick={() => runReturns.mutate()} disabled={runReturns.isPending} size="sm">
                <Play className={`h-4 w-4 mr-2 ${runReturns.isPending ? 'animate-spin' : ''}`} />
                Run Returns Agent
              </Button>
            </div>

            {returnsData ? (
              <>
                <div className="grid gap-4 md:grid-cols-4">
                  <Card><CardContent className="p-4">
                    <span className="text-sm text-muted-foreground">Orders Scored</span>
                    <p className="text-2xl font-bold">{returnsData.summary?.total_orders_scored || 0}</p>
                  </CardContent></Card>
                  <Card className="bg-red-50 dark:bg-red-900/20"><CardContent className="p-4">
                    <span className="text-sm text-red-600">High Risk</span>
                    <p className="text-2xl font-bold text-red-600">{returnsData.summary?.high_risk_orders || 0}</p>
                  </CardContent></Card>
                  <Card><CardContent className="p-4">
                    <span className="text-sm text-muted-foreground">Avg Probability</span>
                    <p className="text-2xl font-bold">{((returnsData.summary?.avg_return_probability || 0) * 100).toFixed(1)}%</p>
                  </CardContent></Card>
                  <Card><CardContent className="p-4">
                    <span className="text-sm text-muted-foreground">Est. Return Rate</span>
                    <p className="text-2xl font-bold">{returnsData.summary?.estimated_return_rate || 'N/A'}</p>
                  </CardContent></Card>
                </div>

                {(returnsData.scored_orders || []).length > 0 && (
                  <Card>
                    <CardHeader><CardTitle className="text-base">Return Risk Scores</CardTitle></CardHeader>
                    <CardContent>
                      <Table>
                        <TableHeader>
                          <TableRow>
                            <TableHead>Order ID</TableHead>
                            <TableHead className="text-right">Return Probability</TableHead>
                            <TableHead>Risk Level</TableHead>
                            <TableHead>COD</TableHead>
                            <TableHead>First-Time Buyer</TableHead>
                            <TableHead>Seasonal Factor</TableHead>
                            <TableHead>Recommendation</TableHead>
                          </TableRow>
                        </TableHeader>
                        <TableBody>
                          {(returnsData.scored_orders || []).slice(0, 15).map((o: any, i: number) => (
                            <TableRow key={i}>
                              <TableCell className="font-mono text-sm">{o.order_id?.slice(0, 8)}</TableCell>
                              <TableCell className="text-right font-semibold">
                                <span className={o.return_probability >= 0.6 ? 'text-red-600' : o.return_probability >= 0.3 ? 'text-orange-600' : ''}>
                                  {(o.return_probability * 100).toFixed(1)}%
                                </span>
                              </TableCell>
                              <TableCell>{riskBadge(o.risk_level)}</TableCell>
                              <TableCell>{o.factors?.is_cod ? 'Yes' : 'No'}</TableCell>
                              <TableCell>{o.factors?.is_first_time_buyer ? 'Yes' : 'No'}</TableCell>
                              <TableCell>{o.factors?.seasonal_factor || '-'}</TableCell>
                              <TableCell className="text-sm text-muted-foreground max-w-[200px] truncate">
                                {o.recommendation || '-'}
                              </TableCell>
                            </TableRow>
                          ))}
                        </TableBody>
                      </Table>
                    </CardContent>
                  </Card>
                )}
              </>
            ) : (
              <Card><CardContent className="p-12 text-center">
                <RotateCcw className="h-16 w-16 mx-auto mb-4 text-muted-foreground opacity-50" />
                <h3 className="text-lg font-semibold">No Returns Data</h3>
                <p className="text-muted-foreground mt-1">Click &quot;Run Returns Agent&quot; to predict return risk</p>
              </CardContent></Card>
            )}
          </div>
        </TabsContent>

        {/* ======= TAB: Agent Status ======= */}
        <TabsContent value="agents">
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            {agents.map((agent: any) => {
              const Icon = agentIcons[agent.id] || Bot;
              const iconColor = agentColors[agent.id] || 'text-gray-600';
              return (
                <Card key={agent.id}>
                  <CardHeader>
                    <div className="flex items-center justify-between">
                      <CardTitle className="text-base flex items-center gap-2">
                        <Icon className={`h-5 w-5 ${iconColor}`} />
                        {agent.name}
                      </CardTitle>
                      <Badge variant={agent.status === 'completed' || agent.status === 'idle' ? 'default' : 'secondary'}>
                        {agent.status === 'completed' ? 'Ready' : agent.status === 'idle' ? 'Idle' : agent.status}
                      </Badge>
                    </div>
                    <CardDescription className="text-xs">{agent.description}</CardDescription>
                  </CardHeader>
                  <CardContent>
                    <div className="space-y-3">
                      <div className="text-xs text-muted-foreground">
                        <span className="font-medium">Sources: </span>{agent.data_sources}
                      </div>
                      <div className="flex flex-wrap gap-1">
                        {(agent.capabilities || []).slice(0, 3).map((cap: string, i: number) => (
                          <Badge key={i} variant="outline" className="text-[10px]">{cap}</Badge>
                        ))}
                      </div>
                      {agent.last_run && (
                        <p className="text-[10px] text-muted-foreground">
                          Last run: {new Date(agent.last_run).toLocaleString()}
                        </p>
                      )}
                      <Button
                        size="sm"
                        variant="outline"
                        className="w-full mt-2"
                        onClick={() => runAgent.mutate(agent.id.replace(/_/g, '-'))}
                        disabled={runAgent.isPending}
                      >
                        <Play className="h-3 w-3 mr-1" /> Run Agent
                      </Button>
                    </div>
                  </CardContent>
                </Card>
              );
            })}
          </div>
        </TabsContent>
      </Tabs>
    </div>
  );
}
