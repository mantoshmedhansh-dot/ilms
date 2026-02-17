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
  Warehouse,
  Package,
  Users,
  ArrowRightLeft,
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
  anomaly_detection: Shield,
  smart_slotting: BarChart3,
  labor_forecasting: Users,
  replenishment: Package,
};

const agentColors: Record<string, string> = {
  anomaly_detection: 'text-red-600',
  smart_slotting: 'text-purple-600',
  labor_forecasting: 'text-blue-600',
  replenishment: 'text-green-600',
};

export default function WMSAICommandCenterPage() {
  const [activeTab, setActiveTab] = useState('alerts');
  const queryClient = useQueryClient();

  const { data: dashboard, isLoading, refetch, isFetching } = useQuery({
    queryKey: ['wms-ai-dashboard'],
    queryFn: async () => {
      const res = await apiClient.get('/wms-ai/dashboard');
      return res.data;
    },
  });

  const runAgent = useMutation({
    mutationFn: async (agentName: string) => {
      const res = await apiClient.post(`/wms-ai/agents/${agentName}/run`);
      return res.data;
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['wms-ai-dashboard'] }),
  });

  const runSlotting = useMutation({
    mutationFn: async () => {
      const res = await apiClient.post('/wms-ai/agents/smart-slotting/run');
      return res.data;
    },
  });

  const runReplenishment = useMutation({
    mutationFn: async () => {
      const res = await apiClient.post('/wms-ai/agents/replenishment/run');
      return res.data;
    },
  });

  const runLabor = useMutation({
    mutationFn: async () => {
      const res = await apiClient.post('/wms-ai/agents/labor-forecasting/run');
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
  const slottingData = runSlotting.data;
  const replenishData = runReplenishment.data;
  const laborData = runLabor.data;

  return (
    <div className="space-y-6 p-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-emerald-100 rounded-lg dark:bg-emerald-900/30">
            <Warehouse className="h-6 w-6 text-emerald-600" />
          </div>
          <div>
            <h1 className="text-2xl font-bold tracking-tight">WMS AI Command Center</h1>
            <p className="text-muted-foreground">
              AI agents monitoring warehouse operations 24/7
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
          { label: 'Total Alerts', key: 'total', icon: Zap, color: 'text-emerald-600', bg: 'bg-emerald-50 dark:bg-emerald-900/20' },
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
          <TabsTrigger value="agents" className="gap-1">
            <Bot className="h-4 w-4" /> Agent Status
          </TabsTrigger>
          <TabsTrigger value="slotting" className="gap-1">
            <BarChart3 className="h-4 w-4" /> Slotting
          </TabsTrigger>
          <TabsTrigger value="replenishment" className="gap-1">
            <Package className="h-4 w-4" /> Replenishment
          </TabsTrigger>
          <TabsTrigger value="labor" className="gap-1">
            <Users className="h-4 w-4" /> Labor Forecast
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
                    {summary.total_alerts || 0} alerts from {summary.agents_ready || 0} agents
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
                          <p className="text-sm text-muted-foreground mt-1">{rec.details}</p>
                          {rec.recommendation && (
                            <p className="text-xs mt-2 text-primary font-medium">
                              Action: {rec.recommendation}
                            </p>
                          )}
                        </div>
                      </div>
                    );
                  })}
                </div>
              ) : (
                <div className="text-center py-12 text-muted-foreground">
                  <CheckCircle className="h-16 w-16 mx-auto mb-4 text-green-500 opacity-50" />
                  <h3 className="text-lg font-semibold">All Clear</h3>
                  <p>No active alerts - warehouse operations are running smoothly</p>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* ======= TAB: Agent Status ======= */}
        <TabsContent value="agents">
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
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

        {/* ======= TAB: Slotting ======= */}
        <TabsContent value="slotting">
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-lg font-semibold">Smart Slotting Analysis</h3>
                <p className="text-sm text-muted-foreground">ABC velocity classification and relocation recommendations</p>
              </div>
              <Button onClick={() => runSlotting.mutate()} disabled={runSlotting.isPending} size="sm">
                <Play className={`h-4 w-4 mr-2 ${runSlotting.isPending ? 'animate-spin' : ''}`} />
                Run Slotting Agent
              </Button>
            </div>

            {slottingData ? (
              <>
                <div className="grid gap-4 md:grid-cols-4">
                  <Card><CardContent className="p-4">
                    <span className="text-sm text-muted-foreground">Products Analyzed</span>
                    <p className="text-2xl font-bold">{slottingData.summary?.total_products_analyzed || 0}</p>
                  </CardContent></Card>
                  <Card className="bg-green-50 dark:bg-green-900/20"><CardContent className="p-4">
                    <span className="text-sm text-green-600">A-Class (Fast)</span>
                    <p className="text-2xl font-bold text-green-600">{slottingData.summary?.abc_distribution?.A || 0}</p>
                  </CardContent></Card>
                  <Card className="bg-yellow-50 dark:bg-yellow-900/20"><CardContent className="p-4">
                    <span className="text-sm text-yellow-600">B-Class (Medium)</span>
                    <p className="text-2xl font-bold text-yellow-600">{slottingData.summary?.abc_distribution?.B || 0}</p>
                  </CardContent></Card>
                  <Card className="bg-red-50 dark:bg-red-900/20"><CardContent className="p-4">
                    <span className="text-sm text-red-600">Relocations Needed</span>
                    <p className="text-2xl font-bold text-red-600">{slottingData.summary?.total_relocations_recommended || 0}</p>
                  </CardContent></Card>
                </div>

                {(slottingData.relocations || []).length > 0 && (
                  <Card>
                    <CardHeader><CardTitle className="text-base">Relocation Recommendations</CardTitle></CardHeader>
                    <CardContent>
                      <Table>
                        <TableHeader>
                          <TableRow>
                            <TableHead>Product</TableHead>
                            <TableHead>ABC Class</TableHead>
                            <TableHead>Current Zone</TableHead>
                            <TableHead>Action</TableHead>
                            <TableHead>Priority</TableHead>
                            <TableHead>Expected Improvement</TableHead>
                          </TableRow>
                        </TableHeader>
                        <TableBody>
                          {(slottingData.relocations || []).slice(0, 10).map((r: any, i: number) => (
                            <TableRow key={i}>
                              <TableCell className="font-mono text-sm">{r.product_id?.slice(0, 8)}</TableCell>
                              <TableCell><Badge variant="outline">{r.abc_class}</Badge></TableCell>
                              <TableCell>{r.current_zone_type || 'N/A'}</TableCell>
                              <TableCell>{r.action}</TableCell>
                              <TableCell>
                                <Badge className={r.priority === 'HIGH' ? 'bg-red-600 text-white' : 'bg-yellow-600 text-white'}>
                                  {r.priority}
                                </Badge>
                              </TableCell>
                              <TableCell className="text-sm">{r.expected_improvement}</TableCell>
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
                <BarChart3 className="h-16 w-16 mx-auto mb-4 text-muted-foreground opacity-50" />
                <h3 className="text-lg font-semibold">No Slotting Data</h3>
                <p className="text-muted-foreground mt-1">Click &quot;Run Slotting Agent&quot; to analyze bin optimization</p>
              </CardContent></Card>
            )}
          </div>
        </TabsContent>

        {/* ======= TAB: Replenishment ======= */}
        <TabsContent value="replenishment">
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-lg font-semibold">Replenishment Monitor</h3>
                <p className="text-sm text-muted-foreground">Forward-pick bin levels and replenishment triggers</p>
              </div>
              <Button onClick={() => runReplenishment.mutate()} disabled={runReplenishment.isPending} size="sm">
                <Play className={`h-4 w-4 mr-2 ${runReplenishment.isPending ? 'animate-spin' : ''}`} />
                Run Replenishment Agent
              </Button>
            </div>

            {replenishData ? (
              <>
                <div className="grid gap-4 md:grid-cols-4">
                  <Card><CardContent className="p-4">
                    <span className="text-sm text-muted-foreground">Total Picking Bins</span>
                    <p className="text-2xl font-bold">{replenishData.summary?.total_picking_bins || 0}</p>
                  </CardContent></Card>
                  <Card className="bg-red-50 dark:bg-red-900/20"><CardContent className="p-4">
                    <span className="text-sm text-red-600">Critical</span>
                    <p className="text-2xl font-bold text-red-600">{replenishData.summary?.by_urgency?.CRITICAL || 0}</p>
                  </CardContent></Card>
                  <Card className="bg-orange-50 dark:bg-orange-900/20"><CardContent className="p-4">
                    <span className="text-sm text-orange-600">High</span>
                    <p className="text-2xl font-bold text-orange-600">{replenishData.summary?.by_urgency?.HIGH || 0}</p>
                  </CardContent></Card>
                  <Card><CardContent className="p-4">
                    <span className="text-sm text-muted-foreground">Avg Lead Time</span>
                    <p className="text-2xl font-bold">{replenishData.summary?.avg_replenishment_lead_time_mins || 0} min</p>
                  </CardContent></Card>
                </div>

                {(replenishData.suggestions || []).length > 0 && (
                  <Card>
                    <CardHeader><CardTitle className="text-base">Replenishment Queue</CardTitle></CardHeader>
                    <CardContent>
                      <Table>
                        <TableHeader>
                          <TableRow>
                            <TableHead>Bin</TableHead>
                            <TableHead>Zone</TableHead>
                            <TableHead>Urgency</TableHead>
                            <TableHead className="text-right">Current</TableHead>
                            <TableHead className="text-right">Max</TableHead>
                            <TableHead className="text-right">Fill %</TableHead>
                            <TableHead className="text-right">Replenish Qty</TableHead>
                            <TableHead>Hours Left</TableHead>
                          </TableRow>
                        </TableHeader>
                        <TableBody>
                          {(replenishData.suggestions || []).slice(0, 15).map((s: any, i: number) => (
                            <TableRow key={i}>
                              <TableCell className="font-mono">{s.destination_bin}</TableCell>
                              <TableCell>{s.zone_name}</TableCell>
                              <TableCell>
                                <Badge className={
                                  s.urgency === 'CRITICAL' ? 'bg-red-600 text-white' :
                                  s.urgency === 'HIGH' ? 'bg-orange-600 text-white' :
                                  'bg-yellow-600 text-white'
                                }>{s.urgency}</Badge>
                              </TableCell>
                              <TableCell className="text-right">{s.current_qty}</TableCell>
                              <TableCell className="text-right">{s.max_qty}</TableCell>
                              <TableCell className="text-right">
                                <span className={s.fill_percentage < 20 ? 'text-red-600 font-bold' : ''}>{s.fill_percentage}%</span>
                              </TableCell>
                              <TableCell className="text-right font-semibold text-primary">{s.replenish_qty}</TableCell>
                              <TableCell>{s.hours_of_stock_remaining != null ? `${s.hours_of_stock_remaining}h` : '-'}</TableCell>
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
                <Package className="h-16 w-16 mx-auto mb-4 text-muted-foreground opacity-50" />
                <h3 className="text-lg font-semibold">No Replenishment Data</h3>
                <p className="text-muted-foreground mt-1">Click &quot;Run Replenishment Agent&quot; to check bin levels</p>
              </CardContent></Card>
            )}
          </div>
        </TabsContent>

        {/* ======= TAB: Labor Forecast ======= */}
        <TabsContent value="labor">
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-lg font-semibold">Labor Demand Forecast</h3>
                <p className="text-sm text-muted-foreground">14-day workforce planning with shift staffing</p>
              </div>
              <Button onClick={() => runLabor.mutate()} disabled={runLabor.isPending} size="sm">
                <Play className={`h-4 w-4 mr-2 ${runLabor.isPending ? 'animate-spin' : ''}`} />
                Run Labor Agent
              </Button>
            </div>

            {laborData?.forecast ? (
              <>
                <div className="grid gap-4 md:grid-cols-4">
                  <Card><CardContent className="p-4">
                    <span className="text-sm text-muted-foreground">Avg Daily Orders</span>
                    <p className="text-2xl font-bold">{laborData.summary?.avg_daily_orders || 0}</p>
                  </CardContent></Card>
                  <Card><CardContent className="p-4">
                    <span className="text-sm text-muted-foreground">Avg Workers Needed</span>
                    <p className="text-2xl font-bold">{laborData.summary?.avg_workers_needed || 0}</p>
                  </CardContent></Card>
                  <Card><CardContent className="p-4">
                    <span className="text-sm text-muted-foreground">Current Workforce</span>
                    <p className="text-2xl font-bold">{laborData.summary?.current_workforce || 0}</p>
                  </CardContent></Card>
                  <Card className={laborData.summary?.gap > 0 ? 'bg-red-50 dark:bg-red-900/20' : 'bg-green-50 dark:bg-green-900/20'}>
                    <CardContent className="p-4">
                      <span className={`text-sm ${laborData.summary?.gap > 0 ? 'text-red-600' : 'text-green-600'}`}>
                        {laborData.summary?.gap > 0 ? 'Shortfall' : 'Surplus'}
                      </span>
                      <p className={`text-2xl font-bold ${laborData.summary?.gap > 0 ? 'text-red-600' : 'text-green-600'}`}>
                        {Math.abs(laborData.summary?.gap || 0)} workers
                      </p>
                    </CardContent>
                  </Card>
                </div>

                <Card>
                  <CardHeader><CardTitle className="text-base">Daily Forecast</CardTitle></CardHeader>
                  <CardContent>
                    <Table>
                      <TableHeader>
                        <TableRow>
                          <TableHead>Date</TableHead>
                          <TableHead>Day</TableHead>
                          <TableHead className="text-right">Orders</TableHead>
                          <TableHead className="text-right">Items</TableHead>
                          <TableHead className="text-right">Hours Needed</TableHead>
                          <TableHead className="text-right">Workers</TableHead>
                          <TableHead>Shifts (M/A/N)</TableHead>
                          <TableHead className="text-right">Utilization</TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {(laborData.forecast || []).map((f: any, i: number) => (
                          <TableRow key={i}>
                            <TableCell>{f.date}</TableCell>
                            <TableCell>{f.day_of_week}</TableCell>
                            <TableCell className="text-right">{f.forecasted_orders}</TableCell>
                            <TableCell className="text-right">{f.forecasted_items}</TableCell>
                            <TableCell className="text-right">{f.labor_hours_needed}</TableCell>
                            <TableCell className="text-right font-semibold">{f.workers_needed}</TableCell>
                            <TableCell>
                              {f.shift_staffing?.morning}/{f.shift_staffing?.afternoon}/{f.shift_staffing?.night}
                            </TableCell>
                            <TableCell className="text-right">
                              <span className={f.capacity_utilization > 100 ? 'text-red-600 font-bold' : ''}>
                                {f.capacity_utilization}%
                              </span>
                            </TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  </CardContent>
                </Card>
              </>
            ) : (
              <Card><CardContent className="p-12 text-center">
                <Users className="h-16 w-16 mx-auto mb-4 text-muted-foreground opacity-50" />
                <h3 className="text-lg font-semibold">No Labor Forecast</h3>
                <p className="text-muted-foreground mt-1">Click &quot;Run Labor Agent&quot; to generate workforce forecast</p>
              </CardContent></Card>
            )}
          </div>
        </TabsContent>
      </Tabs>
    </div>
  );
}
