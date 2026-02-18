'use client';

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Bot,
  RefreshCw,
  AlertTriangle,
  AlertCircle,
  CheckCircle,
  Clock,
  Zap,
  Play,
  Info,
  Truck,
  BarChart3,
  Banknote,
  BadgePercent,
  TrendingUp,
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
  'dealer-performance': BarChart3,
  'collection-optimizer': Banknote,
  'scheme-effectiveness': BadgePercent,
  'demand-sensing': TrendingUp,
};

const agentColors: Record<string, string> = {
  'dealer-performance': 'text-blue-600',
  'collection-optimizer': 'text-green-600',
  'scheme-effectiveness': 'text-purple-600',
  'demand-sensing': 'text-orange-600',
};

const severityBadge = (level: string) => {
  const cls =
    level === 'CRITICAL' ? 'bg-red-600 text-white' :
    level === 'HIGH' ? 'bg-orange-600 text-white' :
    level === 'MEDIUM' ? 'bg-yellow-600 text-white' :
    'bg-gray-200 text-gray-800';
  return <Badge className={`text-xs ${cls}`}>{level}</Badge>;
};

export default function DMSAICommandCenterPage() {
  const [activeTab, setActiveTab] = useState('alerts');
  const queryClient = useQueryClient();

  const { data: dashboard, isLoading, refetch, isFetching } = useQuery({
    queryKey: ['dms-ai-dashboard'],
    queryFn: async () => {
      const res = await apiClient.get('/dms-ai/dashboard');
      return res.data;
    },
  });

  const runAgent = useMutation({
    mutationFn: async (agentName: string) => {
      const res = await apiClient.post(`/dms-ai/agents/${agentName}/run`);
      return res.data;
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['dms-ai-dashboard'] }),
  });

  const runDealerPerf = useMutation({
    mutationFn: async () => {
      const res = await apiClient.post('/dms-ai/agents/dealer-performance/run');
      return res.data;
    },
  });

  const runCollections = useMutation({
    mutationFn: async () => {
      const res = await apiClient.post('/dms-ai/agents/collection-optimizer/run');
      return res.data;
    },
  });

  const runSchemes = useMutation({
    mutationFn: async () => {
      const res = await apiClient.post('/dms-ai/agents/scheme-effectiveness/run');
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
  const dealerPerfData = runDealerPerf.data;
  const collectionsData = runCollections.data;
  const schemesData = runSchemes.data;

  return (
    <div className="space-y-6 p-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-amber-100 rounded-lg dark:bg-amber-900/30">
            <Truck className="h-6 w-6 text-amber-600" />
          </div>
          <div>
            <h1 className="text-2xl font-bold tracking-tight">DMS AI Command Center</h1>
            <p className="text-muted-foreground">
              AI agents monitoring distribution management operations 24/7
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
          { label: 'Medium', key: 'MEDIUM', icon: Clock, color: 'text-amber-600', bg: 'bg-amber-50 dark:bg-amber-900/20' },
          { label: 'Low', key: 'LOW', icon: Info, color: 'text-blue-600', bg: 'bg-blue-50 dark:bg-blue-900/20' },
          { label: 'Total Alerts', key: 'total', icon: Zap, color: 'text-amber-600', bg: 'bg-amber-50 dark:bg-amber-900/20' },
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
          <TabsTrigger value="dealer-scores" className="gap-1">
            <BarChart3 className="h-4 w-4" /> Dealer Scores
          </TabsTrigger>
          <TabsTrigger value="collections" className="gap-1">
            <Banknote className="h-4 w-4" /> Collections
          </TabsTrigger>
          <TabsTrigger value="schemes" className="gap-1">
            <BadgePercent className="h-4 w-4" /> Schemes
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
                    {summary.total_alerts || 0} alerts from {summary.agents_ready || 0}/{summary.agents_total || 4} agents
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
                  <p>No active alerts - distribution operations are running smoothly</p>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* ======= TAB: Dealer Scores ======= */}
        <TabsContent value="dealer-scores">
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-lg font-semibold">Dealer Performance Scores</h3>
                <p className="text-sm text-muted-foreground">Achievement, payment, growth, and claim metrics</p>
              </div>
              <Button onClick={() => runDealerPerf.mutate()} disabled={runDealerPerf.isPending} size="sm">
                <Play className={`h-4 w-4 mr-2 ${runDealerPerf.isPending ? 'animate-spin' : ''}`} />
                Run Performance Agent
              </Button>
            </div>

            {dealerPerfData ? (
              <>
                <div className="grid gap-4 md:grid-cols-4">
                  <Card><CardContent className="p-4">
                    <span className="text-sm text-muted-foreground">Dealers Scored</span>
                    <p className="text-2xl font-bold">{dealerPerfData.summary?.total_dealers_scored || 0}</p>
                  </CardContent></Card>
                  <Card className="bg-red-50 dark:bg-red-900/20"><CardContent className="p-4">
                    <span className="text-sm text-red-600">Critical</span>
                    <p className="text-2xl font-bold text-red-600">{dealerPerfData.summary?.critical_dealers || 0}</p>
                  </CardContent></Card>
                  <Card className="bg-orange-50 dark:bg-orange-900/20"><CardContent className="p-4">
                    <span className="text-sm text-orange-600">High Risk</span>
                    <p className="text-2xl font-bold text-orange-600">{dealerPerfData.summary?.high_risk_dealers || 0}</p>
                  </CardContent></Card>
                  <Card><CardContent className="p-4">
                    <span className="text-sm text-muted-foreground">Avg Achievement</span>
                    <p className="text-2xl font-bold">{dealerPerfData.summary?.avg_achievement || 0}%</p>
                  </CardContent></Card>
                </div>

                {(dealerPerfData.dealer_scores || []).length > 0 && (
                  <Card>
                    <CardHeader><CardTitle className="text-base">Dealer Scores</CardTitle></CardHeader>
                    <CardContent>
                      <Table>
                        <TableHeader>
                          <TableRow>
                            <TableHead>Code</TableHead>
                            <TableHead>Name</TableHead>
                            <TableHead>Tier</TableHead>
                            <TableHead className="text-right">Achievement</TableHead>
                            <TableHead className="text-right">Payment Score</TableHead>
                            <TableHead className="text-right">Claim Rate</TableHead>
                            <TableHead className="text-right">Composite</TableHead>
                            <TableHead>Severity</TableHead>
                          </TableRow>
                        </TableHeader>
                        <TableBody>
                          {(dealerPerfData.dealer_scores || []).slice(0, 20).map((d: any, i: number) => (
                            <TableRow key={i}>
                              <TableCell className="font-mono text-sm">{d.dealer_code}</TableCell>
                              <TableCell>{d.name}</TableCell>
                              <TableCell><Badge variant="outline" className="text-xs">{d.tier}</Badge></TableCell>
                              <TableCell className="text-right">
                                <span className={d.achievement_pct < 50 ? 'text-red-600 font-semibold' : d.achievement_pct < 70 ? 'text-orange-600' : ''}>
                                  {d.achievement_pct}%
                                </span>
                              </TableCell>
                              <TableCell className="text-right">{d.payment_score}</TableCell>
                              <TableCell className="text-right">{d.claim_rate}%</TableCell>
                              <TableCell className="text-right font-semibold">{d.composite_score}</TableCell>
                              <TableCell>{severityBadge(d.severity)}</TableCell>
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
                <h3 className="text-lg font-semibold">No Performance Data</h3>
                <p className="text-muted-foreground mt-1">Click &quot;Run Performance Agent&quot; to score dealers</p>
              </CardContent></Card>
            )}
          </div>
        </TabsContent>

        {/* ======= TAB: Collections ======= */}
        <TabsContent value="collections">
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-lg font-semibold">Collection Optimizer</h3>
                <p className="text-sm text-muted-foreground">Aging analysis, payment prediction, and priority ranking</p>
              </div>
              <Button onClick={() => runCollections.mutate()} disabled={runCollections.isPending} size="sm">
                <Play className={`h-4 w-4 mr-2 ${runCollections.isPending ? 'animate-spin' : ''}`} />
                Run Collection Agent
              </Button>
            </div>

            {collectionsData ? (
              <>
                <div className="grid gap-4 md:grid-cols-4">
                  <Card><CardContent className="p-4">
                    <span className="text-sm text-muted-foreground">Total Outstanding</span>
                    <p className="text-2xl font-bold">{(collectionsData.summary?.total_outstanding || 0).toLocaleString()}</p>
                  </CardContent></Card>
                  <Card className="bg-red-50 dark:bg-red-900/20"><CardContent className="p-4">
                    <span className="text-sm text-red-600">Overdue Dealers</span>
                    <p className="text-2xl font-bold text-red-600">{collectionsData.summary?.total_overdue_dealers || 0}</p>
                  </CardContent></Card>
                  <Card className="bg-orange-50 dark:bg-orange-900/20"><CardContent className="p-4">
                    <span className="text-sm text-orange-600">90+ Days</span>
                    <p className="text-2xl font-bold text-orange-600">{(collectionsData.summary?.aging_buckets?.['90+'] || 0).toLocaleString()}</p>
                  </CardContent></Card>
                  <Card><CardContent className="p-4">
                    <span className="text-sm text-muted-foreground">61-90 Days</span>
                    <p className="text-2xl font-bold">{(collectionsData.summary?.aging_buckets?.['61-90'] || 0).toLocaleString()}</p>
                  </CardContent></Card>
                </div>

                {(collectionsData.priority_ranking || []).length > 0 && (
                  <Card>
                    <CardHeader><CardTitle className="text-base">Priority Ranking</CardTitle></CardHeader>
                    <CardContent>
                      <Table>
                        <TableHeader>
                          <TableRow>
                            <TableHead>#</TableHead>
                            <TableHead>Code</TableHead>
                            <TableHead>Name</TableHead>
                            <TableHead className="text-right">Outstanding</TableHead>
                            <TableHead className="text-right">Overdue</TableHead>
                            <TableHead className="text-right">Max Days</TableHead>
                            <TableHead className="text-right">Priority</TableHead>
                            <TableHead>Strategy</TableHead>
                            <TableHead>Severity</TableHead>
                          </TableRow>
                        </TableHeader>
                        <TableBody>
                          {(collectionsData.priority_ranking || []).slice(0, 15).map((p: any, i: number) => (
                            <TableRow key={i}>
                              <TableCell className="text-muted-foreground">{i + 1}</TableCell>
                              <TableCell className="font-mono text-sm">{p.dealer_code}</TableCell>
                              <TableCell>{p.name}</TableCell>
                              <TableCell className="text-right">{p.outstanding?.toLocaleString()}</TableCell>
                              <TableCell className="text-right font-semibold text-red-600">{p.overdue?.toLocaleString()}</TableCell>
                              <TableCell className="text-right">{p.max_days_overdue}d</TableCell>
                              <TableCell className="text-right font-semibold">{p.priority_score}</TableCell>
                              <TableCell className="text-sm text-muted-foreground max-w-[150px] truncate">{p.strategy}</TableCell>
                              <TableCell>{severityBadge(p.severity)}</TableCell>
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
                <Banknote className="h-16 w-16 mx-auto mb-4 text-muted-foreground opacity-50" />
                <h3 className="text-lg font-semibold">No Collection Data</h3>
                <p className="text-muted-foreground mt-1">Click &quot;Run Collection Agent&quot; to analyze aging and priorities</p>
              </CardContent></Card>
            )}
          </div>
        </TabsContent>

        {/* ======= TAB: Schemes ======= */}
        <TabsContent value="schemes">
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-lg font-semibold">Scheme Effectiveness</h3>
                <p className="text-sm text-muted-foreground">ROI, budget utilization, and participation rates</p>
              </div>
              <Button onClick={() => runSchemes.mutate()} disabled={runSchemes.isPending} size="sm">
                <Play className={`h-4 w-4 mr-2 ${runSchemes.isPending ? 'animate-spin' : ''}`} />
                Run Scheme Agent
              </Button>
            </div>

            {schemesData ? (
              <>
                <div className="grid gap-4 md:grid-cols-4">
                  <Card><CardContent className="p-4">
                    <span className="text-sm text-muted-foreground">Schemes Analyzed</span>
                    <p className="text-2xl font-bold">{schemesData.summary?.total_schemes_analyzed || 0}</p>
                  </CardContent></Card>
                  <Card><CardContent className="p-4">
                    <span className="text-sm text-muted-foreground">Active Schemes</span>
                    <p className="text-2xl font-bold">{schemesData.summary?.active_schemes || 0}</p>
                  </CardContent></Card>
                  <Card className="bg-amber-50 dark:bg-amber-900/20"><CardContent className="p-4">
                    <span className="text-sm text-amber-600">Avg ROI</span>
                    <p className="text-2xl font-bold text-amber-600">{schemesData.summary?.avg_roi || 0}%</p>
                  </CardContent></Card>
                  <Card><CardContent className="p-4">
                    <span className="text-sm text-muted-foreground">Total Budget</span>
                    <p className="text-2xl font-bold">{(schemesData.summary?.total_budget || 0).toLocaleString()}</p>
                  </CardContent></Card>
                </div>

                {(schemesData.scheme_scores || []).length > 0 && (
                  <Card>
                    <CardHeader><CardTitle className="text-base">Scheme Scores</CardTitle></CardHeader>
                    <CardContent>
                      <Table>
                        <TableHeader>
                          <TableRow>
                            <TableHead>Code</TableHead>
                            <TableHead>Name</TableHead>
                            <TableHead>Type</TableHead>
                            <TableHead className="text-right">ROI</TableHead>
                            <TableHead className="text-right">Budget Util</TableHead>
                            <TableHead className="text-right">Participation</TableHead>
                            <TableHead className="text-right">Applications</TableHead>
                            <TableHead>Status</TableHead>
                            <TableHead>Severity</TableHead>
                          </TableRow>
                        </TableHeader>
                        <TableBody>
                          {(schemesData.scheme_scores || []).slice(0, 15).map((s: any, i: number) => (
                            <TableRow key={i}>
                              <TableCell className="font-mono text-sm">{s.scheme_code}</TableCell>
                              <TableCell>{s.scheme_name}</TableCell>
                              <TableCell><Badge variant="outline" className="text-xs">{s.scheme_type?.replace(/_/g, ' ')}</Badge></TableCell>
                              <TableCell className="text-right">
                                <span className={s.roi < 50 ? 'text-red-600 font-semibold' : s.roi < 100 ? 'text-orange-600' : 'text-green-600'}>
                                  {s.roi}%
                                </span>
                              </TableCell>
                              <TableCell className="text-right">{s.budget_utilization_pct}%</TableCell>
                              <TableCell className="text-right">{s.participation_rate_pct}%</TableCell>
                              <TableCell className="text-right">{s.applications}</TableCell>
                              <TableCell><Badge variant={s.is_active ? 'default' : 'secondary'} className="text-xs">{s.is_active ? 'Active' : 'Inactive'}</Badge></TableCell>
                              <TableCell>{severityBadge(s.severity)}</TableCell>
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
                <BadgePercent className="h-16 w-16 mx-auto mb-4 text-muted-foreground opacity-50" />
                <h3 className="text-lg font-semibold">No Scheme Data</h3>
                <p className="text-muted-foreground mt-1">Click &quot;Run Scheme Agent&quot; to analyze scheme effectiveness</p>
              </CardContent></Card>
            )}
          </div>
        </TabsContent>

        {/* ======= TAB: Agent Status ======= */}
        <TabsContent value="agents">
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-2">
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
                        onClick={() => runAgent.mutate(agent.id)}
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
